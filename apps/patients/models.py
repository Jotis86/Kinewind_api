from django.db import models


class Patient(models.Model):
    class FatigueLevel(models.TextChoices):
        VERY_HIGH = "muy_alto", "Muy alto"
        HIGH = "alto", "Alto"
        NORMAL = "normal", "Normal"
        LOW = "bajo", "Bajo"
        VERY_LOW = "muy_bajo", "Muy bajo"

    first_name = models.CharField("nombre", max_length=100)
    last_name = models.CharField("apellidos", max_length=100)
    dni = models.CharField(
        "DNI", max_length=20, unique=True, help_text="Ej.: 12345678A"
    )
    job = models.CharField("trabajo", max_length=150, blank=True)
    birth_date = models.DateField("fecha de nacimiento", null=True, blank=True)
    phone = models.CharField(
        "teléfono", max_length=30, blank=True, help_text="Ej.: 612 345 678"
    )
    email = models.EmailField(
        "email", blank=True, help_text="Ej.: nombre@correo.com"
    )
    address = models.CharField("domicilio", max_length=255, blank=True)
    reason = models.TextField("motivo de la consulta", blank=True)
    history = models.TextField("antecedentes", blank=True)
    medications = models.TextField("uso de medicamentos", blank=True)
    sport_habits = models.BooleanField("hábitos deportivos", null=True, blank=True)
    fatigue_level = models.CharField(
        "nivel de cansancio",
        max_length=20,
        choices=FatigueLevel.choices,
        blank=True,
    )
    gluten_intolerance = models.BooleanField(
        "intolerancia a gluten", null=True, blank=True
    )
    gut_issues = models.BooleanField(
        "problemas intestinales", null=True, blank=True
    )
    notes = models.TextField("observaciones", blank=True)
    active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        return f"{self.last_name}, {self.first_name}"

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.full_name} ({self.dni})"

    def save(self, *args, **kwargs):
        if self.dni:
            self.dni = self.dni.strip().upper()
        super().save(*args, **kwargs)
