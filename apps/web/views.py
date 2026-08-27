import os
import shutil
import subprocess
from datetime import datetime as dt

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)
from django.views.generic.detail import DetailView

from apps.appointments.models import Appointment
from apps.appointments.services import (
    DURATION_CHOICES,
    appointments_overlap,
    slot_times,
)
from apps.patients.models import Patient
from apps.treatments.models import Session, Treatment

from .forms import (
    AppointmentForm,
    LoginForm,
    PatientForm,
    SessionForm,
    TreatmentForm,
)
from .pdf import build_treatment_pdf


class LoginPageView(LoginView):
    template_name = "web/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutPageView(LogoutView):
    pass


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "web/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = timezone.localdate()

        context["patients_active"] = Patient.objects.filter(active=True).count()
        context["appointments_today"] = (
            Appointment.objects.filter(start__date=today)
            .exclude(status=Appointment.Status.CANCELLED)
            .count()
        )
        context["treatments_active"] = Treatment.objects.filter(
            status=Treatment.Status.ACTIVE
        ).count()
        context["appointments_confirmed"] = Appointment.objects.filter(
            status=Appointment.Status.CONFIRMED
        ).count()
        context["appointments"] = (
            Appointment.objects.select_related("patient")
            .filter(start__date=today)
            .exclude(status=Appointment.Status.CANCELLED)
            .order_by("start")
        )
        context["upcoming"] = (
            Appointment.objects.select_related("patient")
            .filter(start__gte=now)
            .exclude(status__in=[Appointment.Status.CANCELLED, Appointment.Status.COMPLETED])
            .order_by("start")[:5]
        )
        context["recent_patients"] = Patient.objects.filter(active=True)[:5]
        context["today"] = today
        return context


# ---------------------------------------------------------------- Pacientes


class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    template_name = "web/patients/patient_list.html"
    context_object_name = "patients"
    paginate_by = 10

    def get_queryset(self):
        queryset = Patient.objects.all()
        q = self.request.GET.get("q")
        active = self.request.GET.get("active")
        if q:
            queryset = queryset.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(dni__icontains=q)
            )
        if active in ("true", "false"):
            queryset = queryset.filter(active=active == "true")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["active"] = self.request.GET.get("active", "")
        context["qs"] = self._build_qs()
        return context

    def _build_qs(self):
        qs = self.request.GET.copy()
        qs.pop("page", None)
        return qs.urlencode()


