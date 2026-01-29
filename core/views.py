from django.core.exceptions import PermissionDenied
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Count
from .models import Paciente, Auditoria
from .models import Medicamento
from .models import SinalVital
from .models import Ocorrencia
from django.db.models import F
from .models import Paciente
import csv
from .utils import calc_idade, calc_tempo_ilpi, paciente_flags
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import date, timedelta
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models.functions import TruncDate
from django.conf import settings
from .models import Paciente, SinalVital
from django.shortcuts import get_object_or_404, render
from datetime import date, datetime
from django.utils.timezone import now
from datetime import time
from django.db.models import F
from django.shortcuts import redirect
from django.contrib import messages
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from datetime import datetime
from django.utils.timezone import make_aware
from django.contrib.staticfiles import finders
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from django.http import HttpResponseForbidden
from django.conf import settings
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from .utils import calc_idade, calc_tempo_ilpi
from .models import Paciente, EstoqueMedicamento, MovEstoqueMedicamento, EstoqueFralda, MovEstoqueFralda
from .models import EstoqueMedicamento, EstoqueFralda
def can_export_pdf(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    groups = getattr(settings, "PDF_EXPORT_GROUPS", ["admin"])
    return user.groups.filter(name__in=groups).exists()


@login_required
def ocorrencias_pdf(request):
    ini = request.GET.get("ini")
    fim = request.GET.get("fim")

    qs = Ocorrencia.objects.select_related("paciente").order_by("-data_hora")

    if ini:
        qs = qs.filter(data_hora__date__gte=ini)
    if fim:
        qs = qs.filter(data_hora__date__lte=fim)

    html = render(
        request,
        "core/relatorio_ocorrencias.html",
        {
            "titulo": "Relatório de Ocorrências",
            "ocorrencias": qs,
            "ini": ini,
            "fim": fim,
        },
    ).content

    response = HttpResponse(html, content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=ocorrencias.html"
    return response

@login_required
def sinais_csv(request):
    ini = request.GET.get("ini")
    fim = request.GET.get("fim")

    qs = SinalVital.objects.select_related("paciente").order_by("-data_hora")

    if ini:
        qs = qs.filter(data_hora__date__gte=ini)
    if fim:
        qs = qs.filter(data_hora__date__lte=fim)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=sinais.csv"

    writer = csv.writer(response)
    writer.writerow(["Paciente", "Data", "Temp", "Sat", "Dextro", "PA", "FC"])

    for s in qs:
        writer.writerow([
            s.paciente.nome,
            s.data_hora,
            s.temperatura,
            s.saturacao_oxigenio,
            s.glicemia,
            s.pressao_arterial,
            s.frequencia_cardiaca,
        ])

    return response


@login_required
def sinais_pdf(request):
    ini = request.GET.get("ini")
    fim = request.GET.get("fim")

    qs = SinalVital.objects.select_related("paciente").order_by("-data_hora")

    if ini:
        qs = qs.filter(data_hora__date__gte=ini)
    if fim:
        qs = qs.filter(data_hora__date__lte=fim)

    html = render(
        request,
        "core/relatorio_sinais.html",
        {
            "titulo": "Relatório de Sinais Vitais",
            "sinais": qs,
            "ini": ini,
            "fim": fim,
        },
    ).content

    response = HttpResponse(html, content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=sinais.html"
    return response


@login_required
def sinal_modal_create(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)

    if request.method == "POST":
        SinalVital.objects.create(
            paciente=paciente,
            data_hora=now(),
            temperatura=parse_float_br(request.POST.get("temperatura")),
            saturacao_oxigenio=parse_float_br(request.POST.get("saturacao_oxigenio")),
            glicemia=parse_float_br(request.POST.get("glicemia")),
            pressao_arterial=request.POST.get("pressao_arterial") or None,
            frequencia_cardiaca=request.POST.get("frequencia_cardiaca") or None,
            frequencia_respiratoria=request.POST.get("frequencia_respiratoria") or None,
            dor_escala=request.POST.get("dor_escala") or None,
            observacoes=request.POST.get("observacoes") or None,
            usuario=request.user,
        )
        return JsonResponse({"ok": True})

    html = render_to_string(
        "core/partials/sinal_modal_form.html",
        {"paciente": paciente},
        request=request,
    )
    return JsonResponse({"html": html})

@login_required
def sinal_modal_update(request, pk):
    sinal = get_object_or_404(SinalVital, pk=pk)

    if request.method == "POST":
        sinal.temperatura = parse_float_br(request.POST.get("temperatura"))
        sinal.saturacao_oxigenio = parse_float_br(request.POST.get("saturacao_oxigenio"))
        sinal.glicemia = parse_float_br(request.POST.get("glicemia"))
        sinal.pressao_arterial = request.POST.get("pressao_arterial") or None
        sinal.frequencia_cardiaca = request.POST.get("frequencia_cardiaca") or None
        sinal.frequencia_respiratoria = request.POST.get("frequencia_respiratoria") or None
        sinal.dor_escala = request.POST.get("dor_escala") or None
        sinal.observacoes = request.POST.get("observacoes") or None
        sinal.save()
        return JsonResponse({"ok": True})

    html = render_to_string(
        "core/partials/sinal_modal_form.html",
        {"paciente": sinal.paciente, "sinal": sinal},
        request=request,
    )
    return JsonResponse({"html": html})


@login_required
def sinal_update(request, pk):
    if not can_edit_advanced(request.user):
        raise PermissionDenied

    s = SinalVital.objects.select_related("paciente").get(pk=pk)
    pacientes = Paciente.objects.order_by("nome")

    if request.method == "POST":
        paciente_id = request.POST.get("paciente_id")
        s.paciente = Paciente.objects.get(id=paciente_id)

        # use seu parse_float_br aqui:
        s.temperatura = parse_float_br(request.POST.get("temperatura"))
        s.saturacao_oxigenio = parse_float_br(request.POST.get("saturacao_oxigenio"))
        s.glicemia = parse_float_br(request.POST.get("glicemia"))

        s.pressao_arterial = request.POST.get("pressao_arterial") or None
        s.frequencia_cardiaca = request.POST.get("frequencia_cardiaca") or None
        s.frequencia_respiratoria = request.POST.get("frequencia_respiratoria") or None
        s.dor_escala = request.POST.get("dor_escala") or None
        s.observacoes = request.POST.get("observacoes") or None
        s.usuario = request.user

        s.save()

        # volta pro paciente já na aba sinais
        return redirect(f"/pacientes/{s.paciente.id}/?tab=sinais")

    return render(request, "core/sinais_form.html", {
        "pacientes": pacientes,
        "obj": s,   # para preencher o form
        "modo": "editar",
    })
@login_required
def sinal_delete(request, pk):
    if not can_delete_advanced(request.user):
        raise PermissionDenied

    s = SinalVital.objects.select_related("paciente").get(pk=pk)

    if request.method == "POST":
        paciente_id = s.paciente.id
        s.delete()
        return redirect(f"/pacientes/{paciente_id}/?tab=sinais")

    return render(request, "core/confirm_delete.html", {
        "titulo": "Excluir Sinal Vital",
        "mensagem": f"Tem certeza que deseja excluir este registro de sinais vitais?",
        "voltar_url": f"/pacientes/{s.paciente.id}/?tab=sinais",
    })

@login_required
def ocorrencia_update(request, pk):
    if not can_edit_advanced(request.user):
        raise PermissionDenied

    o = Ocorrencia.objects.select_related("paciente").get(pk=pk)
    pacientes = Paciente.objects.order_by("nome")

    if request.method == "POST":
        paciente_id = request.POST.get("paciente_id")
        o.paciente = Paciente.objects.get(id=paciente_id)

        o.tipo_ocorrencia = request.POST.get("tipo_ocorrencia") or ""
        o.gravidade = request.POST.get("gravidade") or None
        o.descricao = request.POST.get("descricao") or ""
        o.conduta = request.POST.get("conduta") or None
        o.observacoes = request.POST.get("observacoes") or None

        resolvido = request.POST.get("resolvido") == "1"
        o.resolvido = resolvido
        if resolvido and not o.data_resolucao:
            from django.utils.timezone import now
            o.data_resolucao = now()
        if not resolvido:
            o.data_resolucao = None

        o.usuario = request.user
        o.save()

        return redirect(f"/pacientes/{o.paciente.id}/?tab=oc")

    return render(request, "core/ocorrencias_form.html", {
        "pacientes": pacientes,
        "obj": o,
        "modo": "editar",
    })
@login_required
def ocorrencia_delete(request, pk):
    if not can_delete_advanced(request.user):
        raise PermissionDenied

    o = Ocorrencia.objects.select_related("paciente").get(pk=pk)

    if request.method == "POST":
        paciente_id = o.paciente.id
        o.delete()
        return redirect(f"/pacientes/{paciente_id}/?tab=oc")

    return render(request, "core/confirm_delete.html", {
        "titulo": "Excluir Ocorrência",
        "mensagem": "Tem certeza que deseja excluir esta ocorrência?",
        "voltar_url": f"/pacientes/{o.paciente.id}/?tab=oc",
    })


def user_in_group(user, name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=name).exists()

def can_edit_advanced(user) -> bool:
    return user.is_superuser or user_in_group(user, "admin") or user_in_group(user, "enfermagem")

def can_delete_advanced(user) -> bool:
    return user.is_superuser or user_in_group(user, "admin")


def parse_float_br(value):
    """
    Aceita '36,6' ou '36.6' e devolve float.
    Retorna None se vier vazio.
    """
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    value = value.replace(".", "").replace(",", ".")  # '1.234,5' -> '1234.5'
    return float(value)


@login_required
def paciente_detail(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    idade = calc_idade(paciente.data_nascimento)
    tempo_ilpi = calc_tempo_ilpi(paciente.data_entrada)
    flags = paciente_flags(paciente)

    # aba ativa (via ?tab=)
    tab = request.GET.get("tab", "dados")
    allowed = {"dados", "meds", "sinais", "ocorrencias", "prescricoes", "mar"}
    if tab not in allowed:
        tab = "dados"

    # filtros por período (sinais/ocorrencias)
    inicio = request.GET.get("inicio", "")
    fim = request.GET.get("fim", "")

    # Medicamentos (model legado)
    medicamentos = Medicamento.objects.filter(paciente=paciente).order_by("nome_medicamento")

    # Sinais vitais + filtro
    sinais_qs = SinalVital.objects.filter(paciente=paciente).order_by("-data_hora")
    if inicio:
        sinais_qs = sinais_qs.filter(data_hora__date__gte=inicio)
    if fim:
        sinais_qs = sinais_qs.filter(data_hora__date__lte=fim)
    sinais = sinais_qs[:200]  # limite p/ não pesar

    # cards de média (sinais)
    media_temp = sinais_qs.aggregate(v=Avg("temperatura"))["v"]
    media_fc = sinais_qs.aggregate(v=Avg("frequencia_cardiaca"))["v"]
    media_sat = sinais_qs.aggregate(v=Avg("saturacao_oxigenio"))["v"]

    # Ocorrências + filtro
    ocorr_qs = Ocorrencia.objects.filter(paciente=paciente).order_by("-data_hora")
    if inicio:
        ocorr_qs = ocorr_qs.filter(data_hora__date__gte=inicio)
    if fim:
        ocorr_qs = ocorr_qs.filter(data_hora__date__lte=fim)
    ocorrencias = ocorr_qs[:200]

    pendentes = Ocorrencia.objects.filter(paciente=paciente, resolvido=False).count()

    # Prescrições (se você for migrar p/ MAR profissional)
    prescricoes = Prescricao.objects.filter(paciente=paciente).order_by("-ativa", "nome_medicamento")

    # MAR do dia (Administração de doses)
    hoje = date.today()
    mar = (
        AdministracaoDose.objects
        .filter(prescricao__paciente=paciente, data=hoje)
        .select_related("prescricao", "administrado_por")
        .order_by("horario", "prescricao__nome_medicamento")
    )

    context = {
        "paciente": paciente,    
        "idade": idade,
        "tempo_ilpi": tempo_ilpi,
        "tab": tab,
        "flags": flags,
        "inicio": inicio,
        "fim": fim,
        "medicamentos": medicamentos,
        "sinais": sinais,
        "ocorrencias": ocorrencias,
        "pendentes": pendentes,
        "media_temp": media_temp,
        "media_fc": media_fc,
        "media_sat": media_sat,
        "prescricoes": prescricoes,
        "mar": mar,
    }
    return render(request, "core/paciente_detail.html", context)
@login_required
def paciente_pdf(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)

    medicamentos = Medicamento.objects.filter(paciente=paciente).order_by("nome_medicamento")
    sinais = SinalVital.objects.filter(paciente=paciente).order_by("-data_hora")[:30]
    ocorrencias = Ocorrencia.objects.filter(paciente=paciente).order_by("-data_hora")[:30]

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="paciente_{paciente.id}.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    x = 2 * cm
    y = height - 2 * cm

    def draw_title(text):
        nonlocal y
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x, y, text)
        y -= 0.8 * cm

    def draw_section(text):
        nonlocal y
        y -= 0.2 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, text)
        y -= 0.6 * cm
        c.setLineWidth(0.5)
        c.line(x, y, width - x, y)
        y -= 0.5 * cm

    def draw_kv(label, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, f"{label}:")
        c.setFont("Helvetica", 10)
        c.drawString(x + 4.0*cm, y, str(value or "—"))
        y -= 0.5 * cm

    def draw_paragraph(text, max_width_chars=110):
        nonlocal y
        c.setFont("Helvetica", 9)
        lines = simpleSplit(text or "", "Helvetica", 9, width - 2*x)
        for line in lines:
            if y < 2.5*cm:
                c.showPage()
                y = height - 2*cm
            c.drawString(x, y, line)
            y -= 0.45 * cm

    # Cabeçalho
    draw_title("Ficha Completa do Paciente")
    c.setFont("Helvetica", 9)
    c.drawString(x, y, f"Gerado em: {request.user.username}")
    y -= 0.7 * cm

    # Dados do paciente
    draw_section("Dados do Paciente")
    draw_kv("Nome", paciente.nome)
    draw_kv("Sexo", getattr(paciente, "sexo", "—"))
    draw_kv("Nascimento", getattr(paciente, "data_nascimento", "—"))
    draw_kv("CPF", getattr(paciente, "cpf", "—"))
    draw_kv("Entrada ILPI", getattr(paciente, "entrada_ilpi", "—"))
    draw_kv("Quarto/Leito", f"{getattr(paciente, 'quarto', '')} / {getattr(paciente, 'leito', '')}")
    draw_kv("Grau", getattr(paciente, "grau_dependencia", "—"))
    draw_kv("Contato", getattr(paciente, "contato_emergencia", "—"))
    draw_kv("Telefone", getattr(paciente, "telefone_emergencia", "—"))

    # Medicamentos
    draw_section("Medicamentos")
    if not medicamentos:
        draw_paragraph("Sem medicamentos cadastrados.")
    else:
        for m in medicamentos:
            if y < 3.0*cm:
                c.showPage()
                y = height - 2*cm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, f"- {m.nome_medicamento}")
            y -= 0.5*cm
            c.setFont("Helvetica", 9)
            c.drawString(x+0.5*cm, y, f"Dosagem: {m.dosagem or ''} | Via: {m.via_administracao or ''} | Freq: {m.frequencia or ''} | Horários: {m.horarios or ''}")
            y -= 0.6*cm

    # Sinais vitais
    draw_section("Últimos Sinais Vitais (30)")
    if not sinais:
        draw_paragraph("Sem sinais vitais.")
    else:
        for s in sinais:
            if y < 3.0*cm:
                c.showPage()
                y = height - 2*cm
            c.setFont("Helvetica", 9)
            c.drawString(x, y, f"{s.data_hora} | T={s.temperatura} | PA={s.pressao_arterial} | FC={s.frequencia_cardiaca} | Sat={s.saturacao_oxigenio} | Glic={s.glicemia} | Dor={s.dor_escala}")
            y -= 0.45*cm

    # Ocorrências
    draw_section("Últimas Ocorrências (30)")
    if not ocorrencias:
        draw_paragraph("Sem ocorrências.")
    else:
        for o in ocorrencias:
            if y < 3.0*cm:
                c.showPage()
                y = height - 2*cm
            status = "Resolvida" if o.resolvido else "Pendente"
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x, y, f"{o.data_hora} | {o.tipo_ocorrencia} | {o.gravidade} | {status}")
            y -= 0.45*cm
            c.setFont("Helvetica", 9)
            draw_paragraph(f"Descrição: {o.descricao}", max_width_chars=110)
            y -= 0.2*cm

    c.showPage()
    c.save()
    return response

