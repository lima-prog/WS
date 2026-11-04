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
    python app.py --sem-navegador    -> não abre o navegador sozinho (ex.: ao ligar o Windows)
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
            if acao == "locais":
                return self._json(arquivos_pc.locais())
            if acao == "listar":
                return self._json(arquivos_pc.listar(q.get("caminho", ""), q.get("filtro", "")))
            if acao == "buscar":
                return self._json(arquivos_pc.buscar(q.get("caminho", ""), q.get("termo", ""), q.get("filtro", "")))
            if acao == "favorito":
                return self._json(arquivos_pc.favoritar(q.get("caminho", ""), q.get("nome"), bool(q.get("remover"))))
            if acao == "explorador":
                arquivos_pc.abrir_no_explorador(q.get("caminho", ""))
                return self._json({"ok": True})
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


def main(args: list[str]) -> int:
    _garantir_icone()
    if "--verificar" in args:
        from ppcpm.diagnostico import relatorio
        print(relatorio())
        return 0

    abrir_navegador = "--sem-navegador" not in args
    porta_aberta = _ja_aberto()
    if porta_aberta:
        print(f"O sistema já está aberto neste PC (porta {porta_aberta}). Abrindo no navegador...")
        if abrir_navegador:
            webbrowser.open(f"http://127.0.0.1:{porta_aberta}")
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

    eh_repositorio = (PASTA_APP.parent / ".git").exists()   # cópia de desenvolvimento: não se atualiza sozinha
    if "--sem-atualizar" not in args and (not eh_repositorio or "--atualizar" in args):
        from ppcpm.atualizador import Agendador

        def pedir_reinicio():
            reiniciar.set()
            servidor.shutdown()

        ESTADO["agendador"] = Agendador(pedir_reinicio)
        ESTADO["agendador"].start()

    threading.Thread(target=pagina, daemon=True).start()   # já deixa a página pronta na memória
    if abrir_navegador:
        threading.Timer(1.0, lambda: webbrowser.open(endereco)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nSistema fechado.")
    finally:
        servidor.server_close()
    return CODIGO_REINICIAR if reiniciar.is_set() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
