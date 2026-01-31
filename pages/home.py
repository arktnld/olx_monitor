from nicegui import ui
from models import Ad
from services.database import get_ads, get_all_searches, get_ads_count_by_search, get_ads_count
from services.scheduler import run_search_now, get_task_status
from components.ad_grid import create_ad_grid
from components.ad_modal import AdModal
from components.filters import Filters

PAGE_SIZE = 24


class HomePage:
    def __init__(self):
        self.ads_container = None
        self.modal = AdModal(on_update=self.refresh)
        self.filters = Filters(on_filter_change=self._on_filter_change)
        self.selected_search_id = None
        self.current_filters = {}
        self.tab_buttons = {}
        self.update_button = None
        self.update_timer = None
        self.current_offset = 0
        self.total_count = 0
        self.loaded_ads = []
        self.load_more_container = None

    def create(self):
        with ui.column().classes('w-full max-w-7xl mx-auto p-4 gap-4'):
            self.filters.create_search_bar()
            self._create_search_tabs()
            self.filters.create()
            self._create_results_header()
            self.ads_container = ui.element('div').classes('w-full')
            self.load_more_container = ui.element('div').classes('w-full flex justify-center py-4')
            self.refresh()

    def _on_update_click(self):
        status = get_task_status('search')
        if status['running']:
            ui.notify('Busca já está em execução', type='warning')
            return

        # Iniciar busca
        started = run_search_now()
        if not started:
            ui.notify('Não foi possível iniciar a busca', type='negative')
            return

        # Atualizar UI - mostrar loading no botão
        self.update_button.disable()
        self.update_button.props('loading')
        self.update_button.text = 'Buscando...'

        # Criar timer para verificar progresso
        self.update_timer = ui.timer(1.0, self._check_update_progress)

    def _check_update_progress(self):
        status = get_task_status('search')

        if not status['running']:
            # Busca terminou
            if self.update_timer:
                self.update_timer.cancel()
                self.update_timer = None

            self.update_button.props(remove='loading')
            self.update_button.enable()

            result = status['result']
            if result and result.get('success'):
                total = result.get('total_new', 0)
                if total > 0:
                    self.update_button.text = f'+{total} novos!'
                    ui.notify(f'{total} novos anúncios encontrados!', type='positive')
                else:
                    self.update_button.text = 'Atualizar'
                    ui.notify('Nenhum anúncio novo encontrado', type='info')

                # Atualizar a lista
                self.refresh()
                self._refresh_tabs()
            elif result:
                self.update_button.text = 'Erro!'
                ui.notify('Erro ao buscar anúncios', type='negative')

    def _refresh_tabs(self):
        """Recarrega as tabs com as novas contagens"""
        # Recarregar a página inteira para atualizar tabs
        ui.navigate.reload()

    def _create_search_tabs(self):
        searches = get_all_searches()
        counts = get_ads_count_by_search()
        all_count = sum(counts.values())

        with ui.expansion('Buscas', icon='search').classes('w-full rounded-xl overflow-hidden').props('dense header-class="text-weight-medium"'):
            with ui.row().classes('w-full flex-wrap gap-2 items-center py-2'):
                # Botão de atualizar
                self._create_update_button()

                # Separador visual
                ui.element('div').classes('w-px h-6 bg-gray-300 mx-1')

                # Tabs de busca
                self._create_tab_button(None, 'Todos', all_count)

                for search_data in searches:
                    if search_data.get('active'):
                        search_id = search_data['id']
                        name = search_data['name']
                        count = counts.get(search_id, 0)
                        self._create_tab_button(search_id, name, count)

    def _create_update_button(self):
        self.update_button = ui.button(
            'Atualizar',
            icon='refresh',
            on_click=self._on_update_click
        ).props('outline color=primary rounded')

    def _create_tab_button(self, search_id, name: str, count: int):
        is_selected = self.selected_search_id == search_id

        btn = ui.button(name, on_click=lambda sid=search_id: self._select_tab(sid))
        btn.props(f'rounded {"color=primary" if is_selected else "outline color=grey"}')

        if count > 0:
            with btn:
                ui.badge(str(count)).props('color=red floating')

        self.tab_buttons[search_id] = btn

    def _select_tab(self, search_id):
        self.selected_search_id = search_id
        self.current_offset = 0
        self.loaded_ads = []
        self._update_tab_styles()
        self.refresh()

    def _update_tab_styles(self):
        for sid, btn in self.tab_buttons.items():
            if sid == self.selected_search_id:
                btn.props(remove='outline color=grey', add='color=primary rounded')
            else:
                btn.props(remove='color=primary', add='outline color=grey rounded')

    def _create_results_header(self):
        self.results_label = ui.label('').classes('text-sm text-gray-500')

    def _on_filter_change(self, **filters):
        self.current_filters = filters
        self.current_offset = 0
        self.loaded_ads = []
        self.refresh()

    def refresh(self):
        if self.ads_container:
            self.ads_container.clear()

            # Contar total (só anúncios ativos por padrão)
            self.total_count = get_ads_count(
                search_id=self.selected_search_id,
                status=self.current_filters.get('status', 'all'),
                min_price=self.current_filters.get('min_price'),
                max_price=self.current_filters.get('max_price'),
                state=self.current_filters.get('state'),
                days=self.current_filters.get('days'),
                ad_status=self.current_filters.get('ad_status', 'active'),
                search_text=self.current_filters.get('search_text')
            )

            ads_data = get_ads(
                search_id=self.selected_search_id,
                status=self.current_filters.get('status', 'all'),
                min_price=self.current_filters.get('min_price'),
                max_price=self.current_filters.get('max_price'),
                state=self.current_filters.get('state'),
                days=self.current_filters.get('days'),
                ad_status=self.current_filters.get('ad_status', 'active'),
                search_text=self.current_filters.get('search_text'),
                sort_by=self.current_filters.get('sort_by'),
                limit=PAGE_SIZE,
                offset=0
            )

            self.loaded_ads = [Ad.from_dict(ad) for ad in ads_data]
            self.current_offset = PAGE_SIZE

            self.results_label.set_text(f'{len(self.loaded_ads)} de {self.total_count} anúncios')

            with self.ads_container:
                create_ad_grid(self.loaded_ads, self._on_card_click)

            self._update_load_more_button()

    def _load_more(self):
        ads_data = get_ads(
            search_id=self.selected_search_id,
            status=self.current_filters.get('status', 'all'),
            min_price=self.current_filters.get('min_price'),
            max_price=self.current_filters.get('max_price'),
            state=self.current_filters.get('state'),
            days=self.current_filters.get('days'),
            ad_status=self.current_filters.get('ad_status', 'active'),
            search_text=self.current_filters.get('search_text'),
            sort_by=self.current_filters.get('sort_by'),
            limit=PAGE_SIZE,
            offset=self.current_offset
        )

        new_ads = [Ad.from_dict(ad) for ad in ads_data]
        self.loaded_ads.extend(new_ads)
        self.current_offset += PAGE_SIZE

        # Atualizar UI
        self.ads_container.clear()
        with self.ads_container:
            create_ad_grid(self.loaded_ads, self._on_card_click)

        self.results_label.set_text(f'{len(self.loaded_ads)} de {self.total_count} anúncios')
        self._update_load_more_button()

    def _update_load_more_button(self):
        if self.load_more_container:
            self.load_more_container.clear()
            remaining = self.total_count - len(self.loaded_ads)
            if remaining > 0:
                with self.load_more_container:
                    ui.button(
                        f'Carregar mais ({remaining} restantes)',
                        on_click=self._load_more
                    ).props('color=primary outline rounded')

    def _on_card_click(self, ad: Ad):
        self.modal.show(ad)