@login_required
def meds_dia(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    dia = date.today()

    gerar_doses_do_dia(paciente, dia)

    doses = (AdministracaoDose.objects
             .filter(prescricao__paciente=paciente, data=dia, prescricao__ativa=True)
             .select_related("prescricao")
             .order_by("horario", "prescricao__nome_medicamento"))

    return render(request, "core/meds_dia.html", {
        "paciente": paciente,
        "dia": dia,
        "doses": doses,
    })

@login_required
def dose_toggle(request, pk):
    dose = get_object_or_404(AdministracaoDose, pk=pk)

    dose.administrado = not dose.administrado
    if dose.administrado:
        dose.administrado_em = now()
        dose.administrado_por = request.user
    else:
        dose.administrado_em = None
        dose.administrado_por = None

    dose.save()
    return redirect("meds_dia", pk=dose.prescricao.paciente_id)


def parse_horarios(horarios_str):
    # "06:00, 14:00, 22:00" -> [time(6,0), time(14,0), time(22,0)]
    out = []
    if not horarios_str:
        return out
    for part in horarios_str.split(","):
        part = part.strip()
        if not part:
            continue
        h, m = part.split(":")
        out.append(time(int(h), int(m)))
    return out

def gerar_doses_do_dia(paciente, dia):
    prescricoes = Prescricao.objects.filter(paciente=paciente, ativa=True)
    for p in prescricoes:
        for t in parse_horarios(p.horarios):
            AdministracaoDose.objects.get_or_create(
                prescricao=p,
                data=dia,
                horario=t,
            )


@login_required
def paciente_pdf(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)

    medicamentos = Medicamento.objects.filter(paciente=paciente).order_by("nome_medicamento")
    sinais = SinalVital.objects.filter(paciente=paciente).order_by("-data_hora")[:50]
    ocorrencias = Ocorrencia.objects.filter(paciente=paciente).order_by("-data_hora")[:50]

    html_string = render_to_string("core/paciente_pdf.html", {
        "paciente": paciente,
        "medicamentos": medicamentos,
        "sinais": sinais,
        "ocorrencias": ocorrencias,
        "user": request.user,
    })

    html = HTML(string=html_string, base_url=str(settings.BASE_DIR))
    pdf_bytes = html.write_pdf()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="paciente_{paciente.id}.pdf"'
    return response

def is_enfermagem_ou_admin(user):
    return user.is_superuser or user.groups.filter(name__in=["admin","enfermagem"]).exists()

@user_passes_test(is_enfermagem_ou_admin)
def sinal_create(request):
    ...
def is_recepcao_ou_admin(user):
    return user.is_superuser or user.groups.filter(name__in=["admin","recepcao"]).exists()

@login_required
def paciente_sinais_chart(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    qs = (SinalVital.objects
          .filter(paciente=paciente)
          .order_by("-data_hora")[:30])
    dados = list(reversed([
        {
            "data": s.data_hora.strftime("%d/%m %H:%M"),
            "temp": float(s.temperatura) if s.temperatura is not None else None,
            "fc": int(s.frequencia_cardiaca) if s.frequencia_cardiaca is not None else None,
        } for s in qs
    ]))
    return JsonResponse(dados, safe=False)


@login_required
def paciente_detail(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)

    medicamentos = paciente.medicamentos.all().order_by("-id")

    sinais_qs = paciente.sinais.all().order_by("-data_hora")
    ocorr_qs  = paciente.ocorrencias.all().order_by("-data_hora")

    ini = request.GET.get("ini")
    fim = request.GET.get("fim")

    # filtro por data (YYYY-MM-DD)
    if ini and fim:
        # filtra pela data (não hora)
        sinais_qs = sinais_qs.filter(data_hora__date__range=(ini, fim))
        ocorr_qs  = ocorr_qs.filter(data_hora__date__range=(ini, fim))

    sinais = sinais_qs[:50]
    ocorrencias = ocorr_qs[:50]

    return render(request, "core/paciente_detail.html", {
        "paciente": paciente,
        "medicamentos": medicamentos,
        "sinais": sinais,
        "ocorrencias": ocorrencias,
        "ini": ini or "",
        "fim": fim or "",
    })


@login_required
def ocorrencias_list(request):
    paciente_id = request.GET.get("paciente", "")
    status = request.GET.get("status", "")
    inicio = request.GET.get("inicio", "")
    fim = request.GET.get("fim", "")

    if not inicio:
        inicio = (date.today() - timedelta(days=30)).isoformat()
    if not fim:
        fim = date.today().isoformat()

    qs = Ocorrencia.objects.select_related("paciente").order_by("-data_hora")
    qs = qs.filter(data_hora__date__gte=inicio, data_hora__date__lte=fim)

    if paciente_id:
        qs = qs.filter(paciente_id=paciente_id)

    if status == "pendente":
        qs = qs.filter(resolvido=False)
    elif status == "resolvida":
        qs = qs.filter(resolvido=True)

    total = qs.count()
    pendentes = qs.filter(resolvido=False).count()
    resolvidas = qs.filter(resolvido=True).count()

    return render(request, "core/ocorrencias_list.html", {
        "ocorrencias": qs[:500],
        "pacientes": Paciente.objects.order_by("nome"),
        "paciente_id": paciente_id,
        "status": status,
        "inicio": inicio,
        "fim": fim,
        "total": total,
        "pendentes": pendentes,
        "resolvidas": resolvidas,
    })
@login_required
def ocorrencia_create(request):
    pacientes = Paciente.objects.order_by("nome")

    if request.method == "POST":
        paciente_id = request.POST.get("paciente")
        tipo = (request.POST.get("tipo") or "").strip()
        gravidade = (request.POST.get("gravidade") or "Baixa").strip()
        descricao = (request.POST.get("descricao") or "").strip()

        if not paciente_id or not tipo or not descricao:
            return render(request, "core/ocorrencia_form.html", {
                "pacientes": pacientes,
                "erro": "Paciente, tipo e descrição são obrigatórios."
            })

        Ocorrencia.objects.create(
            paciente_id=paciente_id,
            data_hora=timezone.now(),
            tipo_ocorrencia=tipo,
            gravidade=gravidade,
            descricao=descricao,
            resolvido=False,
        )
        return redirect("ocorrencias_list")

    return render(request, "core/ocorrencia_form.html", {"pacientes": pacientes})

@login_required
def sinais_list(request):
    sinais = (
        SinalVital.objects
        .select_related("paciente")
        .order_by("-data_hora")
    )

    return render(request, "core/sinais_list.html", {
        "sinais": sinais,
    })

@login_required
def sinal_create(request):
    pacientes = Paciente.objects.order_by("nome")
    paciente_pre = request.GET.get("paciente")

    if request.method == "POST":
        paciente = Paciente.objects.get(id=request.POST.get("paciente_id"))

        SinalVital.objects.create(
            paciente=paciente,
            data_hora=now(),
            temperatura=parse_float_br(request.POST.get("temperatura")),
            saturacao_oxigenio=parse_float_br(request.POST.get("saturacao_oxigenio")),
            glicemia=parse_float_br(request.POST.get("glicemia")),
            pressao_arterial=request.POST.get("pressao_arterial") or None,
            frequencia_cardiaca=request.POST.get("frequencia_cardiaca") or None,
            frequencia_respiratoria=request.POST.get("frequencia_respiratoria") or None,
            dor_escala=request.POST.get("dor_escala") or None,
            observacoes=request.POST.get("observacoes") or None,
            usuario=request.user,
        )

        return redirect(request.GET.get("next") or "sinais_list")

    return render(request, "core/sinais_form.html", {
        "pacientes": pacientes,
        "paciente_pre": paciente_pre,
    })

  

@login_required
def medicamentos_list(request):
    paciente_id = request.GET.get("paciente", "")
    q = request.GET.get("q", "").strip()

    qs = Medicamento.objects.select_related("paciente").order_by("paciente__nome", "nome_medicamento")

    if paciente_id:
        qs = qs.filter(paciente_id=paciente_id)
    if q:
        qs = qs.filter(nome_medicamento__icontains=q)

    total = qs.count()
    pacientes_no_filtro = qs.values("paciente_id").distinct().count()

    return render(request, "core/medicamentos_list.html", {
        "medicamentos": qs[:500],
        "pacientes": Paciente.objects.order_by("nome"),
        "paciente_id": paciente_id,
        "q": q,
        "total": total,
        "pacientes_no_filtro": pacientes_no_filtro,
    })
@login_required
def medicamento_create(request):
    pacientes = Paciente.objects.order_by("nome")

    if request.method == "POST":
        paciente_id = request.POST.get("paciente")
        nome_medicamento = (request.POST.get("nome_medicamento") or "").strip()
        dosagem = (request.POST.get("dosagem") or "").strip()
        via = (request.POST.get("via") or "").strip()
        frequencia = (request.POST.get("frequencia") or "").strip()
        horarios = (request.POST.get("horarios") or "").strip()

        if not paciente_id or not nome_medicamento:
            return render(request, "core/medicamento_form.html", {
                "pacientes": pacientes,
                "erro": "Paciente e nome do medicamento são obrigatórios."
            })

        Medicamento.objects.create(
            paciente_id=paciente_id,
            nome_medicamento=nome_medicamento,
            dosagem=dosagem,
            via_administracao=via,
            frequencia=frequencia,
            horarios=horarios,
        )

        # (Opcional) auditoria
        try:
            Auditoria.objects.create(
                usuario=request.user.username,
                acao="ADD",
                modulo="Medicamentos",
                detalhes=f"Medicamento '{nome_medicamento}' cadastrado"
            )
        except:
            pass

        return redirect("medicamentos_list")

    return render(request, "core/medicamento_form.html", {"pacientes": pacientes})

def _parse_date_ymd(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

@login_required
def dashboard(request):
    # Período (padrão: últimos 30 dias)
    ini_dt = _parse_date_ymd(request.GET.get("ini")) or (date.today() - timedelta(days=30))
    fim_dt = _parse_date_ymd(request.GET.get("fim")) or date.today()

    # KPIs de pacientes
    total_pacientes = Paciente.objects.count()
    total_masculino = Paciente.objects.filter(sexo="Masculino").count()
    total_feminino = Paciente.objects.filter(sexo="Feminino").count()

    grau1 = Paciente.objects.filter(grau_dependencia=1).count()
    grau2 = Paciente.objects.filter(grau_dependencia=2).count()
    grau3 = Paciente.objects.filter(grau_dependencia=3).count()

    # Ocorrências no período
    ocorr_qs = Ocorrencia.objects.filter(
        data_hora__date__gte=ini_dt,
        data_hora__date__lte=fim_dt,
    )
    total_ocorr = ocorr_qs.count()
    ocorr_pend = ocorr_qs.filter(resolvido=False).count()
    ocorr_res = ocorr_qs.filter(resolvido=True).count()

    # Tipos de ocorrência (top 5)
    top_tipos = (
        ocorr_qs.values("tipo_ocorrencia")
        .annotate(qtd=Count("id"))
        .order_by("-qtd")[:5]
    )
    meds_ativos = Medicamento.objects.count()  # ou filtrar ativos se tiver campo
    # Casa 1
    casa1_total = Paciente.objects.filter(casa="Casa 1").count()
    casa1_homens = Paciente.objects.filter(casa="Casa 1", sexo="Masculino").count()
    casa1_mulheres = Paciente.objects.filter(casa="Casa 1", sexo="Feminino").count()

    # Casa 2
    casa2_total = Paciente.objects.filter(casa="Casa 2").count()
    casa2_homens = Paciente.objects.filter(casa="Casa 2", sexo="Masculino").count()
    casa2_mulheres = Paciente.objects.filter(casa="Casa 2", sexo="Feminino").count()
    ctx.update({
    "casa1_total": casa1_total,
    "casa1_homens": casa1_homens,
    "casa1_mulheres": casa1_mulheres,
    "casa2_total": casa2_total,
    "casa2_homens": casa2_homens,
    "casa2_mulheres": casa2_mulheres,
    })
    ctx = {
        
        "ini": ini_dt.strftime("%Y-%m-%d"),
        "fim": fim_dt.strftime("%Y-%m-%d"),

        "total_pacientes": total_pacientes,
        "total_masculino": total_masculino,
        "total_feminino": total_feminino,
        "meds_ativos" : meds_ativos,
        "grau1": grau1,
        "grau2": grau2,
        "grau3": grau3,

        "total_ocorr": total_ocorr,
        "ocorr_pend": ocorr_pend,
        "ocorr_res": ocorr_res,

        "top_tipos": top_tipos,
    }
    return render(request, "core/dashboard.html", ctx)
@login_required
def pacientes_list(request):
    q = request.GET.get("q", "").strip()
    pacientes = Paciente.objects.all().order_by("nome")
    if q:
        pacientes = pacientes.filter(nome__icontains=q) | pacientes.filter(cpf__icontains=q)

    return render(request, "core/pacientes_list.html", {"pacientes": pacientes, "q": q})

@login_required
def paciente_create(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        if not nome:
            return render(request, "core/paciente_form.html", {
                "erro": "Nome é obrigatório."
            })

        casa = request.POST.get("casa") or "Casa 1"

        possui_alergia = request.POST.get("possui_alergia") == "sim"
        alergias = request.POST.get("alergias") if possui_alergia else ""

        p = Paciente.objects.create(
            nome=nome,
            casa=casa,
            data_nascimento=request.POST.get("data_nascimento") or None,
            cpf=request.POST.get("cpf") or None,
            rg=request.POST.get("rg") or None,
            sexo=request.POST.get("sexo") or None,
            entrada_ilpi=request.POST.get("entrada_ilpi") or None,
            quarto=request.POST.get("quarto") or None,
            leito=request.POST.get("leito") or None,
            contato_emergencia=request.POST.get("contato_emergencia") or None,
            telefone_emergencia=request.POST.get("telefone_emergencia") or None,
            alergias=alergias,
            condicoes_cronicas=request.POST.get("condicoes_cronicas") or None,
            grau_dependencia=int(request.POST.get("grau_dependencia") or 1),
            observacoes=request.POST.get("observacoes") or None,
        )

        Auditoria.objects.create(
            usuario=request.user,
            acao="ADD",
            modulo="Pacientes",
            detalhes=f'Paciente "{p.nome}" criado'
        )

        return redirect("pacientes_list")

    return render(request, "core/paciente_form.html")

@login_required
def paciente_update(request, pk):
    paciente = Paciente.objects.get(pk=pk)

    if request.method == "POST":
        paciente.nome = request.POST.get("nome")
        paciente.casa = request.POST.get("casa") or paciente.casa or "Casa 1"
        paciente.data_nascimento = request.POST.get("data_nascimento") or None
        paciente.cpf = request.POST.get("cpf") or None
        paciente.rg = request.POST.get("rg") or None
        paciente.sexo = request.POST.get("sexo") or None
        paciente.entrada_ilpi = request.POST.get("entrada_ilpi") or None
        paciente.quarto = request.POST.get("quarto") or None
        paciente.leito = request.POST.get("leito") or None
        paciente.contato_emergencia = request.POST.get("contato_emergencia") or None
        paciente.telefone_emergencia = request.POST.get("telefone_emergencia") or None
        paciente.alergias = request.POST.get("alergias") or None
        paciente.condicoes_cronicas = request.POST.get("condicoes_cronicas") or None
        paciente.grau_dependencia = request.POST.get("grau_dependencia") or paciente.grau_dependencia or 1
        paciente.observacoes = request.POST.get("observacoes") or None

        paciente.save()
        return redirect("pacientes_list")

    return render(request, "core/paciente_form.html", {"paciente": paciente})

@login_required
def paciente_delete(request, pk):
    p = get_object_or_404(Paciente, pk=pk)

    if request.method == "POST":
        nome = p.nome
        p.delete()

        Auditoria.objects.create(
            usuario=request.user,
            acao="DELETE",
            modulo="Pacientes",
            detalhes=f'Paciente "{nome}" excluído'
        )
        return redirect("pacientes_list")

    return render(request, "core/paciente_delete.html", {"p": p})
@login_required
def medicamentos_pdf(request):
    paciente_id = request.GET.get("paciente", "")
    q = request.GET.get("q", "").strip()

    qs = Medicamento.objects.select_related("paciente").order_by("paciente__nome", "nome_medicamento")
    if paciente_id:
        qs = qs.filter(paciente_id=paciente_id)
    if q:
        qs = qs.filter(nome_medicamento__icontains=q)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="medicamentos.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    w, h = A4
    y = h - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Relatório de Medicamentos")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Filtros: paciente={paciente_id or 'Todos'} | busca={q or '—'}")
    y -= 25

    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Paciente")
    c.drawString(200, y, "Medicamento")
    c.drawString(360, y, "Dosagem")
    y -= 12
    c.setFont("Helvetica", 9)

    for m in qs[:1000]:
        if y < 60:
            c.showPage()
            y = h - 40
            c.setFont("Helvetica", 9)
        c.drawString(40, y, (m.paciente.nome or "")[:26])
        c.drawString(200, y, (m.nome_medicamento or "")[:24])
        c.drawString(360, y, (m.dosagem or "")[:18])
        y -= 12

    c.save()
    return response


@login_required
def sinais_pdf(request):
    paciente_id = request.GET.get("paciente", "")
    inicio = request.GET.get("inicio", "")
    fim = request.GET.get("fim", "")
    if not inicio:
        inicio = (date.today() - timedelta(days=7)).isoformat()
    if not fim:
        fim = date.today().isoformat()

    qs = SinalVital.objects.select_related("paciente").order_by("-data_hora")
    qs = qs.filter(data_hora__date__gte=inicio, data_hora__date__lte=fim)
    if paciente_id:
        qs = qs.filter(paciente_id=paciente_id)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="sinais_vitais.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    w, h = A4
    y = h - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Relatório de Sinais Vitais")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Período: {inicio} a {fim} | paciente={paciente_id or 'Todos'}")
    y -= 25

    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Paciente")
    c.drawString(200, y, "Data/Hora")
    c.drawString(320, y, "Temp")
    c.drawString(360, y, "PA")
    c.drawString(440, y, "FC")
    y -= 12
    c.setFont("Helvetica", 9)

    for s in qs[:1000]:
        if y < 60:
            c.showPage()
            y = h - 40
            c.setFont("Helvetica", 9)
        c.drawString(40, y, (s.paciente.nome or "")[:26])
        c.drawString(200, y, str(s.data_hora)[:16])
        c.drawString(320, y, str(s.temperatura or ""))
        c.drawString(360, y, (s.pressao_arterial or "")[:10])
        c.drawString(440, y, str(s.frequencia_cardiaca or ""))
        y -= 12

    c.save()
    return response

@login_required
def chart_ocorrencias_por_dia(request):
    ini = request.GET.get("ini")
    fim = request.GET.get("fim")

    fim_date = date.fromisoformat(fim) if fim else date.today()
    ini_date = date.fromisoformat(ini) if ini else (fim_date - timedelta(days=30))

    qs = (
        Ocorrencia.objects.filter(
            data_hora__date__gte=ini_date,
            data_hora__date__lte=fim_date,
        )
        .annotate(d=TruncDate("data_hora"))
        .values("d")
        .annotate(total=Count("id"))
        .order_by("d")
    )

    data = [{"data": x["d"].isoformat(), "total": x["total"]} for x in qs]
    return JsonResponse(data, safe=False)
@login_required
def chart_sinais_media_por_dia(request):
    ini = request.GET.get("ini")
    fim = request.GET.get("fim")

    fim_date = date.fromisoformat(fim) if fim else date.today()
    ini_date = date.fromisoformat(ini) if ini else (fim_date - timedelta(days=30))

    qs = (
        SinalVital.objects.filter(
            data_hora__date__gte=ini_date,
            data_hora__date__lte=fim_date,
        )
        .annotate(d=TruncDate("data_hora"))
        .values("d")
        .annotate(
            temp=Avg("temperatura"),
            fc=Avg("frequencia_cardiaca"),
        )
        .order_by("d")
    )

    data = []
    for x in qs:
        data.append({
            "data": x["d"].isoformat(),
            "temp": float(x["temp"]) if x["temp"] is not None else None,
            "fc": float(x["fc"]) if x["fc"] is not None else None,
        })

    return JsonResponse(data, safe=False)

@login_required
def ocorrencias_pdf(request):
    paciente_id = request.GET.get("paciente", "")
    status = request.GET.get("status", "")
    inicio = request.GET.get("inicio", "")
    fim = request.GET.get("fim", "")
    if not inicio:
        inicio = (date.today() - timedelta(days=30)).isoformat()
    if not fim:
        fim = date.today().isoformat()

    qs = Ocorrencia.objects.select_related("paciente").order_by("-data_hora")
    qs = qs.filter(data_hora__date__gte=inicio, data_hora__date__lte=fim)
    if paciente_id:
        qs = qs.filter(paciente_id=paciente_id)
    if status == "pendente":
        qs = qs.filter(resolvido=False)
    elif status == "resolvida":
        qs = qs.filter(resolvido=True)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="ocorrencias.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    w, h = A4
    y = h - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Relatório de Ocorrências")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Período: {inicio} a {fim} | status={status or 'Todas'} | paciente={paciente_id or 'Todos'}")
    y -= 25

    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Paciente")
    c.drawString(200, y, "Data/Hora")
    c.drawString(320, y, "Tipo")
    c.drawString(430, y, "Grav.")
    y -= 12
    c.setFont("Helvetica", 9)

    for o in qs[:1000]:
        if y < 60:
            c.showPage()
            y = h - 40
            c.setFont("Helvetica", 9)
        c.drawString(40, y, (o.paciente.nome or "")[:26])
        c.drawString(200, y, str(o.data_hora)[:16])
        c.drawString(320, y, (o.tipo_ocorrencia or "")[:16])
        c.drawString(430, y, (o.gravidade or "")[:10])
        y -= 12

    c.save()
    return response

PRIMARY = HexColor("#1f3a5f")
TEXT = HexColor("#111827")
MUTED = HexColor("#6b7280")


def header(c, titulo):
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, 28.5 * cm, titulo)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, 28.0 * cm, f"Gerado em: {now().strftime('%d/%m/%Y %H:%M')}")


