from nicegui import ui
from urllib.parse import urlparse, parse_qs, urlencode
from models import Search
from services.database import (
    get_all_searches, create_search, update_search,
    delete_search, toggle_search_active,
    get_setting, set_setting
)
from services.scheduler import reschedule_jobs
from services.validators import (
    validate_olx_url, validate_zipcode, validate_search_name,
    sanitize_cep, sanitize_text, ValidationError
)


def parse_olx_url(url: str) -> tuple[str, str, list[str]]:
    """
    Extrai base_url, query e category_patterns de uma URL do OLX.

    Exemplos:
        Com busca: https://www.olx.com.br/hobbies-e-colecoes?q=board%20games
                   -> ('https://www.olx.com.br/hobbies-e-colecoes', 'board games', ['/hobbies-e-colecoes'])

        Sem busca: https://www.olx.com.br/games/jogos-de-nintendo-switch
                   -> ('https://www.olx.com.br/games/jogos-de-nintendo-switch', '', ['/games/'])
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    query = params.get('q', [''])[0]

    # Reconstruir base_url sem o q e sem sf
    new_params = {k: v[0] for k, v in params.items() if k not in ('q', 'sf')}

    if new_params:
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(new_params)}"
    else:
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    # Extrair categoria do path para filtrar anúncios patrocinados
    # Ex: /games/jogos-de-nintendo-switch -> /games/
    path_parts = parsed.path.strip('/').split('/')
    if path_parts and path_parts[0]:
        # Usar a primeira parte do path como categoria principal
        category_pattern = f"/{path_parts[0]}/"
        categories = [category_pattern]
    else:
        categories = []

    return base, query, categories


class ConfigPage:
    def __init__(self):
        self.container = None

    def create(self):
        with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4'):
            self._create_general_settings()

            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Buscas Configuradas').classes('text-2xl font-bold')
                ui.button('+ Nova Busca', on_click=self._show_new_dialog).props('color=primary rounded')

            self.container = ui.element('div').classes('w-full')
            self.refresh()

    def _create_general_settings(self):
        with ui.card().classes('w-full p-4 rounded-xl mb-4'):
            ui.label('Configurações Gerais').classes('text-lg font-bold mb-4')

            current_cep = get_setting('delivery_zipcode', '72860175')

            with ui.row().classes('items-end gap-4'):
                cep_input = ui.input(
                    'CEP para cálculo de frete',
                    value=current_cep,
                    placeholder='00000000'
                ).props('outlined rounded mask="#####-###"').classes('w-48')

                def save_cep():
                    try:
                        cep = sanitize_cep(cep_input.value)
                        validate_zipcode(cep)
                        set_setting('delivery_zipcode', cep)
                        ui.notify('CEP salvo com sucesso!', type='positive')
                    except ValidationError as e:
                        ui.notify(str(e), type='negative')

                ui.button('Salvar', on_click=save_cep).props('color=primary rounded')

            ui.separator().classes('my-4')
            ui.label('Intervalos de Atualização').classes('font-semibold mb-2')

            current_search = get_setting('search_interval', '20')
            current_price = get_setting('price_interval', '20')
            current_status = get_setting('status_check_hour', '00:00')

            with ui.row().classes('items-end gap-4 flex-wrap'):
                search_input = ui.number(
                    'Buscar novos (min)',
                    value=int(current_search or 20),
                    min=5, max=120
                ).props('outlined rounded').classes('w-40')

                price_input = ui.number(
                    'Checar preços (min)',
                    value=int(current_price or 20),
                    min=5, max=120
                ).props('outlined rounded').classes('w-40')

                status_input = ui.input(
                    'Checar status (hora)',
                    value=current_status or '00:00',
                    placeholder='HH:MM'
                ).props('outlined rounded mask="##:##"').classes('w-32')

                def save_intervals():
                    search_val = int(search_input.value) if search_input.value else 20
                    price_val = int(price_input.value) if price_input.value else 20
                    status_val = status_input.value or '00:00'

                    if search_val < 5 or price_val < 5:
                        ui.notify('Intervalo mínimo é 5 minutos', type='negative')
                        return

                    set_setting('search_interval', str(search_val))
                    set_setting('price_interval', str(price_val))
                    set_setting('status_check_hour', status_val)
                    reschedule_jobs()
                    ui.notify('Intervalos salvos!', type='positive')

                ui.button('Salvar', on_click=save_intervals).props('color=primary rounded')

    def refresh(self):
        if self.container:
            self.container.clear()

            searches = get_all_searches()

            if not searches:
                with self.container:
                    with ui.column().classes('w-full items-center py-10'):
                        ui.icon('search_off', size='xl').classes('text-gray-400')
                        ui.label('Nenhuma busca configurada').classes('text-gray-500')
                        ui.label('Cole uma URL de busca do OLX para começar').classes('text-sm text-gray-400')
                return

            with self.container:
                with ui.column().classes('w-full gap-4'):
                    for search_data in searches:
                        search = Search.from_dict(search_data)
                        self._create_search_card(search)

    def _create_search_card(self, search: Search):
        with ui.card().classes('w-full p-4 rounded-xl'):
            with ui.row().classes('w-full justify-between items-start'):
                with ui.column().classes('flex-grow gap-2'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label(search.name).classes('text-lg font-semibold')
                        if not search.active:
                            ui.badge('Inativo').props('color=grey')

                    # Mostrar URL base
                    ui.label(search.base_url).classes('text-xs text-gray-400 break-all line-clamp-1')

                    # Termos de busca
                    ui.label(f'Buscando: {", ".join(search.queries)}').classes('text-sm text-blue-600')

                    if search.cheap_threshold:
                        ui.label(f'Notificar se preço < R$ {search.cheap_threshold:.0f}').classes('text-xs text-green-600')

                    if search.exclude_keywords:
                        ui.label(f'Excluindo: {", ".join(search.exclude_keywords)}').classes('text-xs text-gray-400')

                with ui.row().classes('gap-2'):
                    ui.switch(
                        value=search.active,
                        on_change=lambda e, sid=search.id: self._toggle_active(sid)
                    ).props('color=green')
                    ui.button(icon='edit', on_click=lambda s=search: self._show_edit_dialog(s)).props('flat round')
                    ui.button(icon='delete', on_click=lambda sid=search.id: self._confirm_delete(sid)).props('flat round color=negative')

    def _toggle_active(self, search_id: int):
        toggle_search_active(search_id)
        self.refresh()

    def _confirm_delete(self, search_id: int):
        with ui.dialog() as dialog, ui.card().classes('rounded-xl'):
            ui.label('Tem certeza que deseja excluir esta busca?').classes('text-lg')
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Excluir', on_click=lambda: self._delete_and_close(search_id, dialog)).props('color=negative')
        dialog.open()

    def _delete_and_close(self, search_id: int, dialog):
        delete_search(search_id)
        dialog.close()
        self.refresh()

    def _show_new_dialog(self):
        self._show_edit_dialog(Search())

    def _show_edit_dialog(self, search: Search):
        is_new = search.id is None

        # Reconstruir URL original se editando
        original_url = ''
        if not is_new and search.base_url:
            if search.queries:
                original_url = search.base_url + '?q=' + search.queries[0]
            else:
                original_url = search.base_url

        with ui.dialog() as dialog, ui.card().classes('w-full max-w-lg rounded-xl'):
            ui.label('Nova Busca' if is_new else 'Editar Busca').classes('text-xl font-bold mb-4')

            name_input = ui.input(
                'Nome da busca',
                value=search.name,
                placeholder='Ex: Board Games Brasil'
            ).props('outlined rounded').classes('w-full')

            ui.label('URL do OLX').classes('font-semibold mt-4 mb-2')

            url_input = ui.input(
                'Cole a URL de busca do OLX',
                value=original_url,
                placeholder='https://www.olx.com.br/games?q=nintendo'
            ).props('outlined rounded').classes('w-full')

            with ui.card().classes('w-full bg-blue-50 p-3 rounded-xl'):
                with ui.row().classes('items-start gap-2'):
                    ui.icon('info', size='xs').classes('text-blue-600 mt-1')
                    with ui.column().classes('gap-1'):
                        ui.label('Como usar:').classes('text-xs font-semibold text-blue-800')
                        ui.label('1. Vá no OLX e faça a busca que deseja').classes('text-xs text-blue-700')
                        ui.label('2. Copie a URL da barra de endereço').classes('text-xs text-blue-700')
                        ui.label('3. Cole aqui').classes('text-xs text-blue-700')

            ui.label('Palavras a excluir (opcional)').classes('font-semibold mt-4 mb-2')

            exclude_input = ui.textarea(
                'Uma por linha',
                value='\n'.join(search.exclude_keywords) if search.exclude_keywords else '',
                placeholder='danificado\nquebrado\ncom defeito'
            ).props('outlined rounded').classes('w-full')

            ui.label('Notificação de preço baixo (opcional)').classes('font-semibold mt-4 mb-2')

            threshold_input = ui.number(
                label='Notificar se preço menor que',
                value=search.cheap_threshold,
                placeholder='Ex: 150'
            ).props('outlined rounded prefix="R$"').classes('w-48')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button(
                    'Criar' if is_new else 'Salvar',
                    on_click=lambda: self._save_search(
                        search.id,
                        name_input.value,
                        url_input.value,
                        exclude_input.value,
                        threshold_input.value,
                        search.active,
                        dialog
                    )
                ).props('color=primary rounded')

        dialog.open()

    def _save_search(self, search_id, name, url, exclude_str, cheap_threshold, active, dialog):
        # Sanitize and validate inputs
        name = sanitize_text(name, max_length=100)
        url = sanitize_text(url)
        exclude = [sanitize_text(e, max_length=100) for e in exclude_str.split('\n') if e.strip()]

        try:
            validate_search_name(name)
        except ValidationError as e:
            ui.notify(str(e), type='negative')
            return

        try:
            validate_olx_url(url)
        except ValidationError as e:
            ui.notify(str(e), type='negative')
            return

        # Extrair base_url, query e categoria da URL
        base_url, query, categories = parse_olx_url(url)

        # Query pode ser vazio (monitorar categoria inteira)
        queries = [query] if query else []

        # Threshold pode ser None se vazio
        threshold = float(cheap_threshold) if cheap_threshold else None

        if search_id is None:
            create_search(
                name=name,
                base_url=base_url,
                queries=queries,
                categories=categories,
                exclude_keywords=exclude,
                cheap_threshold=threshold
            )
        else:
            update_search(
                search_id=search_id,
                name=name,
                base_url=base_url,
                queries=queries,
                categories=categories,
                exclude_keywords=exclude,
                active=active,
                cheap_threshold=threshold
            )

        ui.notify('Busca salva com sucesso', type='positive')
        dialog.close()
        self.refresh()
