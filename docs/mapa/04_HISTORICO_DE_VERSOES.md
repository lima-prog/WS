# 04 — Histórico de versões do SISTEMA PPCPM

> Gerado do histórico do GitHub (`lima-prog/ws`). Uma linha por versão publicada, da mais nova para a mais antiga.
> **Como procurar:** Ctrl+F pelo nome da aba (ex.: "Agrupador", "Etiquetas", "Tela inicial") ou pelo número (ex.: "V275").
> "pacote N" = versão do Python instalado nos PCs. Versões antes da V110 ficaram no projeto antigo (não estão aqui).


## 2026-11-26

- `7342d8a` V290: Impressão Grupo - LIC — botões Limpar no PDF do Pacote e na árvore Obra / Grupo LIC / Tipo / Espessura / OF
- `4a88462` V289: mensagens de status das abas de Produção com ícones de linha (padrão ERP) no lugar dos emojis
- `1d5257e` V288: avisos no padrão do sistema (botão cinza com Enter/Esc); PDFs da Impressão Casada e Multi obra com Sistema.ppcm no nome
- `3e60464` V287: versão nova não apaga o trabalho — espera terminar o que está rodando, guarda todas as abas e devolve depois
- `d574283` V286: arquivo aceito no mesmo formato em todas as abas (verde claro, barra verde, texto escuro); cabeçalho dos resultados da Impressão Casada e Multi obra no tema da Tela inicial
- `fa34a58` V285: Impressão Casada e Multi obra — arquivo aceito em verde (✓), mesmo formato do aviso das pastas raiz
- `8e398b0` V284: Impressão Casada | Multi obra — botão Limpar no Relatório do Lantek
- `62ff567` V283: Impressão Casada - ERP — Limpar no PDF das Ordens e na Conferência por CNC; Atualizar apaga todos os dados da aba (também no Python)
- `f1a5b1e` V282: arquivos gerados em todas as abas vão para a pasta Downloads do usuário (Produção, Conversor CAM, salvar como)
- `3dc1d44` V281: Multi-Obra trazida do app da rede — CNC com peças de várias obras, bloqueio Lantek com 'gerar mesmo assim', PDF já A4 não é reescrito
- `e4c40cc` V280: nome da Base gerada = PPCPM_Programação-Fábrica_Sistema.ppcpm_LOTE_<lote>_<aammdd>
- `096ab71` V279: Listar PCT confere cada obra lida com as OF-TRECHO da planilha de pacotes (2170-22-01 lido errado vira 2170-2-01)

## 2026-11-25

- `3c99f5e` V278: Base gerada — Alterar Fonte de Dados em cada tabela dinâmica (DBF!$A$9 até a última linha com dado) e atualizar todas; filtros PREP_Lista (X) e CDI (LIC, vazio); Classificar com cabeçalho e níveis salvos na DBF
- `45bbc7f` V277: Base gerada — tabelas dinâmicas leem DBF!$A$9 só até a última linha com dado; classificação só nas linhas de dado + recálculo completo antes de atualizar
- `2ea2614` V276: quadro de aviso da Base gerada lista as atualizações da planilha (DBF classificada, tabelas dinâmicas, filtros, data, abas)
- `2508f28` V275: Planilha Base — regras fixas do vídeo: classifica a DBF, filtros fixos (CDI, CLEBER, Quadro), data H5 da PREP_Lista, nomes e cores das abas (FOCCO_VISION_NDPCP399)
- `329999f` V274: Agrupador | Base — botão Listar PCT ao lado das obras (lê o print e lista as OF-TRECHO em Obra(s)); digitar à mão continua
- `52d5b48` V273: Agrupador | Base — pastas raiz das obras fixas no sistema + aviso quando o PC não acessa

## 2026-11-24

