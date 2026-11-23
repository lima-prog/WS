# -*- coding: utf-8 -*-
"""
Funções puras do conversor CAM → DXF (modo CORTE) — sem nenhuma dependência
de tela (nem Tkinter, nem PyQt5). Migradas quase sem alteração do script
original `conversor_cam_dxf_corte_v14.py`, que já mantinha essa parte
desacoplada da interface.

Cobrem: parsing do arquivo .CAM (seções [HEAD]/[SHAPE]/[OUTLINE]/[HOLE]/
[INLINE]/[MARK]), normalização do identificador da obra, formatação do
nome do DXF de saída, e desenho da geometria (contorno + rasgos) num
documento ezdxf.
"""
import os
import math
import ezdxf

# `normalizar_obra` foi movida para nucleo/normalizacao.py: passou a ser
# usada também pela ferramenta Renomear DXF (Tekla/Tecno), então virou
# infraestrutura compartilhada em vez de algo exclusivo do Conversor (regra
# de ouro da arquitetura: pasta de ferramenta nunca importa de outra —
# nucleo/ é o lugar certo pra regra usada por mais de uma). Reexportada
# aqui pelo nome de sempre pra não quebrar `from conversor.utilitarios
# import nome_dxf, normalizar_obra`, já usado por conversor/aba.py.
from nucleo.normalizacao import normalizar_obra  # noqa: F401


def num(v):
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def ler_cam(caminho):
    with open(caminho, "r", encoding="latin-1", errors="replace") as f:
        linhas = [x.strip() for x in f]

    secao = ""
    # [OUTLINE] e [INLINE] guardam BLOCOS de contorno fechados (cada
    # marcador "LIV1"/"LIV2"/... começa um bloco novo — inclusive quando
    # "LIV1" se repete várias vezes seguidas dentro da mesma seção, como
    # acontece quando a peça tem mais de um contorno/recorte). Cada bloco
    # é uma lista de registros (vértice reto ou arco) — ver
    # desenhar_bloco_contorno().
    blocos_outline, blocos_inline, rasgos = [], [], []
    shape_tipo = ""
    dados = {
        "posicao": "", "obra": "", "num_com": "", "quantidade": "", "marca": "",
        "comprimento": "", "largura": "",
        "espessura": "", "material": "",
        "tipo_cam": "DESCONHECIDO",
        "tem_recorte_interno": False,
        "arquivo": os.path.basename(caminho)
    }

    for linha in linhas:
        if not linha:
            continue

        if linha.startswith("[") and linha.endswith("]"):
            secao = linha
            continue

        if secao == "[SHAPE]" and not shape_tipo:
            partes_shape = linha.split()
            if partes_shape:
                codigo = partes_shape[0].upper()
                shape_tipo = codigo
                # "R" = chapa retangular plana, já pronta para corte.
                # Qualquer outro código (A, L, N, C, Z, T, U, etc.) é um
                # perfil / peça com dobra: o bloco [OUTLINE] desses CAMs
                # descreve a seção transversal bruta do perfil, não o
                # desenvolvido plano — por isso não deve ser convertido
                # no modo CORTE (ver conversão mais abaixo).
                dados["tipo_cam"] = "PLANIFICADO" if codigo == "R" else "DOBRADO"
            continue

        if secao == "[HEAD]" and ":" in linha:
            chave, valor = linha.split(":", 1)
            chave, valor = chave.strip(), valor.strip()

            if chave == "NUM_COM":
                # Guardado só como referência/última reserva: em produção
                # já apareceu NUM_COM truncado (ex.: "2000" em vez de
                # "2000-2-01"), então não é mais a fonte principal da
                # obra — ver o fallback por pasta no final da função.
                dados["num_com"] = valor
            elif chave == "POS_PEZ":
                dados["posicao"] = valor
            elif chave == "QTA_PEZ":
                dados["quantidade"] = valor
            elif chave == "LUN_PRO":
                dados["comprimento"] = valor
            elif chave == "LAR_PRO":
                dados["largura"] = valor
            elif chave == "SPE_PRO":
                dados["espessura"] = valor
            elif chave == "MAT_PRO":
                dados["material"] = valor

        elif secao == "[OUTLINE]":
            if linha.upper().startswith("LIV"):
                blocos_outline.append([])
                continue
            p = linha.split()
            # Cada linha de [OUTLINE]/[INLINE] é um VÉRTICE RETO (coluna
            # de raio, índice 3, igual a 0) ou um ARCO (raio > 0 — nesse
            # caso "x y" NÃO é um ponto do desenho, é o CENTRO do arco;
            # ang_inicio/ang_fim vêm nas duas colunas seguintes). Ver
            # desenhar_bloco_contorno() para a regra de desenho, validada
            # ponto a ponto contra um DXF de referência do TecnoMETAL.
            if len(p) >= 6 and all(num(v) for v in p[:6]) and blocos_outline:
                blocos_outline[-1].append({
                    "x": float(p[0]), "y": float(p[1]),
                    "raio": float(p[3]),
                    "ang_inicio": float(p[4]), "ang_fim": float(p[5]),
                })

        elif secao == "[HOLE]":
            if linha.upper().startswith("LIV"):
                continue
            p = linha.split()
            if len(p) >= 7 and p[0].upper() == "H":
                try:
                    rasgos.append({
                        "largura": float(p[1]),
                        "x": float(p[2]),
                        "y": float(p[3]),
                        "z": float(p[4]),
                        "reta": float(p[5]),
                        "angulo": float(p[6])
                    })
                except ValueError:
                    pass

        elif secao == "[INLINE]":
            if linha.upper().startswith("LIV"):
                # Um novo "LIV1" (mesmo repetido) sempre começa um bloco
                # de contorno novo — uma peça pode ter vários recortes
                # internos (e, num CAM tipo "R", até o contorno externo
                # da própria chapa aparece aqui como o primeiro bloco).
                blocos_inline.append([])
                continue
            p = linha.split()
            if len(p) >= 6 and all(num(v) for v in p[:6]) and blocos_inline:
                raio = float(p[3])
                blocos_inline[-1].append({
                    "x": float(p[0]), "y": float(p[1]),
                    "raio": raio,
                    "ang_inicio": float(p[4]), "ang_fim": float(p[5]),
                })
                if raio > 1e-6:
                    dados["tem_recorte_interno"] = True

        elif secao == "[MARK]":
            if linha.upper().startswith("LIV"):
                continue
            p = linha.split()
            if len(p) >= 5:
                # Usada somente no nome do DXF; nunca desenhada.
                dados["marca"] = p[-1]

    # A identificação da obra vem sempre do nome da pasta da obra, não
    # do NUM_COM do .cam. Estrutura real de produção:
    #   L:\<grupo>\...\<OBRA>\CAM\arquivo.cam
    # A pasta um nível acima de "CAM" tem o identificador completo da
    # obra (ex.: "2000-2-01_L1"). Já apareceu CAM real com NUM_COM
    # incompleto (ex.: "2000" em vez de "2000-2-01"), então o NUM_COM
    # só é usado se por algum motivo não der pra ler o nome da pasta.
    pasta_cam = os.path.dirname(os.path.abspath(caminho))
    pasta_obra = os.path.dirname(pasta_cam)
    nome_pasta_obra = os.path.basename(pasta_obra)
    dados["obra"] = nome_pasta_obra or dados["num_com"]

    return blocos_outline, rasgos, blocos_inline, dados


