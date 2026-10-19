from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from gateagora.models import Empresa, Cavalo, ItemFatura
from gateagora.views import obter_fatura_pendente


def primeiro_dia_mes_seguinte(data):
    ano = data.year + (1 if data.month == 12 else 0)
    mes = 1 if data.month == 12 else data.month + 1
    return date(ano, mes, 1)


class Command(BaseCommand):
    help = "Gera as mensalidades fixas de baia do mês seguinte, no dia de emissão de cada empresa."

    def add_arguments(self, parser):
        parser.add_argument(
            "--forcar", action="store_true",
            help="Gera mesmo fora do dia de emissão (para testes).",
        )
        parser.add_argument(
            "--empresa", type=int,
            help="ID da empresa (opcional).",
        )

    def handle(self, *args, **options):
        hoje = timezone.localdate()
        empresas = Empresa.objects.all()
        if options["empresa"]:
            empresas = empresas.filter(id=options["empresa"])

        for empresa in empresas:
            dia_emissao = max(1, empresa.dia_vencimento - empresa.dias_antecedencia_emissao)

            if not options["forcar"] and hoje.day != dia_emissao:
                self.stdout.write(f"[{empresa.nome}] hoje não é dia de emitir (dia {dia_emissao}).")
                continue

            competencia = primeiro_dia_mes_seguinte(hoje)
            vencimento = date(competencia.year, competencia.month, empresa.dia_vencimento)

            # Cavalo entra até o fim do mês da saída
            cavalos = (
                Cavalo.objects
                .filter(empresa=empresa, proprietario__isnull=False)
                .filter(Q(data_saida__isnull=True) | Q(data_saida__gte=competencia))
                .select_related("proprietario")
            )

            criados = 0
            with transaction.atomic():
                for cavalo in cavalos:
                    if not cavalo.mensalidade_baia or cavalo.mensalidade_baia <= 0:
                        continue

                    fatura = obter_fatura_pendente(
                        empresa, cavalo.proprietario, "FIXA", competencia, vencimento,
                    )

                    # Não duplica: se o item já existe nessa fatura, pula
                    if ItemFatura.objects.filter(fatura=fatura, cavalo=cavalo, tipo="BAIA").exists():
                        continue

                    ItemFatura.objects.create(
                        fatura=fatura,
                        tipo="BAIA",
                        cavalo=cavalo,
                        descricao=f"Mensalidade baia — {cavalo.nome} — {competencia:%m/%Y}",
                        valor=cavalo.mensalidade_baia,
                        data=hoje,
                    )
                    criados += 1

            self.stdout.write(
                self.style.SUCCESS(f"[{empresa.nome}] {criados} mensalidade(s) de baia gerada(s).")
            )