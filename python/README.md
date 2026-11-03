# SISTEMA - PPCPM — Versão Python

Versão em Python do sistema do Grupo Projeart. Fica **no mesmo esquema do HTML**: mesma tela de login, mesmo menu, mesmas cores, mesmos programas PPCP. O `index.html` continua sendo o sistema publicado na Vercel; esta pasta acompanha cada versão dele.

## Como funciona

```
index.html  ──►  gerar_python.py  ──►  ppcpm/gerado/  ──►  app.py (Python)  ──►  mesma página
```

| Arquivo | Para que serve |
|---|---|
| `gerar_python.py` | Separa o `index.html` em partes organizadas e confere se a remontagem fica idêntica |
| `ABRIR_SISTEMA.bat` | Abre o sistema no Windows (duplo clique, CMD ou Terminal) |
| `app.py` | Servidor Python (só biblioteca padrão) que abre o sistema em `http://127.0.0.1:5000` |
| `ppcpm/config.py` | Versão, pacote atual, obra para impressão, menu e ligação com o Supabase |
| `ppcpm/calculos.py` | Regras da Tela inicial (quadros da "Visão geral do dia") já escritas em Python |
| `ppcpm/banco.py` | Leitura das tabelas do Supabase (projeto "SISTEMA PCP") com o login do usuário, sem instalar nada |
| `ppcpm/montagem.py` | Junta as partes e entrega a página completa |
| `ppcpm/gerado/` | Partes do sistema separadas pelo gerador (veja `MAPA.md`) — **não editar à mão** |
| `testes/` | Testes automáticos (`python -m pytest testes`) |

## Abrir pelo Windows (casa ou PC da empresa)

O sistema **não instala nada**: usa só o que já vem com o Python (3.8 ou mais novo). Não precisa de pip, de administrador nem de internet para instalar componentes.

**Duplo clique:** abra a pasta `python` e dê dois cliques em `ABRIR_SISTEMA.bat`.

**Pelo CMD:**

```bat
cd C:\caminho\da\pasta\python
ABRIR_SISTEMA.bat
```

**Pelo PowerShell / Terminal do Windows:** `.\ABRIR_SISTEMA.bat`

O `ABRIR_SISTEMA.bat` procura o Python sozinho (comando `py`, comando `python` e as pastas onde o Python costuma ficar). Se não achar, baixa um **Python portátil** só para esta pasta (`.python`), sem instalar e sem pedir administrador. Se a rede bloquear esse download, ele explica como instalar pela Microsoft Store.

O navegador abre sozinho em `http://127.0.0.1:5000` (se a porta 5000 estiver ocupada, usa 5001, 5002...). Deixe a janela preta aberta enquanto usar. Para fechar: `Ctrl+C` ou feche a janela.

**Liberar para outros computadores da rede:** `ABRIR_SISTEMA.bat --rede` — a janela mostra o endereço (ex.: `http://192.168.0.15:5000`) para os colegas abrirem.

## Abrir manualmente (qualquer sistema)

```bash
cd python
python app.py                  # só neste computador
python app.py --rede           # outros computadores da rede também
python app.py --sem-navegador  # não abre o navegador sozinho
```

## A cada versão nova

```bash
cd python
python gerar_python.py          # atualiza ppcpm/gerado/ a partir do index.html
python -m pytest testes         # confere tudo (opcional: pip install pytest)
```

## Caminho para virar Python de verdade

1. **Pronto:** estrutura separada, servidor Python sem instalações, Tela inicial calculada em Python (`/api/resumo`).
2. Trocar os quadros da Tela inicial para ler `/api/resumo` em vez de calcular no JavaScript.
3. Passar cada programa PPCP (`ppcpm/gerado/modulos/pgN.html`) para Python, um por vez, começando pelos que leem planilhas (Análise DBF × Focco, Agrupador | Base, Validação de Peso), usando `pandas` / `openpyxl`.
4. Login e cadastro de usuários pelo Python (o banco Supabase continua o mesmo).

Observação: a Vercel publica só o `index.html`. Esta pasta fica fora da publicação (`.vercelignore`).
