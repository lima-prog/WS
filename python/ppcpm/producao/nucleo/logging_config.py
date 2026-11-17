"""Log de erros dos programas de Produção (validador) dentro do PPCPM."""
import logging
import os
import traceback

logger = logging.getLogger("ppcpm.producao")
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                        "dados_locais", "producao", "producao.log")


def configurar_logging():
    pass


def registrar_erro_fatal(titulo, info=None):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n=== {titulo}\n")
            if info and info[0] is not None:
                f.write("".join(traceback.format_exception(*info)))
    except Exception:
        pass
