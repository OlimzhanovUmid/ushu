# Слой 03 — Ecto: схемы, миграции, changeset'ы и ограничения

Это третий слой из семи в переписывании ushu на Elixir/Phoenix. Первый слой
(`elixir-01-foundation`) дал нам каркас Phoenix-проекта с SQLite, второй
(`elixir-02-scoring-core`) — чистую математику подсчёта очков без базы данных.
Теперь мы кладём фундамент данных: **все таблицы, все схемы, все ограничения
целостности**. Всё, что дальше построят слои 04 (бизнес-операции) и 07
(импорт из Django), будет опираться на решения этого слоя.

Почему это отдельный слой, а не «часть контекстов»? Потому что модель данных —
это контракт. Импортёр из Django-базы, чистое ядро подсчёта и LiveView-экраны
должны сойтись на одних и тех же именах таблиц, колонок и значений enum'ов.
Зафиксировав их здесь, мы делаем остальные слои независимыми друг от друга.

---

## Ключевые концепции Elixir/Phoenix в этом слое

### 1. Ecto — это НЕ ORM. Четыре независимых кирпича

Главный ментальный сдвиг после Django ORM и JPA/Hibernate: **Ecto не следит
за объектами**. Нет session, нет persistence context, нет dirty checking, нет
lazy loading, нет «сохранил объект — и связанные тоже сохранились». Ecto — это
четыре маленькие библиотеки, которые можно использовать даже по отдельности:

| Кирпич | Что делает | Аналог в Django | Аналог в Spring/JPA |
|---|---|---|---|
| `Ecto.Repo` | Единственная точка общения с БД: `Repo.insert/get/update/delete/all` | `Model.objects` + менеджер | `EntityManager` / Spring Data repository |
| `Ecto.Schema` | Описывает отображение строки таблицы в struct | `class Meta` + поля модели | `@Entity` + `@Column` |
| `Ecto.Changeset` | Приём внешних данных: cast → валидация → отчёт об ошибках | `ModelForm` / `full_clean()` | Bean Validation (`@Valid`) + DTO-маппинг |
| `Ecto.Query` | Композируемый DSL запросов | QuerySet | JPQL / Criteria API / QueryDSL |

Ключевое отличие: в Django `participant.save()` — метод на объекте, и объект
«знает», как себя сохранить. В Ecto struct — это просто данные (как Kotlin
`data class`), а сохраняет их **Repo**:

```elixir
# Django:  p = Participant(...); p.save()
# Kotlin:  participantRepository.save(p)
# Ecto:
%Participant{}
|> Participant.changeset(%{name_en: "Aliev T.", sex: :male, age: :y12_14, club_id: 3})
|> Repo.insert()
#=> {:ok, %Participant{id: 42, ...}}  либо  {:error, %Ecto.Changeset{...}}
```

Обратите внимание на возвращаемое значение: `{:ok, ...}` / `{:error, ...}` —
это идиома Elixir вместо исключений. Как `Result<T>` в Kotlin, только
встроенная в язык через pattern matching:

```elixir
case Repo.insert(changeset) do
  {:ok, participant} -> ...
  {:error, changeset} -> ...  # внутри changeset — список ошибок по полям
end
```

Ещё одно следствие «Ecto — не ORM»: **никакого lazy loading**. В JPA вы
привыкли, что `score.getJudge().getUsername()` может внезапно выстрелить
`LazyInitializationException` или незаметно сделать N+1 запросов. В Ecto
ассоциация, которую вы не загрузили явно, — это `%Ecto.Association.NotLoaded{}`,
и обращение к ней сразу и честно падает. Загрузка всегда явная:

```elixir
score = Repo.get!(Score, id) |> Repo.preload([:judge, participation: [:participant]])
score.judge.username  # работает, потому что мы явно сказали preload
```

Это дизайн-решение, а не недоработка: N+1 в Ecto невозможен «случайно» —
только если вы явно напишете цикл с запросами.

