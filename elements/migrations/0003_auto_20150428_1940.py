# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('elements', '0002_element_prizemlenie'),
    ]

    operations = [
        migrations.AlterField(
            model_name='element',
            name='difficulty',
            field=models.IntegerField(choices=[(0, 'A'), (1, 'B'), (2, 'C'), (3, 'D')]),
            preserve_default=True,
        ),
    ]
