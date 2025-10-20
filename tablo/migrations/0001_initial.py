# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sortedm2m.fields
from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('participants', '0001_initial'),
        ('elements', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ElementStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('done', models.BooleanField(default=False)),
                ('element', models.ForeignKey(to='elements.Element', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Participation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.IntegerField(default=0)),
                ('state', models.IntegerField(default=0, choices=[(0, b'waiting'), (1, b'doing'), (2, b'finished')])),
                ('finalscore', models.FloatField()),
                ('participant', models.ForeignKey(to='participants.Participant', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Score',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('bclass', models.FloatField(null=True, blank=True)),
                ('saved', models.BooleanField(default=False)),
                ('aclass', models.ManyToManyField(to='elements.ErrorCode')),
                ('cclass', sortedm2m.fields.SortedManyToManyField(help_text=None, to='tablo.ElementStatus')),
                ('judge', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('participation', models.ForeignKey(to='tablo.Participation', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tablo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('age', models.IntegerField(choices=[(0, b'7-12'), (1, b'13-15'), (2, b'16-18'), (3, b'19+')])),
                ('sex', models.IntegerField(choices=[(0, 'Man'), (1, 'Woman')])),
                ('category', models.ForeignKey(to='elements.ElementCategory', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='participation',
            name='tablo',
            field=models.ForeignKey(to='tablo.Tablo', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
