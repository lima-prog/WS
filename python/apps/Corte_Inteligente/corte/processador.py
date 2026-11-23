# -*- coding: utf-8 -*-
"""
Motor de processamento da aba Corte Inteligente: divide ordens de
fabricacao (pecas compridas) em partes cortaveis, respeitando tamanhos
padrao de barra e evitando cortar em cima de furos.

Sem nenhuma dependencia de PyQt5 diretamente -- so QEventLoop/QTimer pra
dar um respiro visual entre arquivos durante o processamento. Toda a
interacao com a tela acontece por callback (o parametro `visualizador`
precisa expor: atualizar_progresso, atualizar_status, adicionar_log,
mostrar_visualizacao, visualizacao_habilitada, velocidade_visualizacao --
e' exatamente o que corte/aba.py::AbaCorte implementa).
"""
import os
import ezdxf
from PyQt5.QtCore import QEventLoop, QTimer

from nucleo.logging_config import logger


class ProcessadorDXF:
    TAMANHOS_CORTE = [6000, 5590, 5500]
    MARGEM_FURO    = 30
    PARTE_MINIMA   = 500

    def __init__(self, visualizador, banco_dados):
        self.visualizador = visualizador
        self.banco_dados  = banco_dados

    # ── entrada ──────────────────────────────────────────────────────────────

    def processar_pasta(self, caminho_pasta):
        try:
            arquivos_dxf = [f for f in os.listdir(caminho_pasta) if f.lower().endswith('.dxf')]
            if not arquivos_dxf:
                raise ValueError("Nenhum arquivo DXF encontrado na pasta")

            total = len(arquivos_dxf)
            proc_id = self.banco_dados.registrar_processamento(caminho_pasta, total)

            for idx, nome in enumerate(arquivos_dxf, 1):
                self.visualizador.atualizar_progresso(idx, total)
                self.visualizador.atualizar_status(f"Processando {idx}/{total}: {nome}")
                try:
                    res = self._processar_arquivo(os.path.join(caminho_pasta, nome))
                    arq_id = self.banco_dados.registrar_arquivo(
                        proc_id, nome, res['estrategia'], res['eficiencia'], res['perda_mm'])
                    for p in res['partes_geradas']:
                        self.banco_dados.registrar_parte(arq_id, p['nome'], p['comprimento'], p['furos'])
                    for ev in res['eventos']:
                        self.banco_dados.registrar_evento(
                            proc_id, arq_id, nome, ev['tipo'], ev['detalhe'],
                            ev.get('posicao_x'), ev.get('comprimento_mm'))

                    if self.visualizador.visualizacao_habilitada():
                        self.visualizador.mostrar_visualizacao(
                            res['dimensoes_originais'], res['partes'], res['furos'],
                            nome, res['estrategia'], res['eficiencia'], res['perda_mm'])
                        loop = QEventLoop()
                        QTimer.singleShot(self.visualizador.velocidade_visualizacao(), loop.quit)
                        loop.exec_()
                except Exception as e:
                    logger.error(f"Erro ao processar {nome}: {e}")
                    self.visualizador.adicionar_log(f"❌ ERRO: {nome} — {e}")
                    self.banco_dados.registrar_evento(
                        proc_id, None, nome, 'erro', str(e))

            return True
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            self.visualizador.adicionar_log(f"❌ ERRO GERAL: {e}")
            return False

    def _processar_arquivo(self, caminho):
        doc = ezdxf.readfile(caminho)
        msp = doc.modelspace()

        entidades = list(msp)
        x_inicio, x_fim, altura = self._bounding_box(entidades)
        comprimento_total = x_fim - x_inicio

        furos = [
            {'center': (e.dxf.center.x, e.dxf.center.y), 'radius': e.dxf.radius}
            for e in entidades if e.dxftype() == 'CIRCLE'
        ]

        partes, estrategia, eficiencia, perda, eventos = self._aplicar_estrategia_corte(
            x_inicio, x_fim, furos)

        partes_geradas = self._gerar_arquivos_partes(caminho, partes, entidades, furos, x_inicio, x_fim, altura)

        return {
            'dimensoes_originais': (comprimento_total, altura),
            'partes':        partes,
            'furos':         furos,
            'estrategia':    estrategia,
            'eficiencia':    eficiencia,
            'perda_mm':      perda,
            'partes_geradas': partes_geradas,
            'eventos':       eventos,
        }

    def _bounding_box(self, entidades):
        xs, ys = [], []
        for e in entidades:
            t = e.dxftype()
            if t == 'LINE':
                xs += [e.dxf.start.x, e.dxf.end.x]
                ys += [e.dxf.start.y, e.dxf.end.y]
            elif t in ('CIRCLE', 'ARC'):
                cx, cy, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
                xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
            elif t == 'LWPOLYLINE':
                for p in e.get_points():
                    xs.append(p[0]); ys.append(p[1])
        return min(xs), max(xs), max(ys) - min(ys)

    # ── estratégia de corte ───────────────────────────────────────────────────

    def _furo_na_posicao(self, pos, furos):
        return any(abs(f['center'][0] - pos) < self.MARGEM_FURO for f in furos)

    def _tentar_corte(self, x_inicio, x_fim, tamanho, furos):
        comp = x_fim - x_inicio
        for pos in [x_inicio + tamanho, x_fim - tamanho]:
            resto = comp - tamanho
            if resto < self.PARTE_MINIMA:
                continue
            if pos <= x_inicio or pos >= x_fim:
                continue
            if not self._furo_na_posicao(pos, furos):
                return pos
        return None

    def _corte_forcado(self, x_inicio, x_fim, furos):
        comp = x_fim - x_inicio
        for base in [x_inicio + (comp - self.PARTE_MINIMA), x_inicio + self.PARTE_MINIMA]:
            if not self._furo_na_posicao(base, furos):
                return base
            for delta in [-self.MARGEM_FURO, +self.MARGEM_FURO]:
                pos = base + delta
                menor = min(pos - x_inicio, x_fim - pos)
                if menor >= self.PARTE_MINIMA and not self._furo_na_posicao(pos, furos):
                    return pos
        return None

    def _dividir_segmento(self, x_inicio, x_fim, furos):
        for tamanho in self.TAMANHOS_CORTE:
            pos = self._tentar_corte(x_inicio, x_fim, tamanho, furos)
            if pos is not None:
                return pos, tamanho, f"{tamanho}mm"
        pos = self._corte_forcado(x_inicio, x_fim, furos)
        if pos is not None:
            return pos, None, f"forçado ({pos-x_inicio:.0f}+{x_fim-pos:.0f})"
        return None

    def _aplicar_estrategia_corte(self, x_inicio, x_fim, furos):
        cortes, descricoes = [], []
        eventos = []  # corte forçado / segmento bloqueado, pra registrar no banco
        pendentes = [(x_inicio, x_fim)]

        while pendentes:
            si, sf = pendentes.pop(0)
            if sf - si <= max(self.TAMANHOS_CORTE):
                continue
            res = self._dividir_segmento(si, sf, furos)
            if res is None:
                msg = f"Segmento {sf-si:.0f}mm não pôde ser dividido (furo bloqueando)"
                self.visualizador.adicionar_log(f"⚠ {msg}")
                eventos.append({
                    'tipo': 'segmento_bloqueado', 'detalhe': msg,
                    'posicao_x': si, 'comprimento_mm': sf - si,
                })
                continue
            pos, tamanho, desc = res
            cortes.append(pos); descricoes.append(desc)
            if tamanho is None:  # corte forçado (nenhum tamanho padrão coube)
                eventos.append({
                    'tipo': 'corte_forcado', 'detalhe': desc,
                    'posicao_x': pos, 'comprimento_mm': None,
                })
            for novo in [(si, pos), (pos, sf)]:
                if novo[1] - novo[0] > max(self.TAMANHOS_CORTE):
                    pendentes.append(novo)

        posicoes = [x_inicio] + sorted(set(cortes)) + [x_fim]
        partes   = [(posicoes[i], posicoes[i+1]) for i in range(len(posicoes)-1)]
        comp_total = x_fim - x_inicio
        eficiencia = 100.0
        perda      = 0.0
        n = len(partes)
        if n == 1:
            estrategia = "Sem corte (peça inteira)"
        else:
            tam_str    = " + ".join(f"{p[1]-p[0]:.0f}" for p in partes)
            estrategia = f"{n} partes [{tam_str}] mm"
        return partes, estrategia, eficiencia, perda, eventos

    # ── geração dos arquivos DXF preservando geometria original ──────────────

    @staticmethod
    def _intersecao_vertical(x_corte, x1, y1, x2, y2):
        """Y da interseção da vertical x=x_corte com o segmento (x1,y1)-(x2,y2)."""
        if abs(x2 - x1) < 1e-9:
            return None
        t = (x_corte - x1) / (x2 - x1)
        if -1e-9 <= t <= 1 + 1e-9:
            return y1 + t * (y2 - y1)
        return None

    @staticmethod
    def _aparar_linha(x1, y1, x2, y2, xa, xb):
        """
        Apara o segmento (x1,y1)-(x2,y2) para o intervalo X [xa,xb].
        Retorna (p_inicio, p_fim) ou None se fora do intervalo.
        """
        pts = []

        def add(px, py):
            if xa - 1e-9 <= px <= xb + 1e-9:
                pts.append((px, py))

        add(x1, y1)
        add(x2, y2)

        dx = x2 - x1
        for xc in (xa, xb):
            if abs(dx) > 1e-9:
                t = (xc - x1) / dx
                if -1e-9 <= t <= 1 + 1e-9:
                    add(xc, y1 + t * (y2 - y1))

        if len(pts) < 2:
            return None

        def param(p):
            if abs(dx) > 1e-9:
                return (p[0] - x1) / dx
            dy = y2 - y1
            return (p[1] - y1) / dy if abs(dy) > 1e-9 else 0

        pts = sorted(set(pts), key=param)
        p0, p1 = pts[0], pts[-1]

        # descarta segmentos degenerados
        if abs(p1[0] - p0[0]) < 1e-9 and abs(p1[1] - p0[1]) < 1e-9:
            return None
        return p0, p1

    def _gerar_arquivos_partes(self, caminho_original, partes, entidades_orig, furos, x_inicio, x_fim, altura):
        base, ext    = os.path.splitext(caminho_original)
        nome_arquivo = os.path.basename(base)
        partes_nome  = nome_arquivo.split(' - ')
        partes_geradas = []

        for i, (xa, xb) in enumerate(partes):
            letra = chr(65 + i)

            if len(partes_nome) > 1:
                prefixo    = partes_nome[0]
                sufixo     = ' - '.join(partes_nome[1:])
                nome_parte = f"{prefixo}[{letra}] - {sufixo}{ext}"
            else:
                nome_parte = f"{nome_arquivo}[{letra}]{ext}"

            caminho_parte = os.path.join(os.path.dirname(caminho_original), nome_parte)

            doc = ezdxf.new()
            msp = doc.modelspace()

            # ── 1. Copiar e aparar entidades originais ──────────────────
            for ent in entidades_orig:
                t = ent.dxftype()

                if t == 'LINE':
                    x1, y1 = ent.dxf.start.x, ent.dxf.start.y
                    x2, y2 = ent.dxf.end.x,   ent.dxf.end.y
                    res = self._aparar_linha(x1, y1, x2, y2, xa, xb)
                    if res:
                        msp.add_line(res[0], res[1])

                elif t == 'CIRCLE':
                    cx = ent.dxf.center.x
                    # furos: só inclui se o centro estiver dentro da parte
                    if xa <= cx <= xb:
                        msp.add_circle(
                            (ent.dxf.center.x, ent.dxf.center.y),
                            ent.dxf.radius)

                elif t == 'ARC':
                    cx = ent.dxf.center.x
                    r  = ent.dxf.radius
                    # inclui o arco se o centro (ou parte dele) estiver na faixa
                    if xa - r <= cx <= xb + r:
                        msp.add_arc(
                            (ent.dxf.center.x, ent.dxf.center.y),
                            r,
                            ent.dxf.start_angle,
                            ent.dxf.end_angle)

                elif t == 'LWPOLYLINE':
                    pts = list(ent.get_points())
                    n_pts = len(pts)
                    segmentos_ok = []
                    # Correção (v2): uma polilinha FECHADA (ent.closed) tem um
                    # segmento IMPLÍCITO ligando o último ponto de volta ao
                    # primeiro, que nunca fica gravado explicitamente no DXF.
                    # O nosso conversor CAM→DXF desenha o contorno inteiro da
                    # peça como uma única LWPOLYLINE fechada — ignorar esse
                    # segmento fazia a borda da peça sumir nas partes geradas.
                    n_segmentos = n_pts if ent.closed else n_pts - 1
                    for j in range(n_segmentos):
                        p1 = pts[j]
                        p2 = pts[(j + 1) % n_pts]
                        x1, y1 = p1[0], p1[1]
                        x2, y2 = p2[0], p2[1]
                        res = self._aparar_linha(x1, y1, x2, y2, xa, xb)
                        if res:
                            segmentos_ok.append(res)
                    for seg in segmentos_ok:
                        msp.add_line(seg[0], seg[1])

            # ── 2. Adicionar borda de corte esquerda (se não for o início original) ──
            if abs(xa - x_inicio) > 1e-6:
                y_topo = self._y_na_posicao(xa, entidades_orig, topo=True)
                y_base = self._y_na_posicao(xa, entidades_orig, topo=False)
                msp.add_line((xa, y_base), (xa, y_topo))

            # ── 3. Adicionar borda de corte direita (se não for o fim original) ──
            if abs(xb - x_fim) > 1e-6:
                y_topo = self._y_na_posicao(xb, entidades_orig, topo=True)
                y_base = self._y_na_posicao(xb, entidades_orig, topo=False)
                msp.add_line((xb, y_base), (xb, y_topo))

            doc.saveas(caminho_parte)

            qtd_furos = sum(1 for f in furos if xa <= f['center'][0] <= xb)
            partes_geradas.append({
                'nome':        nome_parte,
                'comprimento': xb - xa,
                'furos':       qtd_furos,
            })

        return partes_geradas

    def _y_na_posicao(self, x_pos, entidades, topo=True):
        """
        Encontra o Y (topo ou base) da peça original na posição X dada,
        percorrendo as linhas (e polilinhas) e calculando interseções.
        """
        ys = []
        for ent in entidades:
            t = ent.dxftype()
            if t == 'LINE':
                x1, y1 = ent.dxf.start.x, ent.dxf.start.y
                x2, y2 = ent.dxf.end.x,   ent.dxf.end.y
                y = self._intersecao_vertical(x_pos, x1, y1, x2, y2)
                if y is not None:
                    ys.append(y)
            elif t == 'LWPOLYLINE':
                # Correção (v2): o contorno gerado pelo nosso conversor é uma
                # única LWPOLYLINE fechada (sem entidades LINE separadas) —
                # sem este bloco, esta função sempre retornava 0/0 para esses
                # arquivos, gerando uma "borda de corte" de comprimento zero.
                pts = list(ent.get_points())
                n_pts = len(pts)
                n_segmentos = n_pts if ent.closed else n_pts - 1
                for j in range(n_segmentos):
                    p1 = pts[j]
                    p2 = pts[(j + 1) % n_pts]
                    y = self._intersecao_vertical(x_pos, p1[0], p1[1], p2[0], p2[1])
                    if y is not None:
                        ys.append(y)
        if not ys:
            return 0
        return max(ys) if topo else min(ys)


