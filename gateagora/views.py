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
from django.db.models import Case, When, IntegerField, Value

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, black, grey
from django.utils import timezone
from django.utils.timezone import localtime

from reportlab.lib import colors
from urllib.parse import quote  # se precisar

from .models import (
    Empresa, Perfil, Aluno, Cavalo, Baia, Piquete, Aula,
    ItemEstoque, MovimentacaoFinanceira, MovimentacaoEstoque, DocumentoCavalo,
    ConfigPrazoManejo, Fatura, ItemFatura
)

BRAND_NAME = "Gate 4"

# Rodapé padrão para TODAS as mensagens WhatsApp do sistema
MSG_RODAPE = "\n📲 _Enviado via *Gate 4 — Gestão de Haras e Hípicas*_ 🐎"

# Emojis por tipo de item de fatura — usado em mensagens WhatsApp e PDF
EMOJIS_TIPO_FATURA = {
    'HOTELARIA':     '🏨',
    'AULA':          '🎓',
    'VETERINARIO':   '🩺',
    'VERMIFUGO':     '💊',
    'CASQUEIO':      '🦶',
    'FERRAGEAMENTO': '🦶',
    'OUTROS':        '🧪',
}


# ── Login ─────────────────────────────────────────────────────────────────────

class CustomLoginView(LoginView):
    template_name = "gateagora/login.html"
    form_class    = AuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        # Se o perfil for Aluno, vai direto para encilhamento
        try:
            if user.perfil.cargo == 'Aluno':
                return '/encilhamento/'
        except:
            pass
        return '/'  # demais cargos vão para o dashboard

def get_pdf_colors(request):
    # SEMPRE LIGHT PARA ECONOMIZAR TINTA
    return {
        "bg": (1, 1, 1),           # branco
        "text": (0, 0, 0),         # preto
        "primary": (0.2, 0.2, 0.2) # cinza escuro
    }

# ── Utilitários ───────────────────────────────────────────────────────────────

def formata_real(valor):
    try:
        val = float(valor) if valor else 0.0
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

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