### 2. Ecto.Schema — struct плюс отображение

Схема выглядит так (это настоящий код этого слоя, слегка сокращённый):

```elixir
defmodule Ushu.Competition.Participation do
  use Ecto.Schema
  import Ecto.Changeset

  schema "participations" do
    field :draw_order, :integer, default: 0
    field :state, Ecto.Enum,
      values: [:waiting, :performing, :finished, :no_show],
      default: :waiting
    field :final_score_centi, :integer   # nil до финализации
    field :bonus, :boolean, default: false
    field :group_entry, :boolean, default: false

    belongs_to :participant, Ushu.Roster.Participant
    belongs_to :tablo, Ushu.Competition.Tablo
    has_many :scores, Ushu.Competition.Score

    timestamps()
  end
end
```

Параллели:

- `schema "participations" do ... end` ≈ Django `class Meta: db_table = ...` +
  объявления полей, или JPA `@Entity @Table(name = "participations")`.
- `belongs_to :tablo` ≈ Django `ForeignKey(Tablo)` ≈ JPA `@ManyToOne`. Ecto
  автоматически заводит поле `tablo_id`.
- `has_many :scores` ≈ Django reverse accessor `participation.score_set` ≈
  JPA `@OneToMany(mappedBy = ...)`. Это **только про чтение через preload** —
  каскады удаления мы объявим в миграции, на уровне БД (см. ниже, это важно).
- `timestamps()` добавляет `inserted_at`/`updated_at` — как
  `auto_now_add`/`auto_now` в Django или `@CreatedDate`/`@LastModifiedDate`
  в Spring Data, только без всякой магии аудита: Repo сам проставляет их при
  insert/update.

### 3. Ecto.Enum — типизированные значения вместо магических чисел

В Django-версии возраст был `IntegerField(choices=AGE_CHOICES)`, и константы
успели разъехаться с ярлыками: `AGE_9_11 = 0` показывался как `'9-10'`,
`AGE_7_8 = 4`, `AGE_11 = 5` — порядок чисел давно не соответствовал порядку
возрастов. Состояние `FINISHED` с `finalscore == 0` означало неявку. Категория
«группа» определялась сравнением имени с строкой `'group'`.

В Ecto каждое такое значение становится атомом из закрытого списка:

```elixir
field :age, Ecto.Enum, values: [:y7_8, :y9_10, :y11, :y12_14, :y15_17, :adult]
field :state, Ecto.Enum, values: [:waiting, :performing, :finished, :no_show]
field :format, Ecto.Enum, values: [:individual, :group, :duilian]  # у категории
field :kind, Ecto.Enum, values: [:a, :b, :shared]                  # у кода ошибки
```

В коде это атомы (`:performing` — как Kotlin `enum class` entry), а в базе —
читаемые строки `'performing'`. Попытка записать что-то вне списка делает
changeset невалидным ещё до запроса к БД. Неявка теперь — честное состояние
`:no_show`, а не сговор двух полей. Принадлежность кода ошибки судье A или B —
колонка `kind`, а не знание «номера 1–79 это A, 80–89 это B».

Сравните с JPA: `@Enumerated(EnumType.STRING)` — очень похоже, только Ecto
ещё и валидирует на входе, а мы дополнительно прибьём список CHECK-ограничением
в самой базе (об этом ниже).

### 4. Ecto.Changeset — валидация как конвейер данных

Changeset — самая непривычная и самая полезная часть Ecto. В Django валидация
размазана: часть в полях модели, часть в `clean()`, часть в формах, и
`Model.save()` вообще её не запускает, если не позвать `full_clean()`. В JPA —
Bean Validation аннотации плюс то, что вспомнили проверить в сервисе.

В Ecto это одна явная функция — конвейер преобразований над неизменяемой
структурой:

```elixir
def changeset(participation, attrs) do
  participation
  |> cast(attrs, [:draw_order, :state, :final_score_centi, :bonus,
                  :group_entry, :participant_id, :tablo_id])
  |> validate_required([:state, :participant_id, :tablo_id])
  |> validate_number(:draw_order, greater_than_or_equal_to: 0)
  |> unique_constraint([:participant_id, :tablo_id],
       name: :participations_participant_id_tablo_id_index)
  |> unique_constraint(:state, name: :one_performing_participation)
  |> foreign_key_constraint(:tablo_id)
end
```

Читается сверху вниз благодаря pipe-оператору `|>` (тот же дух, что цепочки
`let`/`also` в Kotlin, только это основной стиль языка):

1. `cast` — взять из внешних данных ТОЛЬКО перечисленные поля (защита от
   mass assignment; в Django для этого нужен `fields = [...]` в форме).
2. `validate_*` — проверки в памяти, без похода в БД.
3. `*_constraint` — регистрация ожиданий о том, что может отвергнуть база
   (подробно в следующем пункте — это главный паттерн слоя).

Changeset — это значение. Его можно вернуть из функции, посмотреть
`changeset.errors`, отдать в LiveView для подсветки полей. Никакого выброса
исключений в счастливом пути.

### 5. Валидация в changeset vs ограничения в БД — паттерн `unique_constraint`

Это центральная идея слоя, поэтому подробно.

Есть два класса проверок:

- **Проверки данных** (`validate_required`, `validate_number`,
  `validate_format`) — смотрят только на сами данные. Их можно сделать в
  памяти, они надёжны.
- **Проверки состояния мира** («нет ли уже такой регистрации?», «существует
  ли клуб с таким id?») — их в памяти сделать НЕЛЬЗЯ без гонки. Между вашим
  `SELECT ... EXISTS` и вашим `INSERT` другой процесс успеет вставить дубль.
  Django-версия ushu наступила ровно на эти грабли: двойной клик секретаря
  создавал две регистрации, пока в стабилизации не добавили
  `UniqueConstraint`.

Ecto решает это честно: единственный судья уникальности — **база данных**.
А `unique_constraint/3` в changeset — это не проверка, а **обещание красиво
обработать отказ БД**: если INSERT упадёт на уникальном индексе с этим именем,
Ecto превратит ошибку СУБД в обычную ошибку changeset'а на нужном поле, и
`Repo.insert` вернёт `{:error, changeset}` вместо исключения.

```elixir
# Два конкурентных запроса регистрируют одного участника в одно табло:
# оба проходят валидации в памяти, оба доходят до INSERT,
# один коммитится, второй получает:
{:error, changeset} = Repo.insert(dup)
changeset.errors
#=> [participant_id: {"has already been taken", [...]}]
```

Важная деталь: имя в `unique_constraint(..., name: ...)` должно **точно
совпадать** с именем индекса в миграции. Если промахнуться — вместо
`{:error, changeset}` прилетит исключение `Ecto.ConstraintError`. Поэтому в
задачах слоя есть отдельный тест, который для каждого именованного индекса
намеренно вызывает нарушение и проверяет, что оно приземляется в changeset.

Тот же паттерн работает для внешних ключей (`foreign_key_constraint`) и
CHECK-ограничений (`check_constraint`).

В JPA аналога этому паттерну по сути нет: там нарушение уникальности — это
`DataIntegrityViolationException` из глубины `flush()`, которую все ловят
как умеют. В Ecto отказ БД — штатная ветка happy-path кода.

### 6. Миграции — версионируемый DSL, как Liquibase, но кодом

Вы знаете Liquibase из мира Jmix/Spring. Ecto-миграции — та же идея
(упорядоченные, применяются один раз, журналируются в служебной таблице
`schema_migrations`), но пишутся на Elixir:

