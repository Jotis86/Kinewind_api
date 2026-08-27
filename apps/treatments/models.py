from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Treatment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "activo", "Activo"
        FINISHED = "finalizado", "Finalizado"
        CANCELLED = "cancelado", "Cancelado"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="treatments",
        verbose_name="paciente",
    )
    diagnosis = models.CharField("diagnóstico / motivo", max_length=255)
    description = models.TextField("descripción", blank=True)
    total_sessions = models.PositiveIntegerField(
        "cantidad de sesiones", default=1
    )
    frequency = models.CharField(
        "frecuencia", max_length=100, blank=True, help_text="Ej: 2 veces por semana"
    )
    start_date = models.DateField("fecha de inicio", default=timezone.localdate)
    end_date = models.DateField("fecha de fin", null=True, blank=True)
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    notes = models.TextField("observaciones", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def sessions_done(self):
        return self.sessions.filter(status=Session.Status.DONE).count()

    def save(self, *args, **kwargs):
        from .services import sync_treatment_sessions, validate_sessions_sync

        old_total = None
        if self.pk and not self._state.adding:
            old_total = (
                self.__class__.objects.filter(pk=self.pk)
                .values_list("total_sessions", flat=True)
                .first()
            )
        if (
            old_total is not None
            and old_total != self.total_sessions
            and self.total_sessions < old_total
        ):
            error = validate_sessions_sync(self, self.total_sessions)
            if error:
                raise ValidationError({"total_sessions": error})
        super().save(*args, **kwargs)
        if old_total is not None and old_total != self.total_sessions:
            sync_treatment_sessions(self, self.total_sessions)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.diagnosis} — {self.patient}"


class Session(models.Model):
    class Status(models.TextChoices):
        PENDING = "pendiente", "Pendiente"
        DONE = "realizada", "Realizada"
        CANCELLED = "cancelada", "Cancelada"

    treatment = models.ForeignKey(
        Treatment,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="tratamiento",
    )
    number = models.PositiveIntegerField("número de sesión")
    date = models.DateField("fecha", default=timezone.localdate)
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    clinical_notes = models.TextField("notas clínicas", blank=True)
    evolution = models.TextField("evolución", blank=True)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["treatment", "number"],
                name="unique_session_per_treatment",
            )
        ]

    def __str__(self):
        return f"{self.treatment} — Sesión {self.number}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.treatment_id and self.number:
            duplicated = (
                Session.objects.filter(
                    treatment_id=self.treatment_id, number=self.number
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if duplicated:
                raise ValidationError(
                    {"number": f"El tratamiento ya tiene la sesión {self.number}."}
                )
