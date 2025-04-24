# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0005_participation_bonus'),
    ]

    operations = [
        migrations.AddField(
            model_name='participation',
            name='group',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
