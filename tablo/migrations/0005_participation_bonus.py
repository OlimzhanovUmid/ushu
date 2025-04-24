# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0004_auto_20150420_0414'),
    ]

    operations = [
        migrations.AddField(
            model_name='participation',
            name='bonus',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
