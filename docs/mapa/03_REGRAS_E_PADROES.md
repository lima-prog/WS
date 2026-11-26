# 03 — Regras fixas e padrões (valem para toda mudança)

## SEGURANÇA (obrigatório)
- **Não usar PowerShell em nada** (o Bitdefender da empresa bloqueia). Instalar/abrir é por `.bat` e Python.
- **Nunca** pedir para desligar o antivírus.
- APIs de arquivos só no próprio PC: `127.0.0.1` + cabeçalho `X-PPCPM: 1` + conferência do Host (`_do_proprio_pc()`).
  Quem acessa pela rede (`--rede`) **não** vê os arquivos do Wadson.
- Claude não digita nem copia senhas, chaves ou segredos pelo usuário.
- O repositório GitHub é **público**: o que vai para ele (inclusive planilhas modelo) pode ser baixado por qualquer um.

## ROTINA de cada versão nova
1. Mudar no `index.html` (blocos `src-pgN`; dentro deles escrever `<\/script>`).
2. Subir `VERSAO` no `index.html` e em `versao.json`; se mudou Python não gerado, subir `pacote` nos **dois** `versao_python.json`.
3. `cd python && python3 gerar_python.py` → tem que dizer **"remontagem IDÊNTICA"**.
4. `python3 -m pytest -q` → todos os testes passando.
5. Conferir com prints (Playwright) a tela mudada.
6. Commit **"VNNN: o que mudou"**, enviar ao GitHub e esperar o Vercel ficar `success`.
7. Responder em português; se o pedido veio com print, devolver print do resultado.
8. Acrescentar a versão no `04_HISTORICO_DE_VERSOES.md` (ou regenerar pelo Git).

## PADRÃO VISUAL
- Tema **Azul Projeart + ERP clássico**: faixa/borda azul `#0b3d91`, quadros com faixa de título e borda leve,
  botões cinza-azulado claro (`#f3f5f7 → #d9dee5`, borda `#8f9aa7`) com **letra preta**, cabeçalhos de tabela no tema dos botões.
- Avisos/perguntas: modelo **Modal Azul Projeart** (erro = faixa vermelha), arrastáveis pelo título, teclas Esc/Enter.
- **Arquivo aceito** (todas as abas): fundo verde claro `#f3faf5`, borda `#cfe8d6`, **barra verde à esquerda** `#1e8e3e`, texto escuro em negrito com ✓ (V286).
- Ícones de linha (SVG), sem emoji; Base fixa = ícone banco de dados com cadeado.
- Sem barra de rolagem de fora; tema claro e escuro; avisos no idioma escolhido (pt/en/es).

## PLANILHA BASE (Agrupador | Base → Gerar Base Preenchida) — sempre assim (V275–V278)
Código: bloco "V275 — REGRAS FIXAS" em `validador_fluxos_ppcp.py`; resumo em `producao/base_fixa/REGRAS_GERACAO_BASE.md`.
1. **DBF:** Classificar (linha 9 = cabeçalho, "Meus dados contêm cabeçalhos", níveis salvos):
   OF-TRECHO A→Z › Nº LIBERAÇÃO A→Z › MARCA A→Z › PAI X FILHO Z→A. Depois recalcular tudo.
2. **Tabelas dinâmicas (DBF até RUPTURA MP):** em **cada** tabela, Alterar Fonte de Dados = `DBF!$A$9:<última coluna><última linha COM DADO>` e Atualizar.
3. **Filtros:** PREP_Lista FLUXO PRD = Fluxo 1–4 e FILTRO TD LISTA MAQ. = X; PREP_Quadro tabela PESO POR BC = FLUXO PRD (Tudo);
   CLEBER = "VP c/ Perfil Lam."; CDI = COMPONENTE LIC, ACESSÓRIOS (vazio), PERFIL LAMINADO (vazio),
   GRUPO LIC = ESCADA, ACESSÓRIOS, VIGA/PILARES/SOLDADOS, ACESSÓRIOS BARRA, ACESSÓRIOS SOLDADOS; + filtros das observações "<<<" do modelo.
4. **PREP_Lista H5** = data do dia.
5. **Nomes e cores das abas:** DBF (mantém) · FOCCO_VISION_NDPCP301 → **FOCCO_VISION_NDPCP399** #ACB9CA · PESO X FLUXO #F4B084 ·
   DET. PCT #66FFFF · PREP_LISTA X MAQ X ORD X TRECHO #666633 · PREP_QUADRO GESTÃO A VISTA #7030A0 · CLEBER_TS x VM x VP x PERFIL #FFD966 ·
   CDI_PROG_PCT #CCFF33 · LT #FF0000 · MARLON_POSIÇÃO_PERFILADEIRA #00CC99 · ELVIS_PERFIL_LAM (sem cor) · RUPTURA MP #FF66FF · BD #3399FF · CALENDÁRIO (mantém).
6. **Quadro de aviso** no fim lista cada atualização com ✔/⚠ (só com Excel instalado).
7. **Nome do arquivo:** `PPCPM_Programação-Fábrica_Sistema.ppcpm_LOTE_<lote>_<aammdd>.xlsx`, salvo em **Downloads**.

## Outras regras combinadas
- **Nomes dos PDFs:** Impressão Casada = `impressao_casada_Sistema.ppcm_<aammdd>.pdf`; Multi obra = `impressao_casada_multiobra_Sistema.ppcm_<aammdd>.pdf` (por obra: `..._obra_<obra>.pdf`) (V288).
- **Versão nova nunca apaga o trabalho** (V287): antes de reiniciar, o sistema espera terminar o que está rodando (até 15 min) e guarda tudo (`python/ppcpm/sessao.py` → `dados_locais/sessao_antes_atualizar.pkl`; tela: `ppcpm_trabalho_antes_atualizar`); depois devolve. Só o usuário apaga (Atualizar / Limpar). Aba nova feita só no HTML com dados na memória: criar `window.__ppcpmSalvar()` / `__ppcpmRestaurar(d)`.
- **Todo arquivo gerado vai para a pasta Downloads** do usuário, em todas as abas e todos os PCs (V282) — nunca ao lado do arquivo de origem. Exceção: apps que organizam arquivos no lugar (Renomear, Espelhar, Corte, Visualizador, Criar Pasta) e o envio fixo do Gerenciamento de roteiro.
- Etiquetas: PERFIL L, PERFIL U/C, PERFIL SOLDADO e TUBO = 1 etiqueta por pacote (mesma lógica).
- Base fixa e pastas raiz: fixas no sistema, iguais em todos os PCs; o sistema avisa o que falta no PC.
- Listar PCT existe no Bloco de notas e no Agrupador; digitar à mão continua valendo.
- Telas não perdem dados ao trocar de aba; janelas abrem no centro e podem ir para a 2ª tela.

## APP DA REDE (main.py em X:\ppcp_dxf_ferramentas)
- É outro app (PPCP — Ferramentas — Projeart), separado do SISTEMA PPCPM; o PPCPM tem uma **cópia** do Validador de Fluxos dele.
- Regra do Wadson: **avisar cada mudança** feita no app da rede; ele decide o que leva para o PPCPM. Trazer sempre mantendo as configurações do PPCPM (regras da Base, nome do arquivo, Downloads, pastas fixas).
- Conferência automática: tarefa agendada "Avisar mudanças no app da rede" (seg–sex 07:43), compara com `BASE_APP_REDE.json` nesta pasta.
