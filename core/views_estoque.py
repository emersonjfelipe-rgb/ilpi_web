from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now

from .models import (
    Paciente, Produto, EstoquePacienteItem, MovimentoEstoque
)


def parse_decimal_br(value: str):
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    value = value.replace(".", "").replace(",", ".")  # 1.234,56 -> 1234.56
    try:
        return Decimal(value)
    except:
        return None


@login_required
def estoque_list(request):
    tipo = request.GET.get("tipo", "ALL")  # ALL / MED / FRA
    q = request.GET.get("q", "").strip()

    items = EstoquePacienteItem.objects.select_related("paciente", "produto").order_by("paciente__nome", "produto__nome")

    if tipo in ("MED", "FRA"):
        items = items.filter(produto__tipo=tipo)

    if q:
        items = items.filter(paciente__nome__icontains=q) | items.filter(produto__nome__icontains=q)

    baixos = items.filter(quantidade_atual__lte=models.F("minimo_alerta")) if False else None  # placeholder

    # baixo (sem usar F para não depender de import)
    low_items = [i for i in items if i.baixo]

    return render(request, "core/estoque_list.html", {
        "items": items,
        "low_items": low_items,
        "tipo": tipo,
        "q": q,
    })


@login_required
def estoque_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    items = EstoquePacienteItem.objects.filter(paciente=paciente).select_related("produto").order_by("produto__tipo", "produto__nome")
    low_items = [i for i in items if i.baixo]

    return render(request, "core/estoque_paciente.html", {
        "paciente": paciente,
        "items": items,
        "low_items": low_items,
    })


@login_required
def estoque_item_create(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    produtos = Produto.objects.filter(ativo=True).order_by("tipo", "nome")

    if request.method == "POST":
        produto_id = request.POST.get("produto_id")
        qtd = parse_decimal_br(request.POST.get("quantidade_atual")) or Decimal("0")
        minimo = parse_decimal_br(request.POST.get("minimo_alerta")) or Decimal("10")
        consumo = parse_decimal_br(request.POST.get("consumo_diario"))

        produto = get_object_or_404(Produto, pk=produto_id)

        item, created = EstoquePacienteItem.objects.get_or_create(
            paciente=paciente,
            produto=produto,
            defaults={
                "quantidade_atual": qtd,
                "minimo_alerta": minimo,
                "consumo_diario": consumo if produto.tipo == "FRA" else None
            }
        )

        if not created:
            item.quantidade_atual = qtd
            item.minimo_alerta = minimo
            if produto.tipo == "FRA":
                item.consumo_diario = consumo
            item.save()

        MovimentoEstoque.objects.create(
            item=item,
            motivo="AJUSTE",
            quantidade=Decimal("0"),
            usuario=request.user,
            observacao="Criação/atualização do item de estoque"
        )

        return redirect("estoque_paciente", pk=paciente.id)

    return render(request, "core/estoque_item_form.html", {
        "paciente": paciente,
        "produtos": produtos
    })


@login_required
def estoque_entrada(request, item_id):
    item = get_object_or_404(EstoquePacienteItem, pk=item_id)

    if request.method == "POST":
        qtd = parse_decimal_br(request.POST.get("quantidade"))
        obs = request.POST.get("observacao") or None
        if not qtd:
            return redirect("estoque_paciente", pk=item.paciente.id)

        item.quantidade_atual = (item.quantidade_atual or Decimal("0")) + qtd
        item.save(update_fields=["quantidade_atual", "atualizado_em"])

        MovimentoEstoque.objects.create(
            item=item,
            motivo="ENTRADA",
            quantidade=qtd,
            usuario=request.user,
            observacao=obs or "Entrada de estoque"
        )

        return redirect("estoque_paciente", pk=item.paciente.id)

    return render(request, "core/estoque_entrada_form.html", {"item": item})


@login_required
def processar_consumo_fraldas(request):
    """
    Baixa automática de fraldas (consumo diário) para TODOS os pacientes.
    Você pode rodar isso 1x por dia (botão) ou depois automatizar em tarefa/cron.
    """
    if request.method != "POST":
        return redirect("estoque_list")

    items = EstoquePacienteItem.objects.select_related("produto").filter(produto__tipo="FRA")
    for item in items:
        if item.consumo_diario is None:
            continue
        if item.consumo_diario <= 0:
            continue

        item.quantidade_atual = (item.quantidade_atual or Decimal("0")) - item.consumo_diario
        item.save(update_fields=["quantidade_atual", "atualizado_em"])

        MovimentoEstoque.objects.create(
            item=item,
            motivo="FRALDA",
            quantidade=(item.consumo_diario * Decimal("-1")),
            usuario=request.user,
            observacao=f"Baixa automática diária de fraldas em {now().strftime('%d/%m/%Y')}"
        )

    return redirect("estoque_list")
