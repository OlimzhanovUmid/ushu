# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0006_participation_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='score',
            name='berrors',
            field=models.ManyToManyField(related_name='berrors', to='tablo.WrapperErrorCode'),
            preserve_default=True,
        ),
    ]
