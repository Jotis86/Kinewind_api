from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.treatments.models import Session
from apps.treatments.serializers import TreatmentSerializer

from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    filterset_fields = ["active"]
    search_fields = ["first_name", "last_name", "dni"]
    ordering_fields = ["last_name", "created_at"]

    def destroy(self, request, *args, **kwargs):
        """Baja lógica: marca al paciente como inactivo."""
        patient = self.get_object()
        patient.active = False
        patient.save(update_fields=["active"])
        return Response(self.get_serializer(patient).data)

    @action(detail=True, methods=["get"])
    def treatments(self, request, pk=None):
        patient = self.get_object()
        queryset = (
            patient.treatments.select_related("patient")
            .annotate(
                sessions_done_count=Count(
                    "sessions", filter=Q(sessions__status=Session.Status.DONE)
                )
            )
            .all()
        )
        return Response(TreatmentSerializer(queryset, many=True).data)

    @action(detail=True, methods=["get"])
    def appointments(self, request, pk=None):
        from apps.appointments.serializers import AppointmentSerializer

        patient = self.get_object()
        queryset = patient.appointments.select_related("patient").order_by("start")
        return Response(AppointmentSerializer(queryset, many=True).data)
