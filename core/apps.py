from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _apply_sqlite_pragmas(sender, connection, **kwargs):
    """WAL journal + busy-timeout so ~10 concurrent judge writers don't hit
    'database is locked'. WAL also stops the single writer from blocking
    readers (the monitor/scoreboard). No-op on non-sqlite backends and
    harmless on the in-memory test database."""
    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA busy_timeout=20000;')
        cursor.execute('PRAGMA synchronous=NORMAL;')


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        connection_created.connect(_apply_sqlite_pragmas)
