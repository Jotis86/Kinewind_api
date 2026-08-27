from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["full_name", "dni", "phone", "active"]
    list_filter = ["active"]
    search_fields = ["first_name", "last_name", "dni"]
