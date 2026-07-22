from django.contrib import admin

from .models import Club, Country

# Register your models here.


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    list_filter = ('country',)
    search_fields = ('name',)
    list_select_related = ('country',)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_en', 'name_ru_short', 'name_en_short')
    search_fields = ('name_ru', 'name_en', 'name_ru_short', 'name_en_short')
