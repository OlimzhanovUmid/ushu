from django.contrib import admin
from .models import Tablo, Participation, ElementStatus, Score, WrapperErrorCode,CombinationStatus

# Register your models here.
admin.site.register(Tablo)

class ParticipationAdmin(admin.ModelAdmin):
	search_fields = [
		'participant__name_ru',
		'participant__name_en',
	]
	list_filter = ('state',)

admin.site.register(Participation, ParticipationAdmin)
admin.site.register(ElementStatus)

class ScoreAdmin(admin.ModelAdmin):
	search_fields = [
		'participation__participant__name_ru',
		'participation__participant__name_en',
	]

admin.site.register(Score, ScoreAdmin)
admin.site.register(WrapperErrorCode)
admin.site.register(CombinationStatus)
