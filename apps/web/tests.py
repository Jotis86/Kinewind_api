from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.patients.models import Patient
from apps.treatments.models import Session, Treatment


class WebBaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="fisio", password="pass12345"
        )
        self.client.force_login(self.user)


class AuthWebTestCase(TestCase):
    def test_login_required_redirects(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.headers["Location"])

    def test_login_page(self):
        response = self.client.get(reverse("web:login"))
        self.assertEqual(response.status_code, 200)

    def test_login_flow(self):
        User.objects.create_user(username="fisio", password="pass12345")
        response = self.client.post(
            reverse("web:login"),
            {"username": "fisio", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], reverse("web:dashboard"))


class DashboardTestCase(WebBaseTestCase):
    def test_dashboard_counts(self):
        patient = Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222"
        )
        today = timezone.localdate()
        Appointment.objects.create(
            patient=patient,
            start=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.min.time())
            )
            + timedelta(hours=10),
        )
        response = self.client.get(reverse("web:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1")
        self.assertContains(response, "Ana")
        self.assertContains(response, "Lopez")

    def test_dashboard_has_calendar_quick_access(self):
        response = self.client.get(reverse("web:dashboard"))
        self.assertContains(response, "Ver calendario")
        self.assertContains(response, reverse("web:calendar"))


class PatientWebTestCase(WebBaseTestCase):
    def test_create_patient(self):
        response = self.client.post(
            reverse("web:patient-create"),
            {
                "first_name": "Pedro",
                "last_name": "Sosa",
                "dni": "40222333",
                "phone": "612 345 678",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Patient.objects.filter(dni="40222333").exists())

    def test_duplicate_dni_rejected(self):
        Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222"
        )
        response = self.client.post(
            reverse("web:patient-create"),
            {"first_name": "Otro", "last_name": "Paciente", "dni": "40111222"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe un paciente con ese DNI")
        self.assertNotContains(response, "already exists")
        self.assertNotContains(response, "único")

    def test_duplicate_dni_case_insensitive(self):
        Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222A"
        )
        response = self.client.post(
            reverse("web:patient-create"),
            {"first_name": "Otro", "last_name": "Paciente", "dni": "40111222a"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe un paciente con ese DNI")

    def test_edit_keeps_untouched_booleans(self):
        patient = Patient.objects.create(
            first_name="Ana",
            last_name="Lopez",
            dni="40111222B",
            job="Enfermera",
            sport_habits=True,
            fatigue_level="alto",
            gluten_intolerance=False,
            gut_issues=True,
        )
        # Editar sin tocar los booleanos (llegan 'unknown' desde el widget)
        response = self.client.post(
            reverse("web:patient-update", args=[patient.pk]),
            {
                "first_name": "Ana",
                "last_name": "Lopez",
                "dni": "40111222B",
                "job": "Enfermera",
                "phone": "",
                "email": "",
                "reason": "",
                "history": "",
                "medications": "",
                "sport_habits": "unknown",
                "fatigue_level": "alto",
                "gluten_intolerance": "unknown",
                "gut_issues": "unknown",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        patient.refresh_from_db()
        self.assertTrue(patient.sport_habits)
        self.assertFalse(patient.gluten_intolerance)
        self.assertTrue(patient.gut_issues)

    def test_edit_changes_booleans(self):
        patient = Patient.objects.create(
            first_name="Ana",
            last_name="Lopez",
            dni="40111222C",
            sport_habits=True,
            gluten_intolerance=False,
            gut_issues=True,
        )
        response = self.client.post(
            reverse("web:patient-update", args=[patient.pk]),
            {
                "first_name": "Ana",
                "last_name": "Lopez",
                "dni": "40111222C",
                "job": "",
                "phone": "",
                "email": "",
                "reason": "",
                "history": "",
                "medications": "",
                "sport_habits": "false",
                "fatigue_level": "",
                "gluten_intolerance": "true",
                "gut_issues": "false",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        patient.refresh_from_db()
        self.assertFalse(patient.sport_habits)
        self.assertTrue(patient.gluten_intolerance)
        self.assertFalse(patient.gut_issues)

    def test_dni_uppercased(self):
        response = self.client.post(
            reverse("web:patient-create"),
            {"first_name": "Pedro", "last_name": "Sosa", "dni": "30111222b"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Patient.objects.filter(dni="30111222B").exists())

    def test_invalid_dni_format_rejected(self):
        response = self.client.post(
            reverse("web:patient-create"),
            {"first_name": "Ana", "last_name": "Lopez", "dni": "abc"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DNI inválido")

    def test_invalid_phone_rejected(self):
        response = self.client.post(
            reverse("web:patient-create"),
            {
                "first_name": "Ana",
                "last_name": "Lopez",
                "dni": "40111222",
                "phone": "no-es-un-teléfono",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teléfono inválido")

    def test_list_patients_requires_auth(self):
        self.client.logout()
        response = self.client.get(reverse("web:patient-list"))
        self.assertEqual(response.status_code, 302)

    def test_soft_delete(self):
        patient = Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222"
        )
        response = self.client.post(reverse("web:patient-delete", args=[patient.pk]))
        self.assertEqual(response.status_code, 302)
        patient.refresh_from_db()
        self.assertFalse(patient.active)

    def test_reactivate(self):
        patient = Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222", active=False
        )
        response = self.client.post(
            reverse("web:patient-activate", args=[patient.pk])
        )
        self.assertEqual(response.status_code, 302)
        patient.refresh_from_db()
        self.assertTrue(patient.active)


class TreatmentWebTestCase(WebBaseTestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222"
        )
        self.treatment = Treatment.objects.create(
            patient=self.patient, diagnosis="Hombro", total_sessions=3
        )

    def test_create_session(self):
        response = self.client.post(
            reverse("web:session-create", args=[self.treatment.pk]),
            {"number": 1, "date": "2026-08-20"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Session.objects.count(), 1)

    def test_edit_keeps_dates(self):
        treatment = Treatment.objects.create(
            patient=self.patient,
            diagnosis="Rodilla",
            start_date="2026-08-01",
            end_date="2026-09-15",
            total_sessions=3,
        )
        response = self.client.post(
            reverse("web:treatment-update", args=[treatment.pk]),
            {
                "patient": self.patient.pk,
                "diagnosis": "Rodilla editado",
                "description": "",
                "total_sessions": 3,
                "frequency": "",
                "start_date": "2026-08-01",
                "end_date": "2026-09-15",
                "status": "activo",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        treatment.refresh_from_db()
        self.assertEqual(treatment.start_date.isoformat(), "2026-08-01")
        self.assertEqual(treatment.end_date.isoformat(), "2026-09-15")
        self.assertEqual(treatment.diagnosis, "Rodilla editado")

    def test_duplicate_session_rejected(self):
        Session.objects.create(treatment=self.treatment, number=1)
        response = self.client.post(
            reverse("web:session-create", args=[self.treatment.pk]),
            {"number": 1, "date": "2026-08-20"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ya tiene la sesión")

    def test_complete_session(self):
        session = Session.objects.create(treatment=self.treatment, number=1)
        response = self.client.post(
            reverse("web:session-complete", args=[session.pk])
        )
        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, Session.Status.DONE)

    def test_finish_treatment_missing_sessions(self):
        Session.objects.create(
            treatment=self.treatment, number=1, status=Session.Status.DONE
        )
        Session.objects.create(
            treatment=self.treatment, number=2, status=Session.Status.PENDING
        )
        response = self.client.post(
            reverse("web:treatment-finish", args=[self.treatment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.treatment.refresh_from_db()
        self.assertEqual(self.treatment.status, Treatment.Status.ACTIVE)
        self.assertIsNone(self.treatment.end_date)

    def test_finish_treatment_complete(self):
        for n in range(1, 4):
            Session.objects.create(
                treatment=self.treatment, number=n, status=Session.Status.DONE
            )
        response = self.client.post(
            reverse("web:treatment-finish", args=[self.treatment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.treatment.refresh_from_db()
        self.assertEqual(self.treatment.status, Treatment.Status.FINISHED)
        self.assertIsNotNone(self.treatment.end_date)

    def test_export_pdf(self):
        Session.objects.create(
            treatment=self.treatment,
            number=1,
            clinical_notes="Primera evaluación",
        )
        response = self.client.get(
            reverse("web:treatment-pdf", args=[self.treatment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def _update_payload(self, **overrides):
        payload = {
            "patient": self.patient.pk,
            "diagnosis": "Hombro",
            "description": "",
            "total_sessions": self.treatment.total_sessions,
            "frequency": "",
            "start_date": "2026-08-18",
            "end_date": "",
            "status": "activo",
            "notes": "",
        }
        payload.update(overrides)
        return payload

    def test_edit_treatment_increase_syncs_sessions(self):
        Session.objects.bulk_create(
            [
                Session(treatment=self.treatment, number=n)
                for n in range(1, 3)
            ]
        )
        response = self.client.post(
            reverse("web:treatment-update", args=[self.treatment.pk]),
            self._update_payload(total_sessions=5),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(Session.objects.values_list("number", flat=True)),
            [1, 2, 3, 4, 5],
        )

    def test_edit_treatment_decrease_syncs_sessions(self):
        Session.objects.bulk_create(
            [
                Session(treatment=self.treatment, number=n)
                for n in range(1, 4)
            ]
        )
        response = self.client.post(
            reverse("web:treatment-update", args=[self.treatment.pk]),
            self._update_payload(total_sessions=2),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Session.objects.count(), 2)

    def test_edit_treatment_decrease_blocked_by_done(self):
        Session.objects.bulk_create(
            [
                Session(treatment=self.treatment, number=n)
                for n in range(1, 4)
            ]
        )
        Session.objects.filter(treatment=self.treatment, number=3).update(
            status=Session.Status.DONE
        )
        response = self.client.post(
            reverse("web:treatment-update", args=[self.treatment.pk]),
            self._update_payload(total_sessions=2),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "No se puede reducir el total de sesiones"
        )
        self.assertEqual(Session.objects.count(), 3)


class AppointmentWebTestCase(WebBaseTestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222"
        )

    def test_create_appointment(self):
        response = self.client.post(
            reverse("web:appointment-create"),
            {
                "patient": self.patient.pk,
                "start_date": "2026-08-20",
                "start_time": "10:00",
                "duration": 30,
                "status": "programada",
            },
        )
        self.assertEqual(response.status_code, 302)
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.start.date().isoformat(), "2026-08-20")
        self.assertEqual(
            timezone.localtime(appointment.start).strftime("%H:%M"), "10:00"
        )

    def test_missing_slot_rejected(self):
        response = self.client.post(
            reverse("web:appointment-create"),
            {
                "patient": self.patient.pk,
                "start_date": "2026-08-20",
                "start_time": "",
                "duration": 30,
                "status": "programada",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Elige el día y un horario libre")

    def test_short_duration_rejected(self):
        response = self.client.post(
            reverse("web:appointment-create"),
            {
                "patient": self.patient.pk,
                "start_date": "2026-08-20",
                "start_time": "10:00",
                "duration": 2,
                "status": "programada",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La duración mínima es de 20 minutos")

    def test_same_start_rejected(self):
        start = timezone.make_aware(
            timezone.datetime(2026, 8, 20, 10, 0)
        )
        Appointment.objects.create(
            patient=self.patient, start=start, duration=45
        )
        response = self.client.post(
            reverse("web:appointment-create"),
            {
                "patient": self.patient.pk,
                "start_date": "2026-08-20",
                "start_time": "10:00",
                "duration": 45,
                "status": "programada",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe una cita")
        self.assertContains(response, "Elige otro día")
        self.assertNotContains(response, "already exists")
        self.assertNotContains(response, "único")

    def test_overlap_rejected(self):
        start = timezone.make_aware(
            timezone.datetime(2026, 8, 20, 10, 0)
        )
        Appointment.objects.create(
            patient=self.patient, start=start, duration=45
        )
        response = self.client.post(
            reverse("web:appointment-create"),
            {
                "patient": self.patient.pk,
                "start_date": "2026-08-20",
                "start_time": "10:30",
                "duration": 45,
                "status": "programada",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "solapa")

    def test_slots_endpoint(self):
        start = timezone.make_aware(timezone.datetime(2026, 8, 20, 10, 0))
        Appointment.objects.create(
            patient=self.patient, start=start, duration=60
        )
        response = self.client.get(
            reverse("web:appointment-slots"),
            {"date": "2026-08-20", "duration": 30},
        )
        self.assertEqual(response.status_code, 200)
        occupied = response.json()["slots"]
        self.assertIn("10:00", occupied)
        self.assertIn("10:30", occupied)
        self.assertNotIn("12:00", occupied)

    def test_slots_endpoint_excludes_cancelled(self):
        start = timezone.make_aware(timezone.datetime(2026, 8, 20, 10, 0))
        Appointment.objects.create(
            patient=self.patient,
            start=start,
            duration=30,
            status=Appointment.Status.CANCELLED,
        )
        response = self.client.get(
            reverse("web:appointment-slots"),
            {"date": "2026-08-20", "duration": 30},
        )
        self.assertNotIn("10:00", response.json()["slots"])

    def test_confirm_action(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            start=timezone.now() + timedelta(days=1),
        )
        response = self.client.post(
            reverse("web:appointment-status", args=[appointment.pk, "confirmar"])
        )
        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)

    def test_complete_action(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            start=timezone.now() + timedelta(days=1),
            status=Appointment.Status.CONFIRMED,
        )
        response = self.client.post(
            reverse("web:appointment-status", args=[appointment.pk, "completar"])
        )
        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

    def test_reprogram_cancelled(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            start=timezone.now() + timedelta(days=1),
            status=Appointment.Status.CANCELLED,
        )
        response = self.client.post(
            reverse("web:appointment-status", args=[appointment.pk, "programar"])
        )
        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)

    def test_status_change_blocked_on_overlap(self):
        start = timezone.make_aware(timezone.datetime(2026, 8, 25, 10, 0))
        Appointment.objects.create(patient=self.patient, start=start, duration=45)
        cancelled = Appointment.objects.create(
            patient=self.patient,
            start=start,
            duration=45,
            status=Appointment.Status.CANCELLED,
        )
        response = self.client.post(
            reverse("web:appointment-status", args=[cancelled.pk, "programar"])
        )
        self.assertEqual(response.status_code, 302)
        cancelled.refresh_from_db()
        self.assertEqual(cancelled.status, Appointment.Status.CANCELLED)

    def test_agenda_page(self):
        day = timezone.localdate()
        Appointment.objects.create(
            patient=self.patient,
            start=timezone.make_aware(
                timezone.datetime.combine(day, timezone.datetime.min.time())
            )
            + timedelta(hours=10),
        )
        response = self.client.get(reverse("web:agenda"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana")


class CalendarWebTestCase(WebBaseTestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222"
        )

    def _week_start(self):
        today = timezone.localdate()
        return today - timedelta(days=today.weekday())

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("web:calendar"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.headers["Location"])

    def test_defaults_to_current_week(self):
        response = self.client.get(reverse("web:calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calendario")
        self.assertContains(
            response, f'value="{self._week_start():%Y-%m-%d}"'
        )

    def test_week_appointments_visible(self):
        day = self._week_start() + timedelta(days=1)
        Appointment.objects.create(
            patient=self.patient,
            start=timezone.make_aware(
                timezone.datetime.combine(day, timezone.datetime.min.time())
            )
            + timedelta(hours=10),
        )
        response = self.client.get(reverse("web:calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana")
        self.assertContains(response, "Lopez")

    def test_outside_week_appointments_hidden(self):
        other = Patient.objects.create(
            first_name="Luis", last_name="Perez", dni="40222333"
        )
        day = self._week_start() + timedelta(days=7)
        Appointment.objects.create(
            patient=other,
            start=timezone.make_aware(
                timezone.datetime.combine(day, timezone.datetime.min.time())
            )
            + timedelta(hours=10),
        )
        response = self.client.get(reverse("web:calendar"))
        self.assertNotContains(response, "Luis")

    def test_cancelled_appointments_hidden(self):
        day = self._week_start()
        Appointment.objects.create(
            patient=self.patient,
            start=timezone.make_aware(
                timezone.datetime.combine(day, timezone.datetime.min.time())
            )
            + timedelta(hours=10),
            status=Appointment.Status.CANCELLED,
        )
        response = self.client.get(reverse("web:calendar"))
        self.assertNotContains(response, "Ana")

    def test_week_start_param_navigates(self):
        prev_week = self._week_start() - timedelta(days=7)
        response = self.client.get(
            reverse("web:calendar"), {"week_start": prev_week.isoformat()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{prev_week:%Y-%m-%d}"')
        self.assertNotContains(
            response, f'value="{self._week_start():%Y-%m-%d}"'
        )

    def test_navigation_links(self):
        response = self.client.get(reverse("web:calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "chevron-double-left")
        self.assertContains(response, "chevron-left")
        self.assertContains(response, "chevron-right")
        self.assertContains(response, "chevron-double-right")
        self.assertContains(response, "Hoy")

    def test_event_positioning(self):
        day = self._week_start()
        Appointment.objects.create(
            patient=self.patient,
            start=timezone.make_aware(
                timezone.datetime.combine(day, timezone.datetime.min.time())
            )
            + timedelta(hours=10),
            duration=50,
        )
        Appointment.objects.create(
            patient=self.patient,
            start=timezone.make_aware(
                timezone.datetime.combine(day, timezone.datetime.min.time())
            )
            + timedelta(hours=12, minutes=30),
            duration=80,
        )
        response = self.client.get(reverse("web:calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'style="top: 0px; height: 50px;"')
        self.assertContains(response, 'style="top: 150px; height: 80px;"')

    def test_clipped_event(self):
        day = self._week_start()
        Appointment.objects.create(
            patient=self.patient,
            start=timezone.make_aware(
                timezone.datetime.combine(day, timezone.datetime.min.time())
            )
            + timedelta(hours=21, minutes=30),
            duration=80,
        )
        response = self.client.get(reverse("web:calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cal-clip-bottom")
        self.assertContains(response, 'style="top: 690px; height: 30px;"')

    def test_invalid_week_start_falls_back(self):
        response = self.client.get(
            reverse("web:calendar"), {"week_start": "basura"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, f'value="{self._week_start():%Y-%m-%d}"'
        )

    def test_week_start_snaps_to_monday(self):
        wednesday = self._week_start() + timedelta(days=2)
        response = self.client.get(
            reverse("web:calendar"), {"week_start": wednesday.isoformat()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, f'value="{self._week_start():%Y-%m-%d}"'
        )
        self.assertNotContains(response, f'value="{wednesday:%Y-%m-%d}"')


class DatabaseDumpTestCase(WebBaseTestCase):
    @mock.patch("apps.web.views.subprocess.run")
    def test_dump_download(self, mock_run):
        mock_run.return_value = mock.Mock(
            returncode=0, stdout=b"-- Kinewind dump\n", stderr=b""
        )
        with mock.patch(
            "apps.web.views.shutil.which", return_value="/usr/bin/pg_dump"
        ):
            response = self.client.get(reverse("web:db-dump"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/sql")
        self.assertIn(
            f'filename="{timezone.localdate():%Y-%m-%d}.sql"',
            response["Content-Disposition"],
        )
        self.assertTrue(response.content.startswith(b"-- Kinewind dump"))

    @mock.patch("apps.web.views.shutil.which", return_value=None)
    def test_dump_missing_pg_dump(self, mock_which):
        response = self.client.get(reverse("web:db-dump"))
        self.assertEqual(response.status_code, 503)

    def test_dump_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("web:db-dump"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.headers["Location"])
