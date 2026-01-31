"""Push notifications service for OLX Monitor"""

from typing import Optional
from nicegui import ui
from services.logger import get_logger

logger = get_logger("olx_monitor.notifications")


async def notify_price_alert(
    ad_title: str,
    old_price: str,
    new_price: str,
    target_price: float,
    ad_url: str,
    image_url: Optional[str] = None
):
    """
    Send price alert notification via NiceGUI.

    This uses NiceGUI's notification system which works within the browser.
    For push notifications when browser is closed, the service worker handles it.

    Args:
        ad_title: Title of the ad
        old_price: Previous price
        new_price: Current price
        target_price: Target price that triggered the alert
        ad_url: URL of the ad
        image_url: Optional image URL for the notification
    """
    message = f"Preço baixou para R$ {new_price}!"
    if target_price:
        message = f"Preço atingiu R$ {new_price} (alvo: R$ {target_price:.2f})"

    logger.info(f"Price alert: {ad_title} - {old_price} -> {new_price}")

    # Show in-app notification
    ui.notify(
        message=f"{ad_title[:40]}... - {message}",
        type='positive',
        position='top-right',
        timeout=10000,
        close_button=True,
        actions=[{
            'label': 'Ver',
            'color': 'white',
            'handler': lambda: ui.navigate.to(ad_url, new_tab=True)
        }]
    )


def format_price_notification(
    ad_title: str,
    old_price: str,
    new_price: str,
    target_price: float,
    ad_url: str,
    ad_id: int,
    image_url: Optional[str] = None
) -> dict:
    """
    Format notification data for push notification via service worker.

    Returns a dict that can be sent to the service worker.
    """
    return {
        'title': 'Alerta de Preço - OLX Monitor',
        'body': f'{ad_title[:50]}...\nPreço: R$ {old_price} → R$ {new_price}\nAlvo: R$ {target_price:.2f}',
        'icon': '/static/icon-192.png',
        'image': image_url,
        'tag': f'price-alert-{ad_id}',
        'url': ad_url,
        'adId': ad_id
    }


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
        notify_below: If True, trigger when price <= target. If False, trigger when price >= target.

    Returns:
        True if alert should trigger
    """
    try:
        # Parse Brazilian price format
        current_price = float(current_price_str.replace('.', '').replace(',', '.'))

        if notify_below:
            return current_price <= target_price
        else:
            return current_price >= target_price
    except (ValueError, AttributeError):
        return False
