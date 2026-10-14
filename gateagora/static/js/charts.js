// Gate4 — Gráficos do Dashboard
// Espera que as variáveis existam em window (declaradas no dashboard.html)

function buildCharts() {
  // Cores vindas do tema (claro/escuro) definido no dashboard.html
  const emerald  = cv('--emerald-text') || '#10b981';
  const red      = '#ef4444';
  const amber    = '#f59e0b';
  const blue     = '#3b82f6';
  const indigo   = '#6366f1';
  const grid     = cv('--border')       || '#30363d';
  const strong   = cv('--text-strong')  || '#ffffff';
  const muted    = cv('--text-muted')   || '#8b949e';
  const CAT_CORES = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  /* Fluxo Financeiro 6 Meses */
  if (window.pode_ver_financeiro) {
    const elFin6 = document.getElementById('chartFinanceiro6Meses');
    if (elFin6) {
      if (elFin6._c) elFin6._c.destroy();
      elFin6.style.maxHeight = (window.innerWidth < 768 ? 200 : 260) + 'px';
      elFin6._c = new Chart(elFin6, {
        type: 'bar',
        data: {
          labels: window.labels_meses || [],
          datasets: [
            { label: 'Receitas', data: window.dados_receita || [], backgroundColor: '#6366f1', borderRadius: 6, barThickness: 14 },
            { label: 'Despesas', data: window.dados_despesa || [], backgroundColor: grid, borderRadius: 6, barThickness: 14 },
            { label: 'Saldo Líquido', type: 'line', data: window.dados_lucro || [],
              borderColor: emerald, borderWidth: 2.5, pointBackgroundColor: emerald, tension: 0.4, fill: false, pointRadius: 3 }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top', align: 'end', labels: { boxWidth: 8, font: { size: 9 }, color: muted } } },
          scales: {
            y: { grid: { color: grid + '40' }, ticks: { color: strong, font: { size: 10, weight: '600' } } },
            x: { grid: { display: false }, ticks: { color: muted } }
          }
        }
      });
    }
  }

  /* Faturamento — linha + barra */
  const elFin = document.getElementById('chartFaturamento');
  if (elFin) {
    const maxHeight = window.innerWidth < 768 ? 200 : 260;
    elFin.style.maxHeight = maxHeight + 'px';
    const lblF = window.receita_labels || [];
    const dadF = window.receita_valores || [];
    if (elFin._c) elFin._c.destroy();
    if (lblF.length > 0) {
      elFin._c = new Chart(elFin, {
        type: 'line',
        data: {
          labels: lblF,
          datasets: [{
            label: 'Faturamento (R$)',
            data: dadF,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37,99,235,0.1)',
            tension: 0.3,
            fill: true,
            borderWidth: 2,
            pointRadius: 3
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: { beginAtZero: true, grid: { color: grid + '40' }, ticks: { color: strong, font: { size: 10, weight: '600' } } },
            x: { grid: { display: false }, ticks: { color: muted } }
          }
        }
      });
    }
  }

  /* Receita por Tipo — rosca */
  const elCat = document.getElementById('chartReceitaTipo');
  if (elCat) {
    const maxHeight = window.innerWidth < 768 ? 200 : 260;
    elCat.style.maxHeight = maxHeight + 'px';
    const lblC = window.receita_por_tipo_labels || [];
    const dadC = window.receita_por_tipo_valores || [];
    if (elCat._c) elCat._c.destroy();
    if (lblC.length > 0) {
      const cores = CAT_CORES.slice(0, lblC.length);
      elCat._c = new Chart(elCat, {
        type: 'doughnut',
        data: {
          labels: lblC,
          datasets: [{
            data: dadC,
            backgroundColor: cores,
            borderWidth: 0,
            hoverOffset: 8
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '70%',
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => ` R$ ${ctx.raw.toFixed(2).replace('.', ',')}` } }
          }
        }
      });
      // Atualiza legenda se existe
      const leg = document.getElementById('legendaReceita');
      if (leg) {
        leg.innerHTML = lblC.map((l, i) => `
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:10px;margin-bottom:4px;">
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="width:10px;height:10px;border-radius:50%;background:${cores[i]};display:inline-block;flex-shrink:0"></span>
              <span style="color:var(--text-main)">${l}</span>
            </div>
            <span style="font-family:var(--font-mono);font-weight:700;color:var(--text-main)">
              R$ ${dadC[i].toFixed(2).replace('.', ',')}
            </span>
          </div>`).join('');
      }
    }
  }

  /* Inadimplência — rosca */
  const elInad = document.getElementById('chartInadimplencia');
  if (elInad) {
    const maxHeight = window.innerWidth < 768 ? 200 : 260;
    elInad.style.maxHeight = maxHeight + 'px';
    const lblI = window.inadimplencia_labels || [];
    const dadI = window.inadimplencia_valores || [];
    const bgI = ['#10b981', '#ef4444', '#f59e0b'];
    if (elInad._c) elInad._c.destroy();
    elInad._c = new Chart(elInad, {
      type: 'doughnut',
      data: {
        labels: lblI,
        datasets: [{
          data: dadI,
          backgroundColor: bgI
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '74%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        animation: { duration: 600 }
      }
    });
  }

  /* Ocupação Baias — mini donut no KPI */
  const elOc = document.getElementById('chartOcupacao');
  if (elOc) {
    if (elOc._c) elOc._c.destroy();
    elOc._c = new Chart(elOc, {
      type: 'doughnut',
      data: {
        labels: ['Ocupadas', 'Livres'],
        datasets: [{
          data: [window.baias_ocupadas || 0, window.baias_livres || 0],
          backgroundColor: ['#6366f1', grid],
          borderWidth: 0
        }]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        cutout: '78%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        animation: { duration: 600 }
      }
    });
  }

  /* Treinos por Cavalo — barra horizontal com scroll */
  const lim = window.limite_treinos_mes || 20;
  const lblT = window.ranking_cavalos_labels || [];
  const dadT = window.ranking_cavalos_dados || [];
  const dadR = window.ranking_receita || [];

  const elTr = document.getElementById('chartTreinosCavalos');
  const cont = document.getElementById('containerGraficoCavalos');
  if (elTr && cont) {
    const alturaTotal = Math.max(130, lblT.length * 26);
    cont.style.height = alturaTotal + 'px';

    if (elTr._c) elTr._c.destroy();
    elTr._c = new Chart(elTr, {
      type: 'bar',
      data: {
        labels: lblT.map((nome, i) => dadR[i] > 0 ? `${nome}  · R$ ${dadR[i].toFixed(0)}` : nome),
        datasets: [
          {
            label: 'Aulas',
            data: dadT,
            backgroundColor: dadT.map(v => v >= lim ? red : '#6366f1'),
            borderRadius: 5,
            barPercentage: 0.5,
            categoryPercentage: 1.8
          },
          {
            label: `Limite (${lim})`,
            type: 'line',
            data: Array(lblT.length).fill(lim),
            borderColor: red + '70',
            borderWidth: 1.5,
            borderDash: [5, 4],
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            align: 'end',
            labels: { boxWidth: 8, font: { size: 9 }, color: muted }
          },
          tooltip: {
            callbacks: {
              label: ctx => ctx.dataset.type === 'line'
                ? ` Limite: ${lim}`
                : (dadR[ctx.dataIndex] !== undefined
                  ? ` ${ctx.raw} aula(s)  |  R$ ${dadR[ctx.dataIndex].toFixed(2).replace('.', ',')}`
                  : ` ${ctx.raw} aula(s)`)
            }
          }
        },
        scales: {
          y: {
            grid: { display: false },
            offset: true,
            ticks: { color: strong, font: { size: 11, weight: '600' } }
          },
          x: {
            grid: { color: grid + '40' },
            ticks: { color: muted }
          }
        }
      }
    });
  }
}