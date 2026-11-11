"""
SISTEMA - PPCPM | versão Python

Abre o mesmo sistema do HTML (mesma tela de login, menu, cores e programas), servido pelo
Python deste PC, com o que o HTML sozinho não consegue:
  • ARQUIVOS DO PC: todos os programas abrem arquivos direto das pastas do computador
    (unidades, rede mapeada, Área de Trabalho, Downloads, favoritos, recentes, busca).
  • ATUALIZAÇÃO AUTOMÁTICA: toda versão nova publicada chega sozinha (HTML e Python).
  • Página guardada em memória e compactada: abre mais rápido, também para quem entra pela rede.
Usa só o que já vem com o Python: não precisa de pip nem de administrador.

    python app.py                    -> abre neste computador
    python app.py --rede             -> outros PCs da rede também abrem (sem ver os arquivos deste PC)
    python app.py --sem-navegador    -> não abre a tela sozinho (ex.: ao ligar o Windows)
    python app.py --navegador        -> abre numa aba comum do navegador (em vez da janela de aplicativo)
    python app.py --sem-atualizar    -> não procura versões novas
    python app.py --verificar        -> confere se o PC está pronto (Python, rede, pastas, bibliotecas)
"""
from __future__ import annotations

import gzip
import json
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))  # acha a pasta ppcpm de qualquer lugar

from ppcpm import arquivos_pc, banco, calculos, zebra  # noqa: E402
from ppcpm.config import PASTA_APP, PASTA_GERADO, config, versao, versao_python  # noqa: E402
from ppcpm.montagem import montar  # noqa: E402

PORTA_PADRAO = 5000
CODIGO_REINICIAR = 3          # o ABRIR_SISTEMA.bat reabre o sistema quando recebe este código
PONTE_JS = Path(__file__).resolve().parent / "ppcpm" / "web" / "ponte.js"
LOCAIS_OK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}

_pagina = {"chave": None, "bruta": b"", "gzip": b""}
_trava = threading.Lock()
JANELAS_3D: dict = {}   # visualizador 3D: id -> {"html", "arquivo", "tipo"} (só na memória, últimas 12)
ESTADO = {"porta": PORTA_PADRAO, "rede": False, "agendador": None, "servidor": None, "encerrar": False}


def pagina() -> tuple[bytes, bytes]:
    """Página completa (com a ponte das pastas do PC) guardada em memória enquanto a versão não muda."""
    chave = (PASTA_GERADO / "config.json").stat().st_mtime
    with _trava:
        if _pagina["chave"] != chave:
            bruta = montar(PASTA_GERADO, com_ponte=True).encode("utf-8")
            _pagina.update(chave=chave, bruta=bruta, gzip=gzip.compress(bruta, 6))
        return _pagina["bruta"], _pagina["gzip"]


