# Слой 07 — Импорт данных, релиз и переключение (cutover)

Это седьмой, финальный слой переписывания ushu на Elixir. Слои 01–06 дали нам
работающее приложение — но с пустой базой. Вся история соревнований, справочники
элементов, судьи и клубы живут в Django-файле `db.sqlite3`, а ноутбук на
соревнованиях по-прежнему запускает Django через `start.bat`.

Этот слой закрывает три вещи:

1. **Импорт** — mix-задача `mix ushu.import`, которая читает Django-базу напрямую
   и переливает её в схему Elixir-приложения: с сохранением id, с превращением
   «магических чисел» в типизированные enum'ы и с обязательной самопроверкой.
2. **Деплой** — `mix release`: самодостаточный дистрибутив для Windows-ноутбука,
   `runtime.exs` с переменными `USHU_*`, лаунчер `.bat` и процедура бэкапа,
   учитывающая WAL-режим SQLite.
3. **Переключение** — прогон «сухого турнира», план дня переключения с жёсткой
   контрольной точкой и путь отката: Django остаётся установленным и запускаемым.

Аналогия из твоего мира: это как финальный этап миграции со старого
Spring-монолита — Flyway-скрипты налили данные, `bootJar` собрал артефакт,
а у ops-команды есть runbook с чекпоинтом «если не сошлось — откатываемся».
Только здесь всё это делает один человек на одном ноутбуке, поэтому каждая
процедура обязана быть «двойной клик и понятная надпись».

---

## Ключевые концепции Elixir/Phoenix в этом слое

### 1. Mix-задачи — свои команды в CLI проекта

`mix` — это Gradle Elixir-мира: сборка, тесты, зависимости. Как и в Gradle,
можно писать собственные задачи. Задача — обычный модуль с именем
`Mix.Tasks.<Имя>` и функцией `run/1`:

```elixir
# lib/mix/tasks/ushu.import.ex
defmodule Mix.Tasks.Ushu.Import do
  use Mix.Task

  @shortdoc "Импортирует Django-базу SQLite в приложение ushu"
  @moduledoc """
  ## Использование

      mix ushu.import path/to/db.sqlite3 [--media DIR] [--dry-run]
        [--password-file FILE] [--allow-score-drift]
  """

  @impl Mix.Task
  def run(args) do
    {opts, [source_path], _} =
      OptionParser.parse(args,
        strict: [media: :string, dry_run: :boolean,
                 password_file: :string, allow_score_drift: :boolean])

    Mix.Task.run("app.start")          # поднять приложение (Repo и т.д.)

    case Ushu.Import.run(source_path, opts) do
      {:ok, report}      -> Mix.shell().info(report)
      {:error, report}   -> Mix.shell().error(report)
                            exit({:shutdown, 1})    # ненулевой exit-код
    end
  end
end
```

Сравни с Kotlin/Gradle: `tasks.register("ushuImport") { doLast { ... } }` или
Spring Boot `CommandLineRunner` с профилем. Отличия, которые стоит запомнить:

- Имя модуля определяет имя команды: `Mix.Tasks.Ushu.Import` → `mix ushu.import`.
- `Mix.Task.run("app.start")` — аналог поднятия Spring-контекста: без него
  `Ushu.Repo` не запущен и обращения к базе упадут.
- `@shortdoc` попадает в `mix help` — документация встроена в задачу.

Важный принцип: **вся логика живёт не в задаче, а в обычном модуле**
`Ushu.Import`. Mix-задача — тонкая обёртка (парсинг аргументов + вывод).
Причина та же, по которой в Spring не пишут бизнес-логику в `main()`:
модуль можно тестировать в ExUnit и вызывать из других мест — например,
из релиза, где Mix вообще недоступен (об этом ниже).

### 2. `mix release` — и почему это НЕ uberjar

В JVM-мире ты собираешь fat jar: один файл, но на машине должна стоять JVM.
`mix release` работает иначе — он собирает **каталог**, в который входит:

- скомпилированный BEAM-байткод твоего приложения и всех зависимостей;
- **сам ERTS** (Erlang Runtime System — «JVM» мира Erlang);
- стартовые скрипты: `bin/ushu` (Unix) и `bin/ushu.bat` (Windows).

То есть релиз ближе не к uberjar, а к `jlink + jpackage`: на целевой машине
не нужно ставить ни Elixir, ни Erlang — всё в комплекте.