def _montar_msg_fatura_whatsapp(fatura, empresa):
    """
    Monta mensagem WhatsApp detalhada da fatura, incluindo itens e cavalos.
    """
    total = fatura.total
    itens = list(fatura.itens.all().select_related('cavalo'))  # otimizado

    linhas = [
        f"🐎 *{empresa.nome}* — Lembrete Financeiro",
        "",
        f"Olá, *{fatura.aluno.nome}*! Tudo bem?",
        "",
        "🧾 *Detalhamento da sua fatura*",
        "",
    ]

    if itens:
        for item in itens:
            emoji = EMOJIS_TIPO_FATURA.get(item.tipo, '•')
            tipo_display = item.get_tipo_display()

            # Linha principal do item
            linha_item = f"  {emoji} {tipo_display}: R$ {item.valor:,.2f}"
            linhas.append(linha_item)

            # Descrição adicional (se existir)
            if item.descricao:
                linhas.append(f"      _{item.descricao}_")

            # Cavalo relacionado (muito importante!)
            if item.cavalo:
                linhas.append(f"      🐴 *Cavalo:* {item.cavalo.nome}")
            
            # Linha em branco para separar itens
            linhas.append("")

    else:
        # Fallback quando não tem itens detalhados
        linhas.append(f"  💰 Total: R$ {total:,.2f}")
        linhas.append("")

    # Rodapé da mensagem
    linhas += [
        f"💰 *Total a pagar:* R$ {total:,.2f}",
        f"📅 Vencimento: *{fatura.data_vencimento.strftime('%d/%m/%Y')}*",
        "",
        "✅ Caso o pagamento já tenha sido realizado, por favor, envie o comprovante por aqui 😊",
        "",
        "Ficamos à disposição para qualquer dúvida.",
        "",
        f"Atenciosamente,",
        f"*{empresa.nome}*",
        MSG_RODAPE,
    ]

    return "\n".join(linhas)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    # 1. Identifica a empresa (vinda do middleware)
    empresa = request.empresa
    hoje = date.today()
    mes_selecionado = int(request.GET.get('mes', hoje.month))
    ano_selecionado = int(request.GET.get('ano', hoje.year))

    print(f"DEBUG: Filtrando para o mês {mes_selecionado} de {ano_selecionado}")

    # 2. Verificação de Segurança
    if not empresa and not request.user.is_superuser:
        try:
            return redirect('/admin/gateagora/perfil/add/')
        except:
            return redirect('/admin/')

    # 3. Fluxo normal do sistema
    hoje = timezone.localdate()

        # CONTAS A RECEBER
    faturas_criticas = Fatura.objects.filter(
        empresa=empresa,
        status__in=['PENDENTE', 'ATRASADO'],
        data_vencimento__lte=hoje
    ).prefetch_related('itens').select_related('aluno').order_by('data_vencimento')

    listagem_cobranca = []
    for fatura in faturas_criticas:
        # Tenta o total via ItemFatura primeiro
        v_total = fatura.total

        # Fallback: se nao ha itens, usa o campo valor direto da Fatura
        if v_total == Decimal("0.00") and getattr(fatura, "valor", None):
            v_total = Decimal(str(fatura.valor))

        # Fallback final: hotelaria + aulas concluidas do mes de referencia
        if v_total == Decimal("0.00"):
            cavalos_aluno = Cavalo.objects.filter(proprietario=fatura.aluno, empresa=empresa)
            v_hotel = sum(Decimal(str(c.mensalidade_baia or 0)) for c in cavalos_aluno)
            n_aulas = Aula.objects.filter(
                aluno=fatura.aluno, empresa=empresa, concluida=True,
                data_hora__year=fatura.data_vencimento.year,
                data_hora__month=fatura.data_vencimento.month,
            ).count()
            v_total = v_hotel + Decimal(str(n_aulas)) * Decimal(str(fatura.aluno.valor_aula or 0))

        tel_c = "".join(filter(str.isdigit, str(fatura.aluno.telefone or "")))
        link_zap = f"https://wa.me/55{tel_c}?text={quote(_montar_msg_fatura_whatsapp(fatura, empresa))}" if tel_c else "#"

        listagem_cobranca.append({
            "fatura_id":  fatura.id,
            "aluno":      fatura.aluno.nome,
            "vencimento": fatura.data_vencimento,
            "valor":      formata_real(v_total),
            "atrasado":   fatura.data_vencimento < hoje,
            "link_zap":   link_zap,
        })


    # ── 1) Próximas aulas de hoje ──────────────────────────────────────────────
    proximas_aulas = (
        Aula.objects
        .filter(empresa=empresa, concluida=False, data_hora__date=hoje)
        .select_related('aluno', 'cavalo')
        .order_by('data_hora')
    )

    # ── 2) Alertas e Estoque Unificado ────────────────────────────────────────
    
    # 1. Busca TODOS os itens, classificando por prioridade
    estoque_todos = (
        ItemEstoque.objects
        .filter(empresa=empresa)
        .annotate(
            prioridade=Case(
                When(quantidade_atual__lte=F('alerta_minimo'), then=Value(0)),      # CRÍTICO (Vermelho)
                When(quantidade_atual__lte=F('alerta_minimo') * 2, then=Value(1)),  # ATENÇÃO (Amarelo)
                default=Value(2),                                                  # OK (Verde)
                output_field=IntegerField(),
            )
        )
        .order_by('prioridade', 'quantidade_atual')
    )

    # 2. Contador para o badge de alerta no topo do Dashboard
    estoque_baixo_count = sum(1 for item in estoque_todos if item.prioridade == 0)

    # 3. Preparação dos dados para o GRÁFICO (Chart.js)
    # Aqui garantimos que todos os dados vão para o gráfico, não só os críticos
    estoque_labels = []
    estoque_valores = []
    estoque_cores = []

    for item in estoque_todos:
        estoque_labels.append(item.nome)
        estoque_valores.append(float(item.quantidade_atual))
        
        # Define a cor da barra no gráfico baseada na prioridade calculada
        if item.prioridade == 0:
            estoque_cores.append('#ef4444') # Vermelho tailwind
        elif item.prioridade == 1:
            estoque_cores.append('#f59e0b') # Amarelo tailwind
        else:
            estoque_cores.append('#10b981') # Verde tailwind

    # 4. Documentos vencendo (Manteve-se igual)
    janela_venc = hoje + timedelta(days=30)
    docs_vencendo = (
        DocumentoCavalo.objects
        .filter(cavalo__empresa=empresa, data_validade__range=[hoje, janela_venc])
        .select_related('cavalo')
        .order_by('data_validade')
    )

    # Prazos configuráveis por empresa (usa defaults se não cadastrado)
    try:
        cfg = ConfigPrazoManejo.objects.get(empresa=request.empresa)
        prazo_vacina        = cfg.prazo_vacina
        prazo_vermifugo     = cfg.prazo_vermifugo
        prazo_ferrageamento = cfg.prazo_ferrageamento
        prazo_casqueamento  = cfg.prazo_casqueamento
    except ConfigPrazoManejo.DoesNotExist:
        prazo_vacina        = 365
        prazo_vermifugo     = 90
        prazo_ferrageamento = 60
        prazo_casqueamento  = 60

    def _dias_atraso(data_campo):
        if not data_campo:
            return 9999
        return (hoje - data_campo).days

    def _cavalo_em_alerta(c):
        if c.status_saude != 'Saudável':
            return True
        if _dias_atraso(c.ultima_vacina)    > prazo_vacina:    return True
        if _dias_atraso(c.ultimo_vermifugo) > prazo_vermifugo: return True
        if c.usa_ferradura == 'SIM':
            if _dias_atraso(c.ultimo_ferrageamento) > prazo_ferrageamento: return True
        else:
            if _dias_atraso(c.ultimo_casqueamento) > prazo_casqueamento: return True
        return False

    def _score_criticidade(c):
        atraso_casco = (
            max(0, _dias_atraso(c.ultimo_ferrageamento) - prazo_ferrageamento)
            if c.usa_ferradura == 'SIM'
            else max(0, _dias_atraso(c.ultimo_casqueamento) - prazo_casqueamento)
        )
        atrasos = [
            max(0, _dias_atraso(c.ultima_vacina)    - prazo_vacina),
            max(0, _dias_atraso(c.ultimo_vermifugo) - prazo_vermifugo),
            atraso_casco,
        ]
        bonus_status = 10000 if c.status_saude != 'Saudável' else 0
        return sum(atrasos) + bonus_status

    todos_cavalos = (
        Cavalo.objects
        .filter(empresa=empresa)
        .select_related('proprietario')
    )

    cavalos_alerta_lista = sorted(
        [c for c in todos_cavalos if _cavalo_em_alerta(c)],
        key=_score_criticidade,
        reverse=True
    )

    for c in cavalos_alerta_lista:
        c.alerta_detalhes = []
        if c.status_saude != 'Saudável':
            c.alerta_detalhes.append(f"Status: {c.status_saude}")
        if _dias_atraso(c.ultima_vacina) > prazo_vacina:
            d = _dias_atraso(c.ultima_vacina) - prazo_vacina
            c.alerta_detalhes.append(f"Vacina {d}d atrasada")
        if _dias_atraso(c.ultimo_vermifugo) > prazo_vermifugo:
            d = _dias_atraso(c.ultimo_vermifugo) - prazo_vermifugo
            c.alerta_detalhes.append(f"Vermifugo {d}d atrasado")
        if c.usa_ferradura == 'SIM':
            if _dias_atraso(c.ultimo_ferrageamento) > prazo_ferrageamento:
                d = _dias_atraso(c.ultimo_ferrageamento) - prazo_ferrageamento
                c.alerta_detalhes.append(f"Ferrageamento {d}d atrasado")
        else:
            if _dias_atraso(c.ultimo_casqueamento) > prazo_casqueamento:
                d = _dias_atraso(c.ultimo_casqueamento) - prazo_casqueamento
                c.alerta_detalhes.append(f"Casqueamento {d}d atrasado")

    # ── 3) KPIs ───────────────────────────────────────────────────────────────
    total_baias = Baia.objects.filter(empresa=empresa).count()
    baias_ocupadas = Baia.objects.filter(empresa=empresa, status='Ocupada').count()
    porcentagem_ocupacao = int((baias_ocupadas / total_baias * 100)) if total_baias else 0

    stats = {
        "baias_ocupadas":       baias_ocupadas,
        "baias_livres":         total_baias - baias_ocupadas,
        "total_baias":          total_baias,
        "porcentagem_ocupacao": porcentagem_ocupacao,
        "cavalos_alerta":       len(cavalos_alerta_lista),
        "total_cavalos":        Cavalo.objects.filter(empresa=request.empresa).count(),
        "vacinados":            Cavalo.objects.filter(
            empresa=empresa,
            ultima_vacina__gte=hoje - timedelta(days=365)
        ).count(),
    }

    # ── 4) Relatório de faturamento do mês (via ItemFatura) ───────────────────
    meses_pt = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }
    mes_atual_str = f"{meses_pt[hoje.month]}/{hoje.year}"

    # FATURAMENTO DO MÊS
    faturas_mes = Fatura.objects.filter(
        empresa=empresa,
        data_vencimento__year=ano_selecionado,
        data_vencimento__month=mes_selecionado,
    ).prefetch_related('itens').select_related('aluno')

    relatorio = []
    receita_total_prevista = ItemFatura.objects.filter(
        fatura__empresa=empresa,
        fatura__data_vencimento__year=ano_selecionado,
        fatura__data_vencimento__month=mes_selecionado
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    for fatura in faturas_mes:
        # Pega APENAS a soma real dos itens detalhados desta fatura
        v_fatura = fatura.total 

        # Montagem do link de WhatsApp
        tel = "".join(filter(str.isdigit, str(fatura.aluno.telefone or "")))
        msg = _montar_msg_fatura_whatsapp(fatura, empresa)
        link_wa = f"https://wa.me/55{tel}?text={quote(msg)}" if tel else "#"

        relatorio.append({
            "aluno": fatura.aluno,
            "valor": float(v_fatura),
            "whatsapp": link_wa,
        })
    
    # IMPORTANTE: Note que NÃO existe mais a linha "receita_total_prevista += v_fatura" aqui.
    # Isso impede que o valor seja somado duas vezes ou que use valores "inventados".

    # ── 5) Financeiro mensal para gráfico ─────────────────────────────────────
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

    eixo_meses = _iter_ultimos_meses(hoje, 6)
    labels_meses = []
    dados_receita = []
    dados_despesa = []
    dados_lucro = []

    for m in eixo_meses:
        labels_meses.append(f"{meses_pt[m.month]}/{str(m.year)[2:]}")
        rec, desp = dados_mapeados.get(m, (0.0, 0.0))
        dados_receita.append(rec)
        dados_despesa.append(desp)
        dados_lucro.append(rec - desp)

    # ── 6) Ranking de treinos por cavalo ──────────────────────────────────────
    periodo = request.GET.get('periodo', 'mes')

    if periodo == '30':
        data_inicio = hoje - timedelta(days=30)
        periodo_label = 'Últimos 30 dias'
    elif periodo == '90':
        data_inicio = hoje - timedelta(days=90)
        periodo_label = 'Últimos 3 meses'
    else:
        periodo = 'mes'
        data_inicio = hoje.replace(day=1)
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
        ),
        receita_periodo=Coalesce(
            Sum(
                'itemfatura__valor',
                filter=Q(
                    itemfatura__tipo='AULA',
                    itemfatura__fatura__empresa=empresa,
                    itemfatura__data__gte=data_inicio,
                    itemfatura__data__lte=hoje,
                )
            ),
            Value(0, output_field=DecimalField())
        ),
    )
    .order_by('-treinos_periodo', 'nome')
)

    com_treino = [c for c in ranking_cavalos if c.treinos_periodo > 0]
    sem_treino = [c.nome for c in ranking_cavalos if c.treinos_periodo == 0]
    ranking_labels = [c.nome for c in com_treino]
    ranking_dados = [c.treinos_periodo for c in com_treino]
    ranking_receita = [float(c.receita_periodo) for c in com_treino]

    LIMITE_TREINOS_MES = 20
    limite = LIMITE_TREINOS_MES if periodo in ('mes', '30') else LIMITE_TREINOS_MES * 3

    # ── 7) Relatório completo de inadimplência (todas as faturas abertas) ─────
    faturas_abertas = (
        Fatura.objects
        .filter(empresa=request.empresa, status__in=['PENDENTE', 'ATRASADO'])
        .select_related('aluno')
        .prefetch_related('itens__cavalo')
        .order_by('data_vencimento')
    )

    relatorio_financeiro = []
    for fatura in faturas_abertas:
        total = fatura.total
        tel = ''.join(filter(str.isdigit, str(fatura.aluno.telefone or '')))
        link_wa = "#"
        if tel:
            if not tel.startswith('55'):
                tel = f"55{tel}"
            msg = _montar_msg_fatura_whatsapp(fatura, empresa)
            link_wa = f"https://wa.me/{tel}?text={quote(msg)}"

        relatorio_financeiro.append({
            "fatura":   fatura,
            "valor":    formata_real(total),
            "whatsapp": link_wa,
            "atrasada": fatura.data_vencimento < hoje,
        })

    # ── 8) Receita por categoria (ItemFatura do mes) ─────────────────────────
    LABELS_TIPO = {
        'HOTELARIA':     '🏨 Hotelaria',
        'AULA':          '🎓 Aulas',
        'VETERINARIO':   '🩺 Veterinário',
        'VERMIFUGO':     '💊 Vermífugo',
        'CASQUEIO':      '🦶 Casqueio',
        'FERRAGEAMENTO': '🦶 Ferrageamento',
        'OUTROS':        '🧪 Outros',
    }
    try:
        receita_cat_qs = (
            ItemFatura.objects
            .filter(
                fatura__empresa=empresa,
                # AGORA FILTRA PELO MÊS QUE VOCÊ CLICAR NO DASHBOARD:
                fatura__data_vencimento__year=ano_selecionado, 
                fatura__data_vencimento__month=mes_selecionado,
            )
            .values('tipo')
            .annotate(total=Sum('valor'))
            .order_by('-total')
        )
        receita_por_tipo_labels  = [LABELS_TIPO.get(r['tipo'], r['tipo']) for r in receita_cat_qs]
        receita_por_tipo_valores = [float(r['total']) for r in receita_cat_qs]
    except Exception as e: # Adicionei o 'as e' para o log não dar erro
        import logging
        logging.getLogger(__name__).error("Erro no gráfico de receitas: %s", e, exc_info=True)
        receita_por_tipo_labels  = ["Sem dados no período"]
        receita_por_tipo_valores = [0]

    # ── 9) Contexto final ─────────────────────────────────────────────────────
    context = {
        "brand_name":               BRAND_NAME,
        "empresa":                  empresa,
        "hoje":                     hoje,
        "mes_selecionado":          mes_selecionado,
        "ano_selecionado":          ano_selecionado,
        "proximas_aulas":           proximas_aulas,
        "listagem_cobranca":        listagem_cobranca,
        "relatorio_financeiro":     relatorio_financeiro,
        "estoque_baixo_count":      estoque_baixo_count,
        "estoque_todos":            estoque_todos,
        "estoque_labels":           json.dumps(estoque_labels, ensure_ascii=False),
        "estoque_valores":          json.dumps(estoque_valores),
        "estoque_cores":            json.dumps(estoque_cores),
        "docs_vencendo":            docs_vencendo,
        "cavalos_alerta_lista":     cavalos_alerta_lista,
        "stats":                    stats,
        "relatorio":                relatorio,
        "receita_total_prevista":   float(receita_total_prevista),
        "labels_meses":             json.dumps(labels_meses),
        "dados_receita":            json.dumps(dados_receita),
        "dados_despesa":            json.dumps(dados_despesa),
        "dados_lucro":              json.dumps(dados_lucro),
        "ranking_cavalos_labels":   json.dumps(ranking_labels, ensure_ascii=False),
        "ranking_cavalos_dados":    json.dumps(ranking_dados),
        "ranking_receita":          json.dumps(ranking_receita),
        "cavalos_sem_treino":       sem_treino,
        "limite_treinos_mes":       limite,
        "periodo_label":            periodo_label,
        "periodo_atual":            periodo,
        "receita_por_tipo_labels":  json.dumps(receita_por_tipo_labels,  ensure_ascii=False),
        "receita_por_tipo_valores": json.dumps(receita_por_tipo_valores),
    }

    return render(request, "gateagora/dashboard.html", context)

