# -*- coding: utf-8 -*-
"""Data-integrity tests: uniqueness, single-DOING, and PROTECT (data-integrity)."""
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from clubs.models import Country, Club
from elements.models import Element, ElementCategory, ErrorCode
from judges.models import User as Judge, JUDGE_A, JUDGE_C
from participants.models import Participant, AGE_12_14, AGE_18_plus
from tablo.models import (Tablo, Participation, Score, ElementStatus,
                          WrapperErrorCode, PS_DOING)


def make_judge(username, category, **kw):
    kw.setdefault('last_login', timezone.now())
    return Judge.objects.create(username=username, category=category, **kw)


class Base(TestCase):
    def setUp(self):
        self.country = Country.objects.create(
            name_ru='R', name_en='R', name_ru_short='R', name_en_short='R')
        self.club = Club.objects.create(name='C', country=self.country)
        self.cat = ElementCategory.objects.create(name='nanquan')
        self.participant = Participant.objects.create(
            name_ru='P', name_en='P', sex=0, age=AGE_12_14, club=self.club)
        self.tablo = Tablo.objects.filter(
            category=self.cat, age=AGE_12_14, sex=0).first()


class UniquenessTest(Base):
    def test_duplicate_participation_rejected(self):
        Participation.objects.create(participant=self.participant, tablo=self.tablo)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Participation.objects.create(
                    participant=self.participant, tablo=self.tablo)

    def test_duplicate_tablo_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tablo.objects.create(age=AGE_12_14, sex=0, category=self.cat)

    def test_duplicate_score_rejected(self):
        prtn = Participation.objects.create(
            participant=self.participant, tablo=self.tablo)
        judge = make_judge('a1', JUDGE_A)
        Score.objects.create(judge=judge, participation=prtn)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Score.objects.create(judge=judge, participation=prtn)

    def test_only_one_doing_at_db_level(self):
        p1 = Participation.objects.create(
            participant=self.participant, tablo=self.tablo, state=PS_DOING)
        other = Participant.objects.create(
            name_ru='Q', name_en='Q', sex=0, age=AGE_12_14, club=self.club)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Participation.objects.create(
                    participant=other, tablo=self.tablo, state=PS_DOING)


class ProtectTest(Base):
    def test_judge_with_scores_is_protected(self):
        prtn = Participation.objects.create(
            participant=self.participant, tablo=self.tablo)
        judge = make_judge('a1', JUDGE_A)
        Score.objects.create(judge=judge, participation=prtn)
        with self.assertRaises(ProtectedError):
            judge.delete()

    def test_element_in_status_is_protected(self):
        el = Element.objects.create(name='k', difficulty=0, score=0.5)
        ElementStatus.objects.create(element=el, done=1)
        with self.assertRaises(ProtectedError):
            el.delete()

    def test_errorcode_recorded_is_protected(self):
        ec = ErrorCode.objects.create(name='e', number=1, value=1.0)
        WrapperErrorCode.objects.create(error_code=ec)
        with self.assertRaises(ProtectedError):
            ec.delete()

    def test_country_with_clubs_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.country.delete()


class AssignParticipationInactiveTest(Base):
    def test_inactive_judge_gets_no_score(self):
        active = make_judge('c1', JUDGE_C)
        inactive = make_judge('c2', JUDGE_C, is_active=False)
        adult = Participant.objects.create(
            name_ru='A', name_en='A', sex=0, age=AGE_18_plus, club=self.club)
        Participation.objects.assign_participation(adult, self.cat)
        prtn = Participation.objects.get(
            participant=adult, tablo__category=self.cat)
        self.assertTrue(Score.objects.filter(participation=prtn, judge=active).exists())
        self.assertFalse(Score.objects.filter(participation=prtn, judge=inactive).exists())
