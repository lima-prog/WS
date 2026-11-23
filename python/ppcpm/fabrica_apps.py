"""
PREPARAÇÃO FÁBRICA — peças comuns dos apps que rodam DENTRO da aba do sistema.

Os apps (python/apps/<App>) são cópias do PPCP Ferramentas e cada um traz o SEU pacote `nucleo` (caminhos, log,
normalização...). O Validador de Fluxos da Produção também tem um `nucleo` (menor). Para não misturar, o código de
cada app é importado com o `nucleo` DELE no lugar e, terminada a importação, o `nucleo` que estava antes volta.
A pasta de DADOS (PPCP_DADOS) é a mesma "Pasta de dados do PCP" que o app usaria aberto sozinho (fabrica._pasta_dados).
"""
from __future__ import annotations

import importlib
import math
import os
import sys
import threading

from . import fabrica

_trava = threading.Lock()
_CARREGADOS: dict[str, dict] = {}


def _nucleo_mods() -> dict:
    return {k: v for k, v in sys.modules.items() if k == "nucleo" or k.startswith("nucleo.")}


def carregar(pasta_app: str, modulos: list[str]) -> dict:
    """Importa `modulos` do app python/apps/<pasta_app> (uma vez só) e devolve {nome: módulo}."""
    with _trava:
        ja = _CARREGADOS.get(pasta_app)
        if ja is not None and all(m in ja for m in modulos):
            return ja
        raiz = str(fabrica.PASTA_APPS / pasta_app)
        antes = _nucleo_mods()
        for k in antes:
            sys.modules.pop(k, None)
        if ja and "__nucleo__" in ja:                 # importações seguintes do mesmo app usam o nucleo dele
            sys.modules.update(ja["__nucleo__"])
        env_antes = {k: os.environ.get(k) for k in ("PPCP_DADOS", "PPCP_LOGS")}
        os.environ["PPCP_DADOS"] = fabrica._pasta_dados()
        if not os.environ.get("PPCP_LOGS"):
            pasta_logs = os.path.join(str(fabrica.PASTA_DADOS_PRODUCAO), "logs", pasta_app)
            try:
                os.makedirs(pasta_logs, exist_ok=True)
                os.environ["PPCP_LOGS"] = pasta_logs
            except OSError:
                pass
        sys.path.insert(0, raiz)
        try:
            saida = dict(ja or {})
            for m in modulos:
                saida[m] = importlib.import_module(m)
            saida["__nucleo__"] = _nucleo_mods()
            _CARREGADOS[pasta_app] = saida
            return saida
        finally:
            try:
                sys.path.remove(raiz)
            except ValueError:
                pass
            for k in list(_nucleo_mods()):
                sys.modules.pop(k, None)
            sys.modules.update(antes)
            for k, v in env_antes.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def disponivel(aba: str, pasta_app: str, modulos: list[str]) -> dict:
    est = fabrica.estado(aba)
    if not est.get("existe"):
        return {"ok": False, "erro": f"O {est.get('nome', 'app')} não está nesta instalação (pasta apps/{pasta_app})."}
    if est.get("faltam"):
        return {"ok": False, "faltam": est["faltam"],
                "erro": f"Faltam bibliotecas para o {est['nome']}: " + ", ".join(est["faltam"]) + "."}
    try:
        carregar(pasta_app, modulos)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "erro": f"Não consegui carregar o {est.get('nome', 'app')}: {e}"}
    return {"ok": True}


def limpo(x):
    """Deixa o resultado pronto para JSON (numpy, NaN, conjuntos, caminhos)."""
    if isinstance(x, dict):
        return {str(k): limpo(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [limpo(v) for v in x]
    if isinstance(x, float):
        return None if (math.isnan(x) or math.isinf(x)) else x
    if x is None or isinstance(x, (str, int, bool)):
        return x
    try:
        import numpy as np
        if isinstance(x, np.generic):
            return limpo(x.item())
    except Exception:
        pass
    return str(x)


def pasta_ok(caminho: str) -> str:
    """Caminho colado do Windows (com aspas, espaços, %VARIAVEIS%) -> pasta existente ou ''."""
    c = os.path.expandvars((caminho or "").strip().strip('"').strip("'").strip())
    return c if c and os.path.isdir(c) else ""
