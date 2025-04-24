# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clubs', '0002_auto_20150417_1607'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='image',
            field=models.ImageField(upload_to='countries', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='country',
            name='thumbnail',
            field=models.ImageField(upload_to='countries', blank=True),
            preserve_default=True,
        ),
    ]