def limpar_nome_pasta(nome):
    nome = (nome or "SEM_MATERIAL").strip()
    for ch in '<>:"/\\|?*':
        nome = nome.replace(ch, "_")
    return nome or "SEM_MATERIAL"


def formatar_numero_pasta(valor):
    """
    Só para nomes de pasta de saída: formata a espessura sempre com
    2 casas decimais e vírgula como separador (padrão BR / padrão de
    espessuras da empresa). Ex.: "2.7" -> "2,70", "2" -> "2,00",
    "6.35" -> "6,35". Não afeta os números mostrados na tabela nem o
    nome do DXF.

    Se o valor não for um número válido, devolve o texto original sem
    alterar — assim um dado inesperado não é escondido/mascarado.
    """
    texto = (valor or "").strip()
    try:
        numero = float(texto.replace(",", "."))
    except ValueError:
        return texto

    return f"{numero:.2f}".replace(".", ",")


def nome_dxf(d):
    pos = d["posicao"] or "SEM_POSICAO"

    # A aba Conversor deixa o usuário sobrescrever manualmente a obra de
    # uma peça (botão "Editar Obra"), pra cobrir nomes de pasta fora de
    # qualquer padrão que normalizar_obra() consiga prever. Quando existe
    # esse valor manual (`obra_manual`, gravado direto no dicionário
    # `d` pela tela), ele tem prioridade total sobre o cálculo automático.
    obra_manual = (d.get("obra_manual") or "").strip()
    obra = obra_manual if obra_manual else normalizar_obra(d["obra"])

    qtd = d["quantidade"] or "1"

    nome = f"{pos} - OF{obra} - Q{qtd}.dxf"

    for ch in '<>:"/\\|?*':
        nome = nome.replace(ch, "_")

    return nome.strip()


def caminho_unico(caminho):
    """Se `caminho` já existir, acrescenta " (1)", " (2)", ... até achar um
    nome livre — evita sobrescrever DXF já convertido antes."""
    if not os.path.exists(caminho):
        return caminho

    pasta = os.path.dirname(caminho)
    base, ext = os.path.splitext(os.path.basename(caminho))
    contador = 1

    while True:
        novo = os.path.join(pasta, f"{base} ({contador}){ext}")
        if not os.path.exists(novo):
            return novo
        contador += 1


