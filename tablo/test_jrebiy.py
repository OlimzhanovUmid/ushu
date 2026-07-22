# -*- coding: utf-8 -*-
"""Tests for the jrebiy (draw of lots) management command."""
from django.core.management import call_command
from django.test import TestCase

from clubs.models import Country, Club
from elements.models import ElementCategory
from participants.models import Participant, AGE_12_14
from tablo.models import Tablo, Participation


class JrebiyCommandTest(TestCase):
    def setUp(self):
        country = Country.objects.create(
            name_ru='R', name_en='R', name_ru_short='R', name_en_short='R')
        self.club = Club.objects.create(name='C', country=country)
        self.cat = ElementCategory.objects.create(name='nanquan')
        self.tablo = Tablo.objects.filter(
            category=self.cat, age=AGE_12_14, sex=0).first()
        for i in range(5):
            p = Participant.objects.create(
                name_ru=f'P{i}', name_en=f'P{i}', sex=0, age=AGE_12_14,
                club=self.club)
            Participation.objects.create(participant=p, tablo=self.tablo, order=0)

    def orders(self):
        return sorted(Participation.objects.filter(tablo=self.tablo)
                      .values_list('order', flat=True))

    def test_draw_assigns_unique_orders_per_tablo(self):
        call_command('jrebiy')
        self.assertEqual(self.orders(), [0, 1, 2, 3, 4])
        self.tablo.refresh_from_db()
        self.assertTrue(self.tablo.started)

    def test_started_tablo_skipped_without_force(self):
        self.tablo.started = True
        self.tablo.save()
        # give known orders so we can detect a (non-)change
        for i, p in enumerate(Participation.objects.filter(tablo=self.tablo)):
            p.order = i * 10
            p.save()
        call_command('jrebiy')
        self.assertEqual(
            sorted(Participation.objects.filter(tablo=self.tablo)
                   .values_list('order', flat=True)),
            [0, 10, 20, 30, 40])

    def test_force_redraws_started_tablo(self):
        self.tablo.started = True
        self.tablo.save()
        call_command('jrebiy', '--force')
        self.assertEqual(self.orders(), [0, 1, 2, 3, 4])
