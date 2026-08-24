/* Panorama nacional — beeswarm dos 5.571 municípios + tabela de exposição.
 *
 * As coordenadas vêm prontas de site/posicoes.json, calculadas por site/posicoes.py.
 * Aqui o D3 cuida de escala, eixo, data join e transição — não há simulação de força.
 *
 * Regra de simetria: as quatro fontes de renda têm o mesmo peso visual e o mesmo custo
 * de clique. É o que sustenta a neutralidade do painel e não deve ser afrouxado.
 */
(() => {
  'use strict';

  const secao = document.getElementById('panorama');
  const svgEl = document.getElementById('enxame');
  if (!secao || !svgEl || typeof d3 === 'undefined') return;

  const NOMES = {
    salario_privado: 'salário do setor privado',
    salario_publico: 'folha da administração pública',
    previdencia: 'previdência (INSS e BPC)',
    bolsa_familia: 'Bolsa Família',
  };
  const PORTES = {
    ate_5k: 'até 5 mil habitantes', '5k_20k': '5 a 20 mil',
    '20k_100k': '20 a 100 mil', '100k_mais': '100 mil ou mais',
  };
  const MARGEM = { topo: 14, dir: 12, baixo: 32, esq: 12 };
  const MAX_LINHAS = 50;

  let posicoes = null, dados = null, indice = null;
  let fonte = 'previdencia';
  let alvo = document.body.dataset.padrao;
  let filtros = { uf: '', porte: '' };

  const svg = d3.select(svgEl);
  const gNos = svg.append('g').attr('class', 'nos');
  const gEixo = svg.append('g').attr('class', 'eixo');
  const gAlvo = svg.append('g').attr('class', 'destaque');
  const dica = d3.select('body').append('div').attr('class', 'dica').attr('hidden', true);

  const fmt = (v, c = 0) => v.toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c });
  const massaCurta = (v) => {
    for (const [lim, suf] of [[1e9, ' bi'], [1e6, ' mi'], [1e3, ' mil']]) {
      if (Math.abs(v) >= lim) return 'R$ ' + fmt(v / lim, 1) + suf;
    }
    return 'R$ ' + fmt(v);
  };

  // ---------------------------------------------------------------- desenho
  function desenhar() {
    const linha = posicoes.linhas[fonte];
    const largura = svgEl.clientWidth || 900;
    const escala = (largura - MARGEM.esq - MARGEM.dir) / posicoes.largura;
    const altura = linha.altura * escala + MARGEM.topo + MARGEM.baixo;
    svg.attr('viewBox', `0 0 ${largura} ${altura}`).attr('height', altura);

    const x = d3.scaleLinear().domain([0, 1]).range([MARGEM.esq, largura - MARGEM.dir]);
    const meio = MARGEM.topo + (linha.altura * escala) / 2;

    // dados de desenho na ordem canônica de posicoes.ids
    const pontos = [];
    for (let i = 0; i < posicoes.ids.length; i++) {
      const px = linha.xy[i * 2];
      if (px === null) continue;
      const m = indice.get(posicoes.ids[i]);
      if (!m) continue;
      pontos.push({
        id: posicoes.ids[i], m,
        cx: MARGEM.esq + px * escala,
        cy: meio + linha.xy[i * 2 + 1] * escala,
        r: Math.max(1, posicoes.raios[i] * escala),
      });
    }

    gNos.selectAll('circle')
      .data(pontos, (d) => d.id)
      .join(
        (entra) => entra.append('circle')
          .attr('class', 'no')
          .attr('fill', (d) => `var(--r-${d.m.regiao})`)
          .attr('r', (d) => d.r)
          .attr('cx', (d) => d.cx)
          .attr('cy', (d) => d.cy),
        (atualiza) => atualiza.call((sel) => sel.transition().duration(450)
          .attr('cx', (d) => d.cx).attr('cy', (d) => d.cy).attr('r', (d) => d.r)),
      )
      .classed('apagado', (d) => !passa(d.m))
      .classed('alvo', (d) => d.id === alvo);

    // O eixo e desenhado na propria selecao, nao numa transicao: aplicar um eixo sobre
    // transicao deixa o texto dos ticks vazio na primeira renderizacao. E nao ha o que
    // animar -- o dominio e sempre 0 a 100%, entao os ticks ficam nos mesmos pixels.
    gEixo.attr('transform', `translate(0,${altura - MARGEM.baixo + 8})`)
      .call(d3.axisBottom(x).ticks(6).tickFormat((v) => fmt(v * 100) + '%'));

    marcarAlvo(pontos, largura);
    descrever(pontos);
  }

  function marcarAlvo(pontos, largura) {
    const p = pontos.find((d) => d.id === alvo);
    gAlvo.selectAll('text').remove();
    if (!p) return;
    const aDireita = p.cx < largura / 2;
    gAlvo.append('text')
      .attr('class', 'rotulo-alvo')
      .attr('x', p.cx + (aDireita ? p.r + 6 : -p.r - 6))
      .attr('y', p.cy + 4)
      .attr('text-anchor', aDireita ? 'start' : 'end')
      .text(`${p.m.nome} (${p.m.uf})`);
  }

  // Texto equivalente para quem usa leitor de tela: o gráfico é decorativo sem isto.
  function descrever(pontos) {
    const vals = pontos.filter((p) => passa(p.m) && dados[p.id] && dados[p.id].linhas[fonte])
      .map((p) => dados[p.id].linhas[fonte].part).sort(d3.ascending);
    if (!vals.length) return;
    const dAlvo = dados[alvo];
    const p = dAlvo && dAlvo.linhas[fonte];
    const mAlvo = indice.get(alvo);
    const mediana = d3.quantile(vals, 0.5);
    const acima = p ? vals.filter((v) => v < p.part).length : 0;
    const texto = `Distribuição de ${vals.length.toLocaleString('pt-BR')} municípios pela `
      + `participação de ${NOMES[fonte]} na renda registrada. Mediana de `
      + `${fmt(mediana * 100, 1)}%.`
      + (p && mAlvo ? ` ${mAlvo.nome} está em ${fmt(p.part * 100, 1)}%, acima de `
             + `${fmt(100 * acima / vals.length)}% dos municípios comparados.` : '');
    document.getElementById('enxame-desc').textContent = texto;
  }

  const passa = (m) => (!filtros.uf || m.uf === filtros.uf)
    && (!filtros.porte || m.porte === filtros.porte);

  // ---------------------------------------------------------------- tabela
  function tabela() {
    const corpo = document.querySelector('#ranking tbody');
    const linhas = [];
    for (const [id, d] of Object.entries(dados)) {
      const m = indice.get(id);
      const l = d.linhas[fonte];
      if (!m || !l || !passa(m)) continue;
      linhas.push({ id, m, part: l.part, massa: l.massa, pc: d.massa_per_capita });
    }
    linhas.sort((a, b) => b.part - a.part);

    const mostrar = linhas.slice(0, MAX_LINHAS);
    const naLista = mostrar.some((r) => r.id === alvo);
    const oAlvo = linhas.find((r) => r.id === alvo);
    if (!naLista && oAlvo) mostrar.push(oAlvo);   // o município escolhido nunca some da tabela

    corpo.textContent = '';
    for (const r of mostrar) {
      const tr = document.createElement('tr');
      if (r.id === alvo) tr.className = 'alvo';
      const th = document.createElement('th');
      th.scope = 'row';
      const marca = document.createElement('span');
      marca.className = 'marca';
      marca.style.setProperty('--cor-reg', `var(--r-${r.m.regiao})`);
      th.append(marca, `${r.m.nome} (${r.m.uf})`);
      tr.appendChild(th);
      for (const v of [fmt(r.m.pop), fmt(r.part * 100, 1) + '%', massaCurta(r.massa), 'R$ ' + fmt(r.pc)]) {
        const td = document.createElement('td');
        td.className = 'num';
        td.textContent = v;
        tr.appendChild(td);
      }
      corpo.appendChild(tr);
    }
    document.querySelector('[data-v="fonte-nome"]').textContent = NOMES[fonte];
    document.querySelector('[data-v="ranking-n"]').textContent = fmt(linhas.length);
  }

  // o app.js pode anunciar uma troca de municipio antes de posicoes/dados chegarem
  const pronto = () => posicoes && dados && indice;
  const atualizar = () => { if (pronto()) { desenhar(); tabela(); } };

  // ---------------------------------------------------------------- interação
  secao.querySelector('.seletor').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-fonte]');
    if (!b) return;
    fonte = b.dataset.fonte;
    secao.querySelectorAll('.seletor button').forEach((x) =>
      x.setAttribute('aria-pressed', String(x === b)));
    atualizar();
  });

  document.getElementById('f-uf').addEventListener('change', (e) => {
    filtros.uf = e.target.value; atualizar();
  });
  document.getElementById('f-porte').addEventListener('change', (e) => {
    filtros.porte = e.target.value; atualizar();
  });

  gNos.on('mousemove', (evento) => {
    const d = d3.select(evento.target).datum();
    if (!d || !d.id) return dica.attr('hidden', true);
    const l = dados[d.id].linhas[fonte];
    dica.attr('hidden', null).html('')
      .style('left', `${evento.pageX + 14}px`).style('top', `${evento.pageY - 10}px`);
    dica.append('strong').text(`${d.m.nome} (${d.m.uf})`);
    dica.append('span').text(`${fmt(d.m.pop)} hab · ${fmt(l.part * 100, 1)}% de ${NOMES[fonte]}`);
  });
  gNos.on('mouseleave', () => dica.attr('hidden', true));

  document.addEventListener('municipio:mudou', (e) => {
    alvo = e.detail.id;
    if (!pronto()) return;
    const m = indice.get(alvo);
    // acompanha o município escolhido: comparar com iguais é o recorte útil
    if (m && !filtros.porte) document.getElementById('f-porte').value = filtros.porte = m.porte;
    atualizar();
  });

  let redimensiona;
  window.addEventListener('resize', () => {
    clearTimeout(redimensiona);
    redimensiona = setTimeout(() => { if (pronto()) desenhar(); }, 180);
  });

  // ---------------------------------------------------------------- carga
  Promise.all([
    fetch('posicoes.json').then((r) => r.json()),
    fetch('dados.json').then((r) => r.json()),
    fetch('municipios.json').then((r) => r.json()),
  ]).then(([p, d, m]) => {
    posicoes = p; dados = d;
    indice = new Map(m.map((x) => [x.id, x]));

    const sel = document.getElementById('f-uf');
    for (const uf of [...new Set(m.map((x) => x.uf))].sort()) {
      sel.append(new Option(uf, uf));
    }
    const meu = indice.get(alvo);
    if (meu) document.getElementById('f-porte').value = filtros.porte = meu.porte;
    atualizar();
  }).catch(() => {
    document.getElementById('enxame-desc').textContent =
      'Não foi possível carregar o panorama nacional.';
  });
})();
