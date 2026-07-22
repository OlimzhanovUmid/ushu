from collections import Counter

from django.db import models, transaction
from django.dispatch import receiver
from sortedm2m.fields import SortedManyToManyField

from elements.models import Element, ElementCategory, ErrorCode
from judges.models import (User as Judge, JUDGE_C, JUDGE_CATEGORIES,
                           JUDGE_A, JUDGE_B)
from participants.models import (Participant, AGE_CHOICES, SEX_CHOICES,
                                 AGE_9_11, AGE_12_14, AGE_7_8, AGE_18_plus, AGE_11)

# Create your models here.
PS_WAITING = 0
PS_DOING = 1
PS_FINISHED = 2
PARTICIPATION_STATES = (
    (PS_WAITING, 'waiting'),
    (PS_DOING, 'doing'),
    (PS_FINISHED, 'finished'),
)


class Tablo(models.Model):
    age = models.IntegerField(choices=AGE_CHOICES)
    sex = models.IntegerField(choices=SEX_CHOICES)
    category = models.ForeignKey(ElementCategory, on_delete=models.CASCADE)
    started = models.BooleanField(default=False)  # True if jrebi already done

    class Meta:
        verbose_name = 'табло'
        verbose_name_plural = 'табло'
        constraints = [
            models.UniqueConstraint(
                fields=['age', 'sex', 'category'],
                name='uniq_tablo_age_sex_category'),
        ]

    def __str__(self):
        return f'{self.category.name} - {AGE_CHOICES[self.age][1]} - {SEX_CHOICES[self.sex][1]}'


@receiver(models.signals.post_save, sender=ElementCategory)
def create_tablo(sender, instance, **kwargs):
    for age in AGE_CHOICES:
        for sex in SEX_CHOICES:
            if not Tablo.objects.filter(age=age[0], sex=sex[0], category=instance).exists():
                Tablo.objects.create(age=age[0], sex=sex[0], category=instance)


