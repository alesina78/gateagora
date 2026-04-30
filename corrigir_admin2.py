# Rode com: python corrigir_admin2.py
# Na pasta C:\_GestaoHipica\GATEAGORA

with open('gateagora/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'class ItemEstoqueAdmin(ModelAdmin):'
new = 'class ItemEstoqueAdmin(BaseEmpresaAdmin):'

if old in content:
    with open('gateagora/admin.py', 'w', encoding='utf-8') as f:
        f.write(content.replace(old, new, 1))
    print("OK — ItemEstoqueAdmin corrigido")
else:
    print("ERRO — trecho nao encontrado")
