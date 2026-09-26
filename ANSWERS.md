Перед началом работы над техническим заданием был проведен этап предварительного анализа и подготовки окружения.  
Поскольку в условиях прямо указано наличие намеренных неоднозначностей и потенциальных противоречий в данных, первым шагом стал разбор бизнес-контекста проекта.<br>
Предварительный анализ бизнес-контекста проекта позволяет корректно интерпретировать поля, обработать задержки в поступлении данных (late arrivals) и сформировать правила дедупликации.<br>
Задание моделирует типичный data engineering pipeline для мобильной аналитики и анализа эффективности маркетингового трафика: сбор событий мобильных приложений, очистку и дедупликацию данных, обработку поздних и исправленных событий, а также сопоставление выручки с затратами на маркетинговые кампании.<br>
Предварительный анализ позволил заранее определить границы бизнес-логики, которые легли в основу дальнейших архитектурных решений.

В GitHub создан публичный репозиторий с заданной структурой каталогов.

В PostgreSQL развернута локальная схема БД, созданы таблицы для данных с заданием типов полей, ограничений (constraints) и первичных ключей.  
Надо учесть, что по условию задачи в rewenu_usd могут быть пустые значения, NULL, а разделитель запятая.

Задача 2.1 — Удаление дубликатов

Для выбора последней версии события, которая содержит исправленное значение revenue_usd, используется максимальный 
ingested_at. Тестовые записи исключаются до дедупликации. При одинаковых event_id и ingested_at 
исходные данные (бизнес-логика) не позволяют определить актуальную запись, поэтому дополнительный критерий выбора не вводится.
Для PostgreSQL задача также может быть решена с помощью DISTINCT ON.

2.3 Revenue + Cost + ROAS — обязательно

SQL 1 — формирование app_daily_revenue:

Calculate revenue for each app and calendar day.
Find the last event date in the dataset.
Define the date range for each app: from app launch date to the last event date.
Generate one calendar row for each app and each calendar day.
Add daily revenue to the complete calendar. Days without events receive zero revenue.

SQL 2 — формирование метрик:

The intermediate table contains a row for every calendar day, including days without events, where daily_revenue = 0. 
This is required for the 7-day rolling average: without rows for missing days, AVG() would divide the sum by the number 
of available rows rather than by the number of calendar days in the window.

Calculate cumulative revenue using SUM() window function.
Calculate 7-day rolling average using AVG() over the current day and six preceding calendar days.
Get previous day's revenue using LAG().
Calculate daily revenue change as a percentage of the previous day's revenue. Return NULL when there is no previous 
day or its revenue is zero.

