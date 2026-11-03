/* =====================================================================
   SISTEMA PPCPM — PONTE PYTHON ⇄ PROGRAMAS (só na versão Python)
   Liga todos os programas PPCP às pastas do computador:
   toda vez que um programa pede um arquivo (Análise DBF, Agrupador,
   Validação de Peso, Etiquetas...), abre o seletor "ARQUIVOS DO PC"
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
  }).then(function (j) { LOCAIS = j; ativo = true; }).catch(function () { ativo = false; });

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
    if (/^\.(xlsx|xlsm|xls|xlsb|ods)$/.test(e)) return '#1d7a44';
    if (e === '.dbf') return '#c46a0c'; if (e === '.csv') return '#0f8a8a'; if (e === '.pdf') return '#c62828';
    if (/^\.(zpl|prn|txt)$/.test(e)) return '#555c6b'; if (/^\.(html?|json)$/.test(e)) return '#6a3fb5';
    return '#7b8494';
  }
  function icone(item) {
    var s = item.pasta
      ? '<svg width="18" height="18" viewBox="0 0 24 24"><path fill="#e8a31a" d="M3 6a2 2 0 0 1 2-2h4.2l2 2H19a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24"><path fill="' + corExt(ext(item.nome)) + '" d="M6 2h8l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path fill="#fff" opacity=".55" d="M14 2v5h5z"/></svg>';
    var w = el('span', 'pc-ic'); w.innerHTML = s; return w;
  }

  /* ---------- visual (padrão do sistema: Arial negrito, #0b5cad) ---------- */
  function estilo() {
    if (document.getElementById('ppcpm-pc-css')) return;
    var c = el('style'); c.id = 'ppcpm-pc-css';
    c.textContent = [
      '#ppcpm-pc{position:fixed;inset:0;z-index:2147483000;background:rgba(5,10,25,.55);display:flex;align-items:center;justify-content:center;padding:14px;font:600 13px Arial,Helvetica,sans-serif;color:#1a2233}',
      '#ppcpm-pc *{box-sizing:border-box;font-family:Arial,Helvetica,sans-serif}',
      '#ppcpm-pc .pc-card{background:#fff;border:1px solid #000;border-radius:12px;box-shadow:0 18px 55px rgba(0,0,0,.4);width:min(1040px,100%);height:min(640px,100%);display:flex;flex-direction:column;overflow:hidden}',
      '#ppcpm-pc .pc-top{display:flex;align-items:center;gap:12px;padding:14px 18px 10px;border-bottom:1px solid #e3e7ee}',
      '#ppcpm-pc .pc-top b{font-size:15px;font-weight:700;color:#1f2547;letter-spacing:.3px}',
      '#ppcpm-pc .pc-tipos{margin-left:auto;color:#5b6474;font-size:12px}',
      '#ppcpm-pc button{font:700 13px Arial,Helvetica,sans-serif;border-radius:7px;padding:7px 12px;cursor:pointer;border:1px solid #c5cbd6;background:#f2f4f6;color:#1f2937;white-space:nowrap}',
      '#ppcpm-pc button:hover{background:#e6eaf0}',
      '#ppcpm-pc button.pc-pri{background:#0b5cad;border-color:#0b5cad;color:#fff}',
      '#ppcpm-pc button.pc-pri:hover{background:#1a6dc0}',
      '#ppcpm-pc button:disabled{opacity:.5;cursor:default}',
      '#ppcpm-pc .pc-barra{display:flex;gap:8px;padding:10px 18px;border-bottom:1px solid #e3e7ee;background:#f7f8fa}',
      '#ppcpm-pc input[type=text]{flex:1;min-width:0;border:1px solid #c5cbd6;border-radius:7px;padding:7px 10px;font:600 13px Arial,Helvetica,sans-serif;color:#1a2233;background:#fff}',
      '#ppcpm-pc input[type=text]:focus{outline:2px solid #0b5cad55;border-color:#0b5cad}',
      '#ppcpm-pc .pc-corpo{flex:1;display:flex;min-height:0}',
      '#ppcpm-pc .pc-lado{width:230px;border-right:1px solid #e3e7ee;overflow:auto;padding:8px 0;background:#fafbfc}',
      '#ppcpm-pc .pc-sec{padding:10px 16px 4px;font-size:11px;color:#6b7383;text-transform:uppercase;letter-spacing:.5px}',
      '#ppcpm-pc .pc-loc{display:flex;align-items:center;gap:8px;padding:6px 16px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '#ppcpm-pc .pc-loc:hover{background:#e8f0fb}',
      '#ppcpm-pc .pc-loc.on{background:#dbe8f8;color:#0b5cad}',
      '#ppcpm-pc .pc-loc .pc-x{margin-left:auto;color:#a33;opacity:0;font-size:14px}',
      '#ppcpm-pc .pc-loc:hover .pc-x{opacity:1}',
      '#ppcpm-pc .pc-main{flex:1;display:flex;flex-direction:column;min-width:0}',
      '#ppcpm-pc .pc-ferr{display:flex;gap:10px;align-items:center;padding:10px 14px}',
      '#ppcpm-pc .pc-ferr label{display:flex;gap:6px;align-items:center;white-space:nowrap;color:#3d4554;cursor:pointer}',
      '#ppcpm-pc .pc-cab,#ppcpm-pc .pc-row{display:grid;grid-template-columns:28px 1fr 150px 90px;gap:8px;align-items:center;padding:6px 14px}',
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
      '@media (max-width:720px){#ppcpm-pc .pc-lado{display:none}#ppcpm-pc .pc-cab,#ppcpm-pc .pc-row{grid-template-columns:28px 1fr 80px}#ppcpm-pc .pc-d{display:none}}'
    ].join('\n');
    (document.head || document.documentElement).appendChild(c);
  }

  /* ---------- seletor ---------- */
  function abrirSeletor(op) {
    op = op || {};
    var filtro = filtroDe(op.accept);
    var chave = 'ppcpm:pc:ultima:' + (filtro || '*');
    return new Promise(function (resolve) {
      estilo(); aberto = true;
      var estado = { caminho: '', pai: '', itens: [], sel: [], ordem: lsGet('ppcpm:pc:ordem') || 'nome', soAceitos: !!filtro, busca: null };

      var fundo = el('div'); fundo.id = 'ppcpm-pc'; fundo.setAttribute('role', 'dialog'); fundo.setAttribute('aria-modal', 'true');
      var card = el('div', 'pc-card'); fundo.appendChild(card);

      var top = el('div', 'pc-top'); top.appendChild(el('b', null, 'SISTEMA PPCPM - ARQUIVOS DO PC'));
      top.appendChild(el('span', 'pc-tipos', filtro ? 'Tipos aceitos: ' + filtro.split(',').join(', ') : 'Qualquer arquivo'));
      card.appendChild(top);

      var barra = el('div', 'pc-barra');
      var bSobe = el('button', null, '↑'); bSobe.title = 'Pasta acima';
      var cam = el('input'); cam.type = 'text'; cam.placeholder = 'Cole aqui o caminho copiado do Explorador (ex.: G:\\Meu Drive\\PCP) e aperte Enter';
      var bIr = el('button', null, 'Ir');
      var bFav = el('button', null, '★ Favoritar');
      var bExp = el('button', null, 'Abrir no Explorador');
      [bSobe, cam, bIr, bFav, bExp].forEach(function (x) { barra.appendChild(x); });
      card.appendChild(barra);

      var corpo = el('div', 'pc-corpo'); card.appendChild(corpo);
      var lado = el('aside', 'pc-lado'); corpo.appendChild(lado);
      var main = el('section', 'pc-main'); corpo.appendChild(main);
      var ferr = el('div', 'pc-ferr');
      var busca = el('input'); busca.type = 'text'; busca.placeholder = 'Filtrar nesta pasta… (Enter procura também nas subpastas)';
      var lbl = el('label'); var chk = el('input'); chk.type = 'checkbox'; chk.checked = estado.soAceitos; chk.disabled = !filtro;
      lbl.appendChild(chk); lbl.appendChild(document.createTextNode('Só tipos aceitos'));
      ferr.appendChild(busca); ferr.appendChild(lbl); main.appendChild(ferr);
      var cab = el('div', 'pc-cab');
      cab.appendChild(el('span'));
      var hN = el('span', null, 'Nome'), hD = el('span', 'pc-d', 'Modificado'), hT = el('span', null, 'Tamanho');
      hT.style.textAlign = 'right'; [hN, hD, hT].forEach(function (h) { cab.appendChild(h); }); main.appendChild(cab);
      var lista = el('div', 'pc-lista'); lista.tabIndex = 0; main.appendChild(lista);

      var rod = el('div', 'pc-rod');
      var info = el('span', 'pc-info', '');
      var bWin = el('button', null, 'Janela do Windows'); bWin.title = 'Usar a janela comum de abrir arquivo';
      var bCan = el('button', null, 'Cancelar');
      var bOk = el('button', 'pc-pri', op.multiple ? 'Abrir selecionados' : 'Abrir arquivo'); bOk.disabled = true;
      [info, bWin, bCan, bOk].forEach(function (x) { rod.appendChild(x); });
      card.appendChild(rod);

      function fechar(resultado) {
        aberto = false; document.removeEventListener('keydown', tecla, true); fundo.remove(); resolve(resultado);
      }

      /* ----- painel da esquerda ----- */
      function locItem(nome, caminho, tipo, remover) {
        var d = el('div', 'pc-loc'); d.title = caminho;
        d.appendChild(icone({ pasta: true, nome: '' })); d.appendChild(el('span', null, nome));
        if (remover) {
          var x = el('span', 'pc-x', '✕'); x.title = 'Tirar dos favoritos';
          x.onclick = function (e) { e.stopPropagation(); api('favorito', { caminho: caminho, remover: 1 }).then(function (j) { LOCAIS = j; montarLado(); }); };
          d.appendChild(x);
        }
        d.onclick = function () { ir(caminho); };
        d.dataset.c = caminho; return d;
      }
      function montarLado() {
        lado.innerHTML = '';
        var L = LOCAIS || { unidades: [], pastas: [], favoritos: [], recentes: [] };
        function sec(t, arr, rem) {
          if (!arr.length) return; lado.appendChild(el('div', 'pc-sec', t));
          arr.forEach(function (a) { lado.appendChild(typeof a === 'string' ? locItem(a.split(/[\\/]/).filter(Boolean).pop() || a, a, 'r') : locItem(a.nome, a.caminho, a.tipo, rem)); });
        }
        sec('Favoritos', L.favoritos, true);
        sec('Este computador', L.pastas.concat(L.unidades));
        sec('Recentes', L.recentes);
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
          if (!i.pasta && estado.soAceitos && aceitos.length && aceitos.indexOf(ext(i.nome)) < 0) return false;
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
          r.title = i.caminho;
          r.onclick = function (e) {
            if (i.pasta) { estado.sel = []; atualizarSel(); r.classList.add('sel'); return; }
            if (op.multiple && (e.ctrlKey || e.metaKey)) {
              var k = estado.sel.indexOf(i.caminho); if (k >= 0) estado.sel.splice(k, 1); else estado.sel.push(i.caminho);
            } else if (op.multiple && e.shiftKey && estado.sel.length) {
              var arq = v.filter(function (x) { return !x.pasta; }).map(function (x) { return x.caminho; });
              var a = arq.indexOf(estado.sel[estado.sel.length - 1]), b = arq.indexOf(i.caminho);
              estado.sel = arq.slice(Math.min(a, b), Math.max(a, b) + 1);
            } else estado.sel = [i.caminho];
            atualizarSel();
          };
          r.ondblclick = function () { if (i.pasta) ir(i.caminho); else { estado.sel = [i.caminho]; confirmar(); } };
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
          .catch(function (e) { bOk.disabled = false; info.textContent = ''; window.alert('Não foi possível abrir o arquivo.\n' + e.message); });
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
      bWin.onclick = function () { fechar({ windows: true }); };
      bOk.onclick = confirmar;
      fundo.addEventListener('mousedown', function (e) { if (e.target === fundo) fechar(null); });
      function tecla(e) {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); fechar(null); }
        else if (e.key === 'Enter' && document.activeElement !== cam && document.activeElement !== busca && estado.sel.length) { e.preventDefault(); confirmar(); }
        else if (e.key === 'Backspace' && document.activeElement !== cam && document.activeElement !== busca && estado.pai) { e.preventDefault(); ir(estado.pai); }
      }
      document.addEventListener('keydown', tecla, true);

      (document.body || document.documentElement).appendChild(fundo);
      montarLado();
      var inicio = lsGet(chave) || lsGet('ppcpm:pc:ultima:*') || (LOCAIS && LOCAIS.pastas[0] && LOCAIS.pastas[0].caminho) || (LOCAIS && LOCAIS.unidades[0] && LOCAIS.unidades[0].caminho) || '';
      if (inicio) ir(inicio); else erro('Nenhuma pasta encontrada. Cole o caminho acima.');
      // atualiza unidades/favoritos (pendrive ou rede pode ter conectado agora)
      api('locais').then(function (j) { LOCAIS = j; montarLado(); }).catch(function () { });
      setTimeout(function () { lista.focus(); }, 0);
    });
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
  function usarSeletor(input) {
    return ativo && !aberto && !bypass && input && input.type === 'file' && !input.disabled && !input.webkitdirectory && !input.hasAttribute('webkitdirectory') && !input.hasAttribute('data-ppcpm-windows');
  }
  function viaSeletor(input) {
    abrirSeletor({ accept: input.accept, multiple: input.multiple }).then(function (r) {
      if (!r) return;
      if (r.windows) return janelaWindows(input);
      entregar(input, r.files);
    });
  }

  // 1) programas que abrem a janela com input.click() (a maioria)
  var origClick = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function () {
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
        if (r.windows) return origPicker(o);
        return r.files.map(function (f) {
          return { kind: 'file', name: f.name, getFile: function () { return Promise.resolve(f); },
            queryPermission: function () { return Promise.resolve('granted'); }, requestPermission: function () { return Promise.resolve('granted'); },
            isSameEntry: function (x) { return Promise.resolve(x === this); } };
        });
      });
    };
  }

  // Para os próximos programas em Python: window.PPCPM_PC.abrir({accept:'.dbf', multiple:true})
  window.PPCPM_PC = { abrir: function (o) { return abrirSeletor(o).then(function (r) { return r && r.files ? r.files : []; }); }, ativo: function () { return ativo; } };
})();
