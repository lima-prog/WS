# -*- coding: utf-8 -*-
"""
Corte Inteligente — aplicativo próprio (separado do PPCP Ferramentas).

Gerado por separar_apps.py (v1.0) em 17/11/2026 11:46. NÃO edite à mão: se a ferramenta mudar no
PPCP Ferramentas, rode o separar_apps.py de novo e este app é refeito com o código novo.

O código da ferramenta (pastas ao lado deste arquivo) é uma cópia IDÊNTICA do PPCP Ferramentas — veja
MANIFESTO.json. Este main.py só faz o papel que o unificador fazia: prepara o Python/Qt, aponta os DADOS
para a pasta compartilhada do servidor (pasta_dados.txt) e abre a ferramenta numa janela própria.

    python main.py          abre o app
    iniciar_Corte_Inteligente.bat  abre rápido (copia o código pro PC antes, como o iniciar_ppcp.bat)
"""
import os
import sys

APP_CHAVE = 'corte'
APP_NOME = 'Corte Inteligente'
APP_PASTA = 'Corte_Inteligente'
APP_TIPO = 'qt'
APP_MODULO = 'corte.aba'
APP_CLASSE = 'AbaCorte'
APP_MODO = None
APP_BANCO = True

if getattr(sys, "frozen", False):
    _AQUI = os.path.dirname(sys.executable)
else:
    _AQUI = os.path.dirname(os.path.abspath(__file__))


# ── 1) pasta de DADOS compartilhada (servidor) ──────────────────────────────────────────────────
def _ler_pasta_dados():
    """Lê pasta_dados.txt (1ª linha que não é comentário). Caminho relativo vale a partir da pasta ORIGINAL do app
    (no modo rápido o código roda de uma cópia local, então o .bat informa a origem em PPCP_APP_ORIGEM)."""
    origem = os.environ.get("PPCP_APP_ORIGEM", "").strip().strip('"') or _AQUI
    for base in (origem, _AQUI):
        arq = os.path.join(base, "pasta_dados.txt")
        if not os.path.isfile(arq):
            continue
        try:
            with open(arq, encoding="utf-8-sig") as f:
                for linha in f:
                    linha = linha.strip().strip('"')
                    if linha and not linha.startswith("#"):
                        linha = linha.replace("\\", os.sep).replace("/", os.sep)
                        caminho = linha if os.path.isabs(linha) else os.path.join(origem, linha)
                        return os.path.normpath(os.path.abspath(caminho)), arq
        except OSError:
            pass
        return None, arq
    return None, os.path.join(origem, "pasta_dados.txt")


def _avisar(msg):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, APP_NOME, 0x10)
    except Exception:
        try:
            sys.stderr.write(msg + "\n")
        except Exception:
            pass


def _pasta_do_sistema():
    """Pasta de dados escolhida na tela do SISTEMA - PPCPM (python/dados_locais/producao/pasta_dados.txt) — é a
    MESMA que o Validador de Fluxos usa dentro do PPCPM."""
    origem = os.environ.get("PPCP_APP_ORIGEM", "").strip().strip('"') or _AQUI
    arq = os.path.normpath(os.path.join(origem, "..", "..", "dados_locais", "producao", "pasta_dados.txt"))
    try:
        with open(arq, encoding="utf-8-sig") as f:
            caminho = f.read().strip().strip('"')
        return caminho if caminho and os.path.isdir(caminho) else None
    except OSError:
        return None


def _linha_relativa(arq):
    """True se a 1ª linha do pasta_dados.txt é um caminho RELATIVO (o padrão ../../dados_locais/producao)."""
    try:
        with open(arq, encoding="utf-8-sig") as f:
            for linha in f:
                linha = linha.strip().strip('"')
                if linha and not linha.startswith("#"):
                    return not (os.path.isabs(linha) or linha.startswith("\\") or linha[1:2] == ":")
    except OSError:
        pass
    return False


