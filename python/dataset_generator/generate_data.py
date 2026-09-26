"""
CSV Mock Data Generator using Faker.

Generates three synthetic datasets for analytics/ETL pipelines:
1. events_raw.csv      - Raw tracking events (with dirty data, late arrival, and duplicate updates)
2. apps.csv            - Mobile applications registry
3. campaign_costs.csv  - Daily advertising campaign spend and engagement
"""

import csv
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from faker import Faker

# Ensure UTF-8 output on Windows consoles if needed
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ===========================================================================
# ⚙️ ПАРАМЕТРЫ ГЕНЕРАЦИИ (КОНСТАНТЫ)
# ===========================================================================

# 1. Количество строк в файлах
NUM_APPS: int = 10                  # Количество приложений в apps.csv
NUM_EVENTS: int = 1000              # Количество событий в events_raw.csv
NUM_COSTS: int = 20                 # Количество строк затрат в campaign_costs.csv

# 2. Разделители
CSV_DELIMITER: str = ";"            # Разделитель колонок в CSV файлах (точка с запятой)
MONEY_DECIMAL_SEPARATOR: str = ","   # Разделитель для денег (cost_usd, revenue_usd):
                                    # '.' - стандарт для БД (PostgreSQL, ClickHouse и др.)
                                    # ',' - по условиям задачи / русский Excel

# 3. Временное окно
DAYS_WINDOW: int = 30               # Глубина генерации дат (дней назад от текущей даты)

# 4. Вероятности моделируемых сценариев
DIRTY_DATA_RATE: float = 0.07       # 7% "грязных" данных в events_raw (пустые, '--', нижний регистр, NULL)
LATE_ARRIVAL_RATE: float = 0.05     # 5% событий с задержкой ingested_at на несколько дней
MAX_DELAY_DAYS: int = 7             # Максимальное число дней опоздания для late-arriving событий
DUPLICATE_RATE: float = 0.05        # 5% дубликатов event_id с обновленным ingested_at и, иногда, revenue_usd

# 5. Путь выгрузки и воспроизводимость
OUTPUT_DIR: str = "."               # Папка для сохранения сгенерированных CSV файлов
RANDOM_SEED: Optional[int] = None   # Seed для воспроизводимости (None = случайный запуск каждый раз)

# ===========================================================================


# ---------------------------------------------------------------------------
# Доменные справочники и веса
# ---------------------------------------------------------------------------

EVENT_NAMES: List[str] = [
    "app_open",           # 8 chars
    "session_start",      # 13 chars
    "tutorial_complete",  # 17 chars
    "level_up",           # 8 chars
    "view_ad",            # 7 chars
    "purchase",           # 8 chars
    "button_click",       # 12 chars
    "add_to_cart",        # 11 chars
    "share_social",       # 12 chars
    "rate_app",           # 8 chars
    "session_end",        # 11 chars
]

# Веса распределения событий
EVENT_WEIGHTS: List[int] = [30, 20, 5, 15, 12, 6, 8, 4, 3, 2, 10]

MEDIA_SOURCES: List[str] = [
    "google_ads",
    "facebook",
    "tiktok",
    "unity_ads",
    "apple_search_ads",
    "organic",
]

CAMPAIGN_TEMPLATES: List[str] = [
    "summer_sale_2026",
    "tier1_acquisition",
    "retargeting_v2",
    "brand_awareness",
    "influencer_blast",
    "spring_promo",
    "cpi_android_scale",
    "roas_opt_ios",
    "global_reach_01",
    "reactivation_q3",
]

PURCHASE_AMOUNTS: List[float] = [
    0.99, 1.99, 2.99, 4.99, 7.99, 9.99, 14.99, 19.99, 29.99, 49.99, 99.99
]

PLATFORMS: List[str] = ["Android", "iOS"]


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def get_utc_now() -> datetime:
    """Возвращает текущую дату и время в UTC."""
    return datetime.now(timezone.utc)


