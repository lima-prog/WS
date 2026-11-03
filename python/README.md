# SISTEMA - PPCPM — Versão Python

O mesmo sistema do HTML (mesma tela de login, menu, cores e programas), rodando pelo Python **no seu PC**, com o que o navegador sozinho não faz:

- **Arquivos do PC em todos os programas.** Quando um programa pede um arquivo (Análise DBF, Agrupador, Validação de Peso, Impressão de Etiquetas…), abre a janela **SISTEMA PPCPM - ARQUIVOS DO PC**. Ela mostra as unidades (C:, G:, H:, rede mapeada), a Área de Trabalho, os Documentos e os Downloads, além dos **favoritos** e das **pastas recentes**. Tem também a **busca nas subpastas** e aceita **colar o caminho** copiado do Explorador. A janela comum do Windows continua no botão "Janela do Windows".
- **Atualização automática das duas versões.** Toda versão nova publicada chega sozinha a este PC, tanto o HTML quanto o Python.
- **Mais rápido.** A página fica guardada na memória e vai compactada, o que ajuda também quem entra pela rede.
- **Não instala nada para abrir.** Usa só o Python (3.8 ou mais novo), sem pip e sem administrador.

## Como tudo se liga

```
 Você pede uma mudança ──► index.html (GitHub lima-prog/ws) ──► Vercel publica o HTML (link)
                                   │
                                   └─► gerar_python.py separa em partes ──► python/ (GitHub)
                                                                                │
                 PC com o sistema ◄── atualizador confere a cada 30 min ◄───────┘
                 (ABRIR_SISTEMA.bat)   • código Python novo  → troca e reabre sozinho
                                       • versão nova do HTML → regenera as partes
                                         (se o GitHub estiver bloqueado, pega da Vercel)

 Navegador ──► app.py (este PC) ──► página do sistema + ponte.js em cada programa
                    │                         │
                    │                         └─► pede arquivo ──► /api/pc/... ──► pastas do PC
                    └─► login e dados: banco Supabase (o mesmo de sempre)
```

| Arquivo / pasta | Para que serve |
|---|---|
| `INSTALAR.bat` | Instala neste PC: cria o atalho **SISTEMA - PPCPM** na Área de Trabalho e no Menu Iniciar, e pergunta se deve abrir com o Windows |
| `ABRIR_SISTEMA.bat` | Abre o sistema (acha o Python sozinho e reabre depois de uma atualização) |
| `VERIFICAR_SISTEMA.bat` | Confere o PC: Python, conexões (Supabase, GitHub, Vercel), pastas, bibliotecas por seção e últimas atualizações |
| `INSTALAR_BIBLIOTECAS.bat` | Instala as bibliotecas das seções (pela internet ou sem internet, pela pasta `pacotes`) |
| `BAIXAR_PACOTES_OFFLINE.bat` | Num PC com internet, baixa as bibliotecas para a pasta `pacotes`, para levar a PCs bloqueados |
| `bibliotecas/` | Lista de bibliotecas **por seção** do sistema (veja `bibliotecas/BIBLIOTECAS.md`) |
| `app.py` | Servidor do sistema (só biblioteca padrão do Python) |
| `ppcpm/arquivos_pc.py` | Leitura das pastas do PC: unidades, favoritos, recentes, busca e abrir no Explorador |
| `ppcpm/web/ponte.js` | Liga os programas às pastas do PC (a janela ARQUIVOS DO PC) |
| `ppcpm/atualizador.py` | Atualização automática (GitHub; e Vercel quando o GitHub está bloqueado) |
| `ppcpm/gerador.py` + `gerar_python.py` | Separam o `index.html` em partes organizadas (`ppcpm/gerado/`) |
| `ppcpm/calculos.py` | Regras da Tela inicial já escritas em Python |
| `ppcpm/banco.py` | Leitura do banco Supabase com o login do usuário |
| `ppcpm/bibliotecas.py` / `diagnostico.py` | Lista oficial das bibliotecas e o relatório do VERIFICAR |
| `dados_locais/` | O que é só deste PC (favoritos, recentes, registro de atualizações). A atualização nunca apaga |
| `versao_python.json` | Número do pacote Python (a atualização compara com o GitHub) |

## Instalar no seu PC (uma vez)

1. Instale o Python 3.12 ou mais novo pela **Microsoft Store**, que não pede administrador, ou pelo site python.org, marcando **"Add python.exe to PATH"**.
2. Extraia o `.zip` e dê dois cliques em **`INSTALAR.bat`**.
   - Se a pasta estiver em Downloads, ele copia o sistema para `C:\Users\<você>\SISTEMA-PPCPM`.
   - Cria o atalho **SISTEMA - PPCPM** com o ícone do P da Projeart.
   - Pergunta se o sistema deve abrir junto com o Windows.
3. Pronto. Daqui para frente, abra pelo atalho. As versões novas chegam sozinhas.

Opcional: **`INSTALAR_BIBLIOTECAS.bat`** prepara o PC para os programas em Python (pandas, leitura de DBF, PDF…).

## Abrir

- Atalho **SISTEMA - PPCPM**, ou dois cliques em `ABRIR_SISTEMA.bat`.
- CMD: `ABRIR_SISTEMA.bat`. PowerShell / Terminal: `.\ABRIR_SISTEMA.bat`.
- Se o sistema já estiver aberto, ele só abre o navegador (não abre duas vezes).
- Para deixar os colegas acessarem pela rede: `ABRIR_SISTEMA.bat --rede`. A janela mostra o endereço para eles, por exemplo `http://192.168.0.15:5000`. Eles não instalam nada e **não enxergam os arquivos do seu PC**: cada um escolhe os próprios arquivos pela janela comum do Windows.

Outras opções: `--sem-navegador`, `--sem-atualizar`, `--verificar`.

## Outros PCs (rodar suave)

| Situação do PC | O que fazer |
|---|---|
| Tem internet e Python | `INSTALAR.bat` e depois, se quiser, `INSTALAR_BIBLIOTECAS.bat` |
| Sem Python | O `ABRIR_SISTEMA.bat` baixa um Python portátil só para a pasta. Se a rede bloquear, instale pela Microsoft Store |
| Rede bloqueia o pip | Num PC com internet, rode `BAIXAR_PACOTES_OFFLINE.bat`. Copie a pasta com `pacotes` e rode `INSTALAR_BIBLIOTECAS.bat` (usa a mesma versão do Python) |
| Algo não abre | Rode `VERIFICAR_SISTEMA.bat` e mande o print |

## A cada versão (feito pelo Claude, no repositório)

```bash
cd python
python gerar_python.py          # separa o index.html e atualiza bibliotecas/
python -m pytest testes         # confere tudo
# subir versao_python.json (pacote +1) quando o código Python mudar
```

## Próximos passos para virar Python de verdade

1. **Pronto:** estrutura separada, servidor sem instalações, Arquivos do PC em todos os programas, atualização automática, Tela inicial em Python (`/api/resumo`).
2. Passar a leitura pesada para o Python, um programa por vez, começando por **Análise da DBF X Focco**, **Agrupador | Base** e **Validação de Peso**. O Python lê DBF, Excel e PDF direto da pasta (pandas, dbfread, pdfplumber) e devolve o resultado pronto ao programa.
3. **Impressão de Etiquetas:** imprimir direto na Zebra ZD220, sem janela (pywin32).

Observação: a Vercel publica só o `index.html`. Esta pasta fica fora da publicação (`.vercelignore`).
