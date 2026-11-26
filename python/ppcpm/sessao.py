"""
V287 — NÃO PERDER O TRABALHO QUANDO CHEGA VERSÃO NOVA.

Quando o pacote Python muda, o sistema reinicia sozinho. Antes de reiniciar, guardamos tudo o que o usuário
estava fazendo e, quando o sistema volta, devolvemos do jeito que estava:
  - abas de Produção (Agrupador, Impressão Casada, Multi obra, Grupo LIC, Fluxo 04): arquivos carregados,
    campos, listas, resultados, conferências e cartões;
  - apps da Preparação fábrica: pastas escolhidas, listas, resultados.
O arquivo fica só neste PC (dados_locais/sessao_antes_atualizar.pkl), é lido uma vez e apagado.
Só o próprio usuário apaga o trabalho (botões Atualizar / Limpar).
"""
from __future__ import annotations

import os
import pickle
import sys
import time
import types

from .config import PASTA_DADOS

ARQ = PASTA_DADOS / "sessao_antes_atualizar.pkl"
VALIDADE_SEG = 24 * 3600
_FABRICA = ("aud", "cam", "cor", "esp", "ren", "rot", "vis")
_SEM = ("rodando",)                 # nunca volta "rodando=True" (o trabalho em andamento não continua sozinho)


def _pode(v) -> bool:
    try:
        pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------ widgets da tela falsa (qtfalso)
def _item_lista(it) -> dict:
    d = {k: v for k, v in vars(it).items() if k != "lista"}
    if not _pode(d.get("dados")):
        d["dados"] = {}
    return d


def _item_arvore(it) -> dict:
    d = {k: v for k, v in vars(it).items() if k not in ("pai", "arvore", "filhos")}
    if not _pode(d.get("dados")):
        d["dados"] = {}
    d["filhos"] = [_item_arvore(f) for f in it.filhos]
    return d


def _widget(Q, w):
    d = w.__dict__
    base = {k: d[k] for k in ("_vis", "_ativo", "_dica", "_estilo") if k in d}
    if isinstance(w, Q.QTreeWidget):
        return dict(base, t="arvore", cab=list(w._cab), prof=d.get("_prof"),
                    itens=[_item_arvore(f) for f in w._raiz.filhos],
                    atual=Q.caminho_item(w._atual) if w._atual else None)
    if isinstance(w, Q.QTableWidget):
        return dict(base, t="tabela", lin=w._lin, col=w._col, cab=list(w._cab),
                    cel={k: _item_lista(v) for k, v in w._cel.items()})
    if isinstance(w, Q.QListWidget):
        return dict(base, t="lista", itens=[_item_lista(i) for i in w._itens], atual=w._atual)
    if isinstance(w, Q.QComboBox):
        its = [[t, x if _pode(x) else None] for t, x in w._itens]
        return dict(base, t="combo", itens=its, idx=w._idx)
    if hasattr(w, "cartoes") and isinstance(getattr(w, "cartoes"), dict):        # FaixaKPI
        return dict(base, t="kpis", cartoes={k: [c.lbl_valor._texto, c.lbl_valor.__dict__.get("_estilo", "")]
                                             for k, c in w.cartoes.items()})
    campos = {k: d[k] for k in ("_texto", "_marcado", "_valor") if k in d}
    if campos:
        return dict(base, t="simples", campos=campos)
    return None


def _volta_item_lista(Q, d, dono):
    it = Q.QListWidgetItem()
    for k, v in d.items():
        setattr(it, k, v)
    it.lista = dono
    return it


def _volta_item_arvore(Q, d, pai=None, arvore=None):
    it = Q.QTreeWidgetItem()
    for k, v in d.items():
        if k != "filhos":
            setattr(it, k, v)
    it.pai, it.arvore = pai, arvore
    it.filhos = [_volta_item_arvore(Q, f, it) for f in d.get("filhos", [])]
    return it


