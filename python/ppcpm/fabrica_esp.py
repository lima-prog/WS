"""
PREPARAÇÃO FÁBRICA · ESPELHAR DXF (peças xadrez) — dentro da aba do sistema.
Lógica do app original (apps/Espelhar_DXF/espelhar/processador.py, mirror.py e dxf_util/preview.py), sem alteração.
O processador original espera a tela por QEventLoop/QTimer (pausa da visualização): aqui a pausa é um sleep na
linha de execução do processamento, e o desenho antes/depois é feito no navegador.
"""
from __future__ import annotations

import threading
import time

from . import fabrica_apps as FA

PASTA = "Espelhar_DXF"
MODS = ["dxf_util.preview", "espelhar.mirror", "espelhar.processador"]
_S = {"pasta": "", "rodando": False, "log": [], "status": "Aguardando processamento…", "progresso": 0,
      "historico": [], "fim": None, "id": 0, "vis": True, "vel": 1200}


def _m():
    m = FA.carregar(PASTA, MODS)
    p = m["espelhar.processador"]
    if not getattr(p, "_ppcpm_sem_qt", False):
        espera = [0]

        class _Loop:
            def quit(self):
                pass

            def exec_(self):
                time.sleep(max(0, espera[0]) / 1000)

        class _Timer:
            @staticmethod
            def singleShot(ms, _fn=None):
                espera[0] = ms

        p.QEventLoop, p.QTimer = _Loop, _Timer
        p._ppcpm_sem_qt = True
    return m


class _Tela:
    def atualizar_progresso(self, atual, total):
        _S["progresso"] = int(atual / total * 100) if total else 0

    def atualizar_status(self, msg):
        _S["status"] = msg

    def adicionar_log(self, msg):
        _S["log"].extend(str(msg).split("\n"))

    def visualizacao_habilitada(self):
        return _S["vis"]

    def velocidade_visualizacao(self):
        return _S["vel"]

    def mostrar_resultado(self, antes, depois, nome, avisos):
        _S["historico"].append({"antes": antes, "depois": depois, "nome": nome, "avisos": sorted(set(avisos or []))})
        _S["id"] += 1


def estado(desde: int = 0) -> dict:
    lg = _S["log"]
    desde = max(0, min(desde, len(lg)))
    return FA.limpo({"ok": True, "pasta": _S["pasta"], "rodando": _S["rodando"], "log": lg[desde:], "n": len(lg),
                     "status": _S["status"], "progresso": _S["progresso"], "n_hist": len(_S["historico"]),
                     "fim": _S["fim"], "id": _S["id"], "vis": _S["vis"], "vel": _S["vel"],
                     "subpasta": _m()["espelhar.mirror"].SUBPASTA_ESPELHADAS})


def preview(i: int) -> dict:
    h = _S["historico"]
    if not h:
        return {"ok": True, "vazio": True}
    i = max(0, min(i, len(h) - 1))
    return FA.limpo({"ok": True, "i": i, "total": len(h), **h[i]})


def espelhar(caminho: str, vis: bool, vel: int) -> dict:
    if _S["rodando"]:
        return {"ok": False, "erro": "Já tem um espelhamento em andamento."}
    c = FA.pasta_ok(caminho)
    if not c:
        return {"ok": False, "titulo": "Caminho inválido", "erro": "Por favor, informe um caminho de pasta válido."}
    m = _m()
    try:
        vel = max(100, min(10000, int(vel)))
    except (TypeError, ValueError):
        vel = 1200
    _S.update(pasta=c, rodando=True, log=[f"📁 Pasta: {c}"], historico=[], progresso=0, fim=None, vis=bool(vis), vel=vel,
              status="Espelhando…")
    _S["id"] += 1

    def trabalho():
        ok = False
        try:
            ok = m["espelhar.processador"].ProcessadorEspelhamento(_Tela()).processar_pasta(c)
        except Exception as e:  # noqa: BLE001
            _S["log"].append(f"❌ ERRO GERAL: {e}")
        finally:
            _S.update(rodando=False, progresso=100, fim={"ok": bool(ok)})
            _S["id"] += 1

    threading.Thread(target=trabalho, daemon=True).start()
    return estado()


def limpar() -> dict:
    if _S["rodando"]:
        return {"ok": False, "erro": "Aguarde o espelhamento terminar."}
    _S.update(pasta="", log=[], status="Aguardando processamento…", progresso=0, historico=[], fim=None)
    _S["id"] += 1
    return estado()


def get(acao: str, q: dict) -> dict:
    if acao == "disponivel":
        return FA.disponivel("pg17", PASTA, MODS)
    if acao == "estado":
        d = str(q.get("desde") or "0")
        return estado(int(d) if d.isdigit() else 0)
    if acao == "preview":
        i = str(q.get("i") or "0")
        return preview(int(i) if i.isdigit() else 0)
    return {"ok": False, "erro": "Ação desconhecida."}


def post(acao: str, d: dict) -> dict:
    if acao == "espelhar":
        return espelhar(str(d.get("caminho") or ""), bool(d.get("vis", True)), d.get("vel", 1200))
    if acao == "limpar":
        return limpar()
    return {"ok": False, "erro": "Ação desconhecida."}
