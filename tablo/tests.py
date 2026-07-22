# -*- coding: utf-8 -*-
"""Regression tests for the core scoring business logic in tablo.

These lock current behaviour so dependency upgrades can be verified safe.
The pure scoring methods (calculateA/B/C) do not touch the DB, so they are
exercised with lightweight fake objects; manager/signal/ORM behaviour is
exercised against the test database.
"""
from django.test import TestCase
from django.utils import timezone

from clubs.models import Country, Club
from elements.models import Element, ElementCategory, ErrorCode, Combination
from judges.models import (User as Judge, JUDGE_A, JUDGE_B, JUDGE_C)
from participants.models import Participant, AGE_18_plus, AGE_12_14, AGE_11
from tablo.models import (Tablo, Participation, Score, ElementStatus,
                          WrapperErrorCode, PS_WAITING, PS_FINISHED)


# --- fakes for the pure scoring functions -----------------------------------

class FakeErrorCode(object):
    """Stands in for elements.ErrorCode; identity-equality is what matters."""
    def __init__(self, value):
        self.value = value


class FakeWrap(object):
    """Stands in for WrapperErrorCode (has .error_code)."""
    def __init__(self, error_code):
        self.error_code = error_code


class FakeElement(object):
    def __init__(self, prizemlenie, score):
        self.prizemlenie = prizemlenie
        self.score = score


class FakeStatus(object):
    """Stands in for ElementStatus (has .done and .element)."""
    def __init__(self, done, element):
        self.done = done
        self.element = element


def p():
    """A Participation instance is enough to call the un-saved methods."""
    return Participation()


def make_judge(**kw):
    # last_login is NOT NULL in the historical schema; set it explicitly.
    kw.setdefault('last_login', timezone.now())
    judge = Judge(**kw)
    judge.save()
    return judge


# --- calculateA -------------------------------------------------------------

class CalculateATest(TestCase):
    def test_no_agreement_returns_full_score(self):
        a, b, c = FakeErrorCode(1.0), FakeErrorCode(1.0), FakeErrorCode(1.0)
        scores = [[FakeWrap(a)], [FakeWrap(b)], [FakeWrap(c)]]
        valids, score = p().calculateA(scores, age=AGE_12_14)
        self.assertEqual(valids, [])
        self.assertEqual(score, 7.0)

    def test_all_three_agree_deducts_once(self):
        ec = FakeErrorCode(1.5)
        scores = [[FakeWrap(ec)], [FakeWrap(ec)], [FakeWrap(ec)]]
        valids, score = p().calculateA(scores, age=AGE_12_14)
        self.assertEqual(valids, [ec])
        self.assertEqual(score, 5.5)

    def test_majority_two_of_three_counts(self):
        ec = FakeErrorCode(2.0)
        other = FakeErrorCode(9.0)
        scores = [[FakeWrap(ec)], [FakeWrap(ec)], [FakeWrap(other)]]
        valids, score = p().calculateA(scores, age=AGE_12_14)
        self.assertEqual(valids, [ec])
        self.assertEqual(score, 5.0)

    def test_agreement_only_between_judges_two_and_three(self):
        ec = FakeErrorCode(1.0)
        scores = [[], [FakeWrap(ec)], [FakeWrap(ec)]]
        valids, score = p().calculateA(scores, age=AGE_12_14)
        self.assertEqual(valids, [ec])
        self.assertEqual(score, 6.0)

    def test_adult_max_score_is_five(self):
        a, b, c = FakeErrorCode(1.0), FakeErrorCode(1.0), FakeErrorCode(1.0)
        scores = [[FakeWrap(a)], [FakeWrap(b)], [FakeWrap(c)]]
        _, score = p().calculateA(scores, age=AGE_18_plus)
        self.assertEqual(score, 5.0)


# --- calculateB -------------------------------------------------------------

