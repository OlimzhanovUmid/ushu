# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('elements', '0003_auto_20150428_1940'),
    ]

    operations = [
        migrations.AddField(
            model_name='element',
            name='symbol',
            field=models.CharField(default='', max_length=64),
            preserve_default=True,
        ),
    ]