# Deleting an ElementCategory removes its Tablos via the category FK's
# on_delete=CASCADE; no explicit pre_delete signal needed.


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
            # superuser is admin of system; deactivated judges get no card
            judges = Judge.objects.filter(is_superuser=False, is_active=True)
            for judge in judges:
                if (age == AGE_11
                    or age == AGE_7_8
                    or age == AGE_9_11
                    or age == AGE_12_14
                ) and judge.category == JUDGE_C:
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
    participant = models.ForeignKey(Participant, db_index=True, on_delete=models.CASCADE)
    tablo = models.ForeignKey(Tablo, db_index=True, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)  # order in this Tablo, used for jrebiy
    state = models.IntegerField(choices=PARTICIPATION_STATES, default=0, db_index=True)
    finalscore = models.FloatField(default=0)
    bonus = models.BooleanField(default=False)
    group = models.BooleanField(default=False)

    objects = ParticipationManager()

    class Meta:
        verbose_name = 'участие'
        verbose_name_plural = 'участия'
        constraints = [
            models.UniqueConstraint(
                fields=['participant', 'tablo'],
                name='uniq_participation_participant_tablo'),
            # at most one participant on the carpet at a time
            models.UniqueConstraint(
                fields=['state'], condition=models.Q(state=PS_DOING),
                name='uniq_one_doing_participation'),
        ]

    def __str__(self):
        return f'{self.participant.name_en} ({self.tablo.category.name}) ({self.participant.get_age_display()})'

    def get_scores(self):
        # memoize per instance: the ranking tie-break sort calls this O(n log n)
        # times over the same participations within one request.
        if hasattr(self, '_scores_cache'):
            return self._scores_cache
        letters = {JUDGE_A: 'a', JUDGE_B: 'b', JUDGE_C: 'c'}
        scores = Score.objects.filter(participation=self) \
            .select_related('judge') \
            .prefetch_related('aclass__error_code', 'berrors__error_code',
                              'cclass__statuses__element') \
            .order_by('judge__username')

        allow_save = True
        if self.state == PS_FINISHED and self.finalscore == 0:
            items = {letters[JUDGE_A]: [[], [], []],
                     letters[JUDGE_B]: [0, 0, 0],
                     letters[JUDGE_C]: [(True, []), (True, []), (True, [])],
                     'final_a': ([], 0),
                     'final_b': 0,
                     'final_c': ([], 0),
                     'final': 0,
                     'bonus': self.bonus,
                     'can_be_saved': False}
            self._scores_cache = items
            return items

        items = {letters[JUDGE_A]: [],
                 letters[JUDGE_B]: [],
                 letters[JUDGE_C]: [],
                 'final_a': None,
                 'final_b': None,
                 'final_c': None,
                 'final': 0,
                 'bonus': None,
                 'can_be_saved': False}

        for score in scores:
            allow_save = allow_save and score.saved
            category = score.judge.category
            letter = letters[category]
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
        items['final_a'] = self.calculateA(items['a'], age=self.participant.age)
        items['final_b'] = round(self.calculateB(items['b']) * 100)
        if self.bonus:
            items['final_b'] = items['final_b'] + 5
        items['final_c'] = self.calculateC(items['c'])

        items['final'] = sum([items['final_a'][1] * 100, items['final_b'], items['final_c'][1] * 100])
        items['final'] = round(items['final'] / 100.0, 2)
        items['final_b'] = round(items['final_b'] / 100.0, 2)
        items['saved'] = (self.state == PS_FINISHED)
        items['can_be_saved'] = allow_save
        items['bonus'] = self.bonus
        self._scores_cache = items
        return items

    # --- scoring rules (maximum scores each judge category awards) ---
    MAX_A_SCORE = 7.0          # technical (A) maximum, juniors
    MAX_A_SCORE_ADULT = 5.0    # technical (A) maximum, 18+
    MAX_MOVEMENT_SCORE = 1.4   # C-pool for "priem" (movements)
    MAX_LANDING_SCORE = 0.6    # C-pool for "prizemlenie" (landings)
    MAX_C_SCORE = 2.0          # overall C cap

    def calculateA(self, judge_error_lists, age):
        '''Aggregate the three A-judges' error lists into a final A-score.

        An error counts only when at least two of the three judges report
        it (majority agreement). The agreed errors' values are summed and
        subtracted from the age-dependent maximum score.

        :param judge_error_lists: three lists of objects exposing
            ``.error_code`` (one per A-judge).
        :param age: participant age bucket; adults get a lower maximum.
        :return: tuple ``(agreed_errors, score)``.
        '''
        errors_by_judge = [
            [wrapper.error_code for wrapper in error_list]
            for error_list in judge_error_lists
        ]
        agreed_errors = self._errors_agreed_by_majority(errors_by_judge)
        deduction = sum(error.value for error in agreed_errors)
        max_score = self.MAX_A_SCORE_ADULT if age == AGE_18_plus else self.MAX_A_SCORE
        return agreed_errors, max_score - deduction

    @staticmethod
    def _errors_agreed_by_majority(errors_by_judge):
        '''Errors reported by at least two of the three A-judges.

        Matched entries are consumed, so repeated errors pair one-to-one.
        '''
        first, second, third = errors_by_judge
        agreed = []
        for error in first:
            in_second = error in second
            in_third = error in third
            if in_second:
                second.remove(error)
            if in_third:
                third.remove(error)
            if in_second or in_third:
                agreed.append(error)
        # remaining agreement between the second and third judges only
        for error in second:
            if error in third:
                third.remove(error)
                agreed.append(error)
        return agreed

    def calculateB(self, raw_scores):
        '''Aggregate the B-judges' numeric scores (panel-size independent).

        Only judges who did not submit (``None``) are dropped; a real 0.00
        counts. If any value was awarded by at least two judges, that value
        wins (ties broken by the higher value). Otherwise the highest and
        lowest are trimmed and the remaining scores averaged. For the
        standard four-judge panel with distinct scores this is identical to
        the historical ``(sum - max - min) / 2``.
        '''
        scores = [score for score in raw_scores if score is not None]
        if not scores:
            return 0
        counts = Counter(scores)
        repeated = {value: n for value, n in counts.items() if n >= 2}
        if repeated:
            top = max(repeated.values())
            return max(value for value, n in repeated.items() if n == top)
        n = len(scores)
        if n == 1:
            return scores[0]
        if n == 2:
            return sum(scores) / 2
        return (sum(scores) - max(scores) - min(scores)) / (n - 2)

    def calculateC(self, judge_status_lists):
        '''Aggregate the three C-judges' per-element done/not-done marks.

        For each element the majority verdict wins. A failed element
        deducts its score from the matching pool (landing vs movement);
        the combined pools are capped at :attr:`MAX_C_SCORE`.

        :param judge_status_lists: three ``(saved, statuses)`` tuples whose
            ``statuses`` expose ``.done`` and ``.element``.
        :return: tuple ``(agreed_statuses, score)``.
        '''
        if not judge_status_lists:
            return [], 0
        statuses_per_judge = [statuses for _saved, statuses in judge_status_lists]

        movement_pool = self.MAX_MOVEMENT_SCORE
        landing_pool = self.MAX_LANDING_SCORE
        agreed = []
        # done is tri-state: 1 performed, 0 failed, 2 untouched (abstention).
        # An element is decided only when at least two judges actually marked
        # it the same way; an untouched mark never counts as performed.
        for marks in zip(*statuses_per_judge):
            performed = [s for s in marks if s.done == 1]
            failed = [s for s in marks if s.done == 0]
            if len(performed) >= 2:
                agreed.append(performed[0])  # decided performed, no deduction
            elif len(failed) >= 2:
                loser = failed[0]
                agreed.append(loser)
                if loser.element.prizemlenie:
                    landing_pool -= loser.element.score
                else:
                    movement_pool -= loser.element.score
            # otherwise no majority -> excluded (benefit of the doubt)

        score = max(0, landing_pool) + max(0, movement_pool)
        return agreed, min(score, self.MAX_C_SCORE)

    def is_saved(self):
        return PS_FINISHED == self.state