- `20d77e0` V272: Agrupador | Base — ícone da Base fixa (banco de dados com cadeado, no padrão do sistema) no lugar do emoji
- `1152406` V271: Agrupador | Base — a base gerada vai para a pasta Downloads do usuário
- `6318807` V270: Agrupador | Base — cabeçalho da tabela do consolidado no tema da Tela inicial (cinza claro, texto preto)
- `b88d532` V269: Agrupador | Base — andamento e relógio do tempo ao lado de Atualizar a planilha LANTEK_SKA agora
- `6bdd9b1` V268: planilha LANTEK_SKA rev.02 dentro do sistema (cópia de trabalho em dados_locais quando o Google Drive não está no PC)
- `3fd18b8` V267: Agrupador | Base — Base fixa rev.22 dentro do sistema; quadro Planilha Base só com a Base fixa
- `b015e59` V266: janelas de pergunta (ex.: Atualizar) com botões no padrão do sistema, iguais ao Buscar e Carregar
- `94f0347` V265: Agrupador | Base — andamento (Gerando / Cruzando resultados…) também ao lado de DBFs a agrupar
- `598fa8b` V264: Análise DBF x FOCCO — o nome do arquivo de saída se atualiza a cada Analisar (OF/trecho da DBF/relatório)
- `cf22d25` V263: Tela inicial — coluna Observação editável (fica no servidor, não mexe na planilha)

## 2026-11-23

- `c0c4bc2` V262: Impressão de Etiquetas — COD ITEM TB_PREP vira o setor TUBO (etiqueta própria, como PERFIL L / PERFIL SOLDADO / PERFIL U/C)
- `1027f26` V261: Visualizador DXF e Criar Pasta / Auditoria rodam dentro da aba — os 7 apps da Preparação fábrica no padrão do sistema
- `1b2ceea` V260: Renomear DXF, Conversor CAM → DXF, Espelhar DXF e Corte Inteligente rodam dentro da aba
- `9244f1c` V259: Roteirizador DXF roda dentro da aba (Roteirizador, Relatório de divergências, Peso por fluxo, Verificador)
- `71eaa72` V258: janela Verificação da instalação (e Alteração de LOTE / Bloco de notas) volta a ser arrastável
- `edbcdd2` V257 / pacote 44: menu Planejamento vira Preparação fábrica com 7 apps (Roteirizador, Renomear, Conversor CAM, Espelhar, Corte Inteligente, Visualizador, Criar Pasta/Auditoria)
- `72f4b95` docs: documento de requisitos do fluxo de trabalho e padrões (para reutilizar em projeto novo)

## 2026-11-19

- `0720169` V256: Etiquetas — sem o aviso Impressão enviada depois de imprimir (a confirmação antes já basta)
- `5355b37` V255: Etiquetas — Confirmar impressão no modelo do sistema (impressora em etiqueta, Esc/Enter), arrastável
- `e9d432f` V254: Etiquetas — IMPORTAR DADOS já vai direto para Emitir etiqueta; sai o botão Ir para Emitir etiqueta
- `7603414` V253: quadros Impressão enviada e Formato inválido/erro com a faixa colorida em cima do título (mesmo padrão da Selecionar impressora)
- `7b0a802` V252 / pacote 43: Selecionar impressora no modelo novo (busca, tabela Impressora/Conexão/Situação, grupos Etiquetas/Documentos/Arquivo, faixa azul em cima)
- `672fd53` V251: Etiquetas — aviso 'Impressão enviada' no modelo do sistema (contador, pacote/etapas, impressora) com botão Reimprimir
- `eda0d3a` V250: Etiquetas — barra de situação (importadas · pacote · operador · impressora) no resumo; sai o selo de etiquetas e a linha de status abaixo
- `087304d` V249: Etiquetas — resumo da importação aparece dentro do quadro 1 (padrão 'Carregado com sucesso'), sem janela por cima
- `d79a6f6` V248: Etiquetas — resumo da importação no modelo novo (faixa verde, tabela com ícones, botão Ir para Emitir etiqueta)
- `f983cbb` V247: quadro 'Formato de documento inválido' no modelo novo em todas as abas (arquivo recusado e erros de arquivo do sistema), com 'Escolher outro arquivo'
- `ea0dacc` Pacote 42: instalação de bibliotecas mais rápida — pymupdf fixo em 1.x (2.x baixava onnxruntime/layout, +100 MB) e opcionais instaladas por último

