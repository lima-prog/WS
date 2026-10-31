"""
GERADOR DA VERSÃO PYTHON — SISTEMA PPCPM (Grupo Projeart)
==========================================================

O que faz:
    Lê o index.html (o sistema publicado na Vercel) e separa ele em partes
    organizadas dentro de  python/ppcpm/gerado/ :

        molde.html          estrutura da página (login, menu, telas) com marcadores
        css/sistema.css     todo o visual (cores, botões, cartões, tema claro/escuro)
        js/supabase.js      biblioteca do banco de dados (Supabase)
        js/sistema.js       lógica principal (login, Tela inicial, menu, avisos...)
        modulos/pgN.html    cada programa PPCP embutido (Análise DBF, Agrupador...)
        config.json         versão, pacote atual, obra para impressão, menu, Supabase
        MAPA.md             mapa de tudo que foi separado (tamanho de cada parte)

    O app Python (app.py) junta essas partes de volta e entrega a MESMA página.
    Assim a versão Python fica sempre no mesmo esquema do HTML.

Como usar (a cada versão nova):
    cd python
    python gerar_python.py            -> separa o index.html em partes
    python gerar_python.py --conferir -> confere se a remontagem ficou idêntica
    python app.py                     -> abre o sistema em http://127.0.0.1:5000
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
HTML_PADRAO = AQUI.parent / "index.html"
DESTINO = AQUI / "ppcpm" / "gerado"

sys.path.insert(0, str(AQUI))
from ppcpm.montagem import montar, MARCA  # noqa: E402


def _bloco(s: str, abre: str, inicio: int = 0) -> tuple[int, int, int]:
    """Acha um bloco <script>/<style>. Devolve (início da tag, início do conteúdo, fim da tag de fechamento)."""
    a = s.index(abre, inicio)
    c = s.index(">", a) + 1
    tag = "</style>" if abre.startswith("<style") else "</script>"
    f = s.index(tag, c)
    return a, c, f + len(tag)


def _const(js: str, nome: str, padrao=None):
    m = re.search(r"const " + nome + r"\s*=\s*('([^']*)'|(\d+))", js)
    if not m:
        return padrao
    return m.group(2) if m.group(2) is not None else int(m.group(3))


def separar(html: str) -> dict:
    partes: dict[str, str] = {}
    molde: list[str] = []
    pos = 0

    # 1) CSS principal (o primeiro <style> da página)
    a, c, f = _bloco(html, "<style>")
    molde.append(html[pos:a]); molde.append(MARCA.format("css"))
    partes["css/sistema.css"] = html[c:f - len("</style>")]
    pos = f

    # 2) biblioteca do Supabase
    a, c, f = _bloco(html, "<script>/* supabase-js", pos)
    molde.append(html[pos:a]); molde.append(MARCA.format("supabase"))
    partes["js/supabase.js"] = html[c:f - len("</script>")]
    pos = f

    # 3) programas PPCP embutidos (<script type="text/plain" id="src-pgN">)
    modulos = []
    abre_modulo = re.compile(r'<script type="text/plain" id="src-(pg\d+)">')
    while True:
        m = abre_modulo.search(html, pos)
        if not m:
            break
        pg = m.group(1)
        f = html.index("</script>", m.end())
        molde.append(html[pos:m.start()]); molde.append(MARCA.format("modulo:" + pg))
        partes[f"modulos/{pg}.html"] = html[m.end():f]
        modulos.append(pg)
        pos = f + len("</script>")

    # 4) lógica principal (último <script> da página)
    a = html.rindex("<script>")
    f = html.rindex("</script>")
    molde.append(html[pos:a]); molde.append(MARCA.format("sistema"))
    partes["js/sistema.js"] = html[a + len("<script>"):f]
    molde.append(html[f + len("</script>"):])

    partes["molde.html"] = "".join(molde)

    js = partes["js/sistema.js"]
    prog = re.search(r"const PROG=(\[.*?\]\]);", js)
    menu = json.loads(prog.group(1)) if prog else []
    sb = re.search(r"SB_URL='([^']+)',SB_KEY='([^']+)'", js)
    config = {
        "versao": _const(js, "VERSAO", ""),
        "pacote_atual": _const(js, "PACOTE_ATUAL"),
        "obra_impressao": _const(js, "OBRA_IMPRESSAO"),
        "supabase_url": sb.group(1) if sb else "",
        "supabase_chave_publica": sb.group(2) if sb else "",
        "modulos": [
            {"id": pid, "nome": nome, "titulo": titulo, "arquivo": f"modulos/{pid}.html"}
            for pid, nome, titulo in menu
        ],
        "modulos_no_arquivo": modulos,
    }
    partes["config.json"] = json.dumps(config, ensure_ascii=False, indent=2) + "\n"

    linhas = [f"# Mapa do sistema — {config['versao']}", "",
              "Gerado por `gerar_python.py` a partir do `index.html`. Não edite à mão: rode o gerador de novo.", "",
              "| Parte | Tamanho |", "|---|---|"]
    for nome, txt in partes.items():
        linhas.append(f"| `{nome}` | {len(txt.encode('utf-8')) / 1024:,.0f} KB |".replace(",", "."))
    linhas += ["", "## Menu de programas", "", "| ID | Nome no menu | Título da tela |", "|---|---|---|"]
    cel = lambda t: str(t).replace("|", "\\|")
    linhas += [f"| {m['id']} | {cel(m['nome'])} | {cel(m['titulo'])} |" for m in config["modulos"]]
    partes["MAPA.md"] = "\n".join(linhas) + "\n"
    return partes


def gravar(partes: dict, destino: Path = DESTINO) -> None:
    for nome, txt in partes.items():
        p = destino / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8", newline="")
    # remove módulos que saíram do sistema
    for velho in (destino / "modulos").glob("pg*.html"):
        if f"modulos/{velho.name}" not in partes:
            velho.unlink()


def main(args: list[str]) -> int:
    origem = Path(next((a for a in args if not a.startswith("--")), HTML_PADRAO))
    html = origem.read_text(encoding="utf-8")
    if "--conferir" not in args:
        partes = separar(html)
        gravar(partes)
        cfg = json.loads(partes["config.json"])
        print(f"OK: {cfg['versao']} separado em {len(partes)} partes ({len(cfg['modulos'])} programas) em {DESTINO}")
    igual = montar(DESTINO) == html
    print("Conferência:", "remontagem IDÊNTICA ao index.html" if igual else "DIFERENTE do index.html — rode o gerador de novo")
    return 0 if igual else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
