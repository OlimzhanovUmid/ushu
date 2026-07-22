import json
import math

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.db import IntegrityError, transaction
from django.http import (HttpResponseRedirect, HttpResponse,
                         HttpResponseForbidden, JsonResponse,
                         StreamingHttpResponse)
from django.template import loader
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, View

from clubs.models import Club
from core.views import LoginRequiredMixin, StaffRequiredMixin, staff_required
from elements.models import ElementCategory, Combination, ErrorCode
from judges.models import JUDGE_A, JUDGE_B, JUDGE_C, JUDGE_CATEGORIES
from participants.models import (Participant, SEX_CHOICES,
                                 AGE_9_11, AGE_12_14,
                                 AGE_15_17, AGE_18_plus, AGE_7_8, AGE_11, AGE_CHOICES)
from tablo.models import (Participation, Tablo, PS_WAITING,
                          PS_DOING, Score, WrapperErrorCode,
                          ElementStatus, PS_FINISHED)
from tablo.monitor_state import monitor_state

# Create your views here.
GROUPS = {AGE_18_plus: '',
          AGE_15_17: 'A',
          AGE_12_14: 'B',
          AGE_9_11: 'C',
          AGE_7_8: 'C',
          AGE_11: 'C'}


def publish_monitor_pages(template, contexts):
    """Render every page fully, then publish atomically.

    If any page fails to render (e.g. a missing flag), nothing is published and
    the previous snapshot stays on the projector — no torn/half updates.
    """
    pages = [loader.render_to_string(template, ctx) for ctx in contexts]
    monitor_state.publish(pages)


def redirect_back(request, fallback='tablo_list'):
    '''Redirect to the page the request came from.

    Falls back to a named route when the browser sends no Referer header
    (direct navigation, programmatic clients) instead of raising KeyError
    on ``request.META['HTTP_REFERER']``.
    '''
    target = request.META.get('HTTP_REFERER') or reverse(fallback)
    return HttpResponseRedirect(target)


def get_current_participation():
    '''The single participant currently on the carpet (state DOING), or None.

    Replaces the fragile ``filter(state=PS_DOING)[0]`` used across the views,
    which raised IndexError whenever the main judge finalized while a judge's
    form was still open.
    '''
    return (Participation.objects
            .select_related('participant', 'tablo', 'tablo__category')
            .filter(state=PS_DOING)
            .first())


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='tablo/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))
    request.current_app = current_app
    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Okay, security check complete. Log the user in.
            auth_login(request, user)
            safe = redirect_to and url_has_allowed_host_and_scheme(
                redirect_to, allowed_hosts={request.get_host()},
                require_https=request.is_secure())
            return HttpResponseRedirect(redirect_to if safe else reverse('judge_view'))
    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context)


class ParticipantCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'tablo/participant_create.html'
    b_and_c = 'paticipant_create'
    not_b_and_c = 'pnt_element'
    prefix = 'cat-'

    def validate(self, request, *arg, **kwargs):
        POST = request.POST
        self.errors = []
        self.club = POST.get('club', None)
        self.sex = POST.get('radio_sex', None)
        self.age = POST.get('radio_age', None)
        self.name = POST.get('fullname', None)
        self.categories = []
        for k, v in POST.items():
            if k[:len(self.prefix)] == self.prefix:
                self.categories.append(int(k[len(self.prefix):]))
        res = True
        if not self.club:
            self.errors.append('Please choose club')
            res = False
        if not self.sex:
            self.errors.append('Please choose sex')
            res = False
        if not self.age:
            self.errors.append('Please choose age')
            res = False
        if not self.name:
            self.errors.append('Please give name')
            res = False
        if not self.categories:
            self.errors.append('Please select categories')
            res = False
        return res

    def save(self):
        p = Participant.objects.create(name_en=self.name, sex=self.sex,
                                       age=self.age, club_id=int(self.club))
        categories = ElementCategory.objects.filter(pk__in=self.categories)
        ptn = Participation.objects.assign_participation(p, categories)
        return p

    def post(self, request, *args, **kwargs):
        if self.validate(request, *args, **kwargs):
            ptn = self.save()
            if int(ptn.age) in (AGE_9_11, AGE_11, AGE_12_14, AGE_7_8):
                return HttpResponseRedirect(reverse_lazy(self.b_and_c))
            else:
                return HttpResponseRedirect(reverse_lazy(self.not_b_and_c, args=(ptn.pk,)))
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ParticipantCreateView, self).get_context_data(**kwargs)
        if hasattr(self, 'errors'):
            for error in self.errors:
                messages.error(self.request, error)
        context['clubs'] = Club.objects.all().select_related('country').order_by('pk')
        context['elementcategories'] = ElementCategory.objects.all().order_by('pk')
        context['prefix'] = self.prefix
        return context


