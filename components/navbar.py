from nicegui import ui
from services.database import get_unread_notification_count


def _nav_button_desktop(label: str, icon: str, path: str):
    ui.button(label, icon=icon, on_click=lambda: ui.navigate.to(path)).props(
        'flat dense no-caps'
    ).classes('text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg px-3')


def _nav_button_mobile(label: str, icon: str, path: str):
    with ui.column().classes('items-center gap-0 cursor-pointer min-w-[60px]').on('click', lambda: ui.navigate.to(path)):
        ui.icon(icon, size='sm').classes('text-gray-600')
        ui.label(label).classes('text-xs text-gray-600')


def _notification_button():
    """Button with badge for notifications (desktop)"""
    count = get_unread_notification_count()
    with ui.button(on_click=lambda: ui.navigate.to('/notifications')).props('flat round dense').classes('text-gray-500 hover:text-amber-500') as btn:
        ui.icon('notifications', size='sm')
        if count > 0:
            ui.badge(str(count)).props('color=red floating')
    btn.tooltip('Notificações')


def _notification_button_mobile():
    """Button with badge for notifications (mobile)"""
    count = get_unread_notification_count()
    with ui.column().classes('items-center gap-0 cursor-pointer min-w-[60px]').on('click', lambda: ui.navigate.to('/notifications')):
        with ui.element('div').classes('relative'):
            ui.icon('notifications', size='sm').classes('text-gray-600')
            if count > 0:
                ui.badge(str(count)).props('color=red floating')


def create_navbar():
    # CSS para responsividade
    ui.add_head_html('''
    <style>
        .desktop-nav { display: flex !important; }
        .mobile-nav { display: none !important; }
        @media (max-width: 768px) {
            .desktop-nav { display: none !important; }
            .mobile-nav { display: flex !important; }
            body { padding-bottom: 60px !important; }
        }
    </style>
    ''')

    # Header
    with ui.header().classes('bg-white border-b border-gray-200'):
        with ui.row().classes('w-full max-w-7xl mx-auto items-center justify-between px-4 py-2'):
            # Logo
            with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
                ui.icon('saved_search', size='sm').classes('text-blue-600')
                ui.label('OLX Monitor').classes('text-lg font-semibold text-gray-800')

            # Botões desktop
            with ui.row().classes('gap-1 desktop-nav items-center'):
                _nav_button_desktop('Home', 'home', '/')
                _nav_button_desktop('Acompanhando', 'visibility', '/watching')
                _nav_button_desktop('Histórico', 'history', '/history')
                _nav_button_desktop('Config', 'settings', '/config')
                _nav_button_desktop('Logs', 'schedule', '/logs')

                # Notification button
                _notification_button()

    # Footer mobile
    with ui.footer().classes('bg-white border-t border-gray-200 mobile-nav'):
        with ui.row().classes('w-full justify-around items-center py-2'):
            _nav_button_mobile('Home', 'home', '/')
            _nav_button_mobile('Acompanhar', 'visibility', '/watching')
            _nav_button_mobile('Histórico', 'history', '/history')
            _nav_button_mobile('Config', 'settings', '/config')
            _notification_button_mobile()
