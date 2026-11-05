"""
BIBLIOTECAS POR SEÇÃO DO SISTEMA — fonte única da lista.

Hoje o sistema abre SEM nenhuma biblioteca (só o Python). Estas bibliotecas são para os
programas que vão sendo passados para Python: com elas instaladas, a leitura de DBF, Excel,
CSV e PDF fica no Python (mais rápido e sem travar o navegador).

Os arquivos bibliotecas/*.txt são gerados a partir daqui:  python gerar_python.py
Conferir o que está instalado:                           VERIFICAR_SISTEMA.bat
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path

# nome no pip: (nome para importar, linha do requirements, para que serve)
LIBS = {
    "pandas":     ("pandas", "pandas>=2.2", "Tabelas: ler, cruzar, somar e filtrar planilhas e DBF com rapidez"),
    "openpyxl":   ("openpyxl", "openpyxl>=3.1", "Ler e gravar Excel .xlsx (mantém abas e formatação)"),
    "XlsxWriter": ("xlsxwriter", "XlsxWriter>=3.2", "Gerar o Excel de saída com cores (verde/vermelho), larguras e filtros"),
    "xlrd":       ("xlrd", "xlrd>=2.0", "Ler Excel antigo .xls"),
    "pyxlsb":     ("pyxlsb", "pyxlsb>=1.0.10", "Ler Excel binário .xlsb"),
    "dbfread":    ("dbfread", "dbfread>=2.0.7", "Ler arquivos .DBF (CNC/ERP)"),
    "lxml":       ("lxml", "lxml>=5.2", "Ler o export do FOCCO que vem como .xls em HTML"),
    "pypdf":      ("pypdf", "pypdf>=4.3", "Juntar, separar e reordenar páginas de PDF (ordens, impressão casada)"),
    "pdfplumber": ("pdfplumber", "pdfplumber>=0.11", "Ler texto e tabelas de dentro do PDF (conferência do PDF gerado)"),
    "reportlab":  ("reportlab", "reportlab>=4.2", "Gerar PDF (etiquetas centralizadas, relatórios)"),
    "pywin32":    ("win32print", "pywin32>=306; sys_platform == 'win32'", "Imprimir direto na Zebra ZD220 (ZPL) e listar impressoras do Windows"),
    "ezdxf":      ("ezdxf", "ezdxf>=1.3", "Ler os arquivos DXF roteirizados (peças, medidas) direto no Python"),
    "requests":   ("requests", "requests>=2.32", "Enviar arquivos para a Intranet PCP"),
    "waitress":   ("waitress", "waitress>=3.0", "Servidor mais forte quando muitos usuários acessam pela rede"),
    "py7zr":      ("py7zr", "py7zr>=0.22", "Abrir arquivos compactados .7z como pasta"),
    "rarfile":    ("rarfile", "rarfile>=4.2", "Abrir arquivos .rar como pasta (precisa do 7-Zip ou WinRAR no PC)"),
}

PLANILHAS = ["pandas", "openpyxl", "XlsxWriter", "xlrd", "pyxlsb", "dbfread"]
PDF = ["pypdf", "pdfplumber"]

# (arquivo, nome da seção no sistema, bibliotecas da seção, opcionais)
SECOES = [
    ("nucleo", "Núcleo — Login, Tela inicial, banco Supabase, Arquivos do PC (pastas e compactados) e atualização automática", [], ["py7zr", "rarfile", "waitress"]),
    ("pg2", "Produção › Agrupador | Base", PLANILHAS + PDF, []),
    ("pg3", "Produção › Roteirização produção", ["pandas", "openpyxl", "XlsxWriter"], []),
    ("pg4", "Produção › Impressão Casada - ERP", PLANILHAS + PDF + ["reportlab"], []),
    ("pg5", "Produção › Impressão Casada | Multi obra", PLANILHAS + PDF + ["reportlab"], []),
    ("pg6", "Produção › Impressão Grupo - LIC", PLANILHAS + PDF + ["reportlab"], []),
    ("pg7", "Produção › Impressão - FLUXO 04", PLANILHAS + PDF + ["reportlab"], []),
    ("pg1", "Processo de validação › Análise da DBF X Focco - ERP", PLANILHAS + ["lxml"] + PDF, []),
    ("pg13", "Produção › Relatórios dos fluxos", ["pandas", "openpyxl", "XlsxWriter", "xlrd", "lxml", "ezdxf"], []),
    ("pg14", "Área de impressão › Engenharia (desenhos PDF)", ["pypdf", "pywin32"], ["py7zr", "rarfile"]),
    ("pg10", "Gerenciador de Roteiros › Alteração de Roteiros", ["pandas", "openpyxl", "XlsxWriter", "xlrd"], []),
    ("pg11", "Gerenciador de Roteiros › Acesso ao Intranet", ["requests"], []),
    ("pg12", "Área de impressão › Impressão de Etiquetas", ["pandas", "openpyxl", "xlrd", "dbfread", "reportlab", "pywin32"], []),
]


def todas() -> list[str]:
    vistas: list[str] = []
    for _, _, libs, opc in SECOES:
        for n in libs + opc:
            if n not in vistas:
                vistas.append(n)
    return vistas


def instalada(nome: str) -> str | None:
    """Versão instalada (ou None)."""
    try:
        from importlib.metadata import version
        return version(nome)
    except Exception:
        try:
            import_module(LIBS[nome][0])
            return "instalada"
        except Exception:
            return None


def _txt(titulo: str, nomes: list[str]) -> str:
    linhas = [f"# {titulo}", "# Instalar:  INSTALAR_BIBLIOTECAS.bat   (ou: python -m pip install -r este_arquivo.txt)", ""]
    if not nomes:
        linhas.append("# Nenhuma biblioteca obrigatória: funciona só com o Python.")
    for n in nomes:
        linhas.append(f"{LIBS[n][1]:<42} # {LIBS[n][2]}")
    return "\n".join(linhas) + "\n"


def gerar_arquivos(pasta: Path) -> None:
    """Escreve bibliotecas/*.txt e bibliotecas/BIBLIOTECAS.md."""
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "todas.txt").write_text(_txt("SISTEMA - PPCPM — TODAS as bibliotecas (todas as seções)", todas()), encoding="utf-8")
    for arq, nome, libs, opc in SECOES:
        (pasta / f"{arq}.txt").write_text(_txt(nome, libs + opc), encoding="utf-8")
    md = ["# Bibliotecas por seção do SISTEMA - PPCPM", "",
          "Gerado por `gerar_python.py` a partir de `ppcpm/bibliotecas.py`.", "",
          "**Hoje o sistema abre sem nenhuma biblioteca** (só o Python). As bibliotecas abaixo são para os programas",
          "que vão sendo passados para Python. Instale uma vez em cada PC com `INSTALAR_BIBLIOTECAS.bat`",
          "(ou sem internet, com a pasta `pacotes`, veja o README).", "",
          "## Por seção", "", "| Seção do sistema | Arquivo | Bibliotecas |", "|---|---|---|"]
    for arq, nome, libs, opc in SECOES:
        lista = (", ".join(libs) or "nenhuma obrigatória") + (" (opcional: " + ", ".join(opc) + ")" if opc else "")
        md.append(f"| {nome.replace('|', '¦')} | `{arq}.txt` | {lista} |")
    md += ["", "## O que cada biblioteca faz", "", "| Biblioteca | Para que serve no sistema |", "|---|---|"]
    md += [f"| `{n}` | {LIBS[n][2]} |" for n in todas()]
    (pasta / "BIBLIOTECAS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