```elixir
defmodule Ushu.Repo.Migrations.CreateCompetition do
  use Ecto.Migration

  def change do
    create table(:tablos) do
      add :age, :text, null: false
      add :sex, :text, null: false
      add :element_category_id,
          references(:element_categories, on_delete: :delete_all), null: false
      add :started, :boolean, default: false, null: false
      timestamps()
    end

    create unique_index(:tablos, [:age, :sex, :element_category_id])

    create table(:participations) do
      add :participant_id, references(:participants, on_delete: :delete_all), null: false
      add :tablo_id, references(:tablos, on_delete: :delete_all), null: false
      add :draw_order, :integer, default: 0, null: false
      add :state, :text, default: "waiting", null: false
      add :final_score_centi, :integer
      add :bonus, :boolean, default: false, null: false
      add :group_entry, :boolean, default: false, null: false
      timestamps()
    end

    create unique_index(:participations, [:participant_id, :tablo_id])

    # Инвариант «на ковре максимум один спортсмен» — частичный уникальный индекс
    create unique_index(:participations, [:state],
             where: "state = 'performing'",
             name: :one_performing_participation)

    create constraint(:participations, :participations_state_check,
             check: "state IN ('waiting','performing','finished','no_show')")
  end
end
```

Отличия от Django-миграций: Django генерирует их из моделей автоматически
(`makemigrations`), Ecto — пишутся руками (генератор делает только болванку).
Сначала это кажется шагом назад, но именно поэтому у Ecto-миграции нет
«сюрпризов автогенерации», и она — единственный источник правды о схеме БД.
Схема (`Ecto.Schema`) и миграция независимы: схема описывает, как читать
таблицу, миграция — как её создать. Они могут даже расходиться (схема видит
не все колонки — это легально).

`def change` умеет автоматически откатываться: Ecto знает, что обратное к
`create table` — `drop table`. Как Liquibase rollback, но выводится сам.

Частичный уникальный индекс (`where: "state = 'performing'"`) — жемчужина
этого слоя. Он позволяет базе гарантировать, что строк со `state='performing'`
не бывает двух, при любом количестве строк в других состояниях. Двойная
конкурентная активация физически невозможна — это тот же приём, что мы
добавили в стабилизированный Django, и он переезжает в Elixir без потерь.

### 7. Явные join-схемы вместо неявных M2M (и почему sortedm2m — боль)

В Django-версии порядок элементов в связке держался на пакете `sortedm2m`, а
карточка C-судьи была цепочкой из ТРЁХ таблиц: `Score --sortedm2m-->
CombinationStatus --sortedm2m--> ElementStatus`. Агрегация оценок судей делала
`zip(*statuses_per_judge)` — то есть **корректность подсчёта зависела от
того, что у всех трёх судей цепочки имеют одинаковую длину и порядок**. Ни
одна база данных этого не гарантировала; расхождение означало бы тихо
неправильный счёт.

В Ecto промежуточная таблица many-to-many всегда явная. Мы делаем её схемой
первого класса с колонкой позиции:

```elixir
defmodule Ushu.Catalog.CombinationElement do
  use Ecto.Schema

  schema "combination_elements" do
    belongs_to :combination, Ushu.Catalog.Combination
    belongs_to :element, Ushu.Catalog.Element
    field :position, :integer          # 0, 1, 2, ... — порядок в связке
    timestamps()
  end
end
```

плюс уникальный индекс `(combination_id, position)` — порядок теперь факт
базы данных, а не поведение библиотеки. В JPA это ровно совет «не используйте
`@ManyToMany`, заведите entity для join-таблицы» — здесь он обязателен,
потому что `many_to_many` в Ecto не умеет нести дополнительные колонки.

А трёхэтажная цепочка карточки C-судьи схлопывается в одну плоскую таблицу:

```text
score_marks(score_id, combination_id, element_id, position, verdict)
verdict: pending | performed | failed
```

