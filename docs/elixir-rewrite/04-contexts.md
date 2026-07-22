# Слой 04 — Контексты: бизнес-логика соревнования

Это четвёртый слой переписывания ushu на Elixir/Phoenix (см. openspec-изменение
`elixir-04-contexts`). Предыдущие слои дали нам чистое ядро подсчёта очков
(`Ushu.Scoring`, слой 02) и Ecto-схемы с ограничениями в базе (слой 03). Но данные без
поведения — это ещё не приложение. В этом слое появляется всё, что «происходит» на
соревновании: регистрация участника со снимком судейской панели, жеребьёвка, вывод
участника на ковёр, приём судейских карточек, финализация, неявка, переоткрытие судьи,
итоговая таблица.

В Django-версии эта логика была размазана по `ParticipationManager`, дюжине view-классов
в `tablo/views.py` (800 строк!) и одному post-save-сигналу. В Elixir-версии она собрана в
**контексты** — модули с чётким публичным API. LiveView-слой (слой 06) будет тонким:
распарсил ввод, вызвал одну функцию контекста, отрисовал результат.

---

## Ключевые концепции Elixir/Phoenix в этом слое

### 1. Контексты Phoenix — «bounded context», а не сервис-помойка

В Spring ты привык к слою сервисов: `@Service class CompetitionService` с инжекцией
репозиториев. Контекст Phoenix — идейно то же самое, но с двумя отличиями:

1. Это просто **модуль с функциями**, без DI-контейнера. Никаких прокси, аннотаций,
   бинов — граница видна глазами в коде.
2. Phoenix настаивает, чтобы контексты были нарезаны по **предметным областям**
   (bounded contexts из DDD), а не по техническим слоям и не по одной сущности.

```elixir
defmodule Ushu.Competition do
  @moduledoc """
  Всё, что происходит во время живого соревнования:
  регистрация, жеребьёвка, активация, судейские карточки, финализация.
  """
  alias Ushu.Repo
  alias Ushu.Competition.{Participation, Score}

  def activate(participation_id) do
    # ...
  end
end
```

Мы выделили четыре контекста:

| Контекст | Отвечает за | Аналог в Spring |
|---|---|---|
| `Ushu.Accounts` | пользователи, роли, состав панели | `UserService` + Spring Security |
| `Ushu.Catalog` | справочники: категории, элементы, коды ошибок | `ReferenceDataService` |
| `Ushu.Roster` | кто выступает: участники, клубы, удаление заявок | `RegistrationService` |
| `Ushu.Competition` | живое соревнование целиком | `CompetitionService` |

Почему не «по сущности» (`ParticipationService`, `ScoreService`)? Потому что одна
бизнес-операция трогает несколько таблиц: `activate/1` меняет participation, читает
scores, пишет audit. Если контексты нарезаны по таблицам, каждая операция превращается в
хоровод вызовов между сервисами — знакомая по Spring боль, когда `OrderService` дергает
`PaymentService`, тот дергает `InventoryService`, и транзакционные границы плывут.

Важное правило: **вебу нельзя ходить в Repo напрямую**. LiveView вызывает только функции
контекста. Это тот же принцип, что «контроллер не трогает EntityManager», только в Phoenix
он поддержан конвенцией и код-ревью, а не аннотацией.

### 2. Теговые кортежи `{:ok, _}` / `{:error, _}` вместо исключений

В Kotlin/Spring ошибка бизнес-правила — это обычно исключение:
`throw IllegalStateException("another participant is performing")`, которое где-то наверху
ловит `@ExceptionHandler`. В Elixir доменные исходы — это **значения**:

```elixir
case Competition.activate(id) do
  {:ok, participation} ->
    # успех — работаем с данными
  {:error, :not_waiting} ->
    # участник не в состоянии ожидания
  {:error, :another_performing} ->
    # на ковре уже кто-то есть
end
```

Ближайшая аналогия из Kotlin — sealed class / `Result<T>`:

