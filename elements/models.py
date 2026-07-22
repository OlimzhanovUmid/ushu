from django.db import models
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
        verbose_name = 'категория элементов'
        verbose_name_plural = 'категории элементов'

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
        verbose_name = 'элемент'
        verbose_name_plural = 'элементы'

    def __str__(self):
        cat_names = [cat.name for cat in self.categories.all()]
        return self.name + '(' + ', '.join(cat_names) + ')'


class Combination(models.Model):
    elements = SortedManyToManyField(Element)

    class Meta:
        verbose_name = 'комбинация'
        verbose_name_plural = 'комбинации'

    def __str__(self):
        names = [el.name for el in self.elements.all()]
        return ' + '.join(names)


class ErrorCode(models.Model):
    name = models.CharField(max_length=64)
    number = models.IntegerField(default=0)
    value = models.FloatField(default=0)

    class Meta:
        verbose_name = 'код сбавки'
        verbose_name_plural = 'коды сбавок'

    def __str__(self):
        return f'({self.number}) {self.name}'
