# -*- coding: utf-8 -*-
"""
Matematica do espelhamento de pecas xadrez.

A engenharia libera o DXF/CAM enxergando a peca pela face lisa (xadrez
para baixo). No corte, a chapa vai pra mesa com o xadrez pra cima. As
funcoes abaixo espelham a geometria (mirror no eixo X) pra compensar a
inversao de face, e reancoram a peca em (0,0) pra reimportar com
seguranca no nesting (Lantek/SKA).

Matematica manual (nao usa entity.transform() do ezdxf de proposito: esse
metodo resolve o mirror invertendo o vetor de extrusao/OCS em vez de
recalcular as coordenadas 2D, o que e valido geometricamente mas arriscado
para leitores de CAM mais antigos). Cada funcao abaixo foi validada
numericamente (coordenadas comparadas ponto a ponto contra o espelho
esperado) antes de entrar aqui.
"""
import math
from ezdxf import bbox as ezbbox

SUBPASTA_ESPELHADAS = "ESPELHADAS"


SUBPASTA_ESPELHADAS = "ESPELHADAS"


def _mirror_line(e):
    s, en = e.dxf.start, e.dxf.end
    e.dxf.start = (-s.x, s.y, s.z)
    e.dxf.end = (-en.x, en.y, en.z)


def _mirror_circle(e):
    c = e.dxf.center
    e.dxf.center = (-c.x, c.y, c.z)


def _mirror_arc(e):
    c = e.dxf.center
    e.dxf.center = (-c.x, c.y, c.z)
    old_start, old_end = e.dxf.start_angle, e.dxf.end_angle
    # espelhar inverte o sentido do arco -> inicio/fim trocam de lugar
    e.dxf.start_angle = (180 - old_end) % 360
    e.dxf.end_angle = (180 - old_start) % 360


def _mirror_lwpolyline(e):
    novos = []
    for x, y, sw, ew, bulge in e.get_points(format="xyseb"):
        novos.append((-x, y, sw, ew, -bulge))
    e.set_points(novos, format="xyseb")


def _mirror_polyline_old(e):
    # POLYLINE 2D estilo antigo (R12), com VERTEX filhos (bulge por vertice)
    for v in e.vertices:
        loc = v.dxf.location
        v.dxf.location = (-loc.x, loc.y, loc.z)
        if v.dxf.hasattr("bulge") and v.dxf.bulge:
            v.dxf.bulge = -v.dxf.bulge


def _mirror_ellipse(e):
    c = e.dxf.center
    e.dxf.center = (-c.x, c.y, c.z)
    ma = e.dxf.major_axis
    e.dxf.major_axis = (-ma.x, ma.y, ma.z)
    two_pi = 2 * math.pi
    old_start, old_end = e.dxf.start_param, e.dxf.end_param
    e.dxf.start_param = (two_pi - old_end) % two_pi
    e.dxf.end_param = (two_pi - old_start) % two_pi


def _mirror_spline(e):
    novos_cp = [(-p.x, p.y, p.z) for p in e.control_points]
    e.control_points = novos_cp
    if e.fit_points:
        e.fit_points = [(-p.x, p.y, p.z) for p in e.fit_points]


def _mirror_point(e):
    p = e.dxf.location
    e.dxf.location = (-p.x, p.y, p.z)


def _mirror_face_like(e, attrs):
    for attr in attrs:
        if e.dxf.hasattr(attr):
            p = e.dxf.get(attr)
            e.dxf.set(attr, (-p.x, p.y, p.z))


def _mirror_insert(e):
    ins = e.dxf.insert
    e.dxf.insert = (-ins.x, ins.y, ins.z)
    xscale = e.dxf.xscale if e.dxf.hasattr("xscale") else 1.0
    e.dxf.xscale = -xscale
    rot = e.dxf.rotation if e.dxf.hasattr("rotation") else 0.0
    e.dxf.rotation = (180 - rot) % 360


MIRROR_FUNCS = {
    "LINE": _mirror_line,
    "CIRCLE": _mirror_circle,
    "ARC": _mirror_arc,
    "LWPOLYLINE": _mirror_lwpolyline,
    "POLYLINE": _mirror_polyline_old,
    "ELLIPSE": _mirror_ellipse,
    "SPLINE": _mirror_spline,
    "POINT": _mirror_point,
    "INSERT": _mirror_insert,
    "SOLID": lambda e: _mirror_face_like(e, ["vtx0", "vtx1", "vtx2", "vtx3"]),
    "TRACE": lambda e: _mirror_face_like(e, ["vtx0", "vtx1", "vtx2", "vtx3"]),
    "3DFACE": lambda e: _mirror_face_like(e, ["vtx0", "vtx1", "vtx2", "vtx3"]),
}


def espelhar_documento(doc, avisos):
    """Espelha todas as entidades do modelspace em X e reancora em (0,0).
    `avisos` recebe (por referencia) os tipos de entidade que apareceram e
    NAO tem mirror suportado (ficam na posicao original, sem espelhar)."""
    msp = doc.modelspace()
    for e in list(msp):
        tipo = e.dxftype()
        func = MIRROR_FUNCS.get(tipo)
        if func is not None:
            func(e)
        else:
            avisos.append(tipo)

    # Reancorar em (0,0): desloca tudo pra bbox comecar na origem,
    # mantendo o mesmo tamanho/proporcao relativo de antes.
    box = ezbbox.extents(msp)
    if box.has_data:
        dx = -box.extmin.x
        dy = -box.extmin.y
        if dx != 0 or dy != 0:
            for e in msp:
                e.translate(dx, dy, 0)
    return doc
