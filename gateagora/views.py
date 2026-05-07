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

from django.views.decorators.http import require_POST

from .models import (
    Empresa, Perfil, Aluno, Cavalo, Baia, Piquete, Aula,
    ItemEstoque, MovimentacaoFinanceira, MovimentacaoEstoque, DocumentoCavalo,
    ConfigPrazoManejo, ConfigPrecoManejo, Fatura, ItemFatura, ConfirmacaoPresenca,
    RegistroOcorrencia
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
    'FERRAGEAMENTO': '🧲',
    'OUTROS':        '📦',
}


# ── Login ─────────────────────────────────────────────────────────────────────

class CustomLoginView(LoginView):
    template_name = "gateagora/login.html"
    form_class = AuthenticationForm
    redirect_authenticated_user = True


    def get_success_url(self):
        user = self.request.user
        if hasattr(user, 'perfil') and user.perfil.cargo == 'Aluno':
            return '/minhas-aulas/'
        return '/'

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
    empresa = request.empresa
    hoje = date.today()
    mes_selecionado = int(request.GET.get('mes', hoje.month))
    ano_selecionado = int(request.GET.get('ano', hoje.year))

    print(f"DEBUG: Filtrando para o mês {mes_selecionado} de {ano_selecionado}")

    if not empresa and not request.user.is_superuser:
        try:
            return redirect('/admin/gateagora/perfil/add/')
        except:
            return redirect('/admin/')

    # 1. CÁLCULOS PARA OS GRÁFICOS DO DASHBOARD
    # Soma o valor das faturas PAGAS no mês atual
    faturas_pagas = Fatura.objects.filter(
        empresa=empresa,
        status='PAGO',
        data_vencimento__year=hoje.year,
        data_vencimento__month=hoje.month
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    # Soma o valor de TODAS as faturas ATRASADAS ou PENDENTES que já venceram (acumulado)
    faturas_vencidas = Fatura.objects.filter(
        empresa=empresa,
        status__in=['PENDENTE', 'ATRASADO'],
        data_vencimento__lt=hoje
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    # 2. LISTAGEM DE COBRANÇA (CARD DO DASHBOARD)
    faturas_criticas = Fatura.objects.filter(
        empresa=empresa,
        status__in=['PENDENTE', 'ATRASADO'],
        data_vencimento__lte=hoje
    ).prefetch_related('itens').select_related('aluno').order_by('data_vencimento')

    listagem_cobranca = []
    for fatura in faturas_criticas:
        # Pega o valor nominal da fatura
        v_total = Decimal(str(fatura.valor or 0))

        # Se o valor estiver zerado, tenta calcular via itens ou fallback (sua lógica original)
        if v_total == Decimal("0.00"):
            v_total = fatura.total
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
        # Usa a função auxiliar para montar a mensagem
        msg_zap = _montar_msg_fatura_whatsapp(fatura, empresa)
        link_zap = f"https://wa.me/55{tel_c}?text={quote(msg_zap)}" if tel_c else "#"

        listagem_cobranca.append({
            "fatura_id":  fatura.id,
            "aluno":      fatura.aluno.nome,
            "vencimento": fatura.data_vencimento,
            "valor":      formata_real(v_total),
            "atrasado":   fatura.data_vencimento < hoje,
            "link_zap":   link_zap,
        })
    

    # ── 1) Aulas de hoje — inclui concluídas para não sumirem da lista ─────────
    proximas_aulas = list(
        Aula.objects
        .filter(empresa=empresa, data_hora__date=hoje)
        .select_related('aluno', 'cavalo')
        .order_by('data_hora')
    )
    # Mapeamento seguro — evita RelatedObjectDoesNotExist no descriptor OneToOne
    # Para turmas: múltiplas confirmações por aula
    # Para individual: comportamento idêntico ao anterior
    _conf_qs = list(
        ConfirmacaoPresenca.objects
        .filter(aula_id__in=[a.id for a in proximas_aulas])
        .values('aula_id', 'aluno_id')
    )
    # aula_id → set de aluno_ids confirmados
    _conf_map = {}
    for row in _conf_qs:
        _conf_map.setdefault(row['aula_id'], set()).add(row['aluno_id'])
    for _a in proximas_aulas:
        _conf_alunos     = _conf_map.get(_a.id, set())
        _a.conf_alunos   = _conf_alunos
        _a.is_confirmada = bool(_conf_alunos)
        # NÃO atribuir _a.confirmacao — descriptor OneToOne lança ValueError com bool
        # Garante streak_atual mesmo se campo foi removido por migração
        if not hasattr(_a.aluno, 'streak_atual') if hasattr(_a, 'aluno') else True:
            pass  # streak não exibido nos cards de aula do dashboard

    # ── 2) Alertas e Estoque Unificado ────────────────────────────────────────
    estoque_todos = list(
        ItemEstoque.objects
        .filter(empresa=empresa)
        .prefetch_related('lotes')
        .order_by('nome')
    )

    # Anota cada item com a quantidade efetivamente disponível para uso
    # e a quantidade perdida por vencimento.
    for item in estoque_todos:
        vencido = item.status_validade == 'vencido'

        # Estoque útil: zero quando vencido — produto vencido não existe para uso.
        item._estoque_disponivel = 0 if vencido else item.quantidade_valida

        # Perda contabilizável: só faz sentido quando vencido e havia estoque.
        item.quantidade_descarte = (item.quantidade_atual - item.quantidade_valida) if vencido else 0

        # Prioridade de alerta (menor = mais urgente):
        #   0 → vencido (descarte obrigatório) ou abaixo do mínimo
        #   1 → vence em ≤ 5 dias (alerta_critico)
        #   2 → vence em ≤ 30 dias (alerta)
        #   3 → tudo ok
        if vencido or item._estoque_disponivel <= item.alerta_minimo:
            item.prioridade = 0
        elif item.status_validade == 'alerta_critico':
            item.prioridade = 1
        elif item.status_validade == 'alerta':
            item.prioridade = 2
        else:
            item.prioridade = 3

    # Ordena por prioridade, depois nome
    estoque_todos.sort(key=lambda x: (x.prioridade, x.nome))

    # Itens que aparecem no painel de alertas
    estoque_alerta = [item for item in estoque_todos if item.prioridade <= 2]

    # Badge de críticos: vencidos + abaixo do mínimo
    estoque_baixo_count = sum(1 for item in estoque_todos if item.prioridade == 0)

    # Gera link WhatsApp para fornecedor
    for _item in estoque_todos:
        if _item.fornecedor_contato:
            tel = "".join(filter(str.isdigit, str(_item.fornecedor_contato)))
            if not tel.startswith("55"):
                tel = f"55{tel}"

            # Informa ao fornecedor o estoque *disponível* (não o bruto)
            aviso_vencido = (
                f"⚠️ *Atenção: lote atual VENCIDO* — {_item.quantidade_descarte} {_item.unidade} para descarte.\n"
                if _item.quantidade_descarte > 0 else ""
            )
            msg = (
                f"📦 *Pedido de Reposição — {_item.empresa.nome}* 🐎\n\n"
                f"Olá! Gostaríamos de solicitar a reposição do seguinte item:\n\n"
                f"*Produto:* {_item.nome}\n"
                f"*Estoque disponível (válido):* {item._estoque_disponivel} {item.unidade}\n"
                f"*Estoque mínimo:* {_item.alerta_minimo} {_item.unidade}\n"
                f"{aviso_vencido}"
            )
            if _item.dias_para_vencer is not None and _item.status_validade != 'vencido':
                msg += f"*Validade mais próxima:* {_item.dias_para_vencer} dias\n"
            msg += (
                f"*Quantidade a pedir:* ??? {_item.unidade}\n\n"
                f"Por favor, confirme disponibilidade e prazo de entrega.\n"
                f"⚠️ Antes de qualquer alteração, envie os documentos para conferência.\n\n"
                f"📲 _Enviado via *Gate 4 — Gestão de Haras e Hípicas*_ 🐎"
            )
            _item.whatsapp_fornecedor = f"https://wa.me/{tel}?text={quote(msg)}"
        else:
            _item.whatsapp_fornecedor = None

    # Dados para o gráfico (Chart.js) — usa estoque_disponivel, não quantidade_atual
    estoque_labels = []
    estoque_valores = []
    estoque_cores = []

    for item in estoque_todos:
        estoque_labels.append(item.nome)
        # CORRIGIDO: gráfico reflete o estoque real disponível (vencidos = 0)
        estoque_valores.append(float(item._estoque_disponivel))
        if item.prioridade == 0:
            estoque_cores.append('#ef4444')   # vermelho — crítico / vencido
        elif item.prioridade == 1:
            estoque_cores.append('#f97316')   # laranja — vence em ≤ 5d
        elif item.prioridade == 2:
            estoque_cores.append('#f59e0b')   # âmbar — vence em ≤ 30d
        else:
            estoque_cores.append('#10b981')   # verde — ok

    # 4. Documentos & Procedimentos vencendo/próximos do vencimento
    janela_venc = hoje + timedelta(days=30)

    # 4a. Documentos legais formais (GTA, Exame Mormo/Anemia, etc.)
    #     Inclui TODOS os tipos — vencidos (< hoje) ou vencendo em 60 dias
    janela_docs = hoje + timedelta(days=60)
    docs_formais_qs = list(
        DocumentoCavalo.objects
        .filter(
            cavalo__empresa=empresa,
            data_validade__lte=janela_docs,
        )
        .select_related('cavalo')
        .order_by('data_validade')
    )
    # Adiciona atributo vencido a cada doc para uso no template
    for _doc in docs_formais_qs:
        _doc.vencido = _doc.data_validade < hoje
    docs_formais = docs_formais_qs

    # 4b. Prazos configuráveis por empresa
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

    # Separa documentos por categoria
    TIPOS_SANITARIOS = {'GTA', 'Mormo', 'Anemia Infecciosa Equina', 'Anemia', 'AIE'}
    docs_sanitarios   = [d for d in docs_formais if d.tipo in TIPOS_SANITARIOS]
    docs_manejo_prev  = [d for d in docs_formais if d.tipo not in TIPOS_SANITARIOS]
    docs_vencendo     = docs_formais  # compatibilidade com template

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

    # ── Inadimplência do MÊS SELECIONADO (gráfico + KPIs principais) ────────────
    total_faturas_mes    = faturas_mes.count()
    faturas_pagas_mes    = faturas_mes.filter(status='PAGO').count()
    faturas_vencidas_mes = faturas_mes.filter(
        status__in=['PENDENTE', 'ATRASADO'],
        data_vencimento__lt=hoje
    ).count()
    valor_recebido_mes = (
        faturas_mes.filter(status='PAGO')
        .aggregate(t=Sum('valor'))['t'] or Decimal('0.00')
    )
    valor_inadimplente_mes = (
        faturas_mes.filter(status__in=['PENDENTE', 'ATRASADO'], data_vencimento__lt=hoje)
        .aggregate(t=Sum('valor'))['t'] or Decimal('0.00')
    )
    base_inad_mes = float(valor_recebido_mes) + float(valor_inadimplente_mes)
    indice_inadimplencia = (
        round(float(valor_inadimplente_mes) / base_inad_mes * 100, 1)
        if base_inad_mes > 0 else 0
    )

    # ── Dívida Ativa Total — acumulado histórico (KPI separado) ──────────────
    divida_ativa_qs = Fatura.objects.filter(
        empresa=empresa, status__in=['PENDENTE', 'ATRASADO'], data_vencimento__lt=hoje
    )
    divida_ativa_total = divida_ativa_qs.aggregate(t=Sum('valor'))['t'] or Decimal('0.00')
    # Separa dívida do mês atual vs atrasos antigos
    divida_mes_atual = (
        divida_ativa_qs
        .filter(data_vencimento__year=hoje.year, data_vencimento__month=hoje.month)
        .aggregate(t=Sum('valor'))['t'] or Decimal('0.00')
    )
    divida_historica = divida_ativa_total - divida_mes_atual
    # Para compatibilidade com template existente
    valor_inadimplente = divida_ativa_total
    valor_recebido_ano = (
        Fatura.objects
        .filter(empresa=empresa, status='PAGO', data_vencimento__year=hoje.year)
        .aggregate(t=Sum('valor'))['t'] or Decimal('0.00')
    )

    # --- NOVO BLOCO DE CÁLCULO DE RECEITA ---
    # 1. Calcula o total real baseado na soma de todos os itens de fatura do mês selecionado
    receita_total_prevista = ItemFatura.objects.filter(
        fatura__empresa=empresa,
        fatura__data_vencimento__year=ano_selecionado,
        fatura__data_vencimento__month=mes_selecionado
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    # 2. Monta a listagem para o template sem fazer somas extras (evita duplicar valores)
    relatorio = []
    for fatura in faturas_mes:
        # Pega o total calculado da fatura (método .total do model)
        v_fatura = fatura.total 

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

    # ── 4c) Receita por Cavalo — centro de custo ────────────────────────────────
    receita_por_cavalo = list(
        ItemFatura.objects
        .filter(
            fatura__empresa=empresa,
            fatura__data_vencimento__year=ano_selecionado,
            fatura__data_vencimento__month=mes_selecionado,
            cavalo__isnull=False,
        )
        .values('cavalo__id', 'cavalo__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')[:10]
        # Removido: .select_related('cavalo')
    )

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
            # Soma valor_aula do aluno por treino concluído — evita inflar com
            # outros itens da fatura (hotelaria, vet, etc.)
            Sum(
                'aulas__aluno__valor_aula',
                filter=Q(
                    aulas__concluida=True,
                    aulas__data_hora__date__gte=data_inicio,
                    aulas__data_hora__date__lte=hoje,
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

    # ── 7) Ranking de alunos — streak dinâmico + fallback mês anterior ──────────
    def _candidatos_periodo(d_ini, d_fim):
        return list(
            Aluno.objects
            .filter(empresa=empresa, ativo=True)
            .annotate(
                aulas_periodo=Count(
                    'aulas',
                    filter=Q(
                        aulas__concluida=True,
                        aulas__data_hora__date__gte=d_ini,
                        aulas__data_hora__date__lte=d_fim,
                    )
                )
            )
            .filter(aulas_periodo__gt=0)
            .order_by('-aulas_periodo', 'nome')
        )

    candidatos = _candidatos_periodo(data_inicio, hoje)
    if not candidatos:
        # Fallback: mês anterior
        mes_ant   = (hoje.replace(day=1) - timedelta(days=1))
        inicio_ant = mes_ant.replace(day=1)
        candidatos = _candidatos_periodo(inicio_ant, mes_ant)
        periodo_label = (
            f"{['','Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][mes_ant.month]}"
            f"/{mes_ant.year} (mês anterior)"
        )

    # Recalcula streak de cada candidato dinamicamente (sem depender do campo salvo)
    # Usa datas de aulas concluídas dos últimos 90 dias para ser eficiente
    noventa_dias = hoje - timedelta(days=90)
    ids_candidatos = [a.id for a in candidatos]
    aulas_historico = list(
        Aula.objects
        .filter(
            aluno_id__in=ids_candidatos,
            concluida=True,
            data_hora__date__gte=noventa_dias,
            data_hora__date__lte=hoje,
        )
        .values('aluno_id', 'data_hora')
    )
    # Monta dict aluno_id → set de semanas ISO com aula
    from datetime import timedelta as _td
    semanas_por_aluno = {}
    for row in aulas_historico:
        iso = row['data_hora'].isocalendar()
        key = iso[0] * 100 + iso[1]
        semanas_por_aluno.setdefault(row['aluno_id'], set()).add(key)

    def _calc_streak_dinamico(aluno_id):
        semanas = semanas_por_aluno.get(aluno_id, set())
        if not semanas:
            return 0
        streak = 0
        check  = hoje
        for _ in range(13):  # até 13 semanas = 90 dias
            iso = check.isocalendar()
            key = iso[0] * 100 + iso[1]
            if key in semanas:
                streak += 1
                check  -= _td(days=7)
            else:
                # Tolera a semana atual se ainda não acabou
                if streak == 0:
                    check -= _td(days=7)
                    continue
                break
        return streak

    for al in candidatos:
        al.streak_dinamico = _calc_streak_dinamico(al.id)
        # Sincroniza o campo salvo se divergir — só salva se campo existe no banco
        try:
            if al.streak_dinamico != al.streak_atual:
                al.streak_atual = al.streak_dinamico
                if al.streak_dinamico > al.melhor_streak:
                    al.melhor_streak = al.streak_dinamico
                al.save(update_fields=['streak_atual', 'melhor_streak'])
        except Exception:
            pass  # campo removido por migração — ignora silenciosamente

    # Ordena: streak primeiro (consistência), aulas_periodo como desempate
    ranking_alunos = sorted(
        candidatos,
        key=lambda a: (-a.streak_dinamico, -a.aulas_periodo, a.nome)
    )[:10]

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
        'FERRAGEAMENTO': '🧲 Ferrageamento',
        'OUTROS':        '📦 Outros',
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

    # ── 9) Taxa de confirmação do dia ────────────────────────────────────────
    total_aulas_hoje       = len(proximas_aulas)
    aulas_confirmadas_hoje = sum(1 for a in proximas_aulas if a.is_confirmada)
    aulas_concluidas_hoje  = sum(1 for a in proximas_aulas if a.concluida)

    # ── 10) Alunos inativos 14-29 dias (alerta) e 30+ dias (risco de perda) ─────
    trinta_dias    = hoje - timedelta(days=30)
    quatorze_dias  = hoje - timedelta(days=14)

    # Quem teve aula concluída nos últimos 14 dias — está ativo
    ativos_recentes = set(
        Aula.objects
        .filter(empresa=empresa, concluida=True, data_hora__date__gte=quatorze_dias)
        .values_list('aluno_id', flat=True)
        .distinct()
    )
    # Quem teve aula entre 14-29 dias — inativo mas ainda recuperável
    ativos_14_30 = set(
        Aula.objects
        .filter(
            empresa=empresa, concluida=True,
            data_hora__date__gte=trinta_dias,
            data_hora__date__lt=quatorze_dias,
        )
        .values_list('aluno_id', flat=True)
        .distinct()
    )

    alunos_base = list(
        Aluno.objects
        .filter(empresa=empresa, ativo=True)
        .exclude(id__in=ativos_recentes)
        .order_by('nome')
    )

    # Separa os dois grupos e calcula dias desde a última aula
    alunos_inativos   = []  # 14-29 dias
    alunos_risco      = []  # 30+ dias

    aula_ids = [a.id for a in alunos_base]
    # Última aula concluída de cada aluno
    from django.db.models import Max
    ultima_aula_map = dict(
        Aula.objects
        .filter(empresa=empresa, concluida=True, aluno_id__in=aula_ids)
        .values('aluno_id')
        .annotate(ultima=Max('data_hora__date'))
        .values_list('aluno_id', 'ultima')
    )

    for al in alunos_base:
        ultima = ultima_aula_map.get(al.id)
        dias = (hoje - ultima).days if ultima else None
        al.dias_inativo = dias
        if al.id in ativos_14_30:
            alunos_inativos.append(al)
        else:
            alunos_risco.append(al)

    alunos_inativos = sorted(alunos_inativos, key=lambda x: x.dias_inativo or 0, reverse=True)[:8]
    alunos_risco    = sorted(alunos_risco,    key=lambda x: x.dias_inativo or 0, reverse=True)[:8]

    # ── 11) Capacity Utilization — baseado em confirmações reais (recalculado a cada request)
    capacity_utilization = None

    # ── 12) Equine Workload — cavalos com 3+ aulas hoje ──────────────────────
    from django.db.models import Count as _Count
    cavalos_sobrecarga = list(
        Aula.objects
        .filter(empresa=empresa, data_hora__date=hoje)
        .values('cavalo__id', 'cavalo__nome')
        .annotate(total_aulas=_Count('id'))
        .filter(total_aulas__gte=3)
        .order_by('-total_aulas')
    )
    # total_aulas=3 já é alerta; >=4 é crítico
    for c in cavalos_sobrecarga:
        c['critico'] = c['total_aulas'] >= 4

    # ── 13) Contexto final ────────────────────────────────────────────────────
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
        "ranking_alunos":           ranking_alunos,
        "ranking_cavalos_dados":    json.dumps(ranking_dados),
        "ranking_receita":          json.dumps(ranking_receita),
        "cavalos_sem_treino":       sem_treino,
        "limite_treinos_mes":       limite,
        "periodo_label":            periodo_label,
        "periodo_atual":            periodo,
        "receita_por_tipo_labels":  json.dumps(receita_por_tipo_labels,  ensure_ascii=False),
        "receita_por_tipo_valores": json.dumps(receita_por_tipo_valores),
        # Somente itens críticos/atenção para o painel fusionado do dashboard
        "estoque_alerta":           [i for i in estoque_todos if i.prioridade <= 1],
        # Inadimplência
        "total_faturas":            total_faturas_mes,
        "faturas_pagas":            faturas_pagas_mes,
        "faturas_vencidas":         faturas_vencidas_mes,
        "indice_inadimplencia":     indice_inadimplencia,
        # Inadimplência detalhada
        "valor_inadimplente_mes":   float(valor_inadimplente_mes),
        "valor_recebido_mes":       float(valor_recebido_mes),
        "divida_ativa_total":       float(divida_ativa_total),
        "divida_mes_atual":         float(divida_mes_atual),
        "divida_historica":         float(divida_historica),
        # Compatibilidade
        "valor_inadimplente":       float(valor_inadimplente),
        "valor_recebido_ano":       float(valor_recebido_ano),
        # Documentos separados
        "docs_sanitarios":          docs_sanitarios,
        "docs_manejo_prev":         docs_manejo_prev,
        # Receita por cavalo
        "receita_por_cavalo":       receita_por_cavalo,
        # Taxa de confirmação
        "total_aulas_hoje":         total_aulas_hoje,
        "aulas_confirmadas_hoje":   aulas_confirmadas_hoje,
        "aulas_concluidas_hoje":    aulas_concluidas_hoje,
        # Retenção / churn
        "alunos_inativos":          alunos_inativos,
        "alunos_risco":             alunos_risco,
        # Turmas / bem-estar
        "capacity_utilization":     capacity_utilization,
        "cavalos_sobrecarga":       cavalos_sobrecarga,
    }

    return render(request, "gateagora/dashboard.html", context)

# ── Streak / Gamificação ─────────────────────────────────────────────────────

def _atualizar_streak(aluno):
    """
    Recalcula streak_atual do aluno com base no histórico de aulas concluídas.
    Regra: semana com aula concluída = +1; semana sem aula = reset para 0.
    Atualiza melhor_streak se necessário. Salva o aluno.
    """
    from django.utils import timezone as tz
    hoje     = tz.localdate()
    # Pega as últimas 52 semanas de aulas concluídas
    aulas_ok = list(
        Aula.objects
        .filter(aluno=aluno, concluida=True, data_hora__date__lte=hoje)
        .order_by('-data_hora')
        .values_list('data_hora', flat=True)[:200]
    )

    if not aulas_ok:
        aluno.streak_atual = 0
        aluno.save(update_fields=['streak_atual', 'melhor_streak'])
        return

    # Converte para números de semana ISO (ano * 100 + semana)
    semanas_com_aula = set()
    for dt in aulas_ok:
        iso = dt.isocalendar()
        semanas_com_aula.add(iso[0] * 100 + iso[1])

    # Conta semanas consecutivas a partir da semana atual / última semana
    semana_ref = hoje.isocalendar()
    semana_key = semana_ref[0] * 100 + semana_ref[1]

    # Aceita também semana passada como "ainda ativa"
    from datetime import date, timedelta
    semana_passada = (hoje - timedelta(days=7)).isocalendar()
    semana_pass_key = semana_passada[0] * 100 + semana_passada[1]

    if semana_key not in semanas_com_aula and semana_pass_key not in semanas_com_aula:
        aluno.streak_atual = 0
        aluno.save(update_fields=['streak_atual', 'melhor_streak'])
        return

    # Conta para trás semana a semana
    streak = 0
    check = hoje
    for _ in range(52):
        iso   = check.isocalendar()
        key   = iso[0] * 100 + iso[1]
        if key in semanas_com_aula:
            streak += 1
            check  -= timedelta(days=7)
        else:
            break

    aluno.streak_atual = streak
    if streak > aluno.melhor_streak:
        aluno.melhor_streak = streak
    aluno.save(update_fields=['streak_atual', 'melhor_streak'])


def _selo_streak(semanas):
    """Retorna (nome_selo, icone, cor) baseado no streak atual."""
    if semanas >= 20:
        return ('Cavaleiro de Ouro',   'fa-crown',          '#f59e0b')
    if semanas >= 10:
        return ('Cavaleiro de Prata',  'fa-shield-halved',  '#94a3b8')
    if semanas >= 5:
        return ('Cavaleiro de Bronze', 'fa-medal',          '#b45309')
    return None


# ── Confirmar Presença pelo Dashboard (Gestor) ───────────────────────────────

@login_required
@require_POST
def confirmar_presenca_dashboard(request, aula_id):
    # Gestor ou instrutor confirma presenca de aluno direto pelo dashboard
    try:
        perfil = request.user.perfil
    except Exception:
        return redirect("login")

    if perfil.cargo not in ("Gestor", "Instrutor", "Admin"):
        return redirect("dashboard")

    aula = get_object_or_404(Aula, id=aula_id, empresa=perfil.empresa)
    _, criado = ConfirmacaoPresenca.objects.get_or_create(aula=aula, aluno=aula.aluno)

    if criado:
        messages.success(request, f"Presenca de {aula.aluno.nome} confirmada.")
    else:
        messages.info(request, f"{aula.aluno.nome} ja estava confirmado.")

    return redirect("dashboard")


# ── Confirmar Presença de Turma (Gestor) ─────────────────────────────────────

@login_required
@require_POST
def confirmar_presenca_turma(request, aula_id):
    # Confirma todos os alunos inscritos na turma de uma vez
    try:
        perfil = request.user.perfil
    except Exception:
        return redirect("login")

    if perfil.cargo not in ("Gestor", "Instrutor", "Admin"):
        return redirect("dashboard")

    from gateagora.models import InscricaoAula
    aula = get_object_or_404(Aula, id=aula_id, empresa=perfil.empresa)

    if aula.nome_turma:
        # Turma: confirma todos os inscritos
        inscritos = InscricaoAula.objects.filter(aula=aula).select_related('aluno')
        confirmados = 0
        for insc in inscritos:
            _, criado = ConfirmacaoPresenca.objects.get_or_create(
                aula=aula, aluno=insc.aluno
            )
            if criado:
                confirmados += 1
        if confirmados:
            messages.success(request, f"{confirmados} aluno(s) de '{aula.nome_turma}' confirmados.")
        else:
            messages.info(request, f"Todos os alunos de '{aula.nome_turma}' já estavam confirmados.")
    else:
        # Aula individual: confirma o aluno da aula
        _, criado = ConfirmacaoPresenca.objects.get_or_create(
            aula=aula, aluno=aula.aluno
        )
        if criado:
            messages.success(request, f"Presença de {aula.aluno.nome} confirmada.")
        else:
            messages.info(request, f"{aula.aluno.nome} já estava confirmado.")

    return redirect("dashboard")


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

    aulas = list(
        Aula.objects
        .filter(empresa=empresa, data_hora__date=data)
        .select_related(
            'aluno', 'cavalo', 'cavalo__baia',
            'cavalo__piquete', 'instrutor', 'instrutor__user'
        )
        .order_by('data_hora')
    )
    _conf_enc = set(
        ConfirmacaoPresenca.objects
        .filter(aula_id__in=[a.id for a in aulas])
        .values_list('aula_id', flat=True)
        .distinct()
    )
    for aula in aulas:
        aula.is_confirmada = aula.id in _conf_enc
        if aula.concluida:
            aula.ui_estado = "concluida"
        elif aula.is_confirmada:
            aula.ui_estado = "confirmada"
        else:
            aula.ui_estado = "nao_confirmada" 

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
        "total_aulas":           len(aulas),
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

    # Separa confirmadas das pendentes para mostrar resumo
    total  = len(aulas)
    conf   = sum(1 for a in aulas if getattr(a, 'is_confirmada', False))
    pend   = total - conf

    linhas = [
        f"🐎 *{empresa.nome.upper()}*",
        f"📋 *Guia de Encilhamento — {data_fmt}*",
        f"",
        f"📊 Resumo: {total} aula{'s' if total != 1 else ''} | "
        f"✅ {conf} confirmada{'s' if conf != 1 else ''} | "
        f"⏳ {pend} aguardando",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    for i, aula in enumerate(aulas, 1):
        hora  = timezone.localtime(aula.data_hora).strftime('%H:%M')
        c     = aula.cavalo
        local = f"Baia {c.baia.numero}" if getattr(c,'baia',None)                 else (c.piquete.nome if getattr(c,'piquete',None) else "—")

        confirmada = getattr(aula, 'is_confirmada', False)
        status_icon = "✅" if confirmada else "⏳"
        material = "⚠️ *MATERIAL PRÓPRIO — nao usar equipamento da escola*"                    if getattr(c,'material_proprio',False) else "Material da Escola"

        sela     = getattr(c,'tipo_sela',None)     or "Padrao escola"
        cabecada = getattr(c,'tipo_cabecada',None)  or "Padrao escola"

        linhas += [
            f"",
            f"{status_icon} *AULA {i} — {hora}*  |  {aula.get_local_display() or 'Picadeiro'}",
            f"👤 {aula.aluno.nome}",
            f"🐴 *{c.nome}*  ({local})",
            f"   Sela: {sela}",
            f"   Cabecada: {cabecada}",
            f"   {material}",
        ]
        if aula.instrutor:
            linhas.append(f"   Prof. {aula.instrutor.user.get_full_name()}")
        if aula.relatorio_treino:
            linhas.append(f"📝 _{aula.relatorio_treino}_")
        linhas.append("─" * 26)

    linhas += [
        f"",
        MSG_RODAPE,
    ]

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
        hora = timezone.localtime(aula.data_hora).strftime('%H:%M')
        c    = aula.cavalo

        local    = f"Baia {c.baia.numero}" if getattr(c, 'baia', None) else                    (f"Piquete: {c.piquete.nome}" if getattr(c, 'piquete', None) else "N/D")
        sela      = getattr(c, 'tipo_sela', None)     or "Padrao escola"
        cabecada  = getattr(c, 'tipo_cabecada', None)  or "Padrao escola"
        tem_obs   = bool(getattr(aula, 'relatorio_treino', None))
        material_proprio = getattr(c, 'material_proprio', False)

        # Altura dinamica: base 130 + 14 por obs
        card_altura = 144 if tem_obs else 130
        espaco_necessario = card_altura + 16

        if y - espaco_necessario < 60:
            p.showPage()
            pagina += 1
            y = desenhar_cabecalho(pagina)

        # Fundo do card
        p.setStrokeColor(COR_BORDA)
        p.setLineWidth(0.8)
        p.setFillColor(colors.white)
        p.roundRect(margem_x, y - card_altura, largura, card_altura, 8, fill=1, stroke=1)

        # Faixa colorida lateral: verde=confirmada, ambar=pendente
        confirmada = getattr(aula, 'is_confirmada', False)
        cor_faixa  = colors.HexColor('#10b981') if confirmada else colors.HexColor('#f59e0b')
        p.setFillColor(cor_faixa)
        p.roundRect(margem_x, y - card_altura, 5, card_altura, 2, fill=1, stroke=0)

        # Pill horario
        p.setFillColor(COR_PRIMARIA)
        p.roundRect(margem_x + 12, y - 28, 62, 20, 5, fill=1, stroke=0)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 12)
        p.drawCentredString(margem_x + 43, y - 21, hora)

        # Badge status
        badge_txt = "CONFIRMADA" if confirmada else "AGUARDANDO"
        badge_cor = colors.HexColor('#10b981') if confirmada else colors.HexColor('#f59e0b')
        p.setFillColor(badge_cor)
        p.roundRect(margem_x + largura - 95, y - 28, 88, 18, 4, fill=1, stroke=0)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 7.5)
        p.drawCentredString(margem_x + largura - 51, y - 21, badge_txt)

        # Nome do aluno
        p.setFillColor(COR_TEXTO)
        p.setFont("Helvetica-Bold", 11.5)
        nome_aluno = (aula.aluno.nome[:40] + "...") if len(aula.aluno.nome) > 40 else aula.aluno.nome
        p.drawString(margem_x + 12, y - 47, nome_aluno.upper())

        # Tipo de aula e instrutor
        p.setFillColor(COR_SUB)
        p.setFont("Helvetica", 9)
        tipo_inst = aula.get_tipo_display()
        if aula.instrutor:
            tipo_inst += f"  |  Prof. {aula.instrutor.user.first_name}"
        p.drawString(margem_x + 12, y - 59, tipo_inst)

        # Separador fino
        p.setStrokeColor(COR_BORDA)
        p.setLineWidth(0.4)
        p.line(margem_x + 12, y - 65, margem_x + largura - 12, y - 65)

        # Cavalo + local
        p.setFillColor(COR_TEXTO)
        p.setFont("Helvetica-Bold", 10)
        nome_cav = (c.nome[:30] + "...") if len(c.nome) > 30 else c.nome
        p.drawString(margem_x + 12, y - 79, f"Cavalo: {nome_cav}")
        p.setFillColor(COR_SUB)
        p.setFont("Helvetica", 9)
        p.drawRightString(margem_x + largura - 12, y - 79, f"{local}  |  {aula.get_local_display() or 'Picadeiro'}")

        # Sela + Cabecada
        p.setFillColor(COR_SUB)
        p.setFont("Helvetica", 9)
        sela_txt = (sela[:35] + "...") if len(sela) > 35 else sela
        cab_txt  = (cabecada[:35] + "...") if len(cabecada) > 35 else cabecada
        p.drawString(margem_x + 12, y - 93,  f"Sela:      {sela_txt}")
        p.drawString(margem_x + 12, y - 106, f"Cabecada: {cab_txt}")

        # Material
        if material_proprio:
            p.setFillColor(colors.HexColor('#dc2626'))
            p.setFont("Helvetica-Bold", 9)
            p.drawString(margem_x + 12, y - 120, "** MATERIAL PROPRIO — NAO USAR EQUIPAMENTO DA ESCOLA **")
        else:
            p.setFillColor(COR_SUB)
            p.setFont("Helvetica", 9)
            p.drawString(margem_x + 12, y - 120, "Material da Escola")

        # Observacao (se houver)
        if tem_obs:
            obs = aula.relatorio_treino
            obs_txt = (obs[:90] + "...") if len(obs) > 90 else obs
            p.setFillColor(colors.HexColor('#166534'))
            p.setFont("Helvetica-Oblique", 8.5)
            p.drawString(margem_x + 12, y - 134, f"Obs: {obs_txt}")

        y -= espaco_necessario

    p.save()
    return response


# ── Manejo em Massa ───────────────────────────────────────────────────────────




@login_required
def manejo_em_massa(request):
    empresa = getattr(request, "empresa", None) or request.user.perfil.empresa
    hoje = timezone.localdate()

    # ── PRazos configurados (da Base) ─────────────────────────
    try:
        cfg = ConfigPrazoManejo.objects.get(empresa=empresa)
        prazo_vacina = cfg.prazo_vacina
        prazo_vermifugo = cfg.prazo_vermifugo
        prazo_ferrageamento = cfg.prazo_ferrageamento
        prazo_casqueamento = cfg.prazo_casqueamento
    except ConfigPrazoManejo.DoesNotExist:
        prazo_vacina = 365
        prazo_vermifugo = 90
        prazo_ferrageamento = 60
        prazo_casqueamento = 60

    # ── POST: ATUALIZA CAVALO + DocumentoCavalo (fonte única de verdade) ────────
    if request.method == "POST":
        procedimento = request.POST.get("procedimento")
        data_str     = request.POST.get("data")
        cavalos_ids  = request.POST.getlist("cavalos_selecionados")

        if procedimento and data_str and cavalos_ids:
            data_proc = date.fromisoformat(data_str)

            cavalos = Cavalo.objects.filter(empresa=empresa, id__in=cavalos_ids)

            # Mapeamento procedimento → (campo_cavalo, tipo_doc, titulo_doc)
            MAPA = {
                "Vacinacao":     ("ultima_vacina",        "VACINA", "Vacinação"),
                "Vermifugacao":  ("ultimo_vermifugo",     "EXAME",  "Vermifugação"),
                "Ferrageamento": ("ultimo_ferrageamento", "OUTRO",  "Ferrageamento"),
                "Casqueamento":  ("ultimo_casqueamento",  "OUTRO",  "Casqueamento"),
            }

            if procedimento not in MAPA:
                messages.warning(request, "Procedimento inválido.")
                return redirect("manejo_em_massa")

            campo_cavalo, tipo_doc, titulo_doc = MAPA[procedimento]

            # Carrega config de preços da empresa (se existir)
            try:
                cfg_preco = ConfigPrecoManejo.objects.get(empresa=empresa)
            except Exception:
                cfg_preco = None

            # Mapeamento procedimento → campo de cobrança e tipo ItemFatura
            MAPA_PRECO = {
                "Vacinacao":     ("cobrar_vacina",        "valor_vacina",        "VETERINARIO"),
                "Vermifugacao":  ("cobrar_vermifugo",     "valor_vermifugo",     "VERMIFUGO"),
                "Ferrageamento": ("cobrar_ferrageamento", "valor_ferrageamento", "FERRAGEAMENTO"),
                "Casqueamento":  ("cobrar_casqueamento",  "valor_casqueamento",  "CASQUEIO"),
            }
            campo_cobrar, campo_valor, tipo_fatura = MAPA_PRECO[procedimento]

            for cavalo in cavalos:
                # 1. Atualiza o campo direto no Cavalo (fonte principal do dashboard)
                setattr(cavalo, campo_cavalo, data_proc)
                cavalo.save(update_fields=[campo_cavalo])

                # 2. Gera ItemFatura se cavalo é de hotelaria e procedimento é cobrado
                if (
                    cavalo.categoria == 'HOTELARIA'
                    and cfg_preco
                    and getattr(cfg_preco, campo_cobrar, False)
                ):
                    valor_proc = getattr(cfg_preco, campo_valor, Decimal('0.00'))
                    if valor_proc > 0:
                        hoje_proc = data_proc if hasattr(data_proc, 'year') else timezone.localdate()
                        venc = hoje_proc.replace(day=28) if hasattr(hoje_proc, 'replace') else hoje_proc
                        fatura, _ = Fatura.objects.get_or_create(
                            empresa=empresa,
                            aluno=cavalo.proprietario,
                            status='PENDENTE',
                            data_vencimento__year=hoje_proc.year,
                            data_vencimento__month=hoje_proc.month,
                            defaults={'data_vencimento': venc},
                        )
                        ItemFatura.objects.create(
                            fatura=fatura,
                            tipo=tipo_fatura,
                            cavalo=cavalo,
                            descricao=f"{titulo_doc} — {data_proc}",
                            valor=valor_proc,
                            data=hoje_proc,
                        )

                # 3. Cria ou atualiza o DocumentoCavalo correspondente
                #    (para o painel "Documentos & Vacinas" e histórico)
                # Para OUTRO (ferrageamento/casqueamento), usa o titulo como discriminador
                qs_doc = DocumentoCavalo.objects.filter(cavalo=cavalo, tipo=tipo_doc)
                if tipo_doc == "OUTRO":
                    qs_doc = qs_doc.filter(titulo=titulo_doc)

                doc = qs_doc.order_by("-data_validade").first()

                if doc:
                    doc.data_validade = data_proc
                    doc.save(update_fields=["data_validade"])
                else:
                    DocumentoCavalo.objects.create(
                        cavalo=cavalo,
                        tipo=tipo_doc,
                        titulo=titulo_doc,
                        data_validade=data_proc,
                    )

            messages.success(
                request,
                f"✅ {titulo_doc} registrada para {cavalos.count()} cavalo(s).",
                extra_tags="success"
            )
        else:
            messages.warning(request, "Selecione ao menos um cavalo, um procedimento e uma data.")

        return redirect("manejo_em_massa")

    # ── GET: lê dos campos diretos do Cavalo (mesma fonte que o dashboard) ───────

    def _dias_atraso(data_campo):
        if not data_campo:
            return 9999
        return (hoje - data_campo).days

    def _atraso_excedido(c):
        """Retorna o maior excedente de dias (0 = em dia)."""
        atrasos = [
            max(0, _dias_atraso(c.ultima_vacina)    - prazo_vacina),
            max(0, _dias_atraso(c.ultimo_vermifugo) - prazo_vermifugo),
        ]
        if c.usa_ferradura == "SIM":
            atrasos.append(max(0, _dias_atraso(c.ultimo_ferrageamento) - prazo_ferrageamento))
        else:
            atrasos.append(max(0, _dias_atraso(c.ultimo_casqueamento)  - prazo_casqueamento))
        bonus = 100000 if c.status_saude != "Saudável" else 0
        return sum(atrasos) + bonus

    cavalos_qs = (
        Cavalo.objects
        .filter(empresa=empresa)
        .select_related("proprietario")
        .order_by("nome")
    )

    cavalos_status = []
    for cavalo in cavalos_qs:
        score = _atraso_excedido(cavalo)
        cavalos_status.append({
            "obj":           cavalo,
            "vencido":       score > 0,
            "atraso_maximo": score,
        })

    # Mais crítico primeiro
    cavalos_status.sort(key=lambda x: x["atraso_maximo"], reverse=True)

    return render(request, "gateagora/manejo_em_massa.html", {
        "empresa":             empresa,
        "hoje":                hoje,
        "cavalos_status":      cavalos_status,
        "prazo_vacina":        prazo_vacina,
        "prazo_vermifugo":     prazo_vermifugo,
        "prazo_ferrageamento": prazo_ferrageamento,
        "prazo_casqueamento":  prazo_casqueamento,
    })






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

    # Carrega prazos configurados
    try:
        cfg = ConfigPrazoManejo.objects.get(empresa=empresa)
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

    # Verifica pendências respeitando se o cavalo usa ferradura ou não
    pendencias = []

    # Vacina e Vermifugo são obrigatórios para todos
    if _dias_atraso(cavalo.ultima_vacina) > prazo_vacina:
        pendencias.append("Vacinação")

    if _dias_atraso(cavalo.ultimo_vermifugo) > prazo_vermifugo:
        pendencias.append("Vermifugação")

    # Ferrageamento ou Casqueamento dependendo do tipo
    if cavalo.usa_ferradura == 'SIM':
        if _dias_atraso(cavalo.ultimo_ferrageamento) > prazo_ferrageamento:
            pendencias.append("Ferrageamento")
    else:
        if _dias_atraso(cavalo.ultimo_casqueamento) > prazo_casqueamento:
            pendencias.append("Casqueamento")

    if pendencias:
        messages.warning(
            request,
            f"{cavalo.nome} ainda tem pendências: {', '.join(pendencias)}. "
            f"Registre os procedimentos em 'Manejo em Massa' antes de marcar como Saudável."
        )
    else:
        # Só marca como Saudável se realmente não houver pendências
        cavalo.status_saude = 'Saudável'
        cavalo.save(update_fields=['status_saude'])
        messages.success(
            request, 
            f"✅ {cavalo.nome} marcado como Saudável! Todos os procedimentos estão em dia."
        )

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
    hoje = timezone.localdate()

    itens_qs = (
        ItemEstoque.objects
        .filter(empresa=empresa)
        .prefetch_related('lotes')
    )

    # Itens que já tiveram ajuste hoje
    itens_com_ajuste_hoje = set(
        MovimentacaoEstoque.objects
        .filter(empresa=empresa, data=hoje, tipo="ajuste")
        .values_list("item_id", flat=True)
    )

    for item in itens_qs:
        lotes_ativos = item.lotes.filter(ativo=True)

        # ── Lote mais próximo (apenas para exibição) ───────────────────────
        lote = (
            lotes_ativos
            .exclude(data_validade__isnull=True)
            .order_by("data_validade")
            .first()
        )
        item.lote_numero  = lote.numero_lote if lote else None
        item.data_validade = lote.data_validade if lote else None

        # ── FLAG: item vencido (NÃO é property) ────────────────────────────
        item.esta_vencido = lotes_ativos.filter(
            data_validade__lt=hoje
        ).exists()

        # ── Dias para vencer ───────────────────────────────────────────────
        datas_futuras = lotes_ativos.filter(
            data_validade__gte=hoje
        ).values_list("data_validade", flat=True)

        if datas_futuras:
            item.dias_para_vencer_calc = (min(datas_futuras) - hoje).days
        else:
            item.dias_para_vencer_calc = None

        # ── Quantidade válida (não vencida) ────────────────────────────────
        item.quantidade_valida_calc = (
            lotes_ativos
            .filter(data_validade__gte=hoje)
            .aggregate(total=Sum("quantidade"))["total"] or 0
        )

        # ── Quantidade total (inclui vencidos) ─────────────────────────────
        item.quantidade_atual_calc = (
            lotes_ativos
            .aggregate(total=Sum("quantidade"))["total"] or 0
        )

        # ── Flag: ajuste feito hoje ────────────────────────────────────────
        item.ajuste_feito_hoje = item.id in itens_com_ajuste_hoje

    # ── Ordenação inteligente ─────────────────────────────────────────────
    def _sort_key(item):
        if item.esta_vencido:
            return (0, 0, item.nome)
        if item.dias_para_vencer_calc is not None:
            return (1, item.dias_para_vencer_calc, item.nome)
        return (2, 9999, item.nome)

    itens = sorted(itens_qs, key=_sort_key)

    context = {
        "brand_name": BRAND_NAME,
        "empresa": empresa,
        "hoje": hoje,
        "itens": itens,
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


# ── Minhas Aulas (Aluno) ──────────────────────────────────────────────────────

@login_required
def minhas_aulas(request):
    "Tela exclusiva para o Aluno ver e confirmar suas próprias aulas."

    # 1. Perfil (obrigatório)
    try:
        perfil = request.user.perfil
    except Exception:
        return redirect('login')

    # 2. Aluno vinculado ao usuário via perfil_usuario
    try:
        aluno = Aluno.objects.select_related('plano').get(perfil_usuario=perfil)
    except Aluno.DoesNotExist:
        aluno = None

    if not aluno or aluno.empresa_id != perfil.empresa_id:
        return render(request, "gateagora/minhas_aulas.html", {
            "aluno": None, "empresa": perfil.empresa
        })

    # 3. Prazos de confirmação
    config = ConfigPrazoManejo.objects.filter(empresa=perfil.empresa).first()
    prazo_horas = config.prazo_confirmacao_horas if config else 0
    agora = timezone.now()
    trinta_dias_atras = agora - timezone.timedelta(days=30)

    # 4. Aulas do aluno — futuras + últimos 30 dias
    aulas = list(
        Aula.objects
        .filter(
            aluno=aluno,
            empresa=perfil.empresa,
            data_hora__gte=trinta_dias_atras,
        )
        .select_related(
            "cavalo", "cavalo__baia", "cavalo__piquete",
            "instrutor", "instrutor__user",
        )
        .order_by("data_hora")
    )
    _conf_ma = {
        c.aula_id: c
        for c in ConfirmacaoPresenca.objects.filter(
            aula_id__in=[a.id for a in aulas],
            aluno=aluno,
        )
    }

    proximas = []
    historico = []

    for aula in aulas:
        confirmacao = _conf_ma.get(aula.id)
        aula_passada = aula.data_hora < agora
        pode_confirmar = (
            not aula_passada
            and not confirmacao
            and (
                prazo_horas == 0
                or aula.data_hora <= agora + timezone.timedelta(hours=prazo_horas)
            )
        )
        item = {
            "aula":         aula,
            "ja_confirmou": bool(confirmacao),
            "confirmacao":  confirmacao,
            "aula_passada": aula_passada,
            "pode_confirmar": pode_confirmar,
        }
        if aula_passada:
            historico.append(item)
        else:
            proximas.append(item)

    historico = list(reversed(historico))

    # ── Extras para as 3 abas ─────────────────────────────────────────────────
    proxima_aula     = proximas[0] if proximas else None
    proxima_aula_iso = proxima_aula['aula'].data_hora.isoformat() if proxima_aula else None
    semana           = agora + timezone.timedelta(days=7)
    aulas_semana     = [p for p in proximas if p['aula'].data_hora <= semana]

    cavalo    = None
    instrutor = None
    if proxima_aula:
        cavalo    = proxima_aula['aula'].cavalo
        instrutor = proxima_aula['aula'].instrutor
    elif historico:
        cavalo    = historico[0]['aula'].cavalo
        instrutor = historico[0]['aula'].instrutor

    # ── Histórico de manejo do cavalo (aba Meu Cavalo) ────────────────────────
    historico_manejo = []
    if cavalo:
        historico_manejo = list(
            RegistroOcorrencia.objects
            .filter(cavalo=cavalo)
            .order_by('-data')[:10]
        )

    # ── Ranking gamificação — mesmo cálculo do dashboard ─────────────────────
    from datetime import timedelta as _td2
    hoje_ma      = agora.date()
    noventa_ma   = hoje_ma - _td2(days=90)

    candidatos_ma = list(
        Aluno.objects
        .filter(empresa=perfil.empresa, ativo=True)
        .annotate(
            aulas_mes=Count(
                'aulas',
                filter=Q(
                    aulas__concluida=True,
                    aulas__data_hora__date__year=hoje_ma.year,
                    aulas__data_hora__date__month=hoje_ma.month,
                )
            )
        )
        .filter(aulas_mes__gt=0)
        .order_by('-aulas_mes', 'nome')
    )

    # Streaks dinâmicos para todos os candidatos
    hist_ma = list(
        Aula.objects
        .filter(
            aluno_id__in=[a.id for a in candidatos_ma],
            concluida=True,
            data_hora__date__gte=noventa_ma,
            data_hora__date__lte=hoje_ma,
        )
        .values('aluno_id', 'data_hora')
    )
    semanas_ma = {}
    for row in hist_ma:
        iso = row['data_hora'].isocalendar()
        key = iso[0] * 100 + iso[1]
        semanas_ma.setdefault(row['aluno_id'], set()).add(key)

    def _streak_ma(aluno_id):
        semanas = semanas_ma.get(aluno_id, set())
        if not semanas:
            return 0
        streak = 0
        check  = hoje_ma
        for _ in range(13):
            iso = check.isocalendar()
            key = iso[0] * 100 + iso[1]
            if key in semanas:
                streak += 1
                check  -= _td2(days=7)
            else:
                if streak == 0:
                    check -= _td2(days=7)
                    continue
                break
        return streak

    for al in candidatos_ma:
        al.streak_dinamico = _streak_ma(al.id)

    ranking_app = sorted(
        candidatos_ma,
        key=lambda a: (-a.streak_dinamico, -a.aulas_mes, a.nome)
    )[:10]

    # Posição do aluno atual no ranking
    posicao_aluno = next(
        (i + 1 for i, a in enumerate(ranking_app) if a.id == aluno.id),
        None
    )

    return render(
        request,
        "gateagora/minhas_aulas.html",
        {
            "aluno":            aluno,
            "proximas":         proximas,
            "historico":        historico,
            "prazo_horas":      prazo_horas,
            "empresa":          perfil.empresa,
            "proxima_aula":     proxima_aula,
            "proxima_aula_iso": proxima_aula_iso,
            "aulas_semana":     aulas_semana,
            "cavalo":           cavalo,
            "instrutor":        instrutor,
            "historico_manejo": historico_manejo,
            # Gamificação
            "streak_atual":     getattr(aluno, 'streak_atual', 0),
            "melhor_streak":    getattr(aluno, 'melhor_streak', 0),
            "selo_streak":      _selo_streak(getattr(aluno, 'streak_atual', 0)),
            "faltam_bronze":    max(0, 5 - getattr(aluno, 'streak_atual', 0)),
            "ranking_app":      ranking_app,
            "posicao_aluno":    posicao_aluno,
        }
    )


@login_required
@require_POST
def confirmar_presenca(request, aula_id):
    """Aluno confirma presença em uma aula."""
    try:
        perfil = request.user.perfil
    except Exception:
        return redirect('login')

    if perfil.cargo != 'Aluno':
        return redirect('dashboard')

    empresa      = perfil.empresa
    nome_usuario = request.user.get_full_name() or request.user.username

    try:
        aluno = Aluno.objects.get(perfil_usuario=perfil)
    except Aluno.DoesNotExist:
        messages.error(request, "Aluno não encontrado para este usuário.")
        return redirect('minhas_aulas')

    aula  = get_object_or_404(Aula, id=aula_id, empresa=empresa, aluno=aluno)
    agora = timezone.now()

    if agora > aula.data_hora:
        messages.warning(request, "Esta aula já aconteceu, não é possível confirmar.")
        return redirect('minhas_aulas')

    _, criado = ConfirmacaoPresenca.objects.get_or_create(aula=aula, aluno=aluno)

    if criado:
        _atualizar_streak(aluno)
        messages.success(request, f"✅ Presença confirmada para {aula.data_hora.strftime('%d/%m às %H:%M')}!")
    else:
        messages.info(request, "Você já havia confirmado esta aula.")

    return redirect('minhas_aulas')


@login_required
@require_POST
def desconfirmar_presenca(request, aula_id):
    """Aluno cancela a confirmação de presença."""
    try:
        perfil = request.user.perfil
    except Exception:
        return redirect('login')

    if perfil.cargo != 'Aluno':
        return redirect('dashboard')

    empresa      = perfil.empresa
    nome_usuario = request.user.get_full_name() or request.user.username

    try:
        aluno = Aluno.objects.get(perfil_usuario=perfil)
    except Aluno.DoesNotExist:
        messages.error(request, "Aluno não encontrado para este usuário.")
        return redirect('minhas_aulas')

    aula  = get_object_or_404(Aula, id=aula_id, empresa=empresa, aluno=aluno)
    agora = timezone.now()

    if agora > aula.data_hora:
        messages.warning(request, "Esta aula já aconteceu.")
        return redirect('minhas_aulas')

    deleted, _ = ConfirmacaoPresenca.objects.filter(aula=aula, aluno=aluno).delete()

    if deleted:
        messages.info(request, f"Confirmação cancelada para {aula.data_hora.strftime('%d/%m às %H:%M')}.")

    return redirect('minhas_aulas')


# ── Relatórios ────────────────────────────────────────────────────────────────

@login_required
def relatorios(request):
    """Página principal de relatórios financeiros."""
    empresa = request.empresa
    if not empresa:
        return redirect('dashboard')

    from datetime import date
    import calendar as _cal

    hoje = timezone.localdate()
    mes  = int(request.GET.get('mes',  hoje.month))
    ano  = int(request.GET.get('ano',  hoje.year))
    tipo = request.GET.get('tipo', 'faturamento')

    inicio   = date(ano, mes, 1)
    ultimo   = _cal.monthrange(ano, mes)[1]
    fim      = date(ano, mes, ultimo)

    faturas = (
        Fatura.objects
        .filter(empresa=empresa, data_vencimento__range=(inicio, fim))
        .select_related('aluno')
        .order_by('status', 'data_vencimento')
    )
    total_previsto = faturas.aggregate(t=Sum('valor'))['t'] or Decimal('0')
    total_recebido = faturas.filter(status='PAGO').aggregate(t=Sum('valor'))['t'] or Decimal('0')
    total_pendente = faturas.filter(status='PENDENTE').aggregate(t=Sum('valor'))['t'] or Decimal('0')
    total_atrasado = faturas.filter(status='ATRASADO').aggregate(t=Sum('valor'))['t'] or Decimal('0')

    freq_alunos = list(
        Aluno.objects
        .filter(empresa=empresa, ativo=True)
        .annotate(
            aulas_realizadas=Count(
                'aulas',
                filter=Q(aulas__concluida=True,
                         aulas__data_hora__date__range=(inicio, fim))
            )
        )
        .filter(aulas_realizadas__gt=0)
        .order_by('-aulas_realizadas')
    )

    # Instrutor em Aula é FK para Perfil — agrupa direto no model Aula
    from django.db.models import Count as _Count2
    instrutores_ids = list(
        Perfil.objects.filter(empresa=empresa, cargo='Instrutor').values_list('id', flat=True)
    )
    instrutores_raw = (
        Aula.objects
        .filter(
            empresa=empresa,
            instrutor_id__in=instrutores_ids,
            concluida=True,
            data_hora__date__range=(inicio, fim),
        )
        .values('instrutor_id', 'instrutor__user__first_name', 'instrutor__user__last_name')
        .annotate(aulas_dadas=_Count2('id'))
        .order_by('-aulas_dadas')
    )
    instrutores = [
        type('Inst', (), {
            'nome': f"{r['instrutor__user__first_name']} {r['instrutor__user__last_name']}".strip(),
            'aulas_dadas': r['aulas_dadas'],
        })()
        for r in instrutores_raw
    ]

        # Estoque com validade próxima ou vencida
    estoque_validade = list(
        ItemEstoque.objects
        .filter(empresa=empresa)
        .prefetch_related('lotes')
        .order_by('nome')
    )

    # Não atribui nada nas properties — apenas força o cálculo
    for item in estoque_validade:
        _ = item.quantidade_valida      # força cache
        _ = item.dias_para_vencer
        _ = item.status_validade

    meses_pt = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

    return render(request, 'gateagora/relatorios.html', {
        'empresa':          empresa,
        'mes':              mes,
        'ano':              ano,
        'tipo':             tipo,
        'mes_nome':         meses_pt[mes],
        'inicio':           inicio,
        'fim':              fim,
        'faturas':          faturas,
        'total_previsto':   total_previsto,
        'total_recebido':   total_recebido,
        'total_pendente':   total_pendente,
        'total_atrasado':   total_atrasado,
        'total_recebido_float': float(total_recebido),
        'total_pendente_float': float(total_pendente),
        'total_atrasado_float': float(total_atrasado),
        'freq_alunos':      freq_alunos,
        'instrutores':      instrutores,
        'estoque_validade': estoque_validade,
        'meses_opcoes':     [(m, meses_pt[m]) for m in range(1, 13)],
        'anos_opcoes':      list(range(hoje.year - 2, hoje.year + 1)),
        'inadimplencia_pct': round(
            float(total_atrasado + total_pendente) / float(total_previsto) * 100, 1
        ) if total_previsto else 0,
    })


@login_required
def relatorio_pdf(request):
    """Gera PDF do relatório financeiro do mês."""
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    from datetime import date
    import calendar as _cal

    empresa = request.empresa
    if not empresa:
        return redirect('dashboard')

    hoje = timezone.localdate()
    mes  = int(request.GET.get('mes', hoje.month))
    ano  = int(request.GET.get('ano', hoje.year))

    meses_pt = ['','Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

    inicio = date(ano, mes, 1)
    fim    = date(ano, mes, _cal.monthrange(ano, mes)[1])

    faturas = (
        Fatura.objects
        .filter(empresa=empresa, data_vencimento__range=(inicio, fim))
        .select_related('aluno')
        .order_by('status', 'data_vencimento')
    )
    total_previsto = faturas.aggregate(t=Sum('valor'))['t'] or Decimal('0')
    total_recebido = faturas.filter(status='PAGO').aggregate(t=Sum('valor'))['t'] or Decimal('0')
    total_atrasado = faturas.filter(status__in=['PENDENTE','ATRASADO']).aggregate(t=Sum('valor'))['t'] or Decimal('0')

    freq_alunos = list(
        Aluno.objects.filter(empresa=empresa, ativo=True)
        .annotate(aulas_realizadas=Count(
            'aulas', filter=Q(aulas__concluida=True,
                              aulas__data_hora__date__range=(inicio, fim))))
        .filter(aulas_realizadas__gt=0).order_by('-aulas_realizadas')
    )
    # streak_atual pode não existir se migração removeu o campo — usa getattr com fallback
    for al in freq_alunos:
        if not hasattr(al, 'streak_atual'):
            al.streak_atual = 0

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_{mes:02d}_{ano}.pdf"'

    doc    = SimpleDocTemplate(response, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    COR_P  = HexColor('#4f46e5')
    COR_V  = HexColor('#10b981')
    COR_R  = HexColor('#ef4444')
    COR_CZ = HexColor('#f1f5f9')
    COR_TX = HexColor('#1e293b')

    def fmt(valor):
        return f"R$ {valor:,.2f}".replace(',','X').replace('.',',').replace('X','.')

    story.append(Paragraph(f"Relatório Financeiro — {meses_pt[mes]}/{ano}",
        ParagraphStyle('t', fontSize=18, fontName='Helvetica-Bold', textColor=COR_P, spaceAfter=4)))
    story.append(Paragraph(empresa.nome,
        ParagraphStyle('s', fontSize=10, textColor=HexColor('#64748b'), spaceAfter=16)))

    # Resumo
    res = Table(
        [['PREVISTO','RECEBIDO','INADIMPLENTE'],
         [fmt(total_previsto), fmt(total_recebido), fmt(total_atrasado)]],
        colWidths=[5.5*cm, 5.5*cm, 5.5*cm]
    )
    res.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),COR_P), ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,-1),9),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME',(0,1),(-1,1),'Helvetica-Bold'), ('FONTSIZE',(0,1),(-1,1),13),
        ('TEXTCOLOR',(1,1),(1,1),COR_V), ('TEXTCOLOR',(2,1),(2,1),COR_R),
        ('BACKGROUND',(0,1),(-1,1),COR_CZ),
        ('BOX',(0,0),(-1,-1),0.5,HexColor('#e2e8f0')),
        ('INNERGRID',(0,0),(-1,-1),0.5,HexColor('#e2e8f0')),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    story.append(res)
    story.append(Spacer(1, 0.5*cm))

    # Faturas
    story.append(Paragraph("Faturas do Período",
        ParagraphStyle('sec', fontSize=12, fontName='Helvetica-Bold',
                       textColor=COR_TX, spaceBefore=12, spaceAfter=6)))
    fd = [['Aluno','Vencimento','Valor','Status']]
    for f in faturas:
        fd.append([
            (f.aluno.nome[:35] if f.aluno else '-'),
            f.data_vencimento.strftime('%d/%m/%Y'),
            fmt(f.valor),
            {'PAGO':'Pago','PENDENTE':'Pendente','ATRASADO':'Atrasado'}.get(f.status, f.status),
        ])
    ft = Table(fd, colWidths=[7*cm, 3*cm, 3.5*cm, 3*cm])
    fts = TableStyle([
        ('BACKGROUND',(0,0),(-1,0),COR_P),('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),
        ('ALIGN',(1,0),(-1,-1),'CENTER'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,COR_CZ]),
        ('BOX',(0,0),(-1,-1),0.5,HexColor('#e2e8f0')),
        ('INNERGRID',(0,0),(-1,-1),0.3,HexColor('#e2e8f0')),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ])
    for i, f in enumerate(faturas, 1):
        if f.status == 'PAGO':
            fts.add('TEXTCOLOR',(3,i),(3,i),COR_V)
        elif f.status in ('PENDENTE','ATRASADO'):
            fts.add('TEXTCOLOR',(3,i),(3,i),COR_R)
    ft.setStyle(fts)
    story.append(ft)

    # Frequência
    if freq_alunos:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Frequência de Alunos",
            ParagraphStyle('sec2', fontSize=12, fontName='Helvetica-Bold',
                           textColor=COR_TX, spaceBefore=12, spaceAfter=6)))
        frd = [['Aluno','Aulas','Streak']]
        for al in freq_alunos:
            frd.append([al.nome[:35], str(al.aulas_realizadas), f"{al.streak_atual} sem"])
        frt = Table(frd, colWidths=[9*cm, 3.5*cm, 4*cm])
        frt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),COR_P),('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),
            ('ALIGN',(1,0),(-1,-1),'CENTER'),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,COR_CZ]),
            ('BOX',(0,0),(-1,-1),0.5,HexColor('#e2e8f0')),
            ('INNERGRID',(0,0),(-1,-1),0.3,HexColor('#e2e8f0')),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ]))
        story.append(frt)

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        f"Gerado em {hoje.strftime('%d/%m/%Y')} · Gate 4 — Gestão de Haras e Hípicas",
        ParagraphStyle('rod', fontSize=7, textColor=HexColor('#94a3b8'), alignment=TA_CENTER)
    ))
    doc.build(story)
    return response


