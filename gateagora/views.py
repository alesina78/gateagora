# -*- coding: utf-8 -*-
from datetime import date, timedelta
from decimal import Decimal
import json
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import (
    Sum, F, Q, Count, DecimalField, Value,
    ExpressionWrapper, Subquery, OuterRef
)
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from .models import (
    Empresa, Perfil, Aluno, Cavalo, Baia, Piquete, Aula,
    ItemEstoque, MovimentacaoFinanceira, DocumentoCavalo
)

BRAND_NAME = "Gate 4"


# ── Login ─────────────────────────────────────────────────────────────────────

class CustomLoginView(LoginView):
    template_name = "gateagora/login.html"
    form_class    = AuthenticationForm
    redirect_authenticated_user = True


# ── Utilitários ───────────────────────────────────────────────────────────────

def _iter_ultimos_meses(base: date, n: int = 6):
    out = []
    for i in range(n):
        m = base.month - i
        y = base.year
        while m <= 0:
            m += 12
            y -= 1
        out.append(date(y, m, 1))
    return sorted(out)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    empresa = getattr(request, "empresa", None)
    if not empresa:
        if hasattr(request.user, "perfil"):
            empresa = request.user.perfil.empresa
        else:
            return redirect('/admin/gateagora/perfil/add/')

    hoje = timezone.localdate()

    # 1) Agenda — só aulas não concluídas de hoje
    proximas_aulas = (
        Aula.objects
        .filter(empresa=empresa, concluida=False, data_hora__date=hoje)
        .select_related('aluno', 'cavalo')
        .order_by('data_hora')
    )

    # 2) Alertas
    estoque_critico     = ItemEstoque.objects.filter(
        empresa=empresa, quantidade_atual__lte=F('alerta_minimo')
    )
    estoque_baixo_count = estoque_critico.count()

    janela_venc = hoje + timedelta(days=30)
    docs_vencendo = (
        DocumentoCavalo.objects
        .filter(cavalo__empresa=empresa, data_validade__range=[hoje, janela_venc])
        .select_related('cavalo')
        .order_by('data_validade')
    )

    cavalos_alerta_lista = (
        Cavalo.objects
        .filter(empresa=empresa)
        .exclude(status_saude='Saudável')
        .select_related('proprietario')
        .order_by('status_saude')
    )

    # 3) KPIs
    total_baias          = Baia.objects.filter(empresa=empresa).count()
    baias_ocupadas       = Baia.objects.filter(empresa=empresa, status='Ocupada').count()
    porcentagem_ocupacao = int((baias_ocupadas / total_baias * 100)) if total_baias else 0

    stats = {
        "baias_ocupadas":       baias_ocupadas,
        "baias_livres":         total_baias - baias_ocupadas,
        "total_baias":          total_baias,
        "porcentagem_ocupacao": porcentagem_ocupacao,
        "cavalos_alerta":       Cavalo.objects.filter(empresa=empresa).exclude(status_saude='Saudável').count(),
        "total_cavalos":        Cavalo.objects.filter(empresa=empresa).count(),
        "vacinados":            Cavalo.objects.filter(
            empresa=empresa,
            ultima_vacina__gte=hoje - timedelta(days=365)
        ).count(),
    }

    # 4) Faturamento — Subquery corrigida (evita inflate de JOIN)
    hotelaria_sq = (
        Cavalo.objects
        .filter(proprietario=OuterRef('pk'), empresa=empresa)
        .values('proprietario')
        .annotate(total_hotel=Sum('mensalidade_baia'))
        .values('total_hotel')
    )

    alunos_com_faturamento = (
        Aluno.objects
        .filter(empresa=empresa, ativo=True)
        .annotate(
            aulas_mes=Count(
                'aulas',
                filter=Q(
                    aulas__empresa=empresa,
                    aulas__concluida=True,
                    aulas__data_hora__year=hoje.year,
                    aulas__data_hora__month=hoje.month,
                ),
                distinct=True
            ),
            valor_aulas=ExpressionWrapper(
                Coalesce(
                    Count(
                        'aulas',
                        filter=Q(
                            aulas__empresa=empresa,
                            aulas__concluida=True,
                            aulas__data_hora__year=hoje.year,
                            aulas__data_hora__month=hoje.month
                        ),
                        distinct=True
                    ),
                    Value(0)
                ) * F('valor_aula'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            valor_hotelaria=Coalesce(
                Subquery(hotelaria_sq, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
            )
        )
        .annotate(total=F('valor_aulas') + F('valor_hotelaria'))
        .order_by('-total')
    )

    meses_pt = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }
    mes_atual_str = f"{meses_pt[hoje.month]}/{hoje.year}"

    relatorio              = []
    receita_total_prevista = Decimal('0.00')

    for aluno in alunos_com_faturamento:
        total_aluno = aluno.total or Decimal('0.00')
        receita_total_prevista += total_aluno

        tel     = ''.join(filter(str.isdigit, str(aluno.telefone or '')))
        link_wa = "#"
        if tel:
            if not tel.startswith('55'):
                tel = f"55{tel}"
            msg = (
                f"Olá *{aluno.nome}*! Segue o fechamento de *{mes_atual_str}*:\n"
                f"- Hotelaria: R$ {aluno.valor_hotelaria:,.2f}\n"
                f"- Aulas ({aluno.aulas_mes or 0}): R$ {aluno.valor_aulas:,.2f}\n"
                f"*Total a pagar: R$ {total_aluno:,.2f}*"
            )
            link_wa = f"https://wa.me/{tel}?text={quote(msg)}"

        relatorio.append({
            "aluno":    aluno,
            "valor":    float(total_aluno),
            "whatsapp": link_wa,
        })

    # 5) Financeiro para gráfico
    financeiro_mensal = (
        MovimentacaoFinanceira.objects
        .filter(empresa=empresa)
        .annotate(mes_trunc=TruncMonth('data'))
        .values('mes_trunc')
        .annotate(
            receita=Coalesce(Sum('valor', filter=Q(tipo='Receita')), Value(0, output_field=DecimalField())),
            despesa=Coalesce(Sum('valor', filter=Q(tipo='Despesa')), Value(0, output_field=DecimalField()))
        )
        .order_by('mes_trunc')
    )

    dados_mapeados = {}
    for item in financeiro_mensal:
        dt = item['mes_trunc']
        if dt:
            chave = dt.date().replace(day=1) if hasattr(dt, 'date') else dt.replace(day=1)
            dados_mapeados[chave] = (float(item['receita']), float(item['despesa']))

    eixo_meses    = _iter_ultimos_meses(hoje, 6)
    labels_meses  = []
    dados_receita = []
    dados_despesa = []
    dados_lucro   = []

    for m in eixo_meses:
        labels_meses.append(f"{meses_pt[m.month]}/{str(m.year)[2:]}")
        rec, desp = dados_mapeados.get(m, (0.0, 0.0))
        dados_receita.append(rec)
        dados_despesa.append(desp)
        dados_lucro.append(rec - desp)

    # 6) Ranking de treinos por cavalo — período escolhido pelo usuário
    LIMITE_TREINOS_MES = 20  # ajuste conforme sua hípica

    periodo = request.GET.get('periodo', 'mes')  # mes | 30 | 90

    if periodo == '30':
        data_inicio  = hoje - timedelta(days=30)
        periodo_label = 'Últimos 30 dias'
    elif periodo == '90':
        data_inicio  = hoje - timedelta(days=90)
        periodo_label = 'Últimos 3 meses'
    else:  # padrão: mês atual
        periodo      = 'mes'
        data_inicio  = hoje.replace(day=1)
        periodo_label = f"{meses_pt[hoje.month]}/{hoje.year}"

    ranking_cavalos = (
        Cavalo.objects
        .filter(empresa=empresa)
        .annotate(
            treinos_periodo=Count(
                'aulas',
                filter=Q(
                    aulas__concluida=True,
                    aulas__data_hora__date__gte=data_inicio,
                    aulas__data_hora__date__lte=hoje,
                )
            )
        )
        .order_by('-treinos_periodo', 'nome')
    )

    com_treino     = [c for c in ranking_cavalos if c.treinos_periodo > 0]
    sem_treino     = [c.nome for c in ranking_cavalos if c.treinos_periodo == 0]
    ranking_labels = [c.nome for c in com_treino]
    ranking_dados  = [c.treinos_periodo for c in com_treino]

    # Limite proporcional ao período
    limite = LIMITE_TREINOS_MES if periodo == 'mes' else (
        LIMITE_TREINOS_MES if periodo == '30' else LIMITE_TREINOS_MES * 3
    )

    context = {
        "brand_name":               BRAND_NAME,
        "empresa":                  empresa,
        "hoje":                     hoje,
        "proximas_aulas":           proximas_aulas,
        "estoque_baixo_count":      estoque_baixo_count,
        "estoque_critico":          estoque_critico,
        "docs_vencendo":            docs_vencendo,
        "cavalos_alerta_lista":     cavalos_alerta_lista,
        "stats":                    stats,
        "relatorio":                relatorio,
        "receita_total_prevista":   float(receita_total_prevista),
        "labels_meses":             json.dumps(labels_meses),
        "dados_receita":            json.dumps(dados_receita),
        "dados_despesa":            json.dumps(dados_despesa),
        "dados_lucro":              json.dumps(dados_lucro),
        "top_alunos_labels":        json.dumps([r["aluno"].nome for r in relatorio[:10]], ensure_ascii=False),
        "top_alunos_valores":       json.dumps([r["valor"] for r in relatorio[:10]]),
        # Ranking cavalos
        "ranking_cavalos_labels":   json.dumps(ranking_labels, ensure_ascii=False),
        "ranking_cavalos_dados":    json.dumps(ranking_dados),
        "cavalos_sem_treino":       sem_treino,
        "limite_treinos_mes":       limite,
        "periodo_label":            periodo_label,
        "periodo_atual":            periodo,
    }
    return render(request, "gateagora/dashboard.html", context)


# ── Concluir Aula ─────────────────────────────────────────────────────────────

@login_required
def concluir_aula(request, aula_id):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    aula    = get_object_or_404(Aula, id=aula_id, empresa=empresa)
    aula.concluida = True
    aula.save(update_fields=['concluida'])
    messages.success(request, f"Aula de {aula.aluno.nome} marcada como finalizada!")
    return redirect("dashboard")


# ── PDF Fatura ────────────────────────────────────────────────────────────────

@login_required
def gerar_relatorio_pdf(request, aluno_id):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    aluno   = get_object_or_404(Aluno, id=aluno_id, empresa=empresa)

    hoje     = timezone.localdate()
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março',    4: 'Abril',
        5: 'Maio',    6: 'Junho',     7: 'Julho',     8: 'Agosto',
        9: 'Setembro',10: 'Outubro',  11: 'Novembro', 12: 'Dezembro'
    }
    mes_str = f"{meses_pt[hoje.month]}/{hoje.year}"

    cavalos_aluno   = Cavalo.objects.filter(proprietario=aluno, empresa=empresa)
    valor_hotelaria = sum(c.mensalidade_baia for c in cavalos_aluno)
    aulas_mes       = Aula.objects.filter(
        empresa=empresa, aluno=aluno, concluida=True,
        data_hora__year=hoje.year, data_hora__month=hoje.month
    )
    valor_aulas = len(aulas_mes) * float(aluno.valor_aula)
    total       = float(valor_hotelaria) + valor_aulas

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="Fatura_{aluno.nome}_{hoje.month}_{hoje.year}.pdf"'
    )

    p    = canvas.Canvas(response, pagesize=A4)
    W, H = A4

    # Cabeçalho
    p.setFillColorRGB(0.06, 0.09, 0.14)
    p.rect(0, H - 80, W, 80, fill=True, stroke=False)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(40, H - 38, empresa.nome.upper())
    p.setFont("Helvetica", 9)
    p.setFillColorRGB(0.6, 0.6, 0.7)
    p.drawString(40, H - 55, f"FATURA DE MENSALIDADE — {mes_str.upper()}")
    p.drawRightString(W - 40, H - 38, f"Emitido: {hoje.strftime('%d/%m/%Y')}")

    # Cliente
    y = H - 110
    p.setFillColorRGB(0.13, 0.16, 0.22)
    p.roundRect(30, y - 12, W - 60, 48, 6, fill=True, stroke=False)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(42, y + 20, f"CLIENTE:  {aluno.nome.upper()}")
    p.setFont("Helvetica", 9)
    p.setFillColorRGB(0.6, 0.6, 0.7)
    if aluno.telefone:
        p.drawString(42, y + 6, f"Telefone: {aluno.telefone}")

    # Cabeçalho tabela
    y -= 38
    p.setFillColorRGB(0.24, 0.28, 0.9)
    p.rect(30, y - 5, W - 60, 24, fill=True, stroke=False)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(42, y + 6, "DESCRIÇÃO")
    p.drawRightString(W - 40, y + 6, "VALOR")
    y -= 28

    # Hotelaria
    if valor_hotelaria > 0:
        p.setFillColorRGB(0.13, 0.16, 0.22)
        p.rect(30, y - 8, W - 60, 22, fill=True, stroke=False)
        p.setFillColorRGB(0.55, 0.75, 1.0)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(42, y + 5, f"Hotelaria ({len(cavalos_aluno)} cavalo(s))")
        p.drawRightString(W - 40, y + 5, f"R$ {float(valor_hotelaria):,.2f}")
        y -= 22
        for c in cavalos_aluno:
            p.setFillColorRGB(0.4, 0.45, 0.55)
            p.setFont("Helvetica", 8)
            p.drawString(55, y, f"• {c.nome}  —  R$ {float(c.mensalidade_baia):,.2f}/mês")
            y -= 13
        y -= 4

    # Aulas
    p.setFillColorRGB(0.13, 0.16, 0.22)
    p.rect(30, y - 8, W - 60, 22, fill=True, stroke=False)
    p.setFillColorRGB(0.55, 0.75, 1.0)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(42, y + 5, f"Aulas ({len(aulas_mes)} × R$ {float(aluno.valor_aula):,.2f})")
    p.drawRightString(W - 40, y + 5, f"R$ {valor_aulas:,.2f}")
    y -= 22
    for aula in aulas_mes:
        p.setFillColorRGB(0.4, 0.45, 0.55)
        p.setFont("Helvetica", 8)
        p.drawString(55, y, f"• {aula.data_hora.strftime('%d/%m')}  —  {aula.cavalo.nome}")
        y -= 13

    # Total
    y -= 18
    p.setFillColorRGB(0.06, 0.73, 0.51)
    p.roundRect(30, y - 10, W - 60, 36, 6, fill=True, stroke=False)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(42, y + 12, "TOTAL A PAGAR")
    p.drawRightString(W - 40, y + 12, f"R$ {total:,.2f}")

    p.showPage()
    p.save()
    return response


