import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from gateagora.models import Empresa, Perfil, Aluno, Cavalo, Aula, MovimentacaoFinanceira

class Command(BaseCommand):
    help = 'Popula o sistema com 32 cavalos e lógica real de hípica para duas empresas'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- Iniciando Limpeza Geral ---")
        MovimentacaoFinanceira.objects.all().delete()
        Aula.objects.all().delete()
        Cavalo.objects.all().delete()
        Perfil.objects.all().delete()
        Aluno.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()
        Empresa.objects.all().delete()

        # 1. CRIAR USUÁRIOS
        self.stdout.write("--- Criando Usuários ---")
        def criar_user(username, email, is_staff=False):
            u, created = User.objects.get_or_create(username=username, defaults={'email': email})
            u.set_password('Gate2024')
            u.is_staff = is_staff
            u.save()
            return u

        u_ale = criar_user('alessandro_admin', 'alessandro@gate4.com.py', True)
        u_gestor1 = criar_user('gestor_hipica1', 'gestor1@hipica.com')
        u_admin = criar_user('Admin', 'gateagora@gmail.com', True)

        # 2. CRIAR EMPRESAS
        self.stdout.write("--- Criando Empresas ---")
        empresas = [
            Empresa.objects.create(nome="Hípica Porto Alegre", slug="hipica-poa"),
            Empresa.objects.create(nome="Haras da Serra", slug="haras-serra")
        ]

        # Vincular Alessandro a ambas (usando a primeira como padrão)
        Perfil.objects.create(user=u_ale, empresa=empresas[0], cargo='Gestor')
        Perfil.objects.create(user=u_gestor1, empresa=empresas[0], cargo='Gestor')
        Perfil.objects.create(user=u_admin, empresa=empresas[1], cargo='Gestor')

        hoje = date.today()
        celular = "+5551991387872"

        for emp in empresas:
            self.stdout.write(f"Populando: {emp.nome}")
            
            # 3. ALUNOS E PROPRIETÁRIOS
            # Criar Aluno "Fantasma" para cavalos próprios
            dono_hipica = Aluno.objects.create(nome=f"PROPRIEDADE {emp.nome.upper()}", empresa=emp, ativo=True, telefone=celular)
            
            # 15 Alunos (5 são proprietários, 2 têm material próprio)
            nomes_humanos = ["Suzana", "Ricardo", "Ana Cláudia", "Beto", "Helena", "Marcos", "Julia", "Enzo", "Carla", "Pedro", "Sofia", "Luiz", "Marta", "Fabio", "Teresa"]
            alunos = []
            for i, nome in enumerate(nomes_humanos):
                tem_material = True if i < 2 else False
                alunos.append(Aluno.objects.create(nome=nome, empresa=emp, ativo=True, telefone=celular))

            # 4. CAVALOS (32 total: 17 Próprios, 15 Hotelaria)
            nomes_cavalos = ["Zenda", "Aromah", "Jade", "Pampa", "Trovão", "Dourado", "Relâmpago", "Estrela", "Luna", "Apolo", "Faraó", "Ginga", "Hércules", "Índio", "Jasmim", "Kaiser", "Lord", "Mel", "Nobre", "Orion", "Pérola", "Quartzo", "Raio", "Sultão", "Titan", "Uranio", "Vento", "Xerife", "Zorro", "Brisa", "Cometa", "Dama"]
            
            racas = ["Crioulo", "Lusitano", "Quarto de Milha", "Hípico"]
            
            for i in range(32):
                is_proprio = i < 17
                dono = dono_hipica if is_proprio else random.choice(alunos[:5])
                
                # Lógica de datas críticas pedida
                c_date = hoje - timedelta(days=random.randint(10, 45))
                v_date = hoje - timedelta(days=random.randint(10, 60))
                
                # Ajustar 2 cavalos para casqueio próximo (3 dias)
                if i < 2: c_date = hoje - timedelta(days=42) # Se ciclo é 45, faltam 3
                # Ajustar 4 para vermífugo próximo (2 dias)
                if 2 <= i < 6: v_date = hoje - timedelta(days=88) # Se ciclo é 90, faltam 2
                
                Cavalo.objects.create(
                    nome=nomes_cavalos[i],
                    empresa=emp,
                    proprietario=dono,
                    raca=random.choice(racas),
                    ultimo_casqueamento=c_date,
                    ultimo_vermifugo=v_date
                    # Removi a linha do documento_vencimento aqui
                )

            # 5. FINANCEIRO (01/11/2025 até 30/04/2026)
            data_ini = date(2025, 11, 1)
            data_fim = date(2026, 4, 30)
            curr = data_ini
            while curr <= data_fim:
                if curr.day == 10: # Receitas no dia 10
                    MovimentacaoFinanceira.objects.create(
                        empresa=emp, tipo='Receita', descricao="Mensalidades e Hotelaria",
                        valor=Decimal(random.randint(15000, 22000)), data=curr
                    )
                if curr.day == 15: # Despesas no dia 15
                    MovimentacaoFinanceira.objects.create(
                        empresa=emp, tipo='Despesa', descricao="Ração e Ferrageamento",
                        valor=Decimal(random.randint(6000, 9000)), data=curr
                    )
                curr += timedelta(days=1)

            # 6. TREINOS/AULAS (Segunda a Sábado)
            curr = data_ini
            cavalos_emp = Cavalo.objects.filter(empresa=emp)
            while curr <= hoje:
                if curr.weekday() < 6: # 0-5 é Seg-Sab
                    for _ in range(3): # 3 treinos por dia
                        aula_dt = timezone.make_aware(datetime.combine(curr, datetime.min.time() + timedelta(hours=random.randint(8, 17))))
                        Aula.objects.create(
                            empresa=emp,
                            aluno=random.choice(alunos),
                            cavalo=random.choice(cavalos_emp),
                            data_hora=aula_dt,
                            realizada=True
                        )
                curr += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS("=== BANCO POPULADO COM SUCESSO! ==="))