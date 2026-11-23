# -*- coding: utf-8 -*-
"""
Acesso ao banco de dados desta ferramenta. Usa o MESMO arquivo
`pcp_projeart.db` compartilhado com o resto do app (via
`nucleo.caminhos.CAMINHO_BANCO_DADOS` — já ganha de graça o tratamento de
caminho em modo `.exe`, ver `nucleo/caminhos.py`), mas com tabelas
próprias, prefixadas com `auditoria_` pra nunca colidir com as tabelas de
outra ferramenta (padrão já usado pelo Corte: `corte_processamentos`,
`corte_arquivos`...).

Extraído de `cria_pasta_auditoria.py`: no script original essas tabelas
não tinham prefixo (`config`, `pacotes`, `raizes`...) porque era um
programa isolado, com seu próprio banco. Só o nome mudou aqui — a lógica
de cada função é idêntica.

Cada função abre e fecha sua própria conexão sqlite3 (sem pool) — mesmo
padrão do script original; o banco é local e as operações são rápidas o
suficiente pra isso não ser um problema.
"""
import sqlite3
from datetime import datetime

from nucleo.caminhos import CAMINHO_BANCO_DADOS


def inicializar_banco():
    """Cria as tabelas desta ferramenta se ainda não existirem."""
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_config (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_pacotes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            lote          TEXT NOT NULL,
            of_trecho     TEXT NOT NULL,
            importado_em  TEXT NOT NULL,
            UNIQUE(lote, of_trecho)
        )
    """)
    # Diretórios raiz cadastrados (pode ter quantos o usuário quiser). Cada
    # um contém suas próprias pastas de mês E sua própria pasta LOTE 9999.
    # Criar pastas e a auditoria juntam todas elas.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_raizes (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            caminho  TEXT NOT NULL UNIQUE
        )
    """)
    # Base usada pelas telas "Buscar por Obra" e "Buscar por Pacote" (FASE 2)
    # — é recarregada do zero a cada "Atualizar Base de Busca", nunca
    # atualizada linha a linha, por isso não guarda nada além do que veio
    # da última importação da planilha.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_registros (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            lote               TEXT NOT NULL,
            of_trecho          TEXT NOT NULL,
            obra               TEXT NOT NULL,
            trecho             TEXT NOT NULL,
            subtrecho          TEXT NOT NULL,
            ano_semana         TEXT NOT NULL,
            peso_lic_lote      TEXT NOT NULL,
            qtd_tt_kg_prep     REAL,
            qtd_tt_kg_nprep    REAL,
            data_inicio_artia  TEXT NOT NULL,
            status             TEXT NOT NULL,
            importado_em       TEXT NOT NULL,
            UNIQUE(lote, of_trecho)
        )
    """)
    conn.commit()
    conn.close()


def listar_raizes() -> list:
    """Todos os diretórios raiz cadastrados, na ordem em que foram adicionados."""
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    linhas = conn.execute("SELECT caminho FROM auditoria_raizes ORDER BY id").fetchall()
    conn.close()
    return [l[0] for l in linhas]


def adicionar_raiz(caminho: str) -> bool:
    """Cadastra um novo diretório raiz. Retorna False se já estava na lista."""
    caminho = caminho.strip()
    if not caminho:
        return False
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    try:
        conn.execute("INSERT INTO auditoria_raizes(caminho) VALUES(?)", (caminho,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remover_raiz(caminho: str):
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    conn.execute("DELETE FROM auditoria_raizes WHERE caminho=?", (caminho,))
    conn.commit()
    conn.close()


def salvar_config(chave: str, valor: str):
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    conn.execute(
        "INSERT INTO auditoria_config(chave, valor) VALUES(?,?) "
        "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
        (chave, valor)
    )
    conn.commit()
    conn.close()


def carregar_config(chave: str, padrao: str = "") -> str:
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    row = conn.execute(
        "SELECT valor FROM auditoria_config WHERE chave=?", (chave,)
    ).fetchone()
    conn.close()
    return row[0] if row else padrao


def salvar_pacotes(lote: str, ofs: list):
    """
    Insere pares (lote, of_trecho) ignorando duplicatas.
    Retorna (inseridos, ignorados).
    """
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    cur = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inseridos = 0
    ignorados = 0
    for of in ofs:
        try:
            cur.execute(
                "INSERT INTO auditoria_pacotes(lote, of_trecho, importado_em) VALUES(?,?,?)",
                (lote, of, agora)
            )
            inseridos += 1
        except sqlite3.IntegrityError:
            ignorados += 1
    conn.commit()
    conn.close()
    return inseridos, ignorados


# ── base de busca (FASE 2: Buscar por Obra / Buscar por Pacote) ─────────


def substituir_registros(linhas: list) -> int:
    """
    Recarrega auditoria_registros DO ZERO a partir de `linhas` (lista de
    dicts com as chaves lote/of_trecho/obra/trecho/subtrecho/ano_semana/
    peso_lic_lote/qtd_tt_kg_prep/qtd_tt_kg_nprep/data_inicio_artia/status —
    ver auditoria.utilitarios.ler_linhas_busca_planilha). Chamada sempre
    que o usuário clica em "Atualizar Base de Busca". Retorna quantas
    linhas foram gravadas.
    """
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    cur = conn.cursor()
    cur.execute("DELETE FROM auditoria_registros")
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for linha in linhas:
        cur.execute("""
            INSERT OR REPLACE INTO auditoria_registros
            (lote, of_trecho, obra, trecho, subtrecho, ano_semana, peso_lic_lote,
             qtd_tt_kg_prep, qtd_tt_kg_nprep, data_inicio_artia, status, importado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            linha["lote"], linha["of_trecho"], linha["obra"], linha["trecho"], linha["subtrecho"],
            linha["ano_semana"], linha["peso_lic_lote"], linha["qtd_tt_kg_prep"], linha["qtd_tt_kg_nprep"],
            linha["data_inicio_artia"], linha["status"], agora,
        ))
    conn.commit()
    conn.close()
    return len(linhas)


