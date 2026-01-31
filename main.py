from pathlib import Path
from nicegui import ui, app
from services.database import init_db
from services.scheduler import start_scheduler, stop_scheduler
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
if ('serviceWorker' in navigator) {
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


@app.on_startup
def on_startup():
    start_scheduler()

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
