# -*- coding: utf-8 -*-
"""Spec tests for the corrected scoring rules (scoring-correctness capability)."""
from django.test import TestCase
from django.utils import timezone

from clubs.models import Country, Club
from elements.models import ElementCategory, ErrorCode
from judges.models import User as Judge, JUDGE_B
from participants.models import Participant, AGE_12_14
from tablo.models import Tablo, Participation, Score, WrapperErrorCode


class FakeElement:
    def __init__(self, prizemlenie, score):
        self.prizemlenie = prizemlenie
        self.score = score


class FakeStatus:
    def __init__(self, done, element):
        self.done = done
        self.element = element


def cpanel(marks_per_judge, element):
    """marks_per_judge: list of done-values, one per judge, for one element."""
    return [(True, [FakeStatus(done, element)]) for done in marks_per_judge]


class CalculateBRulesTest(TestCase):
    def setUp(self):
        self.p = Participation()

    def test_repeated_value_wins(self):
        self.assertEqual(self.p.calculateB([9.5, 9.5, 9.7, 9.8]), 9.5)

    def test_repeat_tie_breaks_to_higher(self):
        self.assertEqual(self.p.calculateB([9.5, 9.5, 9.8, 9.8]), 9.8)

    def test_three_distinct_is_middle(self):
        self.assertEqual(self.p.calculateB([7.0, 8.0, 9.0]), 8.0)

    def test_two_distinct_is_average(self):
        self.assertAlmostEqual(self.p.calculateB([9.4, 9.6]), 9.5)

    def test_single_score(self):
        self.assertEqual(self.p.calculateB([9.3]), 9.3)

    def test_none_entries_dropped_zero_kept(self):
        # a real 0.0 participates; None does not
        self.assertEqual(self.p.calculateB([None, 0.0, 0.0]), 0.0)

    def test_all_none_returns_zero(self):
        self.assertEqual(self.p.calculateB([None, None]), 0)

    def test_four_judge_parity_with_old_formula(self):
        self.assertAlmostEqual(self.p.calculateB([9.4, 9.5, 9.6, 9.7]), 9.55)


class CalculateCRulesTest(TestCase):
    def setUp(self):
        self.p = Participation()
        self.move = FakeElement(prizemlenie=False, score=0.5)

    def test_abstain_then_two_performed(self):
        # (2,1,1) -> performed, no deduction, pools full -> capped 2.0
        agreed, score = self.p.calculateC(cpanel([2, 1, 1], self.move))
        self.assertEqual(len(agreed), 1)
        self.assertEqual(agreed[0].done, 1)
        self.assertEqual(score, 2.0)

    def test_abstain_then_two_failed(self):
        # (2,0,0) -> failed, deduct 0.5 from movement pool
        agreed, score = self.p.calculateC(cpanel([2, 0, 0], self.move))
        self.assertEqual(agreed[0].done, 0)
        self.assertAlmostEqual(score, (1.4 - 0.5) + 0.6)

    def test_no_majority_excluded(self):
        # (2,1,0) -> no 2-of-3 majority -> excluded, no deduction, full pools
        agreed, score = self.p.calculateC(cpanel([2, 1, 0], self.move))
        self.assertEqual(agreed, [])
        self.assertEqual(score, 2.0)

    def test_single_real_vote_excluded(self):
        # (2,2,1) -> only one real vote -> benefit of the doubt, excluded
        agreed, score = self.p.calculateC(cpanel([2, 2, 1], self.move))
        self.assertEqual(agreed, [])
        self.assertEqual(score, 2.0)


class GetBScoreRulesTest(TestCase):
    def setUp(self):
        country = Country.objects.create(name_ru='R', name_en='R',
                                         name_ru_short='R', name_en_short='R')
        club = Club.objects.create(name='C', country=country)
        cat = ElementCategory.objects.create(name='nanquan')
        participant = Participant.objects.create(
            name_ru='I', name_en='I', sex=0, age=AGE_12_14, club=club)
        tablo = Tablo.objects.filter(category=cat, age=AGE_12_14, sex=0).first()
        self.prtn = Participation.objects.create(
            participant=participant, tablo=tablo)
        self.judge = Judge.objects.create(username='b1', category=JUDGE_B,
                                          last_login=timezone.now())

    def test_no_input_returns_none(self):
        s = Score.objects.create(judge=self.judge, participation=self.prtn,
                                 bclass=None)
        self.assertIsNone(s.get_b_score())

    def test_zero_is_a_real_vote(self):
        s = Score.objects.create(judge=self.judge, participation=self.prtn,
                                 bclass=0.0)
        self.assertEqual(s.get_b_score(), 0.0)

    def test_deduction_clamped_at_zero(self):
        s = Score.objects.create(judge=self.judge, participation=self.prtn,
                                 bclass=0.5)
        ec = ErrorCode.objects.create(name='big', number=80, value=2.0)
        s.berrors.add(WrapperErrorCode.objects.create(error_code=ec))
        self.assertEqual(s.get_b_score(), 0.0)
