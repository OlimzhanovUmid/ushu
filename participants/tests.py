# -*- coding: utf-8 -*-
from django.test import TestCase

from clubs.models import Country, Club
from participants.models import Participant, AGE_12_14, AGE_18_plus


class ParticipantTest(TestCase):
    def setUp(self):
        country = Country.objects.create(name_ru='Russia', name_en='Russia',
                                         name_ru_short='RU', name_en_short='RU')
        self.club = Club.objects.create(name='Dynamo', country=country)

    def test_str_includes_name_and_club(self):
        pt = Participant.objects.create(name_ru='Ivan', name_en='Ivan',
                                        sex=0, age=AGE_12_14, club=self.club)
        self.assertEqual(str(pt), 'Ivan --- Dynamo')

    def test_age_display(self):
        pt = Participant.objects.create(name_ru='Petr', name_en='Petr',
                                        sex=0, age=AGE_18_plus, club=self.club)
        self.assertEqual(pt.get_age_display(), '18+')
