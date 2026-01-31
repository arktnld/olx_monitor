from nicegui import ui
from typing import Callable
from services.database import get_distinct_states


class Filters:
    def __init__(self, on_filter_change: Callable):
        self.on_filter_change = on_filter_change
        self.status = "all"
        self.ad_status = None
        self.min_price = None
        self.max_price = None
        self.state = None
        self.days = None
        self.search_text = None
        self.sort_by = None

    def create(self):
        states = get_distinct_states()

        # Campo de busca por texto (fora do expansion para ficar sempre visível)
        with ui.row().classes('w-full gap-2 items-center'):
            self.search_input = ui.input(
                placeholder='Buscar por título ou descrição...',
            ).props('dense outlined rounded clearable').classes('flex-grow')
            self.search_input.on('keydown.enter', lambda: self._set_search_text(self.search_input.value))
            ui.button(icon='search', on_click=lambda: self._set_search_text(self.search_input.value)).props('flat round dense')

        with ui.expansion('Filtros', icon='filter_list').classes('w-full rounded-xl overflow-hidden').props('dense header-class="text-weight-medium"'):
            with ui.row().classes('w-full flex-wrap gap-3 items-center py-2'):
                self.sort_select = ui.select(
                    label='Ordenar',
                    options={
                        None: 'Mais recentes',
                        'price_asc': 'Menor preço',
                        'price_desc': 'Maior preço'
                    },
                    value=None,
                    on_change=lambda e: self._set_sort_by(e.value)
                ).props('dense outlined rounded').classes('min-w-[130px]')

                self.status_select = ui.select(
                    label='Status',
                    options={
                        'all': 'Todos',
                        'new': 'Novos',
                        'seen': 'Vistos',
                        'watching': 'Acompanhando'
                    },
                    value='all',
                    on_change=lambda e: self._set_status(e.value)
                ).props('dense outlined rounded').classes('min-w-[120px]')

                self.ad_status_select = ui.select(
                    label='Anúncio',
                    options={
                        None: 'Todos',
                        'active': 'Ativos',
                        'inactive': 'Inativos'
                    },
                    value=None,
                    on_change=lambda e: self._set_ad_status(e.value)
                ).props('dense outlined rounded').classes('min-w-[100px]')

                self.days_select = ui.select(
                    label='Período',
                    options={
                        None: 'Todos',
                        1: '24h',
                        7: '7 dias',
                        30: '30 dias'
                    },
                    value=None,
                    on_change=lambda e: self._set_days(e.value)
                ).props('dense outlined rounded').classes('min-w-[100px]')

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

                # Faixa de preço por último
                self.min_input = ui.number(
                    label='Preço min',
                    on_change=lambda e: self._set_min_price(e.value)
                ).props('dense outlined rounded prefix="R$"').classes('w-28')

                self.max_input = ui.number(
                    label='Preço max',
                    on_change=lambda e: self._set_max_price(e.value)
                ).props('dense outlined rounded prefix="R$"').classes('w-28')

                ui.button(icon='clear', on_click=self._clear_filters).props('flat round dense').tooltip('Limpar filtros')

    def _set_status(self, value):
        self.status = value
        self._trigger_change()

    def _set_ad_status(self, value):
        self.ad_status = value
        self._trigger_change()

    def _set_min_price(self, value):
        self.min_price = value if value else None
        self._trigger_change()

    def _set_max_price(self, value):
        self.max_price = value if value else None
        self._trigger_change()

    def _set_days(self, value):
        self.days = value
        self._trigger_change()

    def _set_state(self, value):
        self.state = value
        self._trigger_change()

    def _set_sort_by(self, value):
        self.sort_by = value
        self._trigger_change()

    def _set_search_text(self, value):
        self.search_text = value.strip() if value else None
        self._trigger_change()

    def _clear_filters(self):
        self.status = "all"
        self.ad_status = None
        self.min_price = None
        self.max_price = None
        self.state = None
        self.days = None
        self.search_text = None
        self.sort_by = None
        self.sort_select.set_value(None)
        self.status_select.set_value('all')
        self.ad_status_select.set_value(None)
        self.min_input.set_value(None)
        self.max_input.set_value(None)
        self.days_select.set_value(None)
        self.state_select.set_value(None)
        self.search_input.set_value('')
        self._trigger_change()

    def _trigger_change(self):
        self.on_filter_change(
            status=self.status,
            ad_status=self.ad_status,
            min_price=self.min_price,
            max_price=self.max_price,
            state=self.state,
            days=self.days,
            search_text=self.search_text,
            sort_by=self.sort_by
        )

    def get_filters(self):
        return {
            'status': self.status,
            'ad_status': self.ad_status,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'state': self.state,
            'days': self.days,
            'search_text': self.search_text,
            'sort_by': self.sort_by
        }
