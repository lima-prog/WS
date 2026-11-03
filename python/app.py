"""
SISTEMA - PPCPM | versão Python

Abre o mesmo sistema do HTML (mesma tela de login, menu, cores e programas),
servido pelo Python. Usa SÓ o que já vem com o Python: não precisa de pip,
de internet para instalar nada, nem de administrador. Funciona no PC da empresa.

Rodar:
    python app.py            -> só neste computador
    python app.py --rede     -> outros computadores da rede também abrem
    python app.py --sem-navegador   -> não abre o navegador sozinho
"""
from __future__ import annotations

import json
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))  # Python portátil também acha a pasta ppcpm

from ppcpm import banco, calculos
from ppcpm.config import MODULOS, OBRA_IMPRESSAO, PACOTE_ATUAL, PASTA_GERADO, VERSAO
from ppcpm.montagem import montar

PORTA_PADRAO = 5000


class Sistema(BaseHTTPRequestHandler):
    server_version = "PPCPM"

    # ---------- respostas ----------
    def _enviar(self, codigo: int, corpo: str | bytes, tipo: str, sem_cache: bool = False) -> None:
        dados = corpo.encode("utf-8") if isinstance(corpo, str) else corpo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        if sem_cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(dados)

    def _json(self, obj, codigo: int = 200) -> None:
        self._enviar(codigo, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", sem_cache=True)

    def log_message(self, formato, *args):  # janela mais limpa: só mostra erros
        if args and str(args[1]).startswith(("4", "5")) and str(args[1]) != "404":
            sys.stderr.write("  aviso: %s\n" % (formato % args))

    # ---------- rotas ----------
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        caminho = urlparse(self.path).path.rstrip("/") or "/"

        if caminho in ("/", "/index.html"):
            # Página completa do sistema, igual ao index.html publicado na Vercel
            return self._enviar(200, montar(PASTA_GERADO), "text/html; charset=utf-8", sem_cache=True)

        if caminho == "/versao.json":
            # Usado pelo aviso "Nova versão disponível"
            return self._json({"versao": VERSAO})

        if caminho == "/api/modulos":
            # Programas PPCP do menu (Análise DBF, Agrupador, Roteirização...)
            return self._json(MODULOS)

        if caminho.startswith("/api/modulo/"):
            # Abre um programa PPCP sozinho, fora do sistema (útil para testar)
            pg = caminho.rsplit("/", 1)[-1]
            if not any(m["id"] == pg for m in MODULOS):
                return self._json({"erro": "Programa não encontrado."}, 404)
            html = (PASTA_GERADO / "modulos" / f"{pg}.html").read_text(encoding="utf-8")
            return self._enviar(200, html.replace("<\\/script", "</script"), "text/html; charset=utf-8")

        if caminho == "/api/resumo":
            # Quadros da Tela inicial calculados em Python (precisa do token do login)
            token = self.headers.get("Authorization", "")
            token = (token[7:] if token.startswith("Bearer ") else token).strip()
            if not token:
                return self._json({"erro": "Faça login no sistema."}, 401)
            try:
                ops = banco.ler_ops(token)
            except Exception as e:  # sem conexão ou token vencido
                return self._json({"erro": "Não foi possível ler o banco.", "detalhe": str(e)}, 502)
            return self._json(calculos.resumo_inicio(ops, PACOTE_ATUAL, OBRA_IMPRESSAO))

        if caminho == "/favicon.ico":
            self.send_response(204)
            return self.end_headers()

        return self._json({"erro": "Página não encontrada."}, 404)


def _porta_livre(host: str, inicial: int) -> int:
    """Usa a 5000; se estiver ocupada (outro programa), tenta 5001, 5002..."""
    for porta in range(inicial, inicial + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", porta)) != 0:
                return porta
    raise SystemExit("Nenhuma porta livre entre %d e %d." % (inicial, inicial + 19))


def _ip_na_rede() -> str:
    try:  # descobre o IP deste computador na rede (não envia nada)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def main(args: list[str]) -> None:
    na_rede = "--rede" in args
    host = "0.0.0.0" if na_rede else "127.0.0.1"
    porta = _porta_livre(host, PORTA_PADRAO)
    servidor = ThreadingHTTPServer((host, porta), Sistema)
    endereco = f"http://127.0.0.1:{porta}"

    print(f"SISTEMA - PPCPM ({VERSAO}) aberto em {endereco}")
    if na_rede:
        print(f"Na rede da empresa: http://{_ip_na_rede()}:{porta}")
    print("Deixe esta janela aberta enquanto usar o sistema. Para fechar: Ctrl+C.")

    if "--sem-navegador" not in args:
        threading.Timer(1.0, lambda: webbrowser.open(endereco)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nSistema fechado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main(sys.argv[1:])