```elixir
# mix.exs
def project do
  [
    app: :ushu,
    # ...
    releases: [
      ushu: [
        include_executables_for: [:windows],
        applications: [runtime_tools: :permanent]
      ]
    ]
  ]
end
```

```
set MIX_ENV=prod
mix release
# → _build/prod/rel/ushu/  — копируешь папку на ноутбук, и всё
```

Два следствия, которые больно узнавать на месте:

1. **ERTS платформенно-зависим.** Релиз, собранный на macOS, не запустится на
   Windows. Кросс-компиляции нет — релиз для ноутбука собираем НА Windows
   (однократная установка Erlang/OTP + Elixir на ноутбук или отдельную
   Windows-машину). Это решение D7 в design.md.
2. **В релизе нет Mix.** `mix ecto.migrate`, `mix ushu.import` — этих команд
   на ноутбуке не существует. Всё, что нужно в проде, выносится в обычные
   модули и вызывается через `bin\ushu.bat eval`:

```elixir
# lib/ushu/release.ex — стандартный паттерн для релизов
defmodule Ushu.Release do
  @app :ushu

  def migrate do
    Application.load(@app)
    for repo <- Application.fetch_env!(@app, :ecto_repos) do
      {:ok, _, _} = Ecto.Migrator.with_repo(repo, &Ecto.Migrator.run(&1, :up, all: true))
    end
  end

  def backup do
    stamp = Calendar.strftime(DateTime.utc_now(), "%Y%m%d-%H%M%S")
    path  = Path.join("backups", "ushu-#{stamp}.sqlite3")
    File.mkdir_p!("backups")
    {:ok, _} = Ushu.Repo.query("VACUUM INTO ?", [path])
    IO.puts("Backup: #{path}")
  end

  def import(source_path, opts \\ []) do
    Application.ensure_all_started(@app)
    Ushu.Import.run(source_path, opts)
  end
end
```

```
:: на ноутбуке:
bin\ushu.bat eval "Ushu.Release.migrate()"
bin\ushu.bat eval "Ushu.Release.backup()"
bin\ushu.bat start
```

Параллель со Spring: `Ushu.Release.migrate/0` — это как запуск Flyway при
старте приложения, только явный и отделённый от старта сервера: миграции
прогоняются лаунчером ДО того, как endpoint начнёт принимать соединения.

### 3. `runtime.exs` — конфигурация времени запуска

В Elixir два вида конфигурации, и это важнейшее различие:

- `config/config.exs`, `config/prod.exs` — **compile-time**: читаются при
  компиляции, их значения запекаются в байткод.
- `config/runtime.exs` — **runtime**: исполняется при каждом старте,
  в том числе внутри релиза. Единственное место, где можно читать переменные
  окружения на проде.

Это аналог пары «`application.yml` в jar» против «env vars, которые Spring
резолвит при старте». Ошибка новичка — прочитать `System.get_env` в
`config.exs` и удивиться, что в релизе значение застыло со времён сборки.

```elixir
# config/runtime.exs
import Config

if config_env() == :prod do
  secret =
    System.get_env("USHU_SECRET_KEY") ||
      raise """
      Переменная USHU_SECRET_KEY не задана.
      Задай её в start-ushu.bat (случайная строка 64+ символов).
      """

  config :ushu, UshuWeb.Endpoint,
    http: [ip: {0, 0, 0, 0}, port: String.to_integer(System.get_env("USHU_PORT") || "8081")],
    secret_key_base: secret,
    server: true

  config :ushu, Ushu.Repo,
    database: System.get_env("USHU_DB_PATH") || "ushu.sqlite3"

  config :ushu, :event,
    title:    System.get_env("USHU_EVENT_TITLE")    || "USHU",
    subtitle: System.get_env("USHU_EVENT_SUBTITLE") || ""
end
```

Обрати внимание на `raise` с человеческим текстом: сервер обязан упасть сразу
и понятно, а не глубоко в стеке Phoenix. Имена переменных — те же
`USHU_*`, что и в Django-версии (`start.bat`): оператору не нужно
переучиваться. Порт по умолчанию 8081 — тот же, что у Django: десять клиентских
машин с закладками ничего не заметят (решение D9).

### 4. BEAM на Windows — что реально нужно знать

Erlang и Elixir на Windows — граждане первого класса: официальные инсталляторы,
релиз генерирует `bin\ushu.bat` автоматически. Практические моменты:

