# Слой 06 — LiveView UI: все экраны системы

Это шестой из семи слоёв переписывания ushu на Elixir/Phoenix. Здесь появляется
всё, что видят люди: логин, три судейских пульта (A/B/C), консоль секретаря,
экран главного судьи, проектор-монитор и печатный протокол. Слой опирается на
уже готовые нижние этажи: бизнес-операции из `elixir-04-contexts`
(активация, приём оценок, финализация, reopen), события PubSub и снапшот
монитора из `elixir-05-realtime`, схему пользователей из `elixir-03-ecto-schema`.

Главная идея слоя: **вместо Django-шаблонов с таймер-поллингом — Phoenix
LiveView**. LiveView — это серверный UI поверх WebSocket: состояние экрана
живёт в процессе на сервере, браузеру уходят только маленькие диффы HTML.
Если ты работал с Vaadin Flow в Jmix — это очень близкая модель: компоненты и
состояние на сервере, браузер — «тонкий терминал». Разница в том, что LiveView
не строит дерево Java-компонентов, а рендерит шаблон и присылает диффы, и что
падение одного экрана — это падение одного лёгкого Erlang-процесса, а не потока
в общем пуле.

---

## Ключевые концепции Elixir/Phoenix в этом слое

### 1. Жизненный цикл LiveView: mount → handle_params → handle_event → handle_info

Каждый открытый экран — отдельный процесс. У процесса есть `socket` — структура
с состоянием (`assigns`). Жизненный цикл:

```elixir
defmodule UshuWeb.SecretaryLive do
  use UshuWeb, :live_view

  # 1. mount вызывается ДВАЖДЫ: сначала для обычного HTTP-рендера
  #    (быстрый первый экран), затем — когда браузер поднял WebSocket.
  def mount(_params, _session, socket) do
    if connected?(socket) do
      # подписки делаем только в live-режиме — при мёртвом рендере
      # процесс живёт миллисекунды и подписка бессмысленна
      Phoenix.PubSub.subscribe(Ushu.PubSub, "competition")
    end

    {:ok, assign(socket, tablos: Ushu.Competition.list_tablo_grid())}
  end

  # 2. handle_params — реакция на URL (и на live-навигацию patch'ем)
  def handle_params(%{"tablo_id" => id}, _uri, socket) do
    {:noreply, assign(socket, standings: Ushu.Competition.standings(id))}
  end
  def handle_params(_params, _uri, socket), do: {:noreply, socket}

  # 3. handle_event — действия пользователя (phx-click, phx-submit, hook)
  def handle_event("activate", %{"id" => id}, socket) do
    case Ushu.Competition.activate(id, socket.assigns.current_user) do
      {:ok, _} -> {:noreply, socket}
      {:error, :already_performing} ->
        {:noreply, put_flash(socket, :error, gettext("На ковре уже есть участник"))}
    end
  end

  # 4. handle_info — сообщения ДРУГИХ процессов (PubSub, таймеры, GenServer)
  def handle_info({:score_saved, _score_id}, socket) do
    {:noreply, refresh_active_panel(socket)}
  end
end
```

Параллели:

- **Vaadin/Jmix**: `mount` ≈ `onInit`/`onAttach` view-контроллера,
  `handle_event` ≈ `@Subscribe` на клик кнопки, `handle_info` ≈
  `UI.access {}` при пуше с фонового потока. Только здесь не нужен
  `@Push` и `UI.access` — процесс LiveView и так один, сообщения из
  почтового ящика обрабатываются последовательно, гонок внутри экрана нет.
- **Django (старый ushu)**: аналога нет вообще. Django-view умирает после
  ответа, поэтому судейские экраны опрашивали сервер таймером, а монитор
  тянул HTML-снапшоты. LiveView-процесс живёт, пока открыта вкладка.

Важное следствие двойного `mount`: весь код в `mount` должен быть идемпотентным,
а состояние — восстановимым из БД. Это же спасает при обрыве Wi-Fi: клиент
LiveView сам переподключается, `mount` выполняется заново и экран полностью
пересинхронизируется. Никакого «накопленного только на клиенте» состояния.

### 2. Assigns и отслеживание изменений (change tracking)

`assigns` — это карта состояния сокета. Рендер — функция от assigns. Магия в
том, что HEEx-шаблон компилируется так, что при повторном рендере по проводу
уходят **только изменившиеся куски**:

```elixir
def render(assigns) do
  ~H"""
  <h1>{@participant.name}</h1>          <%!-- уйдёт только если сменился участник --%>
  <span class="score">{@final_score}</span> <%!-- уйдёт только при новой оценке --%>
  """
end
```

Если изменился только `@final_score`, браузер получит буквально несколько байт
с новым числом. Для наших слабых клиентских машин в зале это принципиально:
никакого React-бандла, никакого re-render всего дерева — сервер сам знает, что
поменялось.

Kotlin-параллель: это как `StateFlow` + Compose-рекомпозиция, только
«рекомпозиция» происходит на сервере, а до клиента доезжает уже готовый дифф.

Правило, которое из этого следует: **меняй assigns только через
`assign/2,3`** — так LiveView помечает ключ «грязным». И не клади в assigns
гигантские структуры «на всякий случай»: держи там ровно то, что рендерится.

### 3. HEEx и функциональные компоненты

HEEx (`~H`) — шаблоны с проверкой HTML на этапе компиляции. Переиспользуемые
куски — не наследование шаблонов как в Django, а **функциональные компоненты**:
обычные функции `assigns -> rendered`, с декларацией атрибутов:

```elixir
defmodule UshuWeb.JudgeComponents do
  use Phoenix.Component

  attr :code, :integer, required: true
  attr :label, :string, required: true

  # кружок кода ошибки для пульта судьи A
  def error_circle(assigns) do
    ~H"""
    <button
      phx-click="add_error"
      phx-value-code={@code}
      class="h-20 w-20 rounded-full text-2xl font-bold border-4">
      {@label}
    </button>
    """
  end

  attr :state, :atom, required: true
  slot :inner_block

  def state_badge(assigns) do
    ~H"""
    <span class={badge_class(@state)}>{render_slot(@inner_block)}</span>
    """
  end

  # ВАЖНО: классы Tailwind — только целыми литеральными строками,
  # иначе сборщик CSS их не увидит и выкинет
  defp badge_class(:waiting),    do: "badge badge-neutral"
  defp badge_class(:performing), do: "badge badge-warning"
  defp badge_class(:finished),   do: "badge badge-success"
  defp badge_class(:no_show),    do: "badge badge-ghost"
end
```

Использование в шаблоне: `<.error_circle code={40} label="40" />`. `attr` даёт
compile-time предупреждения при опечатке — примерно как типизированные
параметры Vaadin-компонента, в отличие от Django-шаблонов, где опечатка в
переменной молча рендерит пустоту.

`phx-click` + `phx-value-*` — это декларативная привязка события: клик уйдёт в
`handle_event("add_error", %{"code" => "40"}, socket)` того же процесса.
Сравни с Django-версией: там клик по кружку собирался руками в JS и отправлялся
POST-формой.

### 4. Формы: changeset + to_form (пульт судьи B)

Единственная «настоящая форма» в слое — ввод балла судьёй B. Идиома Phoenix:
источник правды о валидации — **changeset** (тот же механизм, что в Ecto), в
шаблон он подаётся через `to_form`:

```elixir
defmodule UshuWeb.JudgeBLive do
  use UshuWeb, :live_view

  # embedded_schema — «форма без таблицы», аналог DTO с бин-валидацией в Spring
  defmodule ScoreForm do
    use Ecto.Schema
    import Ecto.Changeset

    embedded_schema do
      field :value, :decimal
    end

    def changeset(form, attrs) do
      form
      |> cast(attrs, [:value])
      |> validate_required([:value])
      |> validate_number(:value,
           greater_than_or_equal_to: 0,
           less_than_or_equal_to: Decimal.new("10.00"))
    end
  end

  def mount(_p, _s, socket) do
    {:ok, assign_form(socket, ScoreForm.changeset(%ScoreForm{}, %{}))}
  end

  # живая валидация: каждый ввод -> changeset -> ошибки в форме
  def handle_event("validate", %{"score_form" => attrs}, socket) do
    cs = ScoreForm.changeset(%ScoreForm{}, attrs) |> Map.put(:action, :validate)
    {:noreply, assign_form(socket, cs)}
  end

  def handle_event("submit", %{"score_form" => attrs}, socket) do
    with {:ok, form} <- Ecto.Changeset.apply_action(ScoreForm.changeset(%ScoreForm{}, attrs), :insert),
         {:ok, _} <- Ushu.Competition.submit_b(socket.assigns.score, form.value, socket.assigns.current_user) do
      {:noreply, assign(socket, submitted: true)}
    else
      {:error, %Ecto.Changeset{} = cs} -> {:noreply, assign_form(socket, cs)}
      {:error, reason} -> {:noreply, put_flash(socket, :error, error_text(reason))}
    end
  end

  defp assign_form(socket, cs), do: assign(socket, form: to_form(cs))
end
```

