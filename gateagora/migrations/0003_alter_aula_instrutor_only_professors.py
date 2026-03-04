# gateagora/migrations/0003_alter_aula_instrutor_only_professors.py
from django.db import migrations, models
import django.db.models.deletion


def map_instrutor_only_professors(apps, schema_editor):
    """
    Converte Aula.instrutor (valor legado = User.id) -> Perfil.id
    SOMENTE quando o Perfil existe e tem cargo='Professor'.
    Regras:
      - Se o valor atual já for um Perfil.id de Professor, mantém.
      - Se o valor parecer ser User.id: busca Perfil com user_id==valor e cargo='Professor';
        se achar, grava Perfil.id; se não, seta NULL.
      - Se não conseguir inferir (ambiguidade), seta NULL.
    """
    Aula = apps.get_model('gateagora', 'Aula')
    Perfil = apps.get_model('gateagora', 'Perfil')

    # Perfis de Professores
    professores = Perfil.objects.filter(cargo='Professor').only('id', 'user_id')
    professors_by_perfil_id = set(p.id for p in professores)
    map_user_to_perfil_id = {p.user_id: p.id for p in professores}

    updated_to_prof = 0
    nulled = 0
    unchanged_ok = 0

    # Itera de forma segura (memória)
    for a in Aula.objects.all().only('id', 'instrutor_id').iterator():
        old = a.instrutor_id
        if old is None:
            continue

        # Caso 1: já é um Perfil.id de Professor (mantém)
        if old in professors_by_perfil_id:
            unchanged_ok += 1
            continue

        # Caso 2: trata old como User.id -> tenta Perfil (Professor)
        new_perfil_id = map_user_to_perfil_id.get(old)
        if new_perfil_id:
            a.instrutor_id = new_perfil_id
            a.save(update_fields=['instrutor'])
            updated_to_prof += 1
        else:
            # Não é professor ou não existe Perfil: deixa NULL
            a.instrutor = None
            a.save(update_fields=['instrutor'])
            nulled += 1

    print(f"[gateagora] Instrutores mapeados p/ Perfil(Professor): {updated_to_prof}")
    print(f"[gateagora] Aulas já corretas (Perfil Professor): {unchanged_ok}")
    print(f"[gateagora] Aulas sem Professor válido (instrutor=NULL): {nulled}")


def reverse_noop(apps, schema_editor):
    # Não revertimos para User (sem mapeamento confiável inverso).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gateagora', '0002_remove_cavalo_historico_medico_and_more'),
        # ^^^ AJUSTE para sua última migração se já estiver em número maior.
    ]

    operations = [
        # Garante que o campo referencia Perfil (estrutura)
        migrations.AlterField(
            model_name='aula',
            name='instrutor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='aulas_ministradas',
                to='gateagora.perfil',
                limit_choices_to={'cargo': 'Professor'},
            ),
        ),
        # Migração de dados: mapeia apenas Professores; demais vira NULL
        migrations.RunPython(map_instrutor_only_professors, reverse_noop),
    ]
	