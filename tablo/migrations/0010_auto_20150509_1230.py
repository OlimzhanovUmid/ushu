# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0009_auto_20150504_0345'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participation',
            name='state',
            field=models.IntegerField(choices=[(0, 'waiting'), (1, 'doing'), (2, 'finished')], default=0, db_index=True),
            preserve_default=True,
        ),
    ]
