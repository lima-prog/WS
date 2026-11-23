"""
PREPARAÇÃO FÁBRICA · CRIAR PASTA / AUDITORIA — dentro da aba do sistema.
Lógica do app original (apps/Criar_Pasta_Auditoria/auditoria/processador.py, banco.py e utilitarios.py), sem
alteração. Configurações (planilha, destino, diretórios raiz) e a base de busca ficam no mesmo banco do app
(pcp_projeart.db, tabelas auditoria_*).
"""
from __future__ import annotations

import os

from . import fabrica_apps as FA

PASTA = "Criar_Pasta_Auditoria"
MODS = ["auditoria.banco", "auditoria.utilitarios", "auditoria.processador"]
_S = {"auditoria": None, "versao_vista": False}


def _m():
    m = FA.carregar(PASTA, MODS)
    if not m.get("_iniciado"):
        m["auditoria.banco"].inicializar_banco()
        m["_iniciado"] = True
    return m


def _b():
    return _m()["auditoria.banco"]


def _u():
    return _m()["auditoria.utilitarios"]


def _p():
    return _m()["auditoria.processador"]


# ------------------------------------------------------------------ configurações
def _raizes_info():
    u = _u()
    saida = []
    for c in _b().listar_raizes():
        p9 = u.obter_pasta_9999(c)
        if not os.path.isdir(c):
            st = ("🚫 pasta não encontrada", "er")
        elif os.path.isdir(p9):
            st = ("✅ LOTE 9999 encontrada", "ok")
        else:
            st = ("⚠️  sem LOTE 9999", "av")
        saida.append({"caminho": c, "status": st[0], "tipo": st[1]})
    return saida


def config() -> dict:
    b, u = _b(), _u()
    pl = b.carregar_config("caminho_planilha")
    xlsx = u.encontrar_arquivo_xlsx(pl) if pl else None
    previa = ""
    if pl:
        previa = (f"📄 Planilha encontrada: {os.path.basename(xlsx)}" if xlsx
                  else "⚠️  Nenhum arquivo .xlsx encontrado nesta pasta")
    r = {"ok": True, "planilha": pl, "destino": b.carregar_config("caminho_destino"), "previa": previa,
         "raizes": _raizes_info(), "versao": _p().VERSAO_ATUAL}
    if not _S["versao_vista"]:
        _S["versao_vista"] = True
        try:
            info = _p().verificar_nova_versao()
            r["nova_versao"] = bool(info.get("tem_nova"))
        except Exception:  # noqa: BLE001
            pass
    return FA.limpo(r)


def salvar_config(chave: str, valor: str) -> dict:
    if chave not in ("caminho_planilha", "caminho_destino"):
        return {"ok": False, "erro": "Configuração desconhecida."}
    b = _b()
    b.salvar_config(chave, (valor or "").strip().strip('"'))
    if chave == "caminho_destino" and valor and not b.listar_raizes():
        b.adicionar_raiz(os.path.dirname((valor or "").strip().strip('"')))
    return config()


def raiz(acao: str, caminho: str) -> dict:
    b = _b()
    caminho = (caminho or "").strip().strip('"')
    if acao == "adicionar":
        if not caminho:
            return {"ok": False, "erro": "Escolha um diretório raiz."}
        if not b.adicionar_raiz(caminho):
            r = config()
            r["aviso"] = {"titulo": "Já cadastrada", "texto": "Esse diretório já está na lista de raízes."}
            return r
    else:
        b.remover_raiz(caminho)
    return config()


def atualizar_base() -> dict:
    b, u = _b(), _u()
    caminho = b.carregar_config("caminho_planilha")
    if not caminho:
        return {"ok": False, "titulo": "Configuração incompleta", "ir_config": True,
                "erro": "Defina a Planilha na tela de Configurações antes de atualizar a base."}
    xlsx = u.encontrar_arquivo_xlsx(caminho)
    if not xlsx:
        return {"ok": False, "titulo": "Erro", "erro": f"Nenhum arquivo .xlsx encontrado em:\n{caminho}"}
    r = _p().importar_planilha_busca(xlsx)
    return {"ok": bool(r.get("ok")), "titulo": "Base atualizada" if r.get("ok") else "Erro", "msg": r.get("msg", ""),
            "erro": "" if r.get("ok") else r.get("msg", "")}


