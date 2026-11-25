# Regras fixas da geração da Planilha Base (SISTEMA PPCPM — Agrupador | Base)

Definidas pelo Wadson (vídeo "ATUALIZAÇÃO DA PLANILHA", 25/11/2026). O sistema faz isso **sempre** que gera a Base
(caminho pelo Excel). O código fica em `validador_fluxos/validador_fluxos_ppcp.py` (bloco "V275 — REGRAS FIXAS").

1. **DBF** — Classificar (A9 até a última linha, "Meus dados contêm cabeçalhos" marcado, níveis salvos na aba): OF-TRECHO (A→Z) › Nº LIBERAÇÃO (A→Z) › MARCA (A→Z) › PAI X FILHO (Z→A).
2. **Tabelas dinâmicas** — em CADA tabela de DBF até RUPTURA MP: Alterar Fonte de Dados = `DBF!$A$9:<última coluna><última linha COM DADO>` (ex.: `$GE$1004`) e Atualizar.
3. **Filtros**
   - PREP_Lista: FLUXO PRD = Fluxo 1, 2, 3 e 4.
   - PREP_Quadro Gestão à Vista: tabela PESO POR BC com FLUXO PRD = (Tudo); as outras ficam com Fluxo 1–4.
   - CLEBER_TS x VM x VP x PERFIL: só "VP c/ Perfil Lam.".
   - PREP_Lista: FILTRO TD LISTA MAQ. = X.
   - CDI_Prog PCT: COMPONENTE x L LIC = LIC; ACESSÓRIOS = (vazio); PERFIL LAMINADO = (vazio); GRUPO LIC = ESCADA, ACESSÓRIOS, VIGA/PILARES/SOLDADOS, ACESSÓRIOS BARRA, ACESSÓRIOS SOLDADOS.
   - Demais filtros: os das observações "<<< Filtrar apenas…" / "<<< Desmarcar filtro…" do próprio modelo.
4. **PREP_Lista** — célula H5 = data do dia.
5. **Nomes e cores das abas**

| Aba no modelo | Nome na Base gerada | Cor |
|---|---|---|
| DBF | DBF | (mantém azul) |
| FOCCO_VISION_NDPCP301 | FOCCO_VISION_NDPCP399 | #ACB9CA |
| Peso x Fluxo | PESO X FLUXO | #F4B084 |
| Det. PCT | DET. PCT | #66FFFF |
| PREP_Lista x Máq x Ord x Trecho | PREP_LISTA X MAQ X ORD X TRECHO | #666633 |
| PREP_Quadro Gestão à Vista | PREP_QUADRO GESTÃO A VISTA | #7030A0 |
| CLEBER_TS x VM x VP x PERFIL | CLEBER_TS x VM x VP x PERFIL | #FFD966 |
| CDI_Prog PCT | CDI_PROG_PCT | #CCFF33 |
| LT | LT | #FF0000 |
| MARLON_Posição x Perfiladeira | MARLON_POSIÇÃO_PERFILADEIRA | #00CC99 |
| ELVIS_Perfil Lam. | ELVIS_PERFIL_LAM | (sem cor) |
| Ruptura MP | RUPTURA MP | #FF66FF |
| BD | BD | #3399FF |
| Calendário | CALENDÁRIO | (mantém) |
