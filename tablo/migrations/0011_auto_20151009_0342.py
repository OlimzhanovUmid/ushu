# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

ALTER_SQL = '''
    ALTER TABLE tablo_elementstatus ALTER COLUMN done TYPE integer USING (
        CASE done
            when TRUE then 1
            when FALSE then 0
        END
        );
    '''

class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0010_auto_20150509_1230'),
    ]

    operations = [
        migrations.RunSQL(ALTER_SQL, None, [
            migrations.AlterField(
                model_name='elementstatus',
                name='done',
                field=models.IntegerField(default=2),
                preserve_default=True,
            ),
        ]),
    ]