class Sistema(BaseHTTPRequestHandler):
    server_version = "PPCPM"
    protocol_version = "HTTP/1.1"

    # ---------- respostas ----------
    def _enviar(self, codigo: int, corpo, tipo: str, sem_cache: bool = True, extra: dict | None = None,
                compactado: bytes | None = None) -> None:
        dados = corpo.encode("utf-8") if isinstance(corpo, str) else corpo
        usar_gzip = compactado is not None and "gzip" in self.headers.get("Accept-Encoding", "")
        if usar_gzip:
            dados = compactado
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        if usar_gzip:
            self.send_header("Content-Encoding", "gzip")
        if sem_cache:
            self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(dados)

    def _json(self, obj, codigo: int = 200) -> None:
        self._enviar(codigo, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def log_message(self, formato, *args):  # janela limpa: só mostra erros do servidor
        if len(args) > 1 and str(args[1]).startswith("5"):
            sys.stderr.write("  aviso: %s\n" % (formato % args))

    def _do_proprio_pc(self) -> bool:
        """Arquivos do PC: só para quem está NESTE computador, abrindo pelo sistema (proteção extra)."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return (self.client_address[0] in LOCAIS_OK and host in ("127.0.0.1", "localhost", "::1")
                and self.headers.get("X-PPCPM") == "1")

    # ---------- rotas ----------
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urlparse(self.path)
        caminho = url.path.rstrip("/") or "/"
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if caminho in ("/", "/index.html"):
                bruta, comp = pagina()
                return self._enviar(200, bruta, "text/html; charset=utf-8", compactado=comp)
            if caminho == "/versao.json":   # usado pelo aviso "Nova versão disponível"
                return self._json({"versao": versao()})
            if caminho == "/pc/janela":   # janela PPCPM - ARQUIVOS (a ponte desenha a tela dentro dela)
                return self._enviar(200, '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
                                    '<title>PPCPM - ARQUIVOS</title><link rel="icon" href="/pc/icone.ico">'
                                    '<style>html,body{margin:0;height:100%;background:#fff;overflow:hidden}</style>'
                                    '</head><body></body></html>', "text/html; charset=utf-8")
            if caminho == "/pc/janela3d":   # janela do visualizador 3D (a aba Engenharia escreve o 3D dentro dela)
                return self._enviar(200, '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
                                    '<title>PPCPM - VISUALIZADOR 3D</title><link rel="icon" href="/pc/icone.ico"></head>'
                                    '<body style="margin:0;font:600 14px Arial;display:grid;place-items:center;height:100vh;'
                                    'color:#5b6474;background:#f4f6f9">Lendo o desenho e montando o 3D…</body></html>',
                                    "text/html; charset=utf-8")
            if caminho.startswith("/pc/3d/"):   # janela própria do VISUALIZAR 3D (aberta como aplicativo)
                if self.client_address[0] not in LOCAIS_OK:
                    return self._json({"erro": "O 3D abre só neste computador."}, 403)
                partes = caminho[len("/pc/3d/"):].split("/")
                j = JANELAS_3D.get(partes[0])
                if not j:
                    return self._enviar(404, '<!doctype html><meta charset="utf-8"><title>PPCPM - 3D</title><body style="font:600 14px Arial;'
                                        'display:grid;place-items:center;height:100vh;margin:0;color:#5b6474">Este 3D já foi fechado. '
                                        'Abra de novo pela aba Engenharia.</body>', "text/html; charset=utf-8")
                if len(partes) > 1 and partes[1] == "arquivo":
                    return self._enviar(200, j["arquivo"], j["tipo"] or "application/octet-stream")
                return self._enviar(200, j["html"], "text/html; charset=utf-8")
            if caminho == "/pc/icone.ico":
                return self._enviar(200, (PONTE_JS.parent / "icone.ico").read_bytes(), "image/x-icon", sem_cache=False)
            if caminho == "/pc/ponte.js":
                return self._enviar(200, PONTE_JS.read_bytes(), "text/javascript; charset=utf-8")
            if caminho == "/api/status":
                ag = ESTADO["agendador"]
                return self._json({"app": "PPCPM", "versao": versao(), "pacote_python": versao_python().get("pacote"),
                                   "rede": ESTADO["rede"], "ultima_verificacao": getattr(ag, "ultimo", None)})
            if caminho.startswith("/api/pc/"):
                return self._arquivos_pc(caminho[len("/api/pc/"):], q)
            if caminho == "/api/zebra/impressoras":
                if not self._do_proprio_pc():
                    return self._json({"erro": "Impressoras só neste computador."}, 403)
                try:
                    return self._json({"impressoras": zebra.listar_impressoras(), "ultima": zebra.ultima_impressora()})
                except Exception as e:
                    return self._json({"erro": str(e)}, 500)
            if caminho == "/api/modulos":
                return self._json(config()["modulos"])
            if caminho.startswith("/api/modulo/"):
                pg = caminho.rsplit("/", 1)[-1]
                if not any(m["id"] == pg for m in config()["modulos"]):
                    return self._json({"erro": "Programa não encontrado."}, 404)
                html = (PASTA_GERADO / "modulos" / f"{pg}.html").read_text(encoding="utf-8")
                return self._enviar(200, html.replace("<\\/script", "</script"), "text/html; charset=utf-8")
            if caminho == "/api/resumo":
                return self._resumo()
            if caminho == "/favicon.ico":
                self.send_response(204); self.send_header("Content-Length", "0"); return self.end_headers()
            return self._json({"erro": "Página não encontrada."}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _corpo_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 20 * 1024 * 1024:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return {}

    def do_POST(self):
        caminho = urlparse(self.path).path.rstrip("/")
        if caminho == "/api/zebra/imprimir":
            # Impressão de Etiquetas: ZPL direto na Zebra ligada a este PC
            if not self._do_proprio_pc():
                return self._json({"erro": "Só o próprio computador da impressora pode imprimir."}, 403)
            d = self._corpo_json()
            zpls = d.get("zpls") or ([d["zpl"]] if d.get("zpl") else [])
            if not zpls:
                return self._json({"erro": "Nenhuma etiqueta para imprimir."}, 400)
            try:
                metodo = ""
                for z in zpls:
                    metodo = zebra.enviar_zpl(str(z), str(d.get("impressora") or ""))
                return self._json({"ok": True, "enviadas": len(zpls), "metodo": metodo})
            except Exception as e:
                return self._json({"erro": str(e)}, 500)
        if caminho == "/api/pc/janela3d":
            # VISUALIZAR 3D: guarda a página e o arquivo e abre numa janela de aplicativo (sem barra de endereço)
            if not self._do_proprio_pc():
                return self._json({"erro": "O 3D abre só neste computador."}, 403)
            d = self._corpo_json()
            ident = "".join(ch for ch in str(d.get("id") or "") if ch.isalnum())[:40]
            if not ident or not d.get("html"):
                return self._json({"erro": "Nada para mostrar."}, 400)
            import base64
            try:
                arq = base64.b64decode(d.get("arquivo") or "")
            except ValueError:
                arq = b""
            JANELAS_3D[ident] = {"html": str(d["html"]), "arquivo": arq, "tipo": str(d.get("tipo") or "")}
            for velho in list(JANELAS_3D)[:-12]:
                JANELAS_3D.pop(velho, None)
            url = f"http://127.0.0.1:{self.server.server_address[1]}/pc/3d/{ident}"
            def inteiro(v, padrao):
                try:
                    return int(float(v))
                except (TypeError, ValueError):
                    return padrao
            janela = (inteiro(d.get("x"), 40), inteiro(d.get("y"), 40), inteiro(d.get("largura"), 1400), inteiro(d.get("altura"), 860))
            return self._json({"ok": True, "url": url, "app": abrir_janela_app(url, *janela)})
        if caminho == "/api/pc/base_preenchida":
            # Agrupador | Base: o Python monta a base preenchida (sem o limite de memória da janela)
            if not self._do_proprio_pc():
                return self._json({"erro": "Só no próprio computador do sistema."}, 403)
            from ppcpm import base_preenchida
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 4 or n > 1024 * 1024 * 1024:
                return self._json({"erro": "Envio vazio ou grande demais."}, 400)
            corpo = self.rfile.read(n)
            tam = int.from_bytes(corpo[:4], "big")
            try:
                d = json.loads(corpo[4:4 + tam].decode("utf-8"))
                arq, r = base_preenchida.gerar(corpo[4 + tam:], d, lambda m: None)
            except base_preenchida.ForaDoPadrao as e:
                return self._json({"erro": str(e), "fallback": True}, 422)
            except Exception as e:  # noqa: BLE001
                import traceback
                traceback.print_exc()
                return self._json({"erro": str(e) or e.__class__.__name__}, 500)
            del corpo
            return self._enviar(200, arq, "application/octet-stream",
                                extra={"X-Resultado": quote(json.dumps(r)), "Access-Control-Expose-Headers": "X-Resultado"})
        if caminho == "/api/encerrar":
            # Botão "Sair" → [S] Sim: desliga o sistema por completo neste PC (só o próprio PC pode)
            if not self._do_proprio_pc():
                return self._json({"erro": "Só o próprio computador do sistema pode encerrá-lo."}, 403)
            self._json({"ok": True, "mensagem": "Sistema encerrado."})
            print("\nSistema encerrado pelo botão Sair. Até amanhã!")
            ESTADO["encerrar"] = True
            threading.Timer(0.5, ESTADO["servidor"].shutdown).start()
            return None
        return self._json({"erro": "Página não encontrada."}, 404)

    def _arquivos_pc(self, acao: str, q: dict):
        if not self._do_proprio_pc():
            return self._json({"erro": "Arquivos do PC só abrem no próprio computador do sistema."}, 403)
        try:
            if acao == "pacotes":   # Tela inicial: planilha de controle de pacotes (linhas só quando mudou)
                from ppcpm import pacotes
                return self._json(pacotes.estado(q.get("linhas") == "1", q.get("desde", "")))
            if acao == "pacotes_limpar":   # Atualizar da Tela inicial: zera para colocar uma planilha nova
                from ppcpm import pacotes
                return self._json(pacotes.limpar())
            if acao == "pacotes_config":   # guarda o caminho da planilha (escolhida na Tela inicial)
                from ppcpm import pacotes
                try:
                    return self._json(pacotes.definir(q.get("caminho", "")))
                except ValueError as e:
                    return self._json({"erro": str(e)}, 400)
                except Exception as e:  # noqa: BLE001
                    return self._json({"erro": f"Não consegui ler essa planilha: {e}"}, 400)
            if acao == "locais":   # rapido=1: resposta imediata (liga a ponte sem esperar o Acesso rápido do Windows)
                return self._json(arquivos_pc.locais(rapido=q.get("rapido") == "1"))
            if acao == "listar":   # todos=1: pasta inteira, sem marcar nos recentes (leitura de pastas pelos programas)
                todos = q.get("todos") == "1"
                return self._json(arquivos_pc.listar(q.get("caminho", ""), q.get("filtro", ""), recente=not todos,
                                                     limite=200000 if todos else arquivos_pc.LIMITE_LISTA))
            if acao == "buscar":
                return self._json(arquivos_pc.buscar(q.get("caminho", ""), q.get("termo", ""), q.get("filtro", "")))
            if acao == "favorito":
                return self._json(arquivos_pc.favoritar(q.get("caminho", ""), q.get("nome"), bool(q.get("remover"))))
            if acao == "explorador":
                arquivos_pc.abrir_no_explorador(q.get("caminho", ""))
                return self._json({"ok": True})
            if acao == "trecho":
                return self._enviar(200, arquivos_pc.ler_trecho(q.get("caminho", ""), int(q.get("ini", 0)), int(q.get("fim", 0))),
                                    "application/octet-stream")
            if acao == "arquivo":
                dados, nome, tipo, mod = arquivos_pc.ler_arquivo(q.get("caminho", ""))
                return self._enviar(200, dados, tipo, extra={"X-Nome": quote(nome), "X-Modificado": str(mod)})
            return self._json({"erro": "Ação desconhecida."}, 404)
        except PermissionError:
            return self._json({"erro": "Sem permissão para abrir esse local."}, 403)
        except (FileNotFoundError, NotADirectoryError) as e:
            return self._json({"erro": str(e)}, 404)
        except OSError as e:
            return self._json({"erro": f"Não foi possível acessar: {e.strerror or e}"}, 500)

    def _resumo(self):
        """Quadros da Tela inicial calculados em Python (precisa do token do login)."""
        token = self.headers.get("Authorization", "")
        token = (token[7:] if token.startswith("Bearer ") else token).strip()
        if not token:
            return self._json({"erro": "Faça login no sistema."}, 401)
        try:
            ops = banco.ler_ops(token)
        except Exception as e:
            return self._json({"erro": "Não foi possível ler o banco.", "detalhe": str(e)}, 502)
        c = config()
        return self._json(calculos.resumo_inicio(ops, c.get("pacote_atual"), c.get("obra_impressao")))


# ---------------- inicialização ----------------
def _navegador_app() -> str | None:
    """Chrome ou Edge deste PC, para abrir o sistema como aplicativo (sem barra de endereço e sem abas)."""
    if not sys.platform.startswith("win"):
        return None
    import os
    candidatos = []
    try:
        import winreg
        for raiz in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for exe in ("chrome.exe", "msedge.exe"):
                try:
                    with winreg.OpenKey(raiz, r"Software\Microsoft\Windows\CurrentVersion\App Paths" + "\\" + exe) as k:
                        candidatos.append(winreg.QueryValueEx(k, "")[0])
                except OSError:
                    pass
    except ImportError:
        pass
    for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""), os.environ.get("LOCALAPPDATA", "")):
        candidatos += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                       os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")]
    candidatos.sort(key=lambda c: "msedge" in c.lower())   # Chrome primeiro, Edge se não tiver Chrome
    return next((c for c in candidatos if c and os.path.isfile(c)), None)


def abrir_janela_app(endereco: str, x: int, y: int, largura: int, altura: int) -> bool:
    """Abre uma janela de aplicativo (só a tela, igual à janela do sistema). False = não deu (o sistema abre como pop-up)."""
    nav = _navegador_app()
    if not nav:
        return False
    import subprocess
    try:
        subprocess.Popen([nav, f"--app={endereco}", f"--window-size={max(600, largura)},{max(400, altura)}",
                          f"--window-position={x},{y}"], close_fds=True)
        return True
    except OSError:
        return False


def abrir_tela(endereco: str, como_app: bool = True) -> None:
    """Abre o sistema: como aplicativo (janela própria, só a tela do sistema) ou, se não der, no navegador."""
    nav = _navegador_app() if como_app else None
    if nav:
        import subprocess
        try:
            subprocess.Popen([nav, f"--app={endereco}"], close_fds=True)
            return
        except OSError:
            pass
    webbrowser.open(endereco)


def _ja_aberto() -> int | None:
    """Se o sistema já está aberto neste PC, devolve a porta (para não abrir duas vezes)."""
    for porta in range(PORTA_PADRAO, PORTA_PADRAO + 20):
        try:
            with urlopen(f"http://127.0.0.1:{porta}/api/status", timeout=0.6) as r:
                if json.loads(r.read().decode("utf-8")).get("app") == "PPCPM":
                    return porta
        except Exception:
            continue
    return None


def _porta_livre(inicial: int) -> int:
    for porta in range(inicial, inicial + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", porta)) != 0:
                return porta
    raise SystemExit("Nenhuma porta livre entre %d e %d." % (inicial, inicial + 19))


def _ip_na_rede() -> str:
    try:  # descobre o IP deste PC na rede (não envia nada)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def _garantir_icone() -> None:
    """Ícone do atalho num lugar fixo (pasta do sistema), que a atualização nunca apaga."""
    fixo, origem = PASTA_APP / "icone.ico", PASTA_APP / "ppcpm" / "web" / "icone.ico"
    try:
        if origem.exists() and (not fixo.exists() or fixo.stat().st_size == 0):
            fixo.write_bytes(origem.read_bytes())
    except OSError:
        pass


def _sem_modo_selecao() -> None:
    """Desliga a "Edição Rápida" da janela preta: um clique nela entrava no modo "Selecionar",
    que PAUSA o sistema (inclusive a atualização) até alguém apertar Esc."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-10)                      # entrada do console
        modo = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(modo)):
            k.SetConsoleMode(h, (modo.value & ~0x0040) | 0x0080)   # tira QUICK_EDIT, mantém EXTENDED_FLAGS
    except Exception:
        pass