## 2026-11-18

- `09e2002` V246: Entrar com Google + e-mail corporativo cria/ativa o cadastro sozinho (sem chave); cadastro normal continua igual
- `731cad7` V245: com zoom próprio, janelas e abas se reajustam inteiras (altura/largura da tela divididas pelo zoom)
- `53b856c` V244: zoom próprio em todas as abas (Ctrl+rodinha / Ctrl +/−/0 sobre a aba), sem mexer na tela principal
- `d38656d` V243 / pacote 41: Alteração de LOTE sem barras de rolagem; janelas separadas com zoom próprio (Ctrl+rodinha, Ctrl +/−/0)
- `8f0a9a6` V242: Alteração de LOTE — Impressa/Pendente no modelo da Tela inicial (selo branco com bolinha)
- `5cb0716` V241: Alteração de LOTE no padrão do sistema (quadros com faixa de título, tabela clara, selos com ícone, faixa colorida por obra)
- `4e608c1` V240 / pacote 40: só um aviso de atualização — o app instalado também usa a Atualização obrigatória
- `96102bf` V239: Blocos de notas — botões no tema claro com letra preta, Salvar .txt azul, ícone do título branco
- `90511e8` V238: Blocos de notas — botão Listar PCT lê o print do pacote (OCR) e preenche OBRA/DBF/Nº PEDIDO/LIBERAÇÃO por obra
- `8f357c6` V237: ajuste automático da altura da aba preservando o tamanho original (sem barra de rolagem de fora)
- `66a1447` V235: barra de rolagem da janela — menu sem altura fixa e área da aba se ajusta sozinha ao tamanho real da tela
- `1285e89` V234: Gerenciamento de roteiro - ERP com o Sistema online ao lado do Atualizar e título no centro
- `fe36a15` V233: botão Atualizar de todas as abas no tema dos botões
- `640119c` V232: menu lateral não aumenta mais a janela (sem barra de rolagem de fora em nenhuma aba)
- `d0777a3` V231: Regras em massa (Alteração / Gerenciamento de roteiro) no tema dos quadros, abas e filtros
- `5189caf` V230: avisos de erro no idioma escolhido pelo usuário (pt/en/es) em todas as abas
- `c7933a8` V229: Análise DBF × Focco — títulos das colunas da tabela no centro
- `e05fd77` V228: Tela inicial — tabela um pouco mais baixa para não aparecer barra de rolagem na janela
- `2ba3717` V227: aviso de Atualização obrigatória no tema Projeart (Agora como padrão, contagem, salva e restaura a tela)
- `b1fcc17` V226: cabeçalhos das tabelas (Roteiros, Etiquetas, Engenharia…) no tema dos botões
- `1a4aed5` V225: Tela inicial — seletor do pacote no modelo do Fluxo alvo
- `4a1d4a6` V224: quadros no modelo do Agrupador em todas as abas (Produção, Análise DBF, Roteiros, Intranet, Etiquetas, Engenharia)
- `b185165` V223: Impressão Casada - ERP — quadros, cartões e listas no mesmo modelo do Agrupador
- `1d3cac7` V222: Agrupador | Base — corpo dos quadros na cor do fundo da página
- `3020061` V221: Roteirização — fundo do quadro na mesma cor do fundo da página
- `d067470` V220: Roteirização produção — quadros no mesmo modelo do Agrupador
- `910ac34` V219: Agrupador | Base — quadros no modelo cinza com faixa de título
- `de92930` V218: Tela inicial — faixa da planilha volta com a borda azul; trocar planilha / ler agora no modelo anterior
- `151083f` V217: Tela inicial — faixa da planilha, botões e busca no tema dos botões
- `d950645` V216: Etiquetas — PERFIL SOLDADO vira uma etiqueta só por pacote, sem obra (igual PERFIL L)
- `a4aaf4f` V215: cartões de KPI da Produção no padrão do sistema (ícones de linha, número grande)
- `2963997` V214: Tela inicial — cabeçalho da tabela no tema dos botões
- `1b906b3` V213: todos os botões das abas no tema cinza-azulado claro com letra preta (mesmo do Agrupador)

