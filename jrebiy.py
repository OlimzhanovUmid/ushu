from tablo.models import Participation, Tablo
from django.db import transaction
#with transaction.atomic():
Tablo.objects.all().update(started=False)
participations = Participation.objects.all().order_by('?')
participations = [i for i in participations]
counter = 0
for p in participations:
  p.order = counter
  p.save()
  counter = counter+1

Tablo.objects.all().update(started=True)