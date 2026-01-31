import time
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from services.database import (
    get_active_searches, ad_exists, create_ad, get_watching_ads,
    add_price_history, update_ad_price, get_last_price_check,
    get_ads_to_check, update_ad_status, get_setting
)
from services.scraper import OlxScraper, filter_urls_by_keywords
from models import Search, Ad


scheduler = BackgroundScheduler()
scraper = OlxScraper()

logs = []
MAX_LOGS = 100

# Estado das tarefas em execução
running_tasks = {
    'search': False,
    'price_check': False,
    'status_check': False
}
task_results = {
    'search': None,
    'price_check': None,
    'status_check': None
}


def add_log(message: str, level: str = "info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {"timestamp": timestamp, "level": level, "message": message}
    logs.insert(0, log_entry)
    if len(logs) > MAX_LOGS:
        logs.pop()
    print(f"[{timestamp}] [{level.upper()}] {message}")


def get_logs():
    return logs


def clear_logs():
    logs.clear()


def job_search_new_ads():
    global running_tasks, task_results

    if running_tasks['search']:
        add_log("Busca já está em execução", "warning")
        return

    running_tasks['search'] = True
    task_results['search'] = None
    add_log("Iniciando busca por novos anúncios...")

    try:
        searches = get_active_searches()
        total_new = 0

        for search_data in searches:
            search = Search.from_dict(search_data)
            add_log(f"Processando busca: {search.name}")

            new_urls = set()

            # Se não tem queries, usa string vazia para buscar categoria inteira
            queries = search.queries if search.queries else ['']

            for query in queries:
                search_url = scraper.build_search_url(search.base_url, query)
                found_urls = scraper.get_ad_urls(search_url, search.categories)
                filtered_urls = filter_urls_by_keywords(found_urls, search.exclude_keywords)

                for url in filtered_urls:
                    if not ad_exists(url):
                        new_urls.add(url)

            add_log(f"  {len(new_urls)} URLs novos encontrados para {search.name}")

            for url in new_urls:
                ad = scraper.get_ad_info(url)
                if ad:
                    create_ad(
                        url=ad.url,
                        title=ad.title,
                        price=ad.price,
                        description=ad.description,
                        state=ad.state,
                        municipality=ad.municipality,
                        neighbourhood=ad.neighbourhood,
                        zipcode=ad.zipcode,
                        seller=ad.seller,
                        condition=ad.condition,
                        published_at=ad.published_at,
                        main_category=ad.main_category,
                        sub_category=ad.sub_category,
                        hobbie_type=ad.hobbie_type,
                        images=ad.images,
                        olx_pay=ad.olx_pay,
                        olx_delivery=ad.olx_delivery,
                        search_id=search.id
                    )
                    total_new += 1
                    add_log(f"  + Novo anúncio: {ad.title[:50]}...")

                time.sleep(2)

        add_log(f"Busca finalizada. {total_new} novos anúncios salvos.", "success")
        task_results['search'] = {'success': True, 'total_new': total_new}
    except Exception as e:
        add_log(f"Erro na busca: {e}", "error")
        task_results['search'] = {'success': False, 'error': str(e)}
    finally:
        running_tasks['search'] = False


def job_check_prices():
    global running_tasks, task_results

    if running_tasks['price_check']:
        add_log("Verificação de preços já está em execução", "warning")
        return

    running_tasks['price_check'] = True
    task_results['price_check'] = None
    add_log("Verificando preços dos anúncios acompanhados...")

    try:
        watching_ads = get_watching_ads()
        price_changes = 0

        for ad_data in watching_ads:
            ad = Ad.from_dict(ad_data)
            current_price = scraper.get_current_price(ad.url)

            if current_price is None:
                add_log(f"  Não foi possível verificar preço: {ad.title[:30]}...", "warning")
                continue

            if ad.id is None:
                continue

            last_check = get_last_price_check(ad.id)
            last_price = last_check.get("price") if last_check else ad.price

            if current_price != last_price:
                add_price_history(ad.id, current_price)
                update_ad_price(ad.id, current_price)
                add_log(f"  Preço alterado: {ad.title[:30]}... ({last_price} -> {current_price})", "info")
                price_changes += 1
            else:
                add_price_history(ad.id, current_price)

            time.sleep(2)

        add_log(f"Verificação finalizada. {price_changes} alterações de preço.", "success")
        task_results['price_check'] = {'success': True, 'price_changes': price_changes}
    except Exception as e:
        add_log(f"Erro na verificação de preços: {e}", "error")
        task_results['price_check'] = {'success': False, 'error': str(e)}
    finally:
        running_tasks['price_check'] = False


def job_check_ad_status():
    """Check if ads are still active (runs daily at midnight)"""
    global running_tasks, task_results

    if running_tasks['status_check']:
        add_log("Verificação de status já está em execução", "warning")
        return

    running_tasks['status_check'] = True
    task_results['status_check'] = None
    add_log("Verificando status dos anúncios...")

    try:
        ads_to_check = get_ads_to_check()
        deactivated = 0

        add_log(f"  {len(ads_to_check)} anúncios para verificar")

        for ad_data in ads_to_check:
            ad_id = ad_data['id']
            url = ad_data['url']

            status = scraper.check_ad_status(url)

            if status == 'inactive':
                update_ad_status(ad_id, 'inactive')
                deactivated += 1
                add_log(f"  Anúncio desativado: {url[:50]}...", "warning")

            time.sleep(1)  # Rate limiting

        add_log(f"Verificação de status finalizada. {deactivated} anúncios desativados.", "success")
        task_results['status_check'] = {'success': True, 'deactivated': deactivated}
    except Exception as e:
        add_log(f"Erro na verificação de status: {e}", "error")
        task_results['status_check'] = {'success': False, 'error': str(e)}
    finally:
        running_tasks['status_check'] = False


def start_scheduler():
    if not scheduler.running:
        # Ler intervalos do banco ou usar defaults
        search_interval = int(get_setting('search_interval', '20') or '20')
        price_interval = int(get_setting('price_interval', '20') or '20')
        status_hour_str = get_setting('status_check_hour', '00:00') or '00:00'

        # Parsear hora do status check
        try:
            hour, minute = map(int, status_hour_str.split(':'))
        except ValueError:
            hour, minute = 0, 0

        scheduler.add_job(
            job_search_new_ads,
            trigger=IntervalTrigger(minutes=search_interval),
            id="search_new_ads",
            name="Buscar novos anúncios",
            replace_existing=True
        )

        scheduler.add_job(
            job_check_prices,
            trigger=IntervalTrigger(minutes=price_interval),
            id="check_prices",
            name="Verificar preços",
            replace_existing=True
        )

        scheduler.add_job(
            job_check_ad_status,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="check_ad_status",
            name="Verificar status dos anúncios",
            replace_existing=True
        )

        scheduler.start()
        add_log(f"Scheduler iniciado (busca: {search_interval}min, preços: {price_interval}min, status: {status_hour_str})", "success")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        add_log("Scheduler parado", "info")


def run_search_now():
    """Executa busca em thread separada (não bloqueia a UI)"""
    if running_tasks['search']:
        return False
    thread = threading.Thread(target=job_search_new_ads, daemon=True)
    thread.start()
    return True


def run_price_check_now():
    """Executa verificação de preços em thread separada"""
    if running_tasks['price_check']:
        return False
    thread = threading.Thread(target=job_check_prices, daemon=True)
    thread.start()
    return True


def run_status_check_now():
    """Executa verificação de status em thread separada"""
    if running_tasks['status_check']:
        return False
    thread = threading.Thread(target=job_check_ad_status, daemon=True)
    thread.start()
    return True


def get_task_status(task_name: str):
    """Retorna o status de uma tarefa (running, result)"""
    return {
        'running': running_tasks.get(task_name, False),
        'result': task_results.get(task_name)
    }


def reschedule_jobs():
    """Reconfigura os jobs com os novos intervalos sem reiniciar o scheduler"""
    if not scheduler.running:
        return False

    search_interval = int(get_setting('search_interval', '20') or '20')
    price_interval = int(get_setting('price_interval', '20') or '20')
    status_hour_str = get_setting('status_check_hour', '00:00') or '00:00'

    try:
        hour, minute = map(int, status_hour_str.split(':'))
    except ValueError:
        hour, minute = 0, 0

    scheduler.reschedule_job(
        "search_new_ads",
        trigger=IntervalTrigger(minutes=search_interval)
    )

    scheduler.reschedule_job(
        "check_prices",
        trigger=IntervalTrigger(minutes=price_interval)
    )

    scheduler.reschedule_job(
        "check_ad_status",
        trigger=CronTrigger(hour=hour, minute=minute)
    )

    add_log(f"Jobs reconfigurados (busca: {search_interval}min, preços: {price_interval}min, status: {status_hour_str})", "success")
    return True


def get_scheduler_status():
    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None
            }
            for job in scheduler.get_jobs()
        ] if scheduler.running else []
    }
