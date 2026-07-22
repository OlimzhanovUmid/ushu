"""Draw of lots (jrebiy): randomize participation start order, per tablo.

Replaces the old ``jrebiy.py`` shell snippet (piped into ``manage.py shell``
with its ``transaction.atomic`` commented out and a *global* numbering that
disagreed with the per-tablo UI draw). This runs in one transaction, numbers
each tablo independently (0..n-1, matching ``JrebiView``), and refuses tablos
already marked ``started`` unless ``--force`` is given.
"""
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from tablo.models import Participation, Tablo


class Command(BaseCommand):
    help = 'Randomize participation start order (draw of lots), per tablo.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Also re-draw tablos already marked as started.')

    def handle(self, *args, **options):
        force = options['force']
        drawn = skipped = 0
        with transaction.atomic():
            for tablo in Tablo.objects.all():
                if tablo.started and not force:
                    skipped += 1
                    continue
                participations = list(Participation.objects.filter(tablo=tablo))
                random.shuffle(participations)
                for order, participation in enumerate(participations):
                    participation.order = order
                    participation.save(update_fields=['order'])
                tablo.started = True
                tablo.save(update_fields=['started'])
                drawn += 1
        self.stdout.write(self.style.SUCCESS(
            'Draw complete: %d tablo(s) drawn, %d skipped.' % (drawn, skipped)))
