# -*- coding: utf-8 -*-
"""Admin do Gate 4"""

from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django import forms
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError

from datetime import date, timedelta
from datetime import datetime

from unfold.admin import ModelAdmin, TabularInline
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from .models import (
    Aluno,
    Aula,
    Baia,
    RacaCavalo,
    Cabecada,
    Cavalo,
    ChecklistItem,
    ConfigPrazoManejo,
    ConfigPrecoManejo,
    DocumentoCavalo,
    Empresa,
    EventoAgendaCavalo,
    Fatura,
    LoteEstoque,
    ItemEstoque,
    ItemFatura,
    MovimentacaoFinanceira,
    Perfil,
    Piquete,
    Plano,
    RegistroOcorrencia,
    Sela,
    Fornecedor,
    LocalAula,
)

# ── ACTION: DUPLICAR REGISTRO ───────────────────────────────────────────────

def duplicar_registro(modeladmin, request, queryset):
    primeiro_pk = None
    for obj in queryset:
        nome_modelo = obj.__class__.__name__
        obj.pk = None
        if nome_modelo == 'Aluno':
            obj.nome = f"{obj.nome} (Cópia)"
            obj.foto = None
            obj.perfil_usuario = None
        elif nome_modelo == 'Aula':
            obj.data_hora = obj.data_hora + timedelta(days=7)
            obj.concluida = False
            obj.relatorio_treino = ""
        elif nome_modelo == 'Baia':
            obj.numero = "???"
        elif nome_modelo == 'Piquete':
            obj.nome = f"{obj.nome} (Cópia)"
        elif nome_modelo == 'ItemEstoque':
            obj.nome = f"{obj.nome} (Cópia)"
        obj.save()
        if primeiro_pk is None:
            primeiro_pk = obj.pk
    total = queryset.count()
    if primeiro_pk and total == 1:
        app  = queryset.model._meta.app_label
        nome = queryset.model._meta.model_name
        url  = reverse(f"admin:{app}_{nome}_change", args=[primeiro_pk])
        modeladmin.message_user(request, "✅ Registro duplicado — revise e salve.", messages.SUCCESS)
        return HttpResponseRedirect(url)
    modeladmin.message_user(request, f"✅ {total} registro(s) duplicado(s).", messages.SUCCESS)

duplicar_registro.short_description = "📋 Duplicar registros selecionados"


# ── ACTION: GERAR AULAS POR PLANO ───────────────────────────────────────────

