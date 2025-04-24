# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0008_auto_20150428_1940'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tablo',
            name='age',
            field=models.IntegerField(choices=[(0, '9-12'), (1, '13-15'), (2, '16-18'), (3, '19+'), (4, '7-9')]),
            preserve_default=True,
        ),
    ]
