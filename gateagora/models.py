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
        ALUNO      = 'Aluno',      'Aluno/Cliente'  # novo

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
    telefone = models.CharField(
        max_length=20, 
        blank=True, null=True, 
        help_text="WhatsApp com DDD")

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
    
    plano = models.ForeignKey(
        'Plano', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Plano Contratado"
    )


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
    USA_FERRADURA_CHOICES = [
        ('SIM', 'Ferrado (Usa Ferradura)'),
        ('NAO', 'Descalço (Apenas Casqueamento)'),
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
    ultimo_vermifugo = models.DateField(null=True, blank=True)
    ultimo_casqueamento = models.DateField(null=True, blank=True)
    usa_ferradura = models.CharField(
        max_length=3,
        choices=USA_FERRADURA_CHOICES,
        default='NAO',
        verbose_name="Usa Ferradura?"
    )

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
    consumo_diario = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Consumo médio por dia (deixe em branco se não aplicável)"
    )

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "nome"]),
            models.Index(fields=["empresa", "quantidade_atual"]),
        ]

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"

    @property
    def dias_restantes(self):
        """Retorna dias até zerar o estoque com base no consumo diário."""
        if not self.consumo_diario or self.consumo_diario <= 0:
            return None
        try:
            return int(Decimal(str(self.quantidade_atual)) / self.consumo_diario)
        except Exception:
            return None

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

class Plano(models.Model):
    """Define as regras de cobrança (Ex: 2x semana, Mensal Livre)"""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100) # Ex: "2x por Semana"
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return f"{self.nome} - R$ {self.valor_mensal}"

class Fatura(models.Model):
    """Controle de Contas a Receber"""
    STATUS_CHOICES = [
        ('PAGO', 'Pago'),
        ('PENDENTE', 'Pendente'),
        ('ATRASADO', 'Atrasado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    aluno = models.ForeignKey(
        'Aluno',
        on_delete=models.CASCADE,
        related_name='faturas',
        null=True,      # temporário para evitar erro de integridade
        blank=True
    )
    data_vencimento = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    data_pagamento = models.DateField(null=True, blank=True)

    @property
    def total(self):
        """Total calculado a partir dos itens (ItemFatura)"""
        from django.db.models import Sum
        from decimal import Decimal
        try:
            result = self.itens.aggregate(total=Sum('valor'))['total']
            return Decimal(result) if result is not None else Decimal('0.00')
        except Exception:
            return Decimal(self.valor or 0)

    def __str__(self):
        aluno_nome = getattr(self.aluno, 'nome', 'Sem aluno')
        return f"{aluno_nome} - {self.data_vencimento} ({self.status})"


class ItemFatura(models.Model):
    TIPO_CHOICES = [
        ('HOTELARIA',     'Hotelaria'),
        ('AULA',          'Aula'),
        ('VETERINARIO',   'Veterinário'),
        ('VERMIFUGO',     'Vermífugo'),
        ('CASQUEIO',      'Casqueio'),
        ('FERRAGEAMENTO', 'Ferrageamento'),
        ('OUTROS',        'Outros'),
    ]

    fatura = models.ForeignKey(Fatura, on_delete=models.CASCADE, related_name='itens')
    cavalo = models.ForeignKey(
        'Cavalo',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Cavalo'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=255, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item de Fatura'
        verbose_name_plural = 'Itens de Fatura'
        ordering = ['tipo', 'data']

    def __str__(self):
        return f"{self.get_tipo_display()} — R$ {self.valor} ({self.fatura})" 

class EventoAgendaCavalo(models.Model):
    """Agenda Inteligente do Cavalo (Vet, Ferrageamento, Descanso)"""
    TIPO_CHOICES = [
        ('AULA', 'Aula'),
        ('VETERINARIO', 'Veterinário'),
        ('FERRAGEAMENTO', 'Ferrageamento'),
        ('DESCANSO', 'Descanso'),
    ]
    cavalo = models.ForeignKey('Cavalo', on_delete=models.CASCADE, related_name='eventos')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.cavalo.nome}"

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

class ConfigPrazoManejo(models.Model):
    empresa             = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='config_prazo_manejo')
    prazo_vacina        = models.PositiveIntegerField(default=365, help_text="Dias entre vacinações")
    prazo_vermifugo     = models.PositiveIntegerField(default=90,  help_text="Dias entre vermifugações")
    prazo_ferrageamento = models.PositiveIntegerField(default=60,  help_text="Dias entre ferrageamentos")
    prazo_casqueamento  = models.PositiveIntegerField(default=60,  help_text="Dias entre casqueamentos")

    class Meta:
        verbose_name        = "Configuração de Prazos de Manejo"
        verbose_name_plural = "Configurações de Prazos de Manejo"

    def __str__(self):
        return f"Prazos de Manejo — {self.empresa.nome}"

# --- 6. MOVIMENTAÇÃO DE ESTOQUE ---

class MovimentacaoEstoque(models.Model):
    """Registro de entradas, saídas e ajustes de estoque por dia."""
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida',   'Saída'),
        ('ajuste',  'Ajuste (Fechamento do Dia)'),
    ]

    empresa    = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    item       = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE, related_name='movimentacoes')
    data       = models.DateField(default=timezone.localdate)
    quantidade = models.DecimalField(max_digits=8, decimal_places=2)
    tipo       = models.CharField(max_length=10, choices=TIPO_CHOICES)
    observacao = models.TextField(blank=True)
    criado_em  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-criado_em']
        indexes  = [models.Index(fields=["empresa", "data", "item"])]
        verbose_name        = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.item.nome} ({self.quantidade} {self.item.unidade}) em {self.data}"