class GerarAulasForm(forms.Form):
    """
    Formulário exibido como tela intermediária no Admin.
    O gestor escolhe: dias da semana, horário, cavalo, período, instrutor e local.
    """
    DIAS_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    FREQUENCIA_CHOICES = [
        ('semanal', 'Semanal — toda semana'),
        ('quinzenal', 'Quinzenal — a cada 2 semanas'),
    ]

    dias_semana = forms.MultipleChoiceField(
        choices=DIAS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Dias da semana",
        help_text="Selecione um ou mais dias"
    )
    frequencia = forms.ChoiceField(
        choices=FREQUENCIA_CHOICES,
        label="Frequência",
        initial='semanal',
    )
    horario = forms.TimeField(
        label="Horário",
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        help_text="Ex: 17:00"
    )
    data_inicio = forms.DateField(
        label="Data de início",
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )
    data_fim = forms.DateField(
        label="Data de fim",
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        help_text="Máximo recomendado: 3 meses"
    )
    cavalo = forms.ModelChoiceField(
        queryset=Cavalo.objects.none(),  # Definido no __init__ ou na action
        label="Cavalo",
        required=False,
        empty_label="— definir depois —",
        help_text="Pode ser alterado aula a aula depois",
    )
    instrutor = forms.ModelChoiceField(
        queryset=Perfil.objects.none(),  # Definido no __init__ ou na action
        label="Instrutor",
        required=False,
        empty_label="— selecionar instrutor —",
        help_text="Opcional"
    )
    local = forms.ChoiceField(
        choices=Aula.LOCAIS_CHOICES,  # Importado diretamente do Model Aula
        label="Local",
        initial='picadeiro_1',
    )

    def __init__(self, *args, empresa=None, cavalo_queryset=None, instrutor_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Atualiza os querysets se informados via parâmetro ou filtra pela empresa
        if cavalo_queryset is not None:
            self.fields['cavalo'].queryset = cavalo_queryset
        elif empresa:
            self.fields['cavalo'].queryset = Cavalo.objects.filter(empresa=empresa)

        if instrutor_queryset is not None:
            self.fields['instrutor'].queryset = instrutor_queryset
        elif empresa:
            cargo_professor = getattr(Perfil.Cargo, 'PROFESSOR', 'Professor')
            self.fields['instrutor'].queryset = Perfil.objects.filter(
                empresa=empresa, 
                cargo=cargo_professor
            )

    def clean_dias_semana(self):
        """
        Converte os valores retornados pelo MultipleChoiceField para inteiros.
        """
        dias = self.cleaned_data.get('dias_semana', [])
        return [int(dia) for dia in dias]

    def clean(self):
        """
        Valida se a data de fim é posterior ou igual à data de início.
        """
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if data_inicio and data_fim:
            if data_fim < data_inicio:
                raise ValidationError({
                    'data_fim': "A data de fim não pode ser anterior à data de início."
                })

        return cleaned_data


# ── BASES MULTI-EMPRESA ─────────────────────────────────────────────────────

class BaseEmpresaAdmin(ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request, 'empresa') and request.empresa:
            return qs.filter(empresa=request.empresa)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not change and not request.user.is_superuser:
            if hasattr(request, 'empresa') and request.empresa:
                obj.empresa = request.empresa
        super().save_model(request, obj, form, change)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if not request.user.is_superuser and hasattr(request, 'empresa') and request.empresa:
            initial['empresa'] = request.empresa.id
        return initial

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "empresa":
            if not request.user.is_superuser and hasattr(request, 'empresa') and request.empresa:
                kwargs["queryset"] = Empresa.objects.filter(id=request.empresa.id)
                kwargs["widget"] = forms.HiddenInput()
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        campos_para_filtrar = ["aluno", "cavalo", "baia", "piquete", "proprietario", "instrutor", "plano"]
        if db_field.name in campos_para_filtrar:
            if not request.user.is_superuser and hasattr(request, 'empresa') and request.empresa:
                model = db_field.related_model
                kwargs["queryset"] = model.objects.filter(empresa=request.empresa)

        if db_field.name == "perfil_usuario":
            if not request.user.is_superuser and hasattr(request, 'empresa') and request.empresa:
                kwargs["queryset"] = Perfil.objects.filter(empresa=request.empresa)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class BaseCavaloAdmin(ModelAdmin):
    """Base para models que têm FK para Cavalo"""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request, 'empresa') and request.empresa:
            return qs.filter(cavalo__empresa=request.empresa)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "cavalo":
            if not request.user.is_superuser and hasattr(request, 'empresa') and request.empresa:
                kwargs["queryset"] = Cavalo.objects.filter(empresa=request.empresa)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class BaseItemEstoqueAdmin(ModelAdmin):
    """Base para models que têm FK para ItemEstoque (ex: LoteEstoque)"""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request, 'empresa') and request.empresa:
            return qs.filter(item__empresa=request.empresa)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "item":
            if not request.user.is_superuser and hasattr(request, 'empresa') and request.empresa:
                kwargs["queryset"] = ItemEstoque.objects.filter(empresa=request.empresa)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PermissaoPorCargoMixin:
    """
    Mixin genérico pra restringir uma tela do admin por Cargo do Perfil.
    Configure em cada subclasse:
      - cargos_acesso_total: podem ver, criar, editar e excluir
      - cargos_somente_leitura: só podem ver, sem editar/criar/excluir
    Superuser sempre tem acesso total, independente da configuração.
    Combine com BaseEmpresaAdmin/BaseCavaloAdmin/etc (que continuam
    cuidando do isolamento entre empresas) -- este mixin só decide
    QUEM de dentro da empresa pode acessar a tela.
    """
    cargos_acesso_total = set()
    cargos_somente_leitura = set()

    def _cargo_do_usuario(self, request):
        if hasattr(request.user, 'perfil'):
            return request.user.perfil.cargo
        return None

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        cargo = self._cargo_do_usuario(request)
        return cargo in self.cargos_acesso_total or cargo in self.cargos_somente_leitura

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return self._cargo_do_usuario(request) in self.cargos_acesso_total

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._cargo_do_usuario(request) in self.cargos_acesso_total

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._cargo_do_usuario(request) in self.cargos_acesso_total

@admin.register(Sela)
class SelaAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ["nome"]
    search_fields = ["nome"]


@admin.register(Cabecada)
class CabecadaAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ["nome"]
    search_fields = ["nome"]

# ── INLINES ─────────────────────────────────────────────────────────────────

class DocumentoInline(TabularInline):
    model = DocumentoCavalo
    extra = 0
    tab = True


class OcorrenciaInline(TabularInline):
    model = RegistroOcorrencia
    extra = 0
    tab = True
    fields = ['data', 'titulo', 'descricao', 'veterinario']


class ItemFaturaInline(TabularInline):
    model = ItemFatura
    extra = 0
    tab = True
    fields = ['tipo', 'cavalo', 'descricao', 'valor', 'data']

    def get_changeform_initial_data(self, request):
        return {'data': date.today()}

    def has_add_permission(self, request, obj=None):
        if obj and obj.status == 'PAGO':
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'PAGO':
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == 'PAGO':
            return False
        return True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "cavalo":
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                try:
                    fatura = Fatura.objects.get(pk=obj_id)
                    kwargs["queryset"] = Cavalo.objects.filter(empresa=fatura.empresa)
                except Fatura.DoesNotExist:
                    pass
            elif not request.user.is_superuser and hasattr(request, 'empresa') and request.empresa:
                kwargs["queryset"] = Cavalo.objects.filter(empresa=request.empresa)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class LoteEstoqueInline(TabularInline):
    model = LoteEstoque
    extra = 0
    fields = (
        'numero_lote',
        'quantidade',
        'data_validade',
        'ativo',
    )
    
# ── ADMINS ──────────────────────────────────────────────────────────────────