class PntElementView(LoginRequiredMixin, TemplateView):
    template_name = 'tablo/pnt_element.html'
    success_url = reverse_lazy('paticipant_create')

    def get_context_data(self, **kwargs):
        pk = kwargs.get('pk')
        p = get_object_or_404(Participant, pk=pk)

        context = super(PntElementView, self).get_context_data(**kwargs)
        combinations = Combination.objects.all().prefetch_related('elements')
        combinations = sorted(combinations, key=lambda x: x.__str__())
        # context['options'] = json.dumps([
        #                                 {'name':c.__unicode__(), 'pk':c.pk}
        #                                 for c in combinations
        #                                 ])
        ps = Participation.objects.filter(participant=p).select_related('tablo')
        categories = [t.tablo.category for t in ps]
        categories = filter(
            lambda x: not ('group' in x.name.lower() or 'duilian' in x.name.lower()),
            categories)
        context['categories'] = list(categories)

        elems = {}
        for cat in context['categories']:
            elems.setdefault(cat.pk, [])

        for cmb in combinations:
            elem = cmb.elements.all().prefetch_related('categories')[0]
            for cat in context['categories']:
                if cat in elem.categories.all():
                    # elems.setdefault(cat.pk, [])
                    elems[cat.pk].append({'name': cmb.__str__(), 'pk': cmb.pk})

        for k, v in elems.items():
            elems[k] = json.dumps(v)

        context['cat_items'] = elems
        return context

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        p = get_object_or_404(Participant, pk=pk)

        POST = request.POST
        tablos = {}
        categories = {}
        participations = Participation.objects.filter(participant=p)

        for k, v in POST.items():
            if k.startswith('cat-'):
                splitted = k.split('-')
                category = int(splitted[1])
                if not categories.get(category, None):
                    categories[category] = []
                order = int(splitted[2])
                combination = Combination.objects.get(pk=int(v))
                categories[category].append((order, combination))

        for k in categories.keys():
            categories[k] = sorted(categories[k], key=lambda x: x[0])

        with transaction.atomic():
            for prt in participations:
                cat = prt.tablo.category.pk
                if cat not in categories:
                    continue
                combinations = categories[cat]
                scores = Score.objects.filter(judge__category=JUDGE_C, participation=prt)
                for score in scores:
                    for c in combinations:
                        score.add_combination(c[1])

        return HttpResponseRedirect(self.success_url)


class TabloListView(LoginRequiredMixin, TemplateView):
    template_name = 'tablo/tablo_list.html'

    def get_context_data(self, **kwargs):
        context = super(TabloListView, self).get_context_data(**kwargs)
        context['elementcategories'] = ElementCategory.objects.all().order_by('pk')
        return context


def counts(valids):
    # done is tri-state; only a decided-performed movement (done == 1) counts
    # toward the high-value-element tie-break (untouched/failed must not).
    prijoks = list(filter(lambda x: x.done == 1 and (not x.element.prizemlenie), valids))
    e4 = len(list(filter(lambda x: x.element.score > 0.3, prijoks)))
    e3 = len(list(filter(lambda x: x.element.score > 0.2, prijoks)))
    e2 = len(list(filter(lambda x: x.element.score > 0.1, prijoks)))
    return e4, e3, e2


