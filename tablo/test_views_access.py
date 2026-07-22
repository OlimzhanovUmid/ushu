# -*- coding: utf-8 -*-
"""Access-control and mutation-safety tests (judging-access-control)."""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from clubs.models import Country, Club
from elements.models import Element, ElementCategory
from judges.models import User as Judge, JUDGE_A, JUDGE_C
from participants.models import Participant, AGE_18_plus
from tablo.models import (Tablo, Participation, Score, ElementStatus,
                          CombinationStatus, PS_WAITING, PS_DOING)


def make_judge(username, category, **kw):
    kw.setdefault('last_login', timezone.now())
    return Judge.objects.create(username=username, category=category, **kw)


class AccessHelper(TestCase):
    def setUp(self):
        self.client = Client()
        country = Country.objects.create(name_ru='R', name_en='R',
                                         name_ru_short='R', name_en_short='R')
        self.club = Club.objects.create(name='C', country=country)
        self.cat = ElementCategory.objects.create(name='nanquan')
        self.staff = make_judge('main', JUDGE_A, is_staff=True)
        self.judge = make_judge('a1', JUDGE_A)

    def a_participation(self, state=PS_WAITING, age=AGE_18_plus, order=0):
        participant = Participant.objects.create(
            name_ru='P', name_en='P', sex=0, age=age, club=self.club)
        tablo = Tablo.objects.filter(category=self.cat, age=age, sex=0).first()
        return Participation.objects.create(
            participant=participant, tablo=tablo, state=state, order=order)


class MutationEndpointAuthTest(AccessHelper):
    def test_delete_requires_login(self):
        p = self.a_participation()
        resp = self.client.post(reverse('delete_participation', args=[p.pk]))
        self.assertEqual(resp.status_code, 302)  # redirected to login
        self.assertTrue(Participation.objects.filter(pk=p.pk).exists())

    def test_delete_forbidden_for_non_staff(self):
        p = self.a_participation()
        self.client.force_login(self.judge)
        resp = self.client.post(reverse('delete_participation', args=[p.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Participation.objects.filter(pk=p.pk).exists())

    def test_delete_get_not_allowed(self):
        p = self.a_participation()
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('delete_participation', args=[p.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Participation.objects.filter(pk=p.pk).exists())

    def test_delete_works_for_staff_post(self):
        p = self.a_participation()
        self.client.force_login(self.staff)
        self.client.post(reverse('delete_participation', args=[p.pk]))
        self.assertFalse(Participation.objects.filter(pk=p.pk).exists())

    def test_open_judge_forbidden_for_non_staff(self):
        self.client.force_login(self.judge)
        resp = self.client.post(reverse('open_judge', args=[0]))
        self.assertEqual(resp.status_code, 403)

    def test_has_updated_requires_login(self):
        resp = self.client.get(reverse('has_updated'))
        self.assertEqual(resp.status_code, 302)


class ActivationTest(AccessHelper):
    def test_activate_requires_staff(self):
        p = self.a_participation()
        self.client.force_login(self.judge)
        resp = self.client.post(reverse('participant_activate'), {'pk': p.pk})
        self.assertEqual(resp.status_code, 403)
        p.refresh_from_db()
        self.assertEqual(p.state, PS_WAITING)

    def test_activate_get_not_allowed(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('participant_activate'))
        self.assertEqual(resp.status_code, 405)

    def test_only_one_can_be_active(self):
        p1 = self.a_participation(order=0)
        p2 = self.a_participation(order=1)
        self.client.force_login(self.staff)
        self.client.post(reverse('participant_activate'), {'pk': p1.pk})
        self.client.post(reverse('participant_activate'), {'pk': p2.pk})
        self.assertEqual(Participation.objects.filter(state=PS_DOING).count(), 1)
        p1.refresh_from_db()
        self.assertEqual(p1.state, PS_DOING)

    def test_cannot_activate_non_waiting(self):
        from tablo.models import PS_FINISHED
        p = self.a_participation(state=PS_FINISHED)
        self.client.force_login(self.staff)
        self.client.post(reverse('participant_activate'), {'pk': p.pk})
        p.refresh_from_db()
        self.assertEqual(p.state, PS_FINISHED)


class JudgeSubmitSafetyTest(AccessHelper):
    def test_submit_without_active_participant_does_not_500(self):
        # no DOING participation exists
        self.client.force_login(self.judge)
        resp = self.client.post(reverse('judgea_submit'), {'error': ['5']})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('judge_view'))

    def test_csubmit_idor_cannot_touch_other_judges_status(self):
        p = self.a_participation(state=PS_DOING)
        el = Element.objects.create(name='k', difficulty=0, score=0.5)
        jc1 = make_judge('c1', JUDGE_C)
        jc2 = make_judge('c2', JUDGE_C)
        # each judge owns their own element status
        es_other = self._c_card(jc2, p, el)
        self._c_card(jc1, p, el)
        self.client.force_login(jc1)
        # jc1 tries to set jc2's element status to performed
        self.client.post(reverse('judgec_submit'), {str(es_other.pk): '1'})
        es_other.refresh_from_db()
        self.assertEqual(es_other.done, 2)  # untouched, not modified

    def _c_card(self, judge, participation, element):
        s = Score.objects.create(judge=judge, participation=participation)
        cs = CombinationStatus.objects.create()
        es = ElementStatus.objects.create(element=element, done=2)
        cs.statuses.add(es)
        s.cclass.add(cs)
        return es
