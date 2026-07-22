# -*- coding: utf-8 -*-
"""Repair the ElementStatus.done column type on SQLite.

Migration 0011 changed ``done`` from a boolean to a tri-state integer, but its
database operation was a no-op on SQLite (only PostgreSQL ran the ALTER). On a
freshly-migrated SQLite database the column is therefore still declared with
boolean affinity, so a ``done`` value of 2 (untouched) is coerced back to
False/0 on read -- silently breaking the C-judge tri-state. This rebuilds the
column with proper integer affinity. No-op where it is already integer
(the long-lived production database) and on non-SQLite backends.
"""
from django.db import migrations, models


def rebuild_done_as_integer(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT type FROM pragma_table_info('tablo_elementstatus') "
            "WHERE name='done'")
        row = cursor.fetchone()
    if row and str(row[0]).lower() == 'integer':
        return  # already correct (existing production db)

    ElementStatus = apps.get_model('tablo', 'ElementStatus')
    old_field = models.BooleanField(default=False)
    old_field.set_attributes_from_name('done')
    new_field = ElementStatus._meta.get_field('done')
    schema_editor.alter_field(ElementStatus, old_field, new_field)


class Migration(migrations.Migration):

    dependencies = [
        ('tablo', '0011_auto_20151009_0342'),
    ]

    operations = [
        migrations.RunPython(rebuild_done_as_integer, migrations.RunPython.noop),
    ]
