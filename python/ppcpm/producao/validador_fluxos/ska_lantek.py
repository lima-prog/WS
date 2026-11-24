# -*- coding: utf-8 -*-
"""
Atualiza a planilha FIXA  LANTEK_SKA-REPORT_REL-ANALISE-NESTINGS_rev.02_260129.xlsb  a partir do relatório
"ANALISE DE NESTINGS" exportado do SKA Reports (CSV).

Por que existe: as BASES (BASE_PPCPM…) procuram na aba `LANTEK_REL-ANALISE-NESTING` dessa planilha a máquina em que cada
posição foi programada no Lantek (colunas "OF OF-TRECHO_POSIÇÃO (LANTEK)" e "MÁQUINA_LANTEK" da aba DBF). Antes era
preciso colar o relatório à mão. Agora o Agrupador/Base faz isso sozinho ao gerar a base.

Como atualiza (igual ao processo manual, só que automático), tudo pelo EXCEL (COM) para não quebrar fórmulas/tabelas dinâmicas:
  1. o Excel abre o relatório SKA (CSV com ";" ou ",", vírgula decimal — do jeito do Brasil) e a planilha LANTEK_SKA;
  2. as colunas A:AI (o relatório cru) são substituídas — casando pelo NOME do cabeçalho, não pela posição;
  3. as colunas de fórmula (AJ em diante) são arrastadas a partir da 1ª linha de dados (a "linha-molde"), como se faz à mão;
  4. a data de exportação (A4) vira a de hoje (se for valor fixo), as tabelas dinâmicas são recalculadas e o arquivo é salvo
     num temporário LOCAL e SÓ DEPOIS substitui o original (se algo der errado o original continua intacto);
  5. antes disso é feita uma cópia em "00. Back up" (no máximo uma por dia).
O nome do arquivo NÃO muda: todas as bases apontam para ele pelo nome — por isso todas passam a enxergar os dados novos
(abrindo a base e aceitando "Atualizar vínculos"; a base que o Agrupador acabou de gerar já sai atualizada).

Roda em segundo plano (QThread) — a tela não trava. Precisa de Windows + Excel + pywin32.
"""
import csv
import glob
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unicodedata
from collections import Counter
from datetime import date, datetime

# ── destino FIXO ─────────────────────────────────────────────────────────────────────────────────
PASTA_SKA = (r"G:\.shortcut-targets-by-id\1QJ57NfcTjhvbinkho-hL7zV2UPrjgZ4d\PCP-REDE\PPCPM"
             r"\08. Base Dados Relatórios\03. LANTEK_SKA-REPORT_REL-ANALISE-NESTINGS")
ARQUIVO_SKA = "LANTEK_SKA-REPORT_REL-ANALISE-NESTINGS_rev.02_260129.xlsb"
PASTA_BACKUP = "00. Back up"
ABA_NESTING = "LANTEK_REL-ANALISE-NESTING"

LINHA_CABECALHO = 7        # nomes das colunas na planilha LANTEK_SKA
LINHA_MOLDE = 8            # 1ª linha de dados = linha-molde das fórmulas
COL_CRUA_FIM = 35          # AI: fim da área do relatório cru (A:AI)
COL_FORMULA_INI = 36       # AJ: início das colunas de fórmula
CELULA_DT_EXPORT = "A4"
LIMITE_MINUTOS = float(os.environ.get("PPCP_SKA_LIMITE_MIN", "20"))   # passou disso: encerra o Excel e avisa (nunca fica travado)

# colunas sem as quais NÃO se atualiza (o relatório não é o de análise de nestings, ou veio incompleto)
CABECALHOS_OBRIGATORIOS = ["ID NESTING", "MAQUINA", "REFERENCIA", "DATA PROG NESTING"]

XL_UP, XL_TO_LEFT = -4162, -4159
XL_CALC_AUTO, XL_CALC_MANUAL = -4105, -4135
XL_PASTE_FORMATS = -4122
XL_EXCEL12 = 50            # .xlsb


