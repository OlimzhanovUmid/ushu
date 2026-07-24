from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class Country(models.Model):
    name_ru = models.TextField()
    name_en = models.TextField()
    name_ru_short = models.CharField(max_length=2)
    name_en_short = models.CharField(max_length=2)
    image = models.ImageField(blank=True, upload_to='countries')

    class Meta:
        verbose_name = _('country')
        verbose_name_plural = _('countries')

    def __str__(self):
        return self.name_en_short


class Club(models.Model):
    name = models.TextField()
    country = models.ForeignKey(Country, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('club')
        verbose_name_plural = _('clubs')

    def __str__(self):
        return f'{self.name} ({self.country.name_en_short})'
