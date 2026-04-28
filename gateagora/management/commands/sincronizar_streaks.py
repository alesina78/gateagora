"""
Management command para recalcular streak_atual de todos os alunos ativos.

Uso:
    python manage.py sincronizar_streaks

Rode uma vez após deploys ou quando o campo streak_atual estiver
desatualizado para alunos que nunca usaram o app.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Recalcula streak_atual e melhor_streak de todos os alunos ativos'

    def handle(self, *args, **options):
        from gateagora.models import Aluno, Aula

        hoje    = timezone.localdate()
        alunos  = list(Aluno.objects.filter(ativo=True))
        total   = len(alunos)
        atualizados = 0

        self.stdout.write(f'Processando {total} alunos...')

        # Busca aulas dos últimos 90 dias de todos os alunos em uma query
        ids = [a.id for a in alunos]
        aulas_historico = list(
            Aula.objects
            .filter(
                aluno_id__in=ids,
                concluida=True,
                data_hora__date__gte=hoje - timedelta(days=90),
                data_hora__date__lte=hoje,
            )
            .values('aluno_id', 'data_hora')
        )

        semanas_por_aluno = {}
        for row in aulas_historico:
            iso = row['data_hora'].isocalendar()
            key = iso[0] * 100 + iso[1]
            semanas_por_aluno.setdefault(row['aluno_id'], set()).add(key)

        for aluno in alunos:
            semanas = semanas_por_aluno.get(aluno.id, set())
            streak  = 0
            check   = hoje
            for _ in range(13):
                iso = check.isocalendar()
                key = iso[0] * 100 + iso[1]
                if key in semanas:
                    streak += 1
                    check  -= timedelta(days=7)
                else:
                    if streak == 0:
                        check -= timedelta(days=7)
                        continue
                    break

            mudou = False
            if aluno.streak_atual != streak:
                aluno.streak_atual = streak
                mudou = True
            if streak > aluno.melhor_streak:
                aluno.melhor_streak = streak
                mudou = True
            if mudou:
                aluno.save(update_fields=['streak_atual', 'melhor_streak'])
                atualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Concluído. {atualizados} de {total} alunos atualizados.'
            )
        )
