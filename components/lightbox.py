from nicegui import ui


class Lightbox:
    def __init__(self):
        self.dialog = None
        self.images = []
        self.current_index = 0
        self.image_element = None
        self.counter_label = None

    def show(self, images: list[str], start_index: int = 0):
        if not images:
            return

        self.images = images
        self.current_index = start_index

        if self.dialog:
            self.dialog.delete()

        with ui.dialog() as self.dialog:
            self.dialog.props('maximized')

            with ui.column().classes('w-full h-full bg-black items-center justify-center'):
                # Botão fechar
                ui.button(icon='close', on_click=self._close).props(
                    'flat round color=white size=lg'
                ).classes('absolute top-4 right-4 z-50')

                # Row com setas e imagem
                with ui.row().classes('items-center justify-center gap-4 flex-grow w-full'):
                    # Seta esquerda
                    if len(self.images) > 1:
                        ui.button(icon='chevron_left', on_click=self._prev).props(
                            'flat round color=white size=xl'
                        )

                    # Imagem com fit=scale-down para não distorcer
                    self.image_element = ui.image(self.images[self.current_index]).props(
                        'fit=scale-down no-spinner'
                    ).style('max-width: 85vw; max-height: 85vh;')

                    # Seta direita
                    if len(self.images) > 1:
                        ui.button(icon='chevron_right', on_click=self._next).props(
                            'flat round color=white size=xl'
                        )

                # Contador
                if len(self.images) > 1:
                    self.counter_label = ui.label(
                        f'{self.current_index + 1} / {len(self.images)}'
                    ).classes('text-white text-lg pb-4')

        self.dialog.open()

    def _close(self):
        if self.dialog:
            self.dialog.close()

    def _update_view(self):
        if self.image_element and self.images:
            self.image_element.source = self.images[self.current_index]
            self.image_element.update()
            if self.counter_label:
                self.counter_label.text = f'{self.current_index + 1} / {len(self.images)}'

    def _prev(self):
        self.current_index = (self.current_index - 1) % len(self.images)
        self._update_view()

    def _next(self):
        self.current_index = (self.current_index + 1) % len(self.images)
        self._update_view()


lightbox = Lightbox()
