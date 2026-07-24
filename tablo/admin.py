from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from judges.models import JUDGE_CATEGORIES
from .models import (Tablo, Participation, ElementStatus, Score,
                     WrapperErrorCode, CombinationStatus)

# Register your models here.


@admin.register(Tablo)
class TabloAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'category', 'age_label', 'sex_label', 'started')
    list_filter = ('started', 'category', 'age', 'sex')
    list_select_related = ('category',)

    @admin.display(description=_('age'), ordering='age')
    def age_label(self, obj):
        return obj.get_age_display()

    @admin.display(description=_('sex'), ordering='sex')
    def sex_label(self, obj):
        return obj.get_sex_display()


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('participant_name', 'tablo', 'state', 'order', 'finalscore')
    list_display_links = ('participant_name',)
    list_filter = ('state', 'tablo__category', 'tablo__age', 'tablo__sex')
    search_fields = [
        'participant__name_ru',
        'participant__name_en',
        'participant__club__name',
    ]
    list_select_related = ('participant', 'tablo', 'tablo__category')
    ordering = ('tablo', 'order')

    @admin.display(description=_('participant'), ordering='participant__name_ru')
    def participant_name(self, obj):
        return obj.participant.name_ru or obj.participant.name_en


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('participant_name', 'judge_label', 'tablo_label', 'saved')
    list_display_links = ('participant_name',)
    list_filter = ('saved', 'judge__category', 'participation__state',
                   'participation__tablo__category')
    search_fields = [
        'participation__participant__name_ru',
        'participation__participant__name_en',
        'participation__participant__club__name',
        'judge__username',
    ]
    list_select_related = (
        'judge', 'participation', 'participation__participant',
        'participation__tablo', 'participation__tablo__category',
    )

    @admin.display(description=_('participant'), ordering='participation__participant__name_ru')
    def participant_name(self, obj):
        p = obj.participation.participant
        return p.name_ru or p.name_en

    @admin.display(description=_('judge'), ordering='judge__category')
    def judge_label(self, obj):
        cat = JUDGE_CATEGORIES[obj.judge.category][1]
        return f'{obj.judge.username} ({cat})'

    @admin.display(description=_('tablo'), ordering='participation__tablo')
    def tablo_label(self, obj):
        return obj.participation.tablo


admin.site.register(ElementStatus)
admin.site.register(WrapperErrorCode)
admin.site.register(CombinationStatus)
