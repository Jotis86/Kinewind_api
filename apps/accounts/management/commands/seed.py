from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Crea el usuario admin de la clínica."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@kinewind.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Admin creado: admin / admin123"))
        else:
            self.stdout.write("El admin ya existía.")

        self.stdout.write(self.style.SUCCESS("Seed finalizado."))
