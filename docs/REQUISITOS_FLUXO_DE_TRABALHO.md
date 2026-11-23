# Documento de Requisitos — Fluxo de Trabalho e Padrões do SISTEMA PPCPM

> **Para que serve este documento:** registrar, com detalhe, **como** o SISTEMA PPCPM (Grupo Projeart) é construído, publicado, testado e mantido, para que um **projeto novo** siga exatamente o mesmo fluxo e o mesmo padrão visual.
> Ele vale como guia para quem desenvolve (pessoa ou Claude). Situação de referência: **Versão 256 (HTML) / pacote Python 43**, novembro de 2026.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Arquitetura](#2-arquitetura)
3. [Estrutura de pastas e arquivos](#3-estrutura-de-pastas-e-arquivos)
4. [Fluxo de cada mudança (o ciclo de versão)](#4-fluxo-de-cada-mudança-o-ciclo-de-versão)
5. [Versionamento](#5-versionamento)
6. [Testes e conferência](#6-testes-e-conferência)
7. [Publicação e atualização automática](#7-publicação-e-atualização-automática)
8. [Segurança e restrições obrigatórias](#8-segurança-e-restrições-obrigatórias)
9. [Login, cadastro e banco de dados](#9-login-cadastro-e-banco-de-dados)
10. [Padrão visual (tema do sistema)](#10-padrão-visual-tema-do-sistema)
11. [Padrão das janelas de aviso (quadros)](#11-padrão-das-janelas-de-aviso-quadros)
12. [Comportamentos globais obrigatórios](#12-comportamentos-globais-obrigatórios)
13. [Bibliotecas e instalação nos PCs](#13-bibliotecas-e-instalação-nos-pcs)
14. [Comunicação com o usuário](#14-comunicação-com-o-usuário)
15. [Checklist de cada versão](#15-checklist-de-cada-versão)
16. [Como adaptar para um projeto novo](#16-como-adaptar-para-um-projeto-novo)

---

## 1. Visão geral

| Item | Como é no SISTEMA PPCPM |
|---|---|
| Objetivo | Sistema operacional de PCP (Planejamento e Controle da Produção) com várias abas/programas |
| Dono / quem pede mudanças | Wadson (PCP), sempre em português do Brasil |
| Versões do sistema | **Duas, sempre iguais na tela:** (1) **HTML** publicado no Vercel e (2) **Python** instalado nos PCs |
| Fonte única da verdade | O arquivo **`index.html`** na raiz do repositório |
| Banco e login | Supabase (Postgres + Auth + Edge Functions) |
| Hospedagem do HTML | Vercel, publicando sozinho a cada envio ao GitHub |
| Repositório | GitHub (`lima-prog/ws`), branch `main` |

**Requisito central:** qualquer mudança é feita **uma vez** no `index.html`; a versão Python é **gerada** a partir dele. As duas versões nunca podem divergir.

---

## 2. Arquitetura

```
 Pedido de mudança (texto + print)
          │
          ▼
 index.html  ──► git push (main) ──► Vercel publica o HTML (link público com login)
          │
          └─► python/gerar_python.py separa o index.html em partes ──► python/ppcpm/gerado/
                                                                         │
 PC com o sistema instalado ◄── atualizador confere a cada 1 minuto ◄─────┘
 (C:\Users\<usuário>\SISTEMA-PPCPM)   • HTML novo   → regenera as partes
                                      • pacote Python novo → baixa o .zip, troca e reabre
                                      • GitHub bloqueado → pega da Vercel

 Navegador ──► app.py (127.0.0.1:5000) ──► página + ponte.js em cada aba
                  │
                  ├─► /api/pc/...   arquivos do PC (somente local)
                  ├─► /api/prod/... motor Python das abas de Produção (somente local)
                  └─► login e dados: Supabase (o mesmo do HTML)
```

### 2.1 O `index.html`
- Contém a casca do sistema: tela de login, cabeçalho, menu lateral, Tela inicial, avisos e o tema.
- **Cada aba/programa** fica embutido como um bloco:
  ```html
  <script type="text/plain" id="src-pgN"> ...HTML completo da aba... </script>
  ```
  e é aberto num `<iframe srcdoc>` quando o usuário entra na aba.
- **Regra crítica:** dentro de um módulo nunca pode existir `</script` literal. Escrever `<\/script>`. O módulo termina no primeiro `\n</script>` após o início.
- O menu é definido por duas listas: `PROG` (id, nome no menu, título da página) e `GRP` (agrupamento das abas no menu, ex.: `rot:['pg13','pg10','pg15','pg11']`).
- Recursos comuns (tema dos botões, quadros, zoom, tradução de erros, filtro de arquivos) são **injetados em todas as abas** no momento de montar o `srcdoc` — nunca copiados aba por aba.

### 2.2 A versão Python (`python/`)
- `app.py`: servidor só com a biblioteca padrão do Python (abre em `http://127.0.0.1:5000`).
- `gerar_python.py`: separa o `index.html` em `ppcpm/gerado/` (molde, CSS, JS, módulos) e **confere que a remontagem é idêntica**.
- `ppcpm/web/ponte.js`: liga as abas ao PC (janela "ARQUIVOS DO PC", impressão Zebra, aviso de atualização).
- `ppcpm/atualizador.py`: atualização automática (GitHub e Vercel como reserva).
- `ppcpm/producao/`: abas de Produção rodando a lógica Python original de forma *headless* (um PyQt5 "falso" registra o estado dos widgets e a página web desenha esse estado).
- `dados_locais/`: o que é só daquele PC (favoritos, recentes, logs). **A atualização nunca apaga.**

---

## 3. Estrutura de pastas e arquivos

| Caminho | Função |
|---|---|
| `index.html` | Sistema inteiro (fonte da verdade) |
| `versao.json` | `{"versao": "Versão N", "publicado": "<ISO UTC>"}` — lido pelo aviso de atualização |
| `versao_python.json` (raiz) e `python/versao_python.json` | `{"pacote": N, "data": "...", "notas": "..."}` — **os dois iguais** |
| `vercel.json` | Cabeçalho `Cache-Control: public, max-age=0, must-revalidate` (sempre a versão nova) |
| `python/app.py` | Servidor local |
| `python/gerar_python.py` | Gerador + conferência |
| `python/testes/test_sistema.py` | Testes automáticos (pytest) |
| `python/ppcpm/bibliotecas.py` | Lista oficial de bibliotecas por seção (gera `python/bibliotecas/*.txt`) |
| `python/ppcpm/instalacao.py` | Instalação de bibliotecas pela tela do sistema |
| `python/*.bat` | `INSTALAR`, `ABRIR_SISTEMA`, `VERIFICAR_SISTEMA`, `INSTALAR_BIBLIOTECAS`, `BAIXAR_PACOTES_OFFLINE` |
| `docs/` | Documentação (este arquivo) |

---

## 4. Fluxo de cada mudança (o ciclo de versão)

Toda mudança, por menor que seja, segue **sempre** esta sequência:

1. **Entender o pedido.** Normalmente vem com um print com as partes marcadas em vermelho e um texto curto. Ler o print com atenção: o que está marcado é o que muda; o resto **não mexe**.
2. **Localizar no código.** Achar a aba (`src-pgN`) ou a casca. Nas abas de Produção, editar as fontes de montagem e remontar.
3. **Alterar o `index.html`** com a menor mudança possível que resolva o pedido.
4. **Subir a versão:** `const VERSAO='Versão N+1'` no `index.html` **e** `versao.json` (com `publicado` em UTC).
   - Se mudou qualquer arquivo de `python/` que não seja gerado (ex.: `ponte.js`, `zebra.py`, `instalacao.py`), subir também o **pacote** nos **dois** `versao_python.json`.
5. **Gerar e conferir:** `cd python && python3 gerar_python.py` → tem que imprimir **"Conferência: remontagem IDÊNTICA ao index.html"**.
6. **Testar:** `python3 -m pytest -q` (todos passando) **e** teste visual com Playwright (ver seção 6).
7. **Conferir o print do resultado** antes de entregar (abrir a imagem e olhar se ficou igual ao pedido).
8. **Commit e push** na `main`:
   - Mensagem: `VN: <o que mudou, em português>` (+ `/ pacote M` quando houver).
   - Rodapé obrigatório de coautoria (`Co-Authored-By: ...`) e link da sessão, quando houver.
9. **Esperar o Vercel:** repetir `gh api repos/<dono>/<repo>/commits/main/status --jq .state` até `success`.
10. **Responder ao usuário** em português (ver seção 14), **enviando o print do resultado** sempre que ele tiver mandado print no pedido.

> Nunca entregar sem: versão subida, conferência idêntica, testes passando, print conferido e Vercel em `success`.

---

## 5. Versionamento

| Número | Onde | Quando sobe |
|---|---|---|
| **Versão** (HTML) | `VERSAO` no `index.html` + `versao.json` | **Toda** mudança publicada |
| **Pacote** (Python) | `python/versao_python.json` + `versao_python.json` | Quando muda código Python/ponte não gerado |

- Versões são sequenciais e nunca repetem.
- O número aparece no rodapé do sistema ("… · Versão N") — é o jeito de o usuário conferir se o PC já atualizou.
- Ao corrigir algo publicado com problema, **sobe nova versão** (não reescreve a anterior).

---

## 6. Testes e conferência

### 6.1 Automáticos (pytest)
Os testes mínimos que todo projeto deve ter:
- Remontagem do HTML idêntica ao original.
- Número da versão no `index.html` igual ao `versao.json`.
- Gerador funcionando em outra pasta.
- Ponte injetada em todos os programas.
- Regras de negócio da Tela inicial.
- Leitura de pastas/arquivos do PC (com pasta temporária).
- Listas de bibliotecas atualizadas.
- Casos específicos (ex.: ZPL com acento na Zebra).

### 6.2 Visuais (Playwright)
- Subir o app local: `python3 app.py --sem-navegador --sem-atualizar`.
- Abrir com Chromium, **bloquear chamadas externas** (`https`) e simular o login escondendo a tela de login e chamando `go('pgN')`.
- Tirar print da aba alterada (viewport de PC, ex.: 1600×900) e, quando for detalhe, recortar a área.
- Para janelas/quadros: chamar a função do quadro com dados de exemplo e tirar o print.
- Testar interações relevantes: arrastar o quadro, apertar Enter/Esc, digitar na busca, trocar de aba, mudar a altura da janela.
- **Sempre abrir o print gerado** e conferir antes de dizer que está pronto.
- Avisos como "Sistema Buffer" no print de teste são normais (sem internet) e devem ser explicados ao usuário.

---

## 7. Publicação e atualização automática

### 7.1 HTML (Vercel)
- Publica sozinho a cada push na `main`.
- O site é público, mas **só a tela de login** aparece sem conta; os dados ficam protegidos por login + RLS no Supabase.

### 7.2 Aviso "Atualização obrigatória" (único aviso de atualização)
- Aparece no canto superior direito quando há versão nova (checagem do `versao.json`).
- Opções: **Atualizar em: Agora / 1 / 2 / 3 minutos** — **"Agora" é o padrão**.
- Se ninguém mexer em 30 s, agenda sozinho para 3 minutos (contagem com barra vermelha; aviso nos últimos 30 s).
- Etapas: *Salvando o que você estava fazendo → Baixando a versão nova → Reiniciando o sistema*.
- **Salva e restaura** a aba aberta e os campos digitados; depois mostra "Sistema atualizado. Seu trabalho foi restaurado."
- O app instalado (ponte.js) **usa o mesmo aviso** — nunca pode existir um segundo aviso de atualização.

### 7.3 Versão Python nos PCs
- `atualizador.py` confere a cada **1 minuto** (arquivo leve de versão).
- HTML novo → baixa o `index.html` (Vercel primeiro, GitHub de reserva) e regenera as partes.
- Pacote novo → baixa o `.zip` do GitHub, troca os arquivos (sem tocar em `dados_locais/`) e reabre.
- Se o repositório virar privado, o atualizador precisa ser adaptado **antes** (ele depende de GitHub raw/codeload e do Vercel).

---

## 8. Segurança e restrições obrigatórias

1. **Nunca usar PowerShell** em nada do sistema (o antivírus Bitdefender da empresa bloqueia). Usar `.bat`, `cmd` e Python.
2. **Nunca orientar o usuário a desligar o antivírus.**
3. **APIs de arquivos do PC só locais:** aceitar apenas `127.0.0.1`, com cabeçalho `X-PPCPM: 1` e checagem do `Host`.
4. **Modo rede (`--rede`):** outros PCs podem abrir o sistema, mas **nunca** veem os arquivos do PC que serve.
5. **Credenciais e segredos:** quem desenvolve nunca digita, copia ou expõe senhas/chaves pelo usuário; configurar segredos é tarefa do dono. A chave do Supabase no HTML é a pública (anon); a de serviço fica só nas Edge Functions.
6. **Login obrigatório** para qualquer dado; banco com RLS.
7. Mudanças que não podem ser desfeitas (apagar dados, tornar repositório privado, etc.) só com confirmação explícita do dono.

---

## 9. Login, cadastro e banco de dados

- **Login normal:** login + senha (+ "Salvar senha").
- **Cadastro normal (CADASTRE-SE):** login, senha e e-mail corporativo → Edge Function `cadastro` (ação `solicitar`) gera **chave de acesso de 5 minutos** enviada ao administrador; o usuário ativa com a chave (ação `ativar`).
- **Entrar com Google:**
  - E-mail corporativo (`@projeart.ind.br`) e verificado → se for a primeira vez, o cadastro é **criado/ativado sozinho, sem chave** (ação `google`). Login tirado do e-mail (`nome.sobrenome`, com número se repetir), perfil "Usuário".
  - Conta Google de fora do domínio → recusada ("Use o seu e-mail corporativo").
  - Usuário bloqueado continua bloqueado.
  - O administrador recebe e-mail a cada novo usuário criado pelo Google.
- Tabelas principais: `perfis` (id = `auth.users.id`, login único, `ativo`, `aprovado_em`, `admin`) e `solicitacoes`.
- Configurações compartilhadas entre usuários ficam numa tabela de configuração (ex.: pastas raiz das obras), resolvidas por PC via caminho de rede (UNC).

---

## 10. Padrão visual (tema do sistema)

### 10.1 Cores de referência
| Uso | Valor |
|---|---|
| Azul Projeart (faixas, ícones, destaque) | `#0b3d91` (escuro `#082e6e`) |
| Fundo da página das abas | `#eef1f5` |
| Botão padrão (fundo) | `linear-gradient(#e3e8ee, #cdd4de)` |
| Botão padrão (borda / hover) | `#98a3b3` / `linear-gradient(#d9dfe7, #c2cad5)` borda `#808c9e` |
| Faixa de título dos quadros | `linear-gradient(#d7dce3, #c2c9d3)` com linha `#aab2bd` |
| Borda escura dos quadros | `#545659` |
| Campos (input/select) | `linear-gradient(#f3f5f8, #e6eaf0)`, borda `#98a3b3`, texto preto negrito; ao focar fica branco |
| Verde OK / sucesso | `#1e9e4a` · fundo `#dcf5e3` · texto `#15803d` |
| Vermelho erro | `#c62828` · fundo `#fdeeee` · borda `#f1b9b9` |
| Laranja "Validar" | `#ea580c` / `#c2410c` |

### 10.2 Botões
- **Todos** os botões de ação: fundo cinza-azulado claro, borda cinza, **letra e ícone pretos**, cantos 4px, sombra leve.
- Botão desativado: mesmo tema, opacidade ~0,55.
- **Exceções:** abas de navegação (Início/Emitir/Histórico, passos 1/2/3) mantêm o estilo próprio para mostrar a aba ativa; botão principal de uma janela pode ser azul (`#0b3d91`, letra branca) quando o modelo pedir (ex.: "Salvar .txt", "Atualizar agora").
- Botão **Atualizar** do topo de cada aba: mesmo tema dos botões, sempre com o indicador **"Sistema online"** ao lado (verde/amarelo/vermelho).

### 10.3 Quadros (cards) das abas
- Fundo `#eef1f5`, borda `#545659`, **faixa azul de 3px no topo**, cantos 4px.
- Título numa **faixa cinza** própria, com linha separando do conteúdo; badge numerado (1, 2, 3…) em azul.
- Área de arrastar arquivo: fundo `#eef1f5`, tracejado fino `#a3acb8`; ao passar o mouse escurece.
- Aviso de vazio ("nenhum arquivo"): barra cinza `#c9d0d8`, letra preta negrito.
- Arquivo aceito: linha verde clara com "✓ Carregado com sucesso".

### 10.4 Tabelas
- Cabeçalho no tema dos botões (cinza-azulado claro), **letra preta negrito, centralizada**, divisórias `#98a3b3`.
- Linhas brancas alternando com `#f6f7f9`; hover `#eef4fb`; selecionada `#dbe8fb`.
- Faixa colorida de 4px à esquerda da linha indicando situação (verde impressa, laranja validar, vermelho revisão).
- Situação **Impressa/Pendente**: selo branco com **bolinha colorida** (verde / amarela).

### 10.5 Cartões de indicadores (KPI)
- Ícone de **linha** azul-marinho dentro de um quadradinho claro, rótulo em maiúsculas/negrito, número grande preto.

### 10.6 Tipografia e ícones
- Fonte do sistema (Segoe UI/Roboto/Arial); números de obra em fonte monoespaçada.
- Ícones sempre em SVG de linha (sem emojis coloridos nos quadros novos).

---

## 11. Padrão das janelas de aviso (quadros)

Toda janela/aviso novo segue **o mesmo molde**:

```
┌──────────────────────────────────────────────┐  ← faixa colorida de 4px EM CIMA
│ [ícone]  Título                              │  ← faixa cinza (#f3f5f7 → #d9dee5)
├──────────────────────────────────────────────┤
│  Conteúdo (caixa colorida conforme o tipo,   │
│  etiquetas brancas para nomes de arquivo /   │
│  impressora, tabela com ícones, etc.)        │
├──────────────────────────────────────────────┤
│                        [Botão]  [Botão]      │  ← rodapé cinza, botões no tema
└──────────────────────────────────────────────┘
```

| Tipo | Cor da faixa | Exemplos |
|---|---|---|
| Sucesso | Verde `#1e9e4a` | Impressão enviada, dados importados |
| Erro / recusa | Vermelho `#c62828` | Formato de documento inválido, erro do sistema |
| Pergunta / escolha | Azul `#0b3d91` | Confirmar impressão, Selecionar impressora |
| Atualização | Vermelho | Atualização obrigatória |

Regras:
- **Faixa colorida sempre em cima do título** (não na lateral).
- **Arrastável pelo título** para qualquer lado; duplo clique no título volta ao centro.
- **Teclado:** Enter = ação principal, Esc = cancelar/fechar; mostrar a tecla no botão quando fizer sentido (`Cancelar [Esc]`, `Imprimir [Enter]`).
- Fundo escurecido atrás; foco inicial no botão principal.
- Não mostrar janela de sucesso redundante: se já houve confirmação antes, não exibir outra depois (ex.: impressão).
- Resumos de resultado preferem ficar **na própria tela** (dentro do quadro da etapa) em vez de janela por cima, quando o usuário pedir "mais à vista".

### 11.1 Formato de documento inválido
- Título "Formato de documento inválido"; caixa rosada: "O arquivo selecionado não é compatível com esta etapa e **não foi adicionado**".
- Nome do arquivo em etiqueta; "**Formato aceito:**" por extenso + extensões em selos verdes (`.csv`, `.xlsx`…).
- Botões: **Escolher outro arquivo** (abre o seletor de novo) e **Entendi**.
- Vale para arquivo escolhido **e** arrastado, em **todas** as abas (filtro global pelos `accept`/`data-aceita`).

---

## 12. Comportamentos globais obrigatórios

1. **Sem barra de rolagem na janela principal.** A página tem sempre a altura da janela; quem rola é a área interna (tabela/aba). O menu lateral nunca empurra a página (rola por dentro, sem barra visível). A altura das áreas se ajusta ao tamanho real da janela (escala do Windows incluída).
2. **Zoom próprio por aba e por janela separada** (Ctrl + rodinha, Ctrl +/−, Ctrl 0), salvo por PC, **sem mexer no zoom da tela principal**. Com zoom, tudo que usa altura/largura da tela se reajusta (sem sobrar espaço vazio).
3. **Erros no idioma do usuário** (pt/en/es): mensagens técnicas do navegador/Windows/Python são trocadas por frases claras no idioma escolhido.
4. **Filtro de arquivos global** (seção 11.1).
5. **Janelas separadas** (Bloco de notas, Alteração de LOTE, Arquivos, 3D) seguem o mesmo tema e o mesmo zoom próprio.
6. **Tema claro/escuro:** os quadros e janelas novas mantêm o mesmo visual claro nos dois temas quando o modelo pedir.
7. **Funcionamento nunca muda por causa de ajuste visual.** Pedido de "tema/estilo" mexe só em aparência.

---

## 13. Bibliotecas e instalação nos PCs

- Lista oficial em `ppcpm/bibliotecas.py`, **por seção/aba**, com obrigatórias e **opcionais**.
- A tela "Verificação da instalação" mostra o que falta e instala pela própria tela.
- Instalação em duas etapas: **primeiro as obrigatórias**, depois as opcionais (opcional que falha não derruba a instalação).
- Fixar versões quando uma versão nova trouxer dependências pesadas desnecessárias (ex.: `pymupdf>=1.24,<2`, porque a 2.x baixa +100 MB).
- Sem internet: `BAIXAR_PACOTES_OFFLINE.bat` num PC liberado e copiar a pasta `pacotes`.
- Python 3.12+ pela Microsoft Store (sem administrador) ou python.org com "Add to PATH".

---

## 14. Comunicação com o usuário

- **Sempre em português do Brasil**, linguagem simples, sem jargão técnico desnecessário.
- Começar dizendo o que vai fazer em uma frase; terminar com o resultado.
- **Se o pedido veio com print, responder com print do resultado** (arquivo de imagem).
- Explicar **o que mudou** e **onde**, em tópicos curtos; dizer o que **não** mudou quando houver dúvida.
- Sempre informar: versão publicada, se o Vercel atualizou e que os PCs recebem pela atualização automática.
- Avisar limitações reais (ex.: "testei sem impressora de verdade", "não consegui abrir o Vercel daqui").
- Quando a interpretação do pedido for incerta, dizer qual interpretação foi usada e oferecer o ajuste.
- Perguntar antes de decisões irreversíveis; nas demais, fazer e informar.

---

## 15. Checklist de cada versão

- [ ] Pedido entendido (partes marcadas no print identificadas)
- [ ] Alteração mínima no `index.html` (ou fontes de montagem + remontagem)
- [ ] `VERSAO` e `versao.json` atualizados
- [ ] Pacote Python atualizado (se mudou código Python não gerado) — nos dois arquivos
- [ ] `gerar_python.py` → "remontagem IDÊNTICA"
- [ ] `pytest` todo passando
- [ ] Print com Playwright conferido visualmente
- [ ] Nenhum PowerShell, nenhum segredo exposto, APIs locais protegidas
- [ ] Commit com mensagem `VN: ...` + coautoria
- [ ] Push na `main` e Vercel em `success`
- [ ] Resposta em português com o print do resultado

---

## 16. Como adaptar para um projeto novo

1. Criar repositório no GitHub com a mesma estrutura (`index.html`, `versao.json`, `vercel.json`, `python/`, `docs/`).
2. Ligar o repositório ao Vercel (publicação automática da `main`).
3. Criar o projeto no Supabase: tabelas `perfis` e `solicitacoes`, RLS ativo, Edge Function de cadastro (chave de 5 min + entrada pelo Google com domínio corporativo).
4. Copiar a casca (login, menu, Tela inicial, aviso de atualização, quadros, tema, zoom, filtro de arquivos, tradução de erros) e trocar: nome do sistema, logo, domínio de e-mail permitido, URLs do Vercel/GitHub no `atualizador.py`.
5. Criar as abas como módulos `src-pgN` e registrar em `PROG`/`GRP`.
6. Adaptar `bibliotecas.py` às necessidades das novas abas.
7. Manter os testes mínimos da seção 6.1 desde a primeira versão.
8. Seguir o ciclo da seção 4 e o checklist da seção 15 em **toda** mudança.

---

*Documento mantido junto do código. Ao mudar o fluxo ou o padrão visual, atualizar este arquivo na mesma versão.*
