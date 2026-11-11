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
  fetch(API + 'locais?rapido=1', { cache: 'no-store', headers: CAB }).then(function (r) {   // rápido: não espera o Windows
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
    arquivos: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 10h18"/>',
    voltar: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    avancar: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    atualizar: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 5v6h-6"/>',
    copiar: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    classificar: '<path d="M7 4v16M3 16l4 4 4-4M17 20V4M13 8l4-4 4 4"/>',
    visualizar: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    mais: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
    detalhes: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>',
    chevron: '<path d="M6 9l6 6 6-6"/>',
    direita: '<path d="M9 6l6 6-6 6"/>',
    pin: '<path d="M14 3l7 7-3 1-4 4 1 5-2 1-4-4-5 5M9 15l-4-4 1-2 5 1 4-4 1-3"/>',
    casa: '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    pc: '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/>',
    vLista: '<path d="M4 6h3M10 6h10M4 12h3M10 12h10M4 18h3M10 18h10"/>',
    vIcones: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    vDetalhes: '<path d="M3 5h18M3 10h18M3 15h18M3 20h18"/>',
    ok: '<path d="M5 12l5 5 9-10"/>'
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

  /* ---------- visual: estilo do Explorador de Arquivos do Windows 11 (segue o tema claro/escuro do sistema) ---------- */
  function temaClaro() { try { var u = JSON.parse(localStorage.getItem('projeart_pcp:ui') || 'null'); return !!(u && u.tema === 'light'); } catch (e) { return false; } }
  function estilo(D) {
    D = D || document;
    if (D.getElementById('ppcpm-pc-css')) return;
    var c = D.createElement('style'); c.id = 'ppcpm-pc-css';
    var P = '#ppcpm-pc';
    c.textContent = [
      P + '{--fundo:#191919;--painel:#202020;--campo:#2d2d2d;--borda:#333;--texto:#fff;--texto2:#c8c8c8;--fraco:#9a9a9a;--hover:#2a2a2a;--sel:#2c4a68;--selb:#3d6a96;--acento:#60cdff;--btn:#2d2d2d;--menu:#2c2c2c;--sombra:rgba(0,0,0,.55);--pasta:#e8b54a}',
      P + '.claro{--fundo:#fff;--painel:#f3f3f3;--campo:#fff;--borda:#e1e1e1;--texto:#1a1a1a;--texto2:#3b3b3b;--fraco:#6b6b6b;--hover:#f0f0f0;--sel:#cce8ff;--selb:#99d1ff;--acento:#005fb8;--btn:#fbfbfb;--menu:#f9f9f9;--sombra:rgba(0,0,0,.25);--pasta:#f2b33d}',
      P + '{position:fixed;inset:0;z-index:2147483000;background:rgba(5,10,25,.55);font:400 13px Arial,Helvetica,sans-serif;color:var(--texto)}',
      P + ' *{box-sizing:border-box;font-family:Arial,Helvetica,sans-serif}',
      P + ' .pc-card{position:absolute;background:var(--fundo);border:1px solid var(--borda);border-radius:8px;box-shadow:0 18px 55px var(--sombra);display:flex;flex-direction:column;overflow:hidden;min-width:560px;min-height:380px;color:var(--texto)}',
      P + ' .pc-card.max{border-radius:0}',
      /* abas (como as abas do Explorador) */
      P + ' .pc-abas{position:relative;display:flex;align-items:flex-end;height:40px;padding:0 6px 0 8px;background:var(--painel);user-select:none;flex:none;cursor:move}',
      P + ' .pc-aba{display:flex;align-items:center;gap:8px;height:32px;padding:0 10px 0 12px;min-width:180px;max-width:320px;background:var(--fundo);border-radius:8px 8px 0 0;color:var(--texto);cursor:default}',
      P + ' .pc-aba .pc-an{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      P + ' .pc-aba button{padding:3px!important;border:0!important;background:transparent!important}',
      P + ' .pc-aba button:hover{background:var(--hover)!important}',
      P + ' .pc-abas .pc-tipos{margin:0 auto 9px 14px;color:var(--fraco);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      P + ' .pc-abas .pc-r{display:flex;gap:2px;align-self:center}',
      P + ' .pc-abas .pc-r button{background:transparent;border:0;padding:7px 12px;border-radius:4px}',
      P + ' .pc-abas .pc-r button:hover{background:var(--hover)}',
      P + ' .pc-abas .pc-r button.pc-x:hover{background:#c42b1c;color:#fff}',
      P + '.janela .pc-abas{cursor:default}',
      /* linha do endereço */
      P + ' .pc-end{display:flex;align-items:center;gap:4px;padding:6px 10px;background:var(--fundo);flex:none}',
      P + ' .pc-nav{background:transparent!important;border:0!important;padding:7px 9px!important;border-radius:4px!important;color:var(--texto)!important}',
      P + ' .pc-nav:hover:not(:disabled){background:var(--hover)!important}',
      P + ' .pc-nav:disabled{opacity:.35!important}',
      P + ' .pc-mig{flex:1;min-width:0;height:32px;display:flex;align-items:center;gap:0;background:var(--campo);border:1px solid var(--borda);border-radius:4px;padding:0 4px 0 8px;overflow:hidden;cursor:text}',
      P + ' .pc-mig .pc-sv{color:var(--texto2);margin-right:4px}',
      P + ' .pc-mig .pc-pt{padding:4px 6px;border-radius:3px;white-space:nowrap;cursor:pointer;color:var(--texto)}',
      P + ' .pc-mig .pc-pt:hover{background:var(--hover)}',
      P + ' .pc-mig .pc-sp{color:var(--fraco);padding:0 1px;font-size:11px}',
      P + ' .pc-mig .pc-vz{flex:1 0 40px;align-self:stretch}',
      P + ' .pc-mig .pc-pt,' + P + ' .pc-mig .pc-sp,' + P + ' .pc-mig > .pc-sv{flex:none}',
      P + ' .pc-mig input{flex:1;height:100%;border:0!important;outline:0!important;background:transparent!important;padding:0 4px!important}',
      P + ' .pc-pesq{position:relative;width:260px;flex:none}',
      P + ' .pc-pesq input{width:100%;height:32px;padding:0 32px 0 10px!important}',
      P + ' .pc-pesq .pc-sv{position:absolute;right:10px;top:50%;transform:translateY(-50%);color:var(--texto2)}',
      P + ' input[type=text]{border:1px solid var(--borda);border-radius:4px;font:400 13px Arial,Helvetica,sans-serif;color:var(--texto);background:var(--campo)}',
      P + ' input[type=text]::placeholder{color:var(--fraco)}',
      P + ' input[type=text]:focus{outline:0;border-bottom:2px solid var(--acento)}',
      /* barra de comandos */
      P + ' .pc-cmd{display:flex;align-items:center;gap:2px;padding:4px 10px 6px;background:var(--fundo);border-bottom:1px solid var(--borda);flex:none;min-height:44px}',
      P + ' .pc-cmd button{background:transparent;border:0;padding:7px 10px;border-radius:4px;color:var(--texto)}',
      P + ' .pc-cmd button:hover:not(:disabled){background:var(--hover)}',
      P + ' .pc-cmd button.on{background:var(--hover)}',
      P + ' .pc-cmd .pc-div{width:1px;height:22px;background:var(--borda);margin:0 6px;flex:none}',
      P + ' .pc-cmd .pc-esp{flex:1}',
      P + ' .pc-cmd .pc-ab{color:var(--acento)}',
      P + ' button{font:400 13px Arial,Helvetica,sans-serif;border-radius:4px;padding:7px 12px;cursor:pointer;border:1px solid var(--borda);background:var(--btn);color:var(--texto);white-space:nowrap;display:inline-flex;align-items:center;gap:7px}',
      P + ' button:hover{background:var(--hover)}',
      P + ' button.pc-pri{background:#0b5cad;border-color:#0b5cad;color:#fff;font-weight:700}',
      P + ' button.pc-pri:hover:not(:disabled){background:#1a6dc0;border-color:#1a6dc0}',
      P + ' button.pc-pri:disabled{opacity:.55}',
      P + ' button:disabled{opacity:.45;cursor:default}',
      P + ' .pc-sv{display:inline-flex;align-items:center}',
      P + ' .pc-sv svg{stroke:currentColor}',
      /* menus suspensos */
      P + ' .pc-menu{position:absolute;z-index:20;min-width:220px;background:var(--menu);border:1px solid var(--borda);border-radius:8px;box-shadow:0 10px 30px var(--sombra);padding:4px}',
      P + ' .pc-menu div{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:4px;cursor:pointer;white-space:nowrap;color:var(--texto)}',
      P + ' .pc-menu div:hover{background:var(--hover)}',
      P + ' .pc-menu div .pc-ok{width:14px;color:var(--acento);flex:none}',
      P + ' .pc-menu hr{border:0;border-top:1px solid var(--borda);margin:4px 2px}',
      P + ' .pc-menu .pc-mt{padding:6px 12px 2px;font-size:11px;color:var(--fraco);cursor:default}',
      P + ' .pc-menu .pc-mt:hover{background:transparent}',
      /* corpo */
      P + ' .pc-corpo{flex:1;display:flex;min-height:0;background:var(--fundo)}',
      P + ' .pc-lado{width:240px;flex:none;overflow:auto;padding:6px 0;background:var(--fundo)}',
      P + ' .pc-sep{height:1px;background:var(--borda);margin:8px 12px}',
      P + ' .pc-sec{display:flex;align-items:center;gap:6px;padding:7px 12px 4px;color:var(--texto2);cursor:pointer;user-select:none}',
      P + ' .pc-sec .pc-sv{color:var(--fraco)}',
      P + ' .pc-loc{position:relative;display:flex;align-items:center;gap:10px;padding:6px 12px 6px 28px;margin:0 6px;border-radius:4px;cursor:pointer;white-space:nowrap;overflow:hidden;color:var(--texto)}',
      P + ' .pc-loc.top{padding-left:12px}',
      P + ' .pc-loc .pc-sv{flex:none}',
      P + ' .pc-loc span.pc-ln{overflow:hidden;text-overflow:ellipsis;flex:1}',
      P + ' .pc-loc:hover{background:var(--hover)}',
      P + ' .pc-loc.on{background:var(--hover)}',
      P + ' .pc-loc.on:before{content:"";position:absolute;left:0;top:25%;bottom:25%;width:3px;border-radius:2px;background:var(--acento)}',
      P + ' .pc-loc .pc-pin{color:var(--fraco);flex:none}',
      P + ' .pc-loc .pc-x{display:none;color:var(--fraco);flex:none}',
      P + ' .pc-loc:hover .pc-x{display:inline-flex}',
      P + ' .pc-loc:hover .pc-x + .pc-pin{display:none}',
      P + ' .pc-main{flex:1;display:flex;flex-direction:column;min-width:0;overflow-x:auto}',
      P + ' .pc-main.cols-px .pc-cab,' + P + ' .pc-main.cols-px .pc-lista{min-width:max-content}',
      P + ' .pc-cab span .pc-rz{position:absolute;right:0;top:0;bottom:0;width:7px;cursor:col-resize;z-index:3}',
      P + ' .pc-cab span .pc-rz:hover,' + P + ' .pc-cab span .pc-rz.ativo{background:var(--selb)}',
      P + ' .pc-cab span .pc-fb{position:absolute;right:8px;top:50%;transform:translateY(-50%);width:20px;height:22px;display:none;align-items:center;justify-content:center;border-left:1px solid var(--borda);border-radius:0 3px 3px 0;color:var(--texto2);z-index:2}',
      P + ' .pc-cab span:hover .pc-fb,' + P + ' .pc-cab span.filtrado .pc-fb{display:flex}',
      P + ' .pc-cab span .pc-fb:hover{background:var(--hover);color:var(--texto)}',
      P + ' .pc-cab span.filtrado .pc-fb{color:var(--acento)}',
      P + ' .pc-cab span.filtrado{font-weight:700}',
      P + ' .pc-cab span.pc-tm .pc-fb{right:8px}',
      P + ' .pc-menu.pc-filtro div{padding:6px 12px}',
      P + ' .pc-menu.pc-filtro .pc-cb{position:static;display:inline-flex;margin:0;opacity:1!important}',
      P + ' .pc-menu.pc-filtro .pc-cb svg{opacity:0}',
      P + ' .pc-menu.pc-filtro .pc-cb.on{background:var(--acento);border-color:var(--acento)}',
      P + ' .pc-menu.pc-filtro .pc-cb.on svg{opacity:1;color:#fff}',
      P + ' .pc-split{width:9px;flex:none;cursor:col-resize;z-index:3;position:relative;background:linear-gradient(var(--borda),var(--borda)) center/1px 100% no-repeat}',
      P + ' .pc-split:after{content:"";position:absolute;left:2px;top:50%;width:5px;height:38px;transform:translateY(-50%);border-radius:3px;background:radial-gradient(circle,var(--texto2) 1.2px,transparent 1.6px) center/5px 7px repeat-y;opacity:.75}',
      P + ' .pc-split:hover,' + P + ' .pc-split.ativo{background:var(--selb)}',
      P + ' .pc-split:hover:after,' + P + ' .pc-split.ativo:after{opacity:1}',
      P + ' .pc-card.estreita .pc-split{display:none}',
      P + ' .pc-cab{display:grid;grid-template-columns:var(--pc-cols,minmax(200px,1fr) 160px 190px 90px);align-items:center;padding:0 14px 0 20px;height:32px;color:var(--texto2);border-bottom:1px solid var(--borda);flex:none}',
      P + ' .pc-cab span{position:relative;cursor:pointer;user-select:none;padding:8px 8px;border-left:1px solid var(--borda);white-space:nowrap;overflow:hidden}',
      P + ' .pc-cab span:first-child{border-left:0;padding-left:30px}',
      P + ' .pc-cab span:hover{background:var(--hover)}',
      P + ' .pc-cab span.on:after{content:"";position:absolute;left:50%;top:2px;width:7px;height:7px;border-left:1.5px solid var(--fraco);border-top:1.5px solid var(--fraco);transform:translateX(-50%) rotate(45deg)}',
      P + ' .pc-cab span.on.desc:after{top:-1px;transform:translateX(-50%) rotate(225deg)}',
      P + ' .pc-cab span.pc-tm{text-align:right}',
      P + ' .pc-lista{position:relative;flex:1;overflow:auto;outline:none;padding:2px 8px 8px}',
      P + ' .pc-laco{position:absolute;z-index:3;pointer-events:none;border:1px solid #0b5cad;background:rgba(11,92,173,.28)}',
      P + ' .pc-cb{flex:none;width:16px;height:16px;border:1.5px solid var(--fraco);border-radius:3px;display:inline-flex;align-items:center;justify-content:center;opacity:0;cursor:pointer;background:var(--campo)}',
      P + ' .pc-cb.vz{visibility:hidden}',
      P + ' .pc-row:hover .pc-cb,' + P + ' .pc-row.sel .pc-cb,' + P + '.com-sel .pc-cb{opacity:1}',
      P + ' .pc-row.sel .pc-cb{background:#0b5cad;border-color:#0b5cad;color:#fff}',
      P + ' .pc-cb svg{stroke:#fff!important}',
      P + ' .pc-cbt{position:absolute;left:12px;top:50%;transform:translateY(-50%);padding:0!important;border:0!important}',
      P + ' .pc-cbt:hover{background:transparent!important}',
      P + ' .pc-cab span.pc-nm{padding-left:52px}',
      P + ' .pc-qtd{display:none;align-items:center;gap:6px;padding:5px 10px;border-radius:14px;background:#0b5cad;color:#fff!important;font-weight:700;white-space:nowrap}',
      P + '.com-sel .pc-qtd{display:inline-flex}',
      P + ' .pc-qtd *{color:#fff!important}',
      P + ' .pc-grupo{display:flex;align-items:center;gap:6px;padding:10px 6px 4px;color:var(--texto);font-size:15px;cursor:pointer;user-select:none}',
      P + ' .pc-grupo .pc-sv{color:var(--texto2)}',
      P + ' .pc-grupo .pc-gn{color:var(--fraco);font-size:12px}',
      P + ' .pc-grupo.fechado .pc-sv{transform:rotate(-90deg)}',
      P + ' .pc-row{display:grid;grid-template-columns:var(--pc-cols,minmax(200px,1fr) 160px 190px 90px);align-items:center;padding:0 6px 0 12px;height:30px;border-radius:4px;cursor:default;user-select:none;border:1px solid transparent;color:var(--texto)}',
      P + ' .pc-row:hover{background:var(--hover)}',
      P + ' .pc-row.sel{background:var(--sel);border-color:var(--selb)}',
      P + ' .pc-row .pc-n{display:flex;align-items:center;gap:8px;min-width:0;padding-right:8px}',
      P + ' .pc-row .pc-nt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      P + ' .pc-row .pc-c{color:var(--fraco);font-size:11px;margin-left:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}',
      P + ' .pc-row .pc-d,' + P + ' .pc-row .pc-ti,' + P + ' .pc-row .pc-t{color:var(--texto2);padding:0 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      P + ' .pc-row .pc-t{text-align:right}',
      /* modo lista e ícones grandes */
      P + ' .pc-lista.lista .pc-cab,' + P + '.v-lista .pc-cab,' + P + '.v-icones .pc-cab{display:none}',
      P + '.v-lista .pc-gb{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:0 6px}',
      P + '.v-lista .pc-row{grid-template-columns:1fr;height:28px}',
      P + '.v-lista .pc-row .pc-d,' + P + '.v-lista .pc-row .pc-ti,' + P + '.v-lista .pc-row .pc-t{display:none}',
      P + '.v-icones .pc-gb{display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:6px}',
      P + '.v-icones .pc-row{grid-template-columns:1fr;height:auto;padding:10px 6px;text-align:center}',
      P + '.v-icones .pc-row .pc-n{flex-direction:column;gap:6px;padding:0}',
      P + '.v-icones .pc-row .pc-nt{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;word-break:break-word}',
      P + '.v-icones .pc-row .pc-ic svg{width:48px;height:48px}',
      P + '.v-icones .pc-row .pc-d,' + P + '.v-icones .pc-row .pc-ti,' + P + '.v-icones .pc-row .pc-t,' + P + '.v-icones .pc-row .pc-c{display:none}',
      /* painel de detalhes */
      P + ' .pc-det{width:260px;flex:none;border-left:1px solid var(--borda);padding:16px;overflow:auto;display:none;background:var(--fundo)}',
      P + '.com-det .pc-det{display:block}',
      P + ' .pc-det .pc-dg{display:flex;justify-content:center;padding:18px 0 14px}',
      P + ' .pc-det .pc-dg svg{width:72px;height:72px}',
      P + ' .pc-det b{display:block;font:700 14px Arial,Helvetica,sans-serif;word-break:break-word;margin-bottom:12px}',
      P + ' .pc-det .pc-kv{display:grid;grid-template-columns:92px 1fr;gap:7px 8px;font-size:12px}',
      P + ' .pc-det .pc-kv span:nth-child(odd){color:var(--fraco)}',
      P + ' .pc-det .pc-kv span:nth-child(even){word-break:break-word;color:var(--texto2)}',
      P + ' .pc-ic{display:flex;flex:none}',
      P + ' .pc-vazio{padding:40px 20px;text-align:center;color:var(--fraco)}',
      P + ' .pc-erro{margin:14px;padding:10px 12px;border:1px solid #c42b1c;background:rgba(196,43,28,.12);color:var(--texto);border-radius:6px}',
      /* barra de status e rodapé (como a janela "Abrir" do Windows) */
      P + ' .pc-status{display:flex;align-items:center;gap:14px;padding:0 10px 0 14px;height:28px;color:var(--texto2);font-size:12px;background:var(--fundo);border-top:1px solid var(--borda);flex:none}',
      P + ' .pc-status .pc-info{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      P + ' .pc-status button{background:transparent;border:1px solid transparent;padding:3px 5px;border-radius:3px;color:var(--texto2)}',
      P + ' .pc-status button.on{border-color:var(--borda);background:var(--hover);color:var(--texto)}',
      P + ' .pc-rod{display:flex;gap:8px;align-items:center;padding:10px 14px;background:var(--painel);border-top:1px solid var(--borda);flex:none}',
      P + ' .pc-rod label{color:var(--texto2);white-space:nowrap}',
      P + ' .pc-rod .pc-nome{flex:1;min-width:120px;height:32px;padding:0 10px}',
      P + ' .pc-rod select{height:32px;min-width:170px;max-width:260px;border:1px solid var(--borda);border-radius:4px;background:var(--campo);color:var(--texto);font:400 13px Arial,Helvetica,sans-serif;padding:0 8px}',
      P + ' .pc-rod button{min-width:96px;justify-content:center}',
      /* redimensionar (janela dentro da página) */
      P + ' .pc-h{position:absolute;z-index:5}',
      P + ' .pc-h.n,' + P + ' .pc-h.s{left:10px;right:10px;height:7px;cursor:ns-resize}',
      P + ' .pc-h.n{top:-3px}' + P + ' .pc-h.s{bottom:-3px}',
      P + ' .pc-h.e,' + P + ' .pc-h.w{top:10px;bottom:10px;width:7px;cursor:ew-resize}',
      P + ' .pc-h.e{right:-3px}' + P + ' .pc-h.w{left:-3px}',
      P + ' .pc-h.ne,' + P + ' .pc-h.nw,' + P + ' .pc-h.se,' + P + ' .pc-h.sw{width:14px;height:14px}',
      P + ' .pc-h.ne{top:-3px;right:-3px;cursor:nesw-resize}' + P + ' .pc-h.sw{bottom:-3px;left:-3px;cursor:nesw-resize}',
      P + ' .pc-h.nw{top:-3px;left:-3px;cursor:nwse-resize}' + P + ' .pc-h.se{bottom:-3px;right:-3px;cursor:nwse-resize}',
      P + ' .pc-card.estreita .pc-lado,' + P + ' .pc-card.estreita .pc-det{display:none!important}',
      P + ' .pc-card.estreita .pc-cab,' + P + ' .pc-card.estreita .pc-row{grid-template-columns:1fr 90px}',
      P + ' .pc-card.estreita .pc-d,' + P + ' .pc-card.estreita .pc-ti{display:none}',
      P + ' .pc-card.estreita .pc-tx,' + P + ' .pc-card.estreita .pc-pesq,' + P + ' .pc-card.estreita .pc-tipos{display:none}',
      P + '.arrastando,' + P + '.arrastando *{user-select:none!important}',
      P + '.janela{background:var(--fundo)}',
      P + '.janela .pc-card{left:0!important;top:0!important;width:100%!important;height:100%!important;border:0;border-radius:0;box-shadow:none;min-width:0;min-height:0}',
      P + '.janela .pc-h{display:none}',
      /* cores fixas: alguns programas forçam cor em tudo; aqui a janela mantém as suas */
      P + ' .pc-card,' + P + ' .pc-card button,' + P + ' .pc-card span,' + P + ' .pc-card div,' + P + ' .pc-card b,' + P + ' .pc-card label{color:inherit}',
      P + ' .pc-card{color:var(--texto)!important}',
      P + ' button.pc-pri,' + P + ' button.pc-pri *{color:#fff!important}'
    ].join('\n');
    (D.head || D.documentElement).appendChild(c);
    if (D.body && D !== document) D.body.style.background = temaClaro() ? '#fff' : '#191919';
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

  /* ---------- seletor (estilo Explorador de Arquivos) ---------- */
  var TIPOS = { xlsx: 'Planilha do Microsoft Excel', xlsm: 'Planilha do Excel (com macros)', xls: 'Planilha do Excel 97-2003', xlsb: 'Planilha binária do Excel',
    ods: 'Planilha OpenDocument', csv: 'Arquivo CSV', pdf: 'Documento PDF', dbf: 'Arquivo DBF', zip: 'Pasta compactada (zip)', '7z': 'Arquivo 7-Zip', rar: 'Arquivo WinRAR',
    tar: 'Arquivo TAR', gz: 'Arquivo GZ', txt: 'Documento de texto', html: 'Documento HTML', htm: 'Documento HTML', json: 'Arquivo JSON', zpl: 'Arquivo de etiqueta (ZPL)',
    prn: 'Arquivo de impressão', dxf: 'Desenho DXF', dwg: 'Desenho do AutoCAD', cam: 'Arquivo CAM (CNC)', nc1: 'Arquivo CNC (DSTV)', png: 'Imagem PNG', jpg: 'Imagem JPEG', jpeg: 'Imagem JPEG', docx: 'Documento do Word' };
  function tipoDe(i) { if (i.pasta) return 'Pasta de arquivos'; var e = ext(i.nome).replace('.', ''); return TIPOS[e] || (e ? 'Arquivo ' + e.toUpperCase() : 'Arquivo'); }
  function grupoData(seg) {
    if (!seg) return [9, 'Sem data'];
    var d = new Date(seg * 1000), h = new Date(); h.setHours(0, 0, 0, 0);
    var dia = 864e5, t = d.getTime(), ini = h.getTime(), sem = ini - ((h.getDay() + 6) % 7) * dia;
    if (t >= ini) return [0, 'Hoje']; if (t >= ini - dia) return [1, 'Ontem'];
    if (t >= sem) return [2, 'Anteriormente nesta semana']; if (t >= sem - 7 * dia) return [3, 'Semana passada'];
    var mes = new Date(h.getFullYear(), h.getMonth(), 1).getTime(), mesAnt = new Date(h.getFullYear(), h.getMonth() - 1, 1).getTime();
    if (t >= mes) return [4, 'Anteriormente neste mês']; if (t >= mesAnt) return [5, 'Mês passado'];
    if (t >= new Date(h.getFullYear(), 0, 1).getTime()) return [6, 'Anteriormente neste ano'];
    return [7, 'Há muito tempo'];
  }
  function abrirSeletor(op) {
    op = op || {};
    var filtro = filtroDe(op.accept);
    var chave = 'ppcpm:pc:ultima:' + (op.pasta ? 'pasta' : (filtro || '*'));
    var J0 = abrirJanela();   // abre já no clique (o Chrome só permite janela nova dentro do clique)
    aberto = true; JANELA = J0;
    return janelaPronta(J0).then(function (J) { return new Promise(function (resolve) {
      var D = J ? J.document : document, W = J || window;
      JANELA = J;
      estilo(D); aberto = true;
      var estado = { caminho: '', pai: '', itens: [], sel: [], ordem: lsGet('ppcpm:pc:ordem') || 'nome', desc: lsGet('ppcpm:pc:desc') === '1',
        agrupar: lsGet('ppcpm:pc:agrupar') || 'data', vista: lsGet('ppcpm:pc:vista') || 'detalhes', soAceitos: !!filtro, busca: null,
        atras: [], frente: [], fechados: {}, det: lsGet('ppcpm:pc:det') === '1', ancora: null };
      if (J) try { J.document.title = 'PPCPM - ARQUIVOS'; } catch (e) { }

      var fundo = el('div'); fundo.id = 'ppcpm-pc'; fundo.setAttribute('role', 'dialog'); fundo.setAttribute('aria-modal', 'true');
      if (J) fundo.classList.add('janela');
      if (temaClaro()) fundo.classList.add('claro');
      var card = el('div', 'pc-card'); fundo.appendChild(card);
      function botao(ic, txt, titulo, cls) { var b = el('button', cls || null); if (ic) b.appendChild(svg(ic, 16)); if (txt) b.appendChild(el('span', 'pc-tx', txt)); if (titulo) b.title = titulo; return b; }

      /* ----- aba (como no Explorador) ----- */
      var top = el('div', 'pc-abas');
      var aba = el('div', 'pc-aba'); aba.appendChild(svg('pasta', 16)); var abaNome = el('span', 'pc-an', 'PPCPM - ARQUIVOS'); aba.appendChild(abaNome);
      var bAbaX = botao('fechar', null, 'Fechar (Esc)'); aba.appendChild(bAbaX); top.appendChild(aba);
      top.appendChild(el('span', 'pc-tipos', op.pasta ? 'Escolha uma pasta — os arquivos são lidos direto do seu computador' : filtro ? 'Tipos aceitos: ' + filtro.split(',').join(', ') : 'Qualquer arquivo'));
      var ctl = el('div', 'pc-r');
      var bMax = el('button'); bMax.title = 'Maximizar / restaurar'; bMax.appendChild(svg('maximizar', 14));
      var bX = el('button', 'pc-x'); bX.title = 'Fechar (Esc)'; bX.appendChild(svg('fechar', 15));
      ctl.appendChild(bMax); ctl.appendChild(bX); top.appendChild(ctl);
      card.appendChild(top);
      ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'].forEach(function (d) { var h = el('div', 'pc-h ' + d); h.dataset.d = d; card.appendChild(h); });

      /* ----- endereço: voltar, avançar, acima, atualizar, caminho e pesquisa ----- */
      var end = el('div', 'pc-end');
      var bVolta = botao('voltar', null, 'Voltar (Alt + seta para a esquerda)', 'pc-nav'), bAvanca = botao('avancar', null, 'Avançar (Alt + seta para a direita)', 'pc-nav');
      var bSobe = botao('up', null, 'Pasta acima (Backspace)', 'pc-nav'), bAtual = botao('atualizar', null, 'Atualizar (F5)', 'pc-nav');
      var mig = el('div', 'pc-mig'); mig.title = 'Clique para digitar ou colar um caminho (ex.: G:\\Meu Drive\\PCP)';
      var cam = el('input'); cam.type = 'text'; cam.placeholder = 'Cole o caminho do Explorador e aperte Enter';
      var pesq = el('div', 'pc-pesq'); var busca = el('input'); busca.type = 'text'; busca.placeholder = 'Pesquisar'; pesq.appendChild(busca); pesq.appendChild(svg('busca', 15));
      [bVolta, bAvanca, bSobe, bAtual, mig, pesq].forEach(function (x) { end.appendChild(x); });
      card.appendChild(end);

      /* ----- barra de comandos ----- */
      var cmd = el('div', 'pc-cmd');
      var bAbrirC = botao(op.pasta ? 'ok' : 'abrir', op.pasta ? 'Selecionar pasta' : op.multiple ? 'Abrir selecionados' : 'Abrir', op.pasta ? 'Usar a pasta clicada (ou a pasta aberta)' : 'Abrir o arquivo selecionado (Enter)'); bAbrirC.firstChild.classList.add('pc-ab');
      var bCopiar = botao('copiar', 'Copiar caminho', 'Copiar o caminho da pasta ou do arquivo selecionado');
      var bExp = botao('explorador', 'Abrir no Explorador', 'Abrir esta pasta no Explorador de Arquivos do Windows');
      var bFav = botao('pin', 'Fixar', 'Fixar esta pasta no Acesso rápido (painel da esquerda)');
      var bOrd = botao('classificar', 'Classificar', 'Classificar e agrupar'); bOrd.appendChild(svg('chevron', 12));
      var bVis = botao('visualizar', 'Visualizar', 'Detalhes, lista ou ícones grandes'); bVis.appendChild(svg('chevron', 12));
      var bMais = botao('mais', null, 'Mais opções');
      var bDet = botao('detalhes', 'Detalhes', 'Mostrar o painel de detalhes do arquivo selecionado');
      function div() { return el('span', 'pc-div'); }
      [bAbrirC, div(), bCopiar, bExp, bFav, div(), bOrd, bVis, div(), bMais, el('span', 'pc-esp'), bDet].forEach(function (x) { cmd.appendChild(x); });
      card.appendChild(cmd);

      /* ----- corpo: navegação | lista | detalhes ----- */
      var corpo = el('div', 'pc-corpo'); card.appendChild(corpo);
      var lado = el('aside', 'pc-lado'); corpo.appendChild(lado);
      var split = el('div', 'pc-split'); split.title = 'Arraste para mudar a largura do painel · duplo clique volta ao padrão'; corpo.appendChild(split);
      var main = el('section', 'pc-main'); corpo.appendChild(main);
      (function () {
        var lw = +lsGet('ppcpm:arquivos:painel'); if (lw >= 140 && lw <= 600) lado.style.width = lw + 'px';
        split.addEventListener('dblclick', function () { lsSet('ppcpm:arquivos:painel', ''); ajustarLado(); });
        split.addEventListener('pointerdown', function (e) {
          if (e.button !== 0) return; e.preventDefault(); var x0 = e.clientX, w0 = lado.getBoundingClientRect().width, w = w0;
          split.classList.add('ativo'); split.setPointerCapture(e.pointerId);
          function mv(ev) { w = Math.min(600, Math.max(140, w0 + ev.clientX - x0)); lado.style.width = w + 'px'; }
          function up(ev) { split.removeEventListener('pointermove', mv); split.removeEventListener('pointerup', up); split.classList.remove('ativo'); try { split.releasePointerCapture(ev.pointerId); } catch (_) { } lsSet('ppcpm:arquivos:painel', String(Math.round(w))); }
          split.addEventListener('pointermove', mv); split.addEventListener('pointerup', up);
        });
      })();
      var cab = el('div', 'pc-cab');
      var hN = el('span', null, 'Nome'), hD = el('span', 'pc-d', 'Data de modificação'), hTi = el('span', 'pc-ti', 'Tipo'), hT = el('span', 'pc-tm', 'Tamanho');
      [hN, hD, hTi, hT].forEach(function (h) { cab.appendChild(h); }); main.appendChild(cab);

      /* V149 — como no Explorador: arrastar a divisória das colunas e a borda do painel da esquerda (cursor ↔).
         Cada usuário guarda o seu tamanho; duplo clique na divisória volta ao padrão. */
      var COLS_PADRAO = [null, 160, 190, 90];
      function aplicarCols(w) {
        if (!w) { card.style.removeProperty('--pc-cols'); main.classList.remove('cols-px'); return; }
        card.style.setProperty('--pc-cols', w.map(function (x) { return Math.round(x) + 'px'; }).join(' ')); main.classList.add('cols-px');
      }
      try { var wc = JSON.parse(lsGet('ppcpm:arquivos:colunas') || 'null'); if (Array.isArray(wc) && wc.length === 4) aplicarCols(wc); } catch (e) { }
      var arrastouCol = false;
      [[hN, 'nome'], [hD, 'data'], [hTi, 'tipo'], [hT, 'tam']].forEach(function (p) {
        var fb = el('span', 'pc-fb'); fb.appendChild(svg('chevron', 12)); fb.title = 'Filtrar por ' + p[0].firstChild.textContent;
        fb.addEventListener('click', function (e) { e.stopPropagation(); abrirFiltro(p[0], p[1]); });
        p[0].appendChild(fb);
      });
      [hN, hD, hTi, hT].forEach(function (h, i) {
        var rz = el('span', 'pc-rz'); rz.title = 'Arraste para mudar a largura · duplo clique volta ao padrão'; h.appendChild(rz);
        rz.addEventListener('click', function (e) { e.stopPropagation(); });
        rz.addEventListener('dblclick', function (e) { e.stopPropagation(); aplicarCols(null); lsSet('ppcpm:arquivos:colunas', ''); });
        rz.addEventListener('pointerdown', function (e) {
          if (e.button !== 0) return; e.preventDefault(); e.stopPropagation();
          var ws = [hN, hD, hTi, hT].map(function (x) { return x.getBoundingClientRect().width; }), x0 = e.clientX, w0 = ws[i];
          rz.classList.add('ativo'); rz.setPointerCapture(e.pointerId); arrastouCol = false;
          function mv(ev) { arrastouCol = true; ws[i] = Math.max(i === 0 ? 120 : 60, w0 + ev.clientX - x0); aplicarCols(ws); }
          function up(ev) { rz.removeEventListener('pointermove', mv); rz.removeEventListener('pointerup', up); rz.classList.remove('ativo'); try { rz.releasePointerCapture(ev.pointerId); } catch (_) { } if (arrastouCol) lsSet('ppcpm:arquivos:colunas', JSON.stringify(ws.map(Math.round))); }
          rz.addEventListener('pointermove', mv); rz.addEventListener('pointerup', up);
        });
      });
      var cbTodos = null;
      if (op.multiple) {   // caixa "selecionar todos" no cabeçalho, como no Explorador
        hN.classList.add('pc-nm'); cbTodos = el('span', 'pc-cb pc-cbt'); cbTodos.title = 'Selecionar todos os arquivos (Ctrl + A)'; hN.appendChild(cbTodos);
        cbTodos.onclick = function (e) { e.stopPropagation(); var arqs = ultimaLista.filter(function (i) { return !entraEm(i); }).map(function (i) { return i.caminho; }); estado.sel = estado.sel.length === arqs.length ? [] : arqs; atualizarSel(); };
      }
      var lista = el('div', 'pc-lista'); lista.tabIndex = 0; main.appendChild(lista);
      var det = el('aside', 'pc-det'); corpo.appendChild(det);

      /* ----- status e rodapé (como a janela Abrir do Windows) ----- */
      var status = el('div', 'pc-status'); var stTxt = el('span', 'pc-info', '');
      var bVD = botao('vDetalhes', null, 'Detalhes'), bVI = botao('vIcones', null, 'Ícones grandes');
      status.appendChild(stTxt); status.appendChild(bVD); status.appendChild(bVI); card.appendChild(status);
      var rod = el('div', 'pc-rod');
      var lNome = el('label', null, 'Nome:'); var nome = el('input', 'pc-nome'); nome.type = 'text'; nome.readOnly = true; nome.placeholder = op.multiple ? 'Escolha um ou mais arquivos (Ctrl ou Shift + clique)' : 'Clique duas vezes no arquivo para abrir';
      var tipoSel = el('select'); tipoSel.title = 'Tipos de arquivo';
      if (filtro) { var o1 = el('option', null, 'Tipos aceitos (' + filtro.split(',').join(', ') + ')'); o1.value = '1'; tipoSel.appendChild(o1); }
      var o2 = el('option', null, 'Todos os arquivos (*.*)'); o2.value = '0'; tipoSel.appendChild(o2); tipoSel.value = filtro ? '1' : '0';
      var bWin = botao('janela', 'Janela do Windows', 'Usar a janela comum de abrir arquivo');
      var bOk = el('button', 'pc-pri', op.pasta ? 'Selecionar pasta' : op.multiple ? 'Abrir selecionados' : 'Abrir'); bOk.disabled = true;
      if (op.pasta) { tipoSel.style.display = 'none'; lNome.textContent = 'Pasta:'; nome.placeholder = 'Entre na pasta (dois cliques) ou clique nela e use Selecionar pasta'; }
      var bCan = el('button', null, 'Cancelar');
      var qtd = el('span', 'pc-qtd'); qtd.title = 'Clique para limpar a seleção'; qtd.style.cursor = 'pointer';
      qtd.onclick = function () { estado.sel = []; atualizarSel(); };
      [qtd, lNome, nome, tipoSel, bWin, bOk, bCan].forEach(function (x) { rod.appendChild(x); });
      card.appendChild(rod);

      function fechar(resultado) {
        if (!aberto) return;
        aberto = false; clearInterval(vigia);
        D.removeEventListener('keydown', tecla, true); W.removeEventListener('resize', ajustarTela); D.removeEventListener('pointerdown', fecharMenuFora, true);
        D.removeEventListener('pointermove', lacoMover); D.removeEventListener('pointerup', lacoSoltar);
        if (J) {
          try { if (!J.closed) lsSet(CHAVE_SO, JSON.stringify({ x: J.screenX, y: J.screenY, w: J.innerWidth, h: J.innerHeight })); } catch (e) { }
          try { if (!J.closed) J.close(); } catch (e) { }
          JANELA = null;
          try { window.focus(); } catch (e) { }
        } else fundo.remove();
        resolve(resultado);
      }

      /* ----- menus suspensos ----- */
      var menu = null;
      function fecharMenu() { if (menu) { menu.remove(); menu = null; } [bOrd, bVis, bMais].forEach(function (b) { b.classList.remove('on'); }); }
      function fecharMenuFora(e) { if (menu && !menu.contains(e.target) && (menu.dataset.b === 'ctx' || !e.target.closest('.pc-cmd button'))) fecharMenu(); }
      function abrirMenu(btn, itens) {
        var era = menu && menu.dataset.b === btn.title; fecharMenu(); if (era) return;
        menu = el('div', 'pc-menu'); menu.dataset.b = btn.title;
        itens.forEach(function (it) {
          if (it === '-') { menu.appendChild(el('hr')); return; }
          if (it.titulo) { menu.appendChild(el('div', 'pc-mt', it.titulo)); return; }
          var d = el('div'); var ok = el('span', 'pc-ok'); if (it.on) ok.appendChild(svg('ok', 14)); d.appendChild(ok);
          if (it.ic) d.appendChild(svg(it.ic, 15)); d.appendChild(el('span', null, it.txt));
          d.onclick = function () { fecharMenu(); it.f(); }; menu.appendChild(d);
        });
        var r = btn.getBoundingClientRect(), rc = card.getBoundingClientRect();
        menu.style.left = Math.min(r.left - rc.left, rc.width - 240) + 'px'; menu.style.top = (r.bottom - rc.top + 2) + 'px';
        card.appendChild(menu); btn.classList.add('on');
      }
      function setOrdem(o) { if (estado.ordem === o) estado.desc = !estado.desc; else { estado.ordem = o; estado.desc = o === 'data' || o === 'tam'; } lsSet('ppcpm:pc:ordem', o); lsSet('ppcpm:pc:desc', estado.desc ? '1' : '0'); desenhar(); }
      bOrd.onclick = function () {
        abrirMenu(bOrd, [{ txt: 'Nome', on: estado.ordem === 'nome', f: function () { setOrdem('nome'); } }, { txt: 'Data de modificação', on: estado.ordem === 'data', f: function () { setOrdem('data'); } },
          { txt: 'Tipo', on: estado.ordem === 'tipo', f: function () { setOrdem('tipo'); } }, { txt: 'Tamanho', on: estado.ordem === 'tam', f: function () { setOrdem('tam'); } }, '-',
          { txt: 'Crescente', on: !estado.desc, f: function () { estado.desc = false; lsSet('ppcpm:pc:desc', '0'); desenhar(); } }, { txt: 'Decrescente', on: estado.desc, f: function () { estado.desc = true; lsSet('ppcpm:pc:desc', '1'); desenhar(); } }, '-',
          { titulo: 'Agrupar por' },
          { txt: 'Data de modificação', on: estado.agrupar === 'data', f: function () { setAgrupar('data'); } }, { txt: 'Tipo', on: estado.agrupar === 'tipo', f: function () { setAgrupar('tipo'); } },
          { txt: '(Nenhum)', on: estado.agrupar === 'nenhum', f: function () { setAgrupar('nenhum'); } }]);
      };
      function setAgrupar(a) { estado.agrupar = a; estado.fechados = {}; lsSet('ppcpm:pc:agrupar', a); desenhar(); }
      function setVista(v) { estado.vista = v; lsSet('ppcpm:pc:vista', v); aplicarVista(); desenhar(); }
      function aplicarVista() {
        fundo.classList.toggle('v-lista', estado.vista === 'lista'); fundo.classList.toggle('v-icones', estado.vista === 'icones');
        bVD.classList.toggle('on', estado.vista === 'detalhes'); bVI.classList.toggle('on', estado.vista === 'icones');
        fundo.classList.toggle('com-det', estado.det); bDet.classList.toggle('on', estado.det);
      }
      bVis.onclick = function () {
        abrirMenu(bVis, [{ ic: 'vIcones', txt: 'Ícones grandes', on: estado.vista === 'icones', f: function () { setVista('icones'); } },
          { ic: 'vLista', txt: 'Lista', on: estado.vista === 'lista', f: function () { setVista('lista'); } },
          { ic: 'vDetalhes', txt: 'Detalhes', on: estado.vista === 'detalhes', f: function () { setVista('detalhes'); } }, '-',
          { ic: 'detalhes', txt: 'Painel de detalhes', on: estado.det, f: function () { bDet.onclick(); } }]);
      };
      bMais.onclick = function () {
        abrirMenu(bMais, [{ ic: 'janela', txt: 'Usar a janela comum do Windows', f: function () { bWin.onclick(); } },
          { ic: 'atualizar', txt: 'Atualizar unidades e favoritos', f: function () { api('locais').then(function (j) { LOCAIS = j; montarLado(); }).catch(function () { }); } },
          { ic: 'copiar', txt: 'Copiar caminho da pasta', f: function () { copiar(estado.caminho); } }]);
      };
      bDet.onclick = function () { estado.det = !estado.det; lsSet('ppcpm:pc:det', estado.det ? '1' : '0'); aplicarVista(); mostrarDet(); };
      bVD.onclick = function () { setVista('detalhes'); }; bVI.onclick = function () { setVista('icones'); };

      /* ----- painel da esquerda (Acesso rápido, Este Computador, Recentes) ----- */
      function locItem(nomeL, caminho, ic, opc) {
        opc = opc || {};
        var d = el('div', 'pc-loc' + (opc.top ? ' top' : '')); d.title = nomeL + (caminho && caminho !== nomeL ? '\n' + caminho : '');
        var sv = svg(ic, 20); if (ic === 'pasta' || ic === 'favorito' || ic === 'desktop' || ic === 'documentos' || ic === 'downloads') sv.style.color = 'var(--pasta)';
        if (ic === 'disco' || ic === 'rede') sv.style.color = 'var(--acento)';
        d.appendChild(sv); d.appendChild(el('span', 'pc-ln', nomeL));
        if (opc.remover) {
          var x = el('span', 'pc-x'); x.appendChild(svg('fechar', 13)); x.title = 'Desafixar';
          x.onclick = function (e) { e.stopPropagation(); fixar(caminho, true); };
          d.appendChild(x);
        }
        if (opc.pin) { var pn = el('span', 'pc-pin'); pn.appendChild(svg('pin', 13)); d.appendChild(pn); }
        d.onclick = function () { ir(caminho); };
        d.dataset.c = caminho; return d;
      }
      var secFechada = {};
      try { secFechada = JSON.parse(lsGet('ppcpm:pc:secoes') || '{}') || {}; } catch (e) { }
      function montarLado() {
        lado.innerHTML = '';
        var L = LOCAIS || { unidades: [], pastas: [], favoritos: [], recentes: [] };
        function sec(t, ic, arr, fn) {
          if (!arr.length) return;
          var h = el('div', 'pc-sec'); var ch = svg(secFechada[t] ? 'direita' : 'chevron', 12); h.appendChild(ch);
          var si = svg(ic, 19); si.style.color = ic === 'pc' ? 'var(--acento)' : 'var(--pasta)'; h.appendChild(si); h.appendChild(el('span', null, t));
          h.onclick = function () { secFechada[t] = !secFechada[t]; lsSet('ppcpm:pc:secoes', JSON.stringify(secFechada)); montarLado(); };
          lado.appendChild(h);
          if (!secFechada[t]) arr.forEach(function (a) { lado.appendChild(fn(a)); });
        }
        var fix = [], vistos = {};
        function por(a, fav) { var k = chaveC(a.caminho); if (vistos[k]) { if (fav) vistos[k].fav = true; return; } vistos[k] = { a: a, fav: fav }; fix.push(vistos[k]); }
        L.pastas.forEach(function (a) { por(a, false); });
        (L.acesso_rapido || []).forEach(function (a) { por(a, true); });
        (L.favoritos || []).forEach(function (a) { por(a, true); });
        sec('Acesso rápido', 'favorito', fix, function (x) {
          var d = locItem(x.a.nome, x.a.caminho, x.fav && !/rea de trabalho|documentos|downloads/i.test(x.a.nome) ? 'pasta' : iconeLocal(x.a), { remover: x.fav, pin: x.fav });
          d.oncontextmenu = function (e) { e.preventDefault(); menuEm(e.clientX, e.clientY, [{ ic: 'pasta', txt: 'Abrir', f: function () { ir(x.a.caminho); } },
            x.fav ? { ic: 'pin', txt: 'Desafixar do Acesso rápido', f: function () { fixar(x.a.caminho, true); } } : { ic: 'pin', txt: 'Fixar no Acesso rápido', f: function () { fixar(x.a.caminho); } },
            '-', { ic: 'copiar', txt: 'Copiar caminho', f: function () { copiar(x.a.caminho); } }, { ic: 'explorador', txt: 'Abrir no Explorador', f: function () { api('explorador', { caminho: x.a.caminho }).catch(function () { }); } }]); };
          return d;
        });
        lado.appendChild(el('div', 'pc-sep'));
        sec('Este Computador', 'pc', L.unidades, function (a) { return locItem(a.nome, a.caminho, iconeLocal(a)); });
        if (L.recentes.length) lado.appendChild(el('div', 'pc-sep'));
        sec('Recentes', 'recente', L.recentes, function (a) { var p = a.split(/[\\/]/).filter(Boolean); return locItem(p.length > 1 ? p[p.length - 2] + ' › ' + p[p.length - 1] : (p[0] || a), a, 'recente'); });
        marcarLado(); ajustarLado(); setTimeout(ajustarLado, 60); setTimeout(ajustarLado, 400);
      }
      /* V149 — sem tamanho escolhido pelo usuário, o painel abre largo o bastante para ler o nome inteiro das pastas (até 460px) */
      function ajustarLado() {
        if (+lsGet('ppcpm:arquivos:painel')) return;
        var maior = 240;
        Array.prototype.forEach.call(lado.querySelectorAll('.pc-loc,.pc-sec'), function (d) {
          var t = d.querySelector('.pc-ln') || d.querySelector('span'); if (!t || !t.offsetParent) return;
          var w = t.getBoundingClientRect().left - lado.getBoundingClientRect().left + t.scrollWidth + 48; if (w > maior) maior = w;
        });
        lado.style.width = Math.min(460, Math.ceil(maior)) + 'px';
      }
      function marcarLado() {
        Array.prototype.forEach.call(lado.querySelectorAll('.pc-loc'), function (d) { d.classList.toggle('on', d.dataset.c === estado.caminho); });
      }

      /* ----- caminho clicável (Este Computador › Downloads › 00 - ARQUIVOS) ----- */
      function partesCaminho(c) {
        var out = [], i, rede = /^\\\\/.test(c), ini = rede ? c.indexOf('\\', 2) : -1;
        if (rede) { var fimShare = c.indexOf('\\', ini + 1); var raiz = fimShare < 0 ? c : c.slice(0, fimShare); out.push([raiz.slice(2), raiz]); i = fimShare < 0 ? c.length : fimShare; }
        else i = 0;
        for (var k = i; k <= c.length; k++) {
          if (k === c.length || c[k] === '\\' || c[k] === '/') {
            var seg = c.slice(i, k).replace(/^[\\/]+/, '');
            if (seg) { var alvo = c.slice(0, k); if (/^[A-Za-z]:$/.test(alvo)) alvo += '\\'; if (alvo === '' && c[0] === '/') alvo = '/'; out.push([seg, alvo || '/']); }
            i = k;
          }
        }
        return out;
      }
      function montarMig() {
        mig.innerHTML = ''; var ic = svg('pc', 16); mig.appendChild(ic);
        if (estado.busca) { mig.appendChild(el('span', 'pc-pt', 'Resultados da pesquisa em ' + (estado.caminho.split(/[\\/]/).filter(Boolean).pop() || estado.caminho))); return; }
        var raizEl = el('span', 'pc-pt', 'Este Computador'); raizEl.onclick = function (e) { e.stopPropagation(); }; mig.appendChild(raizEl);
        partesCaminho(estado.caminho).forEach(function (p) {
          var sp = el('span', 'pc-sp'); sp.appendChild(svg('direita', 11)); mig.appendChild(sp);
          var a = el('span', 'pc-pt', p[0]); a.title = p[1]; a.onclick = function (e) { e.stopPropagation(); ir(p[1]); }; mig.appendChild(a);
        });
        mig.appendChild(el('span', 'pc-vz'));                          // espaço livre: clique para digitar o caminho
        mig.scrollLeft = mig.scrollWidth;                                // caminho comprido: mostra o fim (pasta atual)
      }
      function editarCaminho() {
        if (mig.contains(cam)) return;
        mig.innerHTML = ''; mig.appendChild(svg('pasta', 16)); cam.value = estado.caminho; mig.appendChild(cam); cam.focus(); cam.select();
      }
      mig.onclick = editarCaminho;
      cam.onkeydown = function (e) { if (e.key === 'Enter') { e.preventDefault(); if (cam.value.trim()) ir(cam.value.trim().replace(/^"|"$/g, '')); } else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); montarMig(); } };
      cam.onblur = function () { setTimeout(function () { if (D.activeElement !== cam) montarMig(); }, 150); };

      /* ----- lista ----- */
      function ordenar(a) {
        var o = estado.ordem, s = estado.desc ? -1 : 1;
        return a.slice().sort(function (x, y) {
          if (x.pasta !== y.pasta) return x.pasta ? -1 : 1;
          var r = 0;
          if (o === 'data') r = (x.modificado || 0) - (y.modificado || 0);
          else if (o === 'tam') r = (x.tamanho || 0) - (y.tamanho || 0);
          else if (o === 'tipo') r = tipoDe(x).localeCompare(tipoDe(y), 'pt-BR');
          if (!r) r = x.nome.localeCompare(y.nome, 'pt-BR', { numeric: true, sensitivity: 'base' }) * (o === 'nome' ? 1 : s);
          return r * s;
        });
      }
      /* V149 — filtro por coluna, como no Explorador (setinha ⌄ no título da coluna, caixinhas para marcar) */
      estado.filtros = {};
      var KB = 1024, FAIXAS_TAM = ['Vazio (0 KB)', 'Minúsculo (0 - 16 KB)', 'Pequeno (16 KB - 1 MB)', 'Médio (1 - 128 MB)', 'Grande (128 MB - 1 GB)', 'Enorme (1 - 4 GB)', 'Gigantesco (> 4 GB)', 'Não especificado'];
      var FAIXAS_NOME = ['0 - 9', 'A - H', 'I - P', 'Q - Z', 'Outros'];
      function chaveFiltro(col, i) {
        if (col === 'nome') {
          var c = String(i.nome || '').trim().charAt(0).toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
          return /[0-9]/.test(c) ? '0 - 9' : c >= 'A' && c <= 'H' ? 'A - H' : c >= 'I' && c <= 'P' ? 'I - P' : c >= 'Q' && c <= 'Z' ? 'Q - Z' : 'Outros';
        }
        if (col === 'data') return grupoData(i.modificado)[1];
        if (col === 'tipo') return tipoDe(i);
        if (i.pasta) return 'Não especificado';
        var b = +i.tamanho || 0;
        return !b ? FAIXAS_TAM[0] : b < 16 * KB ? FAIXAS_TAM[1] : b < KB * KB ? FAIXAS_TAM[2] : b < 128 * KB * KB ? FAIXAS_TAM[3] : b < KB * KB * KB ? FAIXAS_TAM[4] : b < 4 * KB * KB * KB ? FAIXAS_TAM[5] : FAIXAS_TAM[6];
      }
      function opcoesFiltro(col) {
        var aceitos = filtro ? filtro.split(',') : [], vistos = {}, lista_ = [];
        estado.itens.forEach(function (i) {
          if (op.pasta && !i.pasta) return;
          if (!i.pasta && !i.pacote && estado.soAceitos && aceitos.length && aceitos.indexOf(ext(i.nome)) < 0) return;
          var k = chaveFiltro(col, i); if (!vistos[k]) { vistos[k] = 1; lista_.push(k); }
        });
        var ordem = col === 'nome' ? FAIXAS_NOME : col === 'tam' ? FAIXAS_TAM : null;
        if (ordem) lista_.sort(function (a, b) { return ordem.indexOf(a) - ordem.indexOf(b); });
        else if (col === 'data') lista_.sort(function (a, b) { var g = function (t) { var x = estado.itens.find(function (i) { return grupoData(i.modificado)[1] === t; }); return x ? grupoData(x.modificado)[0] : 99; }; return g(a) - g(b); });
        else lista_.sort(function (a, b) { return a === 'Pasta de arquivos' ? -1 : b === 'Pasta de arquivos' ? 1 : a.localeCompare(b, 'pt-BR'); });
        (estado.filtros[col] || []).forEach(function (k) { if (lista_.indexOf(k) < 0) lista_.push(k); });
        return lista_;
      }
      function marcarFiltros() { [[hN, 'nome'], [hD, 'data'], [hTi, 'tipo'], [hT, 'tam']].forEach(function (p) { var f = estado.filtros[p[1]]; p[0].classList.toggle('filtrado', !!(f && f.length)); }); }
      function abrirFiltro(h, col) {
        var era = menu && menu.dataset.b === 'filtro-' + col; fecharMenu(); if (era) return;
        menu = el('div', 'pc-menu pc-filtro'); menu.dataset.b = 'filtro-' + col;
        var ops = opcoesFiltro(col);
        if (!ops.length) menu.appendChild(el('div', 'pc-mt', 'Nada para filtrar nesta pasta'));
        ops.forEach(function (k) {
          var d = el('div'), cb = el('span', 'pc-cb'); cb.appendChild(svg('ok', 12));
          var marc = function () { var f = estado.filtros[col] || []; cb.classList.toggle('on', f.indexOf(k) >= 0); };
          d.appendChild(cb); d.appendChild(el('span', null, k)); marc();
          d.onclick = function (e) {
            e.stopPropagation(); var f = estado.filtros[col] = estado.filtros[col] || [], ix = f.indexOf(k);
            if (ix >= 0) f.splice(ix, 1); else f.push(k);
            marc(); marcarFiltros(); desenhar();
          };
          menu.appendChild(d);
        });
        if ((estado.filtros[col] || []).length) {
          menu.appendChild(el('hr')); var lp = el('div'); lp.appendChild(el('span', 'pc-ok')); lp.appendChild(el('span', null, 'Limpar filtro'));
          lp.onclick = function () { estado.filtros[col] = []; fecharMenu(); marcarFiltros(); desenhar(); }; menu.appendChild(lp);
        }
        card.appendChild(menu);
        var r0 = h.getBoundingClientRect(), rc = card.getBoundingClientRect(), w = menu.offsetWidth;
        menu.style.left = Math.max(4, Math.min(r0.right - rc.left - w, rc.width - w - 6)) + 'px'; menu.style.top = (r0.bottom - rc.top + 2) + 'px';
      }
      function visiveis() {
        var aceitos = filtro ? filtro.split(',') : [], q = estado.busca ? '' : busca.value.trim().toLowerCase();
        return ordenar(estado.itens.filter(function (i) {
          if (q && i.nome.toLowerCase().indexOf(q) < 0) return false;
          if (op.pasta && !i.pasta) return false;
          if (!i.pasta && !i.pacote && estado.soAceitos && aceitos.length && aceitos.indexOf(ext(i.nome)) < 0) return false;
          for (var col in estado.filtros) { var fs = estado.filtros[col]; if (fs && fs.length && fs.indexOf(chaveFiltro(col, i)) < 0) return false; }
          return true;
        }));
      }
      var ultimaLista = [];
      /* ----- seleção com o mouse: clique e arraste no espaço vazio desenha o retângulo (como no Explorador) ----- */
      var laco = { ativo: false, arrastou: false };
      lista.addEventListener('pointerdown', function (e) {
        if (e.button !== 0 || e.target.closest('.pc-cb')) return;
        var r0 = lista.getBoundingClientRect();
        laco = { ativo: true, arrastou: false, x0: e.clientX - r0.left + lista.scrollLeft, y0: e.clientY - r0.top + lista.scrollTop, base: (e.ctrlKey || e.metaKey) && op.multiple ? estado.sel.slice() : [], cx: e.clientX, cy: e.clientY, div: null, rolar: null };
      });
      function lacoMover(e) {
        if (!laco.ativo) return;
        if (!laco.arrastou && Math.abs(e.clientX - laco.cx) + Math.abs(e.clientY - laco.cy) < 6) return;
        if (!laco.arrastou) { laco.arrastou = true; laco.div = el('div', 'pc-laco'); lista.appendChild(laco.div); fundo.classList.add('arrastando'); }
        laco.ex = e.clientX; laco.ey = e.clientY; desenharLaco();
        var r0 = lista.getBoundingClientRect();
        clearInterval(laco.rolar); laco.rolar = null;
        var passo = e.clientY > r0.bottom - 18 ? 18 : e.clientY < r0.top + 18 ? -18 : 0;
        if (passo) laco.rolar = setInterval(function () { lista.scrollTop += passo; desenharLaco(); }, 30);
      }
      function desenharLaco() {
        var r0 = lista.getBoundingClientRect();
        var x1 = laco.ex - r0.left + lista.scrollLeft, y1 = Math.max(0, Math.min(lista.scrollHeight, laco.ey - r0.top + lista.scrollTop));
        var L = Math.min(laco.x0, x1), T = Math.min(laco.y0, y1), W2 = Math.abs(x1 - laco.x0), H2 = Math.abs(y1 - laco.y0);
        laco.div.style.left = L + 'px'; laco.div.style.top = T + 'px'; laco.div.style.width = W2 + 'px'; laco.div.style.height = H2 + 'px';
        var dentro = [];
        Array.prototype.forEach.call(lista.querySelectorAll('.pc-row'), function (row) {
          var rr = row.getBoundingClientRect(), ry = rr.top - r0.top + lista.scrollTop, rx = rr.left - r0.left + lista.scrollLeft;
          if (ry < T + H2 && ry + rr.height > T && rx < L + W2 && rx + rr.width > L) {
            var it = ultimaLista.filter(function (i) { return i.caminho === row.dataset.c; })[0];
            if (it && !entraEm(it)) dentro.push(it.caminho);
          }
        });
        estado.sel = op.multiple ? laco.base.concat(dentro.filter(function (c) { return laco.base.indexOf(c) < 0; })) : dentro.slice(-1);
        if (dentro.length) estado.foco = dentro[dentro.length - 1];
        atualizarSel();
      }
      function lacoSoltar(e) {
        if (!laco.ativo) return;
        clearInterval(laco.rolar);
        var arrastou = laco.arrastou;
        if (laco.div) laco.div.remove();
        laco.ativo = false; fundo.classList.remove('arrastando');
        if (!arrastou && e && !e.target.closest('.pc-row') && lista.contains(e.target)) { estado.sel = []; estado.foco = null; atualizarSel(); }   // clique no vazio limpa
        setTimeout(function () { laco.arrastou = false; }, 0);
      }
      lista.oncontextmenu = function (e) {
        if (e.target.closest('.pc-row')) return;
        e.preventDefault();
        var it = [{ ic: 'atualizar', txt: 'Atualizar (F5)', f: function () { bAtual.onclick(); } }];
        if (estado.caminho) it.push(fixada(estado.caminho) ? { ic: 'pin', txt: 'Desafixar esta pasta do Acesso rápido', f: function () { fixar(estado.caminho, true); } } : { ic: 'pin', txt: 'Fixar esta pasta no Acesso rápido', f: function () { fixar(estado.caminho); } });
        if (op.multiple) it.push({ ic: 'ok', txt: 'Selecionar todos (Ctrl + A)', f: function () { estado.sel = ultimaLista.filter(function (x) { return !entraEm(x); }).map(function (x) { return x.caminho; }); atualizarSel(); } });
        it.push('-', { ic: 'copiar', txt: 'Copiar caminho da pasta', f: function () { copiar(estado.caminho); } }, { ic: 'explorador', txt: 'Abrir no Explorador', f: function () { bExp.onclick(); } });
        menuEm(e.clientX, e.clientY, it);
      };
      function linha(i, v) {
        var r = el('div', 'pc-row'); r.dataset.c = i.caminho;
        var n = el('span', 'pc-n');
        if (op.multiple) {
          var cb = el('span', 'pc-cb' + (entraEm(i) ? ' vz' : '')); cb.appendChild(svg('ok', 12)); n.appendChild(cb);
          if (!entraEm(i)) cb.onclick = function (e) { e.stopPropagation(); var k = estado.sel.indexOf(i.caminho); if (k >= 0) estado.sel.splice(k, 1); else estado.sel.push(i.caminho); estado.ancora = i.caminho; estado.foco = i.caminho; atualizarSel(); };
          cb.ondblclick = function (e) { e.stopPropagation(); };
        }
        n.appendChild(icone(i)); n.appendChild(el('span', 'pc-nt', i.nome));
        if (estado.busca) n.appendChild(el('span', 'pc-c', i.caminho));
        r.appendChild(n); r.appendChild(el('span', 'pc-d', fmtData(i.modificado))); r.appendChild(el('span', 'pc-ti', tipoDe(i))); r.appendChild(el('span', 'pc-t', i.pasta ? '' : fmtTam(i.tamanho)));
        var entra = i.pasta || (i.pacote && (filtro ? filtro.split(',') : []).indexOf(ext(i.nome)) < 0);
        r.title = i.caminho + (i.pacote && entra ? '  (compactado: dois cliques para abrir como pasta)' : '');
        r.onclick = function (e) { if (laco.arrastou) return; escolher(i, v, e); };
        r.oncontextmenu = function (e) { e.preventDefault(); if (estado.sel.indexOf(i.caminho) < 0) escolher(i, v, null); menuItem(i, e); };
        r.ondblclick = function () { if (entra) ir(i.caminho); else { estado.sel = [i.caminho]; confirmar(); } };
        return r;
      }
      function focoPasta() { var f = ultimaLista.filter(function (i) { return i.caminho === estado.foco; })[0]; return f && f.pasta ? f : null; }
      function chaveC(c) { return String(c || '').replace(/[\\/]+$/, '').toLowerCase(); }
      function fixada(c) {
        var L = LOCAIS || {}, k = chaveC(c);
        return (L.favoritos || []).concat(L.acesso_rapido || []).some(function (a) { return chaveC(a.caminho) === k; });
      }
      function fixar(c, tirar) {
        api('favorito', tirar ? { caminho: c, remover: 1 } : { caminho: c }).then(function (j) { LOCAIS = j; montarLado(); atualizarSel(); stTxt.textContent = tirar ? 'Pasta desafixada do Acesso rápido.' : 'Pasta fixada no Acesso rápido.'; })
          .catch(function (e) { stTxt.textContent = e.message; });
      }
      function menuEm(x, y, itens) {
        fecharMenu(); var rc = card.getBoundingClientRect();
        menu = el('div', 'pc-menu'); menu.dataset.b = 'ctx';
        itens.forEach(function (it) {
          if (it === '-') { menu.appendChild(el('hr')); return; }
          var d = el('div'); d.appendChild(el('span', 'pc-ok')); if (it.ic) d.appendChild(svg(it.ic, 15)); d.appendChild(el('span', null, it.txt));
          d.onclick = function () { fecharMenu(); it.f(); }; menu.appendChild(d);
        });
        card.appendChild(menu);
        var w = menu.offsetWidth, h = menu.offsetHeight;
        menu.style.left = Math.min(x - rc.left, rc.width - w - 6) + 'px'; menu.style.top = Math.min(y - rc.top, rc.height - h - 6) + 'px';
      }
      function menuItem(i, e) {
        var it = [];
        if (i.pasta || entraEm(i)) {
          it.push({ ic: 'pasta', txt: 'Abrir', f: function () { ir(i.caminho); } });
          if (i.pasta) it.push(fixada(i.caminho) ? { ic: 'pin', txt: 'Desafixar do Acesso rápido', f: function () { fixar(i.caminho, true); } } : { ic: 'pin', txt: 'Fixar no Acesso rápido', f: function () { fixar(i.caminho); } });
        } else {
          it.push({ ic: 'abrir', txt: estado.sel.length > 1 ? 'Abrir os ' + estado.sel.length + ' selecionados' : 'Abrir', f: confirmar });
          if (op.multiple) it.push({ ic: 'ok', txt: 'Selecionar todos (Ctrl + A)', f: function () { estado.sel = ultimaLista.filter(function (x) { return !entraEm(x); }).map(function (x) { return x.caminho; }); atualizarSel(); } });
        }
        it.push('-', { ic: 'copiar', txt: 'Copiar caminho', f: function () { copiar(i.caminho); } }, { ic: 'explorador', txt: 'Mostrar no Explorador', f: function () { api('explorador', { caminho: i.caminho }).catch(function (x) { stTxt.textContent = x.message; }); } });
        menuEm(e.clientX, e.clientY, it);
      }
      function entraEm(i) { return i.pasta || (i.pacote && (filtro ? filtro.split(',') : []).indexOf(ext(i.nome)) < 0); }
      function escolher(i, v, e) {
        if (entraEm(i)) { estado.sel = []; estado.foco = i.caminho; atualizarSel(); return; }
        estado.foco = i.caminho;
        if (op.multiple && e && (e.ctrlKey || e.metaKey)) {
          var k = estado.sel.indexOf(i.caminho); if (k >= 0) estado.sel.splice(k, 1); else estado.sel.push(i.caminho);
        } else if (op.multiple && e && e.shiftKey && estado.ancora) {
          var arq = v.filter(function (x) { return !entraEm(x); }).map(function (x) { return x.caminho; });
          var a = arq.indexOf(estado.ancora), b = arq.indexOf(i.caminho);
          if (a >= 0 && b >= 0) estado.sel = arq.slice(Math.min(a, b), Math.max(a, b) + 1);
        } else { estado.sel = [i.caminho]; estado.ancora = i.caminho; }
        if (!(e && e.shiftKey)) estado.ancora = i.caminho;
        atualizarSel();
      }
      function desenhar() {
        lista.innerHTML = '';
        var v = visiveis(); ultimaLista = v;
        var comFiltro = Object.keys(estado.filtros).some(function (k) { return estado.filtros[k] && estado.filtros[k].length; });
        if (!v.length) lista.appendChild(el('div', 'pc-vazio', estado.busca ? 'Nada encontrado com "' + estado.busca + '".' : comFiltro ? 'Nenhum item corresponde aos filtros marcados nas colunas.' : 'Esta pasta está vazia ou não tem arquivos dos tipos aceitos.'));
        var grupos = [];
        if (estado.agrupar === 'nenhum' || !v.length) grupos = [{ k: '', t: '', itens: v }];
        else {
          var m = {};
          v.forEach(function (i) {
            var g = estado.agrupar === 'data' ? grupoData(i.modificado) : [0, tipoDe(i)];
            var k = g[1]; if (!m[k]) { m[k] = { k: k, ord: g[0], t: g[1], itens: [] }; grupos.push(m[k]); } m[k].itens.push(i);
          });
          grupos.sort(function (a, b) { return estado.agrupar === 'data' ? a.ord - b.ord : (a.t === 'Pasta de arquivos' ? -1 : b.t === 'Pasta de arquivos' ? 1 : a.t.localeCompare(b.t, 'pt-BR')); });
        }
        grupos.forEach(function (g) {
          if (g.t) {
            var h = el('div', 'pc-grupo' + (estado.fechados[g.k] ? ' fechado' : '')); h.appendChild(svg('chevron', 13)); h.appendChild(el('span', null, g.t)); h.appendChild(el('span', 'pc-gn', '(' + g.itens.length + ')'));
            h.onclick = function () { if (laco.arrastou) return; estado.fechados[g.k] = !estado.fechados[g.k]; desenhar(); }; lista.appendChild(h);
            if (estado.fechados[g.k]) return;
          }
          var gb = el('div', 'pc-gb'); g.itens.forEach(function (i) { gb.appendChild(linha(i, v)); }); lista.appendChild(gb);
        });
        [[hN, 'nome'], [hD, 'data'], [hTi, 'tipo'], [hT, 'tam']].forEach(function (p) { p[0].classList.toggle('on', estado.ordem === p[1]); p[0].classList.toggle('desc', estado.ordem === p[1] && estado.desc); });
        abaNome.textContent = estado.busca ? 'Pesquisa: ' + estado.busca : (estado.caminho.split(/[\\/]/).filter(Boolean).pop() || estado.caminho || 'PPCPM - ARQUIVOS');
        if (J) try { J.document.title = 'PPCPM - ARQUIVOS · ' + abaNome.textContent; } catch (e) { }
        montarMig(); atualizarSel();
      }
      function atualizarSel() {
        Array.prototype.forEach.call(lista.querySelectorAll('.pc-row'), function (r) { r.classList.toggle('sel', estado.sel.indexOf(r.dataset.c) >= 0 || (!estado.sel.length && r.dataset.c === estado.foco)); });
        bOk.disabled = bAbrirC.disabled = op.pasta ? !estado.caminho : !estado.sel.length;
        var n = estado.sel.length, v = ultimaLista, tot = 0;
        v.forEach(function (i) { if (estado.sel.indexOf(i.caminho) >= 0) tot += i.tamanho || 0; });
        nome.value = estado.sel.map(function (c) { return '"' + c.split(/[\\/]/).pop() + '"'; }).join(' ').replace(/^"([^"]*)"$/, '$1');
        stTxt.textContent = v.length + (v.length === 1 ? ' item' : ' itens') + (n ? '   |   ' + n + (n === 1 ? ' item selecionado' : ' itens selecionados') + (tot ? '  ' + fmtTam(tot) : '') : '');
        fundo.classList.toggle('com-sel', n > 0);
        if (op.pasta) { var fp = focoPasta(); nome.value = fp ? fp.nome : (estado.caminho.split(/[\\/]/).filter(Boolean).pop() || estado.caminho); }
        qtd.textContent = n + (n === 1 ? ' arquivo selecionado' : ' arquivos selecionados') + '  ✕';
        if (cbTodos) { var na = v.filter(function (i) { return !entraEm(i); }).length; cbTodos.innerHTML = ''; if (n && n === na) { cbTodos.appendChild(svg('ok', 12)); cbTodos.style.background = '#0b5cad'; cbTodos.style.borderColor = '#0b5cad'; } else { cbTodos.style.background = ''; cbTodos.style.borderColor = ''; } }
        var cf = focoPasta() ? focoPasta().caminho : estado.caminho, jaFix = cf && fixada(cf);
        bFav.title = (jaFix ? 'Desafixar ' : 'Fixar ') + (focoPasta() ? 'a pasta "' + focoPasta().nome + '"' : 'esta pasta') + (jaFix ? ' do' : ' no') + ' Acesso rápido (painel da esquerda e Explorador do Windows)';
        bFav.querySelector('.pc-tx').textContent = jaFix ? 'Desafixar' : 'Fixar';
        mostrarDet();
      }
      function mostrarDet() {
        if (!estado.det) return;
        det.innerHTML = '';
        var c = estado.sel[estado.sel.length - 1] || estado.foco, i = ultimaLista.filter(function (x) { return x.caminho === c; })[0];
        if (!i) { det.appendChild(el('div', 'pc-vazio', 'Selecione um arquivo para ver os detalhes.')); return; }
        var g = el('div', 'pc-dg'); g.appendChild(icone(i)); det.appendChild(g); det.appendChild(el('b', null, i.nome));
        var kv = el('div', 'pc-kv');
        [['Tipo', tipoDe(i)], ['Tamanho', i.pasta ? '' : fmtTam(i.tamanho)], ['Modificado', fmtData(i.modificado)], ['Local', i.caminho.slice(0, i.caminho.length - i.nome.length).replace(/[\\/]$/, '')]].forEach(function (p) { if (p[1]) { kv.appendChild(el('span', null, p[0])); kv.appendChild(el('span', null, p[1])); } });
        det.appendChild(kv);
      }
      function erro(msg) { lista.innerHTML = ''; lista.appendChild(el('div', 'pc-erro', msg)); stTxt.textContent = ''; }

      function ir(c, semHist) {
        estado.busca = null; busca.value = ''; estado.filtros = {}; marcarFiltros();
        lista.innerHTML = ''; lista.appendChild(el('div', 'pc-vazio', 'Abrindo pasta…'));
        api('listar', { caminho: c }).then(function (j) {
          if (!semHist && estado.caminho && estado.caminho !== j.caminho) { estado.atras.push(estado.caminho); estado.frente = []; }
          estado.caminho = j.caminho; estado.pai = j.pai; estado.itens = j.itens; estado.sel = []; estado.foco = null; estado.ancora = null;
          bSobe.disabled = !j.pai; bVolta.disabled = !estado.atras.length; bAvanca.disabled = !estado.frente.length; lsSet(chave, j.caminho);
          busca.placeholder = 'Pesquisar em ' + (j.caminho.split(/[\\/]/).filter(Boolean).pop() || j.caminho);
          desenhar(); marcarLado();
          if (j.cortado) stTxt.textContent += '   |   Pasta muito grande: mostrando os primeiros itens. Use a pesquisa.';
        }).catch(function (e) { erro(e.message + ' — confira o caminho ou se a unidade de rede está conectada.'); montarMig(); });
      }
      function procurar() {
        var t = busca.value.trim(); if (!t || !estado.caminho) return;
        lista.innerHTML = ''; lista.appendChild(el('div', 'pc-vazio', 'Procurando "' + t + '" em ' + estado.caminho + ' e subpastas…'));
        api('buscar', { caminho: estado.caminho, termo: t, filtro: estado.soAceitos ? filtro : '' }).then(function (j) {
          estado.busca = t; estado.itens = j.itens; estado.sel = []; desenhar();
          if (j.incompleta) stTxt.textContent += '   |   Busca parcial (pasta muito grande). Entre numa subpasta para refinar.';
        }).catch(function (e) { erro(e.message); });
      }
      function confirmar() {
        if (op.pasta) { var fp = focoPasta(), c = fp ? fp.caminho : estado.caminho; if (c) fechar({ pasta: c, nome: fp ? fp.nome : (c.split(/[\\/]/).filter(Boolean).pop() || c) }); return; }
        var cams = estado.sel.slice(); if (!cams.length) return;
        bOk.disabled = true; stTxt.textContent = 'Carregando ' + cams.length + (cams.length === 1 ? ' arquivo…' : ' arquivos…');
        Promise.all(cams.map(function (c) {
          return fetch(API + 'arquivo?caminho=' + encodeURIComponent(c), { cache: 'no-store', headers: CAB }).then(function (r) {
            if (!r.ok) return r.json().then(function (j) { throw new Error(j.erro || 'Não foi possível ler o arquivo.'); });
            var nm = decodeURIComponent(r.headers.get('X-Nome') || encodeURIComponent(c.split(/[\\/]/).pop()));
            var mod = +r.headers.get('X-Modificado') || Date.now();
            return r.blob().then(function (b) { var f = new File([b], nm, { type: b.type, lastModified: mod }); try { Object.defineProperty(f, 'ppcpmCaminho', { value: c }); } catch (e) { } return f; });
          });
        })).then(function (files) { fechar({ files: files }); })
          .catch(function (e) { bOk.disabled = false; stTxt.textContent = ''; W.alert('Não foi possível abrir o arquivo.\n' + e.message); });
      }
      function copiar(t) {
        if (!t) return;
        var ok = function () { stTxt.textContent = 'Caminho copiado: ' + t; };
        try { W.navigator.clipboard.writeText(t).then(ok, function () { W.prompt('Copie o caminho:', t); }); } catch (e) { W.prompt('Copie o caminho:', t); }
      }

      /* ----- botões e teclado ----- */
      bVolta.onclick = function () { if (!estado.atras.length) return; estado.frente.push(estado.caminho); ir(estado.atras.pop(), true); };
      bAvanca.onclick = function () { if (!estado.frente.length) return; estado.atras.push(estado.caminho); ir(estado.frente.pop(), true); };
      bSobe.onclick = function () { if (estado.pai) ir(estado.pai); };
      bAtual.onclick = function () { if (estado.caminho) ir(estado.caminho, true); };
      bCopiar.onclick = function () { copiar(estado.sel.length === 1 ? estado.sel[0] : (estado.foco || estado.caminho)); };
      bFav.onclick = function () { var c = focoPasta() ? focoPasta().caminho : estado.caminho; if (c) fixar(c, fixada(c)); };
      bExp.onclick = function () { var c = estado.sel.length === 1 ? estado.sel[0] : estado.caminho; if (c) api('explorador', { caminho: c }).catch(function (e) { stTxt.textContent = e.message; }); };
      busca.oninput = function () { if (!estado.busca) desenhar(); };
      busca.onkeydown = function (e) { if (e.key === 'Enter') { e.preventDefault(); procurar(); } else if (e.key === 'Escape' && (busca.value || estado.busca)) { e.preventDefault(); e.stopPropagation(); if (estado.busca) ir(estado.caminho, true); else { busca.value = ''; desenhar(); } } };
      tipoSel.onchange = function () { estado.soAceitos = tipoSel.value === '1'; desenhar(); };
      [[hN, 'nome'], [hD, 'data'], [hTi, 'tipo'], [hT, 'tam']].forEach(function (p) { p[0].onclick = function () { if (arrastouCol) { arrastouCol = false; return; } setOrdem(p[1]); }; });
      bCan.onclick = function () { fechar(null); };
      bWin.onclick = function () { fechar({ windows: true, deJanela: !!J }); };
      bOk.onclick = confirmar; bAbrirC.onclick = confirmar;
      function moverSel(passo) {
        var v = ultimaLista; if (!v.length) return;
        var atual = estado.sel[estado.sel.length - 1] || estado.foco, k = -1;
        v.forEach(function (i, n) { if (i.caminho === atual) k = n; });
        var nk = Math.max(0, Math.min(v.length - 1, k + passo)); escolher(v[nk], v, null);
        var r = lista.querySelector('.pc-row[data-c="' + (W.CSS && W.CSS.escape ? W.CSS.escape(v[nk].caminho) : v[nk].caminho.replace(/"/g, '\\"')) + '"]'); if (r) r.scrollIntoView({ block: 'nearest' });
      }
      function tecla(e) {
        var ed = D.activeElement === cam || D.activeElement === busca;
        if (e.key === 'Escape' && (D.activeElement === cam || (D.activeElement === busca && (busca.value || estado.busca)))) return;   // o campo trata o Esc
        if (e.key === 'Escape') { if (menu) { fecharMenu(); e.preventDefault(); return; } e.preventDefault(); e.stopPropagation(); fechar(null); }
        else if (e.key === 'F5') { e.preventDefault(); bAtual.onclick(); }
        else if (e.altKey && e.key === 'ArrowLeft') { e.preventDefault(); bVolta.onclick(); }
        else if (e.altKey && e.key === 'ArrowRight') { e.preventDefault(); bAvanca.onclick(); }
        else if (ed) return;
        else if (e.key === 'Enter') {
          e.preventDefault();
          if (estado.sel.length || op.pasta && !focoPasta()) confirmar();
          else { var f = ultimaLista.filter(function (i) { return i.caminho === estado.foco; })[0]; if (f && entraEm(f)) ir(f.caminho); }
        }
        else if (e.key === 'Backspace' && estado.pai) { e.preventDefault(); ir(estado.pai); }
        else if (e.key === 'ArrowDown') { e.preventDefault(); moverSel(1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); moverSel(-1); }
        else if ((e.ctrlKey || e.metaKey) && (e.key === 'a' || e.key === 'A') && op.multiple) { e.preventDefault(); estado.sel = ultimaLista.filter(function (i) { return !entraEm(i); }).map(function (i) { return i.caminho; }); atualizarSel(); }
        else if ((e.ctrlKey || e.metaKey) && (e.key === 'l' || e.key === 'L')) { e.preventDefault(); editarCaminho(); }
        else if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'e' || e.key === 'F' || e.key === 'E')) { e.preventDefault(); busca.focus(); }
      }
      D.addEventListener('keydown', tecla, true);
      D.addEventListener('pointerdown', fecharMenuFora, true);
      D.addEventListener('pointermove', lacoMover); D.addEventListener('pointerup', lacoSoltar);

      (D.body || D.documentElement).appendChild(fundo);
      aplicarVista();
      // fechou a janela pelo X do Windows: cancela
      var vigia = setInterval(function () { if (J && J.closed) fechar(null); }, 400);

      /* ----- tamanho e posição: a janela abre no tamanho que o usuário deixou da última vez ----- */
      var MINW = 560, MINH = 380, CHAVE_JANELA = 'ppcpm:pc:janela', geo, maxi = false;
      function vw() { return fundo.clientWidth; } function vh() { return fundo.clientHeight; }
      function padrao() { var w = Math.min(1100, vw() - 28), h = Math.min(680, vh() - 28); return { w: w, h: h, x: (vw() - w) / 2, y: (vh() - h) / 2 }; }
      function aplicar() {
        var g = maxi ? { x: 0, y: 0, w: vw(), h: vh() } : geo;
        if (!maxi) {
          g.w = Math.max(Math.min(MINW, vw()), Math.min(g.w, vw())); g.h = Math.max(Math.min(MINH, vh()), Math.min(g.h, vh()));
          g.x = Math.min(Math.max(0, g.x), vw() - g.w); g.y = Math.min(Math.max(0, g.y), vh() - g.h);
        }
        card.style.left = g.x + 'px'; card.style.top = g.y + 'px'; card.style.width = g.w + 'px'; card.style.height = g.h + 'px';
        card.classList.toggle('max', maxi); card.classList.toggle('estreita', g.w < 760);
        bMax.innerHTML = ''; bMax.appendChild(svg(maxi ? 'restaurar' : 'maximizar', 14));
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
      bX.onclick = bAbaX.onclick = function () { fechar(null); };
      function ajustarTela() { aplicar(); }
      W.addEventListener('resize', ajustarTela);
      if (J) { ctl.style.display = 'none'; try { J.focus(); } catch (e) { } }

      montarLado();
      var inicio = lsGet(chave) || lsGet('ppcpm:pc:ultima:*') || (LOCAIS && LOCAIS.pastas[0] && LOCAIS.pastas[0].caminho) || (LOCAIS && LOCAIS.unidades[0] && LOCAIS.unidades[0].caminho) || '';
      if (inicio) ir(inicio); else { erro('Nenhuma pasta encontrada. Clique no caminho acima e cole o endereço da pasta.'); montarMig(); }
      // atualiza unidades/favoritos (pendrive ou rede pode ter conectado agora)
      api('locais').then(function (j) { LOCAIS = j; montarLado(); }).catch(function () { });
      setTimeout(function () { lista.focus(); }, 0);
    }); });
  }

  /* ---------- PASTA LOCAL: o mesmo "objeto de pasta" do Chrome (showDirectoryPicker), mas lido pelo Python deste PC.
     Assim os programas (ex.: Agrupador | Base) leem pastas e .zip sem o aviso "Permitir que este site veja e copie arquivos?". */
  var GRANDE = 80 * 1024 * 1024;   // acima disso o arquivo é lido por partes (índice de .zip grandes)
  function urlArq(c) { return API + 'arquivo?caminho=' + encodeURIComponent(c); }
  function trecho(c, a, b) { return fetch(API + 'trecho?caminho=' + encodeURIComponent(c) + '&ini=' + a + '&fim=' + b, { cache: 'no-store', headers: CAB }).then(function (r) { if (!r.ok) throw new Error('Não foi possível ler ' + c); return r.arrayBuffer(); }); }
  function PedacoArq(c, a, b, tipo) { this._c = c; this._a = a; this._b = b; this.size = Math.max(0, b - a); this.type = tipo || ''; }
  PedacoArq.prototype.slice = function (a, b) { a = a == null ? 0 : a < 0 ? this.size + a : a; b = b == null ? this.size : b < 0 ? this.size + b : Math.min(b, this.size); return new PedacoArq(this._c, this._a + a, this._a + Math.max(a, b)); };
  PedacoArq.prototype.arrayBuffer = function () { return trecho(this._c, this._a, this._b); };
  PedacoArq.prototype.text = function () { return this.arrayBuffer().then(function (b) { return new TextDecoder().decode(b); }); };
  PedacoArq.prototype.stream = function () { var self = this; return new ReadableStream({ start: function (ctl) { self.arrayBuffer().then(function (b) { ctl.enqueue(new Uint8Array(b)); ctl.close(); }, function (e) { ctl.error(e); }); } }); };
  function ArqLocal(i) { this.kind = 'file'; this.name = i.nome; this._i = i; this._c = i.caminho; }
  ArqLocal.prototype.getFile = function () {
    var i = this._i;
    if ((i.tamanho || 0) > GRANDE && !/\.zip[\\/]/i.test(i.caminho)) {   // arquivo enorme: entrega "preguiçoso" (lê só os pedaços pedidos)
      var p = new PedacoArq(i.caminho, 0, i.tamanho, ''); p.name = i.nome; p.lastModified = (i.modificado || 0) * 1000; return Promise.resolve(p);
    }
    return fetch(urlArq(i.caminho), { cache: 'no-store', headers: CAB }).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.erro || 'Não foi possível ler o arquivo.'); });
      return r.blob().then(function (b) { var f = new File([b], i.nome, { type: b.type, lastModified: (i.modificado || 0) * 1000 || Date.now() }); try { Object.defineProperty(f, 'ppcpmCaminho', { value: i.caminho }); } catch (e) { } return f; });
    });
  };
  ArqLocal.prototype.queryPermission = ArqLocal.prototype.requestPermission = function () { return Promise.resolve('granted'); };
  ArqLocal.prototype.isSameEntry = function (o) { return Promise.resolve(!!o && o._c === this._c); };
  function PastaLocal(c, nome) { this.kind = 'directory'; this.name = nome || c.split(/[\\/]/).filter(Boolean).pop() || c; this._c = c; this._itens = null; this.ppcpmCaminho = c; }
  PastaLocal.prototype._listar = function () {
    var self = this;
    if (!self._itens) self._itens = api('listar', { caminho: self._c, todos: 1 }).then(function (j) { return j.itens; }).catch(function (e) { self._itens = null; throw e; });
    return self._itens;
  };
  PastaLocal.prototype._filho = function (i) { return i.pasta ? new PastaLocal(i.caminho, i.nome) : new ArqLocal(i); };
  PastaLocal.prototype.entries = function () {
    var self = this, lista = null, k = 0;
    var it = { next: function () { return (lista ? Promise.resolve(lista) : self._listar().then(function (l) { lista = l; return l; })).then(function (l) { if (k >= l.length) return { done: true, value: undefined }; var i = l[k++]; return { done: false, value: [i.nome, self._filho(i)] }; }); } };
    it[Symbol.asyncIterator] = function () { return it; };
    return it;
  };
  PastaLocal.prototype.values = function () { var e = this.entries(), it = { next: function () { return e.next().then(function (r) { return r.done ? r : { done: false, value: r.value[1] }; }); } }; it[Symbol.asyncIterator] = function () { return it; }; return it; };
  PastaLocal.prototype.keys = function () { var e = this.entries(), it = { next: function () { return e.next().then(function (r) { return r.done ? r : { done: false, value: r.value[0] }; }); } }; it[Symbol.asyncIterator] = function () { return it; }; return it; };
  PastaLocal.prototype[Symbol.asyncIterator] = function () { return this.entries(); };
  PastaLocal.prototype._achar = function (nome, pasta) {
    var self = this;
    return self._listar().then(function (l) {
      var i = l.filter(function (x) { return x.nome === nome; })[0] || l.filter(function (x) { return x.nome.toLowerCase() === String(nome).toLowerCase(); })[0];
      if (!i || !!i.pasta !== pasta) throw new DOMException('"' + nome + '" não encontrado em ' + self._c, i ? 'TypeMismatchError' : 'NotFoundError');
      return self._filho(i);
    });
  };
  PastaLocal.prototype.getDirectoryHandle = function (n, o) { if (o && o.create) return Promise.reject(new DOMException('Pasta do PC aberta só para leitura.', 'NotAllowedError')); return this._achar(n, true); };
  PastaLocal.prototype.getFileHandle = function (n, o) { if (o && o.create) return Promise.reject(new DOMException('Pasta do PC aberta só para leitura.', 'NotAllowedError')); return this._achar(n, false); };
  PastaLocal.prototype.queryPermission = function (o) { return Promise.resolve(o && o.mode === 'readwrite' ? 'denied' : 'granted'); };
  PastaLocal.prototype.requestPermission = PastaLocal.prototype.queryPermission;
  PastaLocal.prototype.isSameEntry = function (o) { return Promise.resolve(!!o && o._c === this._c); };
  PastaLocal.prototype.resolve = function (o) { if (!o || !o._c || o._c.indexOf(this._c) !== 0) return Promise.resolve(null); return Promise.resolve(o._c.slice(this._c.length).split(/[\\/]/).filter(Boolean)); };
  PastaLocal.prototype.removeEntry = function () { return Promise.reject(new DOMException('Pasta do PC aberta só para leitura.', 'NotAllowedError')); };

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
    if (temaClaro()) f.classList.add('claro');
    var c = el('div'); c.style.cssText = 'position:absolute;left:50%;top:40%;transform:translate(-50%,-50%);background:var(--painel);color:var(--texto);border:1px solid var(--borda);border-radius:10px;box-shadow:0 18px 55px rgba(0,0,0,.45);padding:18px 20px;display:flex;flex-direction:column;gap:12px;align-items:center;min-width:320px';
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

  // 4) programas que pedem uma PASTA (showDirectoryPicker): abre a PPCPM - ARQUIVOS no modo pasta
  //    e entrega a pasta lida pelo Python — sem o aviso de permissão do Chrome. (Gravar na pasta continua pelo Chrome.)
  if (typeof window.showDirectoryPicker === 'function') {
    var origDir = window.showDirectoryPicker.bind(window);
    window.showDirectoryPicker = function (o) {
      o = o || {};
      if (!ativo || aberto || o.mode === 'readwrite') return origDir(o);
      return abrirSeletor({ pasta: true }).then(function (r) {
        if (!r) throw new DOMException('Cancelado', 'AbortError');
        if (r.windows) return r.deJanela ? new Promise(function (ok, erro) { comClique(function () { origDir(o).then(ok, erro); }); }) : origDir(o);
        return new PastaLocal(r.pasta, r.nome);
      });
    };
  }
  window.PPCPM_PASTA = function (caminho, nome) { return new PastaLocal(caminho, nome); };

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
