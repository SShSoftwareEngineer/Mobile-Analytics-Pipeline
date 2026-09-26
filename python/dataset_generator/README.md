# Mock Data Generator (Faker)

Скрипт для генерации реалистичных синтетических датасетов мобильной аналитики и маркетинга с помощью библиотеки [Faker](https://faker.readthedocs.io/).

---

## 📁 Структура сгенерированных файлов

### 1. `events_raw.csv` (События пользователей)
Содержит события действий пользователей в мобильных приложениях:

| Колонка | Тип | Описание | Примеры значений |
|---|---|---|---|
| `event_id` | Positive Int | Идентификатор события (около 5% строк имеют одинаковый `event_id` с более поздним `ingested_at` и иногда обновленным `revenue_usd`) | `1`, `2`, `42` |
| `user_id` | Positive Int | Идентификатор пользователя | `1024`, `1580` |
| `app_id` | Positive Int | Идентификатор приложения (ссылается на `apps.csv`) | `1`, `3` |
| `event_name` | String (≤ 20) | Название события | `app_open`, `purchase`, `level_up` |
| `event_time` | Datetime (UTC) | Время совершения события | `2026-09-10 14:20:00` |
| `ingested_at` | Datetime (UTC) | Время сохранения в хранилище (≥ `event_time`). С вероятностью ~5% имеет задержку в несколько дней (late-arriving data) | `2026-09-15 18:40:12` |
| `country` | String (2 chars) | Двухбуквенный ISO-код страны. Содержит ~7% "грязных" данных | `US`, `DE`, `""`, `"--"`, `us` |
| `media_source` | String | Источник / рекламный канал | `google_ads`, `facebook`, `tiktok`, `organic` |
| `campaign` | String | Название маркетинговой кампании | `tiktok_summer_sale_2026` |
| `revenue_usd` | Float (2 decimals) | Доход в USD. Содержит ~7% "грязных" данных | `9.99`, `0.00`, `""`, `NULL` |
| `is_test` | Boolean String | Флаг тестового трафика | `true`, `false` |

### 2. `apps.csv` (Реестр приложений)
Справочник мобильных приложений:

| Колонка | Тип | Описание | Примеры значений |
|---|---|---|---|
| `app_id` | Positive Int | Первичный ключ приложения | `1`, `2`, `3` |
| `app_name` | String | Название приложения | `Pixel Quest`, `FitPulse` |
| `platform` | String | Платформа | `Android`, `iOS` |
| `store_id` | Positive Int | Идентификатор в сторе (App Store / Google Play) | `4714226` |
| `launched_on` | Datetime (UTC) | Дата и время запуска приложения | `2024-08-30 18:30:39` |

### 3. `campaign_costs.csv` (Маркетинговые затраты)
Данные о затратах и эффективности рекламных кампаний:

| Колонка | Тип | Описание | Примеры значений |
|---|---|---|---|
| `date` | Datetime (UTC) | Дата и время отчета о затратах | `2026-09-10 00:00:00` |
| `app_id` | Positive Int | Идентификатор приложения (ссылается на `apps.csv`) | `1`, `4` |
| `media_source` | String | Рекламный канал | `google_ads`, `facebook` |
| `campaign` | String | Название кампании | `google_ads_brand_awareness` |
| `cost_usd` | Float (2 decimals) | Затраты в USD | `125.50` |
| `impressions` | Positive Int | Количество показов рекламы | `12500` |
| `clicks` | Positive Int | Количество кликов (всегда ≤ `impressions`) | `450` |

---

## 🛠️ Установка и запуск

### 1. Подготовка окружения
```bash
# Создание виртуального окружения
python -m venv .venv

# Активация окружения (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Запуск генерации
Для запуска достаточно выполнить:
```bash
python generate_data.py
```

### 3. Настройка параметров (константы в коде)
Все параметры генерации вынесены в блок понятных констант в начале файла [**`generate_data.py`**](file:///d:/Kolobok/Work%20in%20IT/Python%20Practices/_Test%20Tasks/Inforce/Antigravity/generate_data.py):

```python
# 1. Количество строк в файлах
NUM_APPS = 10                  # приложений в apps.csv
NUM_EVENTS = 1000              # событий в events_raw.csv
NUM_COSTS = 20                 # строк затрат в campaign_costs.csv

# 2. Разделители
CSV_DELIMITER = ";"            # Разделитель колонок в CSV (по умолчанию точка с запятой ';')
MONEY_DECIMAL_SEPARATOR = "."  # '.' для БД (PostgreSQL, ClickHouse и др.), ',' для ТЗ / Excel

# 3. Временное окно
DAYS_WINDOW = 30               # Глубина генерации (дней назад)

# 4. Вероятности сценариев
DIRTY_DATA_RATE = 0.07         # 7% некорректных данных (пустые, '--', нижний регистр, NULL)
LATE_ARRIVAL_RATE = 0.05       # 5% событий с опозданием ingested_at на несколько дней
MAX_DELAY_DAYS = 7             # Максимальное число дней опоздания
DUPLICATE_RATE = 0.05          # 5% дубликатов event_id с обновленным ingested_at/revenue

# 5. Путь и воспроизводимость
OUTPUT_DIR = "."               # Папка для сохранения CSV файлов
RANDOM_SEED = None             # Seed для детерминированной генерации (или None)
```

Для изменения объемов, разделителя (например, переключения разделителя денег на запятую `","`) или вероятностей ошибок достаточно отредактировать нужные значения прямо в начале файла `generate_data.py` и запустить скрипт.

---

## 🧪 Валидация данных

В репозитории есть скрипт `test_data.py`, который проверяет все бизнес-правила и ограничения целостности:
```bash
python test_data.py
```
Проверяется:
- Положительные целые числа (`event_id`, `user_id`, `app_id`, `store_id`, `impressions`, `clicks`)
- Длина `event_name` не превышает 20 символов
- `ingested_at >= event_time`
- Корректная связь по внешним ключам `app_id`
- Процент и корректность инъекции "грязных" данных (`country`, `revenue_usd`)
- Клики не превышают показы (`clicks <= impressions`)
