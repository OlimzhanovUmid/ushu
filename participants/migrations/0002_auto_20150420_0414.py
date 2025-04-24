# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participant',
            name='sex',
            field=models.IntegerField(choices=[(0, 'Men'), (1, 'Women')]),
            preserve_default=True,
        ),
    ]