def draw_bar_chart(c, title, labels, values, x, y, width=17 * cm, height=6 * cm):
    d = Drawing(width, height)
    d.add(String(10, height - 15, title, fontName="Helvetica-Bold", fontSize=10))

    bc = VerticalBarChart()
    bc.x = 40
    bc.y = 25
    bc.width = width - 60
    bc.height = height - 55
    bc.data = [values or [0]]
    bc.categoryAxis.categoryNames = labels or ["—"]

    d.add(bc)
    renderPDF.draw(d, c, x, y)


def draw_line_chart(c, title, labels, values, x, y, width=17 * cm, height=6 * cm):
    d = Drawing(width, height)
    d.add(String(10, height - 15, title, fontName="Helvetica-Bold", fontSize=10))

    labels = labels or []
    values = values or []

    pts = [(i, (v if v is not None else 0)) for i, v in enumerate(values)]
    if len(pts) < 2:
        d.add(String(10, height / 2, "Sem dados suficientes no período.", fontName="Helvetica", fontSize=9))
        renderPDF.draw(d, c, x, y)
        return

    lp = LinePlot()
    lp.x = 40
    lp.y = 25
    lp.width = width - 60
    lp.height = height - 55
    lp.data = [pts]

    lp.lines[0].strokeWidth = 2
    lp.lines[0].symbol = makeMarker("Circle")
    lp.lines[0].symbol.size = 3

    d.add(lp)

    ini_txt = labels[0] if labels else "—"
    fim_txt = labels[-1] if labels else "—"
    d.add(String(10, 10, f"Início: {ini_txt} | Fim: {fim_txt}", fontName="Helvetica", fontSize=8))

    renderPDF.draw(d, c, x, y)