- **Сборка на Windows обязательна** (см. выше про ERTS).
- **NIF-зависимости** (нативные расширения, аналог JNI) требуют C-компилятор.
  Например, `bcrypt_elixir` для хэширования паролей собирается через
  cc/MSVC — на голом ноутбуке это боль. Поэтому мы просигналили слою 04:
  чистый Elixir `pbkdf2_elixir` предпочтительнее. Импортёру всё равно —
  он хэширует через changeset из `Ushu.Accounts` и не знает алгоритма.
- **Лаунчер** — тот же паттерн, что нынешний `start.bat`: блок `set USHU_*`
  сверху, потом миграции, потом старт:

```bat
@ECHO OFF
REM start-ushu.bat — лаунчер ushu (Elixir). Правь блок ниже перед турниром.
cd /d "%~dp0"

REM --- конфигурация (правится на каждый турнир) ----------------------------
set USHU_SECRET_KEY=CHANGE-ME-random-64-chars
set USHU_PORT=8081
set USHU_DB_PATH=ushu.sqlite3
set USHU_EVENT_TITLE=O'ZBEKISTON USHU FEDERATSIYASI
set USHU_EVENT_SUBTITLE=O'RTA OSIYO CHEMPIONATI
REM -------------------------------------------------------------------------

call bin\ushu.bat eval "Ushu.Release.migrate()"
call bin\ushu.bat start
```

Никакого waitress: Phoenix-endpoint (Bandit/Cowboy) — сам себе продакшн-сервер.
В Django нам был нужен внешний WSGI-сервер с пулом потоков (16 штук, чтобы
SSE-стримы монитора не съели всё); BEAM даёт лёгкие процессы из коробки —
десять клиентов с LiveView-сокетами для него неразличимо мало.

### 5. SQLite из Elixir: `exqlite`, WAL и правильный бэкап

Стек работы с БД трёхслойный, как JPA-стек в Spring:

| Spring | Elixir |
|---|---|
| JDBC-драйвер | `exqlite` — низкоуровневый драйвер SQLite (NIF) |
| Hibernate/JPA | `Ecto` — schemas, changesets, запросы |
| диалект | `ecto_sqlite3` — адаптер Ecto поверх exqlite |

Приложение говорит с базой через Ecto (`Ushu.Repo`). Но импортёру нужен
доступ к ЧУЖОЙ базе (Django-файлу) с двумя десятками таблиц, для которых у
нас нет и не будет Ecto-схем. Городить schemaless-запросы через второй Repo —
церемония без пользы; мы спускаемся на уровень драйвера (решение D1):

```elixir
{:ok, conn} = Exqlite.Sqlite3.open("/path/to/django-copy.sqlite3", mode: :readonly)

{:ok, stmt} =
  Exqlite.Sqlite3.prepare(conn, """
  SELECT id, username, is_superuser, is_staff, is_active, category
  FROM judges_user ORDER BY id
  """)

rows = fetch_all(conn, stmt)   # цикл по Exqlite.Sqlite3.step/2

defp fetch_all(conn, stmt, acc \\ []) do
  case Exqlite.Sqlite3.step(conn, stmt) do
    {:row, row} -> fetch_all(conn, stmt, [row | acc])
    :done       -> Enum.reverse(acc)
  end
end
```

`mode: :readonly` — это гарантия уровня соединения: импортёр физически не
может изменить исходный файл. JDBC-аналог: `readOnly=true` в connection string.

**WAL-режим** ты уже знаешь по Django-версии (DEPLOY.md): живая база — это
ТРИ файла (`.sqlite3`, `-wal`, `-shm`). Скопировать один основной файл при
работающем сервере — получить снимок без закоммиченных данных из WAL.
Правильных пути два:

1. Сервер остановлен → копируй все три файла вместе (или после
   `PRAGMA wal_checkpoint(TRUNCATE)` достаточно основного).
2. Сервер работает → `VACUUM INTO 'backups/ushu-....sqlite3'` — штатный
   онлайн-снапшот SQLite: один самодостаточный файл, консистентный, без
   остановки сервера. Именно это делает `Ushu.Release.backup/0` и
   `backup-ushu.bat` — двойной клик, файл с таймстампом, надпись с именем.

### 6. Дисциплина миграции данных: проверяй, а не верь

Главный урок слоя — методологический. Перелив данных «вроде прошёл без
ошибок» — это ничего. INSERT'ы без исключений не доказывают, что маппинг
верен: перепутанные enum-значения, потерянный порядок sortedm2m, съехавший
на единицу индекс — всё это вставляется молча и стреляет на живом турнире.

