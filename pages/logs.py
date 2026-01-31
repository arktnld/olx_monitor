from nicegui import ui
from datetime import datetime
from services.scheduler import get_logs, clear_logs, get_scheduler_status, reschedule_jobs
from services.database import get_setting, set_setting


class LogsPage:
    def __init__(self):
        self.logs_container = None

    def create(self):
        with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4'):
            ui.label('Scheduler').classes('text-2xl font-bold')

            self._create_status_card()
            self._create_intervals_card()
            self._create_logs_card()

    def _create_status_card(self):
        status = get_scheduler_status()

        with ui.card().classes('w-full p-4 rounded-xl'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-3'):
                    if status['running']:
                        ui.icon('check_circle', color='green').classes('text-2xl')
                        with ui.column().classes('gap-0'):
                            ui.label('Scheduler ativo').classes('font-semibold text-green-700')
                            ui.label('Executando automaticamente').classes('text-xs text-gray-500')
                    else:
                        ui.icon('error', color='red').classes('text-2xl')
                        with ui.column().classes('gap-0'):
                            ui.label('Scheduler inativo').classes('font-semibold text-red-700')
                            ui.label('Reinicie a aplicação').classes('text-xs text-gray-500')

                if status['running'] and status['jobs']:
                    with ui.column().classes('text-right gap-0'):
                        ui.label(f"{len(status['jobs'])} jobs ativos").classes('text-sm text-gray-600')

    def _create_intervals_card(self):
        with ui.card().classes('w-full p-4 rounded-xl'):
            ui.label('Intervalos de Execução').classes('font-semibold text-lg mb-4')

            # Pegar valores atuais ou defaults
            search_interval = int(get_setting('search_interval', '20') or '20')
            price_interval = int(get_setting('price_interval', '20') or '20')
            status_hour = get_setting('status_check_hour', '00:00') or '00:00'

            with ui.column().classes('gap-4 w-full'):
                # Busca de novos anúncios
                with ui.row().classes('w-full items-center justify-between p-3 bg-gray-50 rounded-lg'):
                    with ui.column().classes('gap-0'):
                        ui.label('Buscar novos anúncios').classes('font-medium')
                        ui.label('Procura por novos anúncios nas buscas ativas').classes('text-xs text-gray-500')
                    search_input = ui.number(value=search_interval, min=5, max=120, step=5).props('dense outlined suffix="min"').classes('w-24')

                # Verificar preços
                with ui.row().classes('w-full items-center justify-between p-3 bg-gray-50 rounded-lg'):
                    with ui.column().classes('gap-0'):
                        ui.label('Verificar preços').classes('font-medium')
                        ui.label('Atualiza preços dos anúncios acompanhados').classes('text-xs text-gray-500')
                    price_input = ui.number(value=price_interval, min=5, max=120, step=5).props('dense outlined suffix="min"').classes('w-24')

                # Verificar status
                with ui.row().classes('w-full items-center justify-between p-3 bg-gray-50 rounded-lg'):
                    with ui.column().classes('gap-0'):
                        ui.label('Verificar status').classes('font-medium')
                        ui.label('Verifica se anúncios ainda estão ativos (diário)').classes('text-xs text-gray-500')
                    status_input = ui.input(value=status_hour, placeholder='00:00').props('dense outlined mask="##:##"').classes('w-24')

                with ui.row().classes('w-full justify-end'):
                    ui.button(
                        'Salvar',
                        on_click=lambda: self._save_intervals(
                            search_input.value,
                            price_input.value,
                            status_input.value
                        )
                    ).props('color=primary rounded')

                ui.label('As mudanças são aplicadas imediatamente').classes('text-xs text-gray-400 text-center w-full')

    def _save_intervals(self, search, price, status_hour):
        set_setting('search_interval', str(int(search)))
        set_setting('price_interval', str(int(price)))
        set_setting('status_check_hour', status_hour)

        if reschedule_jobs():
            ui.notify('Intervalos salvos e aplicados!', type='positive')
        else:
            ui.notify('Intervalos salvos! Reinicie a aplicação para aplicar.', type='warning')

    def _create_logs_card(self):
        with ui.card().classes('w-full p-4 rounded-xl'):
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('Logs').classes('font-semibold text-lg')
                with ui.row().classes('gap-2'):
                    ui.button('Limpar', icon='delete', on_click=self._clear_logs).props('flat dense')
                    ui.button('Atualizar', icon='refresh', on_click=self._refresh_logs).props('flat dense')

            self.logs_container = ui.element('div').classes('w-full max-h-96 overflow-y-auto')
            self._render_logs()

    def _render_logs(self):
        if not self.logs_container:
            return

        self.logs_container.clear()
        logs = get_logs()

        with self.logs_container:
            if not logs:
                ui.label('Nenhum log disponível').classes('text-gray-400 italic py-4 text-center')
            else:
                with ui.column().classes('gap-1 font-mono text-xs'):
                    for log in logs:
                        level_colors = {
                            'info': 'text-gray-600',
                            'success': 'text-green-600',
                            'warning': 'text-orange-600',
                            'error': 'text-red-600'
                        }
                        level_icons = {
                            'info': 'info',
                            'success': 'check_circle',
                            'warning': 'warning',
                            'error': 'error'
                        }
                        color = level_colors.get(log['level'], 'text-gray-600')
                        icon = level_icons.get(log['level'], 'info')

                        with ui.row().classes(f'gap-2 items-start py-1 px-2 hover:bg-gray-50 rounded {color}'):
                            ui.icon(icon, size='xs').classes('mt-0.5')
                            ui.label(log['timestamp']).classes('text-gray-400 whitespace-nowrap')
                            ui.label(log['message']).classes('flex-grow')

    def _refresh_logs(self):
        self._render_logs()

    def _clear_logs(self):
        clear_logs()
        self._render_logs()
        ui.notify('Logs limpos', type='info')
