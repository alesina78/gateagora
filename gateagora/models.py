# -*- coding: utf-8 -*-
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.db.models import Sum, Q
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
    perfil_usuario = models.OneToOneField(
        'Perfil',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aluno_vinculado',
        verbose_name="Login do Aluno",
        help_text="Perfil de acesso do aluno ao sistema"
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
    ultimo_vermifugo = models.DateField(null=True, blank=True)
    ultimo_ferrageamento = models.DateField(null=True, blank=True)
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


class ConfirmacaoPresenca(models.Model):
    """
    Registra que um aluno confirmou presença em uma aula específica.
    """
    aula = models.OneToOneField(
        'Aula',
        on_delete=models.CASCADE,
        related_name='confirmacao'
    )
    aluno = models.ForeignKey(
        'Aluno',
        on_delete=models.CASCADE,
        related_name='confirmacoes'
    )
    confirmado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Confirmação de Presença"
        verbose_name_plural = "Confirmações de Presença"

    def __str__(self):
        return f"✅ {self.aluno.nome} confirmou {self.aula}"


class ItemEstoque(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)

    alerta_minimo = models.IntegerField(default=5)
    unidade = models.CharField(
        max_length=20,
        default="Unidade",
        help_text="Ex: KG, Sacos, Fardos"
    )
    fornecedor_contato = models.CharField(max_length=20, blank=True)

    consumo_diario = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Consumo médio diário (para calcular dias restantes)"
    )

    # ⚠️ Campo legado — mantido para o formulário de fechamento do dia (input de ajuste manual).
    # NÃO use para cálculos de disponibilidade. A fonte da verdade são os lotes.
    quantidade_atual = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "nome"]),
            models.Index(fields=["empresa", "quantidade_atual"]),
        ]

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"

    @property
    def quantidade_valida(self):
        """
        Soma dos lotes ativos dentro do prazo de validade.

        Regras:
        - Lotes sem data_validade são considerados sempre válidos (ex: sal mineral).
        - Lotes com data_validade < hoje são IGNORADOS — produto vencido não conta.
        - Se não há NENHUM lote cadastrado, cai no fallback do campo legado
          (quantidade_atual), pois o item não usa controle por lote.
        """
        hoje = timezone.localdate()
        lotes_ativos = self.lotes.filter(ativo=True)

        if not lotes_ativos.exists():
            # Sem lotes: item gerenciado pelo campo legado (sem controle de validade por lote)
            return Decimal(str(self.quantidade_atual))

        resultado = lotes_ativos.filter(
            Q(data_validade__isnull=True) | Q(data_validade__gte=hoje)
        ).aggregate(total=Sum('quantidade'))['total']

        return Decimal(str(resultado or 0))

    @property
    def quantidade_vencida(self):
        """
        Soma dos lotes ativos que já venceram — quantidade a ser descartada.
        Retorna 0 se não há lotes vencidos.
        """
        hoje = timezone.localdate()
        resultado = self.lotes.filter(
            ativo=True,
            data_validade__isnull=False,
            data_validade__lt=hoje,
        ).aggregate(total=Sum('quantidade'))['total']
        return Decimal(str(resultado or 0))

    @property
    def estoque_disponivel(self):
        """
        Estoque que pode efetivamente ser usado.

        Equivalente a quantidade_valida, mas explicitamente retorna 0
        quando status_validade == 'vencido' — usado pelos templates e pela
        view do dashboard para garantir que vencido = zero na exibição.

        Diferença de quantidade_valida: quando há lotes sem data_validade
        junto com lotes vencidos, quantidade_valida soma os sem-validade
        normalmente (correto). estoque_disponivel faz o mesmo — ambos
        ignoram os lotes vencidos. O status_validade é que determina
        se o item aparece como "VENCIDO" no painel.
        """
        return self.quantidade_valida

    @property
    def dias_restantes(self):
        """Projeção de dias até o estoque se esgotar pelo consumo diário."""
        if not self.consumo_diario or self.consumo_diario <= 0:
            return None
        qtd = self.quantidade_valida
        if qtd <= 0:
            return 0
        return int(qtd / self.consumo_diario)

    @property
    def dias_para_vencer(self):
        """
        Dias até o lote com validade mais próxima vencer.

        CORRIGIDO: busca apenas lotes com data_validade definida,
        ordenando pelo mais próximo — seja ele já vencido (negativo)
        ou ainda válido. Lotes sem data_validade são ignorados aqui
        (eles nunca vencem, não fazem sentido no cálculo).
        """
        lote_proximo = self.lotes.filter(
            ativo=True,
            data_validade__isnull=False,
        ).order_by('data_validade').first()

        if not lote_proximo:
            return None
        return (lote_proximo.data_validade - timezone.localdate()).days

    @property
    def status_validade(self):
        """
        Estado de validade do item baseado no lote com data mais próxima.

        Retornos possíveis:
        'ok'             → dentro do prazo (> 30 dias) ou sem data de validade
        'alerta'         → vence em até 30 dias
        'alerta_critico' → vence em até 5 dias
        'vencido'        → lote mais próximo já venceu (dias < 0)

        Nota:
        - 'vencido' não significa necessariamente estoque = 0.
        - Pode haver lotes sem data_validade ainda válidos.
        """

        hoje = timezone.localdate()

        # Busca o lote ativo com validade mais próxima
        lote = (
            self.lotes
            .filter(ativo=True)
            .exclude(data_validade__isnull=True)
            .order_by('data_validade')
            .first()
        )

        # Sem lote com validade → considera OK
        if not lote:
            return 'ok'

        dias = (lote.data_validade - hoje).days

        if dias < 0:
            return 'vencido'
        if dias <= 5:
            return 'alerta_critico'
        if dias <= 30:
            return 'alerta'

        return 'ok'


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
    
    # Adicione este método dentro da classe Fatura
    def calcular_total_real(self):
        """
        Soma o valor das aulas e da hotelaria vinculadas a esta fatura.
        Se v_total já tiver um valor manual, ele ignora a soma e usa o v_total.
        """
        if self.v_total and self.v_total > 0:
            return self.v_total
        
        # Soma todos os itens de aula vinculados
        total_aulas = sum(item.valor for item in self.itens_aula.all())
        # Soma todos os itens de hotelaria vinculados
        total_hotelaria = sum(item.valor for item in self.itens_hotelaria.all())
        
        return total_aulas + total_hotelaria


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
    prazo_confirmacao_horas = models.PositiveIntegerField(
        default=24,
        help_text="Horas antes da aula dentro das quais o aluno pode confirmar presença (0 = sem prazo)"
    )

    class Meta:
        verbose_name        = "Configuração de Prazos de Manejo"
        verbose_name_plural = "Configurações de Prazos de Manejo"

    def __str__(self):
        return f"Prazos de Manejo — {self.empresa.nome}"
    
