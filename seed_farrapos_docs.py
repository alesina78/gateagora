# seed_farrapos_docs.py: cria documentos só para os cavalos do Clube Farrapos.
from datetime import timedelta
from django.utils import timezone
from gateagora.models import Empresa, Cavalo, DocumentoCavalo

emp = Empresa.objects.filter(nome="Clube Farrapos").first()
if emp is None:
    raise SystemExit("Empresa 'Clube Farrapos' não encontrada.")
if DocumentoCavalo.objects.filter(cavalo__empresa=emp).exists():
    raise SystemExit("Documentos do Clube Farrapos já existem. Nada foi criado.")

hoje = timezone.localdate()
cavalos = list(Cavalo.objects.filter(empresa=emp).order_by("id"))
for i, cav in enumerate(cavalos[:8]):
    DocumentoCavalo.objects.create(cavalo=cav, titulo="GTA", tipo="GTA",
                                   data_validade=hoje + timedelta(days=200))
    DocumentoCavalo.objects.create(cavalo=cav, titulo="Atestado de vacinação", tipo="VACINA",
                                   data_validade=hoje + timedelta(days=[-30, 15, 90][i % 3]))
DocumentoCavalo.objects.create(cavalo=cavalos[0], titulo="Exame Mormo/Anemia", tipo="EXAME",
                               data_validade=hoje - timedelta(days=60))
print("Documentos criados:", DocumentoCavalo.objects.filter(cavalo__empresa=emp).count())
