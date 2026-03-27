# -*- coding: utf-8 -*-
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from .models import (
    Empresa, Perfil, Aluno, Baia, Piquete, Cavalo,
    Aula, ItemEstoque, MovimentacaoFinanceira,
    DocumentoCavalo, RegistroOcorrencia,
    Plano, Fatura, EventoAgendaCavalo, ConfigPrazoManejo
)


# ── BASES MULTI-EMPRESA (AGORA CONSISTENTES) ─────────────────────────────────

class BaseEmpresaAdmin(ModelAdmin):
    """
    Filtra o QuerySet usando o request.empresa definido no middleware.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # Se for superuser, vê tudo
        if request.user.is_superuser:
            return qs
            
        # Se tiver empresa no request, filtra. Se não tiver, não vê nada (segurança).
        if hasattr(request, 'empresa') and request.empresa:
            return qs.filter(empresa=request.empresa)
            
        return qs.none()

    def save_model(self, request, obj, form, change):
        # Atribui a empresa do usuário ao salvar um novo registro
        if not change and not request.user.is_superuser:
            if hasattr(request, 'empresa') and request.empresa:
                obj.empresa = request.empresa
        super().save_model(request, obj, form, change)


class BaseCavaloAdmin(ModelAdmin):
    """Usado para modelos que têm FK para Cavalo (ex: Documento, Ocorrência, Evento)"""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(cavalo__empresa=request.user.perfil.empresa)


# ── INLINES ───────────────────────────────────────────────────────────────────

class DocumentoInline(TabularInline):
    model = DocumentoCavalo
    extra = 1
    tab = True


class OcorrenciaInline(TabularInline):
    model = RegistroOcorrencia
    extra = 1
    tab = True
    fields = ['data', 'titulo', 'descricao', 'veterinario']


# ── ADMINS (TODOS CORRIGIDOS) ────────────────────────────────────────────────

@admin.register(Empresa)
class EmpresaAdmin(ModelAdmin):
    list_display = ["nome", "slug", "cidade", "cnpj"]
    search_fields = ["nome", "cnpj"]
    prepopulated_fields = {"slug": ("nome",)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(id=request.user.perfil.empresa.id)
        return qs


@admin.register(Perfil)
class PerfilAdmin(ModelAdmin):
    list_display = ["user", "empresa", "cargo"]
    list_filter = ["empresa", "cargo"]
    search_fields = ["user__username", "user__first_name"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(empresa=request.user.perfil.empresa)
        return qs


@admin.register(Aluno)
class AlunoAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "telefone", "ativo", "valor_aula_formatado"]
    list_editable = ["ativo"]
    list_filter = ["ativo", "empresa"]
    search_fields = ["nome", "telefone"]

    @display(description="Valor Aula", header=True)
    def valor_aula_formatado(self, obj):
        return f"R$ {obj.valor_aula}"


@admin.register(Baia)
class BaiaAdmin(BaseEmpresaAdmin):
    list_display = ["numero", "status", "empresa"]
    list_filter = ["status", "empresa"]
    search_fields = ["numero"]


@admin.register(Piquete)
class PiqueteAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "status", "empresa"]
    list_filter = ["status", "empresa"]


@admin.register(Cavalo)
class CavaloAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "proprietario", "baia", "status_saude_colorido"]
    list_filter = ["status_saude", "categoria", "empresa"]
    search_fields = ["nome", "proprietario__nome"]
    inlines = [DocumentoInline, OcorrenciaInline]

    fieldsets = (
        ("Informações Básicas", {"fields": ("nome", "proprietario", "categoria", "raca", "peso", "fator_atividade")}),
        ("Localização", {"fields": ("onde_dorme", "baia", "piquete")}),
        ("Equipamentos", {"fields": ("tipo_sela", "tipo_cabecada", "material_proprio")}),
        ("Saúde", {"fields": ("status_saude", "ultima_vacina", "ultimo_vermifugo", "ultimo_ferrageamento", "ultimo_casqueamento")}),
        ("Plano Alimentar", {"fields": ("racao_tipo", "racao_qtd_manha", "racao_qtd_noite", "feno_tipo", "feno_qtd", "complemento_nutricional")}),
        ("Financeiro", {"fields": ("mensalidade_baia",)}),
    )

    @display(description="Status Saúde", label=True)
    def status_saude_colorido(self, obj):
        colors = {"Saudável": "success", "Alerta": "warning", "Doente": "danger", "Tratamento": "info"}
        return obj.status_saude, colors.get(obj.status_saude, "neutral")


@admin.register(DocumentoCavalo)
class DocumentoCavaloAdmin(BaseCavaloAdmin):
    list_display = ["titulo", "cavalo", "tipo", "data_validade"]
    list_filter = ["tipo", "cavalo__empresa"]
    search_fields = ["titulo", "cavalo__nome"]


@admin.register(RegistroOcorrencia)
class RegistroOcorrenciaAdmin(BaseCavaloAdmin):
    list_display = ["data", "titulo", "cavalo", "veterinario"]
    list_filter = ["data", "cavalo__empresa"]
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


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "quantidade_atual", "alerta_minimo", "unidade", "status_estoque"]
    list_filter = ["empresa"]
    search_fields = ["nome"]

    @display(description="Status", label=True)
    def status_estoque(self, obj):
        return ("CRÍTICO", "danger") if obj.quantidade_atual <= obj.alerta_minimo else ("OK", "success")


@admin.register(MovimentacaoFinanceira)
class MovimentacaoFinanceiraAdmin(BaseEmpresaAdmin):
    list_display = ["data", "descricao", "tipo_formatado", "valor"]
    list_filter = ["tipo", "data"]
    search_fields = ["descricao"]

    @display(description="Tipo", label=True)
    def tipo_formatado(self, obj):
        color = "success" if obj.tipo == "Receita" else "danger"
        return obj.tipo, color


@admin.register(Plano)
class PlanoAdmin(BaseEmpresaAdmin):
    list_display = ["nome", "valor_mensal"]


@admin.register(Fatura)
class FaturaAdmin(BaseEmpresaAdmin):
    list_display = ["aluno", "data_vencimento", "valor", "status_custom"]
    list_filter = ["status", "data_vencimento"]
    search_fields = ["aluno__nome"]

    @display(description="Status", label=True)
    def status_custom(self, obj):
        colors = {"PAGO": "success", "PENDENTE": "warning", "ATRASADO": "danger"}
        return obj.status, colors.get(obj.status, "neutral")


@admin.register(EventoAgendaCavalo)
class EventoAgendaAdmin(BaseCavaloAdmin):          # ← AGORA CORRIGIDO
    list_display = ["cavalo", "tipo", "data_inicio"]
    list_filter = ["tipo", "cavalo"]


@admin.register(ConfigPrazoManejo)
class ConfigPrazoManejoAdmin(BaseEmpresaAdmin):
    list_display = ["empresa", "prazo_vacina", "prazo_vermifugo", "prazo_ferrageamento", "prazo_casqueamento"]
    list_filter = ["empresa"]