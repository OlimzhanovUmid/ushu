# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

ALTER_SQL = '''
            ALTER TABLE tablo_elementstatus ALTER COLUMN done TYPE integer USING (
        CASE done
            when TRUE then 1
            when FALSE then 0
        END
        ); \
            '''


def alter_done_column(apps, schema_editor):
    # Raw type change only meaningful on PostgreSQL; SQLite is dynamically
    # typed so the column change is a no-op there.
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(ALTER_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ('tablo', '0010_auto_20150509_1230'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='elementstatus',
                    name='done',
                    field=models.IntegerField(default=2),
                    preserve_default=True,
                ),
            ],
            database_operations=[
                migrations.RunPython(alter_done_column,
                                     migrations.RunPython.noop),
            ],
        ),
    ]