# ------------------------------------------------------------------ criar pastas
def criar(lote: str) -> dict:
    b = _b()
    diretorio = b.carregar_config("caminho_planilha")
    destino = b.carregar_config("caminho_destino")
    lote = (lote or "").strip()
    if not diretorio or not destino:
        return {"ok": False, "titulo": "Configuração incompleta", "ir_config": True,
                "erro": "Defina a Planilha e o Destino na tela de Configurações antes de continuar."}
    if not lote:
        return {"ok": False, "titulo": "Campo obrigatório", "erro": "Informe o número do LOTE."}
    r = _p().processar(diretorio, lote, destino, b.listar_raizes())
    if not r.get("ok"):
        return {"ok": False, "titulo": "Erro", "erro": r.get("msg", ""), "resultado_erro": True}
    return FA.limpo({"ok": True, "lote": lote, **r})


# ------------------------------------------------------------------ auditoria
def auditar() -> dict:
    b = _b()
    diretorio = b.carregar_config("caminho_planilha")
    raizes = b.listar_raizes()
    if not diretorio or not raizes:
        return {"ok": False, "titulo": "Configuração incompleta", "ir_config": True,
                "erro": "Defina a Planilha e cadastre ao menos um Diretório raiz na tela de Configurações antes de auditar."}
    r = _p().auditar_lote_9999(diretorio, raizes)
    if not r.get("ok"):
        return {"ok": False, "titulo": "Erro na auditoria", "erro": r.get("msg", "")}
    _S["auditoria"] = r
    return FA.limpo({**r, "nome_9999": _u().NOME_PASTA_9999})


def preparar_mover_auto(caminho_atual: str, lote_destino: str) -> dict:
    b, u = _b(), _u()
    if not caminho_atual or not os.path.isdir(caminho_atual):
        return {"ok": False, "titulo": "Pasta não encontrada",
                "erro": "A pasta de origem não foi encontrada no disco — talvez já tenha sido movida ou renomeada. "
                        "Rode a auditoria de novo pra atualizar a lista."}
    if not lote_destino:
        return {"ok": False, "titulo": "Sem lote de destino",
                "erro": "Esta linha não tem um lote de destino conhecido — use \"Mover para...\"."}
    pasta_destino = u.localizar_pasta_lote_existente(b.listar_raizes(), lote_destino)
    vai_criar = False
    if not pasta_destino:
        padrao = b.carregar_config("caminho_destino")
        if not padrao or not os.path.isdir(padrao):
            return {"ok": False, "titulo": "Pasta do lote não encontrada",
                    "erro": f"Não encontrei nenhuma pasta \"LOTE {lote_destino}\" nas raízes cadastradas, e o Destino "
                            "(pasta do mês) não está configurado pra criar uma nova ali.\n\nConfigure o Destino em "
                            "Configurações, ou use \"Mover para...\" pra escolher o lugar na mão."}
        pasta_destino = os.path.join(padrao, f"LOTE {str(lote_destino).strip()}")
        vai_criar = True
    return {"ok": True, "destino": pasta_destino, "vai_criar": vai_criar}


def mover(origem: str, destino: str) -> dict:
    if not origem or not os.path.isdir(origem):
        return {"ok": False, "titulo": "Pasta não encontrada",
                "erro": "A pasta de origem não foi encontrada no disco — talvez já tenha sido movida ou renomeada. "
                        "Rode a auditoria de novo pra atualizar a lista."}
    r = _p().mover_pasta_of(origem, destino)
    if not r.get("ok"):
        return {"ok": False, "titulo": "Não foi possível mover", "erro": r.get("msg", "")}
    return {"ok": True, "msg": r.get("msg", "")}


# ------------------------------------------------------------------ buscar
def _linha(reg):
    u = _u()
    return {"lote": reg["lote"], "of_trecho": reg["of_trecho"], "obra": reg["obra"], "trecho": reg["trecho"],
            "subtrecho": reg["subtrecho"], "ano_semana": reg["ano_semana"],
            "peso_lic": reg["peso_lic_lote"] or u.PLACEHOLDER_SEM_PESO, "prep": reg["qtd_tt_kg_prep"],
            "nprep": reg["qtd_tt_kg_nprep"], "prep_txt": u.formatar_kg(reg["qtd_tt_kg_prep"]),
            "nprep_txt": u.formatar_kg(reg["qtd_tt_kg_nprep"]), "data_inicio": reg["data_inicio_artia"],
            "status": reg["status"] or u.PLACEHOLDER_SEM_PESO}


def _vazio(msg):
    if _b().contar_registros_busca() == 0:
        return {"ok": True, "linhas": [], "vazia": True,
                "info": "⚠ Base de busca vazia — clique em \"🔄 Atualizar Base de Busca\" em Configurações.",
                "aviso": {"titulo": "Base de busca vazia",
                          "texto": "A base de busca ainda não foi carregada nesta sessão.\n\nVá em Configurações e clique em "
                                   "\"🔄 Atualizar Base de Busca\" antes de pesquisar.", "tipo": "aviso"}}
    return {"ok": True, "linhas": [], "info": "Nenhum registro encontrado.",
            "aviso": {"titulo": "Nada encontrado", "texto": msg, "tipo": "info"}}


def _com_total(regs, info):
    u = _u()
    tp = sum(r["qtd_tt_kg_prep"] or 0 for r in regs)
    tn = sum(r["qtd_tt_kg_nprep"] or 0 for r in regs)
    return FA.limpo({"ok": True, "linhas": [_linha(r) for r in regs], "info": info,
                     "total": {"prep_txt": u.formatar_kg(tp), "nprep_txt": u.formatar_kg(tn)}})


def buscar_obra(valor: str) -> dict:
    b, u = _b(), _u()
    valor = (valor or "").strip()
    if not valor:
        return {"ok": False, "titulo": "Atenção", "erro": "Informe a obra ou o código OF-TRECHO."}
    if "-" in valor:
        reg = b.buscar_por_of_trecho(valor)
        if not reg:
            return _vazio(f"Nenhum registro para o OF-TRECHO {valor}.")
        info = (f"Lote {reg['lote']}   ·   PREP: {u.formatar_kg(reg['qtd_tt_kg_prep'])}   ·   "
                f"ÑPREP: {u.formatar_kg(reg['qtd_tt_kg_nprep'])}")
        return _com_total([reg], info)
    regs = b.buscar_por_obra(valor)
    if not regs:
        return _vazio(f"Nenhum registro para a obra {valor}.")
    return _com_total(regs, _info_total(regs))


def _info_total(regs):
    u = _u()
    tp = sum(r["qtd_tt_kg_prep"] or 0 for r in regs)
    tn = sum(r["qtd_tt_kg_nprep"] or 0 for r in regs)
    return f"Registros: {len(regs)}   ·   PREP total: {u.formatar_kg(tp)}   ·   ÑPREP total: {u.formatar_kg(tn)}"


def buscar_pacote(lote: str) -> dict:
    lote = (lote or "").strip()
    if not lote:
        return {"ok": False, "titulo": "Atenção", "erro": "Informe o número do pacote/lote."}
    regs = _b().buscar_por_pacote(lote)
    if not regs:
        return _vazio(f"Nenhum registro para o pacote {lote}.")
    return _com_total(regs, _info_total(regs))


# ------------------------------------------------------------------ roteamento
def get(acao: str, q: dict) -> dict:
    if acao == "disponivel":
        return FA.disponivel("pg21", PASTA, MODS)
    if acao == "config":
        return config()
    return {"ok": False, "erro": "Ação desconhecida."}


def post(acao: str, d: dict) -> dict:
    if acao == "salvar_config":
        return salvar_config(str(d.get("chave") or ""), str(d.get("valor") or ""))
    if acao == "raiz":
        return raiz(str(d.get("acao") or "adicionar"), str(d.get("caminho") or ""))
    if acao == "atualizar_base":
        return atualizar_base()
    if acao == "criar":
        return criar(str(d.get("lote") or ""))
    if acao == "auditar":
        return auditar()
    if acao == "preparar_mover":
        return preparar_mover_auto(str(d.get("origem") or ""), str(d.get("lote") or ""))
    if acao == "mover":
        return mover(str(d.get("origem") or ""), str(d.get("destino") or ""))
    if acao == "buscar_obra":
        return buscar_obra(str(d.get("valor") or ""))
    if acao == "buscar_pacote":
        return buscar_pacote(str(d.get("valor") or ""))
    return {"ok": False, "erro": "Ação desconhecida."}
