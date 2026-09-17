import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User
from gateagora.models import (
    Empresa, Perfil, Aluno, Cavalo, Baia, Piquete, 
    Aula, ItemEstoque, MovimentacaoFinanceira
)

def run():
    print("--- Iniciando Limpeza de Dados ---")
    MovimentacaoFinanceira.objects.all().delete()
    Aula.objects.all().delete()
    Cavalo.objects.all().delete()
    Aluno.objects.all().delete()
    Baia.objects.all().delete()
    Piquete.objects.all().delete()
    Perfil.objects.all().delete()
    User.objects.exclude(is_superuser=True).delete()
    Empresa.objects.all().delete()

    # --- 1. EMPRESAS ---
    e1 = Empresa.objects.create(nome="Hípica Porto Alegre", slug="hipica-poa", cidade="Porto Alegre")
    e2 = Empresa.objects.create(nome="Centro Equestre Guaíba", slug="ce-guaiba", cidade="Guaíba")
    empresas = [e1, e2]

    # --- 2. USUÁRIOS ---
    # Admin (já deve existir, mas garantimos os gestores)
    u1 = User.objects.create_user('gestor_hipica1', 'gateagora@gmail.com', 'Teste123')
    Perfil.objects.create(user=u1, empresa=e1, tipo='Gestor')
    
    u2 = User.objects.create_user('alessandro_admin', 'alessandro@exemplo.com', 'Gate2024')
    Perfil.objects.create(user=u2, empresa=e1, tipo='Gestor')

    # --- 3. POPULANDO CADA EMPRESA ---
    for emp in empresas:
        print(f"Populando: {emp.nome}")
        
        # Aluno "Hípica" para cavalos próprios
        aluno_hipica = Aluno.objects.create(nome=f"PROPRIEDADE {emp.nome.upper()}", empresa=emp, ativo=True, telefone="+5551991387872")
        
        # Criar Baias e Piquetes
        baias = [Baia.objects.create(nome=f"Baia {i}", empresa=emp) for i in range(1, 21)]
        piquetes = [Piquete.objects.create(nome=f"Piquete {i}", empresa=emp) for i in range(1, 5)]

        # Criar Alunos (15 no total, 5 são donos)
        nomes_alunos = ["Ricardo", "Beatriz", "Carlos", "Fernanda", "Gabriel", "Helena", "Igor", "Julia", "Kevin", "Larissa", "Mauro", "Nádia", "Otávio", "Paula", "Robson"]
        alunos_obj = []
        for i, nome in enumerate(nomes_alunos):
            # 2 primeiros têm material próprio
            tem_material = True if i < 2 else False
            alunos_obj.append(Aluno.objects.create(
                nome=nome, 
                empresa=emp, 
                telefone="+5551991387872",
                ativo=True
            ))

        # Criar Cavalos (32 total: 17 próprios, 15 hotelaria)
        nomes_cavalos = ["Zenda", "Aromah", "Jade", "Trovao", "Pérola", "Netuno", "Luna", "Apolo", "Fênix", "Shiva", "Titan", "Vênus", "Bambam", "Dante", "Eclipse", "Gaya", "Hera", "Indy", "Joker", "Kira", "Lord", "Maya", "Nero", "Odin", "Paco", "Quartz", "Runa", "Saga", "Thor", "Urano", "Vick", "Zorro"]
        
        hoje = date.today()
        cavalos_obj = []
        for i, nome in enumerate(nomes_cavalos):
            is_proprio = i < 17
            dono = aluno_hipica if is_proprio else alunos_obj[i % 5] # Distribui entre os 5 alunos-donos
            
            # Alertas de Casqueio (2 cavalos nos próximos 3 dias)
            data_casq = hoje + timedelta(days=random.randint(1, 3)) if i < 2 else hoje - timedelta(days=random.randint(20, 40))
            # Alertas de Vermífugo (4 cavalos nos próximos 2 dias)
            data_vermi = hoje + timedelta(days=random.randint(1, 2)) if 2 <= i < 6 else hoje - timedelta(days=random.randint(30, 60))

            cav = Cavalo.objects.create(
                nome=nome,
                empresa=emp,
                proprietario=dono,
                baia=baias[i % len(baias)] if i < 20 else None,
                piquete=None if i < 20 else piquetes[i % len(piquetes)],
                raca="Crioulo" if i % 2 == 0 else "BH",
                ultimo_casqueamento=data_casq,
                ultimo_vermifugo=data_vermi,
                peso=random.randint(400, 550)
            )
            cavalos_obj.append(cav)

        # --- 4. AULAS (Nov/2025 a Mar/2026) ---
        data_ini = date(2025, 11, 1)
        data_fim = date(2026, 3, 30)
        curr_date = data_ini

        while curr_date <= data_fim:
            if curr_date.weekday() != 6: # Pula Domingo (6)
                # Gerar 4 a 8 aulas por dia
                for _ in range(random.randint(4, 8)):
                    hora = random.choice([9, 10, 14, 15, 16, 17])
                    dt_aula = timezone.make_aware(datetime.combine(curr_date, datetime.min.time().replace(hour=hora)))
                    
                    Aula.objects.create(
                        empresa=emp,
                        aluno=random.choice(alunos_obj),
                        cavalo=random.choice(cavalos_obj),
                        data_hora=dt_aula,
                        tipo=random.choice(['NORMAL', 'AVULSA']),
                        concluida=True if curr_date < hoje else False
                    )
            curr_date += timedelta(days=1)

        # --- 5. FINANCEIRO ---
        # Receitas de Mensalidade
        for mes in range(11, 13): # Nov e Dez 2025
            for al in alunos_obj:
                MovimentacaoFinanceira.objects.create(
                    empresa=emp, tipo='Receita', descricao=f"Mensalidade - {al.nome}",
                    valor=Decimal("850.00"), data=date(2025, mes, 10)
                )
        for mes in range(1, 4): # Jan a Mar 2026
            for al in alunos_obj:
                MovimentacaoFinanceira.objects.create(
                    empresa=emp, tipo='Receita', descricao=f"Mensalidade - {al.nome}",
                    valor=Decimal("900.00"), data=date(2026, mes, 10)
                )
        
        # Despesas fixas mensais
        for d in [date(2025,11,5), date(2025,12,5), date(2026,1,5), date(2026,2,5), date(2026,3,5)]:
            MovimentacaoFinanceira.objects.create(
                empresa=emp, tipo='Despesa', descricao="Compra de Feno/Ração",
                valor=Decimal(random.randint(2000, 3500)), data=d
            )

    print("--- Script Finalizado com Sucesso! ---")

if __name__ == "__main__":
    run()