# Слой 01 — Фундамент: скелет Phoenix-проекта

Это первый из семи слоёв переписывания ushu с Django на Elixir/Phoenix.
Здесь ещё нет ни одной строчки предметной логики — ни судей, ни оценок, ни
табло. Зато здесь принимаются и фиксируются все «инфраструктурные» решения:
как устроен проект, откуда берётся конфигурация, как настроен SQLite, как
проверяется стиль кода, как запускаются тесты. Слои 02–07 будут только
**добавлять** код в этот скелет и никогда не будут пересматривать эти решения.

Артефакты слоя: `openspec/changes/elixir-01-foundation/` (proposal, specs,
design, tasks — на английском). Этот документ — учебный конспект к ним.

---

## Часть 1. Ключевые концепции Elixir/Phoenix в этом слое

### 1.1 BEAM и OTP: процессы вместо потоков

Elixir компилируется в байткод виртуальной машины **BEAM** (та же VM, на
которой работает Erlang — телеком-система с сорокалетней историей). Главное,
что нужно перестроить в голове после JVM:

**В JVM (Kotlin/Spring):** поток — дорогой ресурс ОС (~1 МБ стека), поэтому
мы их переиспользуем через пулы, а состояние делим между потоками через
`synchronized`, `ConcurrentHashMap`, `AtomicReference`. Корутины Kotlin
облегчают ситуацию, но память всё равно общая — гонки данных возможны.

**В BEAM:** процесс — это структура самой VM, а не ОС. Он занимает ~2–3 КБ,
создаётся за микросекунды, и их спокойно бывают **миллионы**. Ключевое отличие:

- у каждого процесса **своя изолированная память** (куча + стек);
- **общей памяти нет вообще** — процессы общаются только сообщениями
  (копия данных кладётся в почтовый ящик получателя);
- каждый процесс — отдельный сборщик мусора: GC одного процесса не
  останавливает остальные (нет «stop the world»);
- падение процесса **не роняет** ни VM, ни другие процессы.

```elixir
# создать процесс — так же дёшево, как создать объект в JVM
pid = spawn(fn -> IO.puts("привет из процесса #{inspect(self())}") end)

# послать сообщение (асинхронно, неблокирующе)
send(pid, {:score_saved, 42})

# принять сообщение (внутри процесса-получателя)
receive do
  {:score_saved, id} -> IO.puts("оценка #{id} сохранена")
end
```

Ближайшая аналогия из мира Kotlin — акторы (`kotlinx.coroutines.actor` или
Akka), но там это библиотека поверх общей памяти, а здесь — фундамент самой VM.

Почему это важно именно для ushu: каждое подключение судьи (LiveView-сокет),
каждый HTTP-запрос, `MonitorBoard` (слой 05) — это отдельные процессы. Если
у одного судьи что-то упало, остальные девять и проектор этого даже не заметят.

**OTP** — это стандартная библиотека поверх процессов: проверенные «шаблоны
поведения» (behaviours). Два, которые встретятся сразу:

- `GenServer` — процесс-«сервер» с состоянием и обработчиками сообщений
  (грубая аналогия — Spring-бин c `@Async`-очередью и внутренним состоянием,
  но без единой общей переменной);
- `Supervisor` — процесс, который следит за другими и **перезапускает** их
  при падении (об этом ниже).

### 1.2 mix — как Gradle, но проще

`mix` — сборщик, менеджер зависимостей и раннер задач в одном. Соответствия:

| Gradle / Kotlin                     | mix / Elixir                          |
|-------------------------------------|---------------------------------------|
| `build.gradle.kts`                  | `mix.exs`                              |
| Maven Central                       | Hex (hex.pm)                           |
| `gradle.lockfile`                   | `mix.lock` (создаётся всегда, коммитится) |
| `./gradlew build`                   | `mix compile`                          |
| `./gradlew test`                    | `mix test`                             |
| `./gradlew bootRun`                 | `mix phx.server`                       |
| задачи/плагины Gradle               | `mix`-задачи (свои пишутся в 20 строк) |
| профили/`bootJar`                   | `MIX_ENV=prod mix release` (слой 07)   |

`mix.exs` — это обычный Elixir-модуль, никакого отдельного DSL:

```elixir
defmodule Ushu.MixProject do
  use Mix.Project

  def project do
    [
      app: :ushu,
      version: "0.1.0",
      elixir: "~> 1.17",
      deps: deps()
    ]
  end

  # аналог блока dependencies {} в build.gradle.kts
  defp deps do
    [
      {:phoenix, "~> 1.8.9"},
      {:phoenix_live_view, "~> 1.2.0"},
      {:ecto_sql, "~> 3.13"},
      {:ecto_sqlite3, "~> 0.18"},          # драйвер SQLite (вместо postgrex)
      {:gettext, "~> 1.0"},
      {:bandit, "~> 1.5"},                 # HTTP-сервер (чистый Elixir)
      {:credo, "~> 1.7", only: [:dev, :test], runtime: false}
    ]
  end
end
```

> Что реально встало при генерации (июль 2026): тулчейн **Elixir 1.19.5 / OTP 28**
> (зафиксирован в `.tool-versions`), генератор `phx_new 1.8.9`, `gettext 1.0`
> (в проекте изначальный набросок называл `~> 0.26` — но 1.0 уже стал текущим
> мажором), `ecto_sql 3.14`, драйвер `exqlite 0.38`. `postgrex` не подтягивается
> вовсе (он остаётся лишь опциональной транзитивной ссылкой у `ecto_sql`).

`~> 1.8` читается как «1.8 или новее, но меньше 2.0» — то же, что
`[1.8, 2.0)` в Maven. `only: [:dev, :test]` — аналог `testImplementation`.

Важное отличие от Django-мира: вместо `requirements.txt` (плоский список без
транзитивной фиксации) здесь пара `mix.exs` (декларация) + `mix.lock`
(точная фиксация всего дерева) — как `build.gradle.kts` + lockfile.

### 1.3 Дерево супервизии: «let it crash»

В Spring контейнер один раз собирает граф бинов при старте; если бин упал в
рантайме — это просто исключение, стек которого улетает наверх. В OTP
процессы собраны в **дерево**, и у каждого узла есть родитель-супервизор,
который знает, что делать при падении ребёнка: **перезапустить его в чистом
начальном состоянии**.

Наше дерево после этого слоя (файл `lib/ushu/application.ex`):

```elixir
defmodule Ushu.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      UshuWeb.Telemetry,                     # метрики
      Ushu.Repo,                             # пул соединений с SQLite
      {Phoenix.PubSub, name: Ushu.PubSub},   # шина событий (слой 05 будет её использовать)
      UshuWeb.Endpoint                       # HTTP/WebSocket вход
    ]

    opts = [strategy: :one_for_one, name: Ushu.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
```

`strategy: :one_for_one` — «упал ребёнок → перезапусти только его».
Философия называется *let it crash*: вместо оборачивания всего в try/catch
мы пишем счастливый путь, а от редких сбоев защищает супервизор — процесс
перезапускается в заведомо корректном состоянии. Для соревнования это
означает: даже если `MonitorBoard` (слой 05) упадёт из-за бага, через
миллисекунды он поднимется заново и пересоберёт снапшот из базы — потому что
**источник истины — база**, а не память процесса.

Сравнение, которое помогает: Spring-контекст — это «собрали граф один раз и
молимся»; дерево супервизии — это «граф живой, любой узел можно убить, и он
восстановится». Kubernetes перезапускает поды — BEAM делает то же самое с
процессами внутри одной VM, за микросекунды.

### 1.4 Конфигурация: compile-time против runtime

Самые частые грабли новичка в Elixir. В проекте четыре файла + один особый:

```
config/config.exs    — общий, читается ПРИ КОМПИЛЯЦИИ
config/dev.exs       — дополняет config.exs для dev (компиляция)
config/test.exs      — для тестов (компиляция)
config/prod.exs      — для prod (компиляция)
config/runtime.exs   — читается ПРИ КАЖДОМ СТАРТЕ приложения ← env-переменные ЗДЕСЬ
```

Грабли: если прочитать `System.get_env("USHU_PORT")` в `prod.exs`, значение
**запечётся в скомпилированный релиз** на машине сборки, и на ноутбуке
организатора переменная окружения ничего не изменит. Поэтому правило (D7 в
design.md): **всё, что может отличаться у двух запусков одного и того же
бинарника, живёт только в `runtime.exs`**.