```heex
<.form for={@form} phx-change="validate" phx-submit="submit">
  <.input field={@form[:value]} inputmode="decimal" />
  <button disabled={!@form.source.valid?}>{gettext("Отправить")}</button>
</.form>
```

Параллель со Spring: `embedded_schema` + `changeset` ≈ форм-DTO с
`@Valid`/Bean Validation, `to_form` ≈ `BindingResult`, только ошибки
перерисовываются вживую на каждый ввод (`phx-change`), без JS-валидатора.
Против Django-версии: там валидация B-оценки была размазана между JS и view,
и нечисловой ввод молча превращался в 0.0 (`_to_float`). Здесь нечисловой
ввод просто не проходит changeset — и кнопка выключена.

Обрати внимание: клиентская валидация — это UX, а не защита. Настоящая
проверка (владение карточкой, активная попытка, диапазон) живёт в
`Ushu.Competition.submit_b/3` (слой 04). UI лишь дублирует её для удобства.

### 5. JS-хуки и event.code: судейские хоткеи (и починка «кириллического» бага)

Пульты A и C управляются физическими клавишами. В старом ushu хоткеи ловились
по символу (`event.key`), и при русской раскладке `v` превращался в `м` — судья
жал клавишу, ничего не происходило. Правильный API — **`event.code`**: он
называет **физическую позицию клавиши** (`KeyV`, `Space`) независимо от
раскладки.

Там, где LiveView-атрибутов не хватает (нужен именно `event.code`), пишется
**hook** — маленький JS-объект с жизненным циклом, привязанный к DOM-элементу:

```js
// assets/js/hooks/c_hotkeys.js
export const CHotkeys = {
  mounted() {
    this.onKey = (e) => {
      if (e.repeat) return;               // зажатая клавиша не строчит события
      const map = {
        KeyV: "performed",                // физическая V (на ней же русская М)
        KeyX: "failed",                   // физическая X (русская Ч)
        KeyC: "pending",                  // физическая C (русская С) — сброс
      };
      if (map[e.code]) {
        e.preventDefault();
        this.pushEvent("mark", { verdict: map[e.code] }); // -> handle_event("mark", ...)
      } else if (e.code === "ArrowDown" || e.code === "ArrowUp") {
        e.preventDefault();
        this.pushEvent("move_cursor", { dir: e.code === "ArrowDown" ? "next" : "prev" });
      }
    };
    window.addEventListener("keydown", this.onKey);
  },
  destroyed() {
    window.removeEventListener("keydown", this.onKey); // обязательно чистим
  },
};
```

```heex
<div id="c-card" phx-hook="CHotkeys">
  <div :for={{mark, i} <- Enum.with_index(@marks)}
       class={["element-row", i == @cursor && "ring-4"]}>
    {mark.element.name} — <.verdict_icon verdict={mark.verdict} />
  </div>
  <button phx-click="submit" disabled={@pending_count > 0}>
    {gettext("Отправить")}
  </button>
</div>
```

`pushEvent` с хука прилетает в тот же `handle_event`, что и обычный
`phx-click`, — сервер не различает, нажата экранная кнопка или физическая
клавиша. Поэтому вся логика («пометить текущий элемент, сдвинуть курсор на
следующий непомеченный, выключить submit пока есть `:pending`») живёт на
сервере один раз.

Для пульта A хук проще: `Space`/`Enter`/`NumpadEnter` открывают подтверждение
отправки. Есть встроенный `phx-window-keydown`, но он отдаёт `event.key` —
то есть ровно тот баг, который мы чиним, — поэтому оба пульта используют хуки.

Vaadin-параллель: hook ≈ свой клиентский модуль/`executeJs` + `@ClientCallable`
— редкая, точечная капля JS в серверной модели.

### 6. Streams: длинные списки без памяти на сервере

Обычные assigns хранятся в процессе — для списка на сотни строк это лишняя
память в каждом сокете. **Streams** отправляют строки клиенту и «забывают» их
на сервере, а дальше адресуют по id:

