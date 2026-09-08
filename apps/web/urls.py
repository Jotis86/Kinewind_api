from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("login/", views.LoginPageView.as_view(), name="login"),
    path("logout/", views.LogoutPageView.as_view(), name="logout"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Pacientes
    path("pacientes/", views.PatientListView.as_view(), name="patient-list"),
    path("pacientes/nuevo/", views.PatientCreateView.as_view(), name="patient-create"),
    path(
        "pacientes/<int:pk>/",
        views.PatientDetailView.as_view(),
        name="patient-detail",
    ),
    path(
        "pacientes/<int:pk>/editar/",
        views.PatientUpdateView.as_view(),
        name="patient-update",
    ),
    path(
        "pacientes/<int:pk>/baja/",
        views.PatientDeleteView.as_view(),
        name="patient-delete",
    ),
    path(
        "pacientes/<int:pk>/reactivar/",
        views.PatientActivateView.as_view(),
        name="patient-activate",
    ),
    # Tratamientos
    path("tratamientos/", views.TreatmentListView.as_view(), name="treatment-list"),
    path(
        "tratamientos/nuevo/",
        views.TreatmentCreateView.as_view(),
        name="treatment-create",
    ),
    path(
        "tratamientos/<int:pk>/",
        views.TreatmentDetailView.as_view(),
        name="treatment-detail",
    ),
    path(
        "tratamientos/<int:pk>/editar/",
        views.TreatmentUpdateView.as_view(),
        name="treatment-update",
    ),
    path(
        "tratamientos/<int:pk>/eliminar/",
        views.TreatmentDeleteView.as_view(),
        name="treatment-delete",
    ),
    path(
        "tratamientos/<int:pk>/finalizar/",
        views.TreatmentFinishView.as_view(),
        name="treatment-finish",
    ),
    path(
        "tratamientos/<int:pk>/pdf/",
        views.TreatmentPDFView.as_view(),
        name="treatment-pdf",
    ),
    # Sesiones
    path(
        "tratamientos/<int:treatment_pk>/sesiones/nueva/",
        views.SessionCreateView.as_view(),
        name="session-create",
    ),
    path(
        "sesiones/<int:pk>/editar/",
        views.SessionUpdateView.as_view(),
        name="session-update",
    ),
    path(
        "sesiones/<int:pk>/eliminar/",
        views.SessionDeleteView.as_view(),
        name="session-delete",
    ),
    path(
        "sesiones/<int:pk>/realizar/",
        views.SessionCompleteView.as_view(),
        name="session-complete",
    ),
    # Citas
    path("citas/", views.AppointmentListView.as_view(), name="appointment-list"),
    path("citas/slots/", views.AppointmentSlotsView.as_view(), name="appointment-slots"),
    path("citas/nueva/", views.AppointmentCreateView.as_view(), name="appointment-create"),
    path(
        "citas/<int:pk>/editar/",
        views.AppointmentUpdateView.as_view(),
        name="appointment-update",
    ),
    path(
        "citas/<int:pk>/eliminar/",
        views.AppointmentDeleteView.as_view(),
        name="appointment-delete",
    ),
    path(
        "citas/<int:pk>/<str:action>/",
        views.AppointmentStatusView.as_view(),
        name="appointment-status",
    ),
    path("agenda/", views.AgendaView.as_view(), name="agenda"),
    path("calendario/", views.CalendarView.as_view(), name="calendar"),
    path("dump/", views.DatabaseDumpView.as_view(), name="db-dump"),
]
