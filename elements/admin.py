from django.contrib import admin
from .models import Combination, Element, ElementCategory, ErrorCode

# Register your models here.
admin.site.register(ElementCategory)
admin.site.register(Element)
admin.site.register(Combination)
admin.site.register(ErrorCode)
