# 01 — Visão geral do SISTEMA PPCPM

## O que é
Sistema operacional de **PCP (Planejamento e Controle da Produção)** do **Grupo Projeart** (indústria metalúrgica).
Dono e quem pede as mudanças: **Wadson Lima (PCP)**. Reúne num lugar só as ferramentas do PCP: análise de DBF × FOCCO,
geração da Planilha Base, roteiros, impressões, etiquetas Zebra, engenharia (PDF/3D) e os apps de DXF da Preparação fábrica.

## As duas versões (sempre iguais na tela)

| | HTML (navegador) | Python (instalado no PC) |
|---|---|---|
| Onde roda | Vercel: `sistemaoperacional-grupoprojeartv92.vercel.app` | `C:\Users\<usuário>\SISTEMA-PPCPM` (atalho **SISTEMA - PPCPM** na área de trabalho) |
| De onde vem | `index.html` (fonte única) | Gerado do `index.html` por `python/gerar_python.py` + módulos `python/ppcpm/` |
| Atualiza | Sozinho a cada envio ao GitHub | Sozinho: confere a cada 1 min e avisa "Atualização obrigatória" |
| Número | `VERSAO` (ex.: Versão 280) | `pacote` (ex.: 57) em `versao_python.json` |
| O que só ele faz | — | Ler/gravar arquivos do PC e da rede, Excel (COM), Zebra pelo cabo, apps DXF, Base Preenchida |

## Código e publicação
- **GitHub:** `lima-prog/WS` (público), branch `main`. Cada versão = 1 commit "VNNN: …".
- **Vercel** publica o HTML sozinho após cada envio.
- **Supabase** (projeto `zlbgiodxpywrqapjlldg`): login/cadastro, usuários e administradores, dados da Tela inicial
  (`pacotes_impressao`: lote, of_trecho, impresso, revisão, observação), alterações de lote, configurações compartilhadas.

## Estrutura de pastas (repositório)
```
index.html                 ← FONTE ÚNICA (todas as abas: blocos <script type="text/plain" id="src-pgN">)
versao.json                ← versão do HTML
versao_python.json         ← pacote do Python (há uma cópia em python/)
docs/                      ← documentos (requisitos + este mapa em docs/mapa/)
python/
  app.py                   ← servidor local (127.0.0.1) + rotas /api/...
  gerar_python.py          ← gera python/ppcpm/gerado/ a partir do index.html (tem que dar "remontagem IDÊNTICA")
  ABRIR_SISTEMA.bat / INSTALAR.bat / INSTALAR_BIBLIOTECAS.bat / VERIFICAR_SISTEMA.bat
  ppcpm/
    producao/              ← Agrupador | Base (motor.py + qtfalso.py rodam validador_fluxos_ppcp.py)
      base_fixa/           ← BASE_PPCPM_Programação-Fábrica_rev.22_PCT.xlsx + REGRAS_GERACAO_BASE.md
      lantek_ska/          ← modelo LANTEK_SKA rev.02 (.xlsb)
      validador_fluxos/    ← validador_fluxos_ppcp.py (gera a Base pelo Excel), ska_lantek.py
    fabrica_*.py           ← backends dos 7 apps da Preparação fábrica (rot, ren, cam, esp, cor, vis, aud)
    zebra.py               ← impressão de etiquetas
    atualizador.py, instalacao.py, arquivos_pc.py …
  dados_locais/            ← dados de trabalho do PC (ex.: cópia local da LANTEK_SKA)
  testes/                  ← pytest (13 testes)
```

## Caminhos fixos usados pelo sistema
- **Base fixa:** dentro do sistema (`producao/base_fixa`), rev.22.
- **Pastas raiz das obras (fixas):**
  `G:\.shortcut-targets-by-id\1ZwSq5uhu8VPwI99yMC0iAhkM3Ep2MZB1\LIBERACOES\LIBERAÇÕES FOCCO` e
  `\\172.25.0.7\lib-eng\LIBERAÇÕES ENGENHARIA` (o sistema avisa se o PC não acessa).
- **Base gerada:** pasta **Downloads** do usuário, nome `PPCPM_Programação-Fábrica_Sistema.ppcpm_LOTE_<lote>_<aammdd>.xlsx`.
- **LANTEK_SKA:** no Google Drive (G:) se existir; senão cópia em `python/dados_locais/producao/lantek_ska/`.

## Documentos relacionados
- `docs/REQUISITOS_FLUXO_DE_TRABALHO.md` — guia detalhado do fluxo de trabalho e padrão visual (V256).
- Projeto Claude: `claude/SISTEMA-PPCPM-como-publicar-versoes.md`.

## Pastas de trabalho do Wadson (conectadas ao Claude em 26/11/2026)
> Pastas que ele usa para fazer o sistema acontecer. G: = Google Drive (atalhos compartilhados); X: = unidade de rede.

| Pasta | Para que serve |
|---|---|
| `X:\` (inteiro) e `X:\WADSON  LIMA` | Área do Wadson: 00 Versões · 01 Planilhas para teste · 02 Cópias do sistema · 03 VS Code · 04 Instalador Python · 05 Mapa do app |
| `X:\WADSON  LIMA\05  -  MAPA  DO  APP\01  -  MEMORIA  DO  SISTEMA` | **Este mapa** |
| `X:\10. Programação Fábrica\16. Programação- Maquina -Lantek- 2026` | Programação das máquinas Lantek 2026 |
| `G:\…\1QJ57NfcTjhvbinkho-hL7zV2UPrjgZ4d\PCP-REDE\PPCPM` | Pasta raiz do PCP na rede (PCP-REDE) |
| `…\PPCPM\08. Base Dados Relatórios\03. LANTEK_SKA-REPORT_REL-ANALISE-NESTINGS` | Planilha LANTEK_SKA (atualizada pelo Agrupador) |
| `…\PPCPM\10. Programação Fábrica\06. Programação Preparação` | Programação da Preparação |
| `…\PPCPM\18. FOCCO ERP\04. GO LIVE\02. Validação Peso LIC x POSIÇÕES` | Validação de peso (Análise DBF × FOCCO) |
| `…\PPCPM\23. CONTROLE DE PACOTES` | Controle de pacotes (Tela inicial) |
| `…\PPCPM\24. Controle de Impressões por Pacote` | Controle de impressões por pacote |
| `…\PPCPM\1001 - Diego` | Pasta do Diego |
| `G:\…\1ZwSq5uhu8VPwI99yMC0iAhkM3Ep2MZB1\LIBERACOES` | Liberações (pasta raiz das obras: LIBERAÇÕES FOCCO) |
| `C:\Users\wadson.lima\Downloads` | Onde cai a Base gerada e os arquivos baixados |
| `C:\Users\wadson.lima\Documents` · `Pictures` · `Videos` | Documentos, prints e vídeos de explicação |
| `C:\Users\wadson.lima\Desktop\DXF` | Arquivos DXF (apps da Preparação fábrica) |
