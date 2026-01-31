"""Push notifications service for OLX Monitor"""

import json
from typing import Optional
from pywebpush import webpush, WebPushException
from py_vapid import Vapid

from services.database import (
    get_all_push_subscriptions, delete_push_subscription,
    get_setting, set_setting
)
from services.logger import get_logger

logger = get_logger("olx_monitor.notifications")

# Price threshold for automatic notifications on new ads
NEW_AD_PRICE_THRESHOLD = 150.0


def get_or_create_vapid_keys() -> tuple[str, str]:
    """
    Get existing VAPID keys or create new ones.

    Returns:
        Tuple of (public_key, private_key) in base64 format
    """
    public_key = get_setting('vapid_public_key')
    private_key = get_setting('vapid_private_key')

    if public_key and private_key:
        return public_key, private_key

    # Generate new keys
    logger.info("Generating new VAPID keys...")
    vapid = Vapid()
    vapid.generate_keys()

    # Get keys in the format webpush expects
    public_key = vapid.public_key.public_bytes(
        encoding=vapid.public_key.public_bytes.__self__.__class__.__module__.split('.')[0] == 'cryptography'
        and __import__('cryptography.hazmat.primitives.serialization', fromlist=['Encoding']).Encoding.X962
        or None,
        format=__import__('cryptography.hazmat.primitives.serialization', fromlist=['PublicFormat']).PublicFormat.UncompressedPoint
    )

    import base64
    from cryptography.hazmat.primitives import serialization

    # Get raw public key bytes for applicationServerKey
    public_key_bytes = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')

    # Get private key in PEM format for pywebpush
    private_key_pem = vapid.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    # Save to database
    set_setting('vapid_public_key', public_key_b64)
    set_setting('vapid_private_key', private_key_pem)

    logger.info("VAPID keys generated and saved")
    return public_key_b64, private_key_pem


def get_vapid_public_key() -> str:
    """Get the public VAPID key for the frontend"""
    public_key, _ = get_or_create_vapid_keys()
    return public_key


def send_push_notification(
    title: str,
    body: str,
    url: Optional[str] = None,
    tag: Optional[str] = None,
    image: Optional[str] = None
) -> int:
    """
    Send push notification to all subscribed clients.

    Args:
        title: Notification title
        body: Notification body text
        url: URL to open when notification is clicked
        tag: Tag for grouping notifications
        image: Image URL to show in notification

    Returns:
        Number of notifications sent successfully
    """
    subscriptions = get_all_push_subscriptions()

    if not subscriptions:
        logger.debug("No push subscriptions found")
        return 0

    public_key, private_key = get_or_create_vapid_keys()

    payload = json.dumps({
        'title': title,
        'body': body,
        'url': url or '/',
        'tag': tag or 'olx-monitor',
        'image': image,
        'icon': '/static/icon-192.png',
        'badge': '/static/icon-192.png'
    })

    sent = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub['endpoint'],
                    'keys': {
                        'p256dh': sub['p256dh'],
                        'auth': sub['auth']
                    }
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={
                    'sub': 'mailto:noreply@olx-monitor.local'
                }
            )
            sent += 1
        except WebPushException as e:
            logger.warning(f"Push failed for {sub['endpoint'][:50]}...: {e}")
            # Remove invalid subscriptions (410 Gone, 404 Not Found)
            if e.response and e.response.status_code in (404, 410):
                delete_push_subscription(sub['endpoint'])
                logger.info("Removed invalid subscription")
        except Exception as e:
            logger.error(f"Unexpected error sending push: {e}")

    logger.info(f"Sent {sent}/{len(subscriptions)} push notifications")
    return sent


def notify_price_drop(
    ad_title: str,
    old_price: str,
    new_price: str,
    ad_url: str,
    image_url: Optional[str] = None
) -> int:
    """
    Send notification when a watched ad's price drops.

    Args:
        ad_title: Title of the ad
        old_price: Previous price
        new_price: New (lower) price
        ad_url: URL of the ad
        image_url: First image of the ad

    Returns:
        Number of notifications sent
    """
    title = "Preço baixou!"
    body = f"{ad_title[:50]}\nR$ {old_price} → R$ {new_price}"

    logger.info(f"Price drop notification: {ad_title} - {old_price} -> {new_price}")

    return send_push_notification(
        title=title,
        body=body,
        url=ad_url,
        tag=f"price-drop-{hash(ad_url) % 10000}",
        image=image_url
    )


def notify_cheap_ad(
    ad_title: str,
    price: str,
    ad_url: str,
    image_url: Optional[str] = None
) -> int:
    """
    Send notification when a new ad is found with price <= threshold.

    Args:
        ad_title: Title of the ad
        price: Price of the ad
        ad_url: URL of the ad
        image_url: First image of the ad

    Returns:
        Number of notifications sent
    """
    title = f"Novo anúncio por R$ {price}!"
    body = ad_title[:80]

    logger.info(f"Cheap ad notification: {ad_title} - R$ {price}")

    return send_push_notification(
        title=title,
        body=body,
        url=ad_url,
        tag=f"cheap-ad-{hash(ad_url) % 10000}",
        image=image_url
    )


def notify_price_alert(
    ad_title: str,
    current_price: str,
    target_price: float,
    ad_url: str,
    image_url: Optional[str] = None
) -> int:
    """
    Send notification when price alert is triggered.

    Args:
        ad_title: Title of the ad
        current_price: Current price
        target_price: Target price that was set
        ad_url: URL of the ad
        image_url: First image of the ad

    Returns:
        Number of notifications sent
    """
    title = "Alerta de Preço Atingido!"
    body = f"{ad_title[:50]}\nR$ {current_price} (alvo: R$ {target_price:.2f})"

    logger.info(f"Price alert notification: {ad_title} - R$ {current_price} <= R$ {target_price}")

    return send_push_notification(
        title=title,
        body=body,
        url=ad_url,
        tag=f"price-alert-{hash(ad_url) % 10000}",
        image=image_url
    )


def check_price_alert_trigger(
    current_price_str: str,
    target_price: float,
    notify_below: bool = True
) -> bool:
    """
    Check if a price alert should be triggered.

    Args:
        current_price_str: Current price as string (e.g., "100,00")
        target_price: Target price as float
        notify_below: If True, trigger when price <= target

    Returns:
        True if alert should trigger
    """
    try:
        current_price = parse_price(current_price_str)
        if notify_below:
            return current_price <= target_price
        else:
            return current_price >= target_price
    except (ValueError, AttributeError):
        return False


def is_price_drop(old_price_str: str, new_price_str: str) -> bool:
    """Check if price dropped"""
    try:
        old_price = parse_price(old_price_str)
        new_price = parse_price(new_price_str)
        return new_price < old_price
    except (ValueError, AttributeError):
        return False


def is_cheap_ad(price_str: str, threshold: float = NEW_AD_PRICE_THRESHOLD) -> bool:
    """Check if ad price is at or below threshold"""
    try:
        price = parse_price(price_str)
        return price <= threshold
    except (ValueError, AttributeError):
        return False


def parse_price(price_str: str) -> float:
    """Parse Brazilian price format to float"""
    if not price_str:
        return 0.0
    # "1.234,56" -> 1234.56
    return float(price_str.replace('.', '').replace(',', '.'))
