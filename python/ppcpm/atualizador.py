"""
ATUALIZAÇÃO AUTOMÁTICA — mantém as DUAS versões iguais neste PC (HTML e Python).

Toda versão nova publicada (GitHub lima-prog/ws → Vercel) chega sozinha aqui:

  1. Código Python novo (python/versao_python.json mudou)
       -> baixa a pasta python/ do GitHub, troca os arquivos e reinicia o sistema sozinho.
  2. Versão nova do sistema (versao.json / index.html mudou)
       -> baixa o index.html (GitHub ou, se bloqueado, a Vercel) e regenera ppcpm/gerado/.
          Não precisa reiniciar: na próxima tela o usuário vê "Nova versão disponível".

Confere ao abrir e a cada 1 minuto (pela Vercel, que publica na hora). Nunca mexe em: dados_locais/, .venv/, .python/, pacotes/.
Desligar: python app.py --sem-atualizar
"""
from __future__ import annotations

import io
import json
import shutil
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from .config import ARQ_VERSAO_PYTHON, PASTA_APP, PASTA_DADOS, PASTA_GERADO, versao, versao_python
from .gerador import gerar_de_html

GITHUB_RAW = "https://raw.githubusercontent.com/lima-prog/ws/main/"
GITHUB_ZIP = "https://codeload.github.com/lima-prog/ws/zip/refs/heads/main"
VERCEL = "https://sistemaoperacional-grupoprojeartv92.vercel.app/"
INTERVALO_SEG = 60          # confere a cada 1 minuto (só um arquivinho de versão, bem leve)
PROTEGIDOS = {"dados_locais", ".venv", ".python", "pacotes", ".atualizando", "__pycache__"}
ARQ_LOG = PASTA_DADOS / "atualizacoes.log"


