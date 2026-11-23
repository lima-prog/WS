# -*- coding: utf-8 -*-
"""
Motor da aba Espelhar: le cada DXF da pasta, espelha, reancora em (0,0) e
salva na subpasta ESPELHADAS mantendo o nome original.
"""
import os
import ezdxf
from PyQt5.QtCore import QEventLoop, QTimer

from nucleo.logging_config import logger
from dxf_util.preview import extrair_preview_dxf
from espelhar.mirror import SUBPASTA_ESPELHADAS, espelhar_documento


class ProcessadorEspelhamento:
    """Motor da aba Espelhar: le cada DXF da pasta, espelha, reancora em
    (0,0) e salva na subpasta ESPELHADAS mantendo o nome original. Chama de
    volta a aba (self.aba) pra atualizar progresso/log/preview visual."""

    def __init__(self, aba):
        self.aba = aba

    def processar_pasta(self, caminho_pasta):
        try:
            arquivos = sorted(f for f in os.listdir(caminho_pasta) if f.lower().endswith('.dxf'))
            if not arquivos:
                raise ValueError("Nenhum arquivo DXF encontrado na pasta")

            pasta_saida = os.path.join(caminho_pasta, SUBPASTA_ESPELHADAS)
            os.makedirs(pasta_saida, exist_ok=True)

            total = len(arquivos)
            ok_total = 0
            erro_total = 0

            for idx, nome in enumerate(arquivos, 1):
                self.aba.atualizar_progresso(idx, total)
                self.aba.atualizar_status(f"Espelhando {idx}/{total}: {nome}")
                caminho_arquivo = os.path.join(caminho_pasta, nome)
                avisos = []
                try:
                    doc = ezdxf.readfile(caminho_arquivo)
                    msp = doc.modelspace()
                    # retrato ANTES: precisa ser extraido AGORA, antes do mirror
                    # mutar as entidades (senao vira referencia pro estado espelhado)
                    preview_antes = extrair_preview_dxf(list(msp))

                    espelhar_documento(doc, avisos)

                    preview_depois = extrair_preview_dxf(list(msp))
                    destino = os.path.join(pasta_saida, nome)
                    doc.saveas(destino)

                    if self.aba.visualizacao_habilitada():
                        self.aba.mostrar_resultado(preview_antes, preview_depois, nome, avisos)
                        loop = QEventLoop()
                        QTimer.singleShot(self.aba.velocidade_visualizacao(), loop.quit)
                        loop.exec_()

                    msg = f"✅ {nome}"
                    if avisos:
                        msg += f"   ⚠ nao espelhado: {', '.join(sorted(set(avisos)))}"
                    self.aba.adicionar_log(msg)
                    ok_total += 1
                except Exception as e:
                    logger.error(f"Erro ao espelhar {nome}: {e}")
                    self.aba.adicionar_log(f"❌ ERRO: {nome} — {e}")
                    erro_total += 1

            self.aba.adicionar_log(f"\nConcluido: {ok_total} espelhado(s), {erro_total} com erro.")
            self.aba.adicionar_log(f"Salvos em: {pasta_saida}")
            return erro_total == 0
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            self.aba.adicionar_log(f"❌ ERRO GERAL: {e}")
            return False
