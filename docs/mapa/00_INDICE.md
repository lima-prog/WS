# MAPA DO SISTEMA PPCPM — Índice (comece por aqui)

> Memória organizada de tudo que foi criado e melhorado no **SISTEMA PPCPM** (Grupo Projeart · PCP · Wadson Lima).
> Situação deste mapa: **Versão 280 (HTML) / pacote Python 57 — 26/11/2026**.
> Cada arquivo é curto e trata de um assunto só: abra **só o que precisar** (economiza tempo e tokens).

## Onde está cada coisa

| Arquivo | O que tem | Quando abrir |
|---|---|---|
| `01_VISAO_GERAL.md` | O que é o sistema, as 2 versões (HTML e Python), onde fica o código, publicação, banco, pastas | Para entender ou explicar o sistema |
| `02_MAPA_DAS_ABAS.md` | Todas as abas do menu: o que fazem, onde está o código, regras de cada uma | Antes de mexer numa aba |
| `03_REGRAS_E_PADROES.md` | Regras fixas (segurança, visual, rotina de versão, Planilha Base, nomes de arquivo) | Antes de qualquer mudança |
| `04_HISTORICO_DE_VERSOES.md` | Lista de todas as versões publicadas (V110 → V280), por data | Para achar quando/como algo mudou |
| `05_PROCURAR_E_RESTAURAR.md` | Como achar algo rápido e como voltar uma versão/arquivo | Quando algo quebrar ou sumir |

## Atalhos de busca (Ctrl+F no arquivo certo)

| Procurando… | Abra | Busque por |
|---|---|---|
| Uma aba (ex.: Etiquetas) | 02 | o nome da aba |
| Quando algo mudou | 04 | palavra-chave ou `V2xx` |
| Regras da Planilha Base | 03 | `PLANILHA BASE` |
| Como publicar versão nova | 03 | `ROTINA` |
| Voltar uma versão | 05 | `VOLTAR` |

## Regra de ouro (para pessoa ou Claude)

1. Toda mudança é feita **uma vez** no `index.html`; o Python é **gerado** dele (`gerar_python.py`).
2. Toda versão nova: subir número, testar, publicar e **acrescentar 1 linha** no `04_HISTORICO_DE_VERSOES.md` (ou regenerar pelo Git).
3. Regra nova combinada com o Wadson → escrever no `03_REGRAS_E_PADROES.md`.

## Onde este mapa fica guardado

- **PC / rede:** `X:\WADSON  LIMA\05  -  MAPA  DO  APP\01  -  MEMORIA  DO  SISTEMA`
- **Dentro do sistema (GitHub):** pasta `docs/mapa/` do repositório `lima-prog/WS`
- **Projeto no Claude:** "SISTEMA PCPM - PROJEART" → `claude/MAPA-SISTEMA-PPCPM.md` (resumo)
