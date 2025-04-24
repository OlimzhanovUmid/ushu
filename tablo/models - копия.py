from collections import Counter
from django.db import models, transaction
from django.dispatch import receiver
from sortedm2m.fields import SortedManyToManyField

from judges.models import (User as Judge, JUDGE_C, JUDGE_CATEGORIES,
                           JUDGE_A, JUDGE_B)
from elements.models import Element, ElementCategory, ErrorCode
from participants.models import (Participant, AGE_CHOICES, SEX_CHOICES,
                                 AGE_7_12,AGE_13_15, AGE_7_9)

# Create your models here.
PS_WAITING  = 0
PS_DOING    = 1
PS_FINISHED = 2
PARTICIPATION_STATES = (
    (PS_WAITING,    'waiting'),
    (PS_DOING,      'doing'),
    (PS_FINISHED,   'finished'),
)

try:
    from itertools import izip
    izip = izip
except:
    izip = zip
    

class Tablo(models.Model):
    age = models.IntegerField(choices=AGE_CHOICES)
    sex = models.IntegerField(choices=SEX_CHOICES)
    category = models.ForeignKey(ElementCategory)
    started = models.BooleanField(default=False) # True if jrebi already done
    started = models.BooleanField(default=False) 
    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '%s - %s - %s' % (self.category.name,
                                 AGE_CHOICES[self.age][1],
                                 SEX_CHOICES[self.sex][1])

@receiver(models.signals.post_save, sender=ElementCategory)
def create_tablo(sender, instance, **kwargs):
    for age in AGE_CHOICES:
        if (age[0] == AGE_7_12 or age[0] == AGE_7_9) and instance.seven_twelve is False:
            continue
        for sex in SEX_CHOICES:
            if not Tablo.objects.filter(age=age[0], sex=sex[0], category=instance).exists():
                Tablo.objects.create(age=age[0], sex=sex[0], category=instance)

@receiver(models.signals.pre_delete, sender=ElementCategory)
def delete_tablo(sender, instance, **kwargs):
    '''
    not 100% correct API since deletion of category should be rare
    '''
    pk = instance.pk
    Tablo.objects.filter(category=pk).delete()

class ParticipationManager(models.Manager):

    @transaction.atomic
    def assign_participation(self, participant, category):
        '''
        participant - uchastnik chempionata
        category - nanquan, jinshu, daishu,....
        '''
        age = int(participant.age)
        sex = int(participant.sex)
        for tablo in Tablo.objects.filter(age=age, sex=sex, category=category):
            group = False
            cat_name = tablo.category.name.lower()
            if cat_name == 'group':
                group = True
            if group:
                # if there is one participant which belongs to club
                # then no need to create participation,
                # we can use already created participation as group
                has_prtn = Participation.objects \
                                .filter(tablo=tablo,
                                        participant__club=participant.club,
                                        group=True) \
                                .exists()
                if has_prtn:
                    continue
            p = Participation(participant=participant, tablo=tablo,
                          order=0,
                          state=PARTICIPATION_STATES[PS_WAITING][0],
                          finalscore=0,
                          group=group)
            p.save()
            # superuser is admin of system
            judges = Judge.objects.filter(is_superuser=False)
            for judge in judges:
                if (age == AGE_7_9 or age == AGE_7_12 or age == AGE_13_15) and judge.category == JUDGE_C:
                    # no C class judges
                    continue

                if cat_name in ('group', 'duilian',) and judge.category == JUDGE_C:
                    continue

                # is_staff used for Main judge
                # he can only handle reopening and saving final result
                if judge.is_staff:
                    continue

                Score.objects.create(judge=judge, participation=p, saved=False)
        return participant

    @transaction.atomic
    def assign_combinations(self, participation, combinations):
        '''
        participation - participation id
        combinations - Combination model items in ordered way
        '''
        scores = Score.objects.filter(judge__category=JUDGE_C, participation=participation)
        # optimize below code if necessary
        for score in scores:
            for combination in combinations:
                combs = CombinationStatus.objects.create()
                score.cclass.add(combs)
                for element in combination.elements.all():
                    e = ElementStatus.objects.create(element=element)
                    combs.statuses.add(e)
        return participation


