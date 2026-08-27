from django.core.exceptions import ValidationError
from django.db.models import Max
from django.utils import timezone

from .models import Session

SESSIONS_SYNC_ERROR = (
    "No se puede reducir el total de sesiones: hay sesiones "
    "ya realizadas por encima del nuevo total."
)


def validate_sessions_sync(treatment, new_total):
    """Devuelve el error si reducir el total borraría sesiones realizadas.

    Es la parte validable del ajuste: el resto (crear/borrar filas) no
    puede fallar y lo hace `sync_treatment_sessions`.
    """
    extra = treatment.sessions.filter(number__gt=new_total)
    if extra.filter(status=Session.Status.DONE).exists():
        return SESSIONS_SYNC_ERROR
    return None


def sync_treatment_sessions(treatment, new_total):
    """Ajusta las filas de sesión al total planificado del tratamiento.

    - Si el total sube, crea las sesiones que faltan (números consecutivos
      a partir de la última existente, fecha de hoy, estado pendiente).
    - Si baja, borra las sesiones con número por encima del nuevo total.
      Se niega si eso eliminaría sesiones ya realizadas.
    """
    current_count = treatment.sessions.count()
    if current_count == new_total:
        return

    if current_count < new_total:
        last = treatment.sessions.aggregate(max=Max("number"))["max"] or 0
        Session.objects.bulk_create(
            [
                Session(
                    treatment=treatment,
                    number=n,
                    date=timezone.localdate(),
                )
                for n in range(last + 1, new_total + 1)
            ]
        )
        return

    error = validate_sessions_sync(treatment, new_total)
    if error:
        raise ValidationError({"total_sessions": error})
    treatment.sessions.filter(number__gt=new_total).delete()
