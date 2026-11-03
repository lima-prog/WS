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
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
HTML_PADRAO = AQUI.parent / "index.html"

sys.path.insert(0, str(AQUI))
from ppcpm.gerador import PASTA_GERADO as DESTINO, gerar_de_html  # noqa: E402
from ppcpm.montagem import montar  # noqa: E402
from ppcpm import bibliotecas  # noqa: E402


def main(args: list[str]) -> int:
    origem = Path(next((a for a in args if not a.startswith("--")), HTML_PADRAO))
    html = origem.read_text(encoding="utf-8")
    if "--conferir" not in args:
        cfg = gerar_de_html(html, DESTINO)
        print(f"OK: {cfg['versao']} separado em {len(cfg['modulos'])} programas em {DESTINO}")
        bibliotecas.gerar_arquivos(AQUI / "bibliotecas")
        print("OK: listas de bibliotecas por seção atualizadas em bibliotecas/")
    igual = montar(DESTINO) == html
    print("Conferência:", "remontagem IDÊNTICA ao index.html" if igual else "DIFERENTE do index.html — rode o gerador de novo")
    return 0 if igual else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
