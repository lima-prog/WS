# -*- coding: utf-8 -*-
"""
Banco de dados SQLite compartilhado (hoje usado so pela aba de Corte, mas
fica aqui em nucleo/ porque e' o mesmo banco usado pelos outros modulos do
PROG_FLUXOS -- modulo_fluxos, modulo_consulta_pacotes, etc. -- entao
qualquer aba futura que precise gravar algo pode reusar essa mesma conexao
em vez de abrir outro arquivo .db).
"""
import sqlite3
from datetime import datetime

from nucleo.caminhos import CAMINHO_BANCO_DADOS


class BancoDados:
    def __init__(self):
        # conecta no banco compartilhado da raiz do projeto (mesmo usado pelos
        # outros módulos: modulo_fluxos, modulo_consulta_pacotes, etc.)
        self.conn = sqlite3.connect(CAMINHO_BANCO_DADOS)
        self.criar_tabelas()

    def criar_tabelas(self):
        # tabelas prefixadas com "corte_" para não colidir com as tabelas
        # dos outros módulos que também usam esse mesmo banco
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS corte_processamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_processamento TEXT NOT NULL,
            pasta_origem TEXT NOT NULL,
            total_arquivos INTEGER NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS corte_arquivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processamento_id INTEGER,
            nome_original TEXT NOT NULL,
            estrategia TEXT NOT NULL,
            eficiencia REAL NOT NULL,
            perda_mm REAL NOT NULL,
            FOREIGN KEY (processamento_id) REFERENCES corte_processamentos(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS corte_partes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo_id INTEGER,
            nome_parte TEXT NOT NULL,
            comprimento REAL NOT NULL,
            qtd_furos INTEGER NOT NULL,
            FOREIGN KEY (arquivo_id) REFERENCES corte_arquivos(id))''')
        # eventos de diagnóstico: corte forçado, segmento que não pôde ser
        # dividido (furo bloqueando) e erros de processamento
        c.execute('''CREATE TABLE IF NOT EXISTS corte_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processamento_id INTEGER,
            arquivo_id INTEGER,
            nome_arquivo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            detalhe TEXT NOT NULL,
            posicao_x REAL,
            comprimento_mm REAL,
            data_hora TEXT NOT NULL,
            FOREIGN KEY (processamento_id) REFERENCES corte_processamentos(id),
            FOREIGN KEY (arquivo_id) REFERENCES corte_arquivos(id))''')
        self.conn.commit()

    def registrar_processamento(self, pasta_origem, total_arquivos):
        c = self.conn.cursor()
        c.execute('INSERT INTO corte_processamentos (data_processamento,pasta_origem,total_arquivos) VALUES (?,?,?)',
                  (datetime.now().isoformat(), pasta_origem, total_arquivos))
        self.conn.commit()
        return c.lastrowid

    def registrar_arquivo(self, processamento_id, nome_original, estrategia, eficiencia, perda_mm):
        c = self.conn.cursor()
        c.execute('INSERT INTO corte_arquivos (processamento_id,nome_original,estrategia,eficiencia,perda_mm) VALUES (?,?,?,?,?)',
                  (processamento_id, nome_original, estrategia, eficiencia, perda_mm))
        self.conn.commit()
        return c.lastrowid

    def registrar_parte(self, arquivo_id, nome_parte, comprimento, qtd_furos):
        c = self.conn.cursor()
        c.execute('INSERT INTO corte_partes (arquivo_id,nome_parte,comprimento,qtd_furos) VALUES (?,?,?,?)',
                  (arquivo_id, nome_parte, comprimento, qtd_furos))
        self.conn.commit()

    def registrar_evento(self, processamento_id, arquivo_id, nome_arquivo, tipo,
                          detalhe, posicao_x=None, comprimento_mm=None):
        c = self.conn.cursor()
        c.execute('''INSERT INTO corte_eventos
            (processamento_id, arquivo_id, nome_arquivo, tipo, detalhe, posicao_x, comprimento_mm, data_hora)
            VALUES (?,?,?,?,?,?,?,?)''',
            (processamento_id, arquivo_id, nome_arquivo, tipo, detalhe,
             posicao_x, comprimento_mm, datetime.now().isoformat()))
        self.conn.commit()

    def buscar_eventos(self, tipo=None, nome_arquivo=None, data_desde=None):
        query = ("SELECT data_hora, nome_arquivo, tipo, detalhe, posicao_x, comprimento_mm "
                  "FROM corte_eventos WHERE 1=1")
        params = []
        if tipo and tipo != "Todos":
            query += " AND tipo = ?"
            params.append(tipo)
        if nome_arquivo:
            query += " AND nome_arquivo LIKE ?"
            params.append(f"%{nome_arquivo}%")
        if data_desde:
            query += " AND data_hora >= ?"
            params.append(data_desde)
        query += " ORDER BY data_hora DESC"
        c = self.conn.cursor()
        c.execute(query, params)
        return c.fetchall()

    # ── consultas para a tela "Arquivos Processados" (v2) ─────────────────────

    def buscar_partes_editadas(self, nome_arquivo=None):
        """Lista cada parte gerada (arquivo editado/dividido), com o nome do
        arquivo original que deu origem a ela."""
        query = '''SELECT pr.data_processamento, a.nome_original, p.nome_parte,
                          p.comprimento, p.qtd_furos
                   FROM corte_partes p
                   JOIN corte_arquivos a ON p.arquivo_id = a.id
                   JOIN corte_processamentos pr ON a.processamento_id = pr.id
                   WHERE 1=1'''
        params = []
        if nome_arquivo:
            query += " AND (a.nome_original LIKE ? OR p.nome_parte LIKE ?)"
            params += [f"%{nome_arquivo}%", f"%{nome_arquivo}%"]
        query += " ORDER BY p.id DESC"
        c = self.conn.cursor()
        c.execute(query, params)
        return c.fetchall()

    def buscar_arquivos_originais(self, nome_arquivo=None):
        """Lista cada arquivo original processado, com a estratégia usada e
        a quantidade de partes em que foi dividido."""
        query = '''SELECT pr.data_processamento, a.nome_original, a.estrategia,
                          (SELECT COUNT(*) FROM corte_partes p WHERE p.arquivo_id = a.id) AS qtd_partes,
                          a.perda_mm
                   FROM corte_arquivos a
                   JOIN corte_processamentos pr ON a.processamento_id = pr.id
                   WHERE 1=1'''
        params = []
        if nome_arquivo:
            query += " AND a.nome_original LIKE ?"
            params.append(f"%{nome_arquivo}%")
        query += " ORDER BY a.id DESC"
        c = self.conn.cursor()
        c.execute(query, params)
        return c.fetchall()