def _norm(v):
    s = unicodedata.normalize("NFKD", str(v if v is not None else "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().upper()


# Cópia da planilha que vem DENTRO do sistema (ppcpm/producao/lantek_ska). Ela é só o MODELO: o arquivo que é atualizado
# fica em dados_locais/producao/lantek_ska (a atualização do sistema nunca mexe nos dados_locais, então os dados
# colados do SKA não voltam atrás). Só é usada quando a pasta fixa do Google Drive (PASTA_SKA) não existe neste PC.
_AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_SKA_MODELO = os.path.join(os.path.dirname(_AQUI), "lantek_ska")
PASTA_SKA_LOCAL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_AQUI))), "dados_locais", "producao",
                               "lantek_ska")


def caminho_destino(pasta=None, arquivo=None):
    arquivo = arquivo or ARQUIVO_SKA
    if pasta or os.environ.get("PPCP_SKA_PASTA"):
        return os.path.join(pasta or os.environ.get("PPCP_SKA_PASTA"), arquivo)
    drive = os.path.join(PASTA_SKA, arquivo)
    if os.path.isfile(drive) or os.path.isdir(PASTA_SKA):          # 1) a planilha do Drive (a que as bases usam)
        return drive
    local = os.path.join(PASTA_SKA_LOCAL, arquivo)                 # 2) a do próprio sistema
    modelo = os.path.join(PASTA_SKA_MODELO, arquivo)
    if not os.path.isfile(local) and os.path.isfile(modelo):
        try:
            os.makedirs(PASTA_SKA_LOCAL, exist_ok=True)
            shutil.copy2(modelo, local)
        except OSError:
            return modelo if os.path.isfile(modelo) else drive
    return local if os.path.isfile(local) else drive


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 1) Leitura do relatório SKA em Python (conferência rápida — quem converte os valores é o Excel)
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def _ler_texto(caminho):
    bruto = open(caminho, "rb").read()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return bruto.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return bruto.decode("latin-1"), "latin-1"


def _delimitador(texto):
    amostra = "\n".join(texto.splitlines()[:30])
    cont = {d: amostra.count(d) for d in (";", "\t", ",")}
    return max(cont, key=cont.get) if max(cont.values()) else ";"


def _linhas_do_arquivo(caminho):
    """Linhas do relatório (lista de listas de texto/valores) + detalhes do formato."""
    ext = os.path.splitext(caminho)[1].lower()
    if ext in (".csv", ".txt", ".tsv"):
        texto, enc = _ler_texto(caminho)
        delim = _delimitador(texto)
        return list(csv.reader(io.StringIO(texto), delimiter=delim)), {"delim": delim, "enc": enc, "tipo": "csv"}
    if ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        try:
            ws = wb[wb.sheetnames[0]]
            return [list(r) for r in ws.iter_rows(values_only=True)], {"tipo": "excel"}
        finally:
            wb.close()
    if ext == ".xlsb":
        from pyxlsb import open_workbook
        with open_workbook(caminho) as wb:
            with wb.get_sheet(wb.sheets[0]) as sh:
                return [[c.v for c in r] for r in sh.rows()], {"tipo": "excel"}
    if ext == ".xls":
        import pandas as pd
        df = pd.read_excel(caminho, header=None, sheet_name=0)
        return df.where(df.notna(), None).values.tolist(), {"tipo": "excel"}
    raise RuntimeError(f"formato não suportado para o relatório SKA: {ext or 'sem extensão'}")


def achar_cabecalho(linhas, limite=20):
    """(índice da linha do cabeçalho, {nome normalizado: coluna 0-based}) ou (None, {})."""
    for i, r in enumerate(linhas[:limite]):
        nomes = {}
        for j, v in enumerate(r or []):
            n = _norm(v)
            if n and n not in nomes:
                nomes[n] = j
        if "ID NESTING" in nomes:
            return i, nomes
    return None, {}


