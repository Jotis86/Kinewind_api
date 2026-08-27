from django import forms
from django.contrib import admin

from .models import Appointment
from .services import OVERLAP_ERROR, appointments_overlap


class AppointmentAdminForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start") or getattr(self.instance, "start", None)
        if start is None:
            return cleaned
        duration = cleaned.get("duration") or getattr(self.instance, "duration", 45)
        exclude_pk = self.instance.pk if self.instance else None
        if appointments_overlap(start, duration, exclude_pk=exclude_pk):
            raise forms.ValidationError(OVERLAP_ERROR)
        return cleaned


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm
    list_display = ["start", "patient", "status"]
    list_filter = ["status"]
    search_fields = ["patient__first_name", "patient__last_name"]
