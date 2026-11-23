# -*- coding: utf-8 -*-
"""
Renderizador de preview de geometria DXF, genérico e reaproveitável.

Hoje usado pela aba Espelhar (antes/depois lado a lado). Fica em dxf_util/
(fora da pasta de qualquer ferramenta específica) de propósito: qualquer
ferramenta futura que precise desenhar um preview de DXF numa
QGraphicsScene pode importar daqui em vez de reimplementar.

IMPORTANTE: extrair_preview_dxf() precisa ser chamada ANTES de qualquer
mirror/mutação nas entidades. list(msp) só guarda REFERÊNCIAS aos objetos
ezdxf, não cópias — se algo mutar os atributos das entidades "no lugar"
depois (como o mirror do módulo espelhar faz), uma lista de referências
tirada antes passaria a refletir o estado JÁ mutado assim que a mutação
acontecesse. Por isso aqui a gente extrai números puros (x, y) na hora,
independentes dos objetos ezdxf, pra guardar um retrato real do momento.
"""
from ezdxf import path as ezpath
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from PyQt5.QtGui import QColor, QPen, QPainterPath

# Cor padrão do traço: precisa contrastar com o fundo da QGraphicsView de
# quem usa este módulo (hoje: Espelhar DXF). Ajustada pra "#2B2823" (grafite
# escuro) junto da troca geral pra paleta clara "Papel & Grafite" -- o valor
# antigo ("#E6EDF3", quase branco) foi feito pra um fundo escuro e ficaria
# invisível no fundo claro novo. Mantido como constante própria (não importa
# nucleo.estilo) de propósito -- este módulo é genérico/reaproveitável fora
# de qualquer ferramenta específica, então tem seu próprio default simples.
COR_TRACO_PADRAO = "#000000"
COR_FURO_PADRAO = (255, 80, 80)


def extrair_preview_dxf(entidades, sagitta=2.0):
    """Tira um retrato (dados puros: listas de pontos e furos) da geometria
    ATUAL das entidades. Usa ezdxf.path.make_path()+.flattening() de forma
    genérica — funciona pra LINE, ARC, CIRCLE, LWPOLYLINE/POLYLINE com
    bulge, ELLIPSE e SPLINE, sem precisar de matemática separada por tipo."""
    linhas = []   # cada item: lista de (x, y) de um traço contínuo
    furos  = []   # cada item: (cx, cy, r)

    for e in entidades:
        tipo = e.dxftype()
        if tipo == 'CIRCLE':
            c = e.dxf.center
            furos.append((c.x, c.y, e.dxf.radius))
            continue

        try:
            p = ezpath.make_path(e)
            pontos = list(p.flattening(sagitta))
        except Exception:
            continue
        if len(pontos) < 2:
            continue
        linhas.append([(pt.x, pt.y) for pt in pontos])

    return {'linhas': linhas, 'furos': furos}


def desenhar_preview_dxf(scene, preview, cor_traco=None, cor_furo=None):
    """Desenha um retrato já extraído (dict de extrair_preview_dxf) numa
    QGraphicsScene. Nota: o eixo Y do Qt cresce pra baixo, então invertemos
    Y de cada ponto (x, -y) pra a peça aparecer com a orientação correta."""
    if cor_traco is None:
        cor_traco = QColor(COR_TRACO_PADRAO)
    if cor_furo is None:
        cor_furo = QColor(*COR_FURO_PADRAO)

    for cx, cy, r in preview['furos']:
        item = QGraphicsEllipseItem(cx - r, -cy - r, r * 2, r * 2)
        pen = QPen(cor_furo)
        pen.setWidth(0)  # pen cosmética: sempre 1px na tela, não escala com zoom
        item.setPen(pen)
        scene.addItem(item)

    caminho = QPainterPath()
    tem_ponto = False
    for pontos in preview['linhas']:
        caminho.moveTo(pontos[0][0], -pontos[0][1])
        for x, y in pontos[1:]:
            caminho.lineTo(x, -y)
        tem_ponto = True

    if tem_ponto:
        item_caminho = QGraphicsPathItem(caminho)
        pen = QPen(cor_traco)
        pen.setWidth(0)
        item_caminho.setPen(pen)
        scene.addItem(item_caminho)