@login_required
def dashboard(request):
    
    # ===============================
    # 1) Datas (sempre definidas)
    # ===============================
    ini = request.GET.get("ini")
    fim = request.GET.get("fim")

    try:
        ini_dt = datetime.strptime(ini, "%Y-%m-%d").date() if ini else date.today().replace(day=1)
    except:
        ini_dt = date.today().replace(day=1)

    try:
        fim_dt = datetime.strptime(fim, "%Y-%m-%d").date() if fim else date.today()
    except:
        fim_dt = date.today()

    # ===============================
    # 2) CONTEXTO BASE (SEMPRE EXISTE)
    # ===============================
    ctx = {
        "ini": ini_dt.strftime("%Y-%m-%d"),
        "fim": fim_dt.strftime("%Y-%m-%d"),
    }

    # ===============================
    # 3) KPIs GERAIS
    # ===============================
    pacientes = Paciente.objects.all()

    ctx.update({
        "total_pacientes": pacientes.count(),
        "total_masculino": pacientes.filter(sexo="M").count(),
        "total_feminino": pacientes.filter(sexo="F").count(),

        "grau1": pacientes.filter(grau_dependencia=1).count(),
        "grau2": pacientes.filter(grau_dependencia=2).count(),
        "grau3": pacientes.filter(grau_dependencia=3).count(),
    })

    # ===============================
    # 4) MEDICAMENTOS ATIVOS
    # ===============================
    ctx["meds_ativos"] = MedicamentoPaciente.objects.filter(
        ativo=True
    ).count() if "MedicamentoPaciente" in globals() else 0

    # ===============================
    # 5) OCORRÊNCIAS
    # ===============================
    ocorrencias = Ocorrencia.objects.filter(
        data_hora__date__gte=ini_dt,
        data_hora__date__lte=fim_dt
    )

    ctx["ocorr_pend"] = ocorrencias.filter(resolvido=False).count()

    return render(request, "core/dashboard.html", ctx)