# ── Concluir Aula ─────────────────────────────────────────────────────────────

@login_required
def concluir_aula(request, aula_id):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    aula = get_object_or_404(Aula, id=aula_id, empresa=empresa)

    if not aula.concluida:
        aula.concluida = True
        aula.save(update_fields=['concluida'])

        # Busca ou cria a fatura do mês do aluno
        from datetime import date
        hoje = timezone.localdate()
        venc = hoje.replace(day=28)  # ou o dia padrão que vocês usam

        fatura, _ = Fatura.objects.get_or_create(
            empresa=empresa,
            aluno=aula.aluno,
            status='PENDENTE',
            data_vencimento__year=hoje.year,
            data_vencimento__month=hoje.month,
            defaults={'data_vencimento': venc},
        )

        # Cria o item de aula vinculado ao cavalo
        ItemFatura.objects.create(
            fatura=fatura,
            tipo='AULA',
            cavalo=aula.cavalo,
            descricao=f"Aula {aula.get_tipo_display()} — {hoje.strftime('%d/%m/%Y')}",
            valor=aula.aluno.valor_aula,
            data=hoje,
        )

    messages.success(request, f"Aula de {aula.aluno.nome} concluída e lançada na fatura!")
    return redirect("dashboard")


# ── PDF Fatura ────────────────────────────────────────────────────────────────