def _preparar_dados():
    if os.environ.get("PPCP_DADOS", "").strip():
        return                                           # já veio definida (.bat, processo pai ou a pessoa)
    dados, arq = _ler_pasta_dados()
    padrao = _linha_relativa(arq)
    if dados and not padrao and os.path.isdir(dados):   # 1) caminho escrito à mão no pasta_dados.txt (ex.: servidor)
        os.environ["PPCP_DADOS"] = dados
        return
    sistema = _pasta_do_sistema()                        # 2) a pasta de dados escolhida no SISTEMA - PPCPM
    if sistema:
        os.environ["PPCP_DADOS"] = sistema
        return
    if dados and padrao:                                 # 3) padrão: python\dados_locais\producao (criada na 1ª vez)
        try:
            os.makedirs(dados, exist_ok=True)
            os.environ["PPCP_DADOS"] = dados
            return
        except OSError:
            pass
    _avisar(f"{APP_NOME}: não encontrei a pasta de DADOS compartilhada.\n\n"
            f"Pasta indicada: {dados or '(nenhuma)'}\nArquivo: {arq}\n\n"
            "Abra o pasta_dados.txt e coloque na primeira linha o caminho da pasta ppcp_dxf_ferramentas do "
            "servidor (onde ficam etiquetas.db, base_fixa, roteirizador_original\\roteirizador_memoria.db...)\n"
            "ou escolha a pasta de dados na tela do SISTEMA - PPCPM.")
    sys.exit(2)


# ── 2) execução local (código em pasta de rede abre muito devagar) ──────────────────────────────
def _execucao_local():
    """Igual ao nucleo/modo_local.py, mas cada app tem a SUA pasta local (%LOCALAPPDATA%\\PPCP_Apps\\<app>\\app)
    — assim um app nunca apaga a cópia local do unificador nem de outro app."""
    if sys.platform != "win32" or getattr(sys, "frozen", False) or os.environ.get("PPCP_SEM_LOCAL") == "1":
        return
    if os.environ.get("PPCP_APP_ORIGEM"):                # já está rodando da cópia local
        return
    try:
        from nucleo.modo_local import _em_unidade_de_rede, sincronizar
        if not _em_unidade_de_rede(_AQUI):
            return
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        destino = os.path.join(base, "PPCP_Apps", APP_PASTA, "app")
        if os.path.normcase(os.path.abspath(destino)) == os.path.normcase(_AQUI):
            return
        sincronizar(_AQUI, destino)
        local_main = os.path.join(destino, "main.py")
        if not os.path.exists(local_main):
            return
    except Exception:
        return                                           # qualquer problema: segue rodando daqui mesmo
    import subprocess
    env = os.environ.copy()
    env["PPCP_APP_ORIGEM"] = _AQUI
    try:
        codigo = subprocess.call([sys.executable, local_main, *sys.argv[1:]], cwd=destino, env=env)
    except Exception:
        return
    sys.exit(codigo)


def _preparar_logs():
    """Cada app grava o SEU log (dois programas no mesmo arquivo rotativo brigam no Windows)."""
    if os.environ.get("PPCP_LOGS", "").strip():
        return
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".ppcp_apps")
    pasta = os.path.join(base, "PPCP_Apps", APP_PASTA, "logs")
    try:
        os.makedirs(pasta, exist_ok=True)
        os.environ["PPCP_LOGS"] = pasta
    except OSError:
        pass


sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
_preparar_dados()
_execucao_local()
_preparar_logs()


# ── 3) abre a ferramenta ────────────────────────────────────────────────────────────────────────
def _abrir_tk():
    # mesmo caminho do `main.py --roteirizador` / `--ordens` do unificador (sem o encaixe)
    from roteirizador_original.roteirizador_dxf_projeart import main as _main
    _main(APP_MODO)


def _abrir_validador():
    # mesmo caminho do `main.py --validador` do unificador (sem o encaixe)
    import nucleo.ambiente_qt  # noqa: F401
    from validador_fluxos.executar import main as _main
    _main()


class _BancoPreguicoso:
    """Igual ao do janela_principal.py: só conecta ao banco na primeira vez que for usado."""

    def __init__(self):
        self.__dict__["_b"] = None

    def __getattr__(self, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)
        if self.__dict__["_b"] is None:
            from nucleo.banco_dados import BancoDados
            self.__dict__["_b"] = BancoDados()
        return getattr(self.__dict__["_b"], nome)