@login_required
def estoque_dashboard(request):
    meds = EstoqueMedicamento.objects.select_related("paciente").order_by(
        "paciente__nome", "nome_medicamento"
    )
    fraldas = EstoqueFralda.objects.select_related("paciente").order_by(
        "paciente__nome", "tipo"
    )

    # alertas simples
    meds_alerta = meds.filter(quantidade_atual__lte=F("alerta_minimo"))
    fraldas_alerta = fraldas.filter(quantidade_atual__lte=F("alerta_minimo"))

    return render(request, "core/estoque_dashboard.html", {
        "meds": meds,
        "fraldas": fraldas,
        "meds_alerta": meds_alerta,
        "fraldas_alerta": fraldas_alerta,
    })


@login_required
def estoque_med_create(request):
    pacientes = Paciente.objects.order_by("nome")

    if request.method == "POST":
        paciente_id = request.POST.get("paciente_id")
        nome = (request.POST.get("nome_medicamento") or "").strip()
        unidade = (request.POST.get("unidade") or "un").strip()
        qtd = int(request.POST.get("quantidade") or 0)
        alerta = int(request.POST.get("alerta_minimo") or 5)

        paciente = Paciente.objects.get(id=paciente_id)

        estoque, _ = EstoqueMedicamento.objects.get_or_create(
            paciente=paciente,
            nome_medicamento=nome,
            defaults={"unidade": unidade, "alerta_minimo": alerta, "quantidade_atual": 0},
        )

        # atualiza dados
        estoque.unidade = unidade
        estoque.alerta_minimo = alerta
        estoque.quantidade_atual = (estoque.quantidade_atual or 0) + qtd
        estoque.save()

        MovEstoqueMedicamento.objects.create(
            estoque=estoque,
            tipo="ENTRADA",
            quantidade=qtd,
            data_hora=timezone.now(),
            observacao="Entrada manual",
        )

        return redirect("estoque_dashboard")

    return render(request, "core/estoque_med_form.html", {"pacientes": pacientes})


