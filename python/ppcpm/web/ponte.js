/* =====================================================================
   SISTEMA PPCPM — PONTE PYTHON ⇄ PROGRAMAS (só na versão Python)
   Liga todos os programas PPCP às pastas do computador:
   toda vez que um programa pede um arquivo (Análise DBF, Agrupador,
   Validação de Peso, Etiquetas...), abre a janela "PPCPM - ARQUIVOS"
   com unidades, Área de Trabalho, Documentos, Downloads, favoritos,
   recentes, busca e caminho colado do Explorador.
   A janela normal do Windows continua disponível no botão
   "Janela do Windows". Na Vercel este arquivo não existe: nada muda lá.
   ===================================================================== */
(function () {
  'use strict';
  if (window.__ppcpmPonte) return;
  window.__ppcpmPonte = true;

  var API = '/api/pc/';
  var ativo = false, aberto = false, bypass = false;
  var LOCAIS = null;

  /* ---------- liga só se o Python deste PC responder ---------- */
  var CAB = { 'X-PPCPM': '1' };
  fetch(API + 'locais', { cache: 'no-store', headers: CAB }).then(function (r) {
    if (!r.ok) throw 0; return r.json();
  }).then(function (j) { LOCAIS = j; ativo = true; ligarZebra(); }).catch(function () { ativo = false; });

  /* ---------- ZEBRA: Impressão de Etiquetas manda o ZPL direto para a impressora deste PC ----------
     O programa de etiquetas procura estes ganchos; sem eles (Vercel) usa a janela do Chrome. */
  function ligarZebra() {
    window.PPCP_LISTAR_IMPRESSORAS = function () {
      return fetch('/api/zebra/impressoras', { cache: 'no-store', headers: CAB }).then(function (r) {
        return r.json().then(function (j) { if (!r.ok) throw new Error(j.erro || 'Erro ' + r.status); return j.impressoras; });
      });
    };
    window.PPCP_IMPRIMIR_ZPL = function (zpl, impressora) {
      return fetch('/api/zebra/imprimir', { method: 'POST', headers: { 'X-PPCPM': '1', 'Content-Type': 'application/json' },
        body: JSON.stringify({ impressora: impressora, zpl: zpl }) }).then(function (r) {
        return r.json().then(function (j) { if (!r.ok) throw new Error(j.erro || 'Erro ' + r.status); return j; });
      });
    };
  }

  /* ---------- utilidades ---------- */
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function fmtTam(n) { if (!n) return ''; var u = ['B', 'KB', 'MB', 'GB'], i = 0; while (n >= 1024 && i < 3) { n /= 1024; i++; } return n.toLocaleString('pt-BR', { maximumFractionDigits: i ? 1 : 0 }) + ' ' + u[i]; }
  function fmtData(s) { if (!s) return ''; var d = new Date(s * 1000); return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }); }
  function ext(n) { var i = n.lastIndexOf('.'); return i < 0 ? '' : n.slice(i).toLowerCase(); }
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { } }
  function api(nome, params) {
    var q = Object.keys(params || {}).map(function (k) { return k + '=' + encodeURIComponent(params[k]); }).join('&');
    return fetch(API + nome + (q ? '?' + q : ''), { cache: 'no-store', headers: CAB }).then(function (r) {
      return r.json().then(function (j) { if (!r.ok) throw new Error(j.erro || 'Erro ' + r.status); return j; });
    });
  }
  var MIME = { 'application/json': '.json', 'text/csv': '.csv', 'application/pdf': '.pdf', 'text/html': '.html,.htm',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx', 'application/vnd.ms-excel': '.xls', 'text/plain': '.txt' };
  function filtroDe(accept) {
    var out = [];
    String(accept || '').split(',').forEach(function (a) {
      a = a.trim().toLowerCase(); if (!a) return;
      if (a.charAt(0) === '.') out.push(a); else if (MIME[a]) out.push(MIME[a]);
    });
    return out.join(',');
  }
  function corExt(e) {
    if (/^\.(xlsx|xlsm|xls|xlsb|ods)$/.test(e)) return '#1d6f42';
    if (/^\.(zip|7z|rar|tar|gz|tgz|bz2|xz)$/.test(e)) return '#6d28d9';
    if (e === '.dbf') return '#b45309'; if (e === '.csv') return '#0e7490'; if (e === '.pdf') return '#b91c1c';
    if (/^\.(zpl|prn|txt)$/.test(e)) return '#475569'; if (/^\.(html?|json)$/.test(e)) return '#5b21b6';
    return '#64748b';
  }
  /* ícones de linha (padrão corporativo), herdam a cor do texto */
  var ICO = {
    up: '<path d="M12 19V5M5 12l7-7 7 7"/>',
    ir: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    estrela: '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z"/>',
    explorador: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M14 13h5M17 10l3 3-3 3"/>',
    busca: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    janela: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/>',
    abrir: '<path d="M4 20h16M12 4v12M7 11l5 5 5-5"/>',
    fechar: '<path d="M6 6l12 12M18 6L6 18"/>',
    maximizar: '<rect x="4" y="4" width="16" height="16" rx="1.5"/>',
    restaurar: '<rect x="4" y="8" width="12" height="12" rx="1.5"/><path d="M8 8V5.5A1.5 1.5 0 0 1 9.5 4h9A1.5 1.5 0 0 1 20 5.5v9a1.5 1.5 0 0 1-1.5 1.5H16"/>',
    pasta: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    desktop: '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/>',
    documentos: '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
    downloads: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    disco: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7 14h.01M11 14h6"/>',
    rede: '<rect x="3" y="4" width="18" height="7" rx="1.5"/><path d="M7 7.5h.01M12 11v4M5 19h14M12 15v4"/>',
    recente: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    favorito: '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z"/>',
    arquivos: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 10h18"/>'
  };
  function svg(nome, tam) {
    var w = el('span', 'pc-sv'); tam = tam || 16;
    w.innerHTML = '<svg width="' + tam + '" height="' + tam + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + ICO[nome] + '</svg>';
    return w;
  }
  function icone(item) {
    var w = el('span', 'pc-ic');
    if (item.pasta) {
      w.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24"><path fill="#f2b33d" d="M2.5 6.5A1.5 1.5 0 0 1 4 5h5l2 2h9a1.5 1.5 0 0 1 1.5 1.5v10A1.5 1.5 0 0 1 20 20H4a1.5 1.5 0 0 1-1.5-1.5z"/><path fill="#d99a26" d="M2.5 9h19v1H2.5z"/></svg>';
    } else {
      var e = ext(item.nome).replace('.', '').toUpperCase().slice(0, 4) || 'ARQ', c = corExt(ext(item.nome));
      w.innerHTML = '<svg width="20" height="22" viewBox="0 0 20 22"><path fill="#fff" stroke="#9aa5b5" stroke-width="1" d="M2.5.5h10l5 5v15.5h-15z"/><path fill="#e2e8f0" stroke="#9aa5b5" stroke-width="1" d="M12.5.5v5h5"/>'
        + '<rect x="0" y="11" width="16" height="8" rx="1.2" fill="' + c + '"/><text x="8" y="17.2" text-anchor="middle" font-family="Arial" font-weight="700" font-size="5.6" fill="#fff">' + e + '</text></svg>';
    }
    return w;
  }
  function iconeLocal(a, tipo) {
    var n = (a.nome || '').toLowerCase();
    if (tipo === 'fav') return 'favorito'; if (tipo === 'rec') return 'recente';
    if (n.indexOf('rede') === 0) return 'rede'; if (a.tipo === 'unidade') return 'disco';
    if (n.indexOf('área de trabalho') >= 0) return 'desktop'; if (n.indexOf('documentos') >= 0) return 'documentos';
    if (n.indexOf('downloads') >= 0) return 'downloads'; return 'pasta';
  }

  /* ---------- visual (padrão do sistema: Arial negrito, #0b5cad) ---------- */
  function estilo(D) {
    D = D || document;
    if (D.getElementById('ppcpm-pc-css')) return;
    var c = D.createElement('style'); c.id = 'ppcpm-pc-css';
    c.textContent = [
      '#ppcpm-pc{position:fixed;inset:0;z-index:2147483000;background:rgba(5,10,25,.55);font:600 13px Arial,Helvetica,sans-serif;color:#1a2233}',
      '#ppcpm-pc *{box-sizing:border-box;font-family:Arial,Helvetica,sans-serif}',
      '#ppcpm-pc .pc-card{position:absolute;background:#fff;border:1px solid #0b2150;border-radius:10px;box-shadow:0 18px 55px rgba(0,0,0,.45);display:flex;flex-direction:column;overflow:hidden;min-width:560px;min-height:380px}',
      '#ppcpm-pc .pc-card.max{border-radius:0}',
      '#ppcpm-pc .pc-top{position:relative;display:flex;align-items:center;justify-content:center;height:46px;padding:0 120px;background:linear-gradient(180deg,#0b2150,#06142f);color:#fff;cursor:move;user-select:none;flex:none}',
      '#ppcpm-pc .pc-top b{font:700 15px Arial,Helvetica,sans-serif;letter-spacing:.6px;text-transform:uppercase;display:flex;align-items:center;gap:9px;white-space:nowrap}',
      '#ppcpm-pc .pc-top .pc-l{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:#fff;font-size:12px;white-space:nowrap}',
      '#ppcpm-pc .pc-top .pc-r{position:absolute;right:8px;top:50%;transform:translateY(-50%);display:flex;gap:2px}',
      '#ppcpm-pc .pc-top .pc-r button{background:transparent;border:0;color:#cfdcf5;padding:6px 8px;border-radius:6px}',
      '#ppcpm-pc .pc-top .pc-r button:hover{background:rgba(255,255,255,.12);color:#fff}',
      '#ppcpm-pc .pc-top .pc-r button.pc-x:hover{background:#c62828}',
      '#ppcpm-pc .pc-sv{display:inline-flex;align-items:center}',
      '#ppcpm-pc button{font:700 13px Arial,Helvetica,sans-serif;border-radius:7px;padding:7px 12px;cursor:pointer;border:1px solid #c5cbd6;background:#f2f4f6;color:#1f2937;white-space:nowrap;display:inline-flex;align-items:center;gap:7px}',
      '#ppcpm-pc button:hover{background:#e6eaf0}',
      '#ppcpm-pc button.pc-pri{background:#0b5cad;border-color:#0b5cad;color:#fff}',
      '#ppcpm-pc button.pc-pri:hover{background:#1a6dc0}',
      '#ppcpm-pc button:disabled{opacity:.5;cursor:default}',
      '#ppcpm-pc .pc-h{position:absolute;z-index:5}',
      '#ppcpm-pc .pc-h.n,#ppcpm-pc .pc-h.s{left:10px;right:10px;height:7px;cursor:ns-resize}',
      '#ppcpm-pc .pc-h.n{top:-3px}#ppcpm-pc .pc-h.s{bottom:-3px}',
      '#ppcpm-pc .pc-h.e,#ppcpm-pc .pc-h.w{top:10px;bottom:10px;width:7px;cursor:ew-resize}',
      '#ppcpm-pc .pc-h.e{right:-3px}#ppcpm-pc .pc-h.w{left:-3px}',
      '#ppcpm-pc .pc-h.ne,#ppcpm-pc .pc-h.nw,#ppcpm-pc .pc-h.se,#ppcpm-pc .pc-h.sw{width:14px;height:14px}',
      '#ppcpm-pc .pc-h.ne{top:-3px;right:-3px;cursor:nesw-resize}#ppcpm-pc .pc-h.sw{bottom:-3px;left:-3px;cursor:nesw-resize}',
      '#ppcpm-pc .pc-h.nw{top:-3px;left:-3px;cursor:nwse-resize}#ppcpm-pc .pc-h.se{bottom:-3px;right:-3px;cursor:nwse-resize}',
      '#ppcpm-pc .pc-grip{position:absolute;right:3px;bottom:3px;width:12px;height:12px;pointer-events:none;background:linear-gradient(135deg,transparent 50%,#9aa5b5 50%,#9aa5b5 58%,transparent 58%,transparent 70%,#9aa5b5 70%,#9aa5b5 78%,transparent 78%)}',
      '#ppcpm-pc .pc-barra{display:flex;gap:8px;padding:10px 18px;border-bottom:1px solid #e3e7ee;background:#f7f8fa}',
      '#ppcpm-pc input[type=text]{flex:1;min-width:0;border:1px solid #c5cbd6;border-radius:7px;padding:7px 10px;font:600 13px Arial,Helvetica,sans-serif;color:#1a2233;background:#fff}',
      '#ppcpm-pc input[type=text]:focus{outline:2px solid #0b5cad55;border-color:#0b5cad}',
      '#ppcpm-pc .pc-corpo{flex:1;display:flex;min-height:0}',
      '#ppcpm-pc .pc-lado{width:230px;border-right:1px solid #e3e7ee;overflow:auto;padding:8px 0;background:#fafbfc}',
      '#ppcpm-pc .pc-sec{padding:12px 16px 5px;font-size:11px;color:#6b7383;text-transform:uppercase;letter-spacing:.6px}',
      '#ppcpm-pc .pc-loc{display:flex;align-items:center;gap:9px;padding:6px 16px;cursor:pointer;white-space:nowrap;overflow:hidden;color:#1f2937}',
      '#ppcpm-pc .pc-loc .pc-sv{color:#0b5cad;flex:none}',
      '#ppcpm-pc .pc-loc span:not(.pc-sv):not(.pc-x){overflow:hidden;text-overflow:ellipsis}',
      '#ppcpm-pc .pc-loc:hover{background:#e8f0fb}',
      '#ppcpm-pc .pc-loc.on{background:#dbe8f8;color:#0b5cad}',
      '#ppcpm-pc .pc-loc .pc-x{margin-left:auto;color:#a33;opacity:0;font-size:14px}',
      '#ppcpm-pc .pc-loc:hover .pc-x{opacity:1}',
      '#ppcpm-pc .pc-main{flex:1;display:flex;flex-direction:column;min-width:0}',
      '#ppcpm-pc .pc-ferr{display:flex;gap:10px;align-items:center;padding:10px 14px}',
      '#ppcpm-pc .pc-bw{flex:1;position:relative;display:flex}',
      '#ppcpm-pc .pc-bw .pc-sv{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:#6b7383}',
      '#ppcpm-pc .pc-bw input[type=text]{padding-left:32px}',
      '#ppcpm-pc .pc-ferr label{display:flex;gap:6px;align-items:center;white-space:nowrap;color:#3d4554;cursor:pointer}',
      '#ppcpm-pc .pc-cab,#ppcpm-pc .pc-row{display:grid;grid-template-columns:28px 1fr 150px 90px;gap:8px;align-items:center;padding:6px 14px}',
      '#ppcpm-pc .pc-barra button{padding:7px 10px}',
      '#ppcpm-pc .pc-cab{font-size:12px;color:#6b7383;border-bottom:1px solid #e3e7ee;background:#f7f8fa}',
      '#ppcpm-pc .pc-cab span{cursor:pointer;user-select:none}',
      '#ppcpm-pc .pc-lista{flex:1;overflow:auto;outline:none}',
      '#ppcpm-pc .pc-row{cursor:pointer;border-bottom:1px solid #f0f2f5;user-select:none}',
      '#ppcpm-pc .pc-row:hover{background:#f1f6fd}',
      '#ppcpm-pc .pc-row.sel{background:#d6e6fa}',
      '#ppcpm-pc .pc-row .pc-n{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '#ppcpm-pc .pc-row .pc-c{font-weight:500;color:#7b8494;font-size:11px;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '#ppcpm-pc .pc-row .pc-d,#ppcpm-pc .pc-row .pc-t{color:#5b6474;font-weight:500;font-size:12px}',
      '#ppcpm-pc .pc-row .pc-t{text-align:right}',
      '#ppcpm-pc .pc-ic{display:flex}',
      '#ppcpm-pc .pc-vazio{padding:40px 20px;text-align:center;color:#6b7383}',
      '#ppcpm-pc .pc-erro{margin:14px;padding:10px 12px;border:1px solid #f1b4b4;background:#fdeeee;color:#9b1c1c;border-radius:8px}',
      '#ppcpm-pc .pc-rod{display:flex;gap:8px;align-items:center;padding:12px 18px;border-top:1px solid #e3e7ee;background:#f7f8fa}',
      '#ppcpm-pc .pc-info{margin-right:auto;color:#3d4554;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '#ppcpm-pc .pc-card.estreita .pc-lado{display:none}',
      '#ppcpm-pc .pc-card.estreita .pc-cab,#ppcpm-pc .pc-card.estreita .pc-row{grid-template-columns:28px 1fr 80px}',
      '#ppcpm-pc .pc-card.estreita .pc-d{display:none}',
      '#ppcpm-pc .pc-card.estreita .pc-barra .pc-tx{display:none}',
      '#ppcpm-pc .pc-card.estreita .pc-top .pc-l{display:none}',
      '#ppcpm-pc.arrastando,#ppcpm-pc.arrastando *{user-select:none!important}',
      '#ppcpm-pc.janela{background:#fff}',
      '#ppcpm-pc.janela .pc-card{left:0!important;top:0!important;width:100%!important;height:100%!important;border:0;border-radius:0;box-shadow:none;min-width:0;min-height:0}',
      '#ppcpm-pc.janela .pc-h,#ppcpm-pc.janela .pc-grip{display:none}',
      '#ppcpm-pc.janela .pc-top{cursor:default}',
      /* cores fixas: alguns programas forçam cor preta em tudo; aqui a janela mantém as suas */
      '#ppcpm-pc .pc-top,#ppcpm-pc .pc-top *,#ppcpm-pc .pc-top svg{color:#fff!important}',
      '#ppcpm-pc .pc-top .pc-l{color:#fff!important;opacity:.92}',
      '#ppcpm-pc .pc-top svg{stroke:currentColor!important}',
      '#ppcpm-pc button.pc-pri,#ppcpm-pc button.pc-pri *{color:#fff!important}',
      '#ppcpm-pc .pc-loc .pc-sv,#ppcpm-pc .pc-loc .pc-sv svg{color:#0b5cad!important}',
      '#ppcpm-pc .pc-loc .pc-x,#ppcpm-pc .pc-loc .pc-x svg{color:#b42318!important}',
      '#ppcpm-pc .pc-sv svg{stroke:currentColor}'
    ].join('\n');
    (D.head || D.documentElement).appendChild(c);
  }

  /* ---------- janela separada do Windows (pode ir para o outro monitor) ---------- */
  var JANELA = null, CHAVE_SO = 'ppcpm:pc:janela-so';
  function abrirJanela() {
    if (lsGet('ppcpm:pc:modo') === 'dentro') return null;
    var g = null; try { g = JSON.parse(lsGet(CHAVE_SO) || 'null'); } catch (e) { }
    var w = (g && g.w) || 1040, h = (g && g.h) || 640;
    var x = g && g.x != null ? g.x : Math.round((screen.availWidth - w) / 2), y = g && g.y != null ? g.y : Math.round((screen.availHeight - h) / 2);
    var J = null;
    try { J = window.open('/pc/janela', 'ppcpm_arquivos', 'popup=yes,width=' + w + ',height=' + h + ',left=' + x + ',top=' + y); } catch (e) { J = null; }
    return J;
  }
  // espera a janela carregar a página do sistema; se não carregar, volta a abrir dentro da página
  function janelaPronta(J) {
    return new Promise(function (ok) {
      if (!J) return ok(null);
      var t0 = Date.now();
      (function ver() {
        var pronto = false;
        try { pronto = J.location.pathname === '/pc/janela' && J.document.readyState === 'complete' && J.document.body; } catch (e) { }
        if (pronto) return ok(J);
        if (J.closed || Date.now() - t0 > 6000) { try { J.close(); } catch (e) { } return ok(null); }
        setTimeout(ver, 40);
      })();
    });
  }
  // se o programa sair da tela (troca de aba do sistema), fecha a janela junto
  window.addEventListener('pagehide', function () { if (JANELA && !JANELA.closed) try { JANELA.close(); } catch (e) { } });

  /* ---------- seletor ---------- */
  function abrirSeletor(op) {
    op = op || {};
    var filtro = filtroDe(op.accept);
    var chave = 'ppcpm:pc:ultima:' + (filtro || '*');
    var J0 = abrirJanela();   // abre já no clique (o Chrome só permite janela nova dentro do clique)
    aberto = true; JANELA = J0;
    return janelaPronta(J0).then(function (J) { return new Promise(function (resolve) {
      var D = J ? J.document : document, W = J || window;
      JANELA = J;
      estilo(D); aberto = true;
      var estado = { caminho: '', pai: '', itens: [], sel: [], ordem: lsGet('ppcpm:pc:ordem') || 'nome', soAceitos: !!filtro, busca: null };

      var fundo = el('div'); fundo.id = 'ppcpm-pc'; fundo.setAttribute('role', 'dialog'); fundo.setAttribute('aria-modal', 'true');
      if (J) fundo.classList.add('janela');
      var card = el('div', 'pc-card'); fundo.appendChild(card);

      var top = el('div', 'pc-top');
      var tit = el('b'); tit.appendChild(svg('arquivos', 18)); tit.appendChild(D.createTextNode('PPCPM - ARQUIVOS'));
      top.appendChild(tit);
      top.appendChild(el('span', 'pc-l', filtro ? 'Tipos aceitos: ' + filtro.split(',').join(', ') : 'Qualquer arquivo'));
      var ctl = el('div', 'pc-r');
      var bMax = el('button'); bMax.title = 'Maximizar / restaurar'; bMax.appendChild(svg('maximizar', 15));
      var bX = el('button', 'pc-x'); bX.title = 'Fechar (Esc)'; bX.appendChild(svg('fechar', 16));
      ctl.appendChild(bMax); ctl.appendChild(bX); top.appendChild(ctl);
      card.appendChild(top);
      ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'].forEach(function (d) { var h = el('div', 'pc-h ' + d); h.dataset.d = d; card.appendChild(h); });
      card.appendChild(el('div', 'pc-grip'));

      var barra = el('div', 'pc-barra');
      var bSobe = el('button'); bSobe.appendChild(svg('up')); bSobe.title = 'Pasta acima (Backspace)';
      var cam = el('input'); cam.type = 'text'; cam.placeholder = 'Cole aqui o caminho copiado do Explorador (ex.: G:\\Meu Drive\\PCP) e aperte Enter';
      var bIr = el('button'); bIr.title = 'Ir para o caminho digitado (Enter)'; bIr.appendChild(svg('ir')); bIr.appendChild(el('span', 'pc-tx', 'Ir'));
      var bFav = el('button'); bFav.title = 'Guardar esta pasta nos Favoritos'; bFav.appendChild(svg('estrela')); bFav.appendChild(el('span', 'pc-tx', 'Favoritar'));
      var bExp = el('button'); bExp.title = 'Abrir esta pasta no Explorador de Arquivos'; bExp.appendChild(svg('explorador')); bExp.appendChild(el('span', 'pc-tx', 'Abrir no Explorador'));
      [bSobe, cam, bIr, bFav, bExp].forEach(function (x) { barra.appendChild(x); });
      card.appendChild(barra);

      var corpo = el('div', 'pc-corpo'); card.appendChild(corpo);
      var lado = el('aside', 'pc-lado'); corpo.appendChild(lado);
      var main = el('section', 'pc-main'); corpo.appendChild(main);
      var ferr = el('div', 'pc-ferr');
      var busca = el('input'); busca.type = 'text'; busca.placeholder = 'Filtrar nesta pasta… (Enter procura também nas subpastas)';
      var bw = el('div', 'pc-bw'); bw.appendChild(svg('busca')); bw.appendChild(busca);
      var lbl = el('label'); var chk = el('input'); chk.type = 'checkbox'; chk.checked = estado.soAceitos; chk.disabled = !filtro;
      lbl.appendChild(chk); lbl.appendChild(D.createTextNode('Só tipos aceitos'));
      ferr.appendChild(bw); ferr.appendChild(lbl); main.appendChild(ferr);
      var cab = el('div', 'pc-cab');
      cab.appendChild(el('span'));
      var hN = el('span', null, 'Nome'), hD = el('span', 'pc-d', 'Modificado'), hT = el('span', null, 'Tamanho');
      hT.style.textAlign = 'right'; [hN, hD, hT].forEach(function (h) { cab.appendChild(h); }); main.appendChild(cab);
      var lista = el('div', 'pc-lista'); lista.tabIndex = 0; main.appendChild(lista);

      var rod = el('div', 'pc-rod');
      var info = el('span', 'pc-info', '');
      var bWin = el('button'); bWin.appendChild(svg('janela')); bWin.appendChild(el('span', 'pc-tx', 'Janela do Windows')); bWin.title = 'Usar a janela comum de abrir arquivo';
      var bCan = el('button', null, 'Cancelar');
      var bOk = el('button', 'pc-pri'); bOk.appendChild(svg('abrir')); bOk.appendChild(el('span', null, op.multiple ? 'Abrir selecionados' : 'Abrir arquivo')); bOk.disabled = true;
      [info, bWin, bCan, bOk].forEach(function (x) { rod.appendChild(x); });
      card.appendChild(rod);

      function fechar(resultado) {
        if (!aberto) return;
        aberto = false; clearInterval(vigia);
        D.removeEventListener('keydown', tecla, true); W.removeEventListener('resize', ajustarTela);
        if (J) {
          try { if (!J.closed) lsSet(CHAVE_SO, JSON.stringify({ x: J.screenX, y: J.screenY, w: J.innerWidth, h: J.innerHeight })); } catch (e) { }
          try { if (!J.closed) J.close(); } catch (e) { }
          JANELA = null;
          try { window.focus(); } catch (e) { }
        } else fundo.remove();
        resolve(resultado);
      }

      /* ----- painel da esquerda ----- */
      function locItem(nome, caminho, ic, remover) {
        var d = el('div', 'pc-loc'); d.title = caminho;
        d.appendChild(svg(ic)); d.appendChild(el('span', null, nome));
        if (remover) {
          var x = el('span', 'pc-x'); x.appendChild(svg('fechar', 13)); x.title = 'Tirar dos favoritos';
          x.onclick = function (e) { e.stopPropagation(); api('favorito', { caminho: caminho, remover: 1 }).then(function (j) { LOCAIS = j; montarLado(); }); };
          d.appendChild(x);
        }
        d.onclick = function () { ir(caminho); };
        d.dataset.c = caminho; return d;
      }
      function montarLado() {
        lado.innerHTML = '';
        var L = LOCAIS || { unidades: [], pastas: [], favoritos: [], recentes: [] };
        function sec(t, arr, tipo) {
          if (!arr.length) return; lado.appendChild(el('div', 'pc-sec', t));
          arr.forEach(function (a) {
            if (typeof a === 'string') { var p = a.split(/[\\/]/).filter(Boolean); lado.appendChild(locItem(p.length > 1 ? p[p.length - 2] + ' › ' + p[p.length - 1] : (p[0] || a), a, 'recente')); }
            else lado.appendChild(locItem(a.nome, a.caminho, iconeLocal(a, tipo), tipo === 'fav'));
          });
        }
        sec('Favoritos', L.favoritos, 'fav');
        sec('Este computador', L.pastas.concat(L.unidades));
        sec('Recentes', L.recentes, 'rec');
        marcarLado();
      }
      function marcarLado() {
        Array.prototype.forEach.call(lado.querySelectorAll('.pc-loc'), function (d) { d.classList.toggle('on', d.dataset.c === estado.caminho); });
      }

      /* ----- lista ----- */
      function ordenar(a) {
        var o = estado.ordem;
        return a.slice().sort(function (x, y) {
          if (x.pasta !== y.pasta) return x.pasta ? -1 : 1;
          if (o === 'data') return y.modificado - x.modificado;
          if (o === 'tam') return y.tamanho - x.tamanho;
          return x.nome.localeCompare(y.nome, 'pt-BR', { numeric: true, sensitivity: 'base' });
        });
      }
      function visiveis() {
        var aceitos = filtro ? filtro.split(',') : [], q = estado.busca ? '' : busca.value.trim().toLowerCase();
        return ordenar(estado.itens.filter(function (i) {
          if (q && i.nome.toLowerCase().indexOf(q) < 0) return false;
          if (!i.pasta && !i.pacote && estado.soAceitos && aceitos.length && aceitos.indexOf(ext(i.nome)) < 0) return false;
          return true;
        }));
      }
      function desenhar() {
        lista.innerHTML = '';
        var v = visiveis();
        if (!v.length) { lista.appendChild(el('div', 'pc-vazio', estado.busca ? 'Nada encontrado com "' + estado.busca + '".' : 'Pasta vazia ou sem arquivos dos tipos aceitos.')); }
        v.forEach(function (i) {
          var r = el('div', 'pc-row'); r.dataset.c = i.caminho;
          if (estado.sel.indexOf(i.caminho) >= 0) r.classList.add('sel');
          r.appendChild(icone(i));
          var n = el('span', 'pc-n', i.nome);
          if (estado.busca) n.appendChild(el('span', 'pc-c', i.caminho));
          r.appendChild(n); r.appendChild(el('span', 'pc-d', fmtData(i.modificado))); r.appendChild(el('span', 'pc-t', i.pasta ? '' : fmtTam(i.tamanho)));
          if (!i.pacote) r.title = i.caminho;
          var entra = i.pasta || (i.pacote && (filtro ? filtro.split(',') : []).indexOf(ext(i.nome)) < 0);
          if (i.pacote) r.title = i.caminho + (entra ? '  (compactado: dois cliques para abrir como pasta)' : '');
          r.onclick = function (e) {
            if (entra) { estado.sel = []; atualizarSel(); r.classList.add('sel'); return; }
            if (op.multiple && (e.ctrlKey || e.metaKey)) {
              var k = estado.sel.indexOf(i.caminho); if (k >= 0) estado.sel.splice(k, 1); else estado.sel.push(i.caminho);
            } else if (op.multiple && e.shiftKey && estado.sel.length) {
              var arq = v.filter(function (x) { return !x.pasta; }).map(function (x) { return x.caminho; });
              var a = arq.indexOf(estado.sel[estado.sel.length - 1]), b = arq.indexOf(i.caminho);
              estado.sel = arq.slice(Math.min(a, b), Math.max(a, b) + 1);
            } else estado.sel = [i.caminho];
            atualizarSel();
          };
          r.ondblclick = function () { if (entra) ir(i.caminho); else { estado.sel = [i.caminho]; confirmar(); } };
          lista.appendChild(r);
        });
        [hN, hD, hT].forEach(function (h, k) { var o = ['nome', 'data', 'tam'][k]; h.style.color = estado.ordem === o ? '#0b5cad' : ''; });
        atualizarSel();
      }
      function atualizarSel() {
        Array.prototype.forEach.call(lista.querySelectorAll('.pc-row'), function (r) { r.classList.toggle('sel', estado.sel.indexOf(r.dataset.c) >= 0); });
        bOk.disabled = !estado.sel.length;
        var n = estado.sel.length;
        info.textContent = n ? (n === 1 ? estado.sel[0] : n + ' arquivos selecionados') : (op.multiple ? 'Dica: Ctrl ou Shift + clique para escolher vários arquivos' : 'Clique duas vezes no arquivo para abrir');
      }
      function erro(msg) { lista.innerHTML = ''; lista.appendChild(el('div', 'pc-erro', msg)); }

      function ir(c) {
        estado.busca = null; busca.value = '';
        lista.innerHTML = ''; lista.appendChild(el('div', 'pc-vazio', 'Abrindo pasta…'));
        api('listar', { caminho: c }).then(function (j) {
          estado.caminho = j.caminho; estado.pai = j.pai; estado.itens = j.itens; estado.sel = [];
          cam.value = j.caminho; bSobe.disabled = !j.pai; lsSet(chave, j.caminho);
          desenhar(); marcarLado();
          if (j.cortado) info.textContent = 'Pasta muito grande: mostrando os primeiros itens. Use o filtro.';
        }).catch(function (e) { erro(e.message + ' — confira o caminho ou se a unidade de rede está conectada.'); });
      }
      function procurar() {
        var t = busca.value.trim(); if (!t || !estado.caminho) return;
        lista.innerHTML = ''; lista.appendChild(el('div', 'pc-vazio', 'Procurando "' + t + '" em ' + estado.caminho + ' e subpastas…'));
        api('buscar', { caminho: estado.caminho, termo: t, filtro: estado.soAceitos ? filtro : '' }).then(function (j) {
          estado.busca = t; estado.itens = j.itens; estado.sel = []; desenhar();
          if (j.incompleta) info.textContent = 'Busca parcial (pasta muito grande). Entre numa subpasta para refinar.';
        }).catch(function (e) { erro(e.message); });
      }
      function confirmar() {
        var cams = estado.sel.slice(); if (!cams.length) return;
        bOk.disabled = true; info.textContent = 'Carregando ' + cams.length + (cams.length === 1 ? ' arquivo…' : ' arquivos…');
        Promise.all(cams.map(function (c) {
          return fetch(API + 'arquivo?caminho=' + encodeURIComponent(c), { cache: 'no-store', headers: CAB }).then(function (r) {
            if (!r.ok) return r.json().then(function (j) { throw new Error(j.erro || 'Não foi possível ler o arquivo.'); });
            var nome = decodeURIComponent(r.headers.get('X-Nome') || encodeURIComponent(c.split(/[\\/]/).pop()));
            var mod = +r.headers.get('X-Modificado') || Date.now();
            return r.blob().then(function (b) { var f = new File([b], nome, { type: b.type, lastModified: mod }); try { Object.defineProperty(f, 'ppcpmCaminho', { value: c }); } catch (e) { } return f; });
          });
        })).then(function (files) { fechar({ files: files }); })
          .catch(function (e) { bOk.disabled = false; info.textContent = ''; W.alert('Não foi possível abrir o arquivo.\n' + e.message); });
      }

      /* ----- botões e teclado ----- */
      bSobe.onclick = function () { if (estado.pai) ir(estado.pai); };
      bIr.onclick = function () { if (cam.value.trim()) ir(cam.value); };
      cam.onkeydown = function (e) { if (e.key === 'Enter') { e.preventDefault(); bIr.onclick(); } };
      bFav.onclick = function () { if (estado.caminho) api('favorito', { caminho: estado.caminho }).then(function (j) { LOCAIS = j; montarLado(); info.textContent = 'Pasta adicionada aos favoritos.'; }).catch(function (e) { info.textContent = e.message; }); };
      bExp.onclick = function () { var c = estado.sel.length === 1 ? estado.sel[0] : estado.caminho; if (c) api('explorador', { caminho: c }).catch(function (e) { info.textContent = e.message; }); };
      busca.oninput = function () { if (!estado.busca) desenhar(); };
      busca.onkeydown = function (e) { if (e.key === 'Enter') { e.preventDefault(); procurar(); } };
      chk.onchange = function () { estado.soAceitos = chk.checked; desenhar(); };
      [[hN, 'nome'], [hD, 'data'], [hT, 'tam']].forEach(function (p) { p[0].onclick = function () { estado.ordem = p[1]; lsSet('ppcpm:pc:ordem', p[1]); desenhar(); }; });
      bCan.onclick = function () { fechar(null); };
      bWin.onclick = function () { fechar({ windows: true, deJanela: !!J }); };
      bOk.onclick = confirmar;
      function tecla(e) {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); fechar(null); }
        else if (e.key === 'Enter' && D.activeElement !== cam && D.activeElement !== busca && estado.sel.length) { e.preventDefault(); confirmar(); }
        else if (e.key === 'Backspace' && D.activeElement !== cam && D.activeElement !== busca && estado.pai) { e.preventDefault(); ir(estado.pai); }
      }
      D.addEventListener('keydown', tecla, true);

      (D.body || D.documentElement).appendChild(fundo);
      // fechou a janela pelo X do Windows: cancela
      var vigia = setInterval(function () { if (J && J.closed) fechar(null); }, 400);

      /* ----- tamanho e posição: a janela abre no tamanho que o usuário deixou da última vez ----- */
      var MINW = 560, MINH = 380, CHAVE_JANELA = 'ppcpm:pc:janela', geo, maxi = false;
      function vw() { return fundo.clientWidth; } function vh() { return fundo.clientHeight; }
      function padrao() { var w = Math.min(1040, vw() - 28), h = Math.min(640, vh() - 28); return { w: w, h: h, x: (vw() - w) / 2, y: (vh() - h) / 2 }; }
      function aplicar() {
        var g = maxi ? { x: 0, y: 0, w: vw(), h: vh() } : geo;
        if (!maxi) {
          g.w = Math.max(Math.min(MINW, vw()), Math.min(g.w, vw())); g.h = Math.max(Math.min(MINH, vh()), Math.min(g.h, vh()));
          g.x = Math.min(Math.max(0, g.x), vw() - g.w); g.y = Math.min(Math.max(0, g.y), vh() - g.h);
        }
        card.style.left = g.x + 'px'; card.style.top = g.y + 'px'; card.style.width = g.w + 'px'; card.style.height = g.h + 'px';
        card.classList.toggle('max', maxi); card.classList.toggle('estreita', g.w < 760);
        bMax.innerHTML = ''; bMax.appendChild(svg(maxi ? 'restaurar' : 'maximizar', 15));
      }
      function guardar() { lsSet(CHAVE_JANELA, JSON.stringify({ w: geo.w, h: geo.h, x: geo.x, y: geo.y, max: maxi })); }
      try { var g0 = JSON.parse(lsGet(CHAVE_JANELA) || 'null'); geo = g0 && g0.w ? g0 : padrao(); maxi = !!(g0 && g0.max); } catch (e) { geo = padrao(); }
      if (J) maxi = true;   // janela separada: ocupa a janela toda; tamanho e posição são da própria janela do Windows
      aplicar();
      function arrastar(e, modo) {
        if (J || e.button !== 0 || (maxi && modo !== 'mover')) return;
        e.preventDefault();
        if (maxi) { maxi = false; geo.x = e.clientX - geo.w / 2; geo.y = e.clientY - 20; aplicar(); }
        var x0 = e.clientX, y0 = e.clientY, g = { x: geo.x, y: geo.y, w: geo.w, h: geo.h };
        fundo.classList.add('arrastando');
        function mover(ev) {
          var dx = ev.clientX - x0, dy = ev.clientY - y0;
          if (modo === 'mover') { geo.x = g.x + dx; geo.y = g.y + dy; }
          else {
            if (modo.indexOf('e') >= 0) geo.w = Math.max(MINW, Math.min(g.w + dx, vw() - g.x));
            if (modo.indexOf('s') >= 0) geo.h = Math.max(MINH, Math.min(g.h + dy, vh() - g.y));
            if (modo.indexOf('w') >= 0) { var nw = Math.max(MINW, Math.min(g.w - dx, g.x + g.w)); geo.x = g.x + g.w - nw; geo.w = nw; }
            if (modo.indexOf('n') >= 0) { var nh = Math.max(MINH, Math.min(g.h - dy, g.y + g.h)); geo.y = g.y + g.h - nh; geo.h = nh; }
          }
          aplicar();
        }
        function soltar() { D.removeEventListener('pointermove', mover); D.removeEventListener('pointerup', soltar); fundo.classList.remove('arrastando'); guardar(); }
        D.addEventListener('pointermove', mover); D.addEventListener('pointerup', soltar);
      }
      top.addEventListener('pointerdown', function (e) { if (!e.target.closest('button')) arrastar(e, 'mover'); });
      top.addEventListener('dblclick', function (e) { if (!J && !e.target.closest('button')) { maxi = !maxi; aplicar(); guardar(); } });
      Array.prototype.forEach.call(card.querySelectorAll('.pc-h'), function (h) { h.addEventListener('pointerdown', function (e) { arrastar(e, h.dataset.d); }); });
      bMax.onclick = function () { maxi = !maxi; aplicar(); guardar(); };
      bX.onclick = function () { fechar(null); };
      function ajustarTela() { aplicar(); }
      W.addEventListener('resize', ajustarTela);
      if (J) { bMax.style.display = 'none'; try { J.focus(); } catch (e) { } }

      montarLado();
      var inicio = lsGet(chave) || lsGet('ppcpm:pc:ultima:*') || (LOCAIS && LOCAIS.pastas[0] && LOCAIS.pastas[0].caminho) || (LOCAIS && LOCAIS.unidades[0] && LOCAIS.unidades[0].caminho) || '';
      if (inicio) ir(inicio); else erro('Nenhuma pasta encontrada. Cole o caminho acima.');
      // atualiza unidades/favoritos (pendrive ou rede pode ter conectado agora)
      api('locais').then(function (j) { LOCAIS = j; montarLado(); }).catch(function () { });
      setTimeout(function () { lista.focus(); }, 0);
    }); });
  }

  /* ---------- entrega os arquivos ao programa, como se viessem da janela do Windows ---------- */
  function entregar(input, files) {
    var dt = new DataTransfer();
    files.forEach(function (f) { dt.items.add(f); });
    input.files = dt.files;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  function janelaWindows(input) { bypass = true; try { origClick.call(input); } finally { bypass = false; } }
  /* O Chrome só abre a janela do Windows com um clique NESTA tela. Vindo da janela separada,
     mostra um botão para o usuário confirmar com um clique. */
  function comClique(acao) {
    estilo(document);
    var f = el('div'); f.id = 'ppcpm-pc';
    var c = el('div'); c.style.cssText = 'position:absolute;left:50%;top:40%;transform:translate(-50%,-50%);background:#fff;border:1px solid #0b2150;border-radius:10px;box-shadow:0 18px 55px rgba(0,0,0,.45);padding:18px 20px;display:flex;flex-direction:column;gap:12px;align-items:center;min-width:320px';
    c.appendChild(el('b', null, 'Abrir a janela comum do Windows?'));
    var r = el('div'); r.style.cssText = 'display:flex;gap:8px';
    var ok = el('button', 'pc-pri'); ok.appendChild(svg('janela')); ok.appendChild(el('span', null, 'Abrir janela do Windows'));
    var nao = el('button', null, 'Cancelar');
    ok.onclick = function () { f.remove(); acao(); }; nao.onclick = function () { f.remove(); };
    r.appendChild(nao); r.appendChild(ok); c.appendChild(r); f.appendChild(c); document.body.appendChild(f); ok.focus();
  }
  function usarSeletor(input) {
    return ativo && !aberto && !bypass && input && input.type === 'file' && !input.disabled && !input.webkitdirectory && !input.hasAttribute('webkitdirectory') && !input.hasAttribute('data-ppcpm-windows');
  }
  function viaSeletor(input) {
    abrirSeletor({ accept: input.accept, multiple: input.multiple }).then(function (r) {
      if (!r) return;
      if (r.windows) return r.deJanela ? comClique(function () { janelaWindows(input); }) : janelaWindows(input);
      entregar(input, r.files);
    });
  }

  // 1) programas que abrem a janela com input.click() (a maioria)
  var origClick = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function () {
    if (ativo && aberto && !bypass && JANELA && !JANELA.closed && this.type === 'file' && !this.webkitdirectory) { try { JANELA.focus(); } catch (e) { } return; }
    if (usarSeletor(this)) { viaSeletor(this); return; }
    return origClick.apply(this, arguments);
  };
  // 2) clique direto no campo de arquivo ou num <label> ligado a ele
  document.addEventListener('click', function (e) {
    if (bypass || !ativo) return;
    var t = e.target, input = null;
    if (t && t.tagName === 'INPUT' && t.type === 'file') input = t;
    else if (t && t.closest) { var l = t.closest('label'); if (l && l.control && l.control.type === 'file') input = l.control; }
    if (input && usarSeletor(input)) { e.preventDefault(); e.stopPropagation(); viaSeletor(input); }
  }, true);
  // 3) programas que usam showOpenFilePicker (ex.: Impressão de Etiquetas)
  if (typeof window.showOpenFilePicker === 'function') {
    var origPicker = window.showOpenFilePicker.bind(window);
    window.showOpenFilePicker = function (o) {
      if (!ativo || aberto) return origPicker(o);
      o = o || {};
      var accept = [];
      (o.types || []).forEach(function (t) { Object.keys(t.accept || {}).forEach(function (m) { accept = accept.concat(t.accept[m]); }); });
      return abrirSeletor({ accept: accept.join(','), multiple: !!o.multiple }).then(function (r) {
        if (!r) throw new DOMException('Cancelado', 'AbortError');
        if (r.windows) return r.deJanela ? new Promise(function (ok, erro) { comClique(function () { origPicker(o).then(ok, erro); }); }) : origPicker(o);
        return r.files.map(function (f) {
          return { kind: 'file', name: f.name, getFile: function () { return Promise.resolve(f); },
            queryPermission: function () { return Promise.resolve('granted'); }, requestPermission: function () { return Promise.resolve('granted'); },
            isSameEntry: function (x) { return Promise.resolve(x === this); } };
        });
      });
    };
  }

  /* ---------- SAIR = encerrar o sistema por completo neste PC ----------
     Botão "Sair" do sistema: pergunta [S] Sim / [N] Não. Com Sim, faz o logout e desliga
     o Python (a janela preta fecha). No dia seguinte, abre de novo pelo atalho.
     Quem entra pela rede (--rede) só faz o logout normal: não desliga o PC de ninguém. */
  function perguntaSair() {
    return new Promise(function (resolve) {
      estilo();
      var f = el('div'); f.id = 'ppcpm-sair'; f.setAttribute('role', 'alertdialog'); f.setAttribute('aria-modal', 'true');
      f.style.cssText = 'position:fixed;inset:0;z-index:2147483600;background:rgba(5,10,25,.6);display:flex;align-items:center;justify-content:center;padding:16px;font-family:Arial,Helvetica,sans-serif';
      var c = el('div'); c.style.cssText = 'background:#fff;color:#1a2233;border-radius:12px;box-shadow:0 18px 55px rgba(0,0,0,.45);max-width:480px;width:100%;overflow:hidden;border:1px solid #0b2150';
      var t = el('div', null, 'SISTEMA PPCPM - AVISA'); t.style.cssText = 'background:linear-gradient(180deg,#0b2150,#06142f);color:#fff;font:700 14px Arial,Helvetica,sans-serif;letter-spacing:.5px;text-align:center;padding:13px 16px';
      var m = el('div'); m.style.cssText = 'padding:20px 24px 6px;font:700 15px Arial,Helvetica,sans-serif;line-height:1.45';
      m.textContent = 'Deseja sair e encerrar o sistema por completo?';
      var m2 = el('div', null, 'O sistema será desligado neste PC. Para usar de novo, abra pelo atalho SISTEMA - PPCPM.');
      m2.style.cssText = 'padding:0 24px 18px;font:600 13px Arial,Helvetica,sans-serif;color:#4b5563;line-height:1.45';
      var r = el('div'); r.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;padding:12px 18px;background:#f7f8fa;border-top:1px solid #e3e7ee;flex-wrap:wrap';
      function b(txt, pri) {
        var x = el('button', null, txt);
        x.style.cssText = 'font:700 13px Arial,Helvetica,sans-serif;border-radius:7px;padding:8px 16px;cursor:pointer;border:1px solid ' + (pri ? '#0b5cad;background:#0b5cad;color:#fff' : '#c5cbd6;background:#f2f4f6;color:#1f2937');
        return x;
      }
      var bTroca = b('Só trocar de usuário'), bN = b('[N] Não'), bS = b('[S] Sim, encerrar', true);
      bTroca.style.marginRight = 'auto';
      r.appendChild(bTroca); r.appendChild(bN); r.appendChild(bS);
      c.appendChild(t); c.appendChild(m); c.appendChild(m2); c.appendChild(r); f.appendChild(c);
      function fim(v) { document.removeEventListener('keydown', tecla, true); f.remove(); resolve(v); }
      function tecla(e) {
        var k = (e.key || '').toLowerCase();
        if (k === 's' || k === 'enter') { e.preventDefault(); e.stopPropagation(); fim('sim'); }
        else if (k === 'n' || k === 'escape') { e.preventDefault(); e.stopPropagation(); fim('nao'); }
      }
      bS.onclick = function () { fim('sim'); }; bN.onclick = function () { fim('nao'); }; bTroca.onclick = function () { fim('trocar'); };
      document.addEventListener('keydown', tecla, true);
      document.body.appendChild(f); bS.focus();
    });
  }
  function telaEncerrado() {
    var f = el('div');
    f.style.cssText = 'position:fixed;inset:0;z-index:2147483646;background:#06142f;color:#e8f0ff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;font-family:Arial,Helvetica,sans-serif;text-align:center;padding:20px';
    f.innerHTML = '<div style="font:700 22px Arial,Helvetica,sans-serif;letter-spacing:.5px">SISTEMA - PPCPM ENCERRADO</div>'
      + '<div style="font:600 14px Arial,Helvetica,sans-serif;color:#9fb5dc">O sistema foi desligado neste PC. Pode fechar esta aba.</div>'
      + '<div style="font:600 14px Arial,Helvetica,sans-serif;color:#9fb5dc">Para usar de novo, abra pelo atalho <b style="color:#fff">SISTEMA - PPCPM</b>.</div>';
    document.body.appendChild(f);
  }
  if (window.top === window) {
    document.addEventListener('click', function (e) {
      var bt = e.target && e.target.closest && e.target.closest('#out');
      if (!bt || bypass || !ativo) return;
      e.preventDefault(); e.stopImmediatePropagation();
      perguntaSair().then(function (v) {
        if (v === 'nao') return;
        bypass = true; try { bt.click(); } finally { bypass = false; }          // logout normal do sistema
        if (v !== 'sim') return;
        setTimeout(function () {
          fetch('/api/encerrar', { method: 'POST', headers: CAB }).then(function () { telaEncerrado(); try { window.close(); } catch (x) { } })
            .catch(function () { telaEncerrado(); });
        }, 600);
      });
    }, true);
  }

  /* ---------- AVISO DE VERSÃO NOVA (HTML ou Python) ----------
     O Python deste PC se atualiza sozinho. Quando isso acontece, a tela aberta mostra
     "Nova versão disponível" — é só clicar em Atualizar agora (não precisa sair do sistema). */
  if (window.top === window) {
    var inicial = null, avisado = '';
    function statusAgora() { return fetch('/api/status', { cache: 'no-store' }).then(function (r) { return r.json(); }); }
    function avisoVersao(texto) {
      if (document.getElementById('updAviso') || document.getElementById('ppcpm-upd')) return;
      var d = el('div'); d.id = 'ppcpm-upd'; d.setAttribute('role', 'status');
      d.style.cssText = 'position:fixed;right:18px;top:18px;z-index:2147483500;display:flex;align-items:center;gap:12px;background:#e8ebef;color:#1f2937;border:1px solid #c9d0d9;border-left:5px solid #0b5cad;border-radius:10px;padding:12px 14px;box-shadow:0 8px 28px rgba(0,0,0,.35);font:600 13px Arial,Helvetica,sans-serif;max-width:440px';
      var t = el('span'); t.innerHTML = '<b style="font-weight:800">Nova versão disponível</b><br><span style="font-weight:500;color:#4b5563"></span>';
      t.lastChild.textContent = texto + ' — salve o que estiver fazendo e atualize.';
      var ok = el('button', null, 'Atualizar agora'), dep = el('button', null, 'Depois');
      ok.style.cssText = 'background:#0b5cad;color:#fff;border:1px solid #0b5cad;border-radius:7px;padding:8px 14px;font:700 13px Arial,Helvetica,sans-serif;cursor:pointer;white-space:nowrap';
      dep.style.cssText = 'background:#f2f4f6;color:#1f2937;border:1px solid #c5cbd6;border-radius:7px;padding:8px 10px;font:700 13px Arial,Helvetica,sans-serif;cursor:pointer';
      ok.onclick = function () { location.reload(); }; dep.onclick = function () { d.remove(); };
      d.appendChild(t); d.appendChild(ok); d.appendChild(dep); document.body.appendChild(d);
    }
    function conferir() {
      if (document.hidden) return;
      statusAgora().then(function (j) {
        if (!inicial) { inicial = j; return; }
        var chave = j.versao + '|' + j.pacote_python;
        if (chave !== inicial.versao + '|' + inicial.pacote_python && chave !== avisado) {
          avisado = chave;
          avisoVersao(j.versao !== inicial.versao ? j.versao : 'Pacote Python ' + j.pacote_python);
        }
      }).catch(function () { /* sistema reiniciando com a versão nova: confere de novo daqui a pouco */ });
    }
    conferir();
    setInterval(conferir, 30000);
    document.addEventListener('visibilitychange', conferir);
  }

  // Para os próximos programas em Python: window.PPCPM_PC.abrir({accept:'.dbf', multiple:true})
  window.PPCPM_PC = { abrir: function (o) { return abrirSeletor(o).then(function (r) { return r && r.files ? r.files : []; }); }, ativo: function () { return ativo; } };
})();