# ── PDF Guia de Trato ─────────────────────────────────────────────────────────

@login_required
def gerar_ficha_trato_pdf(request):
    empresa  = getattr(request, "empresa", request.user.perfil.empresa)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Guia_Trato.pdf"'

    p    = canvas.Canvas(response, pagesize=A4)
    W, H = A4

    COR_RACAO    = (0.24, 0.48, 1.0)
    COR_VOLUMOSO = (0.13, 0.70, 0.37)
    COR_SUPL     = (0.80, 0.55, 0.10)
    COR_FUNDO    = (0.10, 0.13, 0.18)
    COR_BRANCO   = (1.0,  1.0,  1.0)
    COR_CINZA    = (0.55, 0.60, 0.70)

    pagina = 1

    def cabecalho(p, pagina):
        p.setFillColorRGB(0.06, 0.09, 0.14)
        p.rect(0, H - 65, W, 65, fill=True, stroke=False)
        p.setFillColorRGB(*COR_BRANCO)
        p.setFont("Helvetica-Bold", 15)
        p.drawString(30, H - 32, f"GUIA DE TRATO DIÁRIO — {empresa.nome.upper()}")
        p.setFont("Helvetica", 8)
        p.setFillColorRGB(*COR_CINZA)
        p.drawString(30, H - 50, f"Gerado em: {date.today().strftime('%d/%m/%Y')}   |   Página {pagina}")
        return H - 82

    y = cabecalho(p, pagina)

    cavalos = (
        Cavalo.objects
        .filter(empresa=empresa)
        .select_related('baia', 'piquete', 'proprietario')
        .order_by('baia__numero', 'nome')
    )

    for cavalo in cavalos:
        altura_card = 82 + (14 if cavalo.complemento_nutricional else 0)

        if y - altura_card < 40:
            p.showPage()
            pagina += 1
            y = cabecalho(p, pagina)

        p.setFillColorRGB(*COR_FUNDO)
        p.roundRect(25, y - altura_card, W - 50, altura_card, 8, fill=True, stroke=False)

        if cavalo.categoria == 'HOTELARIA':
            p.setFillColorRGB(0.38, 0.40, 0.95)
        else:
            p.setFillColorRGB(*COR_VOLUMOSO)
        p.rect(25, y - altura_card, 5, altura_card, fill=True, stroke=False)

        p.setFillColorRGB(*COR_BRANCO)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(38, y - 18, cavalo.nome.upper())

        local = (
            f"Baia {cavalo.baia.numero}" if cavalo.baia
            else (cavalo.piquete.nome if cavalo.piquete else "Solto")
        )
        p.setFillColorRGB(*COR_CINZA)
        p.setFont("Helvetica", 8)
        p.drawString(38, y - 30, f"{local}  |  {cavalo.proprietario.nome}  |  {cavalo.get_categoria_display()}")

        linha_y = y - 44

        if cavalo.racao_tipo or cavalo.racao_qtd_manha or cavalo.racao_qtd_noite:
            p.setFillColorRGB(*COR_RACAO)
            p.setFont("Helvetica-Bold", 8)
            p.drawString(38, linha_y, "RAÇÃO:")
            p.setFont("Helvetica", 8)
            partes = []
            if cavalo.racao_tipo:      partes.append(cavalo.racao_tipo)
            if cavalo.racao_qtd_manha: partes.append(f"Manhã {cavalo.racao_qtd_manha}")
            if cavalo.racao_qtd_noite: partes.append(f"Noite {cavalo.racao_qtd_noite}")
            p.drawString(80, linha_y, "  •  ".join(partes))
            linha_y -= 14

        if cavalo.feno_tipo or cavalo.feno_qtd:
            p.setFillColorRGB(*COR_VOLUMOSO)
            p.setFont("Helvetica-Bold", 8)
            p.drawString(38, linha_y, "VOLUMOSO:")
            p.setFont("Helvetica", 8)
            vol = []
            if cavalo.feno_tipo: vol.append(cavalo.feno_tipo)
            if cavalo.feno_qtd:  vol.append(cavalo.feno_qtd)
            p.drawString(95, linha_y, "  •  ".join(vol))
            linha_y -= 14

        if cavalo.complemento_nutricional:
            p.setFillColorRGB(*COR_SUPL)
            p.setFont("Helvetica-Bold", 8)
            p.drawString(38, linha_y, "SUPLEMENTO:")
            p.setFont("Helvetica", 8)
            p.drawString(105, linha_y, cavalo.complemento_nutricional[:80])

        y -= altura_card + 8

    p.save()
    return response


