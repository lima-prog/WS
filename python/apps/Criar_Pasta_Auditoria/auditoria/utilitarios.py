# -*- coding: utf-8 -*-
"""
Funções puras da aba Criar Pasta / Auditoria: nada aqui abre janela nem
mexe no banco de dados — só lê planilha (.xlsx) e o sistema de arquivos,
e devolve dados prontos pro `processador.py` orquestrar.

Extraído de `cria_pasta_auditoria.py` (customtkinter), mesma lógica linha
por linha — só sem nenhuma dependência de UI.
"""
import os
import re

from openpyxl import load_workbook

# Nome da pasta "buffer" onde obras ficam temporariamente até o lote
# oficial delas ser criado.
NOME_PASTA_9999 = "LOTE 9999"

# Quantos dígitos do código da OF são considerados significativos.
# Ex: "1923-12-27__" e "1923-12-27Ø" → mesmo código "192312279" (qualquer
# coisa que não seja dígito é descartada, e só os primeiros CODE_DIGITS
# dígitos contam) — isso permite casar pastas com sujeira no nome (espaço,
# caractere estranho, sufixo) com a OF certa da planilha.
CODE_DIGITS = 9

# Texto mostrado no lugar de um peso/status vazio nas tabelas de busca
# (FASE 2) — mesmo caractere do script original.
PLACEHOLDER_SEM_PESO = "—"


def normalizar_codigo(texto: str) -> str:
    """
    Extrai só os dígitos do texto e mantém os primeiros CODE_DIGITS.
    Isso permite casar "1923-12-27__" / "1923-12-27Ø" com "1923-12-27",
    e também códigos maiores como "1923-101-01" (9 dígitos).
    """
    digitos = re.sub(r"\D", "", str(texto))
    return digitos[:CODE_DIGITS]


def mapear_pastas_por_codigo(diretorio: str) -> dict:
    """
    Lista as subpastas de `diretorio` e monta um dicionário
    {codigo_normalizado: caminho_completo}. Em caso de duas pastas
    com o mesmo código normalizado, mantém a primeira encontrada.
    """
    mapa = {}
    if not diretorio or not os.path.isdir(diretorio):
        return mapa
    for nome in os.listdir(diretorio):
        caminho = os.path.join(diretorio, nome)
        if not os.path.isdir(caminho):
            continue
        codigo = normalizar_codigo(nome)
        if codigo and codigo not in mapa:
            mapa[codigo] = caminho
    return mapa


def mapear_pastas_por_codigo_multi(diretorio: str) -> dict:
    """
    Igual a `mapear_pastas_por_codigo()`, mas guarda TODAS as pastas que
    compartilham o mesmo código normalizado dentro de `diretorio`, não só a
    primeira. Necessária pra auditoria conseguir detectar duplicidade
    física (duas pastas com o mesmo código — ex.: "2141-3-01" e uma cópia
    suja com sufixo) — a versão de valor único descarta a segunda pasta
    silenciosamente, o que escondia esse tipo de problema.
    """
    mapa = {}
    if not diretorio or not os.path.isdir(diretorio):
        return mapa
    for nome in os.listdir(diretorio):
        caminho = os.path.join(diretorio, nome)
        if not os.path.isdir(caminho):
            continue
        codigo = normalizar_codigo(nome)
        if codigo:
            mapa.setdefault(codigo, []).append(caminho)
    return mapa


def encontrar_arquivo_xlsx(caminho: str):
    """Aceita tanto o caminho direto do .xlsx quanto uma pasta que contém um."""
    if os.path.isfile(caminho) and caminho.endswith(".xlsx"):
        return caminho
    if os.path.isdir(caminho):
        for arquivo in os.listdir(caminho):
            if arquivo.endswith(".xlsx"):
                return os.path.join(caminho, arquivo)
    return None


def ler_ofs_da_planilha(caminho_xlsx: str, lote_filtro: str) -> list:
    """
    Lê a planilha (dados a partir da linha 5, cabeçalho na linha 4) e
    retorna a lista de OF/Trecho (coluna B) cujo LOTE (coluna A) bate
    com lote_filtro.
    """
    wb = load_workbook(caminho_xlsx, data_only=True)
    sheet = wb.active
    ofs = []
    for linha in range(5, sheet.max_row + 1):
        cel_lote = sheet[f"A{linha}"].value
        cel_of_trecho = sheet[f"B{linha}"].value
        if cel_lote is None and cel_of_trecho is None:
            continue
        if str(cel_lote).strip() != str(lote_filtro).strip():
            continue
        if not cel_of_trecho:
            continue
        ofs.append(str(cel_of_trecho).strip())
    return ofs


def ler_todas_as_linhas_planilha(caminho_xlsx: str) -> list:
    """
    Lê TODAS as linhas da planilha (a partir da linha 5), sem filtrar por
    lote, e retorna uma lista de tuplas (lote, of_trecho). Usada quando é
    preciso descobrir a que lote uma OF pertence de verdade — por exemplo,
    pra dizer a que lote uma pasta "órfã" da 9999 pertence na planilha.
    """
    wb = load_workbook(caminho_xlsx, data_only=True)
    sheet = wb.active
    linhas = []
    for linha in range(5, sheet.max_row + 1):
        cel_lote = sheet[f"A{linha}"].value
        cel_of_trecho = sheet[f"B{linha}"].value
        if cel_lote is None or not cel_of_trecho:
            continue
        linhas.append((str(cel_lote).strip(), str(cel_of_trecho).strip()))
    return linhas


def obter_mtime(caminho: str) -> str:
    """Data de modificação do arquivo (usado pra detectar mudanças na planilha)."""
    return str(os.path.getmtime(caminho))


def parse_of_trecho(of_trecho: str):
    """
    Quebra o código OF-TRECHO em (obra, trecho, subtrecho).
    Exemplo: "1956-5-21" -> ("1956", "5", "21")
    """
    partes = str(of_trecho).strip().split("-")
    obra = partes[0].strip() if len(partes) >= 1 else str(of_trecho).strip()
    trecho = partes[1].strip() if len(partes) >= 2 else ""
    subtrecho = partes[2].strip() if len(partes) >= 3 else ""
    return obra, trecho, subtrecho


def parse_numero_br(valor):
    """
    Converte valores numéricos vindos da planilha (float ou string BR
    '1.234,56'). Retorna None se a célula estiver vazia (pra diferenciar
    de peso == 0).
    """
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return None
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def formatar_kg(valor) -> str:
    """Formata número no padrão brasileiro (1.234,567); traço se None."""
    if valor is None:
        return PLACEHOLDER_SEM_PESO
    return f"{valor:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")


def chave_ordenacao(codigo):
    """Ordena numericamente quando possível, senão alfabeticamente."""
    try:
        return (0, int(codigo))
    except (ValueError, TypeError):
        return (1, str(codigo))


def ler_linhas_busca_planilha(caminho_xlsx: str) -> list:
    """
    Lê a planilha INTEIRA (dados a partir da linha 5) pras telas Buscar por
    Obra / Buscar por Pacote (FASE 2) — colunas:
        A=LOTE  B=OF-TRECHO  C=ANO-SEMANA  D=PESO LIC/LOTE
        E=QTD TT KG PREP  F=QTD TT KG ÑPREP  G=DATA INICIO ARTIA  H=STATUS
    Retorna uma lista de dicts prontos pra `auditoria.banco.substituir_registros`.
    """
    wb = load_workbook(caminho_xlsx, data_only=True)
    sheet = wb.active
    linhas = []
    for linha in range(5, sheet.max_row + 1):
        lote = sheet[f"A{linha}"].value
        of_trecho = sheet[f"B{linha}"].value
        if not lote or not of_trecho:
            continue
        of_trecho_str = str(of_trecho).strip()
        obra, trecho, subtrecho = parse_of_trecho(of_trecho_str)
        ano_semana = sheet[f"C{linha}"].value
        peso_lic = sheet[f"D{linha}"].value
        qtd_prep = parse_numero_br(sheet[f"E{linha}"].value)
        qtd_nprep = parse_numero_br(sheet[f"F{linha}"].value)
        data_inicio = sheet[f"G{linha}"].value
        status = sheet[f"H{linha}"].value
        linhas.append({
            "lote": str(lote).strip(),
            "of_trecho": of_trecho_str,
            "obra": obra, "trecho": trecho, "subtrecho": subtrecho,
            "ano_semana": str(ano_semana).strip() if ano_semana is not None else "",
            "peso_lic_lote": str(peso_lic).strip() if peso_lic is not None else "",
            "qtd_tt_kg_prep": qtd_prep, "qtd_tt_kg_nprep": qtd_nprep,
            "data_inicio_artia": str(data_inicio).strip() if data_inicio is not None else "",
            "status": str(status).strip() if status is not None else "",
        })
    return linhas


def obter_pasta_9999(raiz: str) -> str:
    return os.path.join(raiz, NOME_PASTA_9999)


def listar_pastas_mes(raiz: str) -> list:
    """Todas as subpastas da raiz, exceto a própria LOTE 9999."""
    pastas = []
    if not raiz or not os.path.isdir(raiz):
        return pastas
    for nome in os.listdir(raiz):
        caminho = os.path.join(raiz, nome)
        if os.path.isdir(caminho) and nome.strip().upper() != NOME_PASTA_9999.upper():
            pastas.append(caminho)
    return pastas


def indexar_estrutura(raiz: str, ignorar: str = None):
    """
    Percorre TODAS as pastas de mês da raiz (exceto `ignorar`), entra em
    cada subpasta que começa com "LOTE" e monta um índice único:
    codigo_normalizado -> (caminho_lote, caminho_mes, caminho_of_real).
    Também retorna quantos LOTEs foram escaneados e quais pastas deram
    erro de leitura (permissão, rede, etc.) — pra deixar claro se a
    varredura foi completa.
    """
    indice = {}
    total_lotes = 0
    pastas_com_erro = []
    for pasta_mes in listar_pastas_mes(raiz):
        if ignorar and os.path.normcase(pasta_mes) == os.path.normcase(ignorar):
            continue
        try:
            subitens = os.listdir(pasta_mes)
        except OSError as e:
            pastas_com_erro.append(f"{pasta_mes}  ({e})")
            continue
        for sub in subitens:
            caminho_lote = os.path.join(pasta_mes, sub)
            if not os.path.isdir(caminho_lote):
                continue
            if not sub.strip().upper().startswith("LOTE"):
                continue
            total_lotes += 1
            try:
                mapa_lote = mapear_pastas_por_codigo(caminho_lote)
            except OSError as e:
                pastas_com_erro.append(f"{caminho_lote}  ({e})")
                continue
            for codigo, caminho_of in mapa_lote.items():
                if codigo not in indice:
                    indice[codigo] = (caminho_lote, pasta_mes, caminho_of)
    return indice, total_lotes, pastas_com_erro


def indexar_estrutura_multi(raiz: str, ignorar: str = None):
    """
    Igual a `indexar_estrutura()`, mas guarda TODAS as pastas que
    compartilham o mesmo código normalizado em toda a raiz, não só a
    primeira encontrada durante a varredura — necessária pra auditoria
    conseguir enxergar quando a mesma OF tem pasta física em mais de um
    LOTE ao mesmo tempo (a versão de valor único mantinha só a primeira
    ocorrência e descartava as outras em silêncio, escondendo duplicidade
    real entre lotes diferentes).
    """
    indice = {}
    total_lotes = 0
    pastas_com_erro = []
    for pasta_mes in listar_pastas_mes(raiz):
        if ignorar and os.path.normcase(pasta_mes) == os.path.normcase(ignorar):
            continue
        try:
            subitens = os.listdir(pasta_mes)
        except OSError as e:
            pastas_com_erro.append(f"{pasta_mes}  ({e})")
            continue
        for sub in subitens:
            caminho_lote = os.path.join(pasta_mes, sub)
            if not os.path.isdir(caminho_lote):
                continue
            if not sub.strip().upper().startswith("LOTE"):
                continue
            total_lotes += 1
            try:
                mapa_lote = mapear_pastas_por_codigo_multi(caminho_lote)
            except OSError as e:
                pastas_com_erro.append(f"{caminho_lote}  ({e})")
                continue
            for codigo, caminhos in mapa_lote.items():
                for caminho_of in caminhos:
                    indice.setdefault(codigo, []).append((caminho_lote, pasta_mes, caminho_of))
    return indice, total_lotes, pastas_com_erro


def localizar_pasta_lote_existente(raizes: list, lote: str):
    """
    Procura, em todas as pastas de mês de todas as raízes cadastradas, uma
    pasta "LOTE {lote}" já existente (ignorando maiúsc./minúsc. e espaços
    nas pontas — mesmo padrão de nome usado em `processar()`).
    Retorna o primeiro caminho encontrado, ou None se ainda não existir em
    lugar nenhum (nesse caso, quem chamar decide se cria uma nova).
    """
    alvo = f"LOTE {str(lote).strip()}".strip().upper()
    for raiz in raizes or []:
        if not raiz or not os.path.isdir(raiz):
            continue
        for pasta_mes in listar_pastas_mes(raiz):
            try:
                subitens = os.listdir(pasta_mes)
            except OSError:
                continue
            for sub in subitens:
                if sub.strip().upper() == alvo:
                    caminho = os.path.join(pasta_mes, sub)
                    if os.path.isdir(caminho):
                        return caminho
    return None