```kotlin
sealed interface ActivateResult {
    data class Ok(val p: Participation) : ActivateResult
    object NotWaiting : ActivateResult
    object AnotherPerforming : ActivateResult
}
```

…только в Elixir это не требует объявлять типы: кортеж `{:error, :not_waiting}` создаётся
на месте, а сопоставление с образцом (pattern matching) в `case` заменяет `when`-ветвление.

Почему это принципиально для ushu: гонка «судья отправил карточку после того, как главный
судья финализировал» — это **нормальный** сценарий, он случается на каждом турнире. В
Django-версии до стабилизации он ронял 500-ю ошибку. Исход, который случается штатно,
должен быть значением, а не исключением. Исключения в Elixir оставляют для настоящих
аварий (отвалилась база) — и там работает философия «let it crash» и супервизоры, о
которых подробнее в слое 05.

Конвенция именования: `activate/1` возвращает кортеж, `activate!/1` (с бэнгом) бросает
исключение. Для мутаций соревнования мы **не** публикуем bang-версии — у каждой ошибки
есть осмысленная реакция в UI.

### 3. `with` — цепочка шагов, каждый из которых может не получиться

Проблема: операция из пяти шагов, каждый возвращает `{:ok, _} | {:error, _}`. Вложенные
`case` дают «лесенку судьбы». Решение — специальная конструкция `with`:

```elixir
def submit_b(%User{} = judge, attrs) do
  with {:ok, participation} <- fetch_active(),                    # есть активный?
       {:ok, score}         <- fetch_own_score(participation, judge), # есть своя карточка?
       {:ok, base}          <- parse_base(attrs.base),            # оценка — число?
       {:ok, codes}         <- validate_codes(attrs.error_code_ids, [:b, :shared]),
       {:ok, saved}         <- persist_b(score, base, codes, judge) do
    broadcast({:score_saved, saved.id})
    {:ok, saved}
  end
end
```

Читается как «happy path» сверху вниз: каждая строка сопоставляет результат шага с
образцом `{:ok, что-то}`. Как только какой-то шаг вернул НЕ то, что слева от `<-` —
цепочка обрывается, и **это значение становится результатом всего `with`**. То есть
`{:error, :no_active}` из первого шага просто «проваливается» наружу — ровно то, что нам
нужно вернуть вызывающему.

Аналог из Kotlin — цепочка `runCatching`/`flatMap` над `Result`, или Arrow-овский
`either { ... bind() ... }`. Но в Elixir это встроено в язык и не требует библиотек.

### 4. `Ecto.Multi` — транзакция как значение (вместо `@Transactional`)

В Spring транзакция — это аннотация: `@Transactional fun activate(...)`, магия прокси. В
Ecto транзакция — это **данные**: ты строишь конвейер именованных шагов, а потом отдаёшь
его целиком в `Repo.transaction/1`:

```elixir
alias Ecto.Multi

def activate(participation_id) do
  with {:ok, p} <- fetch_waiting(participation_id) do
    Multi.new()
    |> Multi.update(:participation, Participation.state_changeset(p, :performing))
    |> Multi.insert(:audit, fn %{participation: p} ->
      Audit.event(nil, :activated, participation_id: p.id)
    end)
    |> Repo.transaction()
    |> case do
      {:ok, %{participation: p}} ->
        Phoenix.PubSub.broadcast(Ushu.PubSub, "competition", {:performance_started, p.id})
        {:ok, p}

      {:error, :participation, %Ecto.Changeset{} = cs, _done} ->
        translate(cs)   # нарушение partial unique index -> {:error, :another_performing}
    end
  end
end
```

Что здесь важно понять:

- **Каждый шаг имеет имя** (`:participation`, `:audit`). При ошибке Ecto говорит, какой
  именно шаг упал и что успело выполниться (`_done`) — в Spring для этого пришлось бы
  копаться в стектрейсе.
- **Шаг может зависеть от предыдущих**: второй `Multi.insert` принимает функцию, которой
  передаются результаты уже выполненных шагов. Аналог `flatMap`.
