from django.core.management.base import BaseCommand
import random
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from gateagora.models import Empresa, Perfil, Aluno, Cavalo, MovimentacaoFinanceira

class Command(BaseCommand):
    help = 'Popula o banco de dados de produção'

    def handle(self, *args, **options):
        self.stdout.write("Limpando dados...")
        Empresa.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

        e1 = Empresa.objects.create(nome="Hípica Porto Alegre", slug="hipica-poa")
        admin = User.objects.get(username='alessandro_admin')
        Perfil.objects.get_or_create(user=admin, empresa=e1, tipo='Gestor')

        aluno_h = Aluno.objects.create(nome="PROPRIEDADE HÍPICA", empresa=e1, ativo=True)
        alunos = [Aluno.objects.create(nome=f"Aluno {i}", empresa=e1, ativo=True) for i in range(1, 11)]
        
        hoje = date.today()
        for i in range(25):
            dono = aluno_h if i < 12 else random.choice(alunos)
            Cavalo.objects.create(
                nome=f"Cavalo {i+1}", empresa=e1, proprietario=dono, raca="Crioulo",
                ultimo_casqueamento=hoje - timedelta(days=10),
                ultimo_vermifugo=hoje - timedelta(days=15)
            )

        for m in [1, 2, 3]:
            MovimentacaoFinanceira.objects.create(
                empresa=e1, tipo='Receita', valor=Decimal("15000.00"), 
                descricao="Mensalidades", data=date(2026, m, 10)
            )

        self.stdout.write(self.style.SUCCESS('=== DADOS CARREGADOS COM SUCESSO! ==='))