# ── Encilhamento ──────────────────────────────────────────────────────────────

def _get_aulas_encilhamento(empresa, data_str):
    from datetime import datetime
    try:
        data = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else timezone.localdate()
    except (ValueError, TypeError):
        data = timezone.localdate()

    aulas = (
        Aula.objects
        .filter(empresa=empresa, data_hora__date=data)
        .select_related(
            'aluno', 'cavalo', 'cavalo__baia',
            'cavalo__piquete', 'instrutor', 'instrutor__user'
        )
        .order_by('data_hora')
    )
    return aulas, data


@login_required
def encilhamento(request):
    empresa  = getattr(request, "empresa", request.user.perfil.empresa)
    data_str = request.GET.get('data', '')
    aulas, data_selecionada = _get_aulas_encilhamento(empresa, data_str)

    return render(request, "gateagora/encilhamento.html", {
        "empresa":          empresa,
        "aulas":            aulas,
        "data_selecionada": data_selecionada,
        "total_aulas":      aulas.count(),
    })


@login_required
def encilhamento_whatsapp(request):
    empresa  = getattr(request, "empresa", request.user.perfil.empresa)
    data_str = request.GET.get('data', '')
    telefone = request.GET.get('telefone', '').strip()
    aulas, data_selecionada = _get_aulas_encilhamento(empresa, data_str)

    meses_pt = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }
    data_fmt = f"{data_selecionada.day:02d}/{meses_pt[data_selecionada.month]}/{data_selecionada.year}"

    linhas = [
        f"🐎 *GUIA DE ENCILHAMENTO — {empresa.nome.upper()}*",
        f"📅 *{data_fmt}*",
        "─" * 30,
    ]

    if not aulas:
        linhas.append("\n_Nenhuma aula programada para este dia._")
    else:
        for aula in aulas:
            c     = aula.cavalo
            local = (
                f"Baia {c.baia.numero}" if c.baia
                else (c.piquete.nome if c.piquete else "Local não definido")
            )
            material = "⚠️ Material PRÓPRIO do proprietário" if c.material_proprio else "✅ Material da Escola"
            linhas += [
                "",
                f"🕐 *{aula.data_hora.strftime('%H:%M')}* — {aula.get_local_display()}",
                f"👤 Aluno: *{aula.aluno.nome}*",
                f"🐴 Cavalo: *{c.nome}* ({local})",
                f"🪑 Sela: {c.tipo_sela or 'Padrão escola'}",
                f"🔗 Cabeçada: {c.tipo_cabecada or 'Padrão escola'}",
                f"🎒 {material}",
            ]
            if aula.relatorio_treino:
                linhas.append(f"📝 Obs: {aula.relatorio_treino}")

    linhas += ["", "─" * 30, "_Enviado via Gate 4 Management_"]

    texto = "\n".join(linhas)
    tel   = ''.join(filter(str.isdigit, telefone))

    if not tel:
        messages.warning(request, "Informe o WhatsApp do cavalariço antes de enviar.")
        return redirect(f"/encilhamento/?data={data_str}")

    if not tel.startswith('55'):
        tel = f"55{tel}"

    return redirect(f"https://wa.me/{tel}?text={quote(texto)}")