class PatientCreateView(LoginRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = "web/patients/patient_form.html"

    def get_success_url(self):
        messages.success(self.request, "Paciente dado de alta correctamente.")
        return reverse("web:patient-detail", args=[self.object.pk])


class PatientUpdateView(LoginRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = "web/patients/patient_form.html"

    def get_success_url(self):
        messages.success(self.request, "Paciente actualizado correctamente.")
        return reverse("web:patient-detail", args=[self.object.pk])


class PatientDetailView(LoginRequiredMixin, DetailView):
    model = Patient
    template_name = "web/patients/patient_detail.html"
    context_object_name = "patient"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["treatments"] = (
            self.object.treatments.select_related("patient")
            .annotate(
                sessions_done_count=Count(
                    "sessions", filter=Q(sessions__status=Session.Status.DONE)
                )
            )
            .order_by("-created_at")
        )
        context["appointments"] = self.object.appointments.order_by("start")
        return context


class PatientDeleteView(LoginRequiredMixin, DeleteView):
    """Baja lógica: marca active=False."""

    model = Patient
    template_name = "web/patients/patient_confirm_delete.html"
    context_object_name = "patient"

    def get_success_url(self):
        return reverse_lazy("web:patient-list")

    def form_valid(self, form):
        self.object.active = False
        self.object.save(update_fields=["active"])
        messages.success(self.request, "Paciente dado de baja.")
        return redirect(self.get_success_url())


class PatientActivateView(LoginRequiredMixin, View):
    """Reactivación: vuelve a poner active=True a un paciente dado de baja."""

    http_method_names = ["post"]

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        if not patient.active:
            patient.active = True
            patient.save(update_fields=["active"])
            messages.success(request, f"{patient.full_name} reactivado.")
        return redirect("web:patient-detail", pk=pk)


# ------------------------------------------------------------- Tratamientos


class TreatmentListView(LoginRequiredMixin, ListView):
    model = Treatment
    template_name = "web/treatments/treatment_list.html"
    context_object_name = "treatments"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            Treatment.objects.select_related("patient")
            .annotate(
                sessions_done_count=Count(
                    "sessions", filter=Q(sessions__status=Session.Status.DONE)
                )
            )
            .order_by("-created_at")
        )
        status = self.request.GET.get("status")
        patient = self.request.GET.get("patient")
        q = self.request.GET.get("q")
        if status:
            queryset = queryset.filter(status=status)
        if patient:
            queryset = queryset.filter(patient_id=patient)
        if q:
            queryset = queryset.filter(
                Q(diagnosis__icontains=q)
                | Q(patient__first_name__icontains=q)
                | Q(patient__last_name__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "")
        context["patient"] = self.request.GET.get("patient", "")
        context["patients"] = Patient.objects.all()
        qs = self.request.GET.copy()
        qs.pop("page", None)
        context["qs"] = qs.urlencode()
        return context


class TreatmentCreateView(LoginRequiredMixin, CreateView):
    model = Treatment
    form_class = TreatmentForm
    template_name = "web/treatments/treatment_form.html"

    def get_initial(self):
        patient = self.request.GET.get("patient")
        return {"patient": patient} if patient else {}

    def get_success_url(self):
        messages.success(self.request, "Tratamiento creado.")
        return reverse("web:treatment-detail", args=[self.object.pk])


class TreatmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Treatment
    form_class = TreatmentForm
    template_name = "web/treatments/treatment_form.html"

    def get_success_url(self):
        messages.success(self.request, "Tratamiento actualizado.")
        return reverse("web:treatment-detail", args=[self.object.pk])


class TreatmentDetailView(LoginRequiredMixin, DetailView):
    model = Treatment
    template_name = "web/treatments/treatment_detail.html"
    context_object_name = "treatment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sessions"] = self.object.sessions.order_by("number")
        context["sessions_done"] = self.object.sessions.filter(
            status=Session.Status.DONE
        ).count()
        return context


class TreatmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Treatment
    template_name = "web/treatments/treatment_confirm_delete.html"
    context_object_name = "treatment"

    def get_success_url(self):
        return reverse_lazy("web:treatment-list")

    def form_valid(self, form):
        messages.success(self.request, "Tratamiento eliminado.")
        return super().form_valid(form)


class TreatmentFinishView(LoginRequiredMixin, View):
    """Finaliza el tratamiento si las sesiones realizadas alcanzan el total."""

    http_method_names = ["post"]

    def post(self, request, pk):
        treatment = get_object_or_404(Treatment, pk=pk)
        done = treatment.sessions.filter(status=Session.Status.DONE).count()
        missing = treatment.total_sessions - done

        if done < treatment.total_sessions:
            messages.error(
                request,
                f"No se puede finalizar el tratamiento: faltan {missing} "
                f"sesión{'es' if missing != 1 else ''} por realizar.",
            )
        else:
            treatment.status = Treatment.Status.FINISHED
            treatment.end_date = treatment.end_date or timezone.localdate()
            treatment.save(update_fields=["status", "end_date"])
            messages.success(request, "Tratamiento finalizado.")
        return redirect("web:treatment-detail", pk=treatment.pk)


class TreatmentPDFView(LoginRequiredMixin, View):
    """Descarga un PDF del tratamiento."""

    def get(self, request, pk):
        treatment = get_object_or_404(
            Treatment.objects.select_related("patient"), pk=pk
        )
        pdf_bytes = build_treatment_pdf(treatment)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="tratamiento-{treatment.pk}.pdf"'
        )
        return response


class DatabaseDumpView(LoginRequiredMixin, View):
    """Descarga un volcado SQL de la base de datos."""

    def get(self, request):
        dump_binary = shutil.which("pg_dump")
        if dump_binary is None:
            return HttpResponse(
                "pg_dump no está disponible en el servidor.",
                status=503,
                content_type="text/plain",
            )

        db = settings.DATABASES["default"]
        env = {
            **os.environ,
            "PGHOST": db["HOST"],
            "PGPORT": str(db["PORT"]),
            "PGUSER": db["USER"],
            "PGPASSWORD": db["PASSWORD"],
            "PGDATABASE": db["NAME"],
        }
        result = subprocess.run(
            [dump_binary, "--format=plain"],
            env=env,
            capture_output=True,
        )
        if result.returncode != 0:
            return HttpResponse(
                result.stderr.decode("utf-8", errors="replace"),
                status=500,
                content_type="text/plain",
            )

        filename = f"{timezone.localdate():%Y-%m-%d}.sql"
        response = HttpResponse(result.stdout, content_type="application/sql")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ----------------------------------------------------------------- Sesiones


