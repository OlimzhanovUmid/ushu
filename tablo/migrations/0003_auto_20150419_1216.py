# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0002_auto_20150419_0659'),
    ]

    operations = [
        migrations.AddField(
            model_name='tablo',
            name='started',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='participation',
            name='finalscore',
            field=models.FloatField(default=0),
            preserve_default=True,
        ),
    ]
