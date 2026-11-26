"""
PREPARAÇÃO FÁBRICA · CONVERSOR CAM → DXF (modo CORTE) — dentro da aba do sistema.
Lógica do app original (apps/Conversor_CAM_DXF/conversor/processador.py e utilitarios.py), sem alteração.
"""
from __future__ import annotations

import os
import threading

from . import fabrica_apps as FA

PASTA = "Conversor_CAM_DXF"
MODS = ["conversor.utilitarios", "conversor.processador"]
_S = {"pasta": "", "dados": {}, "status": "Aguardando...", "erros_leitura": 0, "rodando": False, "resultado": None, "id": 0}


def _m():
    return FA.carregar(PASTA, MODS)


class _Tela:
    """O processador do app chama aba.atualizar_status(msg) durante a leitura/conversão."""

    def atualizar_status(self, msg):
        _S["status"] = msg


def _obra(d):
    manual = (d.get("obra_manual") or "").strip()
    return manual if manual else _m()["conversor.utilitarios"].normalizar_obra(d.get("obra", ""))


def estado() -> dict:
    u = _m()["conversor.utilitarios"]
    linhas = []
    for arq, d in _S["dados"].items():
        linhas.append({"arquivo": arq, "posicao": d.get("posicao", ""), "comprimento": d.get("comprimento", ""),
                       "largura": d.get("largura", ""), "espessura": d.get("espessura", ""), "material": d.get("material", ""),
                       "quantidade": d.get("quantidade", ""), "obra": _obra(d), "obra_manual": bool((d.get("obra_manual") or "").strip()),
                       "tipo_cam": d.get("tipo_cam", "DESCONHECIDO"), "nome_dxf": u.nome_dxf(d)})
    return FA.limpo({"ok": True, "pasta": _S["pasta"], "linhas": linhas, "status": _S["status"], "rodando": _S["rodando"],
                     "erros_leitura": _S["erros_leitura"], "resultado": _S["resultado"], "id": _S["id"]})


def abrir(caminho: str) -> dict:
    c = FA.pasta_ok(caminho)
    if not c:
        return {"ok": False, "titulo": "Pasta não encontrada", "erro": f"Não encontrei essa pasta:\n\n{(caminho or '').strip()}"}
    proc = _m()["conversor.processador"].ProcessadorConversor(_Tela())
    dados, erros, total = proc.carregar_pasta(c)
    _S.update(pasta=c, dados=dados, erros_leitura=erros, resultado=None)
    _S["id"] += 1
    r = estado()
    r["total"] = total
    return r


def limpar() -> dict:
    _S.update(pasta="", dados={}, status="Aguardando...", erros_leitura=0, resultado=None)
    _S["id"] += 1
    return estado()


def editar_obra(arquivos: list, valor: str) -> dict:
    valor = (valor or "").strip()
    for a in arquivos or []:
        d = _S["dados"].get(a)
        if d is None:
            continue
        if valor:
            d["obra_manual"] = valor
        else:
            d.pop("obra_manual", None)
    _S["id"] += 1
    return estado()


def converter(arquivos: list, saida: str, subpastas: bool) -> dict:
    if _S["rodando"]:
        return {"ok": False, "erro": "Já tem uma conversão em andamento."}
    arquivos = [a for a in (arquivos or []) if a in _S["dados"]]
    if not arquivos:
        return {"ok": False, "titulo": "Atenção", "erro": "Selecione pelo menos uma peça."}
    from .caminhos import pasta_downloads
    s = FA.pasta_ok(pasta_downloads())          # V282: DXF convertidos vão sempre para a pasta Downloads
    if not s:
        return {"ok": False, "titulo": "Pasta não encontrada", "erro": f"Não encontrei a pasta de saída:\n\n{(saida or '').strip()}"}
    _S.update(rodando=True, resultado=None, status=f"Convertendo 0/{len(arquivos)}...")
    _S["id"] += 1

    def trabalho():
        try:
            proc = _m()["conversor.processador"].ProcessadorConversor(_Tela())
            ok, erros = proc.converter_arquivos(_S["pasta"], arquivos, _S["dados"], s, bool(subpastas))
            _S["resultado"] = {"sucesso": ok, "erros": erros, "pasta": s, "subpastas": bool(subpastas), "total": len(arquivos)}
            _S["status"] = f"Finalizado: {ok} de {len(arquivos)} DXF(s) criado(s)."
        except Exception as e:  # noqa: BLE001
            _S["resultado"] = {"sucesso": 0, "erros": [str(e)], "pasta": s, "subpastas": bool(subpastas), "total": len(arquivos)}
            _S["status"] = f"Erro: {e}"
        finally:
            _S["rodando"] = False
            _S["id"] += 1

    threading.Thread(target=trabalho, daemon=True).start()
    return estado()


def get(acao: str, q: dict) -> dict:
    if acao == "disponivel":
        return FA.disponivel("pg20", PASTA, MODS)
    if acao == "estado":
        return estado()
    return {"ok": False, "erro": "Ação desconhecida."}


def post(acao: str, d: dict) -> dict:
    if acao == "abrir":
        return abrir(str(d.get("caminho") or ""))
    if acao == "limpar":
        return limpar()
    if acao == "obra":
        return editar_obra(d.get("arquivos") or [], str(d.get("valor") or ""))
    if acao == "converter":
        return converter(d.get("arquivos") or [], str(d.get("saida") or ""), bool(d.get("subpastas", True)))
    return {"ok": False, "erro": "Ação desconhecida."}


# V287: devolve o trabalho que estava aberto antes do sistema reiniciar com a versão nova
try:
    from .sessao import devolver_fabrica as _devolver
    _devolver("cam", _S)
except Exception:  # noqa: BLE001
    pass
