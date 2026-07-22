from django.contrib import admin

from .models import Combination, Element, ElementCategory, ErrorCode

# Register your models here.


@admin.register(ElementCategory)
class ElementCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'difficulty', 'score', 'prizemlenie')
    list_filter = ('difficulty', 'prizemlenie', 'categories')
    search_fields = ('name', 'symbol')


@admin.register(Combination)
class CombinationAdmin(admin.ModelAdmin):
    list_display = ('__str__',)


@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ('number', 'name', 'value')
    search_fields = ('name', 'number')
    ordering = ('number',)
