/* Folha de Pagamento dos Municípios
 *
 * A página já chega com um município renderizado pelo site/build.py. Este script só
 * troca valores dentro da estrutura existente — não constrói markup. Por isso o site
 * continua legível se o JavaScript falhar ou demorar.
 */
(() => {
  'use strict';

  const LINHAS = ['salario_privado', 'salario_publico', 'previdencia', 'bolsa_familia'];
  const UNIDADES = { vinculos: 'vínculos', beneficios: 'benefícios', familias: 'famílias' };
  const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const TRACO = '—';
  const MAX_SUGESTOES = 8;

  const holerite = document.getElementById('holerite');
  const entrada = document.getElementById('q');
  const lista = document.getElementById('sugestoes');
  if (!entrada || !lista) return;
  // A mesma busca serve às duas páginas. Na porta de entrada não há contracheque para
  // preencher, então escolher um município navega para o painel em vez de renderizar.
  const modoPainel = !!holerite;

  let indice = [];        // municipios.json
  let dados = null;       // dados.json, carregado em segundo plano
  let porId = new Map();
  let atual = document.body.dataset.padrao;
  let marcado = -1;       // item destacado nas sugestões
  let pendente = null;    // município escolhido antes de dados.json chegar

  // ---------------------------------------------------------------- formatação
  const fmt = (v, casas = 0) => v.toLocaleString('pt-BR',
    { minimumFractionDigits: casas, maximumFractionDigits: casas });

  // mesma regra do compacto() em build.py
  const formatarMassa = (v) => {
    const escalas = [[1e9, ' bi'], [1e6, ' mi'], [1e3, ' mil']];
    for (const [lim, suf] of escalas) {
      if (Math.abs(v) >= lim) return 'R$ ' + fmt(v / lim, 1) + suf;
    }
    return 'R$ ' + fmt(v);
  };

  const semAcento = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

  // ---------------------------------------------------------------- render
  const põe = (raiz, chave, texto) => {
    const el = raiz.querySelector(`[data-v="${chave}"]`);
    if (el) el.textContent = texto;
  };

  function renderizar(id) {
    const mun = porId.get(id);
    const d = dados && dados[id];
    if (!mun || !d) return;

    põe(holerite, 'municipio', mun.nome);
    põe(holerite, 'uf', `(${mun.uf})`);
    põe(holerite, 'pop', fmt(mun.pop));
    põe(holerite, 'pop18', fmt(mun.pop18));
    const [ano, mes] = d.ref.split('-');
    põe(holerite, 'competencia', `${MESES[Number(mes) - 1]} de ${ano}`);

    for (const chave of LINHAS) {
      const tr = holerite.querySelector(`tr[data-linha="${chave}"]`);
      if (!tr) continue;
      const l = d.linhas[chave];
      const barra = tr.querySelector('[data-v="barra"]');

      if (!l) {
        tr.setAttribute('data-ausente', 'sim');
        tr.title = 'Sem dado publicado para este município nesta fonte';
        ['n', 'por100', 'medio', 'massa', 'part'].forEach((k) => põe(tr, k, TRACO));
        põe(tr, 'unidade', '');
        if (barra) barra.style.width = '0%';
        continue;
      }

      tr.removeAttribute('data-ausente');
      tr.removeAttribute('title');
      põe(tr, 'n', fmt(l.n));
      põe(tr, 'unidade', UNIDADES[l.unidade] || l.unidade);
      põe(tr, 'por100', fmt(l.por100, 1));
      põe(tr, 'medio', 'R$ ' + fmt(l.medio));
      põe(tr, 'massa', formatarMassa(l.massa));
      põe(tr, 'part', fmt(l.part * 100, 1) + '%');
      if (barra) barra.style.width = (l.part * 100).toFixed(2) + '%';
    }

    põe(holerite, 'total', formatarMassa(d.massa_total));
    põe(holerite, 'percapita', 'R$ ' + fmt(d.massa_per_capita));
    const bf = d.linhas.bolsa_familia;
    if (bf && bf.pessoas) põe(holerite, 'bf-pessoas', fmt(bf.pessoas));

    atual = id;
    document.title = `${mun.nome} (${mun.uf}) — Folha de Pagamento dos Municípios`;
    // o panorama escuta isto para destacar o município e ajustar o recorte da tabela
    document.dispatchEvent(new CustomEvent('municipio:mudou', { detail: { id } }));
  }

  function selecionar(id, { historico = true } = {}) {
    if (!porId.has(id)) return;
    if (!modoPainel) { location.href = `painel.html?m=${id}`; return; }
    if (!dados) { pendente = id; entrada.setAttribute('aria-busy', 'true'); return; }
    renderizar(id);
    fecharSugestoes();
    entrada.value = '';
    if (historico) {
      const url = new URL(location.href);
      url.searchParams.set('m', id);
      history.pushState({ m: id }, '', url);
    }
  }

  // ---------------------------------------------------------------- busca
  function procurar(termo) {
    const t = semAcento(termo.trim());
    if (t.length < 2) return [];
    const comeca = [], contem = [];
    for (const m of indice) {
      const pos = m.busca.indexOf(t);
      if (pos === 0) comeca.push(m);
      else if (pos > 0) contem.push(m);
      if (comeca.length >= MAX_SUGESTOES) break;
    }
    return comeca.concat(contem).slice(0, MAX_SUGESTOES);
  }

  function mostrarSugestoes(itens) {
    lista.textContent = '';
    marcado = -1;
    if (!itens.length) return fecharSugestoes();
    itens.forEach((m, i) => {
      const li = document.createElement('li');
      li.id = `sug-${i}`;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', 'false');
      li.dataset.id = m.id;
      li.textContent = m.nome + ' ';
      const uf = document.createElement('span');
      uf.className = 'uf';
      uf.textContent = `(${m.uf})`;
      li.appendChild(uf);
      li.addEventListener('mousedown', (e) => { e.preventDefault(); selecionar(m.id); });
      lista.appendChild(li);
    });
    lista.hidden = false;
    entrada.setAttribute('aria-expanded', 'true');
  }

  function fecharSugestoes() {
    lista.hidden = true;
    lista.textContent = '';
    marcado = -1;
    entrada.setAttribute('aria-expanded', 'false');
    entrada.removeAttribute('aria-activedescendant');
  }

  function mover(passo) {
    const itens = [...lista.children];
    if (!itens.length) return;
    if (marcado >= 0) itens[marcado].setAttribute('aria-selected', 'false');
    marcado = (marcado + passo + itens.length) % itens.length;
    const alvo = itens[marcado];
    alvo.setAttribute('aria-selected', 'true');
    alvo.scrollIntoView({ block: 'nearest' });
    entrada.setAttribute('aria-activedescendant', alvo.id);
  }

  entrada.addEventListener('input', () => mostrarSugestoes(procurar(entrada.value)));
  entrada.addEventListener('blur', () => setTimeout(fecharSugestoes, 120));
  entrada.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); mover(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); mover(-1); }
    else if (e.key === 'Escape') { fecharSugestoes(); }
    else if (e.key === 'Enter') {
      const itens = [...lista.children];
      const alvo = marcado >= 0 ? itens[marcado] : itens[0];
      if (alvo) { e.preventDefault(); selecionar(alvo.dataset.id); }
    }
  });

  // ---------------------------------------------------------------- alternador
  // Só o painel tem contracheque. Sem esta guarda, o addEventListener num elemento
  // inexistente derruba o módulo na porta de entrada -- e derruba junto a carga da
  // lista de municípios, registrada mais abaixo, deixando a busca muda.
  if (modoPainel) {
    holerite.addEventListener('click', (e) => {
      const botao = e.target.closest('button[data-modo]');
      if (!botao) return;
      holerite.dataset.modo = botao.dataset.modo;
      holerite.querySelectorAll('button[data-modo]').forEach((b) => {
        b.setAttribute('aria-pressed', String(b === botao));
      });
    });

    window.addEventListener('popstate', () => {
      const id = new URL(location.href).searchParams.get('m') || document.body.dataset.padrao;
      if (id !== atual) selecionar(id, { historico: false });
    });
  }

  // ---------------------------------------------------------------- carga
  fetch('municipios.json')
    .then((r) => r.json())
    .then((lista) => {
      indice = lista.map((m) => ({ ...m, busca: semAcento(m.nome) }));
      indice.sort((a, b) => b.pop - a.pop);   // empate de nome resolve pela cidade maior
      porId = new Map(indice.map((m) => [m.id, m]));
    })
    .catch(() => { entrada.placeholder = 'Não foi possível carregar a lista de municípios'; });

  // dados.json é grande (3,4 MB) e só o painel precisa dele — a porta de entrada carrega
  // apenas a lista de municípios, que é seis vezes menor. Como o painel já mostra um
  // município renderizado, ele carrega em segundo plano e só é esperado se o usuário
  // escolher outro antes de a carga terminar.
  if (modoPainel) fetch('dados.json')
    .then((r) => r.json())
    .then((d) => {
      dados = d;
      entrada.removeAttribute('aria-busy');
      const alvo = pendente || new URL(location.href).searchParams.get('m');
      if (alvo && alvo !== atual) { pendente = null; selecionar(alvo, { historico: false }); }
    })
    .catch(() => { entrada.placeholder = 'Não foi possível carregar os dados'; });
})();