@login_required
def gerar_relatorio_pdf(request, aluno_id):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    aluno   = get_object_or_404(Aluno, id=aluno_id, empresa=empresa)

    hoje = timezone.localdate()
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    mes_str = f"{meses_pt[hoje.month]}/{hoje.year}"

    # Busca a fatura do mês atual
    fatura_mes = (
        Fatura.objects
        .filter(
            empresa=empresa,
            aluno=aluno,
            data_vencimento__year=hoje.year,
            data_vencimento__month=hoje.month,
        )
        .prefetch_related('itens__cavalo')
        .first()
    )

    itens = list(fatura_mes.itens.all()) if fatura_mes else []
    total = fatura_mes.total if fatura_mes else Decimal('0.00')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="Fatura_{aluno.nome.replace(" ", "_")}_{hoje.month}_{hoje.year}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=A4)
    W, H = A4
    y = H - 80

    # ====================== CABEÇALHO ======================
    # Fundo suave azul claro
    p.setFillColorRGB(0.95, 0.97, 1.0)   # Azul muito claro
    p.rect(0, H - 100, W, 100, fill=True, stroke=False)

    p.setFillColorRGB(0.1, 0.1, 0.25)    # Azul escuro elegante
    p.setFont("Helvetica-Bold", 22)
    p.drawString(45, H - 45, empresa.nome.upper())

    p.setFont("Helvetica", 10)
    p.setFillColorRGB(0.4, 0.4, 0.5)
    p.drawString(45, H - 65, f"FATURA DE MENSALIDADE — {mes_str.upper()}")
    p.drawRightString(W - 45, H - 45, f"Emitido em: {hoje.strftime('%d/%m/%Y')}")

    # ====================== DADOS DO CLIENTE ======================
    y = H - 150
    p.setFillColorRGB(0.95, 0.97, 1.0)
    p.roundRect(35, y - 25, W - 70, 55, 8, fill=True, stroke=False)

    p.setFillColorRGB(0.12, 0.12, 0.25)
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y + 18, f"CLIENTE: {aluno.nome.upper()}")

    p.setFont("Helvetica", 10)
    p.setFillColorRGB(0.35, 0.35, 0.45)
    if aluno.telefone:
        p.drawString(50, y + 3, f"Telefone: {aluno.telefone}")

    y -= 75

    # ====================== TÍTULO DA TABELA ======================
    p.setFillColorRGB(0.15, 0.35, 0.65)   # Azul médio suave
    p.rect(35, y - 5, W - 70, 28, fill=True, stroke=False)

    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y + 10, "DESCRIÇÃO DO SERVIÇO")
    p.drawRightString(W - 50, y + 10, "VALOR")

    y -= 35

    # ====================== ITENS DA FATURA ======================
    if itens:
        for item in itens:
            emoji = EMOJIS_TIPO_FATURA.get(item.tipo, '•')
            tipo_display = item.get_tipo_display()

            # Fundo claro para cada item
            p.setFillColorRGB(0.98, 0.98, 0.99)
            p.rect(35, y - 8, W - 70, 26, fill=True, stroke=False)

            # Emoji + Tipo
            p.setFillColorRGB(0.1, 0.1, 0.25)
            p.setFont("Helvetica-Bold", 10.5)
            p.drawString(50, y + 8, f"{emoji}  {tipo_display}")

            # Valor
            p.setFont("Helvetica-Bold", 10.5)
            p.drawRightString(W - 50, y + 8, f"R$ {float(item.valor):,.2f}")

            y -= 26

            # Descrição (se houver)
            if item.descricao:
                p.setFillColorRGB(0.4, 0.45, 0.55)
                p.setFont("Helvetica", 9)
                p.drawString(65, y + 8, f"   {item.descricao}")
                y -= 14

            # Cavalo (se houver)
            if item.cavalo:
                p.setFillColorRGB(0.35, 0.45, 0.65)
                p.setFont("Helvetica", 9)
                p.drawString(65, y + 8, f"   🐴 {item.cavalo.nome}")
                y -= 14

            y -= 8   # Espaçamento entre itens

    else:
        # Fallback sem itens
        p.setFillColorRGB(0.98, 0.98, 0.99)
        p.rect(35, y - 8, W - 70, 26, fill=True, stroke=False)
        p.setFillColorRGB(0.1, 0.1, 0.25)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y + 8, "Serviços prestados no mês")
        p.drawRightString(W - 50, y + 8, f"R$ {float(total):,.2f}")
        y -= 40

    # ====================== TOTAL ======================
    y -= 20
    p.setFillColorRGB(0.05, 0.55, 0.35)   # Verde suave elegante
    p.roundRect(35, y - 12, W - 70, 42, 10, fill=True, stroke=False)

    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 15)
    p.drawString(50, y + 13, "TOTAL A PAGAR")

    p.setFont("Helvetica-Bold", 16)
    p.drawRightString(W - 50, y + 13, f"R$ {float(total):,.2f}")

    # Rodapé informativo
    p.setFillColorRGB(0.5, 0.5, 0.55)
    p.setFont("Helvetica", 8)
    p.drawCentredString(W/2, 40, "Obrigado por confiar no nosso trabalho • Pagamento via PIX ou dinheiro")

    p.showPage()
    p.save()
    return response


# ── PDF Guia de Trato ─────────────────────────────────────────────────────────

