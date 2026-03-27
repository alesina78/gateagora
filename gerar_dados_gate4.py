import os
import random
from datetime import date, timedelta, datetime
from decimal import Decimal

try:
    import django
    django.setup()
except Exception:
    pass

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from gateagora.models import (
    Empresa, Perfil, Aluno, Baia, Piquete, Cavalo,
    Aula, ItemEstoque, MovimentacaoFinanceira,
    DocumentoCavalo, RegistroOcorrencia
)

print("Limpando dados existentes...")
with transaction.atomic():
    RegistroOcorrencia.objects.all().delete()
    DocumentoCavalo.objects.all().delete()
    Aula.objects.all().delete()
    MovimentacaoFinanceira.objects.all().delete()
    ItemEstoque.objects.all().delete()
    Cavalo.objects.all().delete()
    Piquete.objects.all().delete()
    Baia.objects.all().delete()
    Aluno.objects.all().delete()
    Perfil.objects.all().delete()
    Empresa.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
print("Limpeza concluida.")

HOJE = date.today()
DATA_INICIO = date(2025, 11, 1)
DATA_FIM = date(2026, 4, 30)
TELEFONE = "5551991387872"
random.seed(42)

print("Criando usuarios...")
admin_user, _ = User.objects.get_or_create(username="admin")
admin_user.email = "gateagora@gmail.com"
admin_user.is_superuser = True
admin_user.is_staff = True
admin_user.set_password("Gate$2024")
admin_user.save()

ale_user, _ = User.objects.get_or_create(username="alessandro_admin")
ale_user.email = "alessandroarturosanches@gmail.com"
ale_user.is_superuser = True
ale_user.is_staff = True
ale_user.set_password("Gate2024")
ale_user.save()

print("Criando empresas...")
emp_a = Empresa.objects.create(nome="Haras Santa Fe", slug="haras-santa-fe", cnpj="12.345.678/0001-90", cidade="Porto Alegre - RS")
emp_b = Empresa.objects.create(nome="Hipica Vale Verde", slug="hipica-vale-verde", cnpj="98.765.432/0001-11", cidade="Novo Hamburgo - RS")
print("Empresas criadas.")

print("Criando gestores e professores...")
usuarios_data = [
    ("gestor_hipica1", "Teste123", "gestor1@harassantafe.com.br",     emp_a, "Gestor"),
    ("gestor_hipica2", "Teste123", "gestor2@hipicavaleverde.com.br",  emp_b, "Gestor"),
    ("prof_rodrigo",   "Teste123", "rodrigo@harassantafe.com.br",     emp_a, "Professor"),
    ("prof_carolina",  "Teste123", "carolina@harassantafe.com.br",    emp_a, "Professor"),
    ("prof_marcelo",   "Teste123", "marcelo@hipicavaleverde.com.br",  emp_b, "Professor"),
    ("prof_jessica",   "Teste123", "jessica@hipicavaleverde.com.br",  emp_b, "Professor"),
    ("vet_luciana",    "Teste123", "luciana@harassantafe.com.br",     emp_a, "Veterinario"),
    ("vet_fernando",   "Teste123", "fernando@hipicavaleverde.com.br", emp_b, "Veterinario"),
    ("trat_josue",     "Teste123", "josue@harassantafe.com.br",       emp_a, "Tratador"),
    ("trat_gilberto",  "Teste123", "gilberto@hipicavaleverde.com.br", emp_b, "Tratador"),
]
perfis = {}
for username, senha, email, empresa, cargo in usuarios_data:
    u, _ = User.objects.get_or_create(username=username)
    u.email = email
    u.is_staff = True
    u.set_password(senha)
    u.save()
    p, _ = Perfil.objects.get_or_create(user=u, defaults={"empresa": empresa, "cargo": cargo})
    perfis[username] = p

pa1 = perfis["prof_rodrigo"]
pa2 = perfis["prof_carolina"]
pb1 = perfis["prof_marcelo"]
pb2 = perfis["prof_jessica"]
print("Usuarios criados.")

print("Criando baias...")
baias_a = [Baia.objects.create(empresa=emp_a, numero=str(i), status="Livre") for i in range(1, 36)]
baias_b = [Baia.objects.create(empresa=emp_b, numero=str(i), status="Livre") for i in range(1, 36)]
print("Baias criadas.")

