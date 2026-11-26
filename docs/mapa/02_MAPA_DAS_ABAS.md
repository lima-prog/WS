# 02 — Mapa das abas (menu do sistema)

> Código de cada aba: no `index.html`, bloco `<script type="text/plain" id="src-pgN">`. Lista oficial: `const PROG=[…]` no `index.html`.
> "Py" = parte que só roda no sistema instalado (Python).

## TELA INICIAL
Ligada à **PLANILHA DE CONTROLE DE PACOTES ENTREGUES.xlsx** (aba LIBERAÇÃO DE PCTS).
- Pacote atual (filtro), % impresso, total realizado; tabela **Pacote para revisão** (OF-trecho, ano-semana, peso, status Impressa/Pendente, Revisão, **Observação editável** — fica no Supabase, não mexe na planilha).
- Pesquisar obra (uma ou várias), Selecionar todos, Obras para validar (pacote 9999).
- **Alteração de LOTE** (janela própria) para mover obras revisadas de lote.
- **Blocos de notas** próprio (abas, salvar .txt, localizar, zoom) com **Listar PCT**: lê o print do pacote (OCR Tesseract.js)
  e cria blocos OBRA / DBF / Nº PEDIDO / LIBERAÇÃO FOCCO | OTM. Desde V279 confere com as OF-TRECHO da planilha (corrige 2170-22-01 → 2170-2-01).

## Produção
| Aba | id | O que faz |
|---|---|---|
| **Agrupador \| Base** | pg2 | Junta DBFs das obras + Relatório de Fluxos + FOCCO ERP + relatório SKA e **gera a Planilha Base Preenchida** (Py, Excel). Base fixa rev.22 dentro do sistema; pastas raiz fixas com aviso de acesso; **Listar PCT** ao lado de Obra(s); LANTEK_SKA atualizada sozinha (com relógio do tempo); saída em Downloads. Regras da Base: ver 03 › PLANILHA BASE. Motor: `producao/motor.py` + `qtfalso.py` executando `validador_fluxos_ppcp.py` (widgets ligados por `data-w`, métodos por `data-m`). |
| Roteirização produção | pg3 | Barra de roteirização (inclui Terça Z), "Últimos usados". |
| Impressão Casada - ERP | pg4 | Impressão casada; pendências Lantek por posição + obra + lote. |
| Impressão Casada \| Multi obra | pg5 | Mesma lógica para várias obras; botão ATUALIZAR zera a tela. |
| Impressão Grupo - LIC | pg6 | Impressão por grupo LIC. |
| Impressão - FLUXO 04 | pg7 | Impressão do fluxo 04. |

## Processo de validação
| Aba | id | O que faz |
|---|---|---|
| Análise da DBF X Focco - ERP | pg1 | Compara DBF × relatório FOCCO; nome do arquivo de saída se atualiza a cada Analisar: `Validação-peso__OF-<of-trecho>___ SISTEMA - PPCPM__<data>`. |

## Gerenciador de Roteiros
| Aba | id | O que faz |
|---|---|---|
| Gerar relatórios das ordens | pg13 | Relatório de Ordens x Fluxos a partir do arquivo do Focco. |
| Gerenciamento de roteiro - ERP | pg15 | Gerencia roteiros do ERP; regras em massa. |
| Alteração de Roteiros | pg10 | Altera roteiros; regras em massa. |

## Área de impressão
| Aba | id | O que faz |
|---|---|---|
| Impressão de Etiquetas | pg12 | Lê `Relatorio_Ordens_Fluxos_LOTE_xxx.xlsx` e imprime direto na **Zebra pelo cabo** (Py). Regras: Preparação obra por obra (máquinas em sequência), Não Preparação obra por obra (setor por setor); **PERFIL L** (L1+L2), **PERFIL U/C**, **PERFIL SOLDADO** (PS_PREP) e **TUBO** (TB_PREP) = 1 etiqueta só por pacote, sem obra; Selecionar impressora; Confirmar impressão (Esc/Enter). |
| Engenharia | pg14 | Desenhos PDF de pastas e .zip (zip dentro de zip), busca por obra na pasta da engenharia, **VISUALIZAR 3D** (SHX, furações, legenda, arquivos .CAM). |
| Acesso ao Intranet | pg11 | Acesso/envio para a intranet. |

## Preparação fábrica (7 apps, rodam dentro da aba — Py)
Backends `python/ppcpm/fabrica_{rot,ren,cam,esp,cor,vis,aud}.py`, carregados por `fabrica_apps.py`; rotas `/api/fabrica/<app>/<ação>`.
| App | id | backend |
|---|---|---|
| Roteirizador DXF (Roteirizador, Divergências, Peso por fluxo, Verificador) | pg22 | rot |
| Renomear DXF | pg19 | ren |
| Conversor CAM → DXF | pg20 | cam |
| Espelhar DXF | pg17 | esp |
| Corte Inteligente | pg18 | cor |
| Visualizador DXF | pg16 | vis |
| Criar Pasta / Auditoria | pg21 | aud |

## Outros itens do menu
- **Planejamento RNC** (antes Qualidade / RNC).
- **Usuários:** aprovação de cadastro, administradores (o administrador principal libera/tira acesso de administrador).
- **Configurações:** tema claro/escuro, idioma dos avisos (pt/en/es), etc.
- **Login:** e-mail e senha ou **Entrar com Google** (e-mail corporativo cria/ativa o cadastro sozinho); animação de entrada.

## Janelas próprias do sistema
PPCPM - ARQUIVOS (explorador de arquivos do PC, Py), Verificação da instalação, Alteração de LOTE, Blocos de notas, VISUALIZAR 3D —
todas arrastáveis, no tema do sistema, com zoom próprio (Ctrl+rodinha, Ctrl +/−/0).
