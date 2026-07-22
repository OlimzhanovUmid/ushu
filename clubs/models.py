from django.db import models

# Create your models here.
class Country(models.Model):
    name_ru = models.TextField()
    name_en = models.TextField()
    name_ru_short = models.CharField(max_length=2)
    name_en_short = models.CharField(max_length=2)
    image = models.ImageField(blank=True, upload_to='countries')

    class Meta:
        verbose_name = 'страна'
        verbose_name_plural = 'страны'

    def __str__(self):
        return self.name_en_short


class Club(models.Model):
    name = models.TextField()
    country = models.ForeignKey(Country, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'клуб'
        verbose_name_plural = 'клубы'

    def __str__(self):
        return f'{self.name} ({self.country.name_en_short})'
