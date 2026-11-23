# -*- coding: utf-8 -*-
"""
Motor da aba Conversor CAM→DXF: lê todos os .CAM de uma pasta (não
recursivo — só o nível raiz da pasta escolhida, igual ao script original)
e converte os selecionados para DXF (modo CORTE), organizando a saída em
subpastas por espessura + material quando pedido.

Sem nenhuma dependência de PyQt5. Toda a interação com a tela acontece por
callback (o parâmetro `aba` precisa expor: atualizar_status(msg) — é
exatamente o que conversor/aba.py::AbaConversor implementa).
"""
import os

from nucleo.logging_config import logger
from conversor.utilitarios import (
    ler_cam, criar_dxf_corte, nome_dxf, caminho_unico,
    limpar_nome_pasta, formatar_numero_pasta,
)


class ProcessadorConversor:
    """Motor da aba Conversor: lê a pasta de CAMs e gera os DXFs
    selecionados. Chama de volta a aba (self.aba) pra atualizar status em
    tempo real durante leitura/conversão de lotes grandes."""

    def __init__(self, aba):
        self.aba = aba

    # ── leitura da pasta de CAMs ───────────────────────────────────────────

    def carregar_pasta(self, caminho_pasta):
        """Lê todos os .cam do nível raiz de `caminho_pasta` (não desce em
        subpastas — mesmo comportamento do script original). Retorna
        (dados_arquivos, erros, total): dados_arquivos é
        {nome_arquivo: dados}, erros é a quantidade de .cam que não
        puderam ser lidos, total é a quantidade de .cam encontrados."""
        arquivos = sorted(
            [a for a in os.listdir(caminho_pasta)
             if a.lower().endswith(".cam")
             and os.path.isfile(os.path.join(caminho_pasta, a))],
            key=str.lower)

        dados_arquivos = {}
        erros = 0
        total = len(arquivos)

        for i, arquivo in enumerate(arquivos, start=1):
            caminho = os.path.join(caminho_pasta, arquivo)
            try:
                _, _, _, dados = ler_cam(caminho)
                dados_arquivos[arquivo] = dados
            except Exception as e:
                logger.error(f"Erro ao ler {arquivo}: {e}")
                erros += 1

            # Em pastas com muitos arquivos (ex.: 700+, comum em pastas de
            # rede), essa leitura pode levar alguns segundos. Atualiza o
            # status periodicamente (não a cada arquivo) pra não pesar.
            if total and (i % 20 == 0 or i == total):
                self.aba.atualizar_status(f"Lendo arquivos: {i}/{total}...")

        return dados_arquivos, erros, total

    # ── conversão dos arquivos selecionados ────────────────────────────────

    def converter_arquivos(self, pasta_cam, arquivos, dados_arquivos,
                            pasta_saida, organizar_subpastas):
        """Converte cada arquivo em `arquivos` (nomes de .cam, chaves de
        dados_arquivos) para DXF em pasta_saida. CAMs com dobra são
        ignorados (modo DOBRA ainda não implementado) e viram um erro na
        lista de retorno. Retorna (sucesso, erros: list[str])."""
        sucesso = 0
        erros = []
        total = len(arquivos)

        for i, arquivo in enumerate(arquivos, start=1):
            caminho_cam = os.path.join(pasta_cam, arquivo)

            try:
                dados = dados_arquivos[arquivo]

                # O conversor atual é SOMENTE PARA CORTE. CAM com dobra
                # pode ser exibido pela configuração, mas ainda não é
                # convertido nesta versão.
                if dados.get("tipo_cam") == "DOBRADO":
                    erros.append(
                        f"{arquivo}: CAM com dobra ignorado — "
                        "o modo DOBRA ainda não está habilitado."
                    )
                    continue

                nome = nome_dxf(dados)

                if organizar_subpastas:
                    # Cada combinação de espessura + material recebe sua
                    # própria pasta. Ex.: 1,55 A572 / 6,35 A572
                    # (vírgula no lugar do ponto, padrão BR de medidas.)
                    espessura = limpar_nome_pasta(
                        formatar_numero_pasta(dados["espessura"]))
                    material = limpar_nome_pasta(dados["material"])

                    pasta_destino = os.path.join(
                        pasta_saida, f"{espessura} {material}")
                    os.makedirs(pasta_destino, exist_ok=True)
                    descricao_destino = f"{espessura} {material}"
                else:
                    pasta_destino = pasta_saida
                    descricao_destino = "pasta escolhida"

                caminho_dxf = caminho_unico(os.path.join(pasta_destino, nome))

                criar_dxf_corte(caminho_cam, caminho_dxf)
                sucesso += 1

                # Atualiza o status periodicamente (não a cada arquivo)
                # para não pesar em lotes grandes (ex.: 700+ arquivos).
                if total and (i % 5 == 0 or i == total):
                    self.aba.atualizar_status(
                        f"Convertendo {i}/{total}: {nome} → {descricao_destino}")

            except Exception as erro:
                logger.error(f"Erro ao converter {arquivo}: {erro}")
                erros.append(f"{arquivo}: {erro}")

        return sucesso, erros