def registrar(msg: str) -> None:
    linha = f"{datetime.now():%d/%m/%Y %H:%M:%S}  {msg}"
    print("  [atualização] " + msg)
    try:
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        with open(ARQ_LOG, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except OSError:
        pass


def _baixar(url: str, tempo: int = 30) -> bytes:
    pedido = Request(url + ("&" if "?" in url else "?") + f"t={int(time.time())}",
                     headers={"User-Agent": "SISTEMA-PPCPM", "Cache-Control": "no-cache"})
    with urlopen(pedido, timeout=tempo) as r:
        return r.read()


def _json(urls: list[str]) -> dict | None:
    for u in urls:
        try:
            return json.loads(_baixar(u, 15).decode("utf-8"))
        except Exception:
            continue
    return None


def versoes_remotas() -> dict:
    # Vercel primeiro: publica em segundos e não guarda cache. O GitHub (raw) guarda até 5 min: só reserva.
    html = _json([VERCEL + "versao.json", GITHUB_RAW + "versao.json"])
    py = _json([VERCEL + "versao_python.json", GITHUB_RAW + "python/versao_python.json"])
    return {"html": (html or {}).get("versao"), "python": (py or {}).get("pacote")}


def atualizar_html(versao_remota: str) -> bool:
    for url in (VERCEL + "index.html", VERCEL, GITHUB_RAW + "index.html"):
        try:
            html = _baixar(url, 90).decode("utf-8")
            if f"const VERSAO='{versao_remota}'" not in html:
                continue
            gerar_de_html(html, PASTA_GERADO)
            registrar(f"Sistema atualizado para {versao_remota} (fonte: {url.split('/')[2]}).")
            return True
        except Exception as e:  # tenta a próxima fonte
            registrar(f"Falha ao baixar de {url.split('/')[2]}: {e}")
    return False


def atualizar_python(pacote_remoto) -> bool:
    try:
        dados = _baixar(GITHUB_ZIP, 180)
    except Exception as e:
        registrar(f"Não foi possível baixar o código Python novo: {e}")
        return False
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        nomes = z.namelist()
        raiz = next((n for n in nomes if n.count("/") == 2 and n.endswith("/python/")), None)
        if not raiz:
            registrar("Pacote baixado não tem a pasta python/.")
            return False
        if not any(n.startswith(raiz + "app.py") for n in nomes):
            registrar("Pacote baixado está incompleto (sem app.py).")
            return False
        try:
            no_zip = json.loads(z.read(raiz + ARQ_VERSAO_PYTHON.name).decode("utf-8")).get("pacote")
        except Exception:
            no_zip = None
        if no_zip != pacote_remoto:
            registrar(f"O GitHub ainda está entregando o pacote {no_zip}; tento de novo em 1 minuto.")
            return False
        temp = PASTA_APP / ".atualizando"
        shutil.rmtree(temp, ignore_errors=True)
        for n in nomes:
            if not n.startswith(raiz) or n.endswith("/"):
                continue
            rel = n[len(raiz):]
            if rel.split("/")[0] in PROTEGIDOS:
                continue
            destino = temp / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(z.read(n))
    # Copia só o que mudou, arquivo por arquivo, sem apagar pastas. Assim o ícone do atalho e o
    # que está em uso nunca somem. Só a pasta gerado/ é trocada inteira (para não misturar versões).
    novos = {p.relative_to(temp) for p in temp.rglob("*") if p.is_file()}
    for rel in sorted(novos):
        if rel.name == ARQ_VERSAO_PYTHON.name and len(rel.parts) == 1:
            continue
        if rel.parts[:2] == ("ppcpm", "gerado"):
            continue
        origem, alvo = temp / rel, PASTA_APP / rel
        if alvo.is_file() and alvo.read_bytes() == origem.read_bytes():
            continue
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, alvo)
    if (temp / "ppcpm" / "gerado").is_dir():
        shutil.rmtree(PASTA_GERADO, ignore_errors=True)
        shutil.copytree(temp / "ppcpm" / "gerado", PASTA_GERADO)
    # arquivos de código que saíram do sistema (nunca mexe em ícones, dados_locais, .venv...)
    for pasta in ("ppcpm", "bibliotecas", "ferramentas", "testes"):
        for velho in (PASTA_APP / pasta).rglob("*"):
            rel = velho.relative_to(PASTA_APP)
            if (velho.is_file() and rel not in novos and rel.parts[:2] != ("ppcpm", "gerado")
                    and "__pycache__" not in rel.parts and velho.suffix.lower() != ".ico"):
                try:
                    velho.unlink()
                except OSError:
                    pass
    shutil.copy2(temp / ARQ_VERSAO_PYTHON.name, ARQ_VERSAO_PYTHON)   # por último: marca como concluído
    shutil.rmtree(temp, ignore_errors=True)
    registrar(f"Código Python atualizado para o pacote {pacote_remoto}. Reiniciando o sistema...")
    return True


def verificar_agora() -> dict:
    """Confere e aplica as atualizações. Devolve o que mudou."""
    r = {"python": False, "html": False, "erro": None}
    remoto = versoes_remotas()
    if remoto["html"] is None and remoto["python"] is None:
        r["erro"] = "Sem acesso ao GitHub nem à Vercel agora (internet ou rede da empresa)."
        return r
    local_py = versao_python().get("pacote", 0)
    if remoto["python"] is not None and remoto["python"] != local_py:
        r["python"] = atualizar_python(remoto["python"])
    if remoto["html"] and remoto["html"] != versao():
        r["html"] = atualizar_html(remoto["html"])
    return r


class Agendador(threading.Thread):
    """Confere atualizações em segundo plano. Se o código Python mudar, chama reiniciar()."""

    def __init__(self, reiniciar):
        super().__init__(daemon=True, name="atualizador")
        self.reiniciar = reiniciar
        self.ultimo: dict = {}

    def run(self) -> None:
        time.sleep(2)
        while True:
            try:
                self.ultimo = dict(verificar_agora(), quando=datetime.now().strftime("%d/%m/%Y %H:%M"))
                if self.ultimo.get("python"):
                    self.reiniciar()
                    return
            except Exception as e:
                registrar(f"Erro ao conferir atualizações: {e}")
            time.sleep(INTERVALO_SEG)