```elixir
def mount(_p, _s, socket) do
  {:ok, stream(socket, :participations, Competition.list_participations(tablo_id))}
end

def handle_info({:performance_finalized, id}, socket) do
  # точечно обновляем одну строку по id — без перезагрузки списка
  {:noreply, stream_insert(socket, :participations, Competition.get_participation!(id))}
end
```

```heex
<tbody id="participations" phx-update="stream">
  <tr :for={{dom_id, p} <- @streams.participations} id={dom_id}>
    <td>{p.order}</td><td>{p.participant.name}</td>
    <td><.state_badge state={p.state}>{state_text(p.state)}</.state_badge></td>
  </tr>
</tbody>
```

Где мы это применяем, а где — нет (решение D7): список участников у секретаря —
stream; **таблица standings — обычный assign**, потому что при финализации
одного участника меняются ранги у всех строк сразу, и «точечный» апдейт строк
ничего не экономит — проще пересчитать и перерисовать маленькую таблицу целиком.
Инструмент под задачу, а не везде одинаково.

### 7. live_session и on_mount: авторизация по ролям

Аутентификацию генерирует `mix phx.gen.auth` — это как Spring Security
starter, только генератор кладёт код **в твой проект**, и ты его правишь. Мы
выпиливаем всё e-mail'ное (подтверждения, magic links, сброс пароля почтой —
на офлайн-LAN в зале почты нет) и оставляем username+password.

Охрана LiveView — не плагом (плаги работают на HTTP-запросе, а live-навигация
между экранами не делает HTTP-запросов), а **`on_mount`-хуком**, привязанным к
`live_session` в роутере:

```elixir
# router.ex
live_session :admin_area,
  on_mount: [
    {UshuWeb.UserAuth, :ensure_authenticated},
    {UshuWeb.UserAuth, {:ensure_role, [:admin]}}
  ] do
  live "/secretary", SecretaryLive
  live "/users", UsersLive
  live "/print/:tablo_id", PrintLive
end

live_session :judge_area,
  on_mount: [{UshuWeb.UserAuth, {:ensure_role, [:judge]}}] do
  live "/judge", JudgeEntryLive
end

# монитор — публичный: у проектора нет оператора, вводить пароль некому,
# а показывает он только то, что и так видит весь зал
live_session :monitor_public do
  live "/monitor", MonitorLive
end
```

```elixir
# user_auth.ex
def on_mount({:ensure_role, roles}, _params, _session, socket) do
  user = socket.assigns.current_user
  if user && user.role in roles do
    {:cont, socket}
  else
    {:halt,
     socket
     |> Phoenix.LiveView.put_flash(:error, gettext("Нет доступа"))
     |> Phoenix.LiveView.redirect(to: ~p"/")}
  end
end
```

Ключевое свойство `live_session`: **live-навигация не пересекает границу
сессии**. Судья физически не может «patch'нуться» из своего пульта в консоль
секретаря — при попытке произойдёт полный remount с прогоном всех `on_mount`
хуков. Это структурная защита, а не «проверка, которую можно забыть». В Django
аналог — `@login_required` + ручные `is_staff`-проверки в каждой view (и в
старом ushu их местами забывали — см. pinned-спеку `judging-access-control`).

Jmix-параллель: `live_session` + `on_mount` ≈ view access policies в ролях,
только объявленные в одном месте (роутере), а не размазанные аннотациями.

### 8. PubSub + Presence глазами UI

Слой 05 определил контракт: топик `"competition"` с событиями
`{:performance_started, id}`, `{:score_saved, score_id}`,
`{:score_reopened, score_id}`, `{:performance_finalized, id}` и топик
`"monitor"` с `{:monitor_updated, %MonitorState{}}`. UI — чистый потребитель:
подписался в `mount`, получил сообщение в `handle_info`, **перечитал данные из
контекста** и перерисовался. В событии только id — никаких «жирных» полезных
нагрузок, БД остаётся единственным источником правды (решение D8).

Монитор устроен так:

