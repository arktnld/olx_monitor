import asyncio
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from services.database import (
    get_active_searches, create_ad, get_watching_ads,
    add_price_history, update_ad_price, get_last_price_check,
    get_ads_to_check, update_ad_status, get_setting, get_existing_urls,
    get_active_price_alerts, mark_alert_triggered
)
from services.scraper import OlxScraper, filter_urls_by_keywords
from services.logger import get_logger, get_memory_logs, clear_memory_logs
from services.exceptions import ScraperError
from services.notifications import (
    check_price_alert_trigger, notify_price_alert,
    notify_price_drop, notify_cheap_ad, is_price_drop, is_cheap_ad
)
from models import Search, Ad


sched_logger = get_logger("olx_monitor.scheduler")
scheduler = BackgroundScheduler()
scraper = OlxScraper()

logs = []
MAX_LOGS = 100

# Semaphore to limit concurrent requests
MAX_CONCURRENT_REQUESTS = 5

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
    """Add log entry to memory and logging system"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {"timestamp": timestamp, "level": level, "message": message}
    logs.insert(0, log_entry)
    if len(logs) > MAX_LOGS:
        logs.pop()

    # Also log via structured logger
    log_method = getattr(sched_logger, level, sched_logger.info)
    log_method(message)


def get_logs():
    return logs


def clear_logs():
    logs.clear()


async def _fetch_ad_info_with_semaphore(semaphore: asyncio.Semaphore, url: str) -> tuple[str, Ad | None]:
    """Fetch ad info with semaphore to limit concurrency"""
    async with semaphore:
        ad = await scraper.get_ad_info_async(url)
        await asyncio.sleep(1)  # Rate limiting
        return url, ad


async def _check_price_with_semaphore(semaphore: asyncio.Semaphore, ad: Ad) -> tuple[Ad, str | None]:
    """Check price with semaphore to limit concurrency"""
    async with semaphore:
        price = await scraper.get_current_price_async(ad.url)
        await asyncio.sleep(1)  # Rate limiting
        return ad, price


async def _check_status_with_semaphore(semaphore: asyncio.Semaphore, ad_id: int, url: str) -> tuple[int, str, str | None]:
    """Check status with semaphore to limit concurrency"""
    async with semaphore:
        status = await scraper.check_ad_status_async(url)
        await asyncio.sleep(0.5)  # Rate limiting
        return ad_id, url, status


async def _check_price_alerts() -> int:
    """Check all active price alerts and trigger notifications"""
    alerts = get_active_price_alerts()
    triggered = 0

    for alert in alerts:
        ad_id = alert['ad_id']
        target_price = alert['target_price']
        notify_below = alert['notify_below']
        current_price = alert['price']
        title = alert['title']
        url = alert['url']

        # Skip if already triggered
        if alert.get('triggered_at'):
            continue

        # Check if alert should trigger
        if check_price_alert_trigger(current_price, target_price, notify_below):
            try:
                # Send notification
                await notify_price_alert(
                    ad_title=title,
                    old_price=current_price,  # Current price is already updated
                    new_price=current_price,
                    target_price=target_price,
                    ad_url=url
                )
                # Mark as triggered
                mark_alert_triggered(ad_id)
                triggered += 1
                add_log(f"  Alerta disparado: {title[:30]}... (R$ {current_price} <= R$ {target_price:.2f})", "info")
            except Exception as e:
                add_log(f"  Erro ao disparar alerta: {e}", "error")

    return triggered


async def job_search_new_ads_async():
    """Async version of job_search_new_ads"""
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
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        for search_data in searches:
            search = Search.from_dict(search_data)
            add_log(f"Processando busca: {search.name}")

            all_found_urls = []
            queries = search.queries if search.queries else ['']

            # Collect URLs from all queries (can be parallelized)
            for query in queries:
                search_url = scraper.build_search_url(search.base_url, query)
                found_urls = await scraper.get_ad_urls_async(search_url, search.categories)
                filtered_urls = filter_urls_by_keywords(found_urls, search.exclude_keywords)
                all_found_urls.extend(filtered_urls)

            # Batch check which URLs already exist
            all_found_urls = list(set(all_found_urls))
            existing_urls = get_existing_urls(all_found_urls)
            new_urls = [url for url in all_found_urls if url not in existing_urls]

            add_log(f"  {len(new_urls)} URLs novos encontrados para {search.name}")

            if not new_urls:
                continue

            # Fetch ad info in parallel with semaphore
            tasks = [_fetch_ad_info_with_semaphore(semaphore, url) for url in new_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, BaseException):
                    if isinstance(result, ScraperError):
                        add_log(f"  Erro ao buscar anúncio: {result}", "warning")
                    else:
                        add_log(f"  Erro inesperado: {result}", "error")
                    continue

                url, ad = result
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

                    # Notify if price <= 150
                    if is_cheap_ad(ad.price):
                        first_image = ad.images[0] if ad.images else None
                        notify_cheap_ad(ad.title, ad.price, ad.url, first_image)
                        add_log(f"  Notificação enviada: preço baixo R$ {ad.price}", "info")

        add_log(f"Busca finalizada. {total_new} novos anúncios salvos.", "success")
        task_results['search'] = {'success': True, 'total_new': total_new}
    except Exception as e:
        add_log(f"Erro na busca: {e}", "error")
        task_results['search'] = {'success': False, 'error': str(e)}
    finally:
        running_tasks['search'] = False
        await scraper.close()


async def job_check_prices_async():
    """Async version of job_check_prices"""
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
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        # Convert to Ad objects
        ads = [Ad.from_dict(ad_data) for ad_data in watching_ads]

        # Check prices in parallel
        tasks = [_check_price_with_semaphore(semaphore, ad) for ad in ads]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                if isinstance(result, ScraperError):
                    add_log(f"  Erro ao verificar preço: {result}", "warning")
                else:
                    add_log(f"  Erro inesperado: {result}", "error")
                continue

            ad, current_price = result

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

                # Notify if price dropped (watching ads)
                if is_price_drop(last_price, current_price):
                    first_image = ad.images[0] if ad.images else None
                    notify_price_drop(ad.title, last_price, current_price, ad.url, first_image)
                    add_log(f"  Notificação enviada: preço baixou!", "info")
            else:
                add_price_history(ad.id, current_price)

        # Check price alerts
        alerts_triggered = await _check_price_alerts()

        add_log(f"Verificação finalizada. {price_changes} alterações de preço, {alerts_triggered} alertas.", "success")
        task_results['price_check'] = {'success': True, 'price_changes': price_changes}
    except Exception as e:
        add_log(f"Erro na verificação de preços: {e}", "error")
        task_results['price_check'] = {'success': False, 'error': str(e)}
    finally:
        running_tasks['price_check'] = False
        await scraper.close()


async def job_check_ad_status_async():
    """Async version of job_check_ad_status"""
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
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        add_log(f"  {len(ads_to_check)} anúncios para verificar")

        # Check status in parallel
        tasks = [
            _check_status_with_semaphore(semaphore, ad_data['id'], ad_data['url'])
            for ad_data in ads_to_check
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                if isinstance(result, ScraperError):
                    add_log(f"  Erro ao verificar status: {result}", "warning")
                else:
                    add_log(f"  Erro inesperado: {result}", "error")
                continue

            ad_id, url, status = result

            if status == 'inactive':
                update_ad_status(ad_id, 'inactive')
                deactivated += 1
                add_log(f"  Anúncio desativado: {url[:50]}...", "warning")

        add_log(f"Verificação de status finalizada. {deactivated} anúncios desativados.", "success")
        task_results['status_check'] = {'success': True, 'deactivated': deactivated}
    except Exception as e:
        add_log(f"Erro na verificação de status: {e}", "error")
        task_results['status_check'] = {'success': False, 'error': str(e)}
    finally:
        running_tasks['status_check'] = False
        await scraper.close()


def job_search_new_ads():
    """Wrapper to run async job in sync context"""
    asyncio.run(job_search_new_ads_async())


def job_check_prices():
    """Wrapper to run async job in sync context"""
    asyncio.run(job_check_prices_async())


def job_check_ad_status():
    """Wrapper to run async job in sync context"""
    asyncio.run(job_check_ad_status_async())


def start_scheduler():
    if not scheduler.running:
        search_interval = int(get_setting('search_interval', '20') or '20')
        price_interval = int(get_setting('price_interval', '20') or '20')
        status_hour_str = get_setting('status_check_hour', '00:00') or '00:00'

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