def cmp(u1, u2):
    BIG = 100000
    if u1.state != PS_FINISHED or u2.state != PS_FINISHED:
        k1 = u1.finalscore * BIG - u1.order
        k2 = u2.finalscore * BIG - u2.order
        return int(k1) - int(k2)

    if u1.finalscore != u2.finalscore:
        return int(u1.finalscore * BIG) - int(u2.finalscore * BIG)

    # when equal items
    elems1 = u1.get_scores()
    elems2 = u2.get_scores()
    e4_1, e3_1, e2_1 = counts(elems1['final_c'][0])
    e4_2, e3_2, e2_2 = counts(elems2['final_c'][0])

    if e4_1 != e4_2:
        return e4_1 - e4_2
    if e3_1 != e3_2:
        return e3_1 - e3_2
    if e2_1 != e2_2:
        return e2_1 - e2_2
    return 0


import functools


def sort(uchastniki):
    try:
        return sorted(uchastniki, key=functools.cmp_to_key(cmp), reverse=True)
    except Exception as e:
        raise e


class TabloDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'tablo/tablo_detail.html'
    model = Tablo

    def get_tablo(self):
        pk = self.kwargs.get('pk', None)
        GET = self.request.GET
        sex = GET.get('sex')
        age = GET.get('age')
        # 404 (not 500) when params are missing/blank or no Tablo matches
        return get_object_or_404(Tablo, category=pk, sex=sex, age=age)

    def get_context_data(self, **kwargs):
        self.object = None

        tablo = self.get_tablo()

        context = super(TabloDetailView, self).get_context_data(**kwargs)
        uchastniki = Participation.objects.filter(tablo=tablo)
        if tablo.started:
            uchastniki = uchastniki.order_by('-finalscore', '-order')
            uchastniki = sort(uchastniki)
            # rank only finished participants; unfinished/no-shows get no place
            # (and must not consume a place number)
            i = 1
            for u in uchastniki:
                if u.state == PS_FINISHED:
                    u.rank = i
                    i = i + 1
                else:
                    u.rank = None
            count = len(uchastniki)
        else:
            uchastniki = uchastniki.order_by('-order')
            count = uchastniki.count()

        context['is_group'] = ('group' == tablo.category.name.lower())

        in_process = Participation.objects.filter(state=PS_DOING).exists()
        context['in_process'] = in_process
        if not in_process:
            for u in uchastniki:
                if u.state == PS_WAITING:
                    context['active_pk'] = u.pk
                    break

        group = GROUPS[tablo.age]
        sex = SEX_CHOICES[tablo.sex][1]
        context['title'] = "%s Group %s's %s %s y.o." % (group, sex,
                                                         tablo.category.name,
                                                         AGE_CHOICES[tablo.age][1])
        context['participations'] = uchastniki
        context['tablo'] = tablo
        context['count'] = count
        return context


