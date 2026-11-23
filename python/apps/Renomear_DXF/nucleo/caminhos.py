# -*- coding: utf-8 -*-
"""
Fonte única de verdade para caminhos compartilhados entre módulos do
projeto. Antes da divisão em pacote, cada arquivo calculava sozinho (via
`__file__`) onde ficava o banco/log — agora isso é calculado UMA vez aqui,
e todo mundo importa daqui, em vez de cada módulo adivinhar sua própria
profundidade de pasta.

Estrutura de pastas esperada (rodando com `python main.py`):

    <PASTA_PAI>/
        pcp_projeart.db              <- banco compartilhado (outros módulos do PROG_FLUXOS)
        ppcp_dxf_ferramentas/        <- RAIZ_PROJETO
            main.py
            nucleo/
                caminhos.py          <- este arquivo
            ...

RODANDO CONGELADO (.exe gerado pelo PyInstaller) — LEIA ISSO ANTES DE MEXER:

`__file__` sozinho não é confiável quando o programa vira `.exe`. O
PyInstaller "congela" o projeto inteiro (inclusive este arquivo) dentro do
executável e, ao rodar, extrai tudo pra uma pasta temporária que muda a
cada execução (`sys._MEIPASS`). Se a gente continuasse calculando
CAMINHO_BANCO_DADOS e LOG_PATH a partir de `__file__` nesse modo, o banco
de histórico e o log passariam a "sumir e recomeçar do zero" toda vez que
o programa fosse aberto de novo — porque cada abertura extrairia pra uma
pasta temporária diferente.

Por isso, aqui embaixo, tratamos DOIS tipos de caminho de formas
diferentes quando `sys.frozen` está setado (ou seja, quando é o `.exe`
quem está rodando, não o `python main.py`):

  - Dados PERSISTENTES (banco de dados, log): continuam calculados a
    partir de `sys.executable` — o caminho do `.exe` de verdade, que fica
    parado no lugar onde o usuário colocou o programa. Assim o banco e o
    log continuam no mesmo lugar entre uma abertura e outra do programa,
    igual acontece hoje rodando com Python puro.

  - Dados EMPACOTADOS/SOMENTE LEITURA (as imagens em nucleo/assets/):
    esses são copiados PRA DENTRO do `.exe` na hora de gerar o build (veja
    `main.spec`, seção `datas`) e, ao rodar, o PyInstaller os extrai pra
    `sys._MEIPASS`. Não faz sentido — e não funcionaria — procurá-los do
    lado do `.exe`; tem que procurar dentro de `sys._MEIPASS`.

Rodando com `python main.py` (não congelado), nada disso entra em jogo:
tudo continua sendo calculado a partir de `__file__`, exatamente como
sempre foi.
"""
import os
import sys

# True só quando o programa está rodando como .exe gerado pelo PyInstaller
# (o PyInstaller seta esse atributo sozinho — não existe em `python main.py`
# normal). Outros módulos podem importar essa flag se um dia precisarem
# de algum comportamento diferente em modo empacotado.
RODANDO_CONGELADO = getattr(sys, 'frozen', False)

PASTA_NUCLEO_FONTE = os.path.dirname(os.path.abspath(__file__))

if RODANDO_CONGELADO:
    # Dados persistentes (banco, log): ao lado do .exe de verdade, não da
    # pasta temporária de extração — senão "sumiriam" a cada abertura.
    RAIZ_PROJETO = os.path.dirname(sys.executable)
    # Dados empacotados (assets): dentro da pasta temporária que o
    # PyInstaller extraiu (sys._MEIPASS só existe em modo congelado).
    PASTA_NUCLEO = os.path.join(sys._MEIPASS, "nucleo")
else:
    # Modo normal (`python main.py`): tudo calculado a partir deste
    # arquivo, como sempre foi.
    PASTA_NUCLEO = PASTA_NUCLEO_FONTE
    RAIZ_PROJETO = os.path.dirname(PASTA_NUCLEO)

# ---------------------------------------------------------------------------
# MODO RÁPIDO (código local + dados no servidor) — variável de ambiente PPCP_DADOS
#
# Abrir o programa direto da pasta de rede é lento (cada .py, a lucide.json de 830 KB e as
# bibliotecas são lidos pela rede, e o __pycache__ é gravado lá). O `iniciar_ppcp.bat` copia o
# CÓDIGO pra uma pasta local do PC (%LOCALAPPDATA%\PPCP_Ferramentas\app) e roda de lá; os DADOS
# (bancos, layout da área de trabalho, ícones do usuário, memória do roteirizador) continuam na
# pasta do servidor, que o .bat informa em PPCP_DADOS — assim todo mundo segue enxergando os
# mesmos dados.
#
#   RAIZ_PROJETO : onde está o CÓDIGO (main.py)               -> local no modo rápido
#   RAIZ_DADOS   : onde estão os DADOS do programa            -> servidor no modo rápido
#   PASTA_LOGS   : onde o log é gravado                       -> sempre local no modo rápido
#
# Sem PPCP_DADOS (python main.py direto, ou .exe) RAIZ_DADOS == RAIZ_PROJETO e tudo funciona
# exatamente como antes.
# ---------------------------------------------------------------------------
_dados_env = os.environ.get("PPCP_DADOS", "").strip().strip('"')
RAIZ_DADOS = os.path.normpath(os.path.abspath(_dados_env)) if _dados_env else RAIZ_PROJETO
MODO_RAPIDO = RAIZ_DADOS != RAIZ_PROJETO

PASTA_PAI = os.path.dirname(RAIZ_DADOS)  # uma pasta acima da pasta de DADOS (onde fica o pcp_projeart.db)

CAMINHO_BANCO_DADOS = os.path.join(PASTA_PAI, "pcp_projeart.db")


def _pasta_logs():
    """Log local no modo rápido (gravar log em pasta de rede, a cada linha, pesa); senão ao lado do programa."""
    explicita = os.environ.get("PPCP_LOGS", "").strip().strip('"')
    if explicita:
        pasta = explicita
    elif MODO_RAPIDO:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".ppcp_ferramentas")
        pasta = os.path.join(base, "PPCP_Ferramentas", "logs")
    else:
        return RAIZ_PROJETO
    try:
        os.makedirs(pasta, exist_ok=True)
        return pasta
    except Exception:
        return RAIZ_PROJETO


PASTA_LOGS = _pasta_logs()

# Imagens da marca Projeart (aba Início + ícone da janela). Ficam em
# nucleo/ porque, assim como o banco de dados, são compartilhadas — não
# pertencem a nenhuma ferramenta específica. Em modo congelado, PASTA_NUCLEO
# já aponta pra dentro de sys._MEIPASS (ver acima), então essas duas linhas
# funcionam sem mudança nos dois modos.
PASTA_ASSETS = os.path.join(PASTA_NUCLEO, "assets")
CAMINHO_LOGO_PROJEART  = os.path.join(PASTA_ASSETS, "logo_projeart.png")   # marca completa (fundo branco) — aba Início
CAMINHO_ICONE_PROJEART = os.path.join(PASTA_ASSETS, "icone_projeart.png")  # ícone quadrado (fundo escuro) — ícone da janela
