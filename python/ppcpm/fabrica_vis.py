"""
PREPARAÇÃO FÁBRICA · VISUALIZADOR DXF — dentro da aba do sistema.
A análise da peça (furos, oblongos, rebaixos, medidas), a leitura das unidades e as regras de criar/mover para as
pastas de fluxo são as do app original (apps/Visualizador_DXF/visualizador/aba.py): os métodos de cálculo da tela
original são usados aqui sem alteração (emprestados da classe AbaVisualizador, sem abrir janela Qt). O desenho é
feito no navegador, com as mesmas cores por tipo de entidade.
"""
from __future__ import annotations

import json
import os
import shutil


from . import fabrica, fabrica_apps as FA

PASTA = "Visualizador_DXF"
MODS = ["visualizador.aba"]
ARQ_PREF = fabrica.PASTA_DADOS_PRODUCAO / "visualizador_dxf.json"
TIPOS = ["Fluxo 1", "Fluxo 2", "Fluxo 3", "Fluxo 4", "Acessórios Padrão", "Perfiladeira U E C", "Perfiladeira L",
         "Joist", "Terça Z"]
ATALHOS_PADRAO = {"next_file": "Right", "prev_file": "Left", "reset_zoom": "0", "fit_view": "A",
                  "load_folder": "Tab", "discard_files": "D"}
_S = {"folder_path": "", "root_path": "", "dxf_files": [], "current_index": 0}
_V = {"cls": None}


def _calc():
    """Objeto com os métodos de cálculo da tela original (sem criar QWidget)."""
    if _V["cls"] is None:
        aba = FA.carregar(PASTA, MODS)["visualizador.aba"].AbaVisualizador
        nomes = ["_get_dxf_units", "_safe_convert", "_bulge_to_arc", "_bulge_arc_points", "_collect_arcs_and_lines",
                 "_arc_span", "_arc_endpoints", "_points_close", "_detect_oblong_holes", "_analyze_piece",
                 "_calculate_polygon_area", "extract_folder_structure", "is_fluxo_folder",
                 "extract_thickness_from_folder_name", "_calculate_normalization"]
        _V["cls"] = type("CalculoVisualizador", (), {n: getattr(aba, n) for n in nomes})
    c = _V["cls"]()
    c.drawing_units = 1.0
    c.base_scale = 10
    return c


