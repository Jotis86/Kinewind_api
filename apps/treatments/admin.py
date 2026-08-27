from django.contrib import admin

from .models import Session, Treatment


class SessionInline(admin.TabularInline):
    model = Session
    extra = 0


@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ["diagnosis", "patient", "status", "start_date"]
    list_filter = ["status"]
    inlines = [SessionInline]
