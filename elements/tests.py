# -*- coding: utf-8 -*-
from django.test import TestCase

from elements.models import (Element, ElementCategory, ErrorCode, Combination)


class ElementCategoryTest(TestCase):
    def test_str(self):
        cat = ElementCategory.objects.create(name='nanquan')
        self.assertEqual(str(cat), 'nanquan')


class ElementTest(TestCase):
    def test_str_lists_categories(self):
        c1 = ElementCategory.objects.create(name='nanquan')
        c2 = ElementCategory.objects.create(name='changquan')
        el = Element.objects.create(name='kick', difficulty=0, score=0.5)
        el.categories.add(c1, c2)
        s = str(el)
        self.assertTrue(s.startswith('kick('))
        self.assertIn('nanquan', s)
        self.assertIn('changquan', s)


class CombinationTest(TestCase):
    def test_str_joins_element_names(self):
        comb = Combination.objects.create()
        e1 = Element.objects.create(name='a', difficulty=0, score=0.1)
        e2 = Element.objects.create(name='b', difficulty=1, score=0.2)
        comb.elements.add(e1, e2)
        self.assertEqual(str(comb), 'a + b')


class ErrorCodeTest(TestCase):
    def test_str_format(self):
        ec = ErrorCode.objects.create(name='fall', number=7, value=0.5)
        self.assertEqual(str(ec), '(7) fall')
