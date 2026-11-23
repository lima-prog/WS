# -*- coding: utf-8 -*-
"""
Funções puras da ferramenta "Renomear DXF (Tekla/Tecno)" — sem nenhuma
dependência de tela.

Reconstruída a partir de um .exe antigo, separado deste app
(`renomear_dxf_tekla_tecno.exe`, decompilado a pedido do usuário), que
cobria um fluxo de trabalho diferente do Conversor CAM → DXF: quando o
Tekla/Tecno já exportou os DXF/DWG das peças por fora (não passam pelo
motor de conversão deste app), esse programa só lia a pasta de .CAM
correspondente pra pegar a quantidade de cada peça (QTA_PEZ) e renomeava
os DXF/DWG já existentes, casando pelo nome do arquivo (POSIÇÃO). Mantém
o mesmo formato de nome final que o Conversor já usa neste app:
"<posição> - OF<obra/trecho> - Q<qtd>".

Três correções em relação ao script original (decisões do usuário — ver
CONTINUIDADE.md):
  1. A extensão final agora é sempre a extensão ORIGINAL do arquivo
     (.dxf continua .dxf, .DWG continua .DWG) — o original sempre forçava
     ".DXF" no nome, mesmo em cima de um .DWG de verdade (arquivo com nome
     de DXF mas conteúdo de DWG).
  2. A varredura de DXF/DWG reconhece extensão minúscula também (".dxf",
     ".dwg") — o original só reconhecia "DXF"/"DWG" maiúsculo puro,
     deixando passar batido qualquer arquivo salvo em minúsculo (bem
     comum).
  3. A pasta de DXF/DWG a varrer não é mais fixa em Desktop\\DXF — a tela
     (renomear_dxf/aba.py) deixa o usuário escolher, sugerindo essa pasta
     como ponto de partida se ela existir.

Também reaproveita `normalizar_obra` de nucleo/normalizacao.py — a mesma
regra que o Conversor usa pra tratar o nome da pasta de obra (remove o
marcador de linha "_L<n>", preserva sufixo de sub-lote, limita dígitos) —
em vez do `liberacao.split('_')[0]` ingênuo do script original, que
cortava tudo no primeiro "_" e perdia qualquer sub-lote com "_" no meio
(ex.: "2058-102_01_L1" virava só "2058-102", perdendo o "-01" do meio).
"""
import os

from nucleo.normalizacao import normalizar_obra

_EXTENSOES_VALIDAS = (".dxf", ".dwg")


def derivar_obra_trecho(pasta_cam):
    """
    A pasta escolhida pelo usuário é a pasta de .CAM (ex.:
    ".../2104-2-55_L1/CAM"). A pasta UM NÍVEL ACIMA dela (aqui chamada
    "liberação", mesmo nome que o script original usava para essa
    variável) é quem carrega o identificador real da obra/trecho — mesma
    convenção que o Conversor já usa pra achar a obra a partir do .CAM
    (`ler_cam()` em conversor/utilitarios.py, variável `pasta_obra`: a
    pasta um nível acima da pasta "CAM").

    Devolve (obra_trecho, liberacao): `liberacao` é o nome de pasta cru,
    só pra mostrar na tela e o usuário conferir se bateu com a pasta
    certa; `obra_trecho` já é o valor tratado por `normalizar_obra`, que
    entra de verdade no nome final do arquivo.
    """
    pasta_cam = (pasta_cam or "").rstrip("/\\")
    liberacao = os.path.basename(os.path.dirname(pasta_cam))
    obra_trecho = normalizar_obra(liberacao)
    return obra_trecho, liberacao


def ler_quantidade_cam(caminho_cam):
    """
    Lê só o valor de QTA_PEZ (quantidade de peças) de um arquivo .CAM,
    percorrendo as linhas de texto direto — essa ferramenta só precisa
    desse único campo, não a geometria inteira que o Conversor lê.

    Usa a mesma codificação "latin-1" (com replace nos bytes que não
    baterem) que o Conversor usa pra ler .CAM — evita um crash quando o
    arquivo tem acentuação fora de UTF-8 (comum em exportações antigas do
    Tekla/Tecno). O script original (decompilado) abria com a codificação
    padrão do sistema e usava numpy pra achar a linha (`np.where`, pegando
    sempre o índice [0][0]) — isso quebrava com IndexError sempre que
    "QTA_PEZ:" não aparecia no arquivo. Aqui, se não achar, devolve `None`
    em vez de lançar exceção; quem chama decide o que mostrar (ver
    `analisar()` em processador.py).
    """
    try:
        with open(caminho_cam, "r", encoding="latin-1", errors="replace") as f:
            linhas = f.readlines()
    except OSError:
        return None

    for linha in linhas:
        linha = linha.strip()
        if linha.upper().startswith("QTA_PEZ:"):
            valor = linha.split(":", 1)[1].strip()
            try:
                return str(int(valor))
            except ValueError:
                return None
    return None


def listar_dxf_dwg(pasta_raiz):
    """
    Varre `pasta_raiz` recursivamente (igual ao script original, que
    sempre olhava dentro de Desktop\\DXF e todas as subpastas) e devolve
    o caminho completo de cada arquivo .dxf/.dwg encontrado.
    """
    encontrados = []
    if not pasta_raiz or not os.path.isdir(pasta_raiz):
        return encontrados
    for raiz, _dirs, arquivos in os.walk(pasta_raiz):
        for nome in arquivos:
            _, ext = os.path.splitext(nome)
            if ext.lower() in _EXTENSOES_VALIDAS:
                encontrados.append(os.path.join(raiz, nome))
    return encontrados


def nome_renomeado(posicao, obra_trecho, qtd, extensao_original):
    """
    Nome final do arquivo renomeado: "<posição> - OF<obra_trecho> -
    Q<qtd><extensão original>".
    """
    nome = f"{posicao} - OF{obra_trecho} - Q{qtd}{extensao_original}"
    for ch in '<>:"/\\|?*':
        nome = nome.replace(ch, "_")
    return nome.strip()
