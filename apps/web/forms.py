from datetime import datetime as dt

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import MinValueValidator
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.appointments.services import OVERLAP_ERROR, appointments_overlap
from apps.patients.models import Patient
from apps.patients.validators import validate_dni_format, validate_phone_format
from apps.treatments.models import Session, Treatment
from apps.treatments.services import validate_sessions_sync


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, *args, **kwargs):
        # Con type="date" el navegador exige el valor en formato ISO (YYYY-MM-DD),
        # independientemente de L10N; si no, el campo aparece vacío y al guardar
        # se envía sin valor y se borra la fecha.
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(*args, **kwargs)


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Usuario o contraseña incorrectos.",
        "inactive": "La cuenta está inactiva.",
    }

    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nombre de usuario",
                "autofocus": "autofocus",
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "••••••••"}
        ),
    )


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "dni",
            "job",
            "phone",
            "email",
            "reason",
            "history",
            "medications",
            "sport_habits",
            "fatigue_level",
            "gluten_intolerance",
            "gut_issues",
            "notes",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "autofocus": "autofocus"}
            ),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "dni": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej.: 12345678A"}
            ),
            "job": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej.: 612 345 678"}
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej.: nombre@correo.com",
                }
            ),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "history": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "medications": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "fatigue_level": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        # El ejemplo ya va en el placeholder; se oculta el help_text del modelo
        # para no duplicarlo debajo del campo.
        for field_name in ("dni", "phone", "email"):
            self.fields[field_name].help_text = ""
        # Los booleanos nullable: select Sí/No con "Selecciona una opción" en vez
        # de "Desconocido", manteniendo el NullBooleanSelect para que
        # preseleccione el valor guardado.
        for field_name in ("sport_habits", "gluten_intolerance", "gut_issues"):
            field = self.fields[field_name]
            field.widget.attrs["class"] = "form-select"
            field.required = False
            # Reemplaza solo la etiqueta de la opción 'unknown' por el texto.
            field.widget.choices = [
                (("unknown", "Selecciona una opción") if c == "unknown" else (c, l))
                for c, l in field.widget.choices
            ]
        # Nivel de cansancio: opción vacía con el texto por defecto.
        fatigue = self.fields["fatigue_level"]
        fatigue.widget.attrs["class"] = "form-select"
        fatigue.required = False
        fatigue.choices = [("", "Selecciona una opción")] + list(fatigue.choices)

    def clean_dni(self):
        dni = (self.cleaned_data.get("dni") or "").strip().upper()
        validate_dni_format(dni)
        queryset = Patient.objects.filter(dni__iexact=dni)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Ya existe un paciente con ese DNI.")
        return dni

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            validate_phone_format(phone)
        return phone

    def clean(self):
        cleaned = super().clean()
        # Al editar, si un booleano llega sin valor ('unknown'/'None'), se
        # conserva el valor que ya tenía la instancia en lugar de borrarlo.
        if self.instance and self.instance.pk:
            for name in ("sport_habits", "gluten_intolerance", "gut_issues"):
                if cleaned.get(name) is None:
                    cleaned[name] = getattr(self.instance, name)
        return cleaned

    def validate_unique(self):
        """La unicidad del DNI ya la valida clean_dni con un mensaje claro."""
        pass


class TreatmentForm(forms.ModelForm):
    class Meta:
        model = Treatment
        fields = [
            "patient",
            "diagnosis",
            "description",
            "total_sessions",
            "frequency",
            "start_date",
            "end_date",
            "status",
            "notes",
        ]
        widgets = {
            "patient": forms.Select(attrs={"class": "form-select"}),
            "start_date": DateInput(attrs={"class": "form-control"}),
            "end_date": DateInput(attrs={"class": "form-control"}),
            "diagnosis": forms.TextInput(
                attrs={"class": "form-control", "autofocus": "autofocus"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "total_sessions": forms.NumberInput(attrs={"class": "form-control"}),
            "frequency": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["total_sessions"].validators.append(
            MinValueValidator(
                1, message="El tratamiento debe tener al menos 1 sesión."
            )
        )

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and cleaned.get("total_sessions") is not None:
            old_total = (
                Treatment.objects.filter(pk=self.instance.pk)
                .values_list("total_sessions", flat=True)
                .first()
            )
            if (
                old_total is not None
                and old_total != cleaned["total_sessions"]
            ):
                error = validate_sessions_sync(
                    self.instance, cleaned["total_sessions"]
                )
                if error:
                    self.add_error("total_sessions", error)
        return cleaned


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ["number", "date", "status", "clinical_notes", "evolution"]
        widgets = {
            "date": DateInput(attrs={"class": "form-control"}),
            "number": forms.NumberInput(
                attrs={"class": "form-control", "autofocus": "autofocus"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "clinical_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "evolution": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }

    def __init__(self, *args, treatment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.treatment = treatment or (
            self.instance.treatment if self.instance and self.instance.pk else None
        )
        self.fields["status"].required = False
        self.fields["status"].initial = Session.Status.PENDING

    def clean_number(self):
        number = self.cleaned_data["number"]
        treatment = self.treatment
        if treatment:
            queryset = Session.objects.filter(
                treatment=treatment, number=number
            )
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError(
                    f"El tratamiento ya tiene la sesión {number}."
                )
        return number


class AppointmentForm(forms.ModelForm):
    start_date = forms.DateField(
        label="Día",
        widget=DateInput(attrs={"class": "form-control"}),
    )
    start_time = forms.CharField(
        label="Hora",
        widget=forms.HiddenInput(attrs={"class": "form-control"}),
    )
    duration = forms.IntegerField(
        label="Duración (minutos)",
        widget=forms.HiddenInput(attrs={"class": "form-control"}),
        validators=[
            MinValueValidator(
                20, message="La duración mínima es de 20 minutos."
            )
        ],
    )

    class Meta:
        model = Appointment
        fields = ["patient", "duration", "status", "notes"]
        widgets = {
            "patient": forms.Select(
                attrs={"class": "form-select", "autofocus": "autofocus"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].initial = Appointment.Status.SCHEDULED
        if self.instance and self.instance.pk and self.instance.start:
            self.fields["start_date"].initial = self.instance.start.date()
            self.fields["start_time"].initial = self.instance.start.strftime("%H:%M")
            self.fields["duration"].initial = self.instance.duration

    def validate_unique(self):
        """La unicidad del horario ya la valida clean() (solapamiento)."""
        pass

    def clean(self):
        cleaned = super().clean()
        date_val = cleaned.get("start_date")
        time_val = cleaned.get("start_time")

        start = getattr(self.instance, "start", None)
        if date_val and time_val:
            try:
                time_obj = dt.strptime(time_val, "%H:%M").time()
            except (TypeError, ValueError):
                self.add_error(
                    "start_time", "Selecciona un horario de la cuadrícula."
                )
                return cleaned
            start = timezone.make_aware(dt.combine(date_val, time_obj))
            self.instance.start = start
        cleaned["start"] = start

        if start is None:
            self.add_error(
                "start_time", "Elige el día y un horario libre de la cuadrícula."
            )
            return cleaned

        duration = cleaned.get("duration") or getattr(self.instance, "duration", 30)
        exclude_pk = self.instance.pk if self.instance else None
        if appointments_overlap(start, duration, exclude_pk=exclude_pk):
            raise forms.ValidationError(OVERLAP_ERROR)
        return cleaned