Ключ выравнивания между судьями — `(score_id, position)`, с уникальным
индексом. Теперь «zip» — это честный join по номеру позиции, и если у судьи
не хватает отметки, это видимая ошибка данных, а не тихий сдвиг счёта.
`combination_id` оставлен для группировки на экране судьи (где кончается одна
связка и начинается другая). Тристейт Django `done: 2/1/0` («не тронуто /
выполнено / провалено») стал enum'ом `:pending / :performed / :failed`.

### 8. `on_delete` живёт в БАЗЕ, а не в схеме — паритет с Django PROTECT

В Django `on_delete=PROTECT` на `Score.judge` защищал историю: судью с
оценками удалить нельзя. В Ecto есть два места, где можно объявить поведение
удаления, и выбор между ними принципиален:

- `references(:users, on_delete: :restrict)` в **миграции** — станет
  `ON DELETE RESTRICT` в самой БД. Работает всегда, даже для сырого SQL.
- опция на ассоциации в **схеме** — эмулируется самим Ecto и работает только
  если удалять через Repo определённым способом.

Мы всегда объявляем в миграции. Карта решений:

- `:restrict` (аналог PROTECT) — судья→оценки, элемент→отметки,
  код ошибки→записанные сбавки, страна→клубы, клуб→участники. Судей не
  удаляют — их деактивируют (`active: false`).
- `:delete_all` (аналог CASCADE) — категория→табло, участие→карточки→отметки:
  дерево владения умирает вместе с корнем.
- `:nilify_all` (аналог SET NULL) — журнал `score_events`: аудит должен
  переживать удаление того, что он описывает, поэтому FK зануляются, а
  человекочитаемый контекст (кто, кого, какое табло) продублирован в
  JSON-поле `payload`.

Нюанс SQLite: внешние ключи там выключены по умолчанию (!) и включаются
прагмой `PRAGMA foreign_keys = ON` на каждое соединение. Драйвер exqlite
это делает, но в слое есть регрессионный тест: вставка оценки с
несуществующим `participation_id` обязана упасть. Если кто-то сломает
конфиг — тест поймает.

### 9. Деньги… то есть баллы — целыми числами

Все балльные величины храним integer'ами в сотых долях («центибаллы»):
`7.00 → 700`. Так же, как деньги хранят в копейках. Django-версия уже пришла
к этому в вычислениях (`round(... * 100)` повсюду в `get_scores`), потому что
float даёт `8.549999...`; мы просто фиксируем то же представление в хранении:
`final_score_centi`, `b_score_centi`, `value_centi` (цена элемента),
`deduction_centi` (цена ошибки). Чистое ядро слоя 02 считает в тех же
центибаллах — на границе «база ↔ подсчёт» нет ни одной конверсии. В строку
«8.55» число превращается только на экране.

Бонус: `b_score_centi` **nullable**, и `nil` означает «судья ничего не ввёл»,
а `0` — «судья поставил честный ноль». В Django это различие держалось на
хрупкой связке `bclass is None and not berrors`; теперь это просто два разных
значения колонки.

---

## Решения и почему

Кратко пройдём решения из design.md человеческим языком.

**Схемы сразу в неймспейсах контекстов** (`Ushu.Competition.Participation`,
а не `Ushu.Schemas.Participation`). Слой 04 определит контексты `Accounts` /
`Catalog` / `Roster` / `Competition` — модули-фасады, как сервисный слой в
Spring. Phoenix-конвенция кладёт схемы внутрь их контекста; сделав так сразу,
мы избегаем переименования половины файлов через слой.

**Центибаллы (integer)**, а не float и не decimal. Float — источник дрейфа,
с которым Django-версия уже боролась. Decimal в SQLite хранится текстом —
медленные сравнения и всё равно конверсия для ядра 02. Целые числа — точные,
быстрые и совпадают с представлением ядра.

