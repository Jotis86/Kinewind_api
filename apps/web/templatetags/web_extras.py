from django import template

register = template.Library()

_STATUS_MAP = {
    "programada": "warning",
    "confirmada": "primary",
    "cancelada": "danger",
    "completada": "info",
    "pendiente": "warning",
    "realizada": "success",
    "activo": "success",
    "finalizado": "info",
    "cancelado": "danger",
}


@register.filter
def status_class(value):
    """Devuelve la variante de badge (primary/success/...) según el estado."""
    return _STATUS_MAP.get(str(value), "secondary")


@register.filter
def percent(value, max_value):
    """Porcentaje de value sobre max_value (para barras de progreso)."""
    try:
        value = int(value)
        max_value = int(max_value)
    except (TypeError, ValueError):
        return 0
    if max_value <= 0:
        return 0
    return int(value * 100 / max_value)
