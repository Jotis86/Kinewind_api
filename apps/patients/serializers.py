from rest_framework import serializers

from .models import Patient
from .validators import validate_dni_format, validate_phone_format


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    dni = serializers.CharField(max_length=20)

    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "dni",
            "job",
            "birth_date",
            "phone",
            "email",
            "address",
            "reason",
            "history",
            "medications",
            "sport_habits",
            "fatigue_level",
            "gluten_intolerance",
            "gut_issues",
            "notes",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_dni(self, value):
        value = value.strip().upper()
        validate_dni_format(value)
        queryset = Patient.objects.filter(dni__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un paciente con ese DNI.")
        return value

    def validate_phone(self, value):
        if value:
            validate_phone_format(value)
        return value