## 2026-11-17

- `11ebf79` V212: Tela inicial — nomes do cabeçalho da tabela no centro, negrito
- `b3d9ae7` V211: Tela inicial — Alteração de LOTE no modelo dos botões do Agrupador; cabeçalho com letra preta
- `d252990` V210: Roteirização produção — Últimos usados (abre de novo com um clique)
- `cf1b16c` V209: Agrupador — todos os botões e o Nome do Lote no mesmo modelo
- `b911c4f` V208: Agrupador — Adicionar/Testar pasta no mesmo modelo e botões um pouco mais fortes
- `45b74b7` V207: Agrupador — botões principais no modelo claro
- `d437c88` V206: Agrupador — caminho do arquivo aceito fica verde (base, fluxos, FOCCO, SKA)
- `98cc9e8` V205: botões cinza de Produção com a letra preta
- `8d4cfeb` V204: janelas de escolher pasta/arquivo no modelo novo (ícone, separador, validação)
- `b86bb59` V203: Verificação da instalação no modelo novo (e listas de arquivos no mesmo padrão)
- `0a6d373` V202 / pacote 39: Produção com a lógica nova do Validador de Fluxos
- `9e0e58a` V201: Agrupador | Base — cabeçalho da tabela na cor do botão, letra preta
- `b7c4575` V200: Agrupador | Base — cabeçalho da tabela com borda no tema do sistema, letra preta
- `25b8237` V199: Gerar relatórios — arquivo aceito em verde, seletor de pasta do sistema e avisos no padrão
- `4501244` V198: Gerar relatórios — arquivo do Focco aparece embaixo, no mesmo estilo da lista de pastas

## 2026-11-16

- `e4671a4` V197: status das etiquetas no mesmo estilo da Tela inicial
- `e0e6ce4` V196: Impressão de Etiquetas no modelo novo (ícones, tabela, status)
- `24aab8d` V195: Acesso ao Intranet no modelo da imagem 01
- `09ecd66` V194: Alteração de Roteiros no modelo da imagem 02 (tabela no mesmo padrão também no Gerenciamento ERP)
- `ed361f5` V193: Impressão - FLUXO 04 no padrão da imagem 01
- `5943b3d` V192: Impressão Grupo - LIC no padrão da imagem 01
- `876f091` V191: Impressão Casada no padrão da imagem 02
- `f33b3fc` V190: aba Gerenciamento de roteiro - ERP no modelo da imagem 01
- `61c9c92` V189 / pacote 38: nova aba Gerenciamento de roteiro - ERP
- `99f6a52` V188: Impressão de Etiquetas — avisos e Selecionar impressora no modelo do sistema
- `093e8e0` V187: padrão novo (quadros brancos, faixa azul, borda leve, botões cinza-azulado) em todas as abas restantes
- `3eb21aa` V186 / pacote 37: pastas raiz fixadas acham a pasta em qualquer letra (caminho de rede + troca de letra)
- `7c9dc3c` V185: Agrupador | Base — pastas raiz fixadas no servidor para todos os usuários e PCs
- `5e06b21` V184: janelas Blocos de notas e Alteração de LOTE acompanham o tema do sistema (escuro/claro)
- `da9f253` V183: Blocos de notas próprio do sistema (janela própria, abas, salvar/abrir .txt, localizar/substituir, zoom)
- `c7bc241` V182 / pacote 36: botão Blocos de notas em Obras para validar (abre o Bloco de Notas do Windows)

## 2026-11-13