@admin.register(Empresa)
class EmpresaAdmin(ModelAdmin):
    list_display = ["nome", "slug", "cidade", "cnpj"]
    search_fields = ["nome", "cnpj"]
    prepopulated_fields = {"slug": ("nome",)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs  # vê tudo

        # usuário normal
        if hasattr(request.user, "perfil") and request.user.perfil.empresa:
            return qs.filter(id=request.user.perfil.empresa.id)

        return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        # Superuser vê tudo; gestor só vê a própria empresa (sem editar)
        if request.user.is_superuser:
            return True
        return hasattr(request.user, 'perfil') and bool(request.user.perfil.empresa)


@admin.register(Perfil)
class PerfilAdmin(ModelAdmin):
    list_display = ["user", "empresa", "cargo", "telefone"]
    list_editable = ["empresa", "cargo", "telefone"]
    list_filter = ["cargo"]
    search_fields = ["user__username", "user__first_name", "telefone"]

    fieldsets = (
        (None, {
            "fields": ("user", "empresa", "cargo", "telefone")
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(empresa=request.user.perfil.empresa)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "empresa" and not request.user.is_superuser:
            if hasattr(request.user, 'perfil'):
                kwargs["queryset"] = Empresa.objects.filter(id=request.user.perfil.empresa_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return hasattr(request.user, 'perfil') and request.user.perfil.cargo == 'Gestor'

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and obj.user == request.user:
            return True  # qualquer um pode editar o próprio perfil
        # Gestor edita qualquer perfil da própria empresa
        if hasattr(request.user, 'perfil') and request.user.perfil.cargo == 'Gestor':
            if obj is None:
                return True
            return obj.empresa_id == request.user.perfil.empresa_id
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Gestor não pode escolher empresa diferente da sua
        if db_field.name == "empresa":
            if not request.user.is_superuser and hasattr(request.user, 'perfil'):
                kwargs["queryset"] = Empresa.objects.filter(
                    id=request.user.perfil.empresa_id
                )
                kwargs["widget"] = forms.HiddenInput()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Aluno)
class AlunoAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ("nome", "empresa", "ativo", "get_whatsapp", "streak_atual", "melhor_streak")
    search_fields = ("nome",)
    list_filter = ("empresa", "ativo")
    list_editable = ("ativo",)
    actions = ["criar_login_aluno", "gerar_aulas_plano"]

    # 'telefone' não existe no model Aluno — fica em perfil_usuario.telefone
    # Expomos via readonly para mostrar no formulário sem causar FieldError
    fields = [
        'empresa',
        'perfil_usuario',
        'nome',
        'telefone',    # readonly calculado abaixo
        'foto',
        'ativo',
        'valor_aula',
        'plano',
        'streak_atual',
        'melhor_streak',
    ]
    readonly_fields = ('telefone_perfil',)

    @admin.display(description="Telefone (editar no Perfil vinculado)")
    def telefone_perfil(self, obj):
        if not obj.perfil_usuario:
            return "Sem perfil vinculado — use a action 'Criar Login'"
        tel = obj.perfil_usuario.telefone or "—"
        url = reverse("admin:gateagora_perfil_change", args=[obj.perfil_usuario.pk])
        return format_html(
            '{} &nbsp;<a href="{}" target="_blank">✏️ Editar Perfil</a>',
            tel, url,
        )

    @admin.display(description="WhatsApp")
    def get_whatsapp(self, obj):
        return obj.telefone_limpo or '-'

    
    @admin.display(description="Usuário")
    def usuario_login(self, obj):
        if obj.perfil_usuario and obj.perfil_usuario.user:
            return obj.perfil_usuario.user.username
        return "-"

    @admin.display(description="Valor Aula")
    def valor_aula_formatado(self, obj):
        return f"R$ {obj.valor_aula}"

    @admin.display(description="Tem Login?", boolean=True)
    def tem_login(self, obj):
        return obj.perfil_usuario is not None

    @admin.action(description="🔑 Criar Login para Aluno(s) selecionado(s)")
    def _criar_login_para_aluno(self, request, aluno):
        """Cria User + Perfil pro aluno e vincula. Usado tanto pela action manual
        quanto automaticamente ao salvar um Aluno novo (login agora é obrigatório)."""
        base_username = aluno.nome.lower().replace(" ", ".").replace("ç", "c").replace("ã", "a").replace("ê", "e").replace("é", "e").replace("á", "a").replace("ó", "o").replace("ú", "u").replace("í", "i")[:25]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        if aluno.telefone and len(aluno.telefone) >= 4:
            sufixo = aluno.telefone[-4:]
        else:
            # Sem telefone cadastrado: gera 4 dígitos aleatórios,
            # nunca repete entre alunos diferentes.
            sufixo = get_random_string(4, allowed_chars='0123456789')
        senha_temp = sufixo + "aluno"

        user = User.objects.create_user(
            username=username,
            first_name=aluno.nome.split()[0] if aluno.nome else "",
            last_name=" ".join(aluno.nome.split()[1:]) if len(aluno.nome.split()) > 1 else "",
            password=senha_temp
        )

        perfil = Perfil.objects.create(
            user=user,
            empresa=aluno.empresa,
            cargo='Aluno',
            telefone=aluno.telefone
        )

        aluno.perfil_usuario = perfil
        aluno.save(update_fields=['perfil_usuario'])

        messages.success(
            request,
            f"✅ Login criado para {aluno.nome} — "
            f"Usuário: {username} | Senha: {senha_temp}"
        )
        return perfil


    @admin.action(description="🔑 Criar Login (usuário + senha)")
    def criar_login_aluno(self, request, queryset):
        criados = 0
        for aluno in queryset:
            if aluno.perfil_usuario:
                messages.warning(request, f"{aluno.nome} já possui login.")
                continue
            self._criar_login_para_aluno(request, aluno)
            criados += 1

        if criados == 0:
            messages.warning(request, "Nenhum login foi criado.")


    @admin.action(description="📅 Gerar aulas por plano semanal")
    def gerar_aulas_plano(self, request, queryset):
        from django.template.response import TemplateResponse
        from .models import Cavalo, Perfil

        empresa = getattr(request, 'empresa', None)

        # ── Passo 2: formulário já submetido ────────────────────────
        if 'aplicar' in request.POST:
            form = GerarAulasForm(request.POST)
            form.fields['cavalo'].queryset    = Cavalo.objects.filter(empresa=empresa)
            form.fields['instrutor'].queryset = Perfil.objects.filter(
                empresa=empresa, cargo='Professor'
            )

            form.fields['cavalo'].required = False
            if form.is_valid():
                dias     = [int(d) for d in form.cleaned_data['dias_semana']]
                horario  = form.cleaned_data['horario']
                inicio   = form.cleaned_data['data_inicio']
                fim      = form.cleaned_data['data_fim']
                cavalo   = form.cleaned_data['cavalo']
                instrutor= form.cleaned_data['instrutor']
                local    = form.cleaned_data['local']

                criadas = 0
                puladas = 0
                aulas_bulk = []

                for aluno in queryset:
                    quinzenal = form.cleaned_data['frequencia'] == 'quinzenal'
                    semana_contagem = 0
                    cursor = inicio
                    semana_ref = inicio  # semana de referência para quinzenal
                    while cursor <= fim:
                        if cursor.weekday() in dias:
                            # Para quinzenal: só gera nas semanas pares contadas desde o início
                            semanas_desde_inicio = (cursor - inicio).days // 7
                            if quinzenal and semanas_desde_inicio % 2 != 0:
                                cursor += timedelta(days=1)
                                continue
                            dt = datetime.combine(cursor, horario)
                            # Evita duplicar aula exata (mesmo aluno, mesma data_hora)
                            existe = Aula.objects.filter(
                                empresa=empresa,
                                aluno=aluno,
                                data_hora=dt
                            ).exists()
                            if existe:
                                puladas += 1
                            else:
                                aulas_bulk.append(Aula(
                                    empresa=empresa,
                                    aluno=aluno,
                                    cavalo=cavalo if cavalo else None,
                                    instrutor=instrutor,
                                    data_hora=dt,
                                    local=local,
                                    tipo='NORMAL',
                                    concluida=False,
                                ))
                                criadas += 1
                        cursor += timedelta(days=1)

                Aula.objects.bulk_create(aulas_bulk)

                msg = f"✅ {criadas} aula(s) criada(s)"
                if puladas:
                    msg += f" · {puladas} ignorada(s) por conflito"
                self.message_user(request, msg, messages.SUCCESS)
                return HttpResponseRedirect(
                    reverse('admin:gateagora_aula_changelist')
                )

        # ── Passo 1: exibe o formulário ──────────────────────────────
        else:
            form = GerarAulasForm()
            form.fields['cavalo'].queryset    = Cavalo.objects.filter(empresa=empresa)
            form.fields['instrutor'].queryset = Perfil.objects.filter(
                empresa=empresa, cargo='Professor'
            )

        return TemplateResponse(request, 'admin/gerar_aulas.html', {
            'form':     form,
            'alunos':   queryset,
            'opts':     self.model._meta,
            'title':    'Gerar Aulas por Plano Semanal',
            **self.admin_site.each_context(request),
        })
    
    def save_model(self, request, obj, form, change):
        """
        Faz duas coisas que precisam acontecer juntas na MESMA chamada:
          1) Valida tamanho de foto (máx 5MB). Se passar do limite,
             restaura a foto antiga (em edição) ou deixa vazio (em criação)
             e aborta sem salvar o resto.
          2) Após salvar o Aluno, se for NOVO e não tiver login ainda,
             cria User + Perfil automaticamente. Isso evita cadastro órfão.

        Nota histórica: antes havia 2 métodos com o mesmo nome nesta classe.
        Como Python mantém só o último definido, o comportamento de criar
        login estava sendo silenciosamente perdido. Este aqui é o único.
        """
        is_novo = obj.pk is None
        foto    = request.FILES.get('foto')

        # ── Validação de tamanho da foto ─────────────────────────────
        if foto and foto.size > 5 * 1024 * 1024:
            self.message_user(
                request,
                "❌ A foto não foi salva: tamanho máximo permitido é 5MB.",
                messages.ERROR,
            )
            # Em edição, restaura a foto anterior. Em criação, fica vazia.
            if change:
                obj.foto = Aluno.objects.get(pk=obj.pk).foto
            else:
                obj.foto = None

            # Salva só o necessário — o resto dos dados do form continua válido.
            super().save_model(request, obj, form, change)
            return

        # ── Salva o Aluno normalmente ────────────────────────────────
        super().save_model(request, obj, form, change)

        # ── Cria login se ainda não houver ───────────────────────────
        # Só faz sentido para Aluno NOVO sem perfil vinculado.
        # Se o Gestor já escolheu um perfil manualmente, respeita a escolha.
        if is_novo and not obj.perfil_usuario:
            self._criar_login_para_aluno(request, obj)


@admin.register(Baia)
class BaiaAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor', 'Tratador'}
    cargos_somente_leitura = {'Veterinario'}
    list_display = ["numero", "status", "empresa"]
    list_filter = ["status"]
    search_fields = ["numero"]
    actions = [duplicar_registro]


@admin.register(Piquete)
class PiqueteAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor', 'Tratador'}
    cargos_somente_leitura = {'Veterinario'}
    list_display = ["nome", "status", "empresa"]
    list_filter = ["status"]
    actions = [duplicar_registro]

@admin.register(RacaCavalo)
class RacaCavaloAdmin(ModelAdmin):
    list_display = ["nome"]
    search_fields = ["nome"]

@admin.register(Cavalo)
class CavaloAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor', 'Veterinario', 'Tratador'}
    list_display = ["nome", "proprietario", "baia", "status_saude_colorido"]
    list_filter = ["status_saude", "categoria"]
    search_fields = ["nome", "proprietario__nome"]
    inlines = [DocumentoInline, OcorrenciaInline]

    fieldsets = (
        ("Informações Básicas", {"fields": ("nome", "foto", "proprietario", "categoria", "raca", "peso", "fator_atividade")}),
        ("Localização", {"fields": ("onde_dorme", "baia", "piquete")}),
        ("Equipamentos Padrão", {
            "fields": ("sela_padrao", "cabecada_padrao", "material_proprio"),
            "description": (
                "Estes equipamentos serão herdados automaticamente por cada nova Aula. "
                "Se o instrutor quiser trocar para uma aula específica, basta escolher "
                "outro equipamento na própria Aula (bloco 'Equipamentos Utilizados')."
            ),
        }),
        ("Saúde", {"fields": ("status_saude", "usa_ferradura", "ultima_vacina", "ultimo_vermifugo", "ultimo_ferrageamento", "ultimo_casqueamento")}),
        ("Plano Alimentar", {"fields": ("racao_tipo", "racao_qtd_manha", "racao_qtd_noite", "feno_tipo", "feno_qtd", "complemento_nutricional")}),
        ("Financeiro", {"fields": ("mensalidade_baia",)}),
    )

    @display(description="Status Saúde", label=True)
    def status_saude_colorido(self, obj):
        if not obj or not obj.status_saude:
            return "-"

        colors = {
            "Saudável": "success",
            "Alerta": "warning",
            "Doente": "danger",
            "Tratamento": "info",
            "Observacao": "amber",
        }

        status_display = obj.get_status_saude_display() or obj.status_saude
        color = colors.get(obj.status_saude, "neutral")

        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800">{}',
            color, color, status_display
        )

@admin.register(DocumentoCavalo)
class DocumentoCavaloAdmin(PermissaoPorCargoMixin, BaseCavaloAdmin):
    cargos_acesso_total = {'Gestor', 'Veterinario'}
    cargos_somente_leitura = {'Tratador'}
    list_display = ["titulo", "cavalo", "tipo", "data_validade"]
    list_filter = ["tipo","cavalo"]
    search_fields = ["titulo", "cavalo__nome"]


@admin.register(RegistroOcorrencia)
class RegistroOcorrenciaAdmin(PermissaoPorCargoMixin, BaseCavaloAdmin):
    cargos_acesso_total = {'Gestor', 'Veterinario', 'Professor'}
    cargos_somente_leitura = {'Tratador'}
    list_display = ["data", "titulo", "cavalo", "veterinario"]
    list_filter = ["data"]
    search_fields = ["titulo", "cavalo__nome", "veterinario"]
    date_hierarchy = "data"
    ordering = ["-data"]


@admin.register(Aula)
class AulaAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display    = ["data_hora", "aluno", "cavalo", "tipo", "concluida"]
    list_filter     = ["concluida", "tipo", "data_hora"]
    list_editable   = ["concluida"]
    search_fields   = ["aluno__nome", "cavalo__nome"]
    date_hierarchy  = "data_hora"
    actions         = ["marcar_como_concluida", duplicar_registro]

    # ⚠️ Se o campo local_novo AINDA existe no model, descomente a linha abaixo
    # exclude = ["local_novo"]

    fieldsets = (
        ("Quando e Quem", {
            "fields": ("empresa", "data_hora", "aluno", "cavalo", "instrutor"),
        }),
        ("Equipamentos Utilizados", {
            "fields": ("sela", "cabecada"),
            "description": (
                "Deixe em branco para usar o padrão do cavalo "
                "(configurado no Cavalo → 'Equipamentos Padrão')."
            ),
        }),
        ("Detalhes da Aula", {
            "fields": ("local", "tipo", "concluida", "relatorio_treino"),
        }),
    )

    @admin.action(description="Marcar selecionadas como concluídas")
    def marcar_como_concluida(self, request, queryset):
        queryset.update(concluida=True)


@admin.register(MovimentacaoFinanceira)
class MovimentacaoFinanceiraAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ["data", "descricao", "tipo_formatado", "valor"]
    list_filter = ["tipo", "data"]
    search_fields = ["descricao"]

    @display(description="Tipo", label=True)
    def tipo_formatado(self, obj):
        if obj.tipo == "Receita":
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">{}</span>',
                "+ Receita"
            )
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">{}</span>',
            "- Despesa"
        )


@admin.register(Plano)
class PlanoAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ["nome", "valor_mensal"]


@admin.register(Fatura)
class FaturaAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ["aluno", "data_vencimento", "total_display", "status_custom"]
    list_filter = ["status", "data_vencimento"]
    search_fields = ["aluno__nome"]
    inlines = [ItemFaturaInline]

    @display(description="Total")
    def total_display(self, obj):
        return f"R$ {obj.total:,.2f}"

    @display(description="Status", label=True)
    def status_custom(self, obj):
        colors = {"PAGO": "success", "PENDENTE": "warning", "ATRASADO": "danger"}
        color = colors.get(obj.status, "neutral")
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800">{}',
            color, color, obj.get_status_display() or obj.status
        )

    # ====================== CONTROLE DE FLUXO ======================
    def response_add(self, request, obj, post_url_continue=None):
        """Após criar fatura → abre direto para edição dela"""
        if '_addanother' in request.POST:
            return super().response_add(request, obj, post_url_continue)
        # Força abrir a fatura recém-criada para adicionar itens
        return HttpResponseRedirect(reverse('admin:gateagora_fatura_change', args=[obj.pk]))

    def response_change(self, request, obj):
        """Após salvar fatura ou itens inline → permanece na mesma fatura"""
        if '_continue' in request.POST or '_save' in request.POST:
            return HttpResponseRedirect(reverse('admin:gateagora_fatura_change', args=[obj.pk]))
        return super().response_change(request, obj)

