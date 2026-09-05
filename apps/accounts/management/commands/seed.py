import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Asegura el usuario admin de la clínica (admin/admin123)."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@kinewind.com"},
        )
        password = os.environ.get("ADMIN_PASSWORD", "admin123")
        admin.email = "admin@kinewind.com"
        admin.is_active = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(password)
        admin.save()
        action = "creado" if created else "actualizado"
        self.stdout.write(
            self.style.SUCCESS(f"Admin {action}: admin / {password}")
        )

        self.stdout.write(self.style.SUCCESS("Seed finalizado."))