- `b889241` V181: avisos e confirmações no mesmo padrão do aviso de erro (botão cinza-azulado com borda)
- `c75c6c7` V180: avisos de erro no padrão SISTEMA PPCPM - ERRO (faixa vermelha, frase principal e explicação)
- `7aca673` V179: Análise DBF × Focco no padrão novo (quadros brancos, faixa azul, borda leve, botões cinza-azulado)
- `569ef46` V178: menu — grupo aberto dentro de um quadro com borda
- `8db7abc` V177: Agrupador | Base — leve borda preta em todos os quadros (faixa azul mantida)
- `a37470c` V176: Agrupador | Base no padrão novo (quadros brancos, faixa azul, botões cinza-azulado)

## 2026-11-12

- `7d49188` V175: 'só obras em revisão' no mesmo estilo do botão Revisão
- `454228d` V174: etiqueta 'veio do lote' no mesmo estilo (bolinha e borda)
- `f82fafc` V173: leve borda preta nos quadros da Tela inicial
- `608bbf1` V172: Tela inicial — cabeçalho da tabela cinza-azulado e barra da planilha com faixa azul
- `be84f95` V171: etiquetas com bolinha de cor e borda (Tela inicial e Alteração de LOTE)
- `d2946c7` V170: botão Revisão quadrado (Tela inicial e Alteração de LOTE)
- `021128f` V169: etiquetas quadradas também na Tela inicial
- `18f9252` V168: etiqueta Impressa/Pendente quadrada na Alteração de LOTE
- `c9aaa5e` V167 / pacote 35: verificação da instalação — o sistema avisa o que falta no PC e oferece para instalar
- `17be270` V166: pacote selecionado e botão Alterar lote na cor do cabeçalho
- `27ccd2a` V165: cabeçalho da Alteração de LOTE no formato de cores pedido
- `cbf1be1` V164: janela Alteração de LOTE com ícone da Projeart e sem o X duplicado
- `24b44c5` V163: Alteração de LOTE abre em janela própria (pode ir para a segunda tela)
- `4148d64` V162: Alteração de LOTE — janela para mover obras (revisadas) para outro lote
- `1528d72` V161: Observação obrigatória ao colocar obra em revisão e card % impresso obras revisão
- `6ab9639` V160: Tela inicial — tabela única Pacote para revisão, coluna Revisão e quadro Obras para revisão
- `cf045ba` V159: quadro Obras para validar ligado direto no pacote 9999

## 2026-11-11

- `4f62fa2` V158: tema claro — menu lateral e Sistema online visíveis
- `dc1d26f` V157: quadros de aviso no modelo Modal Azul Projeart
- `1ad5cae` V156 / pacote 34: botão Atualizar da Tela inicial zera os pacotes para colocar uma planilha nova
- `84b9845` V155: Tela inicial alinhada e botões trocar planilha / ler agora com borda e sombra
- `5c93b70` V154: Tela inicial — Selecionar todos, filtro TODOS, Obras para validar (coluna D), pesquisa no tema do sistema
- `37928a3` V153: Tela inicial — Pesquisar obra (uma ou várias) e botão Atualizar
- `6ac0fdb` V152 / pacote 33: Tela inicial ligada à PLANILHA DE CONTROLE DE PACOTES ENTREGUES (filtro de pacote, marcação de impresso, % e lista de obras)
- `8c0ee51` Pacote 32: ícones do painel da esquerda da janela de arquivos maiores
- `ffd8516` V151: borda azul das janelas de aviso mais grossa
- `cf0cb7f` V150: borda das janelas de aviso na cor azul do sistema
- `bacacb8` V149 / pacote 31: filtro por coluna na janela de arquivos (como no Explorador); tira os botões Atualizar de dentro das telas
- `0595b3a` Pacote 30: painel da janela de arquivos se ajusta ao maior nome; alça visível; nome completo no balão
- `28fb854` Pacote 29: janela PPCPM - ARQUIVOS com colunas e painel ajustáveis (cursor ↔), tamanho guardado por usuário
- `30f398d` V148: janelas de aviso/pergunta podem ser arrastadas pelo título (abrem no centro; duplo clique volta ao centro)
- `746dd05` V147: pergunta do Atualizar e avisos rápidos no centro, no padrão SISTEMA PPCPM
- `d3e695c` V146: botão Atualizar (modelo claro com ícone) em todas as abas, ao lado do Sistema online
- `b4abf20` V145: telas ficam vivas ao trocar de aba (não perdem dados); botão ATUALIZAR na Multi obra zera a tela
- `101d424` V144: pendências Lantek mostram a obra ao lado de cada posição
- `e30e7e2` V143: Multi obra/Impressão casada — pendência Lantek considera posição + obra (OF/trecho) + lote da ordem
- `8f63d96` V142: tira Capacidade, Indicadores e Relatórios do menu; Qualidade / RNC vira Planejamento RNC