def desenhar_rasgo(msp, r):
    raio = r["largura"] / 2.0
    cx, cy = r["x"], r["y"]
    reta = r["reta"]

    # Furo circular (reta = 0): não é um rasgo alongado, é um furo
    # redondo comum. Antes isso era desenhado como 2 arcos formando o
    # círculo (e, em versão mais antiga, 2 linhas de comprimento zero
    # que causavam um traço indevido em alguns visualizadores). Agora
    # desenha como uma entidade CIRCLE de verdade: além de não ter a
    # linha degenerada, é o jeito padrão do DXF representar um furo
    # redondo, e qualquer programa que leia furos e calcule dimensão
    # (como a aba Relatório deste mesmo app) reconhece e mede pelo raio
    # diretamente, sem precisar inferir a partir de arcos/linhas.
    if reta <= 1e-6:
        msp.add_circle(
            center=(cx, cy), radius=raio,
            dxfattribs={"layer": "CORTE"}
        )
        return

    a = math.radians(r["angulo"])
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux

    x1, y1 = cx - ux * reta / 2, cy - uy * reta / 2
    x2, y2 = cx + ux * reta / 2, cy + uy * reta / 2

    p1a = (x1 + vx * raio, y1 + vy * raio)
    p1b = (x1 - vx * raio, y1 - vy * raio)
    p2a = (x2 + vx * raio, y2 + vy * raio)
    p2b = (x2 - vx * raio, y2 - vy * raio)

    msp.add_line(p1a, p2a, dxfattribs={"layer": "CORTE"})
    msp.add_line(p1b, p2b, dxfattribs={"layer": "CORTE"})

    direcao = math.degrees(math.atan2(uy, ux))

    msp.add_arc(
        center=(x1, y1), radius=raio,
        start_angle=direcao + 90,
        end_angle=direcao + 270,
        dxfattribs={"layer": "CORTE"}
    )
    msp.add_arc(
        center=(x2, y2), radius=raio,
        start_angle=direcao - 90,
        end_angle=direcao + 90,
        dxfattribs={"layer": "CORTE"}
    )


def desenhar_bloco_contorno(msp, registros):
    """
    Desenha um bloco de contorno fechado lido de [OUTLINE] ou [INLINE]
    (a mesma regra vale para os dois — quem manda é o conteúdo do
    registro, não a seção onde ele apareceu).

    Cada registro é um vértice reto (raio == 0) ou um ARCO (raio > 0 —
    nesse caso x,y é o CENTRO do arco, não um ponto do caminho). Regra,
    validada ponto a ponto contra um DXF de referência do TecnoMETAL:
      - dois vértices retos seguidos  -> uma reta (LINE) entre eles;
      - um registro com raio > 0      -> um ARC (centro/raio/ângulos
        direto do registro); nunca conta como ponto do caminho;
      - vértice reto vizinho de um arco -> nenhuma reta desenhada ali:
        a própria ponta do arco já encosta no vértice.
    O bloco é tratado como fechado (o último registro volta a se ligar
    ao primeiro); se o CAM já repetir o primeiro ponto no final, esse
    ponto duplicado é descartado antes de aplicar a regra acima.
    """
    registros = list(registros)
    if len(registros) > 1:
        r0, rn = registros[0], registros[-1]
        if (abs(r0["x"] - rn["x"]) < 1e-4 and abs(r0["y"] - rn["y"]) < 1e-4
                and r0["raio"] < 1e-6 and rn["raio"] < 1e-6):
            registros = registros[:-1]

    n = len(registros)
    if n < 2:
        return

    for i in range(n):
        atual = registros[i]
        seguinte = registros[(i + 1) % n]

        if atual["raio"] > 1e-6:
            msp.add_arc(
                center=(atual["x"], atual["y"]), radius=atual["raio"],
                start_angle=atual["ang_inicio"], end_angle=atual["ang_fim"],
                dxfattribs={"layer": "CORTE"}
            )
        elif (seguinte["raio"] <= 1e-6
              and (abs(atual["x"] - seguinte["x"]) > 1e-9
                   or abs(atual["y"] - seguinte["y"]) > 1e-9)):
            msp.add_line(
                (atual["x"], atual["y"]), (seguinte["x"], seguinte["y"]),
                dxfattribs={"layer": "CORTE"}
            )


def criar_dxf_corte(caminho_cam, caminho_dxf):
    blocos_outline, rasgos, blocos_inline, dados = ler_cam(caminho_cam)

    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = ezdxf.units.MM
    msp = doc.modelspace()
    doc.layers.add("CORTE")

    for bloco in blocos_outline:
        desenhar_bloco_contorno(msp, bloco)

    for rasgo in rasgos:
        desenhar_rasgo(msp, rasgo)

    for bloco in blocos_inline:
        desenhar_bloco_contorno(msp, bloco)

    doc.saveas(caminho_dxf)
    return dados
