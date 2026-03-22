import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='Admin').exists():
    User.objects.create_superuser('Admin', 'giordano.dba@gmail.com', 'Gate4@2026!')
    print('Superusuario Admin criado com sucesso!')
else:
    print('Usuario Admin ja existe!')