def main(args: list[str]) -> int:
    _garantir_icone()
    _sem_modo_selecao()
    if "--verificar" in args:
        from ppcpm.diagnostico import relatorio
        print(relatorio())
        return 0
    if "--criar-atalho" in args:
        from ppcpm.atalho import garantir
        print(garantir())
        return 0
    if "--sem-atalho" not in args:
        from ppcpm.atalho import garantir_em_segundo_plano
        garantir_em_segundo_plano()      # o atalho da Área de Trabalho sumiu? cria de novo

    abrir_navegador = "--sem-navegador" not in args
    porta_aberta = _ja_aberto()
    if porta_aberta:
        print(f"O sistema já está aberto neste PC (porta {porta_aberta}). Abrindo no navegador...")
        if abrir_navegador:
            abrir_tela(f"http://127.0.0.1:{porta_aberta}", "--navegador" not in args)
        return 0

    na_rede = "--rede" in args
    porta = _porta_livre(PORTA_PADRAO)
    servidor = ThreadingHTTPServer(("0.0.0.0" if na_rede else "127.0.0.1", porta), Sistema)
    servidor.daemon_threads = True
    ESTADO.update(porta=porta, rede=na_rede, servidor=servidor)
    endereco = f"http://127.0.0.1:{porta}"
    reiniciar = threading.Event()

    print(f"SISTEMA - PPCPM ({versao()} · pacote Python {versao_python().get('pacote')}) aberto em {endereco}")
    if na_rede:
        print(f"Na rede da empresa: http://{_ip_na_rede()}:{porta}  (os arquivos deste PC continuam só aqui)")
    print("Deixe esta janela aberta enquanto usar o sistema. Para fechar: Ctrl+C.")
    no_drive = False
    if sys.platform.startswith("win"):
        from ppcpm.acesso_rapido import _rede
        no_drive = _rede(str(PASTA_APP))
        if no_drive:
            print("\n[AVISO] O sistema esta abrindo direto do drive da rede (" + str(PASTA_APP) + ").")
            print("        Essa copia do drive e so o INSTALADOR: ela nao se atualiza (para nao quebrar")
            print("        a pasta que todos usam). Rode o INSTALAR do drive: ele instala em")
            print("        C:\\Users\\<voce>\\SISTEMA-PPCPM, cria o atalho e esse se atualiza sozinho.\n")

    eh_repositorio = (PASTA_APP.parent / ".git").exists()   # cópia de desenvolvimento: não se atualiza sozinha
    if "--sem-atualizar" not in args and not no_drive and (not eh_repositorio or "--atualizar" in args):
        from ppcpm.atualizador import Agendador

        def pedir_reinicio():
            reiniciar.set()
            servidor.shutdown()

        ESTADO["agendador"] = Agendador(pedir_reinicio)
        ESTADO["agendador"].start()

    threading.Thread(target=pagina, daemon=True).start()   # já deixa a página pronta na memória
    if abrir_navegador:
        threading.Timer(1.0, lambda: abrir_tela(endereco, "--navegador" not in args)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nSistema fechado.")
    finally:
        servidor.server_close()
    return CODIGO_REINICIAR if reiniciar.is_set() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
