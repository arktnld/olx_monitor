from nicegui import ui
from models import Ad
from components.ad_card import create_ad_card


def create_ad_grid(ads: list[Ad], on_card_click):
    if not ads:
        with ui.column().classes('w-full items-center py-10'):
            ui.icon('inbox', size='xl').classes('text-gray-400')
            ui.label('Nenhum anúncio encontrado').classes('text-gray-500')
        return

    with ui.element('div').classes('grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2 sm:gap-4 w-full'):
        for ad in ads:
            create_ad_card(ad, on_card_click)