**Ecto.Enum строками + CHECK в базе.** Строки в базе читаемы глазами (во
время турнира вполне реально открыть sqlite3 и посмотреть, что происходит).
CHECK-ограничение — страховка от сырого SQL, в первую очередь от импортёра
слоя 07: если маппинг Django-чисел в строки где-то ошибётся, база откажет
сразу, а не «когда-нибудь при чтении».

**Явные join-схемы.** `combination_elements` с `position` — потому что
порядок был load-bearing (см. концепцию 7). `element_category_memberships` —
для симметрии и чтобы у импортёра была именованная таблица.

**`score_marks` с `combination_id` сверх минимума брифа.** Бриф фиксирует
четыре колонки; мы добавили пятую — FK на связку. Ключ выравнивания судей
не меняется (`score_id, position`), но экрану C-судьи нужны границы связок,
и выводить их из длин связок «по знанию» — значит завести новую неявную
зависимость взамен только что убитой.

**Каскады и запреты — в миграциях, не в схемах.** Поведение при удалении
должно работать и для кода, который мы ещё не написали, и для сырого SQL.
Единственное место, где это гарантировано, — сама БД.

**Частичный уникальный индекс для `:performing`.** — инвариант
«один на ковре» держит база, транзакционный переход состояний (Ecto.Multi)
добавит слой 04. Даже если код 04 будет с багом, двух выступающих не будет.

**`users` через `mix phx.gen.auth`, урезанный до username.** Генератор даёт
проверенное хеширование паролей (bcrypt) и всю сессионную обвязку; мы
выбрасываем email-потоки (подтверждение, сброс — бессмысленны в офлайн-LAN)
и добавляем `role`/`category`/`active`. Правило «category обязательна для
judge и запрещена для остальных» живёт в changeset'е — это замена
джанговского ребуса `is_superuser`/`is_staff`/`category`. Экранная часть
auth приедет в слое 06; пароли из Django не импортируются (их просто заново
раздаёт админ перед турниром — объяснение в слое 07).

**Переименования колонок**: `order → draw_order` и `group → group_entry`
(это ключевые слова SQL — каждый сырой запрос требовал бы кавычек),
`prizemlenie → landing` (терминология ядра подсчёта), `saved → submitted`
(точнее по смыслу), `image → flag_path`. Соответствие старых имён новым —
обязанность импортёра 07, таблица ниже.

**Пять миграций по областям** (users → catalog → roster → competition →
scoring) вместо одной гигантской или шестнадцати мелких: каждая обозрима,
порядок удовлетворяет внешним ключам, откат осмыслен.

**`score_events` — только вставка.** Таблица аудита (кто отправил оценку,
кто переоткрыл карточку, кто финализировал) — новая способность по сравнению
с Django, нужна для протестов. У неё нет `updated_at` и нет update-changeset:
журнал, который можно править, — не журнал.

---

## Как это соотносится с Django-версией

