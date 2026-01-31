from nicegui import ui
from models import Ad, get_price_color


def create_ad_card(ad: Ad, on_click):
    is_inactive = ad.status == 'inactive'
    card_classes = 'cursor-pointer hover:shadow-xl transition-all w-full rounded-xl overflow-hidden'
    if is_inactive:
        card_classes += ' opacity-60'

    with ui.card().classes(card_classes).on('click', lambda: on_click(ad)):
        if ad.first_image:
            img_classes = 'w-full h-28 sm:h-40 object-cover'
            if is_inactive:
                img_classes += ' grayscale'
            ui.image(ad.first_image).classes(img_classes)
        else:
            with ui.element('div').classes('w-full h-28 sm:h-40 bg-gray-100 flex items-center justify-center'):
                ui.icon('image', size='xl').classes('text-gray-300')

        with ui.column().classes('p-2 sm:p-3 gap-1'):
            with ui.row().classes('items-center gap-1 sm:gap-2 flex-wrap'):
                price_classes = 'text-sm sm:text-base font-semibold'
                if is_inactive:
                    price_classes += ' text-gray-500 line-through'
                else:
                    price_classes += f' {get_price_color(ad.price)}'
                ui.label(f'R$ {ad.price}').classes(price_classes)

                if is_inactive:
                    ui.badge('Inativo').props('color=red dense')
                else:
                    if ad.olx_delivery:
                        ui.label('📦')

            ui.label(ad.title).classes('text-xs sm:text-sm line-clamp-2')
            ui.label(f'{ad.municipality}, {ad.state.replace("#", "")}').classes('text-xs text-gray-500 truncate')
            # Data de encontrado só aparece em telas maiores
            if ad.found_at_formatted:
                ui.label(f'Encontrado: {ad.found_at_formatted}').classes('text-xs text-gray-400 hidden sm:block')