## 2026-11-10

- `986a5ea` V141 / pacote 28: base preenchida sempre pelo Python (aceita fórmulas compartilhadas/matriz); janela nunca monta base grande
- `6d986f9` V140: menu 'Gerar relatórios das ordens'
- `5ce3516` V139 / pacote 27: Gerenciador de roteiros (Relatório de Ordens x Fluxos) no grupo Gerenciador de Roteiros, acima de Alteração de Roteiros
- `b520003` V138 / Python pacote 26: Gerar Base Preenchida montada pelo Python do sistema (sem Out of Memory)
- `aefa5d2` V137: Gerar Base Preenchida sem estourar a memória (aba DBF escrita direto no XML, linha por linha)

## 2026-11-09

- `0b2524f` V136: Etiquetas — filtros digitáveis e setor PERFIL SOLDADO (aba PS PREP, COD ITEM = PS_PREP)
- `7a691e4` Python pacote 25: cópia do drive não se atualiza nem mexe no atalho; gerado/ se recupera sozinho
- `8bafc4b` Python pacote 24: desliga o modo Selecionar da janela preta (pausava o sistema e a atualização)
- `0a4c9ce` Python pacote 23: atualização não trava com 'Acesso negado' em gerado_velho
- `cb7388a` V135: botão Entrar com Google na tela de login (mesma conta do cadastro aprovado)
- `77d5d50` V134: tira a frase da animação obrigatória para quem não é administrador
- `b5ec8b7` V133: botão da animação só para o administrador; administrador principal libera/tira acesso de administrador na aba Usuários
- `2c1a764` V132: pacote atual 700 (teste de atualização)
- `b152caa` Python pacote 22: INSTALAR copia sempre para o PC (mesmo do drive da rede), cria o atalho e instala as bibliotecas
- `26072db` Python pacote 21: atalho da Área de Trabalho volta sozinho; .venv copiado de outro PC é recriado na instalação

## 2026-11-06

- `eb95de0` V131: busca automática por obra acha a pasta da obra mesmo abaixo de subpastas
- `2b0c0bd` Python pacote 20: o Acesso rápido do Windows não trava mais "Adicionar arquivos" / "Adicionar pasta"
- `fc514c7` V130: etiqueta do PERFIL L / PERFIL U/C sem o 1º traço e com o nome mais para baixo
- `b71ebb3` V129: PERFIL L e PERFIL U/C — todas as obras num saco só (uma etiqueta com só o nome)
- `098adc6` V128: filtro PERFIL L junta a mesma obra de L1 e L2 numa etiqueta só
- `d4b494f` V127: Impressão de Etiquetas — filtro "PERFIL L" (PERFILADEIRA L1 + L2)
- `d814b13` V126: tela de login não fica mais "travada" no botão girando

## 2026-11-05