```elixir
# config/runtime.exs — выполняется при старте, env-переменные работают
import Config

if config_env() == :prod do
  secret =
    System.get_env("USHU_SECRET_KEY_BASE") ||
      raise "переменная USHU_SECRET_KEY_BASE не задана — задайте её в лаунчере"

  config :ushu, UshuWeb.Endpoint,
    http: [ip: {0, 0, 0, 0}, port: String.to_integer(System.get_env("USHU_PORT") || "8081")],
    secret_key_base: secret
end

# брендинг турнира — читается слоем 06 для шапки монитора и протоколов
config :ushu, :event,
  title: System.get_env("USHU_EVENT_TITLE") || "O'ZBEKISTON USHU FEDERATSIYASI",
  subtitle: System.get_env("USHU_EVENT_SUBTITLE") || "O'RTA OSIYO CHEMPIONATI"
```

Параллели: `config/*.exs` ≈ `application.yml` c профилями Spring, но с
подвохом компиляции, которого в Spring нет; `runtime.exs` ≈
`application.yml` + `${ENV_VAR}`-подстановки. В Django всё было в одном
`settings.py`, который выполнялся при каждом старте — то есть Django-вариант
ближе всего именно к `runtime.exs`.

Имена переменных сохранены из Django-версии: `USHU_PORT`, `USHU_EVENT_TITLE`,
`USHU_EVENT_SUBTITLE`; секрет называется `USHU_SECRET_KEY_BASE` (так Phoenix
называет ключ для подписи сессий/куки — аналог `SECRET_KEY` в Django).

### 1.5 Структура проекта: где что лежит

```
elixir/
├── mix.exs                  # ≈ build.gradle.kts
├── mix.lock                 # лок-файл зависимостей (коммитится)
├── .formatter.exs           # настройки mix format
├── .credo.exs               # настройки линтера Credo
├── .tool-versions           # версии Elixir/OTP (asdf/mise) ≈ jvmToolchain(17)
├── config/                  # см. раздел 1.4
├── lib/
│   ├── ushu/                # ДОМЕННЫЙ слой: Ushu.* — контексты, схемы, чистая логика
│   │   ├── application.ex   #   дерево супервизии
│   │   └── repo.ex          #   Ushu.Repo — доступ к БД (≈ EntityManager+DataSource)
│   ├── ushu_web/            # ВЕБ-слой: UshuWeb.* — то, что видит браузер
│   │   ├── endpoint.ex      #   вход HTTP/WebSocket (≈ DispatcherServlet + middleware)
│   │   ├── router.ex        #   маршруты (≈ urls.py / @RequestMapping)
│   │   ├── telemetry.ex     #   метрики
│   │   └── components/      #   переиспользуемые куски HEEx-разметки
│   ├── ushu.ex
│   └── ushu_web.ex
├── priv/
│   ├── repo/migrations/     # миграции Ecto (≈ Liquibase changelogs / Django migrations)
│   ├── gettext/             # переводы ru/en (≈ locale/*.po в Django — формат тот же!)
│   └── static/              # собранная статика
├── assets/                  # исходники JS/CSS (esbuild + tailwind, всё офлайн)
└── test/
    ├── support/             # DataCase, ConnCase — базовые модули тестов
    └── ...
```

Железное правило слоя: код в `lib/ushu/` **не имеет права** ссылаться на
`UshuWeb.*`. Домен не знает про веб — как сервисный слой в Spring не знает
про контроллеры. В Django это правило было размыто (модели импортировались
где угодно, а `models.py` знал про формат отображения) — здесь оно
закрепляется спецификацией и проверкой в тестах.

Django-приложения (`tablo`, `judges`, `participants`, `clubs`, `elements`)
здесь превратятся не в каталоги с моделями+вьюхами, а в **контексты** —
модули с публичным API (`Ushu.Catalog`, `Ushu.Roster`, `Ushu.Competition`,
слой 04). Контекст ≈ сервисный слой Spring: снаружи зовут только его функции,
а схемы БД — деталь реализации.

### 1.6 SQLite в Ecto: WAL и busy_timeout

`Ushu.Repo` — модуль доступа к БД (адаптер `ecto_sqlite3`). Конфигурация:

```elixir
config :ushu, Ushu.Repo,
  database: db_path,           # из USHU_DB_PATH
  journal_mode: :wal,          # readers не блокируются writer-ом
  busy_timeout: 20_000,        # ждать блокировку 20 с, а не падать
  pool_size: 5                 # SQLite: один писатель, пул маленький
```

Это прямой перенос выстраданных правил из стабилизации Django
(`stabilize-django/specs/lan-deployment`): два судьи нажали «отправить»
одновременно → второй **ждёт** блокировку, а не получает
`database is locked`. В Django этот таймаут однажды был настроен, но не
применён (опция лежала не в том ключе словаря) — поэтому в слое есть
регрессионный тест, который открывает живое соединение и проверяет прагмы.

**Живой урок из реализации.** Тест проверяет `PRAGMA journal_mode` (`= "wal"`)
и `PRAGMA foreign_keys` (`= 1`) прямо на соединении. А вот `busy_timeout`
**прочитать прагмой нельзя**: драйвер `exqlite` ставит таймаут своим
собственным NIF-обработчиком занятости и **намеренно избегает**
`PRAGMA busy_timeout` — потому что эта прагма внутри вызывает
`sqlite3_busy_timeout()`, который снёс бы кастомный обработчик (см. комментарий
в `deps/exqlite/lib/exqlite/connection.ex`). Поэтому `PRAGMA busy_timeout`
всегда возвращает `0`, даже когда таймаут работает. Вывод: проверять надо не
слепо «как в спеке написано», а то, что реально отражает механизм. Для
`busy_timeout` регрессия сторожит **значение в конфиге Repo** (та самая
«опция не в том ключе», от которой пострадал Django), а не бесполезное
показание прагмы.

Отдельно: в SQLite внешние ключи по умолчанию **выключены** — включаем
опцией `foreign_keys: :on` (это атом `:on`/`:off`, а не булево — ещё одна
мелочь, которую проверяешь в исходнике драйвера, а не угадываешь). В
Postgres/H2 такой подлянки нет, помните об этом.

### 1.7 mix format и Credo

- `mix format` — встроенный форматтер, без настроек «на вкус» (как gofmt;
  ktlint — ближайший аналог). Проверка: `mix format --check-formatted`.
- **Credo** — статический анализатор (аналог detekt): сложность, дубли,
  соглашения. Запуск: `mix credo --strict`.

Оба — обязательные «ворота» для всех следующих слоёв: дерево всегда
отформатировано и без замечаний Credo.

### 1.8 gettext: ru по умолчанию, en запасной

Phoenix использует GNU gettext — **тот же формат `.po`-файлов, что и Django**
(каталог `locale/` в Django-проекте). Переводы переносятся почти механически.

```elixir
# config/config.exs — компайл-тайм (какие локали вшить и что по умолчанию)
config :ushu, UshuWeb.Gettext, default_locale: "ru", allowed_locales: ~w(ru en)
```

> Тонкость из реализации: опция называется `allowed_locales`, а не `locales`
> (в первоначальном наброске задачи было `locales` — такого ключа у gettext
> нет). Проверяется это в исходнике `deps/gettext` — ровно тот принцип
> «сверься с драйвером, не выдумывай имя символа», что и с прагмами выше.

```elixir
use Gettext, backend: UshuWeb.Gettext

gettext("Waiting for performance")      # → "Ожидание выступления" при locale=ru
```

Файлы лежат в `priv/gettext/ru/LC_MESSAGES/*.po`. Отдельный каталог
`errors.po` переводит сообщения валидации Ecto («can't be blank» → «не может
быть пустым») — один раз здесь, и все будущие changeset-ошибки слоёв 03–04
автоматически показываются по-русски. Переключение языка на пользователя
(сессия/кнопка) — задача слоя 06; фундамент лишь гарантирует механизм
(`Gettext.put_locale/2`).

Сюда же относится закреплённое решение по горячим клавишам судьи C: в слое 06
они будут читаться по `event.code` (физическая клавиша), а не по символу —
чтобы русская раскладка не ломала управление. К фундаменту это не относится,
но причина, почему i18n продуман с первого слоя, — именно эта.

