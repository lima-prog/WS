"""
PREPARAÇÃO FÁBRICA · CORTE INTELIGENTE — dentro da aba do sistema.
Lógica do app original (apps/Corte_Inteligente/corte/processador.py e nucleo/banco_dados.py), sem alteração.
O processador espera a tela por QEventLoop/QTimer (pausa da visualização): aqui a pausa é um sleep na linha de
execução do processamento, e o desenho das partes é feito no navegador. Diagnóstico e Arquivos Processados leem o
mesmo banco (pcp_projeart.db, tabelas corte_*).
"""
from __future__ import annotations

import threading
import time

from . import fabrica_apps as FA

PASTA = "Corte_Inteligente"
MODS = ["nucleo.banco_dados", "corte.processador"]
_S = {"pasta": "", "rodando": False, "log": [], "status": "Aguardando processamento…", "progresso": 0,
      "historico": [], "fim": None, "id": 0, "vis": True, "vel": 2000}
CORES = ["rgba(11,61,145,.82)", "rgba(30,158,74,.82)", "rgba(234,88,12,.82)", "rgba(124,58,237,.82)", "rgba(198,40,40,.82)"]


def _m():
    m = FA.carregar(PASTA, MODS)
    p = m["corte.processador"]
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


def _banco():
    return _m()["nucleo.banco_dados"].BancoDados()


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

    def mostrar_visualizacao(self, dimensoes, partes, furos, nome, estrategia, eficiencia, perda):
        _S["historico"].append({"dimensoes": list(dimensoes), "partes": [list(p) for p in partes],
                                "furos": [{"center": list(f["center"]), "radius": f["radius"]} for f in furos],
                                "nome": nome, "estrategia": estrategia, "eficiencia": eficiencia, "perda": perda})
        _S["id"] += 1


def estado(desde: int = 0) -> dict:
    lg = _S["log"]
    desde = max(0, min(desde, len(lg)))
    return FA.limpo({"ok": True, "pasta": _S["pasta"], "rodando": _S["rodando"], "log": lg[desde:], "n": len(lg),
                     "status": _S["status"], "progresso": _S["progresso"], "n_hist": len(_S["historico"]),
                     "fim": _S["fim"], "id": _S["id"], "cores": CORES})


def visual(i: int) -> dict:
    h = _S["historico"]
    if not h:
        return {"ok": True, "vazio": True}
    i = max(0, min(i, len(h) - 1))
    return FA.limpo({"ok": True, "i": i, "total": len(h), **h[i]})


def processar(caminho: str, vis: bool, vel: int) -> dict:
    if _S["rodando"]:
        return {"ok": False, "erro": "Já tem um processamento em andamento."}
    c = FA.pasta_ok(caminho)
    if not c:
        return {"ok": False, "titulo": "Caminho inválido", "erro": "Por favor, informe um caminho de pasta válido."}
    m = _m()
    try:
        vel = max(100, min(10000, int(vel)))
    except (TypeError, ValueError):
        vel = 2000
    _S.update(pasta=c, rodando=True, log=[f"📁 Pasta: {c}"], historico=[], progresso=0, fim=None, vis=bool(vis), vel=vel,
              status="Processando…")
    _S["id"] += 1

    def trabalho():
        ok = False
        try:
            banco = m["nucleo.banco_dados"].BancoDados()       # conexão SQLite criada nesta linha de execução
            ok = m["corte.processador"].ProcessadorDXF(_Tela(), banco).processar_pasta(c)
            try:
                banco.conn.close()
            except Exception:  # noqa: BLE001
                pass
        except Exception as e:  # noqa: BLE001
            _S["log"].append(f"❌ ERRO GERAL: {e}")
        finally:
            _S["log"].append("✅ Processamento concluído!" if ok else "⚠ Concluído com erros. Verifique o log.")
            _S.update(rodando=False, progresso=100, fim={"ok": bool(ok)})
            _S["id"] += 1

    threading.Thread(target=trabalho, daemon=True).start()
    return estado()


def limpar() -> dict:
    if _S["rodando"]:
        return {"ok": False, "erro": "Aguarde o processamento terminar."}
    _S.update(pasta="", log=[], status="Aguardando processamento…", progresso=0, historico=[], fim=None)
    _S["id"] += 1
    return estado()


def diagnostico(tipo: str, arquivo: str, desde: str) -> dict:
    try:
        b = _banco()
        linhas = b.buscar_eventos(tipo=tipo or "Todos", nome_arquivo=(arquivo or "").strip() or None,
                                  data_desde=(desde or "").strip() or None)
        b.conn.close()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "titulo": "Erro na consulta", "erro": f"Não foi possível consultar o banco:\n{e}"}
    return FA.limpo({"ok": True, "linhas": [list(l) for l in linhas]})


def processados(originais: bool, filtro: str) -> dict:
    try:
        b = _banco()
        f = (filtro or "").strip() or None
        linhas = b.buscar_arquivos_originais(nome_arquivo=f) if originais else b.buscar_partes_editadas(nome_arquivo=f)
        b.conn.close()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "titulo": "Erro na consulta", "erro": f"Não foi possível consultar o banco:\n{e}"}
    return FA.limpo({"ok": True, "originais": bool(originais), "linhas": [list(l) for l in linhas]})


def get(acao: str, q: dict) -> dict:
    if acao == "disponivel":
        return FA.disponivel("pg18", PASTA, MODS)
    if acao == "estado":
        d = str(q.get("desde") or "0")
        return estado(int(d) if d.isdigit() else 0)
    if acao == "visual":
        i = str(q.get("i") or "0")
        return visual(int(i) if i.isdigit() else 0)
    return {"ok": False, "erro": "Ação desconhecida."}


def post(acao: str, d: dict) -> dict:
    if acao == "processar":
        return processar(str(d.get("caminho") or ""), bool(d.get("vis", True)), d.get("vel", 2000))
    if acao == "limpar":
        return limpar()
    if acao == "diagnostico":
        return diagnostico(str(d.get("tipo") or "Todos"), str(d.get("arquivo") or ""), str(d.get("desde") or ""))
    if acao == "processados":
        return processados(bool(d.get("originais")), str(d.get("filtro") or ""))
    return {"ok": False, "erro": "Ação desconhecida."}


# V287: devolve o trabalho que estava aberto antes do sistema reiniciar com a versão nova
try:
    from .sessao import devolver_fabrica as _devolver
    _devolver("cor", _S)
except Exception:  # noqa: BLE001
    pass
