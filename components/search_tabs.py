from nicegui import ui
from typing import Callable, Optional
from services.database import get_all_searches, get_ads_count_by_search
from models import Search


class SearchTabs:
    def __init__(self, on_tab_change: Callable):
        self.on_tab_change = on_tab_change
        self.selected_search_id = None

    def create(self):
        searches = get_all_searches()
        counts = get_ads_count_by_search()

        with ui.card().classes('w-full p-4'):
            ui.label('Buscas').classes('font-semibold mb-2')

            with ui.row().classes('flex-wrap gap-2'):
                all_count = sum(counts.values())
                self._create_tab_button(None, 'Todos', all_count)

                for search_data in searches:
                    search = Search.from_dict(search_data)
                    if search.active:
                        count = counts.get(search.id, 0)
                        self._create_tab_button(search.id, search.name, count)

    def _create_tab_button(self, search_id: Optional[int], name: str, count: int):
        is_selected = self.selected_search_id == search_id

        with ui.button(on_click=lambda: self._select_tab(search_id)).props(
            f'{"" if is_selected else "outline"} color={"primary" if is_selected else "grey"}'
        ):
            ui.label(name)
            if count > 0:
                ui.badge(str(count)).props('color=red floating')

    def _select_tab(self, search_id: Optional[int]):
        self.selected_search_id = search_id
        self.on_tab_change(search_id)

    def get_selected(self) -> Optional[int]:
        return self.selected_search_id
