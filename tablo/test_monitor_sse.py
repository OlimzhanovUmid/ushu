# -*- coding: utf-8 -*-
"""Monitor SSE + render-safety tests (monitor-realtime capability)."""
import json

from django.template import loader
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from clubs.models import Country, Club
from elements.models import ElementCategory
from participants.models import Participant, AGE_18_plus
from tablo.models import Tablo, Participation
from tablo.monitor_state import monitor_state


class MonitorStreamTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_stream_sends_current_snapshot(self):
        monitor_state.publish(['<b>hello</b>'])
        resp = self.client.get(reverse('monitor_stream'))
        it = resp.streaming_content
        retry = next(it)
        snapshot = next(it)
        resp.close()
        self.assertIn(b'retry', retry)
        self.assertIn(b'event: snapshot', snapshot)
        payload = json.loads(snapshot.decode().split('data: ', 1)[1].strip())
        self.assertEqual(payload['pages'], ['<b>hello</b>'])

    @override_settings(EVENT_TITLE='MY EVENT', EVENT_SUBTITLE='MY SUB')
    def test_idle_screen_uses_configured_branding(self):
        resp = self.client.get(reverse('monitor'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'MY EVENT')
        self.assertContains(resp, 'MY SUB')


class MonitorRenderSafetyTest(TestCase):
    def test_flagless_country_renders_without_error(self):
        # country with no image must not raise on the monitor page
        country = Country.objects.create(
            name_ru='NoFlag', name_en='NoFlag',
            name_ru_short='NF', name_en_short='NF')  # image left blank
        club = Club.objects.create(name='Club', country=country)
        cat = ElementCategory.objects.create(name='nanquan')
        participant = Participant.objects.create(
            name_ru='P', name_en='P', sex=0, age=AGE_18_plus, club=club)
        tablo = Tablo.objects.filter(category=cat, age=AGE_18_plus, sex=0).first()
        prtn = Participation.objects.create(participant=participant, tablo=tablo)
        html = loader.render_to_string('tablo/monitor_tablo.html', {
            'is_group': False,
            'participations': [prtn],
            'title': 'Test',
            'tablo': tablo,
        })
        self.assertIn('P', html)          # the participant row rendered
        self.assertNotIn('<img', html)    # no flag img emitted for a blank image
