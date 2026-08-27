from datetime import datetime as _dt
from datetime import time as _time
from datetime import timedelta

from .models import Appointment

OVERLAP_ERROR = "Ya existe una cita en ese horario. Elige otro día u horario."

SLOT_START = _time(10, 0)
SLOT_END = _time(22, 0)
SLOT_STEP = timedelta(minutes=30)
DURATION_CHOICES = (20, 50, 80)


def slot_times():
    """Huecos de 30 min entre 10:00 y 22:00 (último 21:30)."""
    start = _dt(2000, 1, 1, SLOT_START.hour, SLOT_START.minute)
    end = _dt(2000, 1, 1, SLOT_END.hour, SLOT_END.minute)
    times = []
    current = start
    while current < end:
        times.append(current.strftime("%H:%M"))
        current += SLOT_STEP
    return times


def appointments_overlap(start, duration, exclude_pk=None):
    """Devuelve True si [start, start+duration) solapa con una cita vigente.

    Las citas canceladas no bloquean el horario (se puede re-reservar).
    """
    end = start + timedelta(minutes=duration)

    day_start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    candidates = Appointment.objects.filter(
        start__gte=day_start, start__lt=day_start + timedelta(days=1)
    ).exclude(status=Appointment.Status.CANCELLED)
    if exclude_pk:
        candidates = candidates.exclude(pk=exclude_pk)

    for existing in candidates:
        if start < existing.end and existing.start < end:
            return True
    return False