- **Multi можно собирать по кусочкам и тестировать без базы** — это обычная структура
  данных. `@Transactional`-метод без Spring-контекста не потестируешь.
- Никакой магии self-invocation (классическая ловушка Spring: вызов `@Transactional`
  метода из соседнего метода того же бина молча идёт мимо транзакции). Здесь транзакция
  ровно там, где стоит `Repo.transaction`.

Правило слоя: **аудит-запись — внутри Multi, PubSub-рассылка — строго после коммита**.
Внутри — чтобы не было мутации без следа и следа без мутации (протесты!). После — чтобы
подписчик, получив `{:score_saved, id}` и перечитав базу, гарантированно увидел уже
закоммиченную строку.

### 5. Инвариант «на ковре один участник»: база + контекст, а не UI

В Django проверка «кто-то уже выступает?» жила во view — `if Participation.objects.filter(
state=PS_DOING).exists()` — плюс (после стабилизации) частичный уникальный индекс. Мы
сохраняем оба уровня, но оформляем перевод состояния как явную маленькую state-machine в
changeset-е:

```elixir
# В схеме Participation (слой 03) объявлено:
# unique_constraint(:state, name: :one_performing) — частичный индекс WHERE state='performing'

def state_changeset(participation, new_state) do
  participation
  |> change(state: new_state)
  |> validate_transition(participation.state, new_state)  # waiting->performing, performing->finished|no_show
  |> unique_constraint(:state, name: :one_performing)
end
```

Если два секретаря нажали «активировать» одновременно, оба пройдут проверку «никто не
выступает» (гонка!), но выиграет только один INSERT/UPDATE — второй получит нарушение
индекса, которое `unique_constraint` превратит в ошибку changeset-a, а контекст — в
`{:error, :another_performing}`. Никаких 500, никакого «на табло два участника».

Это тот же паттерн, что optimistic locking в JPA, только инвариант выражен прямо в
DDL и оттого не обходится ни при каком пути записи.

### 6. Проектирование API вокруг инвариантов: владение «по построению»

Самое важное решение слоя — сигнатуры судейских функций. Django-версия страдала IDOR-ом:
`JudgeCSubmit` принимал первичные ключи `ElementStatus` из POST и (до стабилизации)
доверял им — можно было подделать pk и править чужую карточку. Стабилизация добавила
фильтр по владельцу. Elixir-версия делает следующий шаг — **дизайн, при котором подделка
невозможна в принципе**:

```elixir
# НЕ так:  submit_c(score_id, verdicts)   — score_id приходит от клиента, ему нельзя верить
# А так:
def submit_c(%User{} = judge, verdicts) do
  # карточка вычисляется на сервере: активное выступление × текущий судья
  with {:ok, p}     <- fetch_active(),
       {:ok, score} <- fetch_own_score(p, judge),
       :ok          <- verify_marks_owned(score, Map.keys(verdicts)) do
    ...
  end
end
```

Клиент вообще не передаёт идентификатор карточки — только вердикты по элементам. Чужой
`mark_id` в вердиктах отклоняется целиком (`{:error, {:not_owner, ids}}`). Принцип из
security-мира — «make invalid states unrepresentable»: не фильтруй злонамеренный ввод, а
строй API так, чтобы злонамеренному вводу некуда было приткнуться.

Тот же принцип в других местах слоя:

- `no_show` — отдельное состояние enum-а, а не «FINISHED с нулём» (нельзя перепутать
  неявку с реальным нулём);
- коды ошибок валидируются по enum-полю `kind` (`:a | :b | :shared`), а не по числовым
  диапазонам 1–79/80–89/90+, зашитым в if-ах;
- пропуск судей C для юных возрастов и групповых/дуйлянь-категорий — по enum-ам
  `age_bucket` и `format`, а не по сравнению имени категории со строкой `'group'`
  (в Django однажды сломалось бы от переименования категории в админке).

