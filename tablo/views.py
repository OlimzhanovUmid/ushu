import json, os
from django.db import transaction
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import TemplateView, View
from django.views.generic.detail import SingleObjectMixin
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib import messages

from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.template.response import TemplateResponse
from django.contrib.auth import login as auth_login

from core.views import LoginRequiredMixin
from judges.models import User as Judge, JUDGE_A, JUDGE_B, JUDGE_C, JUDGE_CATEGORIES
from clubs.models import Club
from elements.models import ElementCategory, Combination, ErrorCode
from participants.models import (Participant, SEX_CHOICES,
                                 AGE_7_12, AGE_13_15,
                                 AGE_16_18, AGE_19, AGE_7_9)
from tablo.models import (Participation, Tablo, PS_WAITING,
                          PS_DOING, Score, WrapperErrorCode,
                          ElementStatus, PS_FINISHED)

from django.template import loader, Context, Template
from django.conf import settings

# Create your views here.
MONITOR_FL_COUNT = os.path.join(settings.BASE_DIR, 'tablo/templates/tablo/file.count')
GROUPS = {AGE_19 : '',
            AGE_16_18:'A',
            AGE_13_15:'B',
            AGE_7_12:'C',
            AGE_7_9:'C',}

def render_to_file(template, context, flname='showme.html'):
    SHOWME = os.path.join(settings.BASE_DIR, 'tablo/templates/tablo/')
    SHOWME = os.path.join(SHOWME, flname)
    open(SHOWME, "w").write(loader.render_to_string(template, context))

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
    request.current_app=current_app
    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Okay, security check complete. Log the user in.
            auth_login(request, user)
            redirect_to = reverse('judge_view') if not redirect_to else redirect_to
            return HttpResponseRedirect(redirect_to)
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
        self.sex  = POST.get('radio_sex', None)
        self.age  = POST.get('radio_age', None)
        self.name = POST.get('fullname', None)
        self.categories = []
        for k,v in POST.items():
            if k[:len(self.prefix)] == self.prefix:
                self.categories.append( int(k[len(self.prefix):]) )
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
        p = Participant.objects.create(name_en=self.name,sex=self.sex,
                                       age=self.age, club_id=int(self.club))
        categories = ElementCategory.objects.filter(pk__in=self.categories)
        ptn = Participation.objects.assign_participation(p, categories)
        return p

    def post(self, request, *args, **kwargs):
        if self.validate(request, *args, **kwargs):
            ptn = self.save()
            if int(ptn.age) in (AGE_7_12, AGE_13_15,AGE_7_9):
                return HttpResponseRedirect(reverse_lazy(self.b_and_c))
            else:
                return HttpResponseRedirect( reverse_lazy(self.not_b_and_c,args=(ptn.pk,)))
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
        p = Participant.objects.get(pk=pk)

        context = super(PntElementView, self).get_context_data(**kwargs)
        combinations = Combination.objects.all().prefetch_related('elements')
        combinations = sorted(combinations,key=lambda x:x.__unicode__())
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
                    elems[cat.pk].append({'name':cmb.__unicode__(), 'pk':cmb.pk})

        for k,v in elems.items():
            elems[k] = json.dumps(v)

        context['cat_items'] = elems
        return context

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        p = Participant.objects.get(pk=pk)

        POST = request.POST
        tablos = {}
        categories = {}
        participations = Participation.objects.filter(participant=p)

        for k,v in POST.items():
            if k.startswith('cat-'):
                splitted = k.split('-')
                category = int(splitted[1])
                if not categories.get(category, None):
                    categories[category] = []
                order = int(splitted[2])
                combination = Combination.objects.get(pk=int(v))
                categories[category].append( (order, combination) )

        for k in categories.keys():
            categories[k] = sorted(categories[k], key=lambda x:x[0])

        with transaction.atomic():
            for prt in participations:
                cat = prt.tablo.category.pk
                if cat not in categories:
                    continue
                combinations = categories[cat]
                scores = Score.objects.filter(judge__category=JUDGE_C,participation=prt)
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
    prijoks = list(filter(lambda x: x.done and (not x.element.prizemlenie), valids))
    e4 = len( list(filter(lambda x: x.element.score > 0.3, prijoks) ))
    e3 = len( list(filter(lambda x: x.element.score > 0.2, prijoks) ))
    e2 = len( list(filter(lambda x: x.element.score > 0.1, prijoks) ))
    return (e4,e3,e2)

def cmp(u1, u2):
    BIG = 100000
    if u1.state != PS_FINISHED or u2.state != PS_FINISHED:
        k1 = u1.finalscore * BIG - u1.order
        k2 = u2.finalscore * BIG - u2.order
        return int(k1)-int(k2)

    if u1.finalscore != u2.finalscore:
        return int(u1.finalscore*BIG) - int(u2.finalscore*BIG)

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
        return sorted(uchastniki, cmp=cmp, reverse=True)

class TabloDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'tablo/tablo_detail.html'
    model = Tablo

    def get_tablo(self):
        pk = self.kwargs.get('pk', None)
        GET = self.request.GET
        sex = GET.get('sex')
        age = GET.get('age')
        return Tablo.objects.get(category=pk, sex=sex, age=age)

    def get_context_data(self, **kwargs):
        self.object = None

        tablo = self.get_tablo()

        context = super(TabloDetailView, self).get_context_data(**kwargs)
        uchastniki = Participation.objects.filter(tablo=tablo)
        if tablo.started:
            uchastniki = uchastniki.order_by('-finalscore', '-order')
            uchastniki = sort(uchastniki)
            i = 1
            for u in uchastniki:
                if u.state == PS_FINISHED:
                    u.rank = i
                else:
                    u.rank = None
                i = i + 1
            count = len(uchastniki)
        else:
            uchastniki = uchastniki.order_by('-order')
            count = uchastniki.count()

        context['is_group'] = ('group' == tablo.category.name.lower())

        in_process = Participation.objects.filter(state=PS_DOING).exists()
        if not in_process:
            for u in uchastniki:
                if u.state == PS_WAITING:
                    context['active_pk'] = u.pk
                    break

        group = GROUPS[tablo.age]
        sex = SEX_CHOICES[tablo.sex][1]
        context['title'] = "%s Group %s\'s %s" % (group, sex.translate('en'),
                                                  tablo.category.name)
        context['participations'] = uchastniki
        context['tablo'] = tablo
        context['count'] = count
        return context

class TabloMonitorView(TabloDetailView):
    def get_tablo(self):
        pk = self.kwargs.get('pk', None)
        return Tablo.objects.get(pk=pk)

    def get(self, request, *args, **kwargs):
        ref = request.META['HTTP_REFERER']
        context = self.get_context_data(**kwargs)
        count = context['count']
        count = int((count+5)/6.0)
        if not count:
            count = 1
        open(MONITOR_FL_COUNT, "w").write(str(count))
        counter = 0
        for i in range(0,count):
            tmp = context.copy()
            tmp['participations'] = context['participations'][ i*6:i*6+6]
            render_to_file('tablo/monitor_tablo.html', tmp, flname='showme%s.html'%counter)
            counter = counter + 1
        return HttpResponseRedirect(ref)

class TabloPrintView(TabloDetailView):
    template_name = 'tablo/tablo_print.html'

    def get_tablo(self):
        pk = self.kwargs.get('pk', None)
        return Tablo.objects.get(pk=pk)

class JudgeScoreView(LoginRequiredMixin, TemplateView):
    JUDGE_TEMPLATES = {JUDGE_A :'a',
                        JUDGE_B :'b',
                        JUDGE_C :'c',}
    def get_template_names(self):
        judge = self.request.user
        if judge.category not in (JUDGE_A, JUDGE_B, JUDGE_C,):
            return None
        template_name = 'tablo/judge_%s.html'
        return template_name % JUDGE_TEMPLATES[judge.category]


from django.core.cache import caches
def gl_activate_participant(participation):
    c = caches['default']
    for sc in Score.objects.filter(participation=participation):
        c.set( str(sc.judge_id), sc.saved, 15)

def gl_deactivate_participant(participation,judge):
    c = caches['default']
    c.set(str(judge.id), False, 15)

def gl_reopen_participant(participation,judge):
    c = caches['default']
    c.set( str(judge.id), True, 15)

def gl_has_active_participant(judge):
    # c = caches['default']
    # if c.get(str(judge.id), True):
    #     doing = Score.objects.filter(participation__state=PS_DOING,judge=judge,saved=False)
    #     if doing.exists():
    #         c.set( str(judge.id), True, 15 )
    #     else:
    #         c.set( str(judge.id), False, 15 )

    #return c.get(str(judge.id), False)

    return Score.objects.filter(participation__state=PS_DOING,judge=judge,saved=False).exists()

def gl_deactivate_all_participant():
    c = caches['default']
    c.clear()

