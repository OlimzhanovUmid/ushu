# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judges', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='category',
            field=models.IntegerField(default=0, choices=[(0, 'A'), (1, 'B'), (2, 'C')]),
            preserve_default=True,
        ),
    ]