### 7. Пример целиком: `submit_c/2` с гейтом полноты

Правило из закреплённой спеки: судья C обязан отметить **каждый** элемент, прежде чем
карточка сохранится. При этом частичный прогресс терять нельзя (судья отмечает 20+
элементов вживую). Смотри, как теговые кортежи выражают трёхзначный исход:

```elixir
def submit_c(%User{} = judge, verdicts) when is_map(verdicts) do
  with {:ok, p}      <- fetch_active(),
       {:ok, score}  <- fetch_own_score(p, judge),
       :ok           <- verify_marks_owned(score, Map.keys(verdicts)),
       {:ok, score}  <- apply_verdicts(score, verdicts, judge) do   # persist + audit в Multi
    case pending_mark_ids(score) do
      []  -> save_and_broadcast(score, judge)          # {:ok, score} — карточка закрыта
      ids -> {:error, {:unmarked, ids}}                # прогресс сохранён, saved == false
    end
  end
end
```

UI (слой 06) получает `{:error, {:unmarked, ids}}` и подсвечивает пропущенные элементы.
Ни исключений, ни флеш-сообщений из недр модели — контекст возвращает данные, view решает,
как их показать.

---

## Решения и почему (из design.md, человеческим языком)

**Четыре контекста, а не один и не двадцать (D1).** Один «CoreService» — это путь
`tablo/views.py`, где жеребьёвка, SSE и подсчёт очков жили в одном файле. Контекст на
каждую таблицу — противоположная крайность: `activate` трогает три таблицы, и пришлось бы
устраивать межсервисные вызовы с расползающимися транзакциями. Граница по «предметной
причине изменения» — золотая середина.

**Кортежи вместо исключений (D2).** Все штатные отказы — значения из документированного
набора: `:no_active`, `:not_waiting`, `:another_performing`, `:scores_pending`,
`{:invalid_codes, ids}`, `{:unmarked, ids}`, `{:not_owner, ids}`. У каждого есть понятная
реакция в UI. Исключения — только для настоящих аварий.

**Снимок панели при регистрации (D4).** Как в Django: карточки Score создаются сразу при
регистрации для всех подходящих активных судей (3A/4B/3C; без C для `:y7_8`, `:y9_10`,
`:y11`, `:y12_14` и для форматов `:group`/`:duilian`; для групп — одна заявка на клуб).
Альтернатива «снимок при активации» отвергнута: секретарь привык видеть сетку карточек
сразу после регистрации, а смена судьи среди дня решается деактивацией + переоткрытием.

**Отклонять неверные коды, а не молча выбрасывать (D6).** Django предупреждал и сохранял
остальное — то есть судья мог не заметить, что половина сбавок не записалась. Теперь
неверный код валит всю отправку с перечислением плохих кодов; LiveView перерисует форму
мгновенно, это ничего не стоит.

**Переоткрытие любого судьи, включая B (D8).** Твой пункт из zametka.txt. Django
адресовал судей индексом в отсортированном списке (хрупко!), мы адресуем score_id.
Переоткрытие только снимает флаг `saved`, введённые данные остаются — судья правит, а не
вводит заново. Работает только пока участник на ковре; протесты после — через аудит.

**Финализация требует все сохранённые карточки (D9).** В Django это было свойством кнопки
(`can_be_saved`), то есть проверкой на клиенте; POST мимо кнопки финализировал бы с
дырявой панелью. Теперь `{:error, :scores_pending}` — серверный гейт.

**Аудит в транзакции, событие после коммита (D5).** `score_events` пишется тем же Multi,
что и мутация: нет мутации без следа. PubSub — после коммита: подписчик перечитывает базу
и всегда видит закоммиченное. В событиях только идентификаторы, без данных строк — база
остаётся единственным источником правды, и LiveView, пропустивший событие при реконнекте,
просто перечитывает состояние (детали каталога событий — слой 05).

