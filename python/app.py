"""
SISTEMA - PPCPM | versão Python (Flask)

Abre o mesmo sistema do HTML (mesma tela de login, menu, cores e programas),
agora servido pelo Python. Aos poucos, cada regra sai do JavaScript e passa
para os arquivos de ppcpm/ (começando pela Tela inicial, em calculos.py).

Rodar:
    pip install -r requirements.txt
    python app.py            -> http://127.0.0.1:5000
"""
from __future__ import annotations

from flask import Flask, Response, abort, jsonify, request

from ppcpm import banco, calculos
from ppcpm.config import MODULOS, OBRA_IMPRESSAO, PACOTE_ATUAL, PASTA_GERADO, VERSAO
from ppcpm.montagem import montar

app = Flask(__name__)


@app.get("/")
def sistema() -> Response:
    """Página completa do sistema, igual ao index.html publicado na Vercel."""
    return Response(montar(PASTA_GERADO), mimetype="text/html")


@app.get("/versao.json")
def versao():
    """Usado pelo aviso "Nova versão disponível" do sistema."""
    r = jsonify({"versao": VERSAO})
    r.headers["Cache-Control"] = "no-store"
    return r


@app.get("/api/modulos")
def modulos():
    """Lista dos programas PPCP do menu (Análise DBF, Agrupador, Roteirização...)."""
    return jsonify(MODULOS)


@app.get("/api/modulo/<pg>")
def modulo(pg: str) -> Response:
    """Abre um programa PPCP sozinho, fora do sistema (útil para testar)."""
    if not any(m["id"] == pg for m in MODULOS):
        abort(404)
    html = (PASTA_GERADO / "modulos" / f"{pg}.html").read_text(encoding="utf-8")
    return Response(html.replace("<\\/script", "</script"), mimetype="text/html")


@app.get("/api/resumo")
def resumo():
    """Quadros da Tela inicial calculados em Python. Precisa do token do login (Authorization: Bearer ...)."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        return jsonify({"erro": "Faça login no sistema."}), 401
    try:
        ops = banco.ler_ops(token)
    except Exception as e:  # sem conexão ou token vencido
        return jsonify({"erro": "Não foi possível ler o banco.", "detalhe": str(e)}), 502
    return jsonify(calculos.resumo_inicio(ops, PACOTE_ATUAL, OBRA_IMPRESSAO))


if __name__ == "__main__":
    print(f"SISTEMA - PPCPM ({VERSAO}) em http://127.0.0.1:5000")
    app.run(debug=True)