# ItemFatura só existe via inline dentro de FaturaAdmin
# Mantido aqui apenas para o superadmin ter acesso de consulta/auditoria
class ItemFaturaAdmin(ModelAdmin):
    list_display = ["fatura", "tipo", "cavalo", "descricao", "valor", "data"]
    list_filter = ["tipo", "data"]
    search_fields = ["descricao", "fatura__aluno__nome", "cavalo__nome"]
    date_hierarchy = "data"
    ordering = ["-data"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request, 'empresa') and request.empresa:
            return qs.filter(fatura__empresa=request.empresa)
        return qs.none()

    def has_add_permission(self, request):
        return False  # nunca adiciona por aqui, só via inline da Fatura

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser  # só superadmin edita por aqui

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # só superadmin apaga por aqui

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request, 'empresa') and request.empresa:
            if db_field.name == "fatura":
                kwargs["queryset"] = Fatura.objects.filter(empresa=request.empresa)
            if db_field.name == "cavalo":
                kwargs["queryset"] = Cavalo.objects.filter(empresa=request.empresa)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor', 'Tratador'}
    inlines = [LoteEstoqueInline]
    actions = [duplicar_registro]

    list_display = (
        'nome',
        'quantidade_valida_display',
        'quantidade_vencida_display',
        'unidade',
        'status_validade_colorido',
        'dias_restantes_display',
        'status_estoque',
    )

    list_filter = ('empresa',)
    search_fields = ('nome',)
    readonly_fields = ('quantidade_valida', 'dias_para_vencer')
    fields = ('empresa', 'nome', 'unidade', 'alerta_minimo', 'consumo_diario', 'lote_economico', 'fornecedor_padrao')

    @admin.display(description="Estoque Válido")
    def quantidade_valida_display(self, obj):
        """Exibe apenas o estoque dentro do prazo — o que realmente pode ser usado."""
        qtd = obj.quantidade_valida  # deve retornar 0 quando vencido
        return f"{qtd} {obj.unidade}"

    @admin.display(description="Vencido/Descarte")
    def quantidade_vencida_display(self, obj):
        """
        Exibe quanto está perdido por vencimento.
        Fórmula: quantidade total - quantidade válida.
        Se não há data de validade ou não venceu, exibe '—'.
        """
        if obj.status_validade != 'vencido':
            return mark_safe('<span style="color:#94a3b8">—</span>')
        perda = obj.quantidade_atual - obj.quantidade_valida
        if perda <= 0:
            return mark_safe('<span style="color:#94a3b8">—</span>')
        return mark_safe(
            f'<span style="color:#ef4444;font-weight:700">⚠ {perda} {obj.unidade}</span>'
        )

    @admin.display(description="Dias Restantes")
    def dias_restantes_display(self, obj):
        if obj.status_validade == 'vencido':
            dias = obj.dias_para_vencer  # negativo ou 0
            if dias is not None and dias < 0:
                return mark_safe(f'<span style="color:#ef4444">Venceu há {abs(dias)}d</span>')
            return mark_safe('<span style="color:#ef4444">Vencido</span>')
        if obj.dias_para_vencer is None:
            return "—"
        return f"{obj.dias_para_vencer} dias"

    @admin.display(description="Validade")
    def status_validade_colorido(self, obj):
        sv = obj.status_validade
        if sv == 'vencido':
            return mark_safe('<span style="color:#ef4444;font-weight:700">VENCIDO</span>')
        elif sv == 'alerta_critico':
            dias = obj.dias_para_vencer or 0
            return mark_safe(f'<span style="color:#ef4444;font-weight:700">⚠️ {dias}d</span>')
        elif sv == 'alerta':
            dias = obj.dias_para_vencer or 0
            return mark_safe(f'<span style="color:#f59e0b;font-weight:700">⏳ {dias}d</span>')
        return mark_safe('<span style="color:#10b981;font-weight:700">✓ OK</span>')

    @admin.display(description="Status")
    def status_estoque(self, obj):
        """
        CRÍTICO se:
          - item vencido (100% da quantidade é perda), OU
          - estoque válido (não-vencido) está abaixo ou igual ao mínimo.
        """
        if obj.status_validade == 'vencido':
            return mark_safe(
                '<span style="color:#ef4444;font-weight:700" title="Produto vencido — descarte obrigatório">'
                'CRÍTICO (VENCIDO)</span>'
            )
        if obj.quantidade_valida <= obj.alerta_minimo:
            return mark_safe(
                '<span style="color:#ef4444;font-weight:700" title="Estoque válido abaixo do mínimo">'
                'CRÍTICO</span>'
            )
        return mark_safe('<span style="color:#10b981;font-weight:700">OK</span>')


