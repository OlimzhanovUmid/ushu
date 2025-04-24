# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sortedm2m.fields


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CombinationStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('statuses', sortedm2m.fields.SortedManyToManyField(help_text=None, to='tablo.ElementStatus')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='score',
            name='cclass',
            field=sortedm2m.fields.SortedManyToManyField(help_text=None, to='tablo.CombinationStatus'),
            preserve_default=True,
        ),
    ]
