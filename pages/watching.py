from nicegui import ui
from models import Ad, PriceHistory, calculate_price_variation
from services.database import get_watching_ads, get_price_history, get_distinct_states
from services.scheduler import run_price_check_now, get_task_status
from components.ad_modal import AdModal


class WatchingPage:
    def __init__(self):
        self.container = None
        self.modal = AdModal(on_update=self.refresh)
        self.min_price = None
        self.max_price = None
        self.state = None
        self.check_button = None
        self.check_spinner = None
        self.check_result = None
        self.check_timer = None

    def create(self):
        with ui.column().classes('w-full max-w-7xl mx-auto p-4 gap-4'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Acompanhando').classes('text-2xl font-bold')
                self._create_check_button()
            self._create_filters()
            self.container = ui.element('div').classes('w-full')
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
        self.min_input.set_value(None)
        self.max_input.set_value(None)
        self.state_select.set_value(None)
        self.refresh()

    def _create_check_button(self):
        with ui.row().classes('items-center gap-2'):
            self.check_result = ui.label('').classes('text-sm text-gray-500')
            with ui.element('div').classes('relative'):
                self.check_button = ui.button(
                    'Verificar Preços',
                    icon='price_check',
                    on_click=self._on_check_click
                ).props('outline color=primary rounded')
                self.check_spinner = ui.spinner('dots', size='sm').classes('absolute inset-0 m-auto')
                self.check_spinner.set_visibility(False)

    async def _on_check_click(self):
        status = get_task_status('price_check')
        if status['running']:
            ui.notify('Verificação já está em execução', type='warning')
            return

        started = run_price_check_now()
        if not started:
            ui.notify('Não foi possível iniciar a verificação', type='negative')
            return

        self.check_button.disable()
        self.check_button.props('loading')
        self.check_spinner.set_visibility(True)
        self.check_result.set_text('Verificando...')
        self.check_timer = ui.timer(1.0, self._check_progress)

    async def _check_progress(self):
        status = get_task_status('price_check')
        if not status['running']:
            if self.check_timer:
                self.check_timer.cancel()
                self.check_timer = None

            self.check_button.enable()
            self.check_button.props(remove='loading')
            self.check_spinner.set_visibility(False)

            result = status['result']
            if result and result.get('success'):
                changes = result.get('price_changes', 0)
                if changes > 0:
                    self.check_result.set_text(f'{changes} preços alterados!')
                    self.check_result.classes(remove='text-gray-500', add='text-green-600')
                    ui.notify(f'{changes} alterações de preço encontradas!', type='positive')
                else:
                    self.check_result.set_text('Sem alterações')
                    self.check_result.classes(remove='text-green-600', add='text-gray-500')
                self.refresh()
            elif result:
                self.check_result.set_text('Erro')
                self.check_result.classes(add='text-red-600')

    def refresh(self):
        if self.container:
            self.container.clear()

            ads_data = get_watching_ads(
                min_price=self.min_price,
                max_price=self.max_price,
                state=self.state
            )

            if not ads_data:
                with self.container:
                    with ui.column().classes('w-full items-center py-10'):
                        ui.icon('visibility_off', size='xl').classes('text-gray-400')
                        ui.label('Nenhum anúncio sendo acompanhado').classes('text-gray-500')
                        ui.label('Clique em "Acompanhar" em um anúncio para monitorar o preço').classes('text-sm text-gray-400')
                return

            with self.container:
                with ui.element('div').classes('grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2 sm:gap-4 w-full'):
                    for ad_data in ads_data:
                        ad = Ad.from_dict(ad_data)
                        self._create_watching_card(ad)

    def _create_watching_card(self, ad: Ad):
        history_data = get_price_history(ad.id)
        history = [PriceHistory.from_dict(h) for h in history_data]
        variation_value, variation_str = calculate_price_variation(history)
        is_inactive = ad.status == 'inactive'

        card_classes = 'cursor-pointer hover:shadow-lg transition-shadow rounded-xl overflow-hidden'
        if is_inactive:
            card_classes += ' opacity-75'

        with ui.card().classes(card_classes).on('click', lambda: self.modal.show(ad)):
            # Imagem
            if ad.first_image:
                img_classes = 'w-full h-28 sm:h-40 object-cover'
                if is_inactive:
                    img_classes += ' grayscale'
                ui.image(ad.first_image).classes(img_classes)
            else:
                with ui.element('div').classes('w-full h-28 sm:h-40 bg-gray-100 flex items-center justify-center'):
                    ui.icon('image', size='xl').classes('text-gray-300')

            with ui.column().classes('p-2 sm:p-3 gap-1 sm:gap-2'):
                # Título
                ui.label(ad.title).classes('font-semibold text-xs sm:text-sm line-clamp-2')

                # Preço e variação/status
                with ui.row().classes('items-center justify-between flex-wrap gap-1'):
                    with ui.row().classes('items-center gap-1'):
                        price_classes = 'text-sm sm:text-lg font-bold'
                        if is_inactive:
                            price_classes += ' text-gray-500 line-through'
                        else:
                            price_classes += ' text-green-600'
                        ui.label(f'R$ {ad.price}').classes(price_classes)

                        if not is_inactive and ad.is_cheap:
                            ui.badge('Preço Baixo').props('color=orange dense')

                    if is_inactive:
                        ui.badge('Inativo').props('color=red dense')
                    elif variation_value != 0:
                        color = 'bg-green-100 text-green-700' if variation_value < 0 else 'bg-red-100 text-red-700'
                        icon = 'trending_down' if variation_value < 0 else 'trending_up'
                        with ui.element('div').classes(f'flex items-center gap-1 px-1 sm:px-2 py-0.5 sm:py-1 rounded-full {color}'):
                            ui.icon(icon, size='xs')
                            ui.label(variation_str).classes('text-xs font-medium')
                    else:
                        with ui.element('div').classes('flex items-center gap-1 px-1 sm:px-2 py-0.5 sm:py-1 rounded-full bg-gray-100 text-gray-600'):
                            ui.icon('remove', size='xs')
                            ui.label('Estável').classes('text-xs')

                # Histórico resumido (só em desktop)
                if history and len(history) > 1:
                    prices = [h.price for h in history[-5:]]
                    if len(set(prices)) > 1:
                        ui.label(' → '.join(f'R$ {p}' for p in prices)).classes('text-xs text-gray-400 truncate hidden sm:block')

                # Localização
                ui.label(ad.location).classes('text-xs text-gray-500 truncate')
                # Datas só em desktop
                if ad.found_at_formatted:
                    ui.label(f'Encontrado: {ad.found_at_formatted}').classes('text-xs text-gray-400 hidden sm:block')
                if is_inactive and ad.deactivated_at_formatted:
                    ui.label(f'Inativo: {ad.deactivated_at_formatted}').classes('text-xs text-red-400')
