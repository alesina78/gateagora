# gateagora/migrations/0003_alter_aula_instrutor_to_perfil_and_map.py
from django.db import migrations, models
import django.db.models.deletion


def map_user_to_perfil(apps, schema_editor):
    """
    Converte Aula.instrutor (antes: User.id) -> (agora: Perfil.id).
    Estratégia:
      - Depois do AlterField, o valor de instrutor_id ainda contém inteiros antigos.
      - Construímos um mapa user_id -> perfil_id e regravamos Aula.instrutor_id.
    """
    Aula = apps.get_model('gateagora', 'Aula')
    Perfil = apps.get_model('gateagora', 'Perfil')

    # dicionário user_id -> perfil_id
    mapping = {p.user_id: p.id for p in Perfil.objects.all()}

    atualizadas = 0
    for a in Aula.objects.all().only('id', 'instrutor_id'):
        old_user_id = a.instrutor_id
        if old_user_id and old_user_id in mapping:
            a.instrutor_id = mapping[old_user_id]
            a.save(update_fields=['instrutor'])
            atualizadas += 1

    print(f"[gateagora] Aulas atualizadas com Perfil: {atualizadas}")


def reverse_noop(apps, schema_editor):
    # Não tentamos reverter para User (não há mapeamento 100% confiável).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gateagora', '0002_remove_cavalo_historico_medico_and_more'),
        # ^ Troque para a SUA última migração, caso o número já tenha avançado.
    ]

    operations = [
        # 1) Troca a FK de Aula.instrutor para apontar para gateagora.Perfil
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
        # 2) Migração de dados: mapeia os IDs antigos (User) para Perfil
        migrations.RunPython(map_user_to_perfil, reverse_noop),
    ]
	