def ler_relatorio_ska(caminho):
    """Confere o relatório SKA e devolve um resumo (não altera nada).
    {'linhas': n, 'cabecalho_linha': i, 'faltando': [...], 'maquinas': Counter, 'obras': set, 'formato': {...}}.
    Levanta RuntimeError com mensagem clara se não for o relatório certo."""
    linhas, formato = _linhas_do_arquivo(caminho)
    hi, nomes = achar_cabecalho(linhas)
    if hi is None:
        raise RuntimeError('não achei o cabeçalho "ID NESTING" — este não parece ser o relatório '
                           '"ANÁLISE DE NESTINGS" do SKA Reports (exportado em CSV).')
    faltando = [c for c in CABECALHOS_OBRIGATORIOS if c not in nomes]
    if faltando:
        raise RuntimeError("faltam colunas no relatório SKA: " + ", ".join(faltando))
    i_id, i_maq, i_ref = nomes["ID NESTING"], nomes["MAQUINA"], nomes["REFERENCIA"]
    maquinas, obras, n = Counter(), set(), 0
    for r in linhas[hi + 1:]:
        if not r or i_id >= len(r) or str(r[i_id] or "").strip() == "":
            continue
        n += 1
        maquinas[str(r[i_maq] if i_maq < len(r) else "").strip() or "(vazio)"] += 1
        m = re.search(r"OF\s*(\d+-\d+-\d+)", str(r[i_ref]) if i_ref < len(r) else "", re.IGNORECASE)
        if m:
            obras.add(m.group(1))
    if n == 0:
        raise RuntimeError("o relatório SKA não tem nenhuma linha de nesting")
    return {"linhas": n, "cabecalho_linha": hi, "faltando": [], "maquinas": maquinas, "obras": obras, "formato": formato}


def resumo_texto(r):
    maq = ", ".join(f"{k} {v}" for k, v in r["maquinas"].most_common(4))
    return f"{r['linhas']} linha(s) de nesting · {len(r['obras'])} obra-trecho(s) · {maq}"


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 1b) "Já está atualizada?" — evita repetir o trabalho pesado quando o mesmo relatório já foi aplicado
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def _arquivo_estado():
    try:
        from nucleo.caminhos import RAIZ_DADOS
        pasta = RAIZ_DADOS
    except Exception:
        pasta = tempfile.gettempdir()
    return os.path.join(pasta, "ska_ultima_atualizacao.json")


def _assinatura_arquivo(caminho):
    h = hashlib.sha1()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _estado_destino(destino):
    st = os.stat(destino)
    return {"tamanho": st.st_size, "mtime": round(st.st_mtime, 1)}


def ja_atualizada(caminho_relatorio, destino, arquivo_estado=None):
    """Dict do último registro se ESTE relatório (mesmo conteúdo) já foi aplicado e a planilha não mudou desde então."""
    try:
        with open(arquivo_estado or _arquivo_estado(), "r", encoding="utf-8") as f:
            reg = json.load(f)
        if reg.get("destino") != destino or reg.get("relatorio_sha1") != _assinatura_arquivo(caminho_relatorio):
            return None
        atual = _estado_destino(destino)
        if abs(reg.get("mtime", 0) - atual["mtime"]) > 1.5 or reg.get("tamanho") != atual["tamanho"]:
            return None                                    # alguém mexeu na planilha depois: atualiza de novo
        return reg
    except Exception:
        return None


def _registrar_atualizacao(caminho_relatorio, destino, linhas, arquivo_estado=None):
    try:
        reg = {"destino": destino, "relatorio_sha1": _assinatura_arquivo(caminho_relatorio),
               "relatorio_nome": os.path.basename(caminho_relatorio), "linhas": linhas,
               "quando": datetime.now().strftime("%d/%m/%Y %H:%M"), **_estado_destino(destino)}
        with open(arquivo_estado or _arquivo_estado(), "w", encoding="utf-8") as f:
            json.dump(reg, f, ensure_ascii=False)
    except Exception:
        pass


