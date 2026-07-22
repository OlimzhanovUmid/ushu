# -*- coding: utf-8 -*-
"""Deployment-configuration regression tests (lan-deployment capability)."""
from django.db import connections
from django.test import TestCase


class SqliteConfigTest(TestCase):
    def test_busy_timeout_option_is_applied(self):
        # Regression for the historically misplaced OPTIONS dict (it sat as a
        # sibling of the 'default' alias, so the timeout was silently ignored).
        options = connections['default'].settings_dict.get('OPTIONS', {})
        self.assertEqual(options.get('timeout'), 20)

    def test_connection_pragmas_applied(self):
        # The connection_created signal (core.apps) must set the busy-timeout
        # pragma so concurrent judge writers wait instead of erroring.
        with connections['default'].cursor() as cursor:
            cursor.execute('PRAGMA busy_timeout;')
            self.assertEqual(cursor.fetchone()[0], 20000)