class SessionCreateView(LoginRequiredMixin, CreateView):
    model = Session
    form_class = SessionForm
    template_name = "web/treatments/session_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.treatment = get_object_or_404(Treatment, pk=kwargs["treatment_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        next_number = (
            self.treatment.sessions.order_by("-number").values_list(
                "number", flat=True
            ).first()
        )
        return {
            "number": (next_number or 0) + 1,
            "date": timezone.localdate(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["treatment"] = self.treatment
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["treatment"] = self.treatment
        return kwargs

    def form_valid(self, form):
        form.instance.treatment = self.treatment
        messages.success(self.request, "Sesión agregada al tratamiento.")
        return super().form_valid(form)
    def get_success_url(self):
        return reverse("web:treatment-detail", args=[self.treatment.pk])


class SessionUpdateView(LoginRequiredMixin, UpdateView):
    model = Session
    form_class = SessionForm
    template_name = "web/treatments/session_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.treatment = self.get_object().treatment
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["treatment"] = self.treatment
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["treatment"] = self.treatment
        return kwargs

    def get_success_url(self):
        messages.success(self.request, "Sesión actualizada.")
        return reverse("web:treatment-detail", args=[self.treatment.pk])


class SessionDeleteView(LoginRequiredMixin, DeleteView):
    model = Session

    def get_success_url(self):
        messages.success(self.request, "Sesión eliminada.")
        return reverse("web:treatment-detail", args=[self.object.treatment.pk])


class SessionCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        session = get_object_or_404(Session, pk=pk)
        session.status = Session.Status.DONE
        if not session.date:
            session.date = timezone.localdate()
        session.save(update_fields=["status", "date"])
        messages.success(request, f"Sesión {session.number} marcada como realizada.")
        return redirect("web:treatment-detail", pk=session.treatment.pk)


# ------------------------------------------------------------------- Citas


class AppointmentListView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = "web/appointments/appointment_list.html"
    context_object_name = "appointments"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            Appointment.objects.select_related("patient").order_by("start")
        )
        status = self.request.GET.get("status")
        patient = self.request.GET.get("patient")
        day = self.request.GET.get("date")
        if status:
            queryset = queryset.filter(status=status)
        if patient:
            queryset = queryset.filter(patient_id=patient)
        if day:
            queryset = queryset.filter(start__date=day)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status"] = self.request.GET.get("status", "")
        context["patient"] = self.request.GET.get("patient", "")
        context["date"] = self.request.GET.get("date", "")
        context["patients"] = Patient.objects.all()
        qs = self.request.GET.copy()
        qs.pop("page", None)
        context["qs"] = qs.urlencode()
        return context


class AppointmentSlotsView(LoginRequiredMixin, View):
    """Devuelve los huecos ocupados de un día (para la cuadrícula de horarios)."""

    def get(self, request):
        date_str = request.GET.get("date")
        if not date_str:
            return JsonResponse({"slots": []})
        try:
            day = dt.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"slots": []})
        try:
            duration = int(request.GET.get("duration", 30))
        except (TypeError, ValueError):
            duration = 30
        exclude_pk = request.GET.get("exclude") or None

        occupied = []
        for slot in slot_times():
            start = timezone.make_aware(
                dt.combine(day, dt.strptime(slot, "%H:%M").time())
            )
            if appointments_overlap(start, duration, exclude_pk=exclude_pk):
                occupied.append(slot)
        return JsonResponse({"slots": occupied})


class AppointmentFormViewMixin:
    """Añade los huecos y duraciones disponibles al contexto del form de citas."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slot_times"] = slot_times()
        context["durations"] = DURATION_CHOICES
        return context


class AppointmentCreateView(AppointmentFormViewMixin, LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = "web/appointments/appointment_form.html"

    def get_initial(self):
        initial = super().get_initial()
        patient = self.request.GET.get("patient")
        if patient:
            initial["patient"] = patient
        return initial

    def get_success_url(self):
        messages.success(self.request, "Cita creada correctamente.")
        return reverse("web:appointment-list")


class AppointmentUpdateView(AppointmentFormViewMixin, LoginRequiredMixin, UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = "web/appointments/appointment_form.html"

    def get_success_url(self):
        messages.success(self.request, "Cita actualizada.")
        return reverse("web:appointment-list")


class AppointmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Appointment
    template_name = "web/appointments/appointment_confirm_delete.html"
    context_object_name = "appointment"

    def get_success_url(self):
        return reverse_lazy("web:appointment-list")

    def form_valid(self, form):
        messages.success(self.request, "Cita eliminada.")
        return super().form_valid(form)


class AppointmentStatusView(LoginRequiredMixin, View):
    """Cambia el estado de una cita (programar / confirmar / cancelar / completar)."""

    http_method_names = ["post"]

    ACTIONS = {
        "programar": (Appointment.Status.SCHEDULED, "Cita programada."),
        "confirmar": (Appointment.Status.CONFIRMED, "Cita confirmada."),
        "cancelar": (Appointment.Status.CANCELLED, "Cita cancelada."),
        "completar": (Appointment.Status.COMPLETED, "Cita completada."),
    }

    def post(self, request, pk, action):
        appointment = get_object_or_404(Appointment, pk=pk)
        if action not in self.ACTIONS:
            return redirect("web:appointment-list")

        target, message = self.ACTIONS[action]
        if target != Appointment.Status.CANCELLED and appointments_overlap(
            appointment.start,
            appointment.duration,
            exclude_pk=appointment.pk,
        ):
            messages.error(
                request,
                "No se puede cambiar el estado: ya existe otra cita en ese horario.",
            )
            return redirect(
                request.META.get("HTTP_REFERER") or "web:appointment-list"
            )

        appointment.status = target
        appointment.save(update_fields=["status"])
        messages.success(request, message)
        return redirect(request.META.get("HTTP_REFERER") or "web:appointment-list")


class AgendaView(LoginRequiredMixin, TemplateView):
    template_name = "web/appointments/agenda.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_str = self.request.GET.get("date")
        if date_str:
            day = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            day = timezone.localdate()
        context["day"] = day
        context["appointments"] = (
            Appointment.objects.select_related("patient")
            .filter(start__date=day)
            .order_by("start")
        )
        return context
