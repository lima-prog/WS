#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPCP — Validador de Fluxos & Preenchedor de Base (Projeart)
=============================================================

O que faz:
  1. Agrupa varios arquivos de DBF (varios formatos) e padroniza todos
     no layout de 95 colunas usado pela ferramenta HTML (ESQUEMA_DBF).
  2. Le o Relatorio de Fluxos (aba "Relatório Consolidado") como
     referencia — NUNCA e alterado nem salvo, so leitura.
  3. Cruza OF + Marca pra marcar automaticamente o X nas colunas de
     maquina de Fluxo 1-4 (G6m / G3m / BC / CH) — o resto (Perfiladeira
     L/U-C, ACP, etc.) fica igual estava, nao e mexido.
  4. Escreve o consolidado (NUM_COM -> TIPO PINTURA) na aba "DBF" da
     planilha BASE real, e gera uma copia NOVA em .xlsx (nunca
     sobrescreve o arquivo original), com o nome do lote no nome do
     arquivo.

Por que .xlsx e nao .xlsb: nenhuma biblioteca gratuita (Python ou JS)
escreve .xlsb com fidelidade total — regravar em .xlsb quebrou formulas
na primeira tentativa (feita em navegador). openpyxl em .xlsx preserva
formulas, estilos e as demais abas de forma muito mais confiavel.
A BASE precisa entrar como .xlsx (Salvar Como no Excel, se ainda
estiver em .xlsb). Os DBFs individuais e o Relatorio de Fluxos podem
ser .xlsx/.xlsm/.xls/.xlsb/.csv/.txt/.tsv.

Dependencias:  pip install openpyxl pyxlsb pandas PyQt5 xlrd
Opcional (so p/ converter .xlsb -> .xlsx automaticamente, Windows+Excel):
               pip install pywin32
"""

import sys
import os
import collections
import io
import json
import re
import time
import threading
import inspect
import unicodedata
import zipfile
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta
from html.parser import HTMLParser

import openpyxl
from openpyxl.utils import get_column_letter

# --- blindagem: algumas planilhas complexas (ex.: convertidas de .xlsb por
# outra ferramenta) trazem uma "Definição de Nome" de área de impressão
# vazia/corrompida que faz o openpyxl quebrar já na leitura. Isso não tem
# nada a ver com os dados da DBF — só evita que a leitura pare por causa
# de uma configuração de impressão quebrada.
import openpyxl.worksheet.print_settings as _print_settings
_orig_print_titles_from_string = _print_settings.PrintTitles.from_string.__func__


def _safe_print_titles_from_string(cls, value):
    if not value:
        return cls()
    try:
        return _orig_print_titles_from_string(cls, value)
    except Exception:
        return cls()


_print_settings.PrintTitles.from_string = classmethod(_safe_print_titles_from_string)

try:
    from pyxlsb import open_workbook as open_xlsb
except ImportError:
    open_xlsb = None

try:                                    # atualização automática da planilha LANTEK_SKA (ver ska_lantek.py)
    from validador_fluxos import ska_lantek
except ImportError:
    try:
        import ska_lantek
    except ImportError:
        ska_lantek = None

import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QLineEdit, QTableWidget,
    QTableWidgetItem, QMessageBox, QGroupBox, QAbstractItemView, QSplitter,
    QHeaderView, QTabWidget, QScrollArea, QPlainTextEdit, QFrame,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QComboBox, QDialog, QColorDialog, QInputDialog, QMenu,
    QButtonGroup
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QPixmap, QPainter, QIcon
import base64


# ═══════════════════════════════════════════════════════════════════
# ESQUEMA PADRÃO DA DBF (mesmas 95 colunas da ferramenta HTML)
# ═══════════════════════════════════════════════════════════════════
ESQUEMA_DBF = [
    "NUM_COM", "NUM_DIS", "TRA_PEZ", "MAR_PEZ", "DES_PEZ", "POS_PEZ", "QTA_PEZ",
    "NOM_PRO", "LUN_PRO", "LAR_PRO", "SPE_PRO", "MAT_PRO", "PUN_LIS", "SUN_LIS",
    "IDENTIFICADOR", "ESPESSURA", "Desenho", "Descrição", "Material", "Chapas",
    "Peso", "Qtd", "MARCA+TRECHO", "adcionar1", "adcionar2", "ÚLTIMO_PROCESSO",
    "REVISÃO", "FUR", "DESENVOLVIMENTO", "VOLUME", "Identifier", "END_MARCA",
    "GRUPO LIC", "ACABAMENTO", "TIPO PINTURA",
    "COR PINTURA1", "COR PINTURA2", "COR PINTURA3",
    "COMP B - PINT LIQ 1", "COMP C - PINT LIQ 1", "COMP B - PINT LIQ 2",
    "COMP C - PINT LIQ 2", "COMP B - PINT LIQ 3", "COMP C - PINT LIQ 3",
    "PESO_ESP_SV_1", "MICRAGEM1", "PESO_ESP_SV_2", "MICRAGEM2",
    "PESO_ESP_SV_3", "MICRAGEM3", "Grupo FOCCO", "Peso Total", "Pintura Total",
    "QTD_PINTURA_1", "QTD_PINTURA_2", "QTD_PINTURA_3",
    "QTD - COMP B - PINT LIQ 1", "QTD - COMP C - PINT LIQ 1",
    "QTD - COMP B - PINT LIQ 2", "QTD - COMP C - PINT LIQ 2",
    "QTD - COMP B - PINT LIQ 3", "QTD - COMP C - PINT LIQ 3", "PINT_DIF",
    "Desenho FOCCO", "Tempo Rep", "Descrição Focco", "Material Focco",
    "Almoxarifado", "LINHA", "TRECHO", "TIPO LINHA", "PREFIXO_CONJUNTO",
    "PREFIXO PEÇA", "COMP", "LARGURA", "ALTURA", "AREA UNIT", "AREA TOTAL",
    "PESO UNIT", "PESO TOTAL", "TIPO MAT", "ESP ALMA", "ESP FLANGE",
    "TEKLA COD FOCCO", "PERFIL TEKLA", "POLIVIGA", "DESENHISTA", "PROJETISTA",
    "FLG_REC", "TIPO_GEOM", "RECORTE", "DIAM_FURO", "FURO_OBL", "QTD_FUROS",
    "Unid Med",
]

# Nomes alternativos (DBFs antigas usam o cabecalho "amigavel")
ALIAS_DBF = {
    'NUM_DIS': ['N LIBERACAO', 'Nº LIBERAÇÃO'],
    'TRA_PEZ': ['ULT. PROCESSO 1', 'ÚLT. PROCESSO 1'],
    'MAR_PEZ': ['MARCA'],
    'DES_PEZ': ['PRODUTO ACABADO'],
    'POS_PEZ': ['POSICAO', 'POSIÇÃO'],
    'QTA_PEZ': ['QTD PC TT GERAL', 'QTD PÇ TT GERAL'],
    'NOM_PRO': ['MATERIA-PRIMA', 'MATÉRIA-PRIMA'],
    'LUN_PRO': ['COMPRIMENTO (mm)'],
    'LAR_PRO': ['LARGURA (mm)'],
    'SPE_PRO': ['ESPESSURA (mm)'],
    'MAT_PRO': ['COMPOSICAO MP 1', 'COMPOSIÇÃO MP 1'],
    'PUN_LIS': ['PESO UNIT (KG)'],
    'SUN_LIS': ['AREA (mm)', 'ÁREA (mm)'],
    'IDENTIFICADOR': ['GEOMETRIA PERFIL'],
    'ESPESSURA': ['ESPESSURA GERAL (mm)'],
    'Desenho': ['N DESENHO', 'Nº DESENHO'],
    'Descrição': ['DESC. OBJETO/MARCA'],
    'Material': ['COMPOSICAO MP 2', 'COMPOSIÇÃO MP 2'],
    'Chapas': ['FORMATO CHAPA'],
    'Peso': ['PESO TT (KG)'],
    'Qtd': ['QTD PC TT MP', 'QTD PÇ TT MP'],
    'ÚLTIMO_PROCESSO': ['ULTIMO PROCESSO', 'ÚLTIMO PROCESSO', 'ULT. PROCESSO 2', 'ÚLT. PROCESSO 2'],
    'FUR': ['FURACAO', 'FURAÇÃO'],
    'Peso Total': ['PESO TT (KG)_V2', 'PESO TOTAL_V2'],
    'TRECHO': ['OF-TRECHO'],
    'DESENHISTA': ['DESENHISTA'],
    'PROJETISTA': ['PROJETISTA'],
}

# Colunas coladas na base: NUM_COM (A) até TIPO PINTURA (AI) — 0-based inclusive
COL_DBF_INICIO = 0
COL_DBF_FIM = 34

# Colunas de maquina/fluxo na aba DBF da base (1-based, como o openpyxl usa)
# AI = coluna 35 (1-based); a partir dai vem as formulas.
# MAQ. BC=129 / MAQ. CH=130 / MAQ. G6m=131 / MAQ. G3m=132  (1-based)
IDX_MAQ_BC, IDX_MAQ_CH, IDX_MAQ_G6M, IDX_MAQ_G3M = 129, 130, 131, 132
IDX_MAQ_PERFIL_UC = 127  # MAQ. PERFIL. U/C (1-based) — usada só na exceção da marca ED3
FLUXO_PARA_COL = {'FLUXO 1': IDX_MAQ_G6M, 'FLUXO 2': IDX_MAQ_G3M,
                   'FLUXO 3': IDX_MAQ_BC, 'FLUXO 4': IDX_MAQ_CH}
FLUXO_PARA_MAQ = {'FLUXO 1': 'G6m', 'FLUXO 2': 'G3m', 'FLUXO 3': 'BC', 'FLUXO 4': 'CH'}
COLS_FLUXO_AUTO = [IDX_MAQ_BC, IDX_MAQ_CH, IDX_MAQ_G6M, IDX_MAQ_G3M]

# Exceção fixa: a marca "ED3" nunca vai pro Fluxo 4/CH mesmo que o relatório
# diga isso — ela sempre é Perfiladeira U/C. Regra pedida manualmente pelo
# Diego porque essa marca sempre dava erro precisando de ajuste manual.
MARCAS_EXCECAO_FIXA = {
    'ED3': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'ED3 (regra fixa → Perfiladeira U/C)'},
    'SLT1': {'maq': 'CH', 'col': IDX_MAQ_CH, 'fluxo': 'SLT1 (regra fixa → Fluxo 4)'},
    'SLT2': {'maq': 'CH', 'col': IDX_MAQ_CH, 'fluxo': 'SLT2 (regra fixa → Fluxo 4)'},
    'SLT3': {'maq': 'CH', 'col': IDX_MAQ_CH, 'fluxo': 'SLT3 (regra fixa → Fluxo 4)'},
    'ACE1': {'maq': 'CH', 'col': IDX_MAQ_CH, 'fluxo': 'ACE1 (regra fixa → Fluxo 4)'},
    'NM2': {'maq': 'CH', 'col': IDX_MAQ_CH, 'fluxo': 'NM2 (regra fixa → Fluxo 4)'},
    'CSV1': {'maq': 'CH', 'col': IDX_MAQ_CH, 'fluxo': 'CSV1 (regra fixa → Fluxo 4)'},
    'ED-13': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'ED-13 (regra fixa → Perfiladeira U/C)'},
    'ED-2': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'ED-2 (regra fixa → Perfiladeira U/C)'},
    'ED-4': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'ED-4 (regra fixa → Perfiladeira U/C)'},
    'PDG-1': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'PDG-1 (regra fixa → Perfiladeira U/C)'},
    '-143': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': '-143 (regra fixa → Perfiladeira U/C)'},
    'ALT4800-1': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'ALT4800-1 (regra fixa → Perfiladeira U/C)'},
    'ALT5200-1': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'ALT5200-1 (regra fixa → Perfiladeira U/C)'},
    'ALT6000A-1': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'ALT6000A-1 (regra fixa → Perfiladeira U/C)'},
    'ALT6000B-1': {'maq': 'PERFIL. U/C', 'col': IDX_MAQ_PERFIL_UC, 'fluxo': 'ALT6000B-1 (regra fixa → Perfiladeira U/C)'},
}

LINHA_INICIAL_BASE = 10  # 1-based (linha 10 do Excel), onde comecam os dados na aba DBF

# ═══════════════════════════════════════════════════════════════════
# ABA "FOCCO_VISION_NDPCP301" — export direto do FOCCO ERP
# (FOCCO ERP > Relatório VISIONS "NDPCP301" > Filtro LOTE_OF = nº PCT,
#  TP_ORD vazio > Exportar para Excel). Cabecalho da base fica na
# linha 10, dados a partir da linha 11, colunas A (COD EMP) a AN (NOME).
# ═══════════════════════════════════════════════════════════════════
ESQUEMA_FOCCO = [
    "COD EMP", "NUM PEDV", "LOTE OF", "NUM ORDEM", "TP ORD", "DT EMISSAO",
    "OBRA", "SUB TRECHO", "GRUPO LIC", "NRO DES", "MARCA", "POSICAO",
    "TP MATL", "ESPESSURA", "TP ITEM", "GRP INV", "COD FAM 3",
    "DESCRICAO FAM 3", "COD FAM 4", "DESCRICAO FAM 4", "COD ITEM",
    "ID CONFIG", "DESC TECNICA", "DT INICIAL", "DT FINAL", "QTDE",
    "QTDE ENTREGUE", "QTDE REFUGO", "QTDE PENDENTE", "QTDE PEND POS REF",
    "UMP", "PESO DEMAND", "PESO REQUIS", "PESO PENDEN", "FINAL", "IMPR",
    "CREATED ON", "CREATED BY", "COD FUNC", "NOME",
    "COD ALMOX", "DESCRICAO ALMOX", "LOG APONT", "LOG USUARO APONT",
    "ZERO", "VAL", "RETRAB", "DIAS", "OBSERVACAO", "MASCARA",
]
ABA_FOCCO = 'FOCCO_VISION_NDPCP301'
LINHA_INICIAL_FOCCO = 11  # 1-based — logo abaixo do cabecalho (linha 10)
CHAVES_FOCCO = ['COD EMP', 'NUM PEDV', 'LOTE OF', 'NUM ORDEM', 'OBRA', 'MARCA']


# ═══════════════════════════════════════════════════════════════════
# UTILITÁRIOS DE TEXTO
# ═══════════════════════════════════════════════════════════════════
def norm(v):
    if v is None:
        return ''
    s = str(v).replace('\u00a0', ' ')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip().upper()


def squash(v):
    return re.sub(r'[^A-Z0-9]', '', norm(v))


def find_col(header, *nomes):
    H = [norm(h) for h in header]
    Hs = [squash(h) for h in header]
    for n in nomes:
        nn = norm(n)
        if nn in H:
            return H.index(nn)
    for n in nomes:
        a = squash(n)
        if a and a in Hs:
            return Hs.index(a)
    for n in nomes:
        a = squash(n)
        if len(a) >= 5:
            for i, h in enumerate(Hs):
                if h and a in h:
                    return i
    return -1


def parse_br(v):
    if v is None or v == '':
        return 0.0
    s = str(v).strip()
    if not s:
        return 0.0
    if ',' in s and '.' not in s:
        s = s.replace(',', '.')
    elif '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


# ═══════════════════════════════════════════════════════════════════
# LEITURA MULTIFORMATO DE ARQUIVOS DE DBF
# ═══════════════════════════════════════════════════════════════════
def ext_of(path):
    return os.path.splitext(path)[1].lower().lstrip('.')


def _parece_html(path):
    """Varios exports de ERP (FOCCO inclusive) salvam uma tabela HTML com
    extensao .xls/.xlsx — o Excel abre numa boa, mas as libs de planilha
    nao. Sniff dos primeiros bytes pra detectar isso antes de tentar abrir
    como binario de verdade."""
    try:
        with open(path, 'rb') as f:
            head = f.read(1000)
        for enc in ('utf-8', 'latin1'):
            try:
                s = head.decode(enc, errors='ignore').lower()
                if '<html' in s or '<!doctype' in s or '<table' in s:
                    return True
                break
            except Exception:
                continue
    except Exception:
        pass
    return False


class _ExtratorTabelasHTML(HTMLParser):
    """Extrai <table>...</table> de um HTML usando so a biblioteca padrao
    do Python (nada de lxml/html5lib) — export de ERP costuma vir com
    HTML tosco, mas isso aqui e tolerante o bastante pra esses casos."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tabelas = []
        self._pilha_tabela = []   # cada item: lista de linhas da tabela atual
        self._linha_atual = None
        self._celula_atual = None
        self._em_celula = False

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self._pilha_tabela.append([])
        elif tag == 'tr' and self._pilha_tabela:
            self._linha_atual = []
        elif tag in ('td', 'th') and self._pilha_tabela:
            self._em_celula = True
            self._celula_atual = []
        elif tag == 'br' and self._em_celula:
            self._celula_atual.append(' ')

    def handle_endtag(self, tag):
        if tag == 'table' and self._pilha_tabela:
            self.tabelas.append(self._pilha_tabela.pop())
        elif tag == 'tr' and self._linha_atual is not None:
            if self._pilha_tabela:
                self._pilha_tabela[-1].append(self._linha_atual)
            self._linha_atual = None
        elif tag in ('td', 'th') and self._em_celula:
            texto = ''.join(self._celula_atual).replace('\xa0', ' ').strip()
            if self._linha_atual is not None:
                self._linha_atual.append(texto if texto else None)
            self._em_celula = False
            self._celula_atual = None

    def handle_data(self, data):
        if self._em_celula and self._celula_atual is not None:
            self._celula_atual.append(data)


def _html_para_tabelas(path):
    with open(path, 'rb') as f:
        raw = f.read()
    for enc in ('utf-8', 'latin1'):
        try:
            texto = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        texto = raw.decode('utf-8', errors='ignore')

    parser = _ExtratorTabelasHTML()
    parser.feed(texto)
    tabelas = [t for t in parser.tabelas if t]
    if not tabelas:
        raise RuntimeError('nenhuma <table> encontrada no arquivo HTML')
    # normaliza largura das linhas (linhas mais curtas ficam com None no resto)
    out = []
    for i, rows in enumerate(tabelas):
        largura = max((len(r) for r in rows), default=0)
        rows_norm = [r + [None] * (largura - len(r)) for r in rows]
        out.append((f'Tabela {i + 1}' if len(tabelas) > 1 else 'HTML', rows_norm))
    return out


def ler_arquivo_tabular(path):
    """Le qualquer formato suportado -> lista de (nome_aba, linhas) onde
    linhas e uma lista de listas (uma por linha), sem cabecalho fixo."""
    ext = ext_of(path)

    # Exports de ERP as vezes vem com extensao de Excel mas conteudo HTML —
    # sniffar antes de decidir qual biblioteca usar.
    if ext in ('xlsx', 'xlsm', 'xls', 'csv', 'txt') and _parece_html(path):
        return _html_para_tabelas(path)

    if ext in ('xlsx', 'xlsm'):
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        out = []
        for name in wb.sheetnames:
            ws = wb[name]
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            out.append((name, rows))
        return out
    if ext == 'xls':
        # .xls binario legado (BIFF8) — precisa do engine xlrd
        try:
            planilhas = pd.read_excel(path, sheet_name=None, header=None, engine='xlrd')
        except ImportError:
            raise RuntimeError('xlrd nao instalado — pip install xlrd para ler .xls antigo')
        return [(nome, df.where(df.notna(), None).values.tolist()) for nome, df in planilhas.items()]
    if ext == 'xlsb':
        if open_xlsb is None:
            raise RuntimeError('pyxlsb nao instalado — nao consigo ler .xlsb')
        out = []
        with open_xlsb(path) as wb:
            for name in wb.sheets:
                with wb.get_sheet(name) as sheet:
                    rows = [[c.v for c in r] for r in sheet.rows()]
                out.append((name, rows))
        return out
    if ext in ('csv', 'txt', 'tsv', 'prn'):
        sep = '\t' if ext == 'tsv' else None
        try:
            df = pd.read_csv(path, sep=sep, engine='python', header=None,
                              dtype=str, keep_default_na=False, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=sep, engine='python', header=None,
                              dtype=str, keep_default_na=False, encoding='latin1')
        return [(os.path.basename(path), df.values.tolist())]
    if ext == 'dbf':
        try:
            from dbfread import DBF
        except ImportError:
            raise RuntimeError('dbfread nao instalado — pip install dbfread para ler .dbf (dBase)')
        table = DBF(path, encoding='latin1', ignore_missing_memofile=True)
        header = table.field_names
        rows = [header] + [[rec.get(f) for f in header] for rec in table]
        return [(os.path.basename(path), rows)]
    raise RuntimeError(f'formato ".{ext}" nao suportado')


CHAVES_DBF = ['MAR_PEZ', 'NUM_COM', 'POS_PEZ', 'DES_PEZ', 'NUM_DIS', 'QTA_PEZ',
              'PESO TOTAL', 'MARCA+TRECHO', 'GRUPO LIC']


def achar_cabecalho(rows, chaves=CHAVES_DBF, limite=30):
    melhor, score = -1, 0
    for i in range(min(limite, len(rows))):
        cel = [squash(v) for v in (rows[i] or [])]
        sc = sum(1 for k in chaves if squash(k) in cel)
        if sc > score:
            score, melhor = sc, i
        if sc >= 2:
            break
    if melhor >= 0 and score > 0:
        return melhor
    for i in range(min(limite, len(rows))):
        if sum(1 for v in (rows[i] or []) if norm(v) != '') >= 3:
            return i
    return 0


def escolher_planilha_dbf(planilhas):
    """Escolhe a aba/tabela mais provavel de ser a DBF dentro do arquivo."""
    melhor, melhor_score = None, -10**9
    for nome, rows in planilhas:
        if not rows:
            continue
        hi = achar_cabecalho(rows)
        cel = [squash(v) for v in (rows[hi] or [])]
        score = sum(1 for k in CHAVES_DBF if squash(k) in cel)
        score += min(len(rows), 500) / 500.0  # desempata por tamanho
        if norm(nome).find('CONSOLIDAD') >= 0:
            score -= 30
        if score > melhor_score:
            melhor_score, melhor = score, {'nome': nome, 'rows': rows, 'hi': hi}
    return melhor


def linha_eh_cabecalho(row, nomes_conhecidos):
    cel = [squash(v) for v in (row or []) if squash(v)]
    if len(cel) < 4:
        return False
    return sum(1 for v in cel if v in nomes_conhecidos) >= 6


NOMES_CONHECIDOS = set(squash(c) for c in ESQUEMA_DBF)
for _k, _vs in ALIAS_DBF.items():
    for _v in _vs:
        NOMES_CONHECIDOS.add(squash(_v))

IE = {c: i for i, c in enumerate(ESQUEMA_DBF) if c not in {}}
# indices fixos (primeira ocorrencia de cada nome, ESQUEMA_DBF nao repete nomes)
IE = {}
for i, c in enumerate(ESQUEMA_DBF):
    if c not in IE:
        IE[c] = i


def mapear_esquema(hdr_rows):
    norms = [[norm(v) for v in h] for h in hdr_rows]
    squs = [[squash(v) for v in h] for h in hdr_rows]
    usados = set()

    def busca(nome):
        n, q = norm(nome), squash(nome)
        for H in norms:
            for i, v in enumerate(H):
                if v == n and i not in usados:
                    return i
        if q:
            for H in squs:
                for i, v in enumerate(H):
                    if v == q and i not in usados:
                        return i
        return -1

    mapa = []
    for c in ESQUEMA_DBF:
        i = busca(c)
        if i < 0:
            for a in ALIAS_DBF.get(c, []):
                i = busca(a)
                if i >= 0:
                    break
        if i >= 0:
            usados.add(i)
        mapa.append(i)
    return mapa


def _vazio(v):
    """True pra None, string vazia, e NaN (float ou numpy) — protege contra
    qualquer formato que vaze NaN como float em vez de None."""
    if v is None:
        return True
    if isinstance(v, float) and v != v:  # NaN e a unica coisa que nao é igual a si mesma
        return True
    return False


def _recuperar_num_com_de_data(num_com_bruto, num_dis):
    """Quando o OF (ex.: "2001-7-22") parece uma data válida, o Excel às
    vezes converte a célula pra data de verdade sem querer, e o que sobra
    é um número de série gigante (ex.: 37094) em vez do texto certo.
    Detecta isso e recupera o texto original comparando com o que está
    embutido na NUM_DIS (que não sofre essa conversão, por estar dentro
    de um texto maior)."""
    try:
        serial = float(num_com_bruto)
    except (TypeError, ValueError):
        return None
    if serial != int(serial) or not (1 <= serial <= 200000):
        return None
    try:
        data = datetime(1899, 12, 30) + timedelta(days=int(serial))
    except OverflowError:
        return None
    candidato = f'{data.year}-{data.month}-{data.day}'
    if num_dis and candidato in str(num_dis):
        return candidato
    return None


def normalizar_dbf(rows):
    """Le linhas brutas de uma planilha e devolve no ESQUEMA_DBF padrao."""
    hi = achar_cabecalho(rows)
    hdr_rows = [[('' if _vazio(v) else str(v)) for v in (rows[hi] or [])]]
    p = hi + 1
    while p < len(rows) and len(hdr_rows) < 3 and linha_eh_cabecalho(rows[p], NOMES_CONHECIDOS):
        hdr_rows.append([('' if _vazio(v) else str(v)) for v in (rows[p] or [])])
        p += 1
    mapa = mapear_esquema(hdr_rows)
    iPT, iP, iPOS, iMAR = IE['Peso Total'], IE['Peso'], IE['POS_PEZ'], IE['MAR_PEZ']
    iNUMCOM, iNUMDIS = IE['NUM_COM'], IE['NUM_DIS']
    out = []
    for k in range(p, len(rows)):
        r = rows[k] or []
        if linha_eh_cabecalho(r, NOMES_CONHECIDOS):
            continue
        nr = [('' if (i < 0 or i >= len(r) or _vazio(r[i])) else str(r[i]).strip()) for i in mapa]
        # limpa "nan"/"NaN" literal que eventualmente vaze como texto de alguma
        # planilha de origem (mesma causa: NaN virando string antes da gente ver)
        nr = ['' if v.lower() == 'nan' else v for v in nr]
        # corrige NUM_COM que o Excel converteu pra data sem querer
        recuperado = _recuperar_num_com_de_data(nr[iNUMCOM], nr[iNUMDIS])
        if recuperado:
            nr[iNUMCOM] = recuperado
        # linha e "vazia de verdade" se nenhuma coluna que identifica a peça
        # tem conteudo — nao olha as 95 colunas, porque linhas de template
        # sem peça nenhuma ainda carregam resíduo de fórmula (ex.: GRUPO LIC
        # cai em "Verificar", Peso Total em "0.0", TRECHO em um código de
        # erro tipo "0xf") mesmo estando vazias na prática.
        colunas_identificam_peca = (iNUMCOM, IE['NUM_DIS'], iMAR, iPOS, IE['DES_PEZ'])
        if not any(nr[i].strip() for i in colunas_identificam_peca):
            continue
        out.append(nr)
    return out, hi


def _ler_dbfs(paths):
    """Le uma lista de arquivos de DBF e devolve as entries prontas pra
    lista da tela — roda em thread separada, nao mexe em nada do Qt."""
    entries = []
    for p in paths:
        entry = {'path': p, 'nome': os.path.basename(p), 'status': 'lendo', 'rows': None, 'msg': ''}
        try:
            planilhas = ler_arquivo_tabular(p)
            alvo = escolher_planilha_dbf(planilhas)
            if not alvo:
                raise RuntimeError('nenhuma planilha com dados')
            rows, hi = normalizar_dbf(alvo['rows'])
            if not rows:
                raise RuntimeError('0 linhas de dados reconhecidas')
            entry['rows'] = rows
            entry['status'] = 'ok'
            entry['msg'] = f'{len(rows)} linhas · aba "{alvo["nome"]}"'
        except Exception as e:
            entry['status'] = 'erro'
            entry['msg'] = str(e)
        entries.append(entry)
    return entries


EXT_DBF_BUSCA_PRIORIDADE = {'.csv': 0, '.xlsx': 1, '.xlsm': 1, '.xlsb': 1, '.xls': 2, '.txt': 2, '.tsv': 2, '.dbf': 3}
_PASTA_TEMP_BUSCA = None  # criada sob demanda, fica pro resto da sessao do app


def _pasta_temp_busca():
    global _PASTA_TEMP_BUSCA
    if _PASTA_TEMP_BUSCA is None or not os.path.isdir(_PASTA_TEMP_BUSCA):
        _PASTA_TEMP_BUSCA = tempfile.mkdtemp(prefix='ppcp_dbf_busca_')
    return _PASTA_TEMP_BUSCA


def _nome_bate_obra(nome_base, obra_lower):
    """Confere se o nome do arquivo (sem extensao) e da obra pedida — nao
    e so prefixo solto, senao "2058-102-02_L1" bateria por engano com
    "2058-102-02_L111" (arquivo diferente, mesma raiz de nome)."""
    nb = nome_base.lower()
    if nb == obra_lower:
        return True
    if nb.startswith(obra_lower) and nb[len(obra_lower):len(obra_lower) + 1] in ('_', '-', ' '):
        return True
    return False


def _listar_pasta_segura(pasta):
    """os.scandir + já separa arquivo de subpasta num passo só (evita
    uma chamada de stat() extra por item, que em rede é mais uma
    viagem de ida e volta) — devolve [] se a pasta não puder ser lida
    (sem permissão, caiu a rede etc.), sem derrubar a busca inteira."""
    try:
        with os.scandir(pasta) as it:
            return list(it)
    except OSError:
        return []


def _processar_uma_pasta(pasta):
    """Olha só o conteúdo DIRETO de uma pasta (não desce nas subpastas,
    nem abre os .zip aqui — isso roda em paralelo à parte, junto com os
    .zip achados nas OUTRAS pastas do mesmo nível, ver
    _escanear_raiz_completa) — devolve (achados_desta_pasta,
    lista_de_subpastas_pra_descer, lista_de_zips_pra_abrir)."""
    achados_aqui = []
    subpastas = []
    zips = []
    prioridade_pasta = 0 if os.path.basename(pasta).strip().upper() == 'DBF' else 1
    for entry in _listar_pasta_segura(pasta):
        try:
            eh_pasta = entry.is_dir(follow_symlinks=False)
        except OSError:
            continue
        if eh_pasta:
            subpastas.append(entry.path)
            continue
        base, ext = os.path.splitext(entry.name)
        if ext.lower() == '.zip':
            zips.append(entry.path)
            continue
        prioridade_ext = EXT_DBF_BUSCA_PRIORIDADE.get(ext.lower())
        if prioridade_ext is None:
            continue
        achados_aqui.append(((prioridade_pasta, prioridade_ext), base, entry.path))
    return achados_aqui, subpastas, zips


def _escanear_raiz_completa(raiz, max_workers=24):
    """Varre a raiz inteira (recursivo, pastas + dentro de .zip) — I/O
    puro de disco/rede, sem processar obra nenhuma ainda. Devolve uma
    lista "crua" de candidatos (prioridade, nome_base, caminho_ou_zip)
    pra quem chama CACHEAR e reusar em várias buscas de obra sem
    repetir essa varredura cara (importante em rede/Drive, onde só
    listar a árvore de pastas já é lento).

    Varre nível por nível (não pasta por pasta como os.walk) — em cada
    nível, TODAS as pastas daquele nível são listadas ao mesmo tempo
    num pool de threads, em vez de uma de cada vez. Numa pasta de rede
    (SMB, Drive mapeado...), cada "abrir pasta" é uma viagem de ida e
    volta pela rede — listar 20 pastas ao mesmo tempo é muito mais
    rápido que listar 20 pastas uma atrás da outra, mesmo que o total
    Também abre em paralelo todos os .zip achados dentro de um mesmo
    nível — em vez de abrir um zip de cada vez (dentro do processamento
    de cada pasta), todos os zips daquele nível são abertos ao mesmo
    tempo entre si também."""
    if not os.path.isdir(raiz):
        return []
    achados = []
    nivel_atual = [raiz]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        while nivel_atual:
            proximo_nivel = []
            todos_zips_do_nivel = []
            for achados_pasta, subpastas, zips in ex.map(_processar_uma_pasta, nivel_atual):
                achados.extend(achados_pasta)
                proximo_nivel.extend(subpastas)
                todos_zips_do_nivel.extend(zips)
            if todos_zips_do_nivel:
                for achados_zip in ex.map(_escanear_zip_completo, todos_zips_do_nivel):
                    achados.extend(achados_zip)
            nivel_atual = proximo_nivel
    return achados


def _escanear_zip_completo(caminho_zip):
    """Só lista o que tem dentro do .zip (barato) — a extração de
    verdade (cara) só acontece depois, pros poucos arquivos que
    baterem com a obra (ver _filtrar_e_extrair)."""
    achados = []
    try:
        with zipfile.ZipFile(caminho_zip) as z:
            for nome_interno in z.namelist():
                if nome_interno.endswith('/'):
                    continue
                base, ext = os.path.splitext(os.path.basename(nome_interno))
                prioridade_ext = EXT_DBF_BUSCA_PRIORIDADE.get(ext.lower())
                if prioridade_ext is None:
                    continue
                pasta_pai = os.path.basename(os.path.dirname(nome_interno)).strip().upper()
                prioridade_pasta = 0 if pasta_pai == 'DBF' else 1
                achados.append(((prioridade_pasta, prioridade_ext), base, ('__zip__', caminho_zip, nome_interno)))
    except (zipfile.BadZipFile, OSError):
        pass
    return achados


def _filtrar_e_extrair(achados, obra_lower):
    """Filtra a lista já escaneada (barato, só em memória) e SÓ AGORA
    extrai do .zip os poucos arquivos que realmente bateram com a
    obra — nunca extrai o zip inteiro."""
    candidatos = []
    for prioridade, base, caminho in achados:
        if not _nome_bate_obra(base, obra_lower):
            continue
        if isinstance(caminho, tuple) and caminho and caminho[0] == '__zip__':
            _, caminho_zip, nome_interno = caminho
            destino = os.path.join(_pasta_temp_busca(), os.path.basename(nome_interno))
            try:
                with zipfile.ZipFile(caminho_zip) as z, z.open(nome_interno) as origem, open(destino, 'wb') as saida:
                    saida.write(origem.read())
            except (zipfile.BadZipFile, OSError, KeyError):
                continue
            candidatos.append((prioridade, base.lower(), destino))
        else:
            candidatos.append((prioridade, base.lower(), caminho))
    return candidatos


def _candidatos_em_pasta(pasta, obra_lower):
    """Varre uma pasta (recursivo) procurando arquivos de DBF cujo nome
    bate com a obra. Prioriza os que estao numa subpasta "DBF" (o padrao
    real: .../<obra>/<obra-trecho>/DBF/<arquivo>) e, entre formatos
    diferentes do mesmo arquivo (ex.: .csv e .dbf lado a lado), prefere
    o mais facil de ler (.csv/.xlsx antes de .dbf). Qualquer .zip
    encontrado pelo caminho (nao só a pasta inteira da obra zipada, mas
    tambem um lote especifico zipado dentro da pasta) é aberto e
    procurado por dentro tambem. Usada pra pasta pequena e já
    direcionada (a subpasta da própria obra) — pra escanear uma raiz
    GRANDE inteira, prefira _escanear_raiz_completa + _filtrar_e_extrair,
    que permite cachear a varredura entre várias buscas."""
    return _filtrar_e_extrair(_escanear_raiz_completa(pasta), obra_lower)


def _candidatos_em_zip(caminho_zip, obra_lower):
    """Mesma busca, mas dentro de um .zip — extrai os que baterem pra uma
    pasta temporaria (a lib de leitura precisa de um caminho de arquivo
    de verdade, nao consegue ler direto de dentro do zip)."""
    return _filtrar_e_extrair(_escanear_zip_completo(caminho_zip), obra_lower)


def _melhor_por_arquivo(candidatos):
    """Entre candidatos com o MESMO nome base (o mesmo arquivo em formatos
    diferentes, ex.: .csv e .dbf lado a lado), fica só com o de maior
    prioridade. Depois, pra essa MESMA obra buscada: se tiver pelo menos
    um resultado em CSV, os que sobraram em formato pior são descartados
    — mesmo com nome base diferente (comum quando a mesma peça está
    espelhada em mais de uma pasta raiz com nome levemente diferente) —
    fica só com o(s) CSV. Sem nenhum CSV no meio, mantém o comportamento
    de sempre (cada nome base diferente conta como arquivo diferente,
    ex.: lotes diferentes de uma obra "solta")."""
    melhores = {}
    for prioridade, nome_base, caminho in candidatos:
        atual = melhores.get(nome_base)
        if atual is None or prioridade < atual[0]:
            melhores[nome_base] = (prioridade, caminho)
    if not melhores:
        return []
    melhor_prioridade_ext = min(p[0][1] for p in melhores.values())
    if melhor_prioridade_ext == 0:  # 0 = .csv, sempre o formato preferido
        return [c[1] for c in melhores.values() if c[0][1] == 0]
    return [c[1] for c in melhores.values()]


# ── Pastas raiz das obras FIXAS no sistema (iguais em todos os PCs; não dá pra trocar pela tela).
# Se um PC não enxergar alguma delas, a tela avisa qual falta e o que pedir. ──
_ID_ATALHO_LIBERACOES = '1ZwSq5uhu8VPwI99yMC0iAhkM3Ep2MZB1'
RAIZES_FIXAS = [
    {'nome': 'LIBERAÇÕES FOCCO (Google Drive)',
     'caminho': 'G:\\.shortcut-targets-by-id\\' + _ID_ATALHO_LIBERACOES + '\\LIBERACOES\\LIBERAÇÕES FOCCO',
     'precisa': 'o Google Drive para computador instalado e logado, com o atalho da pasta "LIBERACOES" compartilhada'},
    {'nome': 'LIBERAÇÕES ENGENHARIA (rede)',
     'caminho': '\\\\172.25.0.7\\lib-eng\\LIBERAÇÕES ENGENHARIA',
     'precisa': 'acesso à pasta de rede \\\\172.25.0.7\\lib-eng (estar na rede da empresa e ter permissão)'},
]


def _isdir_com_prazo(caminho, prazo=6.0):
    """os.path.isdir que não trava a tela quando a rede não responde."""
    res = {}

    def _v():
        try:
            res['ok'] = os.path.isdir(caminho)
        except OSError:
            res['ok'] = False
    t = threading.Thread(target=_v, daemon=True)
    t.start()
    t.join(prazo)
    return bool(res.get('ok'))


def verificar_raizes_fixas():
    """Para cada pasta fixa: [{nome, caminho, precisa, ok, achado}]. O Google Drive pode estar com
    outra letra de unidade neste PC — tenta G: primeiro e depois as outras letras."""
    saida = []
    for r in RAIZES_FIXAS:
        cam = r['caminho']
        achado = cam if _isdir_com_prazo(cam) else ''
        if not achado and re.match(r'^[A-Za-z]:\\', cam) and os.name == 'nt':
            resto = cam[2:]
            for letra in 'GHIJKLMNOPQRSTUVWXYZDEF':
                alt = letra + ':' + resto
                if alt != cam and os.path.isdir(letra + ':\\') and _isdir_com_prazo(alt, 3.0):
                    achado = alt
                    break
        saida.append(dict(r, ok=bool(achado), achado=achado or cam))
    return saida


def diagnosticar_pasta_raiz(raiz):
    """Ferramenta de depuração pra quando a busca não acha nada numa
    pasta que devia ter a obra — mostra exatamente o que o Python
    consegue enxergar ali, sem adivinhar. Útil pra pastas de rede/Drive
    que às vezes escondem coisa do app sem dar erro nenhum."""
    linhas = [f'Caminho testado: {raiz}']
    if not os.path.isdir(raiz):
        linhas.append('✕ Esse caminho NÃO é uma pasta acessível agora (pode ter caído a rede, '
                       'o Drive não estar sincronizado, ou o caminho estar errado).')
        return linhas
    linhas.append('✓ A pasta abre normalmente.')
    try:
        entradas = sorted(os.listdir(raiz))
    except OSError as e:
        linhas.append(f'✕ A pasta abre mas não consigo LISTAR o conteúdo dela: {e}')
        return linhas
    pastas = [e for e in entradas if os.path.isdir(os.path.join(raiz, e))]
    arquivos = [e for e in entradas if not os.path.isdir(os.path.join(raiz, e))]
    linhas.append(f'\nDentro dela, vejo {len(pastas)} pasta(s) e {len(arquivos)} arquivo(s) direto no primeiro nível:')
    for p in pastas[:40]:
        linhas.append(f'  📁 {p}')
    if len(pastas) > 40:
        linhas.append(f'  … e mais {len(pastas) - 40} pasta(s)')
    for a in arquivos[:40]:
        marcador = ' ← é um .zip' if a.lower().endswith('.zip') else ''
        linhas.append(f'  📄 {a}{marcador}')
    if len(arquivos) > 40:
        linhas.append(f'  … e mais {len(arquivos) - 40} arquivo(s)')

    zips = [a for a in arquivos if a.lower().endswith('.zip')]
    if zips:
        linhas.append(f'\nTestando os .zip encontrados nesse primeiro nível:')
        for z in zips[:10]:
            caminho_zip = os.path.join(raiz, z)
            if not zipfile.is_zipfile(caminho_zip):
                linhas.append(f'  ✕ {z} — não abre como zip válido (pode estar corrompido ou ainda '
                               f'baixando/sincronizando pelo Drive)')
                continue
            try:
                with zipfile.ZipFile(caminho_zip) as zf:
                    nomes = zf.namelist()
                linhas.append(f'  ✓ {z} — abre normalmente, {len(nomes)} item(ns) dentro')
                for n in nomes[:15]:
                    linhas.append(f'      {n}')
                if len(nomes) > 15:
                    linhas.append(f'      … e mais {len(nomes) - 15} item(ns)')
            except (zipfile.BadZipFile, OSError) as e:
                linhas.append(f'  ✕ {z} — encontrado mas deu erro ao abrir: {e}')
    return linhas


def _candidatos_rapidos_bruto(raiz, prefixo_obra):
    """Devolve a lista "crua" (sem filtrar por obra ainda) do atalho
    rápido — a subpasta ou .zip com o número da obra direto na raiz —
    ou None se nem um nem outro existir (aí quem chamou precisa cair
    pra varredura lenta da raiz inteira)."""
    pasta_obra = os.path.join(raiz, prefixo_obra)
    zip_obra = os.path.join(raiz, prefixo_obra + '.zip')
    if os.path.isdir(pasta_obra):
        return _escanear_raiz_completa(pasta_obra)
    if os.path.isfile(zip_obra):
        return _escanear_zip_completo(zip_obra)
    return None


def _listar_raiz_nivel1(raiz):
    """Lista só o primeiro nível da raiz (não recursivo) — usado pra
    reconhecer o padrão comum em pastas de backup/Drive onde a pasta OU
    o .zip da obra já ficam DIRETO na raiz com o código completo da
    obra-trecho no nome (ex.: "2113-4-21_L1", "2113-4-21_L1.zip"), sem
    uma subpasta intermediária só com o número solto da obra. Rápido
    mesmo numa raiz com milhares de itens, porque é UMA listagem só —
    não desce em nenhuma subpasta."""
    try:
        with os.scandir(raiz) as it:
            return list(it)
    except OSError:
        return []


def _candidatos_por_prefixo_na_raiz(entradas_raiz, obra_lower):
    """Entre as entradas do primeiro nível da raiz (já listadas por
    _listar_raiz_nivel1), acha as que baterem com o texto da obra —
    pasta ou .zip — e devolve os achados CRUS de dentro delas (quem
    chama ainda precisa passar por _filtrar_e_extrair, igual o atalho A
    — aqui só evita descer nas milhares de outras pastas que não têm
    nada a ver com a obra buscada)."""
    candidatos = []
    for entry in entradas_raiz:
        eh_zip = entry.name.lower().endswith('.zip')
        nome_sem_ext = entry.name[:-4] if eh_zip else entry.name
        if not _nome_bate_obra(nome_sem_ext, obra_lower):
            continue
        try:
            eh_pasta = (not eh_zip) and entry.is_dir(follow_symlinks=False)
        except OSError:
            continue
        if eh_pasta:
            candidatos.extend(_escanear_raiz_completa(entry.path))
        elif eh_zip:
            candidatos.extend(_escanear_zip_completo(entry.path))
    return candidatos


def buscar_dbfs_por_obra(raizes, obras, busca_completa=False, progresso=None):
    """Pra cada obra (ex.: "2058-102-02" ou só "2058"), procura o(s)
    arquivo(s) de DBF correspondentes — testando TODAS as pastas raiz da
    lista "raizes" e juntando os candidatos antes de escolher, pra se a
    mesma peça existir em mais de uma pasta raiz (ex.: csv numa, xlsb
    noutra) ficar só com UMA versão (a de maior prioridade — csv >
    xlsb/xlsm > xls/txt/tsv > dbf), nunca trazendo duplicado.

    Tenta, em ordem, 3 jeitos de achar cada obra — os 2 primeiros
    SEMPRE rodam (são rápidos), o 3º só se busca_completa=True:

    1) Atalho "padrão A": .../<raiz>/<PREFIXO da obra>/<obra-trecho>/DBF/...
       — uma pasta só com o número antes do "-" agrupando os trechos.
    2) Atalho "padrão B": .../<raiz>/<obra-trecho completo>[_algo]/DBF/...
       (ou .../<raiz>/<obra-trecho completo>[_algo].zip) — quando a
       pasta/zip da obra já fica DIRETO na raiz com o código completo
       no nome (comum em backups do Drive, ex.: "2113-4-21_L1.zip").
       Isso só precisa listar o primeiro nível da raiz UMA vez (rápido
       mesmo com milhares de itens ali) e cacheia essa listagem pra
       reusar entre todas as obras buscadas.
    3) Varredura lenta: desce em TODA a árvore de pastas da raiz,
       nível por nível, em paralelo — só roda se os atalhos 1 e 2 não
       acharem nada em NENHUMA raiz E busca_completa=True (senão pode
       levar minutos numa pasta de rede muito grande/cheia).

    Aceita a "pasta da obra" tanto normal quanto zipada (.zip). Uma obra
    "solta" (ex.: "2058", sem trecho) pode casar com vários arquivos
    DIFERENTES (lotes diferentes) — todos entram, isso não é duplicata.
    Devolve (encontrados: [caminho,...], nao_achadas: [obra,...])."""
    def avisa(msg):
        if progresso:
            progresso(msg)

    if isinstance(raizes, str):
        raizes = [raizes]
    raizes = [r.strip() for r in raizes if r and r.strip()]
    obras_limpas = [o.strip() for o in obras if o and o.strip()]
    prefixos = sorted({o.split('-')[0] for o in obras_limpas})

    cache_rapido = {}    # (raiz, prefixo) -> lista crua | None (nao achou atalho A)
    cache_nivel1 = {}    # raiz -> lista de entradas do primeiro nivel (pro atalho B)
    cache_lenta = {}     # raiz -> lista crua (varredura da raiz inteira)

    avisa(f'Verificando o atalho de {len(prefixos)} obra(s) em {len(raizes)} pasta(s) raiz…')
    with ThreadPoolExecutor(max_workers=16) as ex:
        futuros_rapidos = {(raiz, prefixo): ex.submit(_candidatos_rapidos_bruto, raiz, prefixo)
                            for raiz in raizes for prefixo in prefixos}
        futuros_nivel1 = {raiz: ex.submit(_listar_raiz_nivel1, raiz) for raiz in raizes}

        raizes_precisam_lenta = set()
        for chave, fut in futuros_rapidos.items():
            cache_rapido[chave] = fut.result()
            if cache_rapido[chave] is None:
                raizes_precisam_lenta.add(chave[0])
        for raiz, fut in futuros_nivel1.items():
            cache_nivel1[raiz] = fut.result()

        if busca_completa and raizes_precisam_lenta:
            avisa(f'Atalho não achou tudo — varrendo {len(raizes_precisam_lenta)} pasta(s) raiz inteira(s) '
                  f'(pode demorar)…')
            futuros_lentos = {raiz: ex.submit(_escanear_raiz_completa, raiz) for raiz in raizes_precisam_lenta}
            for raiz, fut in futuros_lentos.items():
                cache_lenta[raiz] = fut.result()

    avisa('Cruzando resultados…')
    encontrados, nao_achadas = [], []
    for obra in obras_limpas:
        prefixo_obra = obra.split('-')[0]
        candidatos_todas_raizes = []
        for raiz in raizes:
            bruto = cache_rapido.get((raiz, prefixo_obra))
            if bruto is not None:
                candidatos_todas_raizes.extend(_filtrar_e_extrair(bruto, obra.lower()))
                continue
            # atalho A não achou nessa raiz — tenta o atalho B (pasta/zip
            # com o código completo direto no primeiro nível da raiz)
            entradas_nivel1 = cache_nivel1.get(raiz)
            if entradas_nivel1:
                bruto_nivel1 = _candidatos_por_prefixo_na_raiz(entradas_nivel1, obra.lower())
                candidatos_todas_raizes.extend(_filtrar_e_extrair(bruto_nivel1, obra.lower()))
            if raiz in cache_lenta:
                candidatos_todas_raizes.extend(_filtrar_e_extrair(cache_lenta[raiz], obra.lower()))

        # junta os candidatos de TODAS as raizes antes de escolher — se a
        # mesma peça existir em duas pastas raiz diferentes (csv numa,
        # xlsb noutra, por exemplo), fica só com a de maior prioridade,
        # uma vez só, em vez de trazer duplicado
        achados = _melhor_por_arquivo(candidatos_todas_raizes)

        if achados:
            encontrados.extend(achados)
        else:
            nao_achadas.append(obra)
    return encontrados, nao_achadas


# ═══════════════════════════════════════════════════════════════════
# RELATÓRIO DE FLUXOS (leitura, nunca alterado)
# ═══════════════════════════════════════════════════════════════════
def _pos_base_colapsada(pos):
    """Versão antiga/agressiva: remove TAMBÉM o número da sub-peça
    (ex.: "@1", "_2"). Usada só de fallback, quando não existe entrada
    pro número de sub-peça exato — mantê-la sempre como primeira opção
    causava erro: sub-peças da MESMA posição podem ter Fluxo DIFERENTE
    entre si (caso real: "-103@1" = Fluxo 3, "-103@2"/"-103@3" = Fluxo 2 —
    colapsar tudo fazia a última sobrescrever as outras)."""
    s = str(pos)
    s = re.split(r'[@\[]', s, maxsplit=1)[0].strip()
    s = re.sub(r'_(\d+|[ULC])$', '', s, flags=re.IGNORECASE)
    return s


def _pos_base(pos):
    """Normaliza a posição PRESERVANDO o número da sub-peça (ex.: "@1"
    vira "_1", pro mesmo formato que a DBF já usa) — porque sub-peças da
    mesma posição podem ter Fluxo diferente entre si (confirmado num caso
    real). Só remove:
    1) sufixo de layout de corte entre colchetes (ex.: "-299@1[A]",
       "-299@1[B]") — isso sim é sempre a MESMA peça física, só cortada
       em duas metades pro nesting;
    2) sufixo de dobra (ex.: "CVL850P10_U", "7-01_E-3_U") — U/L/C so
       indicam o lado da dobra, é a mesma marca."""
    s = str(pos)
    s = re.sub(r'\[[A-Za-z]\]$', '', s).strip()
    s = re.sub(r'@(\d+)$', r'_\1', s)
    s = re.sub(r'_[ULC]$', '', s, flags=re.IGNORECASE)
    return s


def _pos_sem_subtrecho(pos):
    """Tira o prefixo de subtrecho (ex.: "2-02_", "4-70_", "3-01_") do
    começo da posição — usado só pra checar as regras fixas (marcas
    "padrão" tipo ED-13/ALT4800-1/PDG-1 que se repõem em vários
    subtrechos/obras diferentes, sempre com a mesma máquina)."""
    return re.sub(r'^\d+-\d+_', '', str(pos).strip())


def fluxo_para_o_agrupador(valor):
    """Fluxo do Agrupador/Base (chave de FLUXO_PARA_COL: 'FLUXO 1'..'FLUXO 4') a
    partir do que o relatório traz na coluna de fluxo. Aceita:
      - o formato antigo, exato: "Fluxo 3";
      - o formato novo, com a espessura entre colchetes: "Fluxo 3 [8,0]";
      - a máquina LASER ("LASER", "LASER [9,5]"): na planilha da base não existe
        coluna de laser, então o que é dessa máquina conta como FLUXO 3 (BC) —
        valendo SÓ aqui, no Agrupador/Base. Sem isso as peças do laser ficavam
        sem marca de máquina, saíam do "Peso x Fluxo" e davam informação errada.
    Qualquer outra coisa ("SEM ROTEIRIZAÇÃO", vazio, fluxo 5…) devolve None."""
    texto = norm(valor)
    if texto in FLUXO_PARA_COL:
        return texto
    n = numero_fluxo(valor)
    if n and f'FLUXO {n}' in FLUXO_PARA_COL:
        return f'FLUXO {n}'
    if rotulo_fluxo(valor) == 'LASER':
        return 'FLUXO 3'
    return None


def ler_relatorio_fluxos(path):
    """Le a aba 'Relatório Consolidado' e devolve {OF|MARCA: {'maq':..,'fluxo':..}}."""
    planilhas = ler_arquivo_tabular(path)
    nome_aba, rows = None, None

    def _aba_serve(r):
        """A aba tem cabeçalho com OF + posição + fluxo nas primeiras linhas?"""
        for r_ in (r or [])[:15]:
            h_ = [norm(str(c)) for c in (r_ or [])]
            if (any(n in h_ for n in ('OF', 'OF-TRECHO', 'OF TRECHO')) and 'POSICAO' in h_
                    and any(n in h_ for n in ('FLUXO', 'FLUXO DE PRODUCAO'))):
                return True
        return False
    # 1ª escolha: a aba "Preparação" — já vem filtrada só com Fluxo 1-4 e LASER (sem Terça Z, perfiladeira
    # etc.). Se não existir (ou for de outro formato), cai na "Relatório Consolidado", que tem tudo.
    for n, r in planilhas:
        if norm(n) == 'PREPARACAO' and _aba_serve(r):
            nome_aba, rows = n, r
            break
    if nome_aba is None:
        for n, r in planilhas:
            if norm(n) == norm('Relatório Consolidado'):
                nome_aba, rows = n, r
                break
    if nome_aba is None:
        for n, r in planilhas:
            if 'CONSOLIDAD' in norm(n):
                nome_aba, rows = n, r
                break
    if nome_aba is None:
        raise RuntimeError('nao encontrei a aba "Preparação" nem a "Relatório Consolidado" no relatorio de fluxos')

    # Cabeçalho: normalmente é a 1ª linha, mas procura nas primeiras (o relatório
    # pode ter linhas de título acima) — precisa ter a OF, a posição e o fluxo.
    def _tem(h, *nomes):
        return any(n in h for n in nomes)
    hi = 0
    for i_, r_ in enumerate(rows[:15]):
        h_ = [norm(str(c)) for c in (r_ or [])]
        if (_tem(h_, 'OF', 'OF-TRECHO', 'OF TRECHO') and _tem(h_, 'POSICAO')
                and _tem(h_, 'FLUXO', 'FLUXO DE PRODUCAO')):
            hi = i_
            break
    header = [norm(v) for v in (rows[hi] or [])]

    def _col(padrao, *nomes):
        for n in nomes:
            if n in header:
                return header.index(n)
        return padrao
    # nomes aceitos: o formato antigo (OF / Posição / Fluxo) e o novo (OF-TRECHO / POSIÇÃO / FLUXO DE PRODUÇÃO)
    iOF = _col(0, 'OF', 'OF-TRECHO', 'OF TRECHO')
    iPos = _col(1, 'POSICAO')
    iFluxo = _col(3, 'FLUXO', 'FLUXO DE PRODUCAO')
    # o relatório novo tem também "FLUXO DE PRODUÇÃO" (sem a espessura): serve de reforço
    iFluxoProd = header.index(norm('FLUXO DE PRODUÇÃO')) if (norm('FLUXO DE PRODUÇÃO') in header
                                                            and header.index(norm('FLUXO DE PRODUÇÃO')) != iFluxo) else None

    fluxo_map, ignoradas = {}, 0
    colapsado_map, colapsado_valores = {}, {}
    iQtd = next((header.index(n) for n in ('QTDE (ORDEM)', 'QTDE ORDEM', 'QUANTIDADE', 'QTDE') if n in header), None)
    iPesoTot = next((header.index(n) for n in ('PESO TOTAL (KG)', 'PESO TOTAL') if n in header), None)
    iOrdem = next((header.index(n) for n in ('NUM ORDEM', 'ORDEM') if n in header), None)
    ordens_da_chave = {}     # chave -> {(qtd, peso): [nº das ordens]} — p/ somar só ordens DIFERENTES e não as "gêmeas"
    for r in rows[hi + 1:]:
        if not r or not any(v is not None and v != '' for v in r):
            continue
        of, pos = r[iOF] if iOF < len(r) else None, r[iPos] if iPos < len(r) else None
        bruto = r[iFluxo] if iFluxo < len(r) else ''
        fluxo = fluxo_para_o_agrupador(bruto)
        if fluxo is None and iFluxoProd is not None and iFluxoProd < len(r):
            fluxo = fluxo_para_o_agrupador(r[iFluxoProd])
            if fluxo:
                bruto = r[iFluxoProd]
        if not of or not pos:
            continue
        # linha embaralhada pelo gerador do relatório (OF = "Q1", posição = "171_3- OF2148-3-01"):
        # a OF verdadeira veio grudada no fim da posição — desfaz.
        m_emb = re.match(r'^(.+?)\s*-\s*OF\s*(\d+-\d+-\d+)\s*$', str(pos).strip(), re.IGNORECASE)
        if m_emb and not re.match(r'^\d+-\d+', str(of).strip()):
            of, pos = m_emb.group(2), m_emb.group(1)
        col = FLUXO_PARA_COL.get(fluxo) if fluxo else None
        if col is None:
            ignoradas += 1
            continue
        valor = {'maq': FLUXO_PARA_MAQ[fluxo], 'col': col, 'fluxo': bruto}
        chave = f'{norm(of)}|{norm(_pos_base(pos))}'
        # a MESMA peça pode vir em duas ordens (ex.: CH = ordem final/de pintura "ULT.PROC." e CH_INT = chapa
        # intermediária, com a mesma qtde e o mesmo peso): conta UMA vez só, senão o peso sai em dobro
        qtd_r = parse_br(r[iQtd]) if (iQtd is not None and iQtd < len(r)) else None
        peso_r = parse_br(r[iPesoTot]) if (iPesoTot is not None and iPesoTot < len(r)) else None
        ordem_r = str(r[iOrdem]).strip() if (iOrdem is not None and iOrdem < len(r) and r[iOrdem] not in (None, '')) else ''
        ordens_da_chave.setdefault(chave, {}).setdefault((qtd_r, round(peso_r, 3) if peso_r is not None else None), []).append(ordem_r)
        fluxo_map[chave] = valor
        # mapa "colapsado" (numero de sub-peça removido) — so serve de
        # fallback quando a posição não se divide em sub-peças na DBF;
        # so fica valido se TODAS as sub-peças da mesma posição
        # concordarem no mesmo fluxo, senao é ambíguo demais pra arriscar
        chave_colapsada = f'{norm(of)}|{norm(_pos_base_colapsada(pos))}'
        colapsado_map[chave_colapsada] = valor
        colapsado_valores.setdefault(chave_colapsada, set()).add(col)
    colapsado_map = {k: v for k, v in colapsado_map.items() if len(colapsado_valores[k]) == 1}
    gemeas = 0
    for chave, grupos in ordens_da_chave.items():
        gemeas += sum(len(v) - 1 for v in grupos.values())       # ordens "gêmeas" descartadas
        qtds = [q for (q, _pz) in grupos]
        # soma só as ordens com quantidade/peso DIFERENTES (ordens realmente distintas da mesma posição)
        fluxo_map[chave]['qtd'] = None if any(q is None for q in qtds) else sum(qtds)
    return {'granular': fluxo_map, 'colapsado': colapsado_map, 'gemeas': gemeas}, ignoradas, nome_aba


def _candidatos_of_trecho(row):
    """Normalmente NUM_COM já é o OF-trecho completo (ex.: "2001-7-70").
    Mas em alguns exports NUM_COM vem só com o número da obra (ex.: "2129"),
    e o trecho completo fica embutido dentro da NUM_DIS — em formatos
    diferentes dependendo da origem: "2129-7-01_CH-7_R0" (hífen),
    "OF 2129_7-01_P. 7-01_-300" (underscore) ou "F2026_2154-4-01_V-13_R0"
    (com um prefixo de lote/arquivo tipo "F2026_" antes). Por isso a busca
    é ANCORADA no número da obra que já veio na NUM_COM — nunca adivinha
    um número qualquer, senão pode confundir com esse prefixo (ex.: achar
    "2026" do "F2026_" em vez do "2154" de verdade)."""
    candidatos = []
    num_com = row[IE['NUM_COM']]
    if num_com:
        candidatos.append(num_com)
        # NUM_COM as vezes vem com sufixo de lote grudado (ex.: "2001-7-60_L1"
        # em vez de "2001-7-60") — tenta a versão sem esse sufixo tambem
        sem_lote = re.sub(r'_L\d+$', '', str(num_com).strip(), flags=re.IGNORECASE)
        if sem_lote and sem_lote != num_com and sem_lote not in candidatos:
            candidatos.append(sem_lote)
    num_dis = row[IE['NUM_DIS']]
    if num_dis and num_com:
        obra = re.sub(r'\.0$', '', str(num_com).strip())  # tira ".0" de float convertido em texto
        obra = re.sub(r'_L\d+$', '', obra, flags=re.IGNORECASE)  # tira sufixo de lote tambem daqui
        if obra:
            m = re.search(re.escape(obra) + r'[-_](\d+-\d+)', str(num_dis))
            if m:
                reconstruido = f'{obra}-{m.group(1)}'
                if reconstruido not in candidatos:
                    candidatos.append(reconstruido)
    return candidatos


def construir_pos_com_filhos(linhas):
    """Varre todas as linhas do DBF e devolve o conjunto de (NUM_COM,
    posição-base-colapsada) que têm pelo menos uma sub-peça com sufixo
    numérico (ex.: "259_1", "259_2") — usado pra a linha "pai" sem
    sufixo (ex.: "259", a peça inteira) NUNCA levar marcação de fluxo
    quando as sub-peças dela já estão sendo contadas separadamente no
    mesmo DBF (evita somar o peso duas vezes: uma na peça inteira,
    outra de novo em cada parte dela)."""
    com_filhos = set()
    for row in linhas:
        pos = row[IE['POS_PEZ']]
        if not pos or not str(pos).strip():
            continue
        base = _pos_base(str(pos).strip())
        if re.search(r'_\d+$', base):
            num_com = norm(row[IE['NUM_COM']])
            colapsada = norm(_pos_base_colapsada(str(pos)))
            com_filhos.add((num_com, colapsada))
    return com_filhos


def linhas_duplicadas_do_fluxo(linhas, fluxo_map, pos_com_filhos=None):
    """Quando a MESMA posição aparece em mais de uma linha da DBF (ex.: uma por TIPO DE PINTURA), todas
    receberiam o X e o peso sairia em DOBRO no "Peso x Fluxo". Aqui só vale o que o relatório de fluxos
    (aba Preparação) manda produzir: a quantidade da posição no relatório é o limite — as linhas seguintes,
    depois de completar essa quantidade, ficam SEM X. Sem quantidade no relatório, só descarta linha idêntica
    (mesma QTA_PEZ e mesmo Peso Total) a outra já marcada. Devolve {índice_da_linha: chave}."""
    grupos = {}
    for i, row in enumerate(linhas):
        pos = row[IE['POS_PEZ']]
        if not (pos and str(pos).strip()):
            continue
        f = achar_fluxo_da_linha(row, fluxo_map, pos_com_filhos)
        if f and f.get('granular') and f.get('chave'):
            grupos.setdefault(f['chave'], []).append((i, f))
    duplicadas = {}
    for chave, itens in grupos.items():
        if len(itens) < 2:
            continue
        cap = itens[0][1].get('qtd')
        acumulado, vistos = 0.0, set()
        for i, f in itens:
            row = linhas[i]
            q = parse_br(row[IE['QTA_PEZ']])
            assinatura = (round(q, 4), round(parse_br(row[IE['Peso Total']]), 3))
            if cap:
                repetida = acumulado + 1e-6 >= cap
            else:
                repetida = assinatura in vistos
            if repetida:
                duplicadas[i] = chave
            else:
                acumulado += q
                vistos.add(assinatura)
    return duplicadas


def achar_fluxo_da_linha(row, fluxo_map, pos_com_filhos=None):
    """So a linha FILHO (com POS_PEZ preenchido) pode levar o X de máquina —
    a linha PAI (agregado da marca, POS_PEZ vazio) nunca recebe marcação,
    confirmado comparando com uma base preenchida manualmente.

    O cruzamento é pela POSIÇÃO (POS_PEZ), não pela MARCA — o relatório de
    fluxos chama sua coluna de "Posição" mesmo, e numa marca composta (ex.:
    uma viga "4-01_V-13" feita de várias chapas/perfis) cada posição
    filha tem seu proprio codigo (ex.: "4-01_-106"), diferente da marca
    "pai". Confirmado com um caso real onde MARCA != POSIÇÃO.

    pos_com_filhos (opcional): conjunto vindo de construir_pos_com_filhos
    — quando a posição desta linha NÃO tem sufixo de sub-peça mas já
    existem sub-peças irmãs dela no mesmo DBF (ex.: linha "259" existindo
    junto com "259_1"/"259_2"/"259_3"), essa linha "pai" fica sem
    marcação nenhuma, pro peso dela não entrar duplicado no "Peso x
    Fluxo" (confirmado num caso real: as 4 linhas — peça inteira +
    3 sub-peças — estavam levando "X" juntas, somando quase o dobro do
    peso de verdade)."""
    pos = row[IE['POS_PEZ']]
    if not pos or not pos.strip():
        return None
    pos_chave = norm(_pos_base(pos))
    if pos_chave in MARCAS_EXCECAO_FIXA:
        return dict(MARCAS_EXCECAO_FIXA[pos_chave], chave=None)
    pos_sem_subtrecho = norm(_pos_base(_pos_sem_subtrecho(pos)))
    if pos_sem_subtrecho in MARCAS_EXCECAO_FIXA:
        return dict(MARCAS_EXCECAO_FIXA[pos_sem_subtrecho], chave=None)
    if not fluxo_map:
        return None
    granular = fluxo_map.get('granular', fluxo_map)  # compat com dict simples antigo
    colapsado = fluxo_map.get('colapsado', {})
    for of_cand in _candidatos_of_trecho(row):
        chave = f'{norm(of_cand)}|{pos_chave}'
        achado = granular.get(chave)
        if achado:
            return dict(achado, chave=chave, granular=True)
    # fallback: so quando a DBF nao tem a peca dividida em sub-peça mas o
    # relatorio tem — so entra se TODAS as sub-peças dessa posição no
    # relatório concordarem no mesmo fluxo (ver ler_relatorio_fluxos).
    # NUNCA entra pra uma posição sem sufixo que já tem sub-peças irmãs
    # no mesmo DBF (essas já são contadas via o match granular acima).
    if pos_com_filhos is not None and not re.search(r'_\d+$', pos_chave):
        num_com = norm(row[IE['NUM_COM']])
        pos_colapsada_check = norm(_pos_base_colapsada(pos))
        if (num_com, pos_colapsada_check) in pos_com_filhos:
            return None
    pos_colapsada = norm(_pos_base_colapsada(pos))
    for of_cand in _candidatos_of_trecho(row):
        chave = f'{norm(of_cand)}|{pos_colapsada}'
        achado = colapsado.get(chave)
        if achado:
            return dict(achado, chave=chave)
    return None


# ═══════════════════════════════════════════════════════════════════
# RELATÓRIO FOCO (NDPCP301) — leitura, mapeia por nome de coluna
# ═══════════════════════════════════════════════════════════════════
def achar_cabecalho_foco(rows, limite=15):
    melhor, score = -1, 0
    chaves = [squash(c) for c in CHAVES_FOCCO]
    for i in range(min(limite, len(rows))):
        cel = [squash(v) for v in (rows[i] or [])]
        sc = sum(1 for k in chaves if k in cel)
        if sc > score:
            score, melhor = sc, i
        if sc >= 4:
            break
    if melhor >= 0 and score >= 2:
        return melhor
    raise RuntimeError('nao encontrei o cabeçalho do relatório FOCO (esperava colunas como "COD EMP", "NUM PEDV"...)')


def ler_relatorio_foco(path):
    """Le o export do FOCCO ERP (Relatório VISIONS NDPCP301) e devolve as
    linhas ja remapeadas para ESQUEMA_FOCCO (na ordem certa, por nome de
    coluna — tolera a planilha vir com colunas fora de ordem ou faltando)."""
    planilhas = ler_arquivo_tabular(path)
    rows = planilhas[0][1]

    hi = achar_cabecalho_foco(rows)
    header = [norm(v) for v in (rows[hi] or [])]
    mapa = [header.index(norm(c)) if norm(c) in header else -1 for c in ESQUEMA_FOCCO]

    out = []
    for k in range(hi + 1, len(rows)):
        r = rows[k] or []
        nr = [(r[i] if (0 <= i < len(r)) else None) for i in mapa]
        if not any(v is not None and str(v).strip() != '' for v in nr):
            continue
        out.append(nr)
    faltando = sum(1 for i in mapa if i < 0)
    return out, faltando


DATE_COLS_FOCCO = {'DT EMISSAO', 'DT INICIAL', 'DT FINAL'}


def _coagir_valor_foco(nome_coluna, v):
    """Export do FOCCO (HTML) traz tudo como texto — converte pra número
    ou data de verdade quando dá, igual o Excel faz automaticamente
    quando voce cola a tabela manualmente."""
    if v is None:
        return None
    if isinstance(v, float) and v != v:  # NaN
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    if not s or s.lower() == 'nan':
        return None
    if nome_coluna in DATE_COLS_FOCCO:
        for fmt in ('%d/%m/%y', '%d/%m/%Y'):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return s
    num_s = s.replace(',', '.') if (',' in s and '.' not in s) else s
    if re.fullmatch(r'-?\d+', num_s):
        try:
            return int(num_s)
        except ValueError:
            pass
    if re.fullmatch(r'-?\d+(\.\d+)?', num_s):
        try:
            return float(num_s)
        except ValueError:
            pass
    return s


def escrever_foco_na_base(wb, linhas_foco):
    """Limpa a area de dados antiga da aba FOCCO_VISION_NDPCP301 (colunas
    A-AN, a partir da linha 11) e escreve as linhas novas do relatório
    FOCO, convertendo número/data como o Excel faria. Nao mexe em mais
    nada da aba."""
    if ABA_FOCCO not in wb.sheetnames:
        raise RuntimeError(f'a planilha base nao tem aba "{ABA_FOCCO}"')
    ws = wb[ABA_FOCCO]
    n_cols = len(ESQUEMA_FOCCO)

    ultima_linha_antiga = ws.max_row
    n = len(linhas_foco)
    ultima_linha_necessaria = max(ultima_linha_antiga, LINHA_INICIAL_FOCCO + n - 1)

    linhas_valores = [[_coagir_valor_foco(ESQUEMA_FOCCO[c0], v) for c0, v in enumerate(row)]
                       for row in linhas_foco]

    for offset, cells in enumerate(ws.iter_rows(min_row=LINHA_INICIAL_FOCCO, max_row=ultima_linha_necessaria,
                                                 min_col=1, max_col=n_cols)):
        if offset < n:
            for cell, v in zip(cells, linhas_valores[offset]):
                cell.value = v
        else:
            for cell in cells:
                cell.value = None

    return n


# ═══════════════════════════════════════════════════════════════════
# GERAÇÃO DA BASE PREENCHIDA
# ═══════════════════════════════════════════════════════════════════
LINHA_NUM_PCT, COL_NUM_PCT = 5, 3  # 1-based — celula "Nº PCT" (DBF!C5), usada por formulas tipo "PACOTE 676"
LINHA_DT_REFRESH, COL_DT_REFRESH = 2, 3  # 1-based — celula "Dt. refresh" (DBF!C2)


def _valor_lote(lote):
    """Converte o lote pra número quando possível (a célula "Nº PCT" guarda
    número, não texto — é o que a fórmula PACOTE/pivot espera)."""
    s = str(lote).strip()
    try:
        n = float(s.replace(',', '.'))
        return int(n) if n == int(n) else n
    except ValueError:
        return s


def gerar_base_preenchida(caminho_base, linhas_consolidadas, fluxo_map, lote, caminho_saida, linhas_foco=None):
    """Abre a BASE (.xlsx), limpa a area de dados antiga da aba DBF (colunas
    A-AI + as 4 colunas de fluxo automatico), escreve o consolidado novo e
    marca os X de Fluxo 1-4, opcionalmente escreve a aba FOCCO_VISION_NDPCP301
    com o relatorio do FOCO, e salva em um arquivo NOVO (nunca sobrescreve
    o original)."""
    wb = openpyxl.load_workbook(caminho_base, keep_vba=caminho_base.lower().endswith('.xlsm'))
    if 'DBF' not in wb.sheetnames:
        raise RuntimeError('a planilha base nao tem aba "DBF"')
    ws = wb['DBF']
    ws.cell(row=LINHA_NUM_PCT, column=COL_NUM_PCT).value = _valor_lote(lote)
    ws.cell(row=LINHA_DT_REFRESH, column=COL_DT_REFRESH).value = date.today()

    linhas_consolidadas, resumo_dup = remover_linhas_duplicadas(linhas_consolidadas, fluxo_map)
    ultima_linha_antiga = ws.max_row
    n = len(linhas_consolidadas)
    ultima_linha_necessaria = max(ultima_linha_antiga, LINHA_INICIAL_BASE + n - 1)

    # Pre-calcula valor/fluxo de cada linha nova ANTES de tocar na planilha
    # (X so na linha FILHO, que tem POS_PEZ preenchido — a linha PAI nunca
    # recebe marcação de máquina)
    C_POS = IE['POS_PEZ']
    pos_com_filhos = construir_pos_com_filhos(linhas_consolidadas)
    com_fluxo, sem_fluxo = 0, 0
    marcas_achadas = set()
    linhas_valores, linhas_fluxo_col = [], []
    for i_lin, row in enumerate(linhas_consolidadas):
        vals = []
        for c0 in range(COL_DBF_INICIO, COL_DBF_FIM + 1):
            v = row[c0]
            if v == '' or v is None:
                vals.append(None)
                continue
            s = str(v).strip()
            num_s = s.replace(',', '.') if (',' in s and '.' not in s) else s
            vals.append(float(num_s) if re.fullmatch(r'-?\d+(\.\d+)?', num_s) else s)
        linhas_valores.append(vals)

        eh_filho = bool(row[C_POS] and row[C_POS].strip())
        f = achar_fluxo_da_linha(row, fluxo_map, pos_com_filhos) if eh_filho else None
        if f:
            linhas_fluxo_col.append(f['col'])
            com_fluxo += 1
            marcas_achadas.add(f['chave'])
        else:
            linhas_fluxo_col.append(None)
            if eh_filho:
                sem_fluxo += 1

    # 1 passada só por bloco de colunas (limpa + escreve junto), usando
    # iter_rows (bem mais rápido que repetir ws.cell(row=,column=) célula a célula)
    for offset, cells in enumerate(ws.iter_rows(min_row=LINHA_INICIAL_BASE, max_row=ultima_linha_necessaria,
                                                 min_col=COL_DBF_INICIO + 1, max_col=COL_DBF_FIM + 1)):
        if offset < n:
            for cell, v in zip(cells, linhas_valores[offset]):
                cell.value = v
        else:
            for cell in cells:
                cell.value = None

    for offset, cells in enumerate(ws.iter_rows(min_row=LINHA_INICIAL_BASE, max_row=ultima_linha_necessaria,
                                                 min_col=IDX_MAQ_BC, max_col=IDX_MAQ_G3M)):
        for cell in cells:
            cell.value = None
        if offset < n and linhas_fluxo_col[offset] is not None:
            col = linhas_fluxo_col[offset]
            if IDX_MAQ_BC <= col <= IDX_MAQ_G3M:
                cells[col - IDX_MAQ_BC].value = 'X'

    # coluna extra da exceção fixa (ED3 -> Perfiladeira U/C) — fora do bloco
    # contíguo de fluxo, escrita à parte
    for offset, cell in enumerate(list(ws.iter_rows(min_row=LINHA_INICIAL_BASE, max_row=ultima_linha_necessaria,
                                                     min_col=IDX_MAQ_PERFIL_UC, max_col=IDX_MAQ_PERFIL_UC))):
        c = cell[0]
        if offset < n and linhas_fluxo_col[offset] == IDX_MAQ_PERFIL_UC:
            c.value = 'X'

    nao_encontradas = []
    if fluxo_map:
        for chave, info in fluxo_map.get('granular', fluxo_map).items():
            if chave not in marcas_achadas:
                of, marca = chave.split('|', 1)
                nao_encontradas.append((of, marca, info['maq']))

    linhas_foco_gravadas = 0
    if linhas_foco:
        linhas_foco_gravadas = escrever_foco_na_base(wb, linhas_foco)

    wb.save(caminho_saida)
    return {'com_fluxo': com_fluxo, 'sem_fluxo': sem_fluxo, 'nao_encontradas': nao_encontradas,
            'duplicadas': resumo_dup,
            'linhas_foco': linhas_foco_gravadas, 'pivots_atualizados': 0, 'pivots_com_erro': 0,
            'caches_corrigidos': 0, 'caches_com_erro': 0, 'erros_pivot': []}


def remover_linhas_duplicadas(linhas, fluxo_map):
    """Tira DE VEZ da DBF (elas não vão para a base) as linhas repetidas da mesma posição — ver
    linhas_duplicadas_do_fluxo. Devolve (linhas_sem_repetidas, resumo)."""
    if not fluxo_map or not linhas:
        return linhas, _resumo_duplicadas({})
    dup = linhas_duplicadas_do_fluxo(linhas, fluxo_map, construir_pos_com_filhos(linhas))
    if not dup:
        return linhas, _resumo_duplicadas({})
    return [r for i, r in enumerate(linhas) if i not in dup], _resumo_duplicadas(dup)


def _resumo_duplicadas(duplicadas):
    """{'total': n linhas da DBF sem X por serem a mesma posição repetida, 'chaves': [(OF|posição, n)…]}"""
    cont = collections.Counter(duplicadas.values())
    return {'total': len(duplicadas), 'chaves': sorted(cont.items())}


def date_tag():
    return datetime.now().strftime('%y%m%d')


def _gerar_base_e_atualizar_ska(fn_base, args_base, kwargs_base, ska_csv, usar_excel, progresso=None):
    """Tarefa em segundo plano: (1) atualiza a planilha LANTEK_SKA com o relatório SKA, se pedido; (2) gera a base.
    Falha na SKA NUNCA impede a base: vira aviso no resultado (`resultado['ska'] = {'erro': ...}`)."""
    ska = None
    if ska_csv:
        try:
            ska = ska_lantek.atualizar_planilha_ska(ska_csv, progresso=progresso)
        except Exception as e:
            _registrar_erro_no_log('Erro ao atualizar a planilha LANTEK_SKA (Validador)')
            ska = {'erro': str(e) or e.__class__.__name__}
    kw = dict(kwargs_base)
    if usar_excel and ska and 'erro' not in ska:
        kw['atualizar_vinculo_lantek'] = True          # a base já sai com o vínculo Lantek atualizado
    try:
        if progresso and 'progresso' in inspect.signature(fn_base).parameters:
            kw['progresso'] = progresso
    except (TypeError, ValueError):
        pass
    resultado = fn_base(*args_base, **kw)
    resultado['ska'] = ska
    return resultado


def _excel_com_disponivel():
    """Checagem rapida (nao abre o Excel) se da pra usar o caminho via COM —
    é bem mais rapido que o openpyxl pra planilhas grandes/complexas."""
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


def _contar_pivot_tables(path):
    """Conta quantas tabelas dinamicas o arquivo tem, sem precisar abrir o
    workbook inteiro (só espia o .zip) — .xlsx/.xlsm/.xlsb usam o mesmo
    layout de pasta internamente. Usado pra avisar que o caminho openpyxl
    pode resetar filtro/cache dessas abas (limitação da biblioteca, não
    tem como evitar por código — só o Excel de verdade preserva)."""
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            return sum(1 for n in z.namelist()
                       if n.startswith('xl/pivotTables/pivotTable') and (n.endswith('.xml') or n.endswith('.bin')))
    except Exception:
        return 0


_EXCEL_FILEFORMAT = {'xlsb': 50, 'xlsx': 51, 'xlsm': 52}  # xlExcel12 / xlOpenXMLWorkbook / xlOpenXMLWorkbookMacroEnabled


_NOMES_FLUXO_VISIVEIS = {'FLUXO 1', 'FLUXO 2', 'FLUXO 3', 'FLUXO 4'}


def _fixar_filtro_fluxo_prd(pivot_table):
    """Se a tabela dinâmica tem um campo "FLUXO PRD" (ex.: aba Peso x Fluxo),
    garante que só Fluxo 1/2/3/4 ficam marcados como visiveis no filtro —
    o refresh as vezes muda essa seleção sozinho (item novo entra marcado,
    item sem dado sai). Liga os certos ANTES de desligar os outros pra
    nunca deixar a tabela com zero itens visiveis (o Excel nao permite)."""
    try:
        campo = pivot_table.PivotFields('FLUXO PRD')
    except Exception:
        return
    itens = campo.PivotItems()
    total = itens.Count
    for j in range(1, total + 1):
        item = itens.Item(j)
        if norm(item.Name) in _NOMES_FLUXO_VISIVEIS:
            try:
                item.Visible = True
            except Exception:
                pass
    for j in range(1, total + 1):
        item = itens.Item(j)
        if norm(item.Name) not in _NOMES_FLUXO_VISIVEIS:
            try:
                item.Visible = False
            except Exception:
                pass


def _ler_observacoes_de_filtro(ws_com):
    """Varre a aba procurando linhas no formato do modelo: coluna A tem o
    nome de um campo de filtro de pivô, coluna C tem uma observação do
    lado. Duas formas de observação, com sentido OPOSTO um do outro:
      - "<<< Desmarcar filtro X; Y; Z"   -> X, Y, Z ficam DE FORA,
                                             todo o resto fica marcado
      - "<<< Filtrar apenas X" / '"X" e "Y"' -> só X (e Y) ficam
                                             marcados, todo o resto some
    Os itens depois de "apenas" costumam vir entre aspas quando são
    mais de um ou têm espaço no nome (ex.: "PERFILAD. L" e "PERFILAD.
    U/C") — nesse caso usa as aspas pra separar; senão cai no separador
    ";" (igual o "Desmarcar filtro" sempre usa).

    Devolve uma lista de (nome_do_campo, modo, {itens}) — modo é
    'excluir' ou 'somente'. Lida ao vivo toda vez (não confia em nenhum
    estado salvo de execução anterior).

    Lê o bloco de células (colunas A a C, só as ~30 primeiras linhas)
    numa ÚNICA chamada pelo COM (Range(...).Value devolve tudo de uma
    vez) — em vez de uma chamada por célula, que é bem mais lento pelo
    COM (cada .Cells(...).Value é uma ida e volta; numa aba com várias
    pivôs isso se repetia várias vezes e deixava a geração lenta)."""
    saida = []
    try:
        usada = ws_com.UsedRange
        primeira_linha = usada.Row
        ultima_linha = usada.Row + usada.Rows.Count - 1
    except Exception:
        return saida
    # essas observações sempre ficam perto do topo da aba (junto dos
    # filtros da pivô) — limita a variedade pra não vasculhar a aba
    # inteira sem necessidade
    limite = min(ultima_linha, primeira_linha + 30)
    try:
        bloco = ws_com.Range(ws_com.Cells(primeira_linha, 1), ws_com.Cells(limite, 3)).Value
    except Exception:
        return saida
    if bloco is None:
        return saida
    if not isinstance(bloco, tuple):
        bloco = ((bloco,),)  # bloco de 1 celula só o COM devolve sem aninhar
    re_aspas = re.compile('["\u201c\u201d\u2018\u2019\']([^"\u201c\u201d\u2018\u2019\']+)["\u201c\u201d\u2018\u2019\']')
    for linha_vals in bloco:
        if len(linha_vals) < 3:
            continue
        nota = str(linha_vals[2] or '')
        if '<<<' not in nota:
            continue
        m_excluir = re.search(r'Desmarcar\s+filtro\s+(.*)', nota, re.IGNORECASE)
        m_somente = re.search(
            r'(?:Filtrar\s+apenas|Sempre\s+marcar)\s+(?:filtro\s+|fluxos?\s+)?(.*)', nota, re.IGNORECASE)
        if m_excluir:
            modo, resto = 'excluir', m_excluir.group(1)
        elif m_somente:
            modo, resto = 'somente', m_somente.group(1)
        else:
            continue
        resto = resto.strip()
        # termos entre aspas primeiro (mais confiavel quando tem "e" no
        # meio ou nome com espaço/pontuação) — só cai pro separador ";"
        # se não tiver nenhuma aspas na observação
        termos_citados = re_aspas.findall(resto)
        if termos_citados:
            itens = {norm(t) for t in termos_citados}
        else:
            # separa por ";" só FORA de parênteses — algumas observações
            # agrupam prefixos dentro de um parêntese (ex.: "LAMINADO
            # (W_; L_; BR_; TB_; TQ_)"), que não pode virar vários itens
            pedacos = re.split(r';(?![^(]*\))', resto)
            itens = {norm(x) for x in pedacos if x.strip()}
        if not itens:
            continue
        nome_campo = str(linha_vals[0] or '').strip()
        if nome_campo:
            saida.append((nome_campo, modo, itens))
    return saida


_CACHE_OBSERVACOES_POR_ABA = {}


def _aplicar_filtros_das_observacoes(ws_com, pivot_table):
    """Lê as observações da aba ("Desmarcar filtro ..." / "Filtrar
    apenas ...") e ajusta o filtro da pivô pra bater com elas — sempre,
    do zero, a cada geração (em vez de confiar em qual item ficou
    marcado/desmarcado de uma execução anterior, que pode ter ficado
    errado por interação manual no Excel ou por um item novo entrar
    marcado sozinho no refresh). A leitura da aba (a parte lenta pelo
    COM) é cacheada por nome de aba — se a aba tem mais de uma pivô, só
    lê as observações uma vez, não uma vez por pivô."""
    nome_aba = ws_com.Name
    if nome_aba not in _CACHE_OBSERVACOES_POR_ABA:
        _CACHE_OBSERVACOES_POR_ABA[nome_aba] = _ler_observacoes_de_filtro(ws_com)
    observacoes = _CACHE_OBSERVACOES_POR_ABA[nome_aba]
    for nome_campo, modo, itens in observacoes:
        campo = None
        try:
            campo = pivot_table.PivotFields(nome_campo)
        except Exception:
            # o nome pode ter espaço/maiúscula diferente do da coluna A
            # — tenta achar o campo certo comparando de um jeito tolerante
            try:
                for f in pivot_table.PivotFields():
                    if norm(f.Name) == norm(nome_campo):
                        campo = f
                        break
            except Exception:
                pass
        if campo is None:
            continue  # esse campo nao existe NESSA pivô especifica, tudo bem
        try:
            itens_pivot = campo.PivotItems()
            total = itens_pivot.Count
        except Exception:
            continue

        def _chave_frouxa(texto):
            # compara ignorando espaço e pontuação leve também — o texto
            # da observação nem sempre bate espaço-por-espaço com o nome
            # real do item na pivô (ex.: "AC.CSC" vs "AC. CSC")
            return re.sub(r'[\s.\-_]+', '', texto)

        def deve_ficar_visivel(nome_item, modo=modo, itens=itens):
            # compara sem parenteses tambem — "(vazio)" no pivô costuma
            # bater com uma observação que só diz "vazio", sem parenteses
            chave = norm(nome_item).strip('()')
            alvo = {i.strip('()') for i in itens}
            bateu = chave in itens or chave in alvo
            if not bateu:
                # 2ª tentativa: ignora espaço/pontuação dos dois lados
                chave_frouxa = _chave_frouxa(chave)
                bateu = any(_chave_frouxa(a) == chave_frouxa for a in alvo)
            return bateu if modo == 'somente' else not bateu

        # liga os que devem ficar visiveis ANTES de desligar os outros —
        # o Excel não deixa a tabela com zero itens marcados
        for j in range(1, total + 1):
            item = itens_pivot.Item(j)
            if deve_ficar_visivel(item.Name):
                try:
                    item.Visible = True
                except Exception:
                    pass
        for j in range(1, total + 1):
            item = itens_pivot.Item(j)
            if not deve_ficar_visivel(item.Name):
                try:
                    item.Visible = False
                except Exception:
                    pass



def _pasta_downloads():
    """Pasta Downloads do usuário (a de verdade, mesmo se foi movida/OneDrive); se não achar, a pasta do usuário."""
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as k:
                v = os.path.expandvars(winreg.QueryValueEx(k, '{374DE290-123F-4565-9164-39C4925E467B}')[0])
                if os.path.isdir(v):
                    return v
        except OSError:
            pass
    for nome in ('Downloads', 'Transferências'):
        p = os.path.join(os.path.expanduser('~'), nome)
        if os.path.isdir(p):
            return p
    p = os.path.join(os.path.expanduser('~'), 'Downloads')
    try:
        os.makedirs(p, exist_ok=True)
        return p
    except OSError:
        return os.path.expanduser('~')


def _atualizar_vinculo_lantek(wb_com):
    """Atualiza, dentro da base aberta, o vínculo com a planilha LANTEK_SKA (a que alimenta MÁQUINA_LANTEK).
    Devolve quantos vínculos atualizou (0 se não houver / falhar — nunca derruba a geração)."""
    try:
        fontes = wb_com.LinkSources(1)       # xlExcelLinks
    except Exception:
        return 0
    n = 0
    for f in (fontes or ()):
        nome = str(f).upper()
        if 'LANTEK_SKA' in nome and '00. BACK UP' not in nome:
            try:
                # a planilha do vínculo não existe neste PC (sem o Google Drive): aponta para a cópia do sistema
                if ska_lantek and not os.path.isfile(str(f)):
                    novo = ska_lantek.caminho_destino()
                    if os.path.isfile(novo) and os.path.normcase(novo) != os.path.normcase(str(f)):
                        wb_com.ChangeLink(Name=f, NewName=novo, Type=1)
                        n += 1
                        continue
                wb_com.UpdateLink(Name=f, Type=1)
                n += 1
            except Exception:
                pass
    return n


# Na aba "PREP_Lista x Máq x Ord x Trecho" a tabela dinâmica tem TIPO PINTURA como campo de linha: a mesma
# posição/ordem saía em 2 linhas (Pó e Líquida) com a quantidade/peso repartidos — parecia posição repetida e peso
# em dobro. Com True o campo sai das LINHAS dessa tabela (uma linha por posição/ordem, qtd e peso somados).
LISTA_PREP_SEM_TIPO_PINTURA = True
CAMPO_TIPO_PINTURA = 'TIPO PINTURA'


def _tirar_tipo_pintura_da_lista_prep(ws_com, pivot_table):
    """Tira o campo TIPO PINTURA das linhas da tabela dinâmica da aba PREP_Lista…. Devolve True se tirou."""
    if not LISTA_PREP_SEM_TIPO_PINTURA or not norm(ws_com.Name).startswith(norm('PREP_Lista')):
        return False
    try:
        campo = pivot_table.PivotFields(CAMPO_TIPO_PINTURA)
    except Exception:
        return False
    try:
        if campo.Orientation != 1:        # xlRowField — só mexe se estiver mesmo nas linhas
            return False
        campo.Orientation = 0             # xlHidden
        return True
    except Exception:
        return False


RECALCULO_COMPLETO_NA_BASE = False   # True = CalculateFullRebuild no fim da geração pelo Excel (mais lento)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# V275 — REGRAS FIXAS DA ATUALIZAÇÃO DA PLANILHA BASE (passo a passo do vídeo "ATUALIZAÇÃO DA PLANILHA" do
# Wadson, 25/11/2026). Toda Base gerada pelo sistema passa SEMPRE por isto (caminho pelo Excel):
#   1) DBF: classifica os dados por OF-TRECHO (A→Z), Nº LIBERAÇÃO (A→Z), MARCA (A→Z), PAI X FILHO (Z→A).
#   2) Toda tabela dinâmica que lê a DBF: fonte = DBF!$A$9:<última coluna><última linha> e atualizar.
#   3) Filtros de cada aba (abaixo, em FILTROS_FIXOS_BASE) + os das observações "<<< ..." do próprio modelo.
#   4) PREP_Lista: célula H5 = data de hoje.
#   5) Renomeia as abas e pinta as cores do jeito do print (NOMES_CORES_ABAS_BASE).
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
ORDEM_DBF_BASE = [            # (cabeçalho na linha 9 da DBF, crescente?)
    ('OF-TRECHO', True),
    ('Nº LIBERAÇÃO', True),
    ('MARCA', True),
    ('PAI X FILHO', False),   # Z→A: o PAI fica antes dos filhos
]

# (início do nome da aba no modelo, campo da tabela dinâmica, itens que ficam marcados — None = todos "(Tudo)")
# Só vale para a tabela que tem o campo; se nenhum dos itens existir no lote, deixa tudo marcado.
FILTROS_FIXOS_BASE = [
    ('CDI_Prog', 'COMPONENTE', {'LIC'}),
    ('CDI_Prog', 'ACESSÓRIOS', {'(vazio)'}),
    ('CDI_Prog', 'PERFIL LAMINAD', {'(vazio)'}),
    ('CDI_Prog', 'GRUPO LIC', {'ESCADA', 'ACESSÓRIOS', 'VIGA/PILARES/SOLDADOS', 'ACESSÓRIOS BARRA',
                               'ACESSÓRIOS SOLDADOS'}),
    ('CLEBER_TS', 'TS x VM x VP x PERFIL', {'VP c/ Perfil Lam.'}),
    ('PREP_Lista', 'FILTRO TD LISTA MAQ', {'X'}),          # "<<< Sempre marcar X"
]
_NOMES_VAZIO = {'(VAZIO)', 'VAZIO', '(BLANK)', 'BLANK', ''}
# Aba "PREP_Quadro Gestão à Vista": a tabela PESO POR BC (linhas = MÁQUINA_LANTEK) fica com FLUXO PRD = (Tudo).
ABA_QUADRO_GESTAO = 'PREP_Quadro'

ABA_PREP_LISTA = 'PREP_Lista'
CELULA_DATA_PREP_LISTA = 'H5'

# nome no modelo -> (nome na Base gerada, cor da guia RGB ou None = deixa a cor que já tem)
NOMES_CORES_ABAS_BASE = [
    ('DBF', 'DBF', None),
    ('FOCCO_VISION_NDPCP301', 'FOCCO_VISION_NDPCP399', 'ACB9CA'),
    ('Peso x Fluxo', 'PESO X FLUXO', 'F4B084'),
    ('Det. PCT', 'DET. PCT', '66FFFF'),
    ('PREP_Lista x Máq x Ord x Trecho', 'PREP_LISTA X MAQ X ORD X TRECHO', '666633'),
    ('PREP_Quadro Gestão à Vista', 'PREP_QUADRO GESTÃO A VISTA', '7030A0'),
    ('CLEBER_TS x VM x VP x PERFIL', 'CLEBER_TS x VM x VP x PERFIL', 'FFD966'),
    ('CDI_Prog PCT', 'CDI_PROG_PCT', 'CCFF33'),
    ('LT', 'LT', 'FF0000'),
    ('MARLON_Posição x Perfiladeira', 'MARLON_POSIÇÃO_PERFILADEIRA', '00CC99'),
    ('ELVIS_Perfil Lam.', 'ELVIS_PERFIL_LAM', None),
    ('Ruptura MP', 'RUPTURA MP', 'FF66FF'),
    ('BD', 'BD', '3399FF'),
    ('Calendário', 'CALENDÁRIO', None),
]


def _rgb_para_cor_excel(hex6):
    """'RRGGBB' -> número de cor do Excel (BGR)."""
    r, g, b = int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)
    return r + g * 256 + b * 65536


def _colunas_por_cabecalho(ws_com, linha_cab, ultima_col):
    """{cabeçalho normalizado: nº da 1ª coluna com esse nome} lendo a linha de cabeçalho de uma vez."""
    vals = ws_com.Range(ws_com.Cells(linha_cab, 1), ws_com.Cells(linha_cab, ultima_col)).Value
    linha = vals[0] if vals else ()
    out = {}
    for i, v in enumerate(linha, start=1):
        k = norm(v)
        if k and k not in out:
            out[k] = i
    return out


def _ordenar_dbf_base(ws_com, ultima_linha, ultima_col):
    """Passo 1 do vídeo: Classificar a DBF (OF-TRECHO, Nº LIBERAÇÃO, MARCA, PAI X FILHO Z→A).
    Devolve a lista de cabeçalhos usados (vazia = não achou / não ordenou)."""
    linha_cab = LINHA_INICIAL_BASE - 1
    if ultima_linha <= LINHA_INICIAL_BASE:
        return []
    cols = _colunas_por_cabecalho(ws_com, linha_cab, ultima_col)
    chaves = [(nome, cols[norm(nome)], cresc) for nome, cresc in ORDEM_DBF_BASE if norm(nome) in cols]
    if not chaves:
        return []
    srt = ws_com.Sort
    srt.SortFields.Clear()
    for _nome, col, cresc in chaves:
        srt.SortFields.Add(Key=ws_com.Range(ws_com.Cells(LINHA_INICIAL_BASE, col), ws_com.Cells(ultima_linha, col)),
                           SortOn=0, Order=1 if cresc else 2, DataOption=0)   # xlSortOnValues, xlAscending/xlDescending
    # V278: igual a imagem do Wadson — intervalo começa no cabeçalho (linha 9) com "Meus dados contêm cabeçalhos"
    # marcado, e os 4 níveis ficam SALVOS na aba (abrindo Classificar no Excel eles aparecem assim)
    srt.SetRange(ws_com.Range(ws_com.Cells(linha_cab, 1), ws_com.Cells(ultima_linha, ultima_col)))
    srt.Header = 1            # xlYes
    srt.MatchCase = False
    srt.Orientation = 1       # xlTopToBottom
    srt.Apply()
    return [n for n, _c, _o in chaves]


def _achar_campo(pivot_table, nome_campo):
    """Campo da tabela pelo nome exato ou pelo começo do nome (ex.: "FILTRO TD LISTA MAQ" acha "FILTRO TD LISTA MAQ.")."""
    try:
        return pivot_table.PivotFields(nome_campo)
    except Exception:
        pass
    alvo = norm(nome_campo)
    try:
        campos = pivot_table.PivotFields()
        for j in range(1, campos.Count + 1):
            c = campos.Item(j)
            if norm(c.Name).startswith(alvo):
                return c
    except Exception:
        pass
    return None


def _filtrar_campo_somente(pivot_table, nome_campo, visiveis):
    """Deixa marcados só os itens de `visiveis` (None = todos). Liga antes de desligar (nunca zero itens).
    "(vazio)" casa com o item em branco. Em campo de FILTRO (página) liga a seleção de vários itens."""
    campo = _achar_campo(pivot_table, nome_campo)
    if campo is None:
        return False
    if visiveis is None:
        try:
            campo.ClearAllFilters()
            return True
        except Exception:
            return False
    alvo = {norm(v) for v in visiveis}
    if alvo & _NOMES_VAZIO:
        alvo |= _NOMES_VAZIO
    itens = campo.PivotItems()
    total = itens.Count
    nomes = [norm(itens.Item(j).Name) for j in range(1, total + 1)]
    if not any(n in alvo for n in nomes):
        return False                       # nada do lote bate: não esvazia a tabela
    try:
        campo.ClearAllFilters()
    except Exception:
        pass
    try:
        if campo.Orientation == 3:         # xlPageField
            campo.EnableMultiplePageItems = True
    except Exception:
        pass
    for j in range(1, total + 1):
        if nomes[j - 1] in alvo:
            try:
                itens.Item(j).Visible = True
            except Exception:
                pass
    for j in range(1, total + 1):
        if nomes[j - 1] not in alvo:
            try:
                itens.Item(j).Visible = False
            except Exception:
                pass
    return True


def _apontar_tabela_para_dbf(pivot_table, ultima_linha):
    """V278: "Alterar Fonte de Dados" da tabela: se a fonte é a aba DBF, passa a ser DBF linha 9 até `ultima_linha`
    (mesmas colunas). Devolve True se mudou."""
    src = str(pivot_table.SourceData or '')
    col_fim = None
    m = re.match(r"^'?(?:\[[^\]]*\])?([^'!]+)'?!R(\d+)C(\d+):R(\d+)C(\d+)$", src)
    if m and norm(m.group(1)) == 'DBF':
        col_fim = int(m.group(5))
    else:
        m = re.match(r"^'?(?:\[[^\]]*\])?([^'!]+)'?!\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)$", src)
        if m and norm(m.group(1)) == 'DBF':
            from openpyxl.utils import column_index_from_string
            col_fim = column_index_from_string(m.group(4))
    if not col_fim:
        return False
    novo = f"DBF!R{LINHA_INICIAL_BASE - 1}C1:R{ultima_linha}C{col_fim}"
    if src.replace("'", '').endswith(novo.split('!', 1)[1]) and 'DBF' in src.upper():
        return False
    pivot_table.SourceData = novo
    return True


def _tabela_tem_linha(pivot_table, trecho_nome):
    try:
        for f in pivot_table.RowFields():
            if trecho_nome in norm(f.Name):
                return True
    except Exception:
        pass
    return False


def _aplicar_filtros_fixos_base(ws_com, pivot_table, feitos=None):
    """Passo 3 do vídeo: filtros fixos de cada aba. Devolve True se a tabela é da exceção do Quadro (FLUXO PRD = Tudo).
    `feitos` (set) recebe a descrição de cada filtro aplicado — vai para o quadro de aviso do fim."""
    nome_aba = norm(ws_com.Name)
    for inicio, campo, itens in FILTROS_FIXOS_BASE:
        if nome_aba.startswith(norm(inicio)):
            if _filtrar_campo_somente(pivot_table, campo, itens) and feitos is not None:
                feitos.add(f'{inicio} · {campo} = ' + ', '.join(sorted(itens)))
    if nome_aba.startswith(norm(ABA_QUADRO_GESTAO)) and _tabela_tem_linha(pivot_table, 'MAQUINA'):
        if _filtrar_campo_somente(pivot_table, 'FLUXO PRD', None) and feitos is not None:
            feitos.add('PREP_Quadro · PESO POR BC · FLUXO PRD = (Tudo)')
        return True
    return False


def _quadro_atualizacoes_base(resultado, usou_excel=True):
    """Texto do quadro de aviso: o que o sistema atualizou na planilha (regras fixas V275), item por item."""
    if not usou_excel:
        return ('\n\nATUALIZAÇÕES DA PLANILHA (padrão do sistema)\n'
                '  ⚠ Não feitas: gerada sem o Excel neste PC — classificação da DBF, tabelas dinâmicas, filtros, '
                'data da PREP_Lista e nomes/cores das abas só rodam com o Excel instalado.')
    ok = lambda v: '✔' if v else '⚠'
    ordem = resultado.get('ordem_dbf') or []
    linhas = ['', '', 'ATUALIZAÇÕES DA PLANILHA (padrão do sistema)']
    linhas.append(f"  {ok(ordem)} 1. DBF classificada: "
                  + (' → '.join(f'{n} ({"Z→A" if n == "PAI X FILHO" else "A→Z"})' for n in ordem) if ordem
                     else 'NÃO classificou (confira a ordem manualmente)'))
    n_pt, n_err = resultado.get('pivots_atualizados') or 0, resultado.get('pivots_com_erro') or 0
    linhas.append(f"  {ok(n_pt and not n_err)} 2. Tabelas dinâmicas: fonte = {resultado.get('fonte_pivots') or 'DBF'}"
                  f" · {resultado.get('fontes_tabelas') or resultado.get('caches_corrigidos') or 0} fonte(s) alterada(s) · {n_pt} atualizada(s)"
                  + (f' · {n_err} com erro' if n_err else ''))
    filtros = resultado.get('filtros_fixos') or []
    linhas.append(f"  {ok(filtros)} 3. Filtros:" + ('' if filtros else ' nenhum filtro fixo aplicado'))
    linhas += [f'       • {t}' for t in filtros]
    linhas.append(f"  {ok(resultado.get('data_prep_lista'))} 4. PREP_Lista · H5 = data de hoje "
                  f"({date.today().strftime('%d/%m/%Y')})")
    n_abas = resultado.get('abas_renomeadas') or 0
    linhas.append(f"  {ok(n_abas)} 5. Abas com nome e cor do padrão: {n_abas} de {len(NOMES_CORES_ABAS_BASE)}"
                  " (FOCCO_VISION_NDPCP301 → FOCCO_VISION_NDPCP399)")
    return '\n'.join(linhas)


def _renomear_e_pintar_abas_base(wb_com):
    """Passo 5: nomes e cores das abas (o Excel ajusta sozinho as fórmulas que citam a aba renomeada)."""
    por_nome = {}
    for sh in wb_com.Worksheets:
        por_nome[norm(sh.Name)] = sh
    feitas = 0
    for antigo, novo, cor in NOMES_CORES_ABAS_BASE:
        sh = por_nome.get(norm(antigo)) or por_nome.get(norm(novo))
        if sh is None:
            continue
        try:
            if sh.Name != novo:
                sh.Name = novo
            if cor:
                sh.Tab.Color = _rgb_para_cor_excel(cor)
            feitas += 1
        except Exception:
            pass
    return feitas


def gerar_base_preenchida_via_excel(caminho_base, linhas_consolidadas, fluxo_map, lote,
                                     caminho_saida, linhas_foco=None, progresso=None,
                                     atualizar_vinculo_lantek=False):
    """Igual a gerar_base_preenchida, mas escrevendo direto no arquivo via
    automação do Excel (COM/pywin32) — usado quando a base é .xlsb, pra
    nunca precisar converter: o Excel abre, escreve e salva no MESMO
    formato original, com fidelidade total (é o Excel de verdade fazendo).
    Precisa de "pip install pywin32" e do Excel instalado (só Windows)."""
    try:
        import win32com.client
        import pywintypes
    except ImportError:
        raise RuntimeError(
            'precisa do pacote "pywin32" (pip install pywin32) e do Excel instalado nesta máquina '
            'pra escrever direto em .xlsb')

    def avisa(msg):
        if progresso:
            progresso(msg)

    tempos = {}
    _t_fase = {'inicio': time.perf_counter(), 'nome': None}

    def fase(nome):
        agora = time.perf_counter()
        if _t_fase['nome'] is not None:
            tempos[_t_fase['nome']] = round(agora - _t_fase['inicio'], 2)
        _t_fase['inicio'], _t_fase['nome'] = agora, nome
        avisa(f'Gerando base pelo Excel — {nome}…')

    caminho_base = os.path.abspath(caminho_base)
    caminho_saida = os.path.abspath(caminho_saida)
    _CACHE_OBSERVACOES_POR_ABA.clear()  # nunca reaproveita observação de uma geração anterior
    ext_saida = ext_of(caminho_saida)
    file_format = _EXCEL_FILEFORMAT.get(ext_saida, 50)

    excel = None
    wb_com = None
    try:
        fase('abrindo o Excel')
        excel = win32com.client.DispatchEx('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False
        # Evita o diálogo "Atualizar vínculos?" (ou qualquer outro aviso
        # ao abrir) travar pra sempre — com Visible=False essa caixa some
        # da tela mas continua esperando um clique que nunca vem, e o
        # Open() trava minutos (já vi passar de 30min) até alguém matar o
        # processo do Excel no Gerenciador de Tarefas. Isso desliga essa
        # pergunta de vez: sempre abre sem atualizar vínculo nenhum.
        try:
            excel.AskToUpdateLinks = False
        except Exception:
            pass
        try:
            excel.AlertBeforeOverwriting = False
        except Exception:
            pass

        # abre a planilha PRIMEIRO — o Excel so deixa mudar o modo de
        # calculo com pelo menos um workbook aberto, senao da erro COM
        # UpdateLinks=0 reforça a mesma proteção direto no Open() (não
        # depende só da propriedade AskToUpdateLinks do app).
        wb_com = excel.Workbooks.Open(caminho_base, UpdateLinks=0)

        calc_original = excel.Calculation
        try:
            excel.Calculation = -4135  # xlCalculationManual — nao recalcula a cada escrita (bem mais rapido)
        except Exception:
            calc_original = None  # nao conseguiu mudar; segue no modo que o Excel ja estava
        excel.ScreenUpdating = False
        for _prop in ('EnableEvents',):
            try:
                setattr(excel, _prop, False)      # sem macros/eventos reagindo a cada escrita
            except Exception:
                pass

        try:
            ws = wb_com.Sheets('DBF')
        except Exception:
            raise RuntimeError('a planilha base nao tem aba "DBF"')
        ws.Cells(LINHA_NUM_PCT, COL_NUM_PCT).Value = _valor_lote(lote)
        ws.Cells(LINHA_DT_REFRESH, COL_DT_REFRESH).Value = pywintypes.Time(
            datetime.combine(date.today(), datetime.min.time()))

        # 1) limpa a area de dados antiga (colunas A-AI + as 4 colunas de fluxo)
        fase('limpando dados antigos')
        ultima_linha_antiga = ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1
        col_dbf_fim_letra = get_column_letter(COL_DBF_FIM + 1)
        ws.Range(f'A{LINHA_INICIAL_BASE}:{col_dbf_fim_letra}{ultima_linha_antiga}').ClearContents()
        c_ini, c_fim = get_column_letter(IDX_MAQ_BC), get_column_letter(IDX_MAQ_G3M)
        ws.Range(f'{c_ini}{LINHA_INICIAL_BASE}:{c_fim}{ultima_linha_antiga}').ClearContents()

        # 2) monta a matriz de dados novos (so os valores — sem tocar em formula/estilo)
        fase('montando os dados novos')
        C_POS = IE['POS_PEZ']
        com_fluxo, sem_fluxo = 0, 0
        marcas_achadas = set()
        linhas_consolidadas, resumo_dup = remover_linhas_duplicadas(linhas_consolidadas, fluxo_map)
        n = len(linhas_consolidadas)
        pos_com_filhos = construir_pos_com_filhos(linhas_consolidadas)
        matriz_dbf = []
        matriz_fluxo = []  # ordem: BC, CH, G6m, G3m
        linhas_perfil_uc = []  # offsets que caem na exceção fixa (ED3 -> Perfiladeira U/C)
        COLS_ORDEM_FLUXO = [IDX_MAQ_BC, IDX_MAQ_CH, IDX_MAQ_G6M, IDX_MAQ_G3M]
        for offset, row in enumerate(linhas_consolidadas):
            linha_vals = []
            for c0 in range(COL_DBF_INICIO, COL_DBF_FIM + 1):
                v = row[c0]
                if v == '' or v is None:
                    linha_vals.append(None)
                    continue
                s = str(v).strip()
                num_s = s.replace(',', '.') if (',' in s and '.' not in s) else s
                linha_vals.append(float(num_s) if re.fullmatch(r'-?\d+(\.\d+)?', num_s) else s)
            matriz_dbf.append(linha_vals)

            eh_filho = bool(row[C_POS] and row[C_POS].strip())
            f = achar_fluxo_da_linha(row, fluxo_map, pos_com_filhos) if eh_filho else None
            marca_x = [None, None, None, None]  # BC, CH, G6m, G3m
            if f:
                if f['col'] in COLS_ORDEM_FLUXO:
                    marca_x[COLS_ORDEM_FLUXO.index(f['col'])] = 'X'
                elif f['col'] == IDX_MAQ_PERFIL_UC:
                    linhas_perfil_uc.append(offset)
                com_fluxo += 1
                marcas_achadas.add(f['chave'])
            elif eh_filho:
                sem_fluxo += 1
            matriz_fluxo.append(marca_x)

        # 3) escreve tudo de uma vez (range grande — MUITO mais rapido que celula a celula)
        fase('escrevendo a planilha')
        if n:
            ws.Range(ws.Cells(LINHA_INICIAL_BASE, COL_DBF_INICIO + 1),
                     ws.Cells(LINHA_INICIAL_BASE + n - 1, COL_DBF_FIM + 1)).Value = matriz_dbf
            ws.Range(ws.Cells(LINHA_INICIAL_BASE, IDX_MAQ_BC),
                     ws.Cells(LINHA_INICIAL_BASE + n - 1, IDX_MAQ_G3M)).Value = matriz_fluxo
        # coluna extra da exceção fixa (ED3) — celula a celula, sem limpar o
        # resto da coluna (ela tem marcação manual de outras posições)
        for offset in linhas_perfil_uc:
            ws.Cells(LINHA_INICIAL_BASE + offset, IDX_MAQ_PERFIL_UC).Value = 'X'

        # 3b) "arrasta" as fórmulas da aba DBF (colunas depois de AI — são
        # dezenas de colunas auxiliares tipo OF-TRECHO, Chave #1..#10 etc,
        # que alimentam as outras pivôs) pra baixo, até a última linha de
        # dado nova — sem isso, numa obra grande que passa da quantidade de
        # linhas que o modelo já tinha preenchido, essas colunas ficam
        # vazias dali pra baixo e as pivôs saem incompletas. Quem ajusta a
        # referência de célula (linha a linha) é o próprio Excel via
        # AutoFill — exatamente como arrastar a alcinha no Excel de
        # verdade, não uma cópia literal de texto.
        #
        # IMPORTANTE: as colunas de marcação de máquina (PERFIL.U/C, BC,
        # CH, G6m, G3m — de IDX_MAQ_PERFIL_UC até IDX_MAQ_G3M) ficam NO
        # MEIO desse intervalo de colunas, mas eu acabei de escrever nelas
        # no passo 3 (não são fórmula, são os "X" calculados aqui). Se o
        # AutoFill passar por cima delas, ele sobrescreve esse "X" com o
        # que tiver na linha-molde (LINHA_INICIAL_BASE), que normalmente
        # está em branco — apagando quase toda marcação de fluxo (bug real
        # que já aconteceu: 849 marcadas no cálculo, só 75 sobreviviam no
        # arquivo final). Por isso o AutoFill roda em dois pedaços,
        # pulando esse bloco de colunas.
        try:
            ultima_coluna_com_formula = ws.Cells(LINHA_INICIAL_BASE - 1, ws.Columns.Count).End(-4159).Column
        except Exception:
            ultima_coluna_com_formula = 0
        if n and ultima_coluna_com_formula > COL_DBF_FIM + 1:
            fase('arrastando fórmulas (AutoFill)')
            linha_fim_novo = LINHA_INICIAL_BASE + n - 1
            if linha_fim_novo > LINHA_INICIAL_BASE:
                bloco_protegido_ini, bloco_protegido_fim = IDX_MAQ_PERFIL_UC, IDX_MAQ_G3M

                def autofill_colunas(col_ini, col_fim):
                    if col_ini > col_fim:
                        return
                    origem = ws.Range(ws.Cells(LINHA_INICIAL_BASE, col_ini),
                                       ws.Cells(LINHA_INICIAL_BASE, col_fim))
                    destino = ws.Range(ws.Cells(LINHA_INICIAL_BASE, col_ini),
                                        ws.Cells(linha_fim_novo, col_fim))
                    origem.AutoFill(Destination=destino, Type=0)  # xlFillDefault

                autofill_colunas(COL_DBF_FIM + 2, bloco_protegido_ini - 1)
                autofill_colunas(bloco_protegido_fim + 1, ultima_coluna_com_formula)

        nao_encontradas = []
        if fluxo_map:
            for chave, info in fluxo_map.get('granular', fluxo_map).items():
                if chave not in marcas_achadas:
                    of, marca = chave.split('|', 1)
                    nao_encontradas.append((of, marca, info['maq']))

        # 4) aba FOCCO_VISION_NDPCP301 (opcional)
        linhas_foco_gravadas = 0
        if linhas_foco:
            fase('escrevendo aba FOCO')
            try:
                ws_foco = wb_com.Sheets(ABA_FOCCO)
            except Exception:
                try:
                    ws_foco = wb_com.Sheets('FOCCO_VISION_NDPCP399')   # base que já saiu do sistema (aba renomeada)
                except Exception:
                    raise RuntimeError(f'a planilha base nao tem aba "{ABA_FOCCO}"')
            n_cols_foco = len(ESQUEMA_FOCCO)
            ultima_linha_foco = ws_foco.UsedRange.Row + ws_foco.UsedRange.Rows.Count - 1
            col_foco_fim = get_column_letter(n_cols_foco)
            ws_foco.Range(f'A{LINHA_INICIAL_FOCCO}:{col_foco_fim}{ultima_linha_foco}').ClearContents()
            matriz_foco = []
            for row in linhas_foco:
                linha_vals = []
                for c0, v in enumerate(row):
                    val = _coagir_valor_foco(ESQUEMA_FOCCO[c0], v)
                    # COM/pywin32 espera datetime, nao date puro
                    if isinstance(val, date) and not isinstance(val, datetime):
                        val = datetime.combine(val, datetime.min.time())
                    linha_vals.append(val)
                matriz_foco.append(linha_vals)
            if matriz_foco:
                nf = len(matriz_foco)
                ws_foco.Range(ws_foco.Cells(LINHA_INICIAL_FOCCO, 1),
                               ws_foco.Cells(LINHA_INICIAL_FOCCO + nf - 1, n_cols_foco)).Value = matriz_foco
            linhas_foco_gravadas = len(linhas_foco)

        # 5) Recalcula TUDO primeiro (as tabelas dinamicas dependem de
        # colunas com formula depois da AI — se atualizar a pivot antes de
        # recalcular, ela le valor velho/nao calculado e aparece vazia ou
        # com erro #N/D). So depois disso atualiza cada tabela dinamica de
        # cada aba (nao "RefreshAll" — evita travar em conexao externa que
        # nao existe nesta maquina).
        vinculos_lantek = 0
        if atualizar_vinculo_lantek:
            fase('atualizando o vínculo com a planilha LANTEK_SKA')
            vinculos_lantek = _atualizar_vinculo_lantek(wb_com)

        fase('recalculando fórmulas')
        # O cálculo fica em MANUAL até o fim (antes voltava a automático aqui: cada refresh/filtro de tabela
        # dinâmica disparava recálculo de tudo — era o grosso da lentidão). O modo original volta antes de salvar.
        try:
            # Calculate() (recalcula só o que está "sujo", seguindo a árvore
            # de dependências) em vez de CalculateFullRebuild() (reprocessa
            # TODA fórmula da pasta de trabalho do zero, ignorando o que já
            # estava calculado) — nada antes disso quebra a árvore de
            # dependências (só escrevemos valor puro + AutoFill), então o
            # full rebuild aqui era custo sem necessidade. O full rebuild lá
            # embaixo (depois do refresh das pivôs) continua como estava,
            # por segurança.
            excel.Calculate()
        except Exception:
            pass

        # 5-) V275: classifica a DBF igual ao vídeo (OF-TRECHO, Nº LIBERAÇÃO, MARCA, PAI X FILHO Z→A) e recalcula
        ordem_dbf = []
        try:
            fase('classificando a DBF')
            # V277: classifica SÓ as linhas com dado (antes ia até o fim da planilha, junto com as linhas de
            # fórmula vazias lá de baixo — as tabelas dinâmicas saíam só com #VALOR!/(vazio))
            ult_lin = LINHA_INICIAL_BASE + n - 1
            ult_col = max(ultima_coluna_com_formula or 0, COL_DBF_FIM + 1, IDX_MAQ_G3M)
            if n > 1:
                ordem_dbf = _ordenar_dbf_base(ws, ult_lin, ult_col)
            if ordem_dbf:
                # depois de classificar o Excel não marca as fórmulas como "sujas": recalcula TUDO antes das pivôs
                try:
                    excel.CalculateFull()
                except Exception:
                    excel.Calculate()
        except Exception as e:
            ordem_dbf = []
            avisa(f'não consegui classificar a DBF: {e}')
        # data de hoje na PREP_Lista (H5)
        data_prep_ok = False
        for _sh in wb_com.Worksheets:
            if norm(_sh.Name).startswith(norm(ABA_PREP_LISTA)):
                try:
                    _sh.Range(CELULA_DATA_PREP_LISTA).Value = pywintypes.Time(
                        datetime.combine(date.today(), datetime.min.time()))
                    data_prep_ok = True
                except Exception:
                    pass

        # 5a) Corrige o INTERVALO de cada pivot cache que aponta pra aba DBF —
        # elas ficam presas num intervalo fixo antigo (ex.: "DBF!$A$9:$GD$1021")
        # que nao cresce sozinho quando a DBF ganha mais linhas. Sem isso, o
        # RefreshTable so relê o pedacinho antigo e a tabela fica vazia/errada.
        # V277: a fonte das tabelas vai só até a ÚLTIMA LINHA COM DADO da DBF (igual o vídeo: DBF!$A$9:$GE$1004).
        # Antes ia até o fim do intervalo usado (às vezes a linha 1.048.576) e as tabelas saíam vazias/#VALOR!.
        ultima_linha_dbf = (LINHA_INICIAL_BASE + n - 1) if n else (ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1)
        caches_corrigidos, caches_com_erro = 0, 0
        fase('corrigindo intervalo das tabelas dinâmicas')
        import re as _re
        for i in range(1, wb_com.PivotCaches().Count + 1):
            cache = wb_com.PivotCaches().Item(i)
            try:
                # zera o "historico" de itens que a tabela guarda mesmo depois
                # que eles somem da fonte (é o que fazia obra de pacote antigo
                # continuar aparecendo no filtro OF-Trecho mesmo sem estar
                # mais na DBF) — precisa ser setado ANTES do refresh
                try:
                    cache.MissingItemsLimit = 0  # xlMissingItemsNone
                except Exception:
                    pass
                src = str(cache.SourceData)
                novo_src = None
                # formato A1: "DBF!$A$9:$GD$1021" (ou "'DBF'!...")
                m = _re.match(r"^'?([^'!]+)'?!\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)$", src)
                if m and norm(m.group(1)) == norm('DBF'):
                    col_ini, lin_ini, col_fim = m.group(2), m.group(3), m.group(4)
                    novo_src = f"DBF!${col_ini}${lin_ini}:${col_fim}${ultima_linha_dbf}"
                if novo_src is None:
                    # formato R1C1: "DBF!R9C1:R1021C186"
                    m = _re.match(r"^'?([^'!]+)'?!R(\d+)C(\d+):R(\d+)C(\d+)$", src)
                    if m and norm(m.group(1)) == norm('DBF'):
                        lin_ini, col_ini, col_fim = m.group(2), m.group(3), m.group(5)
                        novo_src = f"DBF!R{lin_ini}C{col_ini}:R{ultima_linha_dbf}C{col_fim}"
                if novo_src is None:
                    continue
                if novo_src != src:
                    cache.SourceData = novo_src
                cache.Refresh()                     # V277: sempre relê (mesmo intervalo, dados novos/classificados)
                caches_corrigidos += 1
            except Exception:
                caches_com_erro += 1

        pivots_atualizados, pivots_com_erro = 0, 0
        erros_pivot = []
        pivots_sem_pintura = 0
        caches_ja_atualizados = set()      # várias tabelas dividem o mesmo cache: ler os dados UMA vez por cache
        filtros_feitos = set()
        fontes_tabelas = 0
        fase('atualizando tabelas dinâmicas')
        for ws2 in wb_com.Worksheets:
            try:
                pts = ws2.PivotTables()
                total = pts.Count
            except Exception:
                continue
            for i in range(1, total + 1):
                nome_pivot = '?'
                try:
                    pt = pts.Item(i)
                    nome_pivot = pt.Name
                    # V278: "Alterar Fonte de Dados" em CADA tabela (igual o vídeo) — DBF!$A$9 até a última linha
                    # com dado; depois Atualizar a tabela (sempre, não só uma vez por cache)
                    try:
                        if _apontar_tabela_para_dbf(pt, ultima_linha_dbf):
                            fontes_tabelas += 1
                    except Exception as e_src:
                        erros_pivot.append(f'{ws2.Name} / {nome_pivot}: fonte não mudou ({e_src})')
                    pt.RefreshTable()
                    # forca a tabela a recalcular seu layout (RefreshTable
                    # sozinho as vezes deixa a area de dados velha/vazia
                    # ate a proxima interacao manual do usuario)
                    try:
                        pt.Update()
                    except Exception:
                        pass
                    try:
                        if _tirar_tipo_pintura_da_lista_prep(ws2, pt):
                            pivots_sem_pintura += 1
                    except Exception:
                        pass
                    try:
                        pt.ManualUpdate = True       # os ajustes de filtro abaixo não redesenham a tabela a cada item
                    except Exception:
                        pass
                    # Se a tabela tem um campo "FLUXO PRD", garante que só
                    # Fluxo 1-4 ficam marcados como visiveis no filtro —
                    # o refresh as vezes troca isso sozinho (ex.: entra
                    # "PERFILAD. L" e some "Fluxo 3" da seleção).
                    excecao_quadro = norm(ws2.Name).startswith(norm(ABA_QUADRO_GESTAO)) and \
                        _tabela_tem_linha(pt, 'MAQUINA')
                    try:
                        if not excecao_quadro:
                            _fixar_filtro_fluxo_prd(pt)
                            if norm(ws2.Name).startswith(norm(ABA_PREP_LISTA)):
                                pt.PivotFields('FLUXO PRD')
                                filtros_feitos.add('PREP_Lista · FLUXO PRD = Fluxo 1, 2, 3 e 4')
                    except Exception:
                        pass
                    # Qualquer outro filtro dessa aba que tenha uma
                    # observação "<<< Desmarcar filtro ..." ao lado —
                    # aplica ela AGORA, sempre do zero (não confia em
                    # nenhum estado de filtro que ficou salvo de antes,
                    # que pode estar errado — foi assim que "COMPONENTE
                    # x LIC" ficou preso mostrando só "LIC" e a pivô
                    # "Peso x Fluxo" saiu vazia pra um lote sem peça LIC)
                    try:
                        _aplicar_filtros_das_observacoes(ws2, pt)
                    except Exception:
                        pass
                    try:
                        _aplicar_filtros_fixos_base(ws2, pt, filtros_feitos)   # V278: por último (os do vídeo valem)
                    except Exception:
                        pass
                    try:
                        pt.ManualUpdate = False
                    except Exception:
                        pass
                    try:
                        pt.RefreshTable()
                    except Exception:
                        pass
                    pivots_atualizados += 1
                except Exception as e:
                    try:
                        pt.ManualUpdate = False       # nunca deixa a tabela travada em atualização manual
                    except Exception:
                        pass
                    pivots_com_erro += 1
                    erros_pivot.append(f'{ws2.Name} / {nome_pivot}: {e}')

        # recalcula de novo — refresh de pivot pode gerar formulas novas
        # (ex.: celulas que leem resultado da pivot) que precisam recalcular.
        # Calculate() refaz só o que ficou "sujo" (antes era CalculateFullRebuild = tudo do zero, minutos a mais).
        # Se um dia precisar do cálculo completo: RECALCULO_COMPLETO_NA_BASE = True.
        fase('recalculando de novo')
        try:
            if RECALCULO_COMPLETO_NA_BASE:
                excel.CalculateFullRebuild()
            else:
                excel.Calculate()
        except Exception:
            pass
        if calc_original is not None:
            try:
                excel.Calculation = calc_original
            except Exception:
                pass

        fase('renomeando e pintando as abas')
        abas_renomeadas = 0
        try:
            abas_renomeadas = _renomear_e_pintar_abas_base(wb_com)
        except Exception:
            pass
        try:
            wb_com.Worksheets(1).Activate()
        except Exception:
            pass

        fase('salvando o arquivo')
        wb_com.SaveAs(caminho_saida, FileFormat=file_format)
        tempos['salvando o arquivo'] = round(time.perf_counter() - _t_fase['inicio'], 2)
        return {'com_fluxo': com_fluxo, 'sem_fluxo': sem_fluxo, 'nao_encontradas': nao_encontradas,
                'duplicadas': resumo_dup,
                'linhas_foco': linhas_foco_gravadas,
                'pivots_atualizados': pivots_atualizados, 'pivots_com_erro': pivots_com_erro,
                'caches_corrigidos': caches_corrigidos, 'caches_com_erro': caches_com_erro,
                'pivots_sem_pintura': pivots_sem_pintura,
                'erros_pivot': erros_pivot, 'tempos': tempos, 'vinculos_lantek': vinculos_lantek,
                'ordem_dbf': ordem_dbf, 'abas_renomeadas': abas_renomeadas,
                'filtros_fixos': sorted(filtros_feitos), 'data_prep_lista': data_prep_ok,
                'fonte_pivots': f'DBF!$A$9 até a linha {ultima_linha_dbf}', 'fontes_tabelas': fontes_tabelas}
    finally:
        try:
            if wb_com is not None:
                wb_com.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            if excel is not None:
                excel.Quit()
        except Exception:
            pass


def converter_xlsb_para_xlsx_via_excel(caminho_xlsb):
    """Usa o Excel de verdade (COM/pywin32) pra converter .xlsb -> .xlsx —
    fidelidade total (fórmulas, tabelas dinâmicas, formatação), porque
    quem faz a conversão é o próprio Excel, não uma lib. So funciona no
    Windows com Excel instalado; se não tiver, levanta erro claro pra
    cair no fallback manual."""
    try:
        import win32com.client
    except ImportError:
        raise RuntimeError(
            'conversão automática precisa do pacote "pywin32" (pip install pywin32) '
            'e do Excel instalado nesta máquina')

    caminho_xlsb = os.path.abspath(caminho_xlsb)
    pasta = os.path.dirname(caminho_xlsb)
    nome = os.path.splitext(os.path.basename(caminho_xlsb))[0]
    caminho_xlsx = os.path.join(pasta, f'{nome}_convertido_{date_tag()}.xlsx')

    excel = None
    wb_com = None
    try:
        excel = win32com.client.DispatchEx('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False
        # Mesma proteção contra o diálogo "Atualizar vínculos?" travando
        # pra sempre de forma invisível (ver comentário equivalente em
        # gerar_base_preenchida_via_excel).
        try:
            excel.AskToUpdateLinks = False
        except Exception:
            pass
        wb_com = excel.Workbooks.Open(caminho_xlsb, ReadOnly=True, UpdateLinks=0)
        # 51 = xlOpenXMLWorkbook (.xlsx)
        wb_com.SaveAs(caminho_xlsx, FileFormat=51)
    finally:
        try:
            if wb_com is not None:
                wb_com.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            if excel is not None:
                excel.Quit()
        except Exception:
            pass

    if not os.path.exists(caminho_xlsx):
        raise RuntimeError('o Excel não conseguiu gerar o .xlsx convertido')
    return caminho_xlsx


# ═══════════════════════════════════════════════════════════════════
# ANÁLISE — Comparativo de peso DBF × FOCCO (por marca e Grupo LIC)
# ═══════════════════════════════════════════════════════════════════
PALAVRAS_EXCLUIR_FOCCO = ('TINTA', 'ZINCO', 'CATALISADOR', 'DILUENTE')


def parse_one_dbf_analise(path):
    """Le uma DBF e agrega peso por marca (so linhas PAI, Peso Total > 0)."""
    planilhas = ler_arquivo_tabular(path)
    alvo = escolher_planilha_dbf(planilhas)
    if not alvo:
        raise RuntimeError(f'{os.path.basename(path)}: nenhuma planilha com dados')
    rows, hi = normalizar_dbf(alvo['rows'])
    if not rows:
        raise RuntimeError(f'{os.path.basename(path)}: sem linhas de dados (aba "{alvo["nome"]}")')
    C_MARCA, C_GRUPO = IE['MAR_PEZ'], IE['GRUPO LIC']
    C_QTD, C_PESO_TOT, C_NUM_DIS = IE['QTA_PEZ'], IE['Peso Total'], IE['NUM_DIS']
    if not any(r[C_MARCA].strip() for r in rows):
        raise RuntimeError(f'{os.path.basename(path)}: coluna MAR_PEZ / MARCA não encontrada (aba "{alvo["nome"]}")')

    marcas, of_trecho, obra = {}, '', ''
    for r in rows:
        if not r[C_MARCA] or not r[C_MARCA].strip():
            continue
        peso = parse_br(r[C_PESO_TOT])
        if peso <= 0:
            continue  # so linha PAI
        marca = r[C_MARCA].strip()
        grupo = r[C_GRUPO].strip() if r[C_GRUPO] else ''
        qtd = parse_br(r[C_QTD])
        marcas[marca] = {'grupo': grupo, 'qtd': qtd, 'peso': peso}
        if not of_trecho and r[C_NUM_DIS]:
            m = re.search(r'(\d{3,6})-(\d+-\d+)_', r[C_NUM_DIS])
            if m:
                of_trecho = f'{m.group(1)}-{m.group(2)}'
        if not obra and r[0] and r[0].strip():
            obra = re.sub(r'_L\d+$', '', r[0].strip())
    if not of_trecho:
        of_trecho = obra
    return {'marcas': marcas, 'ofTrecho': of_trecho, 'rows': rows}


def parse_multi_dbf_analise(paths):
    """Une varias DBFs: marcas em uniao (soma se a mesma marca aparecer em
    mais de um arquivo — caso raro, so por seguranca), linhas cruas
    concatenadas na ordem dos arquivos (usadas na aba 'DBF Validada')."""
    resultados = [parse_one_dbf_analise(p) for p in paths]
    all_marcas, of_trecho = {}, ''
    for r in resultados:
        if not of_trecho and r['ofTrecho']:
            of_trecho = r['ofTrecho']
        for marca, dado in r['marcas'].items():
            if marca in all_marcas:
                all_marcas[marca]['peso'] += dado['peso']
                all_marcas[marca]['qtd'] += dado['qtd']
            else:
                all_marcas[marca] = dict(dado)
    raw_rows = []
    for r in resultados:
        raw_rows.extend(r['rows'])
    return {'marcas': all_marcas, 'ofTrecho': of_trecho, 'rows': raw_rows}


def _dedup_focco(raw):
    """Mesma marca pode aparecer em varias linhas do FOCCO (bobina + chapa
    equivalente) — evita contar o mesmo peso duas vezes."""
    marcas = {}
    for marca, linhas in raw.items():
        bob_vals = set()
        for l in linhas:
            if 'BOBINA' in l['desc'] and '1200' in l['desc']:
                bob_vals.add(round(l['qtde'] * 1000))
        total = 0.0
        for l in linhas:
            if 'CHAPA' in l['desc'] and round(l['qtde'] * 1000) in bob_vals:
                continue
            total += l['qtde']
        marcas[marca] = {'peso': total, 'grupo': linhas[0]['grupo']}
    return marcas


def parse_focco_export(path):
    """Le o export do FOCCO (Excel ou HTML disfarçado) usado na Análise de
    Peso — diferente do relatório NDPCP301 (que enche a aba FOCCO_VISION).
    Aqui o cabeçalho esperado tem MARCA, GRP LIC, DESC TECNICA,
    QTDE CORRIGIDA, UM, OBRA, SUB TRECHO."""
    planilhas = ler_arquivo_tabular(path)
    rows, hi = None, -1
    for nome, r in planilhas:
        for i in range(min(15, len(r))):
            cel = [squash(v) for v in (r[i] or [])]
            if squash('MARCA') in cel:
                rows, hi = r, i
                break
        if rows is not None:
            break
    if rows is None:
        rows = planilhas[0][1] if planilhas else []
        hi = achar_cabecalho(rows, ['MARCA', 'GRP LIC', 'DESC TECNICA', 'QTDE CORRIGIDA', 'OBRA'])
    if not rows or hi < 0:
        raise RuntimeError('FOCCO: cabeçalho não encontrado')

    header = rows[hi]
    c_marca = find_col(header, 'MARCA')
    c_grupo = find_col(header, 'GRP LIC')
    c_desc = find_col(header, 'DESC TECNICA')
    c_qtde = find_col(header, 'QTDE CORRIGIDA')
    c_um = find_col(header, 'UM')
    c_obra = find_col(header, 'OBRA')
    c_subtr = find_col(header, 'SUB TRECHO')
    if c_marca < 0:
        raise RuntimeError('FOCCO: coluna MARCA não encontrada')

    def val(r, c):
        return r[c] if (c >= 0 and c < len(r)) else None

    raw, of_trecho = {}, ''
    for r in rows[hi + 1:]:
        if not r or val(r, c_marca) is None:
            continue
        marca = str(val(r, c_marca)).strip()
        if not marca:
            continue
        if not of_trecho and val(r, c_obra):
            subtr = str(val(r, c_subtr)).replace('_', '-') if val(r, c_subtr) else ''
            of_trecho = f'{val(r, c_obra)}-{subtr}'
        um = str(val(r, c_um)).upper().strip() if val(r, c_um) else ''
        if um and um != 'KG':
            continue
        desc = str(val(r, c_desc)).upper() if val(r, c_desc) else ''
        if any(p in desc for p in PALAVRAS_EXCLUIR_FOCCO):
            continue
        qtde = parse_br(val(r, c_qtde))
        grupo = str(val(r, c_grupo)).strip() if val(r, c_grupo) else ''
        raw.setdefault(marca, []).append({'desc': desc, 'qtde': qtde, 'grupo': grupo})

    marcas = _dedup_focco(raw)
    return {'marcas': marcas, 'ofTrecho': of_trecho}


def get_status(delta, pct):
    if abs(delta) < 0.001:
        return {'cls': 'ok', 'label': 'OK', 'filter': 'ok'}
    if abs(pct) <= 1:
        return {'cls': 'ok', 'label': f'✓ {pct:+.2f}%', 'filter': 'ok'}
    if abs(pct) <= 5:
        return {'cls': 'warn', 'label': f'⚠ {pct:+.2f}%', 'filter': 'divergente'}
    return {'cls': 'err', 'label': f'✕ {pct:+.2f}%', 'filter': 'divergente'}


def build_results(dbf, focco):
    """Cruza DBF x FOCCO por marca -> (det_data, grp_data)."""
    all_marcas = set(dbf['marcas'].keys()) | set(focco['marcas'].keys())
    det_data, grupo_map = [], {}
    for marca in all_marcas:
        d, f = dbf['marcas'].get(marca), focco['marcas'].get(marca)
        peso_dbf = d['peso'] if d else 0.0
        peso_focco = f['peso'] if f else 0.0
        grupo = d['grupo'] if d else f['grupo']
        qtd = d['qtd'] if d else 0.0
        delta = peso_focco - peso_dbf
        pct = (delta / peso_dbf * 100) if peso_dbf != 0 else (100.0 if peso_focco != 0 else 0.0)
        det_data.append({'marca': marca, 'grupo': grupo, 'qtd': qtd,
                          'pesoDBF': peso_dbf, 'pesoFOCCO': peso_focco,
                          'delta': delta, 'pct': pct,
                          'soloDBF': bool(d) and not f, 'soloFOCCO': (not d) and bool(f)})
        g = grupo_map.setdefault(grupo, {'grupo': grupo, 'marcas': 0, 'pesoDBF': 0.0, 'pesoFOCCO': 0.0})
        g['marcas'] += 1
        g['pesoDBF'] += peso_dbf
        g['pesoFOCCO'] += peso_focco
    grp_data = []
    for g in grupo_map.values():
        delta = g['pesoFOCCO'] - g['pesoDBF']
        pct = (delta / g['pesoDBF'] * 100) if g['pesoDBF'] != 0 else 0.0
        grp_data.append({**g, 'delta': delta, 'pct': pct})
    grp_data.sort(key=lambda g: g['grupo'])
    det_data.sort(key=lambda r: (r['grupo'], r['marca']))
    return det_data, grp_data


def _analisar_dbf_focco(dbf_paths, focco_path):
    """Le as DBFs + o export do FOCCO e cruza — roda em thread separada,
    nao mexe em nada do Qt."""
    dbf = parse_multi_dbf_analise(dbf_paths)
    focco = parse_focco_export(focco_path)
    of_trecho = dbf['ofTrecho'] or focco['ofTrecho'] or ''
    det_data, grp_data = build_results(dbf, focco)
    return {'det_data': det_data, 'grp_data': grp_data, 'dbf_rows': dbf['rows'], 'of_trecho': of_trecho}


def exportar_analise_excel(caminho_saida, nome_base, det_data, grp_data, dbf_rows, of_trecho):
    """Gera o Excel de validação: aba 'Análise DBF × FOCCO' (resumo por
    grupo + detalhe por marca) e aba 'DBF Validada' (a DBF crua colorida
    pelo status de cada marca)."""
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = 'Análise DBF × FOCCO'

    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    COR = {'hBg': '1E3A5F', 'hFn': 'FFFFFF', 'ok_bg': 'D1FAE5', 'ok_fn': '065F46',
           'warn_bg': 'FEF3C7', 'warn_fn': '92400E', 'err_bg': 'FEE2E2', 'err_fn': '991B1B',
           'solo_bg': 'FFF7ED', 'solo_fn': 'C2410C', 'tot_bg': 'E0E7FF'}
    thin = Side(style='thin', color='FFD1D5DB')
    border = Border(top=thin, bottom=thin, left=thin, right=thin)

    def fill(bg):
        return PatternFill('solid', fgColor=bg)

    def font(fn, bold=False):
        return Font(name='Calibri', color=fn, bold=bold)

    ws1.merge_cells('A1:H1')
    c = ws1['A1']
    c.value = f"VALIDAÇÃO — {nome_base} — {datetime.now().strftime('%d/%m/%Y')}"
    c.font = font('FFFFFF', True)
    c.fill = fill('1E40AF')
    c.alignment = Alignment(vertical='center', horizontal='left', indent=1)
    ws1.row_dimensions[1].height = 26

    ws1.merge_cells('A3:H3')
    c = ws1['A3']
    c.value = 'POR GRUPO LIC'
    c.font = font(COR['hFn'], True)
    c.fill = fill(COR['hBg'])
    c.alignment = Alignment(indent=1)
    ws1.row_dimensions[3].height = 18

    ws1.append(['Grupo LIC', 'Qtd Marcas', 'Peso DBF (kg)', 'Peso FOCCO (kg)', 'Delta (kg)', 'Delta %', 'Status'])
    for cell in ws1[4]:
        cell.font = font('E2E8F0', True)
        cell.fill = fill('334155')
        cell.alignment = Alignment(vertical='center', horizontal='center')
        cell.border = border
    ws1.row_dimensions[4].height = 16

    tD = tF = 0.0
    for g in grp_data:
        tD += g['pesoDBF']
        tF += g['pesoFOCCO']
        st = get_status(g['delta'], g['pct'])
        bg = COR['ok_bg'] if st['filter'] == 'ok' else (COR['err_bg'] if abs(g['pct']) > 5 else COR['warn_bg'])
        fn = COR['ok_fn'] if st['filter'] == 'ok' else (COR['err_fn'] if abs(g['pct']) > 5 else COR['warn_fn'])
        row = [g['grupo'], g['marcas'], g['pesoDBF'], g['pesoFOCCO'], g['delta'], g['pct'] / 100, st['label']]
        ws1.append(row)
        r = ws1.max_row
        for ci in range(1, 8):
            cell = ws1.cell(row=r, column=ci)
            cell.font = font(fn, bold=(ci == 1))
            cell.fill = fill(bg)
            cell.border = border
        ws1.cell(row=r, column=2).number_format = '0'
        ws1.cell(row=r, column=3).number_format = '#,##0.000'
        ws1.cell(row=r, column=4).number_format = '#,##0.000'
        ws1.cell(row=r, column=5).number_format = '+#,##0.000;-#,##0.000;"-"'
        ws1.cell(row=r, column=6).number_format = '+0.00%;-0.00%'
        ws1.cell(row=r, column=7).alignment = Alignment(horizontal='center')
        ws1.row_dimensions[r].height = 16

    td2 = tF - tD
    tp2 = (td2 / tD * 100) if tD != 0 else 0.0
    ws1.append(['TOTAL', sum(g['marcas'] for g in grp_data), tD, tF, td2, tp2 / 100, ''])
    r = ws1.max_row
    for ci in range(1, 8):
        cell = ws1.cell(row=r, column=ci)
        cell.font = font('1E3A5F', True)
        cell.fill = fill(COR['tot_bg'])
        cell.border = border
    ws1.cell(row=r, column=2).number_format = '0'
    ws1.cell(row=r, column=3).number_format = '#,##0.000'
    ws1.cell(row=r, column=4).number_format = '#,##0.000'
    ws1.cell(row=r, column=5).number_format = '+#,##0.000;-#,##0.000;"-"'
    ws1.cell(row=r, column=6).number_format = '+0.00%;-0.00%'
    ws1.row_dimensions[r].height = 18

    ws1.append([])
    ws1.append(['POR MARCA — DETALHE'])
    r = ws1.max_row
    ws1.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
    cell = ws1.cell(row=r, column=1)
    cell.font = font(COR['hFn'], True)
    cell.fill = fill(COR['hBg'])
    cell.alignment = Alignment(indent=1)
    ws1.row_dimensions[r].height = 18

    ws1.append(['Marca', 'Grupo LIC', 'Qtd DBF', 'Peso DBF (kg)', 'Peso FOCCO (kg)', 'Delta (kg)', 'Delta %', 'Status'])
    r = ws1.max_row
    for cell in ws1[r]:
        cell.font = font('E2E8F0', True)
        cell.fill = fill('334155')
        cell.alignment = Alignment(vertical='center', horizontal='center')
        cell.border = border
    ws1.row_dimensions[r].height = 16

    for row_d in det_data:
        st = get_status(row_d['delta'], row_d['pct'])
        if row_d['soloDBF'] or row_d['soloFOCCO']:
            bg, fn = COR['solo_bg'], COR['solo_fn']
        elif st['filter'] == 'ok':
            bg, fn = COR['ok_bg'], COR['ok_fn']
        elif abs(row_d['pct']) > 5:
            bg, fn = COR['err_bg'], COR['err_fn']
        else:
            bg, fn = COR['warn_bg'], COR['warn_fn']
        sl = '⚠ Só DBF' if row_d['soloDBF'] else ('⚠ Só FOCCO' if row_d['soloFOCCO'] else st['label'])
        solo = row_d['soloDBF'] or row_d['soloFOCCO']
        ws1.append([row_d['marca'], row_d['grupo'],
                    row_d['qtd'] if row_d['qtd'] > 0 else None,
                    row_d['pesoDBF'] if row_d['pesoDBF'] > 0 else None,
                    row_d['pesoFOCCO'] if row_d['pesoFOCCO'] > 0 else None,
                    None if solo else row_d['delta'],
                    None if solo else row_d['pct'] / 100,
                    sl])
        r = ws1.max_row
        for ci in range(1, 9):
            cell = ws1.cell(row=r, column=ci)
            cell.font = font(fn, bold=(ci == 1))
            cell.fill = fill(bg)
            cell.border = border
        ws1.cell(row=r, column=8).alignment = Alignment(horizontal='center')
        for ci in (4, 5):
            if ws1.cell(row=r, column=ci).value is not None:
                ws1.cell(row=r, column=ci).number_format = '#,##0.000'
        if ws1.cell(row=r, column=6).value is not None:
            ws1.cell(row=r, column=6).number_format = '+#,##0.000;-#,##0.000;"-"'
        if ws1.cell(row=r, column=7).value is not None:
            ws1.cell(row=r, column=7).number_format = '+0.00%;-0.00%'
        ws1.row_dimensions[r].height = 15

    larguras = [30, 26, 12, 18, 18, 16, 12, 20]
    for i, w in enumerate(larguras, start=1):
        ws1.column_dimensions[get_column_letter(i)].width = w

    # ── ABA 2: DBF Validada ──
    ws2 = wb.create_sheet('DBF Validada')
    sm_map = {}
    for row_d in det_data:
        st = get_status(row_d['delta'], row_d['pct'])
        if row_d['soloDBF'] or row_d['soloFOCCO']:
            sm_map[row_d['marca']] = 'solo'
        elif st['filter'] == 'ok':
            sm_map[row_d['marca']] = 'ok'
        elif abs(row_d['pct']) > 5:
            sm_map[row_d['marca']] = 'err'
        else:
            sm_map[row_d['marca']] = 'warn'
    cor_status = {'ok': 'D1FAE5', 'warn': 'FEF3C7', 'err': 'FEE2E2', 'solo': 'FFF7ED'}

    header = ESQUEMA_DBF[:]
    n_cols = len(header)
    ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(n_cols, 30))
    c = ws2.cell(row=1, column=1)
    c.value = f"DBF VALIDADA — {nome_base} — {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    c.font = font(COR['hFn'], True)
    c.fill = fill(COR['hBg'])
    c.alignment = Alignment(vertical='center', horizontal='left', indent=1)
    ws2.row_dimensions[1].height = 22

    for ci, h in enumerate(header, start=1):
        cell = ws2.cell(row=2, column=ci, value=h)
        cell.font = font(COR['hFn'], True)
        cell.fill = fill('334155')
        cell.alignment = Alignment(vertical='center', horizontal='center')
        cell.border = border
    ws2.row_dimensions[2].height = 17

    C_MARCA, C_PESO_TOT = IE['MAR_PEZ'], IE['Peso Total']
    for row_r in dbf_rows:
        if not any(v != '' for v in row_r):
            continue
        is_pai = parse_br(row_r[C_PESO_TOT]) > 0
        bg = cor_status.get(sm_map.get(row_r[C_MARCA]), 'FFFFFF') if is_pai else 'F8FAFC'
        vals = []
        for v in row_r:
            if v == '' or v is None:
                vals.append(None)
                continue
            s = str(v).strip()
            num_s = s.replace(',', '.') if (',' in s and '.' not in s) else s
            vals.append(float(num_s) if re.fullmatch(r'-?\d+(\.\d+)?', num_s) else s)
        ws2.append(vals)
        r = ws2.max_row
        for ci in range(1, n_cols + 1):
            cell = ws2.cell(row=r, column=ci)
            cell.font = Font(name='Calibri', size=9, color=('1E3A5F' if is_pai else '374151'), bold=is_pai)
            cell.fill = fill(bg)
            cell.border = border
        ws2.row_dimensions[r].height = 15 if is_pai else 13

    ws2.freeze_panes = 'A3'
    for i in range(1, n_cols + 1):
        ws2.column_dimensions[get_column_letter(i)].width = 24 if i - 1 == C_MARCA else 12

    wb.save(caminho_saida)


# ═══════════════════════════════════════════════════════════════════
# INTERFACE (PyQt5)
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# THREAD — roda a leitura/geração em segundo plano pra nao travar a
# janela (ler o Excel e escrever nele é a parte lenta)
# ═══════════════════════════════════════════════════════════════════
def _linha_separadora():
    linha = QFrame()
    linha.setFrameShape(QFrame.HLine)
    linha.setStyleSheet('color: #232a3b;')
    return linha


class DialogoObrasNaoAchadas(QDialog):
    """Telinha que aparece quando a busca automática não acha o DBF de
    alguma obra — em vez de só um aviso de erro, deixa escolher o
    arquivo na mão pra cada obra que faltou, direto ali, sem precisar
    sair do fluxo e ir procurar na aba de baixo."""

    def __init__(self, nao_achadas, callback_adicionar, parent=None, dica_extra=''):
        super().__init__(parent)
        self.setWindowTitle('Obra(s) não encontrada(s) — adicionar na mão')
        self.setMinimumWidth(520)
        self._callback_adicionar = callback_adicionar
        self._resolvidas = set()

        layout = QVBoxLayout(self)
        aviso = QLabel('A busca automática não achou o DBF dessas obras — clica em "Escolher '
                        'arquivo…" pra adicionar na mão, se você souber onde está:' + dica_extra)
        aviso.setWordWrap(True)
        layout.addWidget(aviso)

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setMaximumHeight(320)
        conteudo = QWidget()
        v_linhas = QVBoxLayout(conteudo)
        self._linhas = {}
        for obra in nao_achadas:
            linha = QHBoxLayout()
            lbl = QLabel(obra)
            lbl.setMinimumWidth(140)
            linha.addWidget(lbl)
            status = QLabel('não achada')
            status.setStyleSheet(f'color:{NEON_AMBER};')
            linha.addWidget(status, 1)
            btn = QPushButton('📁 Escolher arquivo…')
            btn.clicked.connect(lambda _=False, o=obra: self._escolher_arquivo(o))
            linha.addWidget(btn)
            v_linhas.addLayout(linha)
            self._linhas[obra] = (status, btn)
        v_linhas.addStretch()
        area.setWidget(conteudo)
        layout.addWidget(area)

        self._area_arrastar = DropArea(
            '⬇ ou arraste aqui o(s) DBF(s) — tenta casar pelo nome do arquivo com a obra certa da lista',
            self._arquivos_arrastados)
        layout.addWidget(self._area_arrastar)

        h_botoes = QHBoxLayout()
        h_botoes.addStretch()
        btn_fechar = QPushButton('Fechar')
        btn_fechar.setObjectName('btnPrincipal')
        btn_fechar.clicked.connect(self.accept)
        h_botoes.addWidget(btn_fechar)
        layout.addLayout(h_botoes)

    def _escolher_arquivo(self, obra):
        path, _ = QFileDialog.getOpenFileName(
            self, f'Escolher arquivo de DBF pra {obra}', '',
            'Suportados (*.xlsx *.xlsm *.xls *.xlsb *.csv *.txt *.tsv *.dbf);;Todos (*)')
        if not path:
            return
        self._callback_adicionar([path])
        self._resolvidas.add(obra)
        status, btn = self._linhas[obra]
        status.setText(f'✓ {os.path.basename(path)}')
        status.setStyleSheet(f'color:{NEON_GREEN};')
        btn.setText('Trocar arquivo…')

    def _arquivos_arrastados(self, paths):
        """Pra cada arquivo solto, tenta casar o nome dele com alguma
        obra ainda pendente da lista (mesma lógica de nome usada na
        busca automática) — se achar, marca aquela linha como
        resolvida; senão, adiciona na lista geral mesmo assim (o
        arquivo pode ser útil mesmo sem bater com nenhuma obra daqui)."""
        self._callback_adicionar(paths)
        for path in paths:
            nome_base = os.path.splitext(os.path.basename(path))[0]
            for obra in self._linhas:
                if obra in self._resolvidas:
                    continue
                if _nome_bate_obra(nome_base, obra.lower()):
                    self._resolvidas.add(obra)
                    status, btn = self._linhas[obra]
                    status.setText(f'✓ {os.path.basename(path)} (arrastado)')
                    status.setStyleSheet(f'color:{NEON_GREEN};')
                    btn.setText('Trocar arquivo…')
                    break


class DialogoCores(QDialog):
    """Telinha simples: um botão-amostra por cor principal do tema (usadas
    nos botões/destaques da tela). Clica na amostra, escolhe a cor, e o
    "Aplicar" já troca a tela inteira na hora, sem precisar reabrir o app."""

    def __init__(self, cores_atuais, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Cores da tela')
        self.setMinimumWidth(340)
        self.cores = dict(cores_atuais)
        self._amostras = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Clica numa cor pra trocar:'))

        campos = [
            ('cyan', 'Destaque / botões principais'),
            ('magenta', 'Botões de ação (Analisar, Processar...)'),
            ('green', 'Sucesso / concluído'),
            ('amber', 'Aviso'),
        ]
        for chave, rotulo in campos:
            linha = QHBoxLayout()
            amostra = QPushButton()
            amostra.setFixedSize(34, 26)
            amostra.setCursor(Qt.PointingHandCursor)
            amostra.clicked.connect(lambda _=False, k=chave: self._escolher(k))
            self._amostras[chave] = amostra
            self._pintar_amostra(chave)
            linha.addWidget(amostra)
            linha.addWidget(QLabel(rotulo), 1)
            layout.addLayout(linha)

        layout.addSpacing(8)
        layout.addWidget(QLabel('Tema da tela:'))
        h_modo = QHBoxLayout()
        self._btn_projeart = QPushButton('🏢 Projeart')
        self._btn_escuro = QPushButton('🌙 Escuro')
        self._btn_claro = QPushButton('☀ Claro')
        estilo_toggle = ('QPushButton:checked { border: 2px solid ' + NEON_CYAN + '; color: ' + NEON_CYAN + '; }')
        for b in (self._btn_projeart, self._btn_escuro, self._btn_claro):
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(estilo_toggle)
        self._btn_projeart.clicked.connect(lambda: self._escolher_modo('projeart'))
        self._btn_escuro.clicked.connect(lambda: self._escolher_modo('escuro'))
        self._btn_claro.clicked.connect(lambda: self._escolher_modo('claro'))
        h_modo.addWidget(self._btn_projeart)
        h_modo.addWidget(self._btn_escuro)
        h_modo.addWidget(self._btn_claro)
        layout.addLayout(h_modo)
        self._marcar_modo_atual()

        layout.addSpacing(8)
        h_botoes = QHBoxLayout()
        btn_padrao = QPushButton('Restaurar padrão')
        btn_padrao.clicked.connect(self._restaurar_padrao)
        h_botoes.addWidget(btn_padrao)
        h_botoes.addStretch()
        btn_cancelar = QPushButton('Cancelar')
        btn_cancelar.clicked.connect(self.reject)
        btn_aplicar = QPushButton('Aplicar')
        btn_aplicar.setObjectName('btnPrincipal')
        btn_aplicar.clicked.connect(self.accept)
        h_botoes.addWidget(btn_cancelar)
        h_botoes.addWidget(btn_aplicar)
        layout.addLayout(h_botoes)

    def _pintar_amostra(self, chave):
        cor = self.cores[chave]
        self._amostras[chave].setStyleSheet(
            f'background-color:{cor}; border:1px solid #2a3348; border-radius:5px;')

    def _escolher(self, chave):
        atual = QColor(self.cores[chave])
        escolhida = QColorDialog.getColor(atual, self, 'Escolher cor')
        if escolhida.isValid():
            self.cores[chave] = escolhida.name()
            self._pintar_amostra(chave)

    def _escolher_modo(self, modo):
        self.cores['modo'] = modo
        # cada tema tem as cores de destaque dele: ao escolher o tema, vêm junto
        base = dict(CORES_PADRAO) if modo == 'projeart' else dict(CORES_NEON_ANTIGAS)
        for k in ('cyan', 'magenta', 'green', 'amber'):
            self.cores[k] = base[k]
        for chave in self._amostras:
            self._pintar_amostra(chave)
        self._marcar_modo_atual()

    def _marcar_modo_atual(self):
        modo = self.cores.get('modo', 'projeart')
        self._btn_projeart.setChecked(modo == 'projeart')
        self._btn_escuro.setChecked(modo == 'escuro')
        self._btn_claro.setChecked(modo == 'claro')

    def _restaurar_padrao(self):
        self.cores = dict(CORES_PADRAO)
        for chave in self._amostras:
            self._pintar_amostra(chave)
        self._marcar_modo_atual()


class CartaoKPI(QFrame):
    """Cartão de indicador no padrão Projeart: ícone, rótulo pequeno e valor grande."""

    def __init__(self, icone, rotulo, valor='—', parent=None):
        super().__init__(parent)
        self.setObjectName('cartaoKpi')
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 12, 14, 12)
        h.setSpacing(12)
        self.lbl_icone = QLabel(icone)
        self.lbl_icone.setObjectName('kpiIcone')
        self.lbl_icone.setAlignment(Qt.AlignCenter)
        self.lbl_icone.setFixedSize(46, 46)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.lbl_rotulo = QLabel(rotulo.upper())
        self.lbl_rotulo.setObjectName('kpiRotulo')
        self.lbl_valor = QLabel(str(valor))
        self.lbl_valor.setObjectName('kpiValor')
        col.addWidget(self.lbl_rotulo)
        col.addWidget(self.lbl_valor)
        h.addWidget(self.lbl_icone)
        h.addLayout(col, 1)

    def definir(self, valor, estado=None):
        """estado: None | 'ok' | 'aviso' | 'erro' — pinta o valor (verde/âmbar/vermelho)."""
        self.lbl_valor.setText(str(valor))
        cor = {'ok': NEON_GREEN, 'aviso': NEON_AMBER, 'erro': '#D64545'}.get(estado)
        self.lbl_valor.setStyleSheet(f'color:{cor};' if cor else '')


class FaixaKPI(QWidget):
    """Linha de cartões de KPI. itens: [(chave, ícone, rótulo)]."""

    def __init__(self, itens, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)
        self.cartoes = {}
        for chave, icone, rotulo in itens:
            c = CartaoKPI(icone, rotulo)
            self.cartoes[chave] = c
            h.addWidget(c, 1)

    def definir(self, chave, valor, estado=None):
        if chave in self.cartoes:
            self.cartoes[chave].definir(valor, estado)


class CaixaRecolhivel(QGroupBox):
    """QGroupBox com botão de minimizar/expandir no título — clica no
    título (ou no ▾/▸) e o conteúdo esconde/mostra. Começa expandida."""

    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self.setTitle('')
        # o tema global reserva "margin-top" pro título nativo do QGroupBox
        # (que aqui não é usado — o título é o botão ▾/▸ desenhado dentro),
        # senão a borda de cima passa por cima do botão.
        self.setStyleSheet('QGroupBox { margin-top: 0px; padding: 8px 10px 10px 10px; }')
        self._expandida = True

        layout_externo = QVBoxLayout(self)
        layout_externo.setContentsMargins(4, 2, 4, 4)
        layout_externo.setSpacing(4)

        self._btn_titulo = QPushButton(f'▾  {titulo}')
        self._btn_titulo.setObjectName('btnTituloCaixa')
        self._btn_titulo.setCheckable(True)
        self._btn_titulo.setChecked(True)
        self._btn_titulo.setStyleSheet(
            'text-align:left; border:none; background:transparent; '
            'font-weight:800; font-size:13px; padding:2px 4px;')
        self._btn_titulo.clicked.connect(self._alternar)
        layout_externo.addWidget(self._btn_titulo)

        self._conteudo = QWidget()
        self._conteudo.setObjectName('conteudoCaixa')
        layout_externo.addWidget(self._conteudo)
        self._titulo_base = titulo

    def _alternar(self):
        self._expandida = not self._expandida
        self._conteudo.setVisible(self._expandida)
        seta = '▾' if self._expandida else '▸'
        self._btn_titulo.setText(f'{seta}  {self._titulo_base}')

    def layout_conteudo(self):
        """Devolve o layout onde os widgets internos devem entrar."""
        if self._conteudo.layout() is None:
            QVBoxLayout(self._conteudo)
        return self._conteudo.layout()


class DropListWidget(QListWidget):
    """QListWidget que aceita arrastar arquivos do Windows Explorer direto
    pra dentro dela — chama on_drop(lista_de_caminhos) quando solta."""

    def __init__(self, on_drop, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._on_drop = on_drop

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            paths = [p for p in paths if os.path.isfile(p)]
            if paths:
                self._on_drop(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class DropArea(QLabel):
    """Área de soltar arquivo(s) — mostra um texto/dica, aceita clique (abre
    diálogo) e arrastar-e-soltar. Chama on_drop(lista_de_caminhos)."""

    def __init__(self, texto, on_drop, on_click=None, parent=None):
        super().__init__(texto, parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(56)
        self.setCursor(Qt.PointingHandCursor)
        self._aplicar_estilo()
        self._on_drop = on_drop
        self._on_click = on_click

    def _aplicar_estilo(self):
        t = tema_atual()
        self.setStyleSheet(
            f'QLabel {{ border: 2px dashed {t["border_forte"]}; border-radius: 8px; '
            f'color: {t["texto_fraco"]}; font-size:12px; padding:6px; }}'
            f'QLabel:hover {{ border-color: {NEON_CYAN}; color: {NEON_CYAN}; }}')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            paths = [p for p in paths if os.path.isfile(p)]
            if paths:
                self._on_drop(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def mousePressEvent(self, event):
        if self._on_click:
            self._on_click()
        super().mousePressEvent(event)


def _registrar_erro_no_log(titulo):
    """Grava no log do programa (se existir) o erro que está sendo tratado, com a pilha completa."""
    try:
        from nucleo.logging_config import registrar_erro_fatal
        registrar_erro_fatal(titulo, sys.exc_info())
    except Exception:
        pass


class Worker(QThread):
    sucesso = pyqtSignal(object)
    erro = pyqtSignal(str)
    progresso = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        # se a função aceita um parâmetro "progresso", injeta um callback
        # que emite pro sinal — assim qualquer função que já reporta fase
        # a fase (via avisa(msg)) aparece ao vivo no status, em vez de só
        # o spinner genérico parado na mesma frase o tempo todo
        try:
            aceita_progresso = 'progresso' in inspect.signature(fn).parameters
        except (TypeError, ValueError):
            aceita_progresso = False
        if aceita_progresso and 'progresso' not in self.kwargs:
            self.kwargs['progresso'] = lambda msg: self.progresso.emit(msg)

    def run(self):
        try:
            resultado = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            _registrar_erro_no_log('Erro numa tarefa em segundo plano (Validador)')
            self.erro.emit(str(e) or e.__class__.__name__)
            return
        self.sucesso.emit(resultado)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PPCP — Validador de Fluxos & Preenchedor de Base — Projeart')
        self.setWindowIcon(self._criar_icone_janela())
        _app_ref = QApplication.instance()
        if _app_ref:
            _app_ref.setWindowIcon(self.windowIcon())      # os diálogos também levam o ícone
        self.resize(1440, 900)
        self.setMinimumSize(900, 640)

        self.dbf_entries = []      # [{'path','nome','status','rows','msg'}]
        self.base_path = None
        self.base_is_xlsb = False
        self.base_fixa_path = None     # a Base fixa em uso (ver achar_base_fixa)
        self.fluxo_map = None
        self.fluxo_report_path = None
        self.foco_rows = None
        self.foco_report_path = None
        self.ska_report_path = None

        # ── Estado da aba Análise ──
        self.analise_dbf_paths = []
        self.analise_focco_path = None
        self.analise_det_data = []
        self.analise_grp_data = []
        self.analise_dbf_rows = []
        self.analise_of_trecho = ''

        # Layout no padrão Projeart: barra lateral azul-marinho com o logo e o menu,
        # topo branco com o título da página e, ao lado, o conteúdo. As abas
        # (self.tabs) continuam existindo — só a barra de abas fica escondida e o
        # menu lateral troca de página — então o resto do programa não muda.
        root_outer = QHBoxLayout(self)
        root_outer.setContentsMargins(0, 0, 0, 0)
        root_outer.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName('sidebar')
        self.sidebar.setFixedWidth(240)
        v_side = QVBoxLayout(self.sidebar)
        v_side.setContentsMargins(14, 22, 14, 12)
        v_side.setSpacing(3)
        self.lbl_logo = QLabel()
        _pm_logo = QPixmap()
        _pm_logo.loadFromData(base64.b64decode(LOGO_PROJEART_B64))
        self.lbl_logo.setPixmap(_pm_logo.scaledToWidth(180, Qt.SmoothTransformation))
        self.lbl_logo.setContentsMargins(6, 0, 0, 0)
        v_side.addWidget(self.lbl_logo)
        lbl_menu = QLabel('PPCP · FLUXOS')
        lbl_menu.setObjectName('sidebarSecao')
        v_side.addWidget(lbl_menu)
        self._nav_layout = QVBoxLayout()
        self._nav_layout.setSpacing(3)
        v_side.addLayout(self._nav_layout)
        v_side.addStretch()
        lbl_rodape = QLabel('© 2026 Projeart\nValidador de Fluxos · ' + str(VERSAO_SCRIPT).split(' ')[0])
        lbl_rodape.setObjectName('sidebarRodape')
        v_side.addWidget(lbl_rodape)
        self._lbl_sidebar_secao, self._lbl_sidebar_rodape = lbl_menu, lbl_rodape
        root_outer.addWidget(self.sidebar)

        coluna = QVBoxLayout()
        coluna.setContentsMargins(0, 0, 0, 0)
        coluna.setSpacing(0)

        self.topbar = QFrame()
        self.topbar.setObjectName('topbar')
        self.topbar.setFixedHeight(78)
        h_top = QHBoxLayout(self.topbar)
        h_top.setContentsMargins(26, 0, 22, 0)
        col_tit = QVBoxLayout()
        col_tit.setSpacing(1)
        col_tit.addStretch()
        self.lbl_pagina_titulo = QLabel('')
        self.lbl_pagina_titulo.setObjectName('paginaTitulo')
        self.lbl_pagina_sub = QLabel('')
        self.lbl_pagina_sub.setObjectName('paginaSub')
        col_tit.addWidget(self.lbl_pagina_titulo)
        col_tit.addWidget(self.lbl_pagina_sub)
        col_tit.addStretch()
        h_top.addLayout(col_tit)
        h_top.addStretch()
        _usuario = os.environ.get('USERNAME') or os.environ.get('USER') or ''
        if _usuario:
            chip = QLabel('👤  ' + _usuario)
            chip.setObjectName('chipUsuario')
            h_top.addWidget(chip)
            h_top.addSpacing(10)
        btn_cores = QPushButton('⚙ Cores')
        btn_cores.setToolTip('Ajustar as cores e o tema da tela')
        btn_cores.clicked.connect(self._abrir_config_cores)
        h_top.addWidget(btn_cores)
        coluna.addWidget(self.topbar)

        self.tabs = QTabWidget()
        # o Qt calcula a largura de cada aba com a fonte da própria barra,
        # ignorando o negrito do QSS — por isso o texto saía cortado.
        # Deixando a fonte igual à do estilo, a medida bate; e nunca corta.
        _f_abas = self.tabs.tabBar().font()
        _f_abas.setPixelSize(12)
        _f_abas.setBold(True)
        self.tabs.tabBar().setFont(_f_abas)
        self.tabs.tabBar().setElideMode(Qt.ElideNone)
        self.tabs.setElideMode(Qt.ElideNone)
        self.tabs.tabBar().hide()          # quem troca de página agora é o menu lateral
        self.tabs.setDocumentMode(True)
        area_conteudo = QWidget()
        v_area = QVBoxLayout(area_conteudo)
        v_area.setContentsMargins(22, 18, 22, 14)
        v_area.addWidget(self.tabs)
        coluna.addWidget(area_conteudo, 1)
        root_outer.addLayout(coluna, 1)

        tab_analise = QWidget()
        self._build_analise_tab(tab_analise)
        self.tabs.addTab(self._scroll(tab_analise), '⚖️ Análise DBF × FOCCO')

        tab_agrup = QWidget()
        root = QVBoxLayout(tab_agrup)
        root.setContentsMargins(4, 8, 4, 12)
        root.setSpacing(16)
        self.tabs.addTab(self._scroll(tab_agrup), '📦 Agrupador / Base')

        tab_impressao = QWidget()
        self._build_impressao_tab(tab_impressao)
        self.tabs.addTab(self._scroll(tab_impressao), '🖨️ Impressão Casada')

        tab_impressao_multi = QWidget()
        self._build_impressao_multi_tab(tab_impressao_multi)
        self.tabs.addTab(self._scroll(tab_impressao_multi), '🖨️📚 Impressão Casada — Multi-Obra')

        tab_lic = QWidget()
        self._build_grupo_lic_tab(tab_lic)
        self.tabs.addTab(self._scroll(tab_lic), '🏷️ Grupo LIC')

        tab_fluxo4 = QWidget()
        self._build_fluxo4_tab(tab_fluxo4)
        self.tabs.addTab(self._scroll(tab_fluxo4), '🔀 Fluxo 4')
        self._montar_navegacao()

        # ── Busca automática por número de obra (caixa própria, em destaque) ──
        gb_busca = QGroupBox('0) Busca automática por obra')
        vb = QVBoxLayout(gb_busca)
        vb.setSpacing(10)

        lbl_raiz = QLabel('Pasta(s) raiz das obras — uma por linha (tenta cada uma até achar)')
        lbl_raiz.setStyleSheet(f'font-size:12px; font-weight:700; color:{NEON_CYAN};')
        vb.addWidget(lbl_raiz)
        self.txt_raiz_obras = QPlainTextEdit()
        self.txt_raiz_obras.setPlaceholderText(
            r'ex: \\172.25.0.7\lib-eng' + '\n' + r'D:\LIBERAÇÕES ENGENHARIA' + '\n' + r'\\outro-servidor\outra-pasta')
        self.txt_raiz_obras.setMaximumHeight(80)
        self.txt_raiz_obras.setStyleSheet('font-size:13px; padding:6px 10px;')
        self.txt_raiz_obras.setReadOnly(True)
        vb.addWidget(self.txt_raiz_obras)
        self.lbl_raiz = QLabel('')
        vb.addWidget(self.lbl_raiz)
        h0a = QHBoxLayout()
        btn_raiz = QPushButton('📁 Adicionar pasta…')
        btn_raiz.setMinimumHeight(34)
        h0a.addWidget(btn_raiz)
        btn_testar = QPushButton('🔍 Testar esta(s) pasta(s)')
        btn_testar.setMinimumHeight(34)
        btn_testar.setToolTip('Mostra exatamente o que o app está enxergando na(s) pasta(s) raiz — '
                               'útil quando a busca não acha algo que devia estar lá')
        btn_testar.clicked.connect(self._testar_pasta_raiz)
        h0a.addWidget(btn_testar)
        h0a.addStretch()
        btn_raiz.clicked.connect(self._escolher_raiz_obras)
        vb.addLayout(h0a)

        lbl_obras = QLabel('Obra(s) — uma por linha')
        lbl_obras.setStyleSheet(f'font-size:12px; font-weight:700; color:{NEON_CYAN}; margin-top:4px;')
        vb.addWidget(lbl_obras)
        dica_obras = QLabel('Digite o código completo (ex: 2058-102-02) pra pegar só aquele trecho, '
                             'ou só o número da obra (ex: 2058) pra trazer todos os trechos dela de uma vez.')
        dica_obras.setWordWrap(True)
        dica_obras.setStyleSheet('font-size:11px; color:#8b95a5; background:transparent; border:none;')
        vb.addWidget(dica_obras)
        self.txt_obras = QPlainTextEdit()
        self.txt_obras.setPlaceholderText('2058-102-02\n2113-8-21\n2113-8-22\n2154-3-01')
        self.txt_obras.setMinimumHeight(130)
        self.txt_obras.setStyleSheet('font-size:14px; font-family:Consolas, monospace; padding:6px;')
        self.txt_obras.textChanged.connect(self._atualizar_contador_obras)
        vb.addWidget(self.txt_obras)

        h0c = QHBoxLayout()
        h0c.setSpacing(14)
        self.btn_buscar_obras = QPushButton('🔍 Buscar e Carregar')
        self.btn_buscar_obras.setObjectName('btnAnalisar')
        self.btn_buscar_obras.setMinimumHeight(42)
        self.btn_buscar_obras.setStyleSheet('font-size:14px; padding:10px 26px;')
        self.btn_buscar_obras.clicked.connect(self.buscar_dbfs_por_obra_click)
        h0c.addWidget(self.btn_buscar_obras)
        self.lbl_contador_obras = QLabel('nenhuma obra digitada')
        self.lbl_contador_obras.setStyleSheet('font-size:12px; color:#8b95a5; background:transparent; border:none;')
        h0c.addWidget(self.lbl_contador_obras)
        h0c.addStretch()
        vb.addLayout(h0c)

        self.chk_busca_completa = QCheckBox('Se não achar pelo atalho, varrer a pasta raiz inteira '
                                             '(mais lento — só ligue se souber que a obra existe)')
        self.chk_busca_completa.setChecked(False)
        vb.addWidget(self.chk_busca_completa)

        root.addWidget(gb_busca)

        # ── Bloco DBFs ──
        gb_dbf = QGroupBox('1) DBFs a agrupar — arraste os arquivos aqui ou use o botão (Excel, CSV/TXT, .xlsb, .dbf)')
        v1 = QVBoxLayout(gb_dbf)
        v1.setSpacing(10)

        h1 = QHBoxLayout()
        btn_add = QPushButton('➕ Adicionar arquivos…')
        btn_add.clicked.connect(self.adicionar_dbfs)
        btn_clear = QPushButton('Limpar lista')
        btn_clear.clicked.connect(self.limpar_dbfs)
        h1.addWidget(btn_add)
        h1.addWidget(btn_clear)
        h1.addStretch()
        v1.addLayout(h1)
        self.lst_dbf = DropListWidget(self._adicionar_dbf_paths)
        self.lst_dbf.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lst_dbf.setMaximumHeight(110)
        v1.addWidget(self.lst_dbf)
        root.addWidget(gb_dbf)

        # ── Bloco Base + Fluxo + Lote ──
        gb_base = QGroupBox('2) Planilha Base (.xlsx) + Relatório de Fluxos (leitura) + Lote')
        v2 = QVBoxLayout(gb_base)
        v2.setSpacing(10)

        h2 = QHBoxLayout()
        btn_base = QPushButton('📊 Usar outra Base (.xlsx)…')
        btn_base.setToolTip('Troca a Base só nesta sessão. Na próxima abertura volta sozinha a Base fixa '
                            '(a revisão mais nova da pasta "base_fixa").')
        btn_base.clicked.connect(self.carregar_base)
        self.lbl_base = QLineEdit()
        self.lbl_base.setPlaceholderText('nenhuma Base fixa encontrada (pasta "base_fixa") — carregue uma ou cole o caminho aqui')
        self.lbl_base.editingFinished.connect(self._caminho_digitado_base)
        h2.addWidget(btn_base)
        h2.addWidget(self.lbl_base, 1)
        btn_hist_base = QPushButton('🕘')
        btn_hist_base.setToolTip('Escolher entre as últimas bases usadas')
        btn_hist_base.setMaximumWidth(34)
        btn_hist_base.clicked.connect(self._mostrar_historico_base)
        h2.addWidget(btn_hist_base)
        btn_limpar_base = QPushButton('🔒 Base fixa')
        btn_limpar_base.setToolTip('Volta a usar a Base fixa (a revisão mais nova da pasta "base_fixa").')
        btn_limpar_base.clicked.connect(self._limpar_base)
        h2.addWidget(btn_limpar_base)
        v2.addLayout(h2)
        v2.addWidget(DropArea('⬇ arraste outra Base (.xlsx) aqui (só se não quiser a Base fixa)',
                              lambda paths: self._processar_base(paths[0])))

        h3 = QHBoxLayout()
        btn_fluxo = QPushButton('🔀 Carregar Relatório de Fluxos…')
        btn_fluxo.clicked.connect(self.carregar_relatorio_fluxo)
        self.lbl_fluxo = QLineEdit()
        self.lbl_fluxo.setPlaceholderText('nenhum relatório carregado — ou cole o caminho do arquivo aqui')
        self.lbl_fluxo.editingFinished.connect(self._caminho_digitado_fluxo)
        h3.addWidget(btn_fluxo)
        h3.addWidget(self.lbl_fluxo, 1)
        btn_hist_fluxo = QPushButton('🕘')
        btn_hist_fluxo.setToolTip('Escolher entre os últimos relatórios usados')
        btn_hist_fluxo.setMaximumWidth(34)
        btn_hist_fluxo.clicked.connect(self._mostrar_historico_fluxo)
        h3.addWidget(btn_hist_fluxo)
        btn_limpar_fluxo = QPushButton('🗑️ Limpar')
        btn_limpar_fluxo.clicked.connect(self._limpar_relatorio_fluxo)
        h3.addWidget(btn_limpar_fluxo)
        v2.addLayout(h3)
        v2.addWidget(DropArea('⬇ arraste o Relatório de Fluxos aqui', lambda paths: self._processar_relatorio_fluxo(paths[0])))

        h3b = QHBoxLayout()
        btn_foco = QPushButton('📥 Carregar Relatório FOCO (NDPCP301)…')
        btn_foco.clicked.connect(self.carregar_relatorio_foco)
        self.lbl_foco = QLineEdit()
        self.lbl_foco.setPlaceholderText('nenhum relatório carregado — ou cole o caminho do arquivo aqui')
        self.lbl_foco.editingFinished.connect(self._caminho_digitado_foco)
        h3b.addWidget(btn_foco)
        h3b.addWidget(self.lbl_foco, 1)
        btn_hist_foco = QPushButton('🕘')
        btn_hist_foco.setToolTip('Escolher entre os últimos relatórios FOCO usados')
        btn_hist_foco.setMaximumWidth(34)
        btn_hist_foco.clicked.connect(self._mostrar_historico_foco)
        h3b.addWidget(btn_hist_foco)
        btn_limpar_foco = QPushButton('🗑️ Limpar')
        btn_limpar_foco.clicked.connect(self._limpar_relatorio_foco)
        h3b.addWidget(btn_limpar_foco)
        v2.addLayout(h3b)
        v2.addWidget(DropArea('⬇ arraste o Relatório FOCO aqui', lambda paths: self._processar_relatorio_foco(paths[0])))

        h4 = QHBoxLayout()
        h4.addWidget(QLabel('Nome do Lote:'))
        self.txt_lote = QLineEdit()
        self.txt_lote.setPlaceholderText('ex: 676')
        self.txt_lote.setMaximumWidth(160)
        h4.addWidget(self.txt_lote)
        h4.addStretch()
        v2.addLayout(h4)

        root.addWidget(gb_base)

        # ── Bloco Lantek (SKA): planilha LANTEK_SKA fixa, atualizada sozinha ao gerar a base ──
        gb_ska = QGroupBox('3) Programação no Lantek — planilha LANTEK_SKA (atualizada sozinha ao gerar a base)')
        v3 = QVBoxLayout(gb_ska)
        v3.setSpacing(8)
        h6 = QHBoxLayout()
        btn_ska = QPushButton('📥 Relatório SKA (CSV)…')
        btn_ska.setToolTip('SKA Reports > RELATÓRIO ANÁLISE DE NESTINGS > Exportar CSV (separador decimal vírgula). '
                           'Ele alimenta a planilha LANTEK_SKA que as bases consultam (coluna MÁQUINA_LANTEK).')
        btn_ska.clicked.connect(self.carregar_relatorio_ska)
        self.lbl_ska = QLineEdit()
        self.lbl_ska.setPlaceholderText('nenhum relatório SKA — baixe o CSV no SKA Reports e carregue aqui (ou cole o caminho)')
        self.lbl_ska.editingFinished.connect(self._caminho_digitado_ska)
        h6.addWidget(btn_ska)
        h6.addWidget(self.lbl_ska, 1)
        btn_hist_ska = QPushButton('🕘')
        btn_hist_ska.setToolTip('Escolher entre os últimos relatórios SKA usados')
        btn_hist_ska.setMaximumWidth(34)
        btn_hist_ska.clicked.connect(self._mostrar_historico_ska)
        h6.addWidget(btn_hist_ska)
        btn_limpar_ska = QPushButton('🗑️ Limpar')
        btn_limpar_ska.clicked.connect(self._limpar_relatorio_ska)
        h6.addWidget(btn_limpar_ska)
        v3.addLayout(h6)
        v3.addWidget(DropArea('⬇ arraste o relatório SKA (CSV) aqui', lambda paths: self._processar_relatorio_ska(paths[0])))
        lbl_destino_ska = QLabel('🔒 Planilha que é atualizada (fixa): ' + (ska_lantek.caminho_destino() if ska_lantek else '—'))
        lbl_destino_ska.setWordWrap(True)
        lbl_destino_ska.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v3.addWidget(lbl_destino_ska)
        h7 = QHBoxLayout()
        self.chk_ska = QCheckBox('Atualizar a planilha LANTEK_SKA automaticamente ao gerar a base')
        self.chk_ska.setChecked(True)
        self.chk_ska.setToolTip('Antes de gerar a base, o Excel (em segundo plano) troca os dados da planilha LANTEK_SKA pelo '
                                'relatório SKA carregado, mantendo as fórmulas, e guarda uma cópia em "00. Back up" '
                                '(uma por dia). As bases enxergam o dado novo porque apontam para esse mesmo arquivo.')
        h7.addWidget(self.chk_ska)
        h7.addStretch()
        self.btn_ska_agora = QPushButton('🔄 Atualizar a planilha LANTEK_SKA agora')
        self.btn_ska_agora.clicked.connect(self.atualizar_ska_agora)
        h7.addWidget(self.btn_ska_agora)
        v3.addLayout(h7)
        root.addWidget(gb_ska)

        # ── Botões de ação ──
        h5 = QHBoxLayout()
        self.btn_vis = QPushButton('👁 Visualizar Consolidado')
        self.btn_vis.clicked.connect(self.visualizar_consolidado)
        self.btn_gerar = QPushButton('⬇️ Gerar Base Preenchida (.xlsx)')
        self.btn_gerar.clicked.connect(self.gerar_base)
        self.btn_gerar.setObjectName('btnPrincipal')
        h5.addWidget(self.btn_vis)
        h5.addWidget(self.btn_gerar)
        h5.addStretch()
        root.addLayout(h5)

        self.lbl_status = QLabel('')
        root.addWidget(self.lbl_status)

        # ── Preview ──
        self.tbl = QTableWidget()
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setMinimumHeight(320)
        root.addWidget(self.tbl, 1)

        # ── Restaura só a pasta raiz das obras (texto, sem risco de
        # informação desatualizada). O Relatório de Fluxos NÃO carrega sozinho — fica no botão de histórico
        # (🕘) ao lado, pra escolher manualmente, nunca carregando relatório antigo sem avisar. A BASE é
        # a exceção: é FIXA (revisão mais nova da pasta base_fixa, ver achar_base_fixa) e carrega sozinha ──
        # Pastas raiz das obras: FIXAS no sistema (RAIZES_FIXAS) — o acesso é conferido em _verificar_raizes
        self.raizes_ok = []
        self.txt_raiz_obras.setPlainText('\n'.join(r['caminho'] for r in RAIZES_FIXAS))

        # Base fixa: carrega sozinha ao abrir (depois da janela montada)
        QTimer.singleShot(0, self._carregar_base_fixa)

    # (ícone, nome no menu, título da página, subtítulo) — na mesma ordem das abas
    _NAV = [
        ('⚖️', 'Análise DBF × FOCCO', 'Análise DBF × FOCCO', 'Compara o peso dos DBFs do trecho com o export do FOCCO'),
        ('📦', 'Agrupador / Base', 'Agrupador / Base', 'Agrupa os DBFs das obras e preenche a base de programação'),
        ('🖨️', 'Impressão Casada', 'Impressão Casada', 'Casa CNC e Ordens na sequência de impressão, por espessura'),
        ('📚', 'Multi-Obra', 'Impressão Casada — Multi-Obra', 'Várias obras no mesmo lote, organizado por Obra → Fluxo'),
        ('🏷️', 'Grupo LIC', 'Grupo LIC', 'Separa as ordens do pacote por Grupo LIC, tipo e espessura'),
        ('🔀', 'Fluxo 4', 'Fluxo 4', 'Casa as ordens do fluxo escolhido pela roteirização, por espessura'),
    ]

    def _criar_icone_janela(self):
        """Ícone da janela no padrão Projeart: quadrado azul-marinho com o "P" do selo."""
        tam = 128
        base = QPixmap(tam, tam)
        base.fill(Qt.transparent)
        pn = QPainter(base)
        pn.setRenderHint(QPainter.Antialiasing)
        pn.setRenderHint(QPainter.SmoothPixmapTransform)
        pn.setBrush(QColor('#0B1D3A'))
        pn.setPen(Qt.NoPen)
        pn.drawRoundedRect(0, 0, tam, tam, 26, 26)
        logo = QPixmap()
        try:
            logo.loadFromData(base64.b64decode(LOGO_PROJEART_B64))
        except Exception:
            pass
        if not logo.isNull():
            letra = logo.copy(0, 0, min(66, logo.width()), logo.height())      # só o "P" do selo
            letra = letra.scaled(int(tam * 0.66), int(tam * 0.66), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pn.drawPixmap((tam - letra.width()) // 2, (tam - letra.height()) // 2, letra)
        else:
            pn.setPen(QColor('#FFFFFF'))
            fonte = pn.font()
            fonte.setPixelSize(80)
            fonte.setBold(True)
            pn.setFont(fonte)
            pn.drawText(base.rect(), Qt.AlignCenter, 'P')
        pn.end()
        return QIcon(base)

    def showEvent(self, e):
        super().showEvent(e)
        # barra de título azul-marinho (Windows 11): só aparência; se o sistema
        # não suportar, nada acontece
        if sys.platform == 'win32' and not getattr(self, '_barra_titulo_ok', False) and CORES_ATUAIS.get('modo') == 'projeart':
            self._barra_titulo_ok = True
            try:
                import ctypes
                hwnd = int(self.winId())
                for atributo, cor in ((35, 0x003A1D0B), (36, 0x00FFFFFF), (34, 0x003A1D0B)):   # fundo, texto, borda (BGR)
                    valor = ctypes.c_int(cor)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(valor), ctypes.sizeof(valor))
            except Exception:
                pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ajustar_menu_compacto()

    def _ajustar_menu_compacto(self):
        """Janela estreita (< 1100 px): o menu lateral recolhe e fica só com os ícones."""
        if not getattr(self, '_nav_botoes', None):
            return
        compacto = self.width() < 1100
        if compacto == getattr(self, '_menu_compacto', None):
            return
        self._menu_compacto = compacto
        self.sidebar.setFixedWidth(76 if compacto else 240)
        for w in (self.lbl_logo, self._lbl_sidebar_secao, self._lbl_sidebar_rodape):
            w.setVisible(not compacto)
        for b, item in zip(self._nav_botoes, self._NAV):
            b.setText(item[0] if compacto else f'{item[0]}   {item[1]}')
            b.setToolTip(item[1] if compacto else '')
            b.setStyleSheet('text-align: center; padding-left: 0px; padding-right: 0px;' if compacto else '')

    def _montar_navegacao(self):
        """Cria os botões do menu lateral (um por aba) e liga com o troca-de-página."""
        self._nav_botoes = []
        self._grupo_nav = QButtonGroup(self)
        self._grupo_nav.setExclusive(True)
        for i in range(min(len(self._NAV), self.tabs.count())):
            icone, rotulo = self._NAV[i][0], self._NAV[i][1]
            b = QPushButton(f'{icone}   {rotulo}')
            b.setObjectName('navItem')
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(42)
            b.clicked.connect(lambda _=False, k=i: self.tabs.setCurrentIndex(k))
            self._grupo_nav.addButton(b)
            self._nav_layout.addWidget(b)
            self._nav_botoes.append(b)
        self.tabs.currentChanged.connect(self._ao_mudar_aba)
        self._ao_mudar_aba(self.tabs.currentIndex())

    def _ao_mudar_aba(self, i):
        if 0 <= i < len(self._nav_botoes):
            self._nav_botoes[i].setChecked(True)
        if 0 <= i < len(self._NAV):
            self.lbl_pagina_titulo.setText(self._NAV[i][2])
            self.lbl_pagina_sub.setText(self._NAV[i][3])

    def _scroll(self, widget):
        """Envolve o conteudo de uma aba em rolagem — garante que a tabela
        de baixo sempre fica alcancavel, mesmo com a janela pequena."""
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setWidget(widget)
        return area

    def _abrir_config_cores(self):
        dialogo = DialogoCores(CORES_ATUAIS, self)
        if dialogo.exec_() == QDialog.Accepted:
            self._aplicar_cores(dialogo.cores)

    def _aplicar_cores(self, cores):
        global CORES_ATUAIS, NEON_CYAN, NEON_MAGENTA, NEON_GREEN, NEON_AMBER, STYLE_SHEET
        CORES_ATUAIS = dict(cores)
        NEON_CYAN = CORES_ATUAIS['cyan']
        NEON_MAGENTA = CORES_ATUAIS['magenta']
        NEON_GREEN = CORES_ATUAIS['green']
        NEON_AMBER = CORES_ATUAIS['amber']
        STYLE_SHEET = construir_folha_estilo(CORES_ATUAIS)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(STYLE_SHEET)
        # widgets com cor pintada direto no Python (fora do QSS global)
        # precisam ser atualizados na mão
        for area in self.findChildren(DropArea):
            area._aplicar_estilo()
        salvar_cores(CORES_ATUAIS)

    # ── Aba Análise DBF × FOCCO ──
    def _build_analise_tab(self, tab):
        v = QVBoxLayout(tab)

        gb1 = QGroupBox('1) DBF(s) do trecho')
        v1 = QVBoxLayout(gb1)
        h1 = QHBoxLayout()
        btn_add = QPushButton('➕ Adicionar DBF(s)…')
        btn_add.clicked.connect(self.an_adicionar_dbfs)
        btn_clear = QPushButton('Limpar')
        btn_clear.clicked.connect(self.an_limpar_dbfs)
        h1.addWidget(btn_add)
        h1.addWidget(btn_clear)
        h1.addStretch()
        v1.addLayout(h1)
        self.an_lst_dbf = DropListWidget(self._an_adicionar_dbf_paths)
        self.an_lst_dbf.setMaximumHeight(90)
        v1.addWidget(self.an_lst_dbf)
        v1.addWidget(DropArea('⬇ arraste DBF(s) aqui', self._an_adicionar_dbf_paths))
        v.addWidget(gb1)

        gb2 = QGroupBox('2) Export do FOCCO (Excel ou HTML)')
        v2 = QVBoxLayout(gb2)
        h2 = QHBoxLayout()
        btn_focco = QPushButton('📥 Carregar export do FOCCO…')
        btn_focco.clicked.connect(self.an_carregar_focco)
        self.an_lbl_focco = QLabel('nenhum arquivo carregado')
        h2.addWidget(btn_focco)
        h2.addWidget(self.an_lbl_focco, 1)
        v2.addLayout(h2)
        v2.addWidget(DropArea('⬇ arraste o export do FOCCO aqui', lambda paths: self._an_definir_focco(paths[0])))
        v.addWidget(gb2)

        h3 = QHBoxLayout()
        self.an_btn_analisar = QPushButton('⚖️ Analisar')
        self.an_btn_analisar.setObjectName('btnAnalisar')
        self.an_btn_analisar.clicked.connect(self.an_analisar)
        h3.addWidget(self.an_btn_analisar)
        h3.addWidget(QLabel('Nome do arquivo de saída:'))
        self.an_txt_nome = QLineEdit()
        self.an_txt_nome.setPlaceholderText('ex: Validação-Peso-LIC x Posição_OF-2001-7-70')
        h3.addWidget(self.an_txt_nome, 1)
        self.an_btn_exportar = QPushButton('⬇ Exportar Excel')
        self.an_btn_exportar.setObjectName('btnPrincipal')
        self.an_btn_exportar.clicked.connect(self.an_exportar)
        self.an_btn_exportar.setEnabled(False)
        h3.addWidget(self.an_btn_exportar)
        v.addLayout(h3)

        self.an_lbl_resumo = QLabel('')
        v.addWidget(self.an_lbl_resumo)

        v.addWidget(QLabel('Por Grupo LIC:'))
        self.an_tbl_grupo = QTableWidget()
        self.an_tbl_grupo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.an_tbl_grupo.setAlternatingRowColors(True)
        self.an_tbl_grupo.setMaximumHeight(220)
        v.addWidget(self.an_tbl_grupo)

        v.addWidget(QLabel('Por Marca — detalhe:'))
        self.an_tbl_detalhe = QTableWidget()
        self.an_tbl_detalhe.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.an_tbl_detalhe.setAlternatingRowColors(True)
        self.an_tbl_detalhe.setMinimumHeight(300)
        v.addWidget(self.an_tbl_detalhe, 1)

    # ── Aba Impressão Casada (CNC + Ordens) ──
    def _build_impressao_tab(self, tab):
        v = QVBoxLayout(tab)

        gb_cnc = QGroupBox('1) PDF(s) dos CNCs (nesting)')
        v1 = QVBoxLayout(gb_cnc)
        h1 = QHBoxLayout()
        btn_add_cnc = QPushButton('➕ Adicionar PDF(s) de CNC…')
        btn_add_cnc.clicked.connect(self._imp_adicionar_cnc)
        btn_clear_cnc = QPushButton('Limpar')
        btn_clear_cnc.clicked.connect(self._imp_limpar_cnc)
        h1.addWidget(btn_add_cnc)
        h1.addWidget(btn_clear_cnc)
        h1.addStretch()
        v1.addLayout(h1)
        self.imp_lst_cnc = DropListWidget(self._imp_adicionar_cnc_paths)
        self.imp_lst_cnc.setMaximumHeight(110)
        v1.addWidget(self.imp_lst_cnc)
        v1.addWidget(DropArea('⬇ arraste PDF(s) de CNC aqui', self._imp_adicionar_cnc_paths))
        v.addWidget(gb_cnc)

        gb_ord = QGroupBox('2) PDF das Ordens de Fabricação')
        v2 = QVBoxLayout(gb_ord)
        h2 = QHBoxLayout()
        btn_ord = QPushButton('📄 Escolher PDF das Ordens…')
        btn_ord.clicked.connect(self._imp_escolher_ordens)
        self.imp_lbl_ordens = QLabel('nenhum arquivo carregado')
        h2.addWidget(btn_ord)
        h2.addWidget(self.imp_lbl_ordens, 1)
        v2.addLayout(h2)
        area_ord = DropArea('⬇ arraste o PDF das Ordens aqui', lambda paths: self._imp_definir_ordens(paths[0]))
        v2.addWidget(area_ord)
        v.addWidget(gb_ord)

        gb_lantek = CaixaRecolhivel('3) Relatório do Lantek (opcional) — segurança extra contra peça sem programação')
        v2b = gb_lantek.layout_conteudo()
        h2b = QHBoxLayout()
        btn_lantek = QPushButton('📥 Escolher Relatório do Lantek…')
        btn_lantek.clicked.connect(self._imp_escolher_lantek)
        self.imp_lbl_lantek = QLabel('nenhum relatório carregado — sem ele, a conferência de "programado ou não" fica desligada')
        self.imp_lbl_lantek.setWordWrap(True)
        h2b.addWidget(btn_lantek)
        h2b.addWidget(self.imp_lbl_lantek, 1)
        v2b.addLayout(h2b)
        area_lantek = DropArea('⬇ arraste o Relatório do Lantek (.csv) aqui',
                                lambda paths: self._imp_definir_lantek(paths[0]))
        v2b.addWidget(area_lantek)
        v.addWidget(gb_lantek)

        gb_opc = CaixaRecolhivel('4) Opções de impressão')
        v3 = gb_opc.layout_conteudo()
        self.imp_chk_duplex = self._imp_checkbox(v3, 'Frente e verso', True,
            'insere página em branco para fechar bloco ímpar')
        self.imp_chk_folha_cnc = self._imp_checkbox(v3, 'Folha dedicada por CNC', True,
            'LIGADO: cada página de CNC sozinha na folha, verso em branco. DESLIGADO: as páginas do mesmo '
            'CNC ficam juntas (a 2ª folha no verso da principal) e o próximo CNC começa em folha nova', )
        self.imp_chk_a4 = self._imp_checkbox(v3, 'Padronizar tudo em A4', True,
            'recorta a margem vazia e aproveita a folha inteira')
        self.imp_chk_qtd_completa = self._imp_checkbox(v3, 'Só com quantidade completa', True,
            'não imprime a ordem se faltar peça nos CNCs carregados')
        self.imp_chk_unir_partes = self._imp_checkbox(v3, "Unir peça dividida [A]/[B]", True,
            'as duas metades saem em sequência, com a ordem uma vez só')
        v.addWidget(gb_opc)

        h4 = QHBoxLayout()
        self.imp_btn_conferir = QPushButton('🔍 Conferir antes')
        self.imp_btn_conferir.clicked.connect(self._imp_conferir)
        h4.addWidget(self.imp_btn_conferir)
        self.imp_btn_gerar = QPushButton('🖨️ Gerar PDF na Sequência de Impressão')
        self.imp_btn_gerar.setObjectName('btnAnalisar')
        self.imp_btn_gerar.clicked.connect(lambda: self._imp_gerar())
        h4.addWidget(self.imp_btn_gerar)
        v.addLayout(h4)

        self.imp_kpis = FaixaKPI([('conjuntos', '📦', 'Conjuntos'), ('ordens', '📋', 'Ordens que casam'),
                                   ('cncs', '🧩', 'CNCs'), ('pendentes', '⏳', 'Pendentes'),
                                   ('paginas', '📄', 'Páginas do PDF')])
        v.addWidget(self.imp_kpis)
        self.imp_lbl_status = QLabel('Aguardando arquivos...')
        v.addWidget(self.imp_lbl_status)

        self.imp_tree_resultado = QTreeWidget()
        self.imp_tree_resultado.setHeaderLabels(['Item', 'Detalhe'])
        self.imp_tree_resultado.setMinimumHeight(320)
        self.imp_tree_resultado.setAlternatingRowColors(True)
        self.imp_tree_resultado.header().setStretchLastSection(True)
        v.addWidget(self.imp_tree_resultado, 1)

        # conferência por CNC: lista de CNCs à esquerda; ao clicar em um, à
        # direita aparecem as posições dele e — depois de gerar o PDF — como
        # cada uma ficou unida à ordem DENTRO do PDF gerado (comparação)
        gb_conf = QGroupBox('Conferência por CNC')
        gb_conf.setToolTip('Esquerda: cada CNC com as posições dele (peças, PARCIAL/COMPLETA). '
                           'Direita: em quais CNCs cada posição está e como ficou no PDF gerado.')
        vc = QVBoxLayout(gb_conf)
        self.imp_lbl_conf = QLabel('Clique em "Conferir antes" pra listar os CNCs. Depois de gerar o PDF, cada '
                                    'posição é conferida DENTRO do PDF gerado.')
        self.imp_lbl_conf.setWordWrap(True)
        vc.addWidget(self.imp_lbl_conf)
        linha_pdf = QHBoxLayout()
        self.imp_btn_comparar_pdf = QPushButton('📑 Comparar com um PDF já gerado…')
        self.imp_btn_comparar_pdf.setToolTip('Lê um PDF de Impressão Casada que você já gerou (ex.: de outro dia) e '
                                              'confere se cada posição dos CNCs carregados ficou unida à ordem')
        self.imp_btn_comparar_pdf.clicked.connect(self._imp_comparar_pdf_existente)
        linha_pdf.addWidget(self.imp_btn_comparar_pdf)
        self.imp_lbl_pdf_comparado = QLabel('PDF comparado: nenhum ainda')
        linha_pdf.addWidget(self.imp_lbl_pdf_comparado, 1)
        vc.addLayout(linha_pdf)
        split_conf = QSplitter(Qt.Horizontal)

        esq = QWidget()
        ve = QVBoxLayout(esq)
        ve.setContentsMargins(0, 0, 0, 0)
        self.imp_busca_cnc = QLineEdit()
        self.imp_busca_cnc.setPlaceholderText('🔎 buscar CNC, posição ou OF…')
        self.imp_busca_cnc.setClearButtonEnabled(True)
        self.imp_busca_cnc.textChanged.connect(self._imp_filtrar_cncs)
        ve.addWidget(self.imp_busca_cnc)
        self.imp_lista_cncs = QTreeWidget()
        self.imp_lista_cncs.setHeaderLabels(['CNC  /  posições dele', 'Ordem (OF)', 'Peças neste CNC · situação', 'PDF'])
        self.imp_lista_cncs.setRootIsDecorated(True)
        self.imp_lista_cncs.setAlternatingRowColors(True)
        self.imp_lista_cncs.setMinimumHeight(420)
        self.imp_lista_cncs.currentItemChanged.connect(self._imp_mostrar_cnc)
        ve.addWidget(self.imp_lista_cncs)

        dir_ = QWidget()
        vd = QVBoxLayout(dir_)
        vd.setContentsMargins(0, 0, 0, 0)
        self.imp_lbl_detalhe_cnc = QLabel('← clique num CNC (ou numa posição) da lista')
        self.imp_lbl_detalhe_cnc.setWordWrap(True)
        vd.addWidget(self.imp_lbl_detalhe_cnc)
        self.imp_tree_detalhe_cnc = QTreeWidget()
        self.imp_tree_detalhe_cnc.setHeaderLabels(['Posição (do CNC)', 'Ordem (OF)', 'Casamento', 'No PDF gerado', 'Onde no PDF'])
        self.imp_tree_detalhe_cnc.setRootIsDecorated(True)
        self.imp_tree_detalhe_cnc.setAlternatingRowColors(True)
        self.imp_tree_detalhe_cnc.setMinimumHeight(420)
        vd.addWidget(self.imp_tree_detalhe_cnc)

        split_conf.addWidget(esq)
        split_conf.addWidget(dir_)
        split_conf.setSizes([590, 810])
        vc.addWidget(split_conf)
        v.addWidget(gb_conf, 1)

        self.imp_caminho_saida = None

    def _imp_checkbox(self, layout, texto, marcado, dica):
        from PyQt5.QtWidgets import QCheckBox
        chk = QCheckBox(texto)
        chk.setChecked(marcado)
        chk.setToolTip(dica)
        layout.addWidget(chk)
        return chk

    def _imp_adicionar_cnc(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Selecionar PDF(s) de CNC', '', 'PDF (*.pdf)')
        self._imp_adicionar_cnc_paths(paths)

    def _imp_adicionar_cnc_paths(self, paths):
        atuais = [self.imp_lst_cnc.item(i).text() for i in range(self.imp_lst_cnc.count())]
        self.imp_caminhos_cnc = getattr(self, 'imp_caminhos_cnc', [])
        for p in paths:
            if p not in self.imp_caminhos_cnc:
                self.imp_caminhos_cnc.append(p)
        self.imp_lst_cnc.clear()
        self.imp_lst_cnc.addItems([os.path.basename(p) for p in self.imp_caminhos_cnc])

    def _imp_limpar_cnc(self):
        self.imp_caminhos_cnc = []
        self.imp_lst_cnc.clear()

    def _imp_escolher_ordens(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar PDF das Ordens', '', 'PDF (*.pdf)')
        if not path:
            return
        self._imp_definir_ordens(path)

    def _imp_definir_ordens(self, path):
        self.imp_caminho_ordens = path
        self.imp_lbl_ordens.setText(os.path.basename(path))

    def _imp_escolher_lantek(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar Relatório do Lantek', '',
                                               'CSV/Excel (*.csv *.xlsx *.xlsm *.xls);;Todos (*)')
        if not path:
            return
        self._imp_definir_lantek(path)

    def _imp_definir_lantek(self, path):
        self.imp_caminho_lantek = path
        self.imp_lbl_lantek.setText(f'✓ {os.path.basename(path)}')

    def _imp_conferir(self):
        caminhos_cnc = getattr(self, 'imp_caminhos_cnc', [])
        caminho_ordens = getattr(self, 'imp_caminho_ordens', None)
        if not caminhos_cnc or not caminho_ordens:
            QMessageBox.warning(self, 'Aviso', 'Selecione o(s) PDF(s) dos CNCs e o PDF das Ordens antes de conferir.')
            return
        self._iniciar_trabalho_em_fundo(
            analisar_impressao_casada,
            (caminhos_cnc, caminho_ordens),
            {'unir_partes': self.imp_chk_unir_partes.isChecked(),
             'exigir_completa': self.imp_chk_qtd_completa.isChecked(),
             'caminho_lantek': getattr(self, 'imp_caminho_lantek', None)},
            botoes_desabilitar=[self.imp_btn_conferir, self.imp_btn_gerar],
            label_status=self.imp_lbl_status,
            msg_rodando='Lendo PDFs e conferindo o casamento (sem gerar PDF ainda)…',
            on_sucesso=lambda r: self._imp_conferido(r),
        )

    def _imp_conferido(self, r):
        msg = (f"🔍 Conferência: {r['grupos']} conjunto(s) · {r['ordens_usadas']} de {r['total_ordens_no_pdf']} "
               f"ordem(ns) vão casar · {len(r['descartadas'])} vão ficar de fora — "
               f"revise antes de gerar o PDF de verdade")
        if r.get('ordens_sem_programacao'):
            msg += f" · 🚨 {len(r['ordens_sem_programacao'])} SEM PROGRAMAÇÃO no Lantek"
        if r.get('ordens_programadas_sem_cnc'):
            msg += f" · 🟡 {len(r['ordens_programadas_sem_cnc'])} programada(s) mas sem CNC aqui"
        msg += self._imp_texto_pendentes(r)
        self.imp_lbl_status.setText(msg)
        self._preencher_kpis(self.imp_kpis, r, gerado=False)
        self._popular_arvore_impressao(self.imp_tree_resultado, r)
        self.imp_tree_resultado.expandToDepth(0)
        self._imp_popular_conferencia(r.get('conferencia'))

    @staticmethod
    def _preencher_kpis(faixa, r, gerado=False):
        """Atualiza os cartões de KPI com o resultado do Conferir antes / da geração."""
        pend = len(r.get('conjuntos_pendentes') or [])
        faixa.definir('conjuntos', r.get('grupos', '—'))
        total = r.get('total_ordens_no_pdf')
        faixa.definir('ordens', f"{r.get('ordens_usadas', 0)} de {total}" if total else r.get('ordens_usadas', '—'))
        faixa.definir('cncs', r.get('total_cncs', len((r.get('conferencia') or {}).get('cnc_posicoes', [])) or '—'))
        faixa.definir('obras', len(r.get('obras') or []) or len({g.get('obra') or '—' for g in r.get('relatorio', [])}) or '—')
        faixa.definir('pendentes', pend, 'aviso' if pend else 'ok')
        if gerado:
            div = (r.get('verificacao') or {}).get('divergencias')
            faixa.definir('paginas', r.get('total_paginas', '—'), 'erro' if div else 'ok')
        else:
            faixa.definir('paginas', '—')

    @staticmethod
    def _imp_texto_pendentes(r):
        """Resumo curto dos conjuntos que ficaram esperando peça (não impressos)."""
        pend = r.get('conjuntos_pendentes') or []
        if not pend:
            return ''
        faltas = [f"{i['pos']} ({i['cortado']} de {i['necessario']})" for g in pend for i in g['incompletas']]
        return (f" · ⏳ {len(pend)} conjunto(s) PENDENTE(S) · {r.get('ordens_pendentes', 0)} ordem(ns) seguradas — "
                f"aguardando peça: {', '.join(faltas[:6])}{' …' if len(faltas) > 6 else ''} (NÃO impressos)")

    @staticmethod
    def _imp_texto_texto_perdido(r):
        """Aviso quando alguma página copiada não manteve todo o texto do PDF de origem (ex.: numeração das peças)."""
        perdas = r.get('texto_perdido') or []
        if not perdas:
            return ''
        onde = ', '.join(f"{p['origem']} pág. {p['pagina']}" for p in perdas[:4])
        return (f" · ⚠️ {len(perdas)} página(s) com texto que NÃO saiu na cópia (numeração das peças?) — "
                f"conferir: {onde}{' …' if len(perdas) > 4 else ''}")

    def _imp_mostrar_nada_a_imprimir(self, tree, lbl, r, com_conferencia=True):
        """Todos os conjuntos estão pendentes: não existe conjunto completo pra
        imprimir, então nenhum PDF é gravado. Mostra o que falta."""
        AMAR = QColor(NEON_AMBER)
        tree.clear()
        msg = '⏳ Nada a imprimir: todos os conjuntos estão aguardando peça(s) que faltam' + self._imp_texto_pendentes(r)
        lbl.setText(msg)
        faixa = self.impm_kpis if tree is self.impm_tree_resultado else self.imp_kpis
        faixa.definir('conjuntos', 0)
        faixa.definir('ordens', 0)
        faixa.definir('pendentes', len(r.get('conjuntos_pendentes') or []), 'aviso')
        faixa.definir('paginas', 0)
        raiz = QTreeWidgetItem(tree, ['⏳ Conjuntos PENDENTES — aguardando completar', f"{len(r.get('conjuntos_pendentes') or [])}"])
        raiz.setForeground(0, AMAR)
        for g in r.get('conjuntos_pendentes') or []:
            ig = QTreeWidgetItem(raiz, [f"CNC(s) {', '.join(g['cncs'])}", rotulo_espessura(g['espessura'])])
            for i in g['incompletas']:
                QTreeWidgetItem(ig, [f"⚠ posição {i['pos']}",
                                      f"tem {i['cortado']} de {i['necessario']} — faltam {i['necessario'] - i['cortado']} · CNC(s): {i['cncs']}"])
            for o in g['ordens']:
                QTreeWidgetItem(ig, [f"📋 Ordem {o} (segurada)", ''])
        tree.expandToDepth(1)
        if com_conferencia and r.get('conferencia'):
            self._imp_popular_conferencia(r['conferencia'], None)
        QMessageBox.warning(self, 'Nada a imprimir', msg + '\n\nQuando o CNC com a peça que falta for carregado, o conjunto '
                                                          'fica completo e sai sozinho na impressão.')

    @staticmethod
    def _imp_juntar(itens, prefixo=''):
        """['a','b','c'] -> "CNC a, b e c"."""
        itens = [str(x) for x in itens]
        if not itens:
            return ''
        corpo = itens[0] if len(itens) == 1 else ', '.join(itens[:-1]) + ' e ' + itens[-1]
        return (prefixo + corpo) if prefixo else corpo

    def _imp_linha_pdf(self, cnc, pos):
        """Linha da verificação do PDF gerado para (CNC, posição), ou None."""
        ver = getattr(self, '_imp_verificacao', None)
        x = ver['por_cnc'].get(cnc) if ver else None
        if not x:
            return None
        for l in x['linhas']:
            if l['pos'] == pos:
                return l
        return None

    def _imp_resumo_posicao(self, pos, ordem):
        """Como a posição ficou no PDF gerado, olhando TODOS os CNCs em que ela aparece.
        Devolve (texto, cor) — cor: 'ok' | 'ruim' | 'neutro'."""
        cncs = self._imp_pos_cncs.get(pos, [])
        if not ordem:
            return 'sem ordem (não casou)', 'neutro'
        if any(c in getattr(self, '_imp_pendentes', set()) for c in cncs):
            return '⏳ conjunto PENDENTE — aguardando completar (não impresso)', 'neutro'
        if getattr(self, '_imp_verificacao', None) is None:
            if len(cncs) > 1:
                return f'previsto: unir com {self._imp_juntar(cncs, "os CNCs ")} (gere o PDF p/ confirmar)', 'neutro'
            return 'gere o PDF para confirmar', 'neutro'
        unidas = [c for c in cncs if (self._imp_linha_pdf(c, pos) or {}).get('estado') == 'unida']
        nao = [c for c in cncs if c not in unidas]
        if len(cncs) <= 1:
            l = self._imp_linha_pdf(cncs[0], pos) if cncs else None
            if l and l['estado'] == 'unida':
                return f"✓ unida · OF pág. {l['onde'].split('OF pág. ')[-1]}", 'ok'
            c0 = cncs[0] if cncs else '?'
            est = (l or {}).get('estado')
            onde = ((l or {}).get('onde') or '').replace('OF pág. ', '')
            if est == 'outro_bloco':
                return f"✗ NÃO unida com o CNC {c0} — OF em outro bloco (pág. {onde})", 'ruim'
            if est == 'ausente':
                return f"✗ NÃO unida com o CNC {c0} — a OF não está no PDF", 'ruim'
            if est == 'cnc_ausente':
                return f"✗ o CNC {c0} não está no PDF", 'ruim'
            return f"✗ NÃO unida com o CNC {c0}", 'ruim'
        if not nao:
            return f"✓ unida com {self._imp_juntar(unidas, 'os CNCs ')}", 'ok'
        if unidas:
            return (f"✗ unida só com {self._imp_juntar(unidas, 'o CNC ' if len(unidas) == 1 else 'os CNCs ')}; "
                    f"NÃO unida com {self._imp_juntar(nao, 'o CNC ' if len(nao) == 1 else 'os CNCs ')}"), 'ruim'
        return f"✗ NÃO unida com nenhum dos CNCs ({self._imp_juntar(cncs)})", 'ruim'

    def _imp_popular_conferencia(self, conf, verificacao=None, nome_pdf=None):
        """Esquerda: cada CNC com as posições dele logo abaixo, com as peças
        que ele tem e se a posição está PARCIAL ou COMPLETA nesse ponto.
        Direita (ao clicar): em quais CNCs a posição está e como ficou no PDF."""
        VERDE, AMBAR, VERM = QColor(NEON_GREEN), QColor(NEON_AMBER), QColor('#ff4d4d')
        CINZA = QColor('#8b95a5')
        if conf is None:
            conf = getattr(self, '_imp_conf_dados', None)       # reusa (botão "comparar PDF")
        self._imp_conf_dados = conf
        self._imp_verificacao = verificacao if (verificacao and 'por_cnc' in verificacao) else None
        self._imp_conf = {c['cnc']: c for c in (conf or {}).get('cnc_posicoes', [])}
        self._imp_conf_ordens = {o['ordem']: o for o in (conf or {}).get('lista_ordens', [])}
        self._imp_pos_cncs, self._imp_linhas = {}, {}
        self._imp_pendentes = {c['cnc'] for c in (conf or {}).get('cnc_posicoes', []) if c.get('pendente')}
        for c in (conf or {}).get('cnc_posicoes', []):
            for p in c['posicoes']:
                self._imp_pos_cncs.setdefault(p['pos'], []).append(c['cnc'])
                self._imp_linhas[(c['cnc'], p['pos'])] = p
        lista = self.imp_lista_cncs
        lista.blockSignals(True)
        lista.clear()
        self.imp_tree_detalhe_cnc.clear()
        self.imp_busca_cnc.clear()
        if not conf:
            lista.blockSignals(False)
            return
        ver = self._imp_verificacao
        itens = {}
        for c in conf['cnc_posicoes']:
            for p in c['posicoes']:
                itens.setdefault(p['pos'], p)
        n_comp = sum(1 for p in itens.values() if p['status_total'] == 'completa')
        n_parc = sum(1 for p in itens.values() if p['status_total'] == 'parcial')
        n_desc = sum(1 for p in itens.values() if p['status_total'] == 'desconhecida')
        sem_ordem = sum(1 for c in conf['cnc_posicoes'] for p in c['posicoes'] if not p['ordem'])
        de_fora = sum(1 for o in conf['lista_ordens'] if not o['casa'])
        repetidas = sum(1 for cs in self._imp_pos_cncs.values() if len(cs) > 1)
        txt = (f"{len(conf['cnc_posicoes'])} CNC(s) · {len(itens)} posição(ões) (contando [A]/[B] à parte): "
               f"{n_comp} COMPLETA(S) · {n_parc} PARCIAL(IS)"
               + (f" · {n_desc} sem quantidade lida" if n_desc else '')
               + f" · {repetidas} em mais de um CNC  |  {len(conf['lista_ordens'])} ordem(ns) no PDF das Ordens · "
               f"{de_fora} ficam de fora")
        if sem_ordem:
            txt += f"  |  ⚠ {sem_ordem} posição(ões) sem ordem"
        if self._imp_pendentes:
            txt += f"  |  ⏳ {len(self._imp_pendentes)} CNC(s) em conjunto(s) PENDENTE(S) — aguardando completar, não impressos"
        if ver:
            ok = sum(x['ok'] for x in ver['por_cnc'].values())
            tot = sum(x['total'] for x in ver['por_cnc'].values())
            txt += (f"\nPDF conferido ({ver['arquivo']}, {ver['total_paginas']} págs., {ver['blocos']} blocos): "
                    + (f"✓ {ok} de {tot} posições unidas ao CNC" if ok == tot
                       else f"✗ {tot - ok} posição(ões) NÃO ficaram unidas ao CNC ({ok} de {tot} ok)"))
            if ver['ordens_repetidas']:
                txt += f"  |  ⚠ {len(ver['ordens_repetidas'])} ordem(ns) REPETIDA(S) no PDF"
            self.imp_lbl_pdf_comparado.setText(f"PDF comparado: {ver['arquivo']}")
        elif verificacao and 'erro' in verificacao:
            txt += f"\n⚠ não consegui conferir o PDF gerado: {verificacao['erro']}"
        self.imp_lbl_conf.setText(txt)

        for c in conf['cnc_posicoes']:
            esp = rotulo_espessura(c['espessura']) if c['espessura'] else 'esp. ?'
            n_c = sum(1 for p in c['posicoes'] if p['estado'] == 'completa')
            n_p = sum(1 for p in c['posicoes'] if p['estado'] == 'parcial')
            resumo = f"{n_c} completa(s)" + (f" · {n_p} PARCIAL(IS)" if n_p else '')
            if c.get('pendente'):
                pdf_txt, cor_pdf = '⏳ pendente', AMBAR
            elif ver:
                x = ver['por_cnc'].get(c['cnc'])
                if x is None:
                    pdf_txt, cor_pdf = '—', CINZA
                elif x['bloco'] is None:
                    pdf_txt, cor_pdf = '✗ fora', VERM
                elif x['ok'] == x['total']:
                    pdf_txt, cor_pdf = '✓', VERDE
                else:
                    pdf_txt, cor_pdf = f"✗ {x['total'] - x['ok']}", VERM
            else:
                pdf_txt, cor_pdf = '', CINZA
            topo = QTreeWidgetItem(lista, [f"CNC {c['cnc']} · {esp}", f"{len(c['posicoes'])} pos.", resumo, pdf_txt])
            topo.setData(0, Qt.UserRole, ('cnc', c['cnc']))
            topo.setData(1, Qt.UserRole, ' '.join([c['cnc']] + [p['pos'] for p in c['posicoes']]
                                                   + [p['ordem'] for p in c['posicoes'] if p['ordem']]).lower())
            topo.setForeground(2, AMBAR if n_p else VERDE)
            topo.setForeground(3, cor_pdf)
            f = topo.font(0)
            f.setBold(True)
            topo.setFont(0, f)
            for p in c['posicoes']:
                n_cncs = len(self._imp_pos_cncs.get(p['pos'], []))
                nome = p['pos'] + (f'   ⇄ {n_cncs} CNCs' if n_cncs > 1 else '')
                if p['estado'] == 'desconhecida':
                    qtxt, cor_q = 'quantidade não lida', CINZA
                else:
                    rot = 'COMPLETA' if p['estado'] == 'completa' else 'PARCIAL'
                    qtxt = f"{p['qtd_neste_cnc']} pç · {rot} {p['acumulado']}/{p['pedido']}" + ('  ◄ última peça' if p['ultima'] else '')
                    cor_q = VERDE if p['estado'] == 'completa' else AMBAR
                if ver:
                    _t, tipo = self._imp_resumo_posicao(p['pos'], p['ordem'])
                    marca, cor_m = {'ok': ('✓', VERDE), 'ruim': ('✗', VERM), 'neutro': ('—', CINZA)}[tipo]
                else:
                    marca, cor_m = '', CINZA
                if c.get('pendente'):
                    marca, cor_m = '⏳', AMBAR
                filho = QTreeWidgetItem(topo, [nome, p['ordem'] or '—', qtxt, marca])
                filho.setData(0, Qt.UserRole, ('pos', c['cnc'], p['pos']))
                filho.setForeground(2, cor_q)
                filho.setForeground(3, cor_m)
                if not p['ordem']:
                    filho.setForeground(1, VERM)
        lista.expandAll()
        for col, larg in enumerate((195, 70, 252)):
            lista.setColumnWidth(col, larg)
        self._imp_ajustar_ultima_coluna(lista)
        lista.blockSignals(False)
        if lista.topLevelItemCount():
            lista.setCurrentItem(lista.topLevelItem(0))

    def _imp_filtrar_cncs(self, texto):
        t = (texto or '').strip().lower()
        for k in range(self.imp_lista_cncs.topLevelItemCount()):
            it = self.imp_lista_cncs.topLevelItem(k)
            it.setHidden(bool(t) and t not in (it.data(1, Qt.UserRole) or ''))

    def _imp_mostrar_cnc(self, item, _anterior=None):
        """Clicou num CNC ou numa posição: à direita, em quais CNCs cada
        posição está (com as peças de cada um), PARCIAL/COMPLETA e como ficou
        no PDF gerado."""
        VERDE, AMBAR, VERM = QColor(NEON_GREEN), QColor(NEON_AMBER), QColor('#ff4d4d')
        CINZA = QColor('#8b95a5')
        det = self.imp_tree_detalhe_cnc
        det.clear()
        if item is None:
            return
        chave = item.data(0, Qt.UserRole)
        if not chave:
            return
        ver = getattr(self, '_imp_verificacao', None)

        def cor_de(tipo):
            return {'ok': VERDE, 'ruim': VERM, 'neutro': CINZA}[tipo]

        def txt_estado(d, pedido):
            if d['estado'] == 'desconhecida':
                return 'quantidade não lida', CINZA
            if d['estado'] == 'completa':
                return ('COMPLETA ◄ última peça aqui' if d['ultima'] else 'COMPLETA'), VERDE
            return f"PARCIAL {d['acumulado']}/{pedido} · faltam {pedido - d['acumulado']}", AMBAR

        def txt_total(p):
            if p['status_total'] == 'desconhecida':
                return 'quantidade não lida', CINZA
            if p['status_total'] == 'completa':
                return f"COMPLETA {p['soma_total']}/{p['pedido']}", VERDE
            return f"PARCIAL {p['soma_total']}/{p['pedido']} · faltam {p['pedido'] - p['soma_total']}", AMBAR

        def pdf_do_cnc(cnc, pos):
            l = self._imp_linha_pdf(cnc, pos)
            if l is None:
                return ('gere o PDF p/ confirmar' if ver is None else '—'), CINZA
            if l['estado'] == 'unida':
                return f"✓ unida — {l['onde']}", VERDE
            if l['estado'] == 'pendente':
                return '⏳ pendente — não impresso (aguardando completar)', AMBAR
            return f"✗ {l['texto']} {('— ' + l['onde']) if l['onde'] else ''}".strip(), VERM

        if chave[0] == 'cnc':
            c = self._imp_conf.get(chave[1])
            if not c:
                return
            x = ver['por_cnc'].get(c['cnc']) if ver else None
            esp = rotulo_espessura(c['espessura']) if c['espessura'] else 'espessura não identificada'
            ordens_do_cnc = {p['ordem'] for p in c['posicoes'] if p['ordem']}
            cab = (f"CNC {c['cnc']} · {esp} · {c['paginas']} página(s) no PDF do CNC  —  "
                   f"{len(c['posicoes'])} posição(ões) · {len(ordens_do_cnc)} ordem(ns)")
            if c.get('pendente'):
                cab += ('\n⏳ CONJUNTO PENDENTE — não impresso, aguardando completar: ' + (c.get('motivo_pendente') or '')
                        + '  (os CNCs que dividem a posição e as posições já completas esperam juntos)')
            elif x and x['bloco'] is not None:
                cab += (f"\nNo PDF gerado: CNC nas págs. {_faixa_paginas(x['paginas_cnc'])} · bloco das págs. "
                        f"{x['faixa_bloco']} · {x['ok']} de {x['total']} posições unidas ao CNC")
            elif x:
                cab += '\nNo PDF gerado: ✗ este CNC não aparece no PDF'
            else:
                cab += '\nPDF gerado: ainda não — gere o PDF (ou use "Comparar com um PDF já gerado…")'
            self.imp_lbl_detalhe_cnc.setText(cab)
            det.setColumnCount(5)
            det.setHeaderLabels(['Posição', 'Ordem (OF)', 'Em quais CNCs (peças)', 'Situação', 'No PDF gerado'])
            for p in c['posicoes']:
                if len(p['cncs']) == 1:
                    d0 = p['cncs'][0]
                    onde = f"só no CNC {d0['cnc']} ({d0['qtd'] if d0['qtd'] is not None else '?'} pç)"
                elif len(p['cncs']) == 2:
                    onde = ' + '.join(f"CNC {d['cnc']} ({d['qtd']})" for d in p['cncs'])
                else:
                    onde = f"{len(p['cncs'])} CNCs (veja abaixo)"
                t_total, cor_t = txt_total(p)
                t_pdf, tipo = self._imp_resumo_posicao(p['pos'], p['ordem'])
                it = QTreeWidgetItem(det, [p['pos'], p['ordem'] or '—', onde, t_total, t_pdf])
                it.setForeground(3, cor_t)
                it.setForeground(4, cor_de(tipo))
                if len(p['cncs']) > 1:
                    it.setForeground(2, AMBAR)
                for d in (p['cncs'] if len(p['cncs']) > 1 else []):   # um CNC por linha: peças, acumulado, PARCIAL/COMPLETA, PDF
                    t_est, cor_e = txt_estado(d, p['pedido'] or 0)
                    qtd = '?' if d['qtd'] is None else d['qtd']
                    acum = '' if d['acumulado'] is None else f" · acumulado {d['acumulado']} de {p['pedido']}"
                    t_p, cor_p = pdf_do_cnc(d['cnc'], p['pos'])
                    marca = ' (este)' if d['cnc'] == c['cnc'] else ''
                    filho = QTreeWidgetItem(it, [f"↳ CNC {d['cnc']}{marca}", '', f"{qtd} peça(s){acum}", t_est, t_p])
                    filho.setForeground(3, cor_e)
                    filho.setForeground(4, cor_p)
                it.setExpanded(True)
            for col, larg in enumerate((150, 96, 225, 190)):
                det.setColumnWidth(col, larg)
            self._imp_ajustar_ultima_coluna(det)
            return

        # clicou numa POSIÇÃO: uma linha por CNC onde ela está
        cnc_clicado, pos = chave[1], chave[2]
        p0 = self._imp_linhas.get((cnc_clicado, pos))
        if not p0:
            return
        t_total, _cor = txt_total(p0)
        o = getattr(self, '_imp_conf_ordens', {}).get(p0['ordem'] or '', {})
        t_pdf, _tipo = self._imp_resumo_posicao(pos, p0['ordem'])
        n = len(p0['cncs'])
        cab = (f"Posição {pos} · OF {p0['ordem'] or '—'}" + (f" ({o.get('paginas', '?')} pág. da ordem)" if p0['ordem'] else '')
               + f" · pede {p0['pedido'] if p0['pedido'] else '?'} peça(s)  —  "
               + (f"está em {n} CNCs" if n > 1 else f"só no CNC {p0['cncs'][0]['cnc']}")
               + f"\nSituação: {t_total}\nNo PDF gerado: {t_pdf}")
        self.imp_lbl_detalhe_cnc.setText(cab)
        det.setColumnCount(5)
        det.setHeaderLabels(['CNC', 'Peças neste CNC', 'Acumulado', 'Situação', 'No PDF gerado'])
        for d in p0['cncs']:
            t_est, cor_e = txt_estado(d, p0['pedido'] or 0)
            t_p, cor_p = pdf_do_cnc(d['cnc'], pos)
            parte = ''
            it = QTreeWidgetItem(det, [f"CNC {d['cnc']}" + ('   ◄ clicado' if d['cnc'] == cnc_clicado else ''),
                                        '?' if d['qtd'] is None else str(d['qtd']),
                                        '—' if d['acumulado'] is None else f"{d['acumulado']} de {p0['pedido']}",
                                        t_est, t_p])
            it.setForeground(3, cor_e)
            it.setForeground(4, cor_p)
        for col, larg in enumerate((165, 125, 100, 215)):
            det.setColumnWidth(col, larg)
        self._imp_ajustar_ultima_coluna(det)

    @staticmethod
    def _imp_ajustar_ultima_coluna(tree):
        """A última coluna se ajusta ao texto (não corta) — se não couber, aparece a barra de rolagem."""
        h = tree.header()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(tree.columnCount() - 1, QHeaderView.ResizeToContents)

    def _imp_comparar_pdf_existente(self):
        """Escolhe um PDF de Impressão Casada que já existe e confere, posição
        por posição, se cada uma ficou unida à ordem lá dentro."""
        conf = getattr(self, '_imp_conf_dados', None)
        if not conf:
            QMessageBox.warning(self, 'Aviso', 'Primeiro clique em "Conferir antes" (com os PDFs dos CNCs e das '
                                                'Ordens carregados) — a comparação usa essa lista de posições.')
            return
        pasta = os.path.dirname(getattr(self, 'imp_caminho_ordens', '') or '') or ''
        caminho, _ = QFileDialog.getOpenFileName(self, 'Escolher o PDF da Impressão Casada já gerado', pasta, 'PDF (*.pdf)')
        if not caminho:
            return
        self._iniciar_trabalho_em_fundo(
            verificar_pdf_gerado, (caminho, conf), {},
            botoes_desabilitar=[self.imp_btn_conferir, self.imp_btn_gerar, self.imp_btn_comparar_pdf],
            label_status=self.imp_lbl_status,
            msg_rodando='Lendo o PDF e conferindo posição por posição…',
            on_sucesso=lambda ver: self._imp_popular_conferencia(None, ver),
        )

    def _imp_gerar(self, ignorar_pendencias_lantek=False):
        caminhos_cnc = getattr(self, 'imp_caminhos_cnc', [])
        caminho_ordens = getattr(self, 'imp_caminho_ordens', None)
        if not caminhos_cnc or not caminho_ordens:
            QMessageBox.warning(self, 'Aviso', 'Selecione o(s) PDF(s) dos CNCs e o PDF das Ordens antes de gerar.')
            return
        if ignorar_pendencias_lantek and getattr(self, '_imp_caminho_saida_pendente', None):
            caminho_saida = self._imp_caminho_saida_pendente
        else:
            pasta = os.path.dirname(caminho_ordens)
            nome_sugerido = f'impressao_casada_{date_tag()}.pdf'
            caminho_saida, _ = QFileDialog.getSaveFileName(self, 'Salvar PDF de Impressão',
                                                             os.path.join(pasta, nome_sugerido), 'PDF (*.pdf)')
            if not caminho_saida:
                return
        self._imp_caminho_saida_pendente = caminho_saida
        self._iniciar_trabalho_em_fundo(
            gerar_impressao_casada,
            (caminhos_cnc, caminho_ordens, caminho_saida),
            {'duplex': self.imp_chk_duplex.isChecked(),
             'folha_dedicada_cnc': self.imp_chk_folha_cnc.isChecked(),
             'padronizar_a4': self.imp_chk_a4.isChecked(),
             'exigir_completa': self.imp_chk_qtd_completa.isChecked(),
             'unir_partes': self.imp_chk_unir_partes.isChecked(),
             'caminho_lantek': getattr(self, 'imp_caminho_lantek', None),
             'ignorar_pendencias_lantek': ignorar_pendencias_lantek},
            botoes_desabilitar=[self.imp_btn_gerar],
            label_status=self.imp_lbl_status,
            msg_rodando='Lendo PDFs e montando a sequência de impressão…',
            on_sucesso=lambda r: self._imp_concluido(r, caminho_saida),
        )

    def _imp_mostrar_bloqueio_pendencias(self, r):
        """Pop-up de bloqueio: enquanto tiver posição sem programação no
        Lantek (ou programada mas sem o CNC carregado aqui), NÃO deixa
        gerar o PDF direto — só com escolha explícita de deixar de fora
        (e aí sai um relatório de pendências separado, pra nada ficar
        esquecido sem registro)."""
        n_vermelho = len(r.get('ordens_sem_programacao') or [])
        n_amarelo = len(r.get('ordens_programadas_sem_cnc') or [])
        linhas = []
        if n_vermelho:
            linhas.append(f"🚨 {n_vermelho} ordem(ns) SEM PROGRAMAÇÃO no Lantek (nunca foi pro CAM):")
            for d in (r['ordens_sem_programacao'] or [])[:8]:
                linhas.append(f"   • Ordem {d['ordem']}{_txt_obra(d)} — {d['posicoes']}")
            if n_vermelho > 8:
                linhas.append(f"   … e mais {n_vermelho - 8}")
        if n_amarelo:
            linhas.append(f"🟡 {n_amarelo} ordem(ns) programada(s), mas sem o CNC carregado aqui:")
            for d in (r['ordens_programadas_sem_cnc'] or [])[:8]:
                linhas.append(f"   • Ordem {d['ordem']}{_txt_obra(d)} — {d['posicoes']}")
            if n_amarelo > 8:
                linhas.append(f"   … e mais {n_amarelo - 8}")

        caixa = QMessageBox(self)
        caixa.setIcon(QMessageBox.Warning)
        caixa.setWindowTitle('Impressão bloqueada — pendências no Lantek')
        caixa.setText('Não é possível gerar o PDF ainda: existem ordens sem programação '
                       'confirmada no Lantek. Resolva isso antes de imprimir, ou gere deixando '
                       'essas ordens de fora (sai um relatório de pendências separado).')
        caixa.setDetailedText('\n'.join(linhas))
        btn_gerar_fora = caixa.addButton('Gerar mesmo assim, deixando de fora', QMessageBox.AcceptRole)
        caixa.addButton('Cancelar', QMessageBox.RejectRole)
        caixa.setDefaultButton(btn_gerar_fora)
        caixa.exec_()
        self.imp_lbl_status.setText(f"🚫 Bloqueado: 🚨 {n_vermelho} sem programação · 🟡 {n_amarelo} sem CNC aqui")
        if caixa.clickedButton() is btn_gerar_fora:
            self._imp_gerar(ignorar_pendencias_lantek=True)

    def _popular_arvore_impressao(self, tree, r, caminho_saida=None, agrupar_por_obra=False):
        """Preenche a árvore de resultado — usada tanto pela conferência
        prévia (sem PDF ainda) quanto depois de gerar o PDF de verdade."""
        tree.clear()

        def item(pai, texto, detalhe='', cor=None):
            it = QTreeWidgetItem([texto, detalhe])
            if cor:
                it.setForeground(0, cor)
            if pai is None:
                tree.addTopLevelItem(it)
            else:
                pai.addChild(it)
            return it

        AMARELO = QColor(NEON_AMBER)
        VERDE = QColor(NEON_GREEN)
        AZUL = QColor(NEON_CYAN)

        if caminho_saida:
            raiz_resumo = item(None, '📄 Arquivo gerado', os.path.basename(caminho_saida)
                               + (' (nome base — um arquivo por obra)' if len(r.get('arquivos') or []) > 1 else ''), AZUL)
            item(raiz_resumo, 'Total de páginas', str(r['total_paginas']))
            if r.get('caminho_pendencias'):
                item(raiz_resumo, '⚠️ Relatório de pendências', os.path.basename(r['caminho_pendencias']), AMARELO)
        else:
            raiz_resumo = item(None, '🔍 Pré-visualização — nenhum PDF gerado ainda', '', AZUL)
            item(raiz_resumo, 'Ordens no PDF', str(r['total_ordens_no_pdf']))
            item(raiz_resumo, 'CNCs reconhecidos', str(r['total_cncs']))
        if agrupar_por_obra:
            obras = sorted({g.get('obra') or '—' for g in r['relatorio']})
            item(raiz_resumo, 'Obras', ' · '.join(obras) or '—')
        if caminho_saida and len(r.get('arquivos') or []) > 1:
            raiz_arq = item(None, f"📁 PDFs gerados — um por obra ({len(r['arquivos'])})", os.path.dirname(caminho_saida), AZUL)
            for ar in r['arquivos']:
                div = '' if not ar.get('divergencias') else f" · ⚠ {ar['divergencias']} divergência(s)"
                item(raiz_arq, f"Obra {ar['obra']} → {os.path.basename(ar['caminho'])}",
                     f"{ar['paginas']} págs · {ar['conjuntos']} conjunto(s) · {ar['ordens']} ordem(ns){div}")
        item(raiz_resumo, 'Espessuras', ' · '.join(r['espessuras']) or '—')
        item(raiz_resumo, 'Conjuntos', str(r['grupos']))
        item(raiz_resumo, 'Ordens que vão casar' if not caminho_saida else 'Ordens impressas',
             str(r['ordens_usadas']))

        raiz_conj = item(None, f"📦 Conjuntos ({r['grupos']})", '', VERDE)
        item_obra, obra_atual = None, object()
        item_fluxo, fluxo_atual = None, object()
        pai_padrao = raiz_conj
        for g in r['relatorio']:
            pai = raiz_conj
            if agrupar_por_obra:
                obra = g.get('obra') or '—'
                fluxo = g.get('fluxo_relatorio') or '—'
                if obra != obra_atual:
                    obra_atual, fluxo_atual = obra, object()
                    item_obra = item(raiz_conj, f'🏗️ Obra {obra}', '')
                if fluxo != fluxo_atual:
                    fluxo_atual = fluxo
                    item_fluxo = item(item_obra, f'Fluxo {fluxo}', '')
                pai = item_fluxo
            item_g = item(pai, f"CNC(s) {', '.join(g['cncs'])}", rotulo_espessura(g['espessura']))
            if 'detalhe_cnc' in g:
                for dc in g['detalhe_cnc']:
                    det = f"{dc['paginas']} página(s)" + (f" + {dc['branca']} branca(s)" if dc['branca'] else '')
                    item(item_g, f"🔧 CNC {dc['cnc']}", det)
                for do_ in g['detalhe_ord']:
                    det = f"{do_['paginas']} página(s)" + (f" + {do_['branca']} branca(s)" if do_['branca'] else '')
                    item(item_g, f"📋 Ordem {do_['ordem']}", f"{do_['posicoes']} · {det}")
            else:
                for o in g.get('ordens', []):
                    item(item_g, f"📋 Ordem {o}", '')

        if r.get('conjuntos_pendentes'):
            pend = r['conjuntos_pendentes']
            raiz = item(None, f"⏳ Conjuntos PENDENTES — aguardando completar ({len(pend)}) · NÃO impressos", '', AMARELO)
            for g in pend:
                item_p = item(raiz, f"CNC(s) {', '.join(g['cncs'])}", rotulo_espessura(g['espessura']))
                for i_ in g['incompletas']:
                    item(item_p, f"⚠ posição {i_['pos']}",
                         f"tem {i_['cortado']} de {i_['necessario']} — faltam {i_['necessario'] - i_['cortado']} · CNC(s): {i_['cncs']}")
                for o_ in g['ordens']:
                    item(item_p, f"📋 Ordem {o_} (segurada)", '')

        if r['sem_numero']:
            raiz = item(None, f"⚠️ Sem número de CNC reconhecido ({len(r['sem_numero'])})", '', AMARELO)
            for s in r['sem_numero']:
                item(raiz, s['arquivo'], f"página {s['pagina']}")

        if r.get('texto_perdido'):
            raiz = item(None, f"⚠️ Páginas com texto que não saiu na cópia ({len(r['texto_perdido'])})", '', AMARELO)
            for t_ in r['texto_perdido']:
                item(raiz, f"{t_['origem']} — página {t_['pagina']}",
                     f"faltou: {t_['faltou']}")

        if r['incompletas']:
            raiz = item(None, f"⚠️ Posições sem quantidade completa ({len(r['incompletas'])})", '', AMARELO)
            for it_ in r['incompletas']:
                item(raiz, it_['pos'], f"cortado {it_['cortado']}/{it_['necessario']} · CNCs: {it_['cncs']}")

        if r['cncs_sem_ordem']:
            item(None, f"⚠️ CNC(s) sem ordem casada ({len(r['cncs_sem_ordem'])})",
                 ', '.join(r['cncs_sem_ordem']), AMARELO)

        if r['partes_complementares']:
            raiz = item(None, f"🔗 Partes complementares [B]/[C]... ({len(r['partes_complementares'])})", '', AMARELO)
            for pc in r['partes_complementares']:
                item(raiz, f"CNC {pc['cnc']}", pc['pos'])

        if r['descartadas']:
            raiz = item(None, f"🗑️ Ordens descartadas — sem CNC casado ({len(r['descartadas'])})", '', AMARELO)
            for d in r['descartadas']:
                item(raiz, f"Ordem {d['ordem']}{_txt_obra(d)}", d['posicoes'])

        if r.get('ordens_sem_programacao'):
            VERMELHO = QColor('#ff4d4d')
            raiz = item(None, f"🚨 SEM PROGRAMAÇÃO NO LANTEK — peça nunca foi pro CAM "
                              f"({len(r['ordens_sem_programacao'])})",
                        'grave: ninguém programou essa peça em nenhum nesting ainda', VERMELHO)
            for d in r['ordens_sem_programacao']:
                item(raiz, f"Ordem {d['ordem']}{_txt_obra(d)}", d['posicoes'])

        if r.get('ordens_programadas_sem_cnc'):
            raiz = item(None, f"🟡 Programada no Lantek, mas sem CNC carregado aqui "
                              f"({len(r['ordens_programadas_sem_cnc'])})",
                        'só falta achar/carregar o PDF certo desse CNC', AMARELO)
            for d in r['ordens_programadas_sem_cnc']:
                det = d['posicoes']
                info = d.get('detalhe')
                if info:
                    det += f" · {info.get('maquina') or '—'} · {info.get('data') or '—'} · nesting {', '.join(info.get('nesting_ids') or [])}"
                item(raiz, f"Ordem {d['ordem']}{_txt_obra(d)}", det)

        tree.expandToDepth(0)
        raiz_conj.setExpanded(True)
        tree.resizeColumnToContents(0)

    def _imp_concluido(self, r, caminho_saida):
        if r.get('bloqueado_pendencias'):
            self._imp_mostrar_bloqueio_pendencias(r)
            return
        self._imp_caminho_saida_pendente = None
        if r.get('nada_a_imprimir'):
            self._imp_mostrar_nada_a_imprimir(self.imp_tree_resultado, self.imp_lbl_status, r)
            return
        msg = (f"✅ PDF montado: {r['total_paginas']} páginas · "
               f"{len(r['espessuras'])} espessura(s) ({' · '.join(r['espessuras'])}) · "
               f"{r['grupos']} conjunto(s) · {r['ordens_usadas']} ordem(ns) impressas")
        if r['descartadas']:
            msg += f" · {len(r['descartadas'])} ordem(ns) descartadas"
        if r.get('caminho_pendencias'):
            msg += f" · ⚠️ pendências deixadas de fora — ver {os.path.basename(r['caminho_pendencias'])}"
        msg += self._imp_texto_pendentes(r)
        msg += self._imp_texto_texto_perdido(r)
        if r.get('a4_falhas'):
            msg += f" · ⚠️ {r['a4_falhas']} página(s) NÃO deu pra ajustar pra A4 — confira"
        elif r.get('a4_corrigidas'):
            msg += f" · 🔧 {r['a4_corrigidas']} página(s) estavam fora do A4 e foram corrigidas automaticamente"
        elif r.get('a4_conferido'):
            msg += ' · A4 conferido ✓'
        if r.get('conferencia'):
            self._imp_popular_conferencia(r['conferencia'], r.get('verificacao'))
        self.imp_lbl_status.setText(msg)
        self._preencher_kpis(self.imp_kpis, r, gerado=True)
        self._popular_arvore_impressao(self.imp_tree_resultado, r, caminho_saida=caminho_saida)
        QMessageBox.information(self, 'Concluído', msg)

    # ── Aba Impressão Casada — Multi-Obra ──
    def _build_impressao_multi_tab(self, tab):
        v = QVBoxLayout(tab)

        gb_cnc = QGroupBox('1) PDF(s) dos CNCs (nesting) — pode misturar várias obras')
        v1 = QVBoxLayout(gb_cnc)
        h1 = QHBoxLayout()
        btn_add_cnc = QPushButton('➕ Adicionar PDF(s) de CNC…')
        btn_add_cnc.clicked.connect(self._impm_adicionar_cnc)
        btn_clear_cnc = QPushButton('Limpar')
        btn_clear_cnc.clicked.connect(self._impm_limpar_cnc)
        h1.addWidget(btn_add_cnc)
        h1.addWidget(btn_clear_cnc)
        h1.addStretch()
        v1.addLayout(h1)
        self.impm_lst_cnc = DropListWidget(self._impm_adicionar_cnc_paths)
        self.impm_lst_cnc.setMaximumHeight(110)
        v1.addWidget(self.impm_lst_cnc)
        v1.addWidget(DropArea('⬇ arraste PDF(s) de CNC aqui', self._impm_adicionar_cnc_paths))
        v.addWidget(gb_cnc)

        gb_ord = QGroupBox('2) PDF(s) das Ordens de Fabricação — um por obra (pode carregar vários)')
        v2 = QVBoxLayout(gb_ord)
        h2 = QHBoxLayout()
        btn_ord = QPushButton('➕ Adicionar PDF(s) das Ordens…')
        btn_ord.clicked.connect(self._impm_escolher_ordens)
        btn_ord_limpar = QPushButton('Limpar')
        btn_ord_limpar.clicked.connect(self._impm_limpar_ordens)
        h2.addWidget(btn_ord)
        h2.addWidget(btn_ord_limpar)
        h2.addStretch()
        v2.addLayout(h2)
        self.impm_lst_ordens = DropListWidget(self._impm_definir_ordens_varias)
        self.impm_lst_ordens.setMaximumHeight(110)
        v2.addWidget(self.impm_lst_ordens)
        v2.addWidget(DropArea('⬇ arraste o(s) PDF(s) das Ordens aqui (um por obra)', self._impm_definir_ordens_varias))
        v.addWidget(gb_ord)

        gb_rel = QGroupBox('3) Relatórios de Fluxos — um por obra (pode carregar vários) — organizam por Obra → Fluxo')
        v2b = QVBoxLayout(gb_rel)
        h2b = QHBoxLayout()
        btn_rel = QPushButton('🔀 Adicionar Relatório(s) de Fluxos…')
        btn_rel.clicked.connect(self._impm_escolher_relatorio)
        btn_rel_limpar = QPushButton('Limpar')
        btn_rel_limpar.clicked.connect(self._impm_limpar_relatorios)
        self.impm_lbl_relatorio = QLabel('nenhum relatório carregado')
        self.impm_lbl_relatorio.setWordWrap(True)
        h2b.addWidget(btn_rel)
        h2b.addWidget(btn_rel_limpar)
        h2b.addWidget(self.impm_lbl_relatorio, 1)
        v2b.addLayout(h2b)
        area_rel = DropArea('⬇ arraste o(s) Relatório(s) de Fluxos aqui (um por obra)',
                             lambda paths: self._impm_definir_relatorios(paths))
        v2b.addWidget(area_rel)
        v.addWidget(gb_rel)

        gb_lantek = CaixaRecolhivel('4) Relatório do Lantek (opcional) — segurança extra contra peça sem programação')
        v2c = gb_lantek.layout_conteudo()
        h2c = QHBoxLayout()
        btn_lantek = QPushButton('📥 Escolher Relatório do Lantek…')
        btn_lantek.clicked.connect(self._impm_escolher_lantek)
        self.impm_lbl_lantek = QLabel('nenhum relatório carregado — sem ele, a conferência de "programado ou não" fica desligada')
        self.impm_lbl_lantek.setWordWrap(True)
        h2c.addWidget(btn_lantek)
        h2c.addWidget(self.impm_lbl_lantek, 1)
        v2c.addLayout(h2c)
        area_lantek = DropArea('⬇ arraste o Relatório do Lantek (.csv) aqui',
                                lambda paths: self._impm_definir_lantek(paths[0]))
        v2c.addWidget(area_lantek)
        v.addWidget(gb_lantek)

        gb_opc = CaixaRecolhivel('5) Opções de impressão')
        v3 = gb_opc.layout_conteudo()
        self.impm_chk_duplex = self._imp_checkbox(v3, 'Frente e verso', True,
            'insere página em branco para fechar bloco ímpar')
        self.impm_chk_folha_cnc = self._imp_checkbox(v3, 'Folha dedicada por CNC', True,
            'LIGADO: cada página de CNC sozinha na folha, verso em branco. DESLIGADO: as páginas do mesmo '
            'CNC ficam juntas (a 2ª folha no verso da principal) e o próximo CNC começa em folha nova', )
        self.impm_chk_a4 = self._imp_checkbox(v3, 'Padronizar tudo em A4', True,
            'recorta a margem vazia e aproveita a folha inteira')
        self.impm_chk_qtd_completa = self._imp_checkbox(v3, 'Só com quantidade completa', True,
            'não imprime a ordem se faltar peça nos CNCs carregados')
        self.impm_chk_unir_partes = self._imp_checkbox(v3, "Unir peça dividida [A]/[B]", True,
            'as duas metades saem em sequência, com a ordem uma vez só')
        v.addWidget(gb_opc)

        gb_obras = CaixaRecolhivel('6) Obras a gerar — não precisa mandar tudo')
        vo = gb_obras.layout_conteudo()
        self.impm_lbl_obras = QLabel('Clique em "Conferir antes" pra listar as obras do lote. '
                                      'Marque só as que você quer no PDF.')
        self.impm_lbl_obras.setWordWrap(True)
        vo.addWidget(self.impm_lbl_obras)
        self.impm_lista_obras = QListWidget()
        self.impm_lista_obras.setMaximumHeight(140)
        vo.addWidget(self.impm_lista_obras)
        self.impm_chk_separar = self._imp_checkbox(vo, 'Gerar um PDF separado por obra', False,
            'um arquivo por obra marcada (nome_obra_2139.pdf…), cada um com as mesmas regras da Impressão Casada: '
            'espessura, laser por último, CNC junto das ordens')
        v.addWidget(gb_obras)

        h4 = QHBoxLayout()
        self.impm_btn_conferir = QPushButton('🔍 Conferir antes')
        self.impm_btn_conferir.clicked.connect(self._impm_conferir)
        h4.addWidget(self.impm_btn_conferir)
        self.impm_btn_gerar = QPushButton('🖨️ Gerar PDF — organizado por Obra → Fluxo')
        self.impm_btn_gerar.setObjectName('btnAnalisar')
        self.impm_btn_gerar.clicked.connect(self._impm_gerar)
        h4.addWidget(self.impm_btn_gerar)
        v.addLayout(h4)

        self.impm_kpis = FaixaKPI([('obras', '🏗️', 'Obras'), ('conjuntos', '📦', 'Conjuntos'),
                                    ('ordens', '📋', 'Ordens que casam'), ('pendentes', '⏳', 'Pendentes'),
                                    ('paginas', '📄', 'Páginas do PDF')])
        v.addWidget(self.impm_kpis)
        self.impm_lbl_status = QLabel('Aguardando arquivos...')
        v.addWidget(self.impm_lbl_status)

        self.impm_tree_resultado = QTreeWidget()
        self.impm_tree_resultado.setHeaderLabels(['Item', 'Detalhe'])
        self.impm_tree_resultado.setMinimumHeight(320)
        self.impm_tree_resultado.setAlternatingRowColors(True)
        self.impm_tree_resultado.header().setStretchLastSection(True)
        v.addWidget(self.impm_tree_resultado, 1)

        self.impm_caminhos_cnc = []
        self.impm_caminhos_ordens = []
        self.impm_caminhos_relatorio = []

    def _impm_adicionar_cnc(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Selecionar PDF(s) de CNC', '', 'PDF (*.pdf)')
        self._impm_adicionar_cnc_paths(paths)

    def _impm_adicionar_cnc_paths(self, paths):
        self.impm_caminhos_cnc = getattr(self, 'impm_caminhos_cnc', [])
        for p in paths:
            if p not in self.impm_caminhos_cnc:
                self.impm_caminhos_cnc.append(p)
        self.impm_lst_cnc.clear()
        self.impm_lst_cnc.addItems([os.path.basename(p) for p in self.impm_caminhos_cnc])

    def _impm_limpar_cnc(self):
        self.impm_caminhos_cnc = []
        self.impm_lst_cnc.clear()

    def _impm_escolher_ordens(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Selecionar PDF(s) das Ordens (um por obra)', '', 'PDF (*.pdf)')
        if paths:
            self._impm_definir_ordens_varias(paths)

    def _impm_definir_ordens_varias(self, paths):
        """Soma os PDFs de ordens escolhidos aos que já estavam (sem repetir o mesmo arquivo)."""
        lista = list(getattr(self, 'impm_caminhos_ordens', []))
        for pth in paths:
            if pth not in lista:
                lista.append(pth)
        self.impm_caminhos_ordens = lista
        self.impm_lst_ordens.clear()
        self.impm_lst_ordens.addItems([os.path.basename(x) for x in lista])

    def _impm_definir_ordens(self, path):              # compatibilidade
        self._impm_definir_ordens_varias([path])

    def _impm_limpar_ordens(self):
        self.impm_caminhos_ordens = []
        self.impm_lst_ordens.clear()

    def _impm_escolher_relatorio(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Selecionar Relatório(s) de Fluxos (um por obra)', '',
                                                 'Excel (*.xlsx *.xlsm *.xlsb *.xls)')
        if not paths:
            return
        self._impm_definir_relatorios(paths)

    def _impm_definir_relatorios(self, paths):
        """Soma os relatórios escolhidos aos que já estavam (sem repetir o mesmo arquivo)."""
        lista = list(getattr(self, 'impm_caminhos_relatorio', []))
        for pth in paths:
            if pth not in lista:
                lista.append(pth)
        self.impm_caminhos_relatorio = lista
        self.impm_lbl_relatorio.setText(f"{len(lista)} relatório(s): " + ' · '.join(os.path.basename(x) for x in lista))

    def _impm_definir_relatorio(self, path):          # compatibilidade
        self._impm_definir_relatorios([path])

    def _impm_limpar_relatorios(self):
        self.impm_caminhos_relatorio = []
        self.impm_lbl_relatorio.setText('nenhum relatório carregado')

    def _impm_escolher_lantek(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar Relatório do Lantek', '',
                                               'CSV/Excel (*.csv *.xlsx *.xlsm *.xls);;Todos (*)')
        if not path:
            return
        self._impm_definir_lantek(path)

    def _impm_definir_lantek(self, path):
        self.impm_caminho_lantek = path
        self.impm_lbl_lantek.setText(f'✓ {os.path.basename(path)}')

    def _impm_conferir(self):
        caminhos_cnc = getattr(self, 'impm_caminhos_cnc', [])
        caminho_ordens = list(getattr(self, 'impm_caminhos_ordens', [])) or None
        caminho_relatorio = list(getattr(self, 'impm_caminhos_relatorio', [])) or None
        if not caminhos_cnc or not caminho_ordens:
            QMessageBox.warning(self, 'Aviso', 'Selecione o(s) PDF(s) dos CNCs e o PDF das Ordens antes de conferir.')
            return
        if not caminho_relatorio:
            QMessageBox.warning(self, 'Aviso', 'Selecione o(s) Relatório(s) de Fluxos antes de conferir.')
            return
        self._iniciar_trabalho_em_fundo(
            analisar_impressao_casada,
            (caminhos_cnc, caminho_ordens),
            {'unir_partes': self.impm_chk_unir_partes.isChecked(),
             'exigir_completa': self.impm_chk_qtd_completa.isChecked(),
             'caminho_relatorio_fluxos': caminho_relatorio,
             'caminho_lantek': getattr(self, 'impm_caminho_lantek', None)},
            botoes_desabilitar=[self.impm_btn_conferir, self.impm_btn_gerar],
            label_status=self.impm_lbl_status,
            msg_rodando='Lendo PDFs, relatório de fluxos e conferindo (sem gerar PDF ainda)…',
            on_sucesso=self._impm_conferido,
        )

    def _impm_conferido(self, r):
        obras = sorted({g.get('obra') or '—' for g in r['relatorio']})
        msg = (f"🔍 Conferência: {len(obras)} obra(s) · {r['grupos']} conjunto(s) · "
               f"{r['ordens_usadas']} de {r['total_ordens_no_pdf']} ordem(ns) vão casar · "
               f"{len(r['descartadas'])} vão ficar de fora — revise antes de gerar o PDF de verdade")
        if r.get('ordens_sem_programacao'):
            msg += f" · 🚨 {len(r['ordens_sem_programacao'])} SEM PROGRAMAÇÃO no Lantek"
        if r.get('ordens_programadas_sem_cnc'):
            msg += f" · 🟡 {len(r['ordens_programadas_sem_cnc'])} programada(s) mas sem CNC aqui"
        msg += self._imp_texto_pendentes(r)
        msg += self._imp_texto_texto_perdido(r)
        if r.get('ordens_repetidas_ignoradas'):
            msg += f" · ⚠ {len(r['ordens_repetidas_ignoradas'])} ordem(ns) repetida(s) em mais de um PDF — contada(s) uma vez só"
        self.impm_lbl_status.setText(msg)
        self._preencher_kpis(self.impm_kpis, r, gerado=False)
        self._popular_arvore_impressao(self.impm_tree_resultado, r, agrupar_por_obra=True)
        self.impm_tree_resultado.expandToDepth(1)
        # lista de obras pra escolher (tudo marcado de início)
        lista = self.impm_lista_obras
        lista.clear()
        for d in r.get('obras', []):
            it = QListWidgetItem(f"Obra {d['obra']} — {d['conjuntos']} conjunto(s) · {d['ordens']} ordem(ns)")
            it.setData(Qt.UserRole, d['obra'])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            lista.addItem(it)
        self.impm_lbl_obras.setText(f"{lista.count()} obra(s) no lote — marque as que vão pro PDF"
                                     + (' (ou gere um PDF por obra)' if lista.count() > 1 else ''))

    def _impm_gerar(self):
        caminhos_cnc = getattr(self, 'impm_caminhos_cnc', [])
        caminho_ordens = list(getattr(self, 'impm_caminhos_ordens', [])) or None
        caminho_relatorio = list(getattr(self, 'impm_caminhos_relatorio', [])) or None
        if not caminhos_cnc or not caminho_ordens:
            QMessageBox.warning(self, 'Aviso', 'Selecione o(s) PDF(s) dos CNCs e o PDF das Ordens antes de gerar.')
            return
        if not caminho_relatorio:
            QMessageBox.warning(self, 'Aviso',
                                 'Selecione o(s) Relatório(s) de Fluxos — eles organizam por Obra → Fluxo.')
            return
        # obras marcadas na lista (só passa o filtro se alguma ficou de fora)
        obras_sel = None
        lista = self.impm_lista_obras
        if lista.count():
            marcadas = [lista.item(i).data(Qt.UserRole) for i in range(lista.count())
                        if lista.item(i).checkState() == Qt.Checked]
            if not marcadas:
                QMessageBox.warning(self, 'Aviso', 'Marque pelo menos uma obra pra gerar.')
                return
            if len(marcadas) < lista.count():
                obras_sel = marcadas
        separar = self.impm_chk_separar.isChecked()
        pasta = os.path.dirname(caminho_ordens[0])
        nome_sugerido = f'impressao_casada_multiobra_{date_tag()}.pdf'
        titulo = 'Salvar PDFs por obra — nome base (cada obra vira um arquivo)' if separar else 'Salvar PDF de Impressão'
        caminho_saida, _ = QFileDialog.getSaveFileName(self, titulo, os.path.join(pasta, nome_sugerido), 'PDF (*.pdf)')
        if not caminho_saida:
            return
        self._iniciar_trabalho_em_fundo(
            gerar_impressao_casada,
            (caminhos_cnc, caminho_ordens, caminho_saida),
            {'obras': obras_sel, 'separar_por_obra': separar,
             'duplex': self.impm_chk_duplex.isChecked(),
             'folha_dedicada_cnc': self.impm_chk_folha_cnc.isChecked(),
             'padronizar_a4': self.impm_chk_a4.isChecked(),
             'exigir_completa': self.impm_chk_qtd_completa.isChecked(),
             'unir_partes': self.impm_chk_unir_partes.isChecked(),
             'caminho_relatorio_fluxos': caminho_relatorio,
             'caminho_lantek': getattr(self, 'impm_caminho_lantek', None)},
            botoes_desabilitar=[self.impm_btn_gerar],
            label_status=self.impm_lbl_status,
            msg_rodando='Lendo PDFs, relatório de fluxos e montando a sequência…',
            on_sucesso=lambda r: self._impm_concluido(r, caminho_saida),
        )

    def _impm_concluido(self, r, caminho_saida):
        if r.get('nada_a_imprimir'):
            self._imp_mostrar_nada_a_imprimir(self.impm_tree_resultado, self.impm_lbl_status, r, com_conferencia=False)
            return
        obras = sorted({g.get('obra') or '—' for g in r['relatorio']})
        n_arq = len(r.get('arquivos') or [])
        msg = (f"✅ {n_arq} PDFs (um por obra) montados: " if n_arq > 1 else "✅ PDF montado: ") + (f"{r['total_paginas']} páginas · {len(obras)} obra(s) · "
               f"{len(r['espessuras'])} espessura(s) · {r['grupos']} conjunto(s) · "
               f"{r['ordens_usadas']} ordem(ns) impressas")
        if r['descartadas']:
            msg += f" · {len(r['descartadas'])} ordem(ns) descartadas"
        if r.get('ordens_sem_programacao'):
            msg += f" · 🚨 {len(r['ordens_sem_programacao'])} SEM PROGRAMAÇÃO no Lantek"
        if r.get('ordens_programadas_sem_cnc'):
            msg += f" · 🟡 {len(r['ordens_programadas_sem_cnc'])} programada(s) mas sem CNC aqui"
        msg += self._imp_texto_pendentes(r)
        if r.get('ordens_repetidas_ignoradas'):
            msg += f" · ⚠ {len(r['ordens_repetidas_ignoradas'])} ordem(ns) repetida(s) em mais de um PDF — contada(s) uma vez só"
        self.impm_lbl_status.setText(msg)
        self._preencher_kpis(self.impm_kpis, r, gerado=True)
        self._popular_arvore_impressao(self.impm_tree_resultado, r, caminho_saida=caminho_saida, agrupar_por_obra=True)
        self.impm_tree_resultado.expandToDepth(1)
        QMessageBox.information(self, 'Concluído', msg)

    # ── Aba Grupo LIC ──
    def _build_grupo_lic_tab(self, tab):
        v = QVBoxLayout(tab)

        gb = QGroupBox('1) PDF das Ordens do Pacote / Obra inteira')
        vb = QVBoxLayout(gb)
        hb = QHBoxLayout()
        btn = QPushButton('📄 Escolher PDF do Pacote…')
        btn.clicked.connect(self._lic_escolher_pacote)
        self.lic_lbl_pacote = QLabel('nenhum arquivo carregado')
        hb.addWidget(btn)
        hb.addWidget(self.lic_lbl_pacote, 1)
        vb.addLayout(hb)
        vb.addWidget(DropArea('⬇ arraste o PDF do pacote aqui', lambda paths: self._lic_definir_pacote(paths[0])))
        v.addWidget(gb)

        gb_rel = QGroupBox('2) Relatório de fluxos (opcional) — lê a aba Não Preparação (e PS PREP / Preparação)')
        vr = QVBoxLayout(gb_rel)
        hr = QHBoxLayout()
        btn_rel = QPushButton('🔀 Adicionar Relatório(s) de Fluxos…')
        btn_rel.clicked.connect(self._lic_escolher_relatorio)
        btn_rel_limpar = QPushButton('Limpar')
        btn_rel_limpar.clicked.connect(self._lic_limpar_relatorios)
        self.lic_lbl_relatorio = QLabel('nenhum relatório carregado — a obra vem só do PDF')
        self.lic_lbl_relatorio.setWordWrap(True)
        hr.addWidget(btn_rel)
        hr.addWidget(btn_rel_limpar)
        hr.addWidget(self.lic_lbl_relatorio, 1)
        vr.addLayout(hr)
        vr.addWidget(DropArea('⬇ arraste o(s) relatório(s) de fluxos aqui (um por obra/lote)',
                               lambda paths: self._lic_definir_relatorios(paths)))
        v.addWidget(gb_rel)

        h = QHBoxLayout()
        self.lic_btn_processar = QPushButton('⚙️ Processar Grupo LIC: separar por obra, Grupo LIC, tipo e espessura')
        self.lic_btn_processar.setObjectName('btnAnalisar')
        self.lic_btn_processar.clicked.connect(self._lic_processar)
        h.addWidget(self.lic_btn_processar)
        self.lic_btn_exportar = QPushButton('📤 Exportar um PDF por Classe…')
        self.lic_btn_exportar.setEnabled(False)
        self.lic_btn_exportar.clicked.connect(self._lic_exportar_por_classe)
        h.addWidget(self.lic_btn_exportar)
        self.lic_btn_pdf_tudo = QPushButton('🖨️ PDF de tudo')
        self.lic_btn_pdf_tudo.setObjectName('btnPrincipal')
        self.lic_btn_pdf_tudo.setEnabled(False)
        self.lic_btn_pdf_tudo.clicked.connect(self._lic_pdf_de_tudo)
        h.addWidget(self.lic_btn_pdf_tudo)
        v.addLayout(h)

        self.lic_chk_pdf_por_obra = QCheckBox('Gerar um PDF separado por obra')
        self.lic_chk_pdf_por_obra.setToolTip(
            'só habilita quando o pacote tem mais de uma obra; vale para "PDF de tudo", "PDF de todo o tipo/grupo" e '
            '"Exportar um PDF por Classe" — cada obra vira um arquivo (nome_obra_2143.pdf…), na mesma sequência '
            '(espessura…). Desmarque a obra na árvore pra não levar.')
        self.lic_chk_pdf_por_obra.setChecked(True)
        self.lic_chk_pdf_por_obra.setEnabled(False)
        v.addWidget(self.lic_chk_pdf_por_obra)

        self.lic_chk_lista_conf = QCheckBox('Salvar lista de conferência (.txt) junto de cada PDF')
        self.lic_chk_lista_conf.setToolTip(
            'grava "<nome>_conferencia.txt" ao lado do PDF com obra, Grupo LIC, tipo, espessura e as páginas de '
            'cada OF — serve pra conferir a folha impressa. Antes de gerar o programa sempre mostra o resumo por '
            'obra e, depois de gerar, confere o PDF contra o pacote (páginas e texto).')
        self.lic_chk_lista_conf.setChecked(True)
        v.addWidget(self.lic_chk_lista_conf)

        h2 = QHBoxLayout()
        self.lic_btn_definir_grupo = QPushButton('🏷️ Definir Grupo LIC da OF selecionada e lembrar pra sempre')
        self.lic_btn_definir_grupo.setEnabled(False)
        self.lic_btn_definir_grupo.clicked.connect(self._lic_definir_grupo_lic_selecionado)
        h2.addWidget(self.lic_btn_definir_grupo)
        h2.addStretch()
        v.addLayout(h2)

        self.lic_lbl_status = QLabel('Aguardando arquivo...')
        v.addWidget(self.lic_lbl_status)

        self.lic_tree = QTreeWidget()
        self.lic_tree.setHeaderLabels(['Obra / Grupo LIC / Tipo / Espessura / OF', 'Detalhe', 'Ação'])
        self.lic_tree.setColumnWidth(0, 340)
        self.lic_tree.setColumnWidth(2, 150)
        self.lic_tree.setMinimumHeight(440)
        self.lic_tree.itemChanged.connect(self._lic_item_marcacao_mudou)
        v.addWidget(self.lic_tree, 1)

        self.lic_caminho_pacote = None
        self.lic_caminhos_relatorio = []
        self._lic_stats_relatorio = None
        self._lic_ordens_cache = None
        self._lic_pos_para_ordem_cache = None

    def _lic_escolher_relatorio(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Selecionar Relatório(s) de Fluxos', '',
                                                 'Excel (*.xlsx *.xlsm *.xlsb *.xls)')
        if paths:
            self._lic_definir_relatorios(paths)

    def _lic_definir_relatorios(self, paths):
        """Soma os relatórios escolhidos aos que já estavam (sem repetir o mesmo arquivo)."""
        lista = list(getattr(self, 'lic_caminhos_relatorio', []))
        for pth in paths:
            if pth not in lista:
                lista.append(pth)
        self.lic_caminhos_relatorio = lista
        self.lic_lbl_relatorio.setText(f"{len(lista)} relatório(s): " + ' · '.join(os.path.basename(x) for x in lista)
                                       + ' — clique em Processar para aplicar')

    def _lic_limpar_relatorios(self):
        self.lic_caminhos_relatorio = []
        self.lic_lbl_relatorio.setText('nenhum relatório carregado — a obra vem só do PDF')

    def _lic_escolher_pacote(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar PDF do Pacote', '', 'PDF (*.pdf)')
        if not path:
            return
        self._lic_definir_pacote(path)

    def _lic_definir_pacote(self, path):
        self.lic_caminho_pacote = path
        self.lic_lbl_pacote.setText(os.path.basename(path))
        self._lic_ordens_cache = None  # arquivo trocou, invalida cache

    def _lic_processar(self):
        if not self.lic_caminho_pacote:
            QMessageBox.warning(self, 'Aviso', 'Selecione o PDF das ordens do pacote.')
            return
        def trabalho(caminho_pacote, caminhos_relatorio):
            ordens, pos_para_ordem = ler_pacote_pdf(caminho_pacote)
            self._lic_stats_relatorio = None
            if caminhos_relatorio:
                linhas_rel = ler_relatorios_fluxos_pacote(caminhos_relatorio)
                self._lic_stats_relatorio = aplicar_relatorio_ao_grupo_lic(ordens, linhas_rel)
            return ordens, pos_para_ordem

        self._iniciar_trabalho_em_fundo(
            trabalho, (self.lic_caminho_pacote, list(self.lic_caminhos_relatorio)), {},
            botoes_desabilitar=[self.lic_btn_processar],
            label_status=self.lic_lbl_status,
            msg_rodando='Lendo PDF e classificando ordens…',
            on_sucesso=self._lic_concluido,
        )

    def _lic_concluido(self, resultado):
        ordens, pos_para_ordem = resultado
        self._lic_ordens_cache = ordens
        self._lic_pos_para_ordem_cache = pos_para_ordem
        # também deixa disponível pra aba Fluxo 4 reaproveitar (mesmo PDF)
        self.f4_ordens_cache = ordens
        self.f4_pos_para_ordem_cache = pos_para_ordem
        self.f4_caminho_pacote_lido = self.lic_caminho_pacote

        arvore = montar_arvore_grupo_lic(ordens)
        obras_pacote = obras_do_pacote(ordens)
        varias_obras = len(obras_pacote) > 1      # com 1 obra só, a árvore fica como antes (sem o nível "Obra")
        tree = self.lic_tree
        tree.blockSignals(True)
        tree.clear()
        AMARELO = QColor(NEON_AMBER)
        total_ordens = 0

        def item_marcavel(textos):
            it = QTreeWidgetItem(textos)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Checked)  # começa tudo marcado "a imprimir", igual o HTML
            return it

        def botao_pdf(texto, item_pai, nome_sugerido):
            b = QPushButton(texto)
            b.setMaximumHeight(24)
            b.setStyleSheet('padding: 2px 8px; font-size: 11px;')
            b.clicked.connect(lambda _=False, it=item_pai, n=nome_sugerido: self._lic_gerar_pdf_marcados(it, n))
            return b

        def montar_grupos(pai, ordens_sub, prefixo_nome):
            """Grupo LIC -> Tipo -> Espessura -> OF, dentro de "pai" (a obra, ou a raiz da árvore)."""
            nonlocal total_ordens
            for bloco in montar_arvore_grupo_lic(ordens_sub):
                item_grupo = item_marcavel([f"{bloco['grupo_lic']} ({bloco['total_ordens']})", '', ''])
                if bloco['sem_grupo_lic']:
                    item_grupo.setForeground(0, AMARELO)
                (pai.addChild(item_grupo) if pai is not None else tree.addTopLevelItem(item_grupo))
                tree.setItemWidget(item_grupo, 2, botao_pdf(
                    '📄 PDF deste grupo (marcados)', item_grupo, f"{prefixo_nome}{bloco['grupo_lic']}"))
                for c in bloco['classes']:
                    item_classe = item_marcavel([f"{c['classe']} ({c['total_ordens']})", '', ''])
                    item_grupo.addChild(item_classe)
                    tree.setItemWidget(item_classe, 2, botao_pdf(
                        '📄 PDF de todo o tipo (marcados)', item_classe, f"{prefixo_nome}{bloco['grupo_lic']}_{c['classe']}"))
                    for e in c['espessuras']:
                        item_esp = item_marcavel([e['rotulo'], f"{len(e['ordens'])} ordem(ns)", ''])
                        item_classe.addChild(item_esp)
                        tree.setItemWidget(item_esp, 2, botao_pdf(
                            '📄 PDF desta espessura (marcados)', item_esp,
                            f"{prefixo_nome}{bloco['grupo_lic']}_{c['classe']}_{e['rotulo']}"))
                        for of in e['ordens']:
                            o = ordens_sub[of]
                            detalhe = o.get('descricao', '')
                            if o.get('of_trecho'):
                                detalhe = f"{o['of_trecho']} · {detalhe}".rstrip(' ·')
                            if o.get('grupo_lic_origem') == 'relatório':
                                detalhe += ' · grupo pelo relatório'
                            item_of = item_marcavel([f'OF {of}', detalhe, ''])
                            item_of.setData(0, Qt.UserRole, of)
                            item_esp.addChild(item_of)
                            total_ordens += 1

        n_grupos = len(arvore)
        if varias_obras:
            # OBRA no topo (igual ao Fluxo 4): cada obra-trecho é um bloco com seus Grupos LIC, tipos e espessuras
            n_grupos = len({bl['grupo_lic'] for bl in arvore})
            for obra in obras_pacote:
                ordens_obra = {of: o for of, o in ordens.items() if obra_trecho_da_ordem(o) == obra}
                item_obra = item_marcavel([f"Obra {obra} ({len(ordens_obra)})", '', ''])
                tree.addTopLevelItem(item_obra)
                tree.setItemWidget(item_obra, 2, botao_pdf('📄 PDF desta obra (marcados)', item_obra, f"obra_{obra}"))
                montar_grupos(item_obra, ordens_obra, f"obra_{obra}_")
        else:
            montar_grupos(None, ordens, '')
        tree.expandToDepth(1 if varias_obras else 0)
        tree.blockSignals(False)
        self.lic_lbl_status.setText(f'✅ {total_ordens} ordem(ns) em {n_grupos} Grupo(s) LIC'
                                    + (f' · {len(obras_pacote)} obras ({", ".join(obras_pacote[:6])}'
                                       f'{" …" if len(obras_pacote) > 6 else ""})' if varias_obras else ''))
        st = getattr(self, '_lic_stats_relatorio', None)
        if st:
            self.lic_lbl_status.setText(
                self.lic_lbl_status.text() + f" · relatório: {st['achadas']} de {st['achadas'] + st['sem_relatorio']} ordem(ns) achadas"
                + (f", {st['sem_relatorio']} sem linha no relatório (ficam com a obra do PDF)" if st['sem_relatorio'] else '')
                + (f", {st['grupo_preenchido']} com Grupo LIC completado pelo relatório" if st['grupo_preenchido'] else ''))
        self.lic_chk_pdf_por_obra.setEnabled(varias_obras)
        self.lic_btn_exportar.setEnabled(bool(ordens))
        self.lic_btn_pdf_tudo.setEnabled(bool(ordens))
        self.lic_btn_definir_grupo.setEnabled(bool(ordens))

    def _lic_item_marcacao_mudou(self, item, coluna):
        """Marcar/desmarcar uma caixinha propaga pros filhos (igual o HTML:
        desmarcar o Tipo desmarca as espessuras e OFs dentro dele) — usada
        tanto na árvore do Grupo LIC quanto na do Fluxo 4."""
        if coluna != 0:
            return
        estado = item.checkState(0)
        arvore = item.treeWidget()
        arvore.blockSignals(True)
        self._lic_marcar_filhos(item, estado)
        arvore.blockSignals(False)

    def _lic_marcar_filhos(self, item, estado):
        for i in range(item.childCount()):
            filho = item.child(i)
            filho.setCheckState(0, estado)
            self._lic_marcar_filhos(filho, estado)

    def _lic_ofs_marcados_sob(self, item):
        """Varre a subárvore a partir de "item" e devolve as OFs (folhas)
        que estão com a caixinha marcada."""
        ofs = []
        of = item.data(0, Qt.UserRole)
        if of is not None:
            if item.checkState(0) == Qt.Checked:
                ofs.append(of)
            return ofs
        for i in range(item.childCount()):
            ofs.extend(self._lic_ofs_marcados_sob(item.child(i)))
        return ofs

    def _lic_gerar_pdf_marcados(self, item_pai, nome_sugerido):
        ofs = self._lic_ofs_marcados_sob(item_pai)
        self._lic_gerar_pdf_ofs(ofs, nome_sugerido)

    def _lic_por_obra_ativo(self):
        return bool(self.lic_chk_pdf_por_obra.isChecked() and self.lic_chk_pdf_por_obra.isEnabled())

    def _lic_confirmar_impressao(self, conf, por_obra):
        """Diálogo de CONFERÊNCIA antes de gerar. Com PROBLEMAS (ordem sem página, OF repetida…) o padrão é cancelar."""
        caixa = QMessageBox(self)
        caixa.setWindowTitle('Conferir antes de gerar o PDF')
        caixa.setIcon(QMessageBox.Critical if conf['erros'] else (QMessageBox.Warning if conf['avisos'] else QMessageBox.Question))
        caixa.setText(f"{conf['total_ordens']} ordem(ns) · {conf['total_paginas']} página(s)"
                      + (f" · {len(conf['por_obra'])} obra(s)" if len(conf['por_obra']) > 1 else '')
                      + ('\n\n✖ Há PROBLEMAS — veja os detalhes.' if conf['erros'] else
                         ('\n\n⚠ Há pontos de atenção — veja os detalhes.' if conf['avisos'] else '\n\nTudo certo na conferência.')))
        caixa.setDetailedText(texto_conferencia_lic(conf, por_obra))
        if conf['erros'] or conf['avisos']:
            caixa.setInformativeText('Gerar mesmo assim?')
        else:
            caixa.setInformativeText('Gerar o PDF?')
        b_ok = caixa.addButton('Gerar mesmo assim' if (conf['erros'] or conf['avisos']) else 'Gerar',
                               QMessageBox.AcceptRole)
        b_cancel = caixa.addButton('Cancelar', QMessageBox.RejectRole)
        caixa.setDefaultButton(b_cancel if conf['erros'] else b_ok)
        # com a lista aberta por padrão fica mais difícil de "passar batido"
        for b in caixa.buttons():
            if caixa.buttonRole(b) == QMessageBox.ActionRole:
                b.click()
        caixa.exec_()
        return caixa.clickedButton() is b_ok

    def _lic_gerar_pdf_ofs(self, ofs, nome_sugerido):
        if not self._lic_ordens_cache or not self.lic_caminho_pacote:
            QMessageBox.warning(self, 'Aviso', 'Processa o Grupo LIC primeiro.')
            return
        if not ofs:
            QMessageBox.warning(self, 'Aviso', 'Não tem nenhuma ordem marcada nesse grupo pra gerar PDF.')
            return
        obra_por_ordem = {of: obra_trecho_da_ordem(self._lic_ordens_cache.get(of, {})) for of in ofs}
        por_obra = self._lic_por_obra_ativo() and len(set(obra_por_ordem.values())) > 1
        conf = conferir_selecao_lic(self._lic_ordens_cache, ofs, obra_por_ordem,
                                    relatorio_usado=bool(getattr(self, '_lic_stats_relatorio', None)),
                                    stats_relatorio=getattr(self, '_lic_stats_relatorio', None), por_obra=por_obra)
        if not self._lic_confirmar_impressao(conf, por_obra):
            return
        nome_arquivo = RE_NOME_ARQUIVO_INVALIDO.sub('_', nome_sugerido).strip('_') + '.pdf'
        caminho_saida, _ = QFileDialog.getSaveFileName(self, 'Salvar PDF', nome_arquivo, 'PDF (*.pdf)')
        if not caminho_saida:
            return
        self._iniciar_trabalho_em_fundo(
            gerar_pdfs_lic_conferidos,
            (self.lic_caminho_pacote, self._lic_ordens_cache, ofs, obra_por_ordem, caminho_saida),
            {'por_obra': por_obra, 'salvar_lista': self.lic_chk_lista_conf.isChecked()},
            botoes_desabilitar=[self.lic_btn_processar, self.lic_btn_exportar, self.lic_btn_pdf_tudo],
            label_status=self.lic_lbl_status,
            msg_rodando=f'Montando e conferindo o PDF ({len(ofs)} ordem(ns))…',
            on_sucesso=self._lic_pdfs_concluidos,
        )

    def _lic_pdfs_concluidos(self, saidas):
        total = sum(x['paginas'] for x in saidas)
        todos_ok = all(x['verificacao']['ok'] for x in saidas)
        linhas = []
        for x in saidas:
            rot = f"obra {x['obra']}: " if x['obra'] is not None else ''
            linhas.append(f"• {rot}{os.path.basename(x['caminho'])} — {x['ordens']} ordem(ns), {x['paginas']} págs\n"
                          f"    {texto_verificacao(x['verificacao'])}"
                          + (f"\n    lista: {os.path.basename(x['lista'])}" if x.get('lista') else ''))
        msg = (('✅ ' if todos_ok else '⚠ CONFERÊNCIA FALHOU — NÃO IMPRIMA sem olhar: ')
               + f"{len(saidas)} PDF(s), {total} página(s) no total")
        self.lic_lbl_status.setText(msg)
        if todos_ok:
            QMessageBox.information(self, 'Concluído', msg + '\n\n' + '\n'.join(linhas))
        else:
            QMessageBox.critical(self, 'Conferência falhou', msg + '\n\n' + '\n'.join(linhas))

    def _lic_pdf_de_tudo(self):
        if not self._lic_ordens_cache:
            QMessageBox.warning(self, 'Aviso', 'Processa o Grupo LIC primeiro.')
            return
        ofs_marcadas = []
        for i in range(self.lic_tree.topLevelItemCount()):
            ofs_marcadas.extend(self._lic_ofs_marcados_sob(self.lic_tree.topLevelItem(i)))
        # a árvore já vem na ordem certa (por posição/marca do desenho) —
        # só tira duplicata, sem reordenar por número de OF
        vistas, ofs_sem_repetir = set(), []
        for of in ofs_marcadas:
            if of not in vistas:
                vistas.add(of)
                ofs_sem_repetir.append(of)
        self._lic_gerar_pdf_ofs(ofs_sem_repetir, 'GRUPO_LIC_MARCADOS')

    def _lic_definir_grupo_lic_selecionado(self):
        item = self.lic_tree.currentItem()
        if not item or not item.text(0).startswith('OF '):
            QMessageBox.warning(self, 'Aviso', 'Selecione uma OF na árvore (dentro de algum grupo "SEM GRUPO '
                                                'LIC") primeiro — clica na linha da OF, não no tipo/espessura.')
            return
        of = item.text(0).replace('OF ', '').strip()
        o = self._lic_ordens_cache.get(of) if self._lic_ordens_cache else None
        if not o:
            return
        chave = _chave_grupo_lic(o)
        if not chave:
            QMessageBox.warning(self, 'Aviso', 'Essa ordem não tem um código de ITEM pra lembrar (ITEM vazio).')
            return
        valor, ok = QInputDialog.getText(self, 'Definir Grupo LIC',
                                          f'Qual o Grupo LIC certo pro item "{chave}"?\n'
                                          f'(vai valer sempre que esse item aparecer, em qualquer pacote)')
        if not ok or not valor.strip():
            return
        valor = valor.strip()
        mapa = carregar_mapa_grupo_lic()
        mapa[chave] = valor
        salvar_mapa_grupo_lic(mapa)
        # reaplica na sessão atual (sem precisar reler o PDF) pra qualquer
        # outra ordem que tenha o mesmo item e também esteja sem Grupo LIC
        for o2 in self._lic_ordens_cache.values():
            if not o2.get('grupo_lic') and _chave_grupo_lic(o2) == chave:
                o2['grupo_lic'] = valor
        self._lic_concluido((self._lic_ordens_cache, self._lic_pos_para_ordem_cache))
        QMessageBox.information(self, 'Salvo', f'Item "{chave}" -> Grupo LIC "{valor}", lembrado pra sempre.')

    def _lic_exportar_por_classe(self):
        if not self._lic_ordens_cache:
            QMessageBox.warning(self, 'Aviso', 'Processa o Grupo LIC primeiro.')
            return
        pasta = QFileDialog.getExistingDirectory(self, 'Escolher pasta pra salvar os PDFs por classe')
        if not pasta:
            return
        self._iniciar_trabalho_em_fundo(
            exportar_pdfs_por_classe,
            (self.lic_caminho_pacote, self._lic_ordens_cache, pasta),
            {'por_obra': bool(self.lic_chk_pdf_por_obra.isChecked() and self.lic_chk_pdf_por_obra.isEnabled())},
            botoes_desabilitar=[self.lic_btn_processar, self.lic_btn_exportar, self.lic_btn_pdf_tudo],
            label_status=self.lic_lbl_status,
            msg_rodando='Montando um PDF por classe…',
            on_sucesso=self._lic_exportado,
        )

    def _lic_exportado(self, resultado):
        total_pdfs = len(resultado)
        total_paginas = sum(r['paginas'] for r in resultado)
        todos_ok = all(r.get('verificacao', {}).get('ok', True) for r in resultado)
        msg = (('✅ ' if todos_ok else '⚠ CONFERÊNCIA FALHOU em algum PDF — NÃO IMPRIMA sem olhar: ')
               + f'{total_pdfs} PDF(s) gerado(s) — {total_paginas} página(s) no total')
        self.lic_lbl_status.setText(msg)
        linhas = '\n'.join(f"• {r['classe']}{' — obra ' + r['obra'] if r.get('obra') else ''}: {r['ordens']} ordem(ns), {r['paginas']} página(s) "
                            f"→ {os.path.basename(r['arquivo'])}"
                            + (f"\n    {texto_verificacao(r['verificacao'])}" if r.get('verificacao') else '')
                            for r in resultado)
        (QMessageBox.information if todos_ok else QMessageBox.critical)(self, 'Exportação concluída', f'{msg}\n\n{linhas}')

    # ── Aba Fluxo 4 ──
    def _build_fluxo4_tab(self, tab):
        v = QVBoxLayout(tab)

        gb1 = QGroupBox('1) PDF das Ordens do Pacote / Obra inteira')
        v1 = QVBoxLayout(gb1)
        h1 = QHBoxLayout()
        btn1 = QPushButton('📄 Escolher PDF do Pacote…')
        btn1.clicked.connect(self._f4_escolher_pacote)
        self.f4_lbl_pacote = QLabel('nenhum arquivo carregado (ou use o já lido na aba Grupo LIC)')
        h1.addWidget(btn1)
        h1.addWidget(self.f4_lbl_pacote, 1)
        v1.addLayout(h1)
        v1.addWidget(DropArea('⬇ arraste o PDF do pacote aqui', lambda paths: self._f4_definir_pacote(paths[0])))
        v.addWidget(gb1)

        gb2 = QGroupBox('2) Relatórios de fluxos (roteirização) — um por obra, pode carregar vários')
        v2 = QVBoxLayout(gb2)
        h2 = QHBoxLayout()
        btn2 = QPushButton('🔀 Adicionar Relatório(s) de Fluxos…')
        btn2.clicked.connect(self._f4_escolher_relatorio)
        btn2_limpar = QPushButton('Limpar')
        btn2_limpar.clicked.connect(self._f4_limpar_relatorios)
        self.f4_lbl_relatorio = QLabel('nenhum relatório carregado')
        self.f4_lbl_relatorio.setWordWrap(True)
        h2.addWidget(btn2)
        h2.addWidget(btn2_limpar)
        h2.addWidget(self.f4_lbl_relatorio, 1)
        h2.addWidget(QLabel('Fluxo alvo:'))
        self.f4_combo_alvo = QComboBox()
        self.f4_combo_alvo.addItems(['4', '1', '2', '3', '5', '6'])
        h2.addWidget(self.f4_combo_alvo)
        v2.addLayout(h2)
        v2.addWidget(DropArea('⬇ arraste o(s) relatório(s) de fluxos aqui (um por obra)', lambda paths: self._f4_definir_relatorios(paths)))
        v.addWidget(gb2)

        h = QHBoxLayout()
        self.f4_btn_processar = QPushButton('⚙️ Processar Fluxo: casar ordens do fluxo alvo')
        self.f4_btn_processar.setObjectName('btnAnalisar')
        self.f4_btn_processar.clicked.connect(self._f4_processar)
        h.addWidget(self.f4_btn_processar)
        v.addLayout(h)

        self.f4_lbl_status = QLabel('Aguardando arquivos...')
        v.addWidget(self.f4_lbl_status)

        self.f4_tree = QTreeWidget()
        self.f4_tree.setHeaderLabels(['OF / Situação', 'Detalhe'])
        self.f4_tree.setColumnWidth(0, 340)
        self.f4_tree.setMinimumHeight(420)
        self.f4_tree.itemChanged.connect(self._lic_item_marcacao_mudou)  # mesma cascata do Grupo LIC
        v.addWidget(self.f4_tree, 1)

        h3b = QHBoxLayout()
        btn_def_fluxo = QPushButton('🔀 Definir Fluxo da OF selecionada e lembrar pra sempre')
        btn_def_fluxo.clicked.connect(self._f4_definir_fluxo_selecionado)
        h3b.addWidget(btn_def_fluxo)
        btn_obs = QPushButton('📝 Observação da OF selecionada')
        btn_obs.clicked.connect(self._f4_definir_observacao_selecionada)
        h3b.addWidget(btn_obs)
        h3b.addStretch()
        v.addLayout(h3b)

        h3 = QHBoxLayout()
        self.f4_btn_gerar_pdf = QPushButton('🖨️ Gerar PDF do Fluxo')
        self.f4_btn_gerar_pdf.setObjectName('btnPrincipal')
        self.f4_btn_gerar_pdf.setEnabled(False)
        self.f4_btn_gerar_pdf.clicked.connect(self._f4_gerar_pdf)
        h3.addWidget(self.f4_btn_gerar_pdf)
        self.f4_chk_pdf_por_obra = QCheckBox('Gerar um PDF separado por obra')
        self.f4_chk_pdf_por_obra.setToolTip('só habilita quando o pacote tem mais de uma obra; cada obra vira um arquivo '
                                             '(nome_obra_2139-2-02.pdf…), na mesma sequência — desmarque a obra na árvore pra não levar')
        self.f4_chk_pdf_por_obra.setEnabled(False)
        h3.addWidget(self.f4_chk_pdf_por_obra)
        h3.addStretch()
        v.addLayout(h3)

        self.f4_caminho_pacote = None
        self.f4_caminhos_relatorio = []
        self.f4_ordens_cache = None
        self.f4_pos_para_ordem_cache = None
        self.f4_caminho_pacote_lido = None
        self.f4_ultimo_resultado = None

    def _f4_escolher_pacote(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar PDF do Pacote', '', 'PDF (*.pdf)')
        if not path:
            return
        self._f4_definir_pacote(path)

    def _f4_definir_pacote(self, path):
        self.f4_caminho_pacote = path
        self.f4_lbl_pacote.setText(os.path.basename(path))

    def _f4_escolher_relatorio(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Selecionar Relatório(s) de Fluxos (um por obra)', '',
                                                 'Excel (*.xlsx *.xlsm *.xlsb *.xls)')
        if paths:
            self._f4_definir_relatorios(paths)

    def _f4_definir_relatorios(self, paths):
        """Soma os relatórios escolhidos aos que já estavam (sem repetir o mesmo arquivo)."""
        lista = list(getattr(self, 'f4_caminhos_relatorio', []))
        for pth in paths:
            if pth not in lista:
                lista.append(pth)
        self.f4_caminhos_relatorio = lista
        self.f4_lbl_relatorio.setText(f"{len(lista)} relatório(s): " + ' · '.join(os.path.basename(x) for x in lista))

    def _f4_definir_relatorio(self, path):              # compatibilidade
        self._f4_definir_relatorios([path])

    def _f4_limpar_relatorios(self):
        self.f4_caminhos_relatorio = []
        self.f4_lbl_relatorio.setText('nenhum relatório carregado')

    def _f4_processar(self):
        caminho_pacote = self.f4_caminho_pacote or self.lic_caminho_pacote
        if not caminho_pacote:
            QMessageBox.warning(self, 'Aviso', 'Selecione o PDF das ordens do pacote (campo 1).')
            return
        if not self.f4_caminhos_relatorio:
            QMessageBox.warning(self, 'Aviso', 'Selecione o(s) relatório(s) de fluxos (campo 2).')
            return
        alvo = self.f4_combo_alvo.currentText()

        def trabalho(caminho_pacote, caminho_relatorio, alvo):
            # reaproveita a leitura do PDF se já foi lida (mesmo arquivo, igual o HTML original)
            if self.f4_ordens_cache is not None and self.f4_caminho_pacote_lido == caminho_pacote:
                ordens, pos_para_ordem = self.f4_ordens_cache, self.f4_pos_para_ordem_cache
            else:
                ordens, pos_para_ordem = ler_pacote_pdf(caminho_pacote)
            obra_pacote = next(iter(ordens.values()))['obra'] if ordens else ''
            linhas_rel = ler_relatorios_fluxos_pacote(caminho_relatorio)
            mapa_fluxo_posicao = carregar_mapa_fluxo_posicao()
            resultado = casar_fluxo_do_pacote(ordens, pos_para_ordem, obra_pacote, linhas_rel, alvo,
                                               mapa_fluxo_posicao=mapa_fluxo_posicao)
            return {'ordens': ordens, 'resultado': resultado, 'alvo': alvo, 'caminho_pacote': caminho_pacote}

        self._iniciar_trabalho_em_fundo(
            trabalho, (caminho_pacote, list(self.f4_caminhos_relatorio), alvo), {},
            botoes_desabilitar=[self.f4_btn_processar, self.f4_btn_gerar_pdf],
            label_status=self.f4_lbl_status,
            msg_rodando='Lendo PDF, relatório de fluxos e casando ordens…',
            on_sucesso=self._f4_concluido,
        )

    def _f4_concluido(self, r):
        ordens, resultado, alvo = r['ordens'], r['resultado'], r['alvo']
        self.f4_ultimo_resultado = r
        observacoes = carregar_observacoes_pacote()
        tree = self.f4_tree
        tree.blockSignals(True)
        tree.clear()

        info_ordem = resultado.get('info_por_ordem', {})

        def detalhe_of(of, o):
            chave = _chave_grupo_lic(o)
            nota = observacoes.get(chave) if chave else None
            base = o.get('descricao', '')
            inf = info_ordem.get(of)
            if inf and inf.get('obra'):
                base = (f"obra {inf['obra']}" + (f" · {inf['setor']}" if inf.get('setor') else '')
                        + (f" · pos. {inf['posicao']}" if inf.get('posicao') else '') + ' · ' + base).rstrip(' ·')
            return f'{base} · 📝 {nota}' if nota else base

        def item_marcavel(textos):
            it = QTreeWidgetItem(textos)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Checked)  # começa tudo marcado "a imprimir", igual o HTML
            return it

        obra_por_ordem = resultado.get('obra_por_ordem', {})
        varias_obras = len({obra_por_ordem.get(of) for of in resultado['ordens_do_fluxo']}) > 1
        item_ok = item_marcavel([f"Ordens do Fluxo {alvo} ({len(resultado['ordens_do_fluxo'])}) "
                                  f"— na sequência de impressão ({'por obra e espessura' if varias_obras else 'por espessura'})", ''])
        espessura_atual = object()  # sentinela — garante que o 1º grupo sempre abre
        obra_atual = object()
        item_esp = item_obra = None
        for of in resultado['ordens_do_fluxo']:
            o = ordens.get(of, {})
            esp = o.get('espessura') or '—'
            if varias_obras and obra_por_ordem.get(of) != obra_atual:     # obra nova: abre o bloco dela
                obra_atual = obra_por_ordem.get(of)
                espessura_atual = object()
                n_obra = sum(1 for x in resultado['ordens_do_fluxo'] if obra_por_ordem.get(x) == obra_atual)
                item_obra = item_marcavel([f"Obra {obra_atual or '—'} ({n_obra})", ''])
                item_ok.addChild(item_obra)
            if esp != espessura_atual:
                espessura_atual = esp
                item_esp = item_marcavel([rotulo_espessura(o.get('espessura')), ''])
                (item_obra if varias_obras else item_ok).addChild(item_esp)
            item_of = item_marcavel([f'OF {of}', detalhe_of(of, o)])
            item_of.setData(0, Qt.UserRole, of)
            item_esp.addChild(item_of)
        tree.addTopLevelItem(item_ok)

        # barra/pilarete/peça padrão NÃO aparecem aqui de propósito — essa
        # aba é só Fluxo 4; essas peças ficam só na árvore do Grupo LIC.
        # (a exclusão continua acontecendo por trás: elas nunca entram em
        # "ordens_do_fluxo", só não mostramos uma seção própria pra elas
        # nessa tela)

        if resultado['sem_info_no_relatorio']:
            AMARELO = QColor(NEON_AMBER)
            item_semi = QTreeWidgetItem(
                [f"⚠️ Sem nenhuma posição no relatório — peça sem CAM ainda "
                 f"({len(resultado['sem_info_no_relatorio'])})", ''])
            item_semi.setForeground(0, AMARELO)
            for d in resultado['sem_info_no_relatorio']:
                of, o = d['of'], ordens.get(d['of'], {})
                # mostra o NOME DA POSIÇÃO junto da OF, pra dar pra reconhecer a peça
                item_semi.addChild(QTreeWidgetItem([f"OF {of}", f"posições: {', '.join(d['posicoes']) or '—'} · "
                                                                  f"{detalhe_of(of, o)}"]))
            tree.addTopLevelItem(item_semi)

        if resultado['sem_ordem']:
            item_so = QTreeWidgetItem([
                f"⚠️ Posições do RELATÓRIO que não têm Ordem impressa neste PDF ({len(resultado['sem_ordem'])})",
                'nenhuma ação necessária aqui — não afeta as ordens acima; provavelmente a Ordem dessa '
                'posição não foi incluída neste PDF do pacote'])
            item_so.setForeground(0, QColor(NEON_AMBER))
            for linha in resultado['sem_ordem'][:200]:
                material = linha.get('material') or '—'
                esp = linha.get('espessura')
                esp_txt = rotulo_espessura(esp) if esp else '—'
                item_so.addChild(QTreeWidgetItem([
                    f"Posição {linha.get('posicao', '—')}",
                    f"Obra-Trecho do relatório: {linha.get('of', '—')} (não é o nº da Ordem) · "
                    f"material: {material} · espessura: {esp_txt}"]))
            tree.addTopLevelItem(item_so)

        tree.expandToDepth(2 if varias_obras else 1)
        tree.blockSignals(False)
        self.f4_chk_pdf_por_obra.setEnabled(varias_obras)
        self.f4_lbl_status.setText(
            f"✅ {len(resultado['ordens_do_fluxo'])} ordem(ns) no Fluxo {alvo}"
            + (f" em {len({obra_por_ordem.get(x) for x in resultado['ordens_do_fluxo']})} obras" if varias_obras else '') + f" · "
            f"{len(resultado['sem_info_no_relatorio'])} sem info no relatório · "
            f"{len(resultado['sem_ordem'])} posição(ões) sem ordem")
        self.f4_btn_gerar_pdf.setEnabled(bool(resultado['ordens_do_fluxo']))

    def _f4_of_selecionada(self):
        """Acha a OF selecionada na árvore (funciona clicando em qualquer
        linha "OF ####", em qualquer seção) e devolve (of, objeto_ordem)."""
        item = self.f4_tree.currentItem()
        if not item or not item.text(0).startswith('OF '):
            return None, None
        of = item.text(0).replace('OF ', '').strip()
        ordens = self.f4_ultimo_resultado['ordens'] if self.f4_ultimo_resultado else {}
        return of, ordens.get(of)

    def _f4_definir_fluxo_selecionado(self):
        of, o = self._f4_of_selecionada()
        if not of:
            QMessageBox.warning(self, 'Aviso', 'Selecione uma OF na árvore — de preferência dentro de '
                                                '"Sem nenhuma posição no relatório" — primeiro.')
            return
        posicoes = sorted(o.get('posicoes', ())) if o else []
        if not posicoes:
            QMessageBox.warning(self, 'Aviso', 'Essa ordem não tem nenhuma posição pra lembrar o fluxo.')
            return
        alvo_atual = self.f4_combo_alvo.currentText()
        fluxo, ok = QInputDialog.getText(self, 'Definir Fluxo',
                                          f'Posições dessa OF: {", ".join(posicoes)}\n\n'
                                          f'Qual o número do Fluxo pra elas (ex.: {alvo_atual})? '
                                          f'Vale sempre que essa posição aparecer de novo, em qualquer pacote.')
        if not ok or not fluxo.strip():
            return
        fluxo = numero_fluxo(fluxo.strip()) or fluxo.strip()
        mapa = carregar_mapa_fluxo_posicao()
        for pos in posicoes:
            mapa[pos] = fluxo
        salvar_mapa_fluxo_posicao(mapa)
        QMessageBox.information(self, 'Salvo', f'Posições {", ".join(posicoes)} -> Fluxo {fluxo}, lembrado '
                                                 f'pra sempre. Processa de novo pra aplicar.')

    def _f4_definir_observacao_selecionada(self):
        of, o = self._f4_of_selecionada()
        if not of:
            QMessageBox.warning(self, 'Aviso', 'Selecione uma OF na árvore primeiro.')
            return
        chave = _chave_grupo_lic(o) if o else None
        if not chave:
            QMessageBox.warning(self, 'Aviso', 'Essa ordem não tem um código de ITEM pra lembrar a observação.')
            return
        observacoes = carregar_observacoes_pacote()
        atual = observacoes.get(chave, '')
        texto, ok = QInputDialog.getText(self, 'Observação', f'Observação pro item "{chave}" '
                                                               f'(vale pra sempre que ele aparecer):',
                                          text=atual)
        if not ok:
            return
        texto = texto.strip()
        if texto:
            observacoes[chave] = texto
        else:
            observacoes.pop(chave, None)
        salvar_observacoes_pacote(observacoes)
        self._f4_concluido(self.f4_ultimo_resultado)

    def _f4_ofs_marcadas(self):
        """Varre a seção "Ordens do Fluxo X" (1º item da árvore) e devolve
        só as OFs com a caixinha marcada."""
        if self.f4_tree.topLevelItemCount() == 0:
            return []
        return self._lic_ofs_marcados_sob(self.f4_tree.topLevelItem(0))

    def _f4_gerar_pdf(self):
        r = self.f4_ultimo_resultado
        if not r or not r['resultado']['ordens_do_fluxo']:
            QMessageBox.warning(self, 'Aviso', 'Processa o fluxo primeiro — não há ordens pra gerar PDF.')
            return
        ofs_marcadas = self._f4_ofs_marcadas()
        if not ofs_marcadas:
            QMessageBox.warning(self, 'Aviso', 'Nenhuma ordem marcada na árvore — desmarque menos coisa :)')
            return
        pasta = os.path.dirname(r['caminho_pacote'])
        nome_sugerido = f"fluxo_{r['alvo']}_{date_tag()}.pdf"
        caminho_saida, _ = QFileDialog.getSaveFileName(self, 'Salvar PDF do Fluxo',
                                                         os.path.join(pasta, nome_sugerido), 'PDF (*.pdf)')
        if not caminho_saida:
            return
        if self.f4_chk_pdf_por_obra.isChecked() and self.f4_chk_pdf_por_obra.isEnabled():
            self._iniciar_trabalho_em_fundo(
                gerar_pdfs_fluxo_por_obra,
                (r['caminho_pacote'], r['ordens'], ofs_marcadas, r['resultado'].get('obra_por_ordem', {}), caminho_saida),
                {},
                botoes_desabilitar=[self.f4_btn_processar, self.f4_btn_gerar_pdf],
                label_status=self.f4_lbl_status,
                msg_rodando='Montando os PDFs por obra…',
                on_sucesso=self._f4_pdfs_por_obra_concluidos,
            )
            return
        self._iniciar_trabalho_em_fundo(
            gerar_pdf_fluxo,
            (r['caminho_pacote'], r['ordens'], ofs_marcadas, caminho_saida),
            {},
            botoes_desabilitar=[self.f4_btn_processar, self.f4_btn_gerar_pdf],
            label_status=self.f4_lbl_status,
            msg_rodando='Montando o PDF do fluxo…',
            on_sucesso=lambda total: self._f4_pdf_concluido(total, caminho_saida),
        )

    def _f4_pdfs_por_obra_concluidos(self, saidas):
        total = sum(s['paginas'] for s in saidas)
        msg = (f"✅ {len(saidas)} PDFs do fluxo (um por obra): {total} página(s) no total — "
               + ' · '.join(f"{s['obra']}: {os.path.basename(s['caminho'])} ({s['paginas']} págs)" for s in saidas))
        self.f4_lbl_status.setText(msg)
        QMessageBox.information(self, 'Concluído', msg)

    def _f4_pdf_concluido(self, total_paginas, caminho_saida):
        msg = f'✅ PDF do fluxo gerado: {total_paginas} página(s) — {os.path.basename(caminho_saida)}'
        self.f4_lbl_status.setText(msg)
        QMessageBox.information(self, 'Concluído', msg)

    def an_adicionar_dbfs(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Selecionar DBF(s)', '',
            'Suportados (*.xlsx *.xlsm *.xls *.xlsb *.csv *.txt *.tsv *.dbf);;Todos (*)')
        self._an_adicionar_dbf_paths(paths)

    def _an_adicionar_dbf_paths(self, paths):
        for p in paths:
            if p not in self.analise_dbf_paths:
                self.analise_dbf_paths.append(p)
        self.an_lst_dbf.clear()
        self.an_lst_dbf.addItems([os.path.basename(p) for p in self.analise_dbf_paths])

    def an_limpar_dbfs(self):
        self.analise_dbf_paths = []
        self.an_lst_dbf.clear()

    def an_carregar_focco(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Selecionar export do FOCCO', '',
            'Suportados (*.xlsx *.xlsm *.xls *.xlsb *.csv *.txt *.html *.htm);;Todos (*)')
        if not path:
            return
        self._an_definir_focco(path)

    def _an_definir_focco(self, path):
        self.analise_focco_path = path
        self.an_lbl_focco.setText(f'{os.path.basename(path)}')

    def an_analisar(self):
        if not self.analise_dbf_paths:
            QMessageBox.warning(self, 'Aviso', 'Adicione ao menos uma DBF.')
            return
        if not self.analise_focco_path:
            QMessageBox.warning(self, 'Aviso', 'Carregue o export do FOCCO.')
            return
        self._iniciar_trabalho_em_fundo(
            _analisar_dbf_focco, (self.analise_dbf_paths, self.analise_focco_path), {},
            botoes_desabilitar=[self.an_btn_analisar, self.an_btn_exportar],
            label_status=self.an_lbl_resumo,
            msg_rodando='Analisando…',
            on_sucesso=self._an_analise_concluida,
        )

    def _an_analise_concluida(self, resultado):
        det_data, grp_data = resultado['det_data'], resultado['grp_data']
        of_trecho = resultado['of_trecho']
        self.analise_det_data = det_data
        self.analise_grp_data = grp_data
        self.analise_dbf_rows = resultado['dbf_rows']
        self.analise_of_trecho = of_trecho
        if not self.an_txt_nome.text().strip():
            self.an_txt_nome.setText(f'Validação-Peso_OF-{of_trecho or "trecho"}_{date_tag()}')

        tot_dbf = sum(r['pesoDBF'] for r in det_data)
        tot_focco = sum(r['pesoFOCCO'] for r in det_data)
        total_delta = tot_focco - tot_dbf
        divergentes = sum(1 for r in det_data if abs(r['pct']) > 1 and abs(r['delta']) > 0.001)
        self.an_lbl_resumo.setText(
            f"OF/Trecho: {of_trecho or '—'} · Peso DBF: {tot_dbf:,.2f} kg · Peso FOCCO: {tot_focco:,.2f} kg · "
            f"Delta: {total_delta:+.3f} kg · {divergentes} marca(s) com >1% divergência")

        self._an_render_grupo()
        self._an_render_detalhe()
        self.an_btn_exportar.setEnabled(True)

    def _an_render_grupo(self):
        cols = ['Grupo LIC', 'Qtd Marcas', 'Peso DBF (kg)', 'Peso FOCCO (kg)', 'Delta (kg)', 'Delta %', 'Status']
        self.an_tbl_grupo.clear()
        self.an_tbl_grupo.setColumnCount(len(cols))
        self.an_tbl_grupo.setHorizontalHeaderLabels(cols)
        self.an_tbl_grupo.setRowCount(len(self.analise_grp_data))
        for i, g in enumerate(self.analise_grp_data):
            st = get_status(g['delta'], g['pct'])
            vals = [g['grupo'], str(g['marcas']), f"{g['pesoDBF']:.3f}", f"{g['pesoFOCCO']:.3f}",
                    f"{g['delta']:+.3f}", f"{g['pct']:+.2f}%", st['label']]
            for j, v in enumerate(vals):
                self.an_tbl_grupo.setItem(i, j, QTableWidgetItem(v))
        self.an_tbl_grupo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _an_render_detalhe(self):
        cols = ['Marca', 'Grupo LIC', 'Qtd DBF', 'Peso DBF (kg)', 'Peso FOCCO (kg)', 'Delta (kg)', 'Delta %', 'Status']
        self.an_tbl_detalhe.clear()
        self.an_tbl_detalhe.setColumnCount(len(cols))
        self.an_tbl_detalhe.setHorizontalHeaderLabels(cols)
        self.an_tbl_detalhe.setRowCount(len(self.analise_det_data))
        for i, r in enumerate(self.analise_det_data):
            st = get_status(r['delta'], r['pct'])
            status_label = '⚠ Só DBF' if r['soloDBF'] else ('⚠ Só FOCCO' if r['soloFOCCO'] else st['label'])
            vals = [r['marca'], r['grupo'],
                    f"{r['qtd']:.0f}" if r['qtd'] > 0 else '—',
                    f"{r['pesoDBF']:.3f}" if r['pesoDBF'] > 0 else '—',
                    f"{r['pesoFOCCO']:.3f}" if r['pesoFOCCO'] > 0 else '—',
                    '—' if (r['soloDBF'] or r['soloFOCCO']) else f"{r['delta']:+.3f}",
                    '—' if (r['soloDBF'] or r['soloFOCCO']) else f"{r['pct']:+.2f}%",
                    status_label]
            for j, v in enumerate(vals):
                self.an_tbl_detalhe.setItem(i, j, QTableWidgetItem(v))
        self.an_tbl_detalhe.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

    def an_exportar(self):
        nome_base = self.an_txt_nome.text().strip() or f'Validação-Peso_{date_tag()}'
        caminho_saida, _ = QFileDialog.getSaveFileName(self, 'Salvar Análise', nome_base + '.xlsx', 'Excel (*.xlsx)')
        if not caminho_saida:
            return
        try:
            exportar_analise_excel(caminho_saida, nome_base, self.analise_det_data, self.analise_grp_data,
                                    self.analise_dbf_rows, self.analise_of_trecho)
            QMessageBox.information(self, 'Concluído', f'✅ {os.path.basename(caminho_saida)} gerado.')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', str(e))

    # ── DBFs (aba Agrupador) ──
    def _atualizar_contador_obras(self):
        obras = [o for o in self.txt_obras.toPlainText().splitlines() if o.strip()]
        if not obras:
            self.lbl_contador_obras.setText('nenhuma obra digitada')
        elif len(obras) == 1:
            self.lbl_contador_obras.setText('1 obra digitada')
        else:
            self.lbl_contador_obras.setText(f'{len(obras)} obras digitadas')

    def _escolher_raiz_obras(self):
        """As pastas raiz agora são fixas no sistema — o botão só confere o acesso de novo."""
        self._verificar_raizes()

    def _verificar_raizes(self, avisar=True):
        """Confere se ESTE PC enxerga as pastas raiz fixas. Se faltar alguma, avisa qual e o que precisa."""
        info = verificar_raizes_fixas()
        self.raizes_ok = [r['achado'] for r in info if r['ok']]
        self.txt_raiz_obras.setPlainText('\n'.join(r['achado'] for r in info))
        faltam = [r for r in info if not r['ok']]
        if not faltam:
            self.lbl_raiz.setText(f'✓ As {len(info)} pastas raiz fixas estão acessíveis neste PC')
        else:
            self.lbl_raiz.setText(f'✕ Este PC não acessa {len(faltam)} de {len(info)} pasta(s) raiz: '
                                  + ', '.join(r['nome'] for r in faltam))
            if avisar:
                texto = ('O sistema precisa destas pastas para achar os DBFs das obras, '
                         'e este computador não está conseguindo abrir:\n\n')
                for r in faltam:
                    texto += f'• {r["nome"]}\n   {r["caminho"]}\n   Precisa de: {r["precisa"]}.\n\n'
                texto += ('Peça para a TI liberar esse acesso neste PC e depois clique em "Verificar acesso".'
                          + ('\n\nEnquanto isso, a busca usa só a(s) pasta(s) que estão acessíveis.' if self.raizes_ok else ''))
                QMessageBox.warning(self, 'Pastas raiz das obras não encontradas neste PC', texto)
        return info

    def _testar_pasta_raiz(self):
        raizes = [r['achado'] for r in self._verificar_raizes(avisar=False)]
        texto_completo = ''
        for raiz in raizes:
            linhas = diagnosticar_pasta_raiz(raiz.strip())
            texto_completo += '\n'.join(linhas) + '\n\n' + ('─' * 60) + '\n\n'
        caixa = QMessageBox(self)
        caixa.setWindowTitle('O que o app está vendo nessa(s) pasta(s)')
        caixa.setText('Resultado do teste (rolagem pra ver tudo):')
        caixa.setDetailedText(texto_completo)
        caixa.setIcon(QMessageBox.Information)
        caixa.exec_()

    def buscar_dbfs_por_obra_click(self):
        obras = [o for o in self.txt_obras.toPlainText().splitlines() if o.strip()]
        info = self._verificar_raizes(avisar=False)
        raizes_validas = [r['achado'] for r in info if r['ok']]
        if not raizes_validas:
            self._verificar_raizes(avisar=True)
            return
        if not obras:
            QMessageBox.warning(self, 'Aviso', 'Digite ao menos uma obra (uma por linha).')
            return
        busca_completa = self.chk_busca_completa.isChecked()
        self._iniciar_trabalho_em_fundo(
            buscar_dbfs_por_obra, (raizes_validas, obras), {'busca_completa': busca_completa},
            botoes_desabilitar=[self.btn_buscar_obras, self.btn_vis, self.btn_gerar],
            label_status=self.lbl_status,
            msg_rodando=f'Procurando {len(obras)} obra(s) em {len(raizes_validas)} pasta(s)…',
            on_sucesso=self._busca_obras_concluida,
        )

    def _busca_obras_concluida(self, resultado):
        encontrados, nao_achadas = resultado
        if encontrados:
            self._adicionar_dbf_paths(encontrados)
        if nao_achadas:
            dialogo = DialogoObrasNaoAchadas(nao_achadas, self._adicionar_dbf_paths, self)
            dialogo.exec_()
        elif not encontrados:
            self.lbl_status.setText('Nenhum arquivo novo encontrado (talvez já estejam na lista).')

    def adicionar_dbfs(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Selecionar DBFs', '',
            'Suportados (*.xlsx *.xlsm *.xls *.xlsb *.csv *.txt *.tsv *.dbf);;Todos (*)')
        self._adicionar_dbf_paths(paths)

    def _adicionar_dbf_paths(self, paths):
        paths = [p for p in paths if not any(e['path'] == p for e in self.dbf_entries)]
        if not paths:
            return
        self._iniciar_trabalho_em_fundo(
            _ler_dbfs, (paths,), {},
            botoes_desabilitar=[self.btn_vis, self.btn_gerar],
            label_status=self.lbl_status,
            msg_rodando=f'Lendo {len(paths)} arquivo(s)…',
            on_sucesso=self._dbfs_lidas,
        )

    def _dbfs_lidas(self, novas_entries):
        self.dbf_entries.extend(novas_entries)
        self._render_dbf_list()
        self.lbl_status.setText(f'{len(novas_entries)} arquivo(s) processado(s).')

    def limpar_dbfs(self):
        self.dbf_entries = []
        self._render_dbf_list()

    def _render_dbf_list(self):
        self.lst_dbf.clear()
        for e in self.dbf_entries:
            icone = '✓' if e['status'] == 'ok' else '✕'
            item = QListWidgetItem(f"{icone} {e['nome']} — {e['msg']}")
            self.lst_dbf.addItem(item)

    # ── Base ──
    def carregar_base(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Selecionar Base', '',
            'Excel / Todos suportados (*.xlsx *.xlsm *.xlsb *.xls);;Excel (*.xlsx *.xlsm);;Todos (*)')
        if not path:
            return
        self._processar_base(path)

    def _caminho_digitado_base(self):
        caminho = self.lbl_base.text().strip().strip('"')
        if caminho and os.path.isfile(caminho) and caminho != getattr(self, 'base_path', None):
            self._processar_base(caminho)

    def _carregar_base_fixa(self):
        """Carrega a Base fixa (revisão mais nova da pasta base_fixa, ou a apontada em base_fixa.txt)."""
        cam = achar_base_fixa()
        self.base_fixa_path = cam
        if not cam:
            return False
        self._processar_base(cam)
        return self.base_path == cam

    def _processar_base(self, path):
        self._processar_base_impl(path)
        if self.base_path and self.base_fixa_path and os.path.normcase(os.path.abspath(path)) == \
                os.path.normcase(os.path.abspath(self.base_fixa_path)):
            txt = self.lbl_base.text()
            self.lbl_base.setText('BASE FIXA · ' + (txt[2:] if txt.startswith('✓ ') else txt))

    def _processar_base_impl(self, path):
        ext = ext_of(path)
        if ext == 'xls':
            self.base_path = None
            self.lbl_base.setText(
                '✕ .xls (formato antigo) não pode ser usado como base — abra no Excel e '
                '"Salvar Como" .xlsx primeiro.')
            return
        if ext == 'xlsb':
            if open_xlsb is None:
                self.base_path = None
                self.lbl_base.setText(
                    '✕ Falta instalar o pacote "pyxlsb" pra ler .xlsb — rode "pip install pyxlsb" '
                    'e abra o app de novo.')
                return
            try:
                with open_xlsb(path) as wb:
                    if 'DBF' not in wb.sheets:
                        raise RuntimeError('a planilha nao tem aba "DBF"')
                self.base_path = path
                self.base_is_xlsb = True
                adicionar_ao_historico('base_path', path)
                self.lbl_base.setText(
                    f'✓ {os.path.basename(path)} · aba DBF encontrada · '
                    f'vai escrever direto em .xlsb pelo Excel (precisa do pywin32 + Excel instalado)')
            except Exception as e:
                self.base_path = None
                self.lbl_base.setText(f'✕ {e}')
            return
        try:
            wb = openpyxl.load_workbook(path, read_only=True)
            try:
                tem_dbf = 'DBF' in wb.sheetnames
            finally:
                wb.close()                      # senão o arquivo (na rede) fica travado pro resto do pessoal
            if not tem_dbf:
                raise RuntimeError('a planilha nao tem aba "DBF"')
            self.base_path = path
            self.base_is_xlsb = False
            adicionar_ao_historico('base_path', path)
            n_pivots = _contar_pivot_tables(path)
            if n_pivots and not _excel_com_disponivel():
                self.lbl_base.setText(
                    f'✓ {os.path.basename(path)} · aba DBF encontrada · '
                    f'⚠ {n_pivots} tabela(s) dinâmica(s) nesta base — sem o Excel/pywin32, a gravação '
                    f'pode resetar filtro/cache delas (limitação da biblioteca Python). '
                    f'Recomendo instalar o pywin32 antes de gerar.')
            else:
                self.lbl_base.setText(f'✓ {os.path.basename(path)} · aba DBF encontrada')
        except Exception as e:
            self.base_path = None
            self.lbl_base.setText(f'✕ {e}')

    def carregar_relatorio_fluxo(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar Relatório de Fluxos', '',
                                               'Excel (*.xlsx *.xlsm *.xlsb *.xls)')
        if not path:
            return
        self._processar_relatorio_fluxo(path)

    def _caminho_digitado_fluxo(self):
        caminho = self.lbl_fluxo.text().strip().strip('"')
        if caminho and os.path.isfile(caminho) and caminho != getattr(self, 'fluxo_report_path', None):
            self._processar_relatorio_fluxo(caminho)

    def _processar_relatorio_fluxo(self, path):
        try:
            fluxo_map, ignoradas, aba = ler_relatorio_fluxos(path)
            self.fluxo_map = fluxo_map
            self.fluxo_report_path = path
            adicionar_ao_historico('fluxo_report_path', path)
            n_laser = sum(1 for i in fluxo_map.get('granular', fluxo_map).values() if 'LASER' in norm(i.get('fluxo', '')))
            self.lbl_fluxo.setText(
                f'✓ {os.path.basename(path)} · aba "{aba}" · {len(fluxo_map.get("granular", fluxo_map))} marca(s) Fluxo 1-4 · {ignoradas} fora do escopo'
                + (f' · {n_laser} do LASER contada(s) como Fluxo 3' if n_laser else '')
                + (f' · {fluxo_map["gemeas"]} ordem(ns) repetida(s) (mesma peça, ex.: tipo de pintura) DESCARTADA(S) — só a Preparação vale'
                   if fluxo_map.get('gemeas') else ''))
        except Exception as e:
            self.fluxo_map = None
            self.lbl_fluxo.setText(f'✕ {e}')

    # ── Relatório SKA (Lantek) ──
    def carregar_relatorio_ska(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar relatório SKA (Análise de Nestings)', '',
                                               'CSV/Excel (*.csv *.txt *.xlsx *.xlsm *.xlsb *.xls)')
        if path:
            self._processar_relatorio_ska(path)

    def _caminho_digitado_ska(self):
        caminho = self.lbl_ska.text().strip().strip('"')
        if caminho and os.path.isfile(caminho) and caminho != getattr(self, 'ska_report_path', None):
            self._processar_relatorio_ska(caminho)

    def _processar_relatorio_ska(self, path):
        try:
            if ska_lantek is None:
                raise RuntimeError('o módulo ska_lantek.py não foi encontrado na pasta do Validador')
            resumo = ska_lantek.ler_relatorio_ska(path)
            self.ska_report_path = path
            adicionar_ao_historico('ska_report_path', path)
            self.lbl_ska.setText(f'✓ {os.path.basename(path)} · {ska_lantek.resumo_texto(resumo)}')
        except Exception as e:
            self.ska_report_path = None
            self.lbl_ska.setText(f'✕ {e}')

    def _mostrar_historico_ska(self):
        self._mostrar_historico(self.sender(), 'ska_report_path', self._processar_relatorio_ska)

    def _limpar_relatorio_ska(self):
        self.ska_report_path = None
        self.lbl_ska.clear()

    def atualizar_ska_agora(self):
        if ska_lantek is None:
            QMessageBox.warning(self, 'Aviso', 'O módulo ska_lantek.py não foi encontrado na pasta do Validador.')
            return
        if not self.ska_report_path:
            QMessageBox.warning(self, 'Aviso', 'Carregue o relatório SKA (CSV) primeiro.')
            return
        if not _excel_com_disponivel():
            QMessageBox.warning(self, 'Aviso', 'Para atualizar a planilha LANTEK_SKA é preciso o Excel + pywin32 neste PC '
                                               '(pip install pywin32).')
            return
        self._iniciar_trabalho_em_fundo(
            ska_lantek.atualizar_planilha_ska, (self.ska_report_path,), {'forcar': True},
            botoes_desabilitar=[self.btn_gerar, self.btn_vis, self.btn_ska_agora],
            label_status=self.lbl_status,
            msg_rodando='Atualizando a planilha LANTEK_SKA pelo Excel (em segundo plano — pode levar alguns minutos)…',
            on_sucesso=self._ska_agora_concluida,
        )

    def _ska_agora_concluida(self, resultado):
        msg = ska_lantek.texto_resultado(resultado)
        self.lbl_status.setText(msg)
        QMessageBox.information(self, 'Planilha LANTEK_SKA', msg + '\n\nAs bases passam a enxergar o dado novo ao abrir '
                                'e aceitar "Atualizar vínculos" (o nome do arquivo não mudou).')

    def carregar_relatorio_foco(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar Relatório FOCO (NDPCP301)', '',
                                               'Excel/CSV (*.xlsx *.xlsm *.xls *.xlsb *.csv *.txt)')
        if not path:
            return
        self._processar_relatorio_foco(path)

    def _caminho_digitado_foco(self):
        caminho = self.lbl_foco.text().strip().strip('"')
        if caminho and os.path.isfile(caminho) and caminho != getattr(self, 'foco_report_path', None):
            self._processar_relatorio_foco(caminho)

    def _processar_relatorio_foco(self, path):
        try:
            linhas, faltando = ler_relatorio_foco(path)
            self.foco_rows = linhas
            self.foco_report_path = path
            adicionar_ao_historico('foco_report_path', path)
            aviso = f' · ⚠ {faltando} coluna(s) do esquema não encontradas no arquivo' if faltando else ''
            self.lbl_foco.setText(f'✓ {os.path.basename(path)} · {len(linhas)} linha(s){aviso}')
        except Exception as e:
            self.foco_rows = None
            self.lbl_foco.setText(f'✕ {e}')

    def _limpar_base(self):
        """Volta pra Base fixa (se houver); sem Base fixa, apenas limpa."""
        self.base_path = None
        self.base_is_xlsb = False
        self.lbl_base.clear()
        self._carregar_base_fixa()

    def _limpar_relatorio_fluxo(self):
        self.fluxo_map = None
        self.fluxo_report_path = None
        self.lbl_fluxo.clear()

    def _limpar_relatorio_foco(self):
        self.foco_rows = None
        self.foco_report_path = None
        self.lbl_foco.clear()

    def _mostrar_historico(self, botao, chave, ao_escolher):
        historico = carregar_historico(chave)
        if not historico:
            QMessageBox.information(self, 'Histórico vazio', 'Ainda não tem nenhum arquivo no histórico.')
            return
        menu = QMenu(self)
        for caminho in historico:
            acao = menu.addAction(os.path.basename(caminho))
            acao.setToolTip(caminho)
            acao.triggered.connect(lambda _=False, c=caminho: ao_escolher(c))
        menu.exec_(botao.mapToGlobal(botao.rect().bottomLeft()))

    def _mostrar_historico_base(self):
        self._mostrar_historico(self.sender(), 'base_path', self._processar_base)

    def _mostrar_historico_fluxo(self):
        self._mostrar_historico(self.sender(), 'fluxo_report_path', self._processar_relatorio_fluxo)

    def _mostrar_historico_foco(self):
        self._mostrar_historico(self.sender(), 'foco_report_path', self._processar_relatorio_foco)

    # ── Consolidar ──
    def _linhas_validas(self):
        linhas = []
        for e in self.dbf_entries:
            if e['status'] == 'ok' and e['rows']:
                linhas.extend(e['rows'])
        return linhas

    def visualizar_consolidado(self):
        linhas = self._linhas_validas()
        if not linhas:
            QMessageBox.warning(self, 'Aviso', 'Carregue ao menos uma DBF válida primeiro.')
            return
        cols = ESQUEMA_DBF[COL_DBF_INICIO:COL_DBF_FIM + 1] + ['Fluxo (auto)']
        self.tbl.clear()
        self.tbl.setColumnCount(len(cols))
        self.tbl.setHorizontalHeaderLabels(cols)
        self.tbl.setRowCount(len(linhas))
        pos_com_filhos = construir_pos_com_filhos(linhas)
        com_fluxo = 0
        for i, row in enumerate(linhas):
            for j in range(COL_DBF_INICIO, COL_DBF_FIM + 1):
                self.tbl.setItem(i, j, QTableWidgetItem(row[j]))
            f = achar_fluxo_da_linha(row, self.fluxo_map, pos_com_filhos)
            self.tbl.setItem(i, len(cols) - 1, QTableWidgetItem(f['maq'] if f else '—'))
            if f:
                com_fluxo += 1
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        aviso_fluxo = (f'🔀 {com_fluxo} marca(s) reconhecida(s) com Fluxo 1-4 · {len(linhas) - com_fluxo} sem fluxo (manual)'
                       if self.fluxo_map else 'Carregue o Relatório de Fluxos para marcar Fluxo 1-4 automaticamente.')
        self.lbl_status.setText(f'{len(linhas)} linha(s) no consolidado · {aviso_fluxo}')

    # ── Gerar base ──
    def gerar_base(self):
        linhas = self._linhas_validas()
        lote = self.txt_lote.text().strip()
        if not self.base_path:
            QMessageBox.warning(self, 'Aviso', 'Carregue a planilha base (.xlsx) primeiro.')
            return
        if not linhas:
            QMessageBox.warning(self, 'Aviso', 'Carregue ao menos uma DBF válida.')
            return
        if not lote:
            QMessageBox.warning(self, 'Aviso', 'Informe o nome/número do lote.')
            return

        # V271: a base gerada vai SEMPRE para a pasta Downloads do usuário (fácil de achar, igual para todos)
        pasta = _pasta_downloads()
        lote_slug = re.sub(r'[^a-zA-Z0-9-]', '-', lote)
        usar_excel = self.base_is_xlsb or _excel_com_disponivel()

        if not usar_excel:
            n_pivots = _contar_pivot_tables(self.base_path)
            if n_pivots:
                resp = QMessageBox.warning(
                    self, 'Tabela dinâmica sem Excel disponível',
                    f'Esta base tem {n_pivots} tabela(s) dinâmica(s). Sem o Excel (pywin32) pra gerar, '
                    f'a biblioteca Python usada aqui PODE resetar o filtro/cache dessas abas — já vi isso '
                    f'acontecer num teste real.\n\nRecomendo cancelar e instalar "pip install pywin32" antes.\n\n'
                    f'Quer continuar mesmo assim (só a aba DBF/FOCO ficam garantidas, o resto é por sua conta e risco)?',
                    QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
                if resp != QMessageBox.Yes:
                    return

        ext_padrao = 'xlsb' if self.base_is_xlsb else 'xlsx'
        nome_saida = f'BASE_PPCPM_Programação-Fábrica_LOTE_{lote_slug}_{date_tag()}.{ext_padrao}'
        filtro = 'Excel Binário (*.xlsb);;Excel (*.xlsx)' if self.base_is_xlsb else 'Excel (*.xlsx)'
        caminho_saida, _ = QFileDialog.getSaveFileName(self, 'Salvar Base Preenchida',
                                                         os.path.join(pasta, nome_saida),
                                                         filtro)
        if not caminho_saida:
            return
        adicionar_ao_historico('pasta_saida_base', os.path.dirname(caminho_saida))

        fn = gerar_base_preenchida_via_excel if usar_excel else gerar_base_preenchida
        msg = ('Gerando base preenchida pelo Excel (mais rápido)… roda em segundo plano.' if usar_excel
               else 'Gerando base preenchida… (biblioteca Python — se instalar o pywin32 fica bem mais rápido)')
        # planilha LANTEK_SKA: atualiza ANTES (mesma tarefa em segundo plano) para a base já sair com o dado novo
        ska_csv, aviso_ska = None, ''
        if getattr(self, 'chk_ska', None) is not None and self.chk_ska.isChecked():
            if not self.ska_report_path:
                aviso_ska = 'planilha LANTEK_SKA não atualizada: nenhum relatório SKA carregado'
            elif ska_lantek is None:
                aviso_ska = 'planilha LANTEK_SKA não atualizada: módulo ska_lantek.py não encontrado'
            elif not _excel_com_disponivel():
                aviso_ska = 'planilha LANTEK_SKA não atualizada: falta o Excel/pywin32 neste PC'
            else:
                ska_csv = self.ska_report_path
                msg = 'Atualizando a planilha LANTEK_SKA e gerando a base pelo Excel (segundo plano — pode levar alguns minutos)…'
        self._aviso_ska_gerar = aviso_ska
        self._iniciar_trabalho_em_fundo(
            _gerar_base_e_atualizar_ska, (fn, (self.base_path, linhas, self.fluxo_map, lote, caminho_saida),
                                         {'linhas_foco': self.foco_rows}, ska_csv, usar_excel),
            {},
            botoes_desabilitar=[self.btn_gerar, self.btn_vis, self.btn_ska_agora],
            label_status=self.lbl_status,
            msg_rodando=msg,
            on_sucesso=lambda resultado: self._gerar_base_concluida(resultado, caminho_saida, usou_excel=usar_excel),
        )

    def _gerar_base_concluida(self, resultado, caminho_saida, usou_excel=True):
        msg = (f"✅ Base gerada: {os.path.basename(caminho_saida)} "
               f"({resultado['com_fluxo']} com fluxo marcado, {resultado['sem_fluxo']} sem fluxo)")
        if not usou_excel:
            # gravou pela biblioteca Python: as tabelas dinâmicas (Peso x Fluxo etc.) NÃO foram atualizadas
            msg += (' · ⚠ gerada SEM o Excel (falta o pywin32 ou o Excel neste PC): fórmulas e tabelas dinâmicas '
                    'não foram atualizadas — gere a base num PC com Excel + pywin32 (pip install pywin32)')
        dup = resultado.get('duplicadas') or {}
        if dup.get('total'):
            msg += (f" · ✔ {dup['total']} linha(s) repetida(s) da DBF (mesma posição, ex.: tipo de pintura diferente) "
                    f"REMOVIDA(S) — não entraram na base")
        if resultado['linhas_foco']:
            msg += f" · {resultado['linhas_foco']} linha(s) na aba FOCO"
        if resultado.get('caches_corrigidos'):
            msg += f" · {resultado['caches_corrigidos']} intervalo(s) de cache corrigido(s)"
        if resultado.get('pivots_atualizados'):
            msg += f" · {resultado['pivots_atualizados']} tabela(s) dinâmica(s) atualizada(s)"
        if resultado.get('ordem_dbf'):
            msg += ' · DBF classificada (' + ' → '.join(resultado['ordem_dbf']) + ')'
        if resultado.get('abas_renomeadas'):
            msg += f" · {resultado['abas_renomeadas']} aba(s) com nome e cor do padrão (FOCCO_VISION_NDPCP399)"
        if resultado.get('pivots_sem_pintura'):
            msg += ' · lista PREP: uma linha por posição/ordem (TIPO PINTURA fora das linhas)'
        if resultado.get('pivots_com_erro'):
            msg += f" · ⚠ {resultado['pivots_com_erro']} tabela(s) dinâmica(s) não atualizaram (confira manualmente)"
        if resultado['nao_encontradas']:
            msg += f" · ⚠ {len(resultado['nao_encontradas'])} marca(s) do relatório não encontradas na DBF carregada"
        ska = resultado.get('ska')
        if ska:
            msg += ' · ' + (ska_lantek.texto_resultado(ska) if 'erro' not in ska
                            else f"⚠ planilha LANTEK_SKA NÃO atualizada: {ska['erro']}")
            if resultado.get('vinculos_lantek'):
                msg += ' · vínculo Lantek da base atualizado'
        elif getattr(self, '_aviso_ska_gerar', ''):
            msg += f" · ℹ {self._aviso_ska_gerar}"
        self.lbl_status.setText(msg)
        detalhe = ''
        if dup.get('total'):
            detalhe += ('\n\nLinhas repetidas REMOVIDAS da DBF (OF | posição: nº de linhas removidas):\n'
                        + '\n'.join(f'  {k.replace("|", " | ")}: {n}' for k, n in dup['chaves'][:30])
                        + (f'\n  … (+{len(dup["chaves"]) - 30})' if len(dup['chaves']) > 30 else ''))
        if resultado.get('erros_pivot'):
            detalhe += '\n\nTabelas dinâmicas que não atualizaram:\n' + '\n'.join(resultado['erros_pivot'])
        detalhe = _quadro_atualizacoes_base(resultado, usou_excel) + detalhe
        if resultado.get('tempos'):
            total = sum(resultado['tempos'].values())
            linhas_tempo = '\n'.join(f'  {nome}: {seg}s' for nome, seg in resultado['tempos'].items())
            detalhe += f'\n\n⏱ Tempo por etapa (total {round(total, 1)}s):\n{linhas_tempo}'
        QMessageBox.information(self, 'Concluído',
                                 msg + '\n\nEste é um arquivo NOVO — o original não foi alterado.\n'
                                       'Confira no Excel antes de substituir a base oficial.' + detalhe)

    _QUADROS_SPINNER = ['◐', '◓', '◑', '◒']

    def _iniciar_trabalho_em_fundo(self, fn, args, kwargs, botoes_desabilitar, label_status,
                                    msg_rodando, on_sucesso):
        """Roda fn(*args, **kwargs) numa QThread separada, pra nao travar a
        janela — desabilita os botões passados enquanto roda e reabilita
        no final (sucesso ou erro). Mostra um iconezinho girando do lado
        da mensagem enquanto roda, pra ficar claro visualmente que está
        processando (antes só tinha o texto)."""
        for b in botoes_desabilitar:
            b.setEnabled(False)

        spinner = QTimer(self)
        estado = {'quadro': 0, 'msg_atual': msg_rodando}

        def _atualizar_spinner():
            quadro = self._QUADROS_SPINNER[estado['quadro'] % len(self._QUADROS_SPINNER)]
            estado['quadro'] += 1
            label_status.setText(f"{quadro} {estado['msg_atual']}")

        _atualizar_spinner()
        spinner.timeout.connect(_atualizar_spinner)
        spinner.start(180)

        worker = Worker(fn, *args, **kwargs)
        worker.progresso.connect(lambda msg: estado.__setitem__('msg_atual', msg))

        def _ao_terminar(*_):
            spinner.stop()
            for b in botoes_desabilitar:
                b.setEnabled(True)

        def _sucesso(resultado):
            _ao_terminar()
            try:
                on_sucesso(resultado)
            except Exception as e:
                # sem isso, uma exceção ao MOSTRAR o resultado derrubava o programa inteiro (PyQt5 aborta)
                import traceback
                _registrar_erro_no_log('Erro ao mostrar o resultado (Validador)')
                label_status.setText('❌ Erro ao mostrar o resultado — o programa continua aberto')
                QMessageBox.critical(self, 'Erro ao mostrar o resultado',
                                     f'{e.__class__.__name__}: {e}\n\n' + traceback.format_exc()[-1200:])

        def _erro(msg):
            _ao_terminar()
            label_status.setText(f'❌ {msg}')
            QMessageBox.critical(self, 'Erro', msg)

        worker.sucesso.connect(_sucesso)
        worker.erro.connect(_erro)
        # segura referencia pra nao ser coletado pelo garbage collector enquanto roda
        self._workers = getattr(self, '_workers', [])
        self._workers.append(worker)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.start()


# ═══════════════════════════════════════════════════════════════════
# TEMA — escuro ou claro, com detalhes neon (mesma linha visual das
# outras ferramentas do PCP) — tudo ajustável pelo botão ⚙ de
# configurações (cores de destaque + escuro/claro)
# ═══════════════════════════════════════════════════════════════════
# Logo da Projeart (selo "GRUPO PROJEART", branco, fundo transparente) — aparece na barra lateral
LOGO_PROJEART_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAPAAAAA9CAYAAACTI+T4AAAK/ElEQVR42u2df6hX5R3HX6fv3b3h7d6hdMPQahhec1Q6jETDliPp0kamoyjasGIYyIxKQ2FbAwfDsM2ha0NBJkwqFtYMt4xiLkeuhaFNYdNQdmehS/GyOxWvXvnuj+c53HPPfZ5znvPre7/P9fOGw/d7znl+P+f9fD7P5/mc5wT1eh2BQOAnrpImEAj8RYv+vR/o00cnMAB06XsDQD9wGjgJXJZmEwiaA4FWoZtNj94NPKwHDYFAkKJCB01WrvnAKT2wfAgska4SCOwSOESzW7RWAy9KtwkEZgL7QOJm1BgEglFVoX0jh6x9CQTYl5F8IfEj0oUCIbC/JH4VeEa6USAE9pfE64FJJaTTAZzVkj1+vG2J8xtL+OixIiHPVbGwFxzzeTlyb5K+dsmS/xnglYxtsd2S1p+EMn4R2BcSf1Yw/iWUs0q75X6PfoA3xa7f5pD2SzruccO9ObHzNksa82Pn8yL/v6l/WyxxxwOPRkiYhMM6zOKEctR1OIEnBPZpTpw3Xotj2KUxKVTLkM/kAmW8NnZ+sYJ2Ogx0O6bRjRgSvSKwLySulUj6Y5br3yiQH8DOmHR0wf9i562R/30lkHhVAnn3JuSxUyjkD4F9IPFghrDfT6hjANwc+R+mHTi2URCLi0HlzUK+toRz0yDwVEoZ4lhrmTYEwF3ABIZ84211EXhAYB9I3OoYbmOGugXAlwzXOx3y6U+49x/Hso6LnUd9xAcM4bfFzlcawszQv0ssbfOOIU8TYVcJjfwicLOT+GgD83J5M6szw9zWhvOx844UAscJPzch7a2Ga09bwv7RcO0ZoZF/BG5mEk+uaG49HpiSQboC3FeA3ElTg6gRa1KKVOzAbFX+JGdbnIydTxQa+UfgE56o02XgSU2gM1q6n0iRftF1012G+2tiA0MeCdyaUoaVkTL0O5AwC4SwY4DAExmyZDYjiW8sMa04QdoKpHUQ+HHkvNcx3k055842XB/5/wfD/fEZ0totNBo9tOSIsz8mbUJL53Gt2tXIt7xiKlubln7ndZqho8W5FFV5IvDvHHkeBqalqLl9Ocn8EvB87JqpjA8Ab6Wk9YalPGnoB74cu/YtRi4rHUVZnuMwOaM8KzQaPQQ5NrUzRegBPo2Qtw+7V1MWydeBMhSdRxlmasA/DWG/YPgyx7PAL3LWJSTmRUuYg8Dt+v/fGemNtQVlnFoYu34OuMaxDMuBXwL3WCRcEFPxtxjCbNZteFK3xfkc7XAH8LHWaHo9s4WIBM6AXaNYh4XAdcCiiGRyXQ9eb5EgAwlxulLa73v69wOGW3/bdRnfNBA7PthtxLzMFQ4gaSp9dAByGsgtJN6XEm+BUMivOfD9TViHHaiXAN6MGGdc54jPWaRXEqLhxyWEuytF9Q1xTcb8b3cYbDpztGNXxvA9wHtCIb8IvKNJ69GmpcX1GSVwKDFd1MBjOtwPY9eiGHRQLy9YJODrKfl/bEmvz/FaGk7r9A+mhDuow70j9PFvDtzsDuyhKtit5+R5MAPlcTQJ+Avw2ijUYwUwG+WHvJHR28r3R8BM4JCeU38ulBECV4kXUOusYlgRiAodw0Me1GeNZZ4pEFzxBF7kSZ2+Ld0qEBXaP/U5Og8WCEJMQdkzatqWMKCPT8ZC5eTjZjCV9H2t6igf6P0o5woX7HNMNzzeL0nLmZOST9n7WpnymOEYLuuR59XFo8AelEPMHuBvwIGS6ul6LKoo3bqrBJ6DsoiORen7EPC7nPlNwL5kU1RjCb2gXDEjx4MZlETgOFYCP6tAg9vN8B1R0nCBZHfXoGA9y3g+C6XrKoF3MHbRWiDuGS05q8A+4F3HsPsLSJXHPOqrgYzh25qs/KVPQ10J3OVB53bmjHexYL53ayJXgXuBDQ4PxcwCeWyj/Jfyz1fUHlkI+aFDmC98J/FYmQP3MnLjt0ZI4BDjK5RkyxPu/bekPNYzfKvaohhXUVtk+dzs7CYWTPc0ksA+bOb9lQrSXM/wjeFudpBkLnhdS+25qH2We0h3o9xkuLbBQetoj5R/TUrYPaMggY/Eyph2POyY7qYMZS26s+ZiS1nT5vLRebHp2Jwylw6AwMWI1ezLRz8Aflog/mMW8tk6YWnCAxI4tFtS527Hvql6kKFfkvJ4V6vmeeK6Ph/LgF87hHuUalxVsz6zQYE0k+K+rwfrPHnWsPv0B2NFhd5TkLyQ3c94c4X1cXVCWVTgYVxA9d5qrvaIKlTtjhxx5lXUDj8pOC0rrEKvaGLyHgC+XkI6l/EP6y3Xv1PCQNFIq/TMCtK0bfFzB/Z9rF+uqH79VcdNU6GbVX3eiH3r06ywrQMHBdWpPCpX1WlH8S9G7rUVzkunFVRXTTui2Mp8DrUxQg1liBzUkrlFP8Th0tENBdXnoAH9EscJ7JsApuXXin3ZzGsVenGJ5M2D7RWmXU+Y55eNxy3Xu0tIO8ueaO2o5aEWrTZ2Ra51ofY+m+yobtu+tvGryP8dJUvhD4BbgFuBWVogrNN9aSPvsrI6MUkCT6L4V//KRhV+zo+gvjMcx17UJ0oOMbS38taEdPoYvhFcvcJ6m9L+B/DVkgaMoh5KVXhilWloylPveoOf48ISuFmWj7bh/o2fMufAc1G7T4R7K29NSWdCReXrcQw3PWO68yrssyrsCuNzxjNtxmez7k71TQglbWrXPcrEnQ185IlaX9Xg8jjVbV2zrgLDSx68oQnfivKKO6fPa/q8H2XVTtsm6Kzl+gBDbyKB2jH0tEW9PUK1b7OVnnZLE5FgL8qx4SJ+IRiFdE9h9iJaivsyl81T6bsllN11T7IXgdUltVd7giAaHKvPiY3Apm/6bAWeyKiiTdTzxwGUd06bHlE/x+/3MQcxf62wUXjaMm/f5Ejg3ybce6uE8rluqnekpPYoc35az0G2XpTNqOEC0ZbhfP17jCEXwg0ZG8r3F+uzDlh52iXpNc17sW/b+pqFwC4P4Crs68WnLHPPM5Y0bW6In3LlINoua7G/s/x74MESNIphsBmxaiiPnRcYenl4+RjtANuSxxMNyPuv2C39aa8SbkyRIvHlrlnAJcwf8w5xXez8VobetKoz/FvC67A7RrjaLtaW0IY7K+iX4znjrcZuOV5INkPcOafRw7KMZPMPdsUB4GueEHgJZgtz1q8buKp1WV7qTlsaKlN1jG/FO7WAihtUWFbXJaEB4OqUtM4mSLqggv7Mopl2YDcopi4jbSvYyL6QN0kCN9KYZuvU6SR/BLysacoyg9qbl7zzG9hucxLuXe0QP+mrGEW+QpK0pPi2YxpOS3FXWaTvlYSBJinHrgzz0jJJvJyRbw6B8h3Ois+APzewzbZUmPbWAnH7GPnVjhA9wJ2ljfwGFbqoqlPVK2JV4QHM7nVFiVGmt89Jhn/T14Sfk/1Tn0X8cU3kvaEB6n7ZPuF3oja6qyKvoqp0ap5VmL19Ii+oZZNXUeuqfQw5FBTFatRSWrgG2Z4wKkc75hU9/+7U5OnF/NJBHM/p40k9r7/NYDQ5hnKceN6xDhd1me5DWVenxMrSr9NzMfhtQS21hN96boloQKHTRk3XvWZQIQdRbq1RPKXtBDfq+H05NKqPUF53N+mBcrpup/jUaoFOe7oOV3Psz1m63qD8uS87aFUh7kYtxYbP5GB8qlOFBJZ9mQWCBiE+Bz5eML3p0qQCQeMQl8AifQUCjyVwERyR5hQIGouoEetaPUk/pCfeNk+Q8E2Rdoa/KTJNmlMgGF0VWiAQXKEqtEAgEAILBAJX/B+jS7mTjXpUcQAAAABJRU5ErkJggg=='

# Padrão visual Projeart: menu lateral azul-marinho (#0B1D3A), topo branco, cartões brancos arredondados,
# cabeçalho de tabela escuro, botões azuis (#2E6AAD). 'cyan' = azul de destaque; 'magenta' = botões de ação.
CORES_NEON_ANTIGAS = {'cyan': '#00e5ff', 'magenta': '#ff2fd0', 'green': '#39ff8f', 'amber': '#ffb02e'}
CORES_PADRAO = {'cyan': '#2E6AAD', 'magenta': '#2E6AAD', 'green': '#1E8E5A', 'amber': '#C77700',
                'modo': 'projeart', 'versao': 2}
CAMINHO_CORES_SALVAS = os.path.join(os.path.expanduser('~'), '.ppcp_cores_tema.json')

TEMA_ESCURO = {
    'bg': '#0b0e14', 'bg_panel': '#0f1420', 'bg_alt': '#121826', 'bg_botao': '#141a29',
    'bg_botao_pressed': '#1a2233', 'bg_tab': '#11151f', 'bg_tab_sel': '#161c2c',
    'border': '#232a3b', 'border_forte': '#2a3348', 'border_pane': '#1f2937',
    'texto': '#e6edf3', 'texto_muted': '#c3cbd8', 'texto_fraco': '#8b95a5',
    'texto_disabled': '#4a5266', 'texto_hover': '#c9d3e0',
    'selecao_bg': '#17324a', 'texto_no_destaque': '#04121a',
    'sidebar': '#080b11', 'topbar': '#0f1420',
}
TEMA_PROJEART = {
    'bg': '#F4F6FA', 'bg_panel': '#FFFFFF', 'bg_alt': '#F7F9FC', 'bg_botao': '#FFFFFF',
    'bg_botao_pressed': '#E6ECF5', 'bg_tab': '#E9EEF6', 'bg_tab_sel': '#FFFFFF',
    'border': '#E3E8F0', 'border_forte': '#D2DAE6', 'border_pane': '#E3E8F0',
    'texto': '#1B2536', 'texto_muted': '#46546B', 'texto_fraco': '#7C8AA0',
    'texto_disabled': '#B3BDCC', 'texto_hover': '#0B1D3A',
    'selecao_bg': '#DCE8F7', 'texto_no_destaque': '#FFFFFF',
    'sidebar': '#0B1D3A', 'topbar': '#FFFFFF',
}
TEMA_CLARO = {
    'bg': '#eef1f6', 'bg_panel': '#ffffff', 'bg_alt': '#f2f5fa', 'bg_botao': '#ffffff',
    'bg_botao_pressed': '#e4e9f0', 'bg_tab': '#e2e8f0', 'bg_tab_sel': '#ffffff',
    'border': '#d7dee7', 'border_forte': '#c3ccd9', 'border_pane': '#d7dee7',
    'texto': '#18212e', 'texto_muted': '#3c4758', 'texto_fraco': '#707c8c',
    'texto_disabled': '#aab3c0', 'texto_hover': '#18212e',
    'selecao_bg': '#cdeaf6', 'texto_no_destaque': '#04121a',
    'sidebar': '#0B1D3A', 'topbar': '#ffffff',
}


def carregar_cores_salvas():
    try:
        with open(CAMINHO_CORES_SALVAS, 'r', encoding='utf-8') as f:
            salvas = json.load(f)
        if salvas.get('versao', 1) < 2:        # config do tema neon antigo -> padrão Projeart (dá pra voltar no botão de cores)
            return dict(CORES_PADRAO)
        cores = dict(CORES_PADRAO)
        cores.update({k: v for k, v in salvas.items() if k in CORES_PADRAO})
        return cores
    except Exception:
        return dict(CORES_PADRAO)


def salvar_cores(cores):
    try:
        with open(CAMINHO_CORES_SALVAS, 'w', encoding='utf-8') as f:
            json.dump(cores, f)
    except Exception:
        pass


def construir_folha_estilo(cores):
    """Monta o QSS inteiro a partir de um dict {'cyan','magenta','green',
    'amber','modo'} — chamada de novo sempre que o usuário muda uma cor
    ou troca claro/escuro na telinha ⚙."""
    NEON_CYAN = cores['cyan']
    NEON_MAGENTA = cores['magenta']
    NEON_GREEN = cores['green']
    NEON_AMBER = cores['amber']
    modo = cores.get('modo')
    T = {'claro': TEMA_CLARO, 'projeart': TEMA_PROJEART}.get(modo, TEMA_ESCURO)
    # texto na cor de destaque: no modo claro o neon (ex.: #00e5ff) fica
    # quase invisível sobre branco, então escurece só pra texto — barras e
    # bordas continuam com o neon. No modo escuro não muda nada.
    ACENTO_TXT = NEON_CYAN
    if cores.get('modo') == 'claro':
        try:
            _h = NEON_CYAN.lstrip('#')
            _r, _g, _b = (int(_h[i:i + 2], 16) for i in (0, 2, 4))
            ACENTO_TXT = '#%02x%02x%02x' % (int(_r * .5), int(_g * .55), int(_b * .6))
        except Exception:
            ACENTO_TXT = NEON_CYAN
    qss = f"""
QWidget {{
    background-color: {T['bg']};
    color: {T['texto']};
    font-family: 'Lexend', 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {T['bg']};
}}

/* ── Abas ── */
QTabWidget::pane {{
    border: 1px solid {T['border_pane']};
    border-radius: 10px;
    background-color: {T['bg_panel']};
    top: -1px;
}}
QTabBar::tab {{
    background: {T['bg_tab']};
    color: {T['texto_fraco']};
    padding: 8px 14px;
    margin-right: 3px;
    min-width: 60px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: .2px;
}}
QTabBar::tab:selected {{
    color: {NEON_CYAN};
    background: {T['bg_tab_sel']};
    border-bottom: 2px solid {NEON_CYAN};
}}
QTabBar::tab:hover:!selected {{
    color: {T['texto_hover']};
}}

/* ── Caixas de grupo ── */
QGroupBox {{
    border: 1px solid {T['border']};
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    background-color: {T['bg_panel']};
    font-weight: 700;
    color: {NEON_CYAN};
    letter-spacing: .3px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: {NEON_CYAN};
}}

/* ── Botões ── */
QPushButton {{
    background-color: {T['bg_botao']};
    color: {T['texto']};
    border: 1px solid {T['border_forte']};
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
}}
QPushButton:hover {{
    border: 1px solid {NEON_CYAN};
    color: {NEON_CYAN};
}}
QPushButton:pressed {{
    background-color: {T['bg_botao_pressed']};
}}
QPushButton:disabled {{
    color: {T['texto_disabled']};
    border: 1px solid {T['border']};
}}

/* Botão principal — usar objectName 'btnPrincipal' para destaque neon cheio */
QPushButton#btnPrincipal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0aa5c2, stop:1 {NEON_CYAN});
    color: {T['texto_no_destaque']};
    border: none;
    font-weight: 800;
    padding: 11px 22px;
}}
QPushButton#btnPrincipal:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {NEON_CYAN}, stop:1 #7cf5ff);
}}
QPushButton#btnPrincipal:disabled {{
    background: {T['bg_botao_pressed']};
    color: {T['texto_disabled']};
}}

QPushButton#btnAnalisar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #b3199c, stop:1 {NEON_MAGENTA});
    color: {T['texto_no_destaque']};
    border: none;
    font-weight: 800;
}}
QPushButton#btnAnalisar:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {NEON_MAGENTA}, stop:1 #ff8ae8);
}}

/* ── Campos de texto ── */
QLineEdit {{
    background-color: {T['bg_panel']};
    border: 1px solid {T['border_forte']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {T['texto']};
    selection-background-color: {NEON_CYAN};
    selection-color: {T['texto_no_destaque']};
}}
QLineEdit:focus {{
    border: 1px solid {NEON_CYAN};
}}

/* ── Listas ── */
QListWidget {{
    background-color: {T['bg_panel']};
    border: 1px solid {T['border']};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 5px 6px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {T['selecao_bg']};
    color: {NEON_CYAN};
}}

/* ── Tabelas ── */
QTableWidget {{
    background-color: {T['bg_panel']};
    alternate-background-color: {T['bg_alt']};
    gridline-color: {T['border']};
    border: 1px solid {T['border']};
    border-radius: 8px;
    selection-background-color: {T['selecao_bg']};
    selection-color: {NEON_CYAN};
}}
QTreeWidget {{
    background-color: {T['bg_panel']};
    alternate-background-color: {T['bg_alt']};
    color: {T['texto_muted']};
    border: 1px solid {T['border']};
    border-radius: 8px;
    selection-background-color: {T['selecao_bg']};
    selection-color: {NEON_CYAN};
}}
QTreeWidget::item {{
    padding: 3px 2px;
}}
QTreeWidget::item:selected {{
    background-color: {T['selecao_bg']};
    color: {NEON_CYAN};
}}
QHeaderView::section {{
    background-color: {T['bg_tab_sel']};
    color: {NEON_CYAN};
    padding: 6px;
    border: none;
    border-bottom: 2px solid {NEON_CYAN};
    font-weight: 700;
}}
QTableCornerButton::section {{
    background-color: {T['bg_tab_sel']};
    border: none;
}}

/* ── Rótulos ── */
QLabel {{
    color: {T['texto_muted']};
}}

/* ── Barra de rolagem ── */
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {T['bg_panel']};
    border: none;
    width: 11px;
    height: 11px;
    margin: 0;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {T['border_forte']};
    border-radius: 5px;
    min-height: 24px;
    min-width: 24px;
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: {NEON_CYAN};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0; width: 0;
}}

/* ── Caixas de mensagem ── */
QMessageBox {{
    background-color: {T['bg_panel']};
}}

/* ═══ Refinamento visual ═══
   Regras abaixo vêm DEPOIS das anteriores de propósito (a última vence
   quando têm a mesma força): só ajustam acabamento, sem mudar estrutura. */

/* rótulos e caixas de marcar sem a faixa de fundo escura que aparecia
   dentro das caixas de grupo (o fundo geral da janela vazava neles) */
QLabel, QCheckBox, QRadioButton {{
    background: transparent;
}}
QCheckBox, QRadioButton {{
    spacing: 8px;
}}

/* abas: mais folga, aba ativa "cola" no painel, sem texto cortado */
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    padding: 10px 20px;
    margin-right: 4px;
    min-width: 72px;
    font-size: 12px;
    border: 1px solid transparent;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background: {T['bg_panel']};
    color: {ACENTO_TXT};
    border: 1px solid {T['border_pane']};
    border-bottom: 3px solid {NEON_CYAN};
}}
QTabBar::tab:hover:!selected {{
    background: {T['bg_tab_sel']};
    color: {T['texto']};
}}

/* caixas de grupo: título em "pílula", respiro maior */
QGroupBox {{
    margin-top: 18px;
    padding: 20px 12px 12px 12px;
}}
QGroupBox::title {{
    left: 14px;
    padding: 3px 12px;
    background-color: {T['bg_tab_sel']};
    border: 1px solid {T['border']};
    border-radius: 11px;
    color: {ACENTO_TXT};
}}

/* botões: altura uniforme, foco visível, desligado discreto */
QPushButton {{
    min-height: 20px;
    padding: 8px 18px;
}}
QPushButton:focus {{
    border: 1px solid {NEON_CYAN};
}}
QPushButton#btnPrincipal, QPushButton#btnAnalisar {{
    border-radius: 9px;
    padding: 10px 22px;
}}

/* campos de texto longos */
QPlainTextEdit, QTextEdit {{
    background-color: {T['bg']};
    border: 1px solid {T['border_forte']};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {NEON_CYAN};
    selection-color: {T['texto_no_destaque']};
}}
QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {NEON_CYAN};
}}
QComboBox {{
    background-color: {T['bg_botao']};
    border: 1px solid {T['border_forte']};
    border-radius: 6px;
    padding: 5px 10px;
}}
QComboBox:hover {{
    border: 1px solid {NEON_CYAN};
}}
QComboBox QAbstractItemView {{
    background-color: {T['bg_panel']};
    border: 1px solid {T['border_forte']};
    selection-background-color: {T['selecao_bg']};
    selection-color: {NEON_CYAN};
}}

/* listas e árvores: linha com realce ao passar o mouse */
QTreeWidget::item {{
    padding: 4px 2px;
}}
QTreeWidget::item:hover:!selected, QListWidget::item:hover:!selected {{
    background-color: {'#EFF5FC' if modo == 'projeart' else T['bg_alt']};
}}

/* barra de rolagem mais fina e discreta */
QScrollBar:vertical {{
    width: 9px;
    margin: 2px;
    background: transparent;
}}
QScrollBar:horizontal {{
    height: 9px;
    margin: 2px;
    background: transparent;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    border-radius: 4px;
}}
QGroupBox {{
    color: {ACENTO_TXT};
}}
QHeaderView::section {{
    color: {ACENTO_TXT};
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    color: {ACENTO_TXT};
}}

/* seções recolhíveis (▾/▸): título na cor de destaque, como os outros
   passos, e interior no mesmo tom da caixa (antes ficava mais escuro) */
QPushButton#btnTituloCaixa {{
    color: {ACENTO_TXT};
    padding: 2px 4px;
}}
QPushButton#btnTituloCaixa:hover {{
    color: {T['texto']};
}}
QWidget#conteudoCaixa {{
    background: transparent;
}}

/* dicas ao passar o mouse */
QToolTip {{
    background-color: {T['bg_alt']};
    color: {T['texto']};
    border: 1px solid {NEON_CYAN};
    border-radius: 6px;
    padding: 6px 8px;
}}
QSplitter::handle {{
    background: {T['border']};
}}

/* ═══ Estrutura Projeart: barra lateral + topo (valem em todos os temas) ═══ */
QFrame#sidebar {{
    background-color: {T['sidebar']};
    border: none;
}}
QFrame#sidebar QLabel {{
    background: transparent;
}}
QLabel#sidebarSecao {{
    color: #7F93B5; font-size: 10px; font-weight: 800; letter-spacing: 1.2px;
    padding: 16px 14px 6px 14px;
}}
QLabel#sidebarRodape {{
    color: #6E83A8; font-size: 10px; padding: 6px 14px;
}}
QPushButton#navItem {{
    background-color: transparent; color: #C5D1E6; border: none; border-radius: 10px;
    text-align: left; padding: 11px 14px; font-size: 13px; font-weight: 600;
}}
QPushButton#navItem:hover {{
    background-color: rgba(255, 255, 255, 0.09); color: #FFFFFF; border: none;
}}
QPushButton#navItem:checked {{
    background-color: {NEON_CYAN}; color: {T['texto_no_destaque']}; border: none;
}}
QFrame#topbar {{
    background-color: {T['topbar']};
    border: none;
    border-bottom: 1px solid {T['border']};
}}
QFrame#topbar QLabel {{
    background: transparent;
}}
QLabel#paginaTitulo {{
    font-size: 28px; font-weight: 700; color: {'#0B1D3A' if modo == 'projeart' else ACENTO_TXT};
}}
QLabel#paginaSub {{
    font-size: 12px; color: {T['texto_fraco']};
}}
QLabel#chipUsuario {{
    background-color: {T['bg_alt']}; border: 1px solid {T['border']}; border-radius: 15px;
    padding: 5px 14px; color: {T['texto_muted']}; font-weight: 600;
}}
QFrame#cartaoKpi {{
    background-color: {T['bg_panel']}; border: 1px solid {T['border']}; border-radius: 14px;
}}
QFrame#cartaoKpi QLabel {{
    background: transparent;
}}
QFrame#cartaoKpi QLabel#kpiIcone {{
    background-color: {T['selecao_bg']}; border-radius: 12px; font-size: 20px; padding: 6px;
}}
QLabel#kpiRotulo {{
    color: {T['texto_fraco']}; font-size: 11px; font-weight: 700;
}}
QLabel#kpiValor {{
    color: {'#0B1D3A' if modo == 'projeart' else T['texto']}; font-size: 24px; font-weight: 800;
}}
"""
    if modo == 'projeart':
        qss += f"""
/* ═══ PADRÃO PROJEART: cartões brancos, tabelas com cabeçalho escuro, botões azuis ═══ */
QGroupBox {{
    background-color: #FFFFFF;
    border: 1px solid #E3E8F0;
    border-radius: 14px;
    margin-top: 0px;
    padding: 46px 16px 16px 16px;
}}
QGroupBox::title {{
    subcontrol-origin: padding;
    subcontrol-position: top left;
    padding: 15px 18px 0px 18px;
    background: transparent;
    border: none;
    color: #0B1D3A;
    font-size: 14px;
    font-weight: 800;
}}
QPushButton {{
    background-color: #FFFFFF;
    border: 1px solid #D2DAE6;
    border-radius: 10px;
    color: #0B1D3A;
    font-weight: 700;
    padding: 9px 18px;
}}
QPushButton:hover {{
    background-color: #F3F7FD; border: 1px solid #2E6AAD; color: #2E6AAD;
}}
QPushButton:pressed {{
    background-color: #E6ECF5;
}}
QPushButton:disabled {{
    background-color: #F1F4F9; border: 1px solid #E3E8F0; color: #A7B2C4;
}}
QPushButton#btnPrincipal, QPushButton#btnAnalisar {{
    background-color: #2E6AAD; color: #FFFFFF; border: none; border-radius: 18px; padding: 10px 26px;
}}
QPushButton#btnPrincipal:hover, QPushButton#btnAnalisar:hover {{
    background-color: #25588F; color: #FFFFFF; border: none;
}}
QPushButton#btnPrincipal:disabled, QPushButton#btnAnalisar:disabled {{
    background-color: #C9D3E3; color: #FFFFFF; border: none;
}}
QPushButton#navItem {{
    background-color: transparent; color: #C5D1E6; border: none; border-radius: 10px; padding: 11px 14px;
}}
QPushButton#navItem:hover {{
    background-color: rgba(255, 255, 255, 0.09); color: #FFFFFF; border: none;
}}
QPushButton#navItem:checked {{
    background-color: #2E6AAD; color: #FFFFFF; border: none;
}}
QPushButton#btnTituloCaixa {{
    background-color: transparent; border: none; color: #0B1D3A; padding: 2px 4px;
}}
QPushButton#btnTituloCaixa:hover {{
    background-color: transparent; border: none; color: #2E6AAD;
}}
QHeaderView::section {{
    background-color: #0B1D3A; color: #FFFFFF; padding: 10px 12px; border: none;
    border-right: 1px solid #16305C; font-weight: 700; font-size: 12px;
}}
QTreeWidget, QTableWidget, QListWidget {{
    background-color: #FFFFFF; alternate-background-color: #F7F9FC;
    border: 1px solid #E3E8F0; border-radius: 10px; gridline-color: #EEF2F7;
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: #DCE8F7; color: #0B1D3A;
}}
QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: #FFFFFF; border: 1px solid #D2DAE6; border-radius: 10px; padding: 7px 10px; color: #1B2536;
    selection-background-color: #2E6AAD; selection-color: #FFFFFF;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid #2E6AAD;
}}
QComboBox {{
    background-color: #FFFFFF; border: 1px solid #D2DAE6; border-radius: 10px; padding: 6px 12px; color: #1B2536;
}}
QComboBox:hover {{
    border: 1px solid #2E6AAD;
}}
QTabWidget::pane {{
    border: none; background: transparent;
}}
QScrollArea {{
    background: transparent; border: none;
}}
QToolTip {{
    background-color: #0B1D3A; color: #FFFFFF; border: 1px solid #0B1D3A; border-radius: 6px; padding: 6px 8px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: #C3CDDC; border-radius: 4px;
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: #2E6AAD;
}}
"""
    return qss


CORES_ATUAIS = carregar_cores_salvas()
NEON_CYAN = CORES_ATUAIS['cyan']
NEON_MAGENTA = CORES_ATUAIS['magenta']
NEON_GREEN = CORES_ATUAIS['green']
NEON_AMBER = CORES_ATUAIS['amber']
STYLE_SHEET = construir_folha_estilo(CORES_ATUAIS)


def tema_atual():
    return {'claro': TEMA_CLARO, 'projeart': TEMA_PROJEART}.get(CORES_ATUAIS.get('modo'), TEMA_ESCURO)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE_SHEET)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


# ═══════════════════════════════════════════════════════════════════
# IMPRESSÃO CASADA — casamento CNC × Ordens (fase 1: lógica de texto)
# ---------------------------------------------------------------------
# Porta fiel da lógica de casamento de posição do Conglomerador (HTML).
# A leitura/montagem de PDF de verdade (fase 2) ainda depende de arquivo
# de exemplo real pra validar — essa parte aqui é pura string/regex e já
# dá pra testar sem PDF nenhum.
# ═══════════════════════════════════════════════════════════════════
RE_COLCHETE = re.compile(r'\[\s*([A-Za-z0-9]+)\s*\]')
RE_QTD_CNC = re.compile(
    r'(?:^|\s)(?:\d+\s+)?([A-Za-z0-9@_.\-]+(?:\s*\[[^\]]*\])?)\s*-\s*OF[A-Za-z0-9\-_.]+\s*-\s*Q(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\b')
RE_POS_CNC = re.compile(r'(?:^|\s)([A-Za-z0-9@_.\-]+(?:\s*\[[^\]]*\])?)\s*-\s*OF[A-Za-z0-9\-_.]+')
RE_CNC_NUM_1 = re.compile(r'\bCNC\b[^\dA-Za-z]{0,4}(\d{3,8})\b')
RE_CNC_NUM_2 = re.compile(r'JOB\S*\s+(\d{3,8})\b', re.IGNORECASE)
RE_CNC_NUM_3 = re.compile(r'^\s*(\d{3,8})\s+Sucata', re.IGNORECASE | re.MULTILINE)
RE_ESP_1 = re.compile(r'\b\d+\s*/\s*(\d+[,.]\d+)\s*/')
RE_ESP_2 = re.compile(r'(\d+[,.]\d+)\s*MM\b', re.IGNORECASE)
RE_ESP_3 = re.compile(r'x\s*(\d+[,.]\d+)\s*x', re.IGNORECASE)
RE_OF_ORDEM = re.compile(r'\bOF:\s*(\d{5,12})\b')
RE_POS_ORDEM = re.compile(r'\bPOS:\s*([A-Za-z0-9@_.\-\[\]]+)')
RE_MARCA_ORDEM = re.compile(r'\bMARCA:\s*([^\n]+)')
RE_HIFEN_QUEBRADO = re.compile(r'-[ \t]*\n[ \t]*')


def separar_parte_da_posicao(bruto):
    """"344[A]" -> ("344", "A"). O colchete pode vir no meio também
    (ex.: "344[A]_U"), e às vezes vem com espaço antes dele no PDF de
    origem (ex.: "344 [A]") — tira ele (e o espaço) de qualquer lugar
    do texto."""
    texto = str(bruto or '').strip()
    m = RE_COLCHETE.search(texto)
    if m:
        return re.sub(r'\s*\[[^\]]*\]', '', texto).strip(), m.group(1).upper()
    return texto, None


def eh_parte_complementar(parte):
    """[A] e [1] são a peça principal; qualquer outra letra/número é a
    parte complementar (ex.: [B], [C], [2]...)."""
    return parte is not None and parte not in ('A', '1')


def normalizar_posicao_casamento(bruto):
    if not bruto:
        return ''
    s = str(bruto).strip().upper()
    s = re.sub(r'\[[^\]]*\]', '', s)
    s = re.sub(r'[\u00a0\s]', '', s)
    s = s.replace('@', '_')
    s = re.sub(r'_[A-Z]+$', '', s)   # 396_U -> 396 (mas mantem 110_2)
    s = re.sub(r'[.,;:]+$', '', s)
    return s


def variacoes_de_posicao(pos):
    """Referência TEKLA embute obra-subtrecho antes da posição
    (ex.: "2-01_-4@1" é a posição "4_1" do subtrecho "2-01"). Além do
    texto inteiro, testa o fragmento à direita do primeiro "_" — mas só
    se não for puramente numérico e curto demais (ambíguo demais)."""
    saida = [pos]
    corte = pos.find('_')
    if corte > 0:
        direita = re.sub(r'^-+', '', pos[corte + 1:])
        if direita and direita != pos:
            if not (direita.isdigit() and len(direita) < 3):
                saida.append(direita)
    return saida


def ordem_da_posicao(pos, pos_para_ordem):
    for v in variacoes_de_posicao(pos):
        if pos_para_ordem.get(v):
            return pos_para_ordem[v]
    return None


def rotulo_espessura(esp):
    return (str(esp).replace('.', ',') + ' mm') if esp else 'espessura não identificada'


def extrair_numero_cnc(linhas):
    """No Autocut o rótulo "CNC" e o número às vezes ficam em células
    separadas — três estratégias em cascata."""
    texto = '\n'.join(linhas)
    m = RE_CNC_NUM_1.search(texto)
    if m:
        return m.group(1)
    m = RE_CNC_NUM_2.search(texto)
    if m:
        return m.group(1)
    m = RE_CNC_NUM_3.search(texto)
    if m:
        return m.group(1)
    return None


RE_CNC_APOS_JOB = re.compile(r'JOB\d+\s+(\d{4,6})\b')


def extrair_numero_cnc_por_job(page):
    """Número real do CNC: o que vem logo depois do código do trabalho no
    cabeçalho ("689/ 6,35/ BC/ 2139-2-02-JOB009081  51607"), lido do texto
    cru da página (onde os dois ficam lado a lado). As outras leituras às
    vezes pegavam número de POSIÇÃO (276, 308, 266…) de outra coluna: num
    lote de 52 páginas, 27 saíram erradas — CNCs diferentes juntos sob o
    mesmo número, e a 2ª página de um CNC (só tiras, sem peças) solta,
    sem ordens. Se não achar, devolve None e vale a leitura de antes."""
    try:
        m = RE_CNC_APOS_JOB.search(page.get_text())
    except Exception:
        return None
    return m.group(1) if m else None


def extrair_numero_cnc_por_rotulo(page):
    """Número do CNC lido pela GEOMETRIA da página: o número de 5 dígitos que
    está na mesma linha do rótulo "CNC" (à direita dele). Resolve CNCs de
    guilhotina em que há uma data entre o rótulo e o número ("CNC  23/10/2026
    52269") — a leitura por texto não reconhecia esse formato e caía no plano
    B, que pegava o "698" do cabeçalho "Trabalho: 698/ 6,35/ FLX1/…" (o número
    do LOTE), juntando 10 CNCs num só. Devolve None se não achar."""
    try:
        M = page.rotation_matrix
        pal = []
        for x0, y0, x1, y1, t, *_ in page.get_text('words'):
            c = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2) * M
            pal.append((c.x, c.y, t))
    except Exception:
        return None
    tol = max(8.0, page.rect.height * 0.012)
    achados = []
    for x, y, t in pal:
        if t != 'CNC':
            continue
        cand = [(nx - x, nt) for nx, ny, nt in pal
                if abs(ny - y) <= tol and nx > x and re.fullmatch(r'\d{5}', nt)]
        if cand:
            achados.append(min(cand))
    return min(achados)[1] if achados else None


def chave_cnc(c):
    """Ordena CNCs de qualquer tipo: os numéricos primeiro (pelo número) e
    depois os de código com letras (ex.: HSG005198, do laser), pelo número
    que vem depois das letras. Antes o casamento usava int(cnc), o que
    quebrava (ou embaralhava) com código tipo "HSG005198"."""
    s = str(c)
    if s.isdigit():
        return (0, int(s), '')
    m = re.fullmatch(r'([A-Za-z]+)(\d+)', s)
    if m:
        return (1, int(m.group(2)), m.group(1).upper())
    return (2, 0, s)


def grupo_e_laser(g):
    """Conjunto do LASER: os CNCs dele têm código que começa com LETRA (ex.:
    HSG005198). O laser sempre sai por ÚLTIMO no PDF — misturado por espessura
    com o plasma (Fluxo 3) ele embaralhava a sequência do plasma."""
    return any(not str(c).isdigit() for c in g['cncs'])


def extrair_codigo_cnc_alfanumerico(page):
    """Código de CNC que tem LETRAS (ex.: "HSG005198" no laser BODOR): o
    texto de 2 a 5 letras + 4 a 8 dígitos que está na MESMA LINHA do rótulo
    "CNC", à direita dele. Sem isso o programa lia número de posição
    (679, 683, 701…) em vez do código e embaralhava as folhas. Devolve None
    se não achar."""
    try:
        M = page.rotation_matrix
        pal = []
        for x0, y0, x1, y1, t, *_ in page.get_text('words'):
            c = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2) * M
            pal.append((c.x, c.y, t))
    except Exception:
        return None
    tol = max(8.0, page.rect.height * 0.012)
    achados = []
    for x, y, t in pal:
        if t != 'CNC':
            continue
        cand = [(nx - x, nt) for nx, ny, nt in pal
                if abs(ny - y) <= tol and nx > x and re.fullmatch(r'[A-Za-z]{2,5}\d{4,8}', nt)]
        if cand:
            achados.append(min(cand))
    return min(achados)[1].upper() if achados else None


def extrair_numero_cnc_por_posicao(page):
    """Fallback quando o texto corrido não ajuda: alguns PDFs (ex.: export
    Autocut) espalham tanto o texto que o rótulo "CNC" e o número dela
    acabam longe um do outro na ordem de leitura — mas continuam
    fisicamente próximos na página (mesma coluna/linha da tabela de
    verdade). Acha a(s) palavra(s) "CNC"/"CNC:" e pega o número (3-8
    dígitos) cujo centro está mais perto fisicamente."""
    try:
        palavras = page.get_text('words')
    except Exception:
        return None
    rotulos, numeros = [], []
    for x0, y0, x1, y1, texto, *_ in palavras:
        t = str(texto).strip().upper().rstrip(':')
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if t == 'CNC':
            rotulos.append((cx, cy))
        elif re.fullmatch(r'\d{3,8}', t):
            numeros.append((cx, cy, t))
    if not rotulos or not numeros:
        return None
    melhor, melhor_dist = None, None
    for rx, ry in rotulos:
        for nx, ny, valor in numeros:
            # da MUITO mais peso ao alinhamento em X (mesma coluna da
            # tabela) do que à distância em Y — testado com um PDF real
            # onde o número certo tinha X quase idêntico ao do rótulo mas
            # ficava mais longe em Y que um número errado de outra coluna
            d = 30 * (nx - rx) ** 2 + (ny - ry) ** 2
            if melhor_dist is None or d < melhor_dist:
                melhor_dist, melhor = d, valor
    return melhor


def extrair_espessura_cnc(linhas):
    """Vem do campo "Trabalho" (ex.: "668/ 4,75/ BC/ ...")."""
    texto = '\n'.join(linhas)
    for rx in (RE_ESP_1, RE_ESP_2, RE_ESP_3):
        m = rx.search(texto)
        if m:
            return m.group(1).replace(',', '.')
    return None


def extrair_posicoes_cnc(linhas):
    """Na tabela do nesting cada referência traz a quantidade:
    "167_U - OF2113-7-58 - Q82   17   82   0"
                           ↑Q    ↑chapa ↑total ↑faltam
    Q82 é quanto a posição precisa no total; o 2º número é quanto sai
    NESTE programa."""
    achadas, complementares, rotulos_complementares = set(), set(), set()
    quantidades = {}
    for linha in linhas:
        q = RE_QTD_CNC.search(linha)
        if q:
            base, _parte = separar_parte_da_posicao(q.group(1))
            norm_pos = normalizar_posicao_casamento(base)
            if norm_pos:
                if norm_pos not in quantidades:
                    quantidades[norm_pos] = {'neste_cnc': 0, 'necessario': 0}
                quantidades[norm_pos]['neste_cnc'] += int(q.group(3))
                quantidades[norm_pos]['necessario'] = max(quantidades[norm_pos]['necessario'], int(q.group(2)))
        for m in RE_POS_CNC.finditer(linha):
            base, parte = separar_parte_da_posicao(m.group(1))
            norm_pos = normalizar_posicao_casamento(base)
            if not norm_pos or re.match(r'^Q\d+$', norm_pos, re.IGNORECASE):
                continue
            if eh_parte_complementar(parte):
                complementares.add(norm_pos)
                rotulos_complementares.add(f'{norm_pos}[{parte}]')
            else:
                achadas.add(norm_pos)
    return {'achadas': achadas, 'complementares': complementares,
            'rotulos_complementares': rotulos_complementares, 'quantidades': quantidades}


def apurar_quantidades(mapa_cnc):
    """Soma a quantidade de cada posição em TODOS os CNCs carregados — sem
    limite de folhas. Peça dividida ([A]/[B]) é contada por PARTE: cada
    metade precisa chegar na quantidade pedida."""
    soma = {}
    for c, dado in mapa_cnc.items():
        for pos, q in dado.get('quantidades', {}).items():
            if pos not in soma:
                soma[pos] = {'cortado': 0, 'necessario': 0, 'cncs': [], 'partes': {}}
            soma[pos]['cortado'] += q['neste_cnc']
            soma[pos]['necessario'] = max(soma[pos]['necessario'], q['necessario'])
            soma[pos]['cncs'].append(c)
            for parte, n in (q.get('partes') or {}).items():
                soma[pos]['partes'][parte] = soma[pos]['partes'].get(parte, 0) + n
    return soma


def posicao_completa(pos, soma):
    s = soma.get(pos)
    if not s or not s['necessario']:
        return True  # sem quantidade legível, não bloqueia
    partes = s.get('partes') or {}
    if len(partes) > 1:  # peça dividida: [A] e [B] têm que estar completas, cada uma
        return all(n >= s['necessario'] for n in partes.values())
    return s['cortado'] >= s['necessario']


def processar_paginas_cnc(paginas_texto):
    """paginas_texto: lista de listas de linhas (uma lista de linhas por
    página, já extraídas do PDF). Devolve {numero_cnc: {...}} + páginas
    sem número reconhecido — equivalente a lerCncsParaImpressao, mas já
    recebendo o texto pronto (a extração de PDF em si é a fase 2)."""
    mapa, sem_numero = {}, []
    for p, linhas in enumerate(paginas_texto):
        numero = extrair_numero_cnc(linhas)
        if not numero:
            sem_numero.append(p + 1)
            continue
        if numero not in mapa:
            mapa[numero] = {'posicoes': set(), 'complementares': set(), 'rotulos_complementares': set(),
                             'quantidades': {}, 'paginas': [], 'espessura': None}
        mapa[numero]['paginas'].append(p)
        if not mapa[numero]['espessura']:
            mapa[numero]['espessura'] = extrair_espessura_cnc(linhas)
        info = extrair_posicoes_cnc(linhas)
        for pos, q in info['quantidades'].items():
            if pos not in mapa[numero]['quantidades']:
                mapa[numero]['quantidades'][pos] = {'neste_cnc': 0, 'necessario': 0}
            mapa[numero]['quantidades'][pos]['neste_cnc'] += q['neste_cnc']
            mapa[numero]['quantidades'][pos]['necessario'] = max(
                mapa[numero]['quantidades'][pos]['necessario'], q['necessario'])
        mapa[numero]['posicoes'] |= info['achadas']
        mapa[numero]['complementares'] |= info['complementares']
        mapa[numero]['rotulos_complementares'] |= info['rotulos_complementares']
    return mapa, sem_numero


RE_SUBTR_ORDEM = re.compile(r'\bSUB_TR\s*:\s*([0-9A-Za-z]+-[0-9A-Za-z]+)', re.I)
RE_OF_CNC = re.compile(r'\bOF(\d{3,5}-[0-9A-Za-z]+-[0-9A-Za-z]+)')


def _of_trecho_da_ordem(texto):
    """Obra-trecho da ordem ("2139-5-01"): campo OBRA + campo SUB_TR do cabeçalho.
    É o mesmo valor que o CNC traz na referência de cada peça ("OF2139-5-01")."""
    obra = primeiro_padrao(texto, PADROES_PACOTE['obra'])
    m = RE_SUBTR_ORDEM.search(texto)
    return f'{obra}-{m.group(1)}'.upper() if obra and m else None


def processar_paginas_ordens(paginas_texto):
    """Equivalente a lerOrdensParaImpressao — recebe as linhas já
    extraídas do PDF de ordens (uma lista de linhas por página)."""
    ordens, pos_para_ordem = {}, {}
    atual = None
    for p, linhas in enumerate(paginas_texto):
        texto = RE_HIFEN_QUEBRADO.sub('-', '\n'.join(linhas))
        m_of = RE_OF_ORDEM.search(texto)
        if m_of:
            atual = m_of.group(1)
            if atual not in ordens:
                ordens[atual] = {'posicoes': set(), 'paginas': [], 'obra': None, 'of': None, 'chaves': set()}
            if not ordens[atual]['obra']:
                ordens[atual]['obra'] = primeiro_padrao(texto, PADROES_PACOTE['obra'])
            if not ordens[atual].get('of'):
                ordens[atual]['of'] = _of_trecho_da_ordem(texto)
            for mp in RE_POS_ORDEM.finditer(texto):
                base, _parte = separar_parte_da_posicao(mp.group(1))
                norm_pos = normalizar_posicao_casamento(base)
                if not norm_pos:
                    continue
                ordens[atual]['posicoes'].add(norm_pos)
                for v in variacoes_de_posicao(norm_pos):
                    pos_para_ordem.setdefault(v, atual)
                    ordens[atual]['chaves'].add(v)
            for mm in RE_MARCA_ORDEM.finditer(texto):
                so_marcas = re.split(r'\s+(?=[A-Z_]+:)', mm.group(1))[0]
                for bruta in so_marcas.split(','):
                    base, _parte = separar_parte_da_posicao(bruta)
                    marca = normalizar_posicao_casamento(base)
                    if not marca:
                        continue
                    for v in variacoes_de_posicao(marca):
                        pos_para_ordem.setdefault(v, atual)
                        ordens[atual]['chaves'].add(v)
        if atual:
            if not ordens[atual].get('of'):
                ordens[atual]['of'] = _of_trecho_da_ordem(texto)
            ordens[atual]['paginas'].append(p)
    return ordens, pos_para_ordem


def agrupar_cncs_para_impressao(mapa_cnc, pos_para_ordem, unir_partes, exigir_completa):
    """Une CNCs que compartilham qualquer ordem/posição (union-find) — em
    qualquer quantidade de folhas, sem limite. Quando uma posição está
    dividida em vários CNCs, TODOS eles entram no mesmo conjunto, junto com
    as posições que já estão completas deles, e o conjunto anda como um
    bloco só.

    Com exigir_completa ligado, o conjunto só é LIBERADO quando todas as
    posições dele estão completas (soma das peças de todas as folhas
    carregadas, contando por parte [A]/[B]). Se alguma ainda falta, o
    conjunto sai marcado 'pendente' (com a lista do que falta em
    'incompletas') e espera — o que já está completo segue pro próximo."""
    cncs = list(mapa_cnc.keys())
    soma = apurar_quantidades(mapa_cnc)

    ordens_do_cnc, vinculos_do_cnc, faltas_do_cnc = {}, {}, {}
    for c in cncs:
        conjunto, vinculos, faltas = set(), set(), set()
        for pos in mapa_cnc[c]['posicoes']:
            of = ordem_da_posicao(pos, pos_para_ordem)
            if of:
                conjunto.add(of)
                vinculos.add(of)
                if exigir_completa and not posicao_completa(pos, soma):
                    faltas.add(pos)
        if unir_partes:
            for pos in mapa_cnc[c]['complementares']:
                of = ordem_da_posicao(pos, pos_para_ordem)
                if of:
                    vinculos.add(of)
                    if exigir_completa and not posicao_completa(pos, soma):
                        faltas.add(pos)
        ordens_do_cnc[c], vinculos_do_cnc[c], faltas_do_cnc[c] = conjunto, vinculos, faltas

    pai = {c: c for c in cncs}

    def raiz(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    # Une todo CNC que divide uma ordem (posição) com outro — qualquer
    # quantidade de folhas, sem limite: guarda quem foi o 1º CNC de cada
    # ordem e vai ligando os seguintes a ele (resultado igual ao de
    # comparar todos os pares, mas linear — não trava com muitas folhas).
    dono_da_ordem = {}
    for c in cncs:
        for of in vinculos_do_cnc[c]:
            if of in dono_da_ordem:
                pai[raiz(c)] = raiz(dono_da_ordem[of])
            else:
                dono_da_ordem[of] = c

    buckets = {}
    for c in cncs:
        buckets.setdefault(raiz(c), []).append(c)

    grupos = []
    for membros in buckets.values():
        membros.sort(key=chave_cnc)
        ordens = set()
        faltas_pos = {}
        for c in membros:
            ordens |= ordens_do_cnc[c]
            for pos in faltas_do_cnc[c]:
                s = soma.get(pos) or {}
                faltas_pos[pos] = {'pos': pos, 'cortado': s.get('cortado', 0), 'necessario': s.get('necessario', 0),
                                    'cncs': ', '.join(s.get('cncs', []))}
        if not ordens and unir_partes:
            for c in membros:
                ordens |= vinculos_do_cnc[c]
        espessura = None
        for c in membros:
            if mapa_cnc[c]['espessura']:
                espessura = mapa_cnc[c]['espessura']
                break
        grupos.append({'cncs': membros, 'espessura': espessura,
                        'ordens': sorted(ordens, key=lambda x: int(x)),
                        'pendente': bool(faltas_pos),
                        'incompletas': sorted(faltas_pos.values(), key=lambda d: _chave_natural(d['pos']))})

    def chave_esp(e):
        try:
            return float(e) if e is not None else float('inf')
        except (TypeError, ValueError):
            return float('inf')

    grupos.sort(key=lambda g: (grupo_e_laser(g), chave_esp(g['espessura']), chave_cnc(g['cncs'][0])))
    return grupos


# ═══════════════════════════════════════════════════════════════════
# IMPRESSÃO CASADA — fase 2: ler PDF de verdade e montar o PDF final
# ═══════════════════════════════════════════════════════════════════
try:
    import pymupdf
except ImportError:
    pymupdf = None
try:
    from pypdf import PdfReader as _PypdfReader, PdfWriter as _PypdfWriter, Transformation as _PypdfTransformation
    from pypdf.generic import RectangleObject as _RectPypdf
except ImportError:
    _PypdfReader = _PypdfWriter = _RectPypdf = _PypdfTransformation = None
try:
    import numpy as _np  # noqa: E402
except ImportError:
    _np = None


def _caixa_pdf_da_pagina(doc, page):
    """MediaBox crua da página (x0, y0, x1, y1) no espaço do PDF, SEM
    rotação — é nesse espaço que a caixa de tinta é medida."""
    try:
        tipo, val = doc.xref_get_key(page.xref, 'MediaBox')
        if tipo == 'array':
            n = [float(t) for t in val.strip('[]').split()]
            if len(n) == 4:
                return n[0], n[1], n[2], n[3]
    except Exception:
        pass
    mb = page.mediabox
    return 0.0, 0.0, mb.width, mb.height


def _recortar_e_escalar_pagina(doc, page, x0, y0, x1, y1, alvo_w, alvo_h):
    """Faz a região (x0,y0)-(x1,y1) da página virar uma folha (0,0)-(alvo_w,
    alvo_h), esticando cada eixo pra encher a folha: aplica a matriz de
    escala/deslocamento no começo do conteúdo e troca MediaBox/CropBox.
    A rotação (/Rotate) da página fica como estava. Remove TrimBox/ArtBox/
    BleedBox herdadas (ficariam com o tamanho antigo)."""
    sx = alvo_w / (x1 - x0)
    sy = alvo_h / (y1 - y0)
    tx, ty = -x0 * sx, -y0 * sy
    page.clean_contents()
    partes = [doc.xref_stream(x) for x in page.get_contents()]
    corpo = b'\n'.join(p for p in partes if p)
    novo = ('q %.6f 0 0 %.6f %.6f %.6f cm\n' % (sx, sy, tx, ty)).encode('ascii') + corpo + b'\nQ'
    xr = doc.get_new_xref()
    doc.update_object(xr, '<<>>')
    doc.update_stream(xr, novo)
    doc.xref_set_key(page.xref, 'Contents', '%d 0 R' % xr)
    caixa = '[0 0 %.4f %.4f]' % (alvo_w, alvo_h)
    doc.xref_set_key(page.xref, 'MediaBox', caixa)
    doc.xref_set_key(page.xref, 'CropBox', caixa)
    for chave in ('TrimBox', 'ArtBox', 'BleedBox'):
        doc.xref_set_key(page.xref, chave, 'null')


A4_PT = (595.28, 841.89)

# Carimbado nos metadados do PDF gerado (campo "Criador") — assim, quando
# aparecer uma página fora do esperado, dá pra saber na hora se o PDF saiu
# desta versão do script ou de uma mais antiga que ficou guardada por aí.
VERSAO_SCRIPT = '2026-11-04 (várias ordens)'


def _pagina_eh_a4(page, tol=1.0):
    """True se a página (já com a rotação aplicada, como aparece na tela e
    na impressora) tem tamanho A4 — em pé ou deitada."""
    w, h = page.rect.width, page.rect.height
    return ((abs(w - A4_PT[0]) <= tol and abs(h - A4_PT[1]) <= tol) or
            (abs(w - A4_PT[1]) <= tol and abs(h - A4_PT[0]) <= tol))


def _garantir_a4(doc):
    """Rede de segurança: confere TODAS as páginas do PDF montado e, se
    alguma ficou fora de A4 (pequena, esticada de menos, tamanho original
    da chapa etc.), ajusta ela na hora — recorta a margem vazia (quando dá
    pra medir) e estica pra encher a folha, igual ao ajuste normal.
    Devolve (corrigidas, falhas)."""
    fora = [i for i in range(doc.page_count) if not _pagina_eh_a4(doc[i])]
    if not fora:
        return 0, 0
    caixas = None
    tmp = os.path.join(tempfile.gettempdir(), 'ppcp_conferir_a4_%d.pdf' % os.getpid())
    try:
        doc.save(tmp)
        caixas = calcular_areas_de_tinta(tmp)
    except Exception:
        caixas = None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    corrigidas = falhas = 0

    def _palavras(pg):
        try:
            return collections.Counter(w[4] for w in pg.get_text('words') if w[4].strip())
        except Exception:
            return collections.Counter()

    for i in fora:
        try:
            esperado = _palavras(doc[i])
            c = caixas[i] if caixas and i < len(caixas) else None
            tentativas = [c if (c and c['right'] - c['left'] > 5 and c['top'] - c['bottom'] > 5) else None, 'inteira']
            feito = False
            for tent in tentativas:
                if tent is None:
                    continue
                tmp = pymupdf.open()          # trabalha numa cópia da página: só troca se NENHUM texto se perdeu
                try:
                    tmp.insert_pdf(doc, from_page=i, to_page=i)
                    x0, y0, x1, y1 = _caixa_pdf_da_pagina(tmp, tmp[0])
                    if tent != 'inteira':
                        x0, y0, x1, y1 = tent['left'], tent['bottom'], tent['right'], tent['top']
                    alvo = (A4_PT[1], A4_PT[0]) if (x1 - x0) > (y1 - y0) else A4_PT
                    _recortar_e_escalar_pagina(tmp, tmp[0], x0, y0, x1, y1, alvo[0], alvo[1])
                    if not (esperado - _palavras(tmp[0])):
                        doc.delete_page(i)
                        doc.insert_pdf(tmp, start_at=i)
                        feito = True
                finally:
                    tmp.close()
                if feito:
                    break
            if feito:
                corrigidas += 1
            else:
                falhas += 1
        except Exception:
            falhas += 1
    return corrigidas, falhas


def _linhas_da_pagina_pymupdf(page):
    """Reconstroi linhas de texto usando o próprio agrupamento em
    (bloco,linha) que o PyMuPDF já calcula a partir da ordem real dos
    operadores de texto do PDF — mais confiável que reagrupar por
    coordenada Y na unha, que quebra em texto girado/rotacionado (onde
    uma "linha" de leitura tem Y bem diferente entre as palavras, não X)."""
    palavras = page.get_text('words')  # (x0,y0,x1,y1,texto,bloco,linha,word_no)
    grupos = {}
    for x0, y0, _x1, _y1, texto, bloco, linha, word_no in palavras:
        if not texto or not texto.strip():
            continue
        grupos.setdefault((bloco, linha), []).append((word_no, x0, y0, texto))
    linhas_final = []
    for chave, itens in grupos.items():
        itens.sort(key=lambda it: it[0])  # ordem real de leitura (word_no)
        y_medio = sum(it[2] for it in itens) / len(itens)
        linhas_final.append((y_medio, chave, ' '.join(it[3] for it in itens)))
    linhas_final.sort(key=lambda l: (l[0], l[1]))  # topo->baixo; empate por (bloco,linha)
    return [t for _, _, t in linhas_final]


def ler_linhas_por_pagina(caminho_pdf):
    """Devolve uma lista (uma por página) de listas de linhas de texto."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf" — rode "pip install pymupdf" e abra o app de novo')
    doc = pymupdf.open(caminho_pdf)
    try:
        return [_linhas_da_pagina_pymupdf(p) for p in doc]
    finally:
        doc.close()


def calcular_areas_de_tinta(caminho_pdf):
    """Renderiza cada página (sem rotação, propositalmente) e mede onde
    tem conteúdo de verdade — pra recortar páginas cuja caixa declarada é
    bem maior que o desenho. Devolve uma lista (uma por página) de
    {'left','bottom','right','top'} em pontos, ou None se não vale a
    pena recortar (página em branco, ou ocupação > 65% da caixa)."""
    doc = pymupdf.open(caminho_pdf)
    areas = []
    try:
        for page in doc:
            rot_original = page.rotation
            page.set_rotation(0)
            base_w, base_h = page.rect.width, page.rect.height
            escala = min(1.0, 700 / max(base_w, base_h, 1))
            pix = page.get_pixmap(matrix=pymupdf.Matrix(escala, escala),
                                   colorspace=pymupdf.csRGB, alpha=False)
            page.set_rotation(rot_original)

            largura, altura = pix.width, pix.height
            buf = _np.frombuffer(pix.samples, dtype=_np.uint8).reshape(altura, largura, 3)
            escuro = _np.any(buf[::2, ::2] < 245, axis=2)  # amostra de 2 em 2px
            ys, xs = _np.nonzero(escuro)
            if len(xs) == 0:
                areas.append(None)
                continue
            x0, x1 = int(xs.min()) * 2, int(xs.max()) * 2
            y0, y1 = int(ys.min()) * 2, int(ys.max()) * 2
            x0, y0 = max(0, x0 - 1), max(0, y0 - 1)
            x1 = min(largura - 1, x1 + 1)
            y1 = min(altura - 1, y1 + 1)
            L, R = x0 / escala, (x1 + 1) / escala
            T, B = base_h - (y0 / escala), base_h - ((y1 + 1) / escala)
            ocupacao = ((R - L) * (T - B)) / max(base_w * base_h, 1)
            if ocupacao > 0.65:
                areas.append(None)
                continue
            margem = max(R - L, T - B) * 0.02 + 5  # +5pt fixo, pra nao cortar rente em paginas com conteudo colado na borda
            areas.append({'left': max(0, L - margem), 'bottom': max(0, B - margem),
                           'right': min(base_w, R + margem), 'top': min(base_h, T + margem)})
    finally:
        doc.close()
    return areas


def _caixa_para_rect_pymupdf(page, caixa):
    """Converte a caixa {'left','bottom','right','top'} (pontos PDF,
    origem embaixo) pra um pymupdf.Rect (origem em cima) na página SEM
    rotação — é o espaço em que show_pdf_page/clip trabalha."""
    altura_sem_rot = page.rect.height if page.rotation == 0 else (
        page.rect.width if page.rotation in (90, 270) else page.rect.height)
    # usa o cropbox nativo da pagina (sem rotacao) como referencia de altura
    box = page.mediabox
    h = box.height
    return pymupdf.Rect(caixa['left'], h - caixa['top'], caixa['right'], h - caixa['bottom'])


def preparar_pdf_ordens(caminho_ordens):
    """Aceita UM PDF de ordens ou VÁRIOS (um por obra, como os PDFs de nesting).
    Com vários, junta tudo num PDF temporário na ordem em que foram carregados.
    Ordem que apareça de novo (no mesmo arquivo ou em outro) vale só a 1ª vez —
    senão sairia impressa em duplicidade. Devolve (caminho_efetivo, pasta_temporaria,
    ordens_repetidas_ignoradas); com um PDF sem repetição nada é copiado e o
    caminho volta o mesmo."""
    if isinstance(caminho_ordens, (str, bytes, os.PathLike)):
        caminhos = [caminho_ordens]
    else:
        caminhos = [c for c in (caminho_ordens or []) if c]
    if not caminhos:
        raise RuntimeError('Nenhum PDF de ordens foi selecionado.')
    vistas, repetidas, plano = set(), [], []
    precisa_novo = len(caminhos) > 1
    for cam in caminhos:
        doc = pymupdf.open(cam)
        capas = []                                   # (pagina, ordem) de cada capa
        for i, pg in enumerate(doc):
            m = RE_OF_ORDEM.search(RE_HIFEN_QUEBRADO.sub('-', pg.get_text()))
            if m:
                capas.append((i, m.group(1)))
        if not capas:                                 # não achei capa: mantém o arquivo inteiro
            plano.append((cam, list(range(doc.page_count))))
            doc.close()
            continue
        manter, no_arquivo = [], set()
        capas_por_pag = dict(capas)
        descartando = None
        for i in range(doc.page_count):
            if i in capas_por_pag:
                of = capas_por_pag[i]
                if of in vistas or of in no_arquivo:
                    descartando = True
                    precisa_novo = True
                    if of not in repetidas:
                        repetidas.append(of)
                else:
                    descartando = False
                    no_arquivo.add(of)
            if descartando is None:                   # antes da 1ª capa: não é de ordem nenhuma
                if len(caminhos) > 1:
                    continue
                manter.append(i)
                continue
            if not descartando:
                manter.append(i)
        vistas |= no_arquivo
        plano.append((cam, manter))
        doc.close()
    if not precisa_novo:
        return caminhos[0], None, []
    pasta = tempfile.mkdtemp(prefix='ordens_unidas_')
    saida = pymupdf.open()
    for cam, manter in plano:
        doc = pymupdf.open(cam)
        ini = None
        for k, i in enumerate(manter):               # copia em blocos de páginas seguidas
            if ini is None:
                ini = ant = i
            elif i == ant + 1:
                ant = i
            else:
                saida.insert_pdf(doc, from_page=ini, to_page=ant)
                ini = ant = i
        if ini is not None:
            saida.insert_pdf(doc, from_page=ini, to_page=ant)
        doc.close()
    cam_final = os.path.join(pasta, 'ordens_unidas.pdf')
    saida.save(cam_final)
    saida.close()
    return cam_final, pasta, repetidas


def limpar_tmp_ordens(pasta):
    if pasta:
        try:
            import shutil
            shutil.rmtree(pasta, ignore_errors=True)
        except Exception:
            pass


def _chave_espessura_grupo(g):
    try:
        return float(str(g['espessura']).replace(',', '.')) if g['espessura'] else float('inf')
    except (TypeError, ValueError):
        return float('inf')


def particionar_por_obra(mapa_cnc, ordens, pos_para_ordem):
    """Separa o casamento por OBRA-TRECHO. Com várias obras no mesmo lote, a mesma
    posição pode existir em obras diferentes ("700_1" em 2139-5-02 e em 2160-2-02);
    casando só pelo nome da posição, o CNC de uma obra pegava a ordem de outra.
    Aqui cada obra-trecho (lida na referência das peças do CNC: "OF2139-5-01")
    casa SÓ com as ordens da mesma obra-trecho (campos OBRA + SUB_TR da ordem);
    as ordens em que não deu pra ler o obra-trecho ficam como reserva.
    Lote com uma obra só (ou sem obra-trecho legível) volta {None: (todos, dict)}
    — o mesmo caminho de sempre."""
    ofs = {c: m.get('of') for c, m in mapa_cnc.items()}
    conhecidos = sorted({o for o in ofs.values() if o})
    if len(conhecidos) <= 1 and not any(o for o in ofs.values() if o and o not in conhecidos):
        return {None: (list(mapa_cnc), pos_para_ordem)}
    saida = {}
    for P in conhecidos:
        d = {}
        for exato in (True, False):
            for o, dado in ordens.items():
                of_o = dado.get('of')
                if (exato and of_o == P) or (not exato and not of_o):
                    for k in dado.get('chaves', ()):
                        d.setdefault(k, o)
        saida[P] = ([c for c in mapa_cnc if ofs[c] == P], d)
    sem_of = [c for c in mapa_cnc if not ofs[c]]
    if sem_of:
        saida[None] = (sem_of, pos_para_ordem)
    return saida


def ler_relatorios_fluxos_pacote(caminhos):
    """Um ou VÁRIOS relatórios (um por obra): junta as linhas de todos. Uma
    mesma ordem que apareça em dois relatórios vale só a 1ª vez."""
    if isinstance(caminhos, (str, bytes, os.PathLike)):
        caminhos = [caminhos]
    linhas, vistas = [], set()
    for cam in caminhos:
        for r in ler_relatorio_fluxos_pacote(cam):
            o = r.get('ordem')
            if o:
                if o in vistas:
                    continue
                vistas.add(o)
            linhas.append(r)
    return linhas


def _analisar_impressao_casada(caminhos_cnc, caminho_ordens, *, unir_partes=True, exigir_completa=True,
                                caminho_relatorio_fluxos=None, caminho_lantek=None, progresso=None):
    """Lê os PDFs de CNC + Ordens e faz o casamento — SEM montar o PDF
    físico. É o motor compartilhado entre gerar_impressao_casada (que
    além disso monta o PDF) e analisar_impressao_casada (só confere,
    pro botão "Conferir antes")."""
    def avisa(msg):
        if progresso:
            progresso(msg)

    avisa('Lendo PDFs dos CNCs…')
    paginas_por_cnc_arquivo = [ler_linhas_por_pagina(c) for c in caminhos_cnc]
    mapa_cnc, sem_numero = {}, []
    ofs_do_cnc = {}                                   # {CNC: Counter de obra-trecho lidos nas referências}
    for f, paginas in enumerate(paginas_por_cnc_arquivo):
        doc_posicional = None
        try:
            doc_posicional = pymupdf.open(caminhos_cnc[f])
        except Exception:
            doc_posicional = False
        for p, linhas_pg in enumerate(paginas):
            numero = None
            if doc_posicional:
                numero = (extrair_numero_cnc_por_job(doc_posicional[p]) or extrair_codigo_cnc_alfanumerico(doc_posicional[p])
                          or extrair_numero_cnc_por_rotulo(doc_posicional[p]))
            if not numero:
                numero = extrair_numero_cnc(linhas_pg)
            if not numero and doc_posicional:
                numero = extrair_numero_cnc_por_posicao(doc_posicional[p])
            if not numero:
                sem_numero.append({'arquivo': os.path.basename(caminhos_cnc[f]), 'pagina': p + 1})
                continue
            if numero not in mapa_cnc:
                mapa_cnc[numero] = {'posicoes': set(), 'complementares': set(), 'rotulos_complementares': set(),
                                     'quantidades': {}, 'paginas': [], 'espessura': None}
            mapa_cnc[numero]['paginas'].append({'arquivo': f, 'indice': p})
            ofs_do_cnc.setdefault(numero, collections.Counter()).update(
                x.upper() for x in RE_OF_CNC.findall('\n'.join(linhas_pg)))
            if not mapa_cnc[numero]['espessura']:
                mapa_cnc[numero]['espessura'] = extrair_espessura_cnc(linhas_pg)
            info = extrair_posicoes_cnc(linhas_pg)
            for pos, q in info['quantidades'].items():
                if pos not in mapa_cnc[numero]['quantidades']:
                    mapa_cnc[numero]['quantidades'][pos] = {'neste_cnc': 0, 'necessario': 0}
                mapa_cnc[numero]['quantidades'][pos]['neste_cnc'] += q['neste_cnc']
                mapa_cnc[numero]['quantidades'][pos]['necessario'] = max(
                    mapa_cnc[numero]['quantidades'][pos]['necessario'], q['necessario'])
            mapa_cnc[numero]['posicoes'] |= info['achadas']
            mapa_cnc[numero]['complementares'] |= info['complementares']
            mapa_cnc[numero]['rotulos_complementares'] |= info['rotulos_complementares']
        if doc_posicional:
            doc_posicional.close()
    for numero, m_ in mapa_cnc.items():
        cont_of = ofs_do_cnc.get(numero)
        m_['of'] = cont_of.most_common(1)[0][0] if cont_of else None

    # Quantidades pela posição das palavras na página (colunas Chapa/Total):
    # a leitura por texto só funciona em alguns layouts. Onde ela não achou
    # a quantidade de uma posição (ex.: laser, guilhotina, Autocut girado),
    # usa esta — assim a regra "só posição completa" vale pra TODA máquina.
    # Quando a leitura por texto já achou, ela é mantida como estava.
    for f in range(len(caminhos_cnc)):
        try:
            visual_f = ler_quantidades_visuais(caminhos_cnc[f])
        except Exception:
            continue
        for numero, m in mapa_cnc.items():
            ja_lidas = {k for k, q in m['quantidades'].items() if not q.get('partes_de_posicao_visual')}
            for pg in m['paginas']:
                if pg['arquivo'] != f or pg['indice'] >= len(visual_f):
                    continue
                for (pos, parte), r in visual_f[pg['indice']].items():
                    if pos in ja_lidas:
                        continue
                    q = m['quantidades'].setdefault(pos, {'neste_cnc': 0, 'necessario': 0, 'partes': {},
                                                           'partes_de_posicao_visual': True})
                    q['neste_cnc'] += r['chapa']
                    q['necessario'] = max(q['necessario'], r['q'])
                    q['partes'][parte] = q['partes'].get(parte, 0) + r['chapa']
                    if pos not in m['posicoes'] and pos not in m['complementares']:
                        if parte and eh_parte_complementar(parte):   # posição que o leitor por texto não viu
                            m['complementares'].add(pos)
                            m['rotulos_complementares'].add(f'{pos}[{parte}]')
                        else:
                            m['posicoes'].add(pos)

    avisa('Lendo ordens de fabricação…')
    paginas_ordens = ler_linhas_por_pagina(caminho_ordens)
    ordens, pos_para_ordem = processar_paginas_ordens(paginas_ordens)

    if not mapa_cnc:
        raise RuntimeError('Nenhum número de CNC foi reconhecido nos PDFs de nesting.')
    if not ordens:
        raise RuntimeError('Nenhuma Ordem de Fabricação foi reconhecida no PDF de ordens.')

    avisa('Casando posições e montando sequência…')
    particoes = particionar_por_obra(mapa_cnc, ordens, pos_para_ordem)
    multi_obra = len(particoes) > 1 or (len(particoes) == 1 and None not in particoes)
    grupos_todos = []
    for P, (cncs_p, ppo_p) in particoes.items():
        gs = agrupar_cncs_para_impressao({c: mapa_cnc[c] for c in cncs_p}, ppo_p, unir_partes, exigir_completa)
        for g_ in gs:
            g_['of'] = P
        grupos_todos += gs
    if multi_obra:      # obra por obra; dentro de cada uma: espessura, laser por último
        grupos_todos.sort(key=lambda g_: (g_['of'] or '~', grupo_e_laser(g_), _chave_espessura_grupo(g_), chave_cnc(g_['cncs'][0])))
    grupos = [g for g in grupos_todos if not g['pendente']]          # completos: vão pro PDF
    grupos_pendentes = [g for g in grupos_todos if g['pendente']]    # esperam a peça que falta

    if caminho_relatorio_fluxos:
        avisa('Lendo relatório(s) de fluxos…')
        linhas_rel = ler_relatorios_fluxos_pacote(caminho_relatorio_fluxos)
        aplicar_relatorio_aos_grupos(grupos, mapa_cnc, ordens, linhas_rel)

    ordens_usadas = set()
    for g in grupos:
        ordens_usadas |= set(g['ordens'])
    ordens_pendentes = set()
    for g in grupos_pendentes:
        ordens_pendentes |= set(g['ordens'])
    ordens_orfas = sorted((o for o in ordens if o not in ordens_usadas and o not in ordens_pendentes),
                          key=lambda x: int(x))
    cncs_sem_ordem = [c for g in grupos if not g['ordens'] for c in g['cncs']]

    incompletas = []
    if exigir_completa:
        for P, (cncs_p, _ppo) in particoes.items():
            soma_qtd = apurar_quantidades({c: mapa_cnc[c] for c in cncs_p})
            for pos in sorted(soma_qtd):
                if not posicao_completa(pos, soma_qtd):
                    s = soma_qtd[pos]
                    item_inc = {'pos': pos, 'cortado': s['cortado'], 'necessario': s['necessario'],
                                 'cncs': ', '.join(s['cncs'])}
                    if multi_obra:
                        item_inc['of'] = P
                    incompletas.append(item_inc)

    partes_complementares = []
    for c in sorted(mapa_cnc, key=chave_cnc):
        for pos in mapa_cnc[c]['rotulos_complementares']:
            partes_complementares.append({'cnc': c, 'pos': pos})

    # ── conferência extra de segurança contra o Lantek (opcional) ──
    # a Ordem sem CNC casado pode ser porque (a) a peça JÁ foi
    # programada/nesteada no CAM só que o PDF desse CNC não foi
    # carregado aqui, ou (b) a peça nem chegou a ser programada em
    # lugar nenhum ainda — bem mais grave, porque passa despercebido:
    # ninguém vai cortar uma peça que não existe em nenhum nesting.
    ordens_sem_programacao, ordens_programadas_sem_cnc = [], []
    if caminho_lantek:
        avisa('Lendo relatório do Lantek (Análise de Nestings)…')
        lantek_programado, _total_lantek = ler_relatorio_lantek(caminho_lantek)
        ordens_sem_programacao, ordens_programadas_sem_cnc = conferir_ordens_com_lantek(
            ordens_orfas, ordens, lantek_programado)

    # obra de cada conjunto: o relatório de fluxos já preencheu; sem ele, vem da
    # própria ordem (campo OBRA do PDF) — assim dá pra escolher/separar por obra
    for g in grupos + grupos_pendentes:
        if not g.get('obra'):
            if g.get('of'):                       # obra-trecho lido nas referências dos CNCs deste conjunto
                g['obra'] = g['of']
                continue
            contagem = {}
            for o in g['ordens']:
                ob = ordens.get(o, {}).get('of') or ordens.get(o, {}).get('obra')
                if ob:
                    contagem[ob] = contagem.get(ob, 0) + 1
            if not contagem:                      # CNC sem ordem: fica na obra do próprio CNC
                for c in g['cncs']:
                    ob = mapa_cnc[c].get('of')
                    if ob:
                        contagem[ob] = contagem.get(ob, 0) + 1
            if contagem:
                g['obra'] = sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    return {
        'caminhos_cnc': list(caminhos_cnc),
        'grupos_pendentes': grupos_pendentes, 'ordens_pendentes': ordens_pendentes,
        'mapa_cnc': mapa_cnc, 'ordens': ordens, 'pos_para_ordem': pos_para_ordem, 'grupos': grupos,
        'multi_obra': multi_obra,
        'particao_do_cnc': {c: P for P, (cncs_p, _p) in particoes.items() for c in cncs_p},
        'pos_para_ordem_por_cnc': {c: ppo_p for P, (cncs_p, ppo_p) in particoes.items() for c in cncs_p},
        'ordens_usadas': ordens_usadas, 'ordens_orfas': ordens_orfas, 'cncs_sem_ordem': cncs_sem_ordem,
        'sem_numero': sem_numero, 'incompletas': incompletas, 'partes_complementares': partes_complementares,
        'ordens_sem_programacao': ordens_sem_programacao,
        'ordens_programadas_sem_cnc': ordens_programadas_sem_cnc,
    }


def _resumo_obras(grupos):
    """[{obra, conjuntos, ordens}] das obras que têm conjunto no PDF (ordem de aparição)."""
    por_obra = {}
    for g in grupos:
        ob = g.get('obra') or '—'
        d = por_obra.setdefault(ob, {'obra': ob, 'conjuntos': 0, 'ordens': 0})
        d['conjuntos'] += 1
        d['ordens'] += len(g['ordens'])
    return list(por_obra.values())


def _conferencia_filtrada(conf, cncs):
    """Conferência só com os CNCs dados (e as ordens deles) — usada quando o PDF
    não leva tudo (obras escolhidas / um PDF por obra), pra não marcar como
    "fora do PDF" um CNC que de propósito está em outro arquivo."""
    cncs = set(cncs)
    cp = [c for c in conf['cnc_posicoes'] if c['cnc'] in cncs]
    ordens_ok = {p['ordem'] for c in cp for p in c['posicoes'] if p['ordem']}
    return {'cnc_posicoes': cp, 'lista_ordens': [o for o in conf['lista_ordens'] if o['ordem'] in ordens_ok]}


def nome_pdf_da_obra(caminho_base, obra):
    """impressao.pdf + obra 2139 -> impressao_obra_2139.pdf."""
    base, ext = os.path.splitext(caminho_base)
    seguro = re.sub(r'[^A-Za-z0-9_-]+', '_', str(obra)).strip('_') or 'sem_obra'
    return f'{base}_obra_{seguro}{ext or ".pdf"}'


def _resumo_pendentes(a):
    """Conjuntos que esperam peça(s): CNCs, espessura, ordens seguradas e o que falta."""
    return [{'cncs': g['cncs'], 'espessura': g['espessura'], 'ordens': g['ordens'],
             'incompletas': g['incompletas']} for g in a.get('grupos_pendentes', [])]


def _chave_natural(texto):
    """Ordena "276_2" antes de "276_10" e "9" antes de "10"."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(texto))]


RE_REF_QTD_VISUAL = re.compile(
    r'([A-Za-z0-9@_.\-]+(?:\s*\[[^\]]*\])?)\s*-\s*OF[A-Za-z0-9\-_.]+\s*-\s*Q(\d+)')


def ler_quantidades_visuais(caminho_pdf):
    """Lê a tabela de itens de cada CNC pela POSIÇÃO das palavras na página
    (colunas Chapa / Total / Faltam), já com a rotação da página aplicada.
    Serve pra exibir as quantidades na conferência — não é usada pelo motor
    de casamento. Devolve, por página, {(posição, parte): {'chapa', 'q',
    'faltam'}}: 'chapa' = peças deste CNC; 'q' = quanto a posição pede no
    total. A parte ([A]/[B]) entra na chave porque cada metade da peça
    dividida tem a própria quantidade."""
    doc = pymupdf.open(caminho_pdf)
    saida = []
    for page in doc:
        M = page.rotation_matrix
        pal = []
        for x0, y0, x1, y1, t, *_ in page.get_text('words'):
            c = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2) * M
            pal.append((c.x, c.y, t))
        res = {}
        cab = [(x, y) for x, y, t in pal if t == 'Chapa']
        if cab:
            xc, yc = cab[0]
            xf = next((x for x, y, t in pal if t == 'Faltam' and abs(y - yc) < 8), None)
            zona = sorted(((x, y, t) for x, y, t in pal if y > yc + 6 and x < xc - 25), key=lambda w: w[1])
            linhas, atual = [], []
            for w in zona:
                if atual and abs(w[1] - atual[-1][1]) > 6:
                    linhas.append(atual)
                    atual = []
                atual.append(w)
            if atual:
                linhas.append(atual)

            def numero(xcol, y_ref):
                if xcol is None:
                    return None
                cand = [(abs(y - y_ref), t) for x, y, t in pal
                        if abs(x - xcol) <= 22 and abs(y - y_ref) <= 10 and re.fullmatch(r'\d+', t)]
                return int(min(cand)[1]) if cand else None

            for lin in linhas:
                y_ref = sum(w[1] for w in lin) / len(lin)
                m = RE_REF_QTD_VISUAL.search(' '.join(t for x, y, t in sorted(lin)))
                if not m:
                    continue
                base, parte = separar_parte_da_posicao(m.group(1))
                pos = normalizar_posicao_casamento(base)
                if not pos:
                    continue
                reg = res.setdefault((pos, parte or ''), {'chapa': 0, 'q': 0, 'faltam': None})
                reg['chapa'] += numero(xc, y_ref) or 0
                reg['q'] = max(reg['q'], int(m.group(2)))
                reg['faltam'] = numero(xf, y_ref)
        saida.append(res)
    doc.close()
    return saida


def calcular_completude(entradas, pedido):
    """entradas: [(cnc, qtd_neste_cnc)] já na ORDEM dos CNCs; pedido: quanto a
    posição pede no total. Conta peça por peça: cada CNC fica PARCIAL enquanto
    a soma acumulada não chega no pedido; COMPLETA só no CNC em que aparece a
    ÚLTIMA peça (marcado 'ultima'). Sem quantidade lida: 'desconhecida'."""
    soma, ultima, por_cnc = 0, None, []
    for cnc, qtd in entradas:
        if qtd is None or not pedido:
            por_cnc.append({'cnc': cnc, 'qtd': qtd, 'acumulado': None, 'estado': 'desconhecida', 'ultima': False})
            continue
        soma += qtd
        completa = soma >= pedido
        e_ultima = completa and ultima is None
        if e_ultima:
            ultima = cnc
        por_cnc.append({'cnc': cnc, 'qtd': qtd, 'acumulado': soma,
                        'estado': 'completa' if completa else 'parcial', 'ultima': e_ultima})
    if not pedido or any(q is None for _c, q in entradas):
        status = 'desconhecida'
    else:
        status = 'completa' if soma >= pedido else 'parcial'
    return {'por_cnc': por_cnc, 'soma': soma, 'status': status, 'ultima_em': ultima}


def montar_conferencia_cnc_ordens(a, exigir_completa=True):
    """Para o "Conferir antes": de cada CNC, as posições que existem no PDF
    dele (com a ordem de cada uma, as quantidades e se a posição está PARCIAL
    ou COMPLETA) e, do outro lado, a lista das ordens. Só LÊ o que o motor
    de casamento já calculou — não altera o casamento."""
    mapa_cnc, ordens, pos_para_ordem = a['mapa_cnc'], a['ordens'], a['pos_para_ordem']
    usadas = a['ordens_usadas']
    multi_obra = bool(a.get('multi_obra'))
    particao = a.get('particao_do_cnc', {})                 # {CNC: obra-trecho} (só quando há várias obras)
    ppo_por_cnc = a.get('pos_para_ordem_por_cnc', {})
    somas_motor = {}
    for c_, P_ in (particao.items() if multi_obra else []):
        somas_motor.setdefault(P_, {})[c_] = mapa_cnc[c_]
    somas_motor = {P_: apurar_quantidades(m_) for P_, m_ in somas_motor.items()}
    soma_motor = apurar_quantidades(mapa_cnc) if not multi_obra else None
    caminhos = a.get('caminhos_cnc') or []
    conjunto_do_cnc, pendente_do_cnc = {}, {}
    for g in a.get('grupos', []):
        for c in g['cncs']:
            conjunto_do_cnc[c] = list(g['cncs'])
    for g in a.get('grupos_pendentes', []):
        for c in g['cncs']:
            conjunto_do_cnc[c] = list(g['cncs'])
            pendente_do_cnc[c] = g
    ordens_pend = a.get('ordens_pendentes', set())

    cache_visual = {}

    def visual(arquivo):
        if arquivo not in cache_visual:
            try:
                cache_visual[arquivo] = ler_quantidades_visuais(caminhos[arquivo]) if caminhos else []
            except Exception:
                cache_visual[arquivo] = []
        return cache_visual[arquivo]

    # 1) itens (posição + parte) de cada CNC, com a quantidade lida
    itens_cnc = {}
    for c in mapa_cnc:
        m = mapa_cnc[c]
        itens = {}
        for pg in m['paginas']:
            paginas = visual(pg['arquivo'])
            for chave, r in (paginas[pg['indice']] if pg['indice'] < len(paginas) else {}).items():
                it = itens.setdefault(chave, {'chapa': 0, 'q': 0})
                it['chapa'] += r['chapa']
                it['q'] = max(it['q'], r['q'])
        achadas = {k[0] for k in itens}
        for pos in set(m['posicoes']) | set(m['complementares']) | set(m['quantidades']):
            if pos not in achadas:             # o leitor por posição não achou: usa o do motor
                q = m['quantidades'].get(pos)
                itens[(pos, '')] = {'chapa': q['neste_cnc'] if q else None, 'q': q['necessario'] if q else 0}
        itens_cnc[c] = itens

    # 2) por item, em todos os CNCs: soma acumulada, PARCIAL/COMPLETA, onde está a última peça
    globais = {}
    for c in sorted(mapa_cnc, key=chave_cnc):
        for chave, it in itens_cnc[c].items():
            g = globais.setdefault((particao.get(c),) + chave, {'q': 0, 'entradas': []})
            g['q'] = max(g['q'], it['q'] or 0)
            g['entradas'].append((c, it['chapa']))
    for g in globais.values():
        r = calcular_completude(g['entradas'], g['q'] or None)
        g['por_cnc'] = {d['cnc']: d for d in r['por_cnc']}
        g['ordem_cncs'] = r['por_cnc']
        g['soma'], g['status'], g['ultima_em'] = r['soma'], r['status'], r['ultima_em']

    cncs_da_ordem = {}
    cnc_posicoes = []
    for c in sorted(mapa_cnc, key=chave_cnc):
        m = mapa_cnc[c]
        linhas = []
        P_c = particao.get(c)
        soma_c = somas_motor.get(P_c, {}) if multi_obra else soma_motor
        for (pos, parte) in sorted(itens_cnc[c], key=lambda k: (_chave_natural(k[0]), k[1])):
            g = globais[(P_c, pos, parte)]
            d = g['por_cnc'][c]
            of = ordem_da_posicao(pos, ppo_por_cnc.get(c, pos_para_ordem))
            if not of:
                situacao = 'sem ordem no PDF das Ordens'
            elif exigir_completa and not posicao_completa(pos, soma_c):
                situacao = 'incompleta — falta peça nos CNCs carregados'
            else:
                situacao = 'ok'
            if of:
                cncs_da_ordem.setdefault(of, set()).add(c)
            rotulo = pos + (f' [{parte}]' if parte else '') + (f' · {P_c}' if (multi_obra and P_c) else '')
            linhas.append({
                'pos': rotulo, 'pos_base': pos, 'parte_rotulo': parte,
                'parte': bool(parte) and eh_parte_complementar(parte),
                'ordem': of, 'situacao': situacao,
                'qtd_neste_cnc': d['qtd'], 'pedido': g['q'] or None,
                'acumulado': d['acumulado'], 'estado': d['estado'], 'ultima': d['ultima'],
                'soma_total': g['soma'], 'status_total': g['status'], 'ultima_em': g['ultima_em'],
                'cncs': g['ordem_cncs'],
                'cortado': g['soma'] if g['status'] != 'desconhecida' else None,
                'necessario': g['q'] or None,
                'paginas_ordem': len(ordens[of]['paginas']) if of else None,
            })
        gp = pendente_do_cnc.get(c)
        cnc_posicoes.append({'cnc': c, 'espessura': m['espessura'], 'paginas': len(m['paginas']),
                              'conjunto': conjunto_do_cnc.get(c, [c]), 'posicoes': linhas,
                              'pendente': bool(gp),
                              'motivo_pendente': ', '.join(f"{i['pos']} ({i['cortado']} de {i['necessario']})"
                                                            for i in (gp['incompletas'] if gp else []))})
    lista_ordens = []
    for of in sorted(ordens, key=lambda x: int(x)):
        lista_ordens.append({
            'ordem': of, 'obra': ordens[of].get('obra'),
            'posicoes': sorted(ordens[of]['posicoes'], key=_chave_natural),
            'cncs': sorted(cncs_da_ordem.get(of, []), key=chave_cnc),
            'paginas': len(ordens[of]['paginas']),
            'casa': of in usadas, 'pendente': of in ordens_pend,
        })
    return {'cnc_posicoes': cnc_posicoes, 'lista_ordens': lista_ordens}


def _faixa_paginas(paginas):
    """[133, 134, 150] -> "133–134, 150"."""
    paginas = sorted(set(paginas))
    partes, ini, ant = [], None, None
    for p in paginas:
        if ini is None:
            ini = ant = p
        elif p == ant + 1:
            ant = p
        else:
            partes.append(str(ini) if ini == ant else f'{ini}–{ant}')
            ini = ant = p
    if ini is not None:
        partes.append(str(ini) if ini == ant else f'{ini}–{ant}')
    return ', '.join(partes)


def verificar_pdf_gerado(caminho_pdf, conf, progresso=None):
    """Lê o PDF da Impressão Casada que FOI GERADO (página por página) e
    confere, posição por posição, se a ordem de cada posição de cada CNC
    realmente ficou unida ao CNC lá dentro. Um "bloco" no PDF é: as páginas
    dos CNCs de um conjunto, seguidas das ordens desse conjunto, até o
    próximo conjunto começar. `conf` vem de montar_conferencia_cnc_ordens."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf"')
    if progresso:
        progresso('Lendo o PDF gerado página por página…')
    doc = pymupdf.open(caminho_pdf)
    n_paginas = doc.page_count
    blocos = []
    atual = None
    ultimo_of = ultimo_cnc = None
    capas_of = {}
    for i in range(doc.page_count):
        pg = i + 1
        pagina = doc[i]
        texto = pagina.get_text()
        m_of = RE_OF_ORDEM.search(RE_HIFEN_QUEBRADO.sub('-', texto))
        if m_of:                                   # capa de uma Ordem de Fabricação
            of = m_of.group(1)
            if atual is None:
                atual = {'cncs': {}, 'ordens': {}, 'tem_ordem': False}
                blocos.append(atual)
            atual['ordens'].setdefault(of, []).append(pg)
            atual['tem_ordem'] = True
            capas_of.setdefault(of, []).append(pg)
            ultimo_of, ultimo_cnc = of, None
            continue
        # página de CNC: tem o código JOB (Autocut) OU o número lido pelo mesmo
        # critério do motor (guilhotina etc. não têm JOB no cabeçalho — sem isso
        # o CNC aparecia como "não está no PDF" mesmo estando lá)
        parece_cnc = any(k in texto for k in ('Faltam', 'Aproveitamento', 'Rep. CNC'))
        num = extrair_numero_cnc_por_job(pagina)
        if not num and parece_cnc:
            num = (extrair_codigo_cnc_alfanumerico(pagina) or extrair_numero_cnc_por_rotulo(pagina)
                   or extrair_numero_cnc(_linhas_da_pagina_pymupdf(pagina)) or extrair_numero_cnc_por_posicao(pagina))
        if num or parece_cnc:                      # página de CNC
            cnc = num or ultimo_cnc
            if cnc is None:
                continue
            if atual is None or atual['tem_ordem']:   # CNC depois de ordem = conjunto novo
                atual = {'cncs': {}, 'ordens': {}, 'tem_ordem': False}
                blocos.append(atual)
            atual['cncs'].setdefault(cnc, []).append(pg)
            ultimo_cnc, ultimo_of = cnc, None
            continue
        if not texto.strip():                      # folha em branco (verso)
            continue
        if ultimo_of and atual:                    # continuação da ordem (ETAPA etc.)
            atual['ordens'][ultimo_of].append(pg)

    bloco_da_ordem = {}
    for k, b in enumerate(blocos):
        for of in b['ordens']:
            bloco_da_ordem.setdefault(of, []).append(k)
    por_cnc, divergencias = {}, 0
    for c in conf['cnc_posicoes']:
        if c.get('pendente'):   # conjunto pendente: de propósito não foi impresso
            por_cnc[c['cnc']] = {'bloco': None, 'pendente': True, 'paginas_cnc': [], 'ok': 0, 'total': 0,
                                  'outras_ordens': [], 'faixa_bloco': '',
                                  'linhas': [{'pos': p['pos'], 'ordem': p['ordem'], 'estado': 'pendente',
                                              'texto': 'conjunto pendente — não impresso', 'onde': ''} for p in c['posicoes']]}
            continue
        ks = [k for k, b in enumerate(blocos) if c['cnc'] in b['cncs']]
        linhas, ok, total = [], 0, 0
        if not ks:
            for p in c['posicoes']:
                linhas.append({'pos': p['pos'], 'ordem': p['ordem'], 'estado': 'cnc_ausente',
                               'texto': 'CNC não está no PDF gerado', 'onde': ''})
                if p['ordem']:
                    total += 1
            por_cnc[c['cnc']] = {'bloco': None, 'paginas_cnc': [], 'linhas': linhas, 'ok': 0,
                                  'total': total, 'outras_ordens': [], 'faixa_bloco': ''}
            divergencias += total
            continue
        b = blocos[ks[0]]
        paginas_cnc = b['cncs'][c['cnc']]
        donas = set()
        for p in c['posicoes']:
            of = p['ordem']
            if not of:
                linhas.append({'pos': p['pos'], 'ordem': None, 'estado': 'sem_ordem',
                               'texto': 'sem ordem (não casou)', 'onde': ''})
                continue
            donas.add(of)
            total += 1
            if of in b['ordens']:
                ok += 1
                linhas.append({'pos': p['pos'], 'ordem': of, 'estado': 'unida',
                               'texto': 'unida ✓',
                               'onde': f"CNC pág. {_faixa_paginas(paginas_cnc)} → OF pág. {_faixa_paginas(b['ordens'][of])}"})
            elif of in bloco_da_ordem:
                onde = _faixa_paginas([pp for k in bloco_da_ordem[of] for pp in blocos[k]['ordens'][of]])
                linhas.append({'pos': p['pos'], 'ordem': of, 'estado': 'outro_bloco',
                               'texto': 'ordem em OUTRO bloco ✗', 'onde': f'OF pág. {onde}'})
            else:
                linhas.append({'pos': p['pos'], 'ordem': of, 'estado': 'ausente',
                               'texto': 'ordem NÃO está no PDF ✗', 'onde': ''})
        divergencias += total - ok
        todas_pgs = list(paginas_cnc) + [pp for v_ in b['ordens'].values() for pp in v_]
        por_cnc[c['cnc']] = {
            'bloco': ks[0], 'paginas_cnc': paginas_cnc, 'linhas': linhas, 'ok': ok, 'total': total,
            'outras_ordens': [(of, _faixa_paginas(pgs)) for of, pgs in b['ordens'].items() if of not in donas],
            'faixa_bloco': _faixa_paginas([min(todas_pgs), max(todas_pgs)]) if todas_pgs else '',
        }
    repetidas = {of: pgs for of, pgs in capas_of.items() if len(pgs) > 1}
    doc.close()
    return {'arquivo': os.path.basename(caminho_pdf), 'total_paginas': n_paginas,
            'blocos': len(blocos), 'por_cnc': por_cnc, 'divergencias': divergencias,
            'ordens_repetidas': repetidas}


def analisar_impressao_casada(caminhos_cnc, caminho_ordens, *, unir_partes=True, exigir_completa=True,
                               caminho_relatorio_fluxos=None, caminho_lantek=None, progresso=None):
    """Só confere o casamento (sem montar PDF nenhum) — pro botão "Conferir antes".
    O PDF das Ordens pode ser UM ou VÁRIOS (uma lista, um por obra)."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf" — rode "pip install pymupdf" e abra o app de novo')
    efetivo, pasta_tmp, repetidas = preparar_pdf_ordens(caminho_ordens)
    try:
        r = _analisar_impressao_casada_core(caminhos_cnc, efetivo, unir_partes=unir_partes,
                                             exigir_completa=exigir_completa,
                                             caminho_relatorio_fluxos=caminho_relatorio_fluxos,
                                             caminho_lantek=caminho_lantek, progresso=progresso)
    finally:
        limpar_tmp_ordens(pasta_tmp)
    if isinstance(r, dict):
        r['ordens_repetidas_ignoradas'] = repetidas
    return r


def _analisar_impressao_casada_core(caminhos_cnc, caminho_ordens, *, unir_partes=True, exigir_completa=True,
                                     caminho_relatorio_fluxos=None, caminho_lantek=None, progresso=None):
    """Só confere o casamento (sem montar PDF nenhum). Roda mais rápido que gerar
    o PDF inteiro, porque pula a parte de medir área de tinta e desenhar página."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf" — rode "pip install pymupdf" e abra o app de novo')
    a = _analisar_impressao_casada(caminhos_cnc, caminho_ordens, unir_partes=unir_partes,
                                    exigir_completa=exigir_completa,
                                    caminho_relatorio_fluxos=caminho_relatorio_fluxos,
                                    caminho_lantek=caminho_lantek, progresso=progresso)
    grupos, ordens, mapa_cnc = a['grupos'], a['ordens'], a['mapa_cnc']
    espessuras = sorted({rotulo_espessura(g['espessura']) for g in grupos})
    descartadas = [{'ordem': o, 'posicoes': ', '.join(sorted(ordens[o]['posicoes']))} for o in a['ordens_orfas']]
    relatorio = []
    for g in grupos:
        relatorio.append({
            'cncs': g['cncs'], 'espessura': g['espessura'], 'ordens': g['ordens'],
            'obra': g.get('obra'), 'fluxo_relatorio': g.get('fluxo_relatorio'),
        })
    return {
        'grupos': len(grupos), 'espessuras': espessuras, 'ordens_usadas': len(a['ordens_usadas']),
        'total_cncs': len(mapa_cnc), 'total_ordens_no_pdf': len(ordens),
        'descartadas': descartadas, 'cncs_sem_ordem': a['cncs_sem_ordem'], 'sem_numero': a['sem_numero'],
        'incompletas': a['incompletas'], 'partes_complementares': a['partes_complementares'],
        'conjuntos_pendentes': _resumo_pendentes(a), 'ordens_pendentes': len(a['ordens_pendentes']),
        'ordens_sem_programacao': a['ordens_sem_programacao'],
        'ordens_programadas_sem_cnc': a['ordens_programadas_sem_cnc'],
        'relatorio': relatorio, 'obras': _resumo_obras(a['grupos']),
        'conferencia': montar_conferencia_cnc_ordens(a, exigir_completa),
    }


def gerar_impressao_casada(caminhos_cnc, caminho_ordens, caminho_saida, *,
                            duplex=True, folha_dedicada_cnc=True, padronizar_a4=True,
                            exigir_completa=True, unir_partes=True, progresso=None,
                            caminho_relatorio_fluxos=None, caminho_lantek=None,
                            ignorar_pendencias_lantek=False, obras=None, separar_por_obra=False):
    """Gera o(s) PDF(s) da Impressão Casada. O PDF das Ordens pode ser UM ou VÁRIOS
    (uma lista de caminhos, um por obra): eles são unidos sem repetir ordem."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf" — rode "pip install pymupdf" e abra o app de novo')
    efetivo, pasta_tmp, repetidas = preparar_pdf_ordens(caminho_ordens)
    try:
        r = _gerar_impressao_casada_core(
            caminhos_cnc, efetivo, caminho_saida, duplex=duplex, folha_dedicada_cnc=folha_dedicada_cnc,
            padronizar_a4=padronizar_a4, exigir_completa=exigir_completa, unir_partes=unir_partes,
            progresso=progresso, caminho_relatorio_fluxos=caminho_relatorio_fluxos, caminho_lantek=caminho_lantek,
            ignorar_pendencias_lantek=ignorar_pendencias_lantek, obras=obras, separar_por_obra=separar_por_obra)
    finally:
        limpar_tmp_ordens(pasta_tmp)
    if isinstance(r, dict):
        r['ordens_repetidas_ignoradas'] = repetidas
    return r


def _gerar_impressao_casada_core(caminhos_cnc, caminho_ordens, caminho_saida, *,
                                  duplex=True, folha_dedicada_cnc=True, padronizar_a4=True,
                                  exigir_completa=True, unir_partes=True, progresso=None,
                                  caminho_relatorio_fluxos=None, caminho_lantek=None,
                                  ignorar_pendencias_lantek=False, obras=None, separar_por_obra=False):
    """Porta fiel de gerarImpressaoCasada (fase 2 — PDF de verdade).
    Lê os PDFs de CNC + Ordens, casa as posições, monta o PDF final na
    sequência de impressão (CNC seguido da(s) Ordem(ns) correspondente(s),
    com página em branco pra fechar bloco duplex) e salva em caminho_saida.
    Devolve um dicionário com o relatório do que foi gerado."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf" — rode "pip install pymupdf" e abra o app de novo')
    if _np is None:
        raise RuntimeError('falta instalar o pacote "numpy" — rode "pip install numpy" e abra o app de novo')

    def avisa(msg):
        if progresso:
            progresso(msg)

    a = _analisar_impressao_casada(caminhos_cnc, caminho_ordens, unir_partes=unir_partes,
                                    exigir_completa=exigir_completa,
                                    caminho_relatorio_fluxos=caminho_relatorio_fluxos,
                                    caminho_lantek=caminho_lantek, progresso=progresso)
    mapa_cnc, ordens = a['mapa_cnc'], a['ordens']
    grupos = a['grupos']
    ordens_usadas, ordens_orfas = a['ordens_usadas'], a['ordens_orfas']
    cncs_sem_ordem, sem_numero = a['cncs_sem_ordem'], a['sem_numero']
    incompletas, partes_complementares = a['incompletas'], a['partes_complementares']
    ordens_sem_programacao = a['ordens_sem_programacao']
    ordens_programadas_sem_cnc = a['ordens_programadas_sem_cnc']

    # Trava profissional: enquanto tiver posição sem programação no Lantek
    # (🚨) ou programada mas sem o CNC carregado aqui (🟡), NÃO gera o PDF
    # — pra nunca deixar ordem pra trás sem perceber. Só segue adiante se
    # ignorar_pendencias_lantek=True (o usuário escolheu isso explicitamente
    # depois de ver o aviso). Como as duas listas só vêm preenchidas quando
    # o Relatório Lantek foi carregado, isso não trava nada pra quem não usa
    # essa conferência.
    if not ignorar_pendencias_lantek and (ordens_sem_programacao or ordens_programadas_sem_cnc):
        return {
            'bloqueado_pendencias': True,
            'ordens_sem_programacao': ordens_sem_programacao,
            'ordens_programadas_sem_cnc': ordens_programadas_sem_cnc,
            'total_ordens_no_pdf': len(ordens),
        }

    if not grupos:   # tudo pendente: não existe conjunto completo pra imprimir (PDF sem página não pode ser gravado)
        return {'nada_a_imprimir': True, 'conjuntos_pendentes': _resumo_pendentes(a),
                'conferencia': montar_conferencia_cnc_ordens(a, exigir_completa),
                'total_ordens_no_pdf': len(ordens), 'ordens_pendentes': len(a['ordens_pendentes'])}

    # Obras escolhidas: só os conjuntos delas vão pro PDF (não precisa mandar tudo).
    obras_disponiveis = _resumo_obras(grupos)
    filtrou_obras = False
    if obras:
        escolhidas = {str(o) for o in obras}
        grupos = [g for g in grupos if (g.get('obra') or '—') in escolhidas]
        if not grupos:
            raise RuntimeError('Nenhuma das obras escolhidas tem conjunto completo pra imprimir.')
        filtrou_obras = True
        ordens_usadas = set()
        for g in grupos:
            ordens_usadas |= set(g['ordens'])
        cncs_sem_ordem = [c for g in grupos if not g['ordens'] for c in g['cncs']]

    # ---- montagem física ----
    docs_cnc = [pymupdf.open(c) for c in caminhos_cnc]
    doc_ord = pymupdf.open(caminho_ordens)
    saida = pymupdf.open()

    caixas_tinta_cnc, caixas_tinta_ord = None, None
    if padronizar_a4:
        caixas_tinta_cnc = []
        for f, c in enumerate(caminhos_cnc):
            avisa(f'Medindo a área útil de {os.path.basename(c)}…')
            caixas_tinta_cnc.append(calcular_areas_de_tinta(c))
        avisa('Medindo a área útil das ordens…')
        caixas_tinta_ord = calcular_areas_de_tinta(caminho_ordens)

    estado = {'ultima_rotacao': 0, 'ultimo_tamanho': A4_PT}
    perdas_texto = []      # páginas em que algum texto do PDF de origem (ex.: numeração das peças) não saiu na cópia

    def _palavras_da_pagina(page):
        try:
            return collections.Counter(w[4] for w in page.get_text('words') if w[4].strip())
        except Exception:
            return collections.Counter()

    def area_util(page):
        # cropbox/mediabox NÃO acompanham a rotação da página (ao contrário
        # de page.rect) — é o espaço certo pra bater com a caixa de tinta,
        # que também é medida sem rotação (calcular_areas_de_tinta força
        # rotation 0 de propósito). Converte de y-pra-baixo (PyMuPDF) pra
        # y-pra-cima (mesma convenção bottom-up da caixa de tinta).
        cb = page.cropbox
        h = page.mediabox.height
        return {'left': cb.x0, 'right': cb.x1, 'top': h - cb.y0, 'bottom': h - cb.y1}

    def add_normalizada(doc_origem, indice, caixa_tinta, rotulo=''):
        """Copia a página ajustando pra A4 e CONFERE se todo o texto dela (numeração das peças no desenho,
        número do CNC, quantidades…) saiu na cópia. Se faltou algo: refaz sem recortar a margem; se ainda
        faltar, copia a página inteira sem mexer e registra o aviso (nada some em silêncio)."""
        esperado = _palavras_da_pagina(doc_origem[indice])
        nova = _normalizar_pagina(doc_origem, indice, caixa_tinta)
        if not esperado:
            return nova
        faltou = esperado - _palavras_da_pagina(saida[saida.page_count - 1])
        if faltou and caixa_tinta:
            saida.delete_page(saida.page_count - 1)
            nova = _normalizar_pagina(doc_origem, indice, None)
            faltou = esperado - _palavras_da_pagina(saida[saida.page_count - 1])
        if faltou:
            saida.delete_page(saida.page_count - 1)
            add_pagina_direta(doc_origem, indice)
            nova = saida[saida.page_count - 1]
            faltou = esperado - _palavras_da_pagina(nova)
            if faltou:      # nem a cópia fiel trouxe o texto todo (leitura do PDF de origem): avisa
                perdas_texto.append({'origem': rotulo, 'pagina': indice + 1,
                                      'faltou': ', '.join(list(faltou.elements())[:12])})
        return nova

    def _normalizar_pagina(doc_origem, indice, caixa_tinta):
        # show_pdf_page não reproduz direito uma página de ORIGEM que já
        # tem rotação própria nem uma página de DESTINO com rotação já
        # setada (testado exaustivamente) — por isso página com rotação
        # usa pypdf mais abaixo (escala uniforme + centraliza, do mesmo
        # jeito que a ferramenta em HTML que já funciona faz), e só
        # página sem rotação usa o recorte+escala vetorial do PyMuPDF.
        orig = doc_origem[indice]
        rot = orig.rotation % 360
        rect_recorte = None
        if caixa_tinta:
            try:
                candidato = _caixa_para_rect_pymupdf(orig, caixa_tinta)
                if candidato.width > 5 and candidato.height > 5:
                    rect_recorte = candidato
            except Exception:
                pass

        if rot == 0:
            if rect_recorte:
                origem_w, origem_h = rect_recorte.width, rect_recorte.height
            else:
                cb = orig.cropbox
                origem_w, origem_h = cb.width, cb.height
            alvo = (A4_PT[1], A4_PT[0]) if origem_w > origem_h else A4_PT
            nova = saida.new_page(width=alvo[0], height=alvo[1])
            nova.show_pdf_page(nova.mediabox, doc_origem, indice, clip=rect_recorte, rotate=0)
            estado['ultimo_tamanho'] = alvo
            estado['ultima_rotacao'] = 0
            return nova

        # página com rotação própria: show_pdf_page não reproduz ela
        # direito (testado em vários PDFs reais — desloca/corta o
        # conteúdo). Em vez disso copia a página fiel (insert_pdf) e aplica
        # o recorte da margem vazia + a escala pra encher a A4 direto no
        # conteúdo dela (matriz de transformação no começo do stream) — o
        # mesmo que o pypdf fazia, mas só com o PyMuPDF (sem depender de
        # biblioteca extra: antes, sem o pypdf instalado, as chapas
        # estreitas ficavam sem ajuste nenhum, silenciosamente).
        pos_antes = saida.page_count
        saida.insert_pdf(doc_origem, from_page=indice, to_page=indice)
        nova = saida[pos_antes]
        x0, y0, x1, y1 = _caixa_pdf_da_pagina(saida, nova)
        if caixa_tinta:
            cx0, cy0 = caixa_tinta['left'], caixa_tinta['bottom']
            cx1, cy1 = caixa_tinta['right'], caixa_tinta['top']
            if cx1 - cx0 > 5 and cy1 - cy0 > 5:
                x0, y0, x1, y1 = cx0, cy0, cx1, cy1
        origem_w, origem_h = x1 - x0, y1 - y0
        caixa_deitada = origem_w > origem_h
        alvo_w, alvo_h = (A4_PT[1], A4_PT[0]) if caixa_deitada else (A4_PT[0], A4_PT[1])
        _recortar_e_escalar_pagina(saida, nova, x0, y0, x1, y1, alvo_w, alvo_h)
        nova = saida.load_page(pos_antes)
        estado['ultimo_tamanho'] = (nova.rect.width, nova.rect.height)
        estado['ultima_rotacao'] = 0
        return nova


    def add_pagina_direta(doc_origem, indice):
        orig = doc_origem[indice]
        saida.insert_pdf(doc_origem, from_page=indice, to_page=indice)
        estado['ultimo_tamanho'] = (orig.rect.width, orig.rect.height)
        estado['ultima_rotacao'] = orig.rotation

    def add_cnc(arquivo_idx, indice):
        if padronizar_a4:
            caixa = caixas_tinta_cnc[arquivo_idx][indice] if caixas_tinta_cnc else None
            add_normalizada(docs_cnc[arquivo_idx], indice, caixa, 'CNC ' + os.path.basename(caminhos_cnc[arquivo_idx]))
        else:
            add_pagina_direta(docs_cnc[arquivo_idx], indice)

    def add_ordem(indice):
        if padronizar_a4:
            caixa = caixas_tinta_ord[indice] if caixas_tinta_ord else None
            add_normalizada(doc_ord, indice, caixa, 'Ordens')
        else:
            add_pagina_direta(doc_ord, indice)

    def add_branca():
        w, h = estado['ultimo_tamanho']
        nova = saida.new_page(width=w, height=h)
        return nova

    def fechar_bloco(qtd_paginas):
        if duplex and qtd_paginas % 2 == 1:
            add_branca()
            return 1
        return 0

    def empilhar_cnc(paginas_do_cnc):
        brancas = 0
        for p in paginas_do_cnc:
            add_cnc(p['arquivo'], p['indice'])
            if duplex and folha_dedicada_cnc:
                add_branca()
                brancas += 1
        if not folha_dedicada_cnc:
            if duplex and len(paginas_do_cnc) % 2 == 1:
                add_branca()
                brancas += 1
        elif not duplex:
            add_branca()
            brancas += 1
        return brancas

    avisa('Montando o PDF…')

    def montar_pdf(grupos_alvo, caminho):
        """Monta e grava UM PDF com os conjuntos dados (mesmas regras sempre:
        espessura, laser por último, CNC junto das ordens, duplex…)."""
        nonlocal saida
        saida = pymupdf.open()
        estado['ultima_rotacao'] = 0
        estado['ultimo_tamanho'] = A4_PT
        relatorio_pdf = []
        for g in grupos_alvo:
            detalhe_cnc = []
            for c in g['cncs']:
                pgs = mapa_cnc[c]['paginas']
                branca = empilhar_cnc(pgs)
                detalhe_cnc.append({'cnc': c, 'paginas': len(pgs), 'branca': branca})
            detalhe_ord = []
            for o in g['ordens']:
                idx = ordens[o]['paginas']
                for i_ in idx:
                    add_ordem(i_)
                branca = fechar_bloco(len(idx))
                detalhe_ord.append({'ordem': o, 'posicoes': ', '.join(sorted(ordens[o]['posicoes'])),
                                     'paginas': len(idx), 'branca': branca})
            relatorio_pdf.append({'cncs': g['cncs'], 'espessura': g['espessura'],
                                   'obra': g.get('obra'), 'fluxo_relatorio': g.get('fluxo_relatorio'),
                                   'detalhe_cnc': detalhe_cnc, 'detalhe_ord': detalhe_ord})
        # Conferência final: com "Padronizar em A4" ligado, nenhuma página pode
        # sair pequena/fora do tamanho — se alguma escapou, corrige agora.
        a4_corrigidas = a4_falhas = 0
        if padronizar_a4:
            avisa('Conferindo se todas as páginas ficaram em A4…')
            a4_corrigidas, a4_falhas = _garantir_a4(saida)
        try:
            saida.set_metadata({'creator': 'Validador Fluxos PPCP ' + VERSAO_SCRIPT,
                                'producer': 'Validador Fluxos PPCP ' + VERSAO_SCRIPT,
                                'subject': 'A4 conferido' if padronizar_a4 else 'sem padronizar A4'})
        except Exception:
            pass
        saida.save(caminho)
        n = saida.page_count
        saida.close()
        return relatorio_pdf, n, a4_corrigidas, a4_falhas

    if separar_por_obra:
        por_obra = {}
        for g in grupos:
            por_obra.setdefault(g.get('obra') or '—', []).append(g)
        destinos = [(ob, gs, nome_pdf_da_obra(caminho_saida, ob)) for ob, gs in por_obra.items()]
    else:
        destinos = [(None, grupos, caminho_saida)]

    relatorio, arquivos = [], []
    total_paginas = a4_corrigidas = a4_falhas = 0
    for ob, gs, cam in destinos:
        if ob is not None:
            avisa(f'Montando o PDF da obra {ob}…')
        rel_pdf, n_pag, c4, f4 = montar_pdf(gs, cam)
        relatorio += rel_pdf
        total_paginas += n_pag
        a4_corrigidas += c4
        a4_falhas += f4
        arquivos.append({'obra': ob, 'caminho': cam, 'paginas': n_pag, 'conjuntos': len(gs),
                          'ordens': sum(len(g['ordens']) for g in gs)})
    for d in docs_cnc:
        d.close()
    doc_ord.close()

    descartadas = [{'ordem': o, 'posicoes': ', '.join(sorted(ordens[o]['posicoes']))} for o in ordens_orfas]
    espessuras = sorted({rotulo_espessura(g['espessura']) for g in grupos})

    caminho_pendencias = None
    if ignorar_pendencias_lantek and (ordens_sem_programacao or ordens_programadas_sem_cnc):
        caminho_pendencias = _gravar_relatorio_pendencias_lantek(
            caminho_saida, ordens_sem_programacao, ordens_programadas_sem_cnc)

    # lê de volta cada PDF que acabou de ser gravado e confere o casamento de verdade
    avisa('Conferindo o PDF gerado (posição por posição)…')
    conferencia = montar_conferencia_cnc_ordens(a, exigir_completa)
    cncs_pendentes = {c for g in a.get('grupos_pendentes', []) for c in g['cncs']}
    parcial = separar_por_obra or filtrou_obras        # nem todos os CNCs estão num mesmo PDF
    verifs = []
    for arq, (ob, gs, cam) in zip(arquivos, destinos):
        conf_pdf = conferencia
        if parcial:
            conf_pdf = _conferencia_filtrada(conferencia, {c for g in gs for c in g['cncs']} | cncs_pendentes)
        try:
            ver = verificar_pdf_gerado(cam, conf_pdf)
        except Exception as e:  # a verificação nunca derruba a geração
            ver = {'erro': str(e)}
        verifs.append(ver)
        arq['divergencias'] = ver.get('divergencias') if 'erro' not in ver else None
    if len(verifs) == 1:
        verificacao = verifs[0]
    else:   # vários PDFs: junta o resultado de todos
        erros = [x['erro'] for x in verifs if 'erro' in x]
        verificacao = {'erro': '; '.join(erros)} if erros else {
            'arquivo': f'{len(verifs)} arquivos (um por obra)', 'total_paginas': total_paginas,
            'blocos': sum(x['blocos'] for x in verifs), 'divergencias': sum(x['divergencias'] for x in verifs),
            'por_cnc': {c: d for x in verifs for c, d in x['por_cnc'].items()},
            'ordens_repetidas': {o: p for x in verifs for o, p in x['ordens_repetidas'].items()}}
    if parcial:
        conferencia = _conferencia_filtrada(conferencia, {c for g in grupos for c in g['cncs']} | cncs_pendentes)

    return {
        'conferencia': conferencia, 'verificacao': verificacao,
        'arquivos': arquivos, 'obras': obras_disponiveis,
        'conjuntos_pendentes': _resumo_pendentes(a), 'ordens_pendentes': len(a['ordens_pendentes']),
        'total_paginas': total_paginas, 'espessuras': espessuras, 'grupos': len(grupos),
        'ordens_usadas': len(ordens_usadas), 'descartadas': descartadas,
        'cncs_sem_ordem': cncs_sem_ordem, 'sem_numero': sem_numero,
        'partes_complementares': partes_complementares, 'incompletas': incompletas,
        'ordens_sem_programacao': ordens_sem_programacao,
        'ordens_programadas_sem_cnc': ordens_programadas_sem_cnc,
        'caminho_pendencias': caminho_pendencias,
        'a4_conferido': bool(padronizar_a4), 'a4_corrigidas': a4_corrigidas, 'a4_falhas': a4_falhas,
        'texto_perdido': perdas_texto,
        'relatorio': relatorio, 'total_ordens_no_pdf': len(ordens),
    }

def _gravar_relatorio_pendencias_lantek(caminho_saida, ordens_sem_programacao, ordens_programadas_sem_cnc):
    """Grava um .txt ao lado do PDF listando as ordens que ficaram de fora
    por causa do Lantek (usado quando o usuário escolhe 'gerar mesmo assim,
    deixando essas ordens de fora') — pra nada ficar esquecido sem registro."""
    caminho = os.path.splitext(caminho_saida)[0] + '_PENDENCIAS_LANTEK.txt'
    linhas = [
        'PENDÊNCIAS LANTEK — ordens que ficaram de fora desta impressão casada',
        f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}',
        f'Arquivo de impressão: {os.path.basename(caminho_saida)}',
        '',
    ]
    if ordens_sem_programacao:
        linhas.append(f'🚨 SEM PROGRAMAÇÃO NO LANTEK — nunca foi pro CAM ({len(ordens_sem_programacao)})')
        for d in ordens_sem_programacao:
            linhas.append(f"   Ordem {d['ordem']}{_txt_obra(d)} — {d['posicoes']}")
        linhas.append('')
    if ordens_programadas_sem_cnc:
        linhas.append(f'🟡 PROGRAMADA NO LANTEK, MAS SEM O CNC CARREGADO AQUI ({len(ordens_programadas_sem_cnc)})')
        for d in ordens_programadas_sem_cnc:
            det = d['posicoes']
            info = d.get('detalhe')
            if info:
                det += f" · {info.get('maquina') or '—'} · {info.get('data') or '—'} · nesting {', '.join(info.get('nesting_ids') or [])}"
            linhas.append(f"   Ordem {d['ordem']}{_txt_obra(d)} — {det}")
        linhas.append('')
    try:
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write('\n'.join(linhas))
        return caminho
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
# GRUPO LIC + FLUXO 4 — fase 1: motor de classificação de material
# ---------------------------------------------------------------------
# Porta fiel de classificarMaterialPacote e das regras de classe (barra,
# pilarete, peça padrão) do Conglomerador. A leitura do PDF do pacote em
# si (lerPacote — com o modo OCR pra PDF sem camada de texto, e toda a
# extração de OF/ITEM/MARCA/POS/DESCRIÇÃO) e a árvore/exportação por
# classe ainda ficam pra próxima etapa — dependem de um PDF real pra
# validar direito, igual a Impressão Casada precisou.
# ═══════════════════════════════════════════════════════════════════
RE_BARRA_MAT = re.compile(
    r'\bBARRA(?:S)?\b|\bBARR\.|\bREDONDO\s*CA\b|\bCA-?\s?[56]0\b|\bBR[_\s]*(?:RED|CHAT|CH|QUAD|SEXT)(?![A-Z])')
RE_ITEM_PILARETE = re.compile(r'^PLL\d{0,3}(?:_[A-Z]+)?\s*(?:[-–]|$)')
CODIGOS_PADRAO = ['SD', 'SEZ', 'SEC', 'PC']
RE_ITEM_PADRAO = re.compile(r'^(?:' + '|'.join(CODIGOS_PADRAO) + r')\d{0,3}(?:_[A-Z]+)?\s*(?:[-–]|$)')


def numero_br(v):
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', '.'))
    except ValueError:
        return None


def mm_br(v):
    n = numero_br(v)
    if n is None:
        return None
    s = f'{n:g}'  # sem zeros a mais (igual Number(n).toString() do JS)
    return s.replace('.', ',')


def medidas_do_texto(t):
    """Primeira sequência dimensional do texto: "50X50X2,00" ou "76,20X3,00"."""
    m = re.search(r'(\d+(?:[,.]\d+)?)\s*[Xx*×]\s*(\d+(?:[,.]\d+)?)(?:\s*[Xx*×]\s*(\d+(?:[,.]\d+)?))?', str(t))
    if not m:
        return None
    bruto = re.sub(r'[*×]', 'x', re.sub(r'\s+', '', m.group(0)))
    return {'a': numero_br(m.group(1)), 'b': numero_br(m.group(2)),
            'c': None if m.group(3) is None else numero_br(m.group(3)), 'bruto': bruto}


def ler_perfil_desenho_pacote(texto):
    """A bitola da BARRA vem do código do perfil (campo NOME_PERFIL /
    carimbo do croqui), não do cabeçalho da ordem — ex.: "BR_RED_9.50"
    (redonda Ø9,50), "BR_CH_50X6" (chata 50x6), "BR_QUAD_20", "Lam. 6.35"."""
    c = re.sub(r'\s+', ' ', str(texto or '').upper())
    if not c:
        return None
    br = lambda v: str(v).replace('.', ',')

    m = re.search(r'\bBR[_\s]*RED[_\s.]*(\d+(?:[,.]\d+)?)', c)
    if m:
        return {'familia': 'BARRA REDONDA', 'bitola': 'Ø ' + br(m.group(1)), 'espessura': mm_br(m.group(1))}

    m = re.search(r'\bBR[_\s]*CHAT?[_\s.]*(\d+(?:[,.]\d+)?)[_\s]*[Xx*×][_\s]*(\d+(?:[,.]\d+)?)', c)
    if m:
        return {'familia': 'BARRA CHATA', 'bitola': br(m.group(1)) + 'x' + br(m.group(2)),
                'espessura': mm_br(m.group(2))}

    m = re.search(r'\bBR[_\s]*QUAD[_\s.]*(\d+(?:[,.]\d+)?)', c)
    if m:
        return {'familia': 'BARRA QUADRADA', 'bitola': br(m.group(1)), 'espessura': mm_br(m.group(1))}

    m = re.search(r'\bLAM\.?[_\s]*(\d+(?:[,.]\d+)?)', c)
    if m:
        return {'familia': 'CHAPA', 'bitola': None, 'espessura': mm_br(m.group(1))}

    if re.search(r'\bBR[_\s]*(?:RED|CHAT|CH|QUAD|SEXT)(?![A-Z])', c):
        if re.search(r'BR[_\s]*RED', c):
            fam = 'BARRA REDONDA'
        elif re.search(r'BR[_\s]*QUAD', c):
            fam = 'BARRA QUADRADA'
        else:
            fam = 'BARRA CHATA'
        return {'familia': fam, 'bitola': None, 'espessura': None}
    return None


def eh_pilarete_pacote(o, material_relatorio=None):
    if not o:
        return False
    if o.get('familia') and 'PILARETE' in o['familia']:
        return True
    if RE_ITEM_PILARETE.match(str(o.get('item') or '').upper().strip()):
        return True
    if re.search(r'\bPILARETE\b|\bPILAR\.?\s*LAM\b', str(o.get('descricao') or '').upper()):
        return True
    if material_relatorio and re.search(r'\bPILARETE\b', str(material_relatorio).upper()):
        return True
    return False


def eh_peca_padrao_pacote(o):
    if not o:
        return False
    if o.get('estoque'):
        return True
    return bool(RE_ITEM_PADRAO.match(str(o.get('item') or '').upper().strip()))


def eh_barra_pacote(o, material_relatorio=None):
    if not o:
        return False
    if o.get('familia') and 'BARRA' in o['familia']:
        return True
    if RE_BARRA_MAT.search(str(o.get('descricao') or '').upper()):
        return True
    if material_relatorio and RE_BARRA_MAT.search(str(material_relatorio).upper()):
        return True
    return False


def classe_pacote(o):
    """Rótulo da classe na árvore do Grupo LIC."""
    if eh_peca_padrao_pacote(o):
        return 'PEÇAS PADRÃO / ESTOQUE'
    if eh_barra_pacote(o):
        return 'ACESSÓRIOS DE BARRA'
    if eh_pilarete_pacote(o):
        return 'PILARETE LAMINADO'
    return o.get('familia') or 'A CLASSIFICAR'


def peso_classe(c):
    """Peça padrão e "a classificar" vão pro fim da lista."""
    if c == 'PEÇAS PADRÃO / ESTOQUE':
        return 3
    if c == 'A CLASSIFICAR':
        return 2
    return 1


def classificar_material_pacote(desc):
    """Devolve {'familia','espessura','bitola'}. Regra de ouro: pra chapa e
    tubo a ESPESSURA é o que agrupa a pilha; pra perfil laminado (W, HP, I)
    a BITOLA é a identidade."""
    t = re.sub(r'\s+', ' ', str(desc or '').upper())
    med = medidas_do_texto(t)
    bit = med['bruto'] if med else None

    if re.search(r'\bTELA\b|\bALAMBRAD', t):
        fam = 'TELA PASSARINHEIRO' if re.search(r'PASSARINH', t) else 'TELA'
        return {'familia': fam, 'espessura': None, 'bitola': None}

    if RE_BARRA_MAT.search(t):
        do_carimbo = ler_perfil_desenho_pacote(t)
        if do_carimbo and do_carimbo.get('familia'):
            return do_carimbo
        if re.search(r'BARRA\s*RED|BARRA\s*Ø|\bBR[_\s]*RED(?![A-Z])|\bREDONDO\s*CA\b|\bCA-?\s?[56]0\b', t):
            return {'familia': 'BARRA REDONDA', 'espessura': None, 'bitola': bit}
        if re.search(r'BARRA\s*QUAD|\bBR[_\s]*QUAD(?![A-Z])', t):
            return {'familia': 'BARRA QUADRADA', 'espessura': None, 'bitola': bit}
        esp_b = (med['c'] if med['c'] is not None else med['b']) if med else None
        chata = bool(re.search(r'BARRA\s*CHATA|\bBR[_\s]*CHAT?(?![A-Z])', t))
        return {'familia': 'BARRA CHATA' if chata else 'BARRA',
                'espessura': None if esp_b is None else mm_br(esp_b), 'bitola': bit}

    if re.search(r'\bPILARETE\b|\bPILAR\.?\s*LAM\b', t):
        esp_p = (med['c'] if med['c'] is not None else med['b']) if med else None
        return {'familia': 'PILARETE LAMINADO',
                'espessura': None if esp_p is None else mm_br(esp_p), 'bitola': bit}

    m = re.search(r'\b(?:PERFIL[_\s]*)?(W|HP|VS|CS|CVS)[_\s]*(\d{2,4})\s*[Xx*×]\s*(\d+(?:[,.]\d+)?)', t)
    if m:
        return {'familia': 'PERFIL ' + m.group(1), 'espessura': None,
                'bitola': f'{m.group(1)} {m.group(2)}x' + m.group(3).replace('.', ',')}

    if re.search(r'\bPERFIL[_\s]*[IH]\b|\bVIGA[_\s]*[IH]\b', t):
        return {'familia': 'PERFIL I / H', 'espessura': None, 'bitola': bit}

    if re.search(r'\bPERFIL[_\s]*Z\b|\bENTERPRISE\s*Z\b|\bZ[_\s]*\d{2,3}\s*[Xx*×]', t):
        return {'familia': 'PERFIL Z', 'espessura': mm_br(med['c']) if (med and med['c'] is not None) else None,
                'bitola': bit}

    if re.search(r'\bUDC\b|\bPERFIL[_\s]*U\b|\bU[_\s]*\d{2,3}\s*[Xx*×]', t):
        return {'familia': 'PERFIL U / UDC', 'espessura': mm_br(med['c']) if (med and med['c'] is not None) else None,
                'bitola': bit}

    if re.search(r'CARTOLA', t):
        return {'familia': 'PERFIL CARTOLA', 'espessura': mm_br(med['c']) if (med and med['c'] is not None) else None,
                'bitola': bit}

    if re.search(r'\bTUBO\b|\bTB\b', t):
        fam = 'TUBO'
        if re.search(r'\bRED(?:ONDO|\.)?\b|Ø|\bDIAM', t):
            fam = 'TUBO REDONDO'
        elif re.search(r'\bQUAD(?:RADO|\.)?\b', t):
            fam = 'TUBO QUADRADO'
        elif re.search(r'\bRET(?:ANGULAR|\.)?\b', t):
            fam = 'TUBO RETANGULAR'
        elif med and med['c'] is not None:
            fam = 'TUBO QUADRADO' if med['a'] == med['b'] else 'TUBO RETANGULAR'
        elif med:
            fam = 'TUBO REDONDO'
        esp = (med['c'] if med['c'] is not None else med['b']) if med else None
        return {'familia': fam, 'espessura': None if esp is None else mm_br(esp), 'bitola': bit}

    if re.search(r'CANTONEIRA|\bL[_\s]*\d{2,3}\s*[Xx*×]\s*\d+', t):
        esp = (med['c'] if med['c'] is not None else med['b']) if med else None
        return {'familia': 'CANTONEIRA', 'espessura': None if esp is None else mm_br(esp), 'bitola': bit}

    if re.search(r'BARRA\s*RED|BARRA\s*Ø|\bREDONDO\s*CA\b', t):
        return {'familia': 'BARRA REDONDA', 'espessura': None, 'bitola': bit}

    if re.search(r'BARRA\s*CHATA|\bBARRA\b', t):
        esp = (med['c'] if med['c'] is not None else med['b']) if med else None
        return {'familia': 'BARRA CHATA', 'espessura': None if esp is None else mm_br(esp), 'bitola': bit}

    if re.search(r'\bTELHA\b|\bTRAPEZOID', t):
        return {'familia': 'TELHA', 'espessura': mm_br(med['c']) if (med and med['c'] is not None) else None,
                'bitola': bit}

    if re.search(r'\bCHAPA\b|\bCH\b|#', t):
        mc = re.search(r'(?:\bCHAPA\b|\bCH\b|#)\s*(\d+(?:[,.]\d+)?)', t)
        esp = numero_br(mc.group(1)) if mc else ((med['c'] if med and med['c'] is not None else None))
        return {'familia': 'CHAPA', 'espessura': None if esp is None else mm_br(esp), 'bitola': bit}

    if re.search(r'PARAFUSO|PORCA|ARRUELA|CHUMBADOR', t):
        return {'familia': 'FIXAÇÃO', 'espessura': None, 'bitola': None}

    return {'familia': None, 'espessura': mm_br(med['c']) if (med and med['c'] is not None) else None, 'bitola': bit}


# ═══════════════════════════════════════════════════════════════════
# GRUPO LIC + FLUXO 4 — fase 2: leitura do PDF do pacote (sem OCR)
# ═══════════════════════════════════════════════════════════════════
PADROES_PACOTE = {
    'grupoLic': [
        re.compile(r'\bGRP[_\s]*LIC\.?\s*:?\s*([^\n]{1,60})', re.IGNORECASE),
        re.compile(r'\bGRUPO[\s_]*LIC(?:ITACAO|ITAÇÃO)?\s*[:=]\s*([^\n]{1,60})', re.IGNORECASE),
        re.compile(r'\bGR(?:\.|UPO)?[\s_]*LIC\.?\s*[:=]\s*([^\n]{1,60})', re.IGNORECASE),
        re.compile(r'\bGRUPO\s*[:=]\s*([^\n]{1,60})', re.IGNORECASE),
    ],
    'obra': [re.compile(r'\bOBRA\s*:?\s*(\d{1,10})\b', re.IGNORECASE)],
    'subTr': [re.compile(r'\bSUB_TR\s*:\s*(\d+(?:-\d+)*)', re.IGNORECASE)],
    'item': [
        re.compile(r'\bITEM\s*:\s*([^\n]{1,60})', re.IGNORECASE),
        re.compile(r'\b(?:DESCRICAO|DESCRIÇÃO|PRODUTO)\s*[:=]\s*([^\n]{1,90})', re.IGNORECASE),
    ],
    'bitolaNome': [
        re.compile(r'\bNOME_PERFIL\s*:\s*(\S{1,30})', re.IGNORECASE),
        re.compile(r'\bNOME[_\s]*ITEM\s*:\s*(\S{1,30})', re.IGNORECASE),
    ],
    'material': [
        re.compile(r'\bTP[_\s]*MATL\s*:\s*([^\n]{1,60})', re.IGNORECASE),
        re.compile(r'\b(?:MATERIAL|MAT)\s*[:=]\s*([^\n]{1,90})', re.IGNORECASE),
    ],
    'espessura': [
        re.compile(r'\bESP(?:ESSURA)?\s*[:=]\s*(\d+(?:[,.]\d+)?)\s*(?:MM)?\b', re.IGNORECASE),
        re.compile(r'\bE\s*=\s*(\d+(?:[,.]\d+)?)\s*MM\b', re.IGNORECASE),
    ],
    'estoque': [re.compile(r'\bITEM[_\s]*EST\s*:?\s*(SIM|S|NAO|NÃO|N)\b', re.IGNORECASE)],
    'ident': [re.compile(r'\bIDENT\s*:?\s*([A-Z_]{3,30})\b', re.IGNORECASE)],
    'demanda': [
        re.compile(r'\b\d{3,6}\s*[-–]\s*((?:CHAPA|BARRA|TUBO|PERFIL|TELA|TELHA|CANTONEIRA|CH)\b[^\n]{0,60})',
                   re.IGNORECASE),
        re.compile(r'\b((?:CHAPA|BARRA|TUBO|TELA|TELHA|CANTONEIRA)\s+(?:CORTAD|LAMINAD|GALV|ASTM|DOBRAD|[A-Z0-9])'
                   r'[^\n]{0,60})', re.IGNORECASE),
    ],
}

_SEP_PACOTE = r'\s*[:;.\-]?\s*'
PADROES_OF = [
    re.compile(r'\bOF\b' + _SEP_PACOTE + r'(\d{5,12})\b', re.IGNORECASE),
    re.compile(r'\bO\.?F\.?\s*n?[º°o]?' + _SEP_PACOTE + r'(\d{5,12})\b', re.IGNORECASE),
    re.compile(r'\bORDEM(?:\s*DE\s*FABRICA\S*)?\s*n?[º°o]?' + _SEP_PACOTE + r'(\d{5,12})\b', re.IGNORECASE),
    re.compile(r'\bO\.?P\.?\s*n?[º°o]?' + _SEP_PACOTE + r'(\d{5,12})\b', re.IGNORECASE),
    re.compile(r'\b(?:JOB|WORK\s*ORDER)' + _SEP_PACOTE + r'(\d{5,12})\b', re.IGNORECASE),
]
ROTULOS_POS_PACOTE = ['POS', 'POSICAO', 'POSIÇÃO', 'PECA', 'PEÇA', 'MARCA', 'MARK', 'PIECE', 'ITEM_POS']


def _escapar_regex(t):
    return re.escape(str(t))


def _regex_do_rotulo(rotulo, tipo, global_=False):
    r = _escapar_regex(rotulo).replace('_', '[_\\s]') + r'\b'
    captura = r'(\d{3,12})' if tipo == 'numero' else (r'([A-Za-z0-9@_.\-\[\]]+)' if tipo == 'token' else r'([^\n]{1,60})')
    return re.compile(r'\b' + r + _SEP_PACOTE + captura, re.IGNORECASE)


def achar_of_pacote(texto):
    for rx in PADROES_OF:
        m = rx.search(texto)
        if m:
            return m.group(1)
    return None


def achar_posicoes_pacote(texto):
    """Devolve [{'bruto','norm'}] de todas as posições da página."""
    saida = []
    for rot in ROTULOS_POS_PACOTE:
        rx = _regex_do_rotulo(rot, 'token', True)
        for m in rx.finditer(texto):
            base, _parte = separar_parte_da_posicao(m.group(1))
            n = normalizar_posicao_casamento(base)
            if n:
                saida.append({'bruto': m.group(1), 'norm': n})
    return saida


def limpar_campo_pacote(v):
    """Corta o valor no próximo campo em CAIXA ALTA seguido de ":"."""
    s = str(v or '')
    s = re.split(r'\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ_.]{2,}\s*:)', s)[0]
    s = re.split(r'\s+(?=GRP[_\s]*LIC)', s, flags=re.IGNORECASE)[0]
    return re.sub(r'\s+', ' ', re.sub(r'[.,;:\-]+$', '', s.strip()))


def primeiro_padrao(texto, lista):
    for rx in lista:
        m = rx.search(texto)
        if m and limpar_campo_pacote(m.group(1)):
            return limpar_campo_pacote(m.group(1))
    return None


def limpar_demanda_pacote(v):
    return re.sub(r'\s+(?:KG|TON|UN|P[ÇC]|M2|M)\b[\s\S]*$', '', str(v or ''), flags=re.IGNORECASE).strip()


def ler_ordens_do_pacote(paginas_texto):
    """Porta fiel de lerOrdensDoPacote (sem o modo OCR) — recebe as linhas
    já extraídas do PDF (uma lista de linhas por página) e devolve
    (ordens, pos_para_ordem). "ordens" é {of: {...campos, familia,
    espessura, bitola, item, estoque, descricao, ...}}."""
    ordens, pos_para_ordem = {}, {}
    atual = None
    for p, linhas in enumerate(paginas_texto):
        texto = RE_HIFEN_QUEBRADO.sub('-', '\n'.join(linhas))
        of = achar_of_pacote(texto)
        if of:
            atual = of
            if atual not in ordens:
                ordens[atual] = {
                    'of': atual, 'paginas': [], 'posicoes': set(), 'rotulos': set(),
                    'texto_cab': '', 'texto_desenho': '',
                    'grupo_lic': None, 'descricao': '', 'familia': None,
                    'item': '', 'bitola_nome': '', 'material': '',
                    'espessura': None, 'bitola': None, 'estoque': False,
                }
            ordens[atual]['texto_cab'] += ('\n' if ordens[atual]['texto_cab'] else '') + texto
            for item in achar_posicoes_pacote(texto):
                ordens[atual]['posicoes'].add(item['norm'])
                ordens[atual]['rotulos'].add(item['bruto'])
                for v in variacoes_de_posicao(item['norm']):
                    pos_para_ordem.setdefault(v, atual)
        if atual:
            ordens[atual]['paginas'].append(p)
            if not of and len(ordens[atual]['texto_desenho']) < 4000:
                ordens[atual]['texto_desenho'] += '\n' + texto

    mapa_grupo_lic_lembrado = carregar_mapa_grupo_lic()
    for of, o in ordens.items():
        t = o['texto_cab']
        o['grupo_lic'] = primeiro_padrao(t, PADROES_PACOTE['grupoLic'])
        o['obra'] = primeiro_padrao(t, PADROES_PACOTE['obra']) or ''
        o['sub_tr'] = primeiro_padrao(t, PADROES_PACOTE['subTr']) or ''
        o['obra_trecho'] = f"{o['obra']}-{o['sub_tr']}" if (o['obra'] and o['sub_tr']) else o['obra']   # ex.: 2166-2-01
        o['item'] = primeiro_padrao(t, PADROES_PACOTE['item']) or ''
        o['bitola_nome'] = primeiro_padrao(t, PADROES_PACOTE['bitolaNome']) or ''
        o['material'] = primeiro_padrao(t, PADROES_PACOTE['material']) or ''
        o['descricao'] = ' · '.join(x for x in (o['item'], o['bitola_nome'], o['material']) if x)

        if not o['grupo_lic']:
            chave = _chave_grupo_lic(o)
            if chave and chave in mapa_grupo_lic_lembrado:
                o['grupo_lic'] = mapa_grupo_lic_lembrado[chave]

        est = primeiro_padrao(t, PADROES_PACOTE['estoque'])
        o['estoque'] = bool(re.match(r'^S', est, re.IGNORECASE)) if est else bool(re.search(r'\bESTOQUE\b', t, re.IGNORECASE))

        o['ident'] = primeiro_padrao(t, PADROES_PACOTE['ident']) or ''
        o['demanda'] = limpar_demanda_pacote(primeiro_padrao(t, PADROES_PACOTE['demanda']))

        # cascata de classificação (ITEM/TP_MATL -> DEMANDA -> IDENT -> texto inteiro)
        base_classe = ' '.join(x for x in (o['item'], o['bitola_nome'], o['material']) if x)
        cls = classificar_material_pacote(base_classe or t)
        o['origem_classe'] = 'ITEM/TP_MATL'

        if o['demanda']:
            cd = classificar_material_pacote((base_classe + ' ' + o['demanda']).strip())
            acrescenta = cd['familia'] and (not cls['familia'] or
                                             (cd['familia'] != cls['familia'] and cd['familia'].startswith(cls['familia'])))
            if acrescenta:
                cls = cd
                o['origem_classe'] = 'DEMANDA'

        for fonte, texto_fonte in (('IDENT', o['ident']), ('texto da folha', t)):
            if cls['familia'] or not texto_fonte:
                continue
            c = classificar_material_pacote(texto_fonte)
            if c['familia']:
                cls = c
                o['origem_classe'] = fonte

        carimbo = (ler_perfil_desenho_pacote(base_classe) or ler_perfil_desenho_pacote(t)
                   or ler_perfil_desenho_pacote(o['texto_desenho']))
        if carimbo:
            o['perfil_carimbo'] = carimbo.get('bitola') or carimbo.get('familia')
            if _troca_familia_pacote(cls['familia'], carimbo['familia']):
                cls = carimbo
                o['origem_classe'] = 'carimbo do desenho'

        o['familia'] = cls['familia']
        o['bitola'] = cls.get('bitola') or (carimbo['bitola'] if carimbo else None)

        esp = mm_br(primeiro_padrao(t, PADROES_PACOTE['espessura']))
        if esp == '0':
            esp = None
        if not esp and carimbo:
            esp = carimbo.get('espessura')
        if not esp:
            esp = cls.get('espessura')
        o['espessura'] = esp

    return ordens, pos_para_ordem


def _troca_familia_pacote(atual, nova):
    """Uma família nova só substitui a atual quando é mais específica —
    "BARRA" cede pra "BARRA CHATA", nunca o contrário."""
    if not nova:
        return False
    if not atual:
        return True
    if nova == atual:
        return False
    return nova.startswith(atual)


CAMINHO_MAPA_GRUPO_LIC = os.path.join(os.path.expanduser('~'), '.ppcp_mapa_grupo_lic.json')
CAMINHO_PREFERENCIAS_AGRUPADOR = os.path.join(os.path.expanduser('~'), '.ppcp_preferencias_agrupador.json')


def carregar_preferencias_agrupador():
    try:
        with open(CAMINHO_PREFERENCIAS_AGRUPADOR, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_preferencias_agrupador(prefs):
    try:
        with open(CAMINHO_PREFERENCIAS_AGRUPADOR, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, ensure_ascii=False)
    except Exception:
        pass


def carregar_mapa_grupo_lic():
    try:
        with open(CAMINHO_MAPA_GRUPO_LIC, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_mapa_grupo_lic(mapa):
    try:
        with open(CAMINHO_MAPA_GRUPO_LIC, 'w', encoding='utf-8') as f:
            json.dump(mapa, f, ensure_ascii=False)
    except Exception:
        pass


def _chave_grupo_lic(o):
    """Chave usada pra lembrar o Grupo LIC de uma posição que vier em
    branco — usa o código do ITEM (ex.: "SD1", "PLL1", "CH_PREP"), que é
    estável entre pacotes diferentes da mesma peça."""
    item = str(o.get('item') or '')
    codigo = item.split(' - ')[0].strip().upper()
    return codigo or None


def _chave_posicao_natural(pos):
    """Chave de ordenação "natural" pra posição/marca do desenho — separa
    letras de números (ex.: "TZ9" < "TZ10" < "TZ100", em vez da ordem de
    texto pura onde "TZ10" viria antes de "TZ9"). Cada pedaço vira uma
    tupla (tipo, valor) pra nunca comparar número com texto direto (isso
    quebra em Python) mesmo quando a posição é só dígitos (ex. "106")."""
    partes = re.findall(r'\d+|\D+', str(pos))
    return [(0, int(p)) if p.isdigit() else (1, p.upper()) for p in partes]


def _posicao_representativa(o):
    """A posição/marca do desenho que representa a ordem, pra ordenar a
    pilha igual o desenho (não pelo número interno da OF, que pode ter
    buracos — comum em peças que vieram originalmente do Tekla)."""
    posicoes = o.get('posicoes')
    if posicoes:
        return sorted(posicoes, key=_chave_posicao_natural)[0]
    return None


def _chave_espessura_rotulo(rotulo):
    """Espessura numérica primeiro (crescente: 6,35 antes de 12,7 — a pilha de corte); o resto (bitola de perfil…) por texto."""
    try:
        return (0, float(str(rotulo).replace(',', '.')), '')
    except (TypeError, ValueError):
        return (1, 0.0, str(rotulo))


def _chave_obra(obra):
    """Obra/trecho em ordem natural (2166-2-01 antes de 2166-3-01 e de 2166-10-01); sem obra por último."""
    o = str(obra or '').strip()
    if not o or o == '—':
        return (2, (), '')
    partes = tuple(int(x) for x in re.findall(r'\d+', o))
    return (0, partes, o) if re.match(r'^\d', o) else (1, (), o)


def obra_trecho_da_ordem(o):
    """A "obra" que separa o Grupo LIC: OBRA-TRECHO (ex.: 2166-2-01) — do relatório de fluxos (OF-TRECHO) quando
    foi carregado, senão do PDF (OBRA + SUB_TR); sem trecho, só o número da obra; sem nada, '—'."""
    return (o.get('of_trecho') or o.get('obra_trecho') or o.get('obra') or '—')


def obras_do_pacote(ordens):
    """Obras distintas lidas das ordens ('—' para ordem sem obra), em ordem."""
    return sorted({obra_trecho_da_ordem(o) for o in ordens.values()}, key=_chave_obra)


def montar_arvore_grupo_lic(ordens):
    """Agrupa as ordens em GRUPO LIC -> Tipo (classe/família) -> Obra -> Espessura
    (o mesmo corte que o Fluxo 4 faz: por obra e espessura, agora dentro de cada Grupo LIC e tipo).
    Dentro de cada espessura, ordena pela MARCA/POSIÇÃO do desenho (não pelo número
    interno da OF) — assim a pilha sai na sequência que o desenho/Tekla usa de verdade.
    Devolve uma lista ordenada de {'grupo_lic','sem_grupo_lic','total_ordens',
    'classes': [{'classe','total_ordens',
                 'espessuras':[{'rotulo','ordens':[of,...]}],            # todas as obras juntas (compatibilidade)
                 'obras':[{'obra','total_ordens','espessuras':[{'rotulo','ordens':[of,...]}]}]}]}."""
    por_grupo_lic = {}
    for of, o in ordens.items():
        grupo_lic = (o.get('grupo_lic') or '').strip() or None
        classe = classe_pacote(o)
        esp = o.get('espessura') or o.get('bitola') or '—'
        obra = obra_trecho_da_ordem(o)
        (por_grupo_lic.setdefault(grupo_lic, {}).setdefault(classe, {}).setdefault(obra, {})
         .setdefault(esp, []).append(of))

    def chave_ordenacao(of):
        pos = _posicao_representativa(ordens[of])
        if pos is not None:
            return (0, _chave_posicao_natural(pos))
        return (1, [int(of)])  # sem posição nenhuma — ordens assim vão pro fim, por OF

    saida = []
    for grupo_lic in sorted(por_grupo_lic, key=lambda g: (1, '') if g is None else (0, g)):
        classes_dict = por_grupo_lic[grupo_lic]
        classes = []
        for classe in sorted(classes_dict, key=lambda c: (peso_classe(c), c)):
            obras_dict = classes_dict[classe]
            obras, plano = [], {}
            for obra in sorted(obras_dict, key=_chave_obra):
                esps = [{'rotulo': e, 'ordens': sorted(ofs, key=chave_ordenacao)}
                        for e, ofs in obras_dict[obra].items()]
                esps.sort(key=lambda g: _chave_espessura_rotulo(g['rotulo']))
                obras.append({'obra': obra, 'espessuras': esps,
                              'total_ordens': sum(len(g['ordens']) for g in esps)})
                for e, ofs in obras_dict[obra].items():
                    plano.setdefault(e, []).extend(ofs)
            espessuras = [{'rotulo': e, 'ordens': sorted(ofs, key=chave_ordenacao)} for e, ofs in plano.items()]
            espessuras.sort(key=lambda g: _chave_espessura_rotulo(g['rotulo']))
            classes.append({'classe': classe, 'espessuras': espessuras, 'obras': obras,
                             'total_ordens': sum(len(g['ordens']) for g in espessuras)})
        saida.append({'grupo_lic': grupo_lic or 'SEM GRUPO LIC (preencher)', 'sem_grupo_lic': grupo_lic is None,
                       'classes': classes, 'total_ordens': sum(c['total_ordens'] for c in classes)})
    return saida


def numero_fluxo(v):
    """Número do fluxo: "Fluxo 3 [6,35]" -> "3"; "3" -> "3"; "3 - Plasma" -> "3".
    O número entre colchetes é ESPESSURA, não fluxo: "LASER [9,5]" não tem
    número de fluxo (antes virava fluxo 9)."""
    t = str(v if v is not None else '')
    m = re.search(r'FLUXO\s*(\d+)', t, re.I) or re.match(r'\s*(\d+)\b', t)
    return str(int(m.group(1))) if m else ''


def rotulo_fluxo(v):
    """Rótulo do fluxo pra agrupar: o número ("3") ou, quando o fluxo não é
    numerado, o nome ("LASER"). Vazio / "-" / "SEM ROTEIRIZAÇÃO" -> ''."""
    n = numero_fluxo(v)
    if n:
        return n
    t = re.sub(r'\s*\[.*?\]\s*', '', str(v if v is not None else '')).strip().upper()
    if not t or t in ('-', '—') or t.startswith('SEM ROTEIRIZ'):
        return ''
    return t


def ordem_da_posicao_pacote(pos, pos_para_ordem):
    """Como ordem_da_posicao, mas tenta também tirar a revisão (_R0, _REV2)
    e os fragmentos da direita — o relatório de fluxos traz a posição no
    formato do desenho ("2-50_PDS1_R0"), a ordem só tem a marca (POS:PDS1)."""
    exata = ordem_da_posicao(pos, pos_para_ordem)
    if exata:
        return exata
    s = str(pos).upper()
    sem_rev = re.sub(r'_(?:R|REV)\d*$', '', s)
    candidatos = []
    if sem_rev != s:
        candidatos.append(sem_rev)
    partes = sem_rev.split('_')
    for k in range(1, len(partes)):
        c = '_'.join(partes[k:])
        if len(c) >= 3:
            candidatos.append(c)
    for c in candidatos:
        r = ordem_da_posicao(c, pos_para_ordem)
        if r:
            return r
    return None


def _ordem_str(v):
    """Número da ordem como texto ("4971280"), aceitando 4971280, 4971280.0 e "4971280"."""
    if v is None or v == '':
        return ''
    if isinstance(v, (int, float)):
        return str(int(v))
    t = str(v).strip()
    return t if t.isdigit() else ''


def _achar_cabecalho(rows, *nomes, limite=30):
    """Índice da 1ª linha (entre as primeiras) que tem TODAS as colunas pedidas
    — nas abas "Não Preparação"/"PS PREP" o cabeçalho está na linha 6, abaixo
    das fórmulas de concatenar."""
    alvo = [norm(n) for n in nomes]
    for i, r in enumerate(rows[:limite]):
        h = [norm(str(c)) for c in (r or [])]
        if all(a in h for a in alvo):
            return i
    return None


# abas do relatório novo que trazem UMA LINHA POR ORDEM (nome normalizado, setor padrão)
_ABAS_ORDENS_RELATORIO = (('PREPARACAO', 'PREPARAÇÃO'), ('NAO PREPARACAO', 'NÃO PREPARAÇÃO'), ('PS PREP', 'ARMAÇÃO'))


def _linhas_do_relatorio_de_ordens(planilhas):
    """Relatório "Ordens x Fluxos" (o mais completo): lê as abas Preparação,
    Não Preparação e PS PREP, que trazem o NÚMERO DA ORDEM junto da posição,
    da espessura, da obra-trecho e do fluxo. Devolve uma linha por ordem com as
    mesmas chaves do relatório antigo (of, posicao, fluxo, material, espessura,
    maquina) mais: ordem, obra, trecho, setor, aba, qtde, marca, descricao.
    A coluna de fluxo que falta numa aba (Não Preparação não tem) é completada
    pela BASE DE DADOS, pelo número da ordem. Devolve [] se o arquivo não tem
    esse formato."""
    por_nome = {norm(n): (n, r) for n, r in planilhas}

    fluxo_base = {}
    if 'BASE DE DADOS' in por_nome:
        rows = por_nome['BASE DE DADOS'][1]
        h = _achar_cabecalho(rows, 'ORDEM', 'FLUXO DE PRODUÇÃO')
        if h is not None:
            cab = [norm(str(c)) for c in rows[h]]
            i_o, i_f = cab.index('ORDEM'), cab.index(norm('FLUXO DE PRODUÇÃO'))
            for r in rows[h + 1:]:
                if i_o < len(r) and i_f < len(r):
                    o, f = _ordem_str(r[i_o]), str(r[i_f] or '').strip()
                    if o and rotulo_fluxo(f):
                        fluxo_base.setdefault(o, f)

    saida, vistos = [], set()
    for chave, setor_padrao in _ABAS_ORDENS_RELATORIO:
        if chave not in por_nome:
            continue
        nome_aba, rows = por_nome[chave]
        h = _achar_cabecalho(rows, 'NUM ORDEM', 'POSIÇÃO')
        if h is None:
            continue
        cab = [norm(str(c)) for c in rows[h]]

        def col(*nomes):
            for n in nomes:
                if norm(n) in cab:
                    return cab.index(norm(n))
            return None
        i_ord, i_of, i_pos = col('NUM ORDEM'), col('OF-TRECHO'), col('POSIÇÃO')
        i_fx, i_esp, i_mat = col('FLUXO'), col('ESPESSURA (mm)'), col('MATERIAL')
        i_maq, i_setor, i_qtd = col('CORTE', 'MÁQUINA'), col('SETOR'), col('QTDE (ORDEM)')
        i_marca, i_desc = col('MARCA'), col('DESCRIÇÃO DO ITEM')
        i_grp = col('GRUPO LIC', 'GRP LIC')

        def pega(r, i):
            return r[i] if (i is not None and i < len(r)) else None
        for r in rows[h + 1:]:
            ordem = _ordem_str(pega(r, i_ord))
            if not ordem:
                continue
            posicao = str(pega(r, i_pos) or '').strip()
            if (ordem, posicao) in vistos:
                continue
            vistos.add((ordem, posicao))
            of = str(pega(r, i_of) or '').strip()
            fluxo = str(pega(r, i_fx) or '').strip()
            if not rotulo_fluxo(fluxo):
                fluxo = fluxo_base.get(ordem, '')
            obra = extrair_obra_do_of_planilha(of)
            saida.append({
                'ordem': ordem, 'of': of, 'obra': obra, 'trecho': of[len(obra):].lstrip('-') if obra else '',
                'posicao': posicao, 'fluxo': fluxo,
                'material': pega(r, i_mat), 'espessura': pega(r, i_esp),
                'maquina': pega(r, i_maq),
                'setor': str(pega(r, i_setor) or setor_padrao).strip(), 'aba': nome_aba,
                'qtde': pega(r, i_qtd), 'marca': pega(r, i_marca), 'descricao': pega(r, i_desc),
                'grupo_lic': str(pega(r, i_grp) or '').strip(),
            })
    return saida


def ler_relatorio_ordens_fluxos(caminho_relatorio):
    """Versão pública: lê o arquivo e devolve as linhas por ordem (ver acima)."""
    return _linhas_do_relatorio_de_ordens(ler_arquivo_tabular(caminho_relatorio))


def indexar_relatorio_por_ordem(linhas_relatorio):
    """{número da ordem: {fluxo, obra, of, trecho, espessura (mm_br), setor, posicao}}
    das linhas que trazem o número da ordem (relatório novo). Relatório antigo
    (sem número de ordem) devolve {}."""
    info = {}
    for r in linhas_relatorio or []:
        o = _ordem_str(r.get('ordem'))
        if not o or o in info:
            continue
        info[o] = {'fluxo': rotulo_fluxo(r.get('fluxo')), 'obra': r.get('obra') or extrair_obra_do_of_planilha(r.get('of')),
                   'of': r.get('of'), 'trecho': r.get('trecho'), 'setor': r.get('setor'),
                   'espessura': mm_br(r.get('espessura')) if r.get('espessura') not in (None, '') else '',
                   'posicao': r.get('posicao'), 'grupo_lic': r.get('grupo_lic') or '', 'aba': r.get('aba') or ''}
    return info


def _grupo_lic_vazio(g):
    """Grupo LIC "em branco": vazio, "0", "-"… (a ordem sai do ERP com GRP_LIC0 quando não tem grupo)."""
    return str(g or '').strip().upper() in ('', '0', '-', '—', 'NONE', 'NULL')


def aplicar_relatorio_ao_grupo_lic(ordens, linhas_rel):
    """Completa as ordens lidas do PDF do pacote com o relatório de fluxos (abas Não Preparação,
    PS PREP e Preparação), pelo NÚMERO DA ORDEM (OF):
      • obra / trecho: vêm do OF-TRECHO do relatório (o['obra'], o['of_trecho']) e o['setor_relatorio'];
      • Grupo LIC: só quando a ordem veio SEM grupo (vazio ou "0") — um grupo real do PDF nunca é trocado.
    Devolve {'achadas','sem_relatorio','grupo_preenchido','obras'}."""
    info = indexar_relatorio_por_ordem(linhas_rel)
    achadas = sem = preenchido = 0
    for of, o in ordens.items():
        inf = info.get(_ordem_str(of))
        if not inf:
            sem += 1
            continue
        achadas += 1
        if inf.get('obra'):
            o['obra'] = inf['obra']
        o['of_trecho'] = inf.get('of') or ''
        o['setor_relatorio'] = inf.get('setor') or ''
        o['aba_relatorio'] = inf.get('aba') or ''
        gr = str(inf.get('grupo_lic') or '').strip()
        if _grupo_lic_vazio(o.get('grupo_lic')) and not _grupo_lic_vazio(gr):
            o['grupo_lic'] = gr
            o['grupo_lic_origem'] = 'relatório'
            preenchido += 1
    return {'achadas': achadas, 'sem_relatorio': sem, 'grupo_preenchido': preenchido,
            'obras': sorted({o.get('obra') for o in ordens.values() if o.get('obra')}, key=_chave_obra)}


def aplicar_relatorio_aos_grupos(grupos, mapa_cnc, ordens, linhas_rel):
    """Marca cada conjunto com a obra e o fluxo do relatório (g['obra'],
    g['fluxo_relatorio']) e ordena Obra -> Fluxo -> espessura -> CNC.
    Com o relatório NOVO a decisão sai das ORDENS do conjunto, pelo número da
    ordem (exato, mesmo que a mesma posição exista em obras/trechos
    diferentes); sem número de ordem (relatório antigo) sai da posição, como
    antes. O fluxo que não é numerado ("LASER") vira o próprio nome."""
    info_ordem = indexar_relatorio_por_ordem(linhas_rel)
    pos_para_fluxo = {}
    for r in linhas_rel:
        if not r.get('posicao'):
            continue
        base, _p = separar_parte_da_posicao(r['posicao'])
        npos = normalizar_posicao_casamento(base)
        fx = rotulo_fluxo(r.get('fluxo'))
        if not npos or not fx:
            continue
        pos_para_fluxo.setdefault(npos, {})
        pos_para_fluxo[npos][fx] = pos_para_fluxo[npos].get(fx, 0) + 1

    def _mais_comum(contagem, vazio='—'):
        if not contagem:
            return vazio
        return sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    def _fluxo_do_grupo(g):
        por_ordem = {}
        for o in g['ordens']:
            fx = (info_ordem.get(str(o)) or {}).get('fluxo')
            if fx:
                por_ordem[fx] = por_ordem.get(fx, 0) + 1
        if por_ordem:
            return _mais_comum(por_ordem)
        contagem = {}
        for c in g['cncs']:
            for pos in mapa_cnc[c]['posicoes']:
                fxs = pos_para_fluxo.get(pos)
                if fxs:
                    fx_pos = _mais_comum(fxs)
                    contagem[fx_pos] = contagem.get(fx_pos, 0) + 1
        return _mais_comum(contagem)

    def _obra_do_grupo(g):
        obras = {}
        for o in g['ordens']:
            inf = info_ordem.get(str(o)) or {}
            ob = inf.get('of') or inf.get('obra') or ordens.get(o, {}).get('of') or ordens.get(o, {}).get('obra')
            if ob:
                obras[ob] = obras.get(ob, 0) + 1
        if not obras and g.get('of'):
            return g['of']
        if not obras:                             # CNC sem ordem: fica na obra do próprio CNC
            for c in g['cncs']:
                ob = mapa_cnc[c].get('of')
                if ob:
                    obras[ob] = obras.get(ob, 0) + 1
        return _mais_comum(obras)

    def _chave_esp_g(g):
        try:
            return float(str(g['espessura']).replace(',', '.')) if g['espessura'] else float('inf')
        except (TypeError, ValueError):
            return float('inf')

    for g in grupos:
        g['obra'] = _obra_do_grupo(g)
        g['fluxo_relatorio'] = _fluxo_do_grupo(g)
    grupos.sort(key=lambda g: (g['obra'], grupo_e_laser(g), g['fluxo_relatorio'], _chave_esp_g(g), chave_cnc(g['cncs'][0])))
    return grupos


def ler_relatorio_fluxos_pacote(caminho_relatorio):
    """Le o relatório de fluxos pra uso no casamento do pacote. Se for o
    relatório NOVO (abas Preparação / Não Preparação com o nº da ordem), usa
    ele — é o mais completo: ordem, posição, espessura e obra de cada linha.
    Senão lê a aba 'Relatório Consolidado' (formato antigo) — pega o
    NÚMERO do fluxo (1/2/3/4...) e também a MÁQUINA (usada como reforço
    quando a coluna Fluxo vier vazia: no Fluxo 4, a máquina sempre é
    CHINESSINHA — ou, em relatórios mais novos, GUILHOTINA PQ)."""
    planilhas = ler_arquivo_tabular(caminho_relatorio)
    novas = _linhas_do_relatorio_de_ordens(planilhas)
    if novas:
        return novas
    nome_aba, rows = None, None
    for n, r in planilhas:
        if norm(n) == norm('Relatório Consolidado') or 'CONSOLIDAD' in norm(n):
            nome_aba, rows = n, r
            break
    if nome_aba is None:
        raise RuntimeError('nao encontrei a aba "Relatório Consolidado" no relatorio de fluxos')
    header = [norm(v) for v in (rows[0] or [])]
    iOF = header.index('OF') if 'OF' in header else 0
    iPos = header.index(norm('Posição')) if norm('Posição') in header else 1
    iFluxo = header.index('FLUXO') if 'FLUXO' in header else 3
    iMaterial = header.index('MATERIAL') if 'MATERIAL' in header else 4
    iEsp = header.index(norm('Espessura (mm)')) if norm('Espessura (mm)') in header else 5
    iMaquina = header.index(norm('Máquina')) if norm('Máquina') in header else None

    saida = []
    for r in rows[1:]:
        if not r or not any(v not in (None, '') for v in r):
            continue
        saida.append({
            'of': r[iOF] if iOF < len(r) else None,
            'posicao': r[iPos] if iPos < len(r) else None,
            'fluxo': r[iFluxo] if iFluxo < len(r) else None,
            'material': r[iMaterial] if iMaterial < len(r) else None,
            'espessura': r[iEsp] if iEsp < len(r) else None,
            'maquina': (r[iMaquina] if iMaquina is not None and iMaquina < len(r) else None),
        })
    return saida


MAQUINAS_FLUXO4 = ('CHINESSINHA', 'CHINESINHA', 'GUILHOTINA PQ')
PREFIXOS_POSICAO_FLUXO4_FIXO = ('AR08', 'XH')


def _maquina_indica_fluxo4(maquina):
    m = norm(str(maquina or ''))
    return any(m.startswith(norm(x)) for x in MAQUINAS_FLUXO4)


def _posicao_fluxo4_fixo(pos):
    """Algumas posições são sempre Fluxo 4 por convenção — mesmo quando o
    relatório não tem a linha pra elas (ex.: peças de consumo/sobra tipo
    AR08xxxxxx, XHxxxxxx)."""
    p = str(pos or '').upper()
    return any(p.startswith(pref) for pref in PREFIXOS_POSICAO_FLUXO4_FIXO)


def extrair_obra_do_of_planilha(v):
    """A coluna "OF" do relatório de fluxos vem OBRA-TRECHO-SUBTRECHO
    (ex.: "2141-4-01") — o número da obra é sempre o primeiro trecho."""
    m = re.match(r'^\s*(\d{2,10})', str(v or ''))
    return m.group(1) if m else ''


CAMINHO_MAPA_FLUXO_POSICAO = os.path.join(os.path.expanduser('~'), '.ppcp_mapa_fluxo_posicao.json')
CAMINHO_OBSERVACOES_PACOTE = os.path.join(os.path.expanduser('~'), '.ppcp_observacoes_pacote.json')
CAMINHO_ULTIMOS_CAMINHOS = os.path.join(os.path.expanduser('~'), '.ppcp_ultimos_caminhos.json')


def carregar_ultimos_caminhos():
    try:
        with open(CAMINHO_ULTIMOS_CAMINHOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_ultimos_caminhos(dados):
    try:
        atuais = carregar_ultimos_caminhos()
        atuais.update(dados)
        with open(CAMINHO_ULTIMOS_CAMINHOS, 'w', encoding='utf-8') as f:
            json.dump(atuais, f, ensure_ascii=False)
    except Exception:
        pass


def adicionar_ao_historico(chave, caminho, maximo=10):
    """Guarda o caminho numa lista de histórico (mais recente primeiro,
    sem repetir, até "maximo" itens) — pra aparecer como opção pra
    ESCOLHER depois, sem carregar nada sozinho quando o app abre (base
    ou relatório antigo poderiam estar desatualizados)."""
    try:
        atuais = carregar_ultimos_caminhos()
        historico = atuais.get(chave, [])
        historico = [c for c in historico if c != caminho]
        historico.insert(0, caminho)
        atuais[chave] = historico[:maximo]
        with open(CAMINHO_ULTIMOS_CAMINHOS, 'w', encoding='utf-8') as f:
            json.dump(atuais, f, ensure_ascii=False)
    except Exception:
        pass


def carregar_historico(chave):
    atuais = carregar_ultimos_caminhos()
    historico = atuais.get(chave, [])
    return [c for c in historico if os.path.isfile(c)]  # só mostra o que ainda existe


# ── Base FIXA ──────────────────────────────────────────────────────────────────────────────────────
# A planilha Base (BASE_PPCPM_Programação-Fábrica_rev.NN_PCT) fica numa pasta "base_fixa" na pasta de DADOS do
# sistema (a do servidor: variável PPCP_DADOS, ou ao lado do programa) e carrega SOZINHA ao abrir o Agrupador.
# Saiu revisão nova? É só colocar o arquivo novo nessa pasta: vale sempre a de MAIOR revisão ("rev.22" > "rev.21").
# Pra apontar pra um arquivo específico (em qualquer pasta), crie base_fixa.txt dentro dessa pasta com o caminho
# completo na primeira linha. Arquivos gerados (nome com _LOTE_) e temporários do Excel (~$) são ignorados.
_EXT_BASE_FIXA = ('.xlsx', '.xlsm', '.xlsb')


def pastas_base_fixa():
    pastas = []
    dados = os.environ.get('PPCP_DADOS', '').strip().strip('"')
    if dados:
        pastas.append(os.path.join(dados, 'base_fixa'))
    aqui = os.path.dirname(os.path.abspath(__file__))
    pastas.append(os.path.join(os.path.dirname(aqui), 'base_fixa'))     # <raiz do projeto>/base_fixa
    pastas.append(os.path.join(aqui, 'base_fixa'))                       # ao lado deste script
    unicas = []
    for p in pastas:
        p = os.path.normpath(p)
        if p not in unicas:
            unicas.append(p)
    return unicas


def revisao_da_base(nome):
    """Número da revisão no nome ('..._rev.22_PCT.xlsx' -> 22); -1 se não houver."""
    m = re.search(r'rev[\s._-]*(\d+)', nome, re.I)
    return int(m.group(1)) if m else -1


def achar_base_fixa():
    """Caminho da Base fixa, ou None."""
    for pasta in pastas_base_fixa():                                    # 1) base_fixa.txt manda
        txt = os.path.join(pasta, 'base_fixa.txt')
        try:
            if os.path.isfile(txt):
                with open(txt, encoding='utf-8-sig') as f:
                    cam = f.readline().strip().strip('"')
                if cam and os.path.isfile(cam):
                    return cam
        except Exception:
            pass
    candidatas = []                                                     # 2) a de maior revisão (empate: a mais nova)
    for pasta in pastas_base_fixa():
        try:
            nomes = os.listdir(pasta)
        except Exception:
            continue
        for n in nomes:
            if n.startswith('~$') or not n.lower().endswith(_EXT_BASE_FIXA) or '_LOTE_' in n.upper():
                continue
            cam = os.path.join(pasta, n)
            if not os.path.isfile(cam):
                continue
            try:
                mt = os.path.getmtime(cam)
            except OSError:
                mt = 0
            candidatas.append((revisao_da_base(n), mt, cam))
    if not candidatas:
        return None
    candidatas.sort()
    return candidatas[-1][2]


def carregar_mapa_fluxo_posicao():
    try:
        with open(CAMINHO_MAPA_FLUXO_POSICAO, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_mapa_fluxo_posicao(mapa):
    try:
        with open(CAMINHO_MAPA_FLUXO_POSICAO, 'w', encoding='utf-8') as f:
            json.dump(mapa, f, ensure_ascii=False)
    except Exception:
        pass


def carregar_observacoes_pacote():
    try:
        with open(CAMINHO_OBSERVACOES_PACOTE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_observacoes_pacote(mapa):
    try:
        with open(CAMINHO_OBSERVACOES_PACOTE, 'w', encoding='utf-8') as f:
            json.dump(mapa, f, ensure_ascii=False)
    except Exception:
        pass


def casar_fluxo_do_pacote(ordens, pos_para_ordem, obra_pacote, linhas_relatorio, alvo, mapa_fluxo_posicao=None):
    """Porta (simplificada) de casarFluxoDoPacote — decide, por ORDEM, qual
    é o fluxo dominante (o que tem mais posições daquela ordem no
    relatório), restringe às linhas da mesma obra do pacote, e devolve as
    ordens do fluxo alvo que NÃO são barra/pilarete/peça padrão (essas
    ficam sempre na árvore do Grupo LIC, nunca no corte de fluxo).

    Peça que ainda não tem CAM feito não aparece no relatório de fluxos
    de jeito nenhum — pra essas, tenta a memória manual por posição
    (mapa_fluxo_posicao, alimentada pela tela "Definir Fluxo desta OF");
    se também não tiver nada lá, a ordem cai em "sem_info_no_relatorio"
    em vez de simplesmente sumir do resultado sem avisar."""
    alvo = str(alvo)
    mapa_fluxo_posicao = mapa_fluxo_posicao or {}
    # Obras do pacote. PDF com UMA obra: como sempre (só as linhas dessa obra).
    # PDF com VÁRIAS obras: cada linha do relatório casa só com as ordens da SUA
    # obra (a mesma posição pode existir em obras diferentes), e nenhuma obra
    # fica de fora por ser "a segunda".
    obras_das_ordens = {o.get('obra') for o in ordens.values() if o.get('obra')}
    multi_obra = len(obras_das_ordens) > 1
    if multi_obra:
        obras_ok = set(obras_das_ordens)
    elif obra_pacote:
        obras_ok = {str(x) for x in ([obra_pacote] if isinstance(obra_pacote, (str, int)) else obra_pacote) if x}
    else:
        obras_ok = None
    pos_por_obra = {}
    if multi_obra:
        for o_, dado_ in ordens.items():
            d_ = pos_por_obra.setdefault(dado_.get('obra'), {})
            for pos_ in dado_.get('posicoes', ()):
                for var_ in variacoes_de_posicao(pos_):
                    d_.setdefault(var_, o_)
    # Linhas do relatório NOVO trazem o número da ordem: casam direto, sem
    # depender de posição (que pode repetir entre obras/trechos) nem de a obra
    # do PDF ser a mesma. As linhas sem número de ordem (relatório antigo)
    # seguem pelo caminho de sempre: por posição.
    linhas_por_ordem = [r for r in linhas_relatorio if r.get('ordem')]
    linhas_por_posicao = [r for r in linhas_relatorio if not r.get('ordem')]
    todas_da_obra = [r for r in linhas_por_posicao if not obras_ok
                      or extrair_obra_do_of_planilha(r['of']) in obras_ok]

    por_of = {}
    sem_ordem = []
    espessura_do_relatorio, info_por_ordem = {}, {}
    for r in linhas_por_ordem:
        of = _ordem_str(r['ordem'])
        fx = rotulo_fluxo(r.get('fluxo'))
        if not fx and _maquina_indica_fluxo4(r.get('maquina')):
            fx = '4'
        if of not in ordens:
            # ordem do relatório que não está neste PDF — só avisa as do fluxo alvo e da obra do pacote
            if fx == alvo and (not obras_ok or extrair_obra_do_of_planilha(r.get('of')) in obras_ok):
                sem_ordem.append(r)
            continue
        a = por_of.setdefault(of, {'fluxos': {}, 'posicoes': 0})
        a['posicoes'] += 1
        a['fluxos'][fx or '—'] = a['fluxos'].get(fx or '—', 0) + 1
        info_por_ordem.setdefault(of, {'obra': r.get('of'), 'setor': r.get('setor'), 'posicao': r.get('posicao')})
        if r.get('espessura') not in (None, ''):
            espessura_do_relatorio.setdefault(of, mm_br(r['espessura']))
    for r in todas_da_obra:
        fx = numero_fluxo(r['fluxo'])
        if not fx and _maquina_indica_fluxo4(r.get('maquina')):
            # coluna Fluxo veio vazia, mas a Máquina já denuncia — no
            # Fluxo 4 a máquina sempre é CHINESSINHA (ou, em relatórios
            # novos, GUILHOTINA PQ)
            fx = '4'
        dict_pos = pos_por_obra.get(extrair_obra_do_of_planilha(r['of']), {}) if multi_obra else pos_para_ordem
        of = ordem_da_posicao_pacote(r['posicao'], dict_pos) if r['posicao'] else None
        if not of or of not in ordens:
            if fx == alvo:
                sem_ordem.append(r)
            continue
        info_por_ordem.setdefault(of, {'obra': r.get('of'), 'setor': None, 'posicao': r.get('posicao')})
        a = por_of.setdefault(of, {'fluxos': {}, 'posicoes': 0})
        a['posicoes'] += 1
        chave_fx = fx or '—'
        a['fluxos'][chave_fx] = a['fluxos'].get(chave_fx, 0) + 1

    def fluxo_dominante(of):
        # posição com prefixo fixo (AR08.../XH...) É Fluxo 4 sempre,
        # mesmo que o relatório diga outra coisa ou nem tenha a linha
        if any(_posicao_fluxo4_fixo(p) for p in ordens.get(of, {}).get('posicoes', ())):
            return '4'
        fs = por_of.get(of, {}).get('fluxos')
        if fs:
            return sorted(fs.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        # nao apareceu NENHUMA linha dessa ordem no relatorio — tenta a
        # memoria manual, por posição (pode ter mais de uma posição na
        # ordem; usa a primeira que tiver um fluxo lembrado)
        for pos in ordens.get(of, {}).get('posicoes', ()):
            fx_lembrado = mapa_fluxo_posicao.get(pos)
            if fx_lembrado:
                return str(fx_lembrado)
        return ''

    # Ordens que o relatório NOVO manda produzir na aba "Preparação" com fluxo
    # definido (ex.: U_INT / L_INT de linha de vida, "ITEM_EST:SIM", cujo roteiro
    # na ordem é só "SEPARAR PEÇAS"). Elas NÃO são peça padrão de verdade — o
    # roteirizador já decidiu o fluxo delas —, então não podem cair na exclusão
    # "peça padrão / estoque" abaixo (isso fazia a ordem sumir do Fluxo 4 e do PDF).
    ordens_preparacao_do_relatorio = set()
    for r in linhas_por_ordem:
        if norm(str(r.get('aba') or '')) in (norm('Preparação'), norm('PS PREP')) and rotulo_fluxo(r.get('fluxo')):
            ordens_preparacao_do_relatorio.add(_ordem_str(r['ordem']))

    ordens_do_fluxo, excluidas, sem_info_no_relatorio = [], [], []
    for of in ordens:
        fx = fluxo_dominante(of)
        if not fx:
            sem_info_no_relatorio.append({'of': of, 'posicoes': sorted(ordens[of].get('posicoes', ()))})
            continue
        if fx != alvo:
            continue
        o = ordens[of]
        padrao = eh_peca_padrao_pacote(o) and of not in ordens_preparacao_do_relatorio
        if eh_barra_pacote(o) or eh_pilarete_pacote(o) or padrao:
            excluidas.append(of)
            continue
        ordens_do_fluxo.append(of)

    # a espessura que o RELATÓRIO deu manda (é a bitola de corte); só quando ele
    # não tem, vale a que foi lida da própria ordem. Assim as ordens saem
    # agrupadas na espessura certa mesmo se a descrição da ordem vier torta.
    for of in ordens_do_fluxo:
        esp_rel = espessura_do_relatorio.get(of)
        if esp_rel:
            ordens[of].setdefault('espessura_pdf', ordens[of].get('espessura'))
            ordens[of]['espessura'] = esp_rel

    def chave_espessura(of):
        esp = ordens[of].get('espessura')
        try:
            return float(str(esp).replace(',', '.')) if esp else float('inf')
        except (TypeError, ValueError):
            return float('inf')

    def chave_ordenacao(of):
        pos = _posicao_representativa(ordens[of])
        if pos is not None:
            return (chave_espessura(of), 0, _chave_posicao_natural(pos))
        return (chave_espessura(of), 1, [int(of)])

    # agrupado por espessura (crescente) — mesma peça de material fica junto,
    # do jeito que sai a pilha de corte de verdade; dentro da mesma
    # espessura, segue a Marca/Posição do desenho (não o número interno
    # da OF, que pode ter buracos — comum em peças que vieram do Tekla).
    def obra_da_ordem(of):
        return (info_por_ordem.get(of) or {}).get('obra') or ordens[of].get('obra') or ''

    ordens_do_fluxo.sort(key=lambda of: (obra_da_ordem(of),) + tuple(chave_ordenacao(of)))
    sem_info_no_relatorio.sort(key=lambda d: int(d['of']))
    obra_por_ordem = {of: obra_da_ordem(of) for of in ordens_do_fluxo}
    return {'ordens_do_fluxo': ordens_do_fluxo, 'obra_por_ordem': obra_por_ordem, 'multi_obra': multi_obra,
            'excluidas_classe': sorted(excluidas, key=lambda x: int(x)),
            'sem_ordem': sem_ordem, 'total_linhas_obra': len(todas_da_obra) + len(linhas_por_ordem),
            'sem_info_no_relatorio': sem_info_no_relatorio, 'info_por_ordem': info_por_ordem}


def ler_pacote_pdf(caminho_pdf, progresso=None):
    """Lê o PDF do pacote/obra e devolve (ordens, pos_para_ordem) — usa
    ler_linhas_por_pagina (a mesma leitura da Impressão Casada)."""
    if progresso:
        progresso('Lendo PDF do pacote…')
    paginas = ler_linhas_por_pagina(caminho_pdf)
    if progresso:
        progresso('Classificando ordens…')
    return ler_ordens_do_pacote(paginas)


def _txt_obra(d):
    """' (obra 2143-3-01)' para listar a ordem junto da obra (a mesma posição existe em várias obras); '' se não souber."""
    ob = (d or {}).get('obra')
    return f" (obra {ob})" if ob else ''


def _obra_confere(of_ordem, obra_ordem, of_lantek):
    """A peça do Lantek é da MESMA obra-trecho da ordem? Posições têm o mesmo nome em obras diferentes
    ("2-01_-96" existe em várias obras), então casar só pelo nome da posição marca como "programada" uma ordem
    cuja peça nem foi programada (a programada era de OUTRA obra). `of_ordem` = obra-trecho lido na ordem
    ("2143-3-01"); sem ele usa só a OBRA ("2143-3") como prefixo; sem nenhum dos dois não dá pra separar
    (comportamento antigo: só a posição)."""
    of_l = norm(of_lantek)
    if of_ordem:
        return norm(of_ordem) == of_l
    if obra_ordem:
        o = norm(obra_ordem)
        return of_l == o or of_l.startswith(o + '-')
    return True


def conferir_ordens_com_lantek(ordens_orfas, ordens, lantek_programado):
    """Para cada ordem sem CNC casado: (a) peça programada no Lantek NA MESMA OBRA-TRECHO -> 🟡 "programada, sem o CNC
    carregado aqui"; (b) não programada nessa obra -> 🚨 "sem programação". Devolve (sem_programacao, programadas_sem_cnc)."""
    sem_programacao, programadas_sem_cnc = [], []
    for of in ordens_orfas:
        dado = ordens[of]
        posicoes_da_ordem = dado['posicoes']
        posicoes_norm = {norm(_pos_base(p)) for p in posicoes_da_ordem}
        item = {'ordem': of, 'posicoes': ', '.join(sorted(posicoes_da_ordem)),
                'obra': dado.get('of') or dado.get('obra') or ''}
        detalhe = None
        achou = False
        for (of_lantek, pos_lantek), info in lantek_programado.items():
            if pos_lantek in posicoes_norm and _obra_confere(dado.get('of'), dado.get('obra'), of_lantek):
                achou = True
                if detalhe is None:
                    detalhe = dict(info, of_lantek=of_lantek)
        if achou:
            item['detalhe'] = detalhe
            programadas_sem_cnc.append(item)
        else:
            sem_programacao.append(item)
    return sem_programacao, programadas_sem_cnc


def ler_relatorio_lantek(caminho):
    """Lê o "Relatório de Análise de Nestings" exportado do Lantek — a
    coluna REFERENCIA vem no mesmo formato de texto que a posição já lida
    nos PDFs de CNC ("308_2 - OF2143-3-01 - Q1"), então reaproveita a
    mesma leitura de posição (RE_POS_CNC) em vez de inventar um parser
    novo. Cada linha do relatório é UMA peça programada (nesting real,
    direto do sistema) — usado como conferência de segurança: se uma
    posição não tiver Ordem casada na Impressão Casada MAS ela aparecer
    aqui como programada, é sinal de alerta (a peça foi cortada/vai ser
    cortada mas a Ordem dela não entrou no lote impresso).

    Devolve um dict {(OF-trecho normalizado, posição normalizada):
    {'qtd': quantidade programada somada, 'maquina':..., 'data':...,
    'nesting_ids': [...]}}."""
    planilhas = ler_arquivo_tabular(caminho)
    if not planilhas:
        raise RuntimeError('não consegui ler nenhuma aba/tabela nesse arquivo')
    nome_aba, rows = planilhas[0]
    if not rows:
        raise RuntimeError('arquivo vazio')
    header = [norm(str(h or '')).lstrip('\ufeff') for h in rows[0]]

    def idx(*nomes_possiveis):
        for n in nomes_possiveis:
            n = norm(n)
            if n in header:
                return header.index(n)
        return None

    i_ref = idx('REFERENCIA', 'REFERÊNCIA')
    i_maquina = idx('MAQUINA', 'MÁQUINA')
    i_data = idx('DATA PROG NESTING')
    i_nesting = idx('ID NESTING')
    if i_ref is None:
        raise RuntimeError('não encontrei a coluna "REFERENCIA" nesse relatório — é mesmo '
                            'o "Análise de Nestings" do Lantek?')

    programado = {}
    total_linhas_com_posicao = 0
    for r in rows[1:]:
        if i_ref >= len(r):
            continue
        ref = str(r[i_ref] or '').strip()
        if not ref:
            continue
        m = RE_POS_CNC.match(ref) or RE_POS_CNC.search(ref)
        if not m:
            continue  # ex.: acessório/consumível sem OF (não é peça de posição rastreada)
        m_of = re.search(r'OF([A-Za-z0-9\-_.]+)', ref)
        if not m_of:
            continue
        pos_bruta = m.group(1)
        base, _parte = separar_parte_da_posicao(pos_bruta)
        pos_norm = norm(_pos_base(base))
        of_norm = norm(m_of.group(1))
        chave = (of_norm, pos_norm)
        m_qtd = re.search(r'-\s*Q(\d+)', ref)
        qtd = int(m_qtd.group(1)) if m_qtd else 0
        entrada = programado.setdefault(chave, {'qtd': 0, 'maquina': None, 'data': None, 'nesting_ids': []})
        entrada['qtd'] += qtd
        if i_maquina is not None and i_maquina < len(r) and r[i_maquina]:
            entrada['maquina'] = str(r[i_maquina])
        if i_data is not None and i_data < len(r) and r[i_data]:
            entrada['data'] = str(r[i_data])
        if i_nesting is not None and i_nesting < len(r) and r[i_nesting]:
            entrada['nesting_ids'].append(str(r[i_nesting]))
        total_linhas_com_posicao += 1
    return programado, total_linhas_com_posicao



def _salvar_paginas_do_pacote(caminho_pacote, paginas, caminho_saida):
    """Grava um PDF só com as páginas pedidas (na ordem dada) do PDF do pacote.
    Usa select() no próprio pacote em vez de copiar página por página: cada cópia levava de novo as fontes/
    recursos compartilhados e o PDF saía ~15x maior (126 páginas = 16 MB; assim ficam ~1 MB). Devolve o nº de páginas."""
    if not paginas:
        raise RuntimeError('nenhuma página para gravar neste PDF')
    doc = pymupdf.open(caminho_pacote)
    try:
        doc.select(list(paginas))
        doc.save(caminho_saida, garbage=4, deflate=True)
        return doc.page_count
    finally:
        doc.close()


def gerar_pdf_fluxo(caminho_pacote, ordens, ordens_selecionadas, caminho_saida, progresso=None):
    """Monta um PDF só com as páginas das ordens do fluxo alvo (na ordem
    em que vierem) — as páginas de cada ordem já foram localizadas na
    leitura do pacote (ordens[of]['paginas'])."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf" — rode "pip install pymupdf" e abra o app de novo')
    if progresso:
        progresso('Montando o PDF do fluxo…')
    paginas = []
    for of in ordens_selecionadas:
        paginas.extend(sorted(ordens.get(of, {}).get('paginas', [])))
    return _salvar_paginas_do_pacote(caminho_pacote, paginas, caminho_saida)


def gerar_pdfs_fluxo_por_obra(caminho_pacote, ordens, ordens_selecionadas, obra_por_ordem, caminho_base, progresso=None):
    """Um PDF por obra (nome_obra_2139-2-02.pdf…), cada um com as ordens marcadas
    daquela obra, na mesma sequência (espessura…). Devolve [{obra, caminho, paginas, ordens}]."""
    por_obra = {}
    for of in ordens_selecionadas:
        por_obra.setdefault(obra_por_ordem.get(of) or '—', []).append(of)
    saidas = []
    for obra, ofs in por_obra.items():
        cam = nome_pdf_da_obra(caminho_base, obra)
        if progresso:
            progresso(f'Montando o PDF da obra {obra}…')
        n = gerar_pdf_fluxo(caminho_pacote, ordens, ofs, cam)
        saidas.append({'obra': obra, 'caminho': cam, 'paginas': n, 'ordens': len(ofs)})
    return saidas


def conferir_selecao_lic(ordens, ofs, obra_por_ordem=None, relatorio_usado=False, stats_relatorio=None, por_obra=False):
    """Resumo de CONFERÊNCIA antes de gerar o PDF do Grupo LIC (nada é gravado aqui).
    Devolve {'total_ordens','total_paginas','por_obra':[{obra,ordens,paginas,grupos,tipos}],'erros':[...],'avisos':[...]}.
    erros = coisa que faria faltar/repetir folha no PDF (ordem sem página, OF repetida/inexistente);
    avisos = dado suspeito (sem Grupo LIC, sem obra, fora do relatório, várias obras num PDF só)."""
    obra_por_ordem = obra_por_ordem or {of: obra_trecho_da_ordem(ordens.get(of, {})) for of in ofs}
    erros, avisos = [], []
    vistas, repetidas = set(), []
    sem_pagina, inexistentes, sem_grupo, sem_obra, fora_rel = [], [], [], [], []
    por_obra_d = {}
    for of in ofs:
        if of in vistas:
            repetidas.append(of)
            continue
        vistas.add(of)
        o = ordens.get(of)
        if o is None:
            inexistentes.append(of)
            continue
        obra = obra_por_ordem.get(of) or '—'
        d = por_obra_d.setdefault(obra, {'obra': obra, 'ordens': 0, 'paginas': 0,
                                         'grupos': collections.Counter(), 'tipos': collections.Counter()})
        n_pag = len(o.get('paginas') or [])
        d['ordens'] += 1
        d['paginas'] += n_pag
        d['grupos'][o.get('grupo_lic') if not _grupo_lic_vazio(o.get('grupo_lic')) else 'SEM GRUPO LIC'] += 1
        d['tipos'][classe_pacote(o)] += 1
        if n_pag == 0:
            sem_pagina.append(of)
        if _grupo_lic_vazio(o.get('grupo_lic')):
            sem_grupo.append(of)
        if obra == '—':
            sem_obra.append(of)
        if relatorio_usado and not o.get('aba_relatorio'):
            fora_rel.append(of)

    def _lista(xs, n=8):
        return ', '.join(xs[:n]) + (f' … (+{len(xs) - n})' if len(xs) > n else '')

    if inexistentes:
        erros.append(f'{len(inexistentes)} OF(s) marcada(s) não existe(m) no pacote lido: {_lista(inexistentes)}')
    if repetidas:
        erros.append(f'{len(repetidas)} OF(s) aparece(m) repetida(s) na seleção (seriam impressas 2x): {_lista(repetidas)}')
    if sem_pagina:
        erros.append(f'{len(sem_pagina)} ordem(ns) sem nenhuma página no pacote (NÃO sairiam no PDF): {_lista(sem_pagina)}')
    if sem_grupo:
        avisos.append(f'{len(sem_grupo)} ordem(ns) sem Grupo LIC (ou "0"): {_lista(sem_grupo)}')
    if sem_obra:
        avisos.append(f'{len(sem_obra)} ordem(ns) sem OBRA identificada: {_lista(sem_obra)}')
    if relatorio_usado and fora_rel:
        avisos.append(f'{len(fora_rel)} ordem(ns) NÃO encontrada(s) no relatório de fluxos informado: {_lista(fora_rel)}')
    if len(por_obra_d) > 1 and not por_obra:
        avisos.append(f'a seleção mistura {len(por_obra_d)} obras e vai sair em UM PDF só '
                      '(marque "Gerar um PDF separado por obra" para separar).')
    lista = sorted(por_obra_d.values(), key=lambda d: _chave_obra(d['obra']))
    return {'total_ordens': sum(d['ordens'] for d in lista), 'total_paginas': sum(d['paginas'] for d in lista),
            'por_obra': lista, 'erros': erros, 'avisos': avisos}


def texto_conferencia_lic(conf, por_obra=False):
    """Texto legível do resumo de conferência (usado no diálogo e no .txt)."""
    L = [f"Total: {conf['total_ordens']} ordem(ns), {conf['total_paginas']} página(s)"
         + (f" — {len(conf['por_obra'])} PDF(s), um por obra" if por_obra and len(conf['por_obra']) > 1 else '')]
    for d in conf['por_obra']:
        L.append('')
        L.append(f"OBRA {d['obra']}: {d['ordens']} ordem(ns), {d['paginas']} página(s)")
        L.append('   Grupo LIC: ' + ' · '.join(f'{g} ({n})' for g, n in sorted(d['grupos'].items())))
        L.append('   Tipo: ' + ' · '.join(f'{t} ({n})' for t, n in sorted(d['tipos'].items())))
    if conf['erros']:
        L += ['', 'PROBLEMAS (corrija antes de imprimir):'] + [f'  ✖ {e}' for e in conf['erros']]
    if conf['avisos']:
        L += ['', 'ATENÇÃO:'] + [f'  ⚠ {a}' for a in conf['avisos']]
    return '\n'.join(L)


def _contagem_palavras_pagina(page):
    return collections.Counter(w[4] for w in page.get_text('words'))


def verificar_pdf_gerado(caminho_pacote, caminho_pdf, paginas_esperadas):
    """Confere o PDF recém-gravado contra o pacote: mesmo nº de páginas e, página a página, o MESMO texto
    (números de peça/posição, OF, obra…) da página de origem. Devolve {'ok','esperadas','geradas',
    'divergentes':[nº da página (1-based) no PDF gerado]} — nunca levanta erro por causa da conferência."""
    res = {'ok': False, 'esperadas': len(paginas_esperadas), 'geradas': 0, 'divergentes': [], 'erro': ''}
    try:
        src = pymupdf.open(caminho_pacote)
        out = pymupdf.open(caminho_pdf)
        try:
            res['geradas'] = out.page_count
            for i, p_src in enumerate(paginas_esperadas):
                if i >= out.page_count:
                    break
                if _contagem_palavras_pagina(src[p_src]) != _contagem_palavras_pagina(out[i]):
                    res['divergentes'].append(i + 1)
            res['ok'] = (out.page_count == len(paginas_esperadas) and not res['divergentes'])
        finally:
            src.close()
            out.close()
    except Exception as e:  # conferência não pode derrubar a geração
        res['erro'] = str(e)
    return res


def texto_verificacao(v):
    if v.get('erro'):
        return f"⚠ não consegui conferir ({v['erro']})"
    if v['ok']:
        return f"✔ conferido: {v['geradas']} págs, texto idêntico ao pacote"
    partes = []
    if v['geradas'] != v['esperadas']:
        partes.append(f"tem {v['geradas']} págs, esperado {v['esperadas']}")
    if v['divergentes']:
        partes.append('texto diferente do pacote nas págs ' + ', '.join(str(x) for x in v['divergentes'][:15]))
    return '✖ ' + '; '.join(partes)


def gerar_pdfs_lic_conferidos(caminho_pacote, ordens, ofs, obra_por_ordem, caminho_saida, por_obra=False,
                              salvar_lista=True, progresso=None):
    """Gera o(s) PDF(s) do Grupo LIC (um por obra se por_obra) e CONFERE cada um contra o pacote.
    Com salvar_lista grava ao lado "<pdf>_conferencia.txt" (obra, OFs e páginas de cada uma).
    Devolve [{'obra','caminho','paginas','ordens','verificacao','lista'}]."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf" — rode "pip install pymupdf" e abra o app de novo')
    grupos = {}
    for of in ofs:
        grupos.setdefault((obra_por_ordem.get(of) or '—') if por_obra else None, []).append(of)
    saidas = []
    for obra, lista_ofs in grupos.items():
        cam = nome_pdf_da_obra(caminho_saida, obra) if obra is not None else caminho_saida
        if progresso:
            progresso('Montando o PDF' + (f' da obra {obra}' if obra is not None else '') + '…')
        paginas = [p for of in lista_ofs for p in sorted(ordens.get(of, {}).get('paginas', []))]
        n = _salvar_paginas_do_pacote(caminho_pacote, paginas, cam)
        if progresso:
            progresso('Conferindo o PDF gerado com o pacote…')
        ver = verificar_pdf_gerado(caminho_pacote, cam, paginas)
        lista_txt = ''
        if salvar_lista:
            lista_txt = os.path.splitext(cam)[0] + '_conferencia.txt'
            try:
                conf = conferir_selecao_lic(ordens, lista_ofs, {of: obra_por_ordem.get(of) for of in lista_ofs},
                                            por_obra=False)
                linhas = [f'CONFERÊNCIA — {os.path.basename(cam)}',
                          f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")} a partir de {os.path.basename(caminho_pacote)}',
                          texto_verificacao(ver), '', texto_conferencia_lic(conf), '',
                          'OF / grupo LIC / tipo / espessura / páginas deste PDF:']
                pg = 1
                for of in lista_ofs:
                    o = ordens.get(of, {})
                    k = len(o.get('paginas') or [])
                    esp = o.get('espessura') or o.get('bitola') or '—'
                    grp = o.get('grupo_lic') if not _grupo_lic_vazio(o.get('grupo_lic')) else 'SEM GRUPO LIC'
                    linhas.append(f"  OF {of}  |  {grp}  |  {classe_pacote(o)}  |  {esp}  |  "
                                  + (f'pág. {pg}' + (f'–{pg + k - 1}' if k > 1 else '') if k else 'SEM PÁGINA'))
                    pg += k
                with open(lista_txt, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(linhas) + '\n')
            except Exception:
                lista_txt = ''
        saidas.append({'obra': obra, 'caminho': cam, 'paginas': n, 'ordens': len(lista_ofs),
                       'verificacao': ver, 'lista': lista_txt})
    return saidas


RE_NOME_ARQUIVO_INVALIDO = re.compile(r'[\\/:*?"<>|]+')


def exportar_pdfs_por_classe(caminho_pacote, ordens, pasta_saida, progresso=None, por_obra=False):
    """Separa o pacote em um PDF por classe do Grupo LIC (chapa, perfil W,
    tubo redondo, acessórios de barra, peça padrão...), cada um só com as
    ordens daquela classe — pra imprimir/enviar cada tipo de material
    separado. Com por_obra=True sai um PDF por classe E obra (chapa_obra_2143.pdf…),
    na sequência obra -> espessura -> posição (igual ao Fluxo 4).
    Devolve uma lista de {'classe','obra','ordens','paginas','arquivo'}."""
    if pymupdf is None:
        raise RuntimeError('falta instalar o pacote "pymupdf" — rode "pip install pymupdf" e abra o app de novo')
    por_classe = {}
    for of, o in ordens.items():
        por_classe.setdefault(classe_pacote(o), []).append(of)

    def chave_posicao(of):
        return ((0, _chave_posicao_natural(_posicao_representativa(ordens[of])))
                if _posicao_representativa(ordens[of]) is not None else (1, [int(of)]))

    def chave_espessura_of(of):
        o = ordens[of]
        return _chave_espessura_rotulo(o.get('espessura') or o.get('bitola') or '—')

    resultado = []
    try:
        for classe in sorted(por_classe, key=lambda c: (peso_classe(c), c)):
            if por_obra:
                por_ob = {}
                for of in por_classe[classe]:
                    por_ob.setdefault(obra_trecho_da_ordem(ordens[of]), []).append(of)
                lotes = [(ob, sorted(ofs, key=lambda of: (chave_espessura_of(of), chave_posicao(of))))
                         for ob, ofs in sorted(por_ob.items(), key=lambda kv: _chave_obra(kv[0]))]
            else:
                lotes = [(None, sorted(por_classe[classe], key=chave_posicao))]
            for obra, ofs in lotes:
                if progresso:
                    progresso(f'Montando PDF de "{classe}"' + (f' — obra {obra}' if obra else '') + '…')
                paginas = [p for of in ofs for p in sorted(ordens[of].get('paginas', []))]
                nome_arquivo = RE_NOME_ARQUIVO_INVALIDO.sub('_', classe).strip().strip('.') or 'SEM_CLASSE'
                if obra:
                    nome_arquivo += '_obra_' + (re.sub(r'[^A-Za-z0-9_-]+', '_', str(obra)).strip('_') or 'sem_obra')
                caminho = os.path.join(pasta_saida, f'{nome_arquivo}.pdf')
                n_pag = _salvar_paginas_do_pacote(caminho_pacote, paginas, caminho)
                ver = verificar_pdf_gerado(caminho_pacote, caminho, paginas)
                resultado.append({'classe': classe, 'obra': obra, 'ordens': len(ofs), 'paginas': n_pag,
                                   'arquivo': caminho, 'verificacao': ver})
    finally:
        pass
    return resultado


if __name__ == '__main__':
    main()
