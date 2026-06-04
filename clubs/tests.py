# -*- coding: utf-8 -*-
from django.test import TestCase

from clubs.models import Country, Club


class CountryTest(TestCase):
    def test_str_is_short_en_name(self):
        c = Country.objects.create(name_ru='Russia', name_en='Russia',
                                   name_ru_short='RU', name_en_short='RU')
        self.assertEqual(str(c), 'RU')


class ClubTest(TestCase):
    def test_str_includes_country_short(self):
        country = Country.objects.create(name_ru='Russia', name_en='Russia',
                                         name_ru_short='RU', name_en_short='RU')
        club = Club.objects.create(name='Dynamo', country=country)
        self.assertEqual(str(club), 'Dynamo (RU)')
