"""
PREPARAÇÃO FÁBRICA · ROTEIRIZADOR DXF — dentro da aba do sistema (sem a janela Tkinter).

A lógica é a do programa original (apps/Roteirizador_DXF/roteirizador_original/roteirizador_dxf_projeart.py),
importada SEM alteração. Este módulo só faz o papel da tela Tkinter:
  • roda o processamento numa linha de execução própria e guarda o log (o que o programa imprime);
  • guarda o relatório de divergências e os pesos da última rodada (a aba pode ser recarregada);
  • executa as ações dos botões (memória SQLite: ignorar, fluxo manual, [PADRÃO] PLANILHA, conferido, forçar CAM);
  • Verificador: pastas da lista, comparação com o retrato e conferência pelas regras (somente leitura).
Só o próprio computador do sistema usa (app.py confere com _do_proprio_pc).
"""
from __future__ import annotations

import io
import math
import os
import shutil
import sys
import threading
import time
import types
from datetime import datetime
from pathlib import Path

from . import fabrica

PASTA_APP = fabrica.PASTA_APPS / "Roteirizador_DXF"
PASTA_RECEBIDOS = fabrica.PASTA_DADOS_PRODUCAO / "recebidos" / "roteirizador"

_trava = threading.Lock()
_M = {"mod": None, "erro": ""}


# ------------------------------------------------------------------ carregar o programa original
def _tk_falso():
    """O programa importa tkinter no topo. Se este Python não tiver tkinter, entra um módulo vazio (a tela não é usada)."""
    try:
        import tkinter  # noqa: F401
        from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser  # noqa: F401
        return
    except Exception:
        pass

    class _Vazio(types.ModuleType):
        def __getattr__(self, nome):
            if nome.startswith("__"):
                raise AttributeError(nome)
            c = type(nome, (object,), {"__init__": lambda s, *a, **k: None})
            setattr(self, nome, c)
            return c

    tk = _Vazio("tkinter")
    for sub in ("ttk", "filedialog", "messagebox", "simpledialog", "colorchooser"):
        m = _Vazio("tkinter." + sub)
        setattr(tk, sub, m)
        sys.modules["tkinter." + sub] = m
    sys.modules["tkinter"] = tk


class _Roteador(io.TextIOBase):
    """sys.stdout: o que a linha de execução do processamento imprime vai para o log da aba; o resto segue normal."""

    def __init__(self, original):
        self.original = original
        self.destinos: dict[int, list] = {}

    def write(self, t):
        d = self.destinos.get(threading.get_ident())
        if d is not None:
            d.append(t)
            return len(t)
        try:
            return self.original.write(t) if self.original else len(t)
        except Exception:
            return len(t)

    def flush(self):
        try:
            if self.original:
                self.original.flush()
        except Exception:
            pass


_ROT: _Roteador | None = None


def _modulo():
    with _trava:
        if _M["mod"] is not None:
            return _M["mod"]
        global _ROT
        _tk_falso()
        if str(PASTA_APP) not in sys.path:
            sys.path.insert(0, str(PASTA_APP))
        import importlib
        mod = importlib.import_module("roteirizador_original.roteirizador_dxf_projeart")

        def _banco():  # memória na pasta de dados do PCP (a mesma que o app usa: PPCP_DADOS/roteirizador_original)
            base = os.path.join(fabrica._pasta_dados(), "roteirizador_original")
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, mod.NOME_BANCO_MEMORIA)

        mod._caminho_banco_memoria = _banco
        if not isinstance(sys.stdout, _Roteador):
            _ROT = _Roteador(sys.stdout)
            sys.stdout = _ROT
        else:
            _ROT = sys.stdout
        try:
            mod.inicializar_memoria()
        except Exception:
            pass
        _M["mod"] = mod
        return mod


def disponivel() -> dict:
    est = fabrica.estado("pg22")
    if not est.get("existe"):
        return {"ok": False, "erro": "O Roteirizador DXF não está nesta instalação (pasta apps/Roteirizador_DXF)."}
    if est.get("faltam"):
        return {"ok": False, "faltam": est["faltam"],
                "erro": "Faltam bibliotecas para o Roteirizador DXF: " + ", ".join(est["faltam"]) + "."}
    try:
        _modulo()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "erro": f"Não consegui carregar o Roteirizador DXF: {e}"}
    return {"ok": True}