**Явное создание табло вместо сигнала (D11).** Django-сигнал post_save на ElementCategory
создавал 12 табло — с гонками и «магией на расстоянии». Теперь
`Catalog.create_element_category/1` создаёт категорию и её табло одним Multi, а уникальный
индекс делает повтор идемпотентным. В Elixir-культуре lifecycle-магии не бывает — все
эффекты видны в точке вызова.

---

## Как это соотносится с Django-версией

| Django (было) | Elixir (стало) |
|---|---|
| `ParticipationManager.assign_participation(participant, category)` | `Ushu.Competition.register_participant/2` |
| матчинг категории по имени `'group'`/`'duilian'` | enum-поле `format: :individual \| :group \| :duilian` |
| `age in (AGE_11, AGE_7_8, AGE_9_11, AGE_12_14)` → без C | age-bucket enum `[:y7_8, :y9_10, :y11, :y12_14]` → без C |
| `JrebiView` (кнопки save/stop) + команда `jrebiy` | `draw_tablo/1` + `draw_all/1` (опция `force: true`) |
| `ParticipantActivateView.post` + частичный индекс | `activate/1`: Multi + `unique_constraint` → `{:error, :another_performing}` |
| `JudgeASubmit` / `JudgeBSubmit` / `JudgeCSubmit` (валидация диапазонов 1–79/90+) | `submit_a/2`, `submit_b/2`, `submit_c/2` (валидация по `kind`) |
| фильтр владельца по pk из POST (после стабилизации) | владение по построению: функции принимают судью, карточка вычисляется на сервере |
| редирект с messages при «нет активного» | `{:error, :no_active}` — view сам решает, что показать |
| `ParticipantScoreView.post` (`save` / `notavailable` / `reopen`) | `finalize/2` / `mark_no_show/1` / `reopen_judge/2` |
| неявка = `FINISHED` + `finalscore == 0` (сентинель) | состояние `:no_show`, `finalscore` пуст |
| `open_judge(request, idx)` — судья по индексу списка | `reopen_judge(score_id, actor)` — по id, любой судья, включая B |
| `views.sort` + `cmp` + `counts` (в файле с views!) | `standings/1` в контексте; арифметика тай-брейка — в чистом `Ushu.Scoring` (слой 02) |
| post_save-сигнал создаёт табло | `Catalog.create_element_category/1` — явный Multi |
| аудита нет | `score_events` — append-only, в каждой мутации |
| SSE-пуш HTML на монитор из view | контекст шлёт доменные события PubSub; монитор — слой 05 |

Сигнатуры публичных функций (контракт для слоя 06) зафиксированы в
`openspec/changes/elixir-04-contexts/design.md`, решение D3 — при написании LiveView
сверяйся с ними, а не с памятью.

События PubSub, которые публикует этот слой (имена общие со слоями 05/06):
топик `"competition"` — `{:performance_started, id}`, `{:score_saved, score_id}`,
`{:score_reopened, score_id}`, `{:performance_finalized, id}` (финализация и неявка).

---

## Что почитать

- Контексты Phoenix (главный документ слоя): https://hexdocs.pm/phoenix/contexts.html
- `Ecto.Multi`: https://hexdocs.pm/ecto/Ecto.Multi.html
- `Ecto.Repo.transaction/2`: https://hexdocs.pm/ecto/Ecto.Repo.html#c:transaction/2
- `with` (специальная форма): https://hexdocs.pm/elixir/Kernel.SpecialForms.html#with/1
- Гайд по `case`/`cond`: https://hexdocs.pm/elixir/case-cond-and-if.html
- `Ecto.Changeset.unique_constraint/3` (перевод нарушений индекса в ошибки):
  https://hexdocs.pm/ecto/Ecto.Changeset.html#unique_constraint/3
- `Phoenix.PubSub`: https://hexdocs.pm/phoenix_pubsub/Phoenix.PubSub.html
- Про «library over framework» и явность вместо магии — доклад-классика:
  https://hexdocs.pm/elixir/naming-conventions.html (конвенции `!`/`?` в именах)
