from nicegui import ui
from services.database import get_notification_history, mark_notifications_read


class NotificationsPage:
    PAGE_SIZE = 20

    def __init__(self):
        self.container = None
        self.status_container = None
        self.load_more_btn = None
        self.offset = 0
        self.has_more = True

    def create(self):
        # Marcar todas como lidas ao entrar na página
        mark_notifications_read()

        with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Histórico de Notificações').classes('text-2xl font-bold')

            # Status das notificações push
            self._create_push_status()

            self.container = ui.element('div').classes('w-full flex flex-col gap-2')
            self._load_notifications()

    def _create_push_status(self):
        with ui.card().classes('w-full p-4 rounded-xl'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('notifications', size='sm').classes('text-gray-600')
                    ui.label('Notificações Push').classes('font-medium')
                    self.status_badge = ui.badge('Verificando...').props('color=grey')

                self.enable_btn = ui.button('Ativar', icon='notifications_active', on_click=self._request_permission).props('color=primary rounded')
                self.enable_btn.set_visibility(False)

        # Verificar status atual
        ui.timer(0.5, self._check_status, once=True)

    async def _check_status(self):
        try:
            result = await ui.run_javascript('''
                (() => {
                    if (!('Notification' in window)) {
                        return { supported: false };
                    }
                    return {
                        supported: true,
                        permission: Notification.permission
                    };
                })();
            ''', timeout=5.0)
            self._update_status(result)
        except Exception:
            self.status_badge.text = 'Erro'
            self.status_badge.props('color=grey')

    def _update_status(self, result):
        if not result or not result.get('supported'):
            self.status_badge.text = 'Não suportado'
            self.status_badge.props('color=grey')
            return

        permission = result.get('permission')
        if permission == 'granted':
            self.status_badge.text = 'Ativo'
            self.status_badge.props('color=green')
            self.enable_btn.set_visibility(False)
        elif permission == 'denied':
            self.status_badge.text = 'Bloqueado'
            self.status_badge.props('color=red')
            self.enable_btn.set_visibility(False)
        else:
            self.status_badge.text = 'Inativo'
            self.status_badge.props('color=orange')
            self.enable_btn.set_visibility(True)

    async def _request_permission(self):
        try:
            result = await ui.run_javascript('''
                (async () => {
                    const granted = await window.requestNotificationPermission();
                    return { granted: granted };
                })();
            ''', timeout=30.0)

            if result and result.get('granted'):
                self.status_badge.text = 'Ativo'
                self.status_badge.props('color=green')
                self.enable_btn.set_visibility(False)
                ui.notify('Notificações ativadas!', type='positive')
            else:
                ui.notify('Não foi possível ativar', type='warning')
        except Exception:
            ui.notify('Erro ao ativar notificações', type='negative')

    def _load_notifications(self):
        notifications = get_notification_history(limit=self.PAGE_SIZE, offset=self.offset)

        if not notifications and self.offset == 0:
            with self.container:
                with ui.column().classes('w-full items-center py-10'):
                    ui.icon('notifications_off', size='xl').classes('text-gray-400')
                    ui.label('Nenhuma notificação ainda').classes('text-gray-500')
            return

        # Se retornou menos do que o PAGE_SIZE, não há mais
        if len(notifications) < self.PAGE_SIZE:
            self.has_more = False

        with self.container:
            for notif in notifications:
                self._create_notification_card(notif)

            # Atualizar offset
            self.offset += len(notifications)

            # Botão carregar mais
            if self.has_more:
                if self.load_more_btn:
                    self.load_more_btn.delete()
                self.load_more_btn = ui.button(
                    'Carregar mais',
                    icon='expand_more',
                    on_click=self._load_more
                ).props('flat color=primary').classes('w-full mt-2')

    def _load_more(self):
        if self.load_more_btn:
            self.load_more_btn.delete()
            self.load_more_btn = None
        self._load_notifications()

    def _create_notification_card(self, notif: dict):
        type_config = {
            'cheap_ad': {
                'icon': 'local_offer',
                'color': 'orange',
                'label': 'Preço Baixo'
            },
            'price_drop': {
                'icon': 'trending_down',
                'color': 'blue',
                'label': 'Preço Caiu'
            },
            'price_alert': {
                'icon': 'notifications_active',
                'color': 'orange',
                'label': 'Alerta de Preço'
            }
        }

        config = type_config.get(notif['type'], {
            'icon': 'notifications',
            'color': 'grey',
            'label': notif['type']
        })

        with ui.card().classes('w-full p-3 rounded-xl'):
            with ui.row().classes('w-full items-start gap-3'):
                # Imagem do anúncio
                if notif.get('image'):
                    ui.image(notif['image']).classes('w-16 h-16 rounded object-cover')
                else:
                    with ui.element('div').classes(f'w-16 h-16 rounded bg-{config["color"]}-100 flex items-center justify-center'):
                        ui.icon(config['icon'], size='md').classes(f'text-{config["color"]}-600')

                # Conteúdo
                with ui.column().classes('flex-grow gap-1'):
                    with ui.row().classes('items-center gap-2'):
                        ui.badge(config['label']).props(f'color={config["color"]}')
                        if notif.get('search_name'):
                            ui.badge(notif['search_name']).props('color=grey outline')
                        if not notif.get('success'):
                            ui.badge('Falhou').props('color=red')

                    # Título
                    title = notif.get('title', 'Sem título')
                    ui.label(title[:60] + ('...' if len(title) > 60 else '')).classes('font-medium')

                    # Preço
                    with ui.row().classes('items-center gap-2'):
                        if notif.get('old_price'):
                            ui.label(f'R$ {notif["old_price"]}').classes('text-gray-400 line-through text-sm')
                            ui.icon('arrow_forward', size='xs').classes('text-gray-400')
                        ui.label(f'R$ {notif["price"]}').classes('text-green-600 font-bold')

                        if notif.get('target_price'):
                            ui.label(f'(alvo: R$ {notif["target_price"]:.0f})').classes('text-xs text-gray-400')

                    # Data
                    ui.label(notif.get('sent_at', '')).classes('text-xs text-gray-400')

                # Link
                if notif.get('url'):
                    ui.button(icon='open_in_new', on_click=lambda u=notif['url']: ui.navigate.to(u, new_tab=True)).props('flat round dense')
