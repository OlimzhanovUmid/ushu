from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from clubs.models import Club

# Create your models here.
SEX_CHOICES = (
    (0, _('Men')),
    (1, _('Women')),
)

AGE_7_12    = 0
AGE_13_15   = 1
AGE_16_18   = 2
AGE_19      = 3
AGE_7_9     = 4
AGE_CHOICES = (
    (AGE_7_12,  '9-12'),
    (AGE_13_15, '13-15'),
    (AGE_16_18, '16-18'),
    (AGE_19,    '19+'),
    (AGE_7_9,  '7-9'),
)

class Participant(models.Model):
    name_ru = models.CharField(max_length=64)
    name_en = models.CharField(max_length=64)
    sex = models.IntegerField(choices=SEX_CHOICES)
    age = models.IntegerField(choices=AGE_CHOICES)
    club = models.ForeignKey(Club)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '%s --- %s' % (self.name_en, self.club.name)
