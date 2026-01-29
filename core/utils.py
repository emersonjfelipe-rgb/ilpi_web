from datetime import date

def calc_idade(data_nascimento: date | None) -> int | None:
    """Retorna idade em anos ou None."""
    if not data_nascimento:
        return None
    hoje = date.today()
    anos = hoje.year - data_nascimento.year
    # Ajusta se ainda não fez aniversário no ano
    if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
        anos -= 1
    return anos

def calc_tempo_ilpi(data_entrada: date | None) -> dict:
    """
    Retorna dict com:
      - dias (int|None)
      - texto (str)
    """
    if not data_entrada:
        return {"dias": None, "texto": "—"}

    hoje = date.today()
    dias = (hoje - data_entrada).days
    if dias < 0:
        return {"dias": dias, "texto": "Data de entrada no futuro (verifique)"}

    meses = dias // 30
    resto = dias % 30

    if meses == 0:
        texto = f"{dias} dia(s)"
    else:
        texto = f"{meses} mês(es) e {resto} dia(s)"

    return {"dias": dias, "texto": texto}
def paciente_flags(paciente) -> list[dict]:
    """
    Retorna uma lista de flags no formato:
      [{"label": "...", "cls": "bg-danger"}, ...]
    cls são classes Bootstrap de cor: bg-danger, bg-warning, bg-success, bg-primary, bg-secondary, bg-info, bg-dark
    """
    flags = []

    # Idade
    idade = calc_idade(getattr(paciente, "data_nascimento", None))
    if idade is None:
        flags.append({"label": "Sem data de nascimento", "cls": "bg-secondary"})
    elif idade >= 80:
        flags.append({"label": "80+", "cls": "bg-warning text-dark"})
    elif idade >= 60:
        flags.append({"label": "60+", "cls": "bg-info text-dark"})

    # Grau (alto risco)
    grau = getattr(paciente, "grau_dependencia", None)
    if grau == 3:
        flags.append({"label": "Alto risco (G3)", "cls": "bg-danger"})
    elif grau == 2:
        flags.append({"label": "G2", "cls": "bg-primary"})
    elif grau == 1:
        flags.append({"label": "G1", "cls": "bg-success"})

    # Entrada recente
    entrada = getattr(paciente, "data_entrada", None)
    tempo = calc_tempo_ilpi(entrada)
    if tempo["dias"] is None:
        flags.append({"label": "Sem data de entrada", "cls": "bg-secondary"})
    else:
        if 0 <= tempo["dias"] <= 30:
            flags.append({"label": "Entrada recente (≤30d)", "cls": "bg-success"})
    # Se nada crítico faltando, marca OK
    criticos_faltando = any(f["label"].startswith("Sem data") for f in flags)
    if not criticos_faltando:
        flags.append({"label": "Cadastro OK", "cls": "bg-dark"})
    # Se nada crítico faltando, marca OK
    criticos_faltando = any(f["label"].startswith("Sem data") for f in flags)
    if not criticos_faltando:
        flags.append({"label": "Cadastro OK", "cls": "bg-dark"})

    return flags