class Participation(models.Model):
    participant = models.ForeignKey(Participant, db_index=True)
    tablo       = models.ForeignKey(Tablo, db_index=True)
    order       = models.IntegerField(default=0) # order in this Tablo, used for jrebiy
    state       = models.IntegerField(choices=PARTICIPATION_STATES, default=0, db_index=True)
    finalscore  = models.FloatField(default=0)
    bonus       = models.BooleanField(default=False)
    group       = models.BooleanField(default=False)

    objects = ParticipationManager()

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '%s (%s) (%s)' % (self.participant.name_en, self.tablo.category.name, self.participant.get_age_display())

    def get_scores(self):
        LETTERS = {JUDGE_A : 'a', JUDGE_B : 'b', JUDGE_C : 'c'}
        scores = Score.objects.filter(participation=self) \
                        .select_related('judge') \
                        .prefetch_related('aclass', 'cclass') \
                        .order_by('judge__username')
        
        allow_save = True
        if self.state == PS_FINISHED and self.finalscore == 0:
            items = {LETTERS[JUDGE_A]:[[],[],[]],
                LETTERS[JUDGE_B]:[0,0,0],
                LETTERS[JUDGE_C]:[(True,[]),(True,[]),(True,[])],
                'final_a':([], 0),
                'final_b':0,
                'final_c':([], 0),
                'final':0,
                'bonus':self.bonus,
                'can_be_saved':False}
            return items

        items = {LETTERS[JUDGE_A]:[],
                LETTERS[JUDGE_B]:[],
                LETTERS[JUDGE_C]:[],
                'final_a':None,
                'final_b':None,
                'final_c':None,
                'final':0,
                'bonus':None,
                'can_be_saved':False}
        
        for score in scores:
            allow_save = allow_save and score.saved
            category = score.judge.category
            letter = LETTERS[category]
            if category == JUDGE_B:
                items[letter].append(score.get_b_score())
            elif category == JUDGE_A:
                errors = []
                for error in score.aclass.all():
                    errors.append(error)
                items[letter].append(errors)
            elif category == JUDGE_C:
                dones = []
                for combination in score.cclass.all():
                    for element in combination.statuses.all():
                        dones.append(element)
                items[letter].append((score.saved, dones))
        items['final_a'] = int(self.calculateA(items['a']) * 100)
        items['final_b'] = int(self.calculateB(items['b']) * 100)
        if self.bonus:
            items['final_b'] = items['final_b'] + 5
        items['final_c'] = int(self.calculateC(items['c']) * 100)

        items['final'] = sum( [ items['final_a'][1], items['final_b'], items['final_c'][1] ] )
        items['saved'] = (self.state == PS_FINISHED)
        items['can_be_saved'] = allow_save
        items['bonus'] = self.bonus
        return items

    def calculateA(self, scores):
        '''
        return tuple(validated_error_codes, score)
        '''
        valids = []
        errors1 = [i.error_code for i in scores[0]]
        errors2 = [i.error_code for i in scores[1]]
        errors3 = [i.error_code for i in scores[2]]
        for i in errors1:
            has = False
            if i in errors2:
                has = True
                errors2.remove(i)
            if i in errors3:
                has=True
                errors3.remove(i)
            if has:
                valids.append(i)

        for j in errors2:
            has = False
            if j in errors3:
                has=True
                errors3.remove(j)
                valids.append(j)
        res = 0
        for error in valids:
            res = res + error.value
        return (valids, 5.0-res)

    def calculateB(self, scores):
        scores = filter(lambda x:x, scores)
        scores = list(scores)
        if not scores or len(scores) < 1:
            return 0
        biggest = max(scores)
        least = min(scores)
        counter = Counter(scores)
        counter.subtract( Counter(list(set(scores))) )
        counter += Counter() # keep only bigger than 0
        if len(counter) % 2 == 0:
            return (sum(scores)-biggest-least)/2
        else:
            most_common = counter.most_common(1)[0]
            return most_common[0]

    def calculateC(self, scores):
        '''
        input (savedBoolean, scores)
        return tuple(validate_done_elements, score)
        '''
        valids = []
        if not scores:
            return ([], 0)
        for i in izip(scores[0][1], scores[1][1], scores[2][1]):
            if i[0].done == i[1].done:
                valids.append(i[0])
            elif i[0].done == i[2].done:
                valids.append(i[0])
            elif i[1].done == i[2].done:
                valids.append(i[1])

        PRIEM_MAX = 1.4
        PRZ_MAX = 0.6
        curr_priem = 1.4
        curr_prz = 0.6
        for v in valids:
            element = v.element
            if element.prizemlenie:
                curr_prz = curr_prz - (0 if v.done else element.score)
            else:
                curr_priem = curr_priem - (0 if v.done else element.score)

        curr_priem = max(0, curr_priem)
        curr_prz = max(0, curr_prz)

        score = sum([curr_prz, curr_priem])
        score = min(score, 2.0)
        return (valids, score)

    def is_saved(self):
        return PS_FINISHED == self.state

class ElementStatus(models.Model):
    element = models.ForeignKey(Element)
    done = models.IntegerField(default=2)

    def get_id(self):
        return str(self.done)

    def get_label(self):
        if self.done == 2:
            return "label-blue"
        elif self.done == 1:
            return "label-orange"
        return "label-black"

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '%s (%s)' % (self.element.name, self.done)

class CombinationStatus(models.Model):
    statuses = SortedManyToManyField(ElementStatus)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return ' + '.join([ '%s (%s)' % (e.element.name, e.done) for e in self.statuses.all()])

class WrapperErrorCode(models.Model):
    error_code = models.ForeignKey(ErrorCode)

class Score(models.Model):
    judge = models.ForeignKey(Judge)
    participation = models.ForeignKey(Participation)
    aclass = models.ManyToManyField(WrapperErrorCode)
    bclass = models.FloatField(blank=True, null=True)
    berrors = models.ManyToManyField(WrapperErrorCode, related_name='berrors')
    cclass = SortedManyToManyField(CombinationStatus)
    saved = models.BooleanField(default=False)

    def add_combination(self, combination):
        cs = CombinationStatus.objects.create()
        for e in combination.elements.all():
            es = ElementStatus.objects.create(element=e)
            cs.statuses.add(es)
        self.cclass.add(cs)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return 'judge(%s) - p(%s) - t(%s)' % (JUDGE_CATEGORIES[self.judge.category][1],
                                      self.participation.participant.name_en, self.participation.tablo)

    def a_error_count(self):
        return self.aclass.all().count()

    def get_c_is_reopen(self):
        try:
            el = self.cclass.all()[0].statuses.all()[0]
            if el and el.done == 2:
                return False
        except:
            return False
        return True


    def get_max_comb_count(self):
        # assuming this is C category judge
        #return
        if not hasattr(self, '_cache_count'):
            counter = 0
            for comb in self.cclass.all():
                for e in comb.statuses.all():
                    counter += 1
            self._cache_count = counter 
        return self._cache_count

    def get_b_score(self):
        score = self.bclass
        for berror in self.berrors.all():
            try:
                er = float(berror.error_code.value)
            except:
                er = 0
            try:
                score = float(score)
            except:
                score = 0
            score = score - er
        if not score:
            return score
        return round(score,2)








