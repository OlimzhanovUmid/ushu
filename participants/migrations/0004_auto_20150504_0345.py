# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from participants.models import AGE_CHOICES


class Migration(migrations.Migration):
    dependencies = [
        ('participants', '0003_auto_20150428_1940'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participant',
            name='age',
            field=models.IntegerField(choices=AGE_CHOICES),
            preserve_default=True,
        ),
    ]