@login_required
def gerar_ficha_trato_pdf(request):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Guia_Trato_{date.today().strftime("%d-%m-%Y")}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Cores para impressão
    COR_TITULO      = HexColor("#1e40af")
    COR_CABECALHO   = HexColor("#f8fafc")
    COR_LINHA       = HexColor("#e2e8f0")
    COR_RACAO       = HexColor("#166534")
    COR_VOLUMOSO    = HexColor("#14532d")
    COR_SUPLEMENTO  = HexColor("#854d0e")
    COR_TEXTO       = HexColor("#0f172a")
    COR_CINZA       = HexColor("#475569")

    pagina = 1

    def cabecalho():
        nonlocal pagina
        p.setFillColor(COR_CABECALHO)
        p.rect(0, height - 82, width, 82, fill=True, stroke=False)

        p.setFillColor(COR_TITULO)
        p.setFont("Helvetica-Bold", 17)
        p.drawString(45, height - 37, f"GUIA DE TRATO DIÁRIO — {empresa.nome.upper()}")

        p.setFont("Helvetica", 9)
        p.setFillColor(COR_CINZA)
        p.drawString(45, height - 55, f"Data: {date.today().strftime('%d/%m/%Y')}   •   Página {pagina}")

        p.setStrokeColor(COR_LINHA)
        p.line(45, height - 68, width - 45, height - 68)

        return height - 98

    y = cabecalho()

    cavalos = (
        Cavalo.objects
        .filter(empresa=empresa)
        .select_related('baia', 'piquete', 'proprietario')
        .order_by('baia__numero', 'nome')
    )

    for cavalo in cavalos:
        # === Altura DINÂMICA e compacta ===
        altura = 58  # altura base reduzida

        if cavalo.racao_tipo or cavalo.racao_qtd_manha or cavalo.racao_qtd_noite:
            altura += 16
        if cavalo.feno_tipo or cavalo.feno_qtd:
            altura += 16
        if cavalo.complemento_nutricional:
            altura += 17

        if y - altura < 55:
            p.showPage()
            pagina += 1
            y = cabecalho()

        # Card compacto
        p.setFillColor(HexColor("#ffffff"))
        p.setStrokeColor(COR_LINHA)
        p.roundRect(38, y - altura, width - 76, altura, 8, fill=True, stroke=True)

        # Barra lateral
        cor_barra = HexColor("#1e40af") if getattr(cavalo, 'categoria', None) == 'HOTELARIA' else HexColor("#166534")
        p.setFillColor(cor_barra)
        p.rect(38, y - altura, 7, altura, fill=True, stroke=False)

        # Nome do Cavalo + Baia/Piquete na mesma linha
        p.setFillColor(COR_TEXTO)
        p.setFont("Helvetica-Bold", 13.5)

        local = f"Baia {cavalo.baia.numero}" if cavalo.baia else \
                (f"Piquete: {cavalo.piquete.nome}" if cavalo.piquete else "Solto")

        p.drawString(55, y - 23, f"{cavalo.nome.upper()}  —  {local}")

        linha_y = y - 41

        # ====================== RAÇÃO ======================
        if cavalo.racao_tipo or cavalo.racao_qtd_manha or cavalo.racao_qtd_noite:
            p.setFillColor(COR_RACAO)
            p.setFont("Helvetica-Bold", 9)
            p.drawString(55, linha_y, "RAÇÃO")

            p.setFillColor(COR_TEXTO)
            p.setFont("Helvetica", 9)
            partes = []
            if cavalo.racao_tipo:
                partes.append(cavalo.racao_tipo)
            if cavalo.racao_qtd_manha:
                partes.append(f"Manhã: {cavalo.racao_qtd_manha}")
            if cavalo.racao_qtd_noite:
                partes.append(f"Noite: {cavalo.racao_qtd_noite}")

            p.drawString(115, linha_y, " • ".join(partes))
            linha_y -= 16

        # ====================== VOLUMOSO ======================
        if cavalo.feno_tipo or cavalo.feno_qtd:
            p.setFillColor(COR_VOLUMOSO)
            p.setFont("Helvetica-Bold", 9)
            p.drawString(55, linha_y, "VOLUMOSO")

            p.setFillColor(COR_TEXTO)
            p.setFont("Helvetica", 9)

            tipo = (cavalo.feno_tipo or "").upper()
            qtd = cavalo.feno_qtd or ""

            if "ALFALFA" in tipo or "ALF" in tipo:
                vol_text = f"Alfafa → {qtd} fatias"
            elif "FENO" in tipo:
                vol_text = f"Feno → {qtd} fatias"
            else:
                vol_text = f"{cavalo.feno_tipo or 'Volumoso'} → {qtd} fatias"

            p.drawString(115, linha_y, vol_text)
            linha_y -= 16

        # ====================== SUPLEMENTO ======================
        if cavalo.complemento_nutricional:
            p.setFillColor(COR_SUPLEMENTO)
            p.setFont("Helvetica-Bold", 9)
            p.drawString(55, linha_y, "SUPLEMENTO")

            p.setFillColor(COR_TEXTO)
            p.setFont("Helvetica", 9)
            p.drawString(130, linha_y, str(cavalo.complemento_nutricional)[:110])

        y -= altura + 10   # Espaçamento reduzido entre cards

    # Rodapé
    p.setFont("Helvetica", 8)
    p.setFillColor(COR_CINZA)
    p.drawString(45, 35, "• Fracionar fardos em fatias uniformes • Verificar sobras do dia anterior")
    p.drawString(45, 25, f"Gate 4 • Gerado em {date.today().strftime('%d/%m/%Y %H:%M')}")

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
    empresa  = request.empresa
    if empresa is None:
        try:
            empresa = request.user.perfil.empresa
        except:
            empresa = None

    data_str = request.GET.get('data', '')

    contatos_funcionarios = []
    funcionarios = (
        Perfil.objects
        .filter(empresa=empresa)
        .select_related('user')
        .order_by('user__first_name')
    )
    for f in funcionarios:
        fone_cru = getattr(f, 'telefone', '') or ''
        telefone = ''.join(filter(str.isdigit, str(fone_cru)))
        if telefone:
            nome_completo = f.user.get_full_name() or f.user.username
            contatos_funcionarios.append({
                "nome":     f"{nome_completo} (Cavalariço)",
                "telefone": telefone,
            })

    contatos_clientes = []
    alunos = Aluno.objects.filter(empresa=empresa).order_by('nome')
    for a in alunos:
        fone_cru = a.telefone or ''
        telefone = ''.join(filter(str.isdigit, str(fone_cru)))
        if telefone:
            contatos_clientes.append({
                "nome":     a.nome,
                "telefone": telefone,
            })

    aulas, data_selecionada = _get_aulas_encilhamento(empresa, data_str)

    context = {
        "brand_name":            BRAND_NAME,
        "empresa":               empresa,
        "aulas":                 aulas,
        "data_selecionada":      data_selecionada,
        "contatos_funcionarios": contatos_funcionarios,
        "contatos_clientes":     contatos_clientes,
        "force_light_theme":     True,
    }
    return render(request, "gateagora/encilhamento.html", context)


# ── Encilhamento WhatsApp ─────────────────────────────────────────────────────