def _volta_widget(Q, w, j):
    d = w.__dict__
    for k in ("_vis", "_ativo", "_dica", "_estilo"):
        if k in j:
            d[k] = j[k]
    t = j.get("t")
    if t == "arvore" and isinstance(w, Q.QTreeWidget):
        d["_cab"] = j["cab"]
        d["_prof"] = j.get("prof")
        w._raiz.filhos = [_volta_item_arvore(Q, f, None, w) for f in j["itens"]]
        d["_atual"] = Q.item_por_caminho(w, j["atual"]) if j.get("atual") else None
    elif t == "tabela" and isinstance(w, Q.QTableWidget):
        d["_lin"], d["_col"], d["_cab"] = j["lin"], j["col"], j["cab"]
        d["_cel"] = {k: _volta_item_lista(Q, v, None) for k, v in j["cel"].items()}
    elif t == "lista" and isinstance(w, Q.QListWidget):
        d["_itens"] = [_volta_item_lista(Q, i, w) for i in j["itens"]]
        d["_atual"] = j["atual"]
    elif t == "combo" and isinstance(w, Q.QComboBox):
        d["_itens"] = j["itens"]
        d["_idx"] = j["idx"]
    elif t == "kpis" and hasattr(w, "cartoes"):
        for k, (txt, est) in j["cartoes"].items():
            c = w.cartoes.get(k)
            if c is not None:
                c.lbl_valor.__dict__["_texto"] = txt
                c.lbl_valor.__dict__["_estilo"] = est
                c.lbl_valor._tocar()
    elif t == "simples":
        d.update(j["campos"])
    w._tocar()


def _tela_producao():
    """{'widgets': {...}, 'dados': {...}} da tela de Produção (se já foi aberta)."""
    from .producao import motor
    win = motor._S.get("win")
    if win is None:
        return None
    Q = motor.Q
    widgets, dados = {}, {}
    for k, v in list(vars(win).items()):
        if isinstance(v, Q.QObject):
            try:
                j = _widget(Q, v)
                if j is not None and _pode(j):
                    widgets[k] = j
            except Exception:
                pass
        elif not callable(v) and not isinstance(v, (types.ModuleType, type)) and _pode(v):
            dados[k] = v
    return {"widgets": widgets, "dados": dados, "saida": motor._S.get("ultima_saida", "")}


def _apps_fabrica():
    saida = {}
    for a in _FABRICA:
        m = sys.modules.get(f"ppcpm.fabrica_{a}")
        S = getattr(m, "_S", None) if m else None
        if isinstance(S, dict):
            saida[a] = {k: v for k, v in S.items() if k not in _SEM and _pode(v)}
    return saida


# ------------------------------------------------------------------ guardar / devolver
def ha_trabalho_rodando() -> bool:
    try:
        from .producao import motor
        if motor._S.get("rodando", 0) > 0 or motor.Q.tarefas_rodando(None) > 0:
            return True
    except Exception:
        pass
    for a in _FABRICA:
        m = sys.modules.get(f"ppcpm.fabrica_{a}")
        if m is not None and isinstance(getattr(m, "_S", None), dict) and m._S.get("rodando"):
            return True
    return False


def esperar_trabalho(max_seg: int = 900) -> None:
    """Antes de reiniciar: espera terminar o que estiver rodando (ex.: gerando a Base), até 15 min."""
    fim = time.time() + max_seg
    while time.time() < fim and ha_trabalho_rodando():
        time.sleep(2)


def guardar() -> bool:
    try:
        pacote = {"quando": time.time(), "producao": _tela_producao(), "fabrica": _apps_fabrica()}
        ARQ.parent.mkdir(parents=True, exist_ok=True)
        tmp = ARQ.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            pickle.dump(pacote, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, ARQ)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[sessão] não consegui guardar o trabalho: {e}")
        return False


def _ler():
    if not ARQ.exists():
        return None
    try:
        with open(ARQ, "rb") as f:
            p = pickle.load(f)
        if time.time() - float(p.get("quando", 0)) > VALIDADE_SEG:
            return None
        return p
    except Exception:
        return None


_PENDENTE = {"p": None, "lido": False}


def _pendente():
    if not _PENDENTE["lido"]:
        _PENDENTE["lido"] = True
        _PENDENTE["p"] = _ler()
        try:
            ARQ.unlink()
        except Exception:
            pass
    return _PENDENTE["p"]


def devolver_producao(win, motor) -> bool:
    """Chamado logo depois de criar a tela de Produção."""
    p = _pendente()
    tela = (p or {}).get("producao")
    if not tela:
        return False
    Q = motor.Q
    for k, v in tela.get("dados", {}).items():
        try:
            setattr(win, k, v)
        except Exception:
            pass
    for k, j in tela.get("widgets", {}).items():
        w = getattr(win, k, None)
        if isinstance(w, Q.QObject):
            try:
                _volta_widget(Q, w, j)
            except Exception:
                pass
    if tela.get("saida"):
        motor._S["ultima_saida"] = tela["saida"]
    return True


def devolver_fabrica(app: str, S: dict) -> None:
    """Chamado quando um app da Preparação fábrica é carregado."""
    p = _pendente()
    d = ((p or {}).get("fabrica") or {}).get(app)
    if d:
        S.update(d)
