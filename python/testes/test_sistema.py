"""Testes da versão Python. Rodar:  python -m pytest testes"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from ppcpm import calculos  # noqa: E402
from ppcpm.config import PASTA_GERADO, VERSAO  # noqa: E402
from ppcpm.montagem import montar  # noqa: E402


def test_remontagem_igual_ao_html():
    original = (RAIZ.parent / "index.html").read_text(encoding="utf-8")
    assert montar(PASTA_GERADO) == original, "Rode: python gerar_python.py"


def test_versao_bate_com_versao_json():
    import json
    publicado = json.loads((RAIZ.parent / "versao.json").read_text(encoding="utf-8"))
    assert publicado["versao"] == VERSAO


def test_resumo_inicio():
    ops = [
        {"id": "OP-1", "qtde": 500, "feito": 500, "st": "Concluída", "prazo": "2026-10-16"},
        {"id": "OP-2", "qtde": 300, "feito": 100, "st": "Em produção", "prazo": "2026-10-01"},
        {"id": "OP-3", "qtde": 200, "feito": 0, "st": "Em aberto", "prazo": "2026-12-01"},
    ]
    r = calculos.resumo_inicio(ops, 694, "2139-5-01", hoje="2026-10-31")
    assert r["total_realizados"] == 600 and r["total_planejado"] == 1000
    assert r["percentual_realizado"] == 60
    assert r["porcentagem_impresso"] == 33
    assert r["obras_impressas"] == 300 and r["obras_pendente"] == 200
    assert r["obras_para_impressao"] == "2139-5-01"
    assert calculos.numero_br(23232) == "23.232"
