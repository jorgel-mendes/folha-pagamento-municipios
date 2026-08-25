/* Panorama nacional — beeswarm dos municípios + tabela de exposição.
 *
 * O empacotamento vertical é calculado aqui, no cliente, e não mais pré-computado no build.
 * A razão: o escopo é dinâmico (estado, região ou país), e posições calculadas para os 5.571
 * municípios deixariam buracos ao mostrar um subconjunto. O algoritmo é o dodge determinístico
 * — ordena por x e encaixa cada ponto no menor |y| livre — não uma simulação de força, então
 * roda em poucos milissegundos mesmo com todos os municípios.
 *
 * Regra de simetria: as quatro fontes de renda têm o mesmo peso visual e o mesmo custo de
 * clique. É o que sustenta a neutralidade do painel e não deve ser afrouxado.
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
  const REGIOES = { N: 'Norte', NE: 'Nordeste', CO: 'Centro-Oeste', SE: 'Sudeste', S: 'Sul' };
  // paleta categórica que se sustenta nos dois temas; usada para UF quando o escopo é a região
  const PALETA = ['#3b7dd8', '#d2691e', '#2e9e83', '#a862c4', '#c1443e',
                  '#5a8f2f', '#c9992a', '#4aa5c4', '#b5567f'];
  const MARGEM = { topo: 10, dir: 12, baixo: 30, esq: 12 };
  // Geometria do enxame em unidades relativas a uma largura de referência, como no
  // pré-cálculo original. Mantém a mesma proporção de ponto e folga em qualquer tela.
  const REF = 1400, R_MIN = 1.1, R_MAX = 6.0, FOLGA = 0.15;
  const MAX_LINHAS = 50;

  let dados = null, indice = null, lista = null;
  let fonte = 'previdencia';
  let alvo = document.body.dataset.padrao;
  let escopo = 'estado';
  let porte = '';
  let foco = null;            // grupo destacado pela legenda (região ou UF)
  let ampliado = false;

  const svg = d3.select(svgEl);
  const gNos = svg.append('g').attr('class', 'nos');
  const gEixo = svg.append('g').attr('class', 'eixo');
  const gAlvo = svg.append('g').attr('class', 'destaque');
  const dica = d3.select('body').append('div').attr('class', 'dica').attr('hidden', true);
  const dialogo = document.getElementById('ampliado');
  const figura = document.getElementById('figura');

  // Transição do D3 avança por requestAnimationFrame, que não roda em aba oculta: o
  // desenho ficaria congelado nos valores antigos. E quem pediu menos movimento no
  // sistema não deve receber animação nenhuma. Nos dois casos, aplica direto.
  const semAnimacao = () => document.visibilityState === 'hidden'
    || window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const fmt = (v, c = 0) => v.toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c });
  const massaCurta = (v) => {
    for (const [lim, suf] of [[1e9, ' bi'], [1e6, ' mi'], [1e3, ' mil']]) {
      if (Math.abs(v) >= lim) return 'R$ ' + fmt(v / lim, 1) + suf;
    }
    return 'R$ ' + fmt(v);
  };

  // ---------------------------------------------------------------- escopo e cor
  function noEscopo(m) {
    const a = indice.get(alvo);
    if (!a) return true;
    if (escopo === 'estado') return m.uf === a.uf;
    if (escopo === 'regiao') return m.regiao === a.regiao;
    return true;
  }
  const visivel = (m) => noEscopo(m) && (!porte || m.porte === porte);

  // A cor muda com o escopo: no país inteiro o padrão que importa é regional; dentro de uma
  // região, é a diferença entre estados; dentro de um estado, nenhuma cor agrega — só o
  // município escolhido precisa se destacar.
  let escalaUF = null;
  function chaveCor(m) {
    if (escopo === 'todos') return m.regiao;
    if (escopo === 'regiao') return m.uf;
    return null;
  }
  function corDe(m) {
    if (!visivel(m)) return 'var(--neutro)';
    if (escopo === 'estado') return m.id === alvo ? 'var(--alvo-cor)' : 'var(--neutro)';
    if (escopo === 'todos') return `var(--r-${m.regiao})`;
    return escalaUF && escalaUF.domain().includes(m.uf) ? escalaUF(m.uf) : 'var(--neutro)';
  }

  function grupos() {
    if (escopo === 'estado') return [];
    const chaves = [...new Set(lista.filter(visivel).map(chaveCor))].sort();
    if (escopo === 'todos') {
      const ordem = ['N', 'NE', 'CO', 'SE', 'S'];
      return ordem.filter((k) => chaves.includes(k))
        .map((k) => ({ chave: k, nome: REGIOES[k], cor: `var(--r-${k})` }));
    }
    escalaUF = d3.scaleOrdinal().domain(chaves).range(PALETA);
    return chaves.map((k) => ({ chave: k, nome: k, cor: escalaUF(k) }));
  }

  // ---------------------------------------------------------------- empacotamento
  // Dodge com raio variável: percorre em ordem de x e coloca cada círculo no menor |y| que
  // não colide. A lista encadeada descarta o que já ficou longe demais à esquerda, o que
  // mantém o custo próximo de linear.
  function empacotar(itens, folga) {
    const eps = 1e-3;
    const rMax = d3.max(itens, (d) => d.r) || 1;
    let cabeca = null, cauda = null;

    const bate = (x, y, r) => {
      let a = cabeca;
      while (a) {
        const dr = r + a.r + folga;
        if (dr * dr - eps > (a.x - x) ** 2 + (a.y - y) ** 2) return true;
        a = a.next;
      }
      return false;
    };

    itens.sort((a, b) => a.x - b.x);
    for (const b of itens) {
      while (cabeca && cabeca.x < b.x - 2 * rMax - folga) cabeca = cabeca.next;
      // Se a poda esvaziou a lista, a cauda precisa cair junto. Sem isto, o próximo
      // encadeamento parte de uma cauda órfã, `cabeca` fica nulo para sempre e nenhuma
      // colisão é mais detectada — todos os pontos depois do primeiro vão no eixo x
      // acabam empilhados em y = 0, e o enxame vira uma linha reta.
      if (!cabeca) cauda = null;
      if (bate(b.x, 0, b.r)) {
        // candidatos: alturas em que b encosta em algum círculo já posicionado, nos dois
        // sentidos — subir e descer — para o enxame crescer simétrico em torno do eixo
        let melhor = Infinity;
        for (let a = cabeca; a; a = a.next) {
          const dr = b.r + a.r + folga;
          const dx = a.x - b.x;
          const base = dr * dr - dx * dx;
          if (base <= 0) continue;
          const dy = Math.sqrt(base);
          for (const y of [a.y + dy, a.y - dy]) {
            if (Math.abs(y) < Math.abs(melhor) && !bate(b.x, y, b.r)) melhor = y;
          }
        }
        b.y = Number.isFinite(melhor) ? melhor : 0;
      } else {
        b.y = 0;
      }
      b.next = null;
      if (cauda === null) cabeca = cauda = b;
      else cauda = cauda.next = b;
    }
    return itens;
  }

  // ---------------------------------------------------------------- desenho
  function desenhar() {
    // a figura e movida para dentro do dialogo ao ampliar, entao medir ela mesma
    // funciona nos dois estados -- e evita ler largura de um dialog ainda sem layout
    const largura = figura.clientWidth || 900;
    const x = d3.scaleLinear().domain([0, 1]).range([MARGEM.esq, largura - MARGEM.dir]);

    // O enxame desenha SEMPRE todos os municípios. O escopo apaga os de fora, não os
    // remove: é esse pano de fundo que dá corpo à distribuição, e manter todo mundo em
    // cena deixa o desenho estável — os pontos não saltam ao trocar de recorte.
    const todos = lista.filter((m) => dados[m.id] && dados[m.id].linhas[fonte]);

    // Geometria em unidades relativas a REF, escaladas para a largura real: a proporção
    // entre ponto, folga e plano fica igual em qualquer tela, e ampliar aumenta tudo junto.
    const escala = (largura - MARGEM.esq - MARGEM.dir) / REF;
    const rEscala = d3.scaleSqrt()
      .domain([0, d3.max(todos, (m) => m.pop) || 1])
      .range([R_MIN * escala, R_MAX * escala]);

    const itens = todos.map((m) => ({
      id: m.id, m,
      x: x(dados[m.id].linhas[fonte].part),
      r: Math.max(R_MIN * escala, rEscala(m.pop)),
    }));
    empacotar(itens, FOLGA * escala);

    const extremo = d3.max(itens, (d) => Math.abs(d.y) + d.r) || 10;
    const altura = extremo * 2 + MARGEM.topo + MARGEM.baixo + 6;
    const meio = MARGEM.topo + extremo;
    svg.attr('viewBox', `0 0 ${largura} ${altura}`)
      .attr('width', largura).attr('height', altura);

    gNos.selectAll('circle')
      .data(itens, (d) => d.id)
      .join(
        (entra) => entra.append('circle').attr('class', 'no')
          .attr('cx', (d) => d.x).attr('cy', (d) => meio + d.y).attr('r', (d) => d.r),
        (att) => att.call((s) => (semAnimacao() ? s : s.transition().duration(400))
          .attr('cx', (d) => d.x).attr('cy', (d) => meio + d.y).attr('r', (d) => d.r)),
      )
      .attr('fill', (d) => corDe(d.m))
      .classed('apagado', (d) => !visivel(d.m) || (foco !== null && chaveCor(d.m) !== foco))
      .classed('alvo', (d) => d.id === alvo);

    gEixo.attr('transform', `translate(0,${altura - MARGEM.baixo + 8})`)
      .call(d3.axisBottom(x).ticks(largura > 700 ? 6 : 4).tickFormat((v) => fmt(v * 100) + '%'));

    marcarAlvo(itens, largura, meio);
    descrever(itens);
  }

  function marcarAlvo(itens, largura, meio) {
    const p = itens.find((d) => d.id === alvo);
    gAlvo.selectAll('text').remove();
    if (!p) return;
    const aDireita = p.x < largura / 2;
    gAlvo.append('text').attr('class', 'rotulo-alvo')
      .attr('x', p.x + (aDireita ? p.r + 6 : -p.r - 6))
      .attr('y', meio + p.y + 4)
      .attr('text-anchor', aDireita ? 'start' : 'end')
      .text(`${p.m.nome} (${p.m.uf})`);
  }

  // Texto equivalente para leitor de tela: sem isto o gráfico é decorativo.
  function descrever(itens) {
    const vals = itens.filter((d) => visivel(d.m))
      .map((d) => dados[d.id].linhas[fonte].part).sort(d3.ascending);
    if (!vals.length) return;
    const a = indice.get(alvo);
    const p = dados[alvo] && dados[alvo].linhas[fonte];
    const abaixo = p ? vals.filter((v) => v < p.part).length : 0;
    const texto = `Distribuição de ${fmt(vals.length)} ${rotuloEscopo()} pela participação de `
      + `${NOMES[fonte]} na renda registrada. Mediana de ${fmt(d3.quantile(vals, 0.5) * 100, 1)}%.`
      + (p && a ? ` ${a.nome} está em ${fmt(p.part * 100, 1)}%, acima de `
                  + `${fmt(100 * abaixo / vals.length)}% dos municípios comparados.` : '')
      + (foco ? ` Destaque aplicado a ${escopo === 'todos' ? REGIOES[foco] : foco}.` : '');
    document.getElementById('enxame-desc').textContent = texto;
  }

  function rotuloEscopo() {
    const a = indice.get(alvo);
    if (escopo === 'estado') return `municípios de ${a ? a.uf : 'um estado'}`;
    if (escopo === 'regiao') return `municípios ${a ? 'do ' + REGIOES[a.regiao] : 'de uma região'}`;
    return 'municípios do Brasil';
  }

  // ---------------------------------------------------------------- legenda
  function legenda() {
    const el = document.getElementById('legenda');
    el.textContent = '';
    const gs = grupos();
    if (!gs.length) {
      el.innerHTML = '<span class="legenda-nota">Dentro de um mesmo estado a cor não acrescenta '
        + 'informação, então só o município escolhido aparece destacado.</span>';
      return;
    }
    for (const g of gs) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'chave';
      b.dataset.chave = g.chave;
      b.style.setProperty('--cor-reg', g.cor);
      b.setAttribute('aria-pressed', String(foco === g.chave));
      b.textContent = g.nome;
      b.title = foco === g.chave ? 'Mostrar todos de novo' : `Destacar ${g.nome}`;
      el.appendChild(b);
    }
  }

  const atualizar = () => { if (dados && indice) { legenda(); desenhar(); tabela(); } };

  // ---------------------------------------------------------------- tabela
  function tabela() {
    const corpo = document.querySelector('#ranking tbody');
    const linhas = [];
    for (const m of lista) {
      const d = dados[m.id];
      const l = d && d.linhas[fonte];
      if (!l || !visivel(m)) continue;
      if (foco !== null && chaveCor(m) !== foco) continue;
      linhas.push({ id: m.id, m, part: l.part, massa: l.massa, pc: d.massa_per_capita });
    }
    linhas.sort((a, b) => b.part - a.part);

    const mostrar = linhas.slice(0, MAX_LINHAS);
    const oAlvo = linhas.find((r) => r.id === alvo);
    // o município escolhido nunca some da tabela, mesmo fora das primeiras posições
    if (oAlvo && !mostrar.includes(oAlvo)) mostrar.push(oAlvo);

    corpo.textContent = '';
    for (const r of mostrar) {
      const tr = document.createElement('tr');
      if (r.id === alvo) tr.className = 'alvo';
      const th = document.createElement('th');
      th.scope = 'row';
      const marca = document.createElement('span');
      marca.className = 'marca';
      marca.style.setProperty('--cor-reg', corDe(r.m));
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

  // ---------------------------------------------------------------- ampliar
  // O layout do <dialog> só estabiliza um ou mais quadros depois de showModal(), e o
  // ResizeObserver não é confiável em toda superfície de renderização. Então esperamos
  // a largura útil realmente mudar antes de redesenhar, com um teto de tentativas.
  // setTimeout e nao requestAnimationFrame: em aba oculta o rAF nao roda nenhum quadro,
  // e o desenho ficaria preso na largura antiga ao voltar.
  function desenharQuandoMudar(larguraAnterior, restantes = 12) {
    setTimeout(() => {
      if (figura.clientWidth !== larguraAnterior || restantes <= 0) desenhar();
      else desenharQuandoMudar(larguraAnterior, restantes - 1);
    }, 30);
  }

  function abrir() {
    if (ampliado || typeof dialogo.showModal !== 'function') return;
    ampliado = true;
    document.body.classList.add('ampliando');
    dialogo.appendChild(figura);
    const antes = figura.clientWidth;
    dialogo.showModal();
    desenharQuandoMudar(antes);
  }
  function fechar() {
    if (!ampliado) return;
    ampliado = false;
    document.body.classList.remove('ampliando');
    const antes = figura.clientWidth;
    document.querySelector('.palco').prepend(figura);
    if (dialogo.open) dialogo.close();
    desenharQuandoMudar(antes);
  }
  figura.addEventListener('click', (e) => { if (!ampliado && !e.target.closest('.opcoes')) abrir(); });
  // clique no backdrop: o alvo do evento é o próprio dialog, nunca um filho
  dialogo.addEventListener('click', (e) => { if (e.target === dialogo) fechar(); });
  dialogo.addEventListener('close', fechar);

  // ---------------------------------------------------------------- opções
  const botaoOpcoes = document.getElementById('abrir-opcoes');
  const painel = document.getElementById('opcoes');
  function alternarPainel(mostrar) {
    painel.hidden = !mostrar;
    botaoOpcoes.setAttribute('aria-expanded', String(mostrar));
  }
  botaoOpcoes.addEventListener('click', (e) => {
    e.stopPropagation();
    alternarPainel(painel.hidden);
  });
  painel.addEventListener('click', (e) => e.stopPropagation());
  document.addEventListener('click', (e) => {
    if (!painel.hidden && !e.target.closest('#opcoes, #abrir-opcoes')) alternarPainel(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !painel.hidden) { alternarPainel(false); botaoOpcoes.focus(); }
  });
  painel.addEventListener('change', (e) => {
    if (e.target.name === 'escopo') { escopo = e.target.value; foco = null; }
    if (e.target.name === 'porte') porte = e.target.value;
    atualizar();
  });

  // ---------------------------------------------------------------- interação
  secao.querySelector('.seletor').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-fonte]');
    if (!b) return;
    fonte = b.dataset.fonte;
    secao.querySelectorAll('.seletor button').forEach((x) =>
      x.setAttribute('aria-pressed', String(x === b)));
    atualizar();
  });

  document.getElementById('legenda').addEventListener('click', (e) => {
    const b = e.target.closest('.chave');
    if (!b) return;
    foco = foco === b.dataset.chave ? null : b.dataset.chave;   // clicar de novo desfaz
    atualizar();
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
    foco = null;
    atualizar();
  });

  let redimensiona;
  window.addEventListener('resize', () => {
    clearTimeout(redimensiona);
    redimensiona = setTimeout(() => { if (dados) desenhar(); }, 180);
  });

  // ---------------------------------------------------------------- carga
  const v = document.body.dataset.versao ? `?v=${document.body.dataset.versao}` : '';
  Promise.all([
    fetch(`dados.json${v}`).then((r) => r.json()),
    fetch(`municipios.json${v}`).then((r) => r.json()),
  ]).then(([d, m]) => {
    dados = d;
    lista = m;
    indice = new Map(m.map((x) => [x.id, x]));
    atualizar();
  }).catch(() => {
    document.getElementById('enxame-desc').textContent =
      'Não foi possível carregar o panorama nacional.';
  });
})();