def format_utc(dt: datetime) -> str:
    """Форматирует datetime в строку UTC YYYY-MM-DD HH:MM:SS."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Генератор данных
# ---------------------------------------------------------------------------

class MockDataGenerator:
    """Генератор датасетов apps, campaign_costs и events_raw."""

    def __init__(
        self,
        seed: Optional[int] = RANDOM_SEED,
        days_window: int = DAYS_WINDOW,
        dirty_rate: float = DIRTY_DATA_RATE,
        late_arrival_rate: float = LATE_ARRIVAL_RATE,
        max_delay_days: int = MAX_DELAY_DAYS,
        duplicate_rate: float = DUPLICATE_RATE,
        decimal_sep: str = MONEY_DECIMAL_SEPARATOR,
    ) -> None:
        self.seed = seed
        self.days_window = days_window
        self.dirty_rate = dirty_rate
        self.late_arrival_rate = late_arrival_rate
        self.max_delay_days = max(1, max_delay_days)
        self.duplicate_rate = duplicate_rate
        self.decimal_sep = decimal_sep

        self.fake = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        self.now_utc = get_utc_now()
        self.start_utc = self.now_utc - timedelta(days=days_window)

    def format_money(self, val: float) -> str:
        """Форматирует денежное значение с 2 знаками после запятой/точки."""
        formatted = f"{val:.2f}"
        if self.decimal_sep != ".":
            formatted = formatted.replace(".", self.decimal_sep)
        return formatted

    def generate_apps(self, num_apps: int = NUM_APPS) -> List[Dict[str, object]]:
        """
        Генерация строк apps.csv.
        
        Колонки:
        - app_id: целое положительное число
        - app_name: строка
        - platform: Android или iOS
        - store_id: целое положительное число
        - launched_on: дата-время в UTC
        """
        apps = []
        app_names_pool = [
            "Pixel Quest", "FinWise Pro", "FitPulse", "Galaxy Runner",
            "ColorMatch 3D", "Mindful Moments", "AutoRacer Turbo", "CryptoSphere",
            "ChefMaster Story", "TowerCraft", "HealthHero", "SoundWave",
            "PhotoCraft Studio", "ZenGarden", "ShadowStrike"
        ]

        for app_id in range(1, num_apps + 1):
            if app_id <= len(app_names_pool):
                app_name = app_names_pool[app_id - 1]
            else:
                app_name = f"{self.fake.word().capitalize()} {self.fake.word().capitalize()}"

            platform = random.choice(PLATFORMS)
            store_id = self.fake.random_int(min=100000, max=9999999)

            # Дата запуска приложения: от 1 до 3 лет назад
            launched_days_ago = random.randint(self.days_window + 10, self.days_window + 1000)
            launched_on = self.now_utc - timedelta(
                days=launched_days_ago,
                seconds=random.randint(0, 86400)
            )

            apps.append({
                "app_id": app_id,
                "app_name": app_name,
                "platform": platform,
                "store_id": store_id,
                "launched_on": format_utc(launched_on),
            })

        return apps

    def generate_campaign_costs(
        self,
        num_costs: int = NUM_COSTS,
        apps: Optional[List[Dict[str, object]]] = None,
        campaigns_pool: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Dict[str, object]]:
        """
        Генерация строк campaign_costs.csv.
        
        Колонки:
        - date: дата-время в UTC
        - app_id: целое положительное число
        - media_source: короткая строка, источник/рекламный канал
        - campaign: строка, название кампании
        - cost_usd: стоимость, положительное число с двумя знаками
        - impressions: небольшое целое положительное число
        - clicks: небольшое целое положительное число
        """
        if apps is None:
            apps = self.generate_apps()
        if campaigns_pool is None:
            campaigns_pool = build_campaigns_pool()

        costs = []
        app_ids = [app["app_id"] for app in apps]

        # Исключаем 'organic' из платных рекламных затрат
        paid_campaigns = [c for c in campaigns_pool if c[0] != "organic"]
        if not paid_campaigns:
            paid_campaigns = [("google_ads", "brand_awareness")]

        for _ in range(num_costs):
            random_seconds = random.randint(0, int(self.days_window * 86400))
            cost_date = self.start_utc + timedelta(seconds=random_seconds)

            app_id = random.choice(app_ids)
            media_source, campaign = random.choice(paid_campaigns)

            impressions = self.fake.random_int(min=500, max=25000)
            ctr = random.uniform(0.012, 0.075)
            clicks = max(1, int(impressions * ctr))

            cpc = random.uniform(0.25, 2.80)
            cost_usd = round(clicks * cpc + random.uniform(0.5, 5.0), 2)

            costs.append({
                "date": format_utc(cost_date),
                "app_id": app_id,
                "media_source": media_source,
                "campaign": campaign,
                "cost_usd": self.format_money(cost_usd),
                "impressions": impressions,
                "clicks": clicks,
            })

        costs.sort(key=lambda x: x["date"])
        return costs

    def generate_events_raw(
        self,
        num_events: int = NUM_EVENTS,
        apps: Optional[List[Dict[str, object]]] = None,
        campaigns_pool: Optional[List[Tuple[str, str]]] = None,
        num_users: Optional[int] = None,
    ) -> List[Dict[str, object]]:
        """
        Генерация строк events_raw.csv с грязными данными, опозданиями и повторами.
        
        Колонки:
        - event_id: целое положительное число (дублируется ~5%)
        - user_id: целое положительное число
        - app_id: целое положительное число
        - event_name: строка до 20 символов
        - event_time: дата-время в UTC
        - ingested_at: дата-время в UTC, больше или равно event_time
        - country: строка из 2 символов в верхнем регистре (грязные: пустой, '--', нижний регистр)
        - media_source: короткая строка, источник/канал
        - campaign: строка, название кампании
        - revenue_usd: стоимость с двумя знаками (грязные: пустой, NULL)
        - is_test: true или false
        """
        if apps is None:
            apps = self.generate_apps()
        if campaigns_pool is None:
            campaigns_pool = build_campaigns_pool()

        events = []
        app_ids = [app["app_id"] for app in apps]

        # Расчет количества уникальных и дублирующихся событий
        num_duplicates = int(num_events * self.duplicate_rate)
        num_unique = max(1, num_events - num_duplicates)

        if num_users is None:
            num_users = max(50, num_unique // 8)
        user_ids = list(range(1001, 1001 + num_users))

        # Привязка пользователей к каналам и странам
        user_attribution = {}
        for uid in user_ids:
            user_attribution[uid] = {
                "campaign_info": random.choice(campaigns_pool),
                "country": self.fake.country_code(),
            }

        # Шаг 1: Генерация уникальных событий
        for _ in range(num_unique):
            user_id = random.choice(user_ids)
            app_id = random.choice(app_ids)
            event_name = random.choices(EVENT_NAMES, weights=EVENT_WEIGHTS, k=1)[0]
            
            # Строго до 20 символов
            event_name = event_name[:20]

            random_offset_seconds = random.randint(0, int(self.days_window * 86400))
            event_time = self.start_utc + timedelta(seconds=random_offset_seconds)

            # Логика задержки записи (ingested_at >= event_time):
            # С вероятностью late_arrival_rate - многодневная задержка (1..max_delay_days дней)
            # В остальных случаях - штатная операционная задержка (до 2 часов)
            if self.late_arrival_rate > 0 and random.random() < self.late_arrival_rate:
                delay_days = random.randint(1, self.max_delay_days)
                delay_seconds = delay_days * 86400 + random.randint(0, 86400)
            else:
                delay_seconds = random.randint(0, 7200)

            ingested_at = event_time + timedelta(seconds=delay_seconds)

            media_source, campaign = user_attribution[user_id]["campaign_info"]

            # Генерация страны с возможностью "грязных" данных
            clean_country = user_attribution[user_id]["country"]
            if self.dirty_rate > 0 and random.random() < self.dirty_rate:
                country = random.choice(["", "--", clean_country.lower()])
            else:
                country = clean_country

            # Генерация revenue_usd с возможностью "грязных" данных
            is_purchase = (event_name == "purchase")
            has_ad_revenue = (event_name == "view_ad" and random.random() < 0.3)

            if is_purchase:
                raw_revenue = random.choice(PURCHASE_AMOUNTS)
            elif has_ad_revenue:
                raw_revenue = round(random.uniform(0.01, 0.25), 2)
            else:
                raw_revenue = 0.00

            if self.dirty_rate > 0 and random.random() < self.dirty_rate:
                revenue_usd = random.choice(["", "NULL"])
            else:
                revenue_usd = self.format_money(raw_revenue)

            # is_test: true или false
            is_test = "true" if random.random() < 0.03 else "false"

            events.append({
                "event_id": 0,
                "user_id": user_id,
                "app_id": app_id,
                "event_name": event_name,
                "event_time": format_utc(event_time),
                "ingested_at": format_utc(ingested_at),
                "country": country,
                "media_source": media_source,
                "campaign": campaign,
                "revenue_usd": revenue_usd,
                "is_test": is_test,
            })

        # Сортируем уникальные события по времени и присваиваем event_id
        events.sort(key=lambda x: x["event_time"])
        for idx, event in enumerate(events, start=1):
            event["event_id"] = idx

        # Шаг 2: Генерация дубликатов (~5%) с тем же event_id, более поздним ingested_at и иногда обновленным revenue_usd
        zero_formatted = self.format_money(0.00)
        if num_duplicates > 0:
            sample_size = min(num_duplicates, len(events))
            base_to_duplicate = random.sample(events, k=sample_size)
            duplicate_events = []

            for orig in base_to_duplicate:
                dup = orig.copy()
                orig_ingested = datetime.strptime(orig["ingested_at"], "%Y-%m-%d %H:%M:%S")

                # Повторное поступление: через 1-5 дней после первой записи
                reingest_delay_seconds = random.randint(3600, 5 * 86400)
                dup_ingested = orig_ingested + timedelta(seconds=reingest_delay_seconds)
                dup["ingested_at"] = format_utc(dup_ingested)

                # Иногда (~45% случаев дублирования) обновляется revenue_usd
                if random.random() < 0.45:
                    if orig["revenue_usd"] in ("", "NULL", zero_formatted):
                        dup["revenue_usd"] = self.format_money(random.choice(PURCHASE_AMOUNTS))
                    else:
                        new_val = random.choice([0.00] + PURCHASE_AMOUNTS)
                        dup["revenue_usd"] = self.format_money(new_val)

                duplicate_events.append(dup)

            events.extend(duplicate_events)

        # Сортировка всех строк по event_time, затем по ingested_at
        events.sort(key=lambda x: (x["event_time"], x["ingested_at"]))

        return events


# ---------------------------------------------------------------------------
# Запись в CSV
# ---------------------------------------------------------------------------

def write_csv(
    filepath: Path,
    fieldnames: List[str],
    rows: List[Dict[str, object]],
    delimiter: str = CSV_DELIMITER,
) -> int:
    """Записывает список словарей в CSV с заданным разделителем колонок."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def build_campaigns_pool() -> List[Tuple[str, str]]:
    """Создает согласованный пул связок (media_source, campaign)."""
    pool = []
    for source in MEDIA_SOURCES:
        if source == "organic":
            pool.append(("organic", "organic_install"))
        else:
            for campaign in random.sample(CAMPAIGN_TEMPLATES, k=min(4, len(CAMPAIGN_TEMPLATES))):
                pool.append((source, f"{source}_{campaign}"))
    return pool


