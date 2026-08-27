from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Appointment
from .services import OVERLAP_ERROR, appointments_overlap


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    end = serializers.DateTimeField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La unicidad del horario la valida appointments_overlap (mensaje claro).
        # Se quita el validador automático que DRF agrega por la UniqueConstraint
        # de `start` (su mensaje "Ya existe appointment con este fecha y hora."
        # es confuso para el usuario).
        self.fields["start"].validators = [
            v
            for v in self.fields["start"].validators
            if not isinstance(v, UniqueValidator)
        ]

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_name",
            "start",
            "duration",
            "end",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start = attrs.get("start", getattr(self.instance, "start", None))
        if start is None:
            return attrs
        duration = attrs.get("duration", getattr(self.instance, "duration", 45))
        exclude_pk = self.instance.pk if self.instance else None
        if appointments_overlap(start, duration, exclude_pk=exclude_pk):
            raise serializers.ValidationError(OVERLAP_ERROR)
        return attrs
