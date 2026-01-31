from nicegui import ui
from models import Ad
from services.database import get_inactive_ads, get_distinct_states
from services.scheduler import run_status_check_now, get_task_status
from components.ad_modal import AdModal


class HistoryPage:
    def __init__(self):
        self.container = None
        self.modal = AdModal(on_update=self.refresh)
        self.min_price = None
        self.max_price = None
        self.state = None
        self.search_text = None
        self.check_button = None
        self.check_spinner = None
        self.check_result = None
        self.check_timer = None

    def create(self):
        with ui.column().classes('w-full max-w-7xl mx-auto p-4 gap-4'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-0'):
                    ui.label('Histórico').classes('text-2xl font-bold')
                    ui.label('Anúncios que foram desativados ou expiraram').classes('text-sm text-gray-500')
                self._create_check_button()
            self._create_search_box()
            self._create_filters()
            self.container = ui.element('div').classes('w-full')
            self.refresh()

    def _create_search_box(self):
        with ui.row().classes('w-full gap-2 items-center'):
            self.search_input = ui.input(
                placeholder='Buscar por título ou descrição...',
            ).props('dense outlined rounded clearable').classes('flex-grow')
            self.search_input.on('keydown.enter', lambda: self._set_search_text(self.search_input.value))
            ui.button(icon='search', on_click=lambda: self._set_search_text(self.search_input.value)).props('flat round dense')

    def _set_search_text(self, value):
        self.search_text = value.strip() if value else None
        self.refresh()

    def _create_filters(self):
        states = get_distinct_states()

        with ui.expansion('Filtros', icon='filter_list').classes('w-full rounded-xl overflow-hidden').props('dense header-class="text-weight-medium"'):
            with ui.row().classes('w-full flex-wrap gap-3 items-center py-2'):
                self.min_input = ui.number(
                    label='Preço min',
                    on_change=lambda e: self._set_min_price(e.value)
                ).props('dense outlined rounded prefix="R$"').classes('w-28')

                self.max_input = ui.number(
                    label='Preço max',
                    on_change=lambda e: self._set_max_price(e.value)
                ).props('dense outlined rounded prefix="R$"').classes('w-28')

                state_options = {None: 'Todos'}
                for s in states:
                    if s:
                        state_options[s] = s.replace('#', '')

                self.state_select = ui.select(
                    label='Estado',
                    options=state_options,
                    value=None,
                    on_change=lambda e: self._set_state(e.value)
                ).props('dense outlined rounded').classes('min-w-[100px]')

                ui.button(icon='clear', on_click=self._clear_filters).props('flat round dense').tooltip('Limpar filtros')

    def _set_min_price(self, value):
        self.min_price = value if value else None
        self.refresh()

    def _set_max_price(self, value):
        self.max_price = value if value else None
        self.refresh()

    def _set_state(self, value):
        self.state = value
        self.refresh()

    def _clear_filters(self):
        self.min_price = None
        self.max_price = None
        self.state = None
        self.search_text = None
        self.min_input.set_value(None)
        self.max_input.set_value(None)
        self.state_select.set_value(None)
        self.search_input.set_value('')
        self.refresh()

    def _create_check_button(self):
        with ui.row().classes('items-center gap-2'):
            self.check_result = ui.label('').classes('text-sm text-gray-500')
            with ui.element('div').classes('relative'):
                self.check_button = ui.button(
                    'Verificar Status',
                    icon='fact_check',
                    on_click=self._on_check_click
                ).props('outline color=primary rounded')
                self.check_spinner = ui.spinner('dots', size='sm').classes('absolute inset-0 m-auto')
                self.check_spinner.set_visibility(False)

    async def _on_check_click(self):
        status = get_task_status('status_check')
        if status['running']:
            ui.notify('Verificação já está em execução', type='warning')
            return

        started = run_status_check_now()
        if not started:
            ui.notify('Não foi possível iniciar a verificação', type='negative')
            return

        self.check_button.disable()
        self.check_button.props('loading')
        self.check_spinner.set_visibility(True)
        self.check_result.set_text('Verificando...')
        self.check_timer = ui.timer(1.0, self._check_progress)

    async def _check_progress(self):
        status = get_task_status('status_check')
        if not status['running']:
            if self.check_timer:
                self.check_timer.cancel()
                self.check_timer = None

            self.check_button.enable()
            self.check_button.props(remove='loading')
            self.check_spinner.set_visibility(False)

            result = status['result']
            if result and result.get('success'):
                deactivated = result.get('deactivated', 0)
                if deactivated > 0:
                    self.check_result.set_text(f'{deactivated} desativados!')
                    self.check_result.classes(remove='text-gray-500', add='text-orange-600')
                    ui.notify(f'{deactivated} anúncios marcados como inativos!', type='warning')
                else:
                    self.check_result.set_text('Nenhum inativo')
                    self.check_result.classes(remove='text-orange-600', add='text-gray-500')
                self.refresh()
            elif result:
                self.check_result.set_text('Erro')
                self.check_result.classes(add='text-red-600')

    def refresh(self):
        if self.container:
            self.container.clear()

            ads_data = get_inactive_ads(
                min_price=self.min_price,
                max_price=self.max_price,
                state=self.state,
                search_text=self.search_text
            )

            if not ads_data:
                with self.container:
                    with ui.column().classes('w-full items-center py-10'):
                        ui.icon('history', size='xl').classes('text-gray-400')
                        ui.label('Nenhum anúncio no histórico').classes('text-gray-500')
                        ui.label('Anúncios desativados aparecerão aqui').classes('text-sm text-gray-400')
                return

            with self.container:
                ui.label(f'{len(ads_data)} anúncios no histórico').classes('text-sm text-gray-500 mb-2')
                with ui.element('div').classes('grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2 sm:gap-4 w-full'):
                    for ad_data in ads_data:
                        ad = Ad.from_dict(ad_data)
                        self._create_history_card(ad)

    def _create_history_card(self, ad: Ad):
        with ui.card().classes('cursor-pointer hover:shadow-lg transition-shadow rounded-xl overflow-hidden opacity-75').on('click', lambda: self.modal.show(ad)):
            # Imagem
            if ad.first_image:
                ui.image(ad.first_image).classes('w-full h-28 sm:h-40 object-cover grayscale')
            else:
                with ui.element('div').classes('w-full h-28 sm:h-40 bg-gray-200 flex items-center justify-center'):
                    ui.icon('image', size='xl').classes('text-gray-400')

            with ui.column().classes('p-2 sm:p-3 gap-1 sm:gap-2'):
                # Título
                ui.label(ad.title).classes('font-semibold text-xs sm:text-sm line-clamp-2')

                # Preço
                with ui.row().classes('items-center justify-between'):
                    ui.label(f'R$ {ad.price}').classes('text-sm sm:text-lg font-bold text-gray-500 line-through')
                    ui.badge('Inativo').props('color=red dense')

                # Localização
                ui.label(ad.location).classes('text-xs text-gray-500 truncate')

                # Datas (só desktop)
                with ui.row().classes('gap-2 flex-wrap hidden sm:flex'):
                    if ad.found_at_formatted:
                        ui.label(f'Encontrado: {ad.found_at_formatted}').classes('text-xs text-gray-400')
                    if ad.deactivated_at_formatted:
                        ui.label(f'Inativo: {ad.deactivated_at_formatted}').classes('text-xs text-red-400')
