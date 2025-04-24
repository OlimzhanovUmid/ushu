# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clubs', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='image',
            field=models.ImageField(upload_to=b'countries', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='country',
            name='thumbnail',
            field=models.ImageField(upload_to=b'countries', blank=True),
            preserve_default=True,
        ),
    ]
