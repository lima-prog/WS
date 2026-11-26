# 05 — Como procurar e como restaurar

## Procurar rápido
| Quero achar… | Onde |
|---|---|
| Quando uma aba mudou | `04_HISTORICO_DE_VERSOES.md` → Ctrl+F no nome da aba |
| O código de uma aba | `index.html` → Ctrl+F `id="src-pgN"` (número da aba no `02_MAPA_DAS_ABAS.md`) |
| A geração da Planilha Base | `python/ppcpm/producao/validador_fluxos/validador_fluxos_ppcp.py` → Ctrl+F `REGRAS FIXAS` |
| Botões/campos do Agrupador | `index.html` bloco `src-pg2` (`data-w` = campo, `data-m` = ação do Python) |
| Listar PCT (leitura do print) | `index.html` → Ctrl+F `function pctObras` / `pctCorrigir` / `ntListarPct` |
| Apps da Preparação fábrica | `python/ppcpm/fabrica_<app>.py` |
| Versão publicada agora | rodapé do sistema ("Versão NNN") e `versao.json` / `versao_python.json` |

## VOLTAR uma versão (quando algo quebrar)
- **Pelo Claude (mais fácil):** pedir "volte a aba X para como estava na VNNN" ou "desfaça a VNNN".
  O Claude acha o commit no `04_HISTORICO_DE_VERSOES.md` (código entre crases, ex.: `3c99f5e`) e publica uma versão nova com a correção.
- **Pelo GitHub:** em `github.com/lima-prog/WS/commits/main`, abrir o commit da versão → ver o que mudou → "Revert".
- **Um arquivo só:** no GitHub, abrir o arquivo → History → escolher a versão → copiar o conteúdo.
- Nunca apagar o histórico; voltar sempre publicando uma **versão nova** (assim todos os PCs se atualizam sozinhos).

## Restaurar o sistema num PC
1. Rodar `INSTALAR.bat` (copia para `C:\Users\<usuário>\SISTEMA-PPCPM`, cria o atalho e instala as bibliotecas).
2. Se faltar algo: `VERIFICAR_SISTEMA.bat` ou janela **Verificação da instalação** no próprio sistema.
3. Sem PowerShell e sem desligar antivírus.

## Manter este mapa em dia
- A cada versão: 1 linha nova no histórico; regra nova → `03`; aba nova → `02`.
- Pedir ao Claude: **"atualize o mapa do sistema"** — ele regenera os arquivos e salva nos 3 lugares (pasta X:, GitHub `docs/mapa/`, projeto Claude).
