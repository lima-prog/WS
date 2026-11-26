"""
PREPARAÇÃO FÁBRICA · RENOMEAR DXF (Tekla/Tecno) — dentro da aba do sistema.
Lógica do app original (apps/Renomear_DXF/renomear_dxf/processador.py e utilitarios.py), sem alteração;
aqui só fica o papel da tela (pastas, análise, seleção e renomear).
"""
from __future__ import annotations

import os

from . import fabrica_apps as FA

PASTA = "Renomear_DXF"
MODS = ["renomear_dxf.utilitarios", "renomear_dxf.processador"]
_S = {"pasta_cam": "", "pasta_dxf": "", "obra": "", "liberacao": "", "linhas": [], "status": "", "analisado": False}

STATUS = {
    "ok": "✅ Pronto pra renomear", "sem_cam": "❌ Sem .CAM correspondente", "sem_quantidade": "⚠ CAM sem QTA_PEZ",
    "renomeado": "✅ Renomeado", "erro_renomear": "❌ Erro ao renomear",
}


def _m():
    return FA.carregar(PASTA, MODS)


def estado() -> dict:
    linhas = [{**{k: v for k, v in l.items() if k != "caminho_atual"}, "i": i, "status_txt": STATUS.get(l["status"], l["status"])}
              for i, l in enumerate(_S["linhas"])]
    return FA.limpo({"ok": True, "pasta_cam": _S["pasta_cam"], "pasta_dxf": _S["pasta_dxf"], "obra": _S["obra"],
                     "liberacao": _S["liberacao"], "linhas": linhas, "status": _S["status"] or
                     "Selecione a pasta CAM e a pasta DXF/DWG pra começar.", "analisado": _S["analisado"]})


def pasta_cam(caminho: str) -> dict:
    c = FA.pasta_ok(caminho)
    if not c:
        return {"ok": False, "titulo": "Pasta não encontrada", "erro": f"Não encontrei essa pasta:\n\n{(caminho or '').strip()}"}
    obra, lib = _m()["renomear_dxf.utilitarios"].derivar_obra_trecho(c)
    _S.update(pasta_cam=c, obra=obra, liberacao=lib)
    return estado()


def pasta_dxf(caminho: str) -> dict:
    c = FA.pasta_ok(caminho)
    if not c:
        return {"ok": False, "titulo": "Pasta não encontrada", "erro": f"Não encontrei essa pasta:\n\n{(caminho or '').strip()}"}
    _S["pasta_dxf"] = c
    return estado()


def analisar(obra_manual: str) -> dict:
    if not _S["pasta_cam"] or not _S["pasta_dxf"]:
        return {"ok": False, "erro": "Selecione a pasta CAM e a pasta DXF/DWG pra começar."}
    m = _m()
    obra_manual = (obra_manual or "").strip()
    linhas, obra_auto, lib, avisos = m["renomear_dxf.processador"].analisar(_S["pasta_cam"], _S["pasta_dxf"])
    obra = obra_manual or obra_auto
    if obra != obra_auto:
        for l in linhas:
            if l["status"] == "ok":
                ext = os.path.splitext(l["arquivo_atual"])[1]
                l["nome_final"] = m["renomear_dxf.utilitarios"].nome_renomeado(l["posicao"], obra, l["quantidade"], ext)
    _S.update(linhas=linhas, obra=obra, liberacao=lib, analisado=True)
    prontos = sum(1 for l in linhas if l["status"] == "ok")
    t = f"{len(linhas)} arquivo(s) encontrado(s) | {prontos} pronto(s) pra renomear"
    if avisos:
        t += " | " + " | ".join(avisos)
    _S["status"] = t
    return estado()


def renomear(indices: list) -> dict:
    sel = []
    for i in indices or []:
        try:
            l = _S["linhas"][int(i)]
        except (ValueError, IndexError):
            continue
        if l["status"] == "ok":
            sel.append(l)
    if not sel:
        return {**estado(), "ok": False, "titulo": "Atenção",
                "erro": "Selecione pelo menos um arquivo com status \"✅ Pronto pra renomear\"."}
    resultados = _m()["renomear_dxf.processador"].renomear(sel)
    ok, erros = 0, []
    for r in resultados:
        l = r["linha"]
        if r["sucesso"]:
            ok += 1
            l["status"] = "renomeado"
            l["caminho_atual"] = r["novo_caminho"]
            l["arquivo_atual"] = os.path.basename(r["novo_caminho"])
        else:
            l["status"] = "erro_renomear"
            l["erro_renomear_msg"] = r["erro"]
            erros.append(f"{l['arquivo_atual']}: {r['erro']}")
    t = f"{ok} arquivo(s) renomeado(s) com sucesso."
    if erros:
        t += f" | {len(erros)} erro(s)."
    _S["status"] = t
    return {**estado(), "erros": erros}


def get(acao: str, q: dict) -> dict:
    if acao == "disponivel":
        return FA.disponivel("pg19", PASTA, MODS)
    if acao == "estado":
        return estado()
    return {"ok": False, "erro": "Ação desconhecida."}


def post(acao: str, d: dict) -> dict:
    if acao == "pasta_cam":
        return pasta_cam(str(d.get("caminho") or ""))
    if acao == "pasta_dxf":
        return pasta_dxf(str(d.get("caminho") or ""))
    if acao == "analisar":
        return analisar(str(d.get("obra") or ""))
    if acao == "renomear":
        return renomear(d.get("indices") or [])
    return {"ok": False, "erro": "Ação desconhecida."}


# V287: devolve o trabalho que estava aberto antes do sistema reiniciar com a versão nova
try:
    from .sessao import devolver_fabrica as _devolver
    _devolver("ren", _S)
except Exception:  # noqa: BLE001
    pass
