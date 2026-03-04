# -*- coding: utf-8 -*-
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from .models import (
    Empresa, Perfil, Aluno, Baia, Piquete, Cavalo, 
    Aula, ItemEstoque, MovimentacaoFinanceira, DocumentoCavalo
)

# --- BASE CLASS PARA SEGURANÇA MULTI-EMPRESA ---

class BaseMultiEmpresaAdmin(ModelAdmin):
    """
    Garante que usuários vejam apenas dados da sua própria empresa.
    Superusuários continuam tendo acesso total.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(empresa=request.user.perfil.empresa)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not change:
            obj.empresa = request.user.perfil.empresa
        super().save_model(request, obj, form, change)

# --- INLINES ---

class DocumentoInline(TabularInline):
    model = DocumentoCavalo
    extra = 1
    tab = True  # Organiza em abas no Unfold

# --- ADMINS ---

@admin.register(Empresa)
class EmpresaAdmin(ModelAdmin):
    list_display = ["nome", "slug", "cidade", "cnpj"]
    search_fields = ["nome", "cnpj"]
    prepopulated_fields = {"slug": ("nome",)}

@admin.register(Perfil)
class PerfilAdmin(ModelAdmin):
    list_display = ["user", "empresa", "cargo"]
    list_filter = ["empresa", "cargo"]
    search_fields = ["user__username", "user__first_name"]

@admin.register(Aluno)
class AlunoAdmin(BaseMultiEmpresaAdmin):
    list_display = ["nome", "telefone", "ativo", "valor_aula_formatado"]
    list_editable = ["ativo"]
    list_filter = ["ativo", "empresa"]
    search_fields = ["nome", "telefone"]

    @display(description="Valor Aula", header=True)
    def valor_aula_formatado(self, obj):
        # Unfold header/label exige retorno de lista ou tupla
        return [f"R$ {obj.valor_aula}"]

@admin.register(Baia)
class BaiaAdmin(BaseMultiEmpresaAdmin):
    list_display = ["numero", "status", "empresa"]
    list_filter = ["status", "empresa"]
    search_fields = ["numero"]

@admin.register(Piquete)
class PiqueteAdmin(BaseMultiEmpresaAdmin):
    list_display = ["nome", "status", "empresa"]
    list_filter = ["status", "empresa"]

@admin.register(Cavalo)
class CavaloAdmin(BaseMultiEmpresaAdmin):
    list_display = ["nome", "proprietario", "baia", "status_saude_colorido"]
    list_filter = ["status_saude", "categoria", "empresa"]
    search_fields = ["nome", "proprietario__nome"]
    inlines = [DocumentoInline]
    
    fieldsets = (
        ("Informações Básicas", {"fields": ("nome", "proprietario", "categoria")}),
        ("Localização", {"fields": ("baia", "piquete")}),
        ("Saúde e Nutrição", {"fields": ("status_saude", "racao_tipo", "racao_qtd_manha", "racao_qtd_noite")}),
        ("Histórico Sanitário", {"fields": ("ultima_vacina", "ultimo_vermifugo")}),
    )

    @display(description="Status Saúde", label=True)
    def status_saude_colorido(self, obj):
        colors = {
            "Saudável": "success",
            "Observação": "warning",
            "Doente": "danger",
            "Tratamento": "info",
        }
        # Retorna obrigatoriamente uma tupla (valor, cor)
        return obj.status_saude, colors.get(obj.status_saude, "neutral")

@admin.register(DocumentoCavalo)
class DocumentoCavaloAdmin(BaseMultiEmpresaAdmin):
    list_display = ["titulo", "cavalo", "data_validade"]
    list_filter = ["data_validade", "cavalo__empresa"]
    search_fields = ["titulo", "cavalo__nome"]

@admin.register(Aula)
class AulaAdmin(BaseMultiEmpresaAdmin):
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
class ItemEstoqueAdmin(BaseMultiEmpresaAdmin):
    list_display = ["nome", "quantidade_atual", "unidade", "status_estoque"]
    list_filter = ["empresa"]
    search_fields = ["nome"]

    @display(description="Status", label=True)
    def status_estoque(self, obj):
        if obj.quantidade_atual <= obj.alerta_minimo:
            return "CRÍTICO", "danger"
        return "OK", "success"

@admin.register(MovimentacaoFinanceira)
class MovimentacaoFinanceiraAdmin(BaseMultiEmpresaAdmin):
    list_display = ["data", "descricao", "tipo_formatado", "valor"]
    list_filter = ["tipo", "data"]
    search_fields = ["descricao"]
    date_hierarchy = "data"

    @display(description="Tipo", label=True)
    def tipo_formatado(self, obj):
        color = "success" if obj.tipo == "Receita" else "danger"
        return obj.tipo, color