### 1.9 ExUnit: скелет тестов

ExUnit — встроенный тестовый фреймворк (≈ JUnit 5):

```elixir
defmodule Ushu.ConfigTest do
  use ExUnit.Case, async: true    # тесты модуля идут параллельно (в своих процессах!)

  test "брендинг по умолчанию совпадает с Django-версией" do
    assert Application.get_env(:ushu, :event)[:title] ==
             "O'ZBEKISTON USHU FEDERATSIYASI"
  end
end
```

Генератор создаёт `test/support/data_case.ex` и `conn_case.ex` — базовые
модули (≈ `@SpringBootTest`-конфигурации): `DataCase` даёт песочницу БД
(каждый тест в транзакции, откат в конце — как `@Transactional` на тестах в
Spring), `ConnCase` — тестовые HTTP-запросы. `mix test` обязан быть зелёным
на свежем клоне без каких-либо env-переменных.

---

## Часть 2. Решения и почему (конспект design.md)

**D1. Подкаталог `elixir/` в этом же репозитории.** Django-версия продолжает
судить соревнования до слоя 07; в одном репо импортёр и спецификации могут
ссылаться друг на друга, история одна. Отдельный репозиторий дал бы только
церемонии.

**D2. `mix phx.new ushu --database sqlite3 --no-mailer`, dashboard оставляем.**
Почтовик убран: авторизация — логин+пароль в офлайн-сети, писем нет вообще.
LiveDashboard оставлен: он работает офлайн, в проде может быть закрыт, а для
изучения OTP это лучший инструмент — живое дерево супервизии, процессы и
метрики прямо в браузере на том же ноутбуке.

**D3. SQLite, а не Postgres.** Один ноутбук, ноль администрирования, бэкап —
копирование файла, импорт из Django-базы (тоже SQLite) с сохранением
целочисленных id — тривиален. Postgres — это сервис, который надо ставить,
запускать и мониторить на «боевом» Windows-ноутбуке ради нагрузки в десять
человек. Не окупается. Вернуться к вопросу — только если появится
мультиковёр (вне рамок переписывания).

**D4. Прагмы прибиты явно + регрессионный тест.** Потому что в Django
аналогичная настройка однажды молча не применилась. Доверяй, но проверяй
`PRAGMA`-ми.

**D5. Один OTP-app, без umbrella.** Umbrella (аналог многомодульного Gradle)
решает проблему независимых релизов — у нас релиз один. Модульность дают
контексты.

**D6. Env-контракт `USHU_*` как в Django.** Оператор уже знает эти имена;
`start.bat` меняется минимально. Prod без секрета не стартует — падает на
этапе конфигурации с понятной ошибкой, а не работает с ключом по умолчанию.

**D7. Компайл-тайм и рантайм строго разделены.** Правило одной строкой: может
отличаться у двух запусков одного бинарника → только `runtime.exs`.

**D8. `check_origin: false`, слушаем `0.0.0.0`.** Клиенты приходят по любому
LAN-IP, который ноутбук получил от роутера. Проверка origin в изолированной
сети не защищает ни от чего, а вот воспроизвести Django-шный `DisallowedHost`
на турнире может легко. Порт по умолчанию — 8081, как в Django (при
параллельном запуске обоих серверов Elixir-версии задаём `USHU_PORT=8082`).
Конкретное действие при реализации: из сгенерированного `config/prod.exs`
**удалён `force_ssl`** — генератор Phoenix ставит его по умолчанию, но на
турнире он редиректил бы каждого судью на `https://` и убил бы весь ивент
(TLS-терминатора нет, сеть офлайновая, всё по чистому HTTP). При render-walk
это подтверждено: `GET /` отдаёт `200` и на `localhost:8081`, и на LAN-IP
`192.168.0.149:8081`, без единой внешней ссылки в HTML.

**D9. format + Credo сейчас, Dialyzer потом.** Dialyzer (аналог строгой
статической проверки типов) полезен, но долго строит кэш и шумит — плохой
спутник на этапе обучения. Вернёмся после слоя 04.

**D10. HTTP-сервер Bandit.** Дефолт Phoenix 1.8, чистый Elixir, нет
C-зависимостей, которые пришлось бы собирать под Windows.

---

## Часть 3. Как это соотносится с Django-версией

