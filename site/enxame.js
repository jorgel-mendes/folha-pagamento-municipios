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

  // Plano de composição: um quadrante por fonte, em ordem circular.
  //
  // A primeira versão usava radviz — média das quatro âncoras pesada pelas participações.
  // Estava errada para o que o gráfico promete: ali a posição mede o equilíbrio entre
  // PARES de fontes, não qual é a maior. Goiânia é o contraexemplo: folha pública 44,0%
  // contra salário privado 42,5%, e mesmo assim caía no quadrante do privado, porque
  // (privado + previdência) supera (pública + Bolsa Família) por 0,097.
  //
  // Agora o quadrante é a fonte dominante por construção. Dentro dele, a distância até o
  // centro é o quanto essa fonte domina, e o ângulo diz qual das duas fontes vizinhas vem
  // em segundo. Nada de posição sem significado.
  const ANCORAS = [
    { chave: 'previdencia',     ang: 45,  curto: 'Previdência' },
    { chave: 'salario_privado', ang: 135, curto: 'Salário privado' },
    { chave: 'salario_publico', ang: 225, curto: 'Folha pública' },
    { chave: 'bolsa_familia',   ang: 315, curto: 'Bolsa Família' },
  ];
  const COR_FONTE = {
    salario_privado: 'var(--c-privado)', salario_publico: 'var(--c-publico)',
    previdencia: 'var(--c-prev)', bolsa_familia: 'var(--c-bf)',
  };

  let dados = null, indice = null, lista = null;
  let vista = 'enxame';       // enxame | plano
  let fonte = 'previdencia';
  let alvo = document.body.dataset.padrao;
  let escopo = 'estado';
  let porte = '';
  let foco = null;            // grupo destacado pela legenda (região, UF ou fonte dominante)
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
  // A fonte com maior participação no município. É o que o plano colore, porque ali a
  // pergunta deixa de ser "quanto de uma fonte" e passa a ser "qual delas manda".
  function dominante(m) {
    const l = (dados[m.id] || {}).linhas || {};
    let melhor = null, maior = -1;
    for (const { chave } of ANCORAS) {
      const p = (l[chave] || {}).part || 0;
      if (p > maior) { maior = p; melhor = chave; }
    }
    return melhor;
  }

  let escalaUF = null;
  function chaveCor(m) {
    if (vista === 'mapa') return dominante(m);
    if (escopo === 'todos') return m.regiao;
    if (escopo === 'regiao') return m.uf;
    return null;
  }
  function corDe(m) {
    if (!visivel(m)) return 'var(--neutro)';
    if (vista === 'mapa') return COR_FONTE[dominante(m)] || 'var(--neutro)';
    if (escopo === 'estado') return m.id === alvo ? 'var(--alvo-cor)' : 'var(--neutro)';
    if (escopo === 'todos') return `var(--r-${m.regiao})`;
    return escalaUF && escalaUF.domain().includes(m.uf) ? escalaUF(m.uf) : 'var(--neutro)';
  }

  function grupos() {
    if (vista === 'mapa') {
      const presentes = new Set(lista.filter(visivel).map(dominante));
      return ANCORAS.filter((a) => presentes.has(a.chave))
        .map((a) => ({ chave: a.chave, nome: a.curto, cor: COR_FONTE[a.chave] }));
    }
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
    if (vista === 'plano') return desenharPlano();
    if (vista === 'mapa') return desenharMapa();
    return desenharEnxame();
  }

  // ---------------------------------------------------------------- mapa
  // A malha municipal tem 269 KB em gzip e só serve a esta vista, então é buscada na
  // primeira vez que o mapa abre -- quem nunca clica em "Mapa" não paga por ela.
  let malha = null, carregandoMalha = false;

  // O d3-geo lê a orientação do anel para saber onde fica o interior do polígono. Anel na
  // direção errada vira o complemento: um município sozinho cobre o planeta e pinta a tela
  // inteira. A simplificação da malha inverte alguns polígonos pequenos, e não dá para
  // corrigir na geração — a montagem da topologia reescreve a orientação para compartilhar
  // arcos entre vizinhos. Então quem julga é o próprio d3: nenhum município brasileiro
  // chega perto de 0,01 esferorradiano (o maior, Altamira, tem 0,004), então área acima
  // disso só pode ser polígono invertido.
  function endireitar(feições) {
    let corrigidos = 0;
    for (const f of feições) {
      if (d3.geoArea(f) < 0.01) continue;
      const g = f.geometry;
      const pols = g.type === 'MultiPolygon' ? g.coordinates : [g.coordinates];
      for (const pol of pols) pol[0].reverse();
      corrigidos++;
    }
    if (corrigidos) console.info(`malha: ${corrigidos} municípios com anel invertido, corrigidos`);
  }

  function desenharMapa() {
    if (!malha) {
      if (!carregandoMalha) {
        carregandoMalha = true;
        document.getElementById('enxame-desc').textContent = 'Carregando a malha municipal…';
        const v = document.body.dataset.versao ? `?v=${document.body.dataset.versao}` : '';
        fetch(`malha.topojson${v}`).then((r) => r.json()).then((t) => {
          const chave = Object.keys(t.objects)[0];
          malha = topojson.feature(t, t.objects[chave]).features;
          endireitar(malha);
          carregandoMalha = false;
          if (vista === 'mapa') desenharMapa();
        }).catch(() => {
          carregandoMalha = false;
          document.getElementById('enxame-desc').textContent =
            'Não foi possível carregar a malha municipal.';
        });
      }
      return;
    }

    const largura = figura.clientWidth || 900;
    const altura = Math.min(largura * 0.78, ampliado ? 680 : 500);

    // No mapa o recorte é o próprio enquadramento: mostrar só quem está no escopo e
    // ajustar a projeção a ele é o que produz o zoom esperado ao trocar de estado.
    const dentro = new Set(lista.filter(visivel).map((m) => m.id));
    const feições = malha.filter((f) => dentro.has(f.properties.id));
    if (!feições.length) return;

    const colecao = { type: 'FeatureCollection', features: feições };
    const projecao = d3.geoMercator().fitSize([largura - 8, altura - 8], colecao);
    const caminho = d3.geoPath(projecao);

    svg.attr('viewBox', `0 0 ${largura} ${altura}`).attr('width', largura).attr('height', altura);
    gEixo.attr('transform', null).selectAll('*').remove();
    gAlvo.selectAll('*').remove();

    gNos.selectAll('path')
      .data(feições, (f) => f.properties.id)
      .join('path')
      .attr('class', 'area')
      .attr('d', caminho)
      .attr('transform', 'translate(4,4)')
      .attr('fill', (f) => {
        const m = indice.get(f.properties.id);
        return m ? corDe(m) : 'var(--neutro)';
      })
      .classed('apagado', (f) => {
        const m = indice.get(f.properties.id);
        return !m || (foco !== null && chaveCor(m) !== foco);
      })
      .classed('alvo', (f) => f.properties.id === alvo);

    gNos.selectAll('circle').remove();
    descreverDominante('no mapa');
  }

  // Posição de um município no plano.
  //   quadrante = fonte dominante (por construção, nunca por acidente de soma)
  //   distância do centro = o quanto ela domina: 1/4 é empate perfeito, 1 é tudo dela
  //   ângulo dentro do quadrante = qual das duas fontes vizinhas vem em segundo
  function posicaoPlano(id, cx, cy, raio) {
    const l = (dados[id] || {}).linhas || {};
    const parte = (k) => (l[k] || {}).part || 0;
    let i = 0;
    for (let k = 1; k < ANCORAS.length; k++) {
      if (parte(ANCORAS[k].chave) > parte(ANCORAS[i].chave)) i = k;
    }
    const dom = ANCORAS[i];
    const antes = ANCORAS[(i - 1 + ANCORAS.length) % ANCORAS.length];
    const depois = ANCORAS[(i + 1) % ANCORAS.length];

    const a = parte(antes.chave), b = parte(depois.chave);
    const t = (a + b) > 0 ? b / (a + b) : 0.5;          // 0 encosta no vizinho anterior
    const ang = ((dom.ang - 45) + 90 * t) * Math.PI / 180;

    // 0,25 é o empate entre as quatro; abaixo disso não existe dominante
    const forca = Math.min(1, Math.max(0, (parte(dom.chave) - 0.25) / 0.75));
    const r = raio * forca;
    return { x: cx + r * Math.cos(ang), y: cy - r * Math.sin(ang), dom: dom.chave, forca };
  }

  function desenharPlano() {
    const largura = figura.clientWidth || 900;
    const lado = Math.min(largura, ampliado ? 620 : 470);
    const altura = lado;
    const cx = largura / 2, cy = altura / 2;
    const raio = lado / 2 - (ampliado ? 46 : 38);

    const todos = lista.filter((m) => dados[m.id] && dados[m.id].linhas);
    const rEscala = d3.scaleSqrt()
      .domain([0, d3.max(todos, (m) => m.pop) || 1])
      .range([ampliado ? 2 : 1.6, ampliado ? 13 : 9]);

    const itens = todos.map((m) => ({
      id: m.id, m,
      ...posicaoPlano(m.id, cx, cy, raio),
      r: Math.max(ampliado ? 2 : 1.6, rEscala(m.pop)),
    }));

    svg.attr('viewBox', `0 0 ${largura} ${altura}`).attr('width', largura).attr('height', altura);
    gEixo.attr('transform', null).selectAll('*').remove();

    // moldura: a cruz que separa os quadrantes e o rótulo de cada fonte no seu canto
    const moldura = gEixo.append('g').attr('class', 'moldura');
    moldura.append('circle').attr('cx', cx).attr('cy', cy).attr('r', raio).attr('class', 'aro');
    moldura.append('line').attr('class', 'eixo-cruz')
      .attr('x1', cx - raio).attr('x2', cx + raio).attr('y1', cy).attr('y2', cy);
    moldura.append('line').attr('class', 'eixo-cruz')
      .attr('x1', cx).attr('x2', cx).attr('y1', cy - raio).attr('y2', cy + raio);

    const conta = {};
    for (const d of itens) if (visivel(d.m)) conta[d.dom] = (conta[d.dom] || 0) + 1;

    for (const a of ANCORAS) {
      const dir = a.ang > 90 && a.ang < 270 ? -1 : 1;      // esquerda ou direita
      const cima = a.ang < 180 ? -1 : 1;
      const x = cx + dir * raio, y = cy + cima * raio;
      const g = moldura.append('g').attr('text-anchor', dir < 0 ? 'start' : 'end');
      g.append('text').attr('class', 'rotulo-ancora')
        .attr('x', x).attr('y', cima < 0 ? y - 8 : y + 16)
        .attr('fill', COR_FONTE[a.chave]).text(a.curto);
      g.append('text').attr('class', 'contagem-quad')
        .attr('x', x).attr('y', cima < 0 ? y + 8 : y + 30)
        .text(`${fmt(conta[a.chave] || 0)} municípios`);
    }

    gNos.selectAll('circle')
      .data(itens, (d) => d.id)
      .join(
        (entra) => entra.append('circle').attr('class', 'no')
          .attr('cx', (d) => d.x).attr('cy', (d) => d.y).attr('r', (d) => d.r),
        (att) => att.call((s) => (semAnimacao() ? s : s.transition().duration(500))
          .attr('cx', (d) => d.x).attr('cy', (d) => d.y).attr('r', (d) => d.r)),
      )
      .attr('fill', (d) => corDe(d.m))
      .classed('apagado', (d) => !visivel(d.m) || (foco !== null && chaveCor(d.m) !== foco))
      .classed('alvo', (d) => d.id === alvo);

    const p = itens.find((d) => d.id === alvo);
    gAlvo.selectAll('text').remove();
    if (p) {
      gAlvo.append('text').attr('class', 'rotulo-alvo')
        .attr('x', p.x + p.r + 6).attr('y', p.y + 4).text(`${p.m.nome} (${p.m.uf})`);
    }
    descreverPlano();
  }

  function desenharEnxame() {
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

    gEixo.selectAll('.moldura').remove();
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

  const descreverPlano = () => descreverDominante('no plano');

  // Plano e mapa respondem à mesma pergunta — qual fonte manda em cada município —, então
  // compartilham o texto equivalente. Muda só a frase que explica como ler o desenho.
  function descreverDominante(onde) {
    const dentro = lista.filter((m) => visivel(m) && dados[m.id]);
    if (!dentro.length) return;
    const conta = {};
    for (const m of dentro) { const d = dominante(m); conta[d] = (conta[d] || 0) + 1; }
    const partes = Object.entries(conta).sort((a, b) => b[1] - a[1])
      .map(([k, n]) => `${NOMES[k]} em ${fmt(n)} (${fmt(100 * n / dentro.length)}%)`).join('; ');
    const a = indice.get(alvo);
    const meu = a && dominante(a);
    const comoLer = onde === 'no mapa'
      ? 'Cada município é pintado com a cor da fonte que pesa mais na sua renda registrada.'
      : 'Cada ponto fica mais próximo da fonte que pesa mais no município.';
    document.getElementById('enxame-desc').textContent =
      `Composição da renda registrada de ${fmt(dentro.length)} ${rotuloEscopo()}. ${comoLer} `
      + `Fonte dominante: ${partes}.`
      + (a && meu ? ` Em ${a.nome}, a fonte dominante é ${NOMES[meu]}.` : '')
      + (foco ? ` Destaque aplicado a ${NOMES[foco] || foco}.` : '');
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
    if (vista === 'mapa') {
      const nota = document.createElement('span');
      nota.className = 'legenda-nota';
      nota.textContent = 'Cor: fonte dominante —';
      el.appendChild(nota);
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
    // Um <dialog> modal desenha na top layer: qualquer coisa fora dele fica atras do
    // backdrop. A dica vive no body, entao era montada e posicionada mas invisivel --
    // por isso o tooltip "parava de funcionar" com o grafico ampliado.
    dialogo.appendChild(dica.node());
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
    document.body.appendChild(dica.node());
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
  // O seletor de fonte só faz sentido no enxame, que mostra uma fonte por vez. O plano
  // usa as quatro ao mesmo tempo, então some em vez de ficar ali sem efeito.
  const seletorFonte = secao.querySelector('.seletor');
  const vistas = secao.querySelector('.vistas');
  if (vistas) {
    vistas.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-vista]');
      if (!b || b.dataset.vista === vista) return;
      vista = b.dataset.vista;
      foco = null;
      // cada vista desenha coisas diferentes nos mesmos grupos: sem limpar, a moldura do
      // plano fica por baixo do eixo da distribuicao
      gNos.selectAll('*').remove();
      gEixo.selectAll('*').remove();
      gAlvo.selectAll('*').remove();
      vistas.querySelectorAll('button').forEach((x) =>
        x.setAttribute('aria-pressed', String(x === b)));
      seletorFonte.hidden = vista !== 'enxame';
      secao.dataset.vista = vista;
      atualizar();
    });
  }

  seletorFonte.addEventListener('click', (e) => {
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

  // O dado sob o cursor muda de forma conforme a vista: circulo com o municipio junto no
  // enxame e no plano, feicao do GeoJSON no mapa. Aqui os dois viram o mesmo municipio.
  function municipioSob(alvoEvento) {
    const d = d3.select(alvoEvento).datum();
    if (!d) return null;
    if (d.m) return d.m;
    if (d.properties && d.properties.id) return indice.get(d.properties.id) || null;
    return null;
  }

  gNos.on('mousemove', (evento) => {
    const m = municipioSob(evento.target);
    if (!m || !dados[m.id]) return dica.attr('hidden', true);
    const l = dados[m.id].linhas;

    dica.attr('hidden', null).html('')
      .style('left', `${evento.clientX + 14}px`).style('top', `${evento.clientY - 10}px`);
    dica.append('strong').text(`${m.nome} (${m.uf})`);
    dica.append('span').text(`${fmt(m.pop)} habitantes`);

    if (vista === 'enxame') {
      // a distribuicao e sobre uma fonte por vez: mostrar so ela e o que responde a vista
      dica.append('span').text(`${fmt(((l[fonte] || {}).part || 0) * 100, 1)}% de ${NOMES[fonte]}`);
      return;
    }
    // composicao e mapa nao dependem da fonte escolhida: as quatro linhas, da maior para
    // a menor, que e a leitura que as duas vistas prometem
    const tabela = dica.append('table').attr('class', 'dica-linhas');
    ANCORAS.map((a) => ({ nome: a.curto, chave: a.chave, part: (l[a.chave] || {}).part || 0 }))
      .sort((x, y) => y.part - x.part)
      .forEach((linha) => {
        const tr = tabela.append('tr');
        tr.append('th').attr('scope', 'row')
          .style('color', COR_FONTE[linha.chave]).text(linha.nome);
        tr.append('td').text(`${fmt(linha.part * 100, 1)}%`);
      });
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
