from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.patients.models import Patient
from apps.treatments.models import Session, Treatment


class TreatmentSessionsSyncTestCase(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="Ana", last_name="Lopez", dni="40111222"
        )

    def _treatment(self, total=10):
        return Treatment.objects.create(
            patient=self.patient,
            diagnosis="Fisioterapia lumbar",
            total_sessions=total,
        )

    def _sessions(self, treatment, count):
        Session.objects.bulk_create(
            [
                Session(treatment=treatment, number=n)
                for n in range(1, count + 1)
            ]
        )

    def test_creating_treatment_does_not_create_sessions(self):
        treatment = self._treatment(total=10)
        self.assertEqual(treatment.sessions.count(), 0)

    def test_increase_creates_missing_sessions(self):
        treatment = self._treatment(total=3)
        self._sessions(treatment, 2)
        treatment.total_sessions = 5
        treatment.save()
        self.assertEqual(
            list(treatment.sessions.values_list("number", flat=True)),
            [1, 2, 3, 4, 5],
        )
        new = treatment.sessions.get(number=5)
        self.assertEqual(new.status, Session.Status.PENDING)

    def test_increase_continues_from_last_number(self):
        treatment = self._treatment(total=2)
        self._sessions(treatment, 2)
        Session.objects.get(treatment=treatment, number=2).delete()
        treatment.total_sessions = 4
        treatment.save()
        self.assertEqual(
            list(treatment.sessions.values_list("number", flat=True)),
            [1, 2, 3, 4],
        )

    def test_decrease_deletes_sessions_above_total(self):
        treatment = self._treatment(total=10)
        self._sessions(treatment, 10)
        treatment.total_sessions = 7
        treatment.save()
        self.assertEqual(
            list(treatment.sessions.values_list("number", flat=True)),
            list(range(1, 8)),
        )

    def test_decrease_blocked_when_done_above_total(self):
        treatment = self._treatment(total=10)
        self._sessions(treatment, 10)
        Session.objects.filter(treatment=treatment, number__gte=8).update(
            status=Session.Status.DONE
        )
        treatment.total_sessions = 7
        with self.assertRaises(ValidationError):
            treatment.save()
        treatment.refresh_from_db()
        self.assertEqual(treatment.total_sessions, 10)
        self.assertEqual(treatment.sessions.count(), 10)

    def test_decrease_allowed_when_done_below_total(self):
        treatment = self._treatment(total=10)
        self._sessions(treatment, 10)
        Session.objects.filter(treatment=treatment, number=1).update(
            status=Session.Status.DONE
        )
        treatment.total_sessions = 7
        treatment.save()
        self.assertEqual(treatment.sessions.count(), 7)
        self.assertEqual(
            list(treatment.sessions.values_list("number", flat=True)),
            list(range(1, 8)),
        )

    def test_no_total_change_is_noop(self):
        treatment = self._treatment(total=3)
        self._sessions(treatment, 1)
        treatment.diagnosis = "Otro diagnóstico"
        treatment.save()
        self.assertEqual(treatment.sessions.count(), 1)
        self.assertEqual(
            list(treatment.sessions.values_list("number", flat=True)),
            [1],
        )