# ---------------------------------------------------------------------------
# Точка входа (запуск генерации)
# ---------------------------------------------------------------------------

def main() -> None:
    out_dir = Path(OUTPUT_DIR)

    print("=" * 65)
    print("🚀 Генератор синтетических данных (Faker)")
    print(f"   • Выходная папка        : {out_dir.resolve()}")
    print(f"   • Разделитель CSV       : '{CSV_DELIMITER}'")
    print(f"   • Разделитель для денег : '{MONEY_DECIMAL_SEPARATOR}' ({'точка (БД)' if MONEY_DECIMAL_SEPARATOR == '.' else 'запятая (ТЗ/Excel)'})")
    print(f"   • Приложений (apps)     : {NUM_APPS}")
    print(f"   • Событий (events_raw)  : {NUM_EVENTS}")
    print(f"   • Затрат (costs)        : {NUM_COSTS}")
    print(f"   • Окно генерации        : {DAYS_WINDOW} дней")
    print(f"   • Доля грязных данных   : {DIRTY_DATA_RATE * 100:.1f}%")
    print(f"   • Доля поздних данных   : {LATE_ARRIVAL_RATE * 100:.1f}% (до {MAX_DELAY_DAYS} дн.)")
    print(f"   • Доля дубликатов       : {DUPLICATE_RATE * 100:.1f}% (повторный event_id)")
    if RANDOM_SEED is not None:
        print(f"   • Random seed           : {RANDOM_SEED}")
    print("=" * 65)

    generator = MockDataGenerator()
    campaigns_pool = build_campaigns_pool()

    # 1. Генерация apps.csv
    print("\n[+] Создание apps.csv...")
    apps_data = generator.generate_apps(num_apps=NUM_APPS)
    apps_path = out_dir / "apps.csv"
    apps_count = write_csv(
        filepath=apps_path,
        fieldnames=["app_id", "app_name", "platform", "store_id", "launched_on"],
        rows=apps_data,
        delimiter=CSV_DELIMITER,
    )
    print(f"    [OK] Записано {apps_count} строк в {apps_path.name} ({apps_path.stat().st_size:,} байт)")

    # 2. Генерация campaign_costs.csv
    print("\n[+] Создание campaign_costs.csv...")
    costs_data = generator.generate_campaign_costs(
        num_costs=NUM_COSTS,
        apps=apps_data,
        campaigns_pool=campaigns_pool,
    )
    costs_path = out_dir / "campaign_costs.csv"
    costs_count = write_csv(
        filepath=costs_path,
        fieldnames=["date", "app_id", "media_source", "campaign", "cost_usd", "impressions", "clicks"],
        rows=costs_data,
        delimiter=CSV_DELIMITER,
    )
    print(f"    [OK] Записано {costs_count} строк в {costs_path.name} ({costs_path.stat().st_size:,} байт)")

    # 3. Генерация events_raw.csv
    print("\n[+] Создание events_raw.csv...")
    events_data = generator.generate_events_raw(
        num_events=NUM_EVENTS,
        apps=apps_data,
        campaigns_pool=campaigns_pool,
    )
    events_path = out_dir / "events_raw.csv"
    events_count = write_csv(
        filepath=events_path,
        fieldnames=[
            "event_id",
            "user_id",
            "app_id",
            "event_name",
            "event_time",
            "ingested_at",
            "country",
            "media_source",
            "campaign",
            "revenue_usd",
            "is_test",
        ],
        rows=events_data,
        delimiter=CSV_DELIMITER,
    )
    print(f"    [OK] Записано {events_count} строк в {events_path.name} ({events_path.stat().st_size:,} байт)")

    print("\n" + "=" * 65)
    print("✅ Все 3 датасета успешно сгенерированы!")
    print("=" * 65)


if __name__ == "__main__":
    main()