Поэтому проверка — не отдельная задача «на потом», а **часть импорта, внутри
той же транзакции, fail-closed** (решение D6). Три яруса:

1. **Счётчики.** Для каждой пары таблиц — точное равенство количества строк,
   включая производные формулы для расплющенных таблиц (число `score_marks`
   равно числу достижимых `elementstatus`-связей и т.п.).
2. **Контрольные суммы.** Σ `finalscore`, Σ `b_score`, участники по табло,
   сохранённые карточки по судьям — дёшево и ловит «строки есть, значения не те».
3. **Семантический пересчёт** — самый сильный ярус: для КАЖДОГО завершённого
   выступления собираем вход из уже импортированных строк, прогоняем через
   чистое ядро `Ushu.Scoring` (слой 02) и сравниваем с `finalscore`,
   сохранённым Django. 225 реальных выступлений — это одновременно 225
   бесплатных интеграционных тестов скорингового ядра на живых данных.
   Расхождение больше 0.01 — откат и ненулевой exit-код. До 0.01 — предупреждение
   (легаси-строки, посчитанные до исправления округления в stabilize-django),
   которое пропускается только явным флагом `--allow-score-drift`.

Плюс два защитных механизма:

- `--dry-run`: полный импорт + вся верификация + печать отчёта, затем
  принудительный rollback. База остаётся пустой, отчёт — на руках. Аналог
  `flyway validate` + прогон на копии, только одним движением.
- Отказ работать с непустой целевой базой: никакого «дольём поверх» —
  пересоздай (`mix ecto.drop && mix ecto.create && mix ecto.migrate`) и
  импортируй заново. Импорт обязан быть воспроизводимым с нуля.

И организационное правило: импортёр НИКОГДА не читает живой Django-файл —
только чекпоинтнутую копию. Read-only соединение защищает от записи, но не
от чтения торн-снапшота при работающем Django.

### 7. Паттерн-матчинг как инструмент маппинга

Маппинги enum'ов — идеальная витрина паттерн-матчинга. В Kotlin ты бы написал
`when (age) { 4 -> Y7_8 ... else -> throw ... }`. В Elixir ветки — это клаузы
функции, а «else -> throw» не нужен: отсутствие подходящей клаузы — уже
`FunctionClauseError`, который откатит транзакцию:

```elixir
# Django-int возраста → типизированный бакет (см. таблицу соответствий ниже)
defp map_age(4), do: :y7_8
defp map_age(0), do: :y9_10
defp map_age(5), do: :y11
defp map_age(1), do: :y12_14
defp map_age(2), do: :y15_17
defp map_age(3), do: :adult
# НЕТ catch-all клаузы — незнакомый возраст обязан уронить импорт,
# а не «угадаться» в какой-нибудь бакет.

# state=2 + finalscore=0 — легаси-сентинель неявки
defp map_state(2, +0.0), do: :no_show
defp map_state(0, _),    do: :waiting
defp map_state(1, _),    do: :performing
defp map_state(2, _),    do: :finished

defp map_role(1, _staff, _cat), do: {:admin, nil}        # is_superuser
defp map_role(0, 1, _cat),      do: {:main_judge, nil}   # is_staff
defp map_role(0, 0, 0),         do: {:judge, :a}
defp map_role(0, 0, 1),         do: {:judge, :b}
defp map_role(0, 0, 2),         do: {:judge, :c}

defp map_kind(n) when n in 1..79,  do: :a
defp map_kind(n) when n in 80..89, do: :b
defp map_kind(n) when n >= 90,     do: :shared

defp map_verdict(2), do: :pending
defp map_verdict(1), do: :performed
defp map_verdict(0), do: :failed
```

Такой код читается как таблица соответствий из спецификации — потому что он
ею и является. Каждая клауза покрывается doctest'ом, включая падающий случай.

Массовые вставки — через `Repo.insert_all/3` пачками (аналог JDBC batch
insert), с явными `id`. Одно исключение: пользователи вставляются через
changeset `Ushu.Accounts` — чтобы отработало хэширование пароля и валидации.

---

## Решения и почему (по design.md)

**D1. Источник читаем напрямую через exqlite, а не вторым Ecto-репо.**
Альтернатива — динамический `Ushu.ImportRepo` поверх Django-файла — давала бы
Ecto-синтаксис, но schemaless: Ecto-схем для Django-таблиц нет, а писать 20
одноразовых схем — церемония. Драйвер напрямую проще, а `mode: :readonly` даёт
железную гарантию неизменности источника.

