from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# =========================
# PACIENTE / PRONTUÁRIO
# =========================

class Prescricao(models.Model):
    paciente = models.ForeignKey("Paciente", on_delete=models.CASCADE)
    nome_medicamento = models.CharField(max_length=120)
    dosagem = models.CharField(max_length=60, blank=True, null=True)
    via = models.CharField(max_length=40, blank=True, null=True)
    frequencia = models.CharField(max_length=40, blank=True, null=True)  # "8/8", "12/12" etc
    horarios = models.CharField(max_length=120, blank=True, null=True)   # "06:00,14:00,22:00"
    ativa = models.BooleanField(default=True)

    data_inicio = models.DateField(blank=True, null=True)
    data_termino = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.paciente} - {self.nome_medicamento}"


class AdministracaoDose(models.Model):
    prescricao = models.ForeignKey(Prescricao, on_delete=models.CASCADE)
    data = models.DateField()
    horario = models.TimeField()

    administrado = models.BooleanField(default=False)
    administrado_em = models.DateTimeField(blank=True, null=True)
    administrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    observacao = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("prescricao", "data", "horario")


class Paciente(models.Model):
    SEXO_CHOICES = [("Masculino","Masculino"), ("Feminino","Feminino")]
    CASA_CHOICES = [("Casa 1", "Casa 1"), ("Casa 2", "Casa 2")]

    casa = models.CharField(max_length=20, choices=CASA_CHOICES, default="Casa 1")
    nome = models.CharField(max_length=200)
    data_nascimento = models.DateField(null=True, blank=True)
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    rg = models.CharField(max_length=30, null=True, blank=True)
    sexo = models.CharField(max_length=15, choices=SEXO_CHOICES, null=True, blank=True)
    entrada_ilpi = models.DateField(null=True, blank=True)
    quarto = models.CharField(max_length=20, null=True, blank=True)
    leito = models.CharField(max_length=20, null=True, blank=True)
    contato_emergencia = models.CharField(max_length=200, null=True, blank=True)
    telefone_emergencia = models.CharField(max_length=30, null=True, blank=True)
    alergias = models.TextField(null=True, blank=True)
    condicoes_cronicas = models.TextField(null=True, blank=True)
    grau_dependencia = models.IntegerField(default=1)
    observacoes = models.TextField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class Medicamento(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="medicamentos")
    nome_medicamento = models.CharField(max_length=200)
    dosagem = models.CharField(max_length=100, null=True, blank=True)
    via_administracao = models.CharField(max_length=60, null=True, blank=True)
    frequencia = models.CharField(max_length=60, null=True, blank=True)
    horarios = models.CharField(max_length=200, null=True, blank=True)
    data_inicio = models.DateField(null=True, blank=True)
    data_termino = models.DateField(null=True, blank=True)
    prescrito_por = models.CharField(max_length=200, null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.paciente.nome} - {self.nome_medicamento}"


class SinalVital(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="sinais")
    data_hora = models.DateTimeField()
    temperatura = models.FloatField(null=True, blank=True)
    pressao_arterial = models.CharField(max_length=20, null=True, blank=True)
    frequencia_cardiaca = models.IntegerField(null=True, blank=True)
    frequencia_respiratoria = models.IntegerField(null=True, blank=True)
    saturacao_oxigenio = models.FloatField(null=True, blank=True)
    glicemia = models.FloatField(null=True, blank=True)
    dor_escala = models.IntegerField(null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.paciente.nome} - {self.data_hora}"


class Ocorrencia(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="ocorrencias")
    data_hora = models.DateTimeField()
    tipo_ocorrencia = models.CharField(max_length=80)
    descricao = models.TextField()
    conduta = models.TextField(null=True, blank=True)
    gravidade = models.CharField(max_length=20, null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolvido = models.BooleanField(default=False)
    data_resolucao = models.DateTimeField(null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.paciente.nome} - {self.tipo_ocorrencia}"


class Auditoria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=30)
    modulo = models.CharField(max_length=60)
    data_hora = models.DateTimeField(auto_now_add=True)
    detalhes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.data_hora} - {self.acao} - {self.modulo}"