# ------------------------------------------------------------------ JSON
def _limpo(x):
    if isinstance(x, dict):
        return {str(k): _limpo(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_limpo(v) for v in x]
    if isinstance(x, float):
        return None if (math.isnan(x) or math.isinf(x)) else x
    if x is None or isinstance(x, (str, int, bool)):
        return x
    try:
        import numpy as np
        if isinstance(x, np.generic):
            return _limpo(x.item())
    except Exception:
        pass
    return str(x)


# ------------------------------------------------------------------ estado da tela
_S = {
    "rodando": False, "log": [], "status": "", "status_tipo": "", "erro_sel": "",
    "planilha": "", "pasta": "", "rel": None, "pesos": None, "rel_id": 0, "gerado_em": "",
}
_V = {"pastas": [], "linhas": {}, "status": "", "status_tipo": "", "status2": "", "status2_tipo": "",
      "lendo": False, "repetir": False, "novas": set(), "aviso_sem_retrato": 0, "id": 0}
_VR = {"rodando": False, "linhas": {}, "status": "", "status_tipo": "", "planilha": "", "id": 0}


def _log(msg):
    _S["log"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _fluxos(mod, esp):
    if esp not in (None, ""):
        try:
            e = str(esp).replace(".", ",")
            return [f"{b} [{e}]" for b in mod._FLUXOS_BASE_DISPONIVEIS]
        except Exception:
            pass
    return list(mod._FLUXOS_BASE_DISPONIVEIS)


def estado(desde: int = 0) -> dict:
    lg = _S["log"]
    desde = max(0, min(int(desde or 0), len(lg)))
    return _limpo({
        "ok": True, "rodando": _S["rodando"], "log": lg[desde:], "n": len(lg), "status": _S["status"],
        "status_tipo": _S["status_tipo"], "erro_sel": _S["erro_sel"], "planilha": _S["planilha"], "pasta": _S["pasta"],
        "rel_id": _S["rel_id"], "ver_id": _V["id"], "vr_id": _VR["id"], "vr_rodando": _VR["rodando"],
        "ver_lendo": _V["lendo"],
    })


# ------------------------------------------------------------------ 1) Roteirizador
def iniciar(planilha: str, pasta: str) -> dict:
    d = disponivel()
    if not d["ok"]:
        return d
    mod = _modulo()
    if _S["rodando"]:
        return {"ok": False, "erro": "Já tem um processamento em andamento."}
    planilha = mod._normalizar_caminho(planilha)
    pasta = mod._normalizar_caminho(pasta)
    _S["planilha"], _S["pasta"] = planilha, pasta
    if not planilha or not os.path.exists(planilha):
        _S["erro_sel"] = "❌ Selecione um caminho de planilha válido."
        return {"ok": False, "erro": _S["erro_sel"], "campo": "planilha"}
    if not pasta or not os.path.exists(pasta):
        _S["erro_sel"] = "❌ Selecione uma pasta de DXF válida."
        return {"ok": False, "erro": _S["erro_sel"], "campo": "pasta"}
    _S.update(rodando=True, log=[], erro_sel="", status="⚙️  Processando, aguarde...", status_tipo="aviso")
    threading.Thread(target=_executar, args=(planilha, pasta), daemon=True).start()
    return {"ok": True}


def _executar(planilha, pasta):
    mod = _modulo()
    buf: list = []
    tid = threading.get_ident()
    pend = [""]

    def escoar():
        if not buf:
            return
        t = pend[0] + "".join(buf)
        buf.clear()
        partes = t.split("\n")
        pend[0] = partes.pop()
        _S["log"].extend(partes)

    _ROT.destinos[tid] = buf
    parar = threading.Event()

    def bomba():
        while not parar.wait(0.25):
            escoar()

    threading.Thread(target=bomba, daemon=True).start()
    try:
        print("\n" + "=" * 70)
        print(f" {mod.VERSAO} ".center(70, "="))
        print("=" * 70 + "\n")
        mod.log(f"📁 Planilha: {planilha}")
        mod.log(f"📁 Pasta DXF: {pasta}")
        print("\n" + "-" * 70)
        df = mod.carregar_planilha(planilha)
        essenciais = ['OF_N', 'POS_N', 'ID_N', 'DEF_N', 'ESP_N', 'LARGURA_N', 'DESENV_N', 'COMPR_N', 'QTD_N']
        presentes = [c for c in essenciais if c in df.columns]
        if len(presentes) < 5:
            msg = ("Colunas essenciais não encontradas na planilha selecionada.\n"
                   f"Colunas encontradas: {presentes}")
            mod.log(f"❌ ERRO: {msg}")
            _erro(msg)
            return
        print("\n" + "-" * 70)
        mod.log("🚀 Iniciando processamento dos arquivos DXF...")
        (dxfs, ofs, _qtd, dims, _furos, _fluxos_atr, ignorados_mem, pesos) = mod.processar(df, pasta)
        mod.log("🔄 Padronizando nomes de pastas...")
        mod.padronizar_espessura(pasta)
        mod.log("🔀 Consolidando pastas de fluxo com espessuras variantes...")
        mod.consolidar_pastas_variantes(pasta)
        mod.log("🔲 Aplicando regra própria para peças de chapa xadrez...")
        mod.processar_pastas_xadrez(pasta, df)
        mod.log("🧾 Salvando retrato da roteirização para conferência posterior (aba Verificador)...")
        mod.salvar_log_roteirizacao(pasta, dxfs)
        mod.log("📊 Analisando divergências (planilha x DXF)...")
        rel = mod.analisar_divergencias(df, dxfs, ofs, ignorados_mem, dims)
        mod.log("🚫 Verificando peças que ficaram fora de qualquer pasta de fluxo...")
        rel["nao_roteirizado"] = mod.detectar_pecas_fora_do_fluxo(pasta, df)
        print("\n" + "=" * 70)
        mod.log("✨ PROCESSO FINALIZADO COM SUCESSO!")
        print("=" * 70 + "\n")
        of_principal = next(iter(ofs)) if ofs else "DESCONHECIDA"
        mod.log(f"📌 OF processada: {of_principal}")
        mod.log(f"📁 Total de arquivos roteirizados: {len(dxfs)}")
        _finalizar(rel, pesos, pasta)
    except Exception as ex:  # noqa: BLE001
        mod.log(f"❌ ERRO INESPERADO durante o processamento: {ex}")
        _erro(str(ex))
    finally:
        parar.set()
        _ROT.destinos.pop(tid, None)
        escoar()
        if pend[0]:
            _S["log"].append(pend[0])
        _S["rodando"] = False


def _erro(msg):
    _S["status"], _S["status_tipo"] = "", ""
    _S["erro_sel"] = "❌ " + msg.split("\n")[0]


def _finalizar(rel, pesos, pasta):
    mod = _modulo()
    n = 0
    for k in ("faltantes", "sem_cam", "ignorados_memoria_lista", "padrao_planilha", "divergencias_tamanho", "nao_roteirizado"):
        rel[k] = list(rel.get(k) or [])
        for it in rel[k]:
            n += 1
            it["_id"] = f"i{n}"
            if k in ("faltantes", "nao_roteirizado"):
                it["opcoes_fluxo"] = _fluxos(mod, it.get("espessura"))
    _S["rel"] = rel
    _S["pesos"] = pesos
    _S["gerado_em"] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    _S["rel_id"] += 1
    _S["status"], _S["status_tipo"] = "✅ Processamento concluído. Veja as abas de relatório e peso.", "ok"
    try:
        ver_adicionar(pasta, silencioso=True)
    except Exception as ex:  # noqa: BLE001
        _log(f"⚠️  Não consegui incluir a pasta no Verificador: {ex}")


def limpar() -> dict:
    if _S["rodando"]:
        return {"ok": False, "erro": "Aguarde o processamento terminar."}
    _S.update(log=[], status="", status_tipo="", erro_sel="", planilha="", pasta="", rel=None, pesos=None, gerado_em="")
    _S["rel_id"] += 1
    return {"ok": True}


def receber(nome: str, dados: bytes) -> dict:
    nome = os.path.basename(nome or "planilha.xlsx").strip() or "planilha.xlsx"
    if os.path.splitext(nome)[1].lower() not in (".csv", ".xlsx", ".xls", ".xlsm"):
        return {"ok": False, "erro": "Formato de planilha inválido."}
    PASTA_RECEBIDOS.mkdir(parents=True, exist_ok=True)
    alvo = PASTA_RECEBIDOS / nome
    alvo.write_bytes(dados)
    return {"ok": True, "caminho": str(alvo)}


# ------------------------------------------------------------------ 2) Relatório de divergências
def relatorio() -> dict:
    rel = _S["rel"]
    if not rel:
        return {"ok": True, "vazio": True, "rel_id": _S["rel_id"]}
    return _limpo({"ok": True, "vazio": False, "rel_id": _S["rel_id"], "gerado_em": _S["gerado_em"], **rel})


def _achar(lista, ids):
    ids = set(ids or [])
    return [it for it in lista if it.get("_id") in ids]


def rel_acao(d: dict) -> dict:
    mod = _modulo()
    rel = _S["rel"]
    if not rel:
        return {"ok": False, "erro": "Nenhum relatório gerado ainda."}
    lista_nome = d.get("lista")
    acao = d.get("acao")
    linhas = {str(x.get("id")): x for x in (d.get("itens") or [])}
    motivo_geral = str(d.get("motivo") or "").strip()
    if lista_nome not in ("faltantes", "nao_roteirizado", "divergencias_tamanho", "sem_cam"):
        return {"ok": False, "erro": "Lista desconhecida."}
    lista = rel[lista_nome]
    sel = _achar(lista, linhas.keys())
    if not sel:
        return {"ok": False, "erro": "Nenhum item selecionado."}
    msg, tipo, falhas, movidos = "", "ok", [], 0
    for it in sel:
        lin = linhas.get(it["_id"], {})
        motivo = str(lin.get("motivo") or "").strip()
        fluxo = str(lin.get("fluxo") or "").strip()
        ident, pos = it.get("identificador", ""), it.get("pos", "")
        if acao == "ignorar":
            mod.marcar_ignorado(ident, pos, motivo)
            rel["ignorados_memoria_lista"].append({**it, "tipo": it.get("tipo") or mod.extrair_tipo_identificador(ident, pos)})
        elif acao == "fluxo":
            mod.marcar_ajuste_manual(ident, pos, fluxo, motivo)
            if lista_nome == "nao_roteirizado":
                pasta_atual, arq = it.get("pasta_atual"), it.get("arquivo")
                try:
                    if pasta_atual and arq:
                        cam = os.path.join(pasta_atual, arq)
                        if os.path.isfile(cam):
                            destino = os.path.join(pasta_atual, fluxo)
                            os.makedirs(destino, exist_ok=True)
                            shutil.move(cam, os.path.join(destino, arq))
                            movidos += 1
                        else:
                            falhas.append(f"{arq} (arquivo não encontrado mais na pasta)")
                    else:
                        falhas.append(f"{arq or '(sem nome)'} (pasta de origem desconhecida)")
                except Exception as ex:  # noqa: BLE001
                    falhas.append(f"{arq} ({ex})")
        elif acao == "padrao":
            mod.marcar_padrao_planilha_manual(ident, pos, motivo)
            novo = dict(it)
            if lista_nome == "nao_roteirizado":
                novo["tipo"] = mod.extrair_tipo_identificador(ident, pos)
            rel["padrao_planilha"].append(novo)
        elif acao == "conferido":
            mod.marcar_divergencia_tamanho_ignorada(ident, pos, motivo_geral)
        elif acao == "forcar_cam":
            mod.marcar_forcar_cam(ident, pos, motivo_geral)
        else:
            return {"ok": False, "erro": "Ação desconhecida."}
        lista.remove(it)
    n = len(sel)
    aba = "aba Não Roteirizado" if lista_nome == "nao_roteirizado" else "aba de relatório"
    if acao == "ignorar":
        msg = f"✅ {n} item(ns) marcado(s) como ignorado(s) - gravado na memória."
        _log(f"🧠 {n} item(ns) marcado(s) como ignorado(s) via {aba}")
    elif acao == "fluxo" and lista_nome == "nao_roteirizado":
        if falhas:
            msg, tipo = (f"⚠️ {movidos} movido(s), {len(falhas)} com problema (veja o log). Fluxo já foi salvo na "
                         "memória mesmo assim."), "aviso"
            _log("⚠️ Falha ao mover fisicamente alguns itens de 'Não Roteirizado': " + "; ".join(falhas))
        else:
            msg = f"✅ {movidos} item(ns) movido(s) para o fluxo escolhido e memorizado(s) para qualquer obra futura."
        _log(f"🔀 Fluxo manual definido e aplicado para {movidos} item(ns) via aba Não Roteirizado")
    elif acao == "fluxo":
        msg = f"✅ Fluxo manual salvo para {n} item(ns)."
        _log(f"🔀 Fluxo manual definido para {n} item(ns) via aba de relatório")
    elif acao == "padrao":
        msg = f"✅ {n} item(ns) movido(s) para [PADRÃO] PLANILHA."
        _log(f"📋 {n} item(ns) movido(s) para [PADRÃO] PLANILHA via {aba}")
    elif acao == "conferido":
        msg = f"✅ {n} divergência(s) marcada(s) como conferida(s) - não aparecem mais."
        _log(f"📐 {n} divergência(s) de tamanho marcada(s) como conferida(s) via aba de relatório")
    elif acao == "forcar_cam":
        msg = f"✅ CAM forçado para {n} item(ns) - gravado na memória."
        _log(f"🔓 CAM forçado para {n} item(ns) via aba de relatório (desconsiderando BR/TB)")
    return {"ok": True, "msg": msg, "tipo": tipo, **relatorio()}


# ------------------------------------------------------------------ 3) Peso por fluxo
def pesos() -> dict:
    mod = _modulo()
    if _S["pesos"] is None:
        return {"ok": True, "vazio": True}
    dados = mod.agregar_pesos_por_fluxo(_S["pesos"])
    cores = mod.carregar_cores_fluxo_customizadas()
    tipo = mod.carregar_preferencia_ui("tipo_grafico_peso", "barras")
    if tipo not in ("barras", "pizza", "velas"):
        tipo = "barras"
    for it in dados:
        it["cor"] = cores.get(it["fluxo"]) or mod._cor_para_fluxo(it["fluxo"])
        it["cor_padrao"] = mod._cor_para_fluxo(it["fluxo"])
        it["peso_total_txt"] = mod.formatar_numero_br(it["peso_total"])
        it["pecas_txt"] = mod.formatar_numero_br(it["quantidade_pecas"], 0)
        it["peso_medio_txt"] = mod.formatar_numero_br(it["peso_medio"])
    tot = sum(d["peso_total"] for d in dados)
    pcs = sum(d["quantidade_pecas"] for d in dados)
    return _limpo({"ok": True, "vazio": False, "tipo": tipo, "dados": dados,
                   "resumo": (f"Peso total roteirizado: {mod.formatar_numero_br(tot)} kg   |   "
                              f"{mod.formatar_numero_br(pcs, 0)} peça(s)   |   {len(dados)} fluxo(s)") if dados else ""})


def pesos_tipo(tipo: str) -> dict:
    mod = _modulo()
    if tipo in ("barras", "pizza", "velas"):
        mod.salvar_preferencia_ui("tipo_grafico_peso", tipo)
    return pesos()


def pesos_cores(cores: dict) -> dict:
    mod = _modulo()
    for fluxo, cor in (cores or {}).items():
        if isinstance(cor, str) and cor.startswith("#") and len(cor) in (4, 7):
            mod.salvar_cor_fluxo_customizada(str(fluxo), cor)
    return pesos()


# ------------------------------------------------------------------ 4) Verificador
def _limpar_caminho(t):
    t = (t or "").strip().strip('"').strip("'").strip()
    t = os.path.expandvars(t)
    if t and os.path.isfile(t):
        t = os.path.dirname(t)
    return t


def verificador() -> dict:
    return _limpo({
        "ok": True, "id": _V["id"], "pastas": _V["pastas"], "lendo": _V["lendo"],
        "status": _V["status"], "status_tipo": _V["status_tipo"], "status2": _V["status2"], "status2_tipo": _V["status2_tipo"],
        "aviso_sem_retrato": _V["aviso_sem_retrato"],
        "linhas": [{"chave": k, **v} for k, v in _V["linhas"].items()],
        "vr": {"rodando": _VR["rodando"], "status": _VR["status"], "status_tipo": _VR["status_tipo"],
               "planilha": _VR["planilha"], "linhas": [{"chave": k, **v} for k, v in _VR["linhas"].items()]},
    })


def ver_adicionar(caminho: str, silencioso: bool = False) -> dict:
    d = disponivel()
    if not d["ok"]:
        return d
    c = _limpar_caminho(caminho)
    if not c or not os.path.isdir(c):
        return {"ok": False, "titulo": "Pasta inválida",
                "erro": "Não encontrei essa pasta:\n\n" + (c or "(campo vazio)") +
                        "\n\nConfira o caminho (pode colar com aspas, tudo bem) e se o computador consegue abrir essa pasta."}
    alvo = os.path.abspath(c)
    if not any(os.path.abspath(p["caminho"]) == alvo for p in _V["pastas"]):
        _V["pastas"].append({"caminho": c, "sel": True})
        if not silencioso:
            _V["novas"].add(alvo)
    _V["id"] += 1
    ver_verificar(mostrar_log=not silencioso)
    return verificador()


def ver_marcar(caminhos: list, sel: bool | None = None) -> dict:
    alvo = {os.path.abspath(c) for c in caminhos or []}
    for p in _V["pastas"]:
        if os.path.abspath(p["caminho"]) in alvo:
            p["sel"] = (not p["sel"]) if sel is None else bool(sel)
    _V["id"] += 1
    return verificador()


def ver_todas() -> dict:
    if _V["pastas"]:
        marcar = any(not p["sel"] for p in _V["pastas"])
        for p in _V["pastas"]:
            p["sel"] = marcar
    _V["id"] += 1
    return verificador()


def ver_remover() -> dict:
    fora = {os.path.abspath(p["caminho"]) for p in _V["pastas"] if p["sel"]}
    _V["pastas"] = [p for p in _V["pastas"] if os.path.abspath(p["caminho"]) not in fora]
    for k in list(_V["linhas"]):
        if os.path.abspath(_V["linhas"][k]["_pasta"]) in fora:
            _V["linhas"].pop(k)
    _V["id"] += 1
    ver_verificar(mostrar_log=False)
    return verificador()


def ver_verificar(mostrar_log: bool = True, periodico: bool = False) -> dict:
    pastas = [p["caminho"] for p in _V["pastas"]]
    if not pastas:
        _V["linhas"].clear()
        _V.update(status="", status2="")
        _V["id"] += 1
        return verificador()
    if _V["lendo"]:
        if not periodico:
            _V["repetir"] = True
        return verificador()
    if not periodico:
        _V["status2"], _V["status2_tipo"] = "🔎 Verificando as pastas…", "aviso"
    _V["lendo"] = True
    _V["id"] += 1
    threading.Thread(target=_ver_trabalho, args=(pastas, mostrar_log), daemon=True).start()
    return verificador()


def _ver_trabalho(pastas, mostrar_log):
    mod = _modulo()
    resultado = {}
    for p in pastas:
        try:
            resultado[p] = mod.comparar_roteirizacoes_da_pasta(p)
        except Exception as ex:  # noqa: BLE001
            resultado[p] = ex
    try:
        atuais = {os.path.abspath(p["caminho"]) for p in _V["pastas"]}
        _ver_aplicar([p for p in pastas if os.path.abspath(p) in atuais], resultado, mostrar_log)
    except Exception as ex:  # noqa: BLE001
        _log(f"⚠️  Verificador: erro ao atualizar a tela: {ex}")
    _V["lendo"] = False
    _V["id"] += 1
    if _V["repetir"]:
        _V["repetir"] = False
        ver_verificar(mostrar_log=False)


def _ver_aplicar(pastas, resultado, mostrar_log):
    atuais_chaves = set()
    nao_enc = 0
    sem_log, com_erro, ok = [], [], []
    for pasta in pastas:
        lista = resultado.get(pasta)
        nome = os.path.basename(os.path.normpath(pasta)) or pasta
        if isinstance(lista, Exception):
            com_erro.append(f"{nome} ({lista})")
            continue
        if not lista:
            sem_log.append(pasta)
            continue
        for res in lista:
            pasta_log = res.get("pasta_log") or pasta
            nome_log = os.path.basename(os.path.normpath(pasta_log)) or pasta_log
            nao_enc += len(res["nao_encontrados"])
            ok.append(f"✅ {nome_log}: retrato de {res.get('gerado_em', '?')} · "
                      f"{res.get('total', 0)} peça(s) conferidas · {len(res['divergencias'])} alterada(s) à mão")
            for item in res["divergencias"]:
                chave = pasta + "|" + os.path.join(pasta_log, str(item.get("arquivo")))
                atuais_chaves.add(chave)
                if chave in _V["linhas"]:
                    _V["linhas"][chave]["fluxo_atual"] = item.get("fluxo_atual")
                else:
                    _V["linhas"][chave] = {**_limpo(item), "_pasta": pasta}
                    if mostrar_log:
                        _log(f"🔍 Verificador: nova alteração manual detectada -> {item.get('arquivo', '')} "
                             f"('{item.get('pasta_no_snapshot', '')}' -> '{item.get('fluxo_atual', '')}')")
    abs_pastas = {os.path.abspath(p) for p in pastas}
    for k in list(_V["linhas"]):
        if os.path.abspath(_V["linhas"][k]["_pasta"]) in abs_pastas and k not in atuais_chaves:
            _V["linhas"].pop(k)
    msgs = list(ok[:6])
    if len(ok) > 6:
        msgs.append(f"… e mais {len(ok) - 6} obra(s) conferida(s).")
    if sem_log:
        nomes = ", ".join(os.path.basename(os.path.normpath(p)) or p for p in sem_log)
        msgs.append(f"ℹ️ Sem retrato do roteirizador: {nomes}. Isso NÃO impede a conferência: use \"Conferir pelas regras "
                    "(somente leitura)\" aqui embaixo (com a planilha da obra) para ver o que está fora da regra. O "
                    "acompanhamento automático de peças movidas à mão só existe depois que o Roteirizador rodar nessa pasta.")
    if com_erro:
        msgs.append("❌ Não consegui ler: " + "; ".join(com_erro))
    _V["status"] = "\n".join(msgs)
    _V["status_tipo"] = "aviso" if (sem_log or com_erro) else "ok"
    t = f"🔎 {len(_V['linhas'])} posição(ões) com fluxo alterado manualmente."
    if nao_enc:
        t += f" ({nao_enc} arquivo(s) do log não encontrado(s) mais na pasta.)"
    if ok:
        t += " Verificando continuamente..."
    _V["status2"], _V["status2_tipo"] = t, "ok"
    if any(os.path.abspath(p) in _V["novas"] for p in sem_log):
        _V["aviso_sem_retrato"] += 1
    _V["novas"] = set()


def ver_salvar(chaves: list, motivos: dict) -> dict:
    mod = _modulo()
    feitos = 0
    ultimo = None
    for chave in chaves or []:
        info = _V["linhas"].get(chave)
        motivo = str((motivos or {}).get(chave) or "").strip()
        if not info or not motivo:
            continue
        fluxo = info.get("fluxo_atual")
        mod.marcar_ajuste_manual(info.get("identificador"), info.get("pos"), fluxo, motivo)
        mod.atualizar_entrada_log_roteirizacao(info.get("pasta_base"), info.get("arquivo"), fluxo)
        _V["linhas"].pop(chave, None)
        feitos += 1
        ultimo = info
        _log(f"🧠 Verificador: ajuste manual salvo -> identificador '{info.get('identificador')}' / "
             f"posição '{info.get('pos')}' -> '{fluxo}' (motivo: {motivo})")
    if ultimo:
        _V["status2"], _V["status2_tipo"] = (f"✅ Ajuste salvo para a posição {ultimo.get('pos')} (identificador "
                                             f"{ultimo.get('identificador')}). Já vale para qualquer obra futura."), "ok"
    _V["id"] += 1
    return {**verificador(), "feitos": feitos}


def vr_conferir(planilha: str, caminho_campo: str = "") -> dict:
    d = disponivel()
    if not d["ok"]:
        return d
    mod = _modulo()
    if _VR["rodando"]:
        return verificador()
    if _limpar_caminho(caminho_campo):
        r = ver_adicionar(caminho_campo)
        if not r.get("ok"):
            return r
    pastas = [p["caminho"] for p in _V["pastas"]]
    if not pastas:
        return {"ok": False, "titulo": "Nenhuma pasta", "erro": "Adicione (campo acima) a pasta dos DXF que você quer conferir."}
    pl = mod._normalizar_caminho(planilha) or mod._normalizar_caminho(_S["planilha"])
    if not pl or not os.path.isfile(pl):
        return {"ok": False, "titulo": "Planilha necessária",
                "erro": "Para aplicar as regras o programa precisa da planilha da obra (a mesma do Roteirizador: é nela que "
                        "estão o identificador, a definição e a espessura de cada posição).\n\nEscolha a planilha no campo acima."}
    _VR.update(planilha=pl, rodando=True, status_tipo="aviso",
               status="🔎 Conferindo com as regras (somente leitura)… pode levar alguns minutos em pasta de rede.")
    _VR["id"] += 1
    threading.Thread(target=_vr_trabalho, args=(pl, pastas), daemon=True).start()
    return verificador()


def _vr_trabalho(planilha, pastas):
    mod = _modulo()
    saida = {"linhas": [], "total": 0, "pastas_ok": 0}
    buf: list = []
    tid = threading.get_ident()
    _ROT.destinos[tid] = buf          # o processar em modo simulação imprime muito: não vai para o terminal
    try:
        df = mod.carregar_planilha(planilha)
        essenciais = ['OF_N', 'POS_N', 'ID_N', 'DEF_N', 'ESP_N', 'LARGURA_N', 'DESENV_N', 'COMPR_N', 'QTD_N']
        if len([c for c in essenciais if c in df.columns]) < 5:
            raise RuntimeError("Colunas essenciais não encontradas na planilha selecionada.")
        mod.inicializar_memoria()
        for p in pastas:
            sim, total = mod.conferir_pasta_com_regras(df, p)
            saida["linhas"].extend(sim)
            saida["total"] += total
            saida["pastas_ok"] += 1
        _VR["linhas"] = {}
        vistos = set()
        for dd in saida["linhas"]:
            chave = os.path.normcase(os.path.abspath(dd["caminho"]))
            if chave in vistos:
                continue
            vistos.add(chave)
            opcoes = []
            for cand in (dd.get("atual"), dd.get("regra")):
                if cand and mod._nome_parece_fluxo(cand) and cand not in opcoes:
                    opcoes.append(cand)
            _VR["linhas"][chave] = {**_limpo(dd), "opcoes": opcoes}
        n = len(_VR["linhas"])
        if n:
            _VR["status"] = (f"⚠️ {n} posição(ões) fora da regra, de {saida['total']} DXF conferido(s) em "
                             f"{saida['pastas_ok']} pasta(s). Nada foi movido.")
            _VR["status_tipo"] = "aviso"
        else:
            _VR["status"] = (f"✅ {saida['total']} DXF conferido(s) em {saida['pastas_ok']} pasta(s): todos estão na "
                             "pasta que a regra manda.")
            _VR["status_tipo"] = "ok"
        _log(f"🔎 Verificador (somente leitura): {n} fora da regra / {saida['total']} conferidos")
    except Exception as ex:  # noqa: BLE001
        _VR["status"], _VR["status_tipo"] = f"❌ Não consegui conferir: {ex}", "erro"
    finally:
        _ROT.destinos.pop(tid, None)
        _VR["rodando"] = False
        _VR["id"] += 1


def vr_salvar(itens: list) -> dict:
    mod = _modulo()
    ok, ultimo = 0, None
    for x in itens or []:
        chave = x.get("chave")
        info = _VR["linhas"].get(chave)
        motivo = str(x.get("motivo") or "").strip()
        fluxo = str(x.get("fluxo") or "").strip()
        if not info or not motivo or not fluxo:
            continue
        if not mod._nome_parece_fluxo(fluxo):
            return {**verificador(), "ok": False, "titulo": "Fluxo inválido",
                    "erro": f"'{fluxo}' não parece um nome de pasta de fluxo (ex.: Fluxo 4 [2,0], Perfiladeira L2 [1,55], "
                            "Perfiladeira U e C [2,0])."}
        mod.marcar_ajuste_manual(info.get("identificador"), info.get("pos"), fluxo, motivo)
        try:
            mod.atualizar_entrada_log_roteirizacao(info.get("pasta_base"), info.get("arquivo"), fluxo)
        except Exception:  # noqa: BLE001
            pass
        _VR["linhas"].pop(chave, None)
        ok += 1
        ultimo = (info, fluxo)
        _log(f"🧠 Verificador (somente leitura): ajuste manual salvo -> identificador '{info.get('identificador')}' / "
             f"posição '{info.get('pos')}' -> '{fluxo}' (motivo: {motivo})")
    if ok == 1 and ultimo:
        info, fluxo = ultimo
        _VR["status"] = (f"✅ Ajuste salvo para a posição {info.get('pos')} (identificador {info.get('identificador')}) -> "
                         f"{fluxo}. Já vale para qualquer obra futura.")
        _VR["status_tipo"] = "ok"
    elif ok:
        _VR["status"], _VR["status_tipo"] = f"✅ {ok} ajuste(s) salvo(s). Já valem para qualquer obra futura.", "ok"
    _VR["id"] += 1
    return {**verificador(), "feitos": ok}



# ------------------------------------------------------------------ V296: Relatório de ordens x fluxos (aba Gerar relatórios das ordens)
# O relatório é gerado pelo MESMO código do app da rede (gerar_relatorio_ordens_fluxos do roteirizador original):
# sequência divergente (aba REGRAS SEQUÊNCIA, linha vermelha), ORDEM MANUAL / ULT.PROC na ROTEIRIZAÇÃO FOCCO, ordem repetida
# para desconsiderar, concatenar só ordem numérica, peso líquido, chapa xadrez, guarda-corpo, painéis de gráficos e logo.
# Padrão PPCPM mantido: o arquivo vai para a pasta Downloads do usuário; a tela continua a do sistema.
PASTA_RO = fabrica.PASTA_DADOS_PRODUCAO / "recebidos" / "relatorio_ordens"
_RO = {"rodando": False, "log": [], "res": None, "erro": "", "id": 0, "sessao": ""}


def _parte_segura(t: str) -> str:
    t = str(t or "").replace("\\", "/")
    partes = [p for p in t.split("/") if p not in ("", ".", "..") and ":" not in p]
    return "/".join(partes)


def ro_receber(nome: str, dados: bytes) -> dict:
    """Arquivo arrastado (sem caminho no PC): grava em recebidos/relatorio_ordens/<sessão>/<caminho relativo>."""
    rel = _parte_segura(nome)
    if "/" not in rel:
        return {"ok": False, "erro": "Nome inválido."}
    alvo = PASTA_RO.joinpath(*rel.split("/"))
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(dados)
    sessao = rel.split("/")[0]
    return {"ok": True, "caminho": str(alvo), "base": str(PASTA_RO / sessao)}


def _ro_resumo(linhas: list, destino: str) -> dict:
    import re
    txt = "\n".join(linhas)
    num = lambda rx: int(re.search(rx, txt).group(1)) if re.search(rx, txt) else 0   # noqa: E731
    m_lote = re.search(r"_LOTE_([^_.]+)", os.path.basename(destino))
    return {
        "lote": m_lote.group(1) if m_lote else "",
        "linhas": num(r"Relatório: (\d+) linha"), "com_dxf": num(r"(\d+) com DXF"),
        "rota_auto": num(r"(\d+) perfilados sem DXF"), "sem_dxf": num(r"perfilados sem DXF, (\d+) sem DXF"),
        "sem_ordem": num(r"\((\d+) DXF\(s\) sem ordem"), "revisar": num(r"conferência: (\d+) ordem"),
        "divergentes": num(r"(\d+) ordem\(ns\) com SEQUÊNCIA DIVERGENTE"),
        "roteirizacao_focco": num(r"ROTEIRIZAÇÃO FOCCO: (\d+) linha"), "preparacao": num(r"Abas: (\d+) em Preparação"),
        "nao_preparacao": num(r"(\d+) em Não Preparação"), "ps_prep": num(r"(\d+) em PS PREP"),
        "desconsiderar": num(r"(\d+) ordem\(ns\) para desconsiderar"), "pendentes": num(r"(\d+) de preparação ainda sem fluxo"),
    }


def ro_iniciar(focco: str, pastas: list, sessao: str = "") -> dict:
    d = disponivel()
    if not d["ok"]:
        return d
    if _RO["rodando"]:
        return {"ok": False, "erro": "Já tem um relatório sendo gerado."}
    mod = _modulo()
    focco = mod._normalizar_caminho(focco)
    pastas = [mod._normalizar_caminho(p) for p in (pastas or []) if str(p or "").strip()]
    if not focco or not os.path.exists(focco):
        return {"ok": False, "erro": "Não encontrei o relatório do Focco: " + str(focco)}
    falta = [p for p in pastas if not os.path.isdir(p)]
    if not pastas or falta:
        return {"ok": False, "erro": "Não encontrei a pasta dos DXF: " + (falta[0] if falta else "(nenhuma)")}
    _RO.update(rodando=True, log=[], res=None, erro="", sessao=_parte_segura(sessao).split("/")[0] if sessao else "")
    _RO["id"] += 1
    threading.Thread(target=_ro_executar, args=(focco, pastas), daemon=True).start()
    return {"ok": True, "id": _RO["id"]}


def _ro_executar(focco, pastas):
    mod = _modulo()
    buf: list = []
    tid = threading.get_ident()
    pend = [""]

    def escoar():
        if not buf:
            return
        t = pend[0] + "".join(buf)
        buf.clear()
        partes = t.split("\n")
        pend[0] = partes.pop()
        _RO["log"].extend(p for p in partes if p.strip())

    _ROT.destinos[tid] = buf
    parar = threading.Event()

    def bomba():
        while not parar.wait(0.25):
            escoar()

    threading.Thread(target=bomba, daemon=True).start()
    try:
        from .caminhos import pasta_downloads
        saida = pasta_downloads()
        os.makedirs(saida, exist_ok=True)
        regs = mod.coletar_registros_das_pastas(pastas, mod.log)
        destino = mod.gerar_relatorio_ordens_fluxos(focco, regs, saida, mod.log)
        escoar()
        _RO["res"] = {"caminho": destino, "nome": os.path.basename(destino), "pasta": saida,
                      "resumo": _ro_resumo(_RO["log"], destino)}
    except Exception as ex:  # noqa: BLE001
        escoar()
        _RO["erro"] = str(ex) or ex.__class__.__name__
    finally:
        parar.set()
        _ROT.destinos.pop(tid, None)
        escoar()
        if pend[0].strip():
            _RO["log"].append(pend[0])
        if _RO["sessao"]:                              # apaga a cópia dos arquivos arrastados
            shutil.rmtree(PASTA_RO / _RO["sessao"], ignore_errors=True)
        _RO["rodando"] = False


def ro_estado(desde: int = 0) -> dict:
    lg = _RO["log"]
    desde = max(0, min(int(desde or 0), len(lg)))
    return _limpo({"ok": True, "rodando": _RO["rodando"], "log": lg[desde:], "n": len(lg), "res": _RO["res"],
                   "erro": _RO["erro"], "id": _RO["id"]})


def ro_abrir(qual: str = "arquivo") -> dict:
    r = _RO["res"]
    if not r:
        return {"ok": False, "erro": "Gere o relatório primeiro."}
    alvo = r["caminho"] if qual == "arquivo" else r["pasta"]
    if not os.path.exists(alvo):
        return {"ok": False, "erro": "O arquivo não está mais na pasta Downloads: " + alvo}
    return fabrica.abrir_pasta_caminho(alvo)

# ------------------------------------------------------------------ roteamento (chamado pelo app.py)
def get(acao: str, q: dict) -> dict:
    if acao == "estado":
        return estado(int(q.get("desde") or 0) if str(q.get("desde") or "0").isdigit() else 0)
    if acao == "disponivel":
        return disponivel()
    if acao == "relatorio":
        return relatorio()
    if acao == "pesos":
        return pesos()
    if acao == "verificador":
        return verificador()
    if acao == "ro_estado":
        return ro_estado(int(q.get("desde") or 0) if str(q.get("desde") or "0").isdigit() else 0)
    return {"ok": False, "erro": "Ação desconhecida."}


def post(acao: str, d: dict) -> dict:
    if acao == "iniciar":
        return iniciar(str(d.get("planilha") or ""), str(d.get("pasta") or ""))
    if acao == "limpar":
        return limpar()
    if acao == "rel":
        return rel_acao(d)
    if acao == "pesos_tipo":
        return pesos_tipo(str(d.get("tipo") or ""))
    if acao == "pesos_cores":
        return pesos_cores(d.get("cores") or {})
    if acao == "ver_adicionar":
        return ver_adicionar(str(d.get("caminho") or ""))
    if acao == "ver_marcar":
        return ver_marcar(d.get("caminhos") or [])
    if acao == "ver_todas":
        return ver_todas()
    if acao == "ver_remover":
        return ver_remover()
    if acao == "ver_verificar":
        return ver_verificar(mostrar_log=not d.get("periodico"), periodico=bool(d.get("periodico")))
    if acao == "ver_salvar":
        return ver_salvar(d.get("chaves") or [], d.get("motivos") or {})
    if acao == "vr_conferir":
        return vr_conferir(str(d.get("planilha") or ""), str(d.get("caminho") or ""))
    if acao == "vr_salvar":
        return vr_salvar(d.get("itens") or [])
    if acao == "ro_iniciar":
        return ro_iniciar(str(d.get("focco") or ""), list(d.get("pastas") or []), str(d.get("sessao") or ""))
    if acao == "ro_abrir":
        return ro_abrir(str(d.get("qual") or "arquivo"))
    return {"ok": False, "erro": "Ação desconhecida."}


# V287: devolve o trabalho que estava aberto antes do sistema reiniciar com a versão nova
try:
    from .sessao import devolver_fabrica as _devolver
    _devolver("rot", _S)
except Exception:  # noqa: BLE001
    pass
