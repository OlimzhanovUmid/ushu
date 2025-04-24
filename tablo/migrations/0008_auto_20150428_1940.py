# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0007_score_berrors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participation',
            name='state',
            field=models.IntegerField(default=0, choices=[(0, 'waiting'), (1, 'doing'), (2, 'finished')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tablo',
            name='age',
            field=models.IntegerField(choices=[(4, '7-9'), (0, '9-12'), (1, '13-15'), (2, '16-18'), (3, '19+')]),
            preserve_default=True,
        ),
    ]
