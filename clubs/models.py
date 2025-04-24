from django.db import models

# Create your models here.
class Country(models.Model):
    name_ru = models.TextField()
    name_en = models.TextField()
    name_ru_short = models.CharField(max_length=2)
    name_en_short = models.CharField(max_length=2)
    thumbnail = models.ImageField(blank=True, upload_to='countries')
    image = models.ImageField(blank=True, upload_to='countries')

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.name_en_short

class Club(models.Model):
    name = models.TextField()
    country = models.ForeignKey(Country)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.country.name_en_short)