- `0c9fc18` Python pacote 19: escolher pasta sem o aviso "Permitir que este site veja e copie arquivos?"
- `77fe92a` Python pacote 18: PPCPM - ARQUIVOS com pastas fixadas e seleção de vários arquivos (como no Explorador)
- `e35128b` Python pacote 17: janela PPCPM - ARQUIVOS no estilo do Explorador de Arquivos (Windows 11)
- `3fbecef` V125 + Python pacote 16: VISUALIZAR 3D abre como janela de aplicativo (sem barra de endereço)
- `11c929b` V124: VISUALIZAR 3D lê arquivos .CAM da máquina (formato ENTITY4)
- `8f66ba5` V123: VISUALIZAR 3D usa a legenda do desenho (nome do arquivo, soldas e emendas)
- `ea6fca8` V122: VISUALIZAR 3D mostra as furações (furos de verdade + destaque laranja)
- `35c0fd2` V121: VISUALIZAR 3D lê desenhos com texto em traços (AutoCAD SHX) e monta estruturas (viga mestra / treliça)
- `276b1d5` V120 + Python pacote 15: VISUALIZAR 3D na aba Engenharia
- `0b4cb05` V119: nova aba Área de impressão › Engenharia — desenhos PDF de pastas, .zip (e zip dentro de zip), busca por obra na pasta da engenharia (Python), ver, imprimir e baixar juntos
- `b940a7c` Python pacote 14: atualização mais rápida — confere a cada 1 minuto pela Vercel (sem o cache de 5 min do GitHub)
- `8e9168a` Python pacote 13: sistema abre como aplicativo (sem barra de endereço) e janela PPCPM - ARQUIVOS sem about:blank
- `cf41e40` V118: animação na tela de login — carregando no ENTRAR, erro (card treme e campos vermelhos), sucesso (✓ BEM-VINDO verde e card sumindo)

## 2026-11-04

- `06785c9` Python pacote 12: janela PPCPM - ARQUIVOS separada do navegador (arrasta para o outro monitor, reabre onde ficou)
- `c09dcfb` V117: nova aba Produção › Relatórios dos fluxos (Relatório de Ordens x Fluxos, pg13)
- `3be7131` V116: regras de impressão das etiquetas — saquinho, Preparação obra por obra (máquinas em sequência), Não Preparação obra por obra (setor por setor); filtro Etapa
- `6df9449` V115: Impressão de Etiquetas lê o Relatorio_Ordens_Fluxos_LOTE_xxx.xlsx
- `71e25cd` V114 + Python pacote 11: Impressão de Etiquetas direto na Zebra pelo cabo
- `7a8dd26` Python pacote 10: ícone do atalho fixo e atualização arquivo por arquivo (o ícone não some mais)
- `9acc5d2` V113: remove a aba Validação de Peso | Análise; Análise da DBF X Focco - ERP passa para Processo de validação
- `73dc1c2` Python pacote 9: aviso de versão nova também para atualizações do Python; confere a cada 5 minutos
- `e8c8025` Python pacote 8: abrir .zip/.tar/.7z/.rar como pasta na janela PPCPM - ARQUIVOS
- `e43a3f3` Python pacote 7: ícones e textos da barra da janela PPCPM - ARQUIVOS em branco

## 2026-11-03

- `4b4b5a6` Python pacote 6: botão Sair com [S] Sim encerra o sistema por completo neste PC
- `51eebd1` Python pacote 5: janela PPCPM - ARQUIVOS redimensionável, título central no tema do sistema, ícones corporativos
- `b1bee49` Python pacote 4: instalador e abertura sem PowerShell (Bitdefender da empresa bloqueia)
- `0c4715a` Python pacote 3: Arquivos do PC em todos os programas, atualização automática HTML+Python, bibliotecas por seção, instalador com atalho
- `58202df` README: ajusta diagrama
- `8044bc5` Python sem instalações: servidor só com biblioteca padrão, ABRIR_SISTEMA.bat acha o Python sozinho ou baixa um portátil (PC da empresa)

## 2026-10-31

- `cf2e401` Python: ABRIR_SISTEMA.bat para abrir pelo CMD/Terminal do Windows e opção --rede
- `9754e17` V112: lista de Obras com colunas Obra, Sub-trecho, Pacote e Status; obra para impressão em uma linha
- `c318eb6` V111: obra 2139-5-01 em Obras para impressão, aviso de versão nova/atualizada no login e pasta python/ (gerador + app Flask)

## 2026-10-29

- `9c4932c` V110: adiciona Terça Z na barra de Roteirização
