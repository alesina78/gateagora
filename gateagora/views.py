# -*- coding: utf-8 -*-
from datetime import timedelta, datetime
from decimal import Decimal
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum, F, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    Empresa, Perfil, Aluno, Cavalo, Baia, Piquete, Aula,
    ItemEstoque, MovimentacaoFinanceira, DocumentoCavalo
)

# Configuração de Branding
BRAND_NAME = "Gate 4"

class CustomLoginView(LoginView):
    """View de login personalizada com suporte ao design Dark."""
    template_name = "gateagora/login.html"
    form_class = AuthenticationForm  # Uso do form padrão para evitar ImportError
    redirect_authenticated_user = True

@login_required
def dashboard(request):
    """
    Dashboard Central: Processa finanças, agenda, estoque e saúde.
    """
    if not hasattr(request.user, "perfil"):
        if request.user.is_superuser:
            empresa_base = Empresa.objects.first()
            if not empresa_base:
                return redirect('/admin/gateagora/empresa/add/')
            Perfil.objects.get_or_create(
                user=request.user, 
                defaults={'empresa': empresa_base, 'cargo': 'Dono'}
            )
        else:
            return redirect('/admin/gateagora/perfil/add/')

    empresa = request.user.perfil.empresa
    hoje = timezone.localdate()

    # 1) AGENDA DE HOJE
    proximas_aulas = (
        Aula.objects
        .filter(empresa=empresa, concluida=False, data_hora__date=hoje)
        .select_related('aluno', 'cavalo')
        .order_by('data_hora')
    )

    # 2) ESTOQUE CRÍTICO
    estoque_critico = ItemEstoque.objects.filter(
        empresa=empresa,
        quantidade_atual__lte=F('alerta_minimo')
    )
    estoque_baixo_count = estoque_critico.count()

    # 3) DOCUMENTOS E SAÚDE
    janela_vencimento = hoje + timedelta(days=30)
    docs_vencendo = DocumentoCavalo.objects.filter(
        cavalo__empresa=empresa, 
        data_validade__range=[hoje, janela_vencimento]
    ).select_related('cavalo')

    baias_ocupadas = Baia.objects.filter(empresa=empresa, status='Ocupada').count()
    baias_livres = Baia.objects.filter(empresa=empresa, status='Livre').count()
    total_baias = Baia.objects.filter(empresa=empresa).count()
    porcentagem_ocupacao = int((baias_ocupadas / total_baias * 100)) if total_baias > 0 else 0

    cavalos_alerta = Cavalo.objects.filter(
        empresa=empresa
    ).exclude(status_saude='Saudável').count()

    stats = {
        "baias_ocupadas": baias_ocupadas,
        "baias_livres": baias_livres,
        "total_baias": total_baias,
        "porcentagem_ocupacao": porcentagem_ocupacao,
        "cavalos_alerta": cavalos_alerta,
        "total_cavalos": Cavalo.objects.filter(empresa=empresa).count(),
        "vacinados": Cavalo.objects.filter(
            empresa=empresa, 
            ultima_vacina__gte=hoje - timedelta(days=365)
        ).count(),
    }

    # 4) RELATÓRIO DE FATURAMENTO MENSAL
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    mes_atual_str = f"{meses_pt[hoje.month]}/{hoje.year}"

    relatorio = []
    receita_total = 0.0

    alunos_ativos = Aluno.objects.filter(empresa=empresa, ativo=True)
    for aluno in alunos_ativos:
        aulas_mes = Aula.objects.filter(
            empresa=empresa, aluno=aluno, concluida=True,
            data_hora__year=hoje.year, data_hora__month=hoje.month
        ).count()
        
        valor_aulas = float(aulas_mes * (aluno.valor_aula or 0))
        valor_hotelaria = float(
            Cavalo.objects.filter(empresa=empresa, proprietario=aluno)
            .aggregate(total=Sum('mensalidade_baia'))['total'] or 0
        )

        total_aluno = valor_aulas + valor_hotelaria
        receita_total += total_aluno

        tel = ''.join(filter(str.isdigit, str(aluno.telefone or '')))
        link_wa = "#"
        if tel:
            if not tel.startswith('55'): tel = f"55{tel}"
            msg = (f"Olá *{aluno.nome}*! Fechamento *{mes_atual_str}*:%0A"
                   f"- Hotelaria: R$ {valor_hotelaria:,.2f}%0A"
                   f"- Aulas ({aulas_mes}): R$ {valor_aulas:,.2f}%0A"
                   f"*Total: R$ {total_aluno:,.2f}*")
            link_wa = f"https://wa.me/{tel}?text={msg}"

        relatorio.append({
            "aluno": aluno,
            "valor": total_aluno,
            "whatsapp": link_wa,
        })

    relatorio.sort(key=lambda x: x["valor"], reverse=True)

    # 5) DADOS DOS GRÁFICOS (Histórico retroativo de 6 meses)
    labels_meses, dados_receita, dados_despesa, dados_lucro = [], [], [], []
    
    for i in range(5, -1, -1):
        # Ajuste para cálculo correto de meses retroativos
        data_aux = hoje.replace(day=1) - timedelta(days=i*30)
        mes_ref = data_aux.month
        ano_ref = data_aux.year
        
        labels_meses.append(f"{meses_pt[mes_ref][:3]}/{str(ano_ref)[2:]}")

        rec = MovimentacaoFinanceira.objects.filter(
            empresa=empresa, tipo='Receita',
            data__year=ano_ref, data__month=mes_ref
        ).aggregate(Sum('valor'))['valor__sum'] or 0
        
        desp = MovimentacaoFinanceira.objects.filter(
            empresa=empresa, tipo='Despesa',
            data__year=ano_ref, data__month=mes_ref
        ).aggregate(Sum('valor'))['valor__sum'] or 0

        dados_receita.append(float(rec))
        dados_despesa.append(float(desp))
        dados_lucro.append(float(rec - desp))

    context = {
        "brand_name": BRAND_NAME,
        "empresa": empresa,
        "hoje": hoje,
        "proximas_aulas": proximas_aulas,
        "estoque_baixo_count": estoque_baixo_count,
        "estoque_critico": estoque_critico,
        "docs_vencendo": docs_vencendo,
        "stats": stats,
        "relatorio": relatorio,
        "receita_total": receita_total,
        "labels_meses": json.dumps(labels_meses),
        "dados_receita": json.dumps(dados_receita),
        "dados_despesa": json.dumps(dados_despesa),
        "dados_lucro": json.dumps(dados_lucro),
    }
    return render(request, "gateagora/dashboard.html", context)