# =========================
# ESTOQUE (NOVO)
# =========================

class Produto(models.Model):
    TIPO_CHOICES = [
        ("MED", "Medicamento"),
        ("FRA", "Fralda"),
    ]

    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES)
    unidade = models.CharField(max_length=30, default="un")  # "comprimido", "ml", "un", "pacote", etc
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nome}"


class EstoquePacienteItem(models.Model):
    """
    Estoque POR PACIENTE.
    - Medicamento: baixa automática quando administra dose (1 unidade por administração)
    - Fralda: baixa automática diária pelo consumo_diario (ex: 6/dia)
    """
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="estoques")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)

    quantidade_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimo_alerta = models.DecimalField(max_digits=10, decimal_places=2, default=10)

    # Para FRALDAS: consumo diário automático (ex: 6)
    consumo_diario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    observacoes = models.TextField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("paciente", "produto")

    def __str__(self):
        return f"{self.paciente.nome} - {self.produto.nome} ({self.quantidade_atual})"

    @property
    def baixo(self):
        try:
            return self.quantidade_atual <= self.minimo_alerta
        except:
            return False


class MovimentoEstoque(models.Model):
    MOTIVO_CHOICES = [
        ("ENTRADA", "Entrada"),
        ("DOSE", "Administração de Dose"),
        ("FRALDA", "Consumo Diário de Fraldas"),
        ("AJUSTE", "Ajuste Manual"),
    ]

    item = models.ForeignKey(EstoquePacienteItem, on_delete=models.CASCADE, related_name="movimentos")
    data_hora = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=10, choices=MOTIVO_CHOICES)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)  # entrada positiva, saída negativa
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    observacao = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.item} | {self.motivo} | {self.quantidade}"
class EstoqueMedicamento(models.Model):
    paciente = models.ForeignKey("Paciente", on_delete=models.CASCADE, related_name="estoque_medicamentos")
    nome_medicamento = models.CharField(max_length=200)
    quantidade_atual = models.IntegerField(default=0)  # em comprimidos/ml/etc
    unidade = models.CharField(max_length=30, default="un")  # un, ml, cp, etc
    alerta_minimo = models.IntegerField(default=5)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.paciente.nome} - {self.nome_medicamento} ({self.quantidade_atual} {self.unidade})"


class MovEstoqueMedicamento(models.Model):
    TIPO = [("ENTRADA", "Entrada"), ("SAIDA", "Saída")]

    estoque = models.ForeignKey(EstoqueMedicamento, on_delete=models.CASCADE, related_name="movs")
    tipo = models.CharField(max_length=10, choices=TIPO)
    quantidade = models.IntegerField()
    data_hora = models.DateTimeField(default=timezone.now)
    observacao = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.estoque} {self.tipo} {self.quantidade}"


class EstoqueFralda(models.Model):
    paciente = models.ForeignKey("Paciente", on_delete=models.CASCADE, related_name="estoque_fraldas")
    tipo = models.CharField(max_length=60, default="G")  # P/M/G/EG, etc
    quantidade_atual = models.IntegerField(default=0)
    consumo_dia = models.IntegerField(default=6)  # ex: 6 fraldas/dia
    alerta_minimo = models.IntegerField(default=20)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.paciente.nome} - Fralda {self.tipo} ({self.quantidade_atual})"


class MovEstoqueFralda(models.Model):
    TIPO = [("ENTRADA", "Entrada"), ("SAIDA", "Saída")]

    estoque = models.ForeignKey(EstoqueFralda, on_delete=models.CASCADE, related_name="movs")
    tipo = models.CharField(max_length=10, choices=TIPO)
    quantidade = models.IntegerField()
    data_hora = models.DateTimeField(default=timezone.now)
    observacao = models.CharField(max_length=200, blank=True, null=True)