@login_required
def encilhamento_pdf(request):
    empresa  = getattr(request, "empresa", request.user.perfil.empresa)
    data_str = request.GET.get('data', '')
    aulas, data_selecionada = _get_aulas_encilhamento(empresa, data_str)

    response = HttpResponse(content_type='application/pdf')
    data_fmt = data_selecionada.strftime('%d-%m-%Y')
    response['Content-Disposition'] = f'attachment; filename="Encilhamento_{data_fmt}.pdf"'

    p    = canvas.Canvas(response, pagesize=A4)
    W, H = A4

    COR_HDR    = (0.06, 0.09, 0.14)
    COR_BRANCO = (1.0,  1.0,  1.0)
    COR_CINZA  = (0.55, 0.60, 0.70)
    COR_INDIGO = (0.38, 0.40, 0.95)
    COR_AMBER  = (0.80, 0.55, 0.10)
    COR_VERDE  = (0.13, 0.70, 0.37)
    COR_CARD   = (0.10, 0.13, 0.18)
    COR_DARK   = (0.07, 0.09, 0.13)

    pagina = 1

    def cabecalho(p, pagina):
        p.setFillColorRGB(*COR_HDR)
        p.rect(0, H - 70, W, 70, fill=True, stroke=False)
        p.setFillColorRGB(*COR_BRANCO)
        p.setFont("Helvetica-Bold", 15)
        p.drawString(30, H - 32, f"GUIA DE ENCILHAMENTO — {empresa.nome.upper()}")
        p.setFont("Helvetica", 9)
        p.setFillColorRGB(*COR_CINZA)
        dias = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
        ds   = dias[data_selecionada.weekday()]
        p.drawString(30, H - 50, f"{ds}, {data_selecionada.strftime('%d/%m/%Y')}   |   Página {pagina}")
        p.drawRightString(W - 30, H - 50, f"Total: {aulas.count()} aula(s)")
        return H - 85

    y = cabecalho(p, pagina)

    if not aulas:
        p.setFillColorRGB(*COR_CINZA)
        p.setFont("Helvetica", 11)
        p.drawCentredString(W / 2, H / 2, "Nenhuma aula programada para este dia.")
        p.save()
        return response

    for aula in aulas:
        c      = aula.cavalo
        altura = 115 + (20 if aula.relatorio_treino else 0)

        if y - altura < 40:
            p.showPage()
            pagina += 1
            y = cabecalho(p, pagina)

        # Fundo card
        p.setFillColorRGB(*COR_CARD)
        p.roundRect(25, y - altura, W - 50, altura, 8, fill=True, stroke=False)

        # Borda lateral
        p.setFillColorRGB(*(COR_VERDE if c.categoria == 'HOTELARIA' else COR_INDIGO))
        p.rect(25, y - altura, 6, altura, fill=True, stroke=False)

        # Horário
        p.setFillColorRGB(*COR_INDIGO)
        p.roundRect(36, y - 24, 52, 20, 4, fill=True, stroke=False)
        p.setFillColorRGB(*COR_BRANCO)
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(62, y - 16, aula.data_hora.strftime('%H:%M'))

        # Local
        p.setFont("Helvetica", 8)
        p.setFillColorRGB(*COR_CINZA)
        p.drawString(96, y - 16, f"| {aula.get_local_display()}")

        # Concluída
        if aula.concluida:
            p.setFillColorRGB(*COR_VERDE)
            p.setFont("Helvetica-Bold", 7)
            p.drawRightString(W - 35, y - 16, "CONCLUÍDA")

        # Aluno
        p.setFillColorRGB(*COR_BRANCO)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(36, y - 40, aula.aluno.nome.upper())

        if aula.instrutor:
            p.setFont("Helvetica", 8)
            p.setFillColorRGB(*COR_CINZA)
            nome_inst = aula.instrutor.user.get_full_name() or aula.instrutor.user.username
            p.drawString(36, y - 52, f"Prof.: {nome_inst}")

        # Bloco cavalo
        p.setFillColorRGB(*COR_DARK)
        p.roundRect(34, y - 80, W - 68, 24, 4, fill=True, stroke=False)
        p.setFillColorRGB(*COR_INDIGO)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(42, y - 72, f"{c.nome.upper()}")
        local = (
            f"Baia {c.baia.numero}" if c.baia
            else (c.piquete.nome if c.piquete else "—")
        )
        p.setFont("Helvetica", 9)
        p.setFillColorRGB(*COR_CINZA)
        p.drawString(160, y - 72, f"|  {local}")
        p.setFillColorRGB(*(COR_VERDE if c.categoria == 'HOTELARIA' else COR_INDIGO))
        p.setFont("Helvetica-Bold", 8)
        p.drawRightString(W - 38, y - 72, c.get_categoria_display().upper())

        # Sela
        p.setFillColorRGB(*COR_AMBER)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(36, y - 92, "SELA:")
        p.setFont("Helvetica", 9)
        p.setFillColorRGB(*COR_BRANCO)
        p.drawString(70, y - 92, c.tipo_sela or "Padrão escola")

        # Cabeçada
        p.setFillColorRGB(0.24, 0.48, 1.0)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(36, y - 104, "CABEÇADA:")
        p.setFont("Helvetica", 9)
        p.setFillColorRGB(*COR_BRANCO)
        p.drawString(88, y - 104, c.tipo_cabecada or "Padrão escola")

        # Material
        if c.material_proprio:
            p.setFillColorRGB(*COR_AMBER)
            p.setFont("Helvetica-Bold", 8)
            p.drawRightString(W - 35, y - 92, "MATERIAL PROPRIO")
        else:
            p.setFillColorRGB(*COR_VERDE)
            p.setFont("Helvetica-Bold", 8)
            p.drawRightString(W - 35, y - 92, "MATERIAL ESCOLA")

        # Observações
        if aula.relatorio_treino:
            p.setFillColorRGB(*COR_CINZA)
            p.setFont("Helvetica-Oblique", 8)
            p.drawString(36, y - 116, f"Obs: {aula.relatorio_treino[:90]}")

        y -= altura + 10

    p.save()
    return response


# ── Manejo em Massa ───────────────────────────────────────────────────────────

@login_required
def manejo_em_massa(request):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    if request.method == "POST":
        procedimento   = request.POST.get("procedimento")
        data_aplicacao = request.POST.get("data")
        ids_cavalos    = request.POST.getlist("cavalos_selecionados")
        cavalos_alvos  = Cavalo.objects.filter(id__in=ids_cavalos, empresa=empresa)

        campos_manejo = {
            "Vacinacao":     "ultima_vacina",
            "Vermifugacao":  "ultimo_vermifugo",
            "Ferrageamento": "ultimo_ferrageamento",
            "Casqueamento":  "ultimo_casqueamento",
        }
        nome_campo = campos_manejo.get(procedimento)
        if nome_campo and data_aplicacao:
            cavalos_alvos.update(**{nome_campo: data_aplicacao})
            messages.success(request, f"{procedimento} aplicado a {cavalos_alvos.count()} animais.")
        return redirect("dashboard")

    cavalos_lista = Cavalo.objects.filter(empresa=empresa).select_related('baia')
    return render(request, "gateagora/manejo_massa.html", {"cavalos": cavalos_lista})
