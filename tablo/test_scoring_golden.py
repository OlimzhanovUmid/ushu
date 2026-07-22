# -*- coding: utf-8 -*-
"""Golden / characterization tests for the end-to-end scoring path.

These lock the CURRENT behaviour of ``Participation.get_scores`` and the
``counts``/``cmp``/``sort`` medal tie-break so the stabilize-django change can
show exactly which outputs it intentionally alters. Tests whose expectations
the change will flip are marked ``CHANGES IN stabilize-django``.
"""
from django.test import TestCase
from django.utils import timezone

from clubs.models import Country, Club
from elements.models import Element, ElementCategory, ErrorCode
from judges.models import User as Judge, JUDGE_A, JUDGE_B, JUDGE_C
from participants.models import Participant, AGE_12_14
from tablo.models import (Tablo, Participation, Score, ElementStatus,
                          CombinationStatus, WrapperErrorCode,
                          PS_FINISHED)
from tablo.views import counts, sort


def make_judge(username, category):
    return Judge.objects.create(username=username, category=category,
                                last_login=timezone.now())


class GoldenHelper(TestCase):
    def setUp(self):
        self.country = Country.objects.create(
            name_ru='Russia', name_en='Russia',
            name_ru_short='RU', name_en_short='RU')
        self.club = Club.objects.create(name='Club', country=self.country)
        self.cat = ElementCategory.objects.create(name='nanquan')
        # movement element (0.5) and landing element (0.3)
        self.move = Element.objects.create(name='kick', difficulty=0, score=0.5,
                                           prizemlenie=False)
        self.land = Element.objects.create(name='land', difficulty=0, score=0.3,
                                           prizemlenie=True)
        self.ec = ErrorCode.objects.create(name='wobble', number=1, value=1.0)
        self.ja = [make_judge('a1', JUDGE_A), make_judge('a2', JUDGE_A),
                   make_judge('a3', JUDGE_A)]
        self.jb = [make_judge('b1', JUDGE_B), make_judge('b2', JUDGE_B),
                   make_judge('b3', JUDGE_B), make_judge('b4', JUDGE_B)]
        self.jc = [make_judge('c1', JUDGE_C), make_judge('c2', JUDGE_C),
                   make_judge('c3', JUDGE_C)]

    def make_participation(self, age=AGE_12_14, order=0):
        participant = Participant.objects.create(
            name_ru='P', name_en='P', sex=0, age=age, club=self.club)
        tablo = Tablo.objects.filter(category=self.cat, age=age, sex=0).first()
        return Participation.objects.create(
            participant=participant, tablo=tablo, order=order)

    def a_score(self, judge, prtn, error_codes):
        s = Score.objects.create(judge=judge, participation=prtn, saved=True)
        for ec in error_codes:
            s.aclass.add(WrapperErrorCode.objects.create(error_code=ec))
        return s

    def b_score(self, judge, prtn, value):
        return Score.objects.create(judge=judge, participation=prtn,
                                    bclass=value, saved=True)

    def c_score(self, judge, prtn, done_marks):
        """done_marks: list of (element, done) in order."""
        s = Score.objects.create(judge=judge, participation=prtn, saved=True)
        cs = CombinationStatus.objects.create()
        for element, done in done_marks:
            cs.statuses.add(ElementStatus.objects.create(element=element, done=done))
        s.cclass.add(cs)
        return s

    def full_panel(self, prtn, b_values, c_done, a_errors=None, bonus=False):
        a_errors = a_errors if a_errors is not None else [[self.ec]] * 3
        for judge, errs in zip(self.ja, a_errors):
            self.a_score(judge, prtn, errs)
        for judge, val in zip(self.jb, b_values):
            self.b_score(judge, prtn, val)
        for judge in self.jc:
            self.c_score(judge, prtn, c_done)
        if bonus:
            prtn.bonus = True
            prtn.save()


