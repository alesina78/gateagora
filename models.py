# -*- coding: utf-8 -*-
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, RegexValidator

# --- 1. ESTRUTURA MULTI-EMPRESA ---

class Empresa(models.Model):
    nome = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    cnpj = models.CharField(max_length=18, blank=True, null=True, help_text="CNPJ da Unidade")
    cidade = models.CharField(max_length=100, default="Cidade Exemplo")
    slug = models.SlugField(
        unique=True,
        help_text="Identificador único na URL (ex: haras-santa-fe)"
    )

    class Meta:
        indexes = [models.Index(fields=["slug"])]

    def __str__(self):
        return self.nome


class Perfil(models.Model):
    class Cargo(models.TextChoices):
        GESTOR = 'Gestor', 'Gestor/Dono'
        VETERINARIO = 'Veterinario', 'Veterinário'
        TRATADOR = 'Tratador', 'Tratador'
        PROFESSOR = 'Professor', 'Professor'

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='funcionarios'
    )
    cargo = models.CharField(
        max_length=50,
        choices=Cargo.choices,
        default=Cargo.TRATADOR
    )

    def __str__(self):
        return f"{self.user.username} - {self.empresa.nome}"


@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    """
    Em SaaS multi-empresa, evite vincular usuários comuns à 'primeira empresa'.
    Para conveniência, apenas superusers recém-criados recebem Perfil 'Gestor'
    na primeira Empresa (se existir).
    """
    if created and instance.is_superuser and Empresa.objects.exists():
        Perfil.objects.get_or_create(
            user=instance,
            defaults={"empresa": Empresa.objects.first(), "cargo": Perfil.Cargo.GESTOR}
        )


# --- 2. GESTÃO OPERACIONAL ---

class Aluno(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=200)
    telefone = models.CharField(
        max_length=20,
        help_text="Formato sugerido: 5511999999999",
        default="",
        validators=[RegexValidator(r'^\+?\d{10,15}$', 'Telefone deve estar no formato internacional, ex: 5511999999999')]
    )
    foto = models.ImageField(upload_to='alunos/', null=True, blank=True)
    ativo = models.BooleanField(default=True)
    valor_aula = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('150.00'))

    class Meta:
        ordering = ['nome']
        indexes = [models.Index(fields=["empresa", "nome"])]

    def __str__(self):
        return f"{self.nome} ({self.empresa.nome})"


class Baia(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    numero = models.CharField(max_length=10)
    status = models.CharField(
        max_length=20,
        choices=[('Livre', 'Livre'), ('Ocupada', 'Ocupada')],
        default='Livre'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'numero'], name='uq_baia_empresa_numero')
        ]
        indexes = [models.Index(fields=["empresa", "status"])]

    def __str__(self):
        return f"Baia {self.numero} - {self.empresa.nome}"


class Piquete(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=50)
    capacidade = models.IntegerField(default=3)
    status = models.CharField(
        max_length=20,
        choices=[('Livre', 'Livre'), ('Ocupado', 'Ocupado')],
        default='Livre'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'nome'], name='uq_piquete_empresa_nome')
        ]
        indexes = [models.Index(fields=["empresa", "status"])]

    def __str__(self):
        return f"{self.nome} ({self.empresa.nome})"


