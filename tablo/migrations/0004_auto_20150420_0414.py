# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('elements', '0001_initial'),
        ('tablo', '0003_auto_20150419_1216'),
    ]

    operations = [
        migrations.CreateModel(
            name='WrapperErrorCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('error_code', models.ForeignKey(to='elements.ErrorCode')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='score',
            name='aclass',
            field=models.ManyToManyField(to='tablo.WrapperErrorCode'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tablo',
            name='sex',
            field=models.IntegerField(choices=[(0, 'Men'), (1, 'Women')]),
            preserve_default=True,
        ),
    ]
