# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clubs', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Participant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name_ru', models.CharField(max_length=64)),
                ('name_en', models.CharField(max_length=64)),
                ('sex', models.IntegerField(choices=[(0, 'Man'), (1, 'Woman')])),
                ('age', models.IntegerField(choices=[(0, b'7-12'), (1, b'13-15'), (2, b'16-18'), (3, b'19+')])),
                ('club', models.ForeignKey(to='clubs.Club')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