@admin.register(EventoAgendaCavalo)
class EventoAgendaAdmin(BaseCavaloAdmin):
    list_display = ["cavalo", "tipo", "data_inicio"]
    list_filter = ["tipo", "cavalo"]


@admin.register(ConfigPrecoManejo)
class ConfigPrecoManejoAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    # Não estava na tabela confirmada -- assumi Gestor-only por ser
    # configuração de preço (financeiro-adjacente). Avise se for diferente.
    cargos_acesso_total = {'Gestor'}
    list_display = ["empresa", "cobrar_vacina", "valor_vacina", "cobrar_vermifugo", "valor_vermifugo", "cobrar_ferrageamento", "valor_ferrageamento", "cobrar_casqueamento", "valor_casqueamento"]
    fieldsets = (
        ("Vacinação",     {"fields": ("cobrar_vacina",        "valor_vacina")}),
        ("Vermifugação",  {"fields": ("cobrar_vermifugo",     "valor_vermifugo")}),
        ("Ferrageamento", {"fields": ("cobrar_ferrageamento", "valor_ferrageamento")}),
        ("Casqueamento",  {"fields": ("cobrar_casqueamento",  "valor_casqueamento")}),
    )


@admin.register(LoteEstoque)
class LoteEstoqueAdmin(PermissaoPorCargoMixin, BaseItemEstoqueAdmin):
    cargos_acesso_total = {'Gestor', 'Tratador'}
    list_display = (
        'item',
        'numero_lote',
        'quantidade',
        'data_validade',
        'ativo',
    )
    list_filter = ('ativo', 'data_validade')
    search_fields = ('numero_lote', 'item__nome')

