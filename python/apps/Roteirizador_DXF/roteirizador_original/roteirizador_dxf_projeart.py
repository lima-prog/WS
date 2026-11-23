import os
import json
import shutil
import pandas as pd
import ezdxf
from datetime import datetime
import re
from collections import defaultdict
import sys
import numpy as np
import math
import sqlite3
import threading
import queue
import ctypes
import zlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
# ===== CONSTANTES =====
DENSIDADE_ACO = 7.85  # g/cm³
VERSAO = "ROTEIRIZADOR DXF PROJEART v19.4"
TITULO_RELATORIO_ORDENS = "RELATÓRIO DE ORDENS PROJEART v19.4"      # [UNIFICADOR] título da janela do app Relatório de Ordens
TOLERANCIA_FURO_CIRCULAR = 0.1  # Tolerância para considerar um círculo
# Nome do arquivo do banco de memória (SQLite), salvo ao lado do script.
# Guarda exceções aprendidas (itens que não geram DXF / ajustes manuais de
# fluxo) - válidas para QUALQUER obra, chave (identificador, posição).
NOME_BANCO_MEMORIA = "roteirizador_memoria.db"
# Prefixos de IDENTIFICADOR que NUNCA geram arquivo DXF/CAM (ex: barra e tubo
# são cortados por serra/outro processo, não por corte a laser/plasma) - o
# relatório de divergências não deve marcar esses itens como "faltante", já
# que a ausência de DXF é esperada e normal para eles.
PREFIXOS_SEM_CAM = ["BR", "TB"]
# Espessuras padrão do processo. Qualquer espessura lida da planilha que esteja
# próxima de um desses valores (dentro da tolerância) é "arredondada" para o
# valor padrão antes de virar nome de pasta - evita pastas variantes tipo
# "Fluxo 4 [6,40]" ao lado de "Fluxo 4 [6,35]" para a mesma espessura nominal.
ESPESSURAS_PADRAO = [
    1.25, 1.55, 1.70, 1.80, 1.95, 2.00, 2.25, 2.30, 2.65, 2.70,
    3.00, 3.35, 3.75, 4.25, 4.75, 6.35, 8.00, 9.50, 12.70, 16.00, 19.00, 22.20, 25.40
]
TOLERANCIA_PADRONIZACAO_ESPESSURA = 0.20  # mm
def padronizar_valor_espessura(esp):
    """
    Arredonda a espessura para o valor padrão mais próximo (ESPESSURAS_PADRAO),
    se estiver dentro da tolerância. Caso contrário, devolve o valor original
    sem alteração (evita "inventar" uma espessura que realmente é diferente).
    """
    if esp is None:
        return esp
    try:
        esp = float(esp)
    except (TypeError, ValueError):
        return esp
    mais_proxima = min(ESPESSURAS_PADRAO, key=lambda v: abs(v - esp))
    if abs(mais_proxima - esp) <= TOLERANCIA_PADRONIZACAO_ESPESSURA:
        return mais_proxima
    return esp
# ===== FUNÇÕES DE ANÁLISE =====
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
# ===== MÓDULO DE MEMÓRIA (SQLite) - exceções aprendidas entre obras =====
# Guarda duas coisas, sempre pela chave (identificador, posição), válidas
# para QUALQUER obra:
#   - ignorados: posições que o usuário marcou como "não gera DXF mesmo" -
#     nunca mais aparecem como faltante no relatório de divergências.
#   - ajustes_manuais: posições com fluxo definido manualmente pelo usuário,
#     sobrepondo TODAS as regras automáticas de decidir_fluxo_peca.
def _caminho_banco_memoria():
    """
    Caminho do banco de memória, salvo ao lado do executável/script (não da
    pasta de DXFs) - assim ele persiste entre execuções e entre obras
    diferentes.
    IMPORTANTE: quando o programa é empacotado em .exe com PyInstaller
    (principalmente no modo --onefile), `__file__` aponta para uma pasta
    TEMPORÁRIA que o Windows cria ao abrir o programa e APAGA ao fechar -
    então, se a gente salvasse o banco "ao lado de __file__" nesse caso, a
    memória inteira seria perdida toda vez que o programa fosse fechado e
    reaberto (é exatamente esse bug que fazia o Roteirizador esquecer os
    fluxos manuais e os motivos já definidos). Por isso, quando o programa
    está rodando como .exe (sys.frozen), usamos a pasta do PRÓPRIO .exe
    (sys.executable), que é fixa e não é apagada.
    """
    try:
        _dados = os.environ.get("PPCP_DADOS", "").strip().strip('"')
        if _dados:
            # MODO RÁPIDO (iniciar_ppcp.bat): o código roda de uma cópia local, mas a memória é
            # COMPARTILHADA e fica na pasta do servidor (PPCP_DADOS/roteirizador_original).
            base = os.path.join(os.path.abspath(_dados), "roteirizador_original")
            os.makedirs(base, exist_ok=True)
        elif getattr(sys, "frozen", False):
            base = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base = os.getcwd()
    return os.path.join(base, NOME_BANCO_MEMORIA)
def _normalizar_chave_memoria(identificador, posicao):
    """Normaliza (identificador, posição) para maiúsculas/sem espaço nas pontas,
    igual ao resto do script - garante que a busca não perca por causa de
    diferença de caixa alta/baixa ou espaço."""
    ident = str(identificador).upper().strip() if identificador else ""
    pos = str(posicao).upper().strip() if posicao else ""
    return ident, pos
def inicializar_memoria():
    """Cria o banco/tabelas de memória se ainda não existirem. Idempotente -
    pode ser chamada toda vez que o script roda, sem apagar dados existentes."""
    caminho = _caminho_banco_memoria()
    conn = sqlite3.connect(caminho)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ignorados (
                identificador TEXT NOT NULL,
                posicao TEXT NOT NULL,
                motivo TEXT,
                data_criacao TEXT,
                PRIMARY KEY (identificador, posicao)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ajustes_manuais (
                identificador TEXT NOT NULL,
                posicao TEXT NOT NULL,
                fluxo_manual TEXT NOT NULL,
                motivo TEXT,
                data_criacao TEXT,
                PRIMARY KEY (identificador, posicao)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS divergencias_tamanho_ignoradas (
                identificador TEXT NOT NULL,
                posicao TEXT NOT NULL,
                motivo TEXT,
                data_criacao TEXT,
                PRIMARY KEY (identificador, posicao)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS forcar_cam (
                identificador TEXT NOT NULL,
                posicao TEXT NOT NULL,
                motivo TEXT,
                data_criacao TEXT,
                PRIMARY KEY (identificador, posicao)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS padrao_planilha_manual (
                identificador TEXT NOT NULL,
                posicao TEXT NOT NULL,
                motivo TEXT,
                data_criacao TEXT,
                PRIMARY KEY (identificador, posicao)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cores_fluxo_customizadas (
                fluxo TEXT PRIMARY KEY,
                cor TEXT NOT NULL,
                data_criacao TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferencias_ui (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()
    return caminho
def carregar_memoria():
    """
    Carrega as duas tabelas do banco de memória em dicionários rápidos de
    consulta, chaveados por (identificador, posição) normalizados:
      - dict_ignorados: {(identificador, posicao): motivo}
      - dict_ajustes:   {(identificador, posicao): fluxo_manual}
    Chamar isso UMA VEZ no início do processamento (não a cada peça).
    """
    inicializar_memoria()
    caminho = _caminho_banco_memoria()
    conn = sqlite3.connect(caminho)
    dict_ignorados = {}
    dict_ajustes = {}
    try:
        for identificador, posicao, motivo in conn.execute("SELECT identificador, posicao, motivo FROM ignorados"):
            dict_ignorados[(identificador, posicao)] = motivo or ""
        for identificador, posicao, fluxo_manual in conn.execute("SELECT identificador, posicao, fluxo_manual FROM ajustes_manuais"):
            dict_ajustes[(identificador, posicao)] = fluxo_manual
    finally:
        conn.close()
    return dict_ignorados, dict_ajustes
def marcar_ignorado(identificador, posicao, motivo=""):
    """Marca (identificador, posição) como 'não gera DXF mesmo' - vale pra
    qualquer obra a partir de agora. Sobrescreve se já existir (mesma chave)."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    caminho = inicializar_memoria()
    conn = sqlite3.connect(caminho)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO ignorados (identificador, posicao, motivo, data_criacao) VALUES (?, ?, ?, ?)",
            (ident, pos, motivo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    finally:
        conn.close()
def marcar_ajuste_manual(identificador, posicao, fluxo_manual, motivo=""):
    """Salva um fluxo manual para (identificador, posição) - vale pra qualquer
    obra a partir de agora, sobrepondo as regras automáticas."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    caminho = inicializar_memoria()
    conn = sqlite3.connect(caminho)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO ajustes_manuais (identificador, posicao, fluxo_manual, motivo, data_criacao) VALUES (?, ?, ?, ?, ?)",
            (ident, pos, fluxo_manual, motivo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    finally:
        conn.close()
    log(f"🧠 Ajuste manual gravado na memória ('{caminho}'): identificador='{ident}' / posição='{pos}' -> '{fluxo_manual}'")
def remover_ignorado(identificador, posicao):
    """Remove uma entrada da tabela de ignorados (caso tenha sido marcada por engano)."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute("DELETE FROM ignorados WHERE identificador=? AND posicao=?", (ident, pos))
        conn.commit()
    finally:
        conn.close()
def remover_ajuste_manual(identificador, posicao):
    """Remove uma entrada da tabela de ajustes manuais (caso tenha sido marcada por engano)."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute("DELETE FROM ajustes_manuais WHERE identificador=? AND posicao=?", (ident, pos))
        conn.commit()
    finally:
        conn.close()
# ===== Memória: divergências de TAMANHO (DXF x planilha) conferidas =====
# Quando o usuário revisa uma divergência de dimensão (aba "📐 Divergência de
# Tamanho") e confirma que está tudo certo (ex: peça dobrada, corte especial,
# erro de digitação já sabido na planilha), ela é marcada aqui - vale para
# QUALQUER obra, pela chave (identificador, posição), e some da lista de
# divergências em rodadas futuras.
def carregar_divergencias_tamanho_ignoradas():
    """Carrega o dict {(identificador, posicao): motivo} de divergências de
    tamanho já conferidas/aceitas pelo usuário."""
    inicializar_memoria()
    conn = sqlite3.connect(_caminho_banco_memoria())
    dict_ignoradas = {}
    try:
        for identificador, posicao, motivo in conn.execute(
                "SELECT identificador, posicao, motivo FROM divergencias_tamanho_ignoradas"):
            dict_ignoradas[(identificador, posicao)] = motivo or ""
    finally:
        conn.close()
    return dict_ignoradas
def marcar_divergencia_tamanho_ignorada(identificador, posicao, motivo=""):
    """Marca (identificador, posição) como 'divergência de tamanho conferida/
    aceita' - vale para qualquer obra a partir de agora."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute(
            "INSERT OR REPLACE INTO divergencias_tamanho_ignoradas "
            "(identificador, posicao, motivo, data_criacao) VALUES (?, ?, ?, ?)",
            (ident, pos, motivo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    finally:
        conn.close()
def remover_divergencia_tamanho_ignorada(identificador, posicao):
    """Remove uma entrada da tabela de divergências de tamanho conferidas
    (caso o usuário queira voltar a ver aquele alerta)."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute(
            "DELETE FROM divergencias_tamanho_ignoradas WHERE identificador=? AND posicao=?", (ident, pos)
        )
        conn.commit()
    finally:
        conn.close()
# ===== Memória: FORÇAR geração de CAM (desconsiderar BR/TB) =====
# Por padrão, identificadores que começam com BR (barra) ou TB (tubo) nunca
# geram DXF/CAM (cortados por serra) e por isso aparecem separados na aba
# "ℹ️ Sem CAM", fora da lista de faltantes. Se para uma posição específica
# isso NÃO for verdade (ex: uma "barra" que na prática precisa ser cortada a
# laser), o usuário pode "forçar CAM" nela - vale para qualquer obra a partir
# de agora, e ela passa a ser tratada normalmente (aparece em faltantes caso
# realmente não tenha DXF correspondente).
def carregar_forcar_cam():
    """Carrega o dict {(identificador, posicao): motivo} de itens marcados
    para NÃO seguir a regra automática de 'sem CAM' (BR/TB)."""
    inicializar_memoria()
    conn = sqlite3.connect(_caminho_banco_memoria())
    dict_forcados = {}
    try:
        for identificador, posicao, motivo in conn.execute(
                "SELECT identificador, posicao, motivo FROM forcar_cam"):
            dict_forcados[(identificador, posicao)] = motivo or ""
    finally:
        conn.close()
    return dict_forcados
def marcar_forcar_cam(identificador, posicao, motivo=""):
    """Marca (identificador, posição) para desconsiderar a regra automática
    de 'sem CAM' (BR/TB) - vale para qualquer obra a partir de agora."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute(
            "INSERT OR REPLACE INTO forcar_cam (identificador, posicao, motivo, data_criacao) VALUES (?, ?, ?, ?)",
            (ident, pos, motivo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    finally:
        conn.close()
def remover_forcar_cam(identificador, posicao):
    """Remove uma entrada da tabela de CAM forçado (caso tenha sido marcada
    por engano, voltando ao comportamento automático BR/TB)."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute("DELETE FROM forcar_cam WHERE identificador=? AND posicao=?", (ident, pos))
        conn.commit()
    finally:
        conn.close()
# ===== Memória: mover manualmente para "[PADRÃO] PLANILHA" (Faltantes) =====
# IMPORTANTE - diferença crucial em relação a marcar_ignorado():
# marcar_ignorado() é uma exclusão DEFINITIVA (a posição nunca mais aparece em
# nenhuma lista, mesmo que um DXF real apareça para ela depois). Já esta
# marcação (padrao_planilha_manual) é uma reclassificação "enquanto não há
# DXF" - em analisar_divergencias(), a verificação de "chave in dxf_chaves"
# continua tendo prioridade MÁXIMA: se em uma obra/rodada futura aparecer um
# DXF de verdade para essa mesma posição, o roteirizador processa e encontra
# normalmente, sem nenhuma interferência desta marcação. Ou seja, isso NUNCA
# desconsidera CAM que realmente exista - só evita que a posição apareça como
# "faltante" enquanto ela seguir sem DXF (ex: alguma liberação futura ainda
# pode gerar CAM para ela).
def carregar_padrao_planilha_manual():
    """Carrega o dict {(identificador, posicao): motivo} de itens movidos
    manualmente para "[PADRÃO] PLANILHA" na aba de Faltantes."""
    inicializar_memoria()
    conn = sqlite3.connect(_caminho_banco_memoria())
    dict_padrao = {}
    try:
        for identificador, posicao, motivo in conn.execute(
                "SELECT identificador, posicao, motivo FROM padrao_planilha_manual"):
            dict_padrao[(identificador, posicao)] = motivo or ""
    finally:
        conn.close()
    return dict_padrao
def marcar_padrao_planilha_manual(identificador, posicao, motivo=""):
    """Marca (identificador, posição) como "[PADRÃO] PLANILHA" - vale para
    qualquer obra a partir de agora, MAS não impede que um DXF real futuro
    para essa mesma posição seja encontrado e processado normalmente (ver
    nota acima em analisar_divergencias)."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute(
            "INSERT OR REPLACE INTO padrao_planilha_manual (identificador, posicao, motivo, data_criacao) "
            "VALUES (?, ?, ?, ?)",
            (ident, pos, motivo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    finally:
        conn.close()
def remover_padrao_planilha_manual(identificador, posicao):
    """Remove uma entrada da tabela padrao_planilha_manual (caso tenha sido
    marcada por engano, voltando a aparecer em Faltantes se ainda sem DXF)."""
    ident, pos = _normalizar_chave_memoria(identificador, posicao)
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute("DELETE FROM padrao_planilha_manual WHERE identificador=? AND posicao=?", (ident, pos))
        conn.commit()
    finally:
        conn.close()
# ===== Memória: cores customizadas por fluxo (aba "⚖️ Peso por Fluxo") =====
# Sobrepõe a cor automática (_cor_para_fluxo) escolhida pelo usuário no editor
# de cores - vale para QUALQUER obra futura, até ser trocada de novo ou
# restaurada ao padrão.
def carregar_cores_fluxo_customizadas():
    """Carrega o dict {fluxo: cor} das cores customizadas pelo usuário."""
    inicializar_memoria()
    conn = sqlite3.connect(_caminho_banco_memoria())
    dict_cores = {}
    try:
        for fluxo, cor in conn.execute("SELECT fluxo, cor FROM cores_fluxo_customizadas"):
            dict_cores[fluxo] = cor
    finally:
        conn.close()
    return dict_cores
def salvar_cor_fluxo_customizada(fluxo, cor):
    """Salva/atualiza a cor customizada de um fluxo - vale para qualquer
    obra futura."""
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cores_fluxo_customizadas (fluxo, cor, data_criacao) VALUES (?, ?, ?)",
            (fluxo, cor, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    finally:
        conn.close()
def remover_cor_fluxo_customizada(fluxo):
    """Remove a cor customizada de um fluxo, voltando à cor automática
    (_cor_para_fluxo)."""
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute("DELETE FROM cores_fluxo_customizadas WHERE fluxo=?", (fluxo,))
        conn.commit()
    finally:
        conn.close()
# ===== Memória: preferências gerais de interface (chave/valor) =====
# Usada, por ora, para lembrar o último tipo de gráfico escolhido na aba
# "⚖️ Peso por Fluxo" (barras/pizza/velas) entre execuções do programa.
def carregar_preferencia_ui(chave, padrao=None):
    """Carrega uma preferência de UI salva (ex: tipo de gráfico escolhido).
    Retorna `padrao` se a chave nunca foi salva."""
    inicializar_memoria()
    conn = sqlite3.connect(_caminho_banco_memoria())
    try:
        linha = conn.execute("SELECT valor FROM preferencias_ui WHERE chave=?", (chave,)).fetchone()
        return linha[0] if linha else padrao
    finally:
        conn.close()
def salvar_preferencia_ui(chave, valor):
    """Salva uma preferência de UI (chave/valor) - vale para qualquer obra
    futura, até ser trocada de novo."""
    conn = sqlite3.connect(inicializar_memoria())
    try:
        conn.execute(
            "INSERT OR REPLACE INTO preferencias_ui (chave, valor) VALUES (?, ?)", (chave, valor)
        )
        conn.commit()
    finally:
        conn.close()
# A revisão dos itens faltantes (marcar "não gera DXF" ou definir um fluxo
# manual) deixou de ser feita por prompts de console - agora é feita direto
# na tela gráfica do relatório de divergências (ver tela_relatorio_divergencias),
# usando os checkboxes das linhas e os botões de ação. As funções de dados
# marcar_ignorado()/marcar_ajuste_manual() acima continuam sendo o que
# efetivamente grava na memória (SQLite); só a interface mudou.
def calcular_peso(largura_mm, altura_mm, espessura_mm):
    """
    Calcula o peso de uma peça em kg
    Volume = largura × altura × espessura (em mm³)
    Converte para cm³ (dividindo por 1000)
    Peso = Volume (cm³) × densidade (g/cm³) / 1000 (para kg)
    """
    if None in [largura_mm, altura_mm, espessura_mm] or any(v <= 0 for v in [largura_mm, altura_mm, espessura_mm] if v):
        return 0.0

    # Calcular volume em mm³
    volume_mm3 = largura_mm * altura_mm * espessura_mm

    # Converter para cm³ (1 cm³ = 1000 mm³)
    volume_cm3 = volume_mm3 / 1000.0

    # Calcular peso em kg (densidade em g/cm³, dividir por 1000 para kg)
    peso_kg = (volume_cm3 * DENSIDADE_ACO) / 1000.0

    return peso_kg
def analisar_furos_dxf(caminho):
    """
    Analisa o arquivo DXF para identificar furos na peça
    Retorna: (tem_furo, tipo_furo, diametro, descricao, quantidade_furos)
    - tem_furo: bool
    - tipo_furo: "CIRCULAR", "OBLONGO", "MISTO" ou None
    - diametro: diâmetro do furo (mm) ou dimensões "LARGxALT" para oblongo
    - descricao: string formatada para exibição
    - quantidade_furos: número total de furos encontrados
    """
    try:
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()

        furos_circulares = []
        furos_oblongos = []

        for e in msp:
            # Detectar círculos (furos circulares)
            if e.dxftype() == "CIRCLE":
                raio = e.dxf.radius
                diametro = raio * 2
                furos_circulares.append(diametro)

            # Detectar elipses (podem ser furos oblongos)
            elif e.dxftype() == "ELLIPSE":
                # Para elipses, calcular eixo maior e menor
                major_axis = e.dxf.major_axis
                ratio = e.dxf.ratio

                # Calcular dimensões
                major_length = math.sqrt(major_axis[0]**2 + major_axis[1]**2) * 2
                minor_length = major_length * ratio

                # Se a diferença entre os eixos for pequena, é praticamente um círculo
                if abs(major_length - minor_length) < TOLERANCIA_FURO_CIRCULAR:
                    furos_circulares.append(major_length)
                else:
                    furos_oblongos.append((major_length, minor_length))

            # Detectar LWPolyline com arcos (pode ser oblongo)
            elif e.dxftype() == "LWPOLYLINE":
                # Verificar se tem bulges (arcos)
                if hasattr(e, 'get_points') and hasattr(e, 'get_bulge'):
                    # Polilinhas com arcos podem representar oblongos
                    points = list(e.get_points())
                    if len(points) >= 4 and e.closed:
                        # Calcular bounding box
                        xs = [p[0] for p in points]
                        ys = [p[1] for p in points]
                        width = max(xs) - min(xs)
                        height = max(ys) - min(ys)
                        if width > 0 and height > 0:
                            furos_oblongos.append((width, height))

        # Contar total de furos
        quantidade_furos = len(furos_circulares) + len(furos_oblongos)

        # Determinar o tipo de furo predominante
        if furos_circulares and not furos_oblongos:
            # Pega o maior diâmetro (mais relevante)
            diametro = max(furos_circulares)
            return True, "CIRCULAR", f"{diametro:.1f}", f"CIRCULAR ø{diametro:.1f}mm ({quantidade_furos} furos)", quantidade_furos

        elif furos_oblongos and not furos_circulares:
            # Pega o maior oblongo
            maior = max(furos_oblongos, key=lambda x: x[0] * x[1])
            larg, alt = maior
            return True, "OBLONGO", f"{larg:.1f}x{alt:.1f}", f"OBLONGO {larg:.1f}x{alt:.1f}mm ({quantidade_furos} furos)", quantidade_furos

        elif furos_circulares and furos_oblongos:
            # Misturado - prioriza oblongo (mais complexo)
            maior_oblongo = max(furos_oblongos, key=lambda x: x[0] * x[1])
            larg, alt = maior_oblongo
            return True, "MISTO", f"{larg:.1f}x{alt:.1f}", f"MISTO (maior: {larg:.1f}x{alt:.1f}mm) - {quantidade_furos} furos", quantidade_furos
        else:
            return False, None, None, "SEM FURO", 0

    except Exception as e:
        log(f"Erro ao analisar furos do DXF: {e}")
        return False, None, None, "ERRO NA ANÁLISE", 0
def obter_dimensoes_dxf(caminho):
    try:
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()
        xs = []
        ys = []
        for e in msp:
            try:
                if hasattr(e.dxf, "start"):
                    xs.append(e.dxf.start[0])
                    ys.append(e.dxf.start[1])
                if hasattr(e.dxf, "end"):
                    xs.append(e.dxf.end[0])
                    ys.append(e.dxf.end[1])
                if hasattr(e.dxf, "center"):
                    xs.append(e.dxf.center[0])
                    ys.append(e.dxf.center[1])
                # Correção (roteirizador v19.4): uma peça sem furo/recorte
                # algum (só o contorno externo, desenhado como uma única
                # LWPOLYLINE) não tem NENHUMA entidade com .dxf.start/.dxf.end/
                # .dxf.center - as três checagens acima ficavam sem nada para
                # coletar e a função retornava (None, None), o que quebrava
                # mais adiante em qualquer lugar que fizesse max(largura,
                # altura) (ex: decidir_fluxo) com o erro "'>' not supported
                # between instances of 'NoneType' and 'NoneType'". Além disso,
                # mesmo em peças COM furo, o bounding box calculado só a
                # partir de LINE/ARC/CIRCLE ficava menor que o tamanho real da
                # peça, pois ignorava o contorno externo por completo. Por
                # isso agora também lemos os vértices da própria LWPOLYLINE
                # (get_points()) e incluímos nas mesmas listas xs/ys usadas no
                # cálculo final - isso não remove nem altera nenhuma leitura
                # já existente, só adiciona a informação que faltava.
                if e.dxftype() == "LWPOLYLINE":
                    for ponto in e.get_points():
                        xs.append(ponto[0])
                        ys.append(ponto[1])
            except:
                pass
        if not xs:
            return None, None
        largura = abs(max(xs) - min(xs))
        altura = abs(max(ys) - min(ys))
        return largura, altura
    except Exception as e:
        log(f"Erro ao ler DXF: {e}")
        return None, None
def _contar_cantos_contorno_linhas(segmentos):
    """
    Recebe uma lista de segmentos (par de pontos (x,y) arredondados) e tenta
    encaixá-los ponta a ponta num único contorno fechado. Se conseguir,
    retorna a quantidade de "cantos reais" - pontos onde a direção do
    percurso realmente muda (colineares consecutivos são unidos e NÃO contam
    como canto extra, para não confundir uma borda reta desenhada em vários
    pedaços com um degrau de verdade).
    Retorna None se os segmentos não formarem um único contorno fechado
    simples (ex: peça com furo feito de linhas, formas desconexas etc.) -
    nesses casos, não arriscamos nenhuma conclusão.
    """
    if len(segmentos) < 5:
        # Um retângulo simples tem 4 lados - com 4 segmentos ou menos não há
        # como existir um degrau
        return None
    pontos = [segmentos[0][0], segmentos[0][1]]
    usados = {0}
    while len(usados) < len(segmentos):
        ultimo = pontos[-1]
        achou = False
        for i, (p1, p2) in enumerate(segmentos):
            if i in usados:
                continue
            if p1 == ultimo:
                pontos.append(p2)
                usados.add(i)
                achou = True
                break
            elif p2 == ultimo:
                pontos.append(p1)
                usados.add(i)
                achou = True
                break
        if not achou:
            return None
    if len(pontos) > 1 and pontos[0] == pontos[-1]:
        pontos = pontos[:-1]
    n = len(pontos)
    if n < 4:
        return None
    def normaliza(dx, dy):
        if abs(dx) < 0.01:
            dx = 0.0
        if abs(dy) < 0.01:
            dy = 0.0
        return (math.copysign(1, dx) if dx != 0 else 0,
                math.copysign(1, dy) if dy != 0 else 0)
    def eh_diagonal(p1, p2):
        # Aresta diagonal (chanfro/corte em ângulo) - tratada pela regra de
        # ângulo separada (possui_angulo_dxf), não deve contar como "canto de
        # degrau" aqui, senão um simples chanfro de canto vira falso positivo
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return abs(dx) > 0.01 and abs(dy) > 0.01
    cantos = 0
    for i in range(n):
        p_ant = pontos[i - 1]
        p_atual = pontos[i]
        p_prox = pontos[(i + 1) % n]
        # Se a aresta de entrada OU de saída deste vértice é diagonal, este
        # vértice faz parte de um chanfro/corte em ângulo, não de um degrau -
        # não conta como canto aqui (fica só para a regra de ângulo decidir)
        if eh_diagonal(p_ant, p_atual) or eh_diagonal(p_atual, p_prox):
            continue
        dir1 = normaliza(p_atual[0] - p_ant[0], p_atual[1] - p_ant[1])
        dir2 = normaliza(p_prox[0] - p_atual[0], p_prox[1] - p_atual[1])
        if dir1 != dir2:
            cantos += 1
    return cantos
def possui_recorte_escalonado(caminho):
    """
    Detecta peças com contorno "em degrau" (ex: uma chapa/base com uma aba ou
    saliência mais estreita no meio, tipo formato de "T" ou "chapéu") feitas
    SÓ com segmentos LINE retos (sem ARC/SPLINE/ELLIPSE) - por isso não são
    pegas por possui_irregularidade() nem por possui_angulo_dxf() (os cantos
    são todos de 90°, não há corte em ângulo).
    Funciona para qualquer tamanho da peça (maior ou menor), pois é uma
    verificação de FORMATO (contagem de cantos do contorno), não de dimensão -
    qualquer peça com mais de 4 cantos reais no contorno externo (um
    retângulo simples tem 4) é considerada "em degrau".
    """
    try:
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()
        segmentos = []
        for e in msp:
            if e.dxftype() == "LINE":
                try:
                    p1 = (round(e.dxf.start[0], 3), round(e.dxf.start[1], 3))
                    p2 = (round(e.dxf.end[0], 3), round(e.dxf.end[1], 3))
                    segmentos.append((p1, p2))
                except Exception:
                    pass
        cantos = _contar_cantos_contorno_linhas(segmentos)
        if cantos is None:
            return False
        return cantos > 4
    except Exception as ex:
        log(f"Erro ao analisar recorte escalonado do DXF: {ex}")
        return False
def possui_irregularidade(caminho):
    try:
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()
        for e in msp:
            if e.dxftype() in ["ARC", "SPLINE", "ELLIPSE"]:
                return True
        # Nenhum ARC/SPLINE/ELLIPSE encontrado - ainda assim, a peça pode ter
        # um contorno em degrau feito só de linhas retas (ex: chapa com aba
        # mais estreita no meio) - isso também conta como irregularidade,
        # pois manualmente/pelas outras regras não seria detectado.
        if possui_recorte_escalonado(caminho):
            return True
        return False
    except:
        return False
def irregularidade_so_arcos_pequenos(caminho, limite_mm=150.0):
    """True quando a "irregularidade" do DXF é SÓ de arcos pequenos - furo oblongo (rasgo) ou canto arredondado: tem arco, nenhum
    arco com diâmetro maior que `limite_mm` (150mm, o mesmo limite do "recorte grande"), sem SPLINE/ELLIPSE e sem contorno em degrau."""
    try:
        msp = ezdxf.readfile(caminho).modelspace()
        tem_arco = False
        for e in msp:
            t = e.dxftype()
            if t in ("SPLINE", "ELLIPSE"):
                return False
            if t == "ARC":
                tem_arco = True
                if e.dxf.radius * 2 > limite_mm:
                    return False
        return tem_arco and not possui_recorte_escalonado(caminho)
    except Exception:
        return False
def normalizar_posicao(pos):
    return pos.replace("@", "_")
def extrair_quantidade_arquivo(nome_arquivo):
    """
    Extrai a quantidade do nome do arquivo DXF (ex: Q8, Q6, Q4)
    """
    try:
        match = re.search(r"Q(\d+)", nome_arquivo.upper())
        if match:
            return int(match.group(1))
    except:
        pass
    return None
def extrair_posicao_base_conjunto(pos_arquivo):
    """
    Remove o sufixo de "lado" do final da posição, usado para identificar peças
    que fazem parte do mesmo conjunto (ex: lado esquerdo/direito de um mesmo
    perfil, cada um com seu próprio arquivo DXF).
    Duas formas aceitas:
    - "@N" no final (ex: "-124@2", "2-01_-124@2" -> "-124"/"2-01_-124") - sempre
      aceito, é um separador exclusivo desse padrão, sem risco de confundir com
      outra coisa.
    - "_2"/"_3" ou "-2"/"-3" no final (ex: "-124_2", "2-01_-124_2" -> "-124"/
      "2-01_-124") - só é aceito quando o caractere ANTES do separador de lado
      for um DÍGITO (ex: "...114_2", onde antes do "_2" vem "4"), mesmo que
      venha um prefixo de trecho antes (ex: "2-01_"). Isso evita confundir com
      marcas reais que usam hífen no nome e terminam em LETRA antes do número,
      como "PDG-2", "MF-2", "CH-2" (posições distintas de verdade, não lados).
    """
    if not pos_arquivo:
        return pos_arquivo
    match_arroba = re.match(r'^(.+)@\d+$', pos_arquivo)
    if match_arroba:
        return match_arroba.group(1)
    match_numerico = re.match(r'^(.*\d)[_-]([23])$', pos_arquivo)
    if match_numerico:
        return match_numerico.group(1)
    return pos_arquivo
def extrair_posicao_base(pos_arquivo):
    """
    Extrai a posição base do nome do arquivo, removendo apenas o sufixo _U quando presente.
    NÃO remove nada antes do primeiro underscore para preservar o trecho da obra (ex: 5-01_)
    """
    if not pos_arquivo:
        return pos_arquivo

    # Lista de sufixos a remover (apenas _U por enquanto)
    sufixos = ['_U']

    for sufixo in sufixos:
        if pos_arquivo.endswith(sufixo):
            return pos_arquivo[:-len(sufixo)]

    # Se não tiver sufixo conhecido, retorna original
    return pos_arquivo
# Peça com mais de 6000mm é dividida em partes: o DXF de cada parte leva a letra entre
# colchetes na posição (ex: "110-2[A]" e "110-2[B]"). Para a planilha/Focco é UMA posição só.
_RE_PARTE = re.compile(r"\s*[\[\(]\s*([A-Za-z])\s*[\]\)]")


def separar_parte_posicao(texto):
    """'110-2[A]' -> ('110-2', 'A'); '110-2[B]_U' -> ('110-2_U', 'B'); sem marca -> (texto, None)."""
    t = str(texto or "")
    m = _RE_PARTE.search(t)
    if not m:
        return t, None
    return (t[:m.start()] + t[m.end():]).strip(), m.group(1).upper()


def extrair_parte_nome(nome):
    """Letra da parte ('A', 'B'...) no nome do DXF, ou None se a peça não foi dividida."""
    try:
        return separar_parte_posicao(os.path.splitext(nome)[0].split(" - ")[0])[1]
    except Exception:
        return None


def _status_dimensao(l_dxf, a_dxf, l_plan, desenv, compr, l_alt, tol):
    """Mesma checagem de dimensão usada por arquivo, para conferir o conjunto A+B."""
    st = comparar_dimensoes_com_tolerancia(l_dxf, a_dxf, l_plan, desenv, tol)
    if st != "OK" and compr is not None and comparar_dimensoes_com_tolerancia(l_dxf, a_dxf, l_plan, compr, tol) == "OK":
        st = "OK"
    if st != "OK" and l_alt is not None:
        if comparar_dimensoes_com_tolerancia(l_dxf, a_dxf, l_alt, desenv, tol) == "OK":
            st = "OK"
        elif compr is not None and comparar_dimensoes_com_tolerancia(l_dxf, a_dxf, l_alt, compr, tol) == "OK":
            st = "OK"
    return st


def extrair_nome(nome):
    """Extrai OF e POSIÇÃO do nome do arquivo DXF (sem a marca de parte [A]/[B])"""
    try:
        nome_sem_extensao = os.path.splitext(nome)[0]
        partes = nome_sem_extensao.split(" - ")
        pos = normalizar_posicao(separar_parte_posicao(partes[0].strip())[0])
        of = partes[1].replace("OF", "").strip()
        return of.upper(), pos.upper()
    except:
        return None, None
def verificar_terca_z(nome_arquivo, pos_planilha, def_planilha):
    """
    Verifica se é uma Terça Z com base em:
    - Nome do arquivo começando com TZ
    - POSIÇÃO na planilha começando com TZ
    - DEFINIÇÃO na planilha começando com Z
    """
    # a posição pode vir com o prefixo do trecho colado (ex.: "4-01_TZ-1", como no relatório do Focco/WF): ignora o prefixo
    sem_trecho = lambda t: re.sub(r"^\d+-\d+_", "", t)
    nome_upper = sem_trecho(nome_arquivo.upper())
    pos_upper = sem_trecho(str(pos_planilha).upper().strip()) if pos_planilha else ""
    def_upper = str(def_planilha).upper().strip() if def_planilha else ""

    # Verificar condições
    if (nome_upper.startswith("TZ") and
        pos_upper.startswith("TZ") and
        def_upper.startswith("Z")):
        return True

    return False
def extrair_tipo_identificador(identificador, posicao=None):
    """
    Extrai o tipo principal do identificador:
    - PRIORIDADE 1: Verificar se deve IGNORAR (campos vazios)
    - PRIORIDADE 2: Verificar IGNORADOS específicos (BR_RED, W_, PS, Terças Z)
    - PRIORIDADE 3: Classificar nas categorias principais
    """

    # ===== PRIORIDADE 1: CAMPOS VAZIOS =====
    # Se posição for vazia ou None, IGNORAR
    if posicao is None or pd.isna(posicao) or str(posicao).strip() == '':
        return "IGNORADO"

    # Se identificador for vazio ou None, IGNORAR
    if identificador is None or pd.isna(identificador) or str(identificador).strip() == '':
        return "IGNORADO"

    id_upper = str(identificador).upper().strip()
    pos_upper = str(posicao).upper().strip()

    # ===== PRIORIDADE 2: IGNORADOS ESPECÍFICOS =====
    # Terças Z (identificador começa com Z) - IGNORAR
    if id_upper.startswith("Z"):
        return "IGNORADO"

    # Outros ignorados
    if (id_upper.startswith("BR_RED") or
        id_upper.startswith("W_") or
        id_upper.startswith("PS")):
        return "IGNORADO"

    # ===== PRIORIDADE 3: CATEGORIAS PRINCIPAIS =====
    if id_upper.startswith("L"):
        return "L"
    elif id_upper.startswith("ZD"):
        return "ZD"
    elif id_upper.startswith("CH."):
        return "CH."
    elif id_upper.startswith("U"):
        return "U"
    elif id_upper.startswith("J"):
        return "J"
    elif "CHAPA_XADREZ" in id_upper:
        return "CHAPA_XADREZ"
    elif id_upper.startswith("CAR"):
        return "CAR"
    elif id_upper.startswith("C"):
        return "C"
    else:
        return "OUTROS"
def eh_terca_z(pos_planilha, identificador):
    """Verifica se é uma Terça Z (para tolerância especial) - "ZD" não conta
    (é chapa dobrada, categoria diferente que só coincide na letra inicial)."""
    if not pos_planilha or not identificador:
        return False

    id_upper = str(identificador).upper().strip()

    # Se identificador começa com Z (e não é "ZD"), é Terça Z
    return id_upper.startswith("Z") and not id_upper.startswith("ZD")
def carregar_planilha_xlsx(caminho, engine=None):
    """Carrega planilha no formato Excel (tabela dinâmica) - mantido para compatibilidade."""
    if os.path.isdir(caminho):
        for arq in os.listdir(caminho):
            if arq.endswith(".xlsx"):
                caminho = os.path.join(caminho, arq)
                break
    log(f"Excel localizado: {caminho}")
    df = pd.read_excel(caminho, engine=engine)
    return _normalizar_planilha_pivot(df)


def _normalizar_planilha_pivot(df):
    """Normaliza a planilha no formato da tabela dinâmica (OF, POSIÇÃO, IDENTIFICADOR, DEFINIÇÃO...)."""
    # Dicionário para armazenar o nome real de cada coluna
    colunas = {
        'OF': None,
        'POSIÇAO': None,
        'IDENTIFICADOR': None,
        'DEFINIÇAO': None,
        'LARGURA': None,
        'DESENVOLVIMENTO': None,
        'COMPRIMENTO': None,
        'ESPESSURA': None,
        'Soma de Qtd': None
    }
    # Mapear colunas existentes na planilha (case insensitive e removendo espaços)
    for col in df.columns:
        col_upper = col.upper().strip()

        if col_upper == 'OF':
            colunas['OF'] = col
        elif col_upper in ['POSIÇAO', 'POSICAO']:
            colunas['POSIÇAO'] = col
        elif col_upper == 'IDENTIFICADOR':
            colunas['IDENTIFICADOR'] = col
        elif col_upper in ['DEFINIÇAO', 'DEFINICAO']:
            colunas['DEFINIÇAO'] = col
        elif col_upper == 'LARGURA':
            colunas['LARGURA'] = col
        elif col_upper == 'DESENVOLVIMENTO':
            colunas['DESENVOLVIMENTO'] = col
        elif col_upper == 'COMPRIMENTO':
            colunas['COMPRIMENTO'] = col
        elif col_upper == 'ESPESSURA':
            colunas['ESPESSURA'] = col
        elif 'SOMA' in col_upper and 'QTD' in col_upper:
            colunas['Soma de Qtd'] = col
    log("\n--- MAPEAMENTO DE COLUNAS ---")
    for campo, coluna in colunas.items():
        if coluna:
            log(f"✅ {campo:<15} -> '{coluna}'")
        else:
            log(f"⚠️  {campo:<15} -> NÃO ENCONTRADA")
    # Função para converter string com vírgula para float
    def converter_para_float(valor):
        if pd.isna(valor):
            return None
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            valor_limpo = valor.strip().replace(',', '.')
            try:
                return float(valor_limpo)
            except:
                return None
        return None
    # Criar colunas normalizadas
    if colunas['OF']:
        df["OF_N"] = df[colunas['OF']].astype(str).str.upper().str.strip()

    if colunas['POSIÇAO']:
        df["POS_N"] = df[colunas['POSIÇAO']].astype(str).str.upper().str.strip()

    if colunas['IDENTIFICADOR']:
        df["ID_N"] = df[colunas['IDENTIFICADOR']].astype(str).str.upper().str.strip()

    if colunas['DEFINIÇAO']:
        df["DEF_N"] = df[colunas['DEFINIÇAO']].astype(str).str.upper().str.strip()

    if colunas['ESPESSURA']:
        df["ESP_N"] = df[colunas['ESPESSURA']].apply(converter_para_float)

    if colunas['LARGURA']:
        df["LARGURA_N"] = df[colunas['LARGURA']].apply(converter_para_float)

    if colunas['DESENVOLVIMENTO']:
        df["DESENV_N"] = df[colunas['DESENVOLVIMENTO']].apply(converter_para_float)

    if colunas['COMPRIMENTO']:
        df["COMPR_N"] = df[colunas['COMPRIMENTO']].apply(converter_para_float)
        log(f"📊 Coluna COMPRIMENTO carregada")

    if colunas['Soma de Qtd']:
        df["QTD_N"] = pd.to_numeric(df[colunas['Soma de Qtd']], errors="coerce")
    log(f"\n📈 Total de linhas carregadas: {len(df)}")
    return df
def carregar_planilha_csv(caminho):
    """
    Carrega a planilha de roteirização diretamente do CSV exportado do sistema
    (ex: 2012-2-01_L2.csv), sem passar pela tabela dinâmica do Excel.
    Formato esperado: separador ';', encoding cp1252, podendo ter uma linha de
    comentários (com '#') na primeira linha antes do cabeçalho real.
    LEITURA TOLERANTE A ERROS DE ENCODING:
    Alguns CSVs exportados vêm com um ou outro byte que não é válido em cp1252
    (ex: 0x8d, 0x81, 0x8f, 0x90, 0x9d - "buracos" da tabela cp1252, comuns quando
    o arquivo foi gerado/editado por outro sistema ou tem caracteres de outro
    encoding misturados). Em vez de travar com UnicodeDecodeError, o carregamento
    abaixo tenta, em ordem:
        1) cp1252 estrito (mais correto, se o arquivo realmente for cp1252 puro)
        2) cp1252 com encoding_errors="replace" (substitui byte inválido por
           caractere de substituição, mas mantém o restante do arquivo intacto)
        3) latin-1 (aceita qualquer byte de 0-255, nunca quebra, mas pode
           interpretar acentos de forma diferente do cp1252 em casos raros)
    Mapeamento de colunas (definido em conjunto com o usuário):
        OF               -> extraído da coluna NUM_DIS (2º token separado por "_")
                             Ex: "F2024_2012-2-01_16_R0" -> OF = "2012-2-01"
        POSIÇÃO          -> POS_PEZ
        IDENTIFICADOR    -> IDENTIFICADOR
        DEFINIÇÃO        -> NOM_PRO
        COMPRIMENTO      -> LUN_PRO
        LARGURA          -> LAR_PRO (se LAR_PRO == 0, usa a coluna DESENVOLVIMENTO)
        ESPESSURA        -> ESPESSURA
        Soma de Qtd      -> Qtd
    Linhas sem POS_PEZ são conjuntos/marcas montadas (ex: vigas inteiras) que não
    correspondem a uma peça de corte individual (não têm DXF) e são descartadas.
    """
    if os.path.isdir(caminho):
        for arq in os.listdir(caminho):
            if arq.lower().endswith(".csv"):
                caminho = os.path.join(caminho, arq)
                break
    log(f"CSV localizado: {caminho}")
    # Verificar se a primeira linha é uma linha de comentários (contém '#')
    # Usa errors="replace" aqui também, só para decidir se pula a 1ª linha -
    # não precisa ser perfeito, é só uma checagem de conteúdo.
    with open(caminho, "r", encoding="cp1252", errors="replace") as f:
        primeira_linha = f.readline()
    pular_linhas = [0] if "#" in primeira_linha else None
    # Tenta ler o CSV de verdade, em cascata de encodings/estratégias, até
    # conseguir - NUNCA deve travar o processamento inteiro por causa de um
    # único byte/caractere estranho no meio do arquivo.
    df = None
    ultimo_erro = None
    tentativas = [
        {"encoding": "cp1252", "encoding_errors": "strict"},
        {"encoding": "cp1252", "encoding_errors": "replace"},
        {"encoding": "latin-1", "encoding_errors": "strict"},
    ]
    for tentativa in tentativas:
        try:
            df = pd.read_csv(
                caminho,
                sep=";",
                skiprows=pular_linhas,
                encoding=tentativa["encoding"],
                encoding_errors=tentativa["encoding_errors"],
            )
            if tentativa["encoding_errors"] == "replace" or tentativa["encoding"] != "cp1252":
                log(f"⚠️  CSV lido com fallback de encoding ({tentativa['encoding']}, "
                    f"encoding_errors='{tentativa['encoding_errors']}') - havia byte(s) "
                    f"inválido(s) para cp1252 estrito no arquivo; caracteres afetados "
                    f"podem ter sido substituídos, mas o restante das colunas "
                    f"(OF/POSIÇÃO/IDENTIFICADOR/dimensões) não é impactado.")
            else:
                log("✅ CSV lido normalmente em cp1252 (sem problemas de encoding).")
            break
        except UnicodeDecodeError as e:
            ultimo_erro = e
            log(f"⚠️  Falha ao ler CSV com encoding={tentativa['encoding']} "
                f"(errors={tentativa['encoding_errors']}): {e}. Tentando próxima estratégia...")
            continue
    if df is None:
        # Não deveria chegar aqui (latin-1 aceita qualquer byte), mas por
        # segurança, se mesmo assim falhar, propaga o erro original.
        raise ultimo_erro
    return _normalizar_planilha_csv(df)


def _normalizar_planilha_csv(df):
    """Normaliza a planilha no formato do CSV exportado do sistema (NUM_DIS, POS_PEZ, NOM_PRO...)."""
    colunas_necessarias = ["NUM_DIS", "POS_PEZ", "IDENTIFICADOR", "NOM_PRO",
                            "LUN_PRO", "LAR_PRO", "ESPESSURA", "DESENVOLVIMENTO", "Qtd", "DES_PEZ", "MAR_PEZ"]
    log("\n--- MAPEAMENTO DE COLUNAS (CSV) ---")
    for col in colunas_necessarias:
        if col in df.columns:
            log(f"✅ {col}")
        else:
            log(f"⚠️  {col} -> NÃO ENCONTRADA")
    # A descrição da peça (DES_PEZ, ex: "ESTICADOR", "MÃO FRANCESA", "TESOURA") geralmente só
    # aparece na linha "mãe" da marca (a linha sem POS_PEZ), ficando em branco na(s) linha(s)
    # de detalhe (peça de corte real, com POS_PEZ preenchido). Antes de descartar as linhas
    # sem POS_PEZ, propagamos essa descrição para as linhas de detalhe da mesma marca (MAR_PEZ),
    # senão a informação se perde.
    if "MAR_PEZ" in df.columns and "DES_PEZ" in df.columns:
        df["DES_PEZ"] = df.groupby("MAR_PEZ")["DES_PEZ"].ffill()
    # Remover linhas sem POS_PEZ (marcas/conjuntos sem peça de corte individual - sem DXF)
    antes = len(df)
    df = df[df["POS_PEZ"].notna() & (df["POS_PEZ"].astype(str).str.strip() != "")].copy()
    log(f"🧹 Linhas removidas (sem POS_PEZ, sem DXF correspondente): {antes - len(df)} de {antes}")
    # Função para converter string com vírgula para float
    def converter_para_float(valor):
        if pd.isna(valor):
            return None
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            valor_limpo = valor.strip().replace(',', '.')
            try:
                return float(valor_limpo)
            except:
                return None
        return None
    def extrair_of_num_dis(num_dis):
        """
        Extrai o OF a partir da coluna NUM_DIS.
        Formato mais comum: F2024_2012-2-01_16_R0 -> OF = 2012-2-01
        Porém peças "genéricas" (CH, PDG, PPG, MF, E, SD, SEZ etc.) costumam vir
        SEM o prefixo tipo "F2024_", ex: 2118-2-01_MF-2_R0 -> aqui o OF ainda é
        "2118-2-01", mas está na 1ª posição, não na 2ª. Por isso a extração busca
        o PADRÃO do OF (números-números-números, ex: 2118-2-01) em qualquer lugar
        da string, em vez de depender de uma posição fixa após split("_").
        """
        try:
            texto = str(num_dis)
            match = re.search(r'\d+-\d+-\d+', texto)
            if match:
                return match.group(0).strip()
            # Fallback: formato antigo (2º token separado por "_")
            partes = texto.split("_")
            if len(partes) >= 2:
                return partes[1].strip()
        except:
            pass
        return None
    # ===== Criar colunas normalizadas (mesmos nomes usados no resto do código) =====
    # OF: extraído do NUM_DIS
    df["OF_N"] = df["NUM_DIS"].apply(extrair_of_num_dis).astype(str).str.upper().str.strip()
    # POSIÇÃO
    df["POS_N"] = df["POS_PEZ"].astype(str).str.upper().str.strip()
    # IDENTIFICADOR
    df["ID_N"] = df["IDENTIFICADOR"].astype(str).str.upper().str.strip()
    # DEFINIÇÃO (NOM_PRO)
    df["DEF_N"] = df["NOM_PRO"].astype(str).str.upper().str.strip()
    # ESPESSURA
    df["ESP_N"] = df["ESPESSURA"].apply(converter_para_float)
    # COMPRIMENTO (LUN_PRO)
    df["COMPR_N"] = df["LUN_PRO"].apply(converter_para_float)
    # LARGURA (LAR_PRO, com fallback para DESENVOLVIMENTO quando LAR_PRO == 0).
    # Guarda também o valor "alternativo" (o que NÃO foi usado) em LARGURA_ALT_N,
    # para servir de segunda tentativa na comparação de dimensões com o DXF -
    # às vezes o valor certo está em LAR_PRO, às vezes em DESENVOLVIMENTO, e não
    # dá para saber de antemão qual é o certo para cada peça.
    lar_pro = df["LAR_PRO"].apply(converter_para_float)
    desenvolvimento_aux = df["DESENVOLVIMENTO"].apply(converter_para_float)
    largura_final = []
    largura_alt = []
    for l, d in zip(lar_pro, desenvolvimento_aux):
        if l is None or l == 0:
            largura_final.append(d)
            largura_alt.append(l)
        else:
            largura_final.append(l)
            largura_alt.append(d)
    df["LARGURA_N"] = largura_final
    df["LARGURA_ALT_N"] = largura_alt
    # DESENV_N: segunda dimensão usada na comparação de medidas com o DXF.
    # Agora que LARGURA já absorve a lógica antiga de "largura x desenvolvimento",
    # a segunda dimensão de comparação passa a ser diretamente o COMPRIMENTO.
    df["DESENV_N"] = df["COMPR_N"]
    # DESCRIÇÃO DA PEÇA (DES_PEZ) - usada para identificar peças especiais como
    # ESTICADOR, que devem seguir regra própria independente da posição/perfil
    if "DES_PEZ" in df.columns:
        df["DESC_N"] = df["DES_PEZ"].astype(str).str.upper().str.strip()
    else:
        df["DESC_N"] = ""
    # MATERIAL (MAT_PRO) - usado para identificar material galvanizado, que não
    # pode ir para o banco de corte (Fluxo 3/plasma)
    if "MAT_PRO" in df.columns:
        df["MATERIAL_N"] = df["MAT_PRO"].astype(str).str.upper().str.strip()
    else:
        df["MATERIAL_N"] = ""
    # GRUPO LIC - usado como sinal adicional para identificar peças JOIST,
    # já que o IDENTIFICADOR sozinho (J/BJ/AJ1/NM1) pode não bastar
    if "GRUPO LIC" in df.columns:
        df["GRUPO_LIC_N"] = df["GRUPO LIC"].astype(str).str.upper().str.strip()
    else:
        df["GRUPO_LIC_N"] = ""
    # QUANTIDADE (Soma de Qtd)
    df["QTD_N"] = df["Qtd"].apply(converter_para_float)
    log(f"\n📈 Total de linhas carregadas: {len(df)}")
    return df
def _planilha_de_tabela(raw):
    """DataFrame cru (sem cabeçalho) de HTML/XML/texto -> (df com cabeçalho, 'csv' ou 'pivot') ou None."""
    for i in range(min(len(raw), 40)):
        cel = [("" if _foc_vazio(v) else str(v).strip()) for v in raw.iloc[i].tolist()]
        up = [re.sub(r"[ÇC]", "C", re.sub(r"[ÃA]", "A", c.upper())) for c in cel]
        layout = None
        if "NUM_DIS" in up and "POS_PEZ" in up:
            layout = "csv"
        elif "OF" in up and ("POSICAO" in up or "POSICAO " in up):
            layout = "pivot"
        if layout:
            df = raw.iloc[i + 1:].copy()
            df.columns = cel
            df = df.loc[:, [c != "" for c in df.columns]]
            df = df.replace(r"^\s*$", np.nan, regex=True).reset_index(drop=True)
            return df, layout
    return None


def _id_para_regras(cod_item, nome_perfil):
    """IDENTIFICADOR que as regras do roteirizador esperam, a partir do COD ITEM do relatório do Focco (WF):
    tira o sufixo _INT/_PREP; chapa 'CH' vira 'CH.'; barra, perfil W, chapa xadrez e terça Z usam o nome do perfil
    (as regras ignoram BR_RED..., W_... e Z...)."""
    base = re.sub(r"_(INT|PREP)$", "", str(cod_item or "").strip().upper())
    nome = str(nome_perfil or "").strip().upper()
    if nome.startswith(("BR_RED", "W_", "CHAPA_XADREZ")) or (base.startswith("Z") and not base.startswith("ZD") and nome.startswith("Z")):
        return nome
    if base == "CH":
        return "CH."
    return base


def _planilha_do_focco(raw, achado):
    """Planilha no formato do relatório do Focco (WF.xls: PACOTE, OBRA, SUB TRECHO, POSICAO, ORDEM, MASCARA, COMP...) -> as mesmas
    colunas normalizadas que o CSV do sistema gera. Uma linha por (OF, posição): o relatório repete a posição por ordem
    (CH, CH_INT, CH_PREP) e por linha de demanda; linhas sem posição (conjuntos soldados) não têm DXF e saem."""
    linha_cab, mapa = achado[0], achado[1]

    def get(linha, chave):
        ci = mapa.get(chave)
        return linha[ci] if ci is not None and ci < len(linha) else None

    registros, vistos = [], set()
    conhecidos = (_trechos_conhecidos(raw.iloc[linha_cab + 1:, mapa["sub_trecho"]].tolist())
                  if mapa.get("sub_trecho") is not None else set())
    # Posição de PREPARAÇÃO = o que ela CONSOME: chapa cortada ("CHAPA CORTADA CIVIL 300 3,00MM") e nenhuma bobina. Esse perfil (U/C/L)
    # é feito na Preparação (cortado + dobrado), NÃO na perfiladeira. A peça da perfiladeira consome BOBINA ("BOBINA CIVIL 300 2,00 X 100MM"),
    # mesmo quando o COD ITEM termina em _PREP (L-100_PREP do planejador PERFILADEIRA). Conferido nos relatórios do Focco: nenhuma peça
    # roteirizada para a perfiladeira consome só chapa cortada.
    consumo_pos = {}
    for k in range(linha_cab + 1, len(raw)):
        linha = raw.iloc[k].tolist()
        pos_k = _foc_texto(get(linha, "posicao"))
        if not pos_k:
            continue
        obra_k, sub_k = _foc_texto(get(linha, "obra")), _sub_trecho_texto(get(linha, "sub_trecho"), pos_k, conhecidos)
        of_k = (f"{obra_k}-{sub_k.replace('_', '-')}" if obra_k else sub_k.replace("_", "-")).upper()
        dem_k = _foc_texto(get(linha, "desc_demanda")).upper()
        tem_bobina, tem_chapa = consumo_pos.get((of_k, pos_k.upper()), (False, False))
        consumo_pos[(of_k, pos_k.upper())] = (tem_bobina or dem_k.startswith("BOBINA"), tem_chapa or dem_k.startswith("CHAPA"))
    chaves_prep = {ch for ch, (bobina, chapa) in consumo_pos.items() if chapa and not bobina}
    for k in range(linha_cab + 1, len(raw)):
        linha = raw.iloc[k].tolist()
        pos = _foc_texto(get(linha, "posicao"))
        if not pos:
            continue
        obra, sub = _foc_texto(get(linha, "obra")), _sub_trecho_texto(get(linha, "sub_trecho"), pos, conhecidos)
        of = (f"{obra}-{sub.replace('_', '-')}" if obra else sub.replace("_", "-")).upper()
        chave = (of, pos.upper())
        if chave in vistos:
            continue
        vistos.add(chave)
        mascara = _foc_texto(get(linha, "mascara"))
        mk = parse_mascara_focco(mascara)
        nome = _foc_texto(get(linha, "nome_perfil"))
        esp = _foc_float(get(linha, "espessura")) or mk.get("esp") or _esp_do_nome(nome)
        comp = _foc_float(get(linha, "comp")) or mk.get("comp")
        larg_col = _foc_float(get(linha, "larg"))
        larg = mk.get("larg") or larg_col                       # largura = desenvolvimento da máscara (como a LAR_PRO do CSV)
        alt = larg_col if (larg_col and mk.get("larg") and abs(larg_col - mk["larg"]) > 1e-9) else None
        registros.append({
            "OF_N": of, "POS_N": pos.upper(), "ID_N": _id_para_regras(get(linha, "cod_item"), nome),
            "DEF_N": nome.upper(), "ESP_N": esp or None, "COMPR_N": comp, "LARGURA_N": larg, "LARGURA_ALT_N": alt,
            "DESENV_N": comp, "DESC_N": "", "MATERIAL_N": str(mk.get("material") or "").upper(),
            "GRUPO_LIC_N": _foc_texto(get(linha, "grupo_lic")).upper(), "QTD_N": _foc_float(get(linha, "qtde")),
            "PREP_N": chave in chaves_prep,
        })
    if not registros:
        raise ValueError("O relatório não tem nenhuma linha com POSICAO preenchida.")
    df = pd.DataFrame(registros)
    log(f"📋 Planilha no formato do Focco (WF): {len(raw) - linha_cab - 1} linhas -> {len(df)} posições (OF + posição) para casar com os DXF")
    return df


def _tentar_planilha_focco(caminho, fmt):
    """Devolve a planilha normalizada se o arquivo for um relatório no formato do Focco (WF.xls); senão None."""
    if fmt not in ("html", "xml2003", "texto", "xlsx", "xls"):
        return None
    try:
        if fmt == "texto":
            with open(caminho, "rb") as f:
                if b"NUM_DIS" in f.read(8192):                # CSV do sistema: tem leitor próprio
                    return None
        tabelas = _abrir_tabelas_focco(caminho)
    except Exception:
        return None
    for _nome, raw in tabelas.items():
        try:
            achado = _achar_cabecalho_focco(raw)
        except Exception:
            achado = None
        if achado and all(achado[1].get(c) is not None for c in ("obra", "sub_trecho", "posicao", "mascara")):
            return _planilha_do_focco(raw, achado)
    return None


def carregar_planilha(caminho):
    """
    Ponto de entrada único para carregar a planilha de roteirização.
    Reconhece o formato pelo CONTEÚDO do arquivo (e não pela extensão): CSV do sistema (novo formato), Excel de tabela
    dinâmica (.xlsx / .xls de verdade) ou arquivo que só tem a extensão .xls mas é texto, HTML ou XML (como a 'WF.xls').
    """
    caminho_real = caminho
    if os.path.isdir(caminho):
        arquivos = os.listdir(caminho)
        for ext in (".csv", ".xlsx", ".xls"):
            achado = next((a for a in arquivos if a.lower().endswith(ext) and not a.startswith("~$")), None)
            if achado:
                caminho_real = os.path.join(caminho, achado)
                break
    try:
        fmt = _sniff_formato(caminho_real)
    except OSError as ex:
        raise ValueError(f"Não consegui abrir a planilha: {ex}")
    df_focco = _tentar_planilha_focco(caminho_real, fmt)       # relatório no formato do Focco (WF.xls)
    if df_focco is not None:
        return df_focco
    if fmt == "xlsx":
        return carregar_planilha_xlsx(caminho_real, engine="openpyxl")
    if fmt == "xls":
        try:
            return carregar_planilha_xlsx(caminho_real, engine="xlrd")
        except ImportError:
            raise ValueError(f"'{os.path.basename(caminho_real)}' é um Excel antigo (.xls) e este computador não tem o leitor desse "
                             "formato. Abra no Excel e salve como .xlsx (ou .csv) e tente de novo.")
    if fmt == "protegido":
        raise ValueError(f"'{os.path.basename(caminho_real)}' está protegido por senha. Remova a senha no Excel e salve de novo.")
    if fmt == "desconhecido":
        raise ValueError(f"Não consegui entender o formato de '{os.path.basename(caminho_real)}'. Salve como .xlsx ou .csv e tente de novo.")
    if fmt == "texto":                                    # CSV do sistema (mesmo que a extensão seja .xls)
        with open(caminho_real, "rb") as f:
            inicio = f.read(8192).decode("cp1252", errors="replace")
        if "NUM_DIS" in inicio and "POS_PEZ" in inicio and ";" in inicio:
            return carregar_planilha_csv(caminho_real)
    # HTML / XML do Excel 2003 / texto com outro separador: lê as tabelas e acha o cabeçalho
    achado = None
    for _nome, raw in _abrir_tabelas_focco(caminho_real).items():
        achado = _planilha_de_tabela(raw)
        if achado:
            break
    if not achado:
        raise ValueError(f"Não achei as colunas da planilha de roteirização em '{os.path.basename(caminho_real)}' "
                         "(esperava NUM_DIS/POS_PEZ do CSV do sistema, ou OF/POSIÇÃO da tabela dinâmica).")
    df, layout = achado
    log(f"Planilha lida pelo conteúdo ({fmt}), formato '{layout}': {caminho_real}")
    return _normalizar_planilha_csv(df) if layout == "csv" else _normalizar_planilha_pivot(df)


def pasta_valida(nome):
    nome = nome.upper()
    if "FLUXO" in nome or "EDITAR" in nome or "PERFILAR" in nome or "PERFILADEIRA" in nome:
        return False
    return True
def buscar_posicao(planilha, of, pos_arquivo):
    """
    Busca na planilha uma posição que corresponda ao arquivo.
    Estratégia:
    1. Match exato primeiro
    2. Se não achar, tenta remover apenas _U do final
    3. Se ainda não achar, tenta remover um prefixo de trecho colado no início
       (ex: arquivo "2-01_MF1_U" -> planilha tem só "MF1"), pois a planilha CSV
       nova usa a POSIÇÃO sem o prefixo de trecho que os nomes de arquivo trazem
    4. NÃO faz startswith para evitar falsos positivos
    """
    # Tentar primeiro com a posição original
    filtro = planilha[
        (planilha["OF_N"] == of) &
        (planilha["POS_N"] == pos_arquivo)
    ]
    if not filtro.empty:
        return filtro
    # Se não encontrar, remover apenas o sufixo _U
    pos_sem_sufixo = extrair_posicao_base(pos_arquivo)

    if pos_sem_sufixo != pos_arquivo:
        filtro_sem_sufixo = planilha[
            (planilha["OF_N"] == of) &
            (planilha["POS_N"] == pos_sem_sufixo)
        ]

        if not filtro_sem_sufixo.empty:
            return filtro_sem_sufixo
    # Se ainda não encontrar, remover um possível prefixo de trecho colado no
    # início da posição (tudo até o primeiro "_"), e tentar de novo com e sem o
    # sufixo _U. Ex: "2-01_MF1_U" -> "MF1_U" -> "MF1"
    if "_" in pos_arquivo:
        pos_sem_trecho = pos_arquivo.split("_", 1)[1]
        pos_sem_trecho_e_sufixo = extrair_posicao_base(pos_sem_trecho)
        for candidato in {pos_sem_trecho, pos_sem_trecho_e_sufixo}:
            if not candidato:
                continue
            filtro_trecho = planilha[
                (planilha["OF_N"] == of) &
                (planilha["POS_N"] == candidato)
            ]
            if not filtro_trecho.empty:
                return filtro_trecho
    # Caminho inverso (planilha no formato do Focco/WF traz o prefixo do trecho, ex.: "4-01_CH-5", e o arquivo vem só
    # "CH-5"): compara com a posição da planilha SEM o prefixo. Só vale se der uma posição única dentro da mesma OF.
    sem_prefixo = planilha["POS_N"].astype(str).str.replace(r"^\d+-\d+_", "", regex=True)
    for candidato in {pos_arquivo, pos_sem_sufixo}:
        if not candidato:
            continue
        filtro_inverso = planilha[(planilha["OF_N"] == of) & (sem_prefixo == candidato)]
        if len(filtro_inverso) == 1:
            return filtro_inverso
    return pd.DataFrame()
def extrair_dimensoes_U(definicao):
    try:
        match = re.search(r"U(\d+)X(\d+)X(\d+\.?\d*)", definicao)
        if match:
            alma = int(match.group(1))
            aba = int(match.group(2))
            esp = float(match.group(3))
            return alma, aba, esp
    except:
        pass
    return None, None, None
def eh_perfil_j_dobrado(definicao):
    """
    Identifica se a DEFINIÇÃO representa um perfil "J" DOBRADO EM CHAPA (ex:
    "J190X196X3.75" - alma x aba x espessura, no mesmo padrão de catálogo de
    extrair_dimensoes_U/C) - o desenvolvimento (chapa plana antes de dobrar)
    dessa peça tem o formato da letra "J" por causa das dobras, mas isso NÃO
    tem NENHUMA relação com estrutura JOIST (treliça).
    Usada para EXCLUIR essas peças da detecção de Joist em regra_perfil_J,
    que olha apenas para o prefixo "J"/"BJ"/"AJ1"/"NM1" no IDENTIFICADOR,
    POSIÇÃO ou GRUPO LIC - sem essa exclusão, um perfil J de chapa cairia por
    engano na rota de Joist só por coincidência de nomenclatura.
    """
    if not definicao:
        return False
    return bool(re.match(r'^J\d+X\d+X\d+\.?\d*', str(definicao).upper().strip()))
def extrair_dimensoes_C(definicao):
    try:
        match = re.search(r"C(\d+)X(\d+)X(\d+)X(\d+\.?\d*)", definicao)
        if match:
            alma = int(match.group(1))
            aba1 = int(match.group(2))
            aba2 = int(match.group(3))
            esp = float(match.group(4))
            return alma, aba1, aba2, esp
    except:
        pass
    return None, None, None, None
def extrair_abas_L(definicao):
    try:
        match = re.search(r"L(\d+)X(\d+)X", definicao)
        if match:
            return int(match.group(1)), int(match.group(2))
    except:
        pass
    return None, None
def extrair_abas_generico(definicao):
    """
    Extrai as duas abas (flanges) de uma DEFINIÇÃO de perfil, tentando os
    padrões de L, U e C nessa ordem (reaproveitando os extratores já
    existentes), independente de qual seja o IDENTIFICADOR da peça:
    - L: "LxxxXyyyX..."      -> (aba1, aba2) = (xxx, yyy)
    - U: "UxxxXyyyXesp"      -> aba única (yyy); devolvida como (aba, aba),
      pois o perfil U tem as duas abas iguais por definição de catálogo
    - C: "CxxxXyyyXzzzXesp"  -> (aba1, aba2) = (yyy, zzz)
    Retorna (aba1, aba2) ou (None, None) se a DEFINIÇÃO não casar com
    nenhum desses padrões.
    """
    aba1, aba2 = extrair_abas_L(definicao)
    if aba1 is not None:
        return aba1, aba2
    _, aba_u, _ = extrair_dimensoes_U(definicao)
    if aba_u is not None:
        return aba_u, aba_u
    _, aba1_c, aba2_c, _ = extrair_dimensoes_C(definicao)
    if aba1_c is not None:
        return aba1_c, aba2_c
    return None, None
# ===== FUNÇÕES AUXILIARES DE PREFIXO E FUROS (integradas do pro_rp_v13) =====
def verificar_prefixo(nome_arquivo, prefixos):
    """
    Verifica se o arquivo começa com algum dos prefixos, ignorando:
    - Prefixos de obra/trecho (ex: 2-01_, 101-01_)
    - Números após hífen (ex: ED-1 → ED, PPG-2 → PPG)
    """
    nome_sem_ext = os.path.splitext(nome_arquivo)[0]
    # Remove prefixos de obra/trecho (2-01_, 101-01_, etc.)
    nome_sem_obra = re.sub(r'^\d+-\d+_[-]?', '', nome_sem_ext)
    # Remove números após prefixo (ED-1 → ED, PPG-2 → PPG)
    nome_sem_numeros = re.sub(r'^([A-Za-z]+)-\d+', r'\1', nome_sem_obra)
    return any(nome_sem_numeros.upper().startswith(p.upper()) for p in prefixos)
def contar_furos_diametro(caminho, diametro_alvo=14.0, tolerancia=0.01):
    """Conta quantos furos circulares de um diâmetro específico existem no DXF."""
    try:
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()
        contador = 0
        for e in msp:
            if e.dxftype() == "CIRCLE":
                if abs(e.dxf.radius * 2 - diametro_alvo) < tolerancia:
                    contador += 1
        return contador
    except Exception as ex:
        log(f"Erro ao contar furos Ø{diametro_alvo} do DXF: {ex}")
        return 0
# ===== REGRAS =====
def regra_terca_z(nome_arquivo, pos_planilha, def_planilha):
    return verificar_terca_z(nome_arquivo, pos_planilha, def_planilha)
def regra_pc(largura_planilha, desenvolvimento_planilha, espessura):
    if not (1.25 <= espessura <= 3.00):
        return None

    def eh_25(valor):
        if valor is None or pd.isna(valor):
            return False
        try:
            valor_float = float(valor)
            return abs(valor_float - 25.0) < 0.01
        except:
            return False

    def eh_50(valor):
        if valor is None or pd.isna(valor):
            return False
        try:
            valor_float = float(valor)
            return abs(valor_float - 50.0) < 0.01
        except:
            return False

    if eh_25(largura_planilha) or eh_25(desenvolvimento_planilha):
        return "CSC"  # ALTERADO: ACP para CSC

    if eh_50(largura_planilha) or eh_50(desenvolvimento_planilha):
        return "Fluxo 4"

    return None
def regra_perfilar_U(esp, identificador, definicao):
    if not identificador.startswith("U"):
        return False

    if not (1.25 <= esp <= 3.00):
        return False

    alma, aba, esp_extraida = extrair_dimensoes_U(definicao)

    if alma is None:
        return None

    if 100 <= alma <= 400 and 50 <= aba <= 103:
        return True

    return False
def regra_perfilar_C(esp, identificador, definicao):
    if not identificador.startswith("C"):
        return False

    if not (1.25 <= esp <= 3.00):
        return False

    alma, aba1, aba2, esp_extraida = extrair_dimensoes_C(definicao)

    if alma is None:
        return None

    # Lábio (aba2) do C: ANTES só aceitava exatamente 25mm, então um C150X61X20X2.00 (lábio 20, comp. 2287, planejador
    # PERFILADEIRA) nunca entrava no catálogo e caía no fallback por tamanho -> Fluxo 2, SEMPRE. Agora vale a mesma regra
    # que o Relatório de Ordens usa pra rota PERFILADEIRA U/C (classificar_rota_html: alma > 100, aba1 > 50, aba2 < 30).
    if (100 <= alma <= 400 and
        25 <= aba1 <= 90 and
        0 < aba2 < 30):
        return True

    return False
# ===== DESTINAÇÃO DE PEÇAS L (L1 / L2) - mesma regra do programador "PERFILADOS - PROGRAMADOR DE L" =====
# L1 (máquina grande): perfis L52X52X1.55, L32X32X1.25 e L32X32X1.55 com comprimento ACIMA de 595mm.
# L2: todas as demais peças da Perfiladeira L.
_L1_PERFIS = ("L52X52X1.55", "L32X32X1.25", "L32X32X1.55")
_L1_COMP_MIN = 595.0


def destino_perfiladeira_L(perfil, comp):
    """'L1' ou 'L2' para uma peça que vai para a Perfiladeira L (perfil na lista da L1 e comprimento > 595mm -> L1)."""
    p = str(perfil or "").strip().upper().replace(",", ".")
    c = _foc_float(comp)                         # aceita número ou texto ("596" / "1.188,5")
    return "L1" if (p in _L1_PERFIS and c is not None and c > _L1_COMP_MIN) else "L2"


def regra_perfilar_L(esp, identificador, definicao):
    """
    Regra de catálogo da Perfiladeira L (abas iguais, espessura até 3,00mm),
    ajustada para a limitação física da máquina:
    - Abas iguais entre 52mm e 100mm (inclusive) -> mantém Perfiladeira L.
    - EXCEÇÃO: os perfis da L1 do programador das perfiladeiras (L32X32X1.25 e L32X32X1.55) têm aba de
      32mm e também vão para a Perfiladeira L. (Não baixei o mínimo para todas as peças L: pedaços de
      aba pequena que o Focco manda para PREPARAÇÃO, como L_PREP, não podem virar perfiladeira.)
    - Demais abas iguais MENORES que 52mm ou MAIORES que 100mm -> a máquina não
      atende essa faixa; a peça NÃO vai para Perfiladeira L - retorna False
      aqui, o que faz decidir_fluxo_peca cair no fallback por tamanho
      (Fluxo 1 acima de 3000mm, Fluxo 2 acima de 400mm, Fluxo 4 abaixo
      disso). Irregularidade e furos já são tratados antes de chegar aqui
      na cadeia de decisão (decidir_fluxo_peca), então continuam valendo
      normalmente mesmo fora da faixa de catálogo.
    """
    if not (1.25 <= esp <= 3.00):
        return False
    if not identificador.startswith("L"):
        return False
    if identificador in ["L-100", "L-150"]:
        return True
    aba1, aba2 = extrair_abas_L(definicao)
    if aba1 is None:
        return None
    if aba1 == aba2 and 52 <= aba1 <= 100:
        return True
    perfil_norm = str(definicao or "").strip().upper().replace(",", ".")
    if aba1 == aba2 and 30 <= aba1 < 52 and any(perfil_norm.startswith(p) for p in _L1_PERFIS):
        return True
    return False
# ===== REGRA PARA IDENTIFICADOR J =====
def regra_perfil_J(esp, identificador, largura_dxf, altura_dxf, pos_planilha="", grupo_lic=""):
    """
    Regra para perfis J (JOIST) - inclui nomenclaturas "J", "BJ", "AJ1" e "NM1":
    - Essas nomenclaturas podem aparecer no IDENTIFICADOR, na POSIÇÃO/marca
      (ex: "NM1-1_U" tem identificador "U" mas a marca é NM1 - ainda é JOIST)
      ou na coluna GRUPO LIC (quando ela contém "JOIST" explicitamente).
    - O IDENTIFICADOR/POSIÇÃO/GRUPO LIC já confirma que é JOIST, então vale
      para qualquer espessura (sem restrição de faixa)
    - Fluxo 1: maior dimensão > 3000
    - Fluxo 2: maior dimensão ≤ 3000
    - Fluxo 4: maior dimensão < 400
    """
    id_upper = str(identificador).upper().strip() if identificador else ""
    pos_upper = str(pos_planilha).upper().strip() if pos_planilha else ""
    grupo_upper = str(grupo_lic).upper().strip() if grupo_lic else ""
    def bate_nomenclatura_joist(texto):
        # Remove um possível prefixo de trecho colado (ex: "4-01_AJ1-1" -> "AJ1-1")
        # antes de checar, pois a posição pode vir com o trecho da obra junto
        texto_sem_trecho = re.sub(r'^\d+-\d+_[-]?', '', texto)
        return (texto_sem_trecho.startswith("J") or texto_sem_trecho.startswith("BJ")
                or texto_sem_trecho.startswith("AJ1") or texto_sem_trecho.startswith("NM1"))
    eh_joist = (bate_nomenclatura_joist(id_upper) or bate_nomenclatura_joist(pos_upper)
                or "JOIST" in grupo_upper)
    if not eh_joist:
        return None

    # Obter a maior dimensão - sem as duas dimensões (DXF sem geometria legível,
    # por exemplo), não dá pra decidir Fluxo 1/2/4 por tamanho aqui, mas o valor
    # retornado só serve hoje pra CONFIRMAR que é Joist (a pasta final é sempre
    # "Joist [espessura]", não usa mais esse Fluxo 1/2/4) - então qualquer valor
    # não-None serve; evita o erro "'>' not supported between NoneType" que
    # travava o processamento inteiro quando a dimensão não era lida.
    if largura_dxf is None or altura_dxf is None:
        return "Fluxo 2"

    maior = max(largura_dxf, altura_dxf)

    # Determinar o fluxo baseado na maior dimensão
    if maior > 3000:
        return "Fluxo 1"
    elif maior < 400:
        return "Fluxo 4"
    else:
        return "Fluxo 2"
def decidir_fluxo(esp, largura, altura, irregular):
    # A checagem de "irregular" vem ANTES de calcular a maior dimensão - uma
    # peça irregular vai pra Fluxo 3 de qualquer forma, e algumas peças
    # irregulares/com geometria complexa podem não ter largura/altura lidas
    # (None) do DXF; calcular "maior" antes travaria o processamento com
    # "'>' not supported between instances of 'NoneType' and 'NoneType'".
    if irregular:
        return f"Fluxo 3 [{str(esp).replace('.', ',')}]"
    if largura is None or altura is None:
        return None  # sem as duas dimensões, não dá pra decidir por tamanho
    maior = max(largura, altura)
    # Tudo acima de 9,50mm vai para Fluxo 3, independente de ser CH. ou perfil
    # (cobre também espessuras entre 9,50 e 12,70 que antes ficavam sem fluxo,
    # como 10,00 / 11,00 / 11,10mm etc, além de tudo >= 12,70)
    if esp > 9.50:
        return f"Fluxo 3 [{str(esp).replace('.', ',')}]"
    if esp == 9.50:
        return f"Fluxo 3 [{str(esp).replace('.', ',')}]" if maior > 400 else f"Fluxo 4 [{str(esp).replace('.', ',')}]"
    if esp == 8.0:
        return f"Fluxo 3 [{str(esp).replace('.', ',')}]" if maior > 400 else f"Fluxo 4 [{str(esp).replace('.', ',')}]"
    if esp in [6.35, 4.75, 4.25, 3.75, 3.35]:
        if maior > 3000:
            return f"Fluxo 1 [{str(esp).replace('.', ',')}]"
        if maior > 400:
            return f"Fluxo 2 [{str(esp).replace('.', ',')}]"
        return f"Fluxo 4 [{str(esp).replace('.', ',')}]"
    return None
def comparar_dimensoes_com_tolerancia(largura_dxf, altura_dxf, largura_plan, altura_plan, tolerancia):
    """
    Compara dimensões considerando possível rotação da peça
    Retorna (status)
    """
    # Combinação 1: direta
    diff1_larg = abs(largura_dxf - largura_plan)
    diff1_alt = abs(altura_dxf - altura_plan)

    # Combinação 2: invertida (peça rotacionada)
    diff2_larg = abs(largura_dxf - altura_plan)
    diff2_alt = abs(altura_dxf - largura_plan)

    if diff1_larg <= tolerancia and diff1_alt <= tolerancia:
        return "OK"
    elif diff2_larg <= tolerancia and diff2_alt <= tolerancia:
        return "OK"
    else:
        return "DIVERGENTE"
# ===== FUNÇÃO PROCESSAR =====
def analisar_recorte_dxf(caminho):
    """
    Analisa recortes/irregularidades (ARC, SPLINE, ELLIPSE) no DXF.
    Retorna (recorte_grande, recorte_dos_dois_lados):
    - recorte_grande: True se algum recorte tiver tamanho (maior dimensão) > 150mm
    - recorte_dos_dois_lados: True se houver recorte tanto na metade esquerda
      quanto na metade direita da peça (considerando o ponto médio da largura)
    """
    try:
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()
        todos_xs = []
        centros_recorte_x = []
        maior_recorte = 0.0
        for e in msp:
            try:
                if hasattr(e.dxf, "start"):
                    todos_xs.append(e.dxf.start[0])
                if hasattr(e.dxf, "end"):
                    todos_xs.append(e.dxf.end[0])
                if hasattr(e.dxf, "center"):
                    todos_xs.append(e.dxf.center[0])
            except:
                pass
            if e.dxftype() == "ARC":
                try:
                    tamanho = e.dxf.radius * 2
                    maior_recorte = max(maior_recorte, tamanho)
                    centros_recorte_x.append(e.dxf.center[0])
                except:
                    pass
            elif e.dxftype() == "ELLIPSE":
                try:
                    major_axis = e.dxf.major_axis
                    tamanho = math.sqrt(major_axis[0] ** 2 + major_axis[1] ** 2) * 2
                    maior_recorte = max(maior_recorte, tamanho)
                    centros_recorte_x.append(e.dxf.center[0])
                except:
                    pass
            elif e.dxftype() == "SPLINE":
                try:
                    pontos = list(e.control_points)
                    if pontos:
                        xs_spline = [p[0] for p in pontos]
                        ys_spline = [p[1] for p in pontos]
                        tamanho = max(max(xs_spline) - min(xs_spline), max(ys_spline) - min(ys_spline))
                        maior_recorte = max(maior_recorte, tamanho)
                        centros_recorte_x.append(sum(xs_spline) / len(xs_spline))
                except:
                    pass
        if not todos_xs or not centros_recorte_x:
            return False, False
        x_min, x_max = min(todos_xs), max(todos_xs)
        x_meio = (x_min + x_max) / 2
        tem_recorte_esquerda = any(x < x_meio for x in centros_recorte_x)
        tem_recorte_direita = any(x >= x_meio for x in centros_recorte_x)
        recorte_grande = maior_recorte > 150
        recorte_dos_dois_lados = tem_recorte_esquerda and tem_recorte_direita
        return recorte_grande, recorte_dos_dois_lados
    except Exception as ex:
        log(f"Erro ao analisar recorte do DXF: {ex}")
        return False, False
def possui_angulo_dxf(caminho, tolerancia_graus=1.0):
    """
    Verifica se o DXF tem linhas em ângulo/grau (diagonais) - segmentos que não
    são puramente horizontais nem verticais, indicando corte em ângulo.
    """
    try:
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()
        for e in msp:
            if e.dxftype() == "LINE":
                try:
                    dx = e.dxf.end[0] - e.dxf.start[0]
                    dy = e.dxf.end[1] - e.dxf.start[1]
                except Exception:
                    continue
                if abs(dx) < 0.01 or abs(dy) < 0.01:
                    continue  # horizontal ou vertical, não conta como ângulo
                angulo = math.degrees(math.atan2(abs(dy), abs(dx)))
                if tolerancia_graus < angulo < (90 - tolerancia_graus):
                    return True
        return False
    except Exception as ex:
        log(f"Erro ao analisar ângulo do DXF: {ex}")
        return False
def possui_angulo_dxf_significativo(caminho, min_cateto=20.0, tolerancia_graus=1.0):
    """
    Igual a possui_angulo_dxf(), mas só considera "corte em ângulo real" uma
    linha diagonal cujos DOIS catetos (dx e dy) sejam de pelo menos
    min_cateto mm cada.
    Isso ignora de propósito:
    - Chanfros pequenos de canto (ex: ~14mm de comprimento, catetos ~10mm) -
      comuns em chapas/perfis para aliviar uma quina, mas que não
      caracterizam um corte diagonal "de verdade" na peça.
    - Bordas quase verticais/horizontais com um pequeno desvio (ex: ~2mm em
      65mm de altura) - isso é imprecisão de desenho/fabricação, não uma
      aresta desenhada propositalmente em ângulo.
    Usada apenas para a promoção Fluxo 4 -> Fluxo 3 (Item 4) - o Item 3
    (Fluxo 1/2 -> Fluxo 3) continua usando possui_angulo_dxf() sem esse
    filtro de tamanho mínimo.
    """
    try:
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()
        for e in msp:
            if e.dxftype() == "LINE":
                try:
                    dx = e.dxf.end[0] - e.dxf.start[0]
                    dy = e.dxf.end[1] - e.dxf.start[1]
                except Exception:
                    continue
                if abs(dx) < min_cateto or abs(dy) < min_cateto:
                    continue  # chanfro pequeno de canto ou quase reto - ignora
                angulo = math.degrees(math.atan2(abs(dy), abs(dx)))
                if tolerancia_graus < angulo < (90 - tolerancia_graus):
                    return True
        return False
    except Exception as ex:
        log(f"Erro ao analisar ângulo significativo do DXF: {ex}")
        return False
def eh_escada_marinheiro(of):
    """
    Identifica se a peça pertence à escada de marinheiro, com base no
    "subtrecho" da OF - o terceiro número, separado por hífen (ex:
    "2089-2-50" -> subtrecho "50"). Mesmo campo/convenção usada para
    identificar OF_N no restante do script (extrair_of_num_dis).
    """
    if not of:
        return False
    partes = str(of).strip().split("-")
    if len(partes) < 3:
        return False
    return partes[-1].strip() == "50"
def regra_escada_marinheiro(identificador, largura_dxf, altura_dxf, quantidade_furos):
    """
    Regra de fluxo específica para peças da escada de marinheiro (subtrecho 50
    da OF). A máquina de Fluxo 1/2/4 tem limitação de largura e de quantidade
    de furos para essas peças, então:
    - A regra vale para peças com largura (menor dimensão) de 38mm ou 50mm
      (tolerância ±3mm) - as larguras típicas da escada de marinheiro. NÃO
      depende do IDENTIFICADOR (L, GC ou outro) ser exatamente reconhecido,
      pois a peça pode não ter esse identificador específico na planilha.
    - Maior dimensão (comprimento) > 400mm -> SEMPRE Fluxo 3, não importa a
      largura/aba (nunca vai para Fluxo 1 ou Fluxo 2).
    - Maior dimensão <= 400mm -> Fluxo 4, EXCETO se tiver mais de 2 furos,
      caso em que também vai para Fluxo 3 (o Fluxo 4 não dá conta de mais de
      2 furos nessas peças).
    Retorna "Fluxo 3", "Fluxo 4" ou None (quando a largura não é 38/50mm ou
    faltam dimensões para decidir).
    """
    if largura_dxf is None or altura_dxf is None:
        return None
    menor = min(largura_dxf, altura_dxf)
    eh_largura_escada = abs(menor - 38) <= 3 or abs(menor - 50) <= 3
    if not eh_largura_escada:
        return None
    maior = max(largura_dxf, altura_dxf)
    if maior > 400:
        return "Fluxo 3"
    if quantidade_furos is not None and quantidade_furos > 2:
        return "Fluxo 3"
    return "Fluxo 4"
_RE_CIV_CSV = re.compile(r"^(CIV|CSV)\d")


def eh_civ_csv(*nomes):
    """True se a posição (ou o nome do arquivo sem o prefixo da obra) é uma peça CIV<n> / CSV<n> - Perfiladeira U e C, mesmo curta."""
    return any(_RE_CIV_CSV.match(str(n or "").upper().strip()) for n in nomes)


def decidir_fluxo_peca(esp, identificador, definicao, pos_planilha, arq, caminho,
                        largura_dxf, altura_dxf, irregular, quantidade_furos, material="",
                        desenvolvimento_planilha=None, of=None, ajustes_manuais=None, grupo_lic="", preparacao=False):
    """
    preparacao=True (a posição consome CHAPA CORTADA e nenhuma bobina, no Focco): perfil L/U/C feito na PREPARAÇÃO a partir da chapa -
    nunca vai para Perfiladeira L nem U e C, mesmo que a definição caiba no catálogo da máquina: segue as regras de tamanho (Fluxo 1/2/4).
    Decide o fluxo de uma peça individual, percorrendo toda a cadeia de prioridade:
    ajuste manual (memória SQLite - prioridade ABSOLUTA, sobrepõe tudo), escada
    de marinheiro (subtrecho 50, L/GC), ACE, peças específicas, regra de furos
    (Fluxo 3), espessura (Fluxo 1/2/3/4), IDENTIFICADOR (perfil J, Perfiladeira
    U/C/L - tem prioridade sobre CSC/prefixo, pois a coluna IDENTIFICADOR da
    planilha é a fonte de verdade sobre o que é L e o que é U/C), regra
    DESENVOLVIMENTO=495 + abas iguais >=400 (Perfiladeira U e C, mesmo fora da
    faixa de catálogo), regra 3,00mm+furos, espessuras ACP+"_u"+altura, prefixos
    TZ/EA/PPG/PC/MFPA/MFP/SC/SEZ, prefixos MF/ED (fallback), fallback por tamanho.
    Por fim, se o resultado for Fluxo 4, verifica recorte grande/dos dois lados
    para promover a peça para Fluxo 3.
    NÃO inclui Terça Z nem o agrupamento por conjunto (@N/lado esquerdo-direito) -
    isso é tratado por quem chama esta função, pois depende de outras peças do
    mesmo conjunto, não só da peça em si.
    É a MESMA função usada tanto na pré-varredura de conjuntos quanto no
    processamento real, para garantir que as duas nunca decidam coisas diferentes
    para a mesma peça.
    Retorna a string do fluxo (ex: "Fluxo 3 [6,35]") ou None se nada bateu.
    """
    # ===== PRIORIDADE ABSOLUTA: ajuste manual salvo na memória (SQLite) =====
    # Se o usuário já revisou essa (identificador, posição) antes - em
    # QUALQUER obra - e definiu um fluxo manual, usa ele direto, sem rodar
    # NENHUMA outra regra (nem escada de marinheiro, nem GC, nem nada).
    if ajustes_manuais:
        chave_memoria = _normalizar_chave_memoria(identificador, pos_planilha)
        if chave_memoria in ajustes_manuais:
            return ajustes_manuais[chave_memoria]
    # Padroniza a espessura para o valor "oficial" mais próximo (ex: 6,40 -> 6,35),
    # evitando pastas variantes e tornando as comparações abaixo mais robustas
    esp = padronizar_valor_espessura(esp)
    nome_sem_prefixo_obra = re.sub(r'^\d+-\d+_[-]?', '', os.path.splitext(arq)[0])
    def fmt(valor_esp):
        # Formatação padrão e única da espessura no nome da pasta, para nunca
        # criar pastas duplicadas tipo "Fluxo 4 [3,00]" vs "Fluxo 4 [3,0]"
        return str(valor_esp).replace('.', ',')
    resultado = None
    # ===== REGRA ESPECIAL: GC é sempre banco de corte (Fluxo 3) =====
    # O identificador GC só pode ser cortado no banco de corte (Fluxo 3),
    # independente de trecho, largura, comprimento ou quantidade de furos -
    # tem prioridade máxima sobre toda a cadeia de decisão.
    id_upper_gc = str(identificador).upper().strip() if identificador else ""
    eh_gc = id_upper_gc.startswith("GC")
    # ===== REGRA ESPECIAL: largura 92mm + espessura 4,75mm é sempre banco de
    # corte (Fluxo 3) =====
    # Combinação específica que só pode ser feita no banco de corte,
    # independente de comprimento, furos ou trecho.
    eh_92_475 = (largura_dxf is not None and altura_dxf is not None
                 and abs(esp - 4.75) < 0.01
                 and abs(min(largura_dxf, altura_dxf) - 92) <= 3)
    if eh_gc or eh_92_475:
        resultado = f"Fluxo 3 [{fmt(esp)}]"
    # ===== REGRA ESPECIAL: ESCADA DE MARINHEIRO (subtrecho 50) - L e GC =====
    # Tem PRIORIDADE MÁXIMA sobre toda a cadeia normal de decisão (inclusive
    # sobre ACE, catálogo de Perfiladeira L, fallback por tamanho etc.) - a
    # máquina de Fluxo 1/2/4 tem limitação de largura/quantidade de furos
    # para essas peças, então L e GC da escada de marinheiro sempre seguem
    # esta regra própria, independente de espessura ou largura da aba. Nunca
    # vai para Fluxo 1 ou Fluxo 2 - só Fluxo 3 ou Fluxo 4.
    elif eh_escada_marinheiro(of) and regra_escada_marinheiro(identificador, largura_dxf, altura_dxf, quantidade_furos):
        fluxo_escada = regra_escada_marinheiro(identificador, largura_dxf, altura_dxf, quantidade_furos)
        resultado = f"{fluxo_escada} [{fmt(esp)}]"
    elif verificar_prefixo(arq, ["ACE"]):
        resultado = f"Fluxo 4 [{fmt(esp)}]"
    elif verificar_prefixo(arq, ["XH0800296", "XI0630250", "MI0630200", "PR0300180"]):
        resultado = f"Fluxo 4 [{fmt(esp)}]"
    else:
        # JOIST (identificador J/BJ/AJ1/NM1) tem prioridade sobre a regra genérica
        # por espessura - senão uma peça JOIST de 6,35mm, por exemplo, cairia na
        # tabela genérica de espessura (decidir_fluxo) antes de ser reconhecida
        # como Joist pelo identificador. EXCETO se a DEFINIÇÃO for um "Perfil J"
        # dobrado em chapa (ex: "J190X196X3.75") - aí não é Joist, é só
        # coincidência de nomenclatura (o desenvolvimento da peça tem forma de
        # "J" por causa das dobras); nesse caso ela cai no fallback normal por
        # tamanho, igual aos perfis L/U/C.
        #
        # IMPORTANTE: Joist não é um fluxo separado por tamanho (Fluxo 1/2/4) -
        # é só um RÓTULO/RENOMEAÇÃO: toda peça Joist vai para uma única pasta
        # "Joist [espessura]", independente do tamanho dela. regra_perfil_J()
        # ainda calcula Fluxo 1/2/4 internamente (só pra confirmar que É Joist),
        # mas esse valor não entra no nome da pasta.
        resultado_J = None
        if not eh_perfil_j_dobrado(definicao):
            resultado_J = regra_perfil_J(esp, identificador, largura_dxf, altura_dxf, pos_planilha, grupo_lic)
        if resultado_J is not None:
            resultado = f"Joist [{fmt(esp)}]"
        else:
            # Regra de furos/recorte (verificada ANTES de decidir_fluxo, pois precisa
            # poder SOBREPOR o resultado padrão dele, ex: Fluxo 1 por tamanho, quando a
            # peça tem furos/recorte suficiente):
            #   A) largura > 450mm + comprimento > 3000mm + mais de 2 furos
            #   B) espessura <= 6,35mm + largura > 100mm + comprimento > 3000mm + mais de 4 furos
            #   C) tem recorte + largura >= 370mm + comprimento > 3000mm + mais de 2 furos
            #   D) largura > 600mm + comprimento > 3000mm, MESMO SEM FUROS - a máquina
            #      de Fluxo 1 não atende peça larga E comprida ao mesmo tempo
            # L de PERFILADEIRA (IDENTIFICADOR L-100/L-150 ou abas iguais do catálogo, até 3,00mm) com SÓ arcos pequenos no DXF - furo
            # oblongo (rasgo) ou canto arredondado, ex.: TLT1406 = L52X52X2.00 com 2 rasgos de R5,5 - NÃO é peça irregular: o furo é feito
            # na própria perfiladeira. Sem isso o arco marcava a peça como "irregular" e ela ia para o Fluxo 3 (LASER) antes de o
            # identificador L ser olhado. Recorte grande (arco > 150mm), spline/elipse e contorno em degrau continuam irregulares.
            if (irregular and esp is not None and esp <= 3.00 + 0.005
                    and regra_perfilar_L(esp, identificador, definicao) is True
                    and irregularidade_so_arcos_pequenos(caminho)):
                irregular = False
            fluxo_por_furos = None
            if esp is not None and esp >= 3.75 and largura_dxf is not None and altura_dxf is not None:
                menor_dim = min(largura_dxf, altura_dxf)
                maior_dim = max(largura_dxf, altura_dxf)
                if maior_dim > 3000:
                    bate_regra_a = menor_dim > 450 and quantidade_furos > 2
                    bate_regra_b = (esp <= 6.35) and (menor_dim > 100) and quantidade_furos > 4
                    bate_regra_c = irregular and menor_dim >= 370 and quantidade_furos > 2
                    bate_regra_d = menor_dim > 600
                    if bate_regra_a or bate_regra_b or bate_regra_c or bate_regra_d:
                        fluxo_por_furos = f"Fluxo 3 [{fmt(esp)}]"
            # EXCEÇÃO: peça pequena/média (largura < 1000mm e comprimento < 3000mm),
            # SEM furos, cujo único recorte seja SIMPLES (pequeno, só de um lado da
            # peça - não caracteriza um degrau/aba real) NÃO é promovida
            # automaticamente para Fluxo 3 só por ser "irregular" - fica em Fluxo 2,
            # dentro da faixa normal de tamanho. Reaproveita analisar_recorte_dxf()
            # (recorte_grande = maior que 150mm; recorte_dos_dois_lados = corte na
            # metade esquerda E direita da peça) para diferenciar "recorte simples"
            # de um recorte grande/complexo de verdade.
            excecao_recorte_simples = False
            if (not fluxo_por_furos and irregular and quantidade_furos == 0
                    and largura_dxf is not None and altura_dxf is not None):
                menor_dim_exc = min(largura_dxf, altura_dxf)
                maior_dim_exc = max(largura_dxf, altura_dxf)
                if menor_dim_exc < 1000 and maior_dim_exc < 3000:
                    recorte_grande, recorte_dos_dois_lados = analisar_recorte_dxf(caminho)
                    if not recorte_grande and not recorte_dos_dois_lados:
                        excecao_recorte_simples = True
            if fluxo_por_furos:
                resultado = fluxo_por_furos
            elif excecao_recorte_simples:
                resultado = f"Fluxo 2 [{fmt(esp)}]"
            else:
                # Regra por espessura, tem prioridade sobre identificador/prefixo. Inclui:
                # >9,50mm sempre Fluxo 3; faixas 6,35/4,75/4,25/3,75/3,35 por tamanho
                fluxo_por_espessura = decidir_fluxo(esp, largura_dxf, altura_dxf, irregular)
                if fluxo_por_espessura:
                    resultado = fluxo_por_espessura
                else:
                    # Prefixos de acessórios padrão (PC/SD/SEZ/SE) mantêm prioridade alta -
                    # são peças de função especial (suportes, esticadores etc.), não um
                    # perfil comum, então vão para a pasta "Acessórios Padrão". Só o "PC"
                    # tem a exceção de 50mm -> Fluxo 4; SD/SEZ/SE vão para Acessórios
                    # Padrão sempre, independente da dimensão. Os demais prefixos (EA,
                    # PPG, TZ, MFPA, MFP, SC) seguem a regra normal por
                    # DEFINIÇÃO/IDENTIFICADOR, no ramo abaixo.
                    if verificar_prefixo(arq, ["PC", "SD", "SEZ", "SE"]):
                        if verificar_prefixo(arq, ["PC"]) and (largura_dxf == 50 or altura_dxf == 50):
                            resultado = f"Fluxo 4 [{fmt(esp)}]"
                        else:
                            resultado = f"Acessórios Padrão [{fmt(esp)}]"
                    else:
                        # IDENTIFICADOR tem prioridade sobre CSC/prefixo genérico: a coluna
                        # IDENTIFICADOR da planilha é quem diz se a peça é L (Perfiladeira L)
                        # ou U/C (Perfiladeira U e C) - isso vale para marcas MF/PDG/ED, que
                        # não têm um fluxo fixo, dependem do que está na planilha.
                        id_upper = str(identificador).upper().strip() if identificador else ""
                        eh_ch = id_upper.startswith("CH.")
                        eh_perfil_luc = (not eh_ch) and id_upper.startswith(("L", "U", "C"))
                        if regra_perfilar_U(esp, identificador, definicao) is True:
                            resultado = f"Perfiladeira U e C [{fmt(esp)}]"
                        elif regra_perfilar_C(esp, identificador, definicao) is True:
                            resultado = f"Perfiladeira U e C [{fmt(esp)}]"
                        elif regra_perfilar_L(esp, identificador, definicao) is True:
                            maior_l = (max(largura_dxf, altura_dxf)
                                       if largura_dxf is not None and altura_dxf is not None else None)
                            resultado = f"Perfiladeira {destino_perfiladeira_L(definicao, maior_l)} [{fmt(esp)}]"
                        elif eh_perfil_luc and 1.25 <= esp <= 3.00:
                            # Caso especial: DESENVOLVIMENTO da planilha = 495mm e abas
                            # iguais >= 400mm - fora da faixa de catálogo normal da
                            # Perfiladeira (que limita L a 30-78mm, U a 50-103mm, C a
                            # 25-90mm) - mesmo assim vai para "Perfiladeira U e C",
                            # seguindo a DEFINIÇÃO/IDENTIFICADOR, em vez de cair no
                            # fallback por tamanho abaixo.
                            aba_a, aba_b = extrair_abas_generico(definicao)
                            abas_iguais_grandes = (
                                aba_a is not None and aba_b is not None
                                and aba_a == aba_b and aba_a >= 400
                            )
                            desenvolvimento_495 = (
                                desenvolvimento_planilha is not None
                                and not pd.isna(desenvolvimento_planilha)
                                and abs(float(desenvolvimento_planilha) - 495) < 0.5
                            )
                            if abas_iguais_grandes and desenvolvimento_495:
                                resultado = f"Perfiladeira U e C [{fmt(esp)}]"
                            elif largura_dxf is not None and altura_dxf is not None:
                                # IDENTIFICADOR confirma que é um perfil L/U/C, mas não bateu as
                                # dimensões de catálogo da Perfiladeira (ex: abas diferentes) ->
                                # vai direto para o fallback por tamanho (Fluxo 1/2/4 conforme o
                                # comprimento/desenvolvimento), SEM passar pelo heurístico de CSC
                                maior = max(largura_dxf, altura_dxf)
                                if maior > 3000:
                                    resultado = f"Fluxo 1 [{fmt(esp)}]"
                                elif maior > 400:
                                    resultado = f"Fluxo 2 [{fmt(esp)}]"
                                else:
                                    resultado = f"Fluxo 4 [{fmt(esp)}]"
                            # else: sem as duas dimensões do DXF, não dá pra decidir por
                            # tamanho aqui - resultado permanece None (peça cai em "Não
                            # Roteirizado" em vez de travar o processamento inteiro)
                        elif (abs(esp - 3.00) < 0.01 and largura_dxf is not None and altura_dxf is not None
                                and abs(altura_dxf - 300) < 0.01 and 190 <= largura_dxf <= 310
                                and contar_furos_diametro(caminho, 14.0) == 4):
                            # Regra específica: 3,00mm, altura 300mm, largura 190-310mm, 4 furos Ø14mm
                            resultado = f"Fluxo 4 [{fmt(esp)}]"
                        elif verificar_prefixo(arq, ["MF", "ED"]):
                            # Fallback: só chega aqui se IDENTIFICADOR não resolveu nada acima
                            resultado = f"Perfiladeira U e C [{fmt(esp)}]"
                        elif 1.25 <= esp <= 3.00 and largura_dxf is not None and altura_dxf is not None:
                            # Fallback por tamanho: qualquer identificador (CH., etc.) que não
                            # bateu em nenhuma regra específica acima - incluindo casos onde
                            # DEFINIÇÃO/IDENTIFICADOR não bateram um perfil de catálogo válido -
                            # é roteirizado pelo tamanho do DXF (nunca cai em CSC por heurística)
                            maior = max(largura_dxf, altura_dxf)
                            if maior > 3000:
                                resultado = f"Fluxo 1 [{fmt(esp)}]"
                            elif maior > 400:
                                resultado = f"Fluxo 2 [{fmt(esp)}]"
                            else:
                                resultado = f"Fluxo 4 [{fmt(esp)}]"
                            # (sem as duas dimensões do DXF nessa faixa de espessura, cai pra
                            # fora deste "elif" e resultado permanece None - peça vai pra "Não
                            # Roteirizado" em vez de travar o processamento com
                            # "'>' not supported between instances of 'NoneType' and 'NoneType'")
    # ESTICADOR (posição "E-<número>", ex: "E-2_U", "E-5_U"): até 800mm de
    # comprimento vai para Fluxo 2, em vez de Perfiladeira U e C. Acima de 800mm
    # continua seguindo a regra normal (Perfiladeira U e C). Só troca quando a
    # cadeia acima decidiu Perfiladeira U e C - não mexe em Fluxo 3 (irregular,
    # furos etc.), e o ajuste manual da memória continua com prioridade (já
    # retornou lá no início da função).
    pos_upper_esticador = str(pos_planilha).upper().strip() if pos_planilha else ""
    eh_esticador_e = bool(re.match(r'^E-\d', pos_upper_esticador)
                          or re.match(r'^E-\d', nome_sem_prefixo_obra.upper()))
    if (eh_esticador_e and resultado and resultado.startswith("Perfiladeira U e C")
            and largura_dxf is not None and altura_dxf is not None
            and max(largura_dxf, altura_dxf) <= 800):
        resultado = f"Fluxo 2 [{fmt(esp)}]"
    # Item 1: limite de máquina da PERFILADEIRA U e C - a máquina não roteia bem peças
    # curtas. Peça U/C com comprimento (maior dimensão do DXF) MENOR que 700mm e espessura
    # de até 3,00mm vai para Fluxo 4, NÃO para a perfiladeira. A partir de 700mm (ou acima
    # de 3,00mm de espessura) mantém a Perfiladeira U e C normalmente.
    # Esse limite vale SÓ para a U e C. A Perfiladeira L (L1/L2) NÃO tem limite de
    # comprimento: peça L curta (ex.: L52X52X1.55 de 540mm) continua na Perfiladeira L.
    # (Esticador "E-" já foi tratado acima, com a regra própria dele.)
    # (Peça de PREPARAÇÃO - chapa cortada, sem bobina - mantém o comportamento antigo: curta vai para Fluxo 4.)
    if (resultado and (resultado.startswith("Perfiladeira U e C") or (preparacao and resultado.startswith("Perfiladeira")))
            and esp is not None and esp <= 3.00 + 0.005
            and largura_dxf is not None and altura_dxf is not None
            and max(largura_dxf, altura_dxf) < 700):
        resultado = f"Fluxo 4 [{fmt(esp)}]"
    # Se a decisão final foi Fluxo 4, nas espessuras 4,75/6,35/8,00/9,50, verificar
    # se o recorte é grande (>150mm) ou aparece dos dois lados da peça - nesse
    # caso, promover para Fluxo 3
    if (resultado and resultado.startswith("Fluxo 4")
            and any(abs(esp - v) < 0.01 for v in [4.75, 6.35, 8.00, 9.50])):
        recorte_grande, recorte_dos_dois_lados = analisar_recorte_dxf(caminho)
        if recorte_grande or recorte_dos_dois_lados:
            resultado = f"Fluxo 3 [{fmt(esp)}]"
    # Item 2b: furos oblongos só são feitos no plasma - se a peça tem furo oblongo
    # e o resultado é Fluxo 4, promove para Fluxo 3 independente de recorte.
    # Exceção: furo oblongo 14x28mm (padrão comum) permanece no Fluxo 4.
    if resultado and resultado.startswith("Fluxo 4"):
        _, tipo_furo_peca, diametro_furo_peca, _, _ = analisar_furos_dxf(caminho)
        if tipo_furo_peca in ("OBLONGO", "MISTO"):
            eh_14x28 = False
            if diametro_furo_peca and "x" in diametro_furo_peca:
                try:
                    partes_dim = [float(v) for v in diametro_furo_peca.split("x")]
                    medidas = sorted(partes_dim)
                    if abs(medidas[0] - 14.0) < 0.5 and abs(medidas[1] - 28.0) < 0.5:
                        eh_14x28 = True
                except (ValueError, IndexError):
                    pass
            if not eh_14x28:
                resultado = f"Fluxo 3 [{fmt(esp)}]"
    # Item 3: em Fluxo 1/2, se a peça tem corte em ângulo/grau e espessura > 3,75mm,
    # promove para Fluxo 3 (máquina de Fluxo 1/2 não faz corte em ângulo bem).
    # Peças de 3,00mm ficam de fora dessa promoção - seguem a regra normal de
    # largura/comprimento.
    if (resultado and (resultado.startswith("Fluxo 1") or resultado.startswith("Fluxo 2"))
            and esp > 3.75 and abs(esp - 3.00) >= 0.01):
        if possui_angulo_dxf(caminho):
            resultado = f"Fluxo 3 [{fmt(esp)}]"

    # Item 4: chanfros/cortes em diagonal feitos só com LINE (sem ARC/SPLINE)
    # não são pegos por possui_irregularidade, então uma peça pequena (<400mm)
    # com cantos chanfrados cai indevidamente em Fluxo 4. Reaproveita a mesma
    # lógica do Item 3, mas promovendo Fluxo 4 -> 3.
    # Usa possui_angulo_dxf_significativo (não possui_angulo_dxf) - só conta
    # como corte em ângulo real quando os dois catetos (dx e dy) são >= 20mm,
    # para NÃO promover peças que só têm um chanfro pequeno de canto ou uma
    # borda quase vertical/horizontal com um pequeno desvio (essas continuam
    # Fluxo 4 normalmente).
    # Peças de 3,00mm ficam de fora - seguem a regra normal de largura/comprimento.
    if resultado and resultado.startswith("Fluxo 4") and abs(esp - 3.00) >= 0.01:
        if possui_angulo_dxf_significativo(caminho):
            resultado = f"Fluxo 3 [{fmt(esp)}]"
    # Caso raro: posição com "T" de Terça (mas sem ser uma Terça Z de verdade) +
    # identificador C + espessura até 3,00mm + largura que encaixa no catálogo da
    # Perfiladeira C (25-90mm de aba) -> força Perfiladeira U e C, nunca Fluxo 3,
    # mesmo que alguma regra acima já tenha decidido outra coisa
    pos_upper_raro = str(pos_planilha).upper().strip() if pos_planilha else ""
    id_upper_raro = str(identificador).upper().strip() if identificador else ""
    if (pos_upper_raro.startswith("T") and id_upper_raro.startswith("C")
            and not id_upper_raro.startswith("CH.") and esp is not None and esp <= 3.00
            and regra_perfilar_C(esp, identificador, definicao) is True):
        resultado = f"Perfiladeira U e C [{fmt(esp)}]"
    # Material galvanizado nunca vai para o banco de corte (Fluxo 3/plasma) - se
    # alguma regra acima promoveu a peça para Fluxo 3, mas o material é
    # galvanizado, volta a decidir pelo tamanho (largura/comprimento) normalmente
    if (resultado and resultado.startswith("Fluxo 3") and material
            and "GALVANIZADO" in material.upper()
            and largura_dxf is not None and altura_dxf is not None):
        maior_galv = max(largura_dxf, altura_dxf)
        if maior_galv > 3000:
            resultado = f"Fluxo 1 [{fmt(esp)}]"
        elif maior_galv > 400:
            resultado = f"Fluxo 2 [{fmt(esp)}]"
        else:
            resultado = f"Fluxo 4 [{fmt(esp)}]"
    # PREPARAÇÃO: a posição consome CHAPA CORTADA (e nenhuma bobina) = o perfil é cortado e dobrado na Preparação, não perfilado. Se a cadeia
    # acima terminou na perfiladeira (porque a definição cabe no catálogo da máquina, ex.: U186X93X3.00 de 1950mm), vai pelas regras de
    # TAMANHO: acima de 3000mm Fluxo 1, acima de 400mm Fluxo 2, senão Fluxo 4. O que a cadeia já mandou para outro fluxo (peça curta
    # abaixo de 700mm -> Fluxo 4, esticador até 800mm -> Fluxo 2 etc.) não muda.
    if (preparacao and resultado and resultado.startswith("Perfiladeira") and esp is not None
            and largura_dxf is not None and altura_dxf is not None):
        maior_prep = max(largura_dxf, altura_dxf)
        if maior_prep > 3000:
            resultado = f"Fluxo 1 [{fmt(esp)}]"
        elif maior_prep > 400:
            resultado = f"Fluxo 2 [{fmt(esp)}]"
        else:
            resultado = f"Fluxo 4 [{fmt(esp)}]"
    # CIV / CSV (ex.: CIV1_U 150x100, CSV1_U 150x200 com furo Ø11): peças CURTAS que o Daniel confirmou serem da PERFILADEIRA U e C - não são
    # Preparação. A regra do "Item 1" (U/C abaixo de 700mm -> Fluxo 4) e o redirecionamento da Preparação (chapa cortada -> Fluxo 4/2/1) não valem
    # para elas, e quando a definição/identificador não casa com o catálogo a peça caía no fallback por tamanho (<=400mm -> Fluxo 4). Por isso, na
    # espessura da perfiladeira (1,25 a 3,00), o que a cadeia mandou para Fluxo 1/2/4 (ou nada) vira Perfiladeira U e C. Fluxo 3 (irregular, oblongo,
    # ângulo, furos), Joist e Acessórios Padrão ficam como estão, e o ajuste manual (memória) já retornou lá no início da função.
    if (eh_civ_csv(pos_planilha, nome_sem_prefixo_obra) and esp is not None and 1.25 <= esp <= 3.00 + 0.005
            and (resultado is None or resultado.startswith(("Fluxo 1", "Fluxo 2", "Fluxo 4")))):
        resultado = f"Perfiladeira U e C [{fmt(esp)}]"
    return resultado
def identificar_grupos_fluxo3(planilha, pasta_base):
    """
    Pré-varredura: identifica conjuntos de peças (mesma posição-base, variando
    apenas o sufixo de lado - "@N", "_2/_3" ou "-2/-3" - lado esquerdo/direito de
    um mesmo perfil) onde PELO MENOS UMA das peças do conjunto foi decidida como
    Fluxo 3 pela cadeia normal de regras (decidir_fluxo_peca - a mesma usada no
    processamento real).
    Não importa qual lado bateu Fluxo 3 nem por qual motivo (furos, irregularidade,
    espessura alta etc.): se qualquer peça do conjunto foi decidida Fluxo 3, TODAS
    as peças do conjunto (mesma posição-base) são roteirizadas juntas, mesmo as que
    individualmente não iriam para lá sozinhas (podem até ser lisas, sem furo),
    pois fazem parte do mesmo conjunto físico.
    Retorna um set de chaves (of, pos_base) que devem ser forçadas para Fluxo 3.
    """
    grupos_forcados = set()
    _ignorados_memoria, ajustes_manuais = carregar_memoria()
    for raiz, dirs, arquivos in os.walk(pasta_base):          # TAMBÉM as pastas de fluxo (reavaliação de obra já roteirizada)
        for arq in arquivos:
            if not arq.upper().endswith(".DXF"):
                continue
            caminho = os.path.join(raiz, arq)
            of, pos = extrair_nome(arq)
            if not of:
                continue
            filtro = buscar_posicao(planilha, of, pos)
            if filtro.empty:
                continue
            linha = filtro.iloc[0]
            esp = linha["ESP_N"]
            identificador = linha["ID_N"]
            definicao = linha["DEF_N"]
            pos_planilha = linha["POS_N"]
            material = str(linha.get("MATERIAL_N", "") or "")
            desenvolvimento_planilha = linha.get("DESENV_N", None)
            grupo_lic = str(linha.get("GRUPO_LIC_N", "") or "")
            preparacao = bool(linha.get("PREP_N", False))
            if regra_terca_z(arq, pos_planilha, definicao):
                # Terças Z têm rota própria, não entram nesse agrupamento
                continue
            tipo = extrair_tipo_identificador(identificador, pos_planilha)
            if tipo == "IGNORADO":
                continue
            largura_dxf, altura_dxf = obter_dimensoes_dxf(caminho)
            irregular = possui_irregularidade(caminho)
            _, _, _, _, quantidade_furos = analisar_furos_dxf(caminho)
            fluxo_individual = decidir_fluxo_peca(
                esp, identificador, definicao, pos_planilha, arq, caminho,
                largura_dxf, altura_dxf, irregular, quantidade_furos, material,
                desenvolvimento_planilha, of, ajustes_manuais, grupo_lic, preparacao
            )
            if fluxo_individual and fluxo_individual.startswith("Fluxo 3"):
                pos_base = extrair_posicao_base_conjunto(pos_planilha)
                grupos_forcados.add((of, pos_base))
    if grupos_forcados:
        log(f"🔗 {len(grupos_forcados)} conjunto(s) identificado(s) para Fluxo 3 (algum lado do conjunto bateu Fluxo 3)")
    return grupos_forcados
def extrair_fluxo_base(fluxo):
    """
    Remove o sufixo de espessura entre colchetes do nome do fluxo (ex:
    "Fluxo 3 [4,75]" -> "Fluxo 3"), usado para agrupar o gráfico de peso por
    fluxo pela categoria principal, independente da espessura específica de
    cada peça.
    """
    if not fluxo:
        return "Sem Fluxo"
    return re.sub(r'\s*\[[^\]]*\]\s*$', '', fluxo).strip()
_MANUAIS_PRESERVAR = {}      # pasta da obra (abspath) -> {arquivo: pasta que o programa tinha escolhido}: arquivos que o usuário MOVEU À MÃO


def _fluxo_do_arquivo(raiz, pasta_base):
    """Se o DXF já está dentro de uma pasta de FLUXO (ou de 'Editar'/'Banco de Corte' dentro dela) devolve
    (nome da pasta de fluxo, pasta que CONTÉM essa pasta de fluxo). Fora de pasta de fluxo devolve (None, raiz).
    É o que permite rodar de novo numa obra já roteirizada sem criar 'Fluxo X/Fluxo Y' aninhado."""
    atual, base = os.path.normpath(raiz), os.path.normpath(pasta_base)
    if atual != base and os.path.basename(atual).strip().lower() in _SUBPASTAS_AUXILIARES_FLUXO:
        pai = os.path.dirname(atual)
        if pai != base and _nome_parece_fluxo(os.path.basename(pai)):
            atual = pai
    if atual != base and _nome_parece_fluxo(os.path.basename(atual)):
        return os.path.basename(atual), os.path.dirname(atual)
    return None, raiz


def _limpar_pastas_de_fluxo_vazias(pasta, pasta_base):
    """Depois de tirar um arquivo de uma pasta de fluxo (ou 'Editar'), apaga a pasta se ficou vazia (sobe enquanto for pasta de fluxo)."""
    base, atual = os.path.normpath(pasta_base), os.path.normpath(pasta)
    while atual != base and (os.path.basename(atual).strip().lower() in _SUBPASTAS_AUXILIARES_FLUXO
                             or _nome_parece_fluxo(os.path.basename(atual))):
        try:
            if os.listdir(atual):
                break
            os.rmdir(atual)
        except OSError:
            break
        atual = os.path.dirname(atual)


def _espessura_do_nome_fluxo(nome):
    m = re.search(r'\[\s*([\d.,]+)\s*\]\s*$', str(nome or ''))
    if not m:
        return None
    try:
        return float(m.group(1).replace(',', '.'))
    except ValueError:
        return None


def _mesmo_fluxo(a, b):
    """Compara o nome da pasta de fluxo onde o DXF ESTÁ com o fluxo que a regra manda, de forma tolerante
    (só para a conferência SOMENTE LEITURA): ignora maiúsculas/espaços, aceita espessura escrita diferente
    ("[2,0]" x "[2,00]") e trata "Perfiladeira L" (sem número) como igual a L1/L2."""
    if not a or not b:
        return False
    if str(a).strip().lower() == str(b).strip().lower():
        return True
    ba, bb = extrair_fluxo_base(a).strip().lower(), extrair_fluxo_base(b).strip().lower()
    if ba != bb:
        la, lb = re.fullmatch(r'perfiladeira l([12]?)', ba), re.fullmatch(r'perfiladeira l([12]?)', bb)
        if not (la and lb and (la.group(1) == '' or lb.group(1) == '')):
            return False
    ea, eb = _espessura_do_nome_fluxo(a), _espessura_do_nome_fluxo(b)
    return ea == eb or (ea is not None and eb is not None and abs(ea - eb) < 0.005)


def processar(planilha, pasta_base, simulacao=None):
    # simulacao=None: comportamento normal (organiza/move os DXF).
    # simulacao=[] (lista vazia): MODO SOMENTE LEITURA do Verificador - NÃO move, NÃO cria pasta e ignora o "retrato" do
    # roteirizador; roda as MESMAS regras de sempre e acrescenta na lista um dict por peça cuja pasta atual é diferente
    # da que a regra manda (funciona em obra roteirizada por qualquer pessoa/programa, com ou sem retrato).
    # Estatísticas para relatório final
    stats = {
        'total_dxfs': 0,
        'encontrados': 0,
        'nao_encontrados': 0,
        'tercas_z': 0,
        'csc': 0,  # ALTERADO: acp para csc
        'fluxo4_pc': 0,
        'perfilares_u': 0,
        'perfilares_c': 0,
        'perfilares_l': 0,
        'fluxos': 0,
        'ajustes_manuais_aplicados': 0,
        'irregularidades': 0,
        'ja_no_lugar': 0,          # reavaliação: já estava na pasta de fluxo certa
        'reposicionados': 0,       # reavaliação: estava em outra pasta de fluxo e foi para a certa (pela regra)
        'mantidos_manual': 0,      # reavaliação: movido à mão pelo usuário depois da última roteirização - mantido
    }
    lista_reposicionados = []
    caminhos_processados = set()

    # Listas para armazenar análises
    dxfs_encontrados = []
    analise_quantidade = []
    analise_dimensoes = []
    analise_furos = []
    analise_pesos = []
    ofs_encontradas = set()
    fluxos_atribuidos = {}
    grupos_partes = defaultdict(list)   # (OF, posição) -> [(arquivo, parte, larg, alt)] p/ peças divididas A/B
    contexto_partes = {}
    # Carrega a memória de exceções (SQLite) - itens marcados como "não gera
    # DXF" (ignorados) e fluxos definidos manualmente (ajustes_manuais),
    # válidos para QUALQUER obra. Carregado UMA VEZ aqui, não a cada peça.
    ignorados_memoria, ajustes_manuais = carregar_memoria()
    log(f"🧠 Memória carregada de '{_caminho_banco_memoria()}': "
        f"{len(ignorados_memoria)} ignorado(s), {len(ajustes_manuais)} ajuste(s) manual(is)")
    if ajustes_manuais:
        for (ident_mem, pos_mem), fluxo_mem in ajustes_manuais.items():
            log(f"   🔀 memorizado: identificador='{ident_mem}' / posição='{pos_mem}' -> '{fluxo_mem}'")
    # ===== REAVALIAÇÃO: rodar de novo numa obra que já foi roteirizada =====
    # Todos os DXF são analisados de novo, inclusive os que já estão dentro de pastas de fluxo. O que o usuário MOVEU À MÃO para
    # outra pasta de fluxo depois da última roteirização (compara com o retrato salvo) é mantido onde está e só é avisado -
    # quem registra o motivo é a aba Verificador. O resto é conferido com as regras e, se estiver na pasta errada, vai para a certa.
    manuais_roteiro, preservar = {}, {}
    try:
        comparacao_anterior = comparar_roteirizacao_com_atual(pasta_base) if simulacao is None else None
    except Exception:
        comparacao_anterior = None
    if comparacao_anterior:
        for dv in comparacao_anterior["divergencias"]:
            if _nome_parece_fluxo(dv.get("fluxo_atual")):
                manuais_roteiro[dv["arquivo"]] = dv["fluxo_atual"]
                preservar[dv["arquivo"]] = dv.get("pasta_no_snapshot")
        log("🔁 Esta pasta já tinha sido roteirizada antes: vou reavaliar TODOS os DXF, inclusive os que já estão em pastas de fluxo.")
        if manuais_roteiro:
            log(f"🖐️ {len(manuais_roteiro)} arquivo(s) foram movidos por você para outro fluxo depois da última roteirização - "
                "mantidos onde estão (registre o motivo na aba Verificador):")
            for nome_m, pasta_m in list(manuais_roteiro.items())[:20]:
                log(f"   🖐️ {nome_m} -> {pasta_m}")
    if simulacao is None:
        _MANUAIS_PRESERVAR[os.path.abspath(pasta_base)] = preservar
    # Pré-varredura: identifica conjuntos (@N / lado esq-dir) que precisam ir
    # juntos para Fluxo 3, usando a mesma decisão que será usada no processamento
    log("🔍 Pré-analisando conjuntos de peças (lado esquerdo/direito) para Fluxo 3...")
    grupos_fluxo3 = identificar_grupos_fluxo3(planilha, pasta_base)
    for raiz, dirs, arquivos in os.walk(pasta_base):          # TAMBÉM as pastas de fluxo (reavaliação de obra já roteirizada)
        for arq in arquivos:
            if not arq.upper().endswith(".DXF"):
                continue
            caminho = os.path.join(raiz, arq)
            if os.path.normpath(caminho) in caminhos_processados:
                continue          # arquivo que acabou de ser movido para uma pasta que o os.walk ainda ia visitar
            stats['total_dxfs'] += 1
            of, pos = extrair_nome(arq)
            if not of:
                continue
            ofs_encontradas.add(of)
            filtro = buscar_posicao(planilha, of, pos)
            if filtro.empty:
                log(f"❌ Não encontrado na planilha -> {arq}")
                stats['nao_encontrados'] += 1
                continue
            stats['encontrados'] += 1
            linha = filtro.iloc[0]
            esp = linha["ESP_N"]
            identificador = linha["ID_N"]
            definicao = linha["DEF_N"]
            pos_planilha = linha["POS_N"]
            largura_planilha = linha.get("LARGURA_N", None)
            largura_planilha_alt = linha.get("LARGURA_ALT_N", None)
            desenvolvimento_planilha = linha.get("DESENV_N", None)
            comprimento_planilha = linha.get("COMPR_N", None)
            qtd_validas = filtro["QTD_N"].dropna() if "QTD_N" in filtro.columns else None
            # A mesma posição pode aparecer em mais de uma linha da planilha (peça
            # que é cortada em vários desenhos diferentes) - nesse caso a quantidade
            # correta para comparar com o DXF é a SOMA de todas as linhas, não só
            # a quantidade de uma linha isolada.
            qtd_planilha = float(qtd_validas.sum()) if qtd_validas is not None and len(qtd_validas) > 0 else None
            descricao_planilha = str(linha.get("DESC_N", "") or "")
            material_planilha = str(linha.get("MATERIAL_N", "") or "")
            grupo_lic_planilha = str(linha.get("GRUPO_LIC_N", "") or "")
            preparacao_planilha = bool(linha.get("PREP_N", False))
            # Extrair quantidade do nome do arquivo (Q8)
            qtd_dxf = extrair_quantidade_arquivo(arq)
            # Verificar ANTES do descarte se é uma Terça Z válida (nome do arquivo,
            # posição e definição seguem o padrão TZ/TZ/Z). Terças Z têm identificador
            # começando com "Z", o que as classificaria como IGNORADO logo abaixo -
            # por isso essa checagem precisa vir primeiro, para que sejam efetivamente
            # roteirizadas seguindo suas próprias regras (tolerância 10mm, fluxo "Terça Z").
            eh_terca_z_real = regra_terca_z(arq, pos_planilha, definicao)
            # Verificar se o identificador é ignorado
            tipo = extrair_tipo_identificador(identificador, pos_planilha)
            # ===== PRIORIDADE ABSOLUTA: ajuste manual salvo na memória (SQLite) =====
            # Precisa ser checado ANTES do descarte por "IGNORADO" - identificadores
            # que começam com "Z" (ex: "ZD") caem em IGNORADO por padrão (a regra
            # assume que só existem Terças Z começando com "Z"), mas podem ser um
            # tipo de peça totalmente diferente que o usuário já definiu manualmente
            # pelo Verificador/relatório. Sem essa checagem aqui, o ajuste manual
            # nunca teria chance de ser aplicado, porque a peça seria descartada
            # antes mesmo de chegar na etapa de decidir o fluxo.
            chave_memoria_direta = _normalizar_chave_memoria(identificador, pos_planilha)
            tem_ajuste_manual = bool(ajustes_manuais and chave_memoria_direta in ajustes_manuais)
            # Se for IGNORADO e NÃO for uma Terça Z válida NEM tiver ajuste manual
            # salvo, não adicionar às análises (BR_RED, W_, PS, campos vazios e
            # demais itens "Z" que não batem o padrão completo)
            if tipo == "IGNORADO" and not eh_terca_z_real and not tem_ajuste_manual:
                continue
            # Também ignorar se a DESCRIÇÃO (DES_PEZ) da peça começar com "BR_RED"
            # ou "BR" - mesmo critério do identificador, mas aplicado à descrição
            if descricao_planilha.upper().strip().startswith(("BR_RED", "BR")):
                continue

            # ===== PRIMEIRO: ANALISAR O DXF (ANTES DE MOVER) =====
            # Obter dimensões do DXF
            largura_dxf, altura_dxf = obter_dimensoes_dxf(caminho)
            parte = extrair_parte_nome(arq)
            grupos_partes[(of, pos_planilha)].append((arq, parte, largura_dxf, altura_dxf))
            if parte:
                log(f"✂️  Peça dividida: {arq} é a parte [{parte}] da posição {pos_planilha}")
                contexto_partes.setdefault((of, pos_planilha), {
                    "identificador": identificador, "largura_planilha": largura_planilha,
                    "largura_planilha_alt": largura_planilha_alt, "desenvolvimento_planilha": desenvolvimento_planilha,
                    "comprimento_planilha": comprimento_planilha,
                    "tolerancia": 10.0 if eh_terca_z(pos_planilha, identificador) else 3.0})

            # Análise de Furos
            tem_furo, tipo_furo, diametro, descricao, quantidade_furos = analisar_furos_dxf(caminho)

            # Determinar tolerância (cada posição pode variar até 3mm para
            # menos ou para mais, exceto Terças Z que têm tolerância maior)
            if eh_terca_z(pos_planilha, identificador):
                tolerancia = 10.0
            else:
                tolerancia = 3.0

            # Determinar fluxo
            fluxo_atual = None
            # Verificar regras de roteirização, em ordem de prioridade:
            # 0) ajuste manual salvo na memória (SQLite) - PRIORIDADE ABSOLUTA,
            #    sobrepõe QUALQUER outra regra, inclusive Terça Z (já calculado
            #    acima, em tem_ajuste_manual/chave_memoria_direta). Se o usuário
            #    já definiu manualmente o fluxo dessa (identificador, posição)
            #    antes (em qualquer obra), usa direto e não roda mais nada.
            # 1) Terça Z  2) decisão individual da peça (decidir_fluxo_peca: ACE,
            # espessura, regras de furos, prefixos, perfil J/U/C/L, fallback)
            # 3) se a peça não decidiu Fluxo 3 sozinha, mas faz parte de um conjunto
            # (mesma posição-base, lado esquerdo/direito) onde outro lado decidiu
            # Fluxo 3, força Fluxo 3 também - não importa o motivo nem qual lado.
            if arq in manuais_roteiro:
                fluxo_atual = manuais_roteiro[arq]          # movido à mão depois da última roteirização: respeita
                stats['mantidos_manual'] += 1
            elif tem_ajuste_manual:
                fluxo_atual = ajustes_manuais[chave_memoria_direta]
                stats['ajustes_manuais_aplicados'] += 1
            elif eh_terca_z_real:
                fluxo_atual = f"Terça Z [{str(esp).replace('.', ',')}]"
                stats['tercas_z'] += 1
            else:
                irregular = possui_irregularidade(caminho)
                fluxo_atual = decidir_fluxo_peca(
                    esp, identificador, definicao, pos_planilha, arq, caminho,
                    largura_dxf, altura_dxf, irregular, quantidade_furos, material_planilha,
                    desenvolvimento_planilha, of, ajustes_manuais, grupo_lic_planilha, preparacao_planilha
                )
                # DIAGNÓSTICO TEMPORÁRIO "ZD": mostra no log todos os valores usados
                # na decisão pra essa categoria específica, pra confirmar por qual
                # caminho da cadeia de regras ela está passando (remover depois de
                # confirmado o comportamento correto).
                if str(identificador).upper().strip().startswith("ZD"):
                    maior_dbg = max(largura_dxf, altura_dxf) if (largura_dxf is not None and altura_dxf is not None) else None
                    log(f"🔎 DIAGNÓSTICO ZD -> arq='{arq}' pos='{pos_planilha}' esp={esp} "
                        f"largura={largura_dxf} altura={altura_dxf} maior={maior_dbg} "
                        f"irregular={irregular} furos={quantidade_furos} material='{material_planilha}' "
                        f"=> fluxo_atual='{fluxo_atual}'")
                if not (fluxo_atual and fluxo_atual.startswith("Fluxo 3")):
                    pos_base = extrair_posicao_base_conjunto(pos_planilha)
                    if (of, pos_base) in grupos_fluxo3:
                        fluxo_atual = f"Fluxo 3 [{str(esp).replace('.', ',')}]"
                # ===== MÁQUINA LASER =====
                # Tudo que cairia em Fluxo 3 (plasma) com espessura até 12,70mm e
                # maior dimensão até 6000mm (inclusive) vai para a pasta "LASER [espessura]". As
                # regras que decidem Fluxo 3 NÃO mudam - só o destino do arquivo.
                # Acima de 12,70mm, acima de 6000mm ou sem dimensão lida,
                # continua Fluxo 3. Ajuste manual da memória não passa por aqui.
                if (fluxo_atual and fluxo_atual.startswith("Fluxo 3")
                        and esp is not None and esp <= 12.70 + 0.001
                        and largura_dxf is not None and altura_dxf is not None
                        and max(largura_dxf, altura_dxf) <= 6000):
                    fluxo_atual = f"LASER [{str(esp).replace('.', ',')}]"
                if fluxo_atual:
                    if fluxo_atual.startswith("Acessórios Padrão"):
                        stats['csc'] += 1
                    elif fluxo_atual.startswith("Perfiladeira U e C"):
                        stats['perfilares_u'] += 1
                    elif fluxo_atual.startswith("Perfiladeira L"):
                        stats['perfilares_l'] += 1
                    elif (fluxo_atual.startswith("Fluxo 4")
                          and verificar_prefixo(arq, ["PC", "SD", "SEZ", "SE"])):
                        stats['fluxo4_pc'] += 1
                    else:
                        stats['fluxos'] += 1
                if irregular:
                    stats['irregularidades'] += 1
            # ===== DEPOIS: MOVER O ARQUIVO =====
            if fluxo_atual:
                # Se o arquivo já está na pasta de fluxo certa (ou dentro de "Editar" dela, caso de peça grande), não faz nada. Se está
                # em OUTRA pasta de fluxo (obra já roteirizada antes, regra corrigida depois), vai para a pasta certa AO LADO dela -
                # a pasta de fluxo nunca é criada dentro de outra pasta de fluxo.
                nome_fluxo_pasta, raiz_base = _fluxo_do_arquivo(raiz, pasta_base)
                if simulacao is not None:
                    # SOMENTE LEITURA: só registra o que está fora da regra; nada é movido nem criado.
                    if not (nome_fluxo_pasta and _mesmo_fluxo(nome_fluxo_pasta, fluxo_atual)):
                        simulacao.append({
                            'of': of, 'pos': pos_planilha, 'identificador': identificador, 'arquivo': arq,
                            'caminho': caminho, 'pasta_base': pasta_base,
                            'regra': fluxo_atual,
                            'atual': nome_fluxo_pasta or f"(fora de pasta de fluxo: {os.path.basename(raiz) or raiz})",
                            'ajuste_manual': bool(arq not in manuais_roteiro and tem_ajuste_manual),
                        })
                    caminhos_processados.add(os.path.normpath(caminho))
                    ja_esta_no_lugar_certo = True
                else:
                    ja_esta_no_lugar_certo = (nome_fluxo_pasta == fluxo_atual)
                if ja_esta_no_lugar_certo:
                    stats['ja_no_lugar'] += 1
                    caminhos_processados.add(os.path.normpath(caminho))
                if not ja_esta_no_lugar_certo:
                    pasta_destino = os.path.join(raiz_base, fluxo_atual)
                    os.makedirs(pasta_destino, exist_ok=True)
                    shutil.move(caminho, os.path.join(pasta_destino, arq))
                    caminhos_processados.add(os.path.normpath(os.path.join(pasta_destino, arq)))
                    if nome_fluxo_pasta:
                        stats['reposicionados'] += 1
                        lista_reposicionados.append((arq, nome_fluxo_pasta, fluxo_atual))
                        log(f"↪️  {arq}: estava em '{nome_fluxo_pasta}' e as regras mandam para '{fluxo_atual}' - movido")
                        _limpar_pastas_de_fluxo_vazias(raiz, pasta_base)
                    # Guarda de None: fluxo_atual pode ter vindo da memória (ajuste
                    # manual), que não depende de dimensão nenhuma - então mesmo uma
                    # peça cujo DXF não teve largura/altura lidas (geometria não
                    # suportada, arquivo incomum) pode chegar até aqui. Sem essa
                    # checagem, travava com "'>' not supported between instances of
                    # 'NoneType' and 'NoneType'".
                    if (largura_dxf is not None and altura_dxf is not None
                            and max(largura_dxf, altura_dxf) > 6001):
                        pasta_editar = os.path.join(pasta_destino, "Editar")
                        os.makedirs(pasta_editar, exist_ok=True)
                        shutil.move(os.path.join(pasta_destino, arq), os.path.join(pasta_editar, arq))
                        if not parte:
                            log(f"✂️  {arq}: comprimento {max(largura_dxf, altura_dxf):.0f}mm (acima de 6000mm) - dividir em "
                                f"[A] e [B] e renomear os DXF como {pos_planilha}[A] e {pos_planilha}[B]. Movido para 'Editar'.")

            elif simulacao is not None:
                # SOMENTE LEITURA: nenhuma regra decidiu esta peça. Se ela também está fora de pasta de fluxo, avisa.
                nome_fluxo_pasta_sr, _raiz_sr = _fluxo_do_arquivo(raiz, pasta_base)
                if not nome_fluxo_pasta_sr:
                    simulacao.append({
                        'of': of, 'pos': pos_planilha, 'identificador': identificador, 'arquivo': arq,
                        'caminho': caminho, 'pasta_base': pasta_base, 'regra': "(sem regra)",
                        'atual': f"(fora de pasta de fluxo: {os.path.basename(raiz) or raiz})", 'ajuste_manual': False,
                    })
            # ===== REGISTRAR TODAS AS ANÁLISES =====
            # Adicionar à lista de DXFs encontrados
            dxf_item = {
                'of': of,
                'pos': pos_planilha,
                'identificador': identificador,
                'arquivo': arq,
                'ignorado': tipo == "IGNORADO",
                'espessura': esp
            }
            dxfs_encontrados.append(dxf_item)

            # Guardar fluxo atribuído
            chave = f"{of}|{pos_planilha}|{identificador}"
            fluxos_atribuidos[chave] = fluxo_atual if fluxo_atual else "Sem Fluxo"
            # Análise de Quantidade
            if qtd_dxf is not None:
                status_qtd = "OK" if qtd_dxf == qtd_planilha else "DIVERGENTE"
                analise_quantidade.append({
                    'pos': pos_planilha,
                    'identificador': identificador,
                    'qtd_dxf': qtd_dxf,
                    'qtd_planilha': qtd_planilha,
                    'status': status_qtd
                })
                if status_qtd == "DIVERGENTE":
                    log(f"⚠️  Divergência de quantidade: {arq} - DXF:{qtd_dxf} ≠ Plan:{qtd_planilha}")

            # Análise de Dimensões (peças divididas A/B são conferidas em conjunto, depois do laço)
            if largura_dxf is not None and altura_dxf is not None and not parte:
                if largura_planilha is not None and desenvolvimento_planilha is not None:
                    status_dim = comparar_dimensoes_com_tolerancia(
                        largura_dxf, altura_dxf, largura_planilha, desenvolvimento_planilha, tolerancia
                    )

                    if status_dim != "OK" and comprimento_planilha is not None:
                        status_dim2 = comparar_dimensoes_com_tolerancia(
                            largura_dxf, altura_dxf, largura_planilha, comprimento_planilha, tolerancia
                        )
                        if status_dim2 == "OK":
                            status_dim = "OK"
                    # Se ainda divergente, tenta com o valor "alternativo" de largura
                    # (LAR_PRO <-> DESENVOLVIMENTO trocados) - às vezes a informação
                    # certa está na outra coluna, então antes de dar divergência de
                    # verdade, verifica a outra também
                    if status_dim != "OK" and largura_planilha_alt is not None:
                        status_dim3 = comparar_dimensoes_com_tolerancia(
                            largura_dxf, altura_dxf, largura_planilha_alt, desenvolvimento_planilha, tolerancia
                        )
                        if status_dim3 == "OK":
                            status_dim = "OK"
                        elif comprimento_planilha is not None:
                            status_dim4 = comparar_dimensoes_com_tolerancia(
                                largura_dxf, altura_dxf, largura_planilha_alt, comprimento_planilha, tolerancia
                            )
                            if status_dim4 == "OK":
                                status_dim = "OK"

                    if status_dim == "DIVERGENTE":
                        log(f"⚠️  Divergência de dimensão: {arq} - Larg DXF={largura_dxf:.1f} Alt DXF={altura_dxf:.1f} | Plan Larg={largura_planilha:.1f} Desenv={desenvolvimento_planilha:.1f} Compr={comprimento_planilha if comprimento_planilha else 'N/A'}")
                    # Diferença de referência (combinação principal: largura x
                    # desenvolvimento/comprimento) - só para exibição na aba
                    # "📐 Divergência de Tamanho"; a decisão OK/DIVERGENTE em si
                    # já considera rotação e a coluna alternativa de largura.
                    ref_altura_planilha = desenvolvimento_planilha if desenvolvimento_planilha is not None else comprimento_planilha
                    diferenca_largura = (abs(largura_dxf - largura_planilha)
                                         if largura_planilha is not None else None)
                    diferenca_altura = (abs(altura_dxf - ref_altura_planilha)
                                        if ref_altura_planilha is not None else None)
                    analise_dimensoes.append({
                        'of': of,
                        'arquivo': arq,
                        'pos': pos_planilha,
                        'identificador': identificador,
                        'largura_dxf': largura_dxf,
                        'largura_planilha': largura_planilha,
                        'altura_dxf': altura_dxf,
                        'desenvolvimento_planilha': desenvolvimento_planilha,
                        'comprimento_planilha': comprimento_planilha,
                        'diferenca_largura': diferenca_largura,
                        'diferenca_altura': diferenca_altura,
                        'tolerancia': tolerancia,
                        'status': status_dim
                    })

            # Análise de Furos
            analise_furos.append({
                'pos': pos_planilha,
                'identificador': identificador,
                'tem_furo': tem_furo,
                'tipo_furo': tipo_furo if tem_furo else "N/A",
                'diametro': diametro if tem_furo else "N/A",
                'descricao': descricao,
                'quantidade_furos': quantidade_furos
            })
            # Análise de Peso (alimenta a aba "⚖️ Peso por Fluxo") - só registra
            # peças que efetivamente foram roteirizadas para algum fluxo e que
            # têm dimensões/espessura conhecidas para calcular o peso.
            if fluxo_atual and largura_dxf is not None and altura_dxf is not None and esp is not None:
                quantidade_peso = qtd_dxf if qtd_dxf is not None else (qtd_planilha if qtd_planilha is not None else 1)
                peso_unitario = calcular_peso(largura_dxf, altura_dxf, esp)
                analise_pesos.append({
                    'fluxo': fluxo_atual,
                    'fluxo_base': extrair_fluxo_base(fluxo_atual),
                    'pos': pos_planilha,
                    'identificador': identificador,
                    'quantidade': quantidade_peso,
                    'peso_unitario': peso_unitario,
                    'peso_total': peso_unitario * quantidade_peso,
                })
            log(f"📄 Processando: {arq} -> {fluxo_atual if fluxo_atual else 'Sem fluxo'} | Furos: {quantidade_furos if tem_furo else 0}")
    # ===== Peças divididas em partes A/B: conferência do conjunto =====
    for (of_g, pos_g), itens_g in grupos_partes.items():
        partes_g = [(a, p, l, h) for a, p, l, h in itens_g if p]
        if not partes_g:
            continue
        soltos = [a for a, p, l, h in itens_g if not p]
        if soltos:
            log(f"⚠️  Posição {pos_g} (OF {of_g}): existe DXF inteiro ({', '.join(soltos)}) junto das partes "
                f"{'/'.join(sorted({p for _, p, _, _ in partes_g}))} - confira se o original ainda deveria estar na pasta")
        ctx = contexto_partes.get((of_g, pos_g))
        dims_ok = [(l, h) for _, _, l, h in partes_g if l is not None and h is not None]
        if not ctx or len(dims_ok) != len(partes_g):
            continue
        comprimento_total = sum(max(l, h) for l, h in dims_ok)
        largura_peca = max(min(l, h) for l, h in dims_ok)
        tol_g = ctx.get("tolerancia", 3.0) * len(partes_g)   # tolerância por parte (corte A/B)
        lp, dp, cp, la = (ctx["largura_planilha"], ctx["desenvolvimento_planilha"], ctx["comprimento_planilha"],
                          ctx["largura_planilha_alt"])
        if lp is None or dp is None:
            continue
        status_g = _status_dimensao(comprimento_total, largura_peca, lp, dp, cp, la, tol_g)
        letras = "+".join(sorted(p for _, p, _, _ in partes_g))
        if status_g == "DIVERGENTE":
            log(f"⚠️  Divergência de dimensão (peça dividida {pos_g}[{letras}]): comprimento somado={comprimento_total:.1f} "
                f"largura={largura_peca:.1f} | Plan Larg={lp:.1f} Desenv={dp:.1f} Compr={cp if cp else 'N/A'}")
        ref_alt = dp if dp is not None else cp
        analise_dimensoes.append({
            'of': of_g, 'arquivo': " + ".join(a for a, _, _, _ in partes_g), 'pos': pos_g,
            'identificador': ctx["identificador"], 'largura_dxf': comprimento_total, 'largura_planilha': lp,
            'altura_dxf': largura_peca, 'desenvolvimento_planilha': dp, 'comprimento_planilha': cp,
            'diferenca_largura': abs(comprimento_total - lp), 'diferenca_altura': abs(largura_peca - ref_alt),
            'tolerancia': tol_g, 'status': status_g})
    # Relatório final
    print("\n" + "="*70)
    print(" 📊 RELATÓRIO DE PROCESSAMENTO ".center(70, "="))
    print("="*70)
    print(f"📁 Total de arquivos DXF encontrados: {stats['total_dxfs']}")
    print(f"✅ Encontrados na planilha: {stats['encontrados']}")
    print(f"❌ Não encontrados na planilha: {stats['nao_encontrados']}")
    print(f"🔷 Terças Z: {stats['tercas_z']}")
    print(f"🧠 Ajustes manuais aplicados (memória): {stats['ajustes_manuais_aplicados']}")
    print(f"🧩 Acessórios Padrão: {stats['csc']}")
    print(f"🔄 Fluxo 4 PC: {stats['fluxo4_pc']}")
    print(f"📌 Perfiladeiras U e C: {stats['perfilares_u'] + stats['perfilares_c']}")
    print(f"📌 Perfiladeiras L: {stats['perfilares_l']}")
    print(f"🔄 Fluxos processados: {stats['fluxos']}")
    print(f"⚠️  Irregularidades: {stats['irregularidades']}")
    if stats['ja_no_lugar'] or stats['reposicionados'] or stats['mantidos_manual']:
        print(f"🔁 Reavaliação: {stats['ja_no_lugar']} já estavam no fluxo certo | {stats['reposicionados']} movido(s) para o fluxo correto | "
              f"{stats['mantidos_manual']} mantido(s) por terem sido movidos à mão")
    print("="*70 + "\n")

    print(f"\n📊 ANÁLISE DE QUANTIDADE: {len(analise_quantidade)} itens analisados")
    print(f"📐 ANÁLISE DE DIMENSÕES: {len(analise_dimensoes)} itens analisados")
    print(f"🔩 ANÁLISE DE FUROS: {len(analise_furos)} itens analisados")
    peso_total_geral = sum(item['peso_total'] for item in analise_pesos)
    print(f"⚖️  PESO TOTAL ROTEIRIZADO: {peso_total_geral:.1f} kg ({len(analise_pesos)} posições)")

    return (dxfs_encontrados, ofs_encontradas, analise_quantidade, analise_dimensoes, analise_furos,
            fluxos_atribuidos, ignorados_memoria, analise_pesos)
def consolidar_pastas_variantes(pasta_base):
    """
    Percorre as pastas de saída (Fluxo 1/2/3/4, Perfiladeira L, Perfiladeira U e C,
    CSC, Terça Z) e funde variações de espessura que na prática são a mesma
    (ex: "Fluxo 4 [6,40]", "Fluxo 4 [4,80]", "Fluxo 4 [3,70]" -> deveriam ser
    "Fluxo 4 [6,35]", "Fluxo 4 [4,75]", "Fluxo 4 [3,75]"), movendo os arquivos
    para a pasta padrão e removendo a pasta variante.
    """
    padrao_nome = re.compile(r'^(.*)\[(-?\d+[.,]?\d*)\]$')
    for raiz, dirs, arquivos in os.walk(pasta_base):
        for nome_pasta in list(dirs):
            match = padrao_nome.match(nome_pasta.strip())
            if not match:
                continue
            prefixo = match.group(1).strip()
            esp_texto = match.group(2).replace(',', '.')
            try:
                esp_valor = float(esp_texto)
            except ValueError:
                continue
            esp_padrao = padronizar_valor_espessura(esp_valor)
            if abs(esp_padrao - esp_valor) < 0.001:
                continue  # já está no padrão, nada a fazer
            nome_padrao = f"{prefixo} [{str(esp_padrao).replace('.', ',')}]"
            caminho_variante = os.path.join(raiz, nome_pasta)
            caminho_padrao = os.path.join(raiz, nome_padrao)
            try:
                os.makedirs(caminho_padrao, exist_ok=True)
                for item in os.listdir(caminho_variante):
                    origem = os.path.join(caminho_variante, item)
                    destino = os.path.join(caminho_padrao, item)
                    if os.path.isdir(origem):
                        # ex: subpasta "Editar" dentro da pasta variante
                        os.makedirs(destino, exist_ok=True)
                        for sub_item in os.listdir(origem):
                            shutil.move(os.path.join(origem, sub_item), os.path.join(destino, sub_item))
                        os.rmdir(origem)
                    else:
                        shutil.move(origem, destino)
                os.rmdir(caminho_variante)
                dirs.remove(nome_pasta)
                log(f"🔀 Pasta variante consolidada: '{nome_pasta}' -> '{nome_padrao}'")
            except Exception as ex:
                log(f"⚠️  Não foi possível consolidar '{nome_pasta}': {ex}")
def _extrair_esp_material_pasta(nome):
    """
    Extrai (espessura, material) do nome de uma pasta de nível raiz da obra,
    aceitando tanto o formato "bruto" com underscore (ex: "6_35_A572-GR50",
    "3_CIVIL-300", vindo de fora do script) quanto o formato já canônico com
    vírgula e espaço (ex: "6,35 A572-GR50", "3,00 CIVIL-300", gerado por uma
    rodada anterior deste próprio script).
    Retorna (espessura: float, material: str) ou (None, None) se o nome não
    seguir nenhum desses padrões (ex: pastas de fluxo como "Fluxo 3 [4,75]",
    que não começam com um número de espessura).
    """
    nome = nome.strip()
    # Formato já canônico: "6,35 A572-GR50" ou só "6,35" (sem material)
    match_canonico = re.match(r'^(\d+),(\d+)(?:\s+(.*))?$', nome)
    if match_canonico:
        esp = float(f"{match_canonico.group(1)}.{match_canonico.group(2)}")
        material = (match_canonico.group(3) or "").strip()
        return esp, material
    # Formato bruto com underscore: "6_35_A572-GR50", "3_CIVIL-300", "6_35"
    partes = nome.split("_", 2)
    if len(partes) < 2:
        return None, None
    try:
        if partes[1].isdigit():
            esp = float(f"{partes[0]}.{partes[1]}")
            material = partes[2] if len(partes) > 2 else ""
        else:
            esp = float(partes[0])
            material = partes[1]
        return esp, material.strip()
    except (ValueError, IndexError):
        return None, None
def _normalizar_material_pasta(material):
    """
    Normaliza o texto do material (parte do nome da pasta que vem depois da
    espessura, ex: "ZAR 400 GALVANIZADO") para servir de CHAVE de comparação
    ao decidir se duas pastas são duplicadas - remove espaços duplicados e o
    espaço entre um bloco de letras e um bloco de números colados (ex:
    "ZAR 400" e "ZAR400" passam a comparar como iguais). Usada só para
    AGRUPAR pastas equivalentes; o nome de exibição final usa o texto
    original (o mais comum do grupo), não este texto normalizado.
    """
    texto = re.sub(r'\s+', ' ', (material or '').strip().upper())
    texto = re.sub(r'(?<=[A-Z])\s+(?=\d)', '', texto)
    texto = re.sub(r'(?<=\d)\s+(?=[A-Z])', '', texto)
    return texto
def padronizar_espessura(pasta_base):
    """
    Renomeia e MESCLA as pastas de nível raiz da obra (espessura + material,
    ex: "6_35_A572-GR50" ou já "6,35 A572-GR50") em uma única pasta canônica
    por combinação espessura+material, resolvendo duas fontes de pastas
    duplicadas na mesma obra:
    1) Espessura fora do padrão de catálogo (ex: "6,40" ou "4,80") é
       arredondada para o valor padrão mais próximo (padronizar_valor_espessura
       - "6,40" -> "6,35", "4,80" -> "4,75") - mesma lógica já usada nas
       pastas de fluxo em consolidar_pastas_variantes(), aplicada aqui às
       pastas de material.
    2) Diferenças cosméticas no texto do material (ex: "ZAR 400 GALVANIZADO"
       vs "ZAR400 GALVANIZADO" - só um espaço de diferença) são tratadas como
       a MESMA pasta (_normalizar_material_pasta).
    Quando duas ou mais pastas (originais ou já renomeadas em rodadas
    anteriores) mapeiam para a mesma combinação espessura+material
    padronizada, os arquivos de TODAS elas são movidos para uma única pasta
    de destino e as demais pastas (agora vazias) são excluídas.
    """
    grupos = defaultdict(list)  # (esp_padrao, chave_material) -> [(caminho, material_original), ...]
    for nome in os.listdir(pasta_base):
        caminho_atual = os.path.join(pasta_base, nome)
        if not os.path.isdir(caminho_atual):
            continue
        esp, material = _extrair_esp_material_pasta(nome)
        if esp is None:
            continue
        esp_padrao = padronizar_valor_espessura(esp)
        chave = (esp_padrao, _normalizar_material_pasta(material))
        grupos[chave].append((caminho_atual, material))
    for (esp_padrao, _chave_material), pastas_do_grupo in grupos.items():
        # Nome final: espessura padronizada + a grafia de material mais
        # comum do grupo (empate: a mais curta, tende a ser a grafia "limpa")
        contagem_material = defaultdict(int)
        for _caminho, material_original in pastas_do_grupo:
            contagem_material[material_original.strip()] += 1
        material_escolhido = max(contagem_material.items(), key=lambda par: (par[1], -len(par[0])))[0]
        novo_nome = f"{esp_padrao:.2f}".replace(".", ",")
        if material_escolhido:
            novo_nome += f" {material_escolhido}"
        novo_caminho = os.path.join(pasta_base, novo_nome)
        destino = novo_caminho if os.path.isdir(novo_caminho) else None
        for caminho_origem, _material_original in pastas_do_grupo:
            try:
                if destino is None:
                    if os.path.abspath(caminho_origem) != os.path.abspath(novo_caminho):
                        os.rename(caminho_origem, novo_caminho)
                        log(f"📁 Renomeado -> '{os.path.basename(caminho_origem)}' -> '{novo_nome}'")
                    destino = novo_caminho
                    continue
                if os.path.abspath(caminho_origem) == os.path.abspath(destino):
                    continue  # já é a própria pasta destino - nada a fazer
                for item in os.listdir(caminho_origem):
                    origem_item = os.path.join(caminho_origem, item)
                    destino_item = os.path.join(destino, item)
                    if os.path.isdir(origem_item):
                        # ex: subpasta "Fluxo 3 [4,75]" ou "Editar" já existente
                        os.makedirs(destino_item, exist_ok=True)
                        for sub_item in os.listdir(origem_item):
                            shutil.move(os.path.join(origem_item, sub_item), os.path.join(destino_item, sub_item))
                        os.rmdir(origem_item)
                    else:
                        shutil.move(origem_item, destino_item)
                os.rmdir(caminho_origem)
                log(f"📁 Mesclado -> '{os.path.basename(caminho_origem)}' -> '{novo_nome}' (pasta duplicada removida)")
            except Exception as ex:
                log(f"⚠️  Não foi possível padronizar/mesclar a pasta '{os.path.basename(caminho_origem)}': {ex}")
def processar_pastas_xadrez(pasta_base, planilha=None):
    """
    Pós-processamento específico para peças de CHAPA XADREZ (chapa
    antiderrapante em relevo) - baseado na mesma abordagem usada na
    roteirização de escada de marinheiro: varre pastas JÁ organizadas e
    move os DXFs encontrados nelas conforme uma regra própria, separada da
    roteirização normal (decidir_fluxo_peca).
    Procura, dentro de pasta_base, QUALQUER subpasta cujo nome contenha
    "XADREZ" (sem diferenciar maiúsculas/minúsculas) e, para cada DXF
    encontrado diretamente nela:
    - Peça IRREGULAR (qualquer recorte/formato que não seja uma chapa lisa
      simples - reaproveita possui_irregularidade(), a mesma análise usada
      na roteirização normal) -> vai para a subpasta "Banco de Corte" dentro
      da pasta de xadrez, MESMO tendo recortes (não vira Fluxo 3 como as
      demais peças irregulares - xadrez com recorte é sempre banco de corte).
    - Peça LISA (não irregular) -> Fluxo 1 se a maior dimensão (largura ou
      altura) for > 3000mm, senão Fluxo 2 - independente da largura (NÃO
      aplica o corte de 400mm usado nas demais categorias de Fluxo 1/2).
    Essa regra vale SOMENTE para peças de chapa xadrez (pastas com "xadrez"
    no nome) - não afeta o roteamento normal das demais peças/pastas.
    OBSERVAÇÃO DE DIMENSÕES (planilha):
    Se `planilha` for informada (o DataFrame já carregado da planilha
    CSV/Excel), além de aplicar a regra de roteamento acima, cada peça tem
    suas dimensões do DXF comparadas com as dimensões da planilha (LARGURA_N
    x DESENV_N/COMPR_N, mesma tolerância de 3mm usada no restante do script),
    e o resultado (OK ou DIVERGENTE) é registrado no log - isso é só uma
    OBSERVAÇÃO/registro adicional, não muda para onde a peça é movida.
    """
    if not os.path.isdir(pasta_base):
        return
    total_processado = 0
    for raiz, dirs, _ in os.walk(pasta_base):
        for nome_pasta in list(dirs):
            if "XADREZ" not in nome_pasta.upper():
                continue
            caminho_pasta_xadrez = os.path.join(raiz, nome_pasta)
            log(f"🔲 Processando peças de chapa xadrez em: {caminho_pasta_xadrez}")
            arquivos = [a for a in os.listdir(caminho_pasta_xadrez) if a.upper().endswith(".DXF")]
            for arq in arquivos:
                caminho_arquivo = os.path.join(caminho_pasta_xadrez, arq)
                if not os.path.exists(caminho_arquivo):
                    continue
                largura_dxf, altura_dxf = obter_dimensoes_dxf(caminho_arquivo)
                # ===== OBSERVAÇÃO: compara com a planilha, se disponível =====
                # Isso é feito ALÉM da regra de roteamento (não interfere nela) -
                # só registra no log se a dimensão do DXF bate com a da planilha.
                if planilha is not None and largura_dxf is not None and altura_dxf is not None:
                    of, pos = extrair_nome(arq)
                    if of:
                        filtro = buscar_posicao(planilha, of, pos)
                        if not filtro.empty:
                            linha_planilha = filtro.iloc[0]
                            largura_planilha = linha_planilha.get("LARGURA_N", None)
                            desenvolvimento_planilha = linha_planilha.get("DESENV_N", None)
                            comprimento_planilha = linha_planilha.get("COMPR_N", None)
                            if largura_planilha is not None and desenvolvimento_planilha is not None:
                                status_obs = comparar_dimensoes_com_tolerancia(
                                    largura_dxf, altura_dxf, largura_planilha,
                                    desenvolvimento_planilha, 3.0
                                )
                                if status_obs != "OK" and comprimento_planilha is not None:
                                    status_obs2 = comparar_dimensoes_com_tolerancia(
                                        largura_dxf, altura_dxf, largura_planilha,
                                        comprimento_planilha, 3.0
                                    )
                                    if status_obs2 == "OK":
                                        status_obs = "OK"
                                if status_obs == "OK":
                                    log(f"📐 OBSERVAÇÃO: {arq} - dimensão do DXF confere com a planilha "
                                        f"(DXF {largura_dxf:.1f}x{altura_dxf:.1f} | "
                                        f"Planilha {largura_planilha:.1f}x{desenvolvimento_planilha:.1f})")
                                else:
                                    log(f"⚠️  OBSERVAÇÃO: {arq} - dimensão do DXF DIVERGENTE da planilha "
                                        f"(DXF {largura_dxf:.1f}x{altura_dxf:.1f} | "
                                        f"Planilha {largura_planilha:.1f}x{desenvolvimento_planilha:.1f})")
                        else:
                            log(f"⚠️  OBSERVAÇÃO: {arq} - posição não encontrada na planilha para conferência de dimensão")
                # ===== REGRA DE ROTEAMENTO (não é afetada pela observação acima) =====
                irregular = possui_irregularidade(caminho_arquivo)
                if irregular:
                    pasta_destino = os.path.join(caminho_pasta_xadrez, "Banco de Corte")
                    os.makedirs(pasta_destino, exist_ok=True)
                    shutil.move(caminho_arquivo, os.path.join(pasta_destino, arq))
                    log(f"🔲 {arq} -> Banco de Corte (chapa xadrez irregular/com recorte)")
                    total_processado += 1
                    continue
                if largura_dxf is None or altura_dxf is None:
                    log(f"⚠️  Não foi possível obter dimensões de {arq} - peça de xadrez não roteirizada")
                    continue
                maior = max(largura_dxf, altura_dxf)
                fluxo = "Fluxo 1" if maior > 3000 else "Fluxo 2"
                pasta_destino = os.path.join(caminho_pasta_xadrez, fluxo)
                os.makedirs(pasta_destino, exist_ok=True)
                shutil.move(caminho_arquivo, os.path.join(pasta_destino, arq))
                log(f"🔲 {arq} -> {fluxo} (chapa xadrez lisa, maior dimensão={maior:.1f}mm)")
                total_processado += 1
    if total_processado:
        log(f"🔲 Total de peças de chapa xadrez pós-processadas: {total_processado}")
# ===== MÓDULO "VERIFICADOR" =====
# Depois que o roteirizador termina de organizar uma obra, salva um "retrato"
# (JSON) de em qual pasta cada arquivo ficou. Mais tarde, na aba Verificador,
# esse retrato é comparado com a organização ATUAL da mesma pasta para
# descobrir:
#   1) posições que JÁ tinham fluxo, mas foram movidas manualmente pra outro
#      fluxo depois (o código tinha uma regra, mas roteirizou errado);
#   2) posições que ficaram FORA de qualquer pasta de fluxo (não existe regra
#      pra elas) - e, quando o usuário move essas peças manualmente pra dentro
#      de um fluxo depois, o Verificador identifica isso e pede o motivo.
# Em ambos os casos, ao descrever o motivo e salvar, o ajuste vira permanente
# na memória (SQLite) e passa a valer pra qualquer obra futura com a mesma
# posição/identificador.
NOME_LOG_ROTEIRIZACAO = "_log_roteirizacao_projeart.json"
# Nomes de subpastas "auxiliares" que não representam um fluxo em si (ex:
# peças grandes demais viram "Fluxo X [esp]/Editar"; xadrez irregular vira
# ".../XADREZ/Banco de Corte") - ao detectar em qual pasta um arquivo está, se
# ele estiver dentro de uma dessas, a pasta considerada é a pasta PAI dela.
_SUBPASTAS_AUXILIARES_FLUXO = {"editar", "banco de corte"}
# Uma pasta só é considerada "pasta de FLUXO de verdade" se o nome dela
# começar com um desses prefixos (ex: "Fluxo 3 [6,35]", "Perfiladeira L
# [4,75]", "Terça Z [3,00]"). Qualquer outra pasta (tipicamente a pasta de
# espessura/material, tipo "6,35 A572-GR50" ou "1,95 ZAR 400 GALVANIZADO") NÃO
# é um fluxo - é só onde as peças ficam esperando até serem roteirizadas. Essa
# checagem por NOME (em vez de contar níveis de pasta) funciona não importa se
# o usuário aponta o Roteirizador pra pasta raiz (com várias espessuras) ou
# direto pra uma pasta de espessura específica.
_PREFIXOS_NOME_DE_FLUXO = (
    "fluxo ", "terça z", "terca z", "perfiladeira u e c", "perfiladeira l",
    "acessórios padrão", "acessorios padrao", "joist ", "laser",
)
def _nome_parece_fluxo(nome):
    """Diz se `nome` (nome de uma pasta) é uma pasta de fluxo de verdade."""
    if not nome:
        return False
    nome_normalizado = nome.strip().lower()
    return any(nome_normalizado.startswith(prefixo) for prefixo in _PREFIXOS_NOME_DE_FLUXO)
def _detectar_pasta_por_caminho(caminho_arquivo, pasta_base):
    """
    Descobre o nome da pasta onde um arquivo DXF está, a partir do caminho
    completo dele e da pasta raiz da obra. Se o arquivo estiver dentro de uma
    subpasta auxiliar (ex: "Editar", "Banco de Corte"), considera a pasta PAI
    dela, não o nome da subpasta auxiliar em si.
    """
    pasta_arquivo = os.path.dirname(caminho_arquivo)
    caminho_relativo = os.path.relpath(pasta_arquivo, pasta_base)
    partes = [p for p in caminho_relativo.split(os.sep) if p not in ("", ".")]
    if not partes:
        return None
    ultima = partes[-1]
    if ultima.strip().lower() in _SUBPASTAS_AUXILIARES_FLUXO and len(partes) >= 2:
        return partes[-2]
    return ultima
def _mapear_arquivos_por_pasta(pasta_base):
    """Varre a pasta da obra e devolve, para cada DXF encontrado, em qual
    pasta ele está agora e o nome dessa pasta."""
    mapa = {}
    for raiz, _dirs, arquivos in os.walk(pasta_base):
        for arq in arquivos:
            if not arq.upper().endswith(".DXF"):
                continue
            mapa[arq] = {
                "pasta_nome": _detectar_pasta_por_caminho(os.path.join(raiz, arq), pasta_base),
                "pasta_atual": raiz,
            }
    return mapa
def _ocultar_arquivo_windows(caminho):
    """
    Marca o arquivo como OCULTO no Windows (atributo de sistema de arquivos,
    não é só o nome começar com "_") - assim ele não aparece no Explorer por
    padrão, sem atrapalhar quem está vendo a pasta da obra. Não faz nada (e
    não gera erro) se não estiver rodando no Windows.
    """
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(caminho), FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass  # não é Windows, ou por algum motivo não deu pra marcar - sem problema


def _mostrar_arquivo_windows(caminho):
    """Tira o atributo OCULTO (necessário pra regravar: no Windows, abrir um arquivo oculto com "w" dá
    PermissionError - por isso o retrato só gravava na 1ª roteirização e depois falhava em silêncio)."""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(str(caminho), 0x80)      # FILE_ATTRIBUTE_NORMAL
    except Exception:
        pass


def _gravar_json_oculto(caminho, payload):
    """Grava o JSON do retrato: destrava (se estava oculto), grava e oculta de novo. Levanta a exceção se não gravar."""
    existia = os.path.exists(caminho)
    if existia:
        _mostrar_arquivo_windows(caminho)
    try:
        with open(caminho, "w", encoding="utf-8") as arquivo_log:
            json.dump(payload, arquivo_log, ensure_ascii=False, indent=2)
    finally:
        _ocultar_arquivo_windows(caminho)


def salvar_log_roteirizacao(pasta_base, dxfs_encontrados):
    """
    Salva, dentro de `pasta_base`, um retrato de em qual pasta cada peça
    roteirizada (lista `dxfs_encontrados`, vinda de processar()) ficou -
    depois de padronizar_espessura/consolidar_pastas_variantes/
    processar_pastas_xadrez terem rodado, ou seja, no estado FINAL da
    roteirização automática, antes de qualquer ajuste manual do usuário.
    Sobrescreve o log anterior dessa mesma pasta a cada rodada. O arquivo é
    marcado como OCULTO - fica lá pra uso interno do Verificador, mas não
    aparece pra quem está navegando na pasta da obra.
    """
    try:
        mapa_atual = _mapear_arquivos_por_pasta(pasta_base)
        itens = []
        for item in dxfs_encontrados:
            arq = item.get("arquivo")
            info = mapa_atual.get(arq)
            if not info:
                continue  # arquivo não foi encontrado na pasta - nada pra registrar
            itens.append({
                "of": item.get("of"),
                "pos": item.get("pos"),
                "identificador": item.get("identificador"),
                "arquivo": arq,
                "espessura": item.get("espessura"),
                "pasta_no_snapshot": info["pasta_nome"],
            })
        preservar = _MANUAIS_PRESERVAR.get(os.path.abspath(pasta_base)) or {}
        for it in itens:                    # movido à mão e mantido: o retrato guarda a escolha ORIGINAL do programa (o Verificador pede o motivo)
            if it["arquivo"] in preservar and preservar[it["arquivo"]]:
                it["pasta_no_snapshot"] = preservar[it["arquivo"]]
        payload = {
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "itens": itens,
        }
        caminho_log = os.path.join(pasta_base, NOME_LOG_ROTEIRIZACAO)
        _gravar_json_oculto(caminho_log, payload)
        log(f"🧾 Log de roteirização salvo (oculto, {len(itens)} peça(s)) - usado depois na aba Verificador.")
    except Exception as ex:
        log(f"⚠️  Não foi possível salvar o log de roteirização para o Verificador: {ex}")
def _localizar_pasta_com_log(pasta_inicial, max_niveis_acima=6):
    """
    Procura o log a partir de `pasta_inicial`, subindo pelas pastas PAI se não
    achar direto nela - útil quando o usuário aponta o Verificador para uma
    subpasta (ex: uma pasta de espessura específica) em vez da pasta principal
    da obra usada no Roteirizador (é lá que o log fica salvo).
    """
    atual = os.path.abspath(pasta_inicial)
    for _ in range(max_niveis_acima + 1):
        if os.path.isfile(os.path.join(atual, NOME_LOG_ROTEIRIZACAO)):
            return atual
        pasta_pai = os.path.dirname(atual)
        if pasta_pai == atual:
            break
        atual = pasta_pai
    return None
def atualizar_entrada_log_roteirizacao(pasta_base, arquivo, novo_fluxo):
    """
    Depois que o usuário resolve uma divergência pelo Verificador (grava o
    ajuste na memória), atualiza também o log salvo em disco pra refletir o
    novo fluxo - assim esse item não volta a aparecer numa próxima
    verificação, mesmo depois de fechar e abrir o programa de novo.
    """
    caminho_log = os.path.join(pasta_base, NOME_LOG_ROTEIRIZACAO)
    if not os.path.isfile(caminho_log):
        return
    try:
        with open(caminho_log, "r", encoding="utf-8") as arquivo_log:
            payload = json.load(arquivo_log)
        mudou = False
        for item in payload.get("itens", []):
            if item.get("arquivo") == arquivo:
                item["pasta_no_snapshot"] = novo_fluxo
                mudou = True
        if mudou:
            _gravar_json_oculto(caminho_log, payload)
    except Exception as ex:
        log(f"⚠️  Não foi possível atualizar o log de roteirização após o ajuste: {ex}")
def comparar_roteirizacao_com_atual(pasta_base):
    """
    Compara o log salvo por salvar_log_roteirizacao() com a organização ATUAL
    da mesma pasta. Retorna None se não achar log em nenhum nível (nem
    subindo pelas pastas pai). Caso contrário, retorna um dict:
      - 'divergencias': posições cuja pasta atual é diferente da pasta em que
        estavam quando a roteirização terminou - foram movidas manualmente
        depois (falta só motivo + salvar).
      - 'nao_encontrados': itens do log cujo arquivo não foi mais encontrado.
      - 'pasta_log': pasta onde o log foi realmente encontrado (pode ser uma
        pasta PAI da que foi informada).
    """
    pasta_log = _localizar_pasta_com_log(pasta_base)
    if pasta_log is None:
        return None
    caminho_log = os.path.join(pasta_log, NOME_LOG_ROTEIRIZACAO)
    try:
        with open(caminho_log, "r", encoding="utf-8") as arquivo_log:
            payload = json.load(arquivo_log)
    except Exception as ex:
        log(f"⚠️  Não foi possível ler o log de roteirização em '{pasta_log}': {ex}")
        return None
    itens_log = payload.get("itens", [])
    mapa_atual = _mapear_arquivos_por_pasta(pasta_log)
    divergencias = []
    nao_encontrados = []
    for item in itens_log:
        arq = item.get("arquivo")
        info_atual = mapa_atual.get(arq)
        if info_atual is None:
            nao_encontrados.append(item)
            continue
        pasta_atual_nome = info_atual["pasta_nome"]
        fluxo_original = item.get("pasta_no_snapshot")
        if pasta_atual_nome != fluxo_original:
            divergente = dict(item)
            divergente["fluxo_atual"] = pasta_atual_nome
            divergente["pasta_base"] = pasta_log
            divergencias.append(divergente)
    return {
        "divergencias": divergencias,
        "nao_encontrados": nao_encontrados,
        "pasta_log": pasta_log,
        "gerado_em": payload.get("gerado_em", ""),
        "total": len(itens_log),
    }


def _localizar_logs_abaixo(pasta_inicial, max_niveis=4):
    """Pastas ABAIXO de `pasta_inicial` que têm o retrato (o usuário apontou uma pasta que contém várias obras)."""
    achadas = []
    base = os.path.abspath(pasta_inicial)
    nivel_base = base.rstrip(os.sep).count(os.sep)
    for raiz, dirs, arquivos in os.walk(base):
        if NOME_LOG_ROTEIRIZACAO in arquivos:
            achadas.append(raiz)
            dirs[:] = []                              # não precisa descer mais dentro de uma obra
            continue
        if raiz.rstrip(os.sep).count(os.sep) - nivel_base >= max_niveis:
            dirs[:] = []
    return achadas


def comparar_roteirizacoes_da_pasta(pasta):
    """Como comparar_roteirizacao_com_atual, mas aceita também uma pasta que CONTÉM várias obras: devolve uma
    lista de resultados (um por retrato achado — acima, na própria pasta ou abaixo dela). Lista vazia = sem retrato."""
    r = comparar_roteirizacao_com_atual(pasta)
    if r is not None:
        return [r]
    resultados = []
    for sub in _localizar_logs_abaixo(pasta):
        r = comparar_roteirizacao_com_atual(sub)
        if r is not None:
            resultados.append(r)
    return resultados
def conferir_pasta_com_regras(planilha, pasta, progresso=None):
    """VERIFICADOR - CONFERÊNCIA SOMENTE LEITURA. Roda as mesmas regras do Roteirizador (processar em modo simulação) sobre
    os DXF que estão em `pasta` e devolve (divergentes, total_conferido): lista de dicts das peças cuja pasta atual NÃO é
    a que a regra manda. Não move nada, não cria pasta, não grava retrato e não depende de a obra ter sido roteirizada
    por este programa (serve para pasta organizada à mão ou por outra versão). Aceita apontar direto para uma pasta de
    fluxo (usa a pasta pai como base e mostra só o que está dentro da escolhida)."""
    pasta = os.path.normpath(pasta)
    base, so_dentro = pasta, None
    if _nome_parece_fluxo(os.path.basename(pasta)) or os.path.basename(pasta).strip().lower() in _SUBPASTAS_AUXILIARES_FLUXO:
        base, so_dentro = os.path.dirname(pasta), pasta
        if os.path.basename(base).strip().lower() and _nome_parece_fluxo(os.path.basename(base)):
            base = os.path.dirname(base)
    sim = []
    resultado = processar(planilha, base, simulacao=sim)
    total = len(resultado[0])
    if so_dentro:
        pref = so_dentro + os.sep
        sim = [d for d in sim if os.path.normpath(d["caminho"]).startswith(pref)]
    sim.sort(key=lambda d: (str(d.get("of")), str(d.get("pos")), str(d.get("arquivo"))))
    return sim, total


def _extrair_espessura_de_pasta(nome_pasta):
    """Tenta extrair a espessura numérica a partir do nome de uma pasta de
    espessura/material (ex: '1,95 ZAR 400 GALVANIZADO' -> 1.95). Retorna None
    se o nome não começar com um número no formato "0,00"."""
    if not nome_pasta:
        return None
    match = re.match(r'^(\d+),(\d+)', nome_pasta.strip())
    if not match:
        return None
    try:
        return float(f"{match.group(1)}.{match.group(2)}")
    except Exception:
        return None
def detectar_pecas_fora_do_fluxo(pasta_base, planilha=None):
    """
    Varre `pasta_base` de verdade (depois de toda a roteirização/padronização
    já ter rodado) e lista TODO arquivo .DXF que esteja fora de uma pasta de
    fluxo de verdade (ver _nome_parece_fluxo) - não importa se essa peça foi
    encontrada e combinada com a planilha durante o processar() ou não.
    Isso cobre tanto peças sem regra no código quanto arquivos cujo nome nem
    bateu com nenhuma linha da planilha (por isso passaram batido pelo
    processar() sem gerar nenhum aviso na tela).
    Quando possível, enriquece o item com os dados reais da planilha (OF,
    posição, identificador, espessura); quando não é possível encontrar a
    linha correspondente, usa o que dá pra extrair do próprio nome do arquivo.
    """
    resultado = []
    mapa = _mapear_arquivos_por_pasta(pasta_base)
    for arq, info in mapa.items():
        if _nome_parece_fluxo(info["pasta_nome"]):
            continue  # está dentro de uma pasta de fluxo de verdade - ok
        of_extraido, pos_extraido = extrair_nome(arq)
        of_final = of_extraido or ""
        pos_final = pos_extraido or ""
        identificador = ""
        espessura = None
        if planilha is not None and of_extraido:
            try:
                filtro = buscar_posicao(planilha, of_extraido, pos_extraido)
            except Exception:
                filtro = None
            if filtro is not None and not filtro.empty:
                linha = filtro.iloc[0]
                identificador = linha.get("ID_N", "") or ""
                pos_final = linha.get("POS_N", pos_final) or pos_final
                of_final = linha.get("OF_N", of_final) or of_final
                espessura = linha.get("ESP_N", None)
        if espessura is None:
            espessura = _extrair_espessura_de_pasta(info["pasta_nome"])
        resultado.append({
            "of": of_final,
            "pos": pos_final,
            "identificador": identificador,
            "arquivo": arq,
            "espessura": espessura,
            "pasta_atual": info["pasta_atual"],
        })
    return resultado
def _peca_nao_gera_cam(identificador):
    """
    Verifica se o IDENTIFICADOR corresponde a um item que nunca gera DXF/CAM
    (ex: BR = barra, TB = tubo - cortados por serra, não por laser/plasma).
    Usa o mesmo estilo de remoção de prefixo de obra/número já usado em
    verificar_prefixo(), para não confundir com posições parecidas.
    """
    if not identificador:
        return False
    id_upper = str(identificador).upper().strip()
    return any(id_upper.startswith(p) for p in PREFIXOS_SEM_CAM)
# ===== TEMA VISUAL COMPARTILHADO DAS TELAS (Tkinter) - NEON FUTURISTA =====
# ===== PADRÃO VISUAL PROJEART (o mesmo dos sistemas web da empresa) =====
# menu lateral azul-marinho #0B1D3A, destaque #2E6AAD, fundo #F1F5FA, cartões brancos com borda #DFE6EF,
# cabeçalho de tabela azul-marinho. (Os nomes "_NEON_*" foram mantidos só para não mexer no resto do código.)
_COR_MARINHO = "#0B2150"          # menu lateral, títulos, cabeçalho de tabela
_COR_PAGINA = "#EEF1F5"           # fundo da página (em volta dos cartões)
_COR_FUNDO = "#FFFFFF"            # fundo dos cartões / conteúdo
_COR_PAINEL = "#F6F7F9"           # painéis internos (zebra, caixas de texto)
_COR_PAINEL_2 = "#EEF1F5"         # painéis secundários
_COR_TEXTO = "#000000"
_COR_TEXTO_SEC = "#4B5563"
_COR_DESTAQUE = "#0B3D91"         # azul de destaque (botão primário, item ativo do menu)
_COR_DESTAQUE_HOVER = "#082E6E"
_COR_OK = "#1E9E4A"
_COR_ALERTA = "#C62828"
_COR_INFO = "#0B3D91"
_COR_AVISO = "#EA580C"
_COR_BORDA = "#C9D0D8"
_COR_BORDA_CAMPO = "#98A3B3"
_NEON_CIANO = "#0B3D91"
_NEON_CIANO_SUAVE = "#0B3D91"
_NEON_ROSA = "#C2549B"
_NEON_VERDE = "#1F9D55"
_NEON_ROXO = "#6B4FBB"
_NEON_AMARELO = "#B7791F"
_COR_SOBRE_NEON = "#FFFFFF"       # texto sobre o azul de destaque
_FONTE_TITULO = "Segoe UI"       # trocada por "Bahnschrift" (Windows 10+) se existir
# Paleta de cores usada no gráfico/tabela de "⚖️ Peso por Fluxo".
_PALETA_CORES_FLUXO = [
    "#2E6AAD", "#1F9D55", "#D64545", "#C98A12", "#6B4FBB",
    "#1B8EA6", "#7A9A1E", "#C2549B", "#4F5FD6", "#17A589",
    "#D9722B", "#3E4FB5", "#5E8F1E", "#B58B00", "#2D9C72", "#B8489A",
]
_FLUXOS_BASE_DISPONIVEIS = [
    "Fluxo 1", "Fluxo 2", "Fluxo 3", "Fluxo 4",
    "Perfiladeira L", "Perfiladeira L1", "Perfiladeira L2", "Perfiladeira U e C", "Acessórios Padrão",
    "Terça Z", "Joist", "LASER",
]
def _cor_para_fluxo(nome_fluxo):
    """Mantém a cor estável de cada fluxo entre execuções."""
    indice = zlib.crc32(nome_fluxo.encode("utf-8")) % len(_PALETA_CORES_FLUXO)
    return _PALETA_CORES_FLUXO[indice]
def formatar_numero_br(valor, decimais=1):
    """Formata número no padrão brasileiro."""
    texto = f"{valor:,.{decimais}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")
def _ativar_dpi_awareness():
    """Deixa o Windows renderizar a janela em resolução nativa (sem esticar a
    imagem) - é o que faz textos e ícones ficarem nítidos em telas com escala
    de 125%/150%. Precisa ser chamado ANTES de criar a janela."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
def _aplicar_estilo_base(janela):
    """
    Tema visual PADRÃO PROJEART (claro): fundo #F1F5FA, cartões brancos com borda #DFE6EF, azul-marinho #0B1D3A,
    destaque #2E6AAD, cabeçalho de tabela azul-marinho. Altera somente a aparência dos widgets.
    """
    global _FONTE_TITULO
    try:
        import tkinter.font as tkfont
        familias = set(tkfont.families(janela))
        for candidata in ("Lexend", "Segoe UI Semibold", "Segoe UI"):
            if candidata in familias:
                _FONTE_TITULO = candidata
                break
    except Exception:
        pass
    F = _FONTE_TITULO
    style = ttk.Style(janela)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    # ---- Configuração global do Tk ----
    # fonte padrão pelos "fontes nomeadas" do Tk (e não por option_add "*Font", que sobrescreve a fonte dos estilos ttk
    # e deixava os títulos das telas com o tamanho do texto comum)
    try:
        import tkinter.font as tkfont
        for _nome_fonte in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            tkfont.nametofont(_nome_fonte).configure(family="Segoe UI", size=10)
    except Exception:
        pass
    janela.option_add("*TButton.cursor", "hand2")
    janela.option_add("*TCheckbutton.cursor", "hand2")
    janela.option_add("*TCombobox*Listbox.background", "#FFFFFF")
    janela.option_add("*TCombobox*Listbox.foreground", _COR_TEXTO)
    janela.option_add("*TCombobox*Listbox.selectBackground", "#DBE8FB")
    janela.option_add("*TCombobox*Listbox.selectForeground", "#000000")
    # ---- Containers ----
    style.configure("TFrame", background=_COR_FUNDO)
    style.configure("Painel.TFrame", background=_COR_PAINEL)
    style.configure("Cartao.TFrame", background=_COR_PAINEL_2)
    # ---- Textos ----
    style.configure("TLabel", background=_COR_FUNDO, foreground=_COR_TEXTO, font=("Segoe UI", 10))
    style.configure("Titulo.TLabel", background=_COR_FUNDO, foreground=_COR_MARINHO, font=(F, 20, "bold"))
    style.configure("Subtitulo.TLabel", background=_COR_FUNDO, foreground=_COR_TEXTO_SEC, font=("Segoe UI", 10))
    style.configure("Secao.TLabel", background=_COR_FUNDO, foreground=_COR_MARINHO, font=(F, 10, "bold"))
    # ---- Entradas (a borda fica azul ao focar) ----
    style.configure("TEntry", fieldbackground="#FFFFFF", foreground=_COR_TEXTO, insertcolor=_COR_DESTAQUE,
                    bordercolor=_COR_BORDA_CAMPO, lightcolor=_COR_BORDA_CAMPO, darkcolor=_COR_BORDA_CAMPO,
                    borderwidth=1, padding=(10, 7), relief="flat")
    style.map("TEntry",
              fieldbackground=[("disabled", "#F1F5FA"), ("focus", "#FFFFFF")],
              foreground=[("disabled", "#8A97AB")],
              bordercolor=[("focus", _COR_DESTAQUE)], lightcolor=[("focus", _COR_DESTAQUE)],
              darkcolor=[("focus", _COR_DESTAQUE)])
    # ---- Botões: secundário branco com borda; primário azul #2E6AAD ----
    style.configure("TButton", background="#D8DEE6", foreground="#000000",
                    bordercolor=_COR_BORDA_CAMPO, lightcolor=_COR_BORDA_CAMPO, darkcolor=_COR_BORDA_CAMPO,
                    focuscolor="#D8DEE6", borderwidth=1, padding=(13, 7), font=(F, 9, "bold"), relief="solid")
    style.map("TButton",
              background=[("pressed", "#BFC8D4"), ("active", "#C9D1DC"), ("disabled", "#E3E8EE")],
              foreground=[("disabled", "#9AA8BD")],
              bordercolor=[("disabled", "#C9D0D8"), ("active", "#808C9E"), ("pressed", "#808C9E")],
              lightcolor=[("disabled", "#C9D0D8"), ("active", "#808C9E"), ("pressed", "#808C9E")],
              darkcolor=[("disabled", "#C9D0D8"), ("active", "#808C9E"), ("pressed", "#808C9E")])
    style.configure("Destaque.TButton", background="#D8DEE6", foreground="#000000",
                    bordercolor="#98A3B3", lightcolor="#98A3B3", darkcolor="#98A3B3",
                    focuscolor="#D8DEE6", font=(F, 10, "bold"), padding=(18, 9), borderwidth=1, relief="solid")
    style.map("Destaque.TButton",
              background=[("pressed", "#BFC8D4"), ("active", "#C9D1DC"), ("disabled", "#E3E8EE")],
              foreground=[("disabled", "#8A929E")],
              bordercolor=[("disabled", "#C9D0D8"), ("active", "#808C9E")],
              lightcolor=[("disabled", "#C9D0D8"), ("active", "#808C9E")],
              darkcolor=[("disabled", "#C9D0D8"), ("active", "#808C9E")])
    style.configure("Perigo.TButton", background=_COR_ALERTA, foreground="#FFFFFF",
                    bordercolor=_COR_ALERTA, lightcolor=_COR_ALERTA, darkcolor=_COR_ALERTA, focuscolor=_COR_ALERTA,
                    font=(F, 9, "bold"), padding=(13, 7), borderwidth=1, relief="solid")
    style.map("Perigo.TButton",
              background=[("pressed", "#B93636"), ("active", "#E25C5C"), ("disabled", "#EBC0C0")],
              foreground=[("disabled", "#FFFFFF")],
              bordercolor=[("disabled", "#EBC0C0"), ("active", "#E25C5C")],
              lightcolor=[("disabled", "#EBC0C0"), ("active", "#E25C5C")],
              darkcolor=[("disabled", "#EBC0C0"), ("active", "#E25C5C")])
    style.configure("Secundario.TButton", background="#D8DEE6", foreground="#000000",
                    bordercolor=_COR_BORDA_CAMPO, lightcolor=_COR_BORDA_CAMPO, darkcolor=_COR_BORDA_CAMPO,
                    focuscolor="#D8DEE6", font=(F, 9, "bold"), padding=(12, 7), borderwidth=1, relief="solid")
    style.map("Secundario.TButton",
              background=[("pressed", "#BFC8D4"), ("active", "#C9D1DC"), ("disabled", "#E3E8EE")],
              foreground=[("disabled", "#9AA8BD")],
              bordercolor=[("disabled", "#C9D0D8"), ("active", "#808C9E")],
              lightcolor=[("disabled", "#C9D0D8"), ("active", "#808C9E")],
              darkcolor=[("disabled", "#C9D0D8"), ("active", "#808C9E")])
    # ---- Combobox / Checkbutton / Radiobutton ----
    style.configure("TCombobox", fieldbackground="#FFFFFF", background="#FFFFFF", foreground=_COR_TEXTO,
                    arrowcolor=_COR_DESTAQUE, bordercolor=_COR_BORDA_CAMPO, lightcolor=_COR_BORDA_CAMPO,
                    darkcolor=_COR_BORDA_CAMPO, padding=(8, 6))
    style.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")],
              bordercolor=[("focus", _COR_DESTAQUE)], lightcolor=[("focus", _COR_DESTAQUE)],
              darkcolor=[("focus", _COR_DESTAQUE)],
              selectbackground=[("readonly", "#FFFFFF")], selectforeground=[("readonly", _COR_TEXTO)])
    style.configure("TCheckbutton", background=_COR_FUNDO, foreground=_COR_TEXTO, font=("Segoe UI", 9))
    style.map("TCheckbutton", background=[("active", _COR_FUNDO)], foreground=[("disabled", "#8A97AB")])
    style.configure("TRadiobutton", background=_COR_FUNDO, foreground=_COR_TEXTO)
    style.map("TRadiobutton", background=[("active", _COR_FUNDO)])
    # ---- Tabelas: cabeçalho azul-marinho com texto branco ----
    style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF", foreground=_COR_TEXTO,
                    rowheight=30, font=("Segoe UI", 9), borderwidth=1, relief="flat",
                    bordercolor=_COR_BORDA, lightcolor=_COR_BORDA, darkcolor=_COR_BORDA)
    style.configure("Treeview.Heading", background="#D5DBE3", foreground="#000000",
                    font=(F, 9, "bold"), padding=(8, 8), borderwidth=0)
    style.map("Treeview", background=[("selected", "#DBE8FB")], foreground=[("selected", "#000000")])
    style.map("Treeview.Heading", background=[("active", "#C2CAD5")])
    # ---- Abas ----
    # A navegação principal é o MENU LATERAL: o Notebook principal esconde as próprias abas.
    style.layout("Principal.TNotebook.Tab", [])
    style.configure("Principal.TNotebook", background=_COR_FUNDO, borderwidth=1, tabmargins=0,
                    bordercolor=_COR_BORDA, lightcolor=_COR_BORDA, darkcolor=_COR_BORDA)
    # sub-abas das telas (Divergências etc.): abas claras, a ativa fica branca com faixa azul
    style.configure("TNotebook", background=_COR_FUNDO, borderwidth=1, tabmargins=(0, 4, 0, 0),
                    bordercolor=_COR_BORDA, lightcolor=_COR_BORDA, darkcolor=_COR_BORDA)
    style.configure("TNotebook.Tab", background="#D8DEE6", foreground="#000000", padding=(16, 8),
                    borderwidth=1, bordercolor=_COR_BORDA, lightcolor=_COR_BORDA, darkcolor=_COR_BORDA,
                    font=(F, 9, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", "#FFFFFF"), ("active", "#C9D1DC")],
              foreground=[("selected", _COR_MARINHO), ("active", _COR_MARINHO)],
              bordercolor=[("selected", _COR_DESTAQUE), ("active", _COR_BORDA_CAMPO)],
              lightcolor=[("selected", _COR_DESTAQUE)], darkcolor=[("selected", "#FFFFFF")],
              expand=[("selected", (0, 2, 0, 0))])
    # ---- Separadores, barras de rolagem e progresso ----
    style.configure("TSeparator", background=_COR_BORDA)
    for orient, grude in (("Vertical", "ns"), ("Horizontal", "we")):
        estilo = f"{orient}.TScrollbar"
        try:  # barra fina: só o "polegar" (sem as setas), fica azul ao passar o mouse
            style.layout(estilo, [(f"{orient}.Scrollbar.trough", {"sticky": grude, "children": [
                (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        except tk.TclError:
            pass
        style.configure(estilo, background="#BFCCDF", troughcolor="#EEF3F9", borderwidth=0,
                        bordercolor="#EEF3F9", lightcolor="#BFCCDF", darkcolor="#BFCCDF",
                        arrowcolor=_COR_DESTAQUE, width=10, gripcount=0, relief="flat")
        style.map(estilo, background=[("pressed", _COR_DESTAQUE), ("active", "#8FA9C9")],
                  lightcolor=[("pressed", _COR_DESTAQUE), ("active", "#8FA9C9")],
                  darkcolor=[("pressed", _COR_DESTAQUE), ("active", "#8FA9C9")])
    style.configure("TProgressbar", troughcolor="#E4EAF2", background=_COR_DESTAQUE,
                    bordercolor=_COR_BORDA, lightcolor=_COR_DESTAQUE, darkcolor=_COR_DESTAQUE)
    return style
def _criar_tabela_somente_leitura(pai, itens):
    """Cria uma Treeview simples (sem seleção/ação) para as abas de referência do relatório."""
    colunas = ("of", "tipo", "pos", "id")
    tree = ttk.Treeview(pai, columns=colunas, show="headings", height=14)
    tree.heading("of", text="OF")
    tree.heading("tipo", text="Tipo")
    tree.heading("pos", text="Posição")
    tree.heading("id", text="Identificador")
    tree.column("of", width=140, anchor="w")
    tree.column("tipo", width=140, anchor="w")
    tree.column("pos", width=120, anchor="w")
    tree.column("id", width=320, anchor="w")
    scroll = ttk.Scrollbar(pai, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="left", fill="y")
    if not itens:
        tree.insert("", "end", values=("", "Nenhum item", "", ""))
    else:
        for it in itens:
            tree.insert("", "end", values=(it["of"], it["tipo"], it["pos"], it["identificador"]))
    return tree
def analisar_divergencias(planilha, dxfs_encontrados, ofs_encontradas, ignorados_memoria=None, analise_dimensoes=None):
    """
    Compara o que consta na planilha com o que foi efetivamente encontrado
    entre os arquivos DXF, para as OFs processadas nesta rodada, e devolve
    os dados prontos para exibição na tela (relatório de divergências).
    Um item da planilha é considerado "FALTANTE" quando não há nenhum DXF
    correspondente (mesma OF + POSIÇÃO + IDENTIFICADOR) entre os processados -
    EXCETO:
    - itens cujo IDENTIFICADOR começa com um prefixo de PREFIXOS_SEM_CAM
      (BR = barra, TB = tubo) - esses nunca geram DXF/CAM - SALVO se a
      posição estiver marcada na memória (forcar_cam) para desconsiderar essa
      regra automática;
    - itens marcados na memória (SQLite, ignorados_memoria) como "não gera
      DXF mesmo" - aprendido de rodadas anteriores, em qualquer obra.
    Nenhum dos dois entra na lista de divergências - aparecem à parte, só
    para conferência/transparência.
    Também monta a lista "[PADRÃO] PLANILHA": itens que o usuário moveu
    MANUALMENTE para lá na aba de Faltantes (memória padrao_planilha_manual) -
    peças que o usuário já sabe que seguem regra própria e por ora não geram
    DXF individual. IMPORTANTE: essa marcação manual NÃO é uma exclusão
    definitiva como marcar_ignorado() - a checagem de "chave in dxf_chaves"
    abaixo tem prioridade máxima, então se em uma rodada futura aparecer um
    DXF de verdade para essa posição (ex: uma liberação nova gerou CAM para
    ela), o roteirizador encontra e processa normalmente, sem interferência
    desta marcação.
    Itens cujo IDENTIFICADOR já é classificado como "IGNORADO" pelo PRÓPRIO
    CÓDIGO em extrair_tipo_identificador (Terças Z sem DXF próprio, BR_RED,
    W_, PS) NÃO entram em "[PADRÃO] PLANILHA" - vão direto para "🧠 Ignorados"
    junto com os itens marcados manualmente via memória (ignorados_memoria),
    já que em ambos os casos o próprio roteirizador já sabe que não há CAM
    para eles, sem precisar de decisão do usuário.
    Também monta a lista de "📐 Divergência de Tamanho": peças cuja dimensão
    do DXF não bate com a da planilha fora da tolerância (analise_dimensoes,
    gerada em processar()), excluindo as que o usuário já marcou como
    conferidas/aceitas (memória divergencias_tamanho_ignoradas).
    """
    ignorados_memoria = ignorados_memoria or {}
    analise_dimensoes = analise_dimensoes or []
    forcar_cam_memoria = carregar_forcar_cam()
    divergencias_tamanho_ignoradas_memoria = carregar_divergencias_tamanho_ignoradas()
    padrao_planilha_manual_memoria = carregar_padrao_planilha_manual()
    planilha_relevante = planilha[planilha["OF_N"].isin(ofs_encontradas)] if ofs_encontradas else planilha.iloc[0:0]
    dxf_chaves = {
        f"{item['of']}|{item['pos']}|{item['identificador']}"
        for item in dxfs_encontrados
    }
    # ===== DEDUPLICAÇÃO: a mesma peça (OF+POSIÇÃO+IDENTIFICADOR) pode aparecer
    # em VÁRIAS linhas da planilha (ex: cortada em mais de uma instância/
    # desenho, ou a soma de quantidade vem de múltiplas linhas) - por isso
    # cada peça é contada UMA ÚNICA VEZ aqui (por chave), nunca por linha
    # crua da planilha. Itens "IGNORADO" NÃO são descartados aqui (diferente
    # de antes) - eles são tratados abaixo como "🧠 Ignorados" em vez de
    # ficarem completamente invisíveis no relatório.
    itens_unicos = {}
    for _, row in planilha_relevante.iterrows():
        identificador = row.get("ID_N", "")
        posicao = row.get("POS_N", "")
        of = row.get("OF_N", "")
        tipo = extrair_tipo_identificador(identificador, posicao)
        chave = f"{of}|{posicao}|{identificador}"
        if chave not in itens_unicos:
            itens_unicos[chave] = {"of": of, "pos": posicao, "identificador": identificador,
                                    "tipo": tipo, "chave": chave, "espessura": row.get("ESP_N", None)}
    faltantes = []
    sem_cam = []
    ignorados_memoria_lista = []
    padrao_planilha = []
    total_relevante = len(itens_unicos)
    for chave, item in itens_unicos.items():
        identificador = item["identificador"]
        posicao = item["pos"]
        # PRIORIDADE MÁXIMA: se já existe um DXF de verdade para essa posição
        # (mesma OF+POSIÇÃO+IDENTIFICADOR), ela está OK - nenhuma marcação
        # manual (padrao_planilha_manual) ou regra automática abaixo pode
        # sobrepor isso; é exatamente o que garante que CAM futuro nunca é
        # descartado por engano.
        if chave in dxf_chaves:
            continue
        chave_memoria_item = _normalizar_chave_memoria(identificador, posicao)
        # [PADRÃO] PLANILHA: SOMENTE itens movidos manualmente pelo usuário
        # (aba Faltantes) - nunca itens classificados automaticamente pelo
        # código como IGNORADO (esses vão para "🧠 Ignorados" abaixo).
        if chave_memoria_item in padrao_planilha_manual_memoria:
            padrao_planilha.append(item)
            continue
        # IGNORADO pelo próprio código (Z, BR_RED, W_, PS) - o roteirizador já
        # sabe que não há CAM para esses, então entram direto em "Ignorados",
        # junto com os marcados manualmente via memória (ignorados_memoria).
        if item["tipo"] == "IGNORADO":
            ignorados_memoria_lista.append(item)
            continue
        if _peca_nao_gera_cam(identificador) and chave_memoria_item not in forcar_cam_memoria:
            sem_cam.append(item)
            continue
        if chave_memoria_item in ignorados_memoria:
            ignorados_memoria_lista.append(item)
            continue
        faltantes.append(item)
    total_encontrados = len(dxf_chaves)
    total_faltantes = len(faltantes)
    total_excluidos = len(sem_cam) + len(ignorados_memoria_lista) + len(padrao_planilha)
    aproveitamento = ((total_relevante - total_faltantes - total_excluidos) / total_relevante * 100) \
        if total_relevante > 0 else 0
    ofs_texto = ", ".join(sorted(ofs_encontradas)) if ofs_encontradas else "N/A"
    # ===== DIVERGÊNCIA DE TAMANHO (DXF x planilha, fora da tolerância) =====
    divergencias_tamanho = []
    for item_dim in analise_dimensoes:
        if item_dim.get("status") != "DIVERGENTE":
            continue
        chave_memoria_dim = _normalizar_chave_memoria(item_dim.get("identificador"), item_dim.get("pos"))
        if chave_memoria_dim in divergencias_tamanho_ignoradas_memoria:
            continue
        divergencias_tamanho.append(item_dim)
    chave_ordenacao = lambda x: (x["of"], x["tipo"], x["pos"])
    chave_ordenacao_dim = lambda x: (x.get("of") or "", x.get("identificador") or "", x.get("pos") or "")
    return {
        "faltantes": sorted(faltantes, key=chave_ordenacao),
        "sem_cam": sorted(sem_cam, key=chave_ordenacao),
        "ignorados_memoria_lista": sorted(ignorados_memoria_lista, key=chave_ordenacao),
        "padrao_planilha": sorted(padrao_planilha, key=chave_ordenacao),
        "divergencias_tamanho": sorted(divergencias_tamanho, key=chave_ordenacao_dim),
        "total_relevante": total_relevante,
        "total_encontrados": total_encontrados,
        "aproveitamento": aproveitamento,
        "ofs_texto": ofs_texto,
    }
def agregar_pesos_por_fluxo(analise_pesos):
    """
    Agrupa a lista de pesos por peça (analise_pesos, gerada em processar())
    pela categoria principal do fluxo (fluxo_base - sem a espessura entre
    colchetes), somando peso total e quantidade de peças de cada um.
    Retorna uma lista de dicts, já ordenada do fluxo mais pesado para o mais
    leve: [{"fluxo": str, "peso_total": float, "quantidade_pecas": int,
    "quantidade_posicoes": int, "peso_medio": float}, ...]
    """
    agregado = defaultdict(lambda: {"peso_total": 0.0, "quantidade_pecas": 0.0, "quantidade_posicoes": 0})
    for item in analise_pesos:
        chave = item["fluxo_base"]
        agregado[chave]["peso_total"] += item["peso_total"]
        agregado[chave]["quantidade_pecas"] += item["quantidade"]
        agregado[chave]["quantidade_posicoes"] += 1
    resultado = []
    for fluxo, dados in agregado.items():
        peso_medio = (dados["peso_total"] / dados["quantidade_pecas"]) if dados["quantidade_pecas"] else 0.0
        resultado.append({
            "fluxo": fluxo,
            "peso_total": dados["peso_total"],
            "quantidade_pecas": dados["quantidade_pecas"],
            "quantidade_posicoes": dados["quantidade_posicoes"],
            "peso_medio": peso_medio,
        })
    resultado.sort(key=lambda x: x["peso_total"], reverse=True)
    return resultado
# ===== TERMINAL OCULTO + LOG DENTRO DA PRÓPRIA INTERFACE =====
# Em vez de imprimir no console (que ficaria aberto atrás da interface), toda
# saída de log()/print() é redirecionada para uma fila (thread-safe) que a
# janela principal lê e mostra dentro da aba "Roteirizador" - por isso NENHUMA
# chamada existente a log()/print() no restante do script precisou mudar.
_FILA_LOG = queue.Queue()

# ===== RELATÓRIO DE ORDENS x FLUXOS (Focco + roteirização) =====
# Lê o relatório de ordens exportado do Focco (qualquer um dos formatos usados:
# "Auditoria de Ordens de Fabricação", "Ordens Planejadas x Demandas"...) - as
# colunas são achadas pelo NOME do cabeçalho, em qualquer posição, e o cabeçalho
# pode estar em qualquer uma das primeiras linhas. Cruza cada ordem (OBRA +
# SUB TRECHO + POSIÇÃO) com o que o roteirizador decidiu e gera um .xlsx no
# layout "Ordens x DXF": uma linha por ordem, com fluxo, máquinas, material,
# espessura, dimensões, pesos e o(s) arquivo(s) DXF.

import unicodedata

_ALIASES_FOCCO = {
    "lote": ["LOTE OF", "PACOTE", "LOTE"],
    "num_ordem": ["NUM ORDEM", "ORDEM", "NUM ORD", "NUMERO ORDEM"],
    "tp_ord": ["TP ORD", "TIPO ORDEM", "TIPO ORD"],
    "dt_emissao": ["DT EMISSAO", "DATA EMISSAO", "DT EMISSAO ORDEM"],
    "obra": ["OBRA", "COD OBRA"],
    "sub_trecho": ["SUB TRECHO", "SUBTRECHO"],
    "posicao": ["POSICAO", "POS", "POSICAO PECA"],
    "marca": ["MARCA"],
    "mascara": ["MASCARA"],
    "desc_demanda": ["DESC TECNICA DEMANDA"],
    "nome_perfil": ["NOME PERFIL"],
    "cod_item_demanda": ["COD ITEM DEMANDA"],
    "qtde_demanda": ["QTDE DEMANDA"],
    "cod_item": ["COD ITEM"],
    "desc_item": ["DESC TECNICA", "DESCRICAO ITEM", "NOME PERFIL"],
    "grupo_lic": ["GRUPO LIC", "GRP LIC"],
    "planejador": ["PLANEJADOR", "NOME"],
    "qtde": ["QTDE OF", "QTDE", "QUANTIDADE"],
    "espessura": ["ESP", "ESPESSURA"],
    "material": ["TP MATL", "MATERIAL"],
    "comp": ["COMP"],
    "larg": ["LARG"],
}

# Máquinas por fluxo (centro de custo, corte, furo, se o furo é sempre feito na
# própria máquina de corte, dobra fixa). Fluxos 1-4 seguem a "SEQUÊNCIA DE
# ROTEIRO" da planilha PCP; o resto segue o modelo de relatório. EDITE AQUI se
# alguma máquina/centro de custo mudar.
_MAQUINAS_POR_FLUXO = {
    "FLUXO 1": {"centro": "PREPARAÇÃO", "corte": "GUILHOTINA 6M", "furo": "PUNCIONADEIRA P113", "furo_sempre": False, "dobra": None},
    "FLUXO 2": {"centro": "PREPARAÇÃO", "corte": "GUILHOTINA 3M", "furo": "PUNCIONADEIRA P51", "furo_sempre": False, "dobra": None},
    "FLUXO 3": {"centro": "PREPARAÇÃO", "corte": "PLASMA", "furo": "PLASMA", "furo_sempre": True, "dobra": None},
    "FLUXO 4": {"centro": "PREPARAÇÃO", "corte": "GUILHOTINA PQ", "furo": "PUNCIONADEIRA P51", "furo_sempre": False, "dobra": None},
    "LASER": {"centro": "PREPARAÇÃO", "corte": "LASER", "furo": "LASER", "furo_sempre": True, "dobra": None},
    "PERFILADEIRA L": {"centro": "PERFILADOS", "corte": "PERFILADEIRA L", "furo": "PERFILADEIRA L", "furo_sempre": True, "dobra": "PERFILADEIRA L"},
    # L1 e L2 são só a separação por máquina: no Focco a operação continua sendo "PERFILADEIRA L"
    "PERFILADEIRA L1": {"centro": "PERFILADOS", "corte": "PERFILADEIRA L", "furo": "PERFILADEIRA L", "furo_sempre": True, "dobra": "PERFILADEIRA L"},
    "PERFILADEIRA L2": {"centro": "PERFILADOS", "corte": "PERFILADEIRA L", "furo": "PERFILADEIRA L", "furo_sempre": True, "dobra": "PERFILADEIRA L"},
    "PERFILADEIRA U E C": {"centro": "PERFILADOS", "corte": "PERFILADEIRA U E C", "furo": "PERFILADEIRA U E C", "furo_sempre": True, "dobra": "PERFILADEIRA U E C"},
    "JOIST": {"centro": "PERFILADOS", "corte": "JOIST", "furo": "JOIST", "furo_sempre": True, "dobra": "JOIST"},
    "TERCA Z": {"centro": "PERFILADOS", "corte": "TERÇA Z", "furo": "TERÇA Z", "furo_sempre": True, "dobra": "TERÇA Z"},
    "PERFILADEIRA": {"centro": "PERFILADOS", "corte": "PERFILADEIRA", "furo": "PERFILADEIRA", "furo_sempre": True, "dobra": "PERFILADEIRA"},
    "ACESSORIOS PADRAO": {"centro": "ACESSÓRIOS PADRÃO", "corte": "ACESSÓRIOS PADRÃO", "furo": "ACESSÓRIOS PADRÃO", "furo_sempre": True, "dobra": "ACESSÓRIOS PADRÃO"},
}

_INCLUIR_ORDENS_SEM_POSICAO = False  # marcas/conjuntos sem posição não geram DXF


def _norm_cab(texto):
    t = unicodedata.normalize("NFKD", str(texto if texto is not None else ""))
    t = t.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", t.upper()).strip()


def _foc_texto(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v).strip()


_RE_DATA_TXT = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})(?:[ T]\d{2}:\d{2}(?::\d{2})?)?\s*$")


def _trechos_conhecidos(valores):
    """Trechos escritos como texto na coluna SUB TRECHO ('4_01' / '4-01'), no formato 'a_bb'."""
    return {str(v).strip().replace("-", "_") for v in valores if isinstance(v, str) and re.fullmatch(r"\d+[_-]\d+", v.strip())}


def _sub_trecho_texto(v, pos="", conhecidos=()):
    """SUB TRECHO como texto ('4_01'). Se o Excel converteu o valor em DATA (ex.: '4-01' virou 01/04), reconstrói o trecho:
    1) pelo prefixo da posição ('4-01_CH-5'); 2) pelo candidato (mês-dia ou dia-mês) que já existe entre os trechos do relatório;
    3) senão, dia-mês (Excel em português)."""
    import datetime as _dt
    d = None
    if isinstance(v, _dt.date):
        d = v
    else:
        m = _RE_DATA_TXT.match(str(v if v is not None else ""))
        if m:
            try:
                d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                d = None
    if d is None:
        return _foc_texto(v)
    m_pos = re.match(r"^(\d+)[-_](\d+)_", str(pos or ""))
    if m_pos:
        return f"{m_pos.group(1)}_{m_pos.group(2)}"
    candidatos = [f"{d.month}_{d.day:02d}", f"{d.day}_{d.month:02d}"]
    for c in candidatos:
        if c in conhecidos:
            return c
    return candidatos[1]


def _foc_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float, np.integer, np.floating)):
        return None if (isinstance(v, float) and math.isnan(v)) else float(v)
    s = str(v).strip()
    if not s or s == "-":
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _foc_int(v):
    f = _foc_float(v)
    return int(f) if f is not None else None


def _foc_data(v):
    if v is None:
        return "-"
    try:
        if pd.isna(v):
            return "-"
    except (TypeError, ValueError):
        pass
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%y")
    d = pd.to_datetime(str(v), errors="coerce", dayfirst=True)
    return d.strftime("%d/%m/%y") if not pd.isna(d) else (str(v) or "-")


def _achar_cabecalho_focco(bruto):
    """Procura, nas primeiras linhas, a linha de cabeçalho; devolve
    (indice_da_linha, {chave: indice_da_coluna}, pontuação) ou None."""
    melhor = None
    for i in range(min(25, len(bruto))):
        celulas = [_norm_cab(v) for v in bruto.iloc[i].tolist()]
        mapa = {}
        for chave, aliases in _ALIASES_FOCCO.items():
            for alias in aliases:
                na = _norm_cab(alias)
                if na in celulas:
                    mapa[chave] = celulas.index(na)
                    break
        if {"obra", "posicao", "num_ordem"} <= set(mapa) and (melhor is None or len(mapa) > melhor[2]):
            melhor = (i, mapa, len(mapa))
    return melhor


def _tipo_ordem(tp_focco, mascara, tem_coluna_mascara):
    """Tipo da ordem (TP ORD): se o relatório do Focco traz a coluna, usa o valor dela (OFA/OFM/OFE).
    Se não traz, deduz pela MÁSCARA: ordem criada MANUALMENTE não tem máscara (OFM); a automática,
    gerada pelo projeto, tem (OFA). OFE só dá para saber pelo relatório que traz a coluna TP ORD."""
    if tp_focco:
        return tp_focco
    if not tem_coluna_mascara:
        return "-"
    return "OFA" if mascara else "OFM"


def _esp_do_nome(nome):
    """Espessura/bitola escrita no NOME do item quando o campo ESP do Focco vem vazio:
    barras 'BR_RED_9.50' -> 9,5 (diâmetro) e tubos 'TB_50.80X2.00-IND-LL' -> 2,0 (parede)."""
    n = str(nome or "").strip().upper()
    m = re.match(r"^BR_[A-Z]+_(\d+(?:[.,]\d+)?)$", n) or re.match(r"^TB_[\d.,]+X(\d+(?:[.,]\d+)?)", n)
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    return v if 0 < v <= 200 else None


def tipo_pintura_da_mascara(mascara):
    """TIPO DE PINTURA lido da MÁSCARA do Focco (campos separados por '#'). O campo muda de posição conforme o tipo de peça,
    então procura pelo CONTEÚDO: 'SEM PINTURA', 'PÓ', 'GALV ...' (ex.: GALV INT COM PASSIVACAO, GALV RAL-9003/PRIMER), 'PRIMER'
    e cor RAL. Devolve o que a máscara diz (mais de um, separados por ' | ') ou '-' quando a máscara não informa pintura."""
    achados = []
    for seg in str(mascara or "").split("#"):
        seg = seg.strip()
        u = seg.upper()
        if not u:
            continue
        if u == "SEM PINTURA":
            texto = "SEM PINTURA"
        elif u in ("PÓ", "PO"):
            texto = "PÓ"
        elif u.startswith("GALV"):
            texto = seg
        elif u == "PRIMER":
            texto = "PRIMER"
        elif re.match(r"^RAL[\s-]?\d{4}$", u):
            texto = seg
        else:
            continue
        if texto not in achados:
            achados.append(texto)
    return " | ".join(achados) if achados else "-"


def _marcas_da_ordem(marca):
    """'109-01_V-34, 109-01_V-35' -> ['109-01_V-34', '109-01_V-35']."""
    return [t.strip() for t in str(marca or "").split(",") if t.strip() and t.strip() != "-"]


def mapa_pintura_por_marca(fl):
    """{(OBRA-TRECHO, MARCA): {tipos de pintura}} lido da MÁSCARA de TODAS as linhas do Focco. A ordem de preparação (CH_PREP, U_PREP...)
    não traz a pintura na máscara dela, mas a ordem da peça montada (VIGA_ALMA_C, ESCADA_INT, ACESS_SOLDADO_INT...) que tem a MESMA
    MARCA na mesma obra-trecho traz. Serve para preencher o TIPO DE PINTURA que a própria máscara não informa."""
    mapa_c = fl["mapa"]
    ci_sub = mapa_c.get("sub_trecho")

    def get(linha, chave):
        ci = mapa_c.get(chave)
        return linha[ci] if ci is not None and ci < len(linha) else None
    conhecidos = _trechos_conhecidos([l[ci_sub] for l in fl["linhas"] if ci_sub is not None and ci_sub < len(l)])
    res = {}
    for linha in fl["linhas"]:
        tipo = tipo_pintura_da_mascara(_foc_texto(get(linha, "mascara")))
        if tipo == "-":
            continue
        pos = _foc_texto(get(linha, "posicao"))
        obra_i = _foc_int(get(linha, "obra"))
        obra_txt = str(obra_i) if obra_i is not None else _foc_texto(get(linha, "obra"))
        sub_raw = _sub_trecho_texto(get(linha, "sub_trecho"), pos, conhecidos)
        obra_trecho = f"{obra_txt}-{sub_raw}".replace("_", "-")
        for t in _marcas_da_ordem(_foc_texto(get(linha, "marca"))):
            res.setdefault((obra_trecho, t), set()).add(tipo)
    return res


def tipo_pintura_da_ordem(mascara, obra_trecho, marca, mapa_pintura):
    """TIPO DE PINTURA da ordem: o da PRÓPRIA máscara; se ela não informa ('-'), o das ordens da mesma peça montada (mesma
    OF-TRECHO e MARCA). Se essas ordens trouxerem tipos DIFERENTES, não adivinha e deixa '-'."""
    proprio = tipo_pintura_da_mascara(mascara)
    if proprio != "-" or not mapa_pintura:
        return proprio
    tipos = set()
    for t in _marcas_da_ordem(marca):
        tipos |= mapa_pintura.get((str(obra_trecho), t), set())
    return next(iter(tipos)) if len(tipos) == 1 else "-"


def parse_mascara_focco(mascara):
    """Extrai peso unitário, comprimento, largura/desenvolvimento, espessura e
    material do texto MASCARA (campos separados por #). O layout varia por tipo
    de item, então ancora no campo de identificação (termina em _R<n>): depois
    dele vêm almox, qtde por conjunto e então peso, comprimento, ..."""
    r = {"peso": None, "comp": None, "larg": None, "esp": None, "material": None, "dobrado": False}
    if not isinstance(mascara, str) or "#" not in mascara:
        return r
    campos = [c.strip() for c in mascara.split("#")]
    r["dobrado"] = "PERFIL DOBRADO" in mascara.upper()
    idx_id = next((i for i, c in enumerate(campos) if re.search(r"_R\d+$", c)), None)
    if idx_id is None:
        return r
    ini = idx_id + 3
    nums, resto = [], []
    for j in range(ini, len(campos)):
        c = campos[j]
        if re.fullmatch(r"-?\d+(,\d+)?", c):
            nums.append(float(c.replace(",", ".")))
        else:
            resto = campos[j:]
            break
    if nums:
        r["peso"] = nums[0]
    if len(nums) > 1:
        r["comp"] = nums[1]
    if len(nums) > 2:
        r["larg"] = nums[2]
    if len(nums) > 3 and 0 < nums[3] <= 60:
        r["esp"] = nums[3]
    if resto and re.search(r"CIVIL|A572|ASTM|ZAR|GALV|SAE|INOX|ALUM", resto[0].upper()):
        r["material"] = resto[0]
    if r["esp"] is None and idx_id >= 6:          # ESP vazio: a bitola vem escrita no nome do item (campo 4)
        r["esp"] = _esp_do_nome(campos[idx_id - 3])
    return r


# ===== LEITURA ROBUSTA DO RELATÓRIO DO FOCCO (reconhece o formato pelo CONTEÚDO) =====
# O Focco pode exportar ".xls" que na verdade é HTML/XML/CSV, ou o arquivo pode estar sem
# extensão. Em vez de confiar na extensão, o programa olha o início do arquivo.
_EXT_TABELA = (".xlsx", ".xlsm", ".xls", ".csv", ".txt", ".html", ".htm", ".xml")


def _normalizar_caminho(texto):
    """Limpa um caminho colado/arrastado: tira aspas, espaços, 'file:///' e variáveis."""
    t = str(texto or "").strip().strip('"').strip("'").strip()
    if t.lower().startswith("file:///"):
        t = t[8:]
        if os.name != "nt" and not t.startswith("/"):
            t = "/" + t
    elif t.lower().startswith("file://"):
        t = ("//" + t[7:]) if os.name == "nt" else t[7:]
    if "%20" in t:
        t = t.replace("%20", " ")
    t = os.path.expandvars(os.path.expanduser(t))
    return os.path.normpath(t) if t else ""


def _sniff_formato(caminho):
    """'xlsx', 'xls', 'xml2003', 'html', 'protegido' ou 'texto' (CSV/TSV)."""
    with open(caminho, "rb") as f:
        cab = f.read(8192)
    if cab[:4] == b"PK\x03\x04":
        return "xlsx"
    if cab[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "protegido" if b"E\x00n\x00c\x00r\x00y\x00p\x00t\x00" in cab else "xls"
    if b"\x00" in cab and not cab[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "desconhecido"          # binário que não é nenhum formato conhecido
    baixo = cab.lower()
    inicio = baixo.lstrip(b"\xef\xbb\xbf \t\r\n")[:100]
    if inicio.startswith(b"<?xml") and b"urn:schemas-microsoft-com:office:spreadsheet" in baixo:
        return "xml2003"
    if inicio.startswith((b"<html", b"<!doctype", b"<table", b"<?xml", b"<meta", b"<head", b"<body")) or b"<table" in baixo:
        return "html"
    return "texto"


def _ler_texto_arquivo(caminho):
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            with open(caminho, "r", encoding=enc, errors="strict") as f:
                return f.read()
        except (UnicodeError, UnicodeDecodeError):
            continue
    with open(caminho, "r", encoding="latin-1", errors="replace") as f:
        return f.read()


def _tabelas_html(texto):
    """Extrai todas as <table> de um HTML (sem bibliotecas externas): lista de DataFrames."""
    from html.parser import HTMLParser

    class _P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.tabelas, self.pilha, self.linha, self.celula = [], [], None, None

        def handle_starttag(self, tag, attrs):
            if tag == "table":
                self.pilha.append([])
            elif tag == "tr" and self.pilha:
                self.linha = []
            elif tag in ("td", "th") and self.linha is not None:
                self.celula = []

        def handle_endtag(self, tag):
            if tag in ("td", "th") and self.celula is not None and self.linha is not None:
                self.linha.append("".join(self.celula).strip())
                self.celula = None
            elif tag == "tr" and self.linha is not None and self.pilha:
                self.pilha[-1].append(self.linha)
                self.linha = None
            elif tag == "table" and self.pilha:
                self.tabelas.append(self.pilha.pop())

        def handle_data(self, data):
            if self.celula is not None:
                self.celula.append(data)

    p = _P()
    p.feed(texto)
    saida = []
    for tab in p.tabelas:
        if len(tab) < 2:
            continue
        largura = max(len(l) for l in tab)
        saida.append(pd.DataFrame([l + [""] * (largura - len(l)) for l in tab], dtype=object))
    return saida


def _tabelas_xml2003(caminho):
    """Planilha 'XML do Excel 2003' (SpreadsheetML): uma tabela por aba."""
    import xml.etree.ElementTree as ET
    ns = "{urn:schemas-microsoft-com:office:spreadsheet}"
    raiz = ET.parse(caminho).getroot()
    saida = {}
    for k, ws in enumerate(raiz.iter(ns + "Worksheet"), 1):
        nome = ws.get(ns + "Name") or f"Plan{k}"
        linhas = []
        for row in ws.iter(ns + "Row"):
            celulas, col = [], 0
            for cel in row.findall(ns + "Cell"):
                idx = cel.get(ns + "Index")
                if idx:
                    while col < int(idx) - 1:
                        celulas.append(None)
                        col += 1
                dado = cel.find(ns + "Data")
                celulas.append(dado.text if dado is not None else None)
                col += 1
            linhas.append(celulas)
        if linhas:
            largura = max(len(l) for l in linhas)
            saida[nome] = pd.DataFrame([l + [None] * (largura - len(l)) for l in linhas], dtype=object)
    return saida


def _abrir_tabelas_focco(caminho):
    """Abre o relatório do Focco, seja qual for o formato, e devolve {nome_da_aba: DataFrame}
    (sem cabeçalho, tudo como objeto). Levanta ValueError com mensagem clara se não conseguir."""
    fmt = _sniff_formato(caminho)
    nome = os.path.basename(caminho)
    try:
        if fmt == "xlsx":
            xls = pd.ExcelFile(caminho, engine="openpyxl")
            return {n: xls.parse(n, header=None, dtype=object) for n in xls.sheet_names}
        if fmt == "xls":
            try:
                xls = pd.ExcelFile(caminho, engine="xlrd")
            except ImportError:
                raise ValueError(f"'{nome}' é um Excel antigo (.xls) e este computador não tem o leitor desse formato. "
                                 "Abra o arquivo no Excel e salve como .xlsx, depois tente de novo.")
            return {n: xls.parse(n, header=None, dtype=object) for n in xls.sheet_names}
        if fmt == "protegido":
            raise ValueError(f"'{nome}' está protegido por senha. Abra no Excel, remova a senha e salve de novo.")
        if fmt == "desconhecido":
            raise ValueError(f"Não consegui entender o formato de '{nome}'. Salve o relatório do Focco como .xlsx e tente de novo.")
        if fmt == "xml2003":
            tabelas = _tabelas_xml2003(caminho)
            if tabelas:
                return tabelas
        if fmt in ("html", "xml2003"):
            tabs = _tabelas_html(_ler_texto_arquivo(caminho))
            if tabs:
                return {f"tabela_{i}": t for i, t in enumerate(sorted(tabs, key=lambda d: -len(d)), 1)}
        # texto delimitado (CSV/TSV/;)
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                df = pd.read_csv(caminho, sep=None, engine="python", header=None, dtype=object,
                                 encoding=enc, on_bad_lines="skip")
                if df.shape[1] > 1:
                    return {"texto": df}
            except (UnicodeError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError):
                continue
    except ValueError:
        raise
    except Exception as ex:
        raise ValueError(f"Não consegui ler '{nome}' (formato {fmt}): {ex}")
    raise ValueError(f"Não consegui entender o formato de '{nome}'. Salve o relatório do Focco como .xlsx e tente de novo.")


def _resolver_arquivo_focco(caminho):
    """Aceita um arquivo OU uma pasta (procura o relatório do Focco dentro dela)."""
    c = _normalizar_caminho(caminho)
    if not c:
        raise FileNotFoundError("Nenhum caminho informado para o relatório do Focco.")
    if os.path.isdir(c):
        candidatos = []
        for n in os.listdir(c):
            pc = os.path.join(c, n)
            if not os.path.isfile(pc) or n.startswith("~$"):
                continue
            ext = os.path.splitext(n)[1].lower()
            if ext in _EXT_TABELA or ext == "":
                pontos = sum(10 for t in ("demanda", "ordens", "focco", "liberad", "planejad", "lote") if t in n.lower())
                candidatos.append((pontos if ext else pontos - 5, os.path.getmtime(pc), pc))
        if not candidatos:
            raise FileNotFoundError(f"Não achei relatório do Focco (.xlsx/.xls/.csv) dentro da pasta: {c}")
        return max(candidatos)[2]
    if not os.path.isfile(c):
        raise FileNotFoundError(f"Arquivo não encontrado: {c}")
    return c


def _classificar_caminho(caminho):
    """Entende o que é um caminho solto/arrastado. Devolve (tipo, caminho_resolvido):
    'tabela' (relatório/planilha: arquivo Excel/CSV), 'pasta_dxf' (pasta com DXF) ou 'desconhecido'."""
    c = _normalizar_caminho(caminho)
    if not c or not os.path.exists(c):
        return "desconhecido", c
    if os.path.isfile(c):
        ext = os.path.splitext(c)[1].lower()
        if ext == ".dxf":
            return "pasta_dxf", os.path.dirname(c)
        if ext in _EXT_TABELA:
            return "tabela", c
        try:
            return ("tabela", c) if _sniff_formato(c) in ("xlsx", "xls", "xml2003", "html", "protegido") else ("desconhecido", c)
        except OSError:
            return "desconhecido", c
    # pasta: tem DXF (até 4 níveis)? senão tem relatório Excel/CSV? senão trata como pasta de DXF
    base_n = c.rstrip(os.sep).count(os.sep)
    tem_tabela = False
    for raiz, _d, nomes in os.walk(c):
        if raiz.count(os.sep) - base_n > 4:
            continue
        if any(n.lower().endswith(".dxf") for n in nomes):
            return "pasta_dxf", c
        if raiz == c and any(os.path.splitext(n)[1].lower() in _EXT_TABELA and not n.startswith("~$") for n in nomes):
            tem_tabela = True
    return ("tabela", c) if tem_tabela else ("pasta_dxf", c)


def ler_relatorio_focco(caminho):
    """Lê o relatório do Focco e devolve uma lista de ordens (dicts), uma por
    ordem+obra+trecho+posição, já com a chave de cruzamento."""
    melhor = _carregar_aba_focco(caminho)
    bruto, linha_cab, mapa, _ = melhor
    ordens, vistos = [], {}
    conhecidos = (_trechos_conhecidos(bruto.iloc[linha_cab + 1:, mapa["sub_trecho"]].tolist())
                  if mapa.get("sub_trecho") is not None else set())
    for k in range(linha_cab + 1, len(bruto)):
        linha = bruto.iloc[k].tolist()

        def val(chave):
            ci = mapa.get(chave)
            return linha[ci] if ci is not None and ci < len(linha) else None

        num_ordem = _foc_int(val("num_ordem"))
        if num_ordem is None:
            continue
        obra = _foc_int(val("obra"))
        pos = _foc_texto(val("posicao"))
        if not pos and "PS" in _foc_texto(val("cod_item")):
            # PS PREP (COD ITEM com "PS", regra PERFIL SOLDADO da planilha PCP): se a POSICAO vier em BRANCO, quem identifica a peça
            # é a MARCA (ou os campos da máscara). Sem isso a ordem era descartada (como as ordens sem posição) e a aba PS PREP
            # ficava sem ela.
            campos_masc = _foc_texto(val("mascara")).split("#")
            pos = (_foc_texto(val("marca")) or (campos_masc[2].strip() if len(campos_masc) > 2 else "")
                   or (campos_masc[0].strip() if campos_masc else ""))
        sub = _sub_trecho_texto(val("sub_trecho"), pos, conhecidos).replace("_", "-")
        if not pos and not _INCLUIR_ORDENS_SEM_POSICAO:
            continue
        chave_dedup = (num_ordem, obra, sub, pos)
        demanda = _foc_texto(val("desc_demanda"))
        if chave_dedup in vistos:
            if demanda and demanda not in vistos[chave_dedup]["demandas"]:
                vistos[chave_dedup]["demandas"].append(demanda)
            continue
        ordens.append({
            "lote": _foc_int(val("lote")),
            "num_ordem": num_ordem,
            "tp_ord": _tipo_ordem(_foc_texto(val("tp_ord")), _foc_texto(val("mascara")), "mascara" in mapa),
            "dt_emissao": _foc_data(val("dt_emissao")),
            "obra": obra,
            "sub_trecho": sub,
            "of": f"{obra}-{sub}" if obra and sub else "",
            "pos": pos,
            "marca": _foc_texto(val("marca")),
            "cod_item": _foc_texto(val("cod_item")),
            "desc_item": _foc_texto(val("desc_item")),
            "grupo_lic": _foc_texto(val("grupo_lic")),
            "planejador": _foc_texto(val("planejador")),
            "qtde": _foc_float(val("qtde")),
            "esp": _foc_float(val("espessura")),
            "material": _foc_texto(val("material")),
            "comp": _foc_float(val("comp")),
            "larg": _foc_float(val("larg")),
            "mascara": _foc_texto(val("mascara")),
            "nome_perfil": _foc_texto(val("nome_perfil")),
            "demandas": [demanda] if demanda else [],
            "tem_col_demanda": "desc_demanda" in mapa,
        })
        vistos[chave_dedup] = ordens[-1]
    return ordens


def _pos_variantes(pos):
    """Formas equivalentes de escrever a mesma posição: com/sem o trecho na frente
    (ex: "100-20_SEZ2-1" = "SEZ2-1") e com/sem o sufixo de lado (ex: "ARL1_U" = "ARL1")."""
    base = str(pos or "").upper().strip().replace("@", "_")
    candidatas = [base]
    sem_trecho = re.sub(r"^\d+[-_]\d+_[-]?", "", base)
    if sem_trecho and sem_trecho != base:
        candidatas.append(sem_trecho)
    for c in list(candidatas):
        sem_lado = re.sub(r"_[A-Z]{1,2}$", "", c)
        if sem_lado and sem_lado != c:
            candidatas.append(sem_lado)
    return list(dict.fromkeys(candidatas))


def _num_limpo(v, casas=1):
    if v is None:
        return "-"
    v = round(float(v), casas)
    return int(v) if v == int(v) else v


def _sequencia_e_maquinas(fluxo_base, tem_furo, dobra):
    """Aplica as regras de máquinas (planilha PCP). Devolve
    (centro, corte, furo, dobra, sequencia)."""
    cfg = _MAQUINAS_POR_FLUXO.get(_norm_cab(fluxo_base))
    if not cfg:
        return "-", "-", "-", "-", fluxo_base or "SEM ROTEIRIZAÇÃO"
    if cfg["dobra"]:
        dobra_final = cfg["dobra"]
    else:
        dobra_final = dobra if dobra and dobra != "NÃO" else "-"
    furo_final = cfg["furo"] if (cfg["furo_sempre"] or tem_furo) else "-"
    seq = cfg["corte"]
    if not cfg["furo_sempre"] and tem_furo:
        seq += " > " + cfg["furo"]
    if dobra_final != "-" and not cfg["dobra"]:
        seq += " > " + dobra_final
    return cfg["centro"], cfg["corte"], furo_final, dobra_final, seq


def _regra_dobra(mascara_info, comp):
    """Regra da planilha PCP: só dobra se a máscara diz PERFIL DOBRADO; até
    400mm de comprimento = PQ, até 3000mm = 3M, acima = 6M."""
    if not mascara_info.get("dobrado") or comp is None:
        return "NÃO"
    if comp <= 400:
        return "DOBRADEIRA PQ"
    if comp <= 3000:
        return "DOBRADEIRA 3M"
    return "DOBRADEIRA 6M"


def _fluxo_perfilado_do_planejador(o):
    """Regra dos PERFILADOS (planilha PCP): a ordem é de perfiladeira quando o
    PLANEJADOR do Focco é "PERFILADEIRA" (PL-005 / PL-024). A máquina vem do tipo
    de perfil: L -> Perfiladeira L; U ou C -> Perfiladeira U e C. Vale mesmo sem
    DXF (perfil sai de bobina, não tem DXF de corte)."""
    if not o or "PERFILADEIRA" not in (o["planejador"] or "").upper():
        return None
    letra = (o["cod_item"] or "").upper().strip()[:1]
    if letra not in ("L", "U", "C", "Z"):
        campos = (o["mascara"] or "").split("#")
        letra = campos[3].strip().upper()[:1] if len(campos) > 3 else ""
    if letra == "L":
        return f"Perfiladeira {destino_perfiladeira_L(o.get('nome_perfil') or o.get('desc_item'), o.get('comp'))}"
    if letra in ("U", "C"):
        return "Perfiladeira U e C"
    return "Perfiladeira"


def coletar_registros_das_pastas(pastas, log_fn=log):
    """Lê TODOS os DXF já roteirizados nas pastas informadas e devolve um
    registro por arquivo: fluxo = nome da pasta de fluxo onde o arquivo está
    (None se estiver fora de qualquer fluxo), espessura/material pelo nome da
    pasta, dimensões e furos medidos no próprio DXF, quantidade pelo nome."""
    arquivos = []
    for pasta in pastas:
        for raiz, _dirs, nomes in os.walk(pasta):
            for nome in nomes:
                if nome.upper().endswith(".DXF"):
                    arquivos.append((pasta, raiz, nome))
    log_fn(f"📁 {len(arquivos)} arquivo(s) DXF encontrado(s) nas pastas informadas")
    registros, fora_padrao = [], 0
    for i, (pasta, raiz, nome) in enumerate(arquivos, 1):
        caminho = os.path.join(raiz, nome)
        of, pos = extrair_nome(nome)
        if not of:
            fora_padrao += 1
            continue
        pasta_nome = _detectar_pasta_por_caminho(caminho, pasta)
        fluxo = extrair_fluxo_base(pasta_nome) if _nome_parece_fluxo(pasta_nome) else None
        esp, material = None, ""
        rel = os.path.relpath(raiz, pasta)
        niveis = [os.path.basename(os.path.normpath(pasta))] + [p for p in rel.split(os.sep) if p not in ("", ".")]
        for nivel in niveis:  # pasta de espessura+material (ex: "1,95 ZAR 400 GALVANIZADO")
            e, mat = _extrair_esp_material_pasta(nivel)
            if e is not None:
                esp, material = e, mat
                break
        if esp is None:
            m_esp = re.search(r"\[(\d+(?:,\d+)?)\]", pasta_nome or "")
            esp = float(m_esp.group(1).replace(",", ".")) if m_esp else None
        try:
            largura, altura = obter_dimensoes_dxf(caminho)
        except Exception:
            largura, altura = None, None
        try:
            furos = analisar_furos_dxf(caminho)[4]
        except Exception:
            furos = 0
        registros.append({
            "of": of, "pos": pos, "identificador": "", "arquivo": nome, "caminho": caminho,
            "fluxo": fluxo, "fluxo_final": fluxo, "fluxo_pasta": pasta_nome if fluxo else None, "esp": esp,
            "largura_dxf": largura, "altura_dxf": altura,
            "parte": extrair_parte_nome(nome),
            "qtd_dxf": extrair_quantidade_arquivo(nome), "qtd_planilha": None,
            "quantidade_furos": furos or 0, "material": material or "",
        })
        if i % 25 == 0:
            log_fn(f"   ... {i}/{len(arquivos)} arquivos lidos")
    if fora_padrao:
        log_fn(f"⚠️  {fora_padrao} arquivo(s) com nome fora do padrão (sem OF) foram ignorados")
    return registros


def _descricao_e_chapa(descricao):
    """True quando a DESCRIÇÃO DO ITEM é uma CHAPA (CHAPA, CHAPA XADREZ...)."""
    return str(descricao or "").strip().upper().startswith("CHAPA")


def _item_e_chapa(o):
    """True quando o item da ordem é uma CHAPA pela descrição do item (a mesma da coluna DESCRIÇÃO DO ITEM)."""
    o = o or {}
    return _descricao_e_chapa(o.get("nome_perfil") or o.get("desc_item"))


def _rota_chapa_so_pintura(rota, desc_demanda, cod_item, descricao_item):
    """Chapa (descrição CHAPA) cuja demanda é SÓ pintura/galvânica (ordem 'ULT.PROC'): a rota (PINTURA, GALVÂNICA...) vira PREPARAÇÃO."""
    arm, pint, _ps, _csc, _d = _flags_pcp(desc_demanda, cod_item)
    if pint and not arm and _descricao_e_chapa(descricao_item) and rota not in _ROTAS_PREP:
        return "PREPARAÇÃO"
    return rota


def _flag_desconsiderar(desc_demanda, cod_item, descricao_item):
    """Igual à coluna ORDENS PARA DESCONSIDERAR da planilha (armação/limpeza ou pintura). Vale para a BASE DE DADOS e para a lista da
    ROTEIRIZAÇÃO FOCCO: a ordem 'ULT.PROC' da CHAPA (consome só tinta/zinco) continua desconsiderada ali - não muda roteiro. A descrição
    CHAPA só tira a ordem da aba ORDENS PARA DESCONSIDERAR e a põe na PREPARAÇÃO (veja _ordem_de_pintura / _rota_chapa_so_pintura)."""
    return _flags_pcp(desc_demanda, cod_item)[4]


def _demanda_principal(livres):
    """UMA descrição de demanda por ORDEM na ROTEIRIZAÇÃO FOCCO (a ordem não se repete): a da chapa que será cortada. Prefere
    'CHAPA CORTADA...', depois 'CHAPA...', depois 'BOBINA...'; deixa por último demanda de sucata, estoque, intermediária, tinta e zinco."""
    itens = [str(d).strip() for d in (livres or []) if str(d or "").strip()]
    if not itens:
        return "-"

    def rank(d):
        u = d.upper()
        if any(k in u for k in ("PARTE DE CONSTRU", "SUCATA", "ESTOQUE", "INTERMEDI", "TINTA", "ZINCO")):
            return 5
        if u.startswith("CHAPA CORTADA"):
            return 0
        if u.startswith("CHAPA"):
            return 1
        if u.startswith("BOBINA"):
            return 2
        return 3
    return min(itens, key=lambda d: (rank(d), itens.index(d)))


def _flags_pcp(desc_demanda, cod_item):
    """Regras da planilha PCP (colunas AH-AL da BASE DE DADOS): devolve
    (armação/limpeza, pintura/lanternim, perfil soldado, CSC, desconsiderar)."""
    d = desc_demanda or ""
    cod = cod_item or ""
    arm = ("XP1" in d) or ("PREPARACAO" in d)
    pint = any(t in d for t in ("TINTA", "INTERMEDI", "TERCEIRIZADO", "ZINCO", "DILUENTE", "CATALISADOR")) \
        or ("LANT_EXT" in cod)
    ps = "PS" in cod
    csc = ("CHAPA GALV" in d) or ("CHAPA ALUM" in d)
    return arm, pint, ps, csc, (arm or pint)


_SEQ_PCP = {  # fluxo: (corte, furo, dobra permitida)
    "FLUXO 1": ("GUILHOTINA 6M", "PUNCIONADEIRA P113", "DOBRADEIRA 6M"),
    "FLUXO 2": ("GUILHOTINA 3M", "PUNCIONADEIRA P51", "DOBRADEIRA 3M"),
    "FLUXO 4": ("GUILHOTINA PQ", "PUNCIONADEIRA P51", "DOBRADEIRA PQ"),
}


def _sequencia_pcp(fluxo_base, dobra, tem_furo):
    """Réplica EXATA da fórmula SEQUÊNCIA DE ROTEIRO da planilha PCP. Devolve ""
    quando a combinação fluxo x dobra x furação não tem regra (a planilha deixa em
    branco). LASER segue a mesma lógica do Fluxo 3 (regra nova, não está na planilha)."""
    f = _norm_cab(fluxo_base)
    if f in _SEQ_PCP:
        corte, furo, dobra_ok = _SEQ_PCP[f]
        base = corte + (" > " + furo if tem_furo else "")
        if dobra == dobra_ok:
            return base + " > " + dobra_ok
        return base if dobra == "NÃO" else ""
    if f in ("FLUXO 3", "LASER"):
        maq = "PLASMA" if f == "FLUXO 3" else "LASER"
        if dobra in ("DOBRADEIRA 6M", "DOBRADEIRA 3M", "DOBRADEIRA PQ"):
            return maq + " > " + dobra
        return maq if dobra == "NÃO" else ""
    return ""


# ===== ROTAS DO HTML "PPCP - ROTEIRIZAÇÃO L - UC" (classificação por linha de demanda) =====
# Réplica fiel da função classify() do HTML. Define a ROTA (setor) de cada linha do
# relatório do Focco. PREPARAÇÃO / PREPARAÇÃO (DOBRA) = o que o roteirizador roteiriza
# por DXF (Fluxos 1-4, LASER); as demais rotas já têm roteiro automático.
_ROTAS_PREP = ("PREPARAÇÃO", "PREPARAÇÃO (DOBRA)")
_ROTAS_ORDEM = ["PREPARAÇÃO", "PREPARAÇÃO (DOBRA)", "PERFILADEIRA U/C", "PERFILADEIRA L", "PERFILADEIRA Z",
                "PERFILADEIRA BANZO JOIST", "PERFILADEIRA U JOIST", "ACESSÓRIOS JOIST", "ACESSÓRIO PADRÃO",
                "BARRAS", "CENTRO DE SERVIÇO", "PINTURA", "GALVÂNICA", "LAMINADOS", "ARMAÇÃO"]
_OBS_ROTA = {
    "PREPARAÇÃO": "Chapa bruta/cortada ASTM · sem intermediários",
    "PREPARAÇÃO (DOBRA)": "Perfil U/C dentro do parâmetro mas comp < 800mm",
    "PERFILADEIRA U/C": "Alma ≥100, aba ≤106 (U) · alma >100, aba1 >50, aba2 <30 (C) · comp ≥800mm",
    "PERFILADEIRA L": "Abas iguais · esp ≤ 3,0mm · sem intermediários",
    "PERFILADEIRA Z": "GRP LIC = PERFIL Z · sem intermediários · sem tinta",
    "PERFILADEIRA BANZO JOIST": "GRP LIC = BANZO JOIST / BANZO PROJOIST · sem intermediários",
    "PERFILADEIRA U JOIST": "GRP LIC = PERFIL U JOIST / PROJOIST · sem intermediários",
    "ACESSÓRIOS JOIST": "GRP LIC = ACESSORIOS JOIST/PRENSA/PROJOIST · sem inter. · sem tinta",
    "ACESSÓRIO PADRÃO": "SE2-4 · SEZ1-4 · SD1 · TIRA BLANK estoque",
    "BARRAS": "Barra redonda ASTM A36 / SAE 1020",
    "CENTRO DE SERVIÇO": "Arremate · Calha · Telhas TP/Zipada · Bobina Zipada · Telas · Passarinheiro",
    "PINTURA": "Tinta (qualquer tipo) · Catalisador/Diluente Epoxi/PU - PRIORIDADE MÁXIMA",
    "GALVÂNICA": "Qualquer demanda com ZINCO",
    "LAMINADOS": "Perfil W/HP/I/U ASTM · Cantoneira · Tubo red./quad. · sem intermediários",
    "ARMAÇÃO": "Todos os itens não classificados nas rotas acima",
}
# fluxo "automático" que corresponde a cada rota (nome usado nas pastas/relatório)
_ROTA_PARA_FLUXO = {
    "PERFILADEIRA L": "Perfiladeira L", "PERFILADEIRA U/C": "Perfiladeira U e C", "PERFILADEIRA Z": "Terça Z",
    "PERFILADEIRA BANZO JOIST": "Joist", "PERFILADEIRA U JOIST": "Joist", "ACESSÓRIOS JOIST": "Joist",
    "ACESSÓRIO PADRÃO": "Acessórios Padrão",
}
_FLUXOS_PREP_NORM = {"FLUXO 1", "FLUXO 2", "FLUXO 3", "FLUXO 4", "LASER"}
_BARRAS_HTML = {s.upper() for s in [
    "BARRA REDONDA ASTM A36 12,70MM", "BARRA REDONDA ASTM A36 16,00MM", "BARRA REDONDA ASTM A36 19,00MM",
    "BARRA REDONDA ASTM A36 22,20MM", "BARRA REDONDA ASTM A36 25,40MM", "BARRA REDONDA ASTM A36 31,75MM",
    "BARRA REDONDA ASTM A36 38,10MM", "BARRA REDONDA ASTM A36 44,45MM", "BARRA REDONDA ASTM A36 9,50MM",
    "BARRA REDONDA SAE 1020 38,10MM"]}
_ACESS_PADRAO_HTML = {s.upper() for s in [
    "SE2 ESTOQUE", "SE3 ESTOQUE", "SE4 ESTOQUE", "SEZ1 ESTOQUE", "SEZ2 ESTOQUE", "SEZ3 ESTOQUE", "SEZ4 ESTOQUE",
    "SD1 ESTOQUE", "TIRA BLANK 25 X 3000 A572 PC", "TIRA BLANK 25 X 3000 ZAR 400 PC"]}
_CS_PERFIS_HTML = {"ARREMATE", "CALHA", "TELHA TP100", "TELHA TP17", "TELHA TP35", "TELHA TP40", "TELHA ZIPADA"}


# TELAS e PASSARINHEIRO são do CENTRO DE SERVIÇO (antes caíam em ARMAÇÃO, o "resto"): olha o COD ITEM (ex.: TELA_PREP) e a DESCRIÇÃO DO ITEM
# (ex.: _PASSARINHEIRO_INOX_1.20_X_50). "TELA"/"TELAS" só como palavra (o "_" e o início/fim do texto separam; TELHA, ESTELA e afins não casam).
_RE_ITEM_CENTRO_SERVICO = re.compile(r"(?<![A-Z0-9])TELAS?(?![A-Z0-9])|PASSARINHEIRO")


def item_e_centro_servico(*textos):
    """True se algum dos textos (COD ITEM, DESCRIÇÃO DO ITEM, NOME PERFIL) é uma TELA ou um PASSARINHEIRO -> SETOR CENTRO DE SERVIÇO."""
    return any(_RE_ITEM_CENTRO_SERVICO.search(str(t or "").upper()) for t in textos)


def classificar_rota_html(desc_demanda, grp_lic, nome_perfil, comp, cod_item="", desc_item=""):
    """Mesma lógica do HTML (função classify), na mesma ordem de prioridade (+ TELAS/PASSARINHEIRO = CENTRO DE SERVIÇO, logo depois
    de pintura/galvânica)."""
    desc = str(desc_demanda or "").strip()
    du = desc.upper()
    grp = str(grp_lic or "").strip().upper()
    nome = str(nome_perfil or "").strip()
    nu = nome.upper()
    try:
        comp = float(str(comp).replace(",", ".")) if comp not in (None, "") else None
    except ValueError:
        comp = None
    itr = bool(re.search(r"INTERMEDIARI", desc, re.I))
    if re.search(r"\bTINTA\b", desc, re.I) or re.search(r"\b(CATALISADOR|DILUENTE)\b.*\b(EPOXI|PU)\b", desc, re.I):
        return "PINTURA"
    if re.search(r"\bZINCO\b", desc, re.I):
        return "GALVÂNICA"
    if item_e_centro_servico(cod_item, desc_item, nome):
        return "CENTRO DE SERVIÇO"
    if re.match(r"^CHAPA\s+(ASTM|CORTADA)", du, re.I):
        return "PREPARAÇÃO"
    if du in _BARRAS_HTML:
        return "BARRAS"
    if du in _ACESS_PADRAO_HTML:
        return "ACESSÓRIO PADRÃO"
    if "PERFIL Z" in grp and not itr:
        return "PERFILADEIRA Z"
    if ("BANZO JOIST" in grp or "BANZO PROJOIST" in grp) and not itr:
        return "PERFILADEIRA BANZO JOIST"
    if ("PERFIL U JOIST" in grp or "PERFIL U PROJOIST" in grp) and not itr:
        return "PERFILADEIRA U JOIST"
    if any(x in grp for x in ("ACESSORIOS JOIST", "ACESSORIOS JOIST PRENSA", "ACESSORIOS PROJOIST PRENSA")) and not itr:
        return "ACESSÓRIOS JOIST"
    if nu in _CS_PERFIS_HTML or "TELHAS" in grp or "BOBINA ZIPADA" in grp:
        return "CENTRO DE SERVIÇO"
    if not itr:
        if re.match(r"^PERFIL\s+(W|HP|I|U)\s+ASTM", du, re.I):
            return "LAMINADOS"
        if re.match(r"^CANTONEIRA\s+(ASTM|PARA\s+LANTERNIM)", du, re.I):
            return "LAMINADOS"
        if re.match(r"^TUBO\s+(REDONDO|QUADRADO)", du, re.I):
            return "LAMINADOS"
        if "VIGA/PILAR LAMINADO" in grp or "PERFIL L JOIST" in grp or "PERFIL L PROJOIST" in grp:
            return "LAMINADOS"
    if not itr and re.match(r"^L\d", nu, re.I):
        m = re.match(r"^L(\d+\.?\d*)X(\d+\.?\d*)X([\d.]+)", nome, re.I)
        if m and float(m.group(1)) == float(m.group(2)) and float(m.group(3)) <= 3.0:
            return "PERFILADEIRA L"
    if not itr:
        if re.match(r"^U\d", nu, re.I):
            m = re.match(r"^U(\d+\.?\d*)X(\d+\.?\d*)X[\d.]+", nome, re.I)
            if m:
                alma, aba = float(m.group(1)), float(m.group(2))
                if re.match(r"^U150X81X3\.00", nome, re.I) and comp is not None and comp < 500:
                    return "PREPARAÇÃO"
                if alma >= 100 and aba <= 106:
                    if comp is not None and comp >= 800:
                        return "PERFILADEIRA U/C"
                    if comp is not None:
                        return "PREPARAÇÃO (DOBRA)"
        if re.match(r"^C\d", nu, re.I):
            m = re.match(r"^C(\d+\.?\d*)X(\d+\.?\d*)X(\d+\.?\d*)", nome, re.I)
            if m:
                alma, a1, a2 = float(m.group(1)), float(m.group(2)), float(m.group(3))
                if alma > 100 and a1 > 50 and a2 < 30:
                    if comp is not None and comp >= 800:
                        return "PERFILADEIRA U/C"
                    if comp is not None:
                        return "PREPARAÇÃO (DOBRA)"
    return "ARMAÇÃO"


def _rota_da_ordem(o):
    """ROTA única da ORDEM (as linhas de demanda de uma ordem podem cair em rotas
    diferentes): se alguma linha ainda 'conta' (não é armação/limpeza nem pintura) usa
    a dela, dando preferência à preparação; senão a da primeira linha. None quando o
    relatório não traz a coluna de demanda."""
    if not o.get("tem_col_demanda"):
        return None
    dem = o["demandas"] or [""]
    rotas = [(classificar_rota_html(d, o["grupo_lic"], o["nome_perfil"] or o["desc_item"], o["comp"],
                                       o["cod_item"], o["desc_item"]),
              _flag_desconsiderar(d, o["cod_item"], o["nome_perfil"] or o["desc_item"])) for d in dem]
    livres = [r for r, f in rotas if not f]
    base = livres or [r for r, _ in rotas]
    for r in base:
        if r in _ROTAS_PREP:
            return r
    if _item_e_chapa(o) and all(_flags_pcp(d, o["cod_item"])[1] and not _flags_pcp(d, o["cod_item"])[0] for d in dem):
        return "PREPARAÇÃO"                              # chapa (descrição CHAPA) com demanda só de tinta/zinco: é PREPARAÇÃO
    return base[0]


_ABA_PINTURA = "ORDENS PARA DESCONSIDERAR"      # (antes "ORDEM DE PINTURA (NÃO IMPRIMIR)") pintura/galvânica + marcas SD1 e SEZ1-SEZ4
_ABA_PS_PREP = "PS PREP"
_ABA_AUX_CONCATENAR = "AUX_CONCATENAR"          # aba oculta com as contas das fórmulas de concatenar


def _ordem_ps_prep(o):
    """True para a ordem de PS PREP. É a regra da planilha PCP, coluna PERFIL SOLDADO da BASE DE DADOS:
        =SE(OU(ÉNÚM(PROCURAR("PS";[@[COD ITEM]])));"X";"")
    ou seja, SÓ olha o COD ITEM da ordem: se contém "PS" (PROCURAR diferencia maiúscula de minúscula) é PS PREP. Não olha marca,
    máscara, posição nem o que a ordem consome (chapa etc.). É a mesma regra do PERFIL SOLDADO de _flags_pcp()."""
    return bool(o) and _flags_pcp("", o.get("cod_item"))[2]


def _setor_exibicao(rota, nome_perfil, comp):
    """SETOR mostrado nos relatórios: a rota 'PERFILADEIRA L' aparece como 'PERFILADEIRA L1' ou 'PERFILADEIRA L2'
    (mesma regra do programador das perfiladeiras L). As demais rotas ficam como estão."""
    if rota == "PERFILADEIRA L":
        return f"PERFILADEIRA {destino_perfiladeira_L(nome_perfil, comp)}"
    return rota


_RE_MARCA_DESCONSIDERAR = re.compile(r"^(?:\d+-\d+_)?(?:SD1|SEZ[1-4])(?:-\d+)?(?:_U)?$")


def _marca_pos_desconsiderar(valor):
    """True quando a MARCA / POSIÇÃO é SD1, SEZ1, SEZ2, SEZ3 ou SEZ4 - com ou sem o trecho colado na frente (4-01_SEZ2-1) e com
    ou sem o sufixo da peça (-1, -1_U). Em marca com várias (SEZ2, SEZ3) todas precisam ser dessas."""
    partes = [p.strip() for p in str(valor or "").upper().split(",") if p.strip() and p.strip() != "-"]
    return bool(partes) and all(_RE_MARCA_DESCONSIDERAR.match(p) for p in partes)


def _item_estoque_acessorio(pos):
    """DXF SEM ordem no Focco cuja POSIÇÃO é SD1 ou SEZ1-SEZ4 (acessório padrão de estoque): devolve (COD ITEM, DESCRIÇÃO DO ITEM)
    como o HTML "Roteirização de Produção" chama esses itens ('SD1' / 'SD1 ESTOQUE', 'SEZ2' / 'SEZ2 ESTOQUE'...); senão None."""
    m = re.match(r"^(?:\d+-\d+_)?(SD1|SEZ[1-4])(?:-\d+)?(?:_U)?$", str(pos or "").strip().upper())
    if not m:
        return None
    desc = f"{m.group(1)} ESTOQUE"
    return (m.group(1), desc) if desc in _ACESS_PADRAO_HTML else None


def _ordem_de_pintura(o):
    """True quando a ORDEM é de pintura/galvânica (todas as linhas de demanda dela são tinta, zinco, diluente/catalisador,
    intermediário ou terceirizado - a coluna ORDEM DE PINTURA/LANTERNIM da planilha PCP). Sem a coluna de demanda no
    relatório do Focco não dá para saber: nesse caso não é tratada como pintura."""
    if not o or not o.get("tem_col_demanda") or _item_e_chapa(o):      # CHAPA (descrição do item) é preparação, não pintura
        return False
    dem = [d for d in (o.get("demandas") or []) if str(d or "").strip()]
    return bool(dem) and all(_flags_pcp(d, o.get("cod_item"))[1] for d in dem)


# ===== PADRÃO DO RELATÓRIO (igual ao arquivo tratado pelo usuário) =====
# Ordem das abas, colunas que saem em cada aba, tudo centralizado e larguras de coluna.
_ORDEM_ABAS_RELATORIO = ["ROTEIRIZAÇÃO FOCCO", "Preparação", "Não Preparação", "PS PREP", "ORDENS PARA DESCONSIDERAR",
                         "Relatório Consolidado (FLuxos)", "CSC", "Ordens x DXF", "BASE DE DADOS", "Resumo"]
_GERAR_ABA_CONFERENCIA = False   # True = gera também a aba "Conferência Roteirização" (no fim)
_COLUNAS_FORA_PREPARACAO = ("TP ORD", "OBRA", "SUB TRECHO")
_COLUNAS_NAO_PREPARACAO = ["LOTE OF", "SETOR", "OF-TRECHO", "NUM ORDEM", "POSIÇÃO", "ESPESSURA (mm)", "COD ITEM",
                           "MARCA", "QTDE (ORDEM)", "DESCRIÇÃO DO ITEM", "MATERIAL", "LARGURA (mm)", "ALTURA (mm)",
                           "PESO UNITÁRIO (kg)", "PESO TOTAL (kg)", "PLANEJADOR", "TIPO DE PINTURA", "GRUPO LIC"]   # GRUPO LIC por último
_LARGURAS_USUARIO = {
 "PLAN DIN": {
  "ESPESSURA": 28.2,
  "ORDEM": 27.6,
  "POSICAO": 13.1,
  "OBRA E TRECHO": 19.0,
  "FLUXO DE PRODUÇÃO": 24.1
 },
 "Preparação": {
  "LOTE OF": 28.4,
  "NUM ORDEM": 28.4,
  "OF-TRECHO": 28.4,
  "POSIÇÃO": 28.4,
  "FLUXO": 28.4,
  "CENTRO DE CUSTO": 28.4,
  "CORTE": 28.4,
  "FURO": 28.4,
  "DOBRA": 28.4,
  "MATERIAL": 28.4,
  "ESPESSURA (mm)": 28.4,
  "LARGURA (mm)": 28.4,
  "ALTURA (mm)": 28.4,
  "PESO UNITÁRIO (kg)": 28.4,
  "PESO TOTAL (kg)": 28.4,
  "ARQUIVO(S) DXF": 28.4,
  "STATUS": 28.4,
  "QTDE (ORDEM)": 28.4,
  "MARCA": 28.4,
  "COD ITEM": 28.4,
  "DESCRIÇÃO DO ITEM": 28.4,
  "GRUPO LIC": 28.4,
  "PLANEJADOR": 28.4,
  "SEQUÊNCIA DE ROTEIRO": 28.4,
  "TEM FURO?": 28.4,
  "OBSERVAÇÃO": 28.4,
  "SETOR": 28.4, "TIPO DE PINTURA": 34
 },
 "Não Preparação": {
  "LOTE OF": 15.0,
  "NUM ORDEM": 22.3,
  "OF-TRECHO": 22.3,
  "POSIÇÃO": 22.3,
  "MATERIAL": 22.3,
  "ESPESSURA (mm)": 22.3,
  "LARGURA (mm)": 22.3,
  "ALTURA (mm)": 22.3,
  "PESO UNITÁRIO (kg)": 22.3,
  "PESO TOTAL (kg)": 22.3,
  "QTDE (ORDEM)": 22.3,
  "MARCA": 22.3,
  "COD ITEM": 22.3,
  "DESCRIÇÃO DO ITEM": 22.3,
  "GRUPO LIC": 22.3
 },
 "Relatório Consolidado (FLuxos)": {
  "OF": 14.0,
  "Posição": 12.0,
  "Quantidade": 11.0,
  "Fluxo": 26.0,
  "Material": 18.0,
  "Espessura (mm)": 14.0,
  "Máquina": 24.0,
  "Largura (mm)": 14.0,
  "Altura (mm)": 12.0,
  "Peso Unitário (kg)": 16.0,
  "Peso Total (kg)": 16.0,
  "TEM FURO?": 11.0,
  "OBRA E TRECHO_POSIÇÃO": 26.0,
  "FLUXO DE PRODUÇÃO": 22.0,
  "FURAÇÃO": 11.0
 },
 "CSC": {
  "COD ITEM DEMANDA": 20.0,
  "DESC TECNICA DEMANDA": 56.0,
  "SAL ESTOQUE": 16.0,
  "N° DA ORDEM": 16.0
 },
 "ROTEIRIZAÇÃO FOCCO": {
  "SEQUÊNCIA DE ROTEIRO": 52.0,
  "ORDEM": 12.0,
  "OBRA E TRECHO_POSIÇÃO": 26.0,
  "DESC TECNICA DEMANDA": 52.0,
  "PLANEJADOR": 36.0,
  "OBRA E TRECHO": 16.0,
  "FLUXO DE PRODUÇÃO": 20.0,
  "Nº DE ORDENS": 14.0,
  "ORDENS (separadas por vírgula)": 90.0
 },
 "Ordens x DXF": {
  "LOTE OF": 9.0,
  "NUM ORDEM": 11.0,
  "TP ORD": 8.0,
  "OBRA": 7.0,
  "SUB TRECHO": 12.0,
  "OF-TRECHO": 13.0,
  "POSIÇÃO": 14.0,
  "FLUXO": 18.0,
  "CENTRO DE CUSTO": 18.0,
  "CORTE": 22.0,
  "FURO": 22.0,
  "DOBRA": 18.0,
  "MATERIAL": 22.0,
  "ESPESSURA (mm)": 16.0,
  "LARGURA (mm)": 14.0,
  "ALTURA (mm)": 13.0,
  "PESO UNITÁRIO (kg)": 20.0,
  "PESO TOTAL (kg)": 17.0,
  "ARQUIVO(S) DXF": 44.0,
  "STATUS": 22.0,
  "QTDE (ORDEM)": 13.0,
  "MARCA": 12.0,
  "COD ITEM": 18.0,
  "DESCRIÇÃO DO ITEM": 30.1,
  "GRUPO LIC": 30.1,
  "PLANEJADOR": 30.1,
  "SEQUÊNCIA DE ROTEIRO": 46.4,
  "TEM FURO?": 30.1,
  "OBSERVAÇÃO": 30.1,
  "SETOR": 30.1, "TIPO DE PINTURA": 34
 },
 "BASE DE DADOS": {
  "PLANEJADOR": 44.0,
  "PACOTE": 12.2,
  "OBRA": 10.2,
  "NOME TRECHO": 18.2,
  "SUB TRECHO": 16.1,
  "POSICAO": 13.1,
  "GRP LIC": 20.8,
  "MARCA": 25.6,
  "ESP": 8.6,
  "LARG": 9.9,
  "COMP": 10.8,
  "DESENHO": 13.6,
  "NOME PERFIL": 19.2,
  "ORDEM": 11.9,
  "COD ITEM": 19.1,
  "MASCARA": 186.4,
  "QTDE OF": 12.7,
  "COD ITEM DEMANDA": 23.6,
  "DESC TECNICA DEMANDA": 53.1,
  "COD ALMOX DEM": 20.4,
  "QTDE DEM UNIT": 19.2,
  "QTDE DEMANDA": 19.6,
  "UM": 8.6,
  "ALMOX CONSUMO": 14.7,
  "TCAD EST ITE ID": 18.8,
  "DEMANDA ID": 16.7,
  "ESPESSURA": 15.2,
  "OBRA E TRECHO": 19.0,
  "OBRA E TRECHO_POSIÇÃO": 27.9,
  "FLUXO DE PRODUÇÃO": 24.1,
  "FURAÇÃO": 17.4,
  "DOBRA": 15.1,
  "SEQUÊNCIA DE ROTEIRO": 51.1,
  "ORDEM ARM/LIMP": 21.9,
  "ORDEM DE PINTURA/LANTERNIM": 34.3,
  "PERFIL SOLDADO": 19.8,
  "CSC": 8.7,
  "ORDENS PARA DESCONSIDERAR": 32.7,
  "SETOR": 18.3, "TIPO DE PINTURA": 34
 },
 "Resumo": {
  "FLUXO": 46.0,
  "ORDENS": 14.0,
  "PESO TOTAL (kg)": 18.0
 }
}

_LARGURAS_USUARIO.setdefault("Preparação", {})["SEQUÊNCIA DE ROTEIRO"] = 52.0   # cabe "GUILHOTINA PQ > PUNCIONADEIRA P51 > DOBRADEIRA PQ"

_LARGURAS_ROTEIRIZACAO_FOCCO = [62, 24, 32, 16, 26, 66, 48]     # SEQUÊNCIA · OBRA E TRECHO · POSIÇÃO · ORDEM · FLUXO · DESC · PLANEJADOR
_LARGURAS_USUARIO["ROTEIRIZAÇÃO FOCCO"] = dict(zip(
    ["SEQUÊNCIA DE ROTEIRO", "OBRA E TRECHO", "POSIÇÃO", "ORDEM", "FLUXO DE PRODUÇÃO", "DESC TECNICA DEMANDA", "PLANEJADOR"],
    _LARGURAS_ROTEIRIZACAO_FOCCO))
_LARGURAS_USUARIO["PS PREP"] = dict(_LARGURAS_USUARIO.get("Não Preparação", {}))     # PS PREP tem as mesmas colunas/larguras da Não Preparação
for _aba_l in ("Preparação", "Não Preparação", "PS PREP"):    # o título "LOTE OF" virou "LOTE": mantém a largura
    if "LOTE OF" in _LARGURAS_USUARIO.get(_aba_l, {}):
        _LARGURAS_USUARIO[_aba_l].setdefault("LOTE", _LARGURAS_USUARIO[_aba_l]["LOTE OF"])


# ===== BASE DE DADOS completa (todas as colunas do Focco + as calculadas da planilha PCP) =====
_COLUNAS_CALC = ["ESPESSURA", "OBRA E TRECHO", "OBRA E TRECHO_POSIÇÃO", "FLUXO DE PRODUÇÃO", "FURAÇÃO", "DOBRA",
                 "SEQUÊNCIA DE ROTEIRO", "ORDEM ARM/LIMP", "ORDEM DE PINTURA/LANTERNIM", "PERFIL SOLDADO", "CSC",
                 "ORDENS PARA DESCONSIDERAR", "SETOR", "TIPO DE PINTURA"]

_COLUNAS_CALC_FIM = [c for c in _COLUNAS_CALC if c != "OBRA E TRECHO"]   # "OBRA E TRECHO" fica no lugar da OBRA

# Máquina de cada fluxo na aba "Relatório Consolidado (FLuxos)" da planilha PCP
_MAQUINA_CONSOLIDADO = {
    "FLUXO 1": "GUILHOTINA 6M", "FLUXO 2": "GUILHOTINA 3M", "FLUXO 3": "AUTOCUT EDGE CONNECT",
    "FLUXO 4": "CHINESSINHA", "LASER": "LASER", "PERFILADEIRA L": "PERFILADEIRA",
    "PERFILADEIRA L1": "PERFILADEIRA", "PERFILADEIRA L2": "PERFILADEIRA",
    "PERFILADEIRA U E C": "PERFILADEIRA", "PERFILADEIRA": "PERFILADEIRA", "TERCA Z": "TERÇA",
    "ACESSORIOS PADRAO": "INDEFINIDO", "JOIST": "JOIST",
}


def _nome_fluxo_pcp(nome):
    """Nome do fluxo como aparece na planilha PCP ("Perfiladeira U E C" com E maiúsculo)."""
    if nome and _norm_cab(re.sub(r"\s*\[.*\]$", "", str(nome))) == "PERFILADEIRA U E C":
        return re.sub(r"^Perfiladeira U e C", "Perfiladeira U E C", str(nome), flags=re.I)
    return nome


def _foc_vazio(v):
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(v, str) and not v.strip()


def _xl(v):
    """Valor seguro p/ escrever no Excel (tira tipos numpy/NaN)."""
    if _foc_vazio(v):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    return v


def _carregar_aba_focco(caminho):
    """Abre o relatório (qualquer formato, arquivo ou pasta) e acha a aba/tabela com o cabeçalho."""
    caminho = _resolver_arquivo_focco(caminho)
    melhor = None
    for nome, bruto in _abrir_tabelas_focco(caminho).items():
        achado = _achar_cabecalho_focco(bruto)
        if achado and (melhor is None or achado[2] > melhor[3]):
            melhor = (bruto, achado[0], achado[1], achado[2])
    if melhor is None:
        raise ValueError("Não encontrei, no relatório do Focco, as colunas OBRA, POSICAO e ORDEM "
                         "(nenhuma aba/tabela tem esse cabeçalho). Confira se é o relatório de ordens x demanda.")
    return melhor


def ler_focco_linhas(caminho):
    """Todas as LINHAS (ordem x demanda) do relatório do Focco, com TODAS as colunas originais."""
    bruto, linha_cab, mapa, _ = _carregar_aba_focco(caminho)
    cab_raw = [_foc_texto(v) for v in bruto.iloc[linha_cab].tolist()]
    cols = [i for i, h in enumerate(cab_raw) if h]
    linhas = []
    ci = mapa["num_ordem"]
    for k in range(linha_cab + 1, len(bruto)):
        linha = bruto.iloc[k].tolist()
        if ci < len(linha) and _foc_int(linha[ci]) is not None:
            linhas.append(linha)
    return {"cab_raw": cab_raw, "cols": cols, "linhas": linhas, "mapa": mapa}


def montar_base_dados(fl, mapa_ordem, mapa_pintura=None):
    """Monta a BASE DE DADOS: colunas originais do Focco + as colunas calculadas (mesmas
    regras das fórmulas da planilha PCP) + ROTA do HTML. `mapa_ordem` liga cada ordem ao
    resultado do roteirizador: {(ordem, obra, sub_trecho, posição): (fluxo, tem_furo)}."""
    mapa = fl["mapa"]
    tem_demanda = "desc_demanda" in mapa

    def get(linha, chave):
        ci = mapa.get(chave)
        return linha[ci] if ci is not None and ci < len(linha) else None

    norm_calc = {_norm_cab(n) for n in _COLUNAS_CALC + ["ROTA (HTML)"]}   # "ROTA (HTML)" = nome antigo do SETOR (relatórios gerados antes)
    ci_obra, ci_sub = mapa.get("obra"), mapa.get("sub_trecho")
    # OBRA e SUB TRECHO viram UMA coluna só ("OBRA E TRECHO", no lugar da OBRA)
    cols_saida = [i for i in fl["cols"] if _norm_cab(fl["cab_raw"][i]) not in norm_calc and i != ci_sub]
    cabecalho = [("OBRA E TRECHO" if i == ci_obra else fl["cab_raw"][i]) for i in cols_saida] + _COLUNAS_CALC_FIM
    saida, calc = [], []
    conhecidos = _trechos_conhecidos([l[ci_sub] for l in fl["linhas"] if ci_sub is not None and ci_sub < len(l)])
    for linha in fl["linhas"]:
        num = _foc_int(get(linha, "num_ordem"))
        obra = get(linha, "obra")
        obra_i = _foc_int(obra)
        pos = _foc_texto(get(linha, "posicao"))
        sub_raw = _sub_trecho_texto(get(linha, "sub_trecho"), pos, conhecidos)
        fluxo_dxf, tem_furo = (None, False)
        if pos:
            fluxo_dxf, tem_furo = mapa_ordem.get((num, obra_i, sub_raw.replace("_", "-"), pos), (None, False))
        desc = _foc_texto(get(linha, "desc_demanda"))
        cod = _foc_texto(get(linha, "cod_item"))
        nome_perfil = _foc_texto(get(linha, "nome_perfil"))
        arm, pint, ps, csc, desc_flag = _flags_pcp(desc, cod)       # desc_flag = coluna ORDENS PARA DESCONSIDERAR da planilha
        esp_raw = get(linha, "espessura")
        if desc_flag:
            esp_calc = None
        else:
            # igual à fórmula do Excel: ESP vazio -> NOME PERFIL; se este também for vazio, o Excel devolve 0
            esp_calc = (nome_perfil or 0) if _foc_vazio(esp_raw) else _xl(esp_raw)
        obra_txt = str(obra_i) if obra_i is not None else _foc_texto(obra)
        obra_trecho = f"{obra_txt}-{sub_raw}".replace("_", "-")
        chave = f"{obra_trecho}_{pos}"
        comp_num = _foc_float(get(linha, "comp"))
        mascara = _foc_texto(get(linha, "mascara"))
        if "PERFIL DOBRADO" in mascara:
            c = comp_num or 0
            dobra = "DOBRADEIRA PQ" if c <= 400 else ("DOBRADEIRA 3M" if c <= 3000 else "DOBRADEIRA 6M")
        else:
            dobra = "NÃO"
        if fluxo_dxf is None:
            fluxo_txt, furo_txt, seq = "SEM ROTEIRIZAÇÃO", "SEM ROTEIRIZAÇÃO", "SEM ROTEIRIZAÇÃO"
        else:
            fluxo_txt, furo_txt = fluxo_dxf, ("SIM" if tem_furo else "NÃO")
            seq = _sequencia_pcp(fluxo_dxf, dobra, tem_furo)
        rota = (_rota_chapa_so_pintura(classificar_rota_html(desc, get(linha, "grupo_lic"), nome_perfil, get(linha, "comp"), cod, nome_perfil),
                                       desc, cod, nome_perfil)
                if tem_demanda else "(sem coluna de demanda)")
        saida.append([(obra_trecho if i == ci_obra else (_xl(linha[i]) if i < len(linha) else None))
                      for i in cols_saida] +
                     [esp_calc, chave, fluxo_txt, furo_txt, dobra, seq,
                      "X" if arm else None, "X" if pint else None, "X" if ps else None, "X" if csc else None,
                      "DESCONSIDERAR" if desc_flag else None, _setor_exibicao(rota, nome_perfil, get(linha, "comp")),
                      tipo_pintura_da_ordem(mascara, obra_trecho, _foc_texto(get(linha, "marca")), mapa_pintura)])
        calc.append({"ordem": num, "pos": pos, "chave": chave, "obra_trecho": obra_trecho, "fluxo": fluxo_txt,
                     "seq": seq, "planejador": _foc_texto(get(linha, "planejador")), "espessura": esp_calc,
                     "desconsidera": desc_flag, "ps": "X" if ps else "", "csc": "X" if csc else "", "rota": rota, "desc": desc,
                     "cod_item_dem": _foc_texto(get(linha, "cod_item_demanda")),
                     "qtde_dem": _foc_float(get(linha, "qtde_demanda")) or 0.0})
    return cabecalho, saida, calc


_LOGO_PROJEART_PNG_B64 = (
    "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"
)


def _inserir_imagem_xlsx(caminho, nome_aba, png_bytes, larg_px, alt_px, off_x_px=14, off_y_px=13):
    """Coloca uma imagem PNG no canto A1 de uma aba de um .xlsx já salvo, escrevendo o XML diretamente (não depende do Pillow).
    Devolve True se inseriu."""
    import zipfile
    import xml.sax.saxutils as _sx
    EMU = 9525                                                   # EMUs por pixel
    with zipfile.ZipFile(caminho) as zin:
        nomes = zin.namelist()
        dados = {n: zin.read(n) for n in nomes}
    wbxml = dados["xl/workbook.xml"].decode("utf-8")
    rels_wb = dados["xl/_rels/workbook.xml.rels"].decode("utf-8")
    m = re.search(r'<sheet\b[^>]*\bname="' + re.escape(_sx.escape(nome_aba, {'"': "&quot;"})) + r'"[^>]*>', wbxml)
    rid = re.search(r'r:id="([^"]+)"', m.group(0)).group(1) if m else None
    if not rid:
        return False
    alvo = re.search(r'<Relationship\b[^>]*\bId="' + re.escape(rid) + r'"[^>]*>', rels_wb).group(0)
    destino = re.search(r'Target="([^"]+)"', alvo).group(1)
    caminho_aba = destino.lstrip("/") if destino.startswith("/") else "xl/" + destino
    pasta_aba, arq_aba = caminho_aba.rsplit("/", 1)
    caminho_rels_aba = f"{pasta_aba}/_rels/{arq_aba}.rels"
    # nomes livres para o desenho e a imagem
    k = 1
    while f"xl/drawings/drawing{k}.xml" in dados:
        k += 1
    nome_desenho, nome_img = f"xl/drawings/drawing{k}.xml", "xl/media/logo_projeart.png"
    j = 1
    while nome_img in dados:
        j += 1
        nome_img = f"xl/media/logo_projeart{j}.png"
    cx, cy = larg_px * EMU, alt_px * EMU
    desenho = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<xdr:oneCellAnchor><xdr:from><xdr:col>0</xdr:col>'
        f'<xdr:colOff>{off_x_px * EMU}</xdr:colOff><xdr:row>0</xdr:row><xdr:rowOff>{off_y_px * EMU}</xdr:rowOff></xdr:from>'
        f'<xdr:ext cx="{cx}" cy="{cy}"/>'
        '<xdr:pic><xdr:nvPicPr><xdr:cNvPr id="2" name="Logo Projeart" descr="Logo Projeart"/>'
        '<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr></xdr:nvPicPr>'
        '<xdr:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
        f'<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr></xdr:pic><xdr:clientData/></xdr:oneCellAnchor></xdr:wsDr>')
    rels_desenho = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        f'Target="../media/{nome_img.rsplit("/", 1)[1]}"/></Relationships>')
    # relação da aba -> desenho
    novo_rel = ('<Relationship Id="rIdLogoProjeart" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
                f'Target="../drawings/{nome_desenho.rsplit("/", 1)[1]}"/>')
    if caminho_rels_aba in dados:
        dados[caminho_rels_aba] = dados[caminho_rels_aba].decode("utf-8").replace("</Relationships>", novo_rel + "</Relationships>").encode("utf-8")
    else:
        dados[caminho_rels_aba] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                                   + novo_rel + '</Relationships>').encode("utf-8")
    # elemento <drawing> na aba (antes de legacyDrawing/tableParts/extLst, se existirem; senão no fim)
    xml_aba = dados[caminho_aba].decode("utf-8")
    tag = '<drawing xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rIdLogoProjeart"/>'
    pos = min([i for i in (xml_aba.find(t) for t in ("<legacyDrawing", "<tableParts", "<extLst")) if i >= 0] or [xml_aba.rfind("</worksheet>")])
    dados[caminho_aba] = (xml_aba[:pos] + tag + xml_aba[pos:]).encode("utf-8")
    # tipos de conteúdo
    ct = dados["[Content_Types].xml"].decode("utf-8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Types ", "<Types ", 1)
        ct = re.sub(r"(<Types\b[^>]*>)", r'\1<Default Extension="png" ContentType="image/png"/>', ct, count=1)
    ct = ct.replace("</Types>", f'<Override PartName="/{nome_desenho}" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>')
    dados["[Content_Types].xml"] = ct.encode("utf-8")
    dados[nome_desenho] = desenho.encode("utf-8")
    dados["xl/drawings/_rels/" + nome_desenho.rsplit("/", 1)[1] + ".rels"] = rels_desenho.encode("utf-8")
    dados[nome_img] = png_bytes
    tmp = caminho + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        ordem = ["[Content_Types].xml"] + [n for n in dados if n != "[Content_Types].xml"]
        for n in ordem:
            zout.writestr(n, dados[n])
    os.replace(tmp, caminho)
    return True


def gerar_relatorio_ordens_fluxos(caminho_focco, registros, pasta_saida, log_fn=log):
    """Cruza as ordens/máscara do Focco com os DXF roteirizados (registros) e
    gera o .xlsx de ordens x fluxos em `pasta_saida`. Devolve o caminho."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    caminho_focco = _resolver_arquivo_focco(caminho_focco)
    log_fn(f"📋 Lendo o relatório do Focco: {caminho_focco}")
    ordens = ler_relatorio_focco(caminho_focco)
    focco_linhas = ler_focco_linhas(caminho_focco)
    mapa_pintura = mapa_pintura_por_marca(focco_linhas)       # pintura da peça montada (mesma OF-TRECHO + MARCA) para as ordens sem pintura na máscara
    log_fn(f"📋 Relatório do Focco lido: {len(ordens)} ordem(ns) com posição, {len(focco_linhas['linhas'])} linha(s) no total")

    # índice dos DXF por (OF, posição)
    indice = defaultdict(list)
    for r in registros:
        of_n = str(r["of"] or "").upper().replace("_", "-")
        for v in _pos_variantes(r["pos"]):
            if r not in indice[(of_n, v)]:
                indice[(of_n, v)].append(r)

    usados = set()
    linhas = []
    for o in ordens:
        achados = []
        for v in _pos_variantes(o["pos"]):
            achados = indice.get((o["of"].upper(), v), [])
            if achados:
                break
        for r in achados:
            usados.add(id(r))
        linhas.append((o, achados))

    sem_ordem = [r for r in registros if id(r) not in usados]
    lote_ref = next((o["lote"] for o in ordens if o["lote"]), None)

    cabecalho = ["LOTE OF", "NUM ORDEM", "TP ORD", "DT EMISSAO", "OBRA", "SUB TRECHO", "OF-TRECHO", "POSIÇÃO",
                 "FLUXO", "CENTRO DE CUSTO", "CORTE", "FURO", "DOBRA", "MATERIAL", "ESPESSURA (mm)",
                 "LARGURA (mm)", "ALTURA (mm)", "PESO UNITÁRIO (kg)", "PESO TOTAL (kg)", "ARQUIVO(S) DXF",
                 "STATUS", "QTDE (ORDEM)", "MARCA", "COD ITEM", "DESCRIÇÃO DO ITEM", "GRUPO LIC",
                 "PLANEJADOR", "SEQUÊNCIA DE ROTEIRO", "TEM FURO?", "OBSERVAÇÃO", "SETOR", "TIPO DE PINTURA"]

    def montar_linha(o, achados):
        mk = parse_mascara_focco(o["mascara"]) if o else {"dobrado": False}
        r = achados[0] if achados else None
        tem_dxf = r is not None
        # peça dividida em partes (110-2[A] + 110-2[B]): o relatório soma o comprimento e o peso das partes
        partes_a = [a for a in achados if a.get("parte")]
        letras_partes = sorted({a["parte"] for a in partes_a})
        dividida = len(letras_partes) >= 2 and all(a["largura_dxf"] is not None and a["altura_dxf"] is not None
                                                   for a in partes_a)
        rota = _rota_da_ordem(o) if o else None
        if tem_dxf:
            fluxo_perf = None
        elif rota:                                   # rota pelo HTML (perfiladeiras, joist, acessório padrão...)
            fluxo_perf = _ROTA_PARA_FLUXO.get(rota)
        else:                                        # relatório sem coluna de demanda: regra do planejador
            fluxo_perf = _fluxo_perfilado_do_planejador(o)
        esp = (r["esp"] if tem_dxf and r["esp"] else None) or (o["esp"] if o else None) or mk.get("esp") \
            or (_esp_do_nome(o["nome_perfil"]) or _esp_do_nome(o["desc_item"]) if o else None)
        material = (o["material"] if o and o["material"] else "") or (r["material"] if tem_dxf and r["material"] else "") \
            or mk.get("material") or "-"
        if tem_dxf and dividida:
            larg = sum(max(a["largura_dxf"], a["altura_dxf"]) for a in partes_a)
            alt = max(min(a["largura_dxf"], a["altura_dxf"]) for a in partes_a)
            peso_unit = sum(calcular_peso(a["largura_dxf"], a["altura_dxf"], esp) for a in partes_a) if esp else None
        elif tem_dxf and r["largura_dxf"] is not None and r["altura_dxf"] is not None:
            larg = max(r["largura_dxf"], r["altura_dxf"])
            alt = min(r["largura_dxf"], r["altura_dxf"])
            peso_unit = calcular_peso(r["largura_dxf"], r["altura_dxf"], esp) if esp else None
        else:
            larg = (o["comp"] if o and o["comp"] else None) or mk.get("comp")
            alt = (o["larg"] if o and o["larg"] else None) or mk.get("larg")
            peso_unit = mk.get("peso")
        qtde_ordem = o["qtde"] if o else None
        if tem_dxf:
            qtd = r["qtd_dxf"] if r["qtd_dxf"] is not None else (qtde_ordem or r["qtd_planilha"] or 1)
        else:
            qtd = qtde_ordem
        peso_total = peso_unit * qtd if (peso_unit is not None and qtd is not None) else None
        if tem_dxf:
            fluxo = r["fluxo_final"] or "SEM FLUXO"
            tem_furo = any((a["quantidade_furos"] or 0) > 0 for a in achados)
            comp_dobra = (o["comp"] if o and o["comp"] else None) or mk.get("comp") or larg
            if r["fluxo_final"]:
                centro, corte, furo, dobra, seq = _sequencia_e_maquinas(fluxo, tem_furo, _regra_dobra(mk, comp_dobra))
            else:
                centro, corte, furo, dobra, seq = "-", "-", "-", "-", "SEM ROTEIRIZAÇÃO"
            tem_furo_txt = "SIM" if tem_furo else "NÃO"
            status = "✅ Tem DXF"
        elif fluxo_perf:
            fluxo = fluxo_perf
            centro, corte, furo, dobra, seq = _sequencia_e_maquinas(fluxo, False, "NÃO")
            tem_furo_txt = "-"
            status = "🔷 Rota automática (sem DXF)"
        elif rota and rota not in _ROTAS_PREP:       # outras rotas automáticas (armação, pintura, laminados...)
            fluxo, centro, corte, furo, dobra, seq, tem_furo_txt = "-", "-", "-", "-", "-", "-", "-"
            status = "🔷 Rota automática (sem DXF)"
        else:
            fluxo, centro, corte, furo, dobra, seq, tem_furo_txt = "-", "-", "-", "-", "-", "-", "-"
            status = "❌ Sem DXF ainda"
        arquivos = ", ".join(dict.fromkeys(a["arquivo"] for a in achados)) if achados else "-"
        if o:
            ident = [o["lote"] or "-", o["num_ordem"], o["tp_ord"], o["dt_emissao"], o["obra"] or "-",
                     o["sub_trecho"] or "-", o["of"] or "-", o["pos"]]
            extra = [qtde_ordem if qtde_ordem is not None else "-", o["marca"] or "-", o["cod_item"] or "-",
                     o["desc_item"] or "-", o["grupo_lic"] or "-", o["planejador"] or "-"]
            obs = ""
        else:
            partes = str(r["of"]).split("-", 1)
            ident = [lote_ref or "-", "-", "-", "-", partes[0], partes[1] if len(partes) > 1 else "-",
                     r["of"], r["pos"]]
            cod_est, desc_est = _item_estoque_acessorio(r["pos"]) or ("-", "-")     # SD1 / SEZ1-4: item de estoque pelo HTML
            extra = ["-", "-", cod_est, desc_est, "-", "-"]
            obs = "Sem ordem no relatório do Focco"
        if dividida:
            nota_div = f"Peça dividida em partes [{'+'.join(letras_partes)}]: comprimento e peso somados"
            fluxos_partes = {a["fluxo_final"] for a in partes_a if a.get("fluxo_final")}
            if len(fluxos_partes) > 1 or any(not a.get("fluxo_final") for a in partes_a):
                nota_div += " | partes em fluxos diferentes: " + ", ".join(
                    f"[{a['parte']}]={a.get('fluxo_final') or 'SEM FLUXO'}" for a in partes_a)
            obs = (obs + " | " if obs else "") + nota_div
        elif len(letras_partes) == 1:
            obs = (obs + " | " if obs else "") + (f"Só a parte [{letras_partes[0]}] foi encontrada - "
                                                   "confira se falta a outra parte (ex: [B])")
        esp_txt = f"{esp:.2f}".replace(".", ",") if esp else "-"
        return (ident + [fluxo, centro, corte, furo, dobra, material, esp_txt, _num_limpo(larg), _num_limpo(alt),
                         _num_limpo(peso_unit, 4), _num_limpo(peso_total, 4), arquivos, status] + extra
                + [seq, tem_furo_txt, obs,
                   (_setor_exibicao(rota, (o["nome_perfil"] or o["desc_item"]) if o else "", o["comp"] if o else None) or "-"),
                   tipo_pintura_da_ordem(o["mascara"], o["of"], o["marca"], mapa_pintura) if o else "-"])

    pares = [(montar_linha(o, a), o, a) for o, a in linhas]
    pares.sort(key=lambda p: (p[0][1] if isinstance(p[0][1], int) else 0, str(p[0][6]), str(p[0][7])))
    pares += [(montar_linha(None, [r]), None, [r]) for r in sorted(sem_ordem, key=lambda x: (str(x["of"]), str(x["pos"])))]
    dados = [p[0] for p in pares]
    ordens_da_linha = [p[1] for p in pares]
    i_pos_d, i_marca_d = cabecalho.index("POSIÇÃO"), cabecalho.index("MARCA")
    flags_marca = [_marca_pos_desconsiderar(l[i_pos_d]) or _marca_pos_desconsiderar(l[i_marca_d]) for l in dados]    # SD1 / SEZ1-4
    flags_pintura = [_ordem_de_pintura(o) or fm for o, fm in zip(ordens_da_linha, flags_marca)]     # para desconsiderar: só na aba própria
    dados_pintura = [l for l, f in zip(dados, flags_pintura) if f]
    flags_ps = [(not f) and _ordem_ps_prep(o) for o, f in zip(ordens_da_linha, flags_pintura)]    # PS PREP: aba própria
    dados_ps = [l for l, f in zip(dados, flags_ps) if f]
    dados_resumo = [l for l, a, b in zip(dados, flags_pintura, flags_ps) if not a and not b]     # o que entra nos totais do Resumo

    # ---- separação em abas: FLUXOS (1-4 e LASER) x NÃO PREPARAÇÃO ----
    ordem_fluxos = {"FLUXO 1": 1, "FLUXO 2": 2, "FLUXO 3": 3, "FLUXO 4": 4, "LASER": 5}

    def classe_da_linha(l):
        """'fluxos' = fluxos de preparação (1, 2, 3, 4, LASER); 'nao_prep' = o que NÃO é
        preparação (perfilados, acessórios, arremates...); 'prep_pendente' = é preparação,
        mas ainda sem fluxo (sem DXF, ou DXF fora de qualquer fluxo)."""
        fluxo = _norm_cab(l[8])
        if fluxo in ordem_fluxos:
            return "fluxos"
        rota = l[30]
        if rota not in (None, "-"):                   # ROTA do HTML: preparação x rota automática
            return "prep_pendente" if rota in _ROTAS_PREP else "nao_prep"
        if l[9] not in ("-", "PREPARAÇÃO"):          # centro de custo diferente de preparação
            return "nao_prep"
        planej = _norm_cab(l[26])                     # PLANEJADOR do Focco (PL-001 = preparação)
        cod = str(l[23] or "").upper()
        if "PREPARACAO" in planej or "_PREP" in cod or l[26] == "-" and l[20].startswith("✅"):
            return "prep_pendente"                    # inclui DXF solto/sem fluxo
        return "nao_prep"

    classes = [classe_da_linha(l) for l in dados]
    dados_fluxos = sorted((l for l, c, pf, ps_ in zip(dados, classes, flags_pintura, flags_ps) if c == "fluxos" and not pf and not ps_),
                          key=lambda l: (ordem_fluxos[_norm_cab(l[8])], l[1] if isinstance(l[1], int) else 0, str(l[7])))
    dados_nao_prep = sorted((l for l, c, pf, ps_ in zip(dados, classes, flags_pintura, flags_ps) if c == "nao_prep" and not pf and not ps_),
                            key=lambda l: (str(l[8]), l[1] if isinstance(l[1], int) else 0, str(l[7])))
    dados_ps = sorted(dados_ps, key=lambda l: (str(l[8]), l[1] if isinstance(l[1], int) else 0, str(l[7])))

    def rotular_estoque(l):
        """Linha SEM ordem no Focco (DXF de ordem de estoque / ordem manual): NUM ORDEM = 'ORDEM MANUAL' e SETOR = 'ESTOQUE'
        (antes ficavam só com hífen). Só muda o que aparece nas abas; a classificação já foi feita com os valores originais."""
        if l[1] == "-":
            nl = list(l)
            nl[1] = "ORDEM MANUAL"
            if nl[30] in (None, "-"):
                nl[30] = "ESTOQUE"
            return nl
        return l
    dados_fluxos = [rotular_estoque(l) for l in dados_fluxos]
    dados_nao_prep = [rotular_estoque(l) for l in dados_nao_prep]
    n_pendentes = sum(1 for c, pf, ps_ in zip(classes, flags_pintura, flags_ps) if c == "prep_pendente" and not pf and not ps_)

    # ---- ROTEIRIZAÇÃO FOCCO: mesmas regras da planilha PCP ----
    # Só entram ordens NÃO desconsideradas (armação/limpeza ou pintura/lanternim) e com
    # SEQUÊNCIA DE ROTEIRO válida (diferente de vazio e de "SEM ROTEIRIZAÇÃO"). Uma
    # linha por linha de demanda, como no pivô da planilha. O que ficou de fora vai
    # para a aba de conferência, com o motivo.
    tem_demanda = any(o is not None and o["tem_col_demanda"] for o in ordens_da_linha)
    lista_focco, conferencia = [], []
    contagem_sit = defaultdict(int)
    contagem_rota_auto = 0
    for linha, o, classe, fm in zip(dados, ordens_da_linha, classes, flags_marca):
        if o is None:
            continue
        fluxo = linha[8]
        rota = re.sub(r"^(PERFILADEIRA L)[12]$", r"\1", str(linha[30])) if linha[30] is not None else None   # L1/L2 -> rota-base
        dem = o["demandas"]
        desc_it = o["nome_perfil"] or o["desc_item"]
        livres = [d for d in dem if not _flag_desconsiderar(d, o["cod_item"], desc_it)]
        desconsidera = ((not livres) if dem else _flag_desconsiderar("", o["cod_item"], desc_it)) or fm
        if desconsidera:
            contagem_sit["➖ Desconsideradas (armação/limpeza, pintura/lanternim ou marcas SD1/SEZ)"] += 1
            continue
        chave = f"{o['of']}_{o['pos']}"
        tem_furo = linha[28] == "SIM"
        dobra = linha[12] if str(linha[12]).startswith("DOBRADEIRA") else "NÃO"
        tem_dxf_fluxo = fluxo not in ("-", "SEM FLUXO") and str(linha[20]).startswith("✅")
        seq = "SEM ROTEIRIZAÇÃO" if not tem_dxf_fluxo else _sequencia_pcp(fluxo, dobra, tem_furo)
        if seq not in ("", "SEM ROTEIRIZAÇÃO"):
            contagem_sit["✅ Roteirizado (sequência válida)"] += 1
            lista_focco.append((seq, o["num_ordem"], o["pos"], _demanda_principal(livres), o["planejador"] or "-", o["of"], fluxo))   # só a POSIÇÃO (a obra/trecho vai em "OBRA E TRECHO")
        # ---- conferência: o que o roteirizador fez x o que as regras (HTML + planilha) esperam ----
        problemas = []
        esp_n = _foc_float(linha[14])
        maior_dim = _foc_float(linha[15])
        if rota in _ROTAS_PREP:
            if not tem_dxf_fluxo:
                problemas.append(("❌ Sem roteirização",
                                  "DXF encontrado, mas fora de qualquer pasta de fluxo" if fluxo == "SEM FLUXO"
                                  else f"Rota {rota}: ordem de preparação sem DXF roteirizado"))
            elif _norm_cab(fluxo) not in _FLUXOS_PREP_NORM:
                problemas.append(("⚠️ Rota diferente do HTML",
                                  f"HTML: {rota} (preparação), mas o DXF está em {fluxo}"))
            elif seq == "":
                problemas.append(("⚠️ Sequência sem regra",
                                  f"Combinação {fluxo} + {dobra} + furação {'SIM' if tem_furo else 'NÃO'} não está prevista na regra"))
        elif rota in _ROTA_PARA_FLUXO:
            esperado = _ROTA_PARA_FLUXO[rota]
            contagem_rota_auto += 1
            if tem_dxf_fluxo and re.sub(r"^(PERFILADEIRA L)[12]$", r"\1", _norm_cab(fluxo)) != _norm_cab(esperado):
                curta = (_norm_cab(fluxo) == "FLUXO 4" and rota == "PERFILADEIRA U/C"
                         and maior_dim is not None and maior_dim < 700 and esp_n is not None and esp_n <= 3.00)
                if curta:
                    problemas.append(("ℹ️ Regra de máquina",
                                      f"HTML: {rota}, mas a peça é curta (<700mm, até 3mm) e foi para {fluxo} (regra de peça curta)"))
                else:
                    problemas.append(("⚠️ Rota diferente do HTML",
                                      f"HTML: {rota} (esperado: {esperado}), mas o DXF está em {fluxo}"))
        elif rota is not None:
            contagem_rota_auto += 1
            if tem_dxf_fluxo:
                problemas.append(("ℹ️ DXF em rota automática",
                                  f"HTML: {rota} (roteiro automático), mas existe DXF roteirizado em {fluxo}"))
        else:                                         # relatório sem coluna de demanda: regra antiga (planejador)
            if seq == "SEM ROTEIRIZAÇÃO" and classe == "prep_pendente":
                problemas.append(("❌ Sem roteirização", "Ordem de preparação sem DXF roteirizado"))
            elif seq == "" and _norm_cab(fluxo) in _FLUXOS_PREP_NORM:
                problemas.append(("⚠️ Sequência sem regra",
                                  f"Combinação {fluxo} + {dobra} + furação {'SIM' if tem_furo else 'NÃO'} não está prevista na regra"))
        if "partes em fluxos diferentes" in str(linha[29]):
            problemas.append(("⚠️ Partes A/B em fluxos diferentes", str(linha[29])))
        for situ, motivo in problemas:
            contagem_sit[situ] += 1
            conferencia.append((situ, motivo, o["num_ordem"], chave, o["planejador"] or "-", o["cod_item"] or "-",
                                fluxo, dobra if fluxo not in ("-", "SEM FLUXO") else "-", linha[28], seq or "-",
                                rota or "-", linha[19]))
    contagem_sit["🔷 Rota automática (não precisa roteirizar)"] = contagem_rota_auto
    lista_focco.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    prioridade_sit = {"❌": 0, "⚠": 1, "ℹ": 2}
    conferencia.sort(key=lambda t: (prioridade_sit.get(t[0][0], 9), t[0], t[2]))

    cores = {"✅": PatternFill("solid", fgColor="D9EAD3"), "🔷": PatternFill("solid", fgColor="DDEBF7"),
             "❌": PatternFill("solid", fgColor="F4CCCC")}
    larguras = [9, 11, 8, 12, 7, 12, 13, 14, 18, 18, 22, 22, 18, 22, 16, 14, 13, 20, 17, 44, 22,
                13, 12, 18, 30, 24, 28, 44, 11, 30, 26, 34]      # a última = TIPO DE PINTURA

    # A coluna DT EMISSAO (índice 3) nunca sai no Excel. Internamente a linha mantém a mesma
    # estrutura (os índices usados nas regras não mudam); as colunas só são escolhidas aqui.
    COL_FORA = 3
    idx_status = cabecalho.index("STATUS")

    def escrever_aba(ws, linhas_aba, manter=None, excluir=(), mover=None, renomear=None):
        if manter is not None:
            idxs = [cabecalho.index(h) for h in manter if h in cabecalho]
        else:
            idxs = [i for i, h in enumerate(cabecalho) if i != COL_FORA and h not in excluir]
        if mover:                                    # mover=("coluna", "antes_desta") ou lista de pares: reposiciona colunas
            for col_m, antes_m in ([mover] if isinstance(mover[0], str) else mover):
                i_col, i_ref = cabecalho.index(col_m), cabecalho.index(antes_m)
                if i_col in idxs and i_ref in idxs:
                    idxs.remove(i_col)
                    idxs.insert(idxs.index(i_ref), i_col)
        ws.append([(renomear or {}).get(cabecalho[i], cabecalho[i]) for i in idxs])      # renomear: só o título muda
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="003366")
        pos_status = idxs.index(idx_status) + 1 if idx_status in idxs else None
        for linha in linhas_aba:
            ws.append([linha[i] for i in idxs])
            if pos_status:
                ws.cell(ws.max_row, pos_status).fill = cores[linha[20][0]]
        for j, i in enumerate(idxs, 1):
            ws.column_dimensions[get_column_letter(j)].width = larguras[i]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(idxs))}{max(ws.max_row, 2)}"

    def cabecalho_concatenar(ws, cel):
        """Título azul-claro, negrito e centralizado da 'FÓRMULA DE CONCATENAR' (como na planilha PCP)."""
        ws[cel] = "FÓRMULA DE CONCATENAR"
        ws[cel].font = Font(bold=True)
        ws[cel].fill = PatternFill("solid", fgColor="9DC3E6")
        lado = Side(style="thin", color="000000")
        ws[cel].border = Border(left=lado, right=lado, top=lado, bottom=lado)

    def moldura_quadro(ws_q, faixa, cor="000000"):
        """Contorno fino em volta de uma faixa mesclada (cada célula da borda recebe o seu lado): o 'quadro' do título/fórmula."""
        lado_q = Side(style="thin", color=cor)
        cels = ws_q[faixa]
        n_lin, n_col = len(cels), len(cels[0])
        for i_q, linha_q in enumerate(cels):
            for j_q, cel_q in enumerate(linha_q):
                cel_q.border = Border(top=lado_q if i_q == 0 else None, bottom=lado_q if i_q == n_lin - 1 else None,
                                      left=lado_q if j_q == 0 else None, right=lado_q if j_q == n_col - 1 else None)

    def topo_sem_linhas(ws_q, ultima_coluna=40):
        """Linhas 1 a 5 com fundo branco: some a grade nessa área, ficando só o painel da logo e os quadros das fórmulas.
        Pinta cada célula até a coluna `ultima_coluna` e também a LINHA INTEIRA (formato da linha), para cobrir qualquer coluna além."""
        branco_q = PatternFill("solid", fgColor="FFFFFF")
        for lin_q in range(1, 6):
            ws_q.row_dimensions[lin_q].fill = branco_q
            for col_q in range(1, ultima_coluna + 1):
                cel_q = ws_q.cell(row=lin_q, column=col_q)
                if cel_q.fill is None or cel_q.fill.fill_type is None:
                    cel_q.fill = branco_q

    wb = Workbook()
    ws = wb.active
    ws.title = "Ordens x DXF"
    # "Ordens x DXF": primeiro o que tem Fluxo 1, 2, 3, 4 (e LASER), em ordem de fluxo; abaixo o restante,
    # organizado pela DESCRIÇÃO DO ITEM (e dentro dela por fluxo, obra/trecho e posição).
    i_desc = cabecalho.index("DESCRIÇÃO DO ITEM")

    def chave_ordens_dxf(l):
        fluxo_n = _norm_cab(l[8])
        num = l[1] if isinstance(l[1], int) else 0
        if fluxo_n in ordem_fluxos:
            return (0, ordem_fluxos[fluxo_n], "", "", num, str(l[7]))
        desc = str(l[i_desc] or "-").strip().upper()
        return (1, 0, "~" if desc in ("", "-") else desc, str(l[8]), str(l[6]), str(l[7]), num)

    escrever_aba(ws, sorted(dados, key=chave_ordens_dxf),                 # tudo (completo)
                 mover=("ESPESSURA (mm)", "FLUXO"))                       # espessura depois da posição e antes do fluxo
    escrever_aba(wb.create_sheet("Preparação"), dados_fluxos, excluir=_COLUNAS_FORA_PREPARACAO,
                 mover=[("SEQUÊNCIA DE ROTEIRO", "NUM ORDEM"),    # sequência logo antes do NUM ORDEM
                        ("FLUXO", "SEQUÊNCIA DE ROTEIRO"),        # fluxo logo antes da sequência
                        ("ESPESSURA (mm)", "CENTRO DE CUSTO"),    # espessura logo depois da posição
                        ("OF-TRECHO", "FLUXO")],                  # OF-TRECHO logo depois do LOTE
                 renomear={"LOTE OF": "LOTE"})
    escrever_aba(wb.create_sheet("Não Preparação"), dados_nao_prep, manter=_COLUNAS_NAO_PREPARACAO, renomear={"LOTE OF": "LOTE"})

    # ---- Não Preparação e PS PREP: MESMO ESTILO da ROTEIRIZAÇÃO FOCCO (logo no topo, campos de concatenar, cabeçalho azul-claro na
    #      linha 6), com as mesmas colunas de antes. Não tem FLUXO nessas abas: o filtro que alimenta os campos é o do SETOR (ou
    #      qualquer outra coluna). As contas auxiliares ficam na aba oculta (coluna 3 = Não Preparação, 4 = PS PREP). ----
    def painel_estilo_focco(ws_p, nome_aba, n_dados, col_aux):
        aux = wb[_ABA_AUX_CONCATENAR] if _ABA_AUX_CONCATENAR in wb.sheetnames else wb.create_sheet(_ABA_AUX_CONCATENAR)
        ws_p.insert_rows(1, 5)                           # abre o espaço do topo: cabeçalho passa para a linha 6
        ultima_p = max(7, 6 + n_dados)
        cab_p = [c.value for c in ws_p[6]]
        col_ordem_p = get_column_letter(cab_p.index("NUM ORDEM") + 1)
        azul_claro_p = PatternFill("solid", fgColor="BDE0F4")
        lado_p = Side(style="thin", color="9DC3E6")
        for c in ws_p[6]:
            c.fill = azul_claro_p
            c.font = Font(bold=True)
            c.border = Border(bottom=lado_p)
        ws_p.row_dimensions[6].height = 30
        ws_p.merge_cells("A1:D5")                        # painel da logo (inserida depois de salvar)
        for lin_p in range(1, 6):
            for col_p in range(1, 5):
                ws_p.cell(row=lin_p, column=col_p).border = Border(top=lado_p if lin_p == 1 else None, bottom=lado_p if lin_p == 5 else None,
                                                                   left=lado_p if col_p == 1 else None, right=lado_p if col_p == 4 else None)
        ref_p = f"'{nome_aba}'!"
        letra_aux = get_column_letter(col_aux)
        for k in range(7, ultima_p + 1):                 # ordens VISÍVEIS acumuladas (muda com o filtro)
            d_k = f"{ref_p}{col_ordem_p}{k}"
            aux.cell(row=k, column=col_aux, value=(f'=IF(AND(SUBTOTAL(103,{d_k})=1,ISNUMBER({d_k})),{d_k}&"","")' if k == 7 else
                                                   f'={letra_aux}{k - 1}&IF(AND(SUBTOTAL(103,{d_k})=1,ISNUMBER({d_k})),IF({letra_aux}{k - 1}="","",",")&{d_k},"")'))
        aux.cell(row=1, column=col_aux, value=f"{nome_aba} (ordens visíveis, acumuladas)")
        faixa_ordem = f"{col_ordem_p}7:{col_ordem_p}{ultima_p}"
        cabecalho_concatenar(ws_p, "E1")                 # FILTRO (E:G): vazio sem filtro; filtrando (ex.: por SETOR) lista as ordens visíveis
        ws_p["E1"] = "FÓRMULA DE CONCATENAR (FILTRO)"
        ws_p.merge_cells("E1:G1")
        ws_p.merge_cells("E2:G2")
        ws_p["E2"] = f'=IF(SUBTOTAL(103,{faixa_ordem})=COUNTA({faixa_ordem}),"",\'{_ABA_AUX_CONCATENAR}\'!{letra_aux}{ultima_p})'
        cabecalho_concatenar(ws_p, "I1")                 # TODAS (I:K): tudo sem filtro; filtrando, só o que ficou visível. Coluna H = espaço
        ws_p["I1"] = "FÓRMULA DE CONCATENAR (TODAS)"
        ws_p.merge_cells("I1:K1")
        ws_p.merge_cells("I2:K2")
        ws_p["I2"] = f"='{_ABA_AUX_CONCATENAR}'!{letra_aux}{ultima_p}"
        for cel_p in ("E2", "I2"):
            ws_p[cel_p].alignment = Alignment(wrap_text=True, horizontal="center", vertical="top")
        ws_p.row_dimensions[2].height = 48
        for faixa_q in ("E1:G1", "E2:G2", "I1:K1", "I2:K2"):
            moldura_quadro(ws_p, faixa_q)                # só os quadros das fórmulas ficam com linha
        topo_sem_linhas(ws_p)                            # e o resto do topo fica sem a grade
        ws_p.sheet_view.zoomScale = 110
        ws_p.freeze_panes = "A7"
        ws_p.auto_filter.ref = f"A6:{get_column_letter(ws_p.max_column)}{ultima_p}"

    painel_estilo_focco(wb["Não Preparação"], "Não Preparação", len(dados_nao_prep), 3)

    # ---- PS PREP: as ordens de perfil soldado (preparação) saem da Não Preparação e ficam nesta aba, com as mesmas colunas ----
    escrever_aba(wb.create_sheet(_ABA_PS_PREP), dados_ps, manter=_COLUNAS_NAO_PREPARACAO, renomear={"LOTE OF": "LOTE"})
    painel_estilo_focco(wb[_ABA_PS_PREP], _ABA_PS_PREP, len(dados_ps), 4)

    # ---- ORDENS PARA DESCONSIDERAR: as ordens de pintura/galvânica e as marcas/posições SD1 e SEZ1-SEZ4 saem das abas de impressão e ficam só aqui ----
    ws_pint = wb.create_sheet(_ABA_PINTURA)
    ws_pint.sheet_properties.tabColor = "C00000"                    # aba vermelha: não imprimir
    cols_pint = ["LOTE OF", "OF-TRECHO", "NUM ORDEM", "POSIÇÃO", "GRUPO LIC", "COD ITEM", "DESCRIÇÃO DO ITEM", "MATERIAL",
                 "ESPESSURA (mm)", "QTDE (ORDEM)", "PESO UNITÁRIO (kg)", "PESO TOTAL (kg)", "TIPO DE PINTURA", "PLANEJADOR"]
    ws_pint.append([("LOTE" if h == "LOTE OF" else h) for h in cols_pint] + ["DEMANDA DA ORDEM (TINTA / ZINCO...)", "MOTIVO"])
    for c in ws_pint[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="C00000")
    idx_pint = [cabecalho.index(h) for h in cols_pint]
    linhas_pint = []
    for l, o, f_d in zip(dados, ordens_da_linha, flags_pintura):
        if f_d:
            dem = " | ".join(dict.fromkeys(str(d).strip() for d in ((o or {}).get("demandas") or []) if str(d or "").strip()))
            if not o and not dem and l[cabecalho.index("DESCRIÇÃO DO ITEM")] not in (None, "-"):
                dem = str(l[cabecalho.index("DESCRIÇÃO DO ITEM")])                  # item de estoque: "SD1 ESTOQUE"
            motivo = "ORDEM DE PINTURA / GALVÂNICA" if _ordem_de_pintura(o) else "MARCA / POSIÇÃO SD1 / SEZ1-SEZ4"
            lin_p = [l[i] for i in idx_pint] + [dem or "-", motivo]
            if not o:                                                                 # sem ordem no Focco = ORDEM MANUAL
                lin_p[cols_pint.index("NUM ORDEM")] = "ORDEM MANUAL"
            linhas_pint.append(lin_p)
    linhas_pint.sort(key=lambda r: (str(r[1]), str(r[3]), r[2] if isinstance(r[2], int) else 0))
    for r_p in linhas_pint:
        ws_pint.append(r_p)
    for j, w in enumerate([9, 14, 12, 22, 20, 16, 30, 16, 14, 13, 16, 16, 34, 36, 60, 34], 1):
        ws_pint.column_dimensions[get_column_letter(j)].width = w
    ws_pint.freeze_panes = "A2"
    ws_pint.auto_filter.ref = f"A1:{get_column_letter(len(cols_pint) + 2)}{max(ws_pint.max_row, 2)}"

    # ---- aba ROTEIRIZAÇÃO FOCCO: igual à da planilha PCP, SEM o bloco de filtros (PLANEJADOR / OBRA E TRECHO / FLUXO DE
    #      PRODUÇÃO / ORDENS PARA DESCONSIDERAR): a lista já vem tratada, só com o que é Fluxo 1, 2, 3 e 4 ----
    rf = wb.create_sheet("ROTEIRIZAÇÃO FOCCO")
    azul = PatternFill("solid", fgColor="003366")           # usado pela aba de conferência
    azul_claro = PatternFill("solid", fgColor="BDE0F4")
    lado_rf = Side(style="thin", color="9DC3E6")
    ultima = max(7, 6 + len(lista_focco))
    # FÓRMULA DE CONCATENAR (ativa, sem precisar de TEXTJOIN): fica VAZIA enquanto nenhuma linha estiver filtrada; ao filtrar a
    # tabela, junta (separadas por vírgula) as ORDENS que ficaram visíveis. Usa a coluna auxiliar I (oculta), que vai
    # acumulando as ordens visíveis linha a linha - funciona em qualquer versão do Excel.
    # painel do topo (A1:C5): "tela" de abertura da aba, com a logo da Projeart (inserida após salvar) e o nome da aba/lote à direita
    rf.merge_cells("A1:C5")                   # só a logo (inserida depois de salvar): sem texto ao lado
    lado_painel = Side(style="thin", color="9DC3E6")
    for lin_p in range(1, 6):
        for col_p in range(1, 4):
            rf.cell(row=lin_p, column=col_p).border = Border(top=lado_painel if lin_p == 1 else None,
                                                             bottom=lado_painel if lin_p == 5 else None,
                                                             left=lado_painel if col_p == 1 else None,
                                                             right=lado_painel if col_p == 3 else None)
    cabecalho_concatenar(rf, "D1")
    rf["D1"] = "FÓRMULA DE CONCATENAR (FILTRO)"
    rf.merge_cells("D1:F1")                   # título e fórmula ocupam D:F (3 colunas): área ampla para a lista de ordens
    rf.merge_cells("D2:F2")
    aux = wb[_ABA_AUX_CONCATENAR]                        # aba oculta (criada pelo painel da Não Preparação)
    ref_rf = "'ROTEIRIZAÇÃO FOCCO'!"
    rf["D2"] = (f'=IF(SUBTOTAL(103,D7:D{ultima})=COUNTA(D7:D{ultima}),"",'
                f"'{_ABA_AUX_CONCATENAR}'!A{ultima})")
    rf["D2"].alignment = Alignment(wrap_text=True, horizontal="center", vertical="top")     # lista longa: começa pelas primeiras ordens
    rf.row_dimensions[2].height = 48
    aux["A1"] = "ROTEIRIZAÇÃO FOCCO (ordens visíveis, acumuladas)"
    for k in range(7, ultima + 1):
        d_k = f"{ref_rf}D{k}"
        aux.cell(row=k, column=1, value=(f'=IF(SUBTOTAL(103,{d_k})=1,{d_k}&"","")' if k == 7 else
                                         f'=A{k - 1}&IF(SUBTOTAL(103,{d_k})=1,IF(A{k - 1}="","",",")&{d_k},"")'))
    # segundo campo: TODAS - sem nada filtrado traz todas as ordens (imprimir tudo de uma vez); filtrando (ex.: uma obra), só as
    # ordens que ficaram visíveis. Fica em H:I, com a
    # coluna G vazia entre os dois campos, para não misturar com o FILTRO (D:F)
    cabecalho_concatenar(rf, "H1")
    rf["H1"] = "FÓRMULA DE CONCATENAR (TODAS)"
    rf.merge_cells("H1:I1")
    rf.merge_cells("H2:I2")
    rf["H2"] = f"='{_ABA_AUX_CONCATENAR}'!A{ultima}"
    rf["H2"].alignment = Alignment(wrap_text=True, horizontal="center", vertical="top")
    rf.column_dimensions["H"].width = 38
    rf.column_dimensions["I"].width = 38
    for faixa_q in ("D1:F1", "D2:F2", "H1:I1", "H2:I2"):
        moldura_quadro(rf, faixa_q)                      # só os quadros das fórmulas ficam com linha
    topo_sem_linhas(rf)                                  # e o resto do topo fica sem a grade
    titulos_rf = ["SEQUÊNCIA DE ROTEIRO", "OBRA E TRECHO", "POSIÇÃO", "ORDEM", "FLUXO DE PRODUÇÃO", "DESC TECNICA DEMANDA",
                  "PLANEJADOR"]
    for j, h in enumerate(titulos_rf, 1):                     # cabeçalho na linha 6 (azul-claro, negrito), como na planilha
        c = rf.cell(row=6, column=j, value=h)
        c.font = Font(bold=True)
        c.fill = azul_claro
        c.border = Border(bottom=lado_rf)
    rf.row_dimensions[6].height = 30
    for k, t in enumerate(lista_focco, 7):    # t = (sequência, ordem, posição, descrição, planejador, obra e trecho, fluxo)
        for j, v in enumerate([t[0], t[5], t[2], t[1], t[6], t[3], t[4]], 1):
            rf.cell(row=k, column=j, value=v)
    for i, w in enumerate(_LARGURAS_ROTEIRIZACAO_FOCCO, 1):
        rf.column_dimensions[get_column_letter(i)].width = w
    rf.sheet_view.zoomScale = 110
    rf.freeze_panes = "A7"
    rf.auto_filter.ref = f"A6:G{ultima}"

    # ---- aba de conferência: o que NÃO ficou roteirizado certo ----
    cf = wb.create_sheet("Conferência Roteirização")
    cab_cf = ["SITUAÇÃO", "MOTIVO", "NUM ORDEM", "OBRA E TRECHO_POSIÇÃO", "PLANEJADOR", "COD ITEM", "FLUXO",
              "DOBRA", "TEM FURO?", "SEQUÊNCIA DE ROTEIRO", "SETOR", "ARQUIVO(S) DXF"]
    cf.append(cab_cf)
    for c in cf[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = azul
        c.alignment = Alignment(horizontal="center")
    cores_cf = {"❌": PatternFill("solid", fgColor="F4CCCC"), "⚠": PatternFill("solid", fgColor="FFF2CC"),
                "ℹ": PatternFill("solid", fgColor="DDEBF7")}
    for t in conferencia:
        cf.append(list(t))
        cf.cell(cf.max_row, 1).fill = cores_cf.get(t[0][0], PatternFill())
    for i, w in enumerate([28, 78, 12, 26, 36, 18, 22, 20, 11, 48, 26, 44], 1):
        cf.column_dimensions[get_column_letter(i)].width = w
    cf.freeze_panes = "A2"
    cf.auto_filter.ref = f"A1:L{max(cf.max_row, 2)}"

    # ---- BASE DE DADOS: todas as colunas do Focco + colunas calculadas (regras da planilha PCP) ----
    mapa_ordem = {}
    for linha_p, o_p, ach_p in pares:
        if o_p is not None:
            fl_p = _nome_fluxo_pcp(ach_p[0]["fluxo_final"]) if ach_p and ach_p[0].get("fluxo_final") else None
            furo_p = any((x.get("quantidade_furos") or 0) > 0 for x in (ach_p or []))
            mapa_ordem[(o_p["num_ordem"], o_p["obra"], o_p["sub_trecho"], o_p["pos"])] = (fl_p, furo_p)
    cab_base, linhas_base, calc_base = montar_base_dados(focco_linhas, mapa_ordem, mapa_pintura)
    wsb = wb.create_sheet("BASE DE DADOS")
    wsb.append(cab_base)
    for j, c in enumerate(wsb[1]):
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F6F5C" if str(c.value) in _COLUNAS_CALC else "003366")  # verde = calculada
        c.alignment = Alignment(horizontal="center", wrap_text=True)
    for lb in linhas_base:
        wsb.append(lb)
    for j, h in enumerate(cab_base, 1):
        wsb.column_dimensions[get_column_letter(j)].width = min(max(len(str(h)) + 4, 10), 40)
    wsb.freeze_panes = "A2"
    wsb.auto_filter.ref = f"A1:{get_column_letter(len(cab_base))}{max(wsb.max_row, 2)}"

    # ---- Relatório Consolidado (FLuxos): o resultado do roteirizador, peça a peça ----
    wsc = wb.create_sheet("Relatório Consolidado (FLuxos)")
    cab_cons = ["OF", "Posição", "Quantidade", "Fluxo", "Material", "Espessura (mm)", "Máquina", "Largura (mm)",
                "Altura (mm)", "Peso Unitário (kg)", "Peso Total (kg)", "TEM FURO?", "OBRA E TRECHO_POSIÇÃO",
                "FLUXO DE PRODUÇÃO", "FURAÇÃO"]
    wsc.append(cab_cons)
    for j, c in enumerate(wsc[1]):
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="003366" if j < 12 else "1F6F5C")
        c.alignment = Alignment(horizontal="center")
    for r in sorted((x for x in registros if x.get("fluxo_final")), key=lambda x: (str(x["of"]), str(x["pos"]))):
        esp_r = r.get("esp")
        larg_r = max(r["largura_dxf"], r["altura_dxf"]) if r.get("largura_dxf") is not None and r.get("altura_dxf") is not None else None
        alt_r = min(r["largura_dxf"], r["altura_dxf"]) if larg_r is not None else None
        pu = calcular_peso(r["largura_dxf"], r["altura_dxf"], esp_r) if (larg_r is not None and esp_r) else None
        qtd_r = r.get("qtd_dxf") or 1
        base_fl = r["fluxo_final"]
        fluxo_nome = _nome_fluxo_pcp(r.get("fluxo_pasta") or (f"{base_fl} [{str(esp_r).replace('.', ',')}]" if esp_r else base_fl))
        furo_r = "SIM" if (r.get("quantidade_furos") or 0) > 0 else "NÃO"
        wsc.append([r["of"], r["pos"], qtd_r, fluxo_nome, r.get("material") or "-",
                    str(esp_r).replace(".", ",") if esp_r else "-",
                    _MAQUINA_CONSOLIDADO.get(_norm_cab(base_fl), "INDEFINIDO"),
                    _num_limpo(larg_r), _num_limpo(alt_r), _num_limpo(pu, 4),
                    _num_limpo(pu * qtd_r if pu is not None else None, 4), furo_r,
                    f"{r['of']}_{r['pos']}".replace("@", "_"), _nome_fluxo_pcp(base_fl), furo_r])
    for j, w in enumerate([14, 12, 11, 26, 18, 14, 24, 14, 12, 16, 16, 11, 26, 22, 11], 1):
        wsc.column_dimensions[get_column_letter(j)].width = w
    wsc.freeze_panes = "A2"
    wsc.auto_filter.ref = f"A1:O{max(wsc.max_row, 2)}"

    # ---- PLAN DIN: ordens por espessura (sem armação/limpeza, pintura e perfil soldado) ----
    def _chave_esp(v):
        return (0, float(v), "") if isinstance(v, (int, float)) else (1, 0.0, str(v))
    vistos_pd, linhas_pd = set(), []
    for c in calc_base:
        if c["desconsidera"] or c["ps"] == "X" or c["espessura"] is None:
            continue
        k = (c["espessura"], c["ordem"], c["pos"])
        if k not in vistos_pd:
            vistos_pd.add(k)
            linhas_pd.append((c["espessura"], c["ordem"], c["pos"], c["planejador"] or "-", c["obra_trecho"], c["fluxo"]))
    linhas_pd.sort(key=lambda t: _chave_esp(t[0]))
    pd_ws = wb.create_sheet("PLAN DIN")
    ult_pd = max(8, 7 + len(linhas_pd))
    pd_ws["A1"], pd_ws["B1"] = "PLANEJADOR", "(Tudo)"
    pd_ws["A2"], pd_ws["B2"] = "OBRA E TRECHO", "(Tudo) - filtre pela coluna D"
    pd_ws["A3"], pd_ws["B3"] = "FLUXO DE PRODUÇÃO", "(Tudo) - filtre pela coluna E"
    pd_ws["A4"], pd_ws["B4"] = "ORDENS PARA DESCONSIDERAR", "só as consideradas"
    pd_ws["A5"], pd_ws["B5"] = "PERFIL SOLDADO", "sem perfil soldado"
    for cel in ("A1", "A2", "A3", "A4", "A5"):
        pd_ws[cel].font = Font(bold=True)
    cabecalho_concatenar(pd_ws, "E1")
    pd_ws["E2"] = f'=_xlfn.TEXTJOIN(",",TRUE,B8:B{ult_pd})'   # acompanha o tamanho da tabela
    for j, h in enumerate(["ESPESSURA", "ORDEM", "POSICAO", "OBRA E TRECHO", "FLUXO DE PRODUÇÃO"], 1):
        cel = pd_ws.cell(row=7, column=j, value=h)
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor="003366")
    for k, t in enumerate(linhas_pd, 8):
        for j, v in enumerate((t[0], t[1], t[2], t[4], t[5]), 1):
            pd_ws.cell(row=k, column=j, value=_xl(v) if v != "" else None)
    pd_ws.freeze_panes = "A8"
    pd_ws.auto_filter.ref = f"A7:E{ult_pd}"

    # ---- CSC: demanda de chapa galvanizada/alumínio (saldo = soma da demanda) ----
    csc_ws = wb.create_sheet("CSC")
    csc_ws["A1"], csc_ws["B1"] = "CSC", "X"
    csc_ws["A1"].font = Font(bold=True)
    cabecalho_concatenar(csc_ws, "F1")
    grupos_csc = defaultdict(float)
    for c in calc_base:
        if c["csc"] == "X":
            grupos_csc[(c["cod_item_dem"], c["desc"])] += c["qtde_dem"]
    for j, h in enumerate(["COD ITEM DEMANDA", "DESC TECNICA DEMANDA", "SAL ESTOQUE", "N° DA ORDEM"], 1):
        cel = csc_ws.cell(row=3, column=j, value=h)
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor="003366")
        cel.alignment = Alignment(horizontal="center")
    k = 4
    for (cod_i, desc_i), tot in sorted(grupos_csc.items()):
        csc_ws.cell(row=k, column=1, value=int(cod_i) if str(cod_i).isdigit() else _xl(cod_i))
        csc_ws.cell(row=k, column=2, value=desc_i)
        csc_ws.cell(row=k, column=3, value=round(tot, 4))
        k += 1
    csc_ws.cell(row=k, column=1, value="Total Geral").font = Font(bold=True)
    csc_ws.cell(row=k, column=3, value=round(sum(grupos_csc.values()), 4)).font = Font(bold=True)
    csc_ws["F2"] = f'=_xlfn.TEXTJOIN(",",TRUE,D4:D{max(k, 4)})'
    for col, w in (("A", 20), ("B", 56), ("C", 16), ("D", 16), ("F", 30)):
        csc_ws.column_dimensions[col].width = w

    rs = wb.create_sheet("Resumo")
    rs.append(["FLUXO", "ORDENS", "PESO TOTAL (kg)"])
    for c in rs[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="003366")
        c.alignment = Alignment(horizontal="center")
    resumo = defaultdict(lambda: [0, 0.0])
    nomes_resumo = {}
    for linha in dados_resumo:
        if linha[8] not in ("-", "SEM FLUXO"):
            k = _norm_cab(linha[8])          # agrupa "Perfiladeira U e C" e "Perfiladeira U E C" juntos
            nomes_resumo.setdefault(k, linha[8])
            resumo[k][0] += 1
            if isinstance(linha[18], (int, float)):
                resumo[k][1] += linha[18]
    for k in sorted(resumo, key=lambda x: nomes_resumo[x]):
        rs.append([nomes_resumo[k], resumo[k][0], round(resumo[k][1], 2)])
    rs.append(["TOTAL ROTEIRIZADO", sum(v[0] for v in resumo.values()), round(sum(v[1] for v in resumo.values()), 2)])
    rs.append(["SEM DXF AINDA", sum(1 for l in dados_resumo if l[20].startswith("❌")), ""])
    rs.append(["DXF FORA DE PASTA DE FLUXO", sum(1 for l in dados_resumo if l[8] == "SEM FLUXO"), ""])
    rs.append([])
    rs.append(["ABAS", "LINHAS", ""])
    for c in rs[rs.max_row]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="003366")
        c.alignment = Alignment(horizontal="center")
    rs.append(["Ordens x DXF (completo)", len(dados), ""])
    rs.append(["Preparação", len(dados_fluxos), ""])
    rs.append(["Não Preparação", len(dados_nao_prep), ""])
    rs.append(["PS PREP", len(dados_ps), ""])
    rs.append(["Ordens para desconsiderar", len(dados_pintura), ""])
    rs.append(["Preparação ainda sem fluxo (só na aba completa)", n_pendentes, ""])
    rs.append([])
    rs.append(["CONFERÊNCIA DA ROTEIRIZAÇÃO (ordens)", "QTDE", ""])
    for c in rs[rs.max_row]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="003366")
        c.alignment = Alignment(horizontal="center")
    for sit in sorted(contagem_sit):
        rs.append([sit, contagem_sit[sit], ""])
    rs.append([])
    rs.append(["ROTAS (HTML)", "LINHAS", "ORDENS"])
    for c in rs[rs.max_row]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="003366")
        c.alignment = Alignment(horizontal="center")
    rs.cell(rs.max_row, 4, "CRITÉRIOS").font = Font(bold=True, color="FFFFFF")
    rs.cell(rs.max_row, 4).fill = PatternFill("solid", fgColor="003366")
    linhas_rota, ordens_rota = defaultdict(int), defaultdict(set)
    for c in calc_base:
        linhas_rota[c["rota"]] += 1
        ordens_rota[c["rota"]].add(c["ordem"])
    for rota_n in _ROTAS_ORDEM + sorted(r for r in linhas_rota if r not in _ROTAS_ORDEM):
        if linhas_rota.get(rota_n):
            rs.append([rota_n, linhas_rota[rota_n], len(ordens_rota[rota_n]), _OBS_ROTA.get(rota_n, "")])
    rs.column_dimensions["D"].width = 80
    for i, w in enumerate([46, 14, 18], 1):
        rs.column_dimensions[get_column_letter(i)].width = w

    ordem_abas = list(_ORDEM_ABAS_RELATORIO) + (["Conferência Roteirização"] if _GERAR_ABA_CONFERENCIA else []) + [_ABA_AUX_CONCATENAR]
    for nome_extra in list(wb.sheetnames):          # abas que não fazem parte do padrão (PLAN DIN, Conferência...)
        if nome_extra not in ordem_abas:
            del wb[nome_extra]
    wb._sheets = [wb[n] for n in ordem_abas if n in wb.sheetnames]
    wb[_ABA_AUX_CONCATENAR].sheet_state = "hidden"
    wb.active = 0
    # padrão do relatório: TUDO centralizado + larguras de coluna iguais às do arquivo tratado
    wsb.row_dimensions[1].height = 28.8
    linha_cab_aba = {"CSC": 3, "ROTEIRIZAÇÃO FOCCO": 6, "Não Preparação": 6, "PS PREP": 6}
    for ws_f in wb.worksheets:
        for linha_f in ws_f.iter_rows():
            for c_f in linha_f:
                if c_f.value is not None and not (ws_f.title == "ROTEIRIZAÇÃO FOCCO" and c_f.coordinate in ("D2", "H2")) \
                        and not (ws_f.title in ("Não Preparação", "PS PREP") and c_f.coordinate in ("E2", "I2")):
                    c_f.alignment = Alignment(horizontal="center", vertical="center", wrap_text=c_f.alignment.wrap_text)
        larg_aba = _LARGURAS_USUARIO.get(ws_f.title, {})
        for c_f in ws_f[linha_cab_aba.get(ws_f.title, 1)]:
            if c_f.value is not None and str(c_f.value) in larg_aba:
                ws_f.column_dimensions[c_f.column_letter].width = larg_aba[str(c_f.value)]
    nome = f"Relatorio_Ordens_Fluxos_LOTE_{lote_ref}.xlsx" if lote_ref else "Relatorio_Ordens_Fluxos.xlsx"
    destino = os.path.join(pasta_saida, nome)
    try:
        wb.save(destino)
    except PermissionError:  # arquivo aberto no Excel - salva com outro nome
        destino = os.path.join(pasta_saida, nome.replace(".xlsx", datetime.now().strftime("_%H%M%S.xlsx")))
        wb.save(destino)
    try:                                                 # logo da Projeart no painel do topo da ROTEIRIZAÇÃO FOCCO
        import base64 as _b64
        _png_logo = _b64.b64decode("".join(_LOGO_PROJEART_PNG_B64))
        for _aba_logo in ("ROTEIRIZAÇÃO FOCCO", "Não Preparação", "PS PREP"):
            _inserir_imagem_xlsx(destino, _aba_logo, _png_logo, 532, 118)
    except Exception as ex_logo:
        log_fn(f"⚠️  Não consegui colocar a logo nas abas ({ex_logo}); o relatório está completo.")
    n_dxf = sum(1 for l in dados if l[20].startswith("✅"))
    n_perf = sum(1 for l in dados if l[20].startswith("🔷"))
    log_fn(f"📋 Relatório: {len(dados)} linha(s) - {n_dxf} com DXF, {n_perf} perfilados sem DXF, "
           f"{len(dados) - n_dxf - n_perf} sem DXF ({len(sem_ordem)} DXF(s) sem ordem no Focco)")
    if not tem_demanda:
        log_fn("⚠️  O relatório do Focco não tem a coluna 'DESC TECNICA DEMANDA': as regras de desconsiderar "
               "(armação/limpeza, pintura/lanternim) só puderam usar o código do item.")
    log_fn(f"📋 ROTEIRIZAÇÃO FOCCO: {len(lista_focco)} linha(s) | conferência: {len(conferencia)} ordem(ns) para revisar")
    log_fn(f"📑 Abas: {len(dados_fluxos)} em Preparação, {len(dados_nao_prep)} em Não Preparação, "
           f"{len(dados_ps)} em PS PREP, {len(dados_pintura)} ordem(ns) para desconsiderar (aba própria), "
           f"{n_pendentes} de preparação ainda sem fluxo")
    return destino


class _RedirecionadorLogParaGUI:
    """Substitui sys.stdout (e sys.stderr): em vez de escrever no terminal,
    empilha o texto na fila que a interface gráfica consome."""
    def write(self, texto):
        if texto:
            _FILA_LOG.put(texto)
    def flush(self):
        pass
def ocultar_console():
    """
    Oculta a janela do console/terminal no Windows, caso exista (ex: quando o
    script é executado via python.exe em vez de pythonw.exe, ou via um .exe
    gerado sem a flag --noconsole/--windowed do PyInstaller). Em outros
    sistemas operacionais, ou quando não há console associado ao processo,
    não faz nada.
    Além de ocultar a janela, redireciona sys.stdout/sys.stderr para a fila de
    log da interface gráfica - assim toda saída (inclusive de bibliotecas de
    terceiros que usem print) passa a aparecer dentro da própria tela do
    roteirizador, em vez de um terminal.
    """
    if sys.platform == "win32":
        try:
            console = ctypes.windll.kernel32.GetConsoleWindow()
            if console:
                ctypes.windll.user32.ShowWindow(console, 0)  # SW_HIDE
        except Exception:
            pass
    sys.stdout = _RedirecionadorLogParaGUI()
    sys.stderr = _RedirecionadorLogParaGUI()
# ===== COMPONENTES VISUAIS EXTRAS (dicas, texto-guia, menu de contexto, log colorido) =====
# Tudo aqui é só aparência/usabilidade: nenhuma função de processamento é alterada.
class _DicaFlutuante:
    """Balão de dica que aparece ao parar o mouse sobre um widget."""
    def __init__(self, widget, texto, atraso=450):
        self.w, self.texto, self.atraso = widget, texto, atraso
        self._id = None
        self._tip = None
        widget.bind("<Enter>", self._agendar, add="+")
        widget.bind("<Leave>", self._ocultar, add="+")
        widget.bind("<ButtonPress>", self._ocultar, add="+")
    def _agendar(self, _e=None):
        self._cancelar()
        self._id = self.w.after(self.atraso, self._mostrar)
    def _cancelar(self):
        if self._id is not None:
            try:
                self.w.after_cancel(self._id)
            except Exception:
                pass
            self._id = None
    def _mostrar(self):
        self._id = None
        try:
            if self._tip is not None or not self.w.winfo_exists():
                return
            x = self.w.winfo_rootx() + 12
            y = self.w.winfo_rooty() + self.w.winfo_height() + 6
            self._tip = tk.Toplevel(self.w)
            self._tip.wm_overrideredirect(True)
            self._tip.wm_geometry(f"+{x}+{y}")
            try:
                self._tip.attributes("-topmost", True)
            except tk.TclError:
                pass
            tk.Label(self._tip, text=self.texto, bg=_COR_MARINHO, fg="#FFFFFF", font=("Segoe UI", 9),
                     padx=10, pady=6, justify="left", wraplength=420, highlightthickness=1,
                     highlightbackground=_COR_MARINHO).pack()
        except Exception:
            self._tip = None
    def _ocultar(self, _e=None):
        self._cancelar()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None
def _placeholder(entry, var, texto):
    """Texto-guia dentro do campo vazio. É só um rótulo por cima do campo: o valor
    da variável (var.get()) NÃO é alterado, então a lógica que lê o campo segue igual."""
    try:
        lbl = tk.Label(entry, text=texto, bg="#FFFFFF", fg="#8A97AB", font=("Segoe UI", 9, "italic"),
                       anchor="w", cursor="xterm")
        def atualizar(*_):
            try:
                if var.get() or entry.focus_get() is entry:
                    lbl.place_forget()
                else:
                    lbl.place(x=12, rely=0.5, anchor="w")
            except tk.TclError:
                pass
        lbl.bind("<Button-1>", lambda _e: entry.focus_set())
        var.trace_add("write", atualizar)
        entry.bind("<FocusIn>", atualizar, add="+")
        entry.bind("<FocusOut>", atualizar, add="+")
        atualizar()
    except Exception:
        pass
def _instalar_menu_contexto(root):
    """Menu do botão direito (Recortar/Copiar/Colar/Selecionar tudo) nos campos de texto."""
    menu = tk.Menu(root, tearoff=0, bg="#FFFFFF", fg=_COR_TEXTO, activebackground=_COR_DESTAQUE,
                   activeforeground=_COR_SOBRE_NEON, bd=0, relief="flat", font=("Segoe UI", 9))
    def mostrar(ev):
        w = ev.widget
        try:
            w.focus_set()
            menu.delete(0, "end")
            menu.add_command(label="Recortar", command=lambda: w.event_generate("<<Cut>>"))
            menu.add_command(label="Copiar", command=lambda: w.event_generate("<<Copy>>"))
            menu.add_command(label="Colar", command=lambda: w.event_generate("<<Paste>>"))
            menu.add_separator()
            menu.add_command(label="Selecionar tudo", command=lambda: w.select_range(0, "end"))
            menu.tk_popup(ev.x_root, ev.y_root)
        finally:
            menu.grab_release()
    root.bind_class("TEntry", "<Button-3>", mostrar)
    root.bind_class("TCombobox", "<Button-3>", mostrar)
def _tag_para_log(texto):
    """Cor da linha do log conforme o tipo de mensagem (só aparência)."""
    if "❌" in texto or re.search(r"\bERRO\b", texto):
        return "erro"
    if "⚠" in texto:
        return "aviso"
    if "✅" in texto or "✨" in texto:
        return "ok"
    if "🧠" in texto or "🔀" in texto:
        return "memoria"
    if any(e in texto for e in ("🔍", "📊", "📋", "📁", "🚀", "🧾", "🔄", "🔲", "🚫", "📄", "📌")):
        return "info"
    return None
def _configurar_tags_log(text):
    text.tag_configure("erro", foreground=_COR_ALERTA)
    text.tag_configure("aviso", foreground=_COR_AVISO)
    text.tag_configure("ok", foreground=_NEON_VERDE)
    text.tag_configure("memoria", foreground=_NEON_ROXO)
    text.tag_configure("info", foreground=_NEON_CIANO_SUAVE)
def _instalar_arrastar_soltar(root, callback):
    """Arrastar e soltar nativo do Windows (sem bibliotecas externas): aceita arquivos e
    pastas soltos em QUALQUER ponto da janela e chama callback(lista_de_caminhos).
    Devolve a referência da função da janela (precisa ficar viva) ou None se não houver
    suporte (outros sistemas) - nesse caso o programa segue normal, só sem o arrastar."""
    if not sys.platform.startswith("win"):
        return None
    try:
        from ctypes import wintypes
        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        WM_DROPFILES, GWLP_WNDPROC = 0x0233, -4
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        set_long.restype = ctypes.c_void_p
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.CallWindowProcW.restype = LRESULT
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragFinish.argtypes = [ctypes.c_void_p]
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        root.update_idletasks()
        hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
        antigo = {"proc": None}

        def proc(h, msg, wp, lp):
            if msg == WM_DROPFILES:
                caminhos = []
                try:
                    total = shell32.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
                    for i in range(total):
                        tam = shell32.DragQueryFileW(wp, i, None, 0)
                        buf = ctypes.create_unicode_buffer(tam + 1)
                        shell32.DragQueryFileW(wp, i, buf, tam + 1)
                        caminhos.append(buf.value)
                except Exception:
                    caminhos = []
                finally:
                    shell32.DragFinish(wp)
                if caminhos:
                    root.after(0, callback, caminhos)   # trata fora do laço de mensagens do Windows
                return 0
            return user32.CallWindowProcW(antigo["proc"], h, msg, wp, lp)

        ref = WNDPROC(proc)
        antigo["proc"] = set_long(hwnd, GWLP_WNDPROC, ctypes.cast(ref, ctypes.c_void_p))
        if not antigo["proc"]:
            return None
        shell32.DragAcceptFiles(hwnd, True)
        return ref
    except Exception:
        return None


# ===== JANELA ÚNICA DO ROTEIRIZADOR =====
# Tudo acontece em UMA ÚNICA janela, organizada em abas (ttk.Notebook):
#   - Aba "🏭 Roteirizador": seleção dos caminhos + log de processamento em
#     tempo real (substitui o terminal).
#   - Aba "📊 Relatório de Divergências": preenchida automaticamente ao final
#     do processamento, sem abrir nenhuma tela nova.
class _AreaRolavel(tk.Frame):
    """Contêiner que se adapta a QUALQUER tela: se o conteúdo cabe, ele ocupa todo o espaço (como antes); se a janela é
    menor do que o conteúdo, aparece a barra de rolagem (vertical e/ou horizontal) em vez de cortar o que está embaixo."""

    def __init__(self, pai, bg):
        super().__init__(pai, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.barra_v = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.barra_h = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.barra_v.set, xscrollcommand=self.barra_h.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.interno = ttk.Frame(self.canvas, style="TFrame", padding=20)
        self._janela = self.canvas.create_window(0, 0, window=self.interno, anchor="nw")
        self._ultimo = None
        self.rotulos = []            # textos de linha inteira: quebram de acordo com a largura da janela
        self._wrap = None
        self.canvas.bind("<Configure>", self._ajustar)
        self.interno.bind("<Configure>", self._ajustar)
        for w in (self.canvas, self.interno):
            w.bind("<Enter>", self._ao_entrar)
            w.bind("<Leave>", self._ao_sair)

    def _ajustar(self, _e=None):
        try:
            larg, alt = self.canvas.winfo_width(), self.canvas.winfo_height()
            if larg < 20 or alt < 20:
                return
            wrap = max(320, larg - 90)
            if wrap != self._wrap:
                self._wrap = wrap
                for lbl in self.rotulos:
                    try:
                        lbl.configure(wraplength=wrap)
                    except tk.TclError:
                        pass
            req_l, req_a = self.interno.winfo_reqwidth(), self.interno.winfo_reqheight()
            # tolerância: uma sobra pequena fica só dentro da margem de 20px da tela e não justifica barra de rolagem
            precisa_v, precisa_h = req_a > alt + 6, req_l > larg + 24
            # as barras só aparecem quando precisam (e a área útil encolhe o tanto que elas ocupam)
            if precisa_v and not self.barra_v.winfo_ismapped():
                self.barra_v.grid(row=0, column=1, sticky="ns")
            elif not precisa_v and self.barra_v.winfo_ismapped():
                self.barra_v.grid_remove()
            if precisa_h and not self.barra_h.winfo_ismapped():
                self.barra_h.grid(row=1, column=0, sticky="ew")
            elif not precisa_h and self.barra_h.winfo_ismapped():
                self.barra_h.grid_remove()
            nova_l, nova_a = (max(larg, req_l) if precisa_h else larg), max(alt, req_a)
            if self._ultimo != (nova_l, nova_a):
                self._ultimo = (nova_l, nova_a)
                self.canvas.itemconfigure(self._janela, width=nova_l, height=nova_a)
                self.canvas.configure(scrollregion=(0, 0, nova_l, nova_a))
            if not precisa_v:
                self.canvas.yview_moveto(0)
            if not precisa_h:
                self.canvas.xview_moveto(0)
        except tk.TclError:
            pass

    def _ao_entrar(self, _e=None):
        self.canvas.bind_all("<MouseWheel>", self._roda)
        self.canvas.bind_all("<Shift-MouseWheel>", self._roda_h)
        self.canvas.bind_all("<Button-4>", lambda e: self._rolar(-3))
        self.canvas.bind_all("<Button-5>", lambda e: self._rolar(3))

    def _ao_sair(self, _e=None):
        for ev in ("<MouseWheel>", "<Shift-MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(ev)

    @staticmethod
    def _tem_rolagem_propria(widget):
        try:
            return widget.winfo_class() in ("Text", "Treeview", "Listbox", "TCombobox")
        except Exception:
            return False

    def _rolar(self, passos):
        if self.barra_v.winfo_ismapped():
            self.canvas.yview_scroll(passos, "units")

    def _roda(self, e):
        if self._tem_rolagem_propria(e.widget):
            return                                  # tabelas, log e listas rolam sozinhos
        self._rolar(int(-e.delta / 120) * 3)

    def _roda_h(self, e):
        if self.barra_h.winfo_ismapped():
            self.canvas.xview_scroll(int(-e.delta / 120) * 3, "units")


class AplicativoRoteirizador:
    # [UNIFICADOR] modo="roteirizador" (4 telas, SEM o Relatório de Ordens) ou modo="ordens" (só o Relatório de Ordens, como app próprio)
    def __init__(self, modo="roteirizador"):
        self.modo = "ordens" if modo == "ordens" else "roteirizador"
        self.root = tk.Tk()
        self.root.title(TITULO_RELATORIO_ORDENS if self.modo == "ordens" else VERSAO)
        self.root.configure(bg=_COR_PAGINA)
        # tamanho da janela proporcional à escala de tela do Windows (125%, 150%...)
        try:
            esc = max(1.0, min(2.0, self.root.winfo_fpixels("1i") / 96.0))
        except Exception:
            esc = 1.0
        larg_tela, alt_tela = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{min(int(1366 * esc), larg_tela - 40)}x{min(int(860 * esc), alt_tela - 80)}")
        self.root.minsize(min(int(1100 * esc), larg_tela - 40), min(int(660 * esc), alt_tela - 80))
        _aplicar_estilo_base(self.root)
        try:
            self._icone_janela = self._criar_icone_projeart(64)
            self.root.iconphoto(True, self._icone_janela)
        except Exception:
            pass
        self._montar_estrutura_projeart()
        self.txt_log = None
        self._processando = False
        self._ultima_analise_pesos = None
        self.abas = ttk.Notebook(self.conteudo, style="Principal.TNotebook")   # abas escondidas: o menu lateral navega
        self.abas.pack(fill="both", expand=True)
        self._abas_rolaveis = []

        def nova_tela(titulo):
            rol = _AreaRolavel(self.abas, _COR_FUNDO)
            self.abas.add(rol, text=titulo)
            self._abas_rolaveis.append(rol)
            return rol.interno                      # o conteúdo de cada tela é montado aqui dentro (rola se não couber)
        if self.modo == "ordens":
            self.aba_relatorio_ordens = nova_tela("Relatório de Ordens")
            self._montar_aba_relatorio_ordens()
        else:
            self.aba_roteirizador = nova_tela("Roteirizador")
            self.aba_relatorio = nova_tela("Relatório de Divergências")
            self.aba_pesos = nova_tela("Peso por Fluxo")
            self.aba_verificador = nova_tela("Verificador")
            self._montar_aba_roteirizador()
            self._montar_aba_relatorio_vazia()
            self._montar_aba_pesos_vazia()
            self._montar_aba_verificador()
        self.abas.bind("<<NotebookTabChanged>>", lambda e: (self._sincronizar_menu(), self.root.after(80, self._quebra_de_linha_dinamica)))
        self._sincronizar_menu()
        self._acabamento_visual()
        self._agendar_drenagem_log()
    # ---------- visual: padrão Projeart (menu lateral, topo branco, conteúdo em cartão, rodapé) ----------
    def _criar_icone_projeart(self, tam=64):
        """Ícone da janela desenhado em código: quadrado azul-marinho com o "P" da Projeart sobre o azul de destaque."""
        img = tk.PhotoImage(width=tam, height=tam)
        esc = tam / 64.0

        def rgb(h):
            return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

        def em_quadrado_arredondado(x, y, x0, y0, x1, y1, r):
            if x < x0 or x > x1 or y < y0 or y > y1:
                return False
            cx, cy = min(max(x, x0 + r), x1 - r), min(max(y, y0 + r), y1 - r)
            return (x - cx) ** 2 + (y - cy) ** 2 <= r * r

        marinho, destaque, branco = rgb(_COR_MARINHO), rgb(_COR_DESTAQUE), (255, 255, 255)
        linhas = []
        for j in range(tam):
            linha = []
            for i in range(tam):
                x, y = i / esc, j / esc
                haste = 22 <= x < 29 and 15 <= y < 49
                dx, dy = x - 31, y - 27
                bojo = x >= 29 and 5.5 ** 2 <= dx * dx + dy * dy <= 12.5 ** 2
                if haste or bojo:
                    cor = branco
                elif em_quadrado_arredondado(x, y, 6, 6, 58, 58, 12):
                    cor = destaque
                else:
                    cor = marinho
                linha.append("#%02x%02x%02x" % cor)
            linhas.append("{" + " ".join(linha) + "}")
        img.put(" ".join(linhas))
        return img

    def _montar_estrutura_projeart(self):
        try:
            esc = max(1.0, min(2.0, self.root.winfo_fpixels("1i") / 96.0))
        except Exception:
            esc = 1.0
        self._esc = esc
        F = _FONTE_TITULO
        MAR, BR = _COR_MARINHO, "#FFFFFF"
        px = lambda v: int(v * esc)
        # ===== menu lateral azul-marinho =====
        self.lateral = tk.Frame(self.root, bg=MAR, width=px(236))
        self.lateral.pack(side="left", fill="y")
        self.lateral.pack_propagate(False)
        rodape_lat = tk.Frame(self.lateral, bg=MAR)
        rodape_lat.pack(side="bottom", fill="x", padx=px(22), pady=(0, px(16)))
        self._lat_rodape = rodape_lat
        tk.Label(rodape_lat, text=VERSAO.split()[-1], bg=MAR, fg="#C9D3E3", font=(F, 9, "bold")).pack(anchor="w")
        tk.Label(rodape_lat, text="© 2026 Projeart", bg=MAR, fg="#7F93B2", font=("Segoe UI", 8)).pack(anchor="w")
        logo = tk.Frame(self.lateral, bg=MAR)
        logo.pack(fill="x", padx=px(14), pady=(px(22), px(26)))
        marca = tk.Canvas(logo, width=px(38), height=px(38), bg=MAR, highlightthickness=0)
        marca.pack(side="left")
        r = px(9)
        x0, y0, x1, y1 = 1, 1, px(38) - 1, px(38) - 1
        marca.create_polygon(x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r,
                             x0, y0 + r, x0, y0, smooth=True, fill=_COR_DESTAQUE, outline=_COR_DESTAQUE)
        marca.create_text(px(19), px(20), text="P", fill=BR, font=(F, 17, "bold"))
        textos = tk.Frame(logo, bg=MAR)
        textos.pack(side="left", padx=(px(10), 0))
        self._lat_textos_logo = textos
        tk.Label(textos, text="PROJEART", bg=MAR, fg=BR, font=(F, 14, "bold")).pack(anchor="w")
        tk.Label(textos, text="SOLUÇÕES TECNOLÓGICAS EM AÇO", bg=MAR, fg="#8C9AB2", font=("Segoe UI", 6, "bold")).pack(anchor="w")
        self._lat_secao = tk.Label(self.lateral, text="RELATÓRIOS" if self.modo == "ordens" else "ROTEIRIZAÇÃO", bg=MAR, fg="#7F93B2", font=("Segoe UI", 8, "bold"), anchor="w")
        self._lat_secao.pack(fill="x", padx=px(26), pady=(0, px(8)))
        if self.modo == "ordens":
            self._rotulos_menu = ("Relatório de Ordens",)
        else:
            self._rotulos_menu = ("Roteirizador", "Relatório de Divergências", "Peso por Fluxo", "Verificador")
        self._itens_menu = []
        for i, rotulo in enumerate(self._rotulos_menu):
            it = tk.Label(self.lateral, text=rotulo, bg=MAR, fg="#C9D3E3", font=(F, 10, "bold"), anchor="w",
                          padx=px(16), pady=px(11), cursor="hand2")
            it.pack(fill="x", padx=px(12), pady=1)
            it.bind("<Button-1>", lambda e, k=i: self.abas.select(k))
            it.bind("<Enter>", lambda e, k=i: self._menu_hover(k, True))
            it.bind("<Leave>", lambda e, k=i: self._menu_hover(k, False))
            self._itens_menu.append(it)
        # ===== coluna da direita: topo branco, conteúdo e rodapé =====
        self.coluna = tk.Frame(self.root, bg=_COR_PAGINA)
        self.coluna.pack(side="left", fill="both", expand=True)
        topo = tk.Frame(self.coluna, bg=BR, height=px(60))
        topo.pack(side="top", fill="x")
        topo.pack_propagate(False)
        tk.Frame(self.coluna, bg=_COR_BORDA, height=1).pack(side="top", fill="x")
        esq = tk.Frame(topo, bg=BR)
        esq.pack(side="left", fill="y", padx=px(26))
        tk.Label(esq, text="Relatório de Ordens" if self.modo == "ordens" else "Roteirizador DXF", bg=BR, fg=MAR, font=(F, 15, "bold")).pack(anchor="w", pady=(px(9), 0))
        tk.Label(esq, text=("PCP  ·  ordens x fluxos  ·  Focco" if self.modo == "ordens"
                            else "PCP  ·  roteirização automática de arquivos DXF  ·  Focco"), bg=BR, fg=_COR_TEXTO_SEC,
                 font=("Segoe UI", 8)).pack(anchor="w")
        dir_ = tk.Frame(topo, bg=BR)
        dir_.pack(side="right", fill="y", padx=px(26))
        tk.Label(dir_, text=VERSAO.split()[-1], bg="#E8F0FA", fg=_COR_DESTAQUE, font=(F, 10, "bold"), padx=px(12),
                 pady=px(4)).pack(side="right", pady=(px(17), 0))
        tk.Label(dir_, text="Sistema ativo", bg=BR, fg=_COR_TEXTO_SEC, font=("Segoe UI", 9)).pack(side="right", padx=(0, px(14)), pady=(px(17), 0))
        tk.Label(dir_, text="●", bg=BR, fg=_COR_OK, font=("Segoe UI", 9)).pack(side="right", pady=(px(17), 0))
        # rodapé (pack ANTES do conteúdo para reservar o espaço embaixo)
        rodape = tk.Frame(self.coluna, bg=BR, height=px(28))
        rodape.pack(side="bottom", fill="x")
        rodape.pack_propagate(False)
        tk.Frame(self.coluna, bg=_COR_BORDA, height=1).pack(side="bottom", fill="x")
        self.rod_ponto = tk.Label(rodape, text="●", bg=BR, fg=_COR_OK, font=("Segoe UI", 9))
        self.rod_ponto.pack(side="left", padx=(px(14), px(4)))
        self.rod_estado = tk.Label(rodape, text="PRONTO", bg=BR, fg=_COR_OK, font=(F, 8, "bold"))
        self.rod_estado.pack(side="left")
        self.rod_hora = tk.Label(rodape, text="", bg=BR, fg=_COR_TEXTO_SEC, font=("Consolas", 9))
        self.rod_hora.pack(side="right", padx=(px(10), px(14)))
        if self.modo != "ordens":
            tk.Label(rodape, text="Ctrl+1…4 troca de tela", bg=BR, fg="#8A97AB", font=("Segoe UI", 8)).pack(side="right", padx=px(14))
        try:
            caminho = _caminho_banco_memoria()
            curto = os.sep.join(caminho.replace("\\", "/").split("/")[-2:])
            tk.Label(rodape, text=f"memória: …{os.sep}{curto}", bg=BR, fg="#8A97AB", font=("Segoe UI", 8)).pack(side="left", expand=True)
        except Exception:
            pass
        self.conteudo = tk.Frame(self.coluna, bg=_COR_PAGINA)
        self.conteudo.pack(side="top", fill="both", expand=True, padx=px(22), pady=px(18))
        self._menu_compacto = False
        self._redim_pendente = None
        self.root.bind("<Configure>", self._ao_redimensionar, add="+")
        self._atualizar_rodape()

    def _ao_redimensionar(self, e):
        if e.widget is not self.root:
            return
        if self._redim_pendente is not None:
            try:
                self.root.after_cancel(self._redim_pendente)
            except Exception:
                pass
        self._redim_pendente = self.root.after(120, self._atualizar_menu_compacto)

    def _atualizar_menu_compacto(self):
        """Janela estreita: o menu lateral recolhe (fica só com o número de cada tela, que é o atalho Ctrl+número)."""
        self._redim_pendente = None
        try:
            esc = getattr(self, "_esc", 1.0)
            compacto = (self.root.winfo_width() / esc) < 1240
            if compacto == self._menu_compacto:
                return
            self._menu_compacto = compacto
            px = lambda v: int(v * esc)
            if compacto:
                self.lateral.configure(width=px(72))
                self._lat_textos_logo.pack_forget()
                self._lat_secao.pack_forget()
                self._lat_rodape.pack_forget()
                for i, it in enumerate(self._itens_menu):
                    it.configure(text=str(i + 1), anchor="center", padx=0)
            else:
                self.lateral.configure(width=px(236))
                self._lat_textos_logo.pack(side="left", padx=(px(10), 0))
                self._lat_secao.pack(fill="x", padx=px(26), pady=(0, px(8)), before=self._itens_menu[0])
                self._lat_rodape.pack(side="bottom", fill="x", padx=px(22), pady=(0, px(16)))
                for i, it in enumerate(self._itens_menu):
                    it.configure(text=self._rotulos_menu[i], anchor="w", padx=px(16))
        except tk.TclError:
            pass

    def _aba_atual(self):
        """Frame interno da tela que está aberta."""
        sel = str(self.abas.select())
        for rol in getattr(self, "_abas_rolaveis", []):
            if str(rol) == sel:
                return rol.interno
        return None

    def _ir_para_aba(self, aba_interna):
        for rol in getattr(self, "_abas_rolaveis", []):
            if rol.interno is aba_interna:
                self.abas.select(rol)
                return

    def _sincronizar_menu(self):
        """Destaca no menu lateral a tela que está aberta."""
        try:
            atual = self.abas.index(self.abas.select())
        except Exception:
            return
        for i, it in enumerate(getattr(self, "_itens_menu", [])):
            ativo = i == atual
            it.configure(bg=_COR_DESTAQUE if ativo else _COR_MARINHO, fg="#FFFFFF" if ativo else "#C9D3E3")

    def _menu_hover(self, k, entrou):
        try:
            if k == self.abas.index(self.abas.select()):
                return
            self._itens_menu[k].configure(bg="#16294B" if entrou else _COR_MARINHO)
        except Exception:
            pass

    def _atualizar_rodape(self):
        try:
            agora = datetime.now()
            if getattr(self, "_processando", False):
                estado, cor = "PROCESSANDO…", _COR_AVISO
            elif getattr(self, "_ro_gerando", False):
                estado, cor = "GERANDO RELATÓRIO…", _COR_AVISO
            else:
                estado, cor = "PRONTO", _COR_OK
            ocupado = estado != "PRONTO"
            cor_ponto = cor if (not ocupado or agora.second % 2 == 0) else "#F0DDB0"
            self.rod_estado.configure(text=estado, fg=cor)
            self.rod_ponto.configure(fg=cor_ponto)
            self.rod_hora.configure(text=agora.strftime("%d/%m/%Y  %H:%M:%S"))
            self.root.after(500, self._atualizar_rodape)
        except tk.TclError:
            pass

    def _aplicar_barra_titulo_escura(self):
        """Barra de título do Windows no tema escuro (botões minimizar/maximizar/fechar
        ficam claros sobre fundo escuro e a borda acende em ciano - Windows 10/11).
        Sem efeito (e sem erro) em sistemas que não suportam."""
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            def atributo(codigo, valor):
                v = ctypes.c_int(valor)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), codigo, ctypes.byref(v), ctypes.sizeof(v))
            def bgr(h):
                r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
                return r | (g << 8) | (b << 16)
            atributo(20, 1)                    # modo escuro (Windows 10 2004+ / 11)
            atributo(19, 1)                    # idem, builds antigas do Windows 10
            atributo(35, bgr(_COR_MARINHO))    # cor da barra de título (Windows 11): azul-marinho Projeart
            atributo(36, bgr("#FFFFFF"))       # cor do texto do título (Windows 11)
            atributo(34, bgr(_COR_MARINHO))    # cor da borda da janela (Windows 11)
        except Exception:
            pass
    # ---------- arrastar e soltar / caminho inteligente ----------
    @staticmethod
    def _separar_caminhos(texto):
        """Separa vários caminhos colados (um por linha, com ou sem aspas)."""
        achados = re.findall(r'"([^"]+)"|([^\r\n;]+)', texto or "")
        return [(a or b).strip() for a, b in achados if (a or b).strip()]

    def _ro_mensagem_zona(self, texto, ok=True):
        try:
            self.lbl_ro_dica.config(text=texto, fg=_NEON_VERDE if ok else _COR_AVISO)
        except Exception:
            pass

    def _ro_entender_caminhos(self, itens):
        """Entende o que cada item é: arquivo Excel/CSV = relatório do Focco; pasta com DXF = pasta dos DXF."""
        msgs, tudo_ok = [], True
        for bruto in itens:
            tipo, c = _classificar_caminho(bruto)
            if tipo == "tabela":
                try:
                    arq = _resolver_arquivo_focco(c)
                except Exception as ex:
                    msgs.append(f"⚠️ {ex}")
                    tudo_ok = False
                    continue
                self.var_ro_focco.set(arq)
                msgs.append(f"📋 Focco: {os.path.basename(arq)}")
            elif tipo == "pasta_dxf":
                self.var_ro_pasta.set(c)
                self._ro_adicionar_pasta()
                msgs.append(f"📁 DXF: {os.path.basename(c) or c}")
            else:
                msgs.append(f"⚠️ Não reconheci: {str(bruto)[:60]}")
                tudo_ok = False
        self._ro_mensagem_zona("  •  ".join(msgs) if msgs else "Nada reconhecido.", tudo_ok and bool(msgs))

    def _rot_entender_caminhos(self, itens):
        """Aba Roteirizador: planilha (arquivo ou pasta DBF com a planilha) e pasta dos DXF."""
        for bruto in itens:
            tipo, c = _classificar_caminho(bruto)
            if tipo == "tabela":
                self.var_planilha.set(c)
                log(f"📥 Planilha definida: {c}")
            elif tipo == "pasta_dxf":
                self.var_pasta.set(c)
                log(f"📥 Pasta dos DXF definida: {c}")
            else:
                log(f"⚠️ Não reconheci o que foi solto: {bruto}")

    def _ao_soltar_arquivos(self, caminhos):
        """Chamado quando arquivos/pastas são soltos na janela: cada aba entende do seu jeito."""
        try:
            aba = self._aba_atual()
        except Exception:
            aba = None
        if self.modo == "ordens":
            self._ro_entender_caminhos(caminhos)
        elif aba is self.aba_roteirizador:
            self._rot_entender_caminhos(caminhos)
        elif aba is self.aba_verificador:
            for bruto in caminhos:
                tipo, c = _classificar_caminho(bruto)
                if tipo == "pasta_dxf" or os.path.isdir(c):
                    self.var_verificador_caminho.set(c)
                    self._verificador_adicionar_pasta()
        else:
            self._ir_para_aba(self.aba_roteirizador)
            self._rot_entender_caminhos(caminhos)

    def _ativar_arrastar_soltar(self):
        self._dnd_ref = _instalar_arrastar_soltar(self.root, self._ao_soltar_arquivos)

    def _acabamento_visual(self):
        """Textos-guia, dicas, menu do botão direito, atalhos e barra de título escura.
        Cada item é independente e protegido - uma falha aqui nunca derruba o programa."""
        for ent, var, txt in (
            (getattr(self, "entry_planilha", None), getattr(self, "var_planilha", None), "Selecione a planilha (.csv ou .xlsx) da obra…"),
            (getattr(self, "entry_pasta", None), getattr(self, "var_pasta", None), "Selecione a pasta com os arquivos DXF…"),
            (getattr(self, "entry_ro_focco", None), getattr(self, "var_ro_focco", None), "Selecione ou arraste o relatório do Focco…"),
            (getattr(self, "entry_ro_pasta", None), getattr(self, "var_ro_pasta", None), "Cole o caminho da pasta, arraste ou clique em Procurar…"),
            (getattr(self, "entry_ro_saida", None), getattr(self, "var_ro_saida", None), "Pasta onde o relatório será salvo (padrão: a 1ª pasta adicionada)…"),
        ):
            if ent is not None and var is not None:
                _placeholder(ent, var, txt)
        for ent, var in (
            (getattr(self, "entry_planilha", None), getattr(self, "var_planilha", None)),
            (getattr(self, "entry_pasta", None), getattr(self, "var_pasta", None)),
            (getattr(self, "entry_ro_focco", None), getattr(self, "var_ro_focco", None)),
            (getattr(self, "entry_ro_saida", None), getattr(self, "var_ro_saida", None)),
        ):
            if ent is not None and var is not None:   # tira aspas/espaços de caminhos colados ao sair do campo
                ent.bind("<FocusOut>", lambda _e, v=var: v.set(_normalizar_caminho(v.get())), add="+")
        self.root.after(400, self._ativar_arrastar_soltar)
        for nome, texto in (
            ("btn_planilha", "Selecionar a planilha (.csv ou .xlsx) da obra"),
            ("btn_pasta", "Selecionar a pasta onde estão os arquivos DXF a roteirizar"),
            ("btn_iniciar", "Roteiriza os DXF: decide o fluxo de cada peça e move os arquivos para as pastas (a tecla Enter também inicia)"),
            ("btn_limpar", "Limpa os campos, o log e os relatórios desta tela"),
            ("btn_ro_gerar", "Gera o Excel de ordens x fluxos lendo os DXF já roteirizados e o relatório do Focco"),
            ("btn_ro_abrir", "Abre o último relatório gerado"),
        ):
            w = getattr(self, nome, None)
            if w is not None:
                try:
                    _DicaFlutuante(w, texto)
                except Exception:
                    pass
        for nome in ("txt_log", "txt_ro_log"):
            w = getattr(self, nome, None)
            if w is not None:
                try:
                    _configurar_tags_log(w)
                except Exception:
                    pass
        try:
            _instalar_menu_contexto(self.root)
            self._instalar_atalhos()
        except Exception:
            pass
        self.root.after(150, self._aplicar_barra_titulo_escura)
        self.root.after(700, self._aplicar_barra_titulo_escura)
        self.root.after(300, self._quebra_de_linha_dinamica)
    def _quebra_de_linha_dinamica(self):
        """Textos longos (subtítulos, avisos) que ocupam a linha inteira passam a quebrar conforme a largura da janela, em vez
        de um tamanho fixo: a tela se adapta a qualquer tamanho sem rolagem horizontal por causa de texto."""
        def percorrer(w, rol):
            for filho in w.winfo_children():
                try:
                    if (rol is not None and filho.winfo_class() in ("Label", "TLabel") and int(str(filho.cget("wraplength")) or 0) > 0
                            and not getattr(filho, "_quebra_ligada", False)):
                        info = filho.pack_info() if filho.winfo_manager() == "pack" else {}
                        # só texto de linha inteira: não o que divide a linha com botões nem o de dentro dos cartões de totais
                        if info.get("side") == "top" and filho.master.winfo_class() == "TFrame":
                            filho._quebra_ligada = True
                            rol.rotulos.append(filho)
                            filho.configure(wraplength=rol._wrap or 360)
                except Exception:
                    pass
                percorrer(filho, rol)
        try:
            for rol in getattr(self, "_abas_rolaveis", []):
                percorrer(rol.interno, rol)
                rol._wrap = None
                rol._ajustar()
        except Exception:
            pass

    def _instalar_atalhos(self):
        for n in range(1, len(self._rotulos_menu) + 1):
            self.root.bind(f"<Control-Key-{n}>", lambda e, i=n - 1: self.abas.select(i))
    def run(self):
        self.root.mainloop()
    # ---------- infraestrutura de log em tempo real ----------
    def _agendar_drenagem_log(self):
        self._drenar_log()
        self.root.after(150, self._agendar_drenagem_log)
    def _drenar_log(self):
        if self.txt_log is None:
            try:
                while True:
                    _FILA_LOG.get_nowait()
            except queue.Empty:
                pass
            return
        atualizou = False
        try:
            while True:
                texto = _FILA_LOG.get_nowait()
                self.txt_log.configure(state="normal")
                _tag = _tag_para_log(texto)
                if _tag:
                    self.txt_log.insert("end", texto, _tag)
                else:
                    self.txt_log.insert("end", texto)
                atualizou = True
        except queue.Empty:
            pass
        if atualizou:
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
    # ---------- Aba 1: seleção de caminhos + log ----------
    def _montar_aba_roteirizador(self):
        pai = self.aba_roteirizador
        ttk.Label(pai, text="Roteirizador", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(pai, text="Selecione (ou arraste para esta janela) a planilha e a pasta dos DXF e inicie o processamento.",
                  style="Subtitulo.TLabel").pack(anchor="w", pady=(0, 14))
        # ----- caminhos de entrada -----
        linha_caminhos = ttk.Frame(pai, style="TFrame")
        linha_caminhos.pack(fill="x", pady=(0, 10))
        bloco_planilha = ttk.Frame(linha_caminhos, style="TFrame")
        bloco_planilha.pack(fill="x", pady=(0, 10))
        ttk.Label(bloco_planilha, text="Caminho da planilha (.csv ou .xlsx)", style="Secao.TLabel").pack(
            anchor="w", pady=(0, 4))
        linha_planilha = ttk.Frame(bloco_planilha, style="TFrame")
        linha_planilha.pack(fill="x")
        self.var_planilha = tk.StringVar()
        self.entry_planilha = ttk.Entry(linha_planilha, textvariable=self.var_planilha,
                                         style="TEntry", font=("Segoe UI", 10))
        self.entry_planilha.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))
        self.btn_planilha = ttk.Button(linha_planilha, text="Procurar...", style="Secundario.TButton",
                                        command=self._escolher_planilha)
        self.btn_planilha.pack(side="left")
        bloco_pasta = ttk.Frame(linha_caminhos, style="TFrame")
        bloco_pasta.pack(fill="x")
        ttk.Label(bloco_pasta, text="Pasta dos arquivos DXF", style="Secao.TLabel").pack(anchor="w", pady=(0, 4))
        linha_pasta = ttk.Frame(bloco_pasta, style="TFrame")
        linha_pasta.pack(fill="x")
        self.var_pasta = tk.StringVar()
        self.entry_pasta = ttk.Entry(linha_pasta, textvariable=self.var_pasta,
                                      style="TEntry", font=("Segoe UI", 10))
        self.entry_pasta.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))
        self.btn_pasta = ttk.Button(linha_pasta, text="Procurar...", style="Secundario.TButton",
                                     command=self._escolher_pasta)
        self.btn_pasta.pack(side="left")
        # ----- barra de ação + status -----
        barra_acao = ttk.Frame(pai, style="TFrame")
        barra_acao.pack(fill="x", pady=(12, 8))
        self.btn_iniciar = ttk.Button(barra_acao, text="Iniciar processamento", style="Destaque.TButton",
                                       command=self._confirmar_selecao)
        self.btn_iniciar.pack(side="left")
        self.btn_limpar = ttk.Button(barra_acao, text="Limpar", style="Secundario.TButton",
                                      command=self._limpar_tela)
        self.btn_limpar.pack(side="left", padx=(8, 0))
        self.lbl_status = tk.Label(barra_acao, text="", bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 9, "bold"))
        self.lbl_status.pack(side="left", padx=(14, 0))
        self.lbl_erro_selecao = tk.Label(barra_acao, text="", bg=_COR_FUNDO, fg=_COR_ALERTA, font=("Segoe UI", 9))
        self.lbl_erro_selecao.pack(side="left", padx=(14, 0))
        self.prog_proc = ttk.Progressbar(barra_acao, mode="indeterminate", length=200, style="TProgressbar")
        # ----- log de processamento (substitui o terminal) -----
        ttk.Label(pai, text="Log de processamento", style="Secao.TLabel").pack(anchor="w", pady=(6, 4))
        frame_log = ttk.Frame(pai, style="TFrame")
        frame_log.pack(fill="both", expand=True)
        self.txt_log = tk.Text(
            frame_log, bg=_COR_PAINEL, fg=_COR_TEXTO, insertbackground=_COR_DESTAQUE, selectbackground="#CFE0F5",
            highlightthickness=1, highlightbackground=_COR_BORDA, highlightcolor=_COR_DESTAQUE,
            font=("Consolas", 9), wrap="word", state="disabled", borderwidth=0, height=8,
        )
        scroll_log = ttk.Scrollbar(frame_log, orient="vertical", command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=scroll_log.set)
        self.txt_log.pack(side="left", fill="both", expand=True)
        scroll_log.pack(side="left", fill="y")
        self.root.bind("<Return>", lambda e: self._confirmar_selecao())
        self.entry_planilha.focus_set()
    def _escolher_planilha(self):
        caminho = filedialog.askopenfilename(
            title="Selecione a planilha",
            filetypes=[("Planilhas", "*.csv *.xlsx *.xls"), ("CSV", "*.csv"),
                       ("Excel", "*.xlsx *.xls"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.var_planilha.set(caminho)
    def _escolher_pasta(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta dos arquivos DXF")
        if caminho:
            self.var_pasta.set(caminho)
    def _confirmar_selecao(self):
        if self._processando:
            return
        planilha = _normalizar_caminho(self.var_planilha.get())
        pasta = _normalizar_caminho(self.var_pasta.get())
        self.var_planilha.set(planilha)
        self.var_pasta.set(pasta)
        if not planilha or not os.path.exists(planilha):
            self.lbl_erro_selecao.config(text="❌ Selecione um caminho de planilha válido.")
            return
        if not pasta or not os.path.exists(pasta):
            self.lbl_erro_selecao.config(text="❌ Selecione uma pasta de DXF válida.")
            return
        self.lbl_erro_selecao.config(text="")
        self._iniciar_processamento(planilha, pasta)
    def _iniciar_processamento(self, caminho_planilha, pasta_dxf):
        self._processando = True
        try:
            self.prog_proc.pack(side="right", padx=(0, 6))
            self.prog_proc.start(14)
        except Exception:
            pass
        self.btn_iniciar.config(state="disabled")
        self.btn_limpar.config(state="disabled")
        self.btn_planilha.config(state="disabled")
        self.btn_pasta.config(state="disabled")
        self.entry_planilha.config(state="disabled")
        self.entry_pasta.config(state="disabled")
        self.lbl_status.config(text="⚙️  Processando, aguarde...", fg=_COR_AVISO)
        # limpa o log da rodada anterior, se houver
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")
        # Processamento pesado roda em thread separada, para a janela e o log
        # continuarem respondendo/atualizando em tempo real, sem travar a
        # interface e sem depender de um terminal separado.
        thread = threading.Thread(
            target=self._executar_processamento,
            args=(caminho_planilha, pasta_dxf),
            daemon=True,
        )
        thread.start()
    def _executar_processamento(self, caminho_planilha, pasta_dxf):
        try:
            print("\n" + "=" * 70)
            print(f" {VERSAO} ".center(70, "="))
            print("=" * 70 + "\n")
            log(f"📁 Planilha: {caminho_planilha}")
            log(f"📁 Pasta DXF: {pasta_dxf}")
            print("\n" + "-" * 70)
            df = carregar_planilha(caminho_planilha)
            colunas_essenciais = ['OF_N', 'POS_N', 'ID_N', 'DEF_N', 'ESP_N', 'LARGURA_N', 'DESENV_N', 'COMPR_N', 'QTD_N']
            colunas_presentes = [col for col in colunas_essenciais if col in df.columns]
            if len(colunas_presentes) < 5:
                mensagem = ("Colunas essenciais não encontradas na planilha selecionada.\n"
                            f"Colunas encontradas: {colunas_presentes}")
                log(f"❌ ERRO: {mensagem}")
                self.root.after(0, self._erro_processamento, mensagem)
                return
            print("\n" + "-" * 70)
            log("🚀 Iniciando processamento dos arquivos DXF...")
            (dxfs_encontrados, ofs_encontradas, analise_quantidade, analise_dimensoes,
             analise_furos, fluxos_atribuidos, ignorados_memoria, analise_pesos) = processar(df, pasta_dxf)
            log("🔄 Padronizando nomes de pastas...")
            padronizar_espessura(pasta_dxf)
            log("🔀 Consolidando pastas de fluxo com espessuras variantes...")
            consolidar_pastas_variantes(pasta_dxf)
            log("🔲 Aplicando regra própria para peças de chapa xadrez...")
            processar_pastas_xadrez(pasta_dxf, df)
            log("🧾 Salvando retrato da roteirização para conferência posterior (aba Verificador)...")
            salvar_log_roteirizacao(pasta_dxf, dxfs_encontrados)
            log("📊 Analisando divergências (planilha x DXF)...")
            dados_relatorio = analisar_divergencias(df, dxfs_encontrados, ofs_encontradas, ignorados_memoria,
                                                      analise_dimensoes)
            # Varre a pasta de verdade e lista QUALQUER dxf que tenha ficado
            # fora de uma pasta de fluxo - cobre tanto peças sem regra no
            # código quanto arquivos cujo nome nem bateu com a planilha (por
            # isso passariam batido, sem aparecer em nenhum outro relatório).
            log("🚫 Verificando peças que ficaram fora de qualquer pasta de fluxo...")
            dados_relatorio["nao_roteirizado"] = detectar_pecas_fora_do_fluxo(pasta_dxf, df)
            print("\n" + "=" * 70)
            log("✨ PROCESSO FINALIZADO COM SUCESSO!")
            print("=" * 70 + "\n")
            of_principal = next(iter(ofs_encontradas)) if ofs_encontradas else "DESCONHECIDA"
            log(f"📌 OF processada: {of_principal}")
            log(f"📁 Total de arquivos roteirizados: {len(dxfs_encontrados)}")
            self.root.after(0, self._finalizar_processamento, dados_relatorio, analise_pesos)
        except Exception as ex:
            log(f"❌ ERRO INESPERADO durante o processamento: {ex}")
            self.root.after(0, self._erro_processamento, str(ex))
    def _reabilitar_selecao(self):
        self._processando = False
        try:
            self.prog_proc.stop()
            self.prog_proc.pack_forget()
        except Exception:
            pass
        self.btn_iniciar.config(state="normal")
        self.btn_limpar.config(state="normal")
        self.btn_planilha.config(state="normal")
        self.btn_pasta.config(state="normal")
        self.entry_planilha.config(state="normal")
        self.entry_pasta.config(state="normal")
    def _limpar_tela(self):
        """
        Limpa os campos de entrada, o log de processamento e o relatório de
        divergências, deixando a tela pronta para uma nova operação sem
        precisar fechar e reabrir o programa. Não faz nada enquanto um
        processamento estiver em andamento (o botão fica desabilitado nesse
        período).
        """
        if self._processando:
            return
        self.var_planilha.set("")
        self.var_pasta.set("")
        self.lbl_erro_selecao.config(text="")
        self.lbl_status.config(text="")
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")
        self._montar_aba_relatorio_vazia()
        self._ultima_analise_pesos = None
        self._montar_aba_pesos_vazia()
        self._ir_para_aba(self.aba_roteirizador)
        self.entry_planilha.focus_set()
    # ---------- Aba: Relatório de Ordens x Fluxos (gerado sob demanda) ----------
    def _montar_aba_relatorio_ordens(self):
        """
        Aba para gerar, SOB DEMANDA, o relatório de ordens x fluxos: lê todos os
        DXF já roteirizados nas pastas informadas e junta, posição por posição,
        com as ordens e a máscara do relatório do Focco. Não roda junto com a
        roteirização - só quando o usuário clicar em "Gerar relatório".
        """
        pai = self.aba_relatorio_ordens
        self._ro_gerando = False
        self._ro_ultimo_arquivo = None
        ttk.Label(pai, text="Relatório de ordens x fluxos", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(pai, text="Junta as ordens do Focco com os DXF já roteirizados e gera o Excel.",
                  style="Subtitulo.TLabel", wraplength=1100).pack(anchor="w", pady=(0, 10))
        # Rodapé (log + botões) é empacotado ANTES do formulário, com side="bottom":
        # assim ele fica sempre visível, mesmo em janelas menores.
        frame_log = ttk.Frame(pai, style="TFrame")
        frame_log.pack(side="bottom", fill="both", expand=True)
        self.txt_ro_log = tk.Text(frame_log, bg=_COR_PAINEL, fg=_COR_TEXTO, insertbackground=_COR_DESTAQUE,
                                  selectbackground="#CFE0F5", highlightthickness=1,
                                  highlightbackground=_COR_BORDA, highlightcolor=_COR_DESTAQUE,
                                  font=("Consolas", 9), wrap="word", state="disabled", borderwidth=0, height=4)
        scroll_log = ttk.Scrollbar(frame_log, orient="vertical", command=self.txt_ro_log.yview)
        self.txt_ro_log.configure(yscrollcommand=scroll_log.set)
        self.txt_ro_log.pack(side="left", fill="both", expand=True)
        scroll_log.pack(side="left", fill="y")
        barra_acao = ttk.Frame(pai, style="TFrame")
        barra_acao.pack(side="bottom", fill="x", pady=(4, 8))
        self.btn_ro_gerar = ttk.Button(barra_acao, text="Gerar relatório", style="Destaque.TButton",
                                       command=self._ro_gerar)
        self.btn_ro_gerar.pack(side="left")
        self.btn_ro_abrir = ttk.Button(barra_acao, text="Abrir relatório", style="Secundario.TButton",
                                       command=self._ro_abrir, state="disabled")
        self.btn_ro_abrir.pack(side="left", padx=(8, 0))
        self.lbl_ro_status = tk.Label(barra_acao, text="", bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 9, "bold"))
        self.lbl_ro_status.pack(side="left", padx=(14, 0))
        self.prog_ro = ttk.Progressbar(barra_acao, mode="indeterminate", length=200, style="TProgressbar")

        # dica discreta (arrastar para a janela funciona em qualquer ponto; esta linha também mostra o resultado do que foi solto)
        self.lbl_ro_dica = tk.Label(pai, text="Dica: você também pode arrastar o relatório e as pastas dos DXF para esta janela.",
                                    bg=_COR_FUNDO, fg=_COR_TEXTO_SEC, font=("Segoe UI", 9), anchor="w")
        self.lbl_ro_dica.pack(anchor="w", pady=(0, 10))

        def linha_caminho(rotulo, var, comando, texto_botao="Procurar...", obs=""):
            cab_linha = ttk.Frame(pai, style="TFrame")
            cab_linha.pack(fill="x", pady=(0, 4))
            ttk.Label(cab_linha, text=rotulo, style="Secao.TLabel").pack(side="left")
            if obs:      # nome do relatório como aparece no Focco, ao lado do rótulo, para não confundir com outro relatório
                tk.Label(cab_linha, text=obs, bg=_COR_FUNDO, fg=_COR_DESTAQUE, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(10, 0))
            linha = ttk.Frame(pai, style="TFrame")
            linha.pack(fill="x", pady=(0, 10))
            entry = ttk.Entry(linha, textvariable=var, style="TEntry", font=("Segoe UI", 10))
            entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))
            ttk.Button(linha, text=texto_botao, style="Secundario.TButton", command=comando).pack(side="left")
            return linha, entry

        self.var_ro_focco = tk.StringVar()
        _, self.entry_ro_focco = linha_caminho("Relatório do Focco", self.var_ro_focco, self._ro_escolher_focco,
                                               obs="(no Focco: Relatório de Ordens Liberadas x Demandas)")

        self.var_ro_pasta = tk.StringVar()
        _linha_p, entry_p = linha_caminho("Pastas dos DXF roteirizados (pode ter várias)",
                                          self.var_ro_pasta, self._ro_escolher_pasta)
        self.entry_ro_pasta = entry_p
        # a pasta entra na lista sozinha: ao escolher em "Procurar", ao colar o caminho, ao dar Enter ou ao sair do campo
        entry_p.bind("<Return>", lambda e: self._ro_adicionar_pasta())
        entry_p.bind("<FocusOut>", lambda e: self._ro_adicionar_pasta(silencioso=True))
        entry_p.bind("<<Paste>>", lambda e: self.root.after(60, lambda: self._ro_adicionar_pasta(silencioso=True)))

        frame_lista = ttk.Frame(pai, style="TFrame")
        frame_lista.pack(fill="x", pady=(0, 6))
        self.lista_ro_pastas = tk.Listbox(
            frame_lista, height=3, bg="#FFFFFF", fg=_COR_TEXTO, selectbackground=_COR_DESTAQUE,
            selectforeground=_COR_SOBRE_NEON, font=("Segoe UI", 9), activestyle="none",
            highlightthickness=1, highlightbackground=_COR_BORDA_CAMPO, highlightcolor=_COR_DESTAQUE,
            borderwidth=0, selectmode="extended",
        )
        scroll_lista = ttk.Scrollbar(frame_lista, orient="vertical", command=self.lista_ro_pastas.yview)
        self.lista_ro_pastas.configure(yscrollcommand=scroll_lista.set)
        self.lista_ro_pastas.pack(side="left", fill="x", expand=True)
        scroll_lista.pack(side="left", fill="y")
        barra_lista = ttk.Frame(pai, style="TFrame")
        barra_lista.pack(fill="x", pady=(0, 10))
        ttk.Button(barra_lista, text="Remover selecionadas", style="Secundario.TButton",
                   command=self._ro_remover_pastas).pack(side="left")
        ttk.Button(barra_lista, text="Limpar lista", style="Secundario.TButton",
                   command=lambda: self.lista_ro_pastas.delete(0, "end")).pack(side="left", padx=(8, 0))

        self.var_ro_saida = tk.StringVar()
        _, self.entry_ro_saida = linha_caminho("Salvar o relatório em", self.var_ro_saida, self._ro_escolher_saida)


    def _ro_escolher_focco(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o relatório do Focco (Relatório de Ordens Liberadas x Demandas)",
            filetypes=[("Excel", "*.xlsx *.xlsm *.xls"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.var_ro_focco.set(caminho)

    def _ro_escolher_pasta(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta dos DXF roteirizados")
        if caminho:
            self.var_ro_pasta.set(caminho)
            self._ro_adicionar_pasta()

    def _ro_adicionar_pasta(self, silencioso=False):
        caminho = _normalizar_caminho(self.var_ro_pasta.get())
        if caminho and os.path.isfile(caminho):
            caminho = os.path.dirname(caminho)          # colou o caminho de um arquivo: usa a pasta dele
        if not caminho or not os.path.isdir(caminho):
            if not silencioso and self.var_ro_pasta.get().strip():
                messagebox.showwarning("Pasta inválida", "Informe uma pasta válida.", parent=self.root)
            return
        existentes = [os.path.abspath(p) for p in self.lista_ro_pastas.get(0, "end")]
        if os.path.abspath(caminho) not in existentes:
            self.lista_ro_pastas.insert("end", caminho)
        if not self.var_ro_saida.get().strip():
            self.var_ro_saida.set(caminho)
        self.var_ro_pasta.set("")

    def _ro_remover_pastas(self):
        for idx in reversed(self.lista_ro_pastas.curselection()):
            self.lista_ro_pastas.delete(idx)

    def _ro_escolher_saida(self):
        caminho = filedialog.askdirectory(title="Pasta onde salvar o relatório")
        if caminho:
            self.var_ro_saida.set(caminho)

    def _ro_log(self, texto):
        """Escreve no log da aba - seguro para chamar de outra thread."""
        def _escrever():
            self.txt_ro_log.configure(state="normal")
            _tag = _tag_para_log(texto)
            if _tag:
                self.txt_ro_log.insert("end", texto + "\n", _tag)
            else:
                self.txt_ro_log.insert("end", texto + "\n")
            self.txt_ro_log.see("end")
            self.txt_ro_log.configure(state="disabled")
        self.root.after(0, _escrever)

    def _ro_gerar(self):
        if self._ro_gerando:
            return
        pastas = list(self.lista_ro_pastas.get(0, "end"))
        saida = _normalizar_caminho(self.var_ro_saida.get())
        try:  # aceita arquivo OU pasta (acha o relatório dentro dela) e limpa aspas/espaços do caminho
            focco = _resolver_arquivo_focco(self.var_ro_focco.get())
            self.var_ro_focco.set(focco)
        except Exception as ex:
            messagebox.showwarning("Relatório do Focco", f"{ex}\n\nSelecione ou arraste o arquivo do relatório do Focco (Relatório de Ordens Liberadas x Demandas).",
                                   parent=self.root)
            return
        if not pastas:
            messagebox.showwarning("Pastas dos DXF", "Adicione ao menos uma pasta com os DXF roteirizados.",
                                   parent=self.root)
            return
        if not saida:
            saida = pastas[0]
            self.var_ro_saida.set(saida)
        try:
            os.makedirs(saida, exist_ok=True)
        except OSError as ex:
            messagebox.showerror("Pasta de saída", f"Não foi possível usar a pasta de saída:\n{ex}", parent=self.root)
            return
        self._ro_gerando = True
        try:
            self.prog_ro.pack(side="right", padx=(0, 6))
            self.prog_ro.start(14)
        except Exception:
            pass
        self.btn_ro_gerar.config(state="disabled")
        self.btn_ro_abrir.config(state="disabled")
        self.lbl_ro_status.config(text="⚙️  Gerando relatório, aguarde...", fg=_COR_AVISO)
        self.txt_ro_log.configure(state="normal")
        self.txt_ro_log.delete("1.0", "end")
        self.txt_ro_log.configure(state="disabled")
        threading.Thread(target=self._ro_executar, args=(focco, pastas, saida), daemon=True).start()

    def _ro_executar(self, focco, pastas, saida):
        try:
            registros = coletar_registros_das_pastas(pastas, log_fn=self._ro_log)
            destino = gerar_relatorio_ordens_fluxos(focco, registros, saida, log_fn=self._ro_log)
            self._ro_log(f"✅ Relatório salvo em: {destino}")
            self.root.after(0, self._ro_finalizar, destino, None)
        except Exception as ex:
            self._ro_log(f"❌ Erro ao gerar o relatório: {ex}")
            self.root.after(0, self._ro_finalizar, None, str(ex))

    def _ro_finalizar(self, destino, erro):
        self._ro_gerando = False
        try:
            self.prog_ro.stop()
            self.prog_ro.pack_forget()
        except Exception:
            pass
        self.btn_ro_gerar.config(state="normal")
        if erro:
            self.lbl_ro_status.config(text="❌ Erro ao gerar o relatório.", fg=_COR_ALERTA)
            messagebox.showerror("Erro ao gerar o relatório", erro, parent=self.root)
            return
        self._ro_ultimo_arquivo = destino
        self.btn_ro_abrir.config(state="normal")
        self.lbl_ro_status.config(text=f"✅ Relatório gerado: {os.path.basename(destino)}", fg=_COR_OK)

    def _ro_abrir(self):
        if not self._ro_ultimo_arquivo or not os.path.exists(self._ro_ultimo_arquivo):
            return
        try:
            os.startfile(self._ro_ultimo_arquivo)
        except Exception:
            messagebox.showinfo("Relatório", f"Arquivo salvo em:\n{self._ro_ultimo_arquivo}", parent=self.root)

    def _erro_processamento(self, mensagem):
        self._reabilitar_selecao()
        self.lbl_status.config(text="❌ Erro no processamento.", fg=_COR_ALERTA)
        messagebox.showerror("Erro ao processar", mensagem, parent=self.root)
    def _valores_fluxo_combobox(self, espessura=None):
        """Monta as opções do combobox de 'Fluxo' usado nas edições inline
        (Faltantes / Não Roteirizado) - já com a espessura formatada quando
        conhecida (ex: 'Fluxo 3 [4,75]'); sem espessura conhecida, deixa só o
        nome base e o usuário completa manualmente com '[x,xx]' se precisar."""
        if espessura not in (None, ""):
            try:
                esp_fmt = str(espessura).replace(".", ",")
            except Exception:
                esp_fmt = None
            if esp_fmt:
                return [f"{base} [{esp_fmt}]" for base in _FLUXOS_BASE_DISPONIVEIS]
        return list(_FLUXOS_BASE_DISPONIVEIS)
    def _finalizar_processamento(self, dados, analise_pesos):
        self._reabilitar_selecao()
        self.lbl_status.config(text="✅ Processamento concluído. Veja as abas de relatório e peso.", fg=_COR_OK)
        self._montar_aba_relatorio(dados)
        self._montar_aba_pesos(analise_pesos)
        self._verificador_incluir_pasta_roteirizada()
        self._ir_para_aba(self.aba_relatorio)

    def _verificador_incluir_pasta_roteirizada(self):
        """Depois de roteirizar, a pasta já entra sozinha na lista do Verificador (sem precisar colar o caminho):
        o retrato acabou de ser gravado nela, então qualquer arquivo que o usuário mover depois aparece lá."""
        try:
            pasta = self._verificador_limpar_caminho(self.var_pasta.get())
            if not pasta or not os.path.isdir(pasta):
                return
            alvo = os.path.abspath(pasta)
            for iid in self.tree_verificador_pastas.get_children():
                if os.path.abspath(self.tree_verificador_pastas.set(iid, "caminho")) == alvo:
                    return
            self.tree_verificador_pastas.insert("", "end", values=("☑", pasta))
            self._verificador_atualizar_comparacoes(mostrar_log=False)
            self._verificador_garantir_monitoramento()
        except Exception as ex:                                  # noqa: BLE001
            log(f"⚠️  Não consegui incluir a pasta no Verificador: {ex}")
    # ---------- Aba 2: relatório de divergências (dentro da mesma janela) ----------
    def _montar_aba_relatorio_vazia(self):
        for widget in self.aba_relatorio.winfo_children():
            widget.destroy()
        tk.Label(
            self.aba_relatorio,
            text="Nenhum relatório gerado ainda.\nProcesse uma planilha/pasta de DXF na aba "
                 "\"Roteirizador\" para visualizar aqui as divergências.",
            bg=_COR_FUNDO, fg=_COR_TEXTO_SEC, font=("Segoe UI", 11), justify="center",
        ).pack(expand=True)
    def _montar_aba_relatorio(self, dados):
        for widget in self.aba_relatorio.winfo_children():
            widget.destroy()
        pai = self.aba_relatorio
        faltantes = list(dados["faltantes"])
        nao_roteirizado = list(dados.get("nao_roteirizado", []))
        sem_cam = list(dados["sem_cam"])
        ignorados_memoria_lista = dados["ignorados_memoria_lista"]
        divergencias_tamanho = list(dados.get("divergencias_tamanho", []))
        padrao_planilha = list(dados.get("padrao_planilha", []))
        ttk.Label(pai, text="Relatório de divergências",
                  style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(
            pai,
            text=f"OF(s): {dados['ofs_texto']}    |    Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            style="Subtitulo.TLabel",
        ).pack(anchor="w", pady=(2, 16))
        # ----- Cards de totais -----
        cards_frame = ttk.Frame(pai, style="TFrame")
        cards_frame.pack(fill="x", pady=(0, 16))
        def criar_card(pai_cards, titulo, valor_inicial, cor):
            borda = cor if cor != _COR_TEXTO else _COR_BORDA_CAMPO
            card = tk.Frame(pai_cards, bg=_COR_PAINEL, padx=10, pady=9,
                            highlightthickness=1, highlightbackground=borda, highlightcolor=borda)
            card.pack(side="left", padx=(0, 8), fill="both", expand=True)     # os cartões dividem a largura da tela
            var = tk.StringVar(value=str(valor_inicial))
            tk.Label(card, textvariable=var, bg=_COR_PAINEL, fg=cor, font=(_FONTE_TITULO, 18, "bold")).pack(anchor="w")
            tk.Label(card, text=titulo, bg=_COR_PAINEL, fg=_COR_TEXTO_SEC, font=("Segoe UI", 7, "bold"),
                     wraplength=112, justify="left", anchor="w").pack(anchor="w")
            return var
        criar_card(cards_frame, "ITENS NA PLANILHA", dados["total_relevante"], _COR_TEXTO)
        criar_card(cards_frame, "DXFS ENCONTRADOS", dados["total_encontrados"], _COR_OK)
        var_faltantes_card = criar_card(cards_frame, "FALTANTES", len(faltantes), _COR_ALERTA)
        var_divergencia_card = criar_card(cards_frame, "DIVERGÊNCIA TAMANHO", len(divergencias_tamanho), _COR_AVISO)
        var_padrao_card = criar_card(cards_frame, "[PADRÃO] PLANILHA", len(padrao_planilha), _COR_INFO)
        var_sem_cam_card = criar_card(cards_frame, "SEM CAM (BR/TB)", len(sem_cam), _COR_INFO)
        var_ignorados_card = criar_card(cards_frame, "IGNORADOS (MEMÓRIA)", len(ignorados_memoria_lista), _COR_INFO)
        criar_card(cards_frame, "APROVEITAMENTO", f"{dados['aproveitamento']:.1f}%", _COR_TEXTO)
        # ----- Sub-abas internas (faltantes / sem CAM / ignorados) -----
        subabas = ttk.Notebook(pai)
        subabas.pack(fill="both", expand=True)
        aba_faltantes = ttk.Frame(subabas, style="TFrame", padding=10)
        subabas.add(aba_faltantes, text=f"Faltantes ({len(faltantes)})")
        tk.Label(
            aba_faltantes,
            text="Dica: clique no quadrado à esquerda da linha para selecionar. Preencha 'Fluxo' e/ou 'Motivo' "
                 "direto na própria linha (sem precisar clicar duas vezes) antes de usar os botões abaixo. As "
                 "ações gravam direto na memória (SQLite) e valem para qualquer obra futura.",
            bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 8), wraplength=1000, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        barra_acoes = ttk.Frame(aba_faltantes, style="TFrame")
        barra_acoes.pack(fill="x", pady=(0, 8))
        lbl_status_faltantes = tk.Label(barra_acoes, text="", bg=_COR_FUNDO, fg=_COR_OK, font=("Segoe UI", 9))
        tabela_frame = ttk.Frame(aba_faltantes, style="Cartao.TFrame")
        tabela_frame.pack(fill="both", expand=True)
        _canvas_falt, frame_faltantes_linhas = self._criar_area_rolavel(tabela_frame)
        larguras_falt = {"sel": 36, "of": 90, "tipo": 100, "pos": 90, "id": 170, "fluxo": 190}
        for col_idx, chave_col in enumerate(["sel", "of", "tipo", "pos", "id", "fluxo"]):
            frame_faltantes_linhas.grid_columnconfigure(col_idx, minsize=larguras_falt[chave_col])
        frame_faltantes_linhas.grid_columnconfigure(6, weight=1, minsize=220)  # motivo (expande)
        titulos_falt = ["", "OF", "Tipo", "Posição", "Identificador", "Fluxo", "Motivo"]
        for col_idx, titulo in enumerate(titulos_falt):
            tk.Label(
                frame_faltantes_linhas, text=titulo, bg=_COR_PAINEL, fg=_NEON_CIANO_SUAVE,
                font=("Segoe UI", 9, "bold"), anchor="w",
            ).grid(row=0, column=col_idx, sticky="nsew", padx=(4, 4), pady=6)
        lbl_faltantes_vazio = tk.Label(
            frame_faltantes_linhas, text="Nenhum item faltante até agora.",
            bg=_COR_PAINEL_2, fg=_COR_TEXTO_SEC, font=("Segoe UI", 9), anchor="w",
        )
        lbl_faltantes_vazio.grid(row=1, column=0, columnspan=7, sticky="w", padx=8, pady=10)
        linhas_faltantes = {}  # chave do item -> dict com widgets/estado da linha
        estado_falt = {"proxima_row": 2}
        def _criar_linha_faltante(it):
            row_idx = estado_falt["proxima_row"]
            estado_falt["proxima_row"] += 1
            widgets_criados = []
            lbl_sel = tk.Label(frame_faltantes_linhas, text="☐", bg=_COR_PAINEL_2, fg=_COR_TEXTO,
                                font=("Segoe UI", 10), cursor="hand2")
            lbl_sel.grid(row=row_idx, column=0, sticky="nsew", padx=(4, 4), pady=3)
            def _alternar_sel(_event=None, lbl=lbl_sel):
                lbl.config(text="☑" if lbl.cget("text") == "☐" else "☐")
            lbl_sel.bind("<Button-1>", _alternar_sel)
            widgets_criados.append(lbl_sel)
            def _lbl(texto, col):
                w = tk.Label(frame_faltantes_linhas, text=texto, bg=_COR_PAINEL_2, fg=_COR_TEXTO,
                              font=("Segoe UI", 9), anchor="w", justify="left")
                w.grid(row=row_idx, column=col, sticky="nsew", padx=(4, 4), pady=3)
                widgets_criados.append(w)
                return w
            _lbl(it.get("of", ""), 1)
            _lbl(it.get("tipo", ""), 2)
            _lbl(it.get("pos", ""), 3)
            _lbl(it.get("identificador", ""), 4)
            var_fluxo = tk.StringVar()
            combo_fluxo = ttk.Combobox(frame_faltantes_linhas, textvariable=var_fluxo, style="TCombobox",
                                        values=self._valores_fluxo_combobox(it.get("espessura")),
                                        font=("Segoe UI", 9))
            combo_fluxo.grid(row=row_idx, column=5, sticky="nsew", padx=(4, 4), pady=3, ipady=2)
            widgets_criados.append(combo_fluxo)
            var_motivo = tk.StringVar()
            entry_motivo = ttk.Entry(frame_faltantes_linhas, textvariable=var_motivo, style="TEntry",
                                      font=("Segoe UI", 9))
            entry_motivo.grid(row=row_idx, column=6, sticky="nsew", padx=(4, 4), pady=3, ipady=3)
            widgets_criados.append(entry_motivo)
            linhas_faltantes[it["chave"]] = {
                "lbl_sel": lbl_sel, "var_fluxo": var_fluxo, "var_motivo": var_motivo,
                "item": it, "widgets": widgets_criados,
            }
            lbl_faltantes_vazio.grid_remove()
        def _remover_linha_faltante(chave_item):
            info = linhas_faltantes.pop(chave_item, None)
            if not info:
                return
            for widget in info["widgets"]:
                widget.destroy()
            if not linhas_faltantes:
                lbl_faltantes_vazio.grid()
        def preencher_faltantes():
            for chave_item in list(linhas_faltantes.keys()):
                _remover_linha_faltante(chave_item)
            for it in faltantes:
                _criar_linha_faltante(it)
        preencher_faltantes()
        def linhas_selecionadas():
            return [chave for chave, info in linhas_faltantes.items() if info["lbl_sel"].cget("text") == "☑"]
        def selecionar_todos():
            if not linhas_faltantes:
                return
            marcar = "☑" if any(info["lbl_sel"].cget("text") == "☐" for info in linhas_faltantes.values()) else "☐"
            for info in linhas_faltantes.values():
                info["lbl_sel"].config(text=marcar)
        def atualizar_contadores():
            var_faltantes_card.set(str(len(linhas_faltantes)))
            subabas.tab(aba_faltantes, text=f"Faltantes ({len(linhas_faltantes)})")
        def mostrar_status(msg, cor):
            lbl_status_faltantes.config(text=msg, fg=cor)
            self.root.after(6000, lambda: lbl_status_faltantes.config(text=""))
        def marcar_selecionados_ignorados():
            selecionados = linhas_selecionadas()
            if not selecionados:
                messagebox.showinfo("Nenhum item selecionado",
                                     "Marque ao menos um item na coluna à esquerda antes de continuar.",
                                     parent=self.root)
                return
            if not messagebox.askyesno(
                "Confirmar",
                f"Marcar {len(selecionados)} item(ns) como 'não gera DXF' permanentemente?\n"
                "Isso vale para qualquer obra futura.\n\n"
                "Dica: preencha o campo 'Motivo' de cada linha antes de confirmar, se quiser registrar o motivo.",
                parent=self.root,
            ):
                return
            for chave_item in selecionados:
                info = linhas_faltantes[chave_item]
                it = info["item"]
                motivo = info["var_motivo"].get().strip()
                marcar_ignorado(it["identificador"], it["pos"], motivo)
                _remover_linha_faltante(chave_item)
            var_ignorados_card.set(str(int(var_ignorados_card.get()) + len(selecionados)))
            atualizar_contadores()
            mostrar_status(f"✅ {len(selecionados)} item(ns) marcado(s) como ignorado(s) - gravado na memória.", _COR_OK)
            log(f"🧠 {len(selecionados)} item(ns) marcado(s) como ignorado(s) via aba de relatório")
        def definir_fluxo_manual_selecionados():
            selecionados = linhas_selecionadas()
            if not selecionados:
                messagebox.showinfo("Nenhum item selecionado",
                                     "Marque ao menos um item na coluna à esquerda antes de continuar.",
                                     parent=self.root)
                return
            sem_fluxo = [c for c in selecionados if not linhas_faltantes[c]["var_fluxo"].get().strip()]
            if sem_fluxo:
                messagebox.showwarning(
                    "Fluxo não preenchido",
                    f"{len(sem_fluxo)} linha(s) selecionada(s) não têm fluxo preenchido.\n\n"
                    "Preencha (ou escolha na lista) o campo 'Fluxo' de cada linha e tente de novo.",
                    parent=self.root,
                )
                return
            if not messagebox.askyesno(
                "Confirmar",
                f"Gravar o fluxo manual de {len(selecionados)} item(ns) na memória?\n\n"
                "Vale para qualquer obra futura com a mesma posição/identificador.",
                parent=self.root,
            ):
                return
            for chave_item in selecionados:
                info = linhas_faltantes[chave_item]
                it = info["item"]
                fluxo = info["var_fluxo"].get().strip()
                motivo = info["var_motivo"].get().strip()
                marcar_ajuste_manual(it["identificador"], it["pos"], fluxo, motivo)
                _remover_linha_faltante(chave_item)
            atualizar_contadores()
            mostrar_status(f"✅ Fluxo manual salvo para {len(selecionados)} item(ns).", _COR_OK)
            log(f"🔀 Fluxo manual definido para {len(selecionados)} item(ns) via aba de relatório")
        def mover_selecionados_para_padrao():
            selecionados = linhas_selecionadas()
            if not selecionados:
                messagebox.showinfo("Nenhum item selecionado",
                                     "Marque ao menos um item na coluna à esquerda antes de continuar.",
                                     parent=self.root)
                return
            if not messagebox.askyesno(
                "Confirmar",
                f"Mover {len(selecionados)} item(ns) para \"[PADRÃO] PLANILHA\"?\n\n"
                "Isso NÃO descarta a peça para sempre: se um DXF real aparecer para ela em uma obra "
                "futura (ex: uma liberação nova gerar CAM), o roteirizador continua encontrando e "
                "processando normalmente - a marcação só evita que ela apareça como faltante enquanto "
                "não houver DXF.",
                parent=self.root,
            ):
                return
            for chave_item in selecionados:
                info = linhas_faltantes[chave_item]
                it = info["item"]
                motivo = info["var_motivo"].get().strip()
                marcar_padrao_planilha_manual(it["identificador"], it["pos"], motivo)
                _remover_linha_faltante(chave_item)
                # Reflete imediatamente na aba "[PADRÃO] PLANILHA", sem precisar reprocessar
                limpar_placeholder_padrao()
                tree_padrao.insert("", "end", values=(it["of"], it["tipo"], it["pos"], it["identificador"]))
                padrao_planilha.append(it)
            var_padrao_card.set(str(len(padrao_planilha)))
            subabas.tab(aba_padrao, text=f"[PADRÃO] PLANILHA ({len(padrao_planilha)})")
            atualizar_contadores()
            mostrar_status(f"✅ {len(selecionados)} item(ns) movido(s) para [PADRÃO] PLANILHA.", _COR_OK)
            log(f"📋 {len(selecionados)} item(ns) movido(s) para [PADRÃO] PLANILHA via aba de relatório")
        ttk.Button(barra_acoes, text="Selecionar/desmarcar todos", style="Secundario.TButton",
                   command=selecionar_todos).pack(side="left")
        ttk.Button(barra_acoes, text="Marcar selecionados como ignorado", style="Perigo.TButton",
                   command=marcar_selecionados_ignorados).pack(side="left", padx=(10, 0))
        ttk.Button(barra_acoes, text="Definir fluxo manual", style="Destaque.TButton",
                   command=definir_fluxo_manual_selecionados).pack(side="left", padx=(10, 0))
        ttk.Button(barra_acoes, text="Mover para [PADRÃO] PLANILHA", style="Secundario.TButton",
                   command=mover_selecionados_para_padrao).pack(side="left", padx=(10, 0))
        lbl_status_faltantes.pack(side="left", padx=(14, 0))
        # === Sub-aba Não Roteirizado (interativa) ============================
        # QUALQUER arquivo .dxf que ficou fora de uma pasta de fluxo de
        # verdade depois da roteirização - seja porque não existe regra no
        # código pra ele, seja porque o nome do arquivo nem bateu com nenhuma
        # linha da planilha (nesse caso os campos abaixo vêm só do que dá pra
        # extrair do nome do arquivo, podendo ficar incompletos).
        aba_nao_roteirizado = ttk.Frame(subabas, style="TFrame", padding=10)
        subabas.add(aba_nao_roteirizado, text=f"Não Roteirizado ({len(nao_roteirizado)})")
        tk.Label(
            aba_nao_roteirizado,
            text="Arquivos DXF que ficaram fora de qualquer pasta de fluxo depois da roteirização. Dica: "
                 "clique no quadrado à esquerda da linha para selecionar. Preencha 'Fluxo' e/ou 'Motivo' direto "
                 "na própria linha (sem precisar clicar duas vezes). Ao clicar em '🔀 Definir fluxo manual', o "
                 "arquivo já é MOVIDO agora mesmo para a pasta do fluxo escolhido e o ajuste é gravado na "
                 "memória (SQLite) - vale para qualquer obra futura com a mesma posição/identificador.",
            bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 8), wraplength=1000, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        barra_acoes_nao_rot = ttk.Frame(aba_nao_roteirizado, style="TFrame")
        barra_acoes_nao_rot.pack(fill="x", pady=(0, 8))
        lbl_status_nao_rot = tk.Label(barra_acoes_nao_rot, text="", bg=_COR_FUNDO, fg=_COR_OK, font=("Segoe UI", 9))
        tabela_frame_nao_rot = ttk.Frame(aba_nao_roteirizado, style="Cartao.TFrame")
        tabela_frame_nao_rot.pack(fill="both", expand=True)
        _canvas_nr, frame_nao_rot_linhas = self._criar_area_rolavel(tabela_frame_nao_rot)
        larguras_nr = {"sel": 36, "of": 90, "pos": 90, "id": 150, "arquivo": 200, "esp": 70, "fluxo": 190}
        for col_idx, chave_col in enumerate(["sel", "of", "pos", "id", "arquivo", "esp", "fluxo"]):
            frame_nao_rot_linhas.grid_columnconfigure(col_idx, minsize=larguras_nr[chave_col])
        frame_nao_rot_linhas.grid_columnconfigure(7, weight=1, minsize=200)  # motivo (expande)
        titulos_nr = ["", "OF", "Posição", "Identificador", "Arquivo", "Esp.", "Fluxo", "Motivo"]
        for col_idx, titulo in enumerate(titulos_nr):
            tk.Label(
                frame_nao_rot_linhas, text=titulo, bg=_COR_PAINEL, fg=_NEON_CIANO_SUAVE,
                font=("Segoe UI", 9, "bold"), anchor="w",
            ).grid(row=0, column=col_idx, sticky="nsew", padx=(4, 4), pady=6)
        lbl_nao_rot_vazio = tk.Label(
            frame_nao_rot_linhas, text="Nenhum item fora de fluxo até agora.",
            bg=_COR_PAINEL_2, fg=_COR_TEXTO_SEC, font=("Segoe UI", 9), anchor="w",
        )
        lbl_nao_rot_vazio.grid(row=1, column=0, columnspan=8, sticky="w", padx=8, pady=10)
        linhas_nao_rot = {}  # nome do arquivo -> dict com widgets/estado da linha
        estado_nr = {"proxima_row": 2}
        def _criar_linha_nao_rot(it):
            row_idx = estado_nr["proxima_row"]
            estado_nr["proxima_row"] += 1
            widgets_criados = []
            lbl_sel = tk.Label(frame_nao_rot_linhas, text="☐", bg=_COR_PAINEL_2, fg=_COR_TEXTO,
                                font=("Segoe UI", 10), cursor="hand2")
            lbl_sel.grid(row=row_idx, column=0, sticky="nsew", padx=(4, 4), pady=3)
            def _alternar_sel(_event=None, lbl=lbl_sel):
                lbl.config(text="☑" if lbl.cget("text") == "☐" else "☐")
            lbl_sel.bind("<Button-1>", _alternar_sel)
            widgets_criados.append(lbl_sel)
            def _lbl(texto, col):
                w = tk.Label(frame_nao_rot_linhas, text=texto, bg=_COR_PAINEL_2, fg=_COR_TEXTO,
                              font=("Segoe UI", 9), anchor="w", justify="left")
                w.grid(row=row_idx, column=col, sticky="nsew", padx=(4, 4), pady=3)
                widgets_criados.append(w)
                return w
            esp = it.get("espessura")
            esp_fmt = str(esp).replace(".", ",") if esp is not None else ""
            _lbl(it.get("of", ""), 1)
            _lbl(it.get("pos", ""), 2)
            _lbl(it.get("identificador", ""), 3)
            _lbl(it.get("arquivo", ""), 4)
            _lbl(esp_fmt, 5)
            var_fluxo = tk.StringVar()
            combo_fluxo = ttk.Combobox(frame_nao_rot_linhas, textvariable=var_fluxo, style="TCombobox",
                                        values=self._valores_fluxo_combobox(esp), font=("Segoe UI", 9))
            combo_fluxo.grid(row=row_idx, column=6, sticky="nsew", padx=(4, 4), pady=3, ipady=2)
            widgets_criados.append(combo_fluxo)
            var_motivo = tk.StringVar()
            entry_motivo = ttk.Entry(frame_nao_rot_linhas, textvariable=var_motivo, style="TEntry",
                                      font=("Segoe UI", 9))
            entry_motivo.grid(row=row_idx, column=7, sticky="nsew", padx=(4, 4), pady=3, ipady=3)
            widgets_criados.append(entry_motivo)
            linhas_nao_rot[it["arquivo"]] = {
                "lbl_sel": lbl_sel, "var_fluxo": var_fluxo, "var_motivo": var_motivo,
                "item": it, "widgets": widgets_criados,
            }
            lbl_nao_rot_vazio.grid_remove()
        def _remover_linha_nao_rot(chave_arquivo):
            info = linhas_nao_rot.pop(chave_arquivo, None)
            if not info:
                return
            for widget in info["widgets"]:
                widget.destroy()
            if not linhas_nao_rot:
                lbl_nao_rot_vazio.grid()
        def preencher_nao_rot():
            for chave_arquivo in list(linhas_nao_rot.keys()):
                _remover_linha_nao_rot(chave_arquivo)
            for it in nao_roteirizado:
                _criar_linha_nao_rot(it)
        preencher_nao_rot()
        def linhas_selecionadas_nao_rot():
            return [chave for chave, info in linhas_nao_rot.items() if info["lbl_sel"].cget("text") == "☑"]
        def selecionar_todos_nao_rot():
            if not linhas_nao_rot:
                return
            marcar = "☑" if any(info["lbl_sel"].cget("text") == "☐" for info in linhas_nao_rot.values()) else "☐"
            for info in linhas_nao_rot.values():
                info["lbl_sel"].config(text=marcar)
        def atualizar_contadores_nao_rot():
            subabas.tab(aba_nao_roteirizado, text=f"Não Roteirizado ({len(linhas_nao_rot)})")
        def mostrar_status_nao_rot(msg, cor):
            lbl_status_nao_rot.config(text=msg, fg=cor)
            self.root.after(6000, lambda: lbl_status_nao_rot.config(text=""))
        def marcar_selecionados_ignorados_nao_rot():
            selecionados = linhas_selecionadas_nao_rot()
            if not selecionados:
                messagebox.showinfo("Nenhum item selecionado",
                                     "Marque ao menos um item na coluna à esquerda antes de continuar.",
                                     parent=self.root)
                return
            if not messagebox.askyesno(
                "Confirmar",
                f"Marcar {len(selecionados)} item(ns) como 'não gera DXF' permanentemente?\n"
                "Isso vale para qualquer obra futura.\n\n"
                "Dica: preencha o campo 'Motivo' de cada linha antes de confirmar, se quiser registrar o motivo.",
                parent=self.root,
            ):
                return
            for chave_arquivo in selecionados:
                info = linhas_nao_rot[chave_arquivo]
                it = info["item"]
                motivo = info["var_motivo"].get().strip()
                marcar_ignorado(it.get("identificador", ""), it.get("pos", ""), motivo)
                _remover_linha_nao_rot(chave_arquivo)
            atualizar_contadores_nao_rot()
            mostrar_status_nao_rot(
                f"✅ {len(selecionados)} item(ns) marcado(s) como ignorado(s) - gravado na memória.", _COR_OK)
            log(f"🧠 {len(selecionados)} item(ns) marcado(s) como ignorado(s) via aba Não Roteirizado")
        def definir_fluxo_manual_selecionados_nao_rot():
            selecionados = linhas_selecionadas_nao_rot()
            if not selecionados:
                messagebox.showinfo("Nenhum item selecionado",
                                     "Marque ao menos um item na coluna à esquerda antes de continuar.",
                                     parent=self.root)
                return
            sem_fluxo = [c for c in selecionados if not linhas_nao_rot[c]["var_fluxo"].get().strip()]
            if sem_fluxo:
                messagebox.showwarning(
                    "Fluxo não preenchido",
                    f"{len(sem_fluxo)} linha(s) selecionada(s) não têm fluxo preenchido.\n\n"
                    "Preencha (ou escolha na lista) o campo 'Fluxo' de cada linha e tente de novo.",
                    parent=self.root,
                )
                return
            if not messagebox.askyesno(
                "Confirmar",
                f"Mover {len(selecionados)} item(ns) para o fluxo escolhido AGORA e gravar na memória?\n\n"
                "Vale para qualquer obra futura com a mesma posição/identificador - da próxima vez que "
                "aparecer, o roteirizador já manda direto pro fluxo certo, sem precisar definir de novo.",
                parent=self.root,
            ):
                return
            movidos = 0
            falhas = []
            for chave_arquivo in selecionados:
                info = linhas_nao_rot[chave_arquivo]
                it = info["item"]
                fluxo = info["var_fluxo"].get().strip()
                motivo = info["var_motivo"].get().strip()
                # 1) grava na memória - vale pra qualquer obra futura, mesmo que
                #    a movimentação física abaixo falhe por algum motivo.
                marcar_ajuste_manual(it.get("identificador", ""), it.get("pos", ""), fluxo, motivo)
                # 2) move o arquivo de verdade AGORA, pra essa mesma peça já
                #    sair da pasta errada sem precisar reprocessar a obra.
                pasta_atual = it.get("pasta_atual")
                arquivo_nome = it.get("arquivo")
                try:
                    if pasta_atual and arquivo_nome:
                        caminho_atual = os.path.join(pasta_atual, arquivo_nome)
                        if os.path.isfile(caminho_atual):
                            pasta_destino = os.path.join(pasta_atual, fluxo)
                            os.makedirs(pasta_destino, exist_ok=True)
                            shutil.move(caminho_atual, os.path.join(pasta_destino, arquivo_nome))
                            movidos += 1
                        else:
                            falhas.append(f"{arquivo_nome} (arquivo não encontrado mais na pasta)")
                    else:
                        falhas.append(f"{arquivo_nome or '(sem nome)'} (pasta de origem desconhecida)")
                except Exception as ex:
                    falhas.append(f"{arquivo_nome} ({ex})")
                _remover_linha_nao_rot(chave_arquivo)
            atualizar_contadores_nao_rot()
            if falhas:
                mostrar_status_nao_rot(
                    f"⚠️ {movidos} movido(s), {len(falhas)} com problema (veja o log). Fluxo já foi salvo na "
                    "memória mesmo assim.", _COR_AVISO)
                log("⚠️ Falha ao mover fisicamente alguns itens de 'Não Roteirizado': " + "; ".join(falhas))
            else:
                mostrar_status_nao_rot(
                    f"✅ {movidos} item(ns) movido(s) para o fluxo escolhido e memorizado(s) para qualquer "
                    "obra futura.", _COR_OK)
            log(f"🔀 Fluxo manual definido e aplicado para {movidos} item(ns) via aba Não Roteirizado")
        def mover_selecionados_para_padrao_nao_rot():
            selecionados = linhas_selecionadas_nao_rot()
            if not selecionados:
                messagebox.showinfo("Nenhum item selecionado",
                                     "Marque ao menos um item na coluna à esquerda antes de continuar.",
                                     parent=self.root)
                return
            if not messagebox.askyesno(
                "Confirmar",
                f"Mover {len(selecionados)} item(ns) para \"[PADRÃO] PLANILHA\"?\n\n"
                "Isso NÃO descarta a peça para sempre: se um DXF real aparecer para ela em uma obra "
                "futura, o roteirizador continua encontrando e processando normalmente.",
                parent=self.root,
            ):
                return
            for chave_arquivo in selecionados:
                info = linhas_nao_rot[chave_arquivo]
                it = info["item"]
                motivo = info["var_motivo"].get().strip()
                marcar_padrao_planilha_manual(it.get("identificador", ""), it.get("pos", ""), motivo)
                _remover_linha_nao_rot(chave_arquivo)
                limpar_placeholder_padrao()
                tree_padrao.insert("", "end", values=(
                    it.get("of", ""), extrair_tipo_identificador(it.get("identificador", ""), it.get("pos", "")),
                    it.get("pos", ""), it.get("identificador", ""),
                ))
                padrao_planilha.append(it)
            var_padrao_card.set(str(len(padrao_planilha)))
            subabas.tab(aba_padrao, text=f"[PADRÃO] PLANILHA ({len(padrao_planilha)})")
            atualizar_contadores_nao_rot()
            mostrar_status_nao_rot(f"✅ {len(selecionados)} item(ns) movido(s) para [PADRÃO] PLANILHA.", _COR_OK)
            log(f"📋 {len(selecionados)} item(ns) movido(s) para [PADRÃO] PLANILHA via aba Não Roteirizado")
        ttk.Button(barra_acoes_nao_rot, text="Selecionar/desmarcar todos", style="Secundario.TButton",
                   command=selecionar_todos_nao_rot).pack(side="left")
        ttk.Button(barra_acoes_nao_rot, text="Marcar selecionados como ignorado", style="Perigo.TButton",
                   command=marcar_selecionados_ignorados_nao_rot).pack(side="left", padx=(10, 0))
        ttk.Button(barra_acoes_nao_rot, text="Definir fluxo manual", style="Destaque.TButton",
                   command=definir_fluxo_manual_selecionados_nao_rot).pack(side="left", padx=(10, 0))
        ttk.Button(barra_acoes_nao_rot, text="Mover para [PADRÃO] PLANILHA", style="Secundario.TButton",
                   command=mover_selecionados_para_padrao_nao_rot).pack(side="left", padx=(10, 0))
        lbl_status_nao_rot.pack(side="left", padx=(14, 0))
        # === Sub-aba Divergência de Tamanho (interativa) =====================
        # Peças cuja dimensão do DXF diverge da planilha fora da tolerância
        # (comparar_dimensoes_com_tolerancia, calculada em processar()) - o
        # usuário pode marcar como "conferido" quando já sabe que aquela
        # divergência é aceitável, para não vê-la de novo (grava na memória,
        # vale para qualquer obra futura).
        aba_divergencia = ttk.Frame(subabas, style="TFrame", padding=10)
        subabas.add(aba_divergencia, text=f"Divergência Tamanho ({len(divergencias_tamanho)})")
        tk.Label(
            aba_divergencia,
            text="Dimensão do DXF diferente da planilha fora da tolerância (±3mm; ±10mm para Terças Z). "
                 "Marque e confirme quando a divergência já for conhecida/aceitável - grava na memória e "
                 "não aparece mais em nenhuma obra futura.",
            bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 8), wraplength=1000, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        barra_acoes_div = ttk.Frame(aba_divergencia, style="TFrame")
        barra_acoes_div.pack(fill="x", pady=(0, 8))
        lbl_status_divergencia = tk.Label(barra_acoes_div, text="", bg=_COR_FUNDO, fg=_COR_OK, font=("Segoe UI", 9))
        tabela_frame_div = ttk.Frame(aba_divergencia, style="TFrame")
        tabela_frame_div.pack(fill="both", expand=True)
        colunas_div = ("sel", "of", "pos", "id", "dxf", "planilha", "diferenca", "tol")
        tree_divergencia = ttk.Treeview(tabela_frame_div, columns=colunas_div, show="headings", height=14)
        tree_divergencia.heading("sel", text="")
        tree_divergencia.heading("of", text="OF")
        tree_divergencia.heading("pos", text="Posição")
        tree_divergencia.heading("id", text="Identificador")
        tree_divergencia.heading("dxf", text="Dimensão DXF (mm)")
        tree_divergencia.heading("planilha", text="Dimensão Planilha (mm)")
        tree_divergencia.heading("diferenca", text="Diferença (mm)")
        tree_divergencia.heading("tol", text="Tolerância")
        tree_divergencia.column("sel", width=40, anchor="center", stretch=False)
        tree_divergencia.column("of", width=110, anchor="w")
        tree_divergencia.column("pos", width=110, anchor="w")
        tree_divergencia.column("id", width=160, anchor="w")
        tree_divergencia.column("dxf", width=160, anchor="center")
        tree_divergencia.column("planilha", width=160, anchor="center")
        tree_divergencia.column("diferenca", width=110, anchor="center")
        tree_divergencia.column("tol", width=90, anchor="center")
        scroll_div = ttk.Scrollbar(tabela_frame_div, orient="vertical", command=tree_divergencia.yview)
        tree_divergencia.configure(yscrollcommand=scroll_div.set)
        tree_divergencia.pack(side="left", fill="both", expand=True)
        scroll_div.pack(side="left", fill="y")
        itens_por_linha_div = {}
        def preencher_divergencias():
            tree_divergencia.delete(*tree_divergencia.get_children())
            itens_por_linha_div.clear()
            if not divergencias_tamanho:
                tree_divergencia.insert("", "end", values=("", "", "", "Nenhuma divergência", "", "", "", ""))
                return
            for it in divergencias_tamanho:
                largura_dxf = it.get("largura_dxf")
                altura_dxf = it.get("altura_dxf")
                largura_planilha = it.get("largura_planilha")
                ref_planilha = it.get("desenvolvimento_planilha")
                if ref_planilha is None:
                    ref_planilha = it.get("comprimento_planilha")
                dxf_texto = (f"{largura_dxf:.1f} x {altura_dxf:.1f}"
                             if largura_dxf is not None and altura_dxf is not None else "N/A")
                planilha_texto = (f"{largura_planilha:.1f} x {ref_planilha:.1f}"
                                   if largura_planilha is not None and ref_planilha is not None else "N/A")
                diffs = [d for d in (it.get("diferenca_largura"), it.get("diferenca_altura")) if d is not None]
                diferenca_texto = f"{max(diffs):.1f}" if diffs else "N/A"
                tolerancia_texto = f"±{it.get('tolerancia', 3.0):.0f}mm"
                iid = tree_divergencia.insert("", "end", values=(
                    "☐", it.get("of", ""), it.get("pos", ""), it.get("identificador", ""),
                    dxf_texto, planilha_texto, diferenca_texto, tolerancia_texto,
                ))
                itens_por_linha_div[iid] = it
        preencher_divergencias()
        def ao_clicar_tree_div(event):
            regiao = tree_divergencia.identify_region(event.x, event.y)
            if regiao != "cell":
                return
            linha = tree_divergencia.identify_row(event.y)
            coluna = tree_divergencia.identify_column(event.x)
            if linha and coluna == "#1" and linha in itens_por_linha_div:
                atual = tree_divergencia.set(linha, "sel")
                tree_divergencia.set(linha, "sel", "☐" if atual == "☑" else "☑")
        tree_divergencia.bind("<Button-1>", ao_clicar_tree_div)
        def linhas_selecionadas_div():
            return [iid for iid in tree_divergencia.get_children()
                    if iid in itens_por_linha_div and tree_divergencia.set(iid, "sel") == "☑"]
        def selecionar_todos_div():
            candidatos = [i for i in tree_divergencia.get_children() if i in itens_por_linha_div]
            marcar = "☑" if any(tree_divergencia.set(i, "sel") == "☐" for i in candidatos) else "☐"
            for iid in candidatos:
                tree_divergencia.set(iid, "sel", marcar)
        def atualizar_contador_divergencia():
            restantes = len(itens_por_linha_div)
            var_divergencia_card.set(str(restantes))
            subabas.tab(aba_divergencia, text=f"Divergência Tamanho ({restantes})")
        def mostrar_status_div(msg, cor):
            lbl_status_divergencia.config(text=msg, fg=cor)
            self.root.after(6000, lambda: lbl_status_divergencia.config(text=""))
        def marcar_selecionados_conferidos():
            selecionados = linhas_selecionadas_div()
            if not selecionados:
                messagebox.showinfo("Nenhum item selecionado",
                                     "Marque ao menos um item na coluna à esquerda antes de continuar.",
                                     parent=self.root)
                return
            motivo = simpledialog.askstring(
                "Motivo (opcional)", "Motivo da divergência aceita (opcional):", parent=self.root
            ) or ""
            for iid in selecionados:
                it = itens_por_linha_div[iid]
                marcar_divergencia_tamanho_ignorada(it["identificador"], it["pos"], motivo)
                tree_divergencia.delete(iid)
                itens_por_linha_div.pop(iid, None)
            atualizar_contador_divergencia()
            mostrar_status_div(
                f"✅ {len(selecionados)} divergência(s) marcada(s) como conferida(s) - não aparecem mais.", _COR_OK
            )
            log(f"📐 {len(selecionados)} divergência(s) de tamanho marcada(s) como conferida(s) via aba de relatório")
        ttk.Button(barra_acoes_div, text="Selecionar/desmarcar todos", style="Secundario.TButton",
                   command=selecionar_todos_div).pack(side="left")
        ttk.Button(barra_acoes_div, text="Marcar selecionados como conferido", style="Destaque.TButton",
                   command=marcar_selecionados_conferidos).pack(side="left", padx=(10, 0))
        lbl_status_divergencia.pack(side="left", padx=(14, 0))
        # === Sub-aba [PADRÃO] PLANILHA (somente leitura) ===================
        # SOMENTE itens movidos MANUALMENTE para lá na aba Faltantes (memória
        # padrao_planilha_manual). Itens classificados automaticamente pelo
        # código como "IGNORADO" (Terças Z sem DXF próprio, BR_RED, W_, PS)
        # NÃO entram aqui - eles vão para a aba "🧠 Ignorados", já que o
        # próprio roteirizador já sabe que não há CAM para eles.
        aba_padrao = ttk.Frame(subabas, style="TFrame", padding=10)
        subabas.add(aba_padrao, text=f"[PADRÃO] PLANILHA ({len(padrao_planilha)})")
        tk.Label(
            aba_padrao,
            text="Itens movidos manualmente a partir de Faltantes (aba anterior) - peças que o usuário já "
                 "sabe que seguem regra própria e por ora não têm DXF. Não contam como faltante, mas a "
                 "marcação NÃO é definitiva: se um DXF real aparecer para a posição em obra futura, ele "
                 "continua sendo encontrado e processado normalmente.",
            bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 8), wraplength=1000, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        tree_padrao = _criar_tabela_somente_leitura(aba_padrao, padrao_planilha)
        def limpar_placeholder_padrao():
            """Remove a linha 'Nenhum item' da tabela de PADRÃO PLANILHA
            (inserida por _criar_tabela_somente_leitura quando a lista está
            vazia), assim que o primeiro item real for movido para lá a
            partir da aba Faltantes."""
            for iid_placeholder in tree_padrao.get_children():
                valores = tree_padrao.item(iid_placeholder, "values")
                if len(valores) >= 2 and valores[1] == "Nenhum item":
                    tree_padrao.delete(iid_placeholder)
        # === Sub-aba sem CAM (interativa - opção de desconsiderar/forçar CAM) ===
        aba_sem_cam = ttk.Frame(subabas, style="TFrame", padding=10)
        subabas.add(aba_sem_cam, text=f"Sem CAM ({len(sem_cam)})")
        tk.Label(
            aba_sem_cam,
            text="Itens cujo IDENTIFICADOR começa com BR (barra) ou TB (tubo) - cortados por serra/outro "
                 "processo, nunca geram DXF/CAM, por isso não entram na contagem de faltantes. Se algum "
                 "destes precisar de CAM mesmo assim, marque e use \"Forçar CAM\" - vale para qualquer "
                 "obra futura (a posição passa a ser tratada normalmente, inclusive aparecendo em "
                 "Faltantes caso realmente não tenha DXF).",
            bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 8), wraplength=1000, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        barra_acoes_semcam = ttk.Frame(aba_sem_cam, style="TFrame")
        barra_acoes_semcam.pack(fill="x", pady=(0, 8))
        lbl_status_semcam = tk.Label(barra_acoes_semcam, text="", bg=_COR_FUNDO, fg=_COR_OK, font=("Segoe UI", 9))
        tabela_frame_semcam = ttk.Frame(aba_sem_cam, style="TFrame")
        tabela_frame_semcam.pack(fill="both", expand=True)
        colunas_semcam = ("sel", "of", "tipo", "pos", "id")
        tree_semcam = ttk.Treeview(tabela_frame_semcam, columns=colunas_semcam, show="headings", height=14)
        tree_semcam.heading("sel", text="")
        tree_semcam.heading("of", text="OF")
        tree_semcam.heading("tipo", text="Tipo")
        tree_semcam.heading("pos", text="Posição")
        tree_semcam.heading("id", text="Identificador")
        tree_semcam.column("sel", width=40, anchor="center", stretch=False)
        tree_semcam.column("of", width=140, anchor="w")
        tree_semcam.column("tipo", width=140, anchor="w")
        tree_semcam.column("pos", width=120, anchor="w")
        tree_semcam.column("id", width=320, anchor="w")
        scroll_semcam = ttk.Scrollbar(tabela_frame_semcam, orient="vertical", command=tree_semcam.yview)
        tree_semcam.configure(yscrollcommand=scroll_semcam.set)
        tree_semcam.pack(side="left", fill="both", expand=True)
        scroll_semcam.pack(side="left", fill="y")
        itens_por_linha_semcam = {}
        def preencher_semcam():
            tree_semcam.delete(*tree_semcam.get_children())
            itens_por_linha_semcam.clear()
            if not sem_cam:
                tree_semcam.insert("", "end", values=("", "", "Nenhum item", "", ""))
                return
            for it in sem_cam:
                iid = tree_semcam.insert("", "end", values=("☐", it["of"], it["tipo"], it["pos"], it["identificador"]))
                itens_por_linha_semcam[iid] = it
        preencher_semcam()
        def ao_clicar_tree_semcam(event):
            regiao = tree_semcam.identify_region(event.x, event.y)
            if regiao != "cell":
                return
            linha = tree_semcam.identify_row(event.y)
            coluna = tree_semcam.identify_column(event.x)
            if linha and coluna == "#1" and linha in itens_por_linha_semcam:
                atual = tree_semcam.set(linha, "sel")
                tree_semcam.set(linha, "sel", "☐" if atual == "☑" else "☑")
        tree_semcam.bind("<Button-1>", ao_clicar_tree_semcam)
        def linhas_selecionadas_semcam():
            return [iid for iid in tree_semcam.get_children()
                    if iid in itens_por_linha_semcam and tree_semcam.set(iid, "sel") == "☑"]
        def selecionar_todos_semcam():
            candidatos = [i for i in tree_semcam.get_children() if i in itens_por_linha_semcam]
            marcar = "☑" if any(tree_semcam.set(i, "sel") == "☐" for i in candidatos) else "☐"
            for iid in candidatos:
                tree_semcam.set(iid, "sel", marcar)
        def atualizar_contador_semcam():
            restantes = len(itens_por_linha_semcam)
            var_sem_cam_card.set(str(restantes))
            subabas.tab(aba_sem_cam, text=f"Sem CAM ({restantes})")
        def mostrar_status_semcam(msg, cor):
            lbl_status_semcam.config(text=msg, fg=cor)
            self.root.after(6000, lambda: lbl_status_semcam.config(text=""))
        def forcar_cam_selecionados():
            selecionados = linhas_selecionadas_semcam()
            if not selecionados:
                messagebox.showinfo("Nenhum item selecionado",
                                     "Marque ao menos um item na coluna à esquerda antes de continuar.",
                                     parent=self.root)
                return
            if not messagebox.askyesno(
                "Confirmar",
                f"Desconsiderar a regra automática de 'sem CAM' (BR/TB) para {len(selecionados)} item(ns)?\n"
                "Essas posições passarão a ser tratadas normalmente (aparecem em Faltantes se não "
                "tiverem DXF correspondente) - vale para qualquer obra futura.",
                parent=self.root,
            ):
                return
            motivo = simpledialog.askstring("Motivo (opcional)", "Motivo (opcional):", parent=self.root) or ""
            for iid in selecionados:
                it = itens_por_linha_semcam[iid]
                marcar_forcar_cam(it["identificador"], it["pos"], motivo)
                tree_semcam.delete(iid)
                itens_por_linha_semcam.pop(iid, None)
            atualizar_contador_semcam()
            mostrar_status_semcam(f"✅ CAM forçado para {len(selecionados)} item(ns) - gravado na memória.", _COR_OK)
            log(f"🔓 CAM forçado para {len(selecionados)} item(ns) via aba de relatório (desconsiderando BR/TB)")
        ttk.Button(barra_acoes_semcam, text="Selecionar/desmarcar todos", style="Secundario.TButton",
                   command=selecionar_todos_semcam).pack(side="left")
        ttk.Button(barra_acoes_semcam, text="Forçar CAM (desconsiderar)", style="Destaque.TButton",
                   command=forcar_cam_selecionados).pack(side="left", padx=(10, 0))
        lbl_status_semcam.pack(side="left", padx=(14, 0))
        # === Sub-aba ignorados (memória manual + classificação automática do código) ===
        aba_ignorados = ttk.Frame(subabas, style="TFrame", padding=10)
        subabas.add(aba_ignorados, text=f"Ignorados ({len(ignorados_memoria_lista)})")
        tk.Label(
            aba_ignorados,
            text="Itens marcados manualmente em rodadas anteriores como 'não gera DXF mesmo' (válido para "
                 "qualquer obra), MAIS itens que o próprio código já classifica automaticamente como "
                 "ignorados (Terças Z sem DXF próprio, BR_RED, W_, PS) - em ambos os casos, o roteirizador "
                 "já sabe que não há CAM, sem precisar de decisão do usuário.",
            bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 8), wraplength=1000, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        _criar_tabela_somente_leitura(aba_ignorados, ignorados_memoria_lista)
    # ---------- Aba 3: peso por fluxo (gráfico + tabela, dentro da mesma janela) ----------
    def _montar_aba_pesos_vazia(self):
        for widget in self.aba_pesos.winfo_children():
            widget.destroy()
        tk.Label(
            self.aba_pesos,
            text="Nenhum dado de peso ainda.\nProcesse uma planilha/pasta de DXF na aba "
                 "\"Roteirizador\" para visualizar aqui o peso por fluxo.",
            bg=_COR_FUNDO, fg=_COR_TEXTO_SEC, font=("Segoe UI", 11), justify="center",
        ).pack(expand=True)
    def _montar_aba_pesos(self, analise_pesos):
        """
        Monta o gráfico (barras horizontais, pizza ou velas/colunas - conforme
        preferência salva) e a tabela de apoio com o peso total roteirizado
        por fluxo (agrupado pela categoria principal, sem a espessura - ex:
        "Fluxo 3", "Perfiladeira L"), cada fluxo com uma cor própria (fixa
        por padrão, ou customizada pelo usuário no editor de cores), para dar
        uma noção visual rápida de onde está concentrado o peso da obra.
        """
        self._ultima_analise_pesos = analise_pesos
        for widget in self.aba_pesos.winfo_children():
            widget.destroy()
        pai = self.aba_pesos
        dados = agregar_pesos_por_fluxo(analise_pesos)
        cores_customizadas = carregar_cores_fluxo_customizadas()
        tipo_grafico = carregar_preferencia_ui("tipo_grafico_peso", "barras")
        if tipo_grafico not in ("barras", "pizza", "velas"):
            tipo_grafico = "barras"
        def obter_cor(fluxo):
            return cores_customizadas.get(fluxo) or _cor_para_fluxo(fluxo)
        ttk.Label(pai, text="Peso por fluxo", style="Titulo.TLabel").pack(anchor="w")
        if not dados:
            tk.Label(
                pai,
                text="Nenhuma peça com peso calculável foi roteirizada nesta rodada\n"
                     "(faltaram dimensões, espessura ou fluxo definido para todas as peças).",
                bg=_COR_FUNDO, fg=_COR_TEXTO_SEC, font=("Segoe UI", 11), justify="center",
            ).pack(anchor="w", pady=(20, 0))
            return
        peso_total_geral = sum(d["peso_total"] for d in dados)
        pecas_total_geral = sum(d["quantidade_pecas"] for d in dados)
        ttk.Label(
            pai,
            text=(f"Peso total roteirizado: {formatar_numero_br(peso_total_geral)} kg   |   "
                  f"{formatar_numero_br(pecas_total_geral, 0)} peça(s)   |   {len(dados)} fluxo(s)"),
            style="Subtitulo.TLabel",
        ).pack(anchor="w", pady=(2, 10))
        # ----- Barra de controles: tipo de gráfico + editar cores -----
        barra_controles = ttk.Frame(pai, style="TFrame")
        barra_controles.pack(fill="x", pady=(0, 10))
        ttk.Label(barra_controles, text="Tipo de gráfico:", style="TLabel").pack(side="left")
        rotulos_grafico = ["Barras horizontais", "Pizza", "Velas (colunas)"]
        chaves_grafico = ["barras", "pizza", "velas"]
        var_combo_tipo = tk.StringVar()
        combo_tipo = ttk.Combobox(
            barra_controles, textvariable=var_combo_tipo, state="readonly",
            values=rotulos_grafico, width=22,
        )
        indice_atual = chaves_grafico.index(tipo_grafico) if tipo_grafico in chaves_grafico else 0
        combo_tipo.current(indice_atual)
        combo_tipo.pack(side="left", padx=(8, 16))
        def ao_mudar_tipo_grafico(event=None):
            indice = combo_tipo.current()
            nova_chave = chaves_grafico[indice] if 0 <= indice < len(chaves_grafico) else "barras"
            salvar_preferencia_ui("tipo_grafico_peso", nova_chave)
            self._montar_aba_pesos(self._ultima_analise_pesos)
        combo_tipo.bind("<<ComboboxSelected>>", ao_mudar_tipo_grafico)
        ttk.Button(
            barra_controles, text="Editar cores", style="Secundario.TButton",
            command=lambda: self._abrir_editor_cores_fluxo(dados),
        ).pack(side="left")
        # ----- Área do gráfico (Canvas puro, sem dependências extras) -----
        ttk.Label(pai, text="Gráfico (peso total por fluxo)", style="Secao.TLabel").pack(anchor="w", pady=(0, 6))
        frame_grafico = ttk.Frame(pai, style="TFrame")
        frame_grafico.pack(fill="x", pady=(0, 16))
        maior_peso = max(d["peso_total"] for d in dados) or 1.0
        if tipo_grafico == "pizza":
            altura_canvas = max(30 * len(dados) + 40, 260)
        elif tipo_grafico == "velas":
            altura_canvas = 340
        else:
            altura_canvas = max(34 * len(dados) + 16, 80)
        canvas = tk.Canvas(frame_grafico, bg=_COR_FUNDO, highlightthickness=0, height=altura_canvas)
        canvas.pack(fill="x", expand=True)
        def desenhar_barras(event=None):
            canvas.delete("all")
            largura_total = canvas.winfo_width()
            if largura_total < 50:
                largura_total = 900
            largura_rotulo = 210
            margem_direita = 210
            largura_disponivel = max(largura_total - largura_rotulo - margem_direita, 60)
            altura_barra = 34
            for i, item in enumerate(dados):
                y0 = i * altura_barra + 6
                y1 = y0 + altura_barra - 10
                cor = obter_cor(item["fluxo"])
                canvas.create_text(
                    largura_rotulo - 10, (y0 + y1) / 2, text=item["fluxo"],
                    fill=_COR_TEXTO, anchor="e", font=("Segoe UI", 9, "bold"),
                )
                largura_barra_px = max((item["peso_total"] / maior_peso) * largura_disponivel, 2)
                canvas.create_rectangle(
                    largura_rotulo, y0, largura_rotulo + largura_barra_px, y1,
                    fill=cor, outline="",
                )
                texto_valor = (f"{formatar_numero_br(item['peso_total'])} kg  "
                               f"({formatar_numero_br(item['quantidade_pecas'], 0)} pç)")
                canvas.create_text(
                    largura_rotulo + largura_barra_px + 8, (y0 + y1) / 2, text=texto_valor,
                    fill=_COR_TEXTO_SEC, anchor="w", font=("Segoe UI", 9),
                )
        def desenhar_pizza(event=None):
            canvas.delete("all")
            largura_total = canvas.winfo_width() or 900
            altura_total = max(canvas.winfo_height(), altura_canvas)
            diametro = max(min(altura_total - 30, largura_total * 0.42), 120)
            raio = diametro / 2
            cx = raio + 30
            cy = altura_total / 2
            angulo_atual = 90.0  # começa no topo (12h)
            for item in dados:
                fracao = (item["peso_total"] / peso_total_geral) if peso_total_geral else 0
                extensao = fracao * 360.0
                if extensao <= 0:
                    continue
                cor = obter_cor(item["fluxo"])
                canvas.create_arc(
                    cx - raio, cy - raio, cx + raio, cy + raio,
                    start=angulo_atual, extent=-extensao,
                    fill=cor, outline=_COR_FUNDO, width=2, style="pieslice",
                )
                angulo_atual -= extensao
            x_legenda = cx + raio + 40
            y_legenda = 16
            for item in dados:
                cor = obter_cor(item["fluxo"])
                fracao_pct = (item["peso_total"] / peso_total_geral * 100) if peso_total_geral else 0
                canvas.create_rectangle(x_legenda, y_legenda, x_legenda + 16, y_legenda + 16, fill=cor, outline="")
                texto = (f"{item['fluxo']} - {formatar_numero_br(item['peso_total'])} kg "
                         f"({fracao_pct:.1f}%)")
                canvas.create_text(
                    x_legenda + 24, y_legenda + 8, text=texto, fill=_COR_TEXTO,
                    anchor="w", font=("Segoe UI", 9),
                )
                y_legenda += 28
        def desenhar_velas(event=None):
            canvas.delete("all")
            largura_total = canvas.winfo_width()
            if largura_total < 50:
                largura_total = 900
            altura_total = altura_canvas
            margem_inferior = 70
            margem_superior = 34
            altura_disponivel = max(altura_total - margem_inferior - margem_superior, 60)
            n = len(dados)
            espaco = (largura_total - 40) / n if n else 0
            largura_coluna = max(espaco * 0.55, 18)
            x = 30
            for item in dados:
                fracao = (item["peso_total"] / maior_peso) if maior_peso else 0
                altura_barra = fracao * altura_disponivel
                cor = obter_cor(item["fluxo"])
                x_centro = x + espaco / 2
                y1 = margem_superior + altura_disponivel
                y0 = y1 - altura_barra
                canvas.create_rectangle(
                    x_centro - largura_coluna / 2, y0, x_centro + largura_coluna / 2, y1,
                    fill=cor, outline="",
                )
                canvas.create_text(
                    x_centro, y0 - 8, text=f"{formatar_numero_br(item['peso_total'])} kg",
                    fill=_COR_TEXTO_SEC, font=("Segoe UI", 8), anchor="s",
                )
                canvas.create_text(
                    x_centro, y1 + 8, text=item["fluxo"], fill=_COR_TEXTO,
                    font=("Segoe UI", 8, "bold"), anchor="n", width=max(espaco - 4, 40),
                )
                x += espaco
        funcao_desenho = {"barras": desenhar_barras, "pizza": desenhar_pizza, "velas": desenhar_velas}[tipo_grafico]
        canvas.bind("<Configure>", funcao_desenho)
        pai.after(80, funcao_desenho)
        # ----- Tabela de apoio (mesmas cores do gráfico, por linha) -----
        ttk.Label(pai, text="Detalhamento por fluxo", style="Secao.TLabel").pack(anchor="w", pady=(4, 6))
        frame_tabela = ttk.Frame(pai, style="TFrame")
        frame_tabela.pack(fill="both", expand=True)
        colunas = ("fluxo", "posicoes", "pecas", "peso_total", "peso_medio")
        tree = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=min(len(dados), 12))
        tree.heading("fluxo", text="Fluxo")
        tree.heading("posicoes", text="Posições")
        tree.heading("pecas", text="Peças (qtd)")
        tree.heading("peso_total", text="Peso total (kg)")
        tree.heading("peso_medio", text="Peso médio/peça (kg)")
        tree.column("fluxo", width=260, anchor="w")
        tree.column("posicoes", width=100, anchor="center")
        tree.column("pecas", width=120, anchor="center")
        tree.column("peso_total", width=160, anchor="e")
        tree.column("peso_medio", width=170, anchor="e")
        scroll_tabela = ttk.Scrollbar(frame_tabela, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_tabela.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll_tabela.pack(side="left", fill="y")
        for item in dados:
            cor = obter_cor(item["fluxo"])
            tag = f"cor_{cor.lstrip('#')}"
            tree.tag_configure(tag, background=cor, foreground="#FFFFFF")
            tree.insert("", "end", tags=(tag,), values=(
                item["fluxo"],
                item["quantidade_posicoes"],
                formatar_numero_br(item["quantidade_pecas"], 0),
                formatar_numero_br(item["peso_total"]),
                formatar_numero_br(item["peso_medio"]),
            ))
    def _abrir_editor_cores_fluxo(self, dados):
        """
        Diálogo modal para customizar a cor de cada fluxo (usada no gráfico E
        na tabela de detalhamento da aba "⚖️ Peso por Fluxo"). Clique no
        quadrado colorido para escolher uma nova cor (colorchooser nativo do
        Tk); "Salvar e aplicar" grava as cores na memória (SQLite - vale para
        qualquer obra futura) e redesenha a aba com as novas cores.
        """
        janela = tk.Toplevel(self.root)
        janela.title("Editar cores do gráfico de peso por fluxo")
        janela.configure(bg=_COR_FUNDO)
        janela.geometry("440x480")
        janela.minsize(380, 380)
        janela.transient(self.root)
        janela.grab_set()
        container = ttk.Frame(janela, style="TFrame", padding=16)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="Cores por fluxo", style="Secao.TLabel").pack(anchor="w", pady=(0, 4))
        tk.Label(
            container,
            text="Clique no quadrado colorido para escolher uma nova cor. As cores ficam salvas e valem "
                 "para qualquer obra futura, até serem trocadas de novo ou restauradas ao padrão.",
            bg=_COR_FUNDO, fg=_COR_TEXTO_SEC, font=("Segoe UI", 8), wraplength=400, justify="left",
        ).pack(anchor="w", pady=(0, 10))
        area_frame = ttk.Frame(container, style="TFrame")
        area_frame.pack(fill="both", expand=True)
        canvas_lista = tk.Canvas(area_frame, bg=_COR_FUNDO, highlightthickness=0)
        scroll_lista = ttk.Scrollbar(area_frame, orient="vertical", command=canvas_lista.yview)
        canvas_lista.configure(yscrollcommand=scroll_lista.set)
        canvas_lista.pack(side="left", fill="both", expand=True)
        scroll_lista.pack(side="left", fill="y")
        frame_interno = tk.Frame(canvas_lista, bg=_COR_FUNDO)
        id_janela_interna = canvas_lista.create_window((0, 0), window=frame_interno, anchor="nw")
        def _ajustar_scroll(event=None):
            canvas_lista.configure(scrollregion=canvas_lista.bbox("all"))
        def _ajustar_largura(event):
            canvas_lista.itemconfigure(id_janela_interna, width=event.width)
        frame_interno.bind("<Configure>", _ajustar_scroll)
        canvas_lista.bind("<Configure>", _ajustar_largura)
        cores_customizadas_atuais = carregar_cores_fluxo_customizadas()
        cores_pendentes = {
            item["fluxo"]: cores_customizadas_atuais.get(item["fluxo"]) or _cor_para_fluxo(item["fluxo"])
            for item in dados
        }
        swatches = {}
        def escolher_cor(fluxo):
            cor_atual = cores_pendentes.get(fluxo, "#42a5f5")
            resultado_cor = colorchooser.askcolor(color=cor_atual, parent=janela, title=f"Cor para {fluxo}")
            if resultado_cor and resultado_cor[1]:
                cores_pendentes[fluxo] = resultado_cor[1]
                swatches[fluxo].configure(bg=resultado_cor[1])
        for item in dados:
            fluxo = item["fluxo"]
            linha = tk.Frame(frame_interno, bg=_COR_FUNDO)
            linha.pack(fill="x", pady=3)
            swatch = tk.Label(
                linha, text="", bg=cores_pendentes[fluxo], width=4, relief="flat",
                cursor="hand2", highlightthickness=1, highlightbackground="#555555",
            )
            swatch.pack(side="left", padx=(0, 10))
            swatch.bind("<Button-1>", lambda e, f=fluxo: escolher_cor(f))
            tk.Label(linha, text=fluxo, bg=_COR_FUNDO, fg=_COR_TEXTO, font=("Segoe UI", 9)).pack(side="left")
            swatches[fluxo] = swatch
        def restaurar_padroes():
            for item in dados:
                fluxo = item["fluxo"]
                cores_pendentes[fluxo] = _cor_para_fluxo(fluxo)
                swatches[fluxo].configure(bg=cores_pendentes[fluxo])
        def aplicar():
            for fluxo, cor in cores_pendentes.items():
                salvar_cor_fluxo_customizada(fluxo, cor)
            janela.destroy()
            self._montar_aba_pesos(self._ultima_analise_pesos)
        def cancelar():
            janela.destroy()
        barra_botoes = ttk.Frame(container, style="TFrame")
        barra_botoes.pack(fill="x", pady=(12, 0))
        ttk.Button(barra_botoes, text="Restaurar padrão", style="Secundario.TButton",
                   command=restaurar_padroes).pack(side="left")
        ttk.Button(barra_botoes, text="Cancelar", style="Secundario.TButton",
                   command=cancelar).pack(side="right", padx=(8, 0))
        ttk.Button(barra_botoes, text="Salvar e aplicar", style="Destaque.TButton",
                   command=aplicar).pack(side="right")
    # ---------- Aba 4: Verificador ----------
    def _criar_area_rolavel(self, parent):
        """Cria um Canvas+Scrollbar+Frame interno com rolagem por mouse wheel
        já configurada e uma barra de rolagem mais visível/larga."""
        canvas = tk.Canvas(parent, bg=_COR_PAINEL_2, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview, style="Verificador.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")
        inner = ttk.Frame(canvas, style="Cartao.TFrame")
        janela = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(janela, width=e.width))
        def _rolar(event):
            delta = event.delta
            if delta == 0:
                delta = 120 if getattr(event, "num", 5) == 4 else -120
            canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: (
            canvas.bind_all("<MouseWheel>", _rolar),
            canvas.bind_all("<Button-4>", _rolar),
            canvas.bind_all("<Button-5>", _rolar),
        ))
        canvas.bind("<Leave>", lambda e: (
            canvas.unbind_all("<MouseWheel>"),
            canvas.unbind_all("<Button-4>"),
            canvas.unbind_all("<Button-5>"),
        ))
        return canvas, inner
    def _montar_aba_verificador(self):
        """
        Monta a aba "🔍 Verificador": permite apontar uma ou mais pastas de
        obras já roteirizadas e comparar automaticamente (assim que a pasta é
        adicionada, e continuamente em segundo plano depois) o que o
        roteirizador decidiu com a organização ATUAL da pasta, identificando
        posições que foram movidas manualmente pra outro fluxo depois.
        Ao descrever o motivo e salvar, o ajuste vira permanente na memória
        (SQLite) e passa a valer pra qualquer obra futura com a mesma
        posição/identificador.
        (Peças que ficaram fora de qualquer fluxo por falta de regra são
        tratadas na aba "🚫 Não Roteirizado", dentro de Relatório de
        Divergências - não faz parte deste Verificador.)
        """
        pai = self.aba_verificador
        for widget in pai.winfo_children():
            widget.destroy()
        style = ttk.Style()
        try:
            style.configure("Verificador.Vertical.TScrollbar", width=12)
        except Exception:
            pass
        self._verificador_monitorando = False
        ttk.Label(pai, text="Verificador de ajustes manuais", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(
            pai,
            text="Compare o que o roteirizador organizou automaticamente com o que foi movido manualmente "
                 "depois. Descreva o motivo de cada ajuste e, ao salvar, ele passa a valer para QUALQUER obra "
                 "futura com a mesma posição/identificador. Também dá para só LER qualquer pasta e ver o que está fora da regra "
                 "(\"Conferir pelas regras\", mais abaixo) — sem precisar ter roteirizado pelo app.",
            style="Subtitulo.TLabel", wraplength=1100,
        ).pack(anchor="w", pady=(0, 14))
        # ----- bloco: pastas de obras a comparar -----
        ttk.Label(pai, text="Pastas de obras já roteirizadas", style="Secao.TLabel").pack(anchor="w", pady=(0, 4))
        linha_add = ttk.Frame(pai, style="TFrame")
        linha_add.pack(fill="x", pady=(0, 8))
        self.var_verificador_caminho = tk.StringVar()
        entry_caminho = ttk.Entry(linha_add, textvariable=self.var_verificador_caminho,
                                   style="TEntry", font=("Segoe UI", 10))
        entry_caminho.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))
        ttk.Button(linha_add, text="Procurar...", style="Secundario.TButton",
                   command=self._verificador_escolher_pasta).pack(side="left")
        ttk.Button(linha_add, text="Adicionar", style="Secundario.TButton",
                   command=self._verificador_adicionar_pasta).pack(side="left", padx=(8, 0))
        entry_caminho.bind("<Return>", lambda e: self._verificador_adicionar_pasta())
        _placeholder(entry_caminho, self.var_verificador_caminho, "Cole o caminho da pasta da obra e pressione Enter…")
        # Botões de ação ficam logo abaixo do campo de adicionar pasta, ANTES
        # da lista - é aqui que fazem sentido, junto da ação de adicionar.
        barra_pastas = ttk.Frame(pai, style="TFrame")
        barra_pastas.pack(fill="x", pady=(0, 8))
        ttk.Button(barra_pastas, text="Selecionar/desmarcar todas", style="Secundario.TButton",
                   command=self._verificador_selecionar_todas_pastas).pack(side="left")
        ttk.Button(barra_pastas, text="Remover selecionadas", style="Perigo.TButton",
                   command=self._verificador_remover_pastas).pack(side="left", padx=(8, 0))
        ttk.Button(barra_pastas, text="Verificar agora", style="Destaque.TButton",
                   command=self._verificador_atualizar_comparacoes).pack(side="left", padx=(8, 0))
        self.lbl_verificador_status = tk.Label(barra_pastas, text="", bg=_COR_FUNDO, fg=_COR_AVISO,
                                                font=("Segoe UI", 9, "bold"), wraplength=800, justify="left")
        self.lbl_verificador_status.pack(side="left", padx=(14, 0))
        frame_pastas = ttk.Frame(pai, style="TFrame")
        frame_pastas.pack(fill="x", pady=(0, 6))
        self.tree_verificador_pastas = ttk.Treeview(
            frame_pastas, columns=("sel", "caminho"), show="headings", height=5
        )
        self.tree_verificador_pastas.heading("sel", text="")
        self.tree_verificador_pastas.heading("caminho", text="Pasta da obra (com checkbox para seleção)")
        self.tree_verificador_pastas.column("sel", width=40, anchor="center", stretch=False)
        self.tree_verificador_pastas.column("caminho", width=900, anchor="w")
        scroll_pastas = ttk.Scrollbar(frame_pastas, orient="vertical", command=self.tree_verificador_pastas.yview,
                                       style="Verificador.Vertical.TScrollbar")
        self.tree_verificador_pastas.configure(yscrollcommand=scroll_pastas.set)
        self.tree_verificador_pastas.pack(side="left", fill="both", expand=True)
        scroll_pastas.pack(side="left", fill="y")
        self.tree_verificador_pastas.bind("<Button-1>", self._verificador_clicar_pasta)
        def _rolar_pastas(event):
            delta = event.delta
            if delta == 0:
                delta = 120 if getattr(event, "num", 5) == 4 else -120
            self.tree_verificador_pastas.yview_scroll(int(-1 * (delta / 120)), "units")
        self.tree_verificador_pastas.bind("<Enter>", lambda e: (
            self.tree_verificador_pastas.bind_all("<MouseWheel>", _rolar_pastas),
            self.tree_verificador_pastas.bind_all("<Button-4>", _rolar_pastas),
            self.tree_verificador_pastas.bind_all("<Button-5>", _rolar_pastas),
        ))
        self.tree_verificador_pastas.bind("<Leave>", lambda e: (
            self.tree_verificador_pastas.unbind_all("<MouseWheel>"),
            self.tree_verificador_pastas.unbind_all("<Button-4>"),
            self.tree_verificador_pastas.unbind_all("<Button-5>"),
        ))
        tk.Label(
            pai, text="Assim que uma pasta é adicionada, ela já é comparada automaticamente com o log de "
                      "roteirização salvo dentro dela - e continua sendo verificada em segundo plano, então "
                      "qualquer arquivo que você mover de pasta depois aparece sozinho na lista abaixo. "
                      "O checkbox aqui serve só para escolher quais remover.",
            bg=_COR_FUNDO, fg=_COR_TEXTO_SEC if "_COR_TEXTO_SEC" in globals() else _COR_AVISO,
            font=("Segoe UI", 8), wraplength=1000, justify="left",
        ).pack(anchor="w", pady=(0, 10))
        # ----- bloco: CONFERÊNCIA SOMENTE LEITURA pelas regras (não depende do "retrato") -----
        ttk.Label(pai, text="Conferir pelas regras (somente leitura)", style="Secao.TLabel").pack(anchor="w", pady=(18, 4))
        tk.Label(
            pai,
            text="Serve para QUALQUER pasta de DXF da lista acima — mesmo organizada à mão, por outra pessoa ou por outra "
                 "versão, sem \"retrato\". O programa aplica as regras de roteirização com a planilha da obra e mostra só "
                 "as posições que estão em pasta diferente da que a regra manda. NADA é movido. Se a posição está certa "
                 "onde está (ou você quer outro fluxo), escolha o fluxo na linha, escreva o motivo e clique em Salvar: "
                 "vira ajuste permanente para qualquer obra futura.",
            bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 8), wraplength=1100, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        linha_pl = ttk.Frame(pai, style="TFrame")
        linha_pl.pack(fill="x", pady=(0, 6))
        self.var_verificador_planilha = tk.StringVar()
        entry_pl = ttk.Entry(linha_pl, textvariable=self.var_verificador_planilha, style="TEntry", font=("Segoe UI", 10))
        entry_pl.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))
        ttk.Button(linha_pl, text="Procurar planilha...", style="Secundario.TButton",
                   command=self._verificador_escolher_planilha).pack(side="left")
        ttk.Button(linha_pl, text="🔎 Conferir pastas da lista", style="Destaque.TButton",
                   command=self._vregra_conferir).pack(side="left", padx=(8, 0))
        _placeholder(entry_pl, self.var_verificador_planilha,
                     "Planilha (.csv / .xlsx) da obra — se ficar vazio, usa a da aba Roteirizador…")
        self.lbl_vregra_status = tk.Label(pai, text="", bg=_COR_FUNDO, fg=_COR_OK, font=("Segoe UI", 9, "bold"),
                                           wraplength=1100, justify="left")
        self.lbl_vregra_status.pack(anchor="w", pady=(0, 6))
        frame_vregra = ttk.Frame(pai, style="Cartao.TFrame")
        frame_vregra.pack(fill="x")
        _canvas_vr, self.frame_vregra_linhas = self._criar_area_rolavel(frame_vregra)
        _canvas_vr.configure(height=230)
        larg_vr = {0: 90, 1: 90, 2: 120, 3: 200, 4: 160, 5: 160, 6: 170}
        for col_idx, minsize in larg_vr.items():
            self.frame_vregra_linhas.grid_columnconfigure(col_idx, minsize=minsize)
        self.frame_vregra_linhas.grid_columnconfigure(7, weight=1, minsize=200)   # motivo
        self.frame_vregra_linhas.grid_columnconfigure(8, minsize=100)
        for col_idx, titulo in enumerate(["OF", "Posição", "Identificador", "Arquivo", "Regra manda",
                                          "Está em", "Fluxo a salvar", "Motivo", ""]):
            tk.Label(self.frame_vregra_linhas, text=titulo, bg=_COR_PAINEL, fg=_NEON_CIANO_SUAVE,
                     font=("Segoe UI", 9, "bold"), anchor="w").grid(row=0, column=col_idx, sticky="nsew", padx=(4, 4), pady=6)
        self.lbl_vregra_vazio = tk.Label(
            self.frame_vregra_linhas, text="Nenhuma conferência feita ainda (ou tudo está de acordo com as regras).",
            bg=_COR_PAINEL_2, fg=_COR_TEXTO_SEC, font=("Segoe UI", 9), anchor="w")
        self.lbl_vregra_vazio.grid(row=1, column=0, columnspan=9, sticky="w", padx=8, pady=10)
        self._vregra_proximo_row = 2
        self._vregra_linhas = {}
        self._vregra_thread = None
        barra_vr = ttk.Frame(pai, style="TFrame")
        barra_vr.pack(fill="x", pady=(8, 0))
        ttk.Button(barra_vr, text="Salvar todos os que já têm motivo", style="Destaque.TButton",
                   command=self._vregra_salvar_todos).pack(side="left")
        # ----- bloco: fluxo alterado manualmente -----
        ttk.Label(pai, text="Posições com fluxo alterado manualmente (só em pastas roteirizadas por este programa)", style="Secao.TLabel").pack(
            anchor="w", pady=(18, 4))
        tk.Label(
            pai,
            text="Se você moveu uma posição para outro fluxo, é porque o roteirizador decidiu errado. Preencha "
                 "o motivo na própria linha e clique em 'Salvar' ao lado - o programa memoriza e passa a "
                 "roteirizar essa posição direto no fluxo certo em qualquer obra futura.",
            bg=_COR_FUNDO, fg=_COR_AVISO, font=("Segoe UI", 8), wraplength=1100, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        frame_resultado_wrapper = ttk.Frame(pai, style="Cartao.TFrame")
        frame_resultado_wrapper.pack(fill="both", expand=True)
        _canvas_div, self.frame_verificador_linhas = self._criar_area_rolavel(frame_resultado_wrapper)
        larguras_col = {"of": 90, "pos": 80, "identificador": 160, "arquivo": 210,
                         "original": 150, "atual": 150}
        for col_idx, chave_largura in enumerate(["of", "pos", "identificador", "arquivo", "original", "atual"]):
            self.frame_verificador_linhas.grid_columnconfigure(col_idx, minsize=larguras_col[chave_largura])
        self.frame_verificador_linhas.grid_columnconfigure(6, weight=1, minsize=220)  # motivo (expande)
        self.frame_verificador_linhas.grid_columnconfigure(7, minsize=110)  # botão salvar
        titulos_cabecalho = ["OF", "Posição", "Identificador", "Arquivo",
                              "Fluxo Roteirizado", "Fluxo Atual", "Motivo", ""]
        for col_idx, titulo in enumerate(titulos_cabecalho):
            tk.Label(
                self.frame_verificador_linhas, text=titulo, bg=_COR_PAINEL, fg=_NEON_CIANO_SUAVE,
                font=("Segoe UI", 9, "bold"), anchor="w",
            ).grid(row=0, column=col_idx, sticky="nsew", padx=(4, 4), pady=6)
        self.lbl_verificador_vazio = tk.Label(
            self.frame_verificador_linhas, text="Nenhuma posição alterada manualmente até agora.",
            bg=_COR_PAINEL_2, fg=_COR_TEXTO_SEC, font=("Segoe UI", 9), anchor="w",
        )
        self.lbl_verificador_vazio.grid(row=1, column=0, columnspan=8, sticky="w", padx=8, pady=10)
        self._verificador_proximo_row = 2
        self._verificador_linhas_widgets = {}  # (pasta, arquivo) -> dict com widgets/estado da linha
        barra_resultado = ttk.Frame(pai, style="TFrame")
        barra_resultado.pack(fill="x", pady=(8, 0))
        ttk.Button(barra_resultado, text="Salvar todos os que já têm motivo", style="Destaque.TButton",
                   command=self._verificador_salvar_todos_preenchidos).pack(side="left")
        self.lbl_verificador_status2 = tk.Label(barra_resultado, text="", bg=_COR_FUNDO, fg=_COR_OK,
                                                 font=("Segoe UI", 9))
        self.lbl_verificador_status2.pack(side="left", padx=(14, 0))
    def _verificador_escolher_pasta(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta da obra (arquivos DXF já roteirizados)")
        if caminho:
            self.var_verificador_caminho.set(caminho)
    @staticmethod
    def _verificador_limpar_caminho(texto):
        """Aceita o caminho como vem do Windows: com aspas ("Copiar como caminho"), com espaços nas pontas,
        com %VARIAVEIS% ou apontando pra um arquivo (aí usa a pasta dele)."""
        t = (texto or "").strip().strip('"').strip("'").strip()
        t = os.path.expandvars(t)
        if t and os.path.isfile(t):
            t = os.path.dirname(t)
        return t

    def _verificador_adicionar_pasta(self):
        caminho = self._verificador_limpar_caminho(self.var_verificador_caminho.get())
        if not caminho or not os.path.isdir(caminho):
            messagebox.showwarning(
                "Pasta inválida",
                "Não encontrei essa pasta:\n\n" + (caminho or "(campo vazio)") +
                "\n\nConfira o caminho (pode colar com aspas, tudo bem) e se o computador consegue abrir essa pasta.",
                parent=self.root)
            return
        for iid in self.tree_verificador_pastas.get_children():
            if os.path.abspath(self.tree_verificador_pastas.set(iid, "caminho")) == os.path.abspath(caminho):
                self.var_verificador_caminho.set("")
                self._verificador_atualizar_comparacoes()
                return
        self.tree_verificador_pastas.insert("", "end", values=("☑", caminho))
        self.var_verificador_caminho.set("")
        if not hasattr(self, "_verificador_novas"):
            self._verificador_novas = set()
        self._verificador_novas.add(os.path.abspath(caminho))       # se não tiver retrato, explica na 1ª verificação
        # Ao adicionar, já compara na hora com o log de roteirização salvo
        # dentro da pasta, sem precisar clicar em nada.
        self._verificador_atualizar_comparacoes()
        self._verificador_garantir_monitoramento()
    def _verificador_clicar_pasta(self, event):
        regiao = self.tree_verificador_pastas.identify_region(event.x, event.y)
        if regiao != "cell":
            return
        linha = self.tree_verificador_pastas.identify_row(event.y)
        coluna = self.tree_verificador_pastas.identify_column(event.x)
        if linha and coluna == "#1":
            atual = self.tree_verificador_pastas.set(linha, "sel")
            self.tree_verificador_pastas.set(linha, "sel", "☐" if atual == "☑" else "☑")
    def _verificador_selecionar_todas_pastas(self):
        itens = self.tree_verificador_pastas.get_children()
        if not itens:
            return
        marcar = "☑" if any(self.tree_verificador_pastas.set(i, "sel") == "☐" for i in itens) else "☐"
        for iid in itens:
            self.tree_verificador_pastas.set(iid, "sel", marcar)
    def _verificador_remover_pastas(self):
        pastas_removidas = set()
        for iid in list(self.tree_verificador_pastas.get_children()):
            if self.tree_verificador_pastas.set(iid, "sel") == "☑":
                pastas_removidas.add(os.path.abspath(self.tree_verificador_pastas.set(iid, "caminho")))
                self.tree_verificador_pastas.delete(iid)
        for chave in list(self._verificador_linhas_widgets.keys()):
            if os.path.abspath(chave[0]) in pastas_removidas:
                self._verificador_remover_linha_resultado(chave)
        self._verificador_atualizar_comparacoes(mostrar_log=False)
    # ---------- Verificador: conferência SOMENTE LEITURA pelas regras ----------
    def _verificador_escolher_planilha(self):
        caminho = filedialog.askopenfilename(
            title="Selecione a planilha da obra",
            filetypes=[("Planilhas", "*.csv *.xlsx *.xls"), ("CSV", "*.csv"),
                       ("Excel", "*.xlsx *.xls"), ("Todos os arquivos", "*.*")], parent=self.root)
        if caminho:
            self.var_verificador_planilha.set(caminho)

    def _vregra_conferir(self):
        t_ant = getattr(self, "_vregra_thread", None)
        if t_ant is not None and t_ant.is_alive():
            return
        # pasta digitada no campo mas ainda não adicionada: adiciona agora
        if self._verificador_limpar_caminho(self.var_verificador_caminho.get()):
            self._verificador_adicionar_pasta()
        pastas = [self.tree_verificador_pastas.set(i, "caminho") for i in self.tree_verificador_pastas.get_children()]
        if not pastas:
            messagebox.showinfo("Nenhuma pasta", "Adicione (campo acima) a pasta dos DXF que você quer conferir.", parent=self.root)
            return
        planilha = _normalizar_caminho(self.var_verificador_planilha.get())
        if not planilha and getattr(self, "var_planilha", None) is not None:
            planilha = _normalizar_caminho(self.var_planilha.get())
        if not planilha or not os.path.isfile(planilha):
            messagebox.showwarning(
                "Planilha necessária",
                "Para aplicar as regras o programa precisa da planilha da obra (a mesma do Roteirizador: é nela que estão "
                "o identificador, a definição e a espessura de cada posição).\n\nEscolha a planilha no campo acima.",
                parent=self.root)
            return
        self.var_verificador_planilha.set(planilha)
        self.lbl_vregra_status.config(text="🔎 Conferindo com as regras (somente leitura)… pode levar alguns minutos em pasta de rede.",
                                       fg=_COR_AVISO)
        saida = {"erro": None, "linhas": [], "total": 0, "pastas_ok": 0}

        def trabalho():
            try:
                df = carregar_planilha(planilha)
                essenciais = ['OF_N', 'POS_N', 'ID_N', 'DEF_N', 'ESP_N', 'LARGURA_N', 'DESENV_N', 'COMPR_N', 'QTD_N']
                if len([c for c in essenciais if c in df.columns]) < 5:
                    raise RuntimeError("Colunas essenciais não encontradas na planilha selecionada.")
                inicializar_memoria()
                for pasta in pastas:
                    sim, total = conferir_pasta_com_regras(df, pasta)
                    saida["linhas"].extend(sim)
                    saida["total"] += total
                    saida["pastas_ok"] += 1
            except Exception as ex:                                      # noqa: BLE001
                saida["erro"] = ex
        t = threading.Thread(target=trabalho, daemon=True)
        self._vregra_thread = t
        t.start()
        self.root.after(200, lambda: self._vregra_esperar(t, saida))

    def _vregra_esperar(self, t, saida):
        try:
            if t.is_alive():
                self.root.after(200, lambda: self._vregra_esperar(t, saida))
                return
        except tk.TclError:
            return
        self._vregra_thread = None
        try:
            if saida["erro"] is not None:
                self.lbl_vregra_status.config(text=f"❌ Não consegui conferir: {saida['erro']}", fg=_COR_ERRO if "_COR_ERRO" in globals() else _COR_AVISO)
                return
            for chave in list(self._vregra_linhas.keys()):
                self._vregra_remover_linha(chave)
            vistos = set()
            for d in saida["linhas"]:
                chave = os.path.normcase(os.path.abspath(d["caminho"]))
                if chave in vistos:
                    continue
                vistos.add(chave)
                self._vregra_criar_linha(chave, d)
            n = len(self._vregra_linhas)
            if n:
                self.lbl_vregra_status.config(
                    text=f"⚠️ {n} posição(ões) fora da regra, de {saida['total']} DXF conferido(s) em {saida['pastas_ok']} pasta(s). "
                         "Nada foi movido.", fg=_COR_AVISO)
            else:
                self.lbl_vregra_status.config(
                    text=f"✅ {saida['total']} DXF conferido(s) em {saida['pastas_ok']} pasta(s): todos estão na pasta que a regra manda.",
                    fg=_COR_OK)
            log(f"🔎 Verificador (somente leitura): {n} fora da regra / {saida['total']} conferidos")
        except tk.TclError:
            return

    def _vregra_criar_linha(self, chave, d):
        pai_l = self.frame_vregra_linhas
        row_idx = self._vregra_proximo_row
        self._vregra_proximo_row += 1
        widgets = []
        def _lbl(texto, col):
            w = tk.Label(pai_l, text=texto, bg=_COR_PAINEL_2, fg=_COR_TEXTO, font=("Segoe UI", 9), anchor="w", justify="left")
            w.grid(row=row_idx, column=col, sticky="nsew", padx=(4, 4), pady=4)
            widgets.append(w)
            return w
        _lbl(d.get("of", ""), 0)
        _lbl(d.get("pos", ""), 1)
        _lbl(d.get("identificador", ""), 2)
        _lbl(d.get("arquivo", ""), 3)
        _lbl(str(d.get("regra", "")) + ("  (memória)" if d.get("ajuste_manual") else ""), 4)
        _lbl(d.get("atual", ""), 5)
        opcoes = []
        for cand in (d.get("atual"), d.get("regra")):
            if cand and _nome_parece_fluxo(cand) and cand not in opcoes:
                opcoes.append(cand)
        var_fluxo = tk.StringVar(value=opcoes[0] if opcoes else "")
        combo = ttk.Combobox(pai_l, textvariable=var_fluxo, values=opcoes, font=("Segoe UI", 9))
        combo.grid(row=row_idx, column=6, sticky="nsew", padx=(4, 4), pady=4, ipady=2)
        widgets.append(combo)
        var_motivo = tk.StringVar()
        entry = ttk.Entry(pai_l, textvariable=var_motivo, style="TEntry", font=("Segoe UI", 9))
        entry.grid(row=row_idx, column=7, sticky="nsew", padx=(4, 4), pady=4, ipady=3)
        widgets.append(entry)
        btn = ttk.Button(pai_l, text="Salvar", style="Secundario.TButton", state="disabled",
                         command=lambda: self._vregra_salvar_linha(chave))
        btn.grid(row=row_idx, column=8, sticky="nsew", padx=(4, 4), pady=4)
        widgets.append(btn)
        def _ao_digitar(*_a):
            btn.config(state=("normal" if var_motivo.get().strip() and var_fluxo.get().strip() else "disabled"))
        var_motivo.trace_add("write", _ao_digitar)
        var_fluxo.trace_add("write", _ao_digitar)
        entry.bind("<Return>", lambda e: self._vregra_salvar_linha(chave))
        self._vregra_linhas[chave] = {"dados": dict(d), "var_motivo": var_motivo, "var_fluxo": var_fluxo, "widgets": widgets}
        self.lbl_vregra_vazio.grid_remove()

    def _vregra_remover_linha(self, chave):
        info = self._vregra_linhas.pop(chave, None)
        if not info:
            return
        for w in info["widgets"]:
            w.destroy()
        if not self._vregra_linhas:
            self.lbl_vregra_vazio.grid()

    def _vregra_salvar_linha(self, chave, silencioso=False):
        info = self._vregra_linhas.get(chave)
        if not info:
            return False
        motivo = info["var_motivo"].get().strip()
        fluxo = info["var_fluxo"].get().strip()
        d = info["dados"]
        if not motivo or not fluxo:
            return False
        if not _nome_parece_fluxo(fluxo):
            messagebox.showwarning(
                "Fluxo inválido",
                f"'{fluxo}' não parece um nome de pasta de fluxo (ex.: Fluxo 4 [2,0], Perfiladeira L2 [1,55], "
                "Perfiladeira U e C [2,0]).", parent=self.root)
            return False
        marcar_ajuste_manual(d.get("identificador"), d.get("pos"), fluxo, motivo)
        try:
            atualizar_entrada_log_roteirizacao(d.get("pasta_base"), d.get("arquivo"), fluxo)
        except Exception:                                              # noqa: BLE001
            pass
        self._vregra_remover_linha(chave)
        if not silencioso:
            self.lbl_vregra_status.config(
                text=f"✅ Ajuste salvo para a posição {d.get('pos')} (identificador {d.get('identificador')}) -> {fluxo}. "
                     "Já vale para qualquer obra futura.", fg=_COR_OK)
        log(f"🧠 Verificador (somente leitura): ajuste manual salvo -> identificador '{d.get('identificador')}' / "
            f"posição '{d.get('pos')}' -> '{fluxo}' (motivo: {motivo})")
        return True

    def _vregra_salvar_todos(self):
        chaves = [c for c, i in self._vregra_linhas.items() if i["var_motivo"].get().strip() and i["var_fluxo"].get().strip()]
        if not chaves:
            messagebox.showinfo("Nenhum motivo preenchido", "Preencha o motivo de ao menos uma linha antes de salvar.", parent=self.root)
            return
        if not messagebox.askyesno(
                "Confirmar",
                f"Gravar o fluxo manual de {len(chaves)} posição(ões) na memória?\n\nIsso vale para QUALQUER obra futura "
                "com a mesma posição/identificador.", parent=self.root):
            return
        ok = sum(1 for c in chaves if self._vregra_salvar_linha(c, silencioso=True))
        self.lbl_vregra_status.config(text=f"✅ {ok} ajuste(s) salvo(s). Já valem para qualquer obra futura.", fg=_COR_OK)

    def _verificador_garantir_monitoramento(self):
        if not getattr(self, "_verificador_monitorando", False):
            self._verificador_monitorando = True
            self.root.after(6000, self._verificador_ciclo_atualizacao)

    def _verificador_ciclo_atualizacao(self):
        if self.tree_verificador_pastas.get_children():
            self._verificador_atualizar_comparacoes(mostrar_log=False, periodico=True)
            self.root.after(6000, self._verificador_ciclo_atualizacao)
        else:
            self._verificador_monitorando = False

    def _verificador_atualizar_comparacoes(self, mostrar_log=True, periodico=False):
        """Compara cada pasta com o retrato. A leitura das pastas (pode ser em rede, com milhares de DXF) roda
        numa THREAD — antes rodava na tela e travava o programa a cada 4 s."""
        pastas = [
            self.tree_verificador_pastas.set(iid, "caminho")
            for iid in self.tree_verificador_pastas.get_children()
        ]
        if not pastas:
            for chave in list(self._verificador_linhas_widgets.keys()):
                self._verificador_remover_linha_resultado(chave)
            self.lbl_verificador_status.config(text="")
            self.lbl_verificador_status2.config(text="")
            return
        t_ant = getattr(self, "_verificador_thread", None)
        if t_ant is not None and t_ant.is_alive():
            if not periodico:
                self._verificador_repetir = True                 # pedido manual durante uma leitura: refaz logo depois
            return
        if not periodico:
            self.lbl_verificador_status2.config(text="🔎 Verificando as pastas…", fg=_COR_AVISO)
        resultado = {}

        def trabalho():
            for p in pastas:
                try:
                    resultado[p] = comparar_roteirizacoes_da_pasta(p)
                except Exception as ex:                          # noqa: BLE001
                    resultado[p] = ex
        t = threading.Thread(target=trabalho, daemon=True)
        self._verificador_thread = t
        t.start()
        self.root.after(120, lambda: self._verificador_esperar(t, pastas, resultado, mostrar_log))

    def _verificador_esperar(self, t, pastas, resultado, mostrar_log):
        try:
            if t.is_alive():
                self.root.after(120, lambda: self._verificador_esperar(t, pastas, resultado, mostrar_log))
                return
        except tk.TclError:
            return
        self._verificador_thread = None
        try:
            atuais = {os.path.abspath(self.tree_verificador_pastas.set(i, "caminho"))
                      for i in self.tree_verificador_pastas.get_children()}
            pastas = [p for p in pastas if os.path.abspath(p) in atuais]    # removida enquanto lia
            self._verificador_aplicar(pastas, resultado, mostrar_log)
        except tk.TclError:
            return
        except Exception as ex:                                  # noqa: BLE001
            log(f"⚠️  Verificador: erro ao atualizar a tela: {ex}")
        if getattr(self, "_verificador_repetir", False):
            self._verificador_repetir = False
            self._verificador_atualizar_comparacoes(mostrar_log=False)

    def _verificador_aplicar(self, pastas, resultado, mostrar_log):
        chaves_divergencias_atuais = set()
        total_nao_encontrados = 0
        pastas_sem_log, pastas_erro, linhas_ok = [], [], []
        for pasta in pastas:
            lista = resultado.get(pasta)
            nome_pasta = os.path.basename(os.path.normpath(pasta)) or pasta
            if isinstance(lista, Exception):
                pastas_erro.append(f"{nome_pasta} ({lista})")
                continue
            if not lista:
                pastas_sem_log.append(pasta)
                continue
            for res in lista:
                pasta_log = res.get("pasta_log") or pasta
                nome_log = os.path.basename(os.path.normpath(pasta_log)) or pasta_log
                total_nao_encontrados += len(res["nao_encontrados"])
                linhas_ok.append(f"✅ {nome_log}: retrato de {res.get('gerado_em', '?')} · "
                                 f"{res.get('total', 0)} peça(s) conferidas · {len(res['divergencias'])} alterada(s) à mão")
                for item in res["divergencias"]:
                    chave = (pasta, os.path.join(pasta_log, str(item.get("arquivo"))))
                    chaves_divergencias_atuais.add(chave)
                    info_existente = self._verificador_linhas_widgets.get(chave)
                    if info_existente:
                        info_existente["lbl_atual"].config(text=item.get("fluxo_atual", ""))
                        info_existente["dados"]["fluxo_atual"] = item.get("fluxo_atual")
                    else:
                        self._verificador_criar_linha_resultado(chave, item)
                        if mostrar_log:
                            log(f"🔍 Verificador: nova alteração manual detectada -> {item.get('arquivo','')} "
                                f"('{item.get('pasta_no_snapshot','')}' -> '{item.get('fluxo_atual','')}')")
        pastas_atuais_abs = {os.path.abspath(p) for p in pastas}
        for chave in list(self._verificador_linhas_widgets.keys()):
            if os.path.abspath(chave[0]) not in pastas_atuais_abs:
                continue
            if chave not in chaves_divergencias_atuais:
                self._verificador_remover_linha_resultado(chave)
        mensagens_status = list(linhas_ok[:6])
        if len(linhas_ok) > 6:
            mensagens_status.append(f"… e mais {len(linhas_ok) - 6} obra(s) conferida(s).")
        if pastas_sem_log:
            nomes = ", ".join(os.path.basename(os.path.normpath(p)) or p for p in pastas_sem_log)
            mensagens_status.append(
                f"ℹ️ Sem retrato do roteirizador: {nomes}. Isso NÃO impede a conferência: use \"Conferir pelas regras "
                "(somente leitura)\" aqui embaixo (com a planilha da obra) para ver o que está fora da regra. O "
                "acompanhamento automático de peças movidas à mão só existe depois que o Roteirizador rodar nessa pasta.")
        if pastas_erro:
            mensagens_status.append("❌ Não consegui ler: " + "; ".join(pastas_erro))
        self.lbl_verificador_status.config(
            text="\n".join(mensagens_status),
            fg=(_COR_AVISO if (pastas_sem_log or pastas_erro) else _COR_OK))
        total_divergencias = len(self._verificador_linhas_widgets)
        self.lbl_verificador_vazio.grid_remove() if total_divergencias else self.lbl_verificador_vazio.grid()
        texto_resultado = f"🔎 {total_divergencias} posição(ões) com fluxo alterado manualmente."
        if total_nao_encontrados:
            texto_resultado += f" ({total_nao_encontrados} arquivo(s) do log não encontrado(s) mais na pasta.)"
        if linhas_ok:
            texto_resultado += " Verificando continuamente..."
        self.lbl_verificador_status2.config(text=texto_resultado, fg=_COR_OK)
        # pasta recém-adicionada SEM retrato: explica na hora (a mensagem pequena no rodapé passava despercebida)
        novas = getattr(self, "_verificador_novas", set())
        avisar = [p for p in pastas_sem_log if os.path.abspath(p) in novas]
        self._verificador_novas = set()
        if avisar:
            messagebox.showinfo(
                "Pasta sem retrato da roteirização",
                "Essa pasta não tem o \"retrato\" que o Roteirizador grava quando organiza uma obra, então o "
                "acompanhamento automático de peças movidas à mão não funciona nela.\n\n"
                "Mas você pode só LER e conferir: em \"Conferir pelas regras (somente leitura)\", escolha a planilha da "
                "obra e clique em \"Conferir pastas da lista\". O programa mostra o que está fora da regra, sem mover "
                "nada, e você ajusta o fluxo de cada posição na própria linha.",
                parent=self.root)

    def _verificador_criar_linha_resultado(self, chave, div):
        pai_linhas = self.frame_verificador_linhas
        row_idx = self._verificador_proximo_row
        self._verificador_proximo_row += 1
        widgets_criados = []
        def _lbl(texto, col):
            widget = tk.Label(pai_linhas, text=texto, bg=_COR_PAINEL_2, fg=_COR_TEXTO,
                               font=("Segoe UI", 9), anchor="w", justify="left")
            widget.grid(row=row_idx, column=col, sticky="nsew", padx=(4, 4), pady=4)
            widgets_criados.append(widget)
            return widget
        _lbl(div.get("of", ""), 0)
        _lbl(div.get("pos", ""), 1)
        _lbl(div.get("identificador", ""), 2)
        _lbl(div.get("arquivo", ""), 3)
        _lbl(div.get("pasta_no_snapshot", ""), 4)
        lbl_atual = _lbl(div.get("fluxo_atual", ""), 5)
        var_motivo = tk.StringVar()
        entry_motivo = ttk.Entry(pai_linhas, textvariable=var_motivo, style="TEntry", font=("Segoe UI", 9))
        entry_motivo.grid(row=row_idx, column=6, sticky="nsew", padx=(4, 4), pady=4, ipady=3)
        widgets_criados.append(entry_motivo)
        btn_salvar = ttk.Button(pai_linhas, text="Salvar", style="Secundario.TButton", state="disabled",
                                 command=lambda: self._verificador_salvar_linha(chave))
        btn_salvar.grid(row=row_idx, column=7, sticky="nsew", padx=(4, 4), pady=4)
        widgets_criados.append(btn_salvar)
        def _ao_digitar(*_args):
            btn_salvar.config(state=("normal" if var_motivo.get().strip() else "disabled"))
        var_motivo.trace_add("write", _ao_digitar)
        entry_motivo.bind("<Return>", lambda e: self._verificador_salvar_linha(chave))
        self._verificador_linhas_widgets[chave] = {
            "var_motivo": var_motivo,
            "lbl_atual": lbl_atual,
            "dados": dict(div),
            "widgets": widgets_criados,
        }
        self.lbl_verificador_vazio.grid_remove()
    def _verificador_remover_linha_resultado(self, chave):
        info = self._verificador_linhas_widgets.pop(chave, None)
        if not info:
            return
        for widget in info["widgets"]:
            widget.destroy()
        if not self._verificador_linhas_widgets:
            self.lbl_verificador_vazio.grid()
    def _verificador_salvar_linha(self, chave):
        info = self._verificador_linhas_widgets.get(chave)
        if not info:
            return
        motivo = info["var_motivo"].get().strip()
        if not motivo:
            return
        dados = info["dados"]
        fluxo_atual = info["lbl_atual"].cget("text") or dados.get("fluxo_atual")
        marcar_ajuste_manual(dados.get("identificador"), dados.get("pos"), fluxo_atual, motivo)
        atualizar_entrada_log_roteirizacao(dados.get("pasta_base"), dados.get("arquivo"), fluxo_atual)
        self._verificador_remover_linha_resultado(chave)
        self.lbl_verificador_status2.config(
            text=f"✅ Ajuste salvo para a posição {dados.get('pos')} (identificador {dados.get('identificador')}). "
                 "Já vale para qualquer obra futura.",
            fg=_COR_OK,
        )
        log(f"🧠 Verificador: ajuste manual salvo -> identificador '{dados.get('identificador')}' / "
            f"posição '{dados.get('pos')}' -> '{fluxo_atual}' (motivo: {motivo})")
    def _verificador_salvar_todos_preenchidos(self):
        chaves_preenchidas = [
            chave for chave, info in self._verificador_linhas_widgets.items()
            if info["var_motivo"].get().strip()
        ]
        if not chaves_preenchidas:
            messagebox.showinfo("Nenhum motivo preenchido",
                                 "Preencha o motivo de ao menos uma linha antes de salvar.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Confirmar",
            f"Gravar o fluxo manual de {len(chaves_preenchidas)} posição(ões) na memória?\n\n"
            "Isso vale para QUALQUER obra futura: sempre que a mesma posição/identificador aparecer "
            "novamente, o roteirizador já vai direto para o fluxo escolhido aqui, sem passar pelas "
            "regras automáticas.",
            parent=self.root,
        ):
            return
        for chave in chaves_preenchidas:
            self._verificador_salvar_linha(chave)
def main(modo="roteirizador"):
    _ativar_dpi_awareness()
    ocultar_console()
    app = AplicativoRoteirizador(modo)
    app.run()
if __name__ == "__main__":
    main("ordens" if "--ordens" in sys.argv else "roteirizador")