class ParticipantActivateView(LoginRequiredMixin, View):
    def get_object(self):
        obj = Participation.objects \
                .select_related('participant', 'tablo') \
                .filter(state=PS_DOING)
        if obj:
            return obj[0]
        else:
            return None

    def render_monitor(self):
        template = 'tablo/monitor_doing.html'
        p = self.get_object()
        group = GROUPS[p.tablo.age]
        sex = SEX_CHOICES[p.tablo.sex][1]
        title = "%s Group %s\'s %s" % (group, sex.translate('en'),
                                                  p.tablo.category.name)
        c = Context({
            'title' : title,
            'participation' : p
        })
        open(MONITOR_FL_COUNT, "w").write("1")
        render_to_file(template, c, flname="showme0.html")
        return None

    def get(self, request, *args, **kwargs):
        ref = request.META.get('HTTP_REFERER', None)
        pk = request.GET.get('pk')
        p = Participation.objects.get(pk=pk)
        p.state = PS_DOING
        p.save()
        gl_activate_participant(p)
        self.render_monitor()
        if ref:
            return HttpResponseRedirect(ref)
        else:
            return HttpResponseRedirect(reverse_lazy('current_score'))

class ParticipantScoreView(LoginRequiredMixin, TemplateView):
    template_name = 'tablo/scores.html'

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        obj = Participation.objects.select_related('participant', 'tablo').get(pk=pk)
        return obj

    def get_context_data(self, **kwargs):
        obj = self.get_object()
        if not obj:
            return {}
        context = super(ParticipantScoreView, self).get_context_data(**kwargs)
        group = GROUPS[obj.participant.age]
        sex = SEX_CHOICES[obj.participant.sex][1]
        context['title'] = "%s Group %s\'s %s" % (group, sex.translate('en'),
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
                rank = rank+1
                if u.pk == obj.pk:
                    break
            context['rank'] = rank
        return context

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        ref = request.META['HTTP_REFERER']
        if 'save' in request.POST.keys() or 'notavailable' in request.POST.keys():
            bonus = int(request.POST.get('bonus', 0))
            obj.bonus = True if bonus == 1 else False

            with transaction.atomic():
                if 'notavailable' in request.POST.keys():
                    scores = {'final':0}
                    Score.objects.filter(participation=obj.pk).update(saved=True)
                    gl_deactivate_all_participant()
                else:
                    scores = obj.get_scores()
                obj.finalscore = scores['final']
                obj.state = PS_FINISHED
                obj.save()
                gl_deactivate_all_participant()
            kwargs['pk'] = obj.pk
            return HttpResponseRedirect(reverse('participant_score',kwargs={'pk':obj.pk}))
        elif 'reopen' in request.POST.keys():
            Score.objects.filter(participation=obj.pk).update(saved=False)
            gl_activate_participant(obj)
        elif 'monitor' in request.POST.keys():
            if Score.objects.filter(participation=obj.pk,saved=False).exists():
                return HttpResponseRedirect(ref)
            kwargs.update({'get_rank':True})
            open(MONITOR_FL_COUNT, "w").write("1")
            render_to_file('tablo/monitor_score.html', self.get_context_data(**kwargs), flname="showme0.html")
        return HttpResponseRedirect(ref)

class CurrentParticipantScoreView(ParticipantScoreView):
    def get_object(self):
        obj = Participation.objects \
                .select_related('participant', 'tablo') \
                .filter(state=PS_DOING)
        if obj:
            return obj[0]
        else:
            return None

import itertools
class JudgeView(LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super(JudgeView, self).get_context_data(**kwargs)
        judge = self.request.user

        doing = Participation.objects.filter(state=PS_DOING)
        if doing:
            p = doing[0]
            s = Score.objects.filter(judge=self.request.user, participation=p)
            if s:
                context['score'] = s[0]
            group = GROUPS[p.tablo.age]
            sex = SEX_CHOICES[p.tablo.sex][1]
            context['title'] = "%s Group %s\'s %s" % (group, sex.translate('en'),
                                                      p.tablo.category.name)
        iterator = itertools.count()
        context['left_title'] = judge.username
        self.request.iterator = iterator
        return context

    def get_template_names(self, **kwargs):
        doing = Participation.objects.filter(state=PS_DOING)
        in_process = doing.exists()
        if not in_process:
            return 'tablo/judge_empty.html'

        p = doing[0]
        s = Score.objects.filter(judge=self.request.user, participation=p)
        # sometimes judge C will enter but there will be no
        # C items, just show empty
        if not s or s[0].saved:
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


class JudgeASubmit(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        POST = request.POST
        p = Participation.objects.filter(state=PS_DOING)[0]
        s = Score.objects.filter(participation=p, judge=request.user)[0]
        v = POST.getlist('error', [])
        with transaction.atomic():
            s.aclass.all().delete()
            if v:
                for i in v:
                    try:
                        num = int(i)
                        if (num < 10 or num > 79): # belongs to cat B
                            if not num >= 90:
                                continue
                        e = ErrorCode.objects.get(number=num)
                        w = WrapperErrorCode.objects.create(error_code=e)
                        s.aclass.add(w)
                    except Exception as e:
                        pass

            s.saved = True
            s.save()
            gl_deactivate_participant(p,request.user)
            return HttpResponseRedirect(reverse('judge_view'))


class JudgeBSubmit(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        POST = request.POST
        p = Participation.objects.filter(state=PS_DOING)[0]
        s = Score.objects.filter(participation=p, judge=request.user)[0]
        v = POST.get('score', None)
        errors = POST.getlist('error', [])

        with transaction.atomic():
            s.berrors.all().delete()
            if v:
                s.bclass = float(v)
            if errors:
                for i in errors:
                    try:
                        num = int(i)
                        if not (num < 10 or num > 79):
                            continue
                        e = ErrorCode.objects.get(number=int(i))
                        w = WrapperErrorCode.objects.create(error_code=e)
                        s.berrors.add(w)
                    except Exception as e:
                        pass

            s.saved = True
            s.save()
            gl_deactivate_participant(p,request.user)
            return HttpResponseRedirect(reverse('judge_view'))


class JudgeCSubmit(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        POST = request.POST
        p = Participation.objects.filter(state=PS_DOING)[0]
        s = Score.objects.filter(participation=p, judge=request.user)[0]
        fill_again = False
        with transaction.atomic():
            for k,v in POST.items():
                try:
                    pk = int(k)
                except:
                    continue
                el = ElementStatus.objects.get(pk=pk)
                el.done = int(v)
                fill_again |= (el.done == 2)
                el.save()
            if fill_again:
                s.saved = False
            else:
                s.saved = True
            s.save()
            if s.saved:
                gl_deactivate_participant(p,request.user)
        return HttpResponseRedirect(reverse('judge_view'))


class JrebiView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        POST = request.POST
        tablo_id = POST.get('tablo', None)
        ref = request.META['HTTP_REFERER']
        if not tablo_id:
            return HttpResponseRedirect(ref)

        tablo = Tablo.objects.get(pk=tablo_id)
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
                    counter = counter+1
            return HttpResponseRedirect(ref)

        return HttpResponseRedirect(ref)

class MonitorView(TemplateView):
    template_name = 'tablo/monitor.html'

class ShowmeView(TemplateView):
    template_name = 'tablo/showme.html'

    def get_template_names(self):
        page = self.request.GET.get('page', 0)
        return 'tablo/showme%s.html' % page

def showme_view(request):
    try:
        counter = open(MONITOR_FL_COUNT,"r").read()
        counter = int(counter)
    except:
        counter = 1

    SHOWME = os.path.join(settings.BASE_DIR, 'tablo/templates/tablo/')
    res = []
    for i in range(0,counter):
        flname = os.path.join(SHOWME, 'showme%s.html'%i)
        fl = open(flname, "r").read()
        res.append({'idx':i, 'content':fl})
    res = sorted(res, key=lambda x:x['idx'])
    return HttpResponse(json.dumps(res), content_type='application/json')


class CounterView(TemplateView):
    template_name = 'tablo/showme.html'

    def get_template_names(self):
        page = self.request.GET.get('page', 0)
        if page == 0:
            return self.template_name
        else:
            return 'tablo/showme%s.html' % page



from django.conf import settings
class LanguageViewEn(View):
    def get(self, request, *args, **kwargs):
        ref = request.META['HTTP_REFERER']
        resp = HttpResponseRedirect(ref)
        resp.set_cookie(settings.LANGUAGE_COOKIE_NAME, 'en-US')
        return resp

class LanguageViewRu(View):
    def get(self, request, *args, **kwargs):
        ref = request.META['HTTP_REFERER']
        resp = HttpResponseRedirect(ref)
        resp.set_cookie(settings.LANGUAGE_COOKIE_NAME, 'ru-RU')
        return resp

def has_updated(request):
    res = {'result':gl_has_active_participant(request.user)}
    return HttpResponse(json.dumps(res), content_type='application/json')

def open_judge(request, idx):
    p = Participation.objects.filter(state=PS_DOING)[0]
    qs = Score.objects.filter(participation=p.pk).select_related('judge').order_by('judge__username')
    idx = int(idx)
    if idx < qs.count():
        item = qs[idx]
        Score.objects.filter(pk=item.pk).update(saved=False)
        gl_reopen_participant(p, item.judge)
    return HttpResponseRedirect(reverse_lazy('current_score'))

def delete_participation(request, pk):
    judge = request.user
    if judge.is_staff:
        with transaction.atomic():
            Score.objects.filter(participation=pk).delete()
            Participation.objects.filter(pk=pk).delete()
    ref = request.META['HTTP_REFERER']
    return HttpResponseRedirect(ref)