class TabloMonitorView(StaffRequiredMixin, TabloDetailView):
    def get_tablo(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(Tablo, pk=pk)

    PARTICIPANTS_PER_SCREEN = 6

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        participations = context['participations']
        per_screen = self.PARTICIPANTS_PER_SCREEN
        screen_count = max(1, math.ceil(context['count'] / per_screen))
        contexts = []
        for screen in range(screen_count):
            page = context.copy()
            page['participations'] = participations[screen * per_screen:(screen + 1) * per_screen]
            contexts.append(page)
        publish_monitor_pages('tablo/monitor_tablo.html', contexts)
        return redirect_back(request)


class TabloPrintView(TabloDetailView):
    template_name = 'tablo/tablo_print.html'

    def get_tablo(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(Tablo, pk=pk)


def judge_has_pending_score(judge):
    '''True if this judge still has an unsaved score for the active participant.

    The judge screens poll ``has_update`` to reload when this flips. (Replaces
    the vestigial ``gl_*`` locmem-cache helpers, which nothing read.)
    '''
    return Score.objects.filter(
        participation__state=PS_DOING, judge=judge, saved=False).exists()


class ParticipantActivateView(StaffRequiredMixin, View):
    def get_object(self):
        return get_current_participation()

    def render_monitor(self):
        p = self.get_object()
        group = GROUPS[p.tablo.age]
        sex = SEX_CHOICES[p.tablo.sex][1]
        title = "%s Group %s's %s %s y.o." % (group, sex,
                                              p.tablo.category.name,
                                              AGE_CHOICES[p.tablo.age][1])
        publish_monitor_pages('tablo/monitor_doing.html',
                              [{'title': title, 'participation': p}])

    def post(self, request, *args, **kwargs):
        pk = request.POST.get('pk')
        # exactly one participant may be DOING; app-level check plus (once the
        # migration lands) the partial unique index on state=DOING as backstop.
        if Participation.objects.filter(state=PS_DOING).exists():
            messages.error(request, _('Another participant is already performing.'))
            return redirect_back(request)
        try:
            with transaction.atomic():
                updated = Participation.objects.filter(
                    pk=pk, state=PS_WAITING).update(state=PS_DOING)
        except IntegrityError:
            messages.error(request, _('Another participant is already performing.'))
            return redirect_back(request)
        if not updated:
            messages.error(request, _('Cannot activate: the participant is not waiting.'))
            return redirect_back(request)
        p = self.get_object()
        if p is not None:
            self.render_monitor()
        return redirect_back(request, fallback='current_score')


class ParticipantScoreView(LoginRequiredMixin, TemplateView):
    template_name = 'tablo/scores.html'

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return (Participation.objects
                .select_related('participant', 'tablo', 'tablo__category')
                .filter(pk=pk).first())

    def get_context_data(self, **kwargs):
        obj = self.get_object()
        if not obj:
            return super(ParticipantScoreView, self).get_context_data(**kwargs)
        context = super(ParticipantScoreView, self).get_context_data(**kwargs)
        group = GROUPS[obj.participant.age]
        sex = SEX_CHOICES[obj.participant.sex][1]
        context['title'] = "%s Group %s's %s" % (group, sex,
                                                 obj.tablo.category.name)
        context['participant'] = obj.participant
        context['participation'] = obj
        context['is_group'] = obj.group
        context['scores'] = obj.get_scores()
        context['show_c'] = (obj.participant.age == 2 or obj.participant.age == 3) and not obj.group

        # rank
        if kwargs.get('get_rank', None):
            uchastniki = Participation.objects.filter(tablo=obj.tablo)
            uchastniki = uchastniki.order_by('-finalscore', '-order')
            uchastniki = sort(uchastniki)
            rank = 0
            for u in uchastniki:
                rank = rank + 1
                if u.pk == obj.pk:
                    break
            context['rank'] = rank
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden('Staff only')
        obj = self.get_object()
        if obj is None:
            messages.info(request, _('The participant was already finalized.'))
            return redirect_back(request)
        ref = request.META.get('HTTP_REFERER') or reverse('tablo_list')
        if 'save' in request.POST or 'notavailable' in request.POST:
            obj.bonus = request.POST.get('bonus') == '1'
            with transaction.atomic():
                if 'notavailable' in request.POST:
                    Score.objects.filter(participation=obj.pk).update(saved=True)
                    obj.finalscore = 0
                else:
                    obj.finalscore = obj.get_scores()['final']
                obj.state = PS_FINISHED
                obj.save()
            return HttpResponseRedirect(reverse('participant_score', kwargs={'pk': obj.pk}))
        elif 'reopen' in request.POST:
            Score.objects.filter(participation=obj.pk).update(saved=False)
        elif 'monitor' in request.POST:
            if Score.objects.filter(participation=obj.pk, saved=False).exists():
                return HttpResponseRedirect(ref)
            kwargs.update({'get_rank': True, 'pk': obj.pk})
            publish_monitor_pages('tablo/monitor_score.html',
                                  [self.get_context_data(**kwargs)])
        return HttpResponseRedirect(ref)


class CurrentParticipantScoreView(ParticipantScoreView):
    def get_object(self):
        return get_current_participation()


class JudgeView(LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super(JudgeView, self).get_context_data(**kwargs)
        judge = self.request.user

        p = get_current_participation()
        if p is not None:
            s = Score.objects.filter(judge=self.request.user, participation=p).first()
            if s is not None:
                context['score'] = s
            group = GROUPS[p.tablo.age]
            sex = SEX_CHOICES[p.tablo.sex][1]
            context['title'] = "%s Group %s's %s %s y.o." % (group, sex,
                                                             p.tablo.category.name,
                                                             AGE_CHOICES[p.tablo.age][1])
        context['left_title'] = judge.username
        return context

    def get_template_names(self, **kwargs):
        p = get_current_participation()
        if p is None:
            return 'tablo/judge_empty.html'

        s = Score.objects.filter(judge=self.request.user, participation=p).first()
        # sometimes judge C will enter but there will be no
        # C items, just show empty
        if s is None or s.saved:
            return 'tablo/judge_empty.html'

        judge = self.request.user
        if judge.category == JUDGE_A:
            return 'tablo/judgea.html'
        elif judge.category == JUDGE_B:
            return 'tablo/judgeb.html'
        elif judge.category == JUDGE_C:
            return 'tablo/judgec.html'
        return None

    def get(self, request, *args, **kwargs):
        judge = self.request.user
        if judge.is_staff:
            return HttpResponseRedirect(reverse_lazy('paticipant_create'))
        return super(JudgeView, self).get(request, *args, **kwargs)


def _judge_score_or_redirect(request):
    '''Resolve (participation, own score) for a judge submit, or a redirect.

    Returns (participation, score, None) on success, or (None, None, response)
    when there is no active participant / no score card for this judge — so the
    submit views never 500 on the finalize-while-open race.
    '''
    p = get_current_participation()
    if p is None:
        messages.info(request, _('The participant was already finalized.'))
        return None, None, HttpResponseRedirect(reverse('judge_view'))
    s = Score.objects.filter(participation=p, judge=request.user).first()
    if s is None:
        return None, None, HttpResponseRedirect(reverse('judge_view'))
    return p, s, None


class JudgeASubmit(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        p, s, redirect = _judge_score_or_redirect(request)
        if redirect is not None:
            return redirect
        invalid = []
        with transaction.atomic():
            s.aclass.all().delete()
            for raw in request.POST.getlist('error', []):
                try:
                    num = int(raw)
                except (TypeError, ValueError):
                    invalid.append(raw)
                    continue
                # A-technical errors are numbered 1-79 or shared 90+
                if not ((1 <= num <= 79) or num >= 90):
                    invalid.append(raw)
                    continue
                try:
                    ec = ErrorCode.objects.get(number=num)
                except ErrorCode.DoesNotExist:
                    invalid.append(raw)
                    continue
                s.aclass.add(WrapperErrorCode.objects.create(error_code=ec))
            s.saved = True
            s.save()
        if invalid:
            messages.warning(request, _('Ignored invalid error codes: %s')
                             % ', '.join(str(x) for x in invalid))
        return HttpResponseRedirect(reverse('judge_view'))


class JudgeBSubmit(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        p, s, redirect = _judge_score_or_redirect(request)
        if redirect is not None:
            return redirect
        raw_score = request.POST.get('score')
        if raw_score not in (None, ''):
            try:
                s.bclass = float(raw_score)
            except (TypeError, ValueError):
                messages.error(request, _('Invalid score value.'))
                return HttpResponseRedirect(reverse('judge_view'))
        invalid = []
        with transaction.atomic():
            s.berrors.all().delete()
            for raw in request.POST.getlist('error', []):
                try:
                    num = int(raw)
                except (TypeError, ValueError):
                    invalid.append(raw)
                    continue
                if 1 <= num <= 79:  # A-technical range, not valid for B
                    invalid.append(raw)
                    continue
                try:
                    ec = ErrorCode.objects.get(number=num)
                except ErrorCode.DoesNotExist:
                    invalid.append(raw)
                    continue
                s.berrors.add(WrapperErrorCode.objects.create(error_code=ec))
            s.saved = True
            s.save()
        if invalid:
            messages.warning(request, _('Ignored invalid error codes: %s')
                             % ', '.join(str(x) for x in invalid))
        return HttpResponseRedirect(reverse('judge_view'))


class JudgeCSubmit(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        p, s, redirect = _judge_score_or_redirect(request)
        if redirect is not None:
            return redirect
        # IDOR guard: only element statuses reachable from THIS judge's own
        # score card may be updated; posted pks are matched against them.
        owned = {es.pk: es
                 for cs in s.cclass.all()
                 for es in cs.statuses.all()}
        with transaction.atomic():
            for key, value in request.POST.items():
                try:
                    pk = int(key)
                except (TypeError, ValueError):
                    continue
                es = owned.get(pk)
                if es is None:
                    continue  # not this judge's element -> ignore
                try:
                    done = int(value)
                except (TypeError, ValueError):
                    continue
                if done not in (0, 1, 2):
                    continue
                es.done = done
                es.save()
            # completeness gate: every element must be marked before saving.
            if any(es.done == 2 for es in owned.values()):
                s.saved = False
                s.save()
                messages.error(request, _('Mark every element before submitting.'))
                return HttpResponseRedirect(reverse('judge_view'))
            s.saved = True
            s.save()
        return HttpResponseRedirect(reverse('judge_view'))


class JrebiView(StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        POST = request.POST
        tablo_id = POST.get('tablo', None)
        ref = request.META.get('HTTP_REFERER') or reverse('tablo_list')
        if not tablo_id:
            return HttpResponseRedirect(ref)

        tablo = get_object_or_404(Tablo, pk=tablo_id)
        if tablo.started:
            return HttpResponseRedirect(ref)

        if 'save' in POST.keys():
            tablo.started = True
            tablo.save()
            return HttpResponseRedirect(ref)
        elif 'stop' in POST.keys():
            with transaction.atomic():
                participations = Participation.objects.filter(tablo=tablo).order_by('?')
                participations = [i for i in participations]
                counter = 0
                for p in participations:
                    p.order = counter
                    p.save()
                    counter = counter + 1
            return HttpResponseRedirect(ref)

        return HttpResponseRedirect(ref)


class MonitorView(TemplateView):
    template_name = 'tablo/monitor.html'

    def get_context_data(self, **kwargs):
        context = super(MonitorView, self).get_context_data(**kwargs)
        context['event_title'] = settings.EVENT_TITLE
        context['event_subtitle'] = settings.EVENT_SUBTITLE
        return context


def monitor_stream(request):
    """Server-Sent Events stream of monitor snapshots.

    Sends the current snapshot immediately, then one event per publish. A 15s
    keepalive comment holds the connection open through idle periods; the
    ``retry`` directive tells the browser to reconnect no faster than 3s.
    """
    def event_stream():
        yield 'retry: 3000\n\n'
        last_revision = -1
        while True:
            revision, pages = monitor_state.wait_for_change(last_revision, timeout=15)
            if revision != last_revision:
                last_revision = revision
                payload = json.dumps({'revision': revision, 'pages': pages})
                yield 'event: snapshot\ndata: %s\n\n' % payload
            else:
                yield ': keepalive\n\n'

    response = StreamingHttpResponse(event_stream(),
                                     content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


class _SetLanguageView(View):
    '''Switch the active language, then return to the previous page.'''
    language_code = None

    def get(self, request, *args, **kwargs):
        response = redirect_back(request)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, self.language_code)
        return response


class LanguageViewEn(_SetLanguageView):
    language_code = 'en-US'


class LanguageViewRu(_SetLanguageView):
    language_code = 'ru-RU'


@login_required
def has_updated(request):
    return JsonResponse({'result': judge_has_pending_score(request.user)})


@staff_required
@require_POST
def open_judge(request, idx):
    p = get_current_participation()
    if p is None:
        return HttpResponseRedirect(reverse_lazy('current_score'))
    qs = (Score.objects.filter(participation=p.pk)
          .select_related('judge').order_by('judge__username'))
    idx = int(idx)
    if 0 <= idx < qs.count():
        item = qs[idx]
        Score.objects.filter(pk=item.pk).update(saved=False)
    return HttpResponseRedirect(reverse_lazy('current_score'))


@staff_required
@require_POST
def delete_participation(request, pk):
    with transaction.atomic():
        Score.objects.filter(participation=pk).delete()
        Participation.objects.filter(pk=pk).delete()
    return redirect_back(request)
