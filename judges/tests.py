# -*- coding: utf-8 -*-
from django.test import TestCase
from django.utils import timezone

from judges.models import User, JUDGE_A, JUDGE_B, JUDGE_C


def make_user(**kw):
    # last_login is NOT NULL in the historical schema; set it explicitly.
    kw.setdefault('last_login', timezone.now())
    return User.objects.create(**kw)


class JudgeUserTest(TestCase):
    def test_default_category_is_a(self):
        u = make_user(username='j1')
        self.assertEqual(u.category, JUDGE_A)

    def test_category_display(self):
        u = make_user(username='j2', category=JUDGE_C)
        self.assertEqual(u.get_category_display(), 'C')

    def test_is_custom_user_model(self):
        from django.contrib.auth import get_user_model
        self.assertIs(get_user_model(), User)