def contar_registros_busca() -> int:
    """
    Quantos registros existem hoje em `auditoria_registros`. Usado pra
    diferenciar "a base nunca foi carregada" de "a base está carregada mas
    esse valor específico não existe" — as telas de busca mostram uma
    mensagem diferente pra cada caso (ver `_tratar_busca_vazia` em
    `auditoria/aba.py`).
    """
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    total = conn.execute("SELECT COUNT(*) FROM auditoria_registros").fetchone()[0]
    conn.close()
    return total


def buscar_por_obra(obra: str) -> list:
    """Todos os OF-TRECHO que pertencem a uma obra, em qualquer pacote."""
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    conn.row_factory = sqlite3.Row
    linhas = conn.execute(
        "SELECT * FROM auditoria_registros WHERE obra=? ORDER BY lote, trecho, subtrecho",
        (obra.strip(),)
    ).fetchall()
    conn.close()
    return linhas


def buscar_por_of_trecho(of_trecho: str):
    """Um OF-TRECHO específico (ex: 1956-2-01)."""
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    conn.row_factory = sqlite3.Row
    linha = conn.execute(
        "SELECT * FROM auditoria_registros WHERE of_trecho=?",
        (of_trecho.strip(),)
    ).fetchone()
    conn.close()
    return linha


def buscar_por_pacote(lote: str) -> list:
    """Todas as obras/trechos que pertencem a um pacote (LOTE)."""
    conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
    conn.row_factory = sqlite3.Row
    linhas = conn.execute(
        "SELECT * FROM auditoria_registros WHERE lote=? ORDER BY obra, trecho, subtrecho",
        (lote.strip(),)
    ).fetchall()
    conn.close()
    return linhas
