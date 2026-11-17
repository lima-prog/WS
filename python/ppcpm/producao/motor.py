"""
MOTOR DA PRODUÇÃO — roda a tela do Validador de Fluxos (validador_fluxos_ppcp.py, sem alteração) no
Python do PPCPM, com o PyQt5 "de mentira" (qtfalso.py), e conversa com as abas do navegador:

  estado    -> o que está na tela (rótulos, listas, árvores, KPIs, botões), avisos e pedidos pendentes
  chamar    -> executa um método da tela (ex.: _imp_conferir) numa linha de execução própria
  responder -> resposta a um pedido (arquivo escolhido, pergunta, texto)
  arvore    -> clique / duplo clique / marcar num item de árvore
  enviar    -> arquivo arrastado do navegador vira um arquivo local (pasta temporária)

Só atende o próprio computador (o app.py já confere). Uma tela só (o app é de um usuário por PC).
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path

from ..config import PASTA_DADOS
from . import qtfalso as Q

AQUI = Path(__file__).resolve().parent
PASTA_PROD = PASTA_DADOS / "producao"
PASTA_TEMP = PASTA_PROD / "recebidos"
PASTA_SAIDA = PASTA_PROD / "gerados"
ARQ_PASTA_DADOS = PASTA_PROD / "pasta_dados.txt"

# aba do PPCPM -> prefixo dos widgets da tela original
ABAS = {
    "agrupador": ("", ["lst_dbf", "lbl_base", "lbl_fluxo", "lbl_foco", "lbl_ska", "lbl_status", "lbl_contador_obras",
                       "txt_lote", "txt_obras", "txt_raiz_obras", "tbl", "btn_buscar_obras", "btn_gerar", "btn_ska_agora",
                       "btn_vis", "chk_busca_completa", "chk_ska"]),
    "imp": ("imp_", None),
    "impm": ("impm_", None),
    "lic": ("lic_", None),
    "f4": ("f4_", None),
}

_lock_carga = threading.Lock()
_S: dict = {"win": None, "V": None, "erro": None, "rodando": 0, "ultimo_erro": "", "por_aba": {}}


# ------------------------------------------------------------------ pasta de dados (base fixa etc.)
def pasta_dados() -> str:
    v = os.environ.get("PPCP_DADOS", "").strip().strip('"')
    if v:
        return v
    try:
        t = ARQ_PASTA_DADOS.read_text(encoding="utf-8").strip()
        if t:
            return t
    except OSError:
        pass
    return ""


def definir_pasta_dados(caminho: str) -> dict:
    caminho = (caminho or "").strip().strip('"')
    if caminho and not os.path.isdir(caminho):
        return {"ok": False, "msg": f"Pasta não encontrada: {caminho}"}
    PASTA_PROD.mkdir(parents=True, exist_ok=True)
    ARQ_PASTA_DADOS.write_text(caminho, encoding="utf-8")
    if caminho:
        os.environ["PPCP_DADOS"] = caminho
    else:
        os.environ.pop("PPCP_DADOS", None)
    return {"ok": True, "pasta": caminho}


# ------------------------------------------------------------------ saída dos arquivos gerados
def _dentro(c: str, pasta: Path) -> bool:
    try:
        return Path(c).resolve().is_relative_to(pasta.resolve())
    except Exception:
        return False


def _saida(sugestao: str, titulo: str = "", pasta: bool = False) -> str:
    """O Qt perguntaria onde salvar. Aqui: ao lado dos arquivos de origem (como o programa sugere), ou na
    pasta 'gerados' quando a origem veio do navegador (pasta temporária)."""
    sugestao = sugestao or ""
    d = os.path.dirname(sugestao) if not pasta else sugestao.rstrip("\\/")
    if not d or not os.path.isdir(d) or _dentro(d, PASTA_TEMP):
        d = str(PASTA_SAIDA)
    os.makedirs(d, exist_ok=True)
    if pasta:
        _S["ultima_saida"] = d
        return d
    nome = os.path.basename(sugestao) or "saida"
    alvo = os.path.join(d, nome)
    if os.path.exists(alvo):
        base, ext = os.path.splitext(nome)
        k = 2
        while os.path.exists(os.path.join(d, f"{base}_{k}{ext}")):
            k += 1
        alvo = os.path.join(d, f"{base}_{k}{ext}")
    _S["ultima_saida"] = alvo
    return alvo


# ------------------------------------------------------------------ carga da tela
def carregar():
    with _lock_carga:
        if _S["win"] is not None or _S["erro"]:
            return _S["win"]
        try:
            pd = pasta_dados()
            if pd:
                os.environ["PPCP_DADOS"] = pd
            if str(AQUI) not in sys.path:
                sys.path.insert(0, str(AQUI))
            Q.instalar_falso()
            Q.CTX.saida_padrao = _saida
            Q.CTX.pasta_temp = str(PASTA_TEMP)
            from validador_fluxos import validador_fluxos_ppcp as V    # noqa: E402
            _S["V"] = V
            _S["win"] = V.MainWindow()
            Q.CTX.msgs.clear()
        except Exception as e:                       # biblioteca faltando etc.
            _S["erro"] = f"{e.__class__.__name__}: {e}"
            _S["trace"] = traceback.format_exc()
        return _S["win"]


def _faltando() -> list[str]:
    from importlib import import_module
    falta = []
    for mod, pip in (("openpyxl", "openpyxl"), ("pandas", "pandas"), ("fitz", "pymupdf"), ("pypdf", "pypdf"),
                     ("pyxlsb", "pyxlsb"), ("xlrd", "xlrd"), ("numpy", "numpy")):
        try:
            import_module(mod)
        except Exception:
            falta.append(pip)
    return falta


# ------------------------------------------------------------------ estado -> navegador
def _widgets_da_aba(win, aba: str):
    pref, nomes = ABAS.get(aba, ("", []))
    for k, v in list(vars(win).items()):
        if nomes is not None:
            if k not in nomes:
                continue
        elif not k.startswith(pref):
            continue
        yield k, v


def estado(aba: str, desde: int = 0, msg_desde: int = 0) -> dict:
    win = carregar()
    if win is None:
        return {"ok": False, "erro": _S["erro"], "faltando": _faltando()}
    ws = {}
    for k, v in _widgets_da_aba(win, aba):
        try:
            if Q.versao_widget(v) > desde:
                j = Q.widget_json(v)
                if j is not None:
                    ws[k] = j
        except Exception:
            pass
    p = Q.CTX.pedido
    if p and p.get("aba") not in (None, aba):
        p = None                        # pedido de outra aba: aparece lá
    return {"ok": True, "tick": Q.novo_tick(), "widgets": ws,
            "msgs": [m for m in Q.CTX.msgs if m["id"] > msg_desde and m.get("aba") in (None, aba)],
            "pedido": p, "ocupado": _S.get("por_aba", {}).get(aba, 0) > 0 or Q.tarefas_rodando(aba) > 0,
            "saida": _S.get("ultima_saida", ""), "erro_tarefa": _S.get("ultimo_erro", ""),
            "pasta_dados": pasta_dados()}


def _aplicar_valores(win, valores: dict):
    for k, val in (valores or {}).items():
        w = getattr(win, k, None)
        if w is None:
            continue
        if isinstance(w, Q.QCheckBox):
            w.setChecked(bool(val))
        elif isinstance(w, Q.QComboBox):
            w.setCurrentIndex(int(val))
        elif isinstance(w, Q.QLineEdit):
            w.setText(str(val))
        elif isinstance(w, Q.QPlainTextEdit):
            w.setPlainText(str(val))
        elif isinstance(w, Q.QSpinBox):
            w.setValue(val)


def _rodar(fn, *args, aba=None):
    _S["rodando"] += 1
    _S["por_aba"][aba] = _S["por_aba"].get(aba, 0) + 1
    _S["ultimo_erro"] = ""

    def corre():
        Q.definir_aba(aba)
        try:
            fn(*args)
        except Exception as e:
            _S["ultimo_erro"] = f"{e.__class__.__name__}: {e}"
            Q.CTX.avisar("erro", "Erro", f"{e.__class__.__name__}: {e}", traceback.format_exc()[-2500:])
            try:
                from .nucleo.logging_config import registrar_erro_fatal
                registrar_erro_fatal("Erro na tela de Produção", sys.exc_info())
            except Exception:
                pass
        finally:
            _S["rodando"] -= 1
            _S["por_aba"][aba] -= 1
    t = threading.Thread(target=corre, daemon=True, name="ppcpm-producao")
    t.start()
    t.join(1.2)           # respostas rápidas já voltam com a tela atualizada


def chamar(aba: str, metodo: str, args=None, valores=None, desde=0, msg_desde=0) -> dict:
    win = carregar()
    if win is None:
        return estado(aba)
    if not metodo:                      # só guarda os valores (caixas marcadas, textos digitados)
        _aplicar_valores(win, valores)
        return estado(aba, desde, msg_desde)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", metodo) or metodo.startswith("__"):
        return {"ok": False, "erro": "Ação inválida."}
    fn = getattr(win, metodo, None)
    if not callable(fn):
        return {"ok": False, "erro": f"Ação não encontrada: {metodo}"}
    _aplicar_valores(win, valores)
    _rodar(fn, *(args or []), aba=aba)
    return estado(aba, desde, msg_desde)


def arvore(aba: str, widget: str, caminho: list, evento: str = "clique", col: int = 0, valor=None,
           desde=0, msg_desde=0) -> dict:
    win = carregar()
    w = getattr(win, widget, None) if win else None
    if not isinstance(w, Q.QTreeWidget):
        return estado(aba, desde, msg_desde)
    it = Q.item_por_caminho(w, caminho)
    if it is None:
        return estado(aba, desde, msg_desde)

    def faz():
        if evento == "marcar":
            it.setCheckState(col, 2 if valor else 0)
            w._emitir("itemChanged", it, col)
        elif evento == "duplo":
            w.setCurrentItem(it)
            w._emitir("itemDoubleClicked", it, col)
        elif evento == "botao":
            b = it.__dict__.get("widgets", {}).get(int(col))
            if b is not None and hasattr(b, "click"):
                w.setCurrentItem(it)
                b.click()
        elif evento == "abrir":
            it.setExpanded(bool(valor))
        else:
            w.setCurrentItem(it)
            w._emitir("itemClicked", it, col)
    _rodar(faz, aba=aba)
    return estado(aba, desde, msg_desde)


def lista(aba: str, widget: str, idx: int, valor, desde=0, msg_desde=0) -> dict:
    """Marcar/desmarcar um item de lista com caixinha (ex.: Obras a gerar)."""
    win = carregar()
    w = getattr(win, widget, None) if win else None
    it = w.item(int(idx)) if isinstance(w, Q.QListWidget) else None
    if it is not None:
        def faz():
            it.setCheckState(2 if valor else 0)
            w._emitir("itemChanged", it)
        _rodar(faz, aba=aba)
    return estado(aba, desde, msg_desde)


def responder(pid: int, resposta) -> dict:
    return {"ok": Q.CTX.responder(pid, resposta)}


def receber_arquivo(nome: str, dados: bytes) -> dict:
    nome = os.path.basename(nome or "arquivo").replace("..", "_") or "arquivo"
    pasta = PASTA_TEMP / time.strftime("%Y%m%d_%H%M%S") / str(Q.novo_tick())
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / nome
    alvo.write_bytes(dados)
    _limpar_temp()
    return {"ok": True, "caminho": str(alvo)}


def _limpar_temp(dias: float = 3):
    """Arquivos enviados pelo navegador ficam 3 dias (dá tempo de gerar de novo) e somem."""
    try:
        limite = time.time() - dias * 86400
        for p in PASTA_TEMP.iterdir():
            if p.is_dir() and p.stat().st_mtime < limite:
                shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass


def abrir(caminho: str, mostrar: bool = False) -> dict:
    if not caminho or not os.path.exists(caminho):
        return {"ok": False, "msg": "Arquivo não encontrado."}
    if not sys.platform.startswith("win"):
        return {"ok": False, "msg": "Abrir arquivos só funciona no Windows."}
    import subprocess
    try:
        if mostrar:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(caminho)])
        else:
            os.startfile(caminho)               # type: ignore[attr-defined]
        return {"ok": True}
    except OSError as e:
        return {"ok": False, "msg": str(e)}
