from rest_framework import serializers

from .models import Session, Treatment
from .services import validate_sessions_sync


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = [
            "id",
            "treatment",
            "number",
            "date",
            "status",
            "clinical_notes",
            "evolution",
        ]
        read_only_fields = ["treatment"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        treatment = attrs.get("treatment") or self.context.get("treatment")
        if treatment is None and self.instance:
            treatment = self.instance.treatment
        number = attrs.get("number", getattr(self.instance, "number", None))
        if treatment and number:
            queryset = Session.objects.filter(treatment=treatment, number=number)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"number": f"El tratamiento ya tiene la sesión {number}."}
                )
        return attrs


class TreatmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    sessions_done = serializers.SerializerMethodField()

    def get_sessions_done(self, obj) -> int:
        annotated = getattr(obj, "sessions_done_count", None)
        if annotated is not None:
            return annotated
        return obj.sessions_done

    def validate_total_sessions(self, value):
        if self.instance and self.instance.pk:
            error = validate_sessions_sync(self.instance, value)
            if error:
                raise serializers.ValidationError(error)
        return value

    class Meta:
        model = Treatment
        fields = [
            "id",
            "patient",
            "patient_name",
            "diagnosis",
            "description",
            "total_sessions",
            "frequency",
            "start_date",
            "end_date",
            "status",
            "notes",
            "sessions_done",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