**D2. Django-id сохраняются; сиквенсы поднимаются после вставки.**
С сохранёнными id все внешние ключи переносятся дословно — не нужна карта
трансляции id сквозь всё расплющивание join'ов. Номера участников на печатных
протоколах остаются сопоставимыми между системами. После вставки:
`UPDATE sqlite_sequence SET seq = MAX(id)` для таблиц с AUTOINCREMENT (Django
их так создаёт; Ecto-таблицы на rowid продолжают с max сами — поднятие там
безвредно). Свежие id получают только синтезированные строки: `score_marks`,
`score_errors`, `combination_elements`.

**D3. Маппинги — тотальные функции без catch-all.**
Смотри код выше. Философия: неожиданное значение в источнике — это вопрос к
человеку, а не повод для «умного» дефолта. Единственный дефолт по правилу
предметной области — `format`: всё, что не `group`/`duilian`, — `:individual`.
Отдельно: коды 701/702 («70A»/«70B») попадают в `:shared` по правилу `>= 90` —
это в точности повторяет поведение Django (их принимали и A-, и B-формы).
Захочется перенести их в `:a` — это правка в админке после импорта, не
спецслучай импортёра.

**D4. Позиционные sortedm2m-цепочки расплющиваются в `score_marks`.**
В Django порядок `zip(*statuses_per_judge)` в `calculateC` держался на
`sort_value` двух join-таблиц — знаменитая «позиционная магия». Импортёр
вычитывает цепочку `score_cclass → combinationstatus → statuses → elementstatus`
с `ORDER BY sc.sort_value, ss.sort_value` и пишет явную колонку `position`
(0-based, сквозная по карточке). Обёртки `WrapperErrorCode` /
`CombinationStatus` / `ElementStatus` при этом исчезают как сущности — они
были артефактами ORM, а не предметной области. `score_events` НЕ бэкфилится:
выдуманные «кто/когда» отравили бы доверие к аудиту; журнал начинается с
переключения.

**D5. Пароли не переносятся.**
Django-хэши pbkdf2 бесполезны вне Django-схемы хэширования, а политика и так —
сброс паролей на каждый турнир. Импортёр генерирует временный пароль каждому
активному пользователю (8 символов, алфавит без 0/O/1/l, через
`:crypto.strong_rand_bytes`), хэширует его штатным changeset'ом и пишет CSV
`username,temporary_password` для главного судьи. Альтернатива — реализовать
Django-верификатор pbkdf2 в Elixir для «прозрачного» первого входа — отвергнута:
реальная работа и постоянная криптоповерхность ради 12 пользователей и
одноразового события.

**D6. Верификация — внутри импорта, fail-closed.** Разобрано в концепции 6.
Ключевой довод против отдельной `mix ushu.verify`: проверку, которую можно
забыть запустить, в день переключения забудут запустить.

**D7. Релиз собирается на Windows.** ERTS платформенный, кросс-сборки нет.
Альтернативы (Burrito, Docker, кросс-контейнеры) — экзотика ради единственной
известной целевой машины; отвергнуты.

**D8. Обслуживание через `Ushu.Release`, бэкап через `VACUUM INTO`.**
В релизе нет Mix — миграции и бэкап обязаны быть вызываемы через
`bin\ushu.bat eval`. `VACUUM INTO` — штатный онлайн-снапшот SQLite, безопасный
под WAL при живом сервере. Ставить на ноутбук `sqlite3.exe` ради бэкапа —
лишняя зависимость, когда релиз умеет сам.

**D9. Порт 8081 и имена `USHU_*` сохраняются.** Десять клиентских машин и
мышечная память оператора дороже красивого нового порта. На сухом прогоне
Elixir живёт на 4000 рядом с Django на 8081; в день переключения занимает 8081.

**D10. Ядро импорта — обычный модуль.** `mix ushu.import` для дев-машины,
`Ushu.Release.import/2` для ноутбука — одна и та же логика `Ushu.Import`.

**Про откат (capability `cutover-runbook`).** Ничто в этом слое не трогает
Django-дерево, его venv и его базу: импортёр читает копию, релиз ставится
рядом. Откат = остановить релиз, дважды кликнуть старый `start.bat`. Честно
проговорённая цена: данные, введённые в Elixir после переключения, в Django
не возвращаются — поэтому на первом живом турнире секретарь печатает протокол
и жмёт `backup-ushu.bat` после каждого закрытого табло. Django удаляется с
ноутбука только после первого полностью чистого турнира на Elixir.