class ElementStatus(models.Model):
    element = models.ForeignKey(Element, on_delete=models.PROTECT)
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
        return f'{self.element.name} ({self.done})'


class CombinationStatus(models.Model):
    statuses = SortedManyToManyField(ElementStatus)

    def __str__(self):
        return ' + '.join([f'{e.element.name} ({e.done})' for e in self.statuses.all()])


class WrapperErrorCode(models.Model):
    error_code = models.ForeignKey(ErrorCode, on_delete=models.PROTECT)


class Score(models.Model):
    judge = models.ForeignKey(Judge, on_delete=models.PROTECT)
    participation = models.ForeignKey(Participation, on_delete=models.CASCADE)
    aclass = models.ManyToManyField(WrapperErrorCode)
    bclass = models.FloatField(blank=True, null=True)
    berrors = models.ManyToManyField(WrapperErrorCode, related_name='berrors')
    cclass = SortedManyToManyField(CombinationStatus)
    saved = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'оценка судьи'
        verbose_name_plural = 'оценки судей'
        constraints = [
            models.UniqueConstraint(
                fields=['judge', 'participation'],
                name='uniq_score_judge_participation'),
        ]

    def add_combination(self, combination):
        cs = CombinationStatus.objects.create()
        for e in combination.elements.all():
            es = ElementStatus.objects.create(element=e)
            cs.statuses.add(es)
        self.cclass.add(cs)

    def __str__(self):
        return f'judge({JUDGE_CATEGORIES[self.judge.category][1]}) - p({self.participation.participant.name_en}) - t({self.participation.tablo})'

    def a_error_count(self):
        return self.aclass.all().count()

    def get_c_is_reopen(self):
        try:
            first_status = self.cclass.all()[0].statuses.all()[0]
        except IndexError:
            return False
        # done == 2 is the untouched default; anything else means the
        # judge already scored and the card has been reopened.
        return not (first_status and first_status.done == 2)

    def get_max_comb_count(self):
        # assumes this is a C-category judge's score card
        if not hasattr(self, '_cache_count'):
            self._cache_count = sum(
                combination.statuses.count()
                for combination in self.cclass.all()
            )
        return self._cache_count

    @staticmethod
    def _to_float(value):
        '''Best-effort float conversion; non-numeric values become 0.0.'''
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def get_b_score(self):
        '''B-judge base score minus the value of each recorded B-error.

        Returns ``None`` only when the judge entered nothing at all (no base
        score and no errors); a legitimate 0.00 is a real vote and is kept.
        Deductions never drive the score below 0.
        '''
        berrors = list(self.berrors.all())
        if self.bclass is None and not berrors:
            return None
        score = self._to_float(self.bclass)
        for berror in berrors:
            score -= self._to_float(berror.error_code.value)
        return round(max(0.0, score), 2)