| Django (было) | Elixir (стало) | Комментарий |
|---|---|---|
| `judges.User(AbstractUser)` + `is_superuser`/`is_staff`/`category` | `users`: `role` enum `admin/main_judge/judge` + `category` enum `a/b/c` (nil если не judge) + `active` | Ребус флагов → две явные колонки |
| `participants.Participant.age` int 4,0,5,1,2,3 | `age` enum `y7_8/y9_10/y11/y12_14/y15_17/adult` | Числа, чей порядок разъехался с ярлыками → имена |
| `sex` int 0/1 | `sex` enum `male/female` | |
| `PARTICIPATION_STATES` 0/1/2 + сентинель `FINISHED && finalscore==0` | `state` enum `waiting/performing/finished/no_show` | Неявка — честное состояние |
| `Participation.order` | `participations.draw_order` | `order` — ключевое слово SQL |
| `Participation.group` | `participations.group_entry` | `group` — ключевое слово SQL |
| `Participation.finalscore` float | `final_score_centi` integer, nil до финализации | Центибаллы |
| `ElementCategory.name == 'group'/'duilian'` (сравнение строк) | `element_categories.format` enum `individual/group/duilian` | Правила C-судейства больше не зависят от написания имени |
| `Element.score` float, `Element.prizemlenie` | `elements.value_centi` integer, `elements.landing` boolean | |
| `ErrorCode.number` диапазоны 1–79 / 80–89 / 90+ | `error_codes.kind` enum `a/b/shared` (+ `number` остаётся для отображения) | Семантика из диапазона → колонка |
| `Combination.elements = SortedManyToManyField` | `combination_elements(combination_id, element_id, position)` + уникальный `(combination_id, position)` | Порядок — факт БД |
| `Element.categories = ManyToManyField` | `element_category_memberships` | Явная join-схема |
| `Score.aclass/berrors` → `WrapperErrorCode` → `ErrorCode` | `score_errors(score_id, error_code_id)` — простые строки, дубли разрешены | Минус одна таблица-обёртка |
| `Score.cclass` → `CombinationStatus` → `ElementStatus.done` 2/1/0 | `score_marks(score_id, combination_id, element_id, position, verdict)` , verdict `pending/performed/failed`, уникальный `(score_id, position)` | Позиционный zip → явная позиция |
| `Score.bclass` float, «None и нет ошибок = не голосовал» | `b_score_centi` integer nullable: `nil` = молчание, `0` = голос | |
| `Score.saved` | `scores.submitted` | |
| `UniqueConstraint` табло/участие/оценка (добавлены при стабилизации) | Те же уникальные индексы + `unique_constraint` в changeset'ах | Паритет |
| Частичный `UniqueConstraint(state=DOING)` | Частичный уникальный индекс `WHERE state = 'performing'` | Паритет |
| `on_delete=PROTECT` (судья, элемент, код ошибки, страна, клуб) | `references(..., on_delete: :restrict)` в миграциях | Паритет |
| `on_delete=CASCADE` (категория→табло, участие→оценки) | `on_delete: :delete_all` | Паритет |
| — (не было) | `score_events` append-only + `nilify_all` | Новое: аудит для протестов |
| — (не было) | `timestamps()` на всех таблицах | Django-модели ushu их не имели |
| `Country.image = ImageField` | `countries.flag_path` string | Файлы скопирует слой 07 |

Чего здесь СОЗНАТЕЛЬНО нет (уйдёт в слой 04): сигнал `post_save` на
`ElementCategory`, создающий табло; `assign_participation` со снимком
судейской панели и дедупликацией групп по клубу; `assign_combinations`;
переходы состояний; агрегация в `get_scores`. Схемы этого слоя — только
данные и инварианты, никакого workflow.

## Что почитать

- Ecto — общая картина и философия: https://hexdocs.pm/ecto/Ecto.html
- `Ecto.Schema` (поля, ассоциации, timestamps): https://hexdocs.pm/ecto/Ecto.Schema.html
- `Ecto.Changeset` — читать целиком, это сердце слоя: https://hexdocs.pm/ecto/Ecto.Changeset.html (особенно разделы про `unique_constraint/3` и `check_constraint/3`)
- `Ecto.Enum`: https://hexdocs.pm/ecto/Ecto.Enum.html
- Миграции (`Ecto.Migration`, `references`, `unique_index` с `where:`): https://hexdocs.pm/ecto_sql/Ecto.Migration.html
- `Ecto.Multi` — понадобится в слое 04 для перехода состояний: https://hexdocs.pm/ecto/Ecto.Multi.html
- Официальный гайд «Data mapping and validation»: https://hexdocs.pm/phoenix/data_modelling.html
- `ecto_sqlite3` — особенности SQLite-адаптера (типы, прагмы): https://hexdocs.pm/ecto_sqlite3/EctoSQLite3.html
- `mix phx.gen.auth` — что генерирует и почему: https://hexdocs.pm/phoenix/mix_phx_gen_auth.html
- Партиальные индексы SQLite (первоисточник): https://sqlite.org/partialindex.html