---

## Как это соотносится с Django-версией

| Django (было) | Elixir (стало) |
|---|---|
| `judges_user.is_superuser=1` | `users.role = :admin`, `category = nil` |
| `judges_user.is_staff=1` (не superuser) | `users.role = :main_judge`, `category = nil` |
| остальные `judges_user` + `category` 0/1/2 | `users.role = :judge`, `category :a/:b/:c` |
| `judges_user.password` (pbkdf2) | НЕ переносится → временные пароли + CSV |
| `is_active` | `users.active` |
| возраст int 4/0/5/1/2/3 | enum `:y7_8/:y9_10/:y11/:y12_14/:y15_17/:adult` |
| `participation.state` 0/1/2 | `:waiting/:performing/:finished` |
| `state=2 AND finalscore=0` (сентинель) | `state = :no_show` |
| имя категории `'group'`/`'duilian'` в коде | `element_categories.format` enum |
| диапазоны номеров ошибок 1–79/80–89/90+ | `error_codes.kind = :a/:b/:shared` |
| `score.bclass` | `scores.b_score` |
| `score_aclass`/`score_berrors` → `WrapperErrorCode` | строки `score_errors` (дубликаты — отдельные строки) |
| `score_cclass(sort_value)` → `CombinationStatus` → `statuses(sort_value)` → `ElementStatus.done` | строки `score_marks(score_id, element_id, position, verdict)` |
| `ElementStatus.done` 2/1/0 | `verdict :pending/:performed/:failed` |
| `elements_combination_elements.sort_value` | `combination_elements.position` |
| `django_session`, `admin_log`, `auth_group`, `content_type`, `django_migrations` | не переносятся |
| `showme*.html`, `file.count` | не переносятся (артефакты снесённого файлового pub/sub) |
| `media/countries/*.png` | копируются в media-каталог Elixir, пути в `countries.image` сохранены |
| `manage.py migrate` в `start.bat` | `Ushu.Release.migrate()` в `start-ushu.bat` |
| venv + waitress-serve, 16 потоков | `mix release`: ERTS в комплекте, встроенный HTTP-сервер |
| `start.bat` (`set USHU_*`) | `start-ushu.bat` — тот же блок переменных, тот же порт 8081 |
| бэкап: `wal_checkpoint(TRUNCATE)` + copy | `backup-ushu.bat` → `VACUUM INTO backups/ushu-<ts>.sqlite3` |
| аудита не было | `score_events` — пуст на момент импорта, пишется с переключения |

День переключения (7 шагов, шпаргалка): остановить Django → чекпоинт + копия
базы → импорт из копии → **КОНТРОЛЬНАЯ ТОЧКА: exit 0, все счётчики сошлись,
все финалы воспроизвелись — иначе назад на Django** → раздать временные пароли
из CSV, каждый ставит свой → запустить релиз на 8081 → smoke-тест по одной
станции каждой роли + монитор.

---

## Что почитать

- Mix-задачи: https://hexdocs.pm/mix/Mix.Task.html
- `mix release` (концепции, структура, eval): https://hexdocs.pm/mix/Mix.Tasks.Release.html
- Релизы в Phoenix (включая `Ushu.Release`-паттерн): https://hexdocs.pm/phoenix/releases.html
- Конфигурация и `runtime.exs`: https://hexdocs.pm/elixir/config-and-releases.html
- `Ecto.Migrator` (миграции без Mix): https://hexdocs.pm/ecto_sql/Ecto.Migrator.html
- exqlite (драйвер): https://hexdocs.pm/exqlite/Exqlite.html
- ecto_sqlite3 (адаптер): https://hexdocs.pm/ecto_sqlite3/Ecto.Adapters.SQLite3.html
- `Repo.insert_all`: https://hexdocs.pm/ecto/Ecto.Repo.html#c:insert_all/3
- SQLite WAL: https://www.sqlite.org/wal.html
- `VACUUM INTO`: https://www.sqlite.org/lang_vacuum.html#vacuuminto
- `OptionParser` (аргументы задач): https://hexdocs.pm/elixir/OptionParser.html
- Erlang/Elixir на Windows: https://www.erlang.org/downloads и https://elixir-lang.org/install.html#windows