class GetScoresGoldenTest(GoldenHelper):
    def test_full_panel_end_to_end(self):
        # A: all three agree on one 1.0 error -> 7.0 - 1.0 = 6.0 -> 600
        # B: [9.5,9.6,9.6,9.7] -> repeated 9.6 -> 960
        # C: both elements performed by all -> pools full, capped 2.0 -> 200
        prtn = self.make_participation()
        self.full_panel(prtn, [9.5, 9.6, 9.6, 9.7],
                        [(self.move, 1), (self.land, 1)])
        items = prtn.get_scores()
        self.assertEqual(items['final_a'][1], 6.0)
        self.assertEqual(items['final_b'], 9.6)
        self.assertEqual(items['final_c'][1], 2.0)
        self.assertEqual(items['final'], 17.6)
        self.assertTrue(items['can_be_saved'])

    def test_bonus_adds_five_centipoints(self):
        prtn = self.make_participation()
        self.full_panel(prtn, [9.5, 9.6, 9.6, 9.7],
                        [(self.move, 1), (self.land, 1)], bonus=True)
        items = prtn.get_scores()
        # 600 + (960 + 5) + 200 = 1765 -> 17.65
        self.assertEqual(items['final'], 17.65)

    def test_b_rounding_no_truncation(self):
        # Fixed by stabilize-django: B aggregate 9.5799.. now rounds to 958
        # centi-points (was truncated to 957 by int()).
        prtn = self.make_participation()
        self.full_panel(prtn, [9.57, 9.59, 9.4, 9.7],
                        [(self.move, 1), (self.land, 1)])
        items = prtn.get_scores()
        # 600 + 958 + 200 = 1758 -> 17.58 (rounded)
        self.assertEqual(items['final'], 17.58)


class GetScoresQueryCountTest(GoldenHelper):
    def test_query_count_is_bounded_and_memoized(self):
        prtn = self.make_participation()
        self.full_panel(prtn, [9.5, 9.6, 9.6, 9.7],
                        [(self.move, 1), (self.land, 1)])
        prtn = Participation.objects.get(pk=prtn.pk)  # fresh instance, no cache
        # A small fixed number of queries (scores+judge, the prefetched A/B/C
        # relations, and the participant) regardless of panel/element count.
        with self.assertNumQueries(8):
            prtn.get_scores()
        # second call is memoized within the instance -> no extra queries
        with self.assertNumQueries(0):
            prtn.get_scores()


class CountsGoldenTest(TestCase):
    class _Elem:
        def __init__(self, score, prizemlenie):
            self.score = score
            self.prizemlenie = prizemlenie

    class _Status:
        def __init__(self, done, element):
            self.done = done
            self.element = element

    def test_untouched_not_counted(self):
        # Fixed by stabilize-django: an untouched element (done==2) is an
        # abstention and must NOT count as a performed high-value element.
        el = self._Elem(score=0.5, prizemlenie=False)
        e4, e3, e2 = counts([self._Status(done=2, element=el)])
        self.assertEqual((e4, e3, e2), (0, 0, 0))

    def test_performed_movement_counted(self):
        el = self._Elem(score=0.5, prizemlenie=False)
        e4, e3, e2 = counts([self._Status(done=1, element=el)])
        self.assertEqual((e4, e3, e2), (1, 1, 1))

    def test_failed_not_counted(self):
        el = self._Elem(score=0.5, prizemlenie=False)
        self.assertEqual(counts([self._Status(done=0, element=el)]), (0, 0, 0))


class CalculateBGoldenTest(TestCase):
    def _p(self):
        return Participation()

    def test_two_distinct_averaged(self):
        # Fixed by stabilize-django: two distinct scores now average (9.55),
        # instead of collapsing to ~0 under the old even-parity path.
        self.assertAlmostEqual(self._p().calculateB([9.5, 9.6]), 9.55)

    def test_three_distinct_middle(self):
        # Fixed by stabilize-django: 3 distinct -> middle score (8.0), not
        # middle/2 (4.0). Trimmed mean (sum-max-min)/(n-2).
        self.assertEqual(self._p().calculateB([7.0, 9.0, 8.0]), 8.0)

    def test_repeated_value_wins(self):
        # Stable: a value seen twice wins; preserved by the change.
        self.assertEqual(self._p().calculateB([8.0, 8.0, 9.0]), 8.0)

    def test_four_judge_panel_matches_old_formula(self):
        # Parity guard: standard 4-judge distinct panel is unchanged.
        self.assertAlmostEqual(self._p().calculateB([9.4, 9.5, 9.6, 9.7]), 9.55)


class SortTiebreakGoldenTest(GoldenHelper):
    def test_equal_finals_broken_by_high_value_element(self):
        # Two finished participations, equal final score; the one whose C-judges
        # agreed on more performed high-value elements ranks higher.
        strong = self.make_participation(order=0)
        weak = self.make_participation(order=1)
        # identical A and B; differ only in one movement element done vs failed
        for prtn, move_done in ((strong, 1), (weak, 0)):
            self.full_panel(prtn, [9.6, 9.6, 9.6, 9.6],
                            [(self.move, move_done), (self.land, 1)])
        # force equal finalscore so the tie-break (counts) decides
        for prtn in (strong, weak):
            prtn.state = PS_FINISHED
            prtn.finalscore = 15.0
            prtn.save()
        ordered = sort([strong, weak])
        self.assertEqual(ordered[0].pk, strong.pk)
