import requests
from pathlib import Path

# Pasta para armazenar imagens locais
IMAGES_DIR = Path(__file__).parent.parent / "data" / "images"


def ensure_images_dir():
    """Cria a pasta de imagens se não existir"""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def get_local_image_path(ad_id: int, index: int) -> Path:
    """Retorna o path local para uma imagem"""
    return IMAGES_DIR / f"{ad_id}_{index}.jpg"


def download_ad_images(ad_id: int, image_urls: list[str]) -> list[str]:
    """
    Baixa as imagens de um anúncio para armazenamento local.
    Retorna lista de paths locais das imagens baixadas.
    """
    ensure_images_dir()
    local_paths = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }

    for i, url in enumerate(image_urls):
        try:
            local_path = get_local_image_path(ad_id, i)

            # Pula se já existe
            if local_path.exists():
                local_paths.append(str(local_path))
                continue

            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                local_paths.append(str(local_path))
                print(f"Imagem salva: {local_path.name}")
            else:
                print(f"Erro ao baixar imagem {url}: {response.status_code}")

        except Exception as e:
            print(f"Erro ao baixar imagem {url}: {e}")

    return local_paths


def get_local_images(ad_id: int) -> list[str]:
    """Retorna lista de URLs das imagens locais de um anúncio"""
    ensure_images_dir()
    local_images = []

    i = 0
    while True:
        path = get_local_image_path(ad_id, i)
        if path.exists():
            # Retorna URL para o servidor servir
            local_images.append(f"/images/{ad_id}_{i}.jpg")
            i += 1
        else:
            break

    return local_images


def delete_ad_images(ad_id: int):
    """Remove todas as imagens locais de um anúncio"""
    i = 0
    while True:
        path = get_local_image_path(ad_id, i)
        if path.exists():
            path.unlink()
            i += 1
        else:
            break


def has_local_images(ad_id: int) -> bool:
    """Verifica se o anúncio tem imagens salvas localmente"""
    return get_local_image_path(ad_id, 0).exists()


def download_watching_ads_images():
    """Baixa imagens de todos os anúncios acompanhados que ainda não têm imagens locais"""
    from services.database import get_watching_ads
    import json

    ads = get_watching_ads()
    downloaded = 0

    for ad_data in ads:
        ad_id = ad_data['id']

        # Pula se já tem imagens
        if has_local_images(ad_id):
            continue

        images_raw = ad_data.get('images', '[]')
        if isinstance(images_raw, str):
            images = json.loads(images_raw) if images_raw else []
        else:
            images = images_raw or []

        if images:
            download_ad_images(ad_id, images)
            downloaded += 1

    return downloaded