# ── Relatório PDF de Estoque / Validades ─────────────────────────────────────

@login_required
def relatorio_estoque_pdf(request):
    """Gera PDF do estoque com controle de validade."""
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from datetime import date

    empresa = request.empresa
    if not empresa:
        return redirect('dashboard')

    hoje = timezone.localdate()

    itens = list(
        ItemEstoque.objects
        .filter(empresa=empresa)
        .prefetch_related('lotes')
        .order_by('nome')
    )

    # Força cálculo das propriedades
    for item in itens:
        _ = item.quantidade_valida
        _ = item.dias_para_vencer
        _ = item.status_validade

    # ... resto do código da função continua igual

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="estoque_validade_{hoje.strftime("%Y%m%d")}.pdf"'
    )

    w, h   = A4
    c      = rl_canvas.Canvas(response, pagesize=A4)
    margem = 2.5 * 28.35  # 2.5cm em pontos

    COR_PRIMARIA = HexColor('#4f46e5')
    COR_VERDE    = HexColor('#10b981')
    COR_AMBAR    = HexColor('#f59e0b')
    COR_VERMELHO = HexColor('#ef4444')
    COR_CINZA    = HexColor('#f8fafc')
    COR_TEXTO    = HexColor('#1e293b')
    COR_MUTED    = HexColor('#64748b')

    def nova_pagina(pagina):
        if pagina > 1:
            c.showPage()
        # Cabeçalho
        c.setFillColor(COR_PRIMARIA)
        c.rect(0, h - 60, w, 60, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(margem, h - 30, 'Relatório de Estoque — Controle de Validade')
        c.setFont('Helvetica', 9)
        c.drawString(margem, h - 47, f'{empresa.nome}   ·   Gerado em {hoje.strftime("%d/%m/%Y")}')
        if pagina > 1:
            c.setFont('Helvetica', 8)
            c.drawRightString(w - margem, h - 47, f'Página {pagina}')
        return h - 80

    def linha_tabela(y, cols, bg=None, bold=False, cor_status=None):
        """Desenha uma linha da tabela."""
        altl = 20
        if bg:
            c.setFillColor(bg)
            c.rect(margem, y - altl + 4, w - 2 * margem, altl, fill=1, stroke=0)

        font = 'Helvetica-Bold' if bold else 'Helvetica'
        larguras = [180, 70, 60, 80, 90]  # Nome, Qtd, Unid, Lote, Validade, Status
        x = margem + 4

        for i, (txt, larg) in enumerate(zip(cols, larguras)):
            if i == 5 and cor_status:
                c.setFillColor(cor_status)
            else:
                c.setFillColor(COR_TEXTO if not bold else colors.white)
            c.setFont(font, 8 if not bold else 7.5)
            c.drawString(x, y - 10, str(txt)[:30])
            x += larg

        # Linha separadora
        c.setStrokeColor(HexColor('#e2e8f0'))
        c.setLineWidth(0.3)
        c.line(margem, y - altl + 4, w - margem, y - altl + 4)
        return y - altl

    # ── Início do PDF ────────────────────────────────────────────────────────
    pagina = 1
    y = nova_pagina(pagina)

    # Resumo rápido
    vencidos = sum(1 for i in itens if i.status_validade == 'vencido')
    alertas  = sum(1 for i in itens if i.status_validade == 'alerta')
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(COR_TEXTO)
    c.drawString(margem, y, f'Total de itens: {len(itens)}')
    c.setFillColor(COR_VERMELHO)
    c.drawString(margem + 130, y, f'Vencidos: {vencidos}')
    c.setFillColor(COR_AMBAR)
    c.drawString(margem + 240, y, f'A vencer em 30 dias: {alertas}')
    y -= 20

    # Cabeçalho da tabela
    y = linha_tabela(y,
        ['PRODUTO', 'QTDE', 'UNID', 'LOTE', 'VALIDADE', 'STATUS'],
        bg=COR_PRIMARIA, bold=True
    )

    # Linhas de dados — itera sobre lotes ativos de cada item
    linha_idx = 0
    for item in itens:
        lotes_ativos = item.lotes.filter(ativo=True).order_by('data_validade')
        if not lotes_ativos.exists():
            # Item sem lotes: exibe linha com dados básicos
            if y < 60:
                pagina += 1
                y = nova_pagina(pagina)
                y = linha_tabela(y,
                    ['PRODUTO', 'QTDE', 'UNID', 'LOTE', 'VALIDADE', 'STATUS'],
                    bg=COR_PRIMARIA, bold=True
                )
            bg_linha = COR_CINZA if linha_idx % 2 == 0 else None
            y = linha_tabela(y,
                [item.nome, '—', item.unidade, '—', '—', '—'],
                bg=bg_linha, cor_status=COR_MUTED
            )
            linha_idx += 1
            continue

        for lote in lotes_ativos:
            if y < 60:
                pagina += 1
                y = nova_pagina(pagina)
                y = linha_tabela(y,
                    ['PRODUTO', 'QTDE', 'UNID', 'LOTE', 'VALIDADE', 'STATUS'],
                    bg=COR_PRIMARIA, bold=True
                )

            val_txt = lote.data_validade.strftime('%d/%m/%Y') if lote.data_validade else '—'

            if lote.data_validade:
                dias = (lote.data_validade - hoje).days
                if dias < 0:
                    status_txt = 'VENCIDO'
                    cor_s      = COR_VERMELHO
                elif dias <= 5:
                    status_txt = f'{dias}d — CRÍTICO'
                    cor_s      = COR_VERMELHO
                elif dias <= 30:
                    status_txt = f'{dias}d p/ vencer'
                    cor_s      = COR_AMBAR
                else:
                    status_txt = f'{dias}d'
                    cor_s      = COR_VERDE
            else:
                status_txt = '—'
                cor_s      = COR_MUTED

            bg_linha = COR_CINZA if linha_idx % 2 == 0 else None
            qtd_txt  = str(lote.quantidade) if hasattr(lote, 'quantidade') else '—'
            y = linha_tabela(y,
                [item.nome, qtd_txt, item.unidade,
                 lote.numero_lote or '—', val_txt, status_txt],
                bg=bg_linha, cor_status=cor_s
            )
            linha_idx += 1

    # Rodapé
    c.setFillColor(COR_MUTED)
    c.setFont('Helvetica', 7)
    c.drawCentredString(w / 2, 30,
        'Gate 4 — Gestão de Haras e Hípicas  ·  Este relatório é confidencial')

    c.save()
    return response

