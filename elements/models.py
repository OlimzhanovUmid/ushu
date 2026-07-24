from django.db import models
from django.utils.translation import gettext_lazy as _
from sortedm2m.fields import SortedManyToManyField

# Create your models here.
DIFFICULTY_CHOICES = (
    (0, 'A'),
    (1, 'B'),
    (2, 'C'),
    (3, 'D'),
)


class ElementCategory(models.Model):  # Chanqguan, Nanquan, Taljiquan
    name = models.CharField(max_length=16)

    class Meta:
        verbose_name = _('element category')
        verbose_name_plural = _('element categories')

    def __str__(self):
        return self.name


class Element(models.Model):
    name = models.CharField(max_length=64)
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES)
    score = models.FloatField()
    categories = models.ManyToManyField(ElementCategory)
    prizemlenie = models.BooleanField(default=False)
    symbol = models.CharField(max_length=64, default="")

    class Meta:
        verbose_name = _('element')
        verbose_name_plural = _('elements')

    def __str__(self):
        cat_names = [cat.name for cat in self.categories.all()]
        return self.name + '(' + ', '.join(cat_names) + ')'


class Combination(models.Model):
    elements = SortedManyToManyField(Element)

    class Meta:
        verbose_name = _('combination')
        verbose_name_plural = _('combinations')

    def __str__(self):
        names = [el.name for el in self.elements.all()]
        return ' + '.join(names)


class ErrorCode(models.Model):
    name = models.CharField(max_length=64)
    number = models.IntegerField(default=0)
    value = models.FloatField(default=0)

    class Meta:
        verbose_name = _('deduction code')
        verbose_name_plural = _('deduction codes')

    def __str__(self):
        return f'({self.number}) {self.name}'