class CalculateBTest(TestCase):
    def test_empty_returns_zero(self):
        self.assertEqual(p().calculateB([]), 0)

    def test_all_falsy_returns_zero(self):
        self.assertEqual(p().calculateB([0, 0, 0]), 0)

    def test_three_distinct_no_majority(self):
        # No repeated value -> trimmed mean (sum - max - min) / (n - 2).
        # For 3 distinct scores that is the middle score (8.0).
        self.assertEqual(p().calculateB([7.0, 9.0, 8.0]), 8.0)

    def test_two_equal_returns_repeated_value(self):
        self.assertEqual(p().calculateB([8.0, 8.0, 9.0]), 8.0)

    def test_all_equal_returns_that_value(self):
        self.assertEqual(p().calculateB([8.5, 8.5, 8.5]), 8.5)


# --- calculateC -------------------------------------------------------------

class CalculateCTest(TestCase):
    def test_empty_returns_zero(self):
        self.assertEqual(p().calculateC([]), ([], 0))

    def test_all_done_full_score_capped_at_two(self):
        el = FakeElement(prizemlenie=False, score=0.5)
        judges = [(True, [FakeStatus(1, el)]) for _ in range(3)]
        valids, score = p().calculateC(judges)
        self.assertEqual(len(valids), 1)
        self.assertEqual(score, 2)

    def test_all_failed_deducts_element_score(self):
        el = FakeElement(prizemlenie=False, score=0.5)
        judges = [(True, [FakeStatus(0, el)]) for _ in range(3)]
        valids, score = p().calculateC(judges)
        self.assertEqual(len(valids), 1)
        # priem 1.4 - 0.5 = 0.9 ; prz 0.6 ; sum 1.5
        self.assertAlmostEqual(score, 1.5)

    def test_prizemlenie_failure_deducts_from_prz_pool(self):
        el = FakeElement(prizemlenie=True, score=0.3)
        judges = [(True, [FakeStatus(0, el)]) for _ in range(3)]
        _, score = p().calculateC(judges)
        # prz 0.6 - 0.3 = 0.3 ; priem 1.4 ; sum 1.7
        self.assertAlmostEqual(score, 1.7)


# --- DB-backed: factories ---------------------------------------------------

class ScoringDBHelper(TestCase):
    def make_country_club(self):
        country = Country.objects.create(
            name_ru='Russia', name_en='Russia',
            name_ru_short='RU', name_en_short='RU')
        return Club.objects.create(name='Club', country=country)


class GetBScoreTest(ScoringDBHelper):
    def setUp(self):
        self.club = self.make_country_club()
        self.cat = ElementCategory.objects.create(name='nanquan')
        self.participant = Participant.objects.create(
            name_ru='Ivan', name_en='Ivan', sex=0, age=AGE_12_14, club=self.club)
        tablo = Tablo.objects.filter(category=self.cat, age=AGE_12_14, sex=0).first()
        self.participation = Participation.objects.create(
            participant=self.participant, tablo=tablo)
        self.judge = make_judge(username='b1', category=JUDGE_B)

    def test_bare_score_returned(self):
        s = Score.objects.create(judge=self.judge,
                                 participation=self.participation, bclass=8.0)
        self.assertEqual(s.get_b_score(), 8.0)

    def test_berror_is_subtracted(self):
        s = Score.objects.create(judge=self.judge,
                                 participation=self.participation, bclass=8.0)
        ec = ErrorCode.objects.create(name='e', number=1, value=1.0)
        s.berrors.add(WrapperErrorCode.objects.create(error_code=ec))
        self.assertEqual(s.get_b_score(), 7.0)


# --- DB-backed: signal + manager --------------------------------------------

class TabloSignalTest(TestCase):
    def test_creating_category_creates_tablo_per_age_sex(self):
        cat = ElementCategory.objects.create(name='changquan')
        # 6 ages x 2 sexes
        self.assertEqual(Tablo.objects.filter(category=cat).count(), 12)

    def test_deleting_category_removes_tablos(self):
        cat = ElementCategory.objects.create(name='taijiquan')
        self.assertEqual(Tablo.objects.filter(category=cat).count(), 12)
        cat.delete()
        self.assertEqual(Tablo.objects.filter(category=cat.pk).count(), 0)


