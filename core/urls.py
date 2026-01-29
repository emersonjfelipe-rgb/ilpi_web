from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("pacientes/", views.pacientes_list, name="pacientes_list"),
    path("pacientes/novo/", views.paciente_create, name="paciente_create"),
    path("pacientes/<int:pk>/editar/", views.paciente_update, name="paciente_update"),
    path("pacientes/<int:pk>/excluir/", views.paciente_delete, name="paciente_delete"),
    path("pacientes/<int:pk>/", views.paciente_detail, name="paciente_detail"),
    path("pacientes/<int:pk>/chart/sinais/", views.paciente_sinais_chart, name="paciente_sinais_chart"),
    path("pacientes/<int:pk>/pdf/", views.paciente_pdf, name="paciente_pdf"),
    path("pacientes/<int:pk>/meds-dia/", views.meds_dia, name="meds_dia"),

    path("medicamentos/", views.medicamentos_list, name="medicamentos_list"),
    path("medicamentos/novo/", views.medicamento_create, name="medicamento_create"),
    path("medicamentos/pdf/", views.medicamentos_pdf, name="medicamentos_pdf"),

    path("sinais/", views.sinais_list, name="sinais_list"),
    path("sinais/novo/", views.sinal_create, name="sinal_create"),
    path("sinais/<int:pk>/editar/", views.sinal_update, name="sinal_update"),
    path("sinais/<int:pk>/excluir/", views.sinal_delete, name="sinal_delete"),
    path("sinais/pdf/", views.sinais_pdf, name="sinais_pdf"),
    path("sinais/csv/", views.sinais_csv, name="sinais_csv"),

    path("ocorrencias/", views.ocorrencias_list, name="ocorrencias_list"),
    path("ocorrencias/nova/", views.ocorrencia_create, name="ocorrencia_create"),
    path("ocorrencias/<int:pk>/editar/", views.ocorrencia_update, name="ocorrencia_update"),
    path("ocorrencias/<int:pk>/excluir/", views.ocorrencia_delete, name="ocorrencia_delete"),
    path("ocorrencias/pdf/", views.ocorrencias_pdf, name="ocorrencias_pdf"),

    path("dose/<int:pk>/toggle/", views.dose_toggle, name="dose_toggle"),

    # Modais Sinais (se você já tem)
    path("pacientes/<int:pk>/sinais/modal/novo/", views.sinal_modal_create, name="sinal_modal_create"),
    path("sinais/<int:pk>/modal/editar/", views.sinal_modal_update, name="sinal_modal_update"),

    # Dashboard PDF
    path("dashboard/pdf/", views.dashboard_pdf, name="dashboard_pdf"),

    # ESTOQUE
    path("estoque/", views.estoque_dashboard, name="estoque_dashboard"),
    path("estoque/med/novo/", views.estoque_med_create, name="estoque_med_create"),
    path("estoque/fralda/novo/", views.estoque_fralda_create, name="estoque_fralda_create"),
]