print("Criando piquetes...")
piquetes_a = [Piquete.objects.create(empresa=emp_a, nome=n, capacidade=4, status="Livre") for n in ["Piquete Norte","Piquete Sul","Piquete Leste"]]
piquetes_b = [Piquete.objects.create(empresa=emp_b, nome=n, capacidade=4, status="Livre") for n in ["Piquete 1","Piquete 2","Piquete 3"]]
print("Piquetes criados.")

print("Criando alunos...")
ea = Aluno.objects.create(empresa=emp_a, nome=emp_a.nome, telefone=TELEFONE, ativo=True, valor_aula=Decimal("0.00"))
eb = Aluno.objects.create(empresa=emp_b, nome=emp_b.nome, telefone=TELEFONE, ativo=True, valor_aula=Decimal("0.00"))

pa_list = []
for nome, val in [("Ana Beatriz Fontana",Decimal("180.00")),("Carlos Eduardo Ramos",Decimal("200.00")),("Fernanda Lopes da Silva",Decimal("165.00")),("Gustavo Henrique Mota",Decimal("190.00")),("Isabela Carvalho Nunes",Decimal("175.00"))]:
    pa_list.append(Aluno.objects.create(empresa=emp_a, nome=nome, telefone=TELEFONE, ativo=True, valor_aula=val))

pb_list = []
for nome, val in [("Ricardo Almeida Teixeira",Decimal("185.00")),("Claudia Mendes Borba",Decimal("195.00")),("Fabio Souza Pinheiro",Decimal("170.00")),("Renata Campos Vieira",Decimal("180.00")),("Marcos Oliveira Duarte",Decimal("175.00"))]:
    pb_list.append(Aluno.objects.create(empresa=emp_b, nome=nome, telefone=TELEFONE, ativo=True, valor_aula=val))

ca_list = []
for nome, val in [("Lucas Martins Pereira",Decimal("150.00")),("Mariana Souza Alves",Decimal("150.00")),("Rafael Torres Duarte",Decimal("160.00")),("Juliana Ribeiro Costa",Decimal("155.00")),("Pedro Augusto Figueira",Decimal("150.00")),("Camila Azevedo Borges",Decimal("160.00")),("Thiago Nascimento Lima",Decimal("145.00")),("Bianca Ferreira Campos",Decimal("155.00")),("Eduardo Vieira Santos",Decimal("150.00"))]:
    ca_list.append(Aluno.objects.create(empresa=emp_a, nome=nome, telefone=TELEFONE, ativo=True, valor_aula=val))

cb_list = []
for nome, val in [("Patricia Lima Rocha",Decimal("150.00")),("Diego Ferreira Nunes",Decimal("155.00")),("Vanessa Carvalho Dias",Decimal("160.00")),("Andre Goncalves Moura",Decimal("150.00")),("Tatiana Barbosa Freitas",Decimal("145.00")),("Leandro Pinto Araujo",Decimal("155.00")),("Simone Batista Castro",Decimal("150.00")),("Rodrigo Medeiros Vale",Decimal("160.00")),("Aline Nascimento Lopes",Decimal("150.00"))]:
    cb_list.append(Aluno.objects.create(empresa=emp_b, nome=nome, telefone=TELEFONE, ativo=True, valor_aula=val))
print("Alunos criados.")

print("Criando cavalos...")
RACAS=["mang_marchador","quarto_milha","psl","crioulo","hipismo","srd"]
ATIVS=["0.018","0.025","0.035"]
SELAS=["Sela Salto Americana Nr 17","Sela Australiana Marrom","Sela Tropeira Tradicional","Sela Western Escura","Sela Inglesa Preta"]
CABS=["Cabecada com Freio Canudo","Cabecada com Freio D","Cabecada Simples Couro","Cabecada com Bridao"]
RACOES=["Guabi Equi-S","Pavo Performance","Eequi Turbo","Farinhao Nutri"]
FENOS=["Coast Cross","Tifton 85","Coastcross Premium"]
SUPLS=["Equiflex","HorsePower Plus","Bio Biotina","Sel-E-Vit"]
FQ=["A vontade","1 fardo/dia","2 fardos/dia"]
SS=["Alerta","Doente","Tratamento"]