class ConfigPrecoManejo(models.Model):
    """Preços de cobrança por procedimento de manejo — por empresa."""
    empresa = models.OneToOneField(
        Empresa, on_delete=models.CASCADE, related_name='config_preco_manejo'
    )
    cobrar_vacina        = models.BooleanField(default=False)
    valor_vacina         = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    cobrar_vermifugo     = models.BooleanField(default=False)
    valor_vermifugo      = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    cobrar_ferrageamento = models.BooleanField(default=False)
    valor_ferrageamento  = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    cobrar_casqueamento  = models.BooleanField(default=False)
    valor_casqueamento   = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name        = "Configuração de Preços de Manejo"
        verbose_name_plural = "Configurações de Preços de Manejo"

    def __str__(self):
        return f"Preços de Manejo — {self.empresa.nome}"


# -- 5.5 lote estoque
class LoteEstoque(models.Model):
    item = models.ForeignKey(
        'ItemEstoque',
        on_delete=models.CASCADE,
        related_name='lotes',
        verbose_name="Item de Estoque"
    )
    quantidade    = models.DecimalField(max_digits=10, decimal_places=2)
    data_validade = models.DateField(null=True, blank=True)
    data_entrada  = models.DateField(auto_now_add=True)
    numero_lote   = models.CharField(max_length=50, blank=True)
    ativo         = models.BooleanField(default=True)

    class Meta:
        verbose_name        = "Lote de Estoque"
        verbose_name_plural = "Lotes de Estoque"
        ordering            = ["data_validade", "data_entrada"]
        indexes             = [models.Index(fields=["item", "data_validade", "ativo"])]

    def __str__(self):
        val = self.data_validade.strftime("%d/%m/%Y") if self.data_validade else "sem validade"
        return f"{self.item.nome} — Lote {self.numero_lote or self.pk} ({val})"

    @property
    def vencido(self):
        if not self.data_validade:
            return False
        return self.data_validade < timezone.localdate()

    @property
    def dias_para_vencer(self):
        if not self.data_validade:
            return None
        return (self.data_validade - timezone.localdate()).days


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