@login_required
def concluir_aula(request, aula_id):
    aula = get_object_or_404(Aula, id=aula_id, empresa=request.user.perfil.empresa)
    aula.concluida = True
    aula.save()
    messages.success(request, f"Aula de {aula.aluno.nome} concluída!")
    return redirect("dashboard")

@login_required
def gerar_relatorio_pdf(request, aluno_id):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    aluno = get_object_or_404(Aluno, id=aluno_id, empresa=request.user.perfil.empresa)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Fatura_{aluno.nome}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"Fatura: {aluno.nome}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Gerado em: {timezone.now().strftime('%d/%m/%Y')}")
    p.drawString(100, 760, f"Empresa: {request.user.perfil.empresa.nome}")
    p.line(100, 750, 500, 750)
    p.showPage()
    p.save()
    return response

@login_required
def gerar_ficha_trato_pdf(request):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    empresa = request.user.perfil.empresa
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Guia_Trato.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, 800, f"GUIA DE TRATO - {empresa.nome.upper()}")
    y = 750
    cavalos = Cavalo.objects.filter(
        empresa=empresa, 
        baia__isnull=False
    ).order_by('baia__numero')
    
    for c in cavalos:
        p.setFont("Helvetica-Bold", 10)
        p.drawString(40, y, f"BAIA {c.baia.numero}: {c.nome}")
        p.setFont("Helvetica", 9)
        p.drawString(50, y-12, f"Ração: {c.racao_tipo or 'Não informada'}")
        y -= 50
        if y < 50: 
            p.showPage()
            y = 800
    p.showPage()
    p.save()
    return response

@login_required
def manejo_em_massa(request):
    empresa = request.user.perfil.empresa
    if request.method == "POST":
        procedimento = request.POST.get("procedimento")
        data = request.POST.get("data")
        ids = request.POST.getlist("cavalos_selecionados")
        cavalos = Cavalo.objects.filter(id__in=ids, empresa=empresa)
        if procedimento == "Vacinacao":
            cavalos.update(ultima_vacina=data)
        elif procedimento == "Vermifugacao":
            cavalos.update(ultimo_vermifugo=data)
        messages.success(request, "Procedimento aplicado com sucesso!")
        return redirect("dashboard")
    cavalos = Cavalo.objects.filter(empresa=empresa)
    return render(request, "gateagora/manejo_massa.html", {"cavalos": cavalos})