NOMES_A=["Trovao do Pampa","Ventania Gaucha","Estrela do Sul","Baio Valente","Guerreiro das Pampas","Sertanejo","Pampeiro","Bravo","Foguete","Cangaceiro","Faceiro","Serrano","Diamante","Orgulho Gaucho","Tropeiro","Brilhante","Majestoso","Sultao do Haras","Principe Arabe","Condor Real","Tornado Azul","Vulcao Negro","Espirito Livre","Raio de Luz","Nobre Lusitano","Duque das Arenas","Eclipse Total","Fenomeno","Gringo","Horizonte","Imperador","Jaguar"]
NOMES_B=["Caraiba","Nordestino","Vento Norte","Catingueiro","Caboclo","Xingo","Agreste","Sertao Bravo","Campeiro","Pioneiro","Baluarte","Celerado","Destaque","Encanto","Festeiro","Galhardo","Herdeiro","Invencivel","Justiceiro","Kraken","Lendario","Maverick","Nuvem Branca","Olimpo","Poseidon","Quarteto","Relampago","Supremo","Trovador","Ultraje","Vigor","Zorro do Vale"]

def mk_cavalos(nomes, baias, piquetes, escola, props, empresa):
    out = []
    for i, nome in enumerate(nomes):
        prop = escola if i < 17 else props[(i-17) % len(props)]
        baia_obj = baias[i] if i < len(baias) else None
        piq_obj = None
        onde = "BAIA" if baia_obj else "PIQUETE"
        if not baia_obj:
            piq_obj = random.choice(piquetes)
        mat = (i >= 17) and (i in [17, 22])
        ss = random.choice(SS) if i in [3,9,15] else "Saudavel"
        uvac = HOJE - timedelta(days=random.randint(30,360))
        uverm = HOJE - timedelta(days=88) if i in [5,11,19,25] else HOJE - timedelta(days=random.randint(5,85))
        ucasq = HOJE - timedelta(days=42) if i in [7,14] else HOJE - timedelta(days=random.randint(5,40))
        uferr = HOJE - timedelta(days=random.randint(5,55))
        mens = Decimal("0.00") if i < 17 else Decimal(str(random.choice([800,900,1000,1100,1200,1500])))
        c = Cavalo(
            empresa=empresa, nome=nome,
            categoria="PROPRIO" if i < 17 else "HOTELARIA",
            status_saude=ss, onde_dorme=onde,
            raca=random.choice(RACAS), peso=round(random.uniform(380,560),1),
            fator_atividade=random.choice(ATIVS),
            tipo_sela="" if mat else random.choice(SELAS),
            tipo_cabecada="" if mat else random.choice(CABS),
            material_proprio=mat, baia=baia_obj, piquete=piq_obj,
            proprietario=prop, ultima_vacina=uvac,
            ultimo_vermifugo=uverm, ultimo_ferrageamento=uferr,
            ultimo_casqueamento=ucasq,
            racao_tipo=random.choice(RACOES),
            racao_qtd_manha="{}kg".format(random.choice([1,1.5,2,2.5,3])),
            racao_qtd_noite="{}kg".format(random.choice([1,1.5,2,2.5])),
            feno_tipo=random.choice(FENOS), feno_qtd=random.choice(FQ),
            complemento_nutricional=random.choice(SUPLS) if random.random()>0.6 else "",
            mensalidade_baia=mens,
        )
        c.save()
        out.append(c)
    return out

cvs_a = mk_cavalos(NOMES_A, baias_a, piquetes_a, ea, pa_list, emp_a)
cvs_b = mk_cavalos(NOMES_B, baias_b, piquetes_b, eb, pb_list, emp_b)
print("{} cavalos A | {} cavalos B".format(len(cvs_a), len(cvs_b)))

print("Criando documentos...")
TIPOS=["GTA","EXAME","VACINA","OUTRO"]
def mk_docs(cvs):
    n = 0
    for i, cav in enumerate(cvs[:20]):
        for j in range(random.randint(1,3)):
            tp = random.choice(TIPOS)
            if i==0 and j==0: dv = HOJE+timedelta(days=5)
            elif i==1 and j==0: dv = HOJE+timedelta(days=12)
            elif i==2 and j==0: dv = HOJE+timedelta(days=25)
            elif i==3 and j==0: dv = HOJE-timedelta(days=8)
            else:
                base = HOJE+timedelta(days=30)
                dv = base+timedelta(days=random.randint(0,(date(2027,12,31)-base).days))
            tits={"GTA":"GTA {}".format(cav.nome),"EXAME":"Exame - {}".format(cav.nome),"VACINA":"Vacina - {}".format(cav.nome),"OUTRO":"Doc - {}".format(cav.nome)}
            DocumentoCavalo.objects.create(cavalo=cav, titulo=tits[tp], tipo=tp, data_validade=dv)
            n += 1
    return n
d1=mk_docs(cvs_a); d2=mk_docs(cvs_b)
print("{} docs A | {} docs B".format(d1,d2))

print("Criando ocorrencias...")
ocs_a=[(3,"Colica Espasmódica","Animal com dor abdominal. Buscopan IV. Observacao noturna.","Dra. Luciana Farias CRMV-RS 12345",-5),(9,"Abscesso no Casco","Claudicacao. Casco drenado. Restricao 10 dias.","Dr. Paulo Silveira CRMV-RS 67890",-2),(15,"Dermite Estival","Lesoes pruriginosas. Shampoo antifungico e pomada.","Dra. Luciana Farias CRMV-RS 12345",-10)]
ocs_b=[(3,"Laminite Leve","Digitos quentes. Pastagem restringida. Dieta ajustada.","Dr. Fernando Almeida CRMV-RS 54321",-7),(9,"Conjuntivite","Secrecao ocular. Colitio antibiotico. Isolamento.","Dr. Fernando Almeida CRMV-RS 54321",-3),(15,"Ferida por Mordida","Laceracao no pescoco. Sutura 3 pontos. Antibiotico 7d.","Dra. Renata Brandao CRMV-RS 98765",-1)]
def mk_ocs(cvs, lst):
    for idx,titulo,desc,vet,off in lst:
        d_oc=HOJE+timedelta(days=off)
        dt=timezone.make_aware(datetime(d_oc.year,d_oc.month,d_oc.day,random.randint(7,18),0))
        RegistroOcorrencia.objects.create(cavalo=cvs[idx],data=dt,titulo=titulo,descricao=desc,veterinario=vet)
mk_ocs(cvs_a,ocs_a); mk_ocs(cvs_b,ocs_b)
print("Ocorrencias criadas.")

print("Criando estoque...")
iest_a=[("Guabi Equi-S 30kg",2,5,"Sacos"),("Vermifugo Panacur",1,3,"Unidade"),("Shampoo Antipatico",0,2,"Unidade"),("Atadura Ortopedica",3,5,"Rolos"),("Coast Cross Feno",80,20,"Fardos"),("Sal Mineral",15,5,"Kg"),("Serragem baia",40,10,"Sacos"),("Oleo de Milho",12,4,"Litros"),("Farelo de Soja",25,8,"Kg"),("Biotina Equina",8,3,"Frascos")]
iest_b=[("Racao Pavo Performance",2,5,"Sacos"),("Sulfato de Magnesio",1,3,"Kg"),("Luvas Descartaveis",4,5,"Caixa"),("Pomada Nitrofurazona",2,4,"Potes"),("Tifton 85 Feno",90,20,"Fardos"),("Sal Mineral Premium",18,5,"Kg"),("Serragem",35,10,"Sacos"),("Oleo de Soja",10,4,"Litros"),("Farinha de Osso",20,6,"Kg"),("Sel-E-Vit",6,2,"Frascos")]
for nm,qt,mn,un in iest_a: ItemEstoque.objects.create(empresa=emp_a,nome=nm,quantidade_atual=qt,alerta_minimo=mn,unidade=un)
for nm,qt,mn,un in iest_b: ItemEstoque.objects.create(empresa=emp_b,nome=nm,quantidade_atual=qt,alerta_minimo=mn,unidade=un)
print("Estoque criado.")

