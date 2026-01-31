# Estados do OLX (subdomínios)
STATES = {
    '': 'Brasil (todo)',
    'ac': 'Acre',
    'al': 'Alagoas',
    'ap': 'Amapá',
    'am': 'Amazonas',
    'ba': 'Bahia',
    'ce': 'Ceará',
    'df': 'Distrito Federal',
    'es': 'Espírito Santo',
    'go': 'Goiás',
    'ma': 'Maranhão',
    'mt': 'Mato Grosso',
    'ms': 'Mato Grosso do Sul',
    'mg': 'Minas Gerais',
    'pa': 'Pará',
    'pb': 'Paraíba',
    'pr': 'Paraná',
    'pe': 'Pernambuco',
    'pi': 'Piauí',
    'rj': 'Rio de Janeiro',
    'rn': 'Rio Grande do Norte',
    'rs': 'Rio Grande do Sul',
    'ro': 'Rondônia',
    'rr': 'Roraima',
    'sc': 'Santa Catarina',
    'sp': 'São Paulo',
    'se': 'Sergipe',
    'to': 'Tocantins',
}

# Regiões comuns por estado
REGIONS = {
    'pe': {
        '': 'Todo estado',
        'grande-recife': 'Grande Recife',
        'zona-da-mata': 'Zona da Mata',
        'agreste': 'Agreste',
        'sertao': 'Sertão',
    },
    'sp': {
        '': 'Todo estado',
        'sao-paulo-e-regiao': 'São Paulo e Região',
        'campinas-e-regiao': 'Campinas e Região',
        'baixada-santista-e-litoral': 'Baixada Santista e Litoral',
        'ribeirao-preto-e-regiao': 'Ribeirão Preto e Região',
    },
    'rj': {
        '': 'Todo estado',
        'rio-de-janeiro-e-regiao': 'Rio de Janeiro e Região',
        'regiao-dos-lagos': 'Região dos Lagos',
        'regiao-serrana': 'Região Serrana',
    },
    'mg': {
        '': 'Todo estado',
        'belo-horizonte-e-regiao': 'Belo Horizonte e Região',
    },
    'ba': {
        '': 'Todo estado',
        'salvador-e-regiao': 'Salvador e Região',
    },
    'pr': {
        '': 'Todo estado',
        'curitiba-e-regiao': 'Curitiba e Região',
    },
    'rs': {
        '': 'Todo estado',
        'porto-alegre-e-regiao': 'Porto Alegre e Região',
    },
}

# Categorias do OLX com path da URL e padrão regex para filtro
CATEGORIES = {
    'games': {
        'name': 'Games',
        'path': 'games',
        'pattern': 'games',
        'subcategories': {
            '': 'Todos',
            'consoles-de-video-game': 'Consoles',
            'acessorios-de-video-game': 'Acessórios',
            'jogos-de-video-game': 'Jogos',
            'jogos-de-video-game/jogos-de-nintendo-switch': 'Jogos Nintendo Switch',
            'jogos-de-video-game/jogos-de-playstation': 'Jogos PlayStation',
            'jogos-de-video-game/jogos-de-xbox': 'Jogos Xbox',
        }
    },
    'eletronicos': {
        'name': 'Eletrônicos e Celulares',
        'path': 'eletronicos-e-celulares',
        'pattern': 'eletronicos|celulares',
        'subcategories': {
            '': 'Todos',
            'celulares': 'Celulares',
            'tablets': 'Tablets',
            'smartwatches': 'Smartwatches',
        }
    },
    'informatica': {
        'name': 'Informática',
        'path': 'computadores-e-acessorios',
        'pattern': 'computadores|informatica',
        'subcategories': {
            '': 'Todos',
            'computadores': 'Computadores',
            'notebooks': 'Notebooks',
            'monitores': 'Monitores',
            'acessorios-para-computador': 'Acessórios',
        }
    },
    'tvs': {
        'name': 'TVs e Vídeo',
        'path': 'tv-video',
        'pattern': 'tv-video|tvs',
        'subcategories': {
            '': 'Todos',
            'tvs': 'TVs',
            'projetores': 'Projetores',
        }
    },
    'audio': {
        'name': 'Áudio',
        'path': 'audio',
        'pattern': 'audio',
        'subcategories': {
            '': 'Todos',
            'fones-de-ouvido': 'Fones de Ouvido',
            'caixas-de-som': 'Caixas de Som',
        }
    },
    'cameras': {
        'name': 'Câmeras e Drones',
        'path': 'cameras-e-drones',
        'pattern': 'cameras|drones',
        'subcategories': {
            '': 'Todos',
            'cameras-digitais': 'Câmeras',
            'drones': 'Drones',
        }
    },
    'moveis': {
        'name': 'Móveis',
        'path': 'moveis',
        'pattern': 'moveis',
        'subcategories': {
            '': 'Todos',
        }
    },
    'eletrodomesticos': {
        'name': 'Eletrodomésticos',
        'path': 'eletrodomesticos',
        'pattern': 'eletrodomesticos',
        'subcategories': {
            '': 'Todos',
        }
    },
    'esportes': {
        'name': 'Esportes e Lazer',
        'path': 'esportes-e-lazer',
        'pattern': 'esportes|lazer',
        'subcategories': {
            '': 'Todos',
            'bicicletas': 'Bicicletas',
            'patins-e-skates': 'Patins e Skates',
        }
    },
    'musica': {
        'name': 'Música e Hobbies',
        'path': 'musica-e-hobbies',
        'pattern': 'musica|hobbies',
        'subcategories': {
            '': 'Todos',
            'instrumentos-musicais': 'Instrumentos',
            'colecoes': 'Coleções',
        }
    },
}


def build_search_url(state: str, region: str, category: str, subcategory: str = '') -> str:
    """Build the OLX search URL based on selections."""
    cat_data = CATEGORIES.get(category, {})
    cat_path = cat_data.get('path', category)

    if subcategory:
        cat_path = f"{cat_path}/{subcategory}"

    if state:
        base = f"https://{state}.olx.com.br"
        if region:
            base = f"{base}/{region}"
    else:
        base = "https://www.olx.com.br"

    return f"{base}/{cat_path}?q="


def get_category_pattern(category: str) -> str:
    """Get the regex pattern for filtering URLs by category."""
    cat_data = CATEGORIES.get(category, {})
    return cat_data.get('pattern', category)
