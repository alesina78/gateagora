# -*- coding: utf-8 -*-
"""Admin do Gate 4"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django import forms
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe

from datetime import date

from unfold.admin import ModelAdmin, TabularInline
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from .models import (
    Aluno,
    Aula,
    Baia,
    Cavalo,
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
)


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

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        # gestor só edita o próprio perfil
        if obj and obj.user == request.user:
            return True
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
class AlunoAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "telefone", "ativo", "valor_aula_formatado", "usuario_login"]
    list_editable = ["ativo"]
    list_filter = ["ativo"]
    search_fields = ["nome", "telefone", "perfil_usuario__user__username"]
    actions = ["criar_login_aluno"]

    fields = [
        'empresa',
        'perfil_usuario',
        'nome',
        'telefone',
        'foto',
        'ativo',
        'valor_aula',
        'plano',
    ]

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
    def criar_login_aluno(self, request, queryset):
        criados = 0
        for aluno in queryset:
            if aluno.perfil_usuario:
                messages.warning(request, f"{aluno.nome} já possui login.")
                continue

            base_username = aluno.nome.lower().replace(" ", ".").replace("ç", "c").replace("ã", "a").replace("ê", "e").replace("é", "e").replace("á", "a").replace("ó", "o").replace("ú", "u").replace("í", "i")[:25]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            senha_temp = (aluno.telefone[-4:] if aluno.telefone and len(aluno.telefone) >= 4 else "1234") + "aluno"

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

            criados += 1
            messages.success(
                request,
                f"✅ Login criado para {aluno.nome} — "
                f"Usuário: {username} | Senha: {senha_temp}"
            )

        if criados == 0:
            messages.warning(request, "Nenhum login foi criado.")


@admin.register(Baia)
class BaiaAdmin(BaseEmpresaAdmin):
    list_display = ["numero", "status", "empresa"]
    list_filter = ["status"]
    search_fields = ["numero"]


@admin.register(Piquete)
class PiqueteAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "status", "empresa"]
    list_filter = ["status"]


@admin.register(Cavalo)
class CavaloAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "proprietario", "baia", "status_saude_colorido"]
    list_filter = ["status_saude", "categoria"]
    search_fields = ["nome", "proprietario__nome"]
    inlines = [DocumentoInline, OcorrenciaInline]

    fieldsets = (
        ("Informações Básicas", {"fields": ("nome", "proprietario", "categoria", "raca", "peso", "fator_atividade")}),
        ("Localização", {"fields": ("onde_dorme", "baia", "piquete")}),
        ("Equipamentos", {"fields": ("tipo_sela", "tipo_cabecada", "material_proprio")}),
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
class DocumentoCavaloAdmin(BaseCavaloAdmin):
    list_display = ["titulo", "cavalo", "tipo", "data_validade"]
    list_filter = ["tipo","cavalo"]
    search_fields = ["titulo", "cavalo__nome"]


@admin.register(RegistroOcorrencia)
class RegistroOcorrenciaAdmin(BaseCavaloAdmin):
    list_display = ["data", "titulo", "cavalo", "veterinario"]
    list_filter = ["data"]
    search_fields = ["titulo", "cavalo__nome", "veterinario"]
    date_hierarchy = "data"
    ordering = ["-data"]


@admin.register(Aula)
class AulaAdmin(BaseEmpresaAdmin):
    list_display = ["data_hora", "aluno", "cavalo", "tipo", "concluida"]
    list_filter = ["concluida", "tipo", "data_hora"]
    list_editable = ["concluida"]
    search_fields = ["aluno__nome", "cavalo__nome"]
    date_hierarchy = "data_hora"
    actions = ["marcar_como_concluida"]

    @admin.action(description="Marcar selecionadas como concluídas")
    def marcar_como_concluida(self, request, queryset):
        queryset.update(concluida=True)


@admin.register(MovimentacaoFinanceira)
class MovimentacaoFinanceiraAdmin(BaseEmpresaAdmin):
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
class PlanoAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "valor_mensal"]


@admin.register(Fatura)
class FaturaAdmin(BaseEmpresaAdmin):
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
class ItemEstoqueAdmin(BaseEmpresaAdmin):
    inlines = [LoteEstoqueInline]

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
class ConfigPrecoManejoAdmin(BaseEmpresaAdmin):
    list_display = ["empresa", "cobrar_vacina", "valor_vacina", "cobrar_vermifugo", "valor_vermifugo", "cobrar_ferrageamento", "valor_ferrageamento", "cobrar_casqueamento", "valor_casqueamento"]
    fieldsets = (
        ("Vacinação",     {"fields": ("cobrar_vacina",        "valor_vacina")}),
        ("Vermifugação",  {"fields": ("cobrar_vermifugo",     "valor_vermifugo")}),
        ("Ferrageamento", {"fields": ("cobrar_ferrageamento", "valor_ferrageamento")}),
        ("Casqueamento",  {"fields": ("cobrar_casqueamento",  "valor_casqueamento")}),
    )


@admin.register(LoteEstoque)
class LoteEstoqueAdmin(ModelAdmin):
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
    model = Perfil
    fields = ["empresa", "cargo", "telefone"]
    can_delete = False
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "empresa":
            if not request.user.is_superuser and hasattr(request.user, 'perfil'):
                # Gestor só pode vincular à própria empresa
                kwargs["queryset"] = Empresa.objects.filter(
                    id=request.user.perfil.empresa_id
                )
                kwargs["widget"] = forms.HiddenInput()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CustomUserAdmin(BaseUserAdmin, UnfoldModelAdmin):
    inlines = [PerfilInline]
    list_display = ("username", "email", "get_telefone", "is_active", "is_staff")
    search_fields = ("username", "email")
    ordering = ("username",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Gestor vê apenas usuários da própria empresa
        if hasattr(request.user, 'perfil') and request.user.perfil.empresa:
            return qs.filter(perfil__empresa=request.user.perfil.empresa)
        return qs.none()

    def has_add_permission(self, request):
        # Apenas superuser cria usuários pelo admin
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

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


admin.site.register(User, CustomUserAdmin)