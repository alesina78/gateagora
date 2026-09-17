# Rode com: python corrigir_admin.py
# Na pasta C:\_GestaoHipica\GATEAGORA

with open('gateagora/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''class PerfilInline(TabularInline):
    model = Perfil
    fields = ["empresa", "cargo", "telefone"]
    can_delete = False
    extra = 0'''

new = '''class PerfilInline(TabularInline):
    model = Perfil
    fields = ["empresa", "cargo", "telefone"]
    can_delete = False
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "empresa":
            if not request.user.is_superuser and hasattr(request.user, "perfil"):
                kwargs["queryset"] = Empresa.objects.filter(
                    id=request.user.perfil.empresa_id
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)'''

if old in content:
    with open('gateagora/admin.py', 'w', encoding='utf-8') as f:
        f.write(content.replace(old, new, 1))
    print("OK — admin.py corrigido")
else:
    print("ERRO — trecho não encontrado")