class Cavalo(models.Model):
    CATEGORIA_CHOICES = [
        ('PROPRIO', 'Próprio (Escola)'),
        ('HOTELARIA', 'Hotelaria (Particular)'),
    ]
    STATUS_SAUDE_CHOICES = [
        ('Saudável', 'Saudável'),
        ('Alerta', 'Alerta'),
        ('Doente', 'Doente'),
        ('Tratamento', 'Em Tratamento'),
    ]
    LOCAL_DORMIDA = [
        ('BAIA', 'Dorme na Baia'),
        ('PIQUETE', 'Dorme no Piquete'),
    ]
    RACA_CHOICES = [
        ('mang_marchador', 'Mangalarga Marchador'),
        ('quarto_milha', 'Quarto de Milha'),
        ('psl', 'Puro Sangue Lusitano'),
        ('crioulo', 'Crioulo'),
        ('hipismo', 'Cavalo de Hipismo (BH)'),
        ('srd', 'Sem Raça Definida'),
    ]
    ATIVIDADE_CHOICES = [
        ('0.018', 'Leve (Passeio/Aposentado)'),
        ('0.025', 'Moderada (Escola/Aulas)'),
        ('0.035', 'Intensa (Salto/Competição)'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='PROPRIO')
    status_saude = models.CharField(max_length=20, choices=STATUS_SAUDE_CHOICES, default='Saudável')
    onde_dorme = models.CharField(max_length=10, choices=LOCAL_DORMIDA, default='BAIA')
    foto = models.ImageField(upload_to='cavalos/', null=True, blank=True)

    # IA e Raça
    raca = models.CharField(max_length=25, choices=RACA_CHOICES, default='srd')
    peso = models.FloatField(
        default=450.0,
        validators=[MinValueValidator(100)],
        help_text="Peso aproximado para cálculo de ração"
    )
    fator_atividade = models.CharField(max_length=10, choices=ATIVIDADE_CHOICES, default='0.025')

    # Equipamentos para Cavalariços
    tipo_sela = models.CharField(max_length=100, blank=True, help_text="Ex: Sela Salto Americana")
    tipo_cabecada = models.CharField(max_length=100, blank=True, help_text="Ex: Cabeçada com Freio D")
    material_proprio = models.BooleanField(default=False, help_text="Marque se o material for exclusivo do proprietário")

    # Alojamento
    baia = models.OneToOneField(Baia, on_delete=models.SET_NULL, null=True, blank=True)
    piquete = models.ForeignKey(Piquete, on_delete=models.SET_NULL, null=True, blank=True)
    proprietario = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='cavalos',
        help_text="Se for Próprio, vincular ao gestor ou escola"
    )

    # SAÚDE
    ultima_vacina = models.DateField(null=True, blank=True)
    ultimo_ferrageamento = models.DateField(null=True, blank=True)
    # Novos campos
    ultimo_vermifugo = models.DateField(null=True, blank=True)
    ultimo_casqueamento = models.DateField(null=True, blank=True)

    # PLANO ALIMENTAR
    racao_tipo = models.CharField(max_length=100, blank=True, help_text="Ex: Guabi Equi-S")
    racao_qtd_manha = models.CharField(max_length=50, blank=True, help_text="Ex: 2kg")
    racao_qtd_noite = models.CharField(max_length=50, blank=True, help_text="Ex: 2kg")
    feno_tipo = models.CharField(max_length=100, blank=True, default="Coast Cross")
    feno_qtd = models.CharField(max_length=100, blank=True, default="À vontade")
    complemento_nutricional = models.TextField(blank=True)

    mensalidade_baia = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))

    class Meta:
        ordering = ['nome']
        indexes = [
            models.Index(fields=["empresa", "status_saude"]),
            models.Index(fields=["empresa", "categoria"]),
        ]

    def __str__(self):
        return f"{self.nome} ({self.empresa.nome})"


# --- 3. DOCUMENTAÇÃO E ALERTAS ---

class DocumentoCavalo(models.Model):
    TIPO_CHOICES = [
        ('GTA', 'GTA'),
        ('EXAME', 'Exame (Mormo/Anemia)'),
        ('VACINA', 'Atestado de Vacinação'),
        ('OUTRO', 'Outro'),
    ]
    cavalo = models.ForeignKey(Cavalo, on_delete=models.CASCADE, related_name='documentos')
    titulo = models.CharField(max_length=100, default="Documento")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    data_validade = models.DateField()
    arquivo = models.FileField(upload_to='docs_cavalos/', null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["data_validade", "tipo"])]

    def __str__(self):
        return f"{self.tipo} - {self.cavalo.nome}"


class RegistroOcorrencia(models.Model):
    cavalo = models.ForeignKey(Cavalo, on_delete=models.CASCADE, related_name='ocorrencias')
    data = models.DateTimeField(default=timezone.now)
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    foto_evidencia = models.ImageField(upload_to='ocorrencias/', null=True, blank=True)
    veterinario = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-data"]
        indexes = [models.Index(fields=["cavalo", "data"])]

    def __str__(self):
        return f"{self.titulo} - {self.cavalo.nome}"


# --- 4. AULAS E ESTOQUE ---

class Aula(models.Model):
    LOCAIS_CHOICES = [
        ('picadeiro_1', 'Picadeiro Principal'),
        ('picadeiro_2', 'Picadeiro Coberto'),
        ('pista_salto', 'Pista de Salto'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    TIPO_AULA_CHOICES = [('NORMAL', 'Aula Normal'), ('RECUPERAR', 'Aula a Recuperar')]

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='aulas')
    cavalo = models.ForeignKey(Cavalo, on_delete=models.CASCADE, related_name='aulas')

    instrutor = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='aulas_ministradas',
        limit_choices_to={'cargo': 'Professor'}
    )

    data_hora = models.DateTimeField(db_index=True)
    local = models.CharField(max_length=20, choices=LOCAIS_CHOICES, default='picadeiro_1')
    tipo = models.CharField(max_length=15, choices=TIPO_AULA_CHOICES, default='NORMAL')
    concluida = models.BooleanField(default=False)
    relatorio_treino = models.TextField(blank=True)

    class Meta:
        ordering = ["data_hora"]
        indexes = [models.Index(fields=["empresa", "data_hora"])]

    def clean(self):
        """
        Garante integridade:
        - Aluno, Cavalo e Instrutor (se houver) devem pertencer à mesma Empresa da Aula
        - Instrutor precisa ter cargo 'Professor'
        """
        erros = {}
        if self.aluno and self.empresa and self.aluno.empresa_id != self.empresa_id:
            erros['aluno'] = "Aluno deve pertencer à mesma empresa da aula."
        if self.cavalo and self.empresa and self.cavalo.empresa_id != self.empresa_id:
            erros['cavalo'] = "Cavalo deve pertencer à mesma empresa da aula."
        if self.instrutor:
            if self.instrutor.empresa_id != self.empresa_id:
                erros['instrutor'] = "Instrutor deve pertencer à mesma empresa da aula."
            if self.instrutor.cargo != Perfil.Cargo.PROFESSOR:
                erros['instrutor'] = "Instrutor deve ter cargo 'Professor'."
        if erros:
            from django.core.exceptions import ValidationError
            raise ValidationError(erros)

    def __str__(self):
        data = self.data_hora.strftime('%d/%m') if self.data_hora else 's/ data'
        return f"{self.aluno.nome} - {data}"


class ItemEstoque(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    quantidade_atual = models.IntegerField(default=0)
    alerta_minimo = models.IntegerField(default=5)
    unidade = models.CharField(max_length=20, default="Unidade", help_text="Ex: KG, Sacos, Fardos")
    fornecedor_contato = models.CharField(max_length=20, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "nome"]),
            models.Index(fields=["empresa", "quantidade_atual"]),
        ]

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"


class MovimentacaoFinanceira(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    TIPO_CHOICES = [('Receita', 'Receita'), ('Despesa', 'Despesa')]
    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    # Permite backdate/correções (em vez de auto_now_add=True)
    data = models.DateField(default=timezone.localdate)

    class Meta:
        indexes = [models.Index(fields=["empresa", "data", "tipo"])]

    def __str__(self):
        return f"{self.tipo}: {self.descricao} ({self.empresa.nome})"


# --- 5. SINCRONIZAÇÃO DE BAIA (status) ---

@receiver(pre_save, sender=Cavalo)
def liberar_baia_antiga(sender, instance: Cavalo, **kwargs):
    """Se a baia do cavalo mudou, libera a antiga."""
    if not instance.pk:
        return
    try:
        antigo = Cavalo.objects.select_related('baia').get(pk=instance.pk)
    except Cavalo.DoesNotExist:
        return
    if antigo.baia and antigo.baia != instance.baia:
        antigo.baia.status = 'Livre'
        antigo.baia.save(update_fields=['status'])

@receiver(post_save, sender=Cavalo)
def ocupar_baia_nova(sender, instance: Cavalo, **kwargs):
    """Ocupa a nova baia (se houver)."""
    if instance.baia:
        instance.baia.status = 'Ocupada'
        instance.baia.save(update_fields=['status'])