def _pref() -> dict:
    try:
        return json.loads(ARQ_PREF.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _salvar_pref(**k):
    p = _pref()
    p.update(k)
    try:
        ARQ_PREF.parent.mkdir(parents=True, exist_ok=True)
        ARQ_PREF.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _arquivos():
    fp = _S["folder_path"]
    if not fp or not os.path.isdir(fp):
        return []
    return sorted(f for f in os.listdir(fp) if f.lower().endswith(".dxf") and os.path.isfile(os.path.join(fp, f)))


def _base():
    c = _calc()
    fp = _S["folder_path"]
    return os.path.dirname(fp) if c.is_fluxo_folder(fp) else fp


def _pastas_mover():
    fp = _S["folder_path"]
    if not fp or not os.path.exists(fp):
        return {}
    try:
        base = _base()
        existentes = [i for i in os.listdir(base) if os.path.isdir(os.path.join(base, i))]
    except OSError:
        return {}
    return {t: next((f for f in existentes if f.startswith(t)), None) for t in TIPOS}


def estado() -> dict:
    p = _pref()
    return FA.limpo({"ok": True, "folder_path": _S["folder_path"], "root_path": _S["root_path"],
                     "total": len(_S["dxf_files"]), "indice": _S["current_index"],
                     "arquivo": _S["dxf_files"][_S["current_index"]] if _S["dxf_files"] else "",
                     "mover": _pastas_mover(), "tipos": TIPOS, "auto_fit": p.get("auto_fit", True),
                     "atalhos": {**ATALHOS_PADRAO, **(p.get("shortcuts") or {})}, "ultima": p.get("last_folder", "")})


def carregar(caminho: str, raiz: bool = True) -> dict:
    c = FA.pasta_ok(caminho)
    if not c:
        return {"ok": False, "titulo": "Aviso", "erro": f"Não encontrei essa pasta:\n\n{(caminho or '').strip()}"}
    _S["folder_path"] = c
    if raiz:
        _S["root_path"] = c
    _salvar_pref(last_folder=c)
    _S["dxf_files"] = _arquivos()
    _S["current_index"] = 0
    r = estado()
    r["vazia"] = not _S["dxf_files"]
    return r


def ir(indice: int) -> dict:
    if 0 <= indice < len(_S["dxf_files"]):
        _S["current_index"] = indice
    return estado()


def descartar() -> dict:
    _S["dxf_files"] = []
    _S["current_index"] = 0
    return estado()


def peca() -> dict:
    """Geometria + análise do arquivo atual (mesmas regras da tela original)."""
    if not _S["dxf_files"]:
        return {"ok": True, "vazio": True}
    import ezdxf
    import numpy as np
    nome = _S["dxf_files"][_S["current_index"]]
    cam = os.path.join(_S["folder_path"], nome)
    c = _calc()
    try:
        f1, f2 = c.extract_folder_structure(cam)
        doc = ezdxf.readfile(cam)
        c.drawing_units = c._get_dxf_units(doc)
        info = c._analyze_piece(doc)
        scale, centro = c._calculate_normalization(doc)
        sc = c._safe_convert
        g = {"linhas": [], "circulos": [], "arcos": [], "polis": []}
        for e in doc.modelspace():
            try:
                t = e.dxftype()
                if t == "LINE":
                    g["linhas"].append([sc(e.dxf.start[0]), sc(e.dxf.start[1]), sc(e.dxf.end[0]), sc(e.dxf.end[1])])
                elif t == "CIRCLE":
                    g["circulos"].append([sc(e.dxf.center[0]), sc(e.dxf.center[1]), sc(e.dxf.radius)])
                elif t == "ARC":
                    cx, cy, r = sc(e.dxf.center[0]), sc(e.dxf.center[1]), sc(e.dxf.radius)
                    sa, ea = sc(e.dxf.start_angle) % 360, sc(e.dxf.end_angle) % 360
                    if ea < sa:
                        ea += 360
                    ang = np.linspace(np.radians(sa), np.radians(ea), 30)
                    g["arcos"].append([[float(cx + r * np.cos(a)), float(cy + r * np.sin(a))] for a in ang])
                elif t in ("LWPOLYLINE", "POLYLINE"):
                    if t == "LWPOLYLINE":
                        raw = [(sc(p[0]), sc(p[1]), sc(p[2])) for p in e.get_points("xyb")]
                        fechado = e.closed
                    else:
                        raw = [(sc(v.dxf.location[0]), sc(v.dxf.location[1]), sc(getattr(v.dxf, "bulge", 0.0)))
                               for v in e.vertices]
                        fechado = getattr(e, "is_closed", False)
                    n = len(raw)
                    if n >= 2:
                        full = [(raw[0][0], raw[0][1])]
                        for i in range(n if fechado else n - 1):
                            x1, y1, b = raw[i]
                            x2, y2, _ = raw[(i + 1) % n]
                            if abs(b) > 1e-9:
                                full.extend(c._bulge_arc_points((x1, y1), (x2, y2), b, 24)[1:])
                            else:
                                full.append((x2, y2))
                        g["polis"].append([[float(x), float(y)] for x, y in full])
            except Exception:  # noqa: BLE001
                pass
        mx = (0.9 * c.base_scale / scale) if scale else 1.0          # meia-janela do zoom 100% (mesma conta do app)
        return FA.limpo({"ok": True, "nome": nome, "pastas": [f1, f2], "info": info, "geo": g,
                         "centro": [float(centro[0]), float(centro[1])], "meia": float(mx) / 0.9,
                         "indice": _S["current_index"], "total": len(_S["dxf_files"])})
    except Exception as ex:  # noqa: BLE001
        return {"ok": True, "erro_arquivo": f"Erro ao processar arquivo:\n{nome}\n\n{ex}", "nome": nome,
                "indice": _S["current_index"], "total": len(_S["dxf_files"])}


def criar_pasta(tipo: str, confirmado: bool) -> dict:
    if tipo not in TIPOS:
        return {"ok": False, "erro": "Tipo desconhecido."}
    if not _S["folder_path"]:
        return {"ok": False, "titulo": "Aviso", "erro": "Nenhuma pasta carregada!"}
    c = _calc()
    try:
        fp = _S["folder_path"]
        if c.is_fluxo_folder(fp):
            base = os.path.dirname(fp)
            esp = c.extract_thickness_from_folder_name(os.path.basename(base))
        else:
            base = fp
            esp = c.extract_thickness_from_folder_name(os.path.basename(fp))
        existentes = [i for i in os.listdir(base) if os.path.isdir(os.path.join(base, i)) and i.startswith(tipo)]
        if existentes and not confirmado:
            return {"ok": True, "perguntar": True, "titulo": "Pastas Existentes",
                    "texto": f'Já existem pastas do tipo "{tipo}":\n\n' + "\n".join(existentes) +
                             "\n\nDeseja criar uma nova mesmo assim?"}
        nome = f"{tipo} [{esp}]" if esp else tipo
        novo = os.path.join(base, nome)
        if os.path.exists(novo):
            return {**estado(), "status": f"Pasta '{nome}' já existe."}
        os.makedirs(novo, exist_ok=True)
        return {**estado(), "status": f"✔ Pasta '{nome}' criada com sucesso!"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "titulo": "Erro", "erro": f"Erro ao criar pasta:\n{e}"}


def mover(tipo: str, passo: str) -> dict:
    """passo: '' = verificar; 'substituir' = já confirmou que pode substituir; 'ok' = confirmou o movimento."""
    if not _S["dxf_files"] or _S["current_index"] >= len(_S["dxf_files"]):
        return {"ok": False, "titulo": "Aviso", "erro": "Nenhum arquivo para mover!"}
    try:
        nome = _S["dxf_files"][_S["current_index"]]
        origem = os.path.join(_S["folder_path"], nome)
        if not os.path.exists(origem):
            return {"ok": False, "titulo": "Erro", "erro": f"Arquivo não encontrado: {nome}"}
        base = _base()
        alvo = next((i for i in os.listdir(base) if os.path.isdir(os.path.join(base, i)) and i.startswith(tipo)), None)
        if not alvo:
            return {"ok": False, "titulo": "Erro", "erro": f"Pasta '{tipo}' não encontrada!"}
        destino = os.path.join(base, alvo, nome)
        if passo == "":
            if os.path.exists(destino):
                return {"ok": True, "perguntar": "substituir", "titulo": "Arquivo Existente",
                        "texto": f'"{nome}" já existe em "{alvo}". Substituir?'}
            passo = "substituir"
        if passo == "substituir":
            return {"ok": True, "perguntar": "ok", "titulo": "Confirmar Movimento", "texto": f'Mover "{nome}" para "{alvo}"?'}
        shutil.move(origem, destino)
        _S["dxf_files"] = _arquivos()
        if _S["current_index"] >= len(_S["dxf_files"]):
            _S["current_index"] = max(0, len(_S["dxf_files"]) - 1)
        return {**estado(), "status": f"✔ '{nome}' movido para '{alvo}'"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "titulo": "Erro", "erro": f"Erro ao mover arquivo:\n{e}"}


def arvore() -> dict:
    raiz = _S["root_path"]
    if not raiz or not os.path.isdir(raiz):
        return {"ok": False, "titulo": "Aviso", "erro": "Nenhuma pasta carregada!\nUse 'Carregar Pasta' primeiro."}
    atual = os.path.normpath(_S["folder_path"] or raiz)
    vistos = [0]

    def conta(p):
        try:
            return sum(1 for f in os.listdir(p) if os.path.isfile(os.path.join(p, f)) and f.lower().endswith(".dxf"))
        except OSError:
            return 0

    def filhos(p, prof):
        try:
            nomes = sorted((e for e in os.listdir(p) if os.path.isdir(os.path.join(p, e))), key=str.lower)
        except OSError:
            return []
        saida = []
        for n in nomes:
            vistos[0] += 1
            if vistos[0] > 3000 or prof > 12:
                break
            cam = os.path.join(p, n)
            saida.append({"nome": n, "caminho": cam, "dxf": conta(cam), "atual": os.path.normpath(cam) == atual,
                          "filhos": filhos(cam, prof + 1)})
        return saida

    return {"ok": True, "raiz": {"nome": os.path.basename(raiz) or raiz, "caminho": raiz, "dxf": conta(raiz),
                                 "atual": os.path.normpath(raiz) == atual, "filhos": filhos(raiz, 0)}}


def get(acao: str, q: dict) -> dict:
    if acao == "disponivel":
        return FA.disponivel("pg16", PASTA, MODS)
    if acao == "estado":
        return estado()
    if acao == "peca":
        return peca()
    if acao == "arvore":
        return arvore()
    return {"ok": False, "erro": "Ação desconhecida."}


def post(acao: str, d: dict) -> dict:
    if acao == "carregar":
        return carregar(str(d.get("caminho") or ""), bool(d.get("raiz", True)))
    if acao == "ir":
        try:
            return ir(int(d.get("indice") or 0))
        except (TypeError, ValueError):
            return estado()
    if acao == "descartar":
        return descartar()
    if acao == "criar_pasta":
        return criar_pasta(str(d.get("tipo") or ""), bool(d.get("confirmado")))
    if acao == "mover":
        return mover(str(d.get("tipo") or ""), str(d.get("passo") or ""))
    if acao == "abrir_pasta":
        if _S["folder_path"] and os.path.exists(_S["folder_path"]):
            return fabrica.abrir_pasta_caminho(_S["folder_path"])
        return {"ok": False, "titulo": "Aviso", "erro": "Nenhuma pasta válida para abrir!"}
    if acao == "pref":
        k = {}
        if "auto_fit" in d:
            k["auto_fit"] = bool(d["auto_fit"])
        if isinstance(d.get("shortcuts"), dict):
            k["shortcuts"] = {a: str(b) for a, b in d["shortcuts"].items() if a in ATALHOS_PADRAO}
        _salvar_pref(**k)
        return estado()
    return {"ok": False, "erro": "Ação desconhecida."}


# V287: devolve o trabalho que estava aberto antes do sistema reiniciar com a versão nova
try:
    from .sessao import devolver_fabrica as _devolver
    _devolver("vis", _S)
except Exception:  # noqa: BLE001
    pass