```elixir
def mount(_p, _s, socket) do
  if connected?(socket), do: Phoenix.PubSub.subscribe(Ushu.PubSub, "monitor")
  # текущий снапшот живёт в GenServer'е MonitorBoard (слой 05);
  # перезапуск сервера не страшен: клиент сам переподключится,
  # mount выполнится заново и заберёт свежий снапшот
  {:ok, assign(socket, board: Ushu.Competition.MonitorBoard.get())}
end

def handle_info({:monitor_updated, %MonitorState{} = state}, socket) do
  {:noreply, assign(socket, board: state)}
end

def render(assigns) do
  ~H"""
  <div class="h-screen bg-black text-white">
    <%= case @board.mode do %>
      <% :idle -> %>       <.idle_screen title={@board.title} subtitle={@board.subtitle} />
      <% :performing -> %> <.now_performing p={@board.participation} />
      <% :scores -> %>     <.final_scores p={@board.participation} scores={@board.scores} />
      <% :standings -> %>  <.standings_board rows={@board.rows} />
    <% end %>
  </div>
  """
end
```

Сравни с Django-версией: там монитор рендерил HTML в файлы
`showme*.html` в каталоге шаблонов и раздавал их по SSE со счётчиком
`file.count`. Здесь состояние — структура в памяти GenServer'а, доставка —
обычный механизм LiveView, файловой системы в контуре нет вообще.

**Presence** — «кто онлайн» поверх PubSub: судейский пульт при connected-mount
делает `UshuWeb.Presence.track(self(), "judges", user.id, %{category: ...})`,
а консоль секретаря подписана на этот топик и в `handle_info` на
`presence_diff` обновляет панель «судьи на связи». Упал ноутбук судьи A2 —
секретарь видит это до того, как зал начнёт ждать оценку. В Django такой
возможности не было в принципе; в мире Spring пришлось бы городить
heartbeat-таблицу или трекать WebSocket-сессии руками.

### 9. gettext: русский интерфейс по умолчанию

Все строки — через `gettext`; локаль по умолчанию `ru`, вторая — `en`:

```elixir
<button>{gettext("Отправить")}</button>
put_flash(socket, :error, gettext("На ковре уже есть участник"))
```

Тонкость LiveView: локаль — состояние **процесса**. Plug выставил её для
HTTP-рендера, но live-сокет — другой процесс, поэтому есть парный
`on_mount :set_locale`, читающий локаль из сессии и вызывающий
`Gettext.put_locale/2` ещё раз (решение D11). Забудешь — мёртвый рендер будет
русским, а после подключения сокета экран «мигнёт» в английский.

---

## Решения и почему

**D1. phx.gen.auth, хирургически без почты.** Генератор даёт проверенную
session-механику (хэширование, ротация токена сессии, remember me). Писать своё
— переизобретать защиту от session fixation ради «простоты». Оставлять
почтовые потоки «на будущее» — мёртвая поверхность атаки и лишний код в
учебной кодовой базе. Регистрации нет вообще: судей заводит админ.

**D2–D3. Роли — on_mount на live_session; монитор публичный.** Плаги не
покрывают live-навигацию, поэтому охрана именно в `on_mount`. Разбиение по
ролям на разные `live_session` делает границу структурной. Монитор без логина
— осознанно: у проектора нет клавиатуры и оператора, а в снапшоте только
публичные данные зала.

**D4. Три модуля пультов, а не один с `case`.** У A, B и C разные машины
состояний (список ошибок / форма с числом / курсор по элементам) и разные
хуки. Один модуль на троих был бы «Django-view с if'ами» — тем, от чего уходим.
Общее (ожидание участника, реакция на активацию/финализацию/reopen) вынесено в
разделяемый помощник и компоненты.

**D5. Хоткеи через хуки на `event.code`.** Встроенный `phx-window-keydown`
отдаёт `event.key` — layout-зависимый символ, то есть ровно исходный баг.
30 строк своего хука против внешней библиотеки — выбор очевиден.

**D6. Форма только там, где есть форма.** B — changeset + `to_form`. A и C —
не формы: каждый тап уже событие на сервер, промежуточного «несданного
состояния формы» не существует.

**D7. Streams выборочно.** Списки — stream (память), standings — assign
(ранги пересчитываются глобально, точечные апдейты строк бессмысленны).

**D8. События тонкие, UI перечитывает БД.** Никогда не бывает «монитор показал
старую копию из события»: событие — это звонок «перечитай», а не сами данные.

**D9. Монитор = LiveView вместо самодельного SSE.** Требования pinned-спеки
`monitor-realtime` (без поллинга, без рваных чтений, без файлов, переподключение
с бэкоффом) LiveView закрывает штатно: reconnect встроен, mount перечитывает
снапшот, диффы атомарны.

**D10. Печать — HTML + `@media print`.** Протокол печатается браузером;
PDF-генератор — тяжёлая зависимость без выгоды для принтера в зале.

**D11. Локаль в сессии, выставляется дважды** (plug + on_mount) — см. выше.

Компромиссы, о которых стоит помнить: LiveView требует живого соединения —
при обрыве Wi-Fi пульт на секунды «замирает» (клиент переподключится сам, и
Presence покажет обрыв секретарю); каждая клавиша C-судьи — это round-trip до
сервера, но сервер стоит в том же зале, RTT по LAN — миллисекунды.

---

## Как это соотносится с Django-версией

| Django (старый ushu) | Elixir/Phoenix (этот слой) |
|---|---|
| Судейские экраны опрашивают сервер таймером (`setInterval` + reversed URL) | Пульт подписан на PubSub `"competition"`; экран меняется push'ем без опроса |
| Монитор: HTML-файлы `showme*.html` + `file.count` + самодельный SSE | `MonitorLive` читает `%MonitorState{}` из GenServer'а и подписан на `"monitor"`; файловой системы нет |
| Хоткеи по `event.key` — ломались на русской раскладке | Хуки на `event.code` (`KeyV`/`KeyC`/`KeyX`, `Space`) — физическая клавиша, раскладка не важна |
| C-судья мог отправить карточку с неотмеченными элементами (баг из pinned-спеки) | Submit выключен, пока есть `:pending`; сервер (слой 04) дублирует запрет |
| Права: `is_staff`/`is_superuser` + ручные проверки в каждой view (местами забытые) | Роли `admin`/`main_judge`/`judge`; `on_mount`-гарды на `live_session` — забыть негде |
| Логин Django с email-полями «в нагрузку» | phx.gen.auth, адаптированный до username+password; почтовых потоков нет как маршрутов |
| Reopen только как «открыть судью» без следа | Reopen per-judge (включая B — пункт из zametka.txt), с подтверждением и записью в `score_events` |
| Секретарь не видит, кто из судей на связи | Панель Presence: онлайн/офлайн каждого судьи в реальном времени |
| No-show = `FINISHED` с `finalscore == 0` (сентинель) | Явное состояние `:no_show`; в standings и протоколе — без ранга |
| Протокол: экспорт/шаблоны с ручными правками | `PrintLive` + `@media print`; ранги только по `:finished` |
| Интерфейс — жёстко зашитые строки (частично узбекские в шаблонах) | gettext: `ru` по умолчанию, `en` вторая; брендинг монитора из `EVENT_TITLE`/`EVENT_SUBTITLE` |
| Валидация B-оценки: `_to_float` молча превращал мусор в 0.0 | Changeset + `to_form`: мусор не проходит, кнопка выключена, 0.00 — валидный голос |

Маршруты (для ориентира): `/login`, `/judge` (авто-выбор пульта по категории
судьи), `/scores` (главный судья), `/secretary`, `/users`, `/print/:tablo_id`
(админ), `/monitor` (без логина).

---

## Что почитать

- LiveView: жизненный цикл, assigns, bindings —
  <https://hexdocs.pm/phoenix_live_view/Phoenix.LiveView.html>
- Change tracking и HEEx — <https://hexdocs.pm/phoenix_live_view/assigns-eex.html>
- Функциональные компоненты — <https://hexdocs.pm/phoenix_live_view/Phoenix.Component.html>
- Формы: `to_form`, валидация — <https://hexdocs.pm/phoenix_live_view/form-bindings.html>
- JS-хуки — <https://hexdocs.pm/phoenix_live_view/js-interop.html>
- Streams — <https://hexdocs.pm/phoenix_live_view/Phoenix.LiveView.html#stream/4>
- `live_session` и безопасность —
  <https://hexdocs.pm/phoenix_live_view/security-model.html>
- phx.gen.auth — <https://hexdocs.pm/phoenix/mix_phx_gen_auth.html>
- Presence — <https://hexdocs.pm/phoenix/Phoenix.Presence.html>
- Gettext — <https://hexdocs.pm/gettext/Gettext.html>
- `event.code` vs `event.key` (почему хоткеи не зависят от раскладки) —
  <https://developer.mozilla.org/docs/Web/API/KeyboardEvent/code>
