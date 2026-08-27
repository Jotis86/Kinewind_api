from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Session, Treatment
from .serializers import SessionSerializer, TreatmentSerializer


class TreatmentViewSet(viewsets.ModelViewSet):
    queryset = (
        Treatment.objects.select_related("patient")
        .annotate(
            sessions_done_count=Count(
                "sessions", filter=Q(sessions__status=Session.Status.DONE)
            )
        )
        .all()
    )
    serializer_class = TreatmentSerializer
    filterset_fields = ["patient", "status"]
    search_fields = ["diagnosis", "patient__first_name", "patient__last_name"]
    ordering_fields = ["created_at", "start_date"]

    @action(detail=True, methods=["get", "post"])
    def sessions(self, request, pk=None):
        treatment = self.get_object()
        if request.method == "GET":
            queryset = treatment.sessions.all()
            status_filter = request.query_params.get("status")
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            return Response(SessionSerializer(queryset, many=True).data)

        serializer = SessionSerializer(
            data=request.data, context={"treatment": treatment}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(treatment=treatment)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED
        )


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.select_related("treatment__patient").all()
    serializer_class = SessionSerializer
    filterset_fields = ["treatment", "status", "date"]
    ordering_fields = ["date", "number"]
