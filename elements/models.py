from django.db import models
from sortedm2m.fields import SortedManyToManyField

# Create your models here.
DIFFICULTY_CHOICES = (
    (0, 'A'),
    (1, 'B'),
    (2, 'C'),
    (3, 'D'),
)
class ElementCategory(models.Model): # Chanqguan, Nanquan, Taljiquan
    name = models.CharField(max_length=16)
    seven_twelve = models.BooleanField(default=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.name

class Element(models.Model):
    name            = models.CharField(max_length=64)
    difficulty      = models.IntegerField(choices=DIFFICULTY_CHOICES)
    score           = models.FloatField()
    categories      = models.ManyToManyField(ElementCategory)
    prizemlenie     = models.BooleanField(default=False)
    symbol          = models.CharField(max_length=64,default="")

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        cat_names = [cat.name for cat in self.categories.all()]
        return self.name + '(' + ', '.join(cat_names) + ')'

class Combination(models.Model):
    elements = SortedManyToManyField(Element)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        names = [el.name for el in self.elements.all()]
        return ' + '.join(names)

class ErrorCode(models.Model):
    name = models.CharField(max_length=64)
    number = models.IntegerField(default=0)
    value = models.FloatField(default=0)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '(%s) %s' % (self.number, self.name,)







