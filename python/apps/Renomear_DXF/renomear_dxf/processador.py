# -*- coding: utf-8 -*-
"""
Motor da aba Renomear DXF (Tekla/Tecno): a partir de uma pasta de .CAM e
uma pasta de .DXF/.DWG já exportados por fora (Tekla/Tecno), casa cada
arquivo pela POSIÇÃO (nome do arquivo sem extensão) com a quantidade lida
do .CAM correspondente, e monta o nome final "<posição> - OF<obra/trecho>
- Q<qtd><extensão>" — sem renomear nada ainda. Só depois de conferir na
tela (ver renomear_dxf/aba.py) o usuário decide quais linhas realmente
renomear, evitando repetir o problema do script original, que renomeava
tudo de uma vez sem chance de revisão e travava (IndexError/KeyError) se
algum arquivo não tivesse um .CAM correspondente.

Sem nenhuma dependência de PyQt5.
"""
import os

from nucleo.logging_config import logger
from renomear_dxf.utilitarios import (
    derivar_obra_trecho, ler_quantidade_cam, listar_dxf_dwg, nome_renomeado,
)


def analisar(pasta_cam, pasta_dxf):
    """
    Devolve (linhas, obra_trecho, liberacao, avisos):
      - linhas: lista de dicts, um por arquivo .dxf/.dwg encontrado em
        `pasta_dxf`:
          {"caminho_atual", "arquivo_atual", "posicao", "quantidade"
           (string, ou None se não achou CAM correspondente ou o .CAM não
           tinha QTA_PEZ legível), "nome_final" (ou None), "status":
           "ok" | "sem_cam" | "sem_quantidade"}
      - obra_trecho: identificador já tratado (via normalizar_obra) que
        entra no nome final.
      - liberacao: nome de pasta cru (um nível acima da pasta CAM), só
        pra mostrar na tela e o usuário conferir se bateu com a pasta
        certa.
      - avisos: lista de strings com problemas que não impedem a análise
        (ex.: nenhum .CAM ou nenhum .DXF/.DWG encontrado).
    """
    obra_trecho, liberacao = derivar_obra_trecho(pasta_cam)
    avisos = []

    arquivos_cam = []
    if pasta_cam and os.path.isdir(pasta_cam):
        arquivos_cam = sorted(
            [a for a in os.listdir(pasta_cam)
             if a.lower().endswith(".cam")
             and os.path.isfile(os.path.join(pasta_cam, a))],
            key=str.lower
        )
    if not arquivos_cam:
        avisos.append("Não encontrei nenhum arquivo .CAM na pasta CAM escolhida.")

    dict_qtd = {}
    for arquivo in arquivos_cam:
        posicao = os.path.splitext(arquivo)[0]
        caminho = os.path.join(pasta_cam, arquivo)
        qtd = ler_quantidade_cam(caminho)
        if qtd is None:
            logger.warning(f"Renomear DXF: não achei QTA_PEZ legível em {arquivo}")
        dict_qtd[posicao] = qtd

    caminhos_dxf = listar_dxf_dwg(pasta_dxf)
    if not caminhos_dxf:
        avisos.append("Não encontrei nenhum arquivo .DXF/.DWG na pasta escolhida.")

    linhas = []
    for caminho in sorted(caminhos_dxf, key=str.lower):
        arquivo_atual = os.path.basename(caminho)
        posicao, ext = os.path.splitext(arquivo_atual)
        qtd = dict_qtd.get(posicao)

        if posicao not in dict_qtd:
            status = "sem_cam"
            nome_final = None
        elif qtd is None:
            status = "sem_quantidade"
            nome_final = None
        else:
            status = "ok"
            nome_final = nome_renomeado(posicao, obra_trecho, qtd, ext)

        linhas.append({
            "caminho_atual": caminho,
            "arquivo_atual": arquivo_atual,
            "posicao": posicao,
            "quantidade": qtd,
            "nome_final": nome_final,
            "status": status,
        })

    return linhas, obra_trecho, liberacao, avisos


def renomear(linhas):
    """
    Executa o rename de cada linha em `linhas` (só as que o chamador já
    filtrou como prontas — normalmente status == "ok"). Cada arquivo é
    renomeado dentro da MESMA pasta onde já está (o script original
    também nunca move de pasta, só troca o nome).

    Nunca sobrescreve um arquivo já existente com o nome final — se já
    existir algo com esse nome na pasta, reporta como erro em vez de
    apagar silenciosamente (o script original usava os.rename puro, que
    sobrescreveria sem avisar).

    Devolve uma lista de resultados, UM POR LINHA DE ENTRADA, na mesma
    ordem de `linhas` — cada item é
    {"linha": <o mesmo dict recebido>, "sucesso": bool,
     "novo_caminho": <caminho final, só quando sucesso>,
     "erro": <string, só quando falhou>}.

    Devolver o resultado por linha (em vez de só um total) é o que deixa
    `renomear_dxf/aba.py` atualizar o status de cada arquivo recém-
    renomeado DIRETO na tabela em memória, sem precisar rodar `analisar()`
    de novo — reanalisar do zero faria o arquivo já renomeado (que agora
    tem outro nome, sem casar com nenhuma posição de `.CAM`) aparecer como
    "❌ Sem .CAM correspondente", parecendo um erro quando na verdade foi
    um sucesso (bug relatado pelo usuário — ver CONTINUIDADE.md).
    """
    resultados = []
    for linha in linhas:
        caminho_atual = linha["caminho_atual"]
        nome_final = linha["nome_final"]
        if not nome_final:
            continue

        pasta = os.path.dirname(caminho_atual)
        caminho_final = os.path.join(pasta, nome_final)

        try:
            if os.path.abspath(caminho_atual) == os.path.abspath(caminho_final):
                # já está com o nome final (ex.: clicou renomear de novo
                # sem reanalisar) — nada a fazer, mas não é erro.
                resultados.append({
                    "linha": linha, "sucesso": True,
                    "novo_caminho": caminho_final, "erro": None,
                })
                continue
            if os.path.exists(caminho_final):
                resultados.append({
                    "linha": linha, "sucesso": False, "novo_caminho": None,
                    "erro": (f"já existe um arquivo \"{nome_final}\" "
                             "nessa pasta — não sobrescrevi."),
                })
                continue
            os.rename(caminho_atual, caminho_final)
            resultados.append({
                "linha": linha, "sucesso": True,
                "novo_caminho": caminho_final, "erro": None,
            })
        except OSError as e:
            logger.error(f"Erro ao renomear {caminho_atual}: {e}")
            resultados.append({
                "linha": linha, "sucesso": False,
                "novo_caminho": None, "erro": str(e),
            })

    return resultados
