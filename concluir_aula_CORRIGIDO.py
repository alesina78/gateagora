# ── Concluir Aula ─────────────────────────────────────────────────────────────
# B3 FIX: a view recebia aula_id mas buscava no model Cavalo com variável cavalo_id indefinida.
# Corrigido para buscar Aula pelo id correto e filtrar pela empresa do usuário.

@login_required
def concluir_aula(request, aula_id):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    # B3 FIX: busca Aula (não Cavalo), usa aula_id (não cavalo_id)
    aula = get_object_or_404(Aula, id=aula_id, empresa=empresa)
    aula.concluida = True
    aula.save(update_fields=['concluida'])
    messages.success(request, f"Aula de {aula.aluno.nome} marcada como finalizada!")
    return redirect("dashboard")
