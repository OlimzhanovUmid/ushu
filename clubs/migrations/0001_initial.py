# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Club',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name_ru', models.TextField()),
                ('name_en', models.TextField()),
                ('name_ru_short', models.CharField(max_length=2)),
                ('name_en_short', models.CharField(max_length=2)),
                ('thumbnail', models.ImageField(upload_to=b'countries')),
                ('image', models.ImageField(upload_to=b'countries')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='club',
            name='country',
            field=models.ForeignKey(to='clubs.Country'),
            preserve_default=True,
        ),
    ]