def _encerrar_excel(excel):
    """Mata o processo do Excel que ESTE programa abriu (só ele)."""
    try:
        import win32process
        pid = win32process.GetWindowThreadProcessId(excel.Hwnd)[1]
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=30)
    except Exception:
        try:
            excel.Quit()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2) Backup
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def fazer_backup(destino, agora=None):
    """Copia o arquivo para '00. Back up' (no máximo uma cópia por dia). Devolve o caminho (ou None se já havia do dia)."""
    agora = agora or datetime.now()
    pasta_bkp = os.path.join(os.path.dirname(destino), PASTA_BACKUP)
    os.makedirs(pasta_bkp, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(destino))
    if glob.glob(os.path.join(pasta_bkp, f"{glob.escape(stem)}_bkp_{agora:%Y%m%d}_*{ext}")):
        return None
    alvo = os.path.join(pasta_bkp, f"{stem}_bkp_{agora:%Y%m%d_%H%M}{ext}")
    shutil.copy2(destino, alvo)
    return alvo


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 3) Atualização pelo Excel
# ═══════════════════════════════════════════════════════════════════════════════════════════════
def _col_letra(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _abrir_origem(excel, caminho, formato):
    """Abre o relatório no Excel (CSV lido do jeito brasileiro). Devolve o workbook."""
    if formato.get("tipo") == "csv":
        enc = formato.get("enc", "utf-8-sig")
        delim = formato.get("delim", ";")
        excel.Workbooks.OpenText(Filename=caminho, Origin=65001 if enc.startswith("utf") else 1252, StartRow=1,
                                 DataType=1, TextQualifier=1, ConsecutiveDelimiter=False,
                                 Tab=(delim == "\t"), Semicolon=(delim == ";"), Comma=(delim == ","),
                                 Space=False, Other=False, Local=True)
        return excel.ActiveWorkbook
    return excel.Workbooks.Open(caminho, 0, True)       # UpdateLinks=0, ReadOnly=True


def _mapa_cabecalho(valores):
    """Value2 de um bloco A1:..  → (linha_cabecalho 1-based, {nome normalizado: coluna 1-based}) ou (None, {})."""
    for i, linha in enumerate(valores, 1):
        nomes = {}
        for j, v in enumerate(linha, 1):
            n = _norm(v)
            if n and n not in nomes:
                nomes[n] = j
        if "ID NESTING" in nomes:
            return i, nomes
    return None, {}


def _corrigir_pivot_caches(wb, aba, ultima_linha):
    """Estica o intervalo de cada tabela dinâmica que lê a aba do Lantek até a última linha nova e atualiza."""
    ok, erro = 0, 0
    try:
        total = wb.PivotCaches().Count
    except Exception:
        return 0, 0
    for i in range(1, total + 1):
        try:
            cache = wb.PivotCaches().Item(i)
            try:
                cache.MissingItemsLimit = 0
            except Exception:
                pass
            src = str(cache.SourceData)
            novo = None
            m = re.match(r"^'?([^'!]+)'?!\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)$", src)
            if m and _norm(m.group(1)) == _norm(aba):
                novo = f"'{aba}'!${m.group(2)}${m.group(3)}:${m.group(4)}${ultima_linha}"
            else:
                m = re.match(r"^'?([^'!]+)'?!R(\d+)C(\d+):R(\d+)C(\d+)$", src)
                if m and _norm(m.group(1)) == _norm(aba):
                    novo = f"'{aba}'!R{m.group(2)}C{m.group(3)}:R{ultima_linha}C{m.group(5)}"
            if novo and novo != src:
                cache.SourceData = novo
            cache.Refresh()
            ok += 1
        except Exception:
            erro += 1
    return ok, erro


def _log_tempo(texto):
    """Anota o tempo de cada fase em %LOCALAPPDATA%\\PPCP_Ferramentas\\logs\\ska_tempos.txt (para achar o que está lento)."""
    try:
        pasta = os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "PPCP_Ferramentas", "logs")
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "ska_tempos.txt"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {texto}\n")
    except Exception:
        pass


