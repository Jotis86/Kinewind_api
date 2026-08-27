from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(ModelViewSet):
    queryset = Appointment.objects.select_related("patient").all()
    serializer_class = AppointmentSerializer
    filterset_fields = ["patient", "status"]
    search_fields = ["patient__first_name", "patient__last_name"]
    ordering_fields = ["start"]

    @action(detail=False, methods=["get"])
    def agenda(self, request):
        """Agenda del día: ?date=YYYY-MM-DD (por defecto hoy), ordenada por hora."""
        date_str = request.query_params.get("date")
        if date_str:
            day = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            day = timezone.localdate()
        appointments = self.queryset.filter(start__date=day).order_by("start")
        return Response(
            {
                "date": day.isoformat(),
                "appointments": AppointmentSerializer(
                    appointments, many=True
                ).data,
            }
        )