class AssignParticipationTest(ScoringDBHelper):
    def setUp(self):
        self.club = self.make_country_club()
        self.cat = ElementCategory.objects.create(name='nanquan')
        self.participant = Participant.objects.create(
            name_ru='Ivan', name_en='Ivan', sex=0, age=AGE_12_14, club=self.club)
        # one judge of each category, none staff/superuser
        self.ja = make_judge(username='a', category=JUDGE_A)
        self.jb = make_judge(username='b', category=JUDGE_B)
        self.jc = make_judge(username='c', category=JUDGE_C)

    def test_assign_creates_participation_and_scores(self):
        Participation.objects.assign_participation(self.participant, self.cat)
        prtn = Participation.objects.filter(participant=self.participant,
                                            tablo__category=self.cat)
        self.assertEqual(prtn.count(), 1)
        # AGE_12_14 excludes class-C judges -> only A and B get scores
        scores = Score.objects.filter(participation=prtn.first())
        self.assertEqual(scores.count(), 2)
        self.assertFalse(
            scores.filter(judge__category=JUDGE_C).exists())

    def test_staff_judge_gets_no_score(self):
        staff = make_judge(username='main', category=JUDGE_A,
                                     is_staff=True)
        Participation.objects.assign_participation(self.participant, self.cat)
        prtn = Participation.objects.get(participant=self.participant,
                                         tablo__category=self.cat)
        self.assertFalse(
            Score.objects.filter(participation=prtn, judge=staff).exists())

    def test_class_c_judge_included_for_adult(self):
        adult = Participant.objects.create(
            name_ru='Petr', name_en='Petr', sex=0, age=AGE_18_plus,
            club=self.club)
        Participation.objects.assign_participation(adult, self.cat)
        prtn = Participation.objects.get(participant=adult,
                                         tablo__category=self.cat)
        self.assertTrue(
            Score.objects.filter(participation=prtn,
                                 judge__category=JUDGE_C).exists())


class AssignCombinationsTest(ScoringDBHelper):
    def setUp(self):
        self.club = self.make_country_club()
        self.cat = ElementCategory.objects.create(name='nanquan')
        self.adult = Participant.objects.create(
            name_ru='Petr', name_en='Petr', sex=0, age=AGE_18_plus,
            club=self.club)
        self.jc = make_judge(username='c', category=JUDGE_C)
        self.el1 = Element.objects.create(name='kick', difficulty=0, score=0.5)
        self.el2 = Element.objects.create(name='punch', difficulty=1, score=0.3)

    def test_combinations_attached_to_class_c_scores(self):
        Participation.objects.assign_participation(self.adult, self.cat)
        prtn = Participation.objects.get(participant=self.adult,
                                         tablo__category=self.cat)
        comb = Combination.objects.create()
        comb.elements.add(self.el1, self.el2)
        Participation.objects.assign_combinations(prtn, [comb])
        c_score = Score.objects.get(participation=prtn,
                                    judge__category=JUDGE_C)
        self.assertEqual(c_score.cclass.count(), 1)
        self.assertEqual(c_score.get_max_comb_count(), 2)


# --- small model behaviours -------------------------------------------------

class ElementStatusLabelTest(TestCase):
    def test_labels(self):
        self.assertEqual(ElementStatus(done=2).get_label(), 'label-blue')
        self.assertEqual(ElementStatus(done=1).get_label(), 'label-orange')
        self.assertEqual(ElementStatus(done=0).get_label(), 'label-black')


class TabloStrTest(TestCase):
    def test_str_contains_category_name(self):
        cat = ElementCategory.objects.create(name='wushu')
        tablo = Tablo.objects.filter(category=cat).first()
        self.assertIn('wushu', str(tablo))
