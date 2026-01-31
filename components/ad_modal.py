from nicegui import ui, background_tasks
from models import Ad, PriceHistory, calculate_price_variation, get_price_color
from components.lightbox import lightbox
from services.database import toggle_ad_watching, mark_ad_seen, get_price_history, update_ad_status
from services.scraper import OlxScraper
from services.delivery import get_delivery_quote_async, DeliveryQuote
import re


class AdModal:
    def __init__(self, on_update=None):
        self.dialog = None
        self.on_update = on_update
        self.current_ad = None
        self.current_image_index = 0
        self.dots = []
        self.scraper = OlxScraper()
        self.watch_btn = None
        self.status_changed = False
        # Containers para atualização assíncrona
        self.status_container = None
        self.delivery_container = None
        self.inactive_banner = None

    def _extract_list_id(self, url: str) -> int | None:
        """Extrai o list_id da URL do anúncio"""
        match = re.search(r'-(\d+)$', url)
        return int(match.group(1)) if match else None

    async def _check_status_async(self, ad: Ad):
        """Verifica status do anúncio de forma assíncrona"""
        try:
            new_status = await background_tasks.run_cpu_bound(
                self.scraper.check_ad_status, ad.url
            )

            if new_status is None:
                # Limpar spinner mesmo se falhou
                if self.status_container:
                    self.status_container.clear()
                return

            if new_status != ad.status:
                update_ad_status(ad.id, new_status)
                ad.status = new_status
                self.status_changed = True

            # Atualizar UI baseado no status
            if self.status_container:
                self.status_container.clear()
                if new_status == 'inactive':
                    with self.status_container:
                        ui.badge('INATIVO').props('color=red')

                    if self.inactive_banner:
                        self.inactive_banner.clear()
                        with self.inactive_banner:
                            with ui.card().classes('w-full bg-red-50 rounded-xl'):
                                with ui.row().classes('p-3 items-center gap-2'):
                                    ui.icon('warning', size='sm').classes('text-red-600')
                                    ui.label('Este anúncio não está mais disponível no OLX').classes('text-red-700 text-sm')

                    # Esconder botão de acompanhar
                    if self.watch_btn:
                        self.watch_btn.set_visibility(False)

        except Exception:
            # Limpar spinner em caso de erro
            if self.status_container:
                self.status_container.clear()

    async def _load_delivery_async(self, ad: Ad):
        """Carrega informações de frete de forma assíncrona"""
        if not ad.olx_delivery:
            return

        list_id = self._extract_list_id(ad.url)
        if not list_id:
            return

        try:
            quote = await get_delivery_quote_async(list_id)

            if self.delivery_container:
                self.delivery_container.clear()
                if quote:
                    with self.delivery_container:
                        self._render_delivery_info(quote)
                # Se não tem quote, simplesmente limpa o loading

        except Exception:
            # Em caso de erro, limpa o loading
            if self.delivery_container:
                self.delivery_container.clear()

    def _render_delivery_info(self, quote: DeliveryQuote):
        """Renderiza informações de frete"""
        with ui.card().classes('w-full bg-purple-50 rounded-xl'):
            with ui.column().classes('p-3 gap-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('local_shipping', size='sm').classes('text-purple-600')
                    ui.label('Entrega OLX').classes('font-semibold text-purple-800')

                with ui.row().classes('gap-4 flex-wrap'):
                    if quote.standard:
                        with ui.column().classes('gap-0'):
                            ui.label('Padrão').classes('text-xs text-gray-500')
                            if quote.standard.is_free:
                                ui.label('Frete Grátis').classes('text-sm font-bold text-green-600')
                            else:
                                ui.label(quote.standard.price_label).classes('text-sm font-bold')
                            ui.label(f'{quote.standard.days} dias').classes('text-xs text-gray-400')

                    if quote.express:
                        with ui.column().classes('gap-0'):
                            ui.label('Expressa').classes('text-xs text-gray-500')
                            if quote.express.is_free:
                                ui.label('Frete Grátis').classes('text-sm font-bold text-green-600')
                            else:
                                ui.label(quote.express.price_label).classes('text-sm font-bold')
                            ui.label(f'{quote.express.days} dias').classes('text-xs text-gray-400')

    def _close_dialog(self):
        if self.dialog:
            self.dialog.close()
        if self.status_changed and self.on_update:
            self.on_update()
        self.status_changed = False

    def show(self, ad: Ad):
        self.current_ad = ad
        self.current_image_index = 0
        self.dots = []
        self.status_changed = False

        # Usar status atual (será atualizado assincronamente)
        is_inactive = ad.status == 'inactive'

        mark_ad_seen(ad.id)

        if self.dialog:
            try:
                self.dialog.delete()
            except ValueError:
                pass
            self.dialog = None

        with ui.dialog().props('full-width') as self.dialog:
            with ui.card().classes('w-full max-w-4xl mx-auto max-h-[90vh] overflow-y-auto rounded-2xl'):
                with ui.row().classes('w-full justify-between items-center p-4 pb-0'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label('Detalhes do Anúncio').classes('text-lg font-semibold')
                        # Container para status (atualizado assincronamente)
                        self.status_container = ui.element('span').classes('inline-flex items-center gap-1')
                        with self.status_container:
                            if is_inactive:
                                ui.badge('INATIVO').props('color=red')
                            elif ad.status == 'active':
                                ui.spinner('dots', size='xs').classes('text-gray-400')

                    ui.button(icon='close', on_click=self._close_dialog).props('flat round dense')

                # Banner de inativo (container para atualização assíncrona)
                self.inactive_banner = ui.element('div').classes('w-full px-4')
                if is_inactive:
                    with self.inactive_banner:
                        with ui.card().classes('w-full bg-red-50 rounded-xl mt-2'):
                            with ui.row().classes('p-3 items-center gap-2'):
                                ui.icon('warning', size='sm').classes('text-red-600')
                                ui.label('Este anúncio não está mais disponível no OLX').classes('text-red-700 text-sm')

                # Usar imagens locais se disponíveis
                images = ad.get_images()
                if images:
                    with ui.column().classes('w-full px-4 pt-2'):
                        img_classes = 'w-full rounded-xl cursor-pointer'
                        if is_inactive:
                            img_classes += ' grayscale opacity-75'
                        self.main_image = ui.image(images[0]).props(
                            'fit=contain no-spinner'
                        ).classes(img_classes).style('max-height: 450px;')
                        self.main_image.on('click', self._open_lightbox)

                        if len(images) > 1:
                            with ui.row().classes('w-full justify-center items-center gap-2 py-2'):
                                ui.button(icon='chevron_left', on_click=self._prev_image).props('flat dense')
                                for i in range(len(images)):
                                    dot = ui.button().props('flat round dense').classes(
                                        f'w-3 h-3 min-w-0 min-h-0 p-0 {"bg-blue-500" if i == 0 else "bg-gray-300"}'
                                    )
                                    dot.on('click', lambda e, idx=i: self._go_to_image(idx))
                                    self.dots.append(dot)
                                ui.button(icon='chevron_right', on_click=self._next_image).props('flat dense')

                with ui.column().classes('w-full p-4 gap-3'):
                    with ui.row().classes('items-center gap-2'):
                        price_classes = 'text-2xl font-bold'
                        if is_inactive:
                            price_classes += ' text-gray-500 line-through'
                        else:
                            price_classes += f' {get_price_color(ad.price)}'
                        ui.label(f'R$ {ad.price}').classes(price_classes)

                        if not is_inactive:
                            if ad.olx_pay:
                                ui.badge('OLXPay').props('color=green')
                            if ad.olx_delivery:
                                ui.badge('📦 Entrega OLX').props('color=blue')

                    # Container para informações de frete (carregado assincronamente)
                    if ad.olx_delivery and not is_inactive:
                        self.delivery_container = ui.element('div').classes('w-full')
                        with self.delivery_container:
                            with ui.row().classes('items-center gap-2 text-gray-400'):
                                ui.spinner('dots', size='xs')
                                ui.label('Calculando frete...').classes('text-sm')

                    if ad.watching:
                        history_data = get_price_history(ad.id)
                        history = [PriceHistory.from_dict(h) for h in history_data]
                        variation_value, variation_str = calculate_price_variation(history)

                        with ui.card().classes('w-full bg-blue-50 rounded-xl'):
                            with ui.column().classes('p-3 gap-2'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('trending_up', size='sm').classes('text-blue-600')
                                    ui.label('Acompanhamento').classes('font-semibold text-blue-800')

                                with ui.row().classes('gap-6'):
                                    with ui.column().classes('gap-0'):
                                        ui.label('Variação').classes('text-xs text-gray-500')
                                        color = 'text-green-600' if variation_value < 0 else ('text-red-600' if variation_value > 0 else 'text-gray-600')
                                        ui.label(variation_str).classes(f'text-lg font-bold {color}')

                                if history:
                                    with ui.column().classes('gap-1'):
                                        prices = [h.price for h in history[-5:]]
                                        # Só mostra histórico se houve variação real
                                        if len(set(prices)) > 1:
                                            ui.label('Histórico:').classes('text-xs text-gray-500')
                                            ui.label(' → '.join(f'R$ {p}' for p in prices)).classes('text-sm')

                                        last_check = history[-1].checked_at if history else None
                                        if last_check:
                                            ui.label(f'Última verificação: {last_check}').classes('text-xs text-gray-400')

                    ui.separator().classes('w-full')

                    ui.label(ad.title).classes('text-lg font-semibold')
                    if ad.condition:
                        ui.label(ad.condition).classes('text-sm text-gray-600')

                    with ui.column().classes('gap-1'):
                        if ad.location:
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('location_on', size='sm').classes('text-gray-500')
                                ui.label(ad.location).classes('text-sm')

                        if ad.formatted_date:
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('schedule', size='sm').classes('text-gray-500')
                                ui.label(f'Publicado: {ad.formatted_date}').classes('text-sm')

                        if ad.found_at_formatted:
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('search', size='sm').classes('text-blue-500')
                                ui.label(f'Encontrado: {ad.found_at_formatted}').classes('text-sm text-blue-600')

                        if ad.deactivated_at_formatted:
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('cancel', size='sm').classes('text-red-500')
                                ui.label(f'Inativo desde: {ad.deactivated_at_formatted}').classes('text-sm text-red-600')

                        if ad.seller:
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('person', size='sm').classes('text-gray-500')
                                ui.label(f'Vendedor: {ad.seller}').classes('text-sm')

                    if ad.description:
                        ui.separator().classes('w-full')
                        ui.label('Descrição:').classes('font-semibold')
                        ui.label(ad.description).classes('text-sm text-gray-700 whitespace-pre-wrap')

                    if ad.category_path:
                        ui.separator().classes('w-full')
                        ui.label(f'Categoria: {ad.category_path}').classes('text-xs text-gray-500')

                    ui.separator().classes('w-full')

                    with ui.row().classes('w-full gap-3'):
                        if not is_inactive:
                            watch_icon = 'visibility_off' if ad.watching else 'visibility'
                            self.watch_btn = ui.button(
                                'Parar' if ad.watching else 'Acompanhar',
                                icon=watch_icon,
                                on_click=lambda: self._toggle_watching()
                            ).classes('flex-1')
                            self.watch_btn.props(f'rounded color={"orange" if ad.watching else "primary"} outline')

                        ui.button(
                            'Abrir no OLX',
                            icon='open_in_new',
                            on_click=lambda: ui.navigate.to(ad.url, new_tab=True)
                        ).props('rounded color=positive').classes('flex-1')

        self.dialog.open()

        # Iniciar carregamento assíncrono após abrir o modal
        if not is_inactive:
            background_tasks.create(self._check_status_async(ad))
        if ad.olx_delivery and not is_inactive:
            background_tasks.create(self._load_delivery_async(ad))

    def _open_lightbox(self):
        if self.current_ad:
            images = self.current_ad.get_images()
            if images:
                lightbox.show(images, self.current_image_index)

    def _update_image_view(self):
        if self.current_ad:
            images = self.current_ad.get_images()
            if images:
                self.main_image.set_source(images[self.current_image_index])
            for i, dot in enumerate(self.dots):
                dot.classes(remove='bg-gray-300 bg-blue-500')
                if i == self.current_image_index:
                    dot.classes(add='bg-blue-500')
                else:
                    dot.classes(add='bg-gray-300')

    def _prev_image(self):
        if self.current_ad:
            images = self.current_ad.get_images()
            if images:
                self.current_image_index = (self.current_image_index - 1) % len(images)
                self._update_image_view()

    def _next_image(self):
        if self.current_ad:
            images = self.current_ad.get_images()
            if images:
                self.current_image_index = (self.current_image_index + 1) % len(images)
                self._update_image_view()

    def _go_to_image(self, index: int):
        if self.current_ad:
            images = self.current_ad.get_images()
            if images:
                self.current_image_index = index
                self._update_image_view()

    def _toggle_watching(self):
        if self.current_ad and self.watch_btn:
            toggle_ad_watching(self.current_ad.id)
            self.current_ad.watching = not self.current_ad.watching
            # Atualizar botão
            if self.current_ad.watching:
                self.watch_btn.props(remove='color=primary', add='color=orange')
                self.watch_btn.text = 'Parar'
                self.watch_btn._props['icon'] = 'visibility_off'
            else:
                self.watch_btn.props(remove='color=orange', add='color=primary')
                self.watch_btn.text = 'Acompanhar'
                self.watch_btn._props['icon'] = 'visibility'
            self.watch_btn.update()