# ── USER ADMIN (registrado apenas UMA vez) ──────────────────────────────────

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


class PerfilInline(TabularInline):
    """
    Inline que aparece DENTRO da página de edição do User.
    Só exibe formulário quando o User JÁ existe mas ainda não tem Perfil.
    Isso evita o erro 'After you've created a user...' — o Django não
    consegue renderizar inline durante a CRIAÇÃO (o User não tem PK ainda).
    """
    model = Perfil
    fields = ["empresa", "cargo", "telefone"]
    can_delete = False
    max_num = 1

    def get_extra(self, request, obj=None, **kwargs):
        """
        Controla quantos formulários EM BRANCO mostrar.
        - Criando User (obj=None): 0 — não mostra inline nenhum.
        - Editando User SEM perfil: 1 — mostra 1 form para o Gestor preencher.
        - Editando User COM perfil: 0 — o form já está preenchido.
        """
        if obj is not None and not hasattr(obj, 'perfil'):
            return 1
        return 0

    def has_add_permission(self, request, obj=None):
        """
        Bloqueia 'add' durante a criação do User (obj=None).
        Evita erro de IntegrityError na tabela Perfil.
        """
        if obj is None:
            return False
        return super().has_add_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "empresa":
            if not request.user.is_superuser and hasattr(request.user, 'perfil'):
                # Gestor só pode vincular à própria empresa
                kwargs["queryset"] = Empresa.objects.filter(
                    id=request.user.perfil.empresa_id
                )
                kwargs["widget"] = forms.HiddenInput()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Campo empresa fica oculto pro Gestor — precisa vir pré-preenchido,
        # senão o Django recusa salvar (campo obrigatório vazio).
        if not request.user.is_superuser and hasattr(request.user, 'perfil'):
            formset.form.base_fields['empresa'].initial = request.user.perfil.empresa_id
        return formset


