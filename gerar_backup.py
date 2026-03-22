import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core import serializers
from django.apps import apps

# Modelos para excluir
EXCLUIR = ['contenttypes', 'auth.permission', 'admin.logentry', 'sessions.session']

todos_objetos = []
for model in apps.get_models():
    label = f"{model._meta.app_label}.{model._meta.model_name}"
    if any(label.startswith(ex) for ex in EXCLUIR):
        continue
    try:
        objetos = model.objects.all()
        if objetos.exists():
            todos_objetos.extend(objetos)
            print(f"OK: {label} ({objetos.count()} registros)")
    except Exception as e:
        print(f"SKIP: {label} - {e}")

data = serializers.serialize('json', todos_objetos, indent=2, use_natural_foreign_keys=True, use_natural_primary_keys=True)

with open('backup_dados.json', 'w', encoding='utf-8') as f:
    f.write(data)

print(f"\nBackup salvo em backup_dados.json ({len(todos_objetos)} objetos)")
