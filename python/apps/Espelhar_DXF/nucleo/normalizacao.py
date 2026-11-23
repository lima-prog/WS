# -*- coding: utf-8 -*-
"""
Regra compartilhada para extrair o identificador de obra/trecho a partir
do nome de uma pasta no padrão usado pelas exportações Tekla/Tecno (ex.:
"2058-102_01_L1", "2104-2-55_L1-2").

Usada por mais de uma ferramenta deste app — Conversor CAM → DXF
(conversor/utilitarios.py, no nome do DXF gerado a partir do .CAM) e
Renomear DXF Tekla/Tecno (renomear_dxf/utilitarios.py, pra montar o nome
final de um DXF/DWG já exportado por fora) — por isso mora aqui em
nucleo/ em vez de dentro da pasta de uma ferramenta específica (regra de
ouro da arquitetura: uma pasta de ferramenta nunca importa de outra).
"""
import re


def normalizar_obra(valor):
    """
    Converte NUM_COM (ou o nome da pasta da obra, no fallback) para o
    identificador da obra usado no DXF.

    Exemplos:
        2058-102_01_L1  -> 2058-102-01
        2058-102_01_L2  -> 2058-102-01
        2113-7-55_L1    -> 2113-7-55
        2104-2-55_L1-2  -> 2104-2-55-2   (o "-2" depois do "_L1" é dado
                                           de verdade, ex. sub-lote — só o
                                           "_L1" em si é removido)
    """
    valor = (valor or "").strip()

    # Remove o marcador de linha "_L1", "_L2", "_L10" etc., em qualquer
    # posição do nome — não só quando está bem no final. Antes o padrão só
    # batia quando "_L<número>" era literalmente o fim da string, então
    # uma pasta como "2104-2-55_L1-2" (com um "-2" de sub-lote colado
    # depois do marcador de linha) não batia com nada e o "_L1-2" inteiro
    # ficava no resultado. Agora só o "_L<número>" em si some; qualquer
    # coisa que venha depois dele (como esse "-2") é considerada dado de
    # verdade e continua aparecendo no identificador final.
    valor = re.sub(r"_L\d+", "", valor, flags=re.IGNORECASE)

    # O restante dos "_" vira "-".
    valor = valor.replace("_", "-")

    # A identificação da obra possui no máximo 9 dígitos.
    partes = []
    total_digitos = 0

    for parte in valor.split("-"):
        digitos = sum(ch.isdigit() for ch in parte)

        if total_digitos + digitos > 9:
            break

        partes.append(parte)
        total_digitos += digitos

    resultado = "-".join(partes).strip("-")

    return resultado or "SEM_OBRA"