@login_required
def encilhamento_whatsapp(request):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    data_str = request.GET.get('data', '')
    telefone = request.GET.get('telefone', '').strip()
    aulas, data_selecionada = _get_aulas_encilhamento(empresa, data_str)

    if not telefone:
        messages.warning(request, "Informe o telefone do cavalariço.")
        return redirect(f"/encilhamento/?data={data_str}")

    data_fmt = data_selecionada.strftime('%d de %B de %Y').capitalize()

    linhas = [
        f"🐎 *{empresa.nome.upper()}*",
        f"📋 *Ordem de Encilhamento*",
        f"📅 {data_fmt}",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    for aula in aulas:
        hora = timezone.localtime(aula.data_hora).strftime('%H:%M')
        c    = aula.cavalo
        local    = f"Baia {c.baia.numero}" if c.baia else (c.piquete.nome if c.piquete else "—")
        material = "⚠️ *Material PRÓPRIO*" if c.material_proprio else "✅ Material da Escola"

        linhas += [
            f"🕒 *{hora}* — {aula.get_local_display() or 'Picadeiro'}",
            f"👤 *Aluno:* {aula.aluno.nome}",
            f"🐴 *Cavalo:* {c.nome} ({local})",
            f"🪑 *Sela:* {c.tipo_sela or 'Padrão escola'}",
            f"🔗 *Cabeçada:* {c.tipo_cabecada or 'Padrão escola'}",
            f"{material}",
        ]
        if aula.relatorio_treino:
            linhas.append(f"📝 Obs: {aula.relatorio_treino}")
        linhas.append("─" * 25)

    linhas.append(MSG_RODAPE)

    texto = "\n".join(linhas)
    tel = "".join(filter(str.isdigit, telefone))
    if not tel.startswith('55'):
        tel = f"55{tel}"

    return redirect(f"https://wa.me/{tel}?text={quote(texto)}")


# ── PDF Encilhamento ──────────────────────────────────────────────────────────

@login_required
def encilhamento_pdf(request):
    empresa = getattr(request, "empresa", None)
    if not empresa and hasattr(request.user, 'perfil'):
        empresa = request.user.perfil.empresa

    data_str = request.GET.get('data', '')
    aulas, data_selecionada = _get_aulas_encilhamento(empresa, data_str)

    response = HttpResponse(content_type='application/pdf')
    data_fmt = data_selecionada.strftime('%d-%m-%Y')
    response['Content-Disposition'] = f'attachment; filename="Encilhamento_{data_fmt}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Cores ajustadas
    COR_PRIMARIA = colors.HexColor('#4F46E5')     # indigo-600
    COR_TEXTO    = colors.HexColor('#1F2937')     # texto principal (quase preto)
    COR_SUB      = colors.HexColor('#374151')     # cinza mais escuro (melhor que o anterior)
    COR_BORDA    = colors.HexColor('#CBD5E1')

    def desenhar_cabecalho(pagina):
        p.setStrokeColor(colors.lightgrey)
        p.line(45, height - 55, width - 45, height - 55)

        p.setFont("Helvetica-Bold", 18)
        p.setFillColor(COR_PRIMARIA)
        p.drawString(45, height - 38, "Guia de Encilhamento")

        p.setFont("Helvetica", 10)
        p.setFillColor(COR_SUB)
        p.drawRightString(width - 45, height - 38, empresa.nome.upper())
        p.drawRightString(width - 45, height - 50, f"Data: {data_selecionada.strftime('%d/%m/%Y')}  •  Página {pagina}")

        return height - 80

    y = desenhar_cabecalho(1)
    pagina = 1
    margem_x = 45
    largura = width - 2 * margem_x

    for aula in aulas:
        if y < 140:
            p.showPage()
            pagina += 1
            y = desenhar_cabecalho(pagina)

        hora = timezone.localtime(aula.data_hora).strftime('%H:%M')
        c = aula.cavalo

        local = f"Baia {c.baia.numero}" if getattr(c, 'baia', None) else \
                (f"Piquete: {c.piquete.nome}" if getattr(c, 'piquete', None) else "N/D")

        material = "⚠️ MATERIAL PRÓPRIO" if getattr(c, 'material_proprio', False) else "Material da Escola"

        # Card compacto
        card_altura = 118

        p.setStrokeColor(COR_BORDA)
        p.setFillColor(colors.white)
        p.roundRect(margem_x, y - card_altura, largura, card_altura, 8, fill=1, stroke=1)

        # Borda azul apenas no horário (sem fundo)
        p.setStrokeColor(COR_PRIMARIA)
        p.setLineWidth(2)
        p.roundRect(margem_x + 6, y - 32, 78, 24, 6, fill=0, stroke=1)

        # Hora
        p.setFillColor(COR_PRIMARIA)
        p.setFont("Helvetica-Bold", 13)
        p.drawString(margem_x + 14, y - 22, f"{hora}")

        # Aluno (mais escuro)
        p.setFillColor(COR_TEXTO)
        p.setFont("Helvetica-Bold", 12)
        nome_aluno = aula.aluno.nome[:38] + "..." if len(aula.aluno.nome) > 38 else aula.aluno.nome
        p.drawString(margem_x + 15, y - 48, f"👤 {nome_aluno.upper()}")

        # Cavalo
        p.setFillColor(COR_TEXTO)
        p.setFont("Helvetica-Bold", 10.5)
        p.drawString(margem_x + 15, y - 65, f"🐴 {c.nome}")

        # Demais informações - agora com cinza mais escuro
        p.setFillColor(COR_SUB)          # ← Aqui está o ajuste principal
        p.setFont("Helvetica", 9.8)

        p.drawString(margem_x + 15, y - 79, f"📍 {local} • {aula.get_local_display() or 'Picadeiro'}")
        p.drawString(margem_x + 15, y - 92, f"🪑 Sela:     {getattr(c, 'tipo_sela', 'Padrão')}")
        p.drawString(margem_x + 15, y - 104, f"🔗 Cabeçada: {getattr(c, 'tipo_cabecada', 'Padrão')}")

        # Material
        if getattr(c, 'material_proprio', False):
            p.setFillColor(colors.red)
            p.setFont("Helvetica-Bold", 9)
            p.drawString(margem_x + 15, y - 117, material)
        else:
            p.setFillColor(COR_SUB)
            p.setFont("Helvetica", 9)
            p.drawString(margem_x + 15, y - 117, material)

        # Observação (se houver)
        if getattr(aula, 'relatorio_treino', None):
            p.setFillColor(colors.darkgreen)
            p.setFont("Helvetica", 9)
            obs = aula.relatorio_treino[:85] + "..." if len(aula.relatorio_treino) > 85 else aula.relatorio_treino
            p.drawString(margem_x + 15, y - 130, f"📝 {obs}")

        y -= (card_altura + 12)

    p.save()
    return response


# ── Manejo em Massa ───────────────────────────────────────────────────────────

@login_required
def manejo_em_massa(request):
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    hoje = timezone.localdate()

    try:
        from .models import ConfigPrazoManejo
        cfg = ConfigPrazoManejo.objects.get(empresa=request.empresa)
        prazo_vacina        = cfg.prazo_vacina
        prazo_vermifugo     = cfg.prazo_vermifugo
        prazo_ferrageamento = cfg.prazo_ferrageamento
        prazo_casqueamento  = cfg.prazo_casqueamento
    except Exception:
        prazo_vacina        = 365
        prazo_vermifugo     = 90
        prazo_ferrageamento = 60
        prazo_casqueamento  = 60

    if request.method == "POST":
        procedimento   = request.POST.get("procedimento")
        data_aplicacao = request.POST.get("data")
        ids_cavalos    = request.POST.getlist("cavalos_selecionados")

        from .models import Cavalo
        cavalos_alvos = Cavalo.objects.filter(id__in=ids_cavalos, empresa=empresa)

        if not data_aplicacao or not cavalos_alvos.exists():
            messages.warning(request, "Selecione ao menos um cavalo, procedimento e data.")
            return redirect("dashboard")

        if procedimento == "Vacinacao":
            cavalos_alvos.update(ultima_vacina=data_aplicacao)
            messages.success(request, f"Vacinacao registrada em {cavalos_alvos.count()} animal(is).")

        elif procedimento == "Vermifugacao":
            cavalos_alvos.update(ultimo_vermifugo=data_aplicacao)
            messages.success(request, f"Vermifugacao registrada em {cavalos_alvos.count()} animal(is).")

        elif procedimento == "Ferrageamento":
            cavalos_alvos.update(
                ultimo_ferrageamento=data_aplicacao,
                ultimo_casqueamento=data_aplicacao,
            )
            messages.success(
                request,
                f"Ferrageamento (+ Casqueamento) registrado em {cavalos_alvos.count()} animal(is)."
            )

        elif procedimento == "Casqueamento":
            cavalos_alvos.update(ultimo_casqueamento=data_aplicacao)
            messages.success(request, f"Casqueamento registrado em {cavalos_alvos.count()} animal(is).")

        else:
            messages.warning(request, "Procedimento invalido.")

        return redirect("dashboard")

    # GET — monta lista
    from .models import Cavalo

    def _dias_atraso(data_campo):
        if not data_campo:
            return 9999
        return (hoje - data_campo).days

    def _score_criticidade(c):
        atraso_casco = (
            max(0, _dias_atraso(c.ultimo_ferrageamento) - prazo_ferrageamento)
            if c.usa_ferradura == 'SIM'
            else max(0, _dias_atraso(c.ultimo_casqueamento) - prazo_casqueamento)
        )
        atrasos = [
            max(0, _dias_atraso(c.ultima_vacina)    - prazo_vacina),
            max(0, _dias_atraso(c.ultimo_vermifugo) - prazo_vermifugo),
            atraso_casco,
        ]
        bonus_status = 10000 if c.status_saude != 'Saudável' else 0
        return sum(atrasos) + bonus_status

    def _cavalo_em_alerta(c):
        if c.status_saude != 'Saudável':
            return True
        if _dias_atraso(c.ultima_vacina)    > prazo_vacina:    return True
        if _dias_atraso(c.ultimo_vermifugo) > prazo_vermifugo: return True
        if c.usa_ferradura == 'SIM':
            if _dias_atraso(c.ultimo_ferrageamento) > prazo_ferrageamento: return True
        else:
            if _dias_atraso(c.ultimo_casqueamento) > prazo_casqueamento: return True
        return False

    todos = list(
        Cavalo.objects
        .filter(empresa=empresa)
        .select_related('proprietario', 'baia')
        .order_by('nome')
    )

    em_alerta = sorted([c for c in todos if _cavalo_em_alerta(c)],     key=_score_criticidade, reverse=True)
    em_dia    = sorted([c for c in todos if not _cavalo_em_alerta(c)], key=lambda c: c.nome)

    def _etiquetas(c):
        tags = []
        if c.status_saude != 'Saudável':
            tags.append({'label': f'Status: {c.status_saude}', 'cor': 'red'})
        d = _dias_atraso(c.ultima_vacina) - prazo_vacina
        if d > 0: tags.append({'label': f'Vacina +{d}d', 'cor': 'red' if d > 30 else 'amber'})
        d = _dias_atraso(c.ultimo_vermifugo) - prazo_vermifugo
        if d > 0: tags.append({'label': f'Vermifugo +{d}d', 'cor': 'red' if d > 30 else 'amber'})
        if c.usa_ferradura == 'SIM':
            d = _dias_atraso(c.ultimo_ferrageamento) - prazo_ferrageamento
            if d > 0: tags.append({'label': f'Ferrageamento +{d}d', 'cor': 'red' if d > 30 else 'amber'})
        else:
            d = _dias_atraso(c.ultimo_casqueamento) - prazo_casqueamento
            if d > 0: tags.append({'label': f'Casqueamento +{d}d', 'cor': 'red' if d > 30 else 'amber'})
        return tags

    for c in em_alerta + em_dia:
        c.etiquetas_manejo = _etiquetas(c)

    context = {
        "brand_name":            BRAND_NAME,
        "empresa":               empresa,
        "hoje":                  hoje,
        "cavalos_alerta":        em_alerta,
        "cavalos_em_dia":        em_dia,
        "prazo_vacina":          prazo_vacina,
        "prazo_vermifugo":       prazo_vermifugo,
        "prazo_ferrageamento":   prazo_ferrageamento,
        "prazo_casqueamento":    prazo_casqueamento,
    }
    return render(request, "gateagora/manejo_em_massa.html", context)


# ── Baixa de Fatura ───────────────────────────────────────────────────────────

@login_required
def dar_baixa_fatura(request, fatura_id):
    empresa = request.user.perfil.empresa
    fatura = get_object_or_404(Fatura, id=fatura_id, empresa=empresa)

    if fatura.status != 'PAGO':
        v_total = fatura.total  # sempre correto, pois os itens vêm do concluir_aula

        fatura.status = 'PAGO'
        fatura.data_pagamento = timezone.localdate()
        fatura.save()

        MovimentacaoFinanceira.objects.create(
            empresa=empresa,
            tipo='Receita',
            valor=v_total,
            data=timezone.localdate(),
            descricao=f"Recebimento Fatura #{fatura.id} — {fatura.aluno.nome}"
        )
        messages.success(request, f"Baixa realizada! R$ {v_total:,.2f} para {fatura.aluno.nome}.")
    else:
        messages.info(request, "Esta fatura já consta como paga.")

    return redirect('dashboard')


# ── Configuração de prazos ────────────────────────────────────────────────────

@login_required
def config_prazos_manejo(request):
    from .models import ConfigPrazoManejo

    empresa = request.empresa
    if not empresa and not request.user.is_superuser:
        return redirect('/admin/')
    cfg, _ = ConfigPrazoManejo.objects.get_or_create(empresa=request.empresa)

    if request.method == "POST":
        cfg.prazo_vacina        = int(request.POST.get("prazo_vacina",        365))
        cfg.prazo_vermifugo     = int(request.POST.get("prazo_vermifugo",      90))
        cfg.prazo_ferrageamento = int(request.POST.get("prazo_ferrageamento",  60))
        cfg.prazo_casqueamento  = int(request.POST.get("prazo_casqueamento",   60))
        cfg.save()
        messages.success(request, "Prazos de manejo atualizados com sucesso!")
        return redirect("dashboard")

    context = {
        "brand_name": BRAND_NAME,
        "empresa":    empresa,
        "cfg":        cfg,
    }
    return render(request, "gateagora/config_prazos_manejo.html", context)


# ── Marcar cavalo como saudável ───────────────────────────────────────────────

@login_required
def marcar_saudavel(request, cavalo_id):
    from .models import Cavalo, ConfigPrazoManejo
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    cavalo  = get_object_or_404(Cavalo, id=cavalo_id, empresa=empresa)
    hoje    = timezone.localdate()

    try:
        cfg = ConfigPrazoManejo.objects.get(empresa=request.empresa)
        prazo_vacina        = cfg.prazo_vacina
        prazo_vermifugo     = cfg.prazo_vermifugo
        prazo_ferrageamento = cfg.prazo_ferrageamento
        prazo_casqueamento  = cfg.prazo_casqueamento
    except ConfigPrazoManejo.DoesNotExist:
        prazo_vacina        = 365
        prazo_vermifugo     = 90
        prazo_ferrageamento = 60
        prazo_casqueamento  = 60

    def _atraso(data_campo, prazo):
        if not data_campo:
            return True
        return (hoje - data_campo).days > prazo

    pendencias = []
    if _atraso(cavalo.ultima_vacina,    prazo_vacina):    pendencias.append("Vacinação")
    if _atraso(cavalo.ultimo_vermifugo, prazo_vermifugo): pendencias.append("Vermifugação")
    if cavalo.usa_ferradura == 'SIM':
        if _atraso(cavalo.ultimo_ferrageamento, prazo_ferrageamento):
            pendencias.append("Ferrageamento")
    else:
        if _atraso(cavalo.ultimo_casqueamento, prazo_casqueamento):
            pendencias.append("Casqueamento")

    if pendencias:
        messages.warning(
            request,
            f"{cavalo.nome} ainda tem pendências: {', '.join(pendencias)}. "
            f"Registre os procedimentos em Manejo em Massa antes de marcar como Saudável."
        )
    else:
        cavalo.status_saude = 'Saudável'
        cavalo.save(update_fields=['status_saude'])
        messages.success(request, f"{cavalo.nome} marcado como Saudável! Todos os procedimentos estão em dia.")

    return redirect("dashboard")


# ── Movimentação de Estoque ───────────────────────────────────────────────────

@login_required
def movimentar_estoque(request):
    """Registra uma entrada ou saída pontual de estoque."""
    empresa = getattr(request, "empresa", request.user.perfil.empresa)

    if request.method == "POST":
        item_id    = request.POST.get("item_id")
        tipo       = request.POST.get("tipo")          # entrada | saida
        quantidade = request.POST.get("quantidade")
        observacao = request.POST.get("observacao", "")

        try:
            item = get_object_or_404(ItemEstoque, id=item_id, empresa=empresa)
            qtd  = Decimal(str(quantidade))

            if qtd <= 0:
                messages.warning(request, "Quantidade deve ser maior que zero.")
                return redirect("dashboard")

            if tipo == "entrada":
                item.quantidade_atual += int(qtd)
            elif tipo == "saida":
                item.quantidade_atual = max(0, item.quantidade_atual - int(qtd))
            else:
                messages.warning(request, "Tipo de movimentação inválido.")
                return redirect("dashboard")

            item.save(update_fields=["quantidade_atual"])

            MovimentacaoEstoque.objects.create(
                empresa=empresa,
                item=item,
                tipo=tipo,
                quantidade=qtd,
                observacao=observacao,
            )

            messages.success(
                request,
                f"{'Entrada' if tipo == 'entrada' else 'Saída'} de {qtd} {item.unidade} "
                f"registrada para {item.nome}."
            )

        except Exception as e:
            messages.error(request, f"Erro ao registrar movimentação: {e}")

    return redirect("dashboard")


# ── Fechamento do Dia (Estoque) ───────────────────────────────────────────────

@login_required
def fechamento_dia(request):
    """Exibe a tela de fechamento diário de estoque."""
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    hoje    = timezone.localdate()

    itens_qs = ItemEstoque.objects.filter(empresa=empresa)

    # Marca quais itens já tiveram ajuste hoje
    itens_com_ajuste_hoje = set(
        MovimentacaoEstoque.objects
        .filter(empresa=empresa, data=hoje, tipo="ajuste")
        .values_list("item_id", flat=True)
    )

    for item in itens_qs:
        item.ajuste_feito_hoje = item.id in itens_com_ajuste_hoje

    # Ordenação inteligente:
    # 1º — itens COM consumo_diario, ordenados por dias_restantes (menor = mais urgente)
    # 2º — itens SEM consumo_diario, ordenados por nome
    def _sort_key(item):
        dias = item.dias_restantes  # None se sem consumo_diario
        if dias is not None:
            return (0, dias, item.nome)  # grupo urgente, quanto menos dias = mais cedo
        return (1, 9999, item.nome)      # grupo sem consumo, por nome

    itens = sorted(itens_qs, key=_sort_key)

    context = {
        "brand_name": BRAND_NAME,
        "empresa":    empresa,
        "hoje":       hoje,
        "itens":      itens,
    }
    return render(request, "gateagora/fechamento_estoque.html", context)


@login_required
def salvar_fechamento(request):
    """Salva os ajustes do fechamento diário de estoque."""
    empresa = getattr(request, "empresa", request.user.perfil.empresa)
    hoje    = timezone.localdate()

    if request.method != "POST":
        return redirect("fechamento_dia")

    itens = ItemEstoque.objects.filter(empresa=empresa)
    ajustes_salvos = 0

    for item in itens:
        campo_qtd = request.POST.get(f"qtd_{item.id}")
        campo_obs = request.POST.get(f"obs_{item.id}", "")

        if campo_qtd is None:
            continue

        try:
            nova_qtd = int(campo_qtd)
        except (ValueError, TypeError):
            continue

        diferenca = nova_qtd - item.quantidade_atual

        if diferenca == 0:
            continue

        MovimentacaoEstoque.objects.create(
            empresa=empresa,
            item=item,
            tipo="ajuste",
            quantidade=abs(diferenca),
            observacao=campo_obs or (
                f"Fechamento do dia: {'consumo extra' if diferenca < 0 else 'reposição'}"
            ),
            data=hoje,
        )

        item.quantidade_atual = nova_qtd
        item.save(update_fields=["quantidade_atual"])
        ajustes_salvos += 1

    if ajustes_salvos:
        messages.success(request, f"Fechamento do dia salvo! {ajustes_salvos} item(ns) ajustado(s).")
    else:
        messages.info(request, "Nenhuma alteração registrada no fechamento de hoje.")

    return redirect("dashboard")