def _abrir_qt():
    import nucleo.ambiente_qt  # noqa: F401   (PRIMEIRO, antes de qualquer PyQt5 — igual ao main.py)
    from nucleo.logging_config import configurar_logging, registrar_erro_fatal, LOG_PATH
    logger = configurar_logging()
    import importlib
    from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut
    from PyQt5.QtCore import Qt, QEvent
    from PyQt5.QtGui import QIcon, QPalette, QColor, QKeySequence
    from nucleo.caminhos import CAMINHO_ICONE_PROJEART, RAIZ_PROJETO, RAIZ_DADOS
    from nucleo.estilo import ESTILO_GERAL, COR_TEXTO_SUB, COR_DESTAQUE

    class JanelaApp(QMainWindow):
        def __init__(self, conteudo):
            super().__init__()
            self.conteudo = conteudo
            self.setWindowTitle(f"{APP_NOME} — SISTEMA - PPCPM")
            self.setWindowIcon(QIcon(CAMINHO_ICONE_PROJEART))
            self.setStyleSheet(ESTILO_GERAL)         # no unificador o estilo geral vem da janela principal
            self.setCentralWidget(conteudo)
            QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)
            tela = QApplication.primaryScreen()
            a = tela.availableGeometry() if tela is not None else None
            w, h = 1360, 840
            if a is not None:
                w, h = min(w, int(a.width() * 0.94)), min(h, int(a.height() * 0.92))
                self.resize(w, h)
                self.move(a.x() + (a.width() - w) // 2, a.y() + (a.height() - h) // 2)
            else:
                self.resize(w, h)

        def changeEvent(self, ev):
            super().changeEvent(ev)
            # atalhos próprios da ferramenta (hoje só o Visualizador): ligados enquanto a janela está na frente,
            # igual ao unificador faz com a janela ativa
            if hasattr(self.conteudo, "set_atalhos_ativos") and ev.type() in (QEvent.ActivationChange, QEvent.WindowStateChange):
                self.conteudo.set_atalhos_ativos(self.isActiveWindow() and not self.isMinimized())

        def closeEvent(self, ev):
            if hasattr(self.conteudo, "set_atalhos_ativos"):
                self.conteudo.set_atalhos_ativos(False)
            if hasattr(self.conteudo, "encerrar"):
                self.conteudo.encerrar()
            super().closeEvent(ev)

    try:
        logger.info(f"Iniciando {APP_NOME} (app separado) — código: {RAIZ_PROJETO} | dados: {RAIZ_DADOS} | log: {LOG_PATH}")
        QApplication.setStyle("Fusion")
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NOME)
        app.setWindowIcon(QIcon(CAMINHO_ICONE_PROJEART))
        paleta = app.palette()
        paleta.setColor(QPalette.PlaceholderText, QColor(COR_TEXTO_SUB))
        paleta.setColor(QPalette.Highlight, QColor("#DBE8FB"))           # seleção azul-clara do SISTEMA - PPCPM
        paleta.setColor(QPalette.HighlightedText, QColor("#000000"))     # com letra preta
        app.setPalette(paleta)
        modulo = importlib.import_module(APP_MODULO)
        classe = getattr(modulo, APP_CLASSE)
        conteudo = classe(_BancoPreguicoso()) if APP_BANCO else classe()
        janela = JanelaApp(conteudo)
        janela.show()
        if hasattr(conteudo, "set_atalhos_ativos"):
            conteudo.set_atalhos_ativos(True)
        codigo = app.exec_()
    except Exception:
        registrar_erro_fatal(f"ERRO FATAL AO INICIAR {APP_NOME}", sys.exc_info())
        _avisar(f"{APP_NOME} não conseguiu iniciar.\n\nDetalhes no arquivo:\n{LOG_PATH}")
        sys.exit(1)
    logger.info(f"{APP_NOME} encerrado normalmente.")
    sys.exit(codigo)


if __name__ == "__main__":
    if APP_TIPO == "tk":
        _abrir_tk()
    elif APP_TIPO == "validador":
        _abrir_validador()
    else:
        _abrir_qt()