class CustomUserAdmin(BaseUserAdmin, UnfoldModelAdmin):
    inlines = [PerfilInline]
    list_display = ("username", "email", "get_telefone", "is_active", "is_staff")
    search_fields = ("username", "email")
    ordering = ("username",)
    actions = ["redefinir_senha"]

    # ✅ ESTE É O SEGREDO PARA MATAR O ERRO
    # "After you've created a user, you'll be able to edit more user options."
    #
    # Este `add_fieldsets` define QUAIS CAMPOS aparecem na TELA DE CRIAÇÃO.
    # Como só listamos username + senha, o Django não tenta renderizar o
    # inline de Perfil durante a criação — só depois que o User existe.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )

    @admin.action(description="🔑 Redefinir senha deste usuário")
    def redefinir_senha(self, request, queryset):
        from django import forms
        from django.template.response import TemplateResponse

        if queryset.count() != 1:
            self.message_user(request, "Selecione exatamente 1 usuário por vez.", level=messages.WARNING)
            return

        alvo = queryset.first()

        # Gestor só pode redefinir senha de gente da própria empresa
        if not request.user.is_superuser:
            perfil_alvo = getattr(alvo, 'perfil', None)
            perfil_seu = getattr(request.user, 'perfil', None)
            if not perfil_alvo or not perfil_seu or perfil_alvo.empresa_id != perfil_seu.empresa_id:
                self.message_user(request, "Você só pode redefinir senha de usuários da sua própria hípica.", level=messages.ERROR)
                return

        class RedefinirSenhaForm(forms.Form):
            nova_senha = forms.CharField(label="Nova senha", widget=forms.TextInput)

        if 'aplicar' in request.POST:
            form = RedefinirSenhaForm(request.POST)
            if form.is_valid():
                alvo.set_password(form.cleaned_data['nova_senha'])
                alvo.save()
                self.message_user(
                    request,
                    f"✅ Senha de '{alvo.username}' redefinida com sucesso."
                )
                return
        else:
            form = RedefinirSenhaForm()

        return TemplateResponse(
            request,
            "admin/redefinir_senha.html",
            {
                "form": form,
                "usuario": alvo,
                "queryset": queryset,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )

    def save_model(self, request, obj, form, change):
        """
        Após salvar o User:
          - Se acabou de ser CRIADO (change=False) e ainda não tiver Perfil,
            cria um Perfil mínimo com cargo 'Aluno' (o mais seguro).
          - Empresa usada: a do Gestor logado. Se for superuser sem perfil,
            cai na primeira Empresa do banco.
        O Gestor pode trocar cargo e telefone depois, editando o User
        (o inline de Perfil aparece automaticamente na tela de edição).
        """
        super().save_model(request, obj, form, change)

        if not change and not hasattr(obj, 'perfil'):
            empresa = None
            if not request.user.is_superuser and hasattr(request.user, 'perfil'):
                empresa = request.user.perfil.empresa
            else:
                empresa = Empresa.objects.first()

            if empresa:
                Perfil.objects.create(
                    user    = obj,
                    empresa = empresa,
                    cargo   = 'Aluno',
                )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Gestor vê apenas usuários da própria empresa
        if hasattr(request.user, 'perfil') and request.user.perfil.empresa:
            return qs.filter(perfil__empresa=request.user.perfil.empresa)
        return qs.none()

    def has_add_permission(self, request):
        # Superuser sempre pode. Gestor pode cadastrar usuários da própria empresa.
        if request.user.is_superuser:
            return True
        return hasattr(request.user, 'perfil') and request.user.perfil.cargo == 'Gestor'

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, 'perfil') or request.user.perfil.cargo != 'Gestor':
            return False
        if obj is None:
            return True  # necessário para o Django mostrar a lista/tela
        # Gestor só edita usuários da própria empresa
        obj_perfil = getattr(obj, 'perfil', None)
        return bool(obj_perfil) and obj_perfil.empresa_id == request.user.perfil.empresa_id

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return self.fieldsets
        # Gestor não pode ver nem alterar is_superuser, groups ou user_permissions
        # -- evita que um Gestor se autopromova (ou promova outro usuário) a superuser.
        return (
            (None, {'fields': ('username', 'password')}),
            ('Informações pessoais', {
                'fields': ('first_name', 'last_name', 'email')
            }),
            ('Permissões', {
                'fields': ('is_active', 'is_staff')
            }),
        )

    def get_telefone(self, obj):
        perfil = getattr(obj, 'perfil', None)
        return perfil.telefone if perfil else "-"
    get_telefone.short_description = "Telefone"

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações pessoais', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Permissões', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            )
        }),
    )

@admin.register(Fornecedor)
class FornecedorAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ("nome", "empresa", "telefone", "email", "ativo", "get_whatsapp_link")
    list_filter = ("ativo", "empresa")
    search_fields = ("nome", "telefone", "email")
    list_editable = ("ativo",)

    fields = (
        'empresa',
        'nome',
        'telefone',
        'email',
        'observacoes',
        'ativo',
    )

    @admin.display(description="WhatsApp")
    def get_whatsapp_link(self, obj):
        numero = obj.telefone_limpo
        if not numero:
            return "-"
        return format_html(
            '<a href="https://wa.me/55{}" target="_blank">📲 Abrir</a>',
            numero,
        )

admin.site.register(User, CustomUserAdmin)

@admin.register(LocalAula)
class LocalAulaAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ["nome", "ativo"]
    list_editable = ["ativo"]
    search_fields = ["nome"]


@admin.register(ChecklistItem)
class ChecklistItemAdmin(PermissaoPorCargoMixin, BaseEmpresaAdmin):
    cargos_acesso_total = {'Gestor'}
    list_display = ["descricao", "tipo", "ordem", "ativo"]
    list_editable = ["tipo", "ordem", "ativo"]
    list_filter = ["tipo", "ativo"]
    search_fields = ["descricao"]