def _coluna(v, n):
    """Value2 de uma coluna (n x 1) -> lista de n valores."""
    if not isinstance(v, tuple):
        return [v]
    return [linha[0] if isinstance(linha, tuple) else linha for linha in v][:n]


def _blocos(indices, folga=10):
    """[3,4,5,9,40] -> [(3,9),(40,40)]: junta linhas próximas em blocos (folga = buracos tolerados)."""
    blocos = []
    for i in sorted(indices):
        if blocos and i - blocos[-1][1] <= folga + 1:
            blocos[-1][1] = i
        else:
            blocos.append([i, i])
    return [tuple(b) for b in blocos]


def atualizar_planilha_ska(caminho_relatorio, destino=None, progresso=None, fazer_bkp=True, forcar=False,
                           arquivo_estado=None, limite_minutos=None):
    """Atualiza a planilha LANTEK_SKA com o relatório. Devolve um dict de resultado; levanta RuntimeError se não deu.
    `progresso(msg)` recebe a fase atual (aparece na tela enquanto roda em segundo plano)."""
    def avisa(msg):
        if progresso:
            progresso(msg)

    destino = os.path.abspath(destino or caminho_destino())
    caminho_relatorio = os.path.abspath(caminho_relatorio)
    tempos, t0 = {}, [time.perf_counter(), None]

    parar_relogio_tela = threading.Event()

    def fase(nome):
        agora = time.perf_counter()
        if t0[1]:
            tempos[t0[1]] = round(agora - t0[0], 1)
            _log_tempo(f"{t0[1]}: {tempos[t0[1]]} s")
        t0[0], t0[1] = agora, nome
        avisa(f"Planilha LANTEK_SKA — {nome}…")

    def _tique():                       # a cada 3 s mostra há quanto tempo a fase está rodando (a tela nunca parece parada)
        while not parar_relogio_tela.wait(3):
            if t0[1]:
                seg = int(time.perf_counter() - t0[0])
                avisa(f"Planilha LANTEK_SKA — {t0[1]}… {seg // 60}:{seg % 60:02d}")
    threading.Thread(target=_tique, daemon=True).start()

    try:
        import pythoncom
        import win32com.client
    except ImportError:
        raise RuntimeError('precisa do pacote "pywin32" (pip install pywin32) e do Excel instalado neste PC '
                           "para atualizar a planilha LANTEK_SKA")

    fase("conferindo o relatório SKA")
    if not os.path.isfile(caminho_relatorio):
        raise RuntimeError(f"relatório SKA não encontrado: {caminho_relatorio}")
    resumo = ler_relatorio_ska(caminho_relatorio)
    if not os.path.isfile(destino):
        raise RuntimeError("a planilha LANTEK_SKA fixa não foi encontrada (o Google Drive está aberto neste PC?):\n" + destino)

    if not forcar:                                         # mesmo relatório já aplicado: não repete o trabalho pesado
        reg = ja_atualizada(caminho_relatorio, destino, arquivo_estado)
        if reg:
            return {"pulou": True, "linhas": reg.get("linhas", resumo["linhas"]), "quando": reg.get("quando", ""),
                    "destino": destino, "tempos": {}}

    backup = None
    if fazer_bkp:
        fase("guardando cópia em 00. Back up")
        try:
            backup = fazer_backup(destino)
        except Exception as e:
            raise RuntimeError(f"não consegui guardar a cópia de segurança, então NÃO atualizei a planilha: {e}")

    pasta_tmp = tempfile.mkdtemp(prefix="ska_lantek_")
    tmp_xlsb = os.path.join(pasta_tmp, "novo.xlsb")
    excel = wb_src = wb_dst = None
    resultado = {}
    pythoncom.CoInitialize()
    estourou = [False]
    relogio = None
    wb_branco = None
    try:
        fase("abrindo o Excel")
        excel = win32com.client.DispatchEx("Excel.Application")
        limite = (limite_minutos if limite_minutos is not None else LIMITE_MINUTOS) * 60

        def _estourou():
            estourou[0] = True
            _encerrar_excel(excel)
        relogio = threading.Timer(limite, _estourou)     # nunca fica travado: passou do limite, o Excel é encerrado
        relogio.daemon = True
        relogio.start()
        excel.Visible = False
        excel.DisplayAlerts = False
        for prop in ("AskToUpdateLinks", "AlertBeforeOverwriting", "EnableEvents"):
            try:
                setattr(excel, prop, False)
            except Exception:
                pass

        try:                                              # cálculo manual ANTES de abrir a planilha pesada (não recalcula ao abrir)
            wb_branco = excel.Workbooks.Add()
            excel.Calculation = XL_CALC_MANUAL
        except Exception:
            wb_branco = None

        fase("lendo o relatório SKA")
        wb_src = _abrir_origem(excel, caminho_relatorio, resumo["formato"])
        ws_src = wb_src.Worksheets(1)
        cab_src = ws_src.Range("A1:CZ25").Value2
        h_src, nomes_src = _mapa_cabecalho(cab_src)
        if h_src is None:
            raise RuntimeError('o Excel não achou o cabeçalho "ID NESTING" no relatório (separador/ codificação do CSV?)')
        col_id = nomes_src["ID NESTING"]
        ultima_src = ws_src.Cells(ws_src.Rows.Count, col_id).End(XL_UP).Row
        n = ultima_src - h_src
        if n <= 0:
            raise RuntimeError("o relatório SKA não tem linhas de dados")

        fase("abrindo a planilha LANTEK_SKA (é pesada, pode levar alguns minutos)")
        wb_dst = excel.Workbooks.Open(destino, 0)           # UpdateLinks=0: não perde tempo atualizando vínculos externos
        try:
            if wb_dst.ReadOnly:
                raise RuntimeError("a planilha LANTEK_SKA está aberta por outra pessoa (ou em outro Excel) — "
                                   "feche-a e tente de novo")
        except AttributeError:
            pass
        ws = wb_dst.Worksheets(ABA_NESTING)
        try:
            excel.Calculation = XL_CALC_MANUAL
        except Exception:
            pass
        excel.ScreenUpdating = False
        try:                                              # usa todos os núcleos do PC no recálculo
            excel.MultiThreadedCalculation.Enabled = True
            excel.MultiThreadedCalculation.ThreadMode = 0
        except Exception:
            pass

        # cabeçalho do destino → quais colunas vêm de onde
        cab_dst = ws.Range(ws.Cells(LINHA_CABECALHO, 1), ws.Cells(LINHA_CABECALHO, COL_CRUA_FIM)).Value2[0]
        pares, sem_origem = [], []
        for c_dst, nome in enumerate(cab_dst, 1):
            n_norm = _norm(nome)
            if not n_norm:
                continue
            if n_norm in nomes_src:
                pares.append((c_dst, nomes_src[n_norm]))
            else:
                sem_origem.append(str(nome))
        for obrig in CABECALHOS_OBRIGATORIOS:
            if obrig not in [_norm(x) for x in cab_dst] or obrig not in nomes_src:
                raise RuntimeError(f'coluna obrigatória "{obrig}" não bate entre o relatório SKA e a planilha LANTEK_SKA '
                                   "— nada foi alterado")

        ultima_antiga = ws.Cells(ws.Rows.Count, 1).End(XL_UP).Row
        ultima_formula_antiga = ws.Cells(ws.Rows.Count, COL_FORMULA_INI + 2).End(XL_UP).Row
        ult_col_formula = ws.Cells(LINHA_CABECALHO, ws.Columns.Count).End(XL_TO_LEFT).Column
        ultima_nova = LINHA_MOLDE - 1 + n

        fase(f"trocando os dados ({n} linhas)")
        antigas = max(0, ultima_antiga - LINHA_MOLDE + 1)
        novos = {c_dst: _coluna(ws_src.Range(ws_src.Cells(h_src + 1, c_src), ws_src.Cells(h_src + n, c_src)).Value2, n)
                 for c_dst, c_src in pares}
        mudadas, incremental = None, False
        if antigas > 0:                                    # só reescreve o que mudou: o Excel recalcula só essas linhas
            velho = ws.Range(ws.Cells(LINHA_MOLDE, 1), ws.Cells(ultima_antiga, COL_CRUA_FIM)).Value2
            if not isinstance(velho, tuple):
                velho = ((velho,),)
            mudadas = set(range(antigas, n))                # linhas além das antigas
            for i in range(min(n, antigas)):
                lin = velho[i]
                for c in range(1, COL_CRUA_FIM + 1):
                    nv = novos[c][i] if c in novos else None
                    if lin[c - 1] != nv:
                        mudadas.add(i)
                        break
            blocos = _blocos(mudadas)
            incremental = len(mudadas) <= 0.6 * n and len(blocos) <= 150
        if incremental:
            if n < antigas:                                 # relatório menor: limpa as linhas que sobraram
                ws.Range(ws.Cells(LINHA_MOLDE + n, 1), ws.Cells(ultima_antiga, COL_CRUA_FIM)).ClearContents()
            if ultima_nova > ultima_antiga:
                try:
                    ws.Range(ws.Cells(LINHA_MOLDE, 1), ws.Cells(LINHA_MOLDE, COL_CRUA_FIM)).Copy()
                    ws.Range(ws.Cells(ultima_antiga + 1, 1), ws.Cells(ultima_nova, COL_CRUA_FIM)).PasteSpecial(XL_PASTE_FORMATS)
                    excel.CutCopyMode = False
                except Exception:
                    pass
            for a, b in blocos:
                ws.Range(ws.Cells(LINHA_MOLDE + a, 1), ws.Cells(LINHA_MOLDE + b, COL_CRUA_FIM)).ClearContents()
                for c_dst in novos:
                    parte = tuple((v,) for v in novos[c_dst][a:b + 1])
                    ws.Range(ws.Cells(LINHA_MOLDE + a, c_dst), ws.Cells(LINHA_MOLDE + b, c_dst)).Value2 = parte
            avisa(f"Planilha LANTEK_SKA — só {len(mudadas)} de {n} linhas mudaram…")
        else:
            limpar_ate = max(ultima_antiga, ultima_nova)
            ws.Range(ws.Cells(LINHA_MOLDE, 1), ws.Cells(limpar_ate, COL_CRUA_FIM)).ClearContents()
            if ultima_nova > ultima_antiga:        # linhas novas além do que já estava formatado: copia o formato da linha-molde
                try:
                    ws.Range(ws.Cells(LINHA_MOLDE, 1), ws.Cells(LINHA_MOLDE, COL_CRUA_FIM)).Copy()
                    ws.Range(ws.Cells(ultima_antiga + 1, 1), ws.Cells(ultima_nova, COL_CRUA_FIM)).PasteSpecial(XL_PASTE_FORMATS)
                    excel.CutCopyMode = False
                except Exception:
                    pass
            for c_dst in novos:
                parte = tuple((v,) for v in novos[c_dst])
                ws.Range(ws.Cells(LINHA_MOLDE, c_dst), ws.Cells(ultima_nova, c_dst)).Value2 = parte

        fase("arrastando as fórmulas")
        fim_formula = max(ultima_nova, ultima_formula_antiga)
        if fim_formula > LINHA_MOLDE and ult_col_formula >= COL_FORMULA_INI:
            if incremental and ultima_formula_antiga >= LINHA_MOLDE:
                if ultima_nova > ultima_formula_antiga:     # fórmulas antigas ficam como estão; só estica para as linhas novas
                    ini_f = ws.Range(ws.Cells(ultima_formula_antiga, COL_FORMULA_INI), ws.Cells(ultima_formula_antiga, ult_col_formula))
                    ini_f.AutoFill(ws.Range(ws.Cells(ultima_formula_antiga, COL_FORMULA_INI), ws.Cells(ultima_nova, ult_col_formula)), 0)
            else:
                molde = ws.Range(ws.Cells(LINHA_MOLDE, COL_FORMULA_INI), ws.Cells(LINHA_MOLDE, ult_col_formula))
                molde.AutoFill(ws.Range(ws.Cells(LINHA_MOLDE, COL_FORMULA_INI), ws.Cells(fim_formula, ult_col_formula)), 0)

        try:
            cel = ws.Range(CELULA_DT_EXPORT)
            if not cel.HasFormula:
                cel.Value2 = float((date.today() - date(1899, 12, 30)).days)
        except Exception:
            pass

        fase("recalculando só o que mudou")
        try:
            excel.Calculate()                              # só as células "sujas" (rápido), não a pasta inteira
        except Exception:
            pass
        fase("atualizando as tabelas dinâmicas")
        pv_ok, pv_erro = _corrigir_pivot_caches(wb_dst, ABA_NESTING, ultima_nova)
        try:
            excel.Calculation = XL_CALC_AUTO               # o arquivo precisa ser salvo em cálculo AUTOMÁTICO
        except Exception:
            pass

        fase("salvando (em arquivo temporário)")
        wb_dst.SaveAs(tmp_xlsb, FileFormat=XL_EXCEL12)
        resultado = {"linhas": n, "linhas_antes": max(0, ultima_antiga - LINHA_MOLDE + 1), "sem_origem": sem_origem,
                     "pivots_ok": pv_ok, "pivots_erro": pv_erro, "backup": backup, "destino": destino,
                     "obras": len(resumo["obras"]),
                     "linhas_mudadas": (len(mudadas) if incremental else None)}
    except Exception as e:
        if estourou[0]:
            raise RuntimeError(f"a atualização demorou mais de {int(limite / 60)} min e o Excel foi encerrado — "
                               "a planilha original NÃO foi alterada (tente de novo; se repetir, veja se ela está pesada/aberta por outra pessoa)")
        raise
    finally:
        parar_relogio_tela.set()
        try:
            if relogio is not None:
                relogio.cancel()
        except Exception:
            pass
        for wb in (wb_dst, wb_src, wb_branco):
            try:
                if wb is not None:
                    wb.Close(SaveChanges=False)
            except Exception:
                pass
        try:
            if excel is not None:
                excel.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    fase("substituindo o arquivo")
    novo = destino + ".novo"
    try:
        shutil.copy2(tmp_xlsb, novo)
        os.replace(novo, destino)
    except Exception as e:
        raise RuntimeError(f"a planilha foi atualizada, mas não consegui substituir o arquivo original ({e}). "
                           f"A versão nova ficou em: {tmp_xlsb}")
    shutil.rmtree(pasta_tmp, ignore_errors=True)
    t0[1] and tempos.__setitem__(t0[1], round(time.perf_counter() - t0[0], 1))
    resultado["tempos"] = tempos
    resultado["segundos"] = round(sum(tempos.values()))
    _registrar_atualizacao(caminho_relatorio, destino, resultado["linhas"], arquivo_estado)
    return resultado


def texto_resultado(r):
    """Frase curta para o status do Agrupador."""
    if r.get("pulou"):
        return (f"✅ Planilha LANTEK_SKA já estava atualizada com este relatório ({r['linhas']} linhas, "
                f"{r.get('quando', '')}) — não precisei repetir")
    msg = f"✅ Planilha LANTEK_SKA atualizada ({r['linhas']} linhas de nesting, antes {r['linhas_antes']}"
    if r.get("linhas_mudadas") is not None:
        msg += f", só {r['linhas_mudadas']} mudaram"
    msg += f", {r['segundos']} s)" if r.get("segundos") is not None else ")"
    if r.get("backup"):
        msg += " · cópia em 00. Back up"
    if r.get("sem_origem"):
        msg += f" · ⚠ colunas sem origem no relatório: {', '.join(r['sem_origem'][:4])}"
    if r.get("pivots_erro"):
        msg += f" · ⚠ {r['pivots_erro']} tabela(s) dinâmica(s) não atualizaram"
    return msg
