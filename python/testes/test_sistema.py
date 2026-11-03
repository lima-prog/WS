"""Testes da versão Python. Rodar:  python -m pytest testes"""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from ppcpm import arquivos_pc, bibliotecas, calculos  # noqa: E402
from ppcpm.config import PASTA_GERADO, config, versao  # noqa: E402
from ppcpm.gerador import gerar_de_html  # noqa: E402
from ppcpm.montagem import PONTE_MODULO, PONTE_PAGINA, montar  # noqa: E402

INDEX = RAIZ.parent / "index.html"
precisa_index = pytest.mark.skipif(not INDEX.exists(), reason="index.html só existe no repositório")


@precisa_index
def test_remontagem_igual_ao_html():
    assert montar(PASTA_GERADO) == INDEX.read_text(encoding="utf-8"), "Rode: python gerar_python.py"


@precisa_index
def test_versao_bate_com_versao_json():
    publicado = json.loads((RAIZ.parent / "versao.json").read_text(encoding="utf-8"))
    assert publicado["versao"] == versao()


@precisa_index
def test_gerador_em_outra_pasta(tmp_path):
    cfg = gerar_de_html(INDEX.read_text(encoding="utf-8"), tmp_path / "gerado")
    assert cfg["versao"] == versao() and (tmp_path / "gerado" / "molde.html").exists()
    with pytest.raises(ValueError):
        gerar_de_html("<html>outra coisa</html>", tmp_path / "x")


def test_ponte_entra_em_todos_os_programas():
    html = montar(PASTA_GERADO, com_ponte=True)
    assert html.count(PONTE_MODULO) == len(config()["modulos_no_arquivo"])
    assert html.count(PONTE_PAGINA) == 1                      # e uma vez na página principal
    assert PONTE_PAGINA not in montar(PASTA_GERADO)          # versão da Vercel continua sem a ponte


def test_resumo_inicio():
    ops = [
        {"id": "OP-1", "qtde": 500, "feito": 500, "st": "Concluída", "prazo": "2026-10-16"},
        {"id": "OP-2", "qtde": 300, "feito": 100, "st": "Em produção", "prazo": "2026-10-01"},
        {"id": "OP-3", "qtde": 200, "feito": 0, "st": "Em aberto", "prazo": "2026-12-01"},
    ]
    r = calculos.resumo_inicio(ops, 694, "2139-5-01", hoje="2026-10-31")
    assert r["total_realizados"] == 600 and r["total_planejado"] == 1000
    assert r["percentual_realizado"] == 60 and r["porcentagem_impresso"] == 33
    assert r["obras_impressas"] == 300 and r["obras_pendente"] == 200
    assert r["obras_para_impressao"] == "2139-5-01"
    assert calculos.numero_br(23232) == "23.232"


def test_arquivos_do_pc(tmp_path, monkeypatch):
    monkeypatch.setattr(arquivos_pc, "ARQ_PASTAS", tmp_path / "pastas.json")
    (tmp_path / "Obra 2139").mkdir()
    (tmp_path / "Obra 2139" / "CNC_2139-5-01.DBF").write_bytes(b"dbf")
    (tmp_path / "foco.xlsx").write_bytes(b"x")
    (tmp_path / "~$foco.xlsx").write_bytes(b"lixo")          # arquivo temporário do Excel: some da lista
    r = arquivos_pc.listar(f'"{tmp_path}"', ".dbf")             # caminho colado com aspas
    assert [i["nome"] for i in r["itens"]] == ["Obra 2139"] and r["ocultos_pelo_filtro"] == 1
    b = arquivos_pc.buscar(str(tmp_path), "2139-5", ".dbf")
    assert [i["nome"] for i in b["itens"]] == ["CNC_2139-5-01.DBF"]
    dados, nome, _, _ = arquivos_pc.ler_arquivo(b["itens"][0]["caminho"])
    assert dados == b"dbf" and nome == "CNC_2139-5-01.DBF"
    loc = arquivos_pc.favoritar(str(tmp_path), "Pasta teste")
    assert loc["favoritos"][0]["nome"] == "Pasta teste" and str(tmp_path) in loc["recentes"]
    with pytest.raises(FileNotFoundError):
        arquivos_pc.listar(str(tmp_path / "nao-existe"))


def test_listas_de_bibliotecas_atualizadas(tmp_path):
    bibliotecas.gerar_arquivos(tmp_path)
    for arq in tmp_path.iterdir():
        assert arq.read_text(encoding="utf-8") == (RAIZ / "bibliotecas" / arq.name).read_text(encoding="utf-8"), \
            "Rode: python gerar_python.py"
    assert {s[0] for s in bibliotecas.SECOES} >= {m["id"] for m in config()["modulos"]}   # toda seção do menu tem lista
