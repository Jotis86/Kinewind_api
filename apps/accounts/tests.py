from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.patients.models import Patient
from apps.treatments.models import Session, Treatment


class BaseAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="fisio", email="fisio@kinewind.com", password="pass12345"
        )
        self.client.force_authenticate(self.user)
        self.patient = Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222", phone="11 1234-5678"
        )


class AuthTestCase(BaseAPITestCase):
    def test_login_returns_tokens(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "fisio", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_me_requires_auth(self):
        self.client.force_authenticate(None)
        response = self.client.get(reverse("accounts:me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_blocked_when_user_exists(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            reverse("accounts:register"),
            {"username": "otro", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_register_first_run(self):
        User.objects.all().delete()
        self.client.force_authenticate(None)
        response = self.client.post(
            reverse("accounts:register"),
            {"username": "admin2", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class PatientTestCase(BaseAPITestCase):
    def test_create_patient(self):
        response = self.client.post(
            reverse("patient-list"),
            {"first_name": "Pedro", "last_name": "Sosa", "dni": "40222333"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_api_duplicate_dni(self):
        self.client.post(
            reverse("patient-list"),
            {"first_name": "Ana", "last_name": "Lopez", "dni": "40222333"},
            format="json",
        )
        response = self.client.post(
            reverse("patient-list"),
            {"first_name": "Otro", "last_name": "Paciente", "dni": "40222333"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = str(response.data["dni"])
        self.assertIn("Ya existe un paciente con ese DNI", errors)
        self.assertNotIn("debe ser único", errors)

    def test_api_duplicate_dni_case_insensitive(self):
        self.client.post(
            reverse("patient-list"),
            {"first_name": "Ana", "last_name": "Lopez", "dni": "40222333A"},
            format="json",
        )
        response = self.client.post(
            reverse("patient-list"),
            {"first_name": "Otro", "last_name": "Paciente", "dni": "40222333a"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_dni_uppercased(self):
        response = self.client.post(
            reverse("patient-list"),
            {"first_name": "Pedro", "last_name": "Sosa", "dni": "40222333b"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["dni"], "40222333B")

    def test_api_invalid_dni_format(self):
        response = self.client.post(
            reverse("patient-list"),
            {"first_name": "Ana", "last_name": "Lopez", "dni": "abc"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_invalid_phone(self):
        response = self.client.post(
            reverse("patient-list"),
            {
                "first_name": "Ana",
                "last_name": "Lopez",
                "dni": "40222333",
                "phone": "no-valido",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logical_delete(self):
        response = self.client.delete(
            reverse("patient-detail", args=[self.patient.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.active)

    def test_list_treatments(self):
        treatment = Treatment.objects.create(
            patient=self.patient, diagnosis="Hombro", total_sessions=4
        )
        response = self.client.get(
            reverse("patient-treatments", args=[self.patient.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], treatment.pk)

    def test_list_appointments(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            start=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(
            reverse("patient-appointments", args=[self.patient.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], appointment.pk)


class TreatmentTestCase(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.treatment = Treatment.objects.create(
            patient=self.patient, diagnosis="Rodilla", total_sessions=5
        )

    def test_create_session_nested(self):
        response = self.client.post(
            reverse("treatment-sessions", args=[self.treatment.pk]),
            {"number": 1, "date": "2026-08-20"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Session.objects.count(), 1)

    def test_session_unique_number(self):
        Session.objects.create(treatment=self.treatment, number=1)
        response = self.client.post(
            reverse("treatment-sessions", args=[self.treatment.pk]),
            {"number": 1, "date": "2026-08-21"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sessions_done_property(self):
        Session.objects.create(
            treatment=self.treatment, number=1, status=Session.Status.DONE
        )
        Session.objects.create(
            treatment=self.treatment, number=2, status=Session.Status.PENDING
        )
        self.treatment.refresh_from_db()
        self.assertEqual(self.treatment.sessions_done, 1)

    def test_list_treatments_no_n_plus_one(self):
        for i in range(5):
            treatment = Treatment.objects.create(
                patient=self.patient,
                diagnosis=f"Patología {i}",
                total_sessions=2,
            )
            Session.objects.create(
                treatment=treatment, number=1, status=Session.Status.DONE
            )
        with self.assertNumQueries(2):
            response = self.client.get(reverse("treatment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        done = {t["id"]: t["sessions_done"] for t in response.data["results"]}
        self.assertEqual(sum(done.values()), 5)


class AppointmentTestCase(BaseAPITestCase):
    def test_overlap_rejected(self):
        start = timezone.now() + timedelta(days=2)
        Appointment.objects.create(patient=self.patient, start=start, duration=45)
        response = self.client.post(
            reverse("appointment-list"),
            {
                "patient": self.patient.pk,
                "start": (start + timedelta(minutes=30)).isoformat(),
                "duration": 45,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_same_start_rejected(self):
        start = timezone.now() + timedelta(days=2)
        Appointment.objects.create(patient=self.patient, start=start, duration=45)
        response = self.client.post(
            reverse("appointment-list"),
            {
                "patient": self.patient.pk,
                "start": start.isoformat(),
                "duration": 45,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = str(response.data)
        self.assertIn("Ya existe una cita", errors)
        self.assertIn("Elige otro día", errors)
        self.assertNotIn("unique", errors.lower())
        self.assertNotIn("fecha y hora", errors)

    def test_db_unique_start(self):
        from django.db import IntegrityError

        start = timezone.now() + timedelta(days=2)
        Appointment.objects.create(patient=self.patient, start=start, duration=45)
        with self.assertRaises(IntegrityError):
            Appointment.objects.create(
                patient=self.patient, start=start, duration=45
            )

    def test_cancelled_does_not_block_slot(self):
        start = timezone.now() + timedelta(days=2)
        Appointment.objects.create(
            patient=self.patient,
            start=start,
            duration=45,
            status=Appointment.Status.CANCELLED,
        )
        appointment = Appointment.objects.create(
            patient=self.patient, start=start, duration=45
        )
        self.assertEqual(
            appointment.status, Appointment.Status.SCHEDULED
        )

    def test_non_overlap_accepted(self):
        start = timezone.now() + timedelta(days=2)
        Appointment.objects.create(patient=self.patient, start=start, duration=45)
        response = self.client.post(
            reverse("appointment-list"),
            {
                "patient": self.patient.pk,
                "start": (start + timedelta(hours=2)).isoformat(),
                "duration": 45,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_agenda_endpoint(self):
        day = timezone.localdate()
        start = timezone.make_aware(
            timezone.datetime.combine(day, timezone.datetime.min.time())
        ) + timedelta(hours=10)
        Appointment.objects.create(patient=self.patient, start=start)
        response = self.client.get(reverse("appointment-agenda"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["date"], day.isoformat())
        self.assertEqual(len(response.data["appointments"]), 1)