@login_required
def estoque_fralda_create(request):
    pacientes = Paciente.objects.order_by("nome")

    if request.method == "POST":
        paciente_id = request.POST.get("paciente_id")
        tipo = (request.POST.get("tipo") or "G").strip()
        qtd = int(request.POST.get("quantidade") or 0)
        consumo_dia = int(request.POST.get("consumo_dia") or 6)
        alerta = int(request.POST.get("alerta_minimo") or 20)

        paciente = Paciente.objects.get(id=paciente_id)

        estoque, _ = EstoqueFralda.objects.get_or_create(
            paciente=paciente,
            tipo=tipo,
            defaults={"consumo_dia": consumo_dia, "alerta_minimo": alerta, "quantidade_atual": 0},
        )

        estoque.consumo_dia = consumo_dia
        estoque.alerta_minimo = alerta
        estoque.quantidade_atual = (estoque.quantidade_atual or 0) + qtd
        estoque.save()

        MovEstoqueFralda.objects.create(
            estoque=estoque,
            tipo="ENTRADA",
            quantidade=qtd,
            data_hora=timezone.now(),
            observacao="Entrada manual",
        )

        return redirect("estoque_dashboard")

    return render(request, "core/estoque_fralda_form.html", {"pacientes": pacientes})
@login_required
def dashboard_pdf(request):
    ini = request.GET.get("ini")
    fim = request.GET.get("fim")

    try:
        ini_dt = datetime.strptime(ini, "%Y-%m-%d").date() if ini else date.today().replace(day=1)
    except:
        ini_dt = date.today().replace(day=1)

    try:
        fim_dt = datetime.strptime(fim, "%Y-%m-%d").date() if fim else date.today()
    except:
        fim_dt = date.today()

    pacientes = Paciente.objects.all()

    total_pacientes = pacientes.count()
    total_masculino = pacientes.filter(sexo="M").count()
    total_feminino = pacientes.filter(sexo="F").count()

    grau1 = pacientes.filter(grau_dependencia=1).count()
    grau2 = pacientes.filter(grau_dependencia=2).count()
    grau3 = pacientes.filter(grau_dependencia=3).count()

    ocorr_qs = Ocorrencia.objects.filter(
        data_hora__date__gte=ini_dt,
        data_hora__date__lte=fim_dt
    )
    ocorr_pend = ocorr_qs.filter(resolvido=False).count()
    ocorr_total = ocorr_qs.count()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="dashboard.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    w, h = A4

    # Cabeçalho
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, h - 2.2 * cm, "Dashboard Gerencial – Relatório")

    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, h - 2.9 * cm, f"Período: {ini_dt.strftime('%d/%m/%Y')} até {fim_dt.strftime('%d/%m/%Y')}")

    # Bloco KPIs
    y = h - 4.2 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Indicadores")
    y -= 0.8 * cm

    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, y, f"Total de pacientes: {total_pacientes}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Homens: {total_masculino} | Mulheres: {total_feminino}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Grau 1: {grau1} | Grau 2: {grau2} | Grau 3: {grau3}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Ocorrências no período: {ocorr_total} (Pendentes: {ocorr_pend})")

    c.showPage()
    c.save()
    return response