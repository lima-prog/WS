# -*- coding: utf-8 -*-
"""
Log centralizado do programa inteiro (todas as abas usam o mesmo `logger`
daqui). Cobre dois cenários que o console sozinho não resolve no Windows:
o terminal fechar antes de dar tempo de ler um erro, e um erro nativo
(fora do Python) que não gera nenhuma exceção pra capturar.

Uso em main.py:
    from nucleo.logging_config import configurar_logging, registrar_erro_fatal, LOG_PATH
    logger = configurar_logging()
    ...
    try:
        ...
    except Exception:
        registrar_erro_fatal("ERRO FATAL AO INICIAR O PROGRAMA", sys.exc_info())

Uso em qualquer outro módulo que precise logar algo:
    from nucleo.logging_config import logger
    logger.error("mensagem")
"""
import os
import sys
import logging
import logging.handlers
import traceback

from nucleo.caminhos import PASTA_LOGS

# O log fica "do lado do programa" (dentro de ppcp_dxf_ferramentas/, onde o
# main.py mora) — igual era antes da divisão em pacote, só que agora
# RAIZ_PROJETO vem de um lugar só (nucleo/caminhos.py) em vez de cada
# arquivo calcular por conta própria.
LOG_PATH = os.path.join(PASTA_LOGS, "app_dxf_ppcp_log.txt")  # PASTA_LOGS: local no modo rápido (ver caminhos.py)

logger = logging.getLogger("ppcp")


def registrar_erro_fatal(titulo, exc_info=None):
    """Grava um erro fatal no arquivo de log E imprime no console. Usado
    tanto pelo try/except do main.py quanto pelo excepthook global abaixo."""
    texto = f"\n{'=' * 70}\n{titulo}\n{'=' * 70}\n"
    if exc_info:
        texto += "".join(traceback.format_exception(*exc_info))
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(texto)
    except Exception:
        pass  # se nem isso der certo, ao menos o print abaixo ainda mostra algo
    try:
        print(texto)
    except Exception:
        pass  # sem console (pythonw)


def _excepthook_global(exc_type, exc_value, exc_tb):
    """Pega qualquer erro que escape sem tratamento e garante que fica
    registrado no log antes do programa fechar, em vez de simplesmente
    sumir junto com o terminal."""
    registrar_erro_fatal("ERRO NÃO TRATADO (o programa provavelmente vai fechar)",
                         (exc_type, exc_value, exc_tb))


def configurar_logging():
    """Liga o log em arquivo + console e o excepthook global. Chamar uma
    vez só, bem no início do main.py. Retorna o logger compartilhado."""
    # Sem console (pythonw / atalho sem janela) sys.stderr é None: não cria o handler de console.
    handlers_console = [logging.StreamHandler()] if sys.stderr is not None else []
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers_console + [
            # rotativo: ao chegar em 5 MB vira `.1`/`.2` e recomeça (antes o arquivo só crescia —
            # chegou a 63 MB — e cada linha era gravada na hora, o que pesa em pasta de rede)
            logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=2,
                                                 encoding='utf-8', delay=True),
        ],
    )
    logger.setLevel(logging.INFO)
    # O ezdxf escreve ~11 linhas de INFO ("creating ACAD_... dictionary") A CADA arquivo DXF criado —
    # eram ~90% do log e deixavam Corte/Espelhar/Conversor lentos (gravação em arquivo + console por DXF).
    # Só avisos e erros dele interessam.
    logging.getLogger("ezdxf").setLevel(logging.WARNING)
    sys.excepthook = _excepthook_global
    return logger