print("Criando financeiro...")
MP={1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
DF=[("Energia Eletrica",1200,2200),("Agua e Saneamento",400,800),("Salario Tratador",1800,2500)]
def mk_fin(emp):
    d=DATA_INICIO
    while d<=DATA_FIM:
        if d.day==10:
            MovimentacaoFinanceira.objects.create(empresa=emp,descricao="Mensalidades {}/{}".format(MP[d.month],d.year),valor=Decimal(str(round(random.uniform(8000,15000),2))),tipo="Receita",data=d)
            MovimentacaoFinanceira.objects.create(empresa=emp,descricao="Aulas {}/{}".format(MP[d.month],d.year),valor=Decimal(str(round(random.uniform(3000,6000),2))),tipo="Receita",data=d)
        if d.day==15:
            q=random.randint(20,40)
            MovimentacaoFinanceira.objects.create(empresa=emp,descricao="Compra Racao {} sacos".format(q),valor=Decimal(str(round(q*random.uniform(85,120),2))),tipo="Despesa",data=d)
        if d.day==5:
            for desc,vmin,vmax in DF:
                MovimentacaoFinanceira.objects.create(empresa=emp,descricao=desc,valor=Decimal(str(round(random.uniform(vmin,vmax),2))),tipo="Despesa",data=d)
        if random.random()<0.10:
            MovimentacaoFinanceira.objects.create(empresa=emp,descricao="Despesa Avulsa",valor=Decimal(str(round(random.uniform(200,2500),2))),tipo="Despesa",data=d)
        d+=timedelta(days=1)
mk_fin(emp_a); mk_fin(emp_b)
print("Financeiro: {} A | {} B".format(MovimentacaoFinanceira.objects.filter(empresa=emp_a).count(),MovimentacaoFinanceira.objects.filter(empresa=emp_b).count()))

print("Criando aulas...")
LOCAIS=["picadeiro_1","picadeiro_2","pista_salto"]
HORARIOS=[8,9,10,14,15,16,17]
def mk_aulas(emp, cvs, comuns, props, profs):
    todos=comuns+props; d=DATA_INICIO; total=0
    while d<=DATA_FIM:
        if d.weekday()==6:
            d+=timedelta(days=1); continue
        for hora in sorted(random.sample(HORARIOS,min(random.randint(3,5),len(HORARIOS)))):
            aluno=random.choice(todos); cav=random.choice(cvs); prof=random.choice(profs)
            conc=(random.random()>0.08) if d<HOJE else ((random.random()>0.6) if d==HOJE else False)
            dt=timezone.make_aware(datetime(d.year,d.month,d.day,hora,random.choice([0,30])))
            Aula.objects.create(empresa=emp,aluno=aluno,cavalo=cav,instrutor=prof,data_hora=dt,local=random.choice(LOCAIS),tipo=random.choices(["NORMAL","RECUPERAR"],weights=[90,10])[0],concluida=conc,relatorio_treino="")
            total+=1
        d+=timedelta(days=1)
    return total
ta=mk_aulas(emp_a,cvs_a,ca_list,pa_list,[pa1,pa2])
tb=mk_aulas(emp_b,cvs_b,cb_list,pb_list,[pb1,pb2])
print("{} aulas A | {} aulas B".format(ta,tb))

print("")
print("="*60)
print("DADOS GERADOS COM SUCESSO - GATE 4")
print("="*60)
print("Empresas:          {}".format(Empresa.objects.count()))
print("Usuarios:          {}".format(User.objects.count()))
print("Alunos:            {}".format(Aluno.objects.count()))
print("Baias:             {}".format(Baia.objects.count()))
print("Piquetes:          {}".format(Piquete.objects.count()))
print("Cavalos:           {}".format(Cavalo.objects.count()))
print("Documentos:        {}".format(DocumentoCavalo.objects.count()))
print("Ocorrencias:       {}".format(RegistroOcorrencia.objects.count()))
print("Itens Estoque:     {}".format(ItemEstoque.objects.count()))
print("Movim. Financeiras:{}".format(MovimentacaoFinanceira.objects.count()))
print("Aulas:             {}".format(Aula.objects.count()))
print("")
print("CREDENCIAIS:")
print("  admin            / Gate$2024")
print("  alessandro_admin / Gate2024")
print("  gestor_hipica1   / Teste123  (Haras Santa Fe)")
print("  gestor_hipica2   / Teste123  (Hipica Vale Verde)")
print("  prof_rodrigo     / Teste123")
print("  prof_carolina    / Teste123")
print("  prof_marcelo     / Teste123")
print("  prof_jessica     / Teste123")
print("  vet_luciana      / Teste123")
print("  vet_fernando     / Teste123")
print("Concluido!")