| Django (сейчас)                                  | Elixir/Phoenix (этот слой)                                  |
|--------------------------------------------------|--------------------------------------------------------------|
| `manage.py` + команды                             | `mix` + задачи (`mix phx.server`, `mix test`, свои mix-таски) |
| `requirements.txt`                                | `mix.exs` (декларация) + `mix.lock` (фиксация)                |
| `ushu/settings.py` (один файл, читается на старте)| `config/{config,dev,test,prod}.exs` (компиляция) + `runtime.exs` (старт) |
| `USHU_SECRET_KEY`                                 | `USHU_SECRET_KEY_BASE`                                        |
| `USHU_DEBUG=0/1`                                  | нет флага: окружение выбирается сборкой (`MIX_ENV=dev/prod`)  |
| `USHU_ALLOWED_HOSTS` + `DisallowedHost`           | не нужно: `check_origin: false` в офлайн-LAN (D8)             |
| `USHU_EVENT_TITLE` / `USHU_EVENT_SUBTITLE`        | те же имена → `Application.get_env(:ushu, :event)`            |
| WSGI + runserver/waitress                         | Bandit внутри `UshuWeb.Endpoint` (процесс в дереве супервизии)|
| `urls.py`                                         | `lib/ushu_web/router.ex`                                      |
| Django-приложения (`tablo`, `judges`, …)          | контексты `Ushu.*` (появятся в слое 04)                       |
| ORM + `migrations/`                               | Ecto + `priv/repo/migrations/` (слой 03)                      |
| `OPTIONS={'timeout': 20}` + WAL в `settings.py`   | `journal_mode: :wal, busy_timeout: 20_000` в конфиге Repo + тест на PRAGMA |
| `locale/*.po`                                     | `priv/gettext/*/LC_MESSAGES/*.po` — тот же формат gettext     |
| `python manage.py test`                           | `mix test` (песочница БД на каждый тест)                      |
| нет форматтера/линтера                            | `mix format` + `mix credo --strict` как обязательные ворота   |
| `start.bat` задаёт env и запускает runserver      | тот же принцип; сам лаунчер и `mix release` — слой 07         |

Чего в этом слое **нет** нарочно: аутентификации (слои 03–04), схем БД (03),
чистого ядра подсчёта (02), PubSub-топиков и `MonitorBoard` (05), экранов
(06), импорта и релиза (07).

---

## Часть 4. Что почитать

Официальная документация (вся — hexdocs.pm, работает и офлайн через
`mix hex.docs fetch`):

- Введение в Elixir: https://hexdocs.pm/elixir/introduction.html — особенно
  главы про pattern matching, процессы и модули.
- Процессы и OTP «с нуля»: https://hexdocs.pm/elixir/processes.html и
  https://hexdocs.pm/elixir/genservers.html
- Супервизоры и Application: https://hexdocs.pm/elixir/supervisor-and-application.html
- Mix: https://hexdocs.pm/mix/Mix.html и `mix help` в терминале.
- Конфигурация (compile vs runtime): https://hexdocs.pm/elixir/Config.html и
  https://hexdocs.pm/mix/Mix.Tasks.Release.html#module-runtime-configuration
- Phoenix, обзор каталогов: https://hexdocs.pm/phoenix/directory_structure.html
- Phoenix Endpoint/Router: https://hexdocs.pm/phoenix/routing.html
- Ecto + SQLite: https://hexdocs.pm/ecto_sqlite3/Ecto.Adapters.SQLite3.html —
  список всех прагм (`journal_mode`, `busy_timeout`, …).
- Gettext: https://hexdocs.pm/gettext/Gettext.html
- ExUnit: https://hexdocs.pm/ex_unit/ExUnit.html
- Credo: https://hexdocs.pm/credo/overview.html
- Книга, если захочется системно: «Elixir in Action» (Saša Jurić) — лучшее
  объяснение BEAM/OTP для людей с JVM-бэкграундом.

Следующий слой — `elixir-02-scoring-core`: чистое ядро подсчёта очков
(`Ushu.Scoring`) без единого обращения к базе, с перенесёнными «золотыми»
числовыми тестами из Django. Там же познакомимся со структурами, pattern
matching в полную силу и doctest-ами.
