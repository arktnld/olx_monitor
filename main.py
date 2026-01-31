from pathlib import Path
from nicegui import ui, app
from fastapi import Request
from fastapi.responses import JSONResponse
from services.database import init_db, save_push_subscription
from services.scheduler import start_scheduler, stop_scheduler
from services.notifications import get_vapid_public_key
from components.navbar import create_navbar
from pages.home import HomePage
from pages.watching import WatchingPage
from pages.history import HistoryPage
from pages.config import ConfigPage
from pages.logs import LogsPage


init_db()

# Servir imagens locais
IMAGES_DIR = Path(__file__).parent / "data" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.add_static_files('/images', IMAGES_DIR)

# Servir arquivos estáticos (PWA)
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.add_static_files('/static', STATIC_DIR)
# Service worker na raiz (Chrome espera /sw.js)
app.add_static_file(local_file=STATIC_DIR / "service_worker.js", url_path="/sw.js")

ui.add_head_html('''
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="manifest" href="/static/manifest.json">
<link rel="apple-touch-icon" href="/static/icon-192.png">
<meta name="theme-color" content="#3b82f6">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="OLX Monitor">
<script>
// Service Worker and Push Notifications
async function setupPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications not supported');
        return;
    }

    try {
        // Register service worker
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.log('Service Worker registered');

        // Check if already subscribed
        let subscription = await registration.pushManager.getSubscription();

        if (!subscription) {
            // Get VAPID public key from server
            const response = await fetch('/api/vapid-public-key');
            const { publicKey } = await response.json();

            // Convert base64 to Uint8Array
            const padding = '='.repeat((4 - publicKey.length % 4) % 4);
            const base64 = (publicKey + padding).replace(/-/g, '+').replace(/_/g, '/');
            const rawData = window.atob(base64);
            const applicationServerKey = new Uint8Array(rawData.length);
            for (let i = 0; i < rawData.length; ++i) {
                applicationServerKey[i] = rawData.charCodeAt(i);
            }

            // Subscribe to push
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            });

            // Send subscription to server
            await fetch('/api/push-subscription', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subscription: subscription.toJSON() })
            });

            console.log('Push subscription saved');
        }
    } catch (error) {
        console.error('Push notification setup failed:', error);
    }
}

// Request notification permission on user interaction
window.requestNotificationPermission = async function() {
    if (!('Notification' in window)) {
        alert('Este navegador não suporta notificações');
        return false;
    }

    if (Notification.permission === 'granted') {
        await setupPushNotifications();
        return true;
    }

    if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            await setupPushNotifications();
            return true;
        }
    }

    return false;
};

// Auto-setup if permission already granted
if ('Notification' in window && Notification.permission === 'granted') {
    setupPushNotifications();
} else if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
}
</script>
<style>
    body, .q-page, .nicegui-content {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
</style>
''', shared=True)


@ui.page('/')
def home_page():
    create_navbar()
    HomePage().create()


@ui.page('/watching')
def watching_page():
    create_navbar()
    WatchingPage().create()


@ui.page('/history')
def history_page():
    create_navbar()
    HistoryPage().create()


@ui.page('/config')
def config_page():
    create_navbar()
    ConfigPage().create()


@ui.page('/logs')
def logs_page():
    create_navbar()
    LogsPage().create()


@app.get('/api/vapid-public-key')
def api_vapid_public_key():
    """Get the VAPID public key for push notifications"""
    return JSONResponse({'publicKey': get_vapid_public_key()})


@app.post('/api/push-subscription')
async def api_push_subscription(request: Request):
    """Save a push notification subscription"""
    try:
        data = await request.json()
        subscription = data.get('subscription', {})

        endpoint = subscription.get('endpoint')
        keys = subscription.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not all([endpoint, p256dh, auth]):
            return JSONResponse({'error': 'Missing subscription data'}, status_code=400)

        save_push_subscription(endpoint, p256dh, auth)
        return JSONResponse({'success': True})
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@app.on_startup
def on_startup():
    start_scheduler()

    # Generate VAPID keys on startup if they don't exist
    get_vapid_public_key()

    # Baixar imagens dos anúncios acompanhados que ainda não têm imagens locais
    from services.images import download_watching_ads_images
    downloaded = download_watching_ads_images()
    if downloaded > 0:
        print(f"Imagens baixadas para {downloaded} anúncios acompanhados")


@app.on_shutdown
def on_shutdown():
    stop_scheduler()


ui.run(
    title='OLX Ads Monitor',
    favicon='🔍',
    dark=False,
    reload=False,
    port=8088
)
