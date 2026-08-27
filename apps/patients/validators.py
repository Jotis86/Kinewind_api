import re

from django.core.exceptions import ValidationError

# 7-8 dígitos con letra opcional (DNI) o NIE (X/Y/Z + 7 dígitos + letra)
DNI_RE = re.compile(r"^(?:[0-9]{7,8}[A-Za-z]?|[XYZ][0-9]{7}[A-Za-z])$")

# Teléfono español: 9 dígitos con separadores opcionales y prefijo +34/0034 opcional
PHONE_RE = re.compile(r"^(\+34|0034)?[\s.-]?\d{3}[\s.-]?\d{3}[\s.-]?\d{3}$")

DNI_ERROR = "DNI inválido: 7 u 8 dígitos, opcionalmente seguido de una letra (o NIE)."
PHONE_ERROR = "Teléfono inválido: 9 dígitos, con prefijo +34 opcional."


def validate_dni_format(value):
    if not DNI_RE.match(str(value)):
        raise ValidationError(DNI_ERROR)


def validate_phone_format(value):
    if not PHONE_RE.match(str(value)):
        raise ValidationError(PHONE_ERROR)
