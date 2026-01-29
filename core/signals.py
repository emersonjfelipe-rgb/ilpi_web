import re
from decimal import Decimal, InvalidOperation
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import AdministracaoDose, EstoquePacienteItem, Produto, MovimentoEstoque


def parse_decimal_br(txt: str):
    if txt is None:
        return None
    s = str(txt).strip()
    if not s:
        return None
    # aceita "36,6" ou "36.6"
    s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and s.count(".") >= 1 else s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def inferir_qtd_da_dosagem(dosagem: str, unidade_produto: str):
    """
    Tenta extrair a quantidade da string dosagem.
    Exemplos aceitos:
      - "1 cp", "2 comprimidos", "0,5 cp"
      - "10 ml", "5mL", "15 ML"
      - "20 gotas"
    Se falhar -> retorna 1
    """
    if not dosagem:
        return Decimal("1")

    d = dosagem.lower().strip()

    # captura primeiro número (inteiro ou decimal com vírgula/ponto)
    m = re.search(r"(\d+(?:[.,]\d+)?)", d)
    if not m:
        return Decimal("1")

    qtd = parse_decimal_br(m.group(1)) or Decimal("1")

    # Heurística por unidade:
    # Se o produto é "ml" e dosagem veio tipo "1 cp" (incompatível), ainda assim baixa qtd.
    # (Depois podemos refinar para validar unidade)
    # Se dosagem for tipo "1/2" (meio comprimido), você pode escrever "0,5 cp" que funciona.

    # evita negativo / zero
    if qtd <= 0:
        return Decimal("1")

    return qtd


@receiver(pre_save, sender=AdministracaoDose)
def dose_pre_save(sender, instance, **kwargs):
    if instance.pk:
        old = AdministracaoDose.objects.filter(pk=instance.pk).first()
        instance._old_administrado = bool(old.administrado) if old else False
    else:
        instance._old_administrado = False


@receiver(post_save, sender=AdministracaoDose)
def dose_post_save(sender, instance, created, **kwargs):
    # Só baixa quando muda False -> True
    old = getattr(instance, "_old_administrado", False)
    if old is True:
        return
    if not instance.administrado:
        return

    presc = instance.prescricao
    paciente = presc.paciente
    nome_med = (presc.nome_medicamento or "").strip()
    if not nome_med:
        return

    # Produto MED pelo nome (case-insensitive)
    prod = Produto.objects.filter(tipo="MED", nome__iexact=nome_med, ativo=True).first()
    if not prod:
        return

    item = EstoquePacienteItem.objects.filter(paciente=paciente, produto=prod).first()
    if not item:
        return

    # QUANTIDADE POR POSOLOGIA:
    # usa presc.dosagem (ex: "2 cp", "10 ml")
    qtd = inferir_qtd_da_dosagem(presc.dosagem or "", prod.unidade or "")

    item.quantidade_atual = (item.quantidade_atual or Decimal("0")) - qtd
    item.save(update_fields=["quantidade_atual", "atualizado_em"])

    MovimentoEstoque.objects.create(
        item=item,
        motivo="DOSE",
        quantidade=(qtd * Decimal("-1")),
        usuario=instance.administrado_por,
        observacao=f"Baixa automática por posologia: {qtd} {prod.unidade} | dose {instance.data} {instance.horario}"
    )
