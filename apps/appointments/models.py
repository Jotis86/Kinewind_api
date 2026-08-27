from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "programada", "Programada"
        CONFIRMED = "confirmada", "Confirmada"
        CANCELLED = "cancelada", "Cancelada"
        COMPLETED = "completada", "Completada"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name="paciente",
    )
    start = models.DateTimeField("fecha y hora", db_index=True)
    duration = models.PositiveIntegerField(
        "duración (minutos)", default=50
    )
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    notes = models.TextField("notas", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def end(self):
        from datetime import timedelta

        return self.start + timedelta(minutes=self.duration)

    class Meta:
        ordering = ["start"]
        constraints = [
            models.UniqueConstraint(
                fields=["start"],
                condition=models.Q(
                    status__in=(
                        "programada",
                        "confirmada",
                        "completada",
                    )
                ),
                name="unique_appointment_start",
            ),
        ]

    def __str__(self):
        return f"{self.patient} — {self.start:%d/%m/%Y %H:%M}"
