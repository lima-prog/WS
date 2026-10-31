# SISTEMA - PPCPM — Versão Python

Versão em Python do sistema do Grupo Projeart. Fica **no mesmo esquema do HTML**: mesma tela de login, mesmo menu, mesmas cores, mesmos programas PPCP. O `index.html` continua sendo o sistema publicado na Vercel; esta pasta acompanha cada versão dele.

## Como funciona

```
index.html  ──►  gerar_python.py  ──►  ppcpm/gerado/  ──►  app.py (Flask)  ──►  mesma página
```

| Arquivo | Para que serve |
|---|---|
| `gerar_python.py` | Separa o `index.html` em partes organizadas e confere se a remontagem fica idêntica |
| `app.py` | Servidor Python que abre o sistema em `http://127.0.0.1:5000` |
| `ppcpm/config.py` | Versão, pacote atual, obra para impressão, menu e ligação com o Supabase |
| `ppcpm/calculos.py` | Regras da Tela inicial (quadros da "Visão geral do dia") já escritas em Python |
| `ppcpm/banco.py` | Leitura das tabelas do Supabase (projeto "SISTEMA PCP") com o login do usuário |
| `ppcpm/montagem.py` | Junta as partes e entrega a página completa |
| `ppcpm/gerado/` | Partes do sistema separadas pelo gerador (veja `MAPA.md`) — **não editar à mão** |
| `testes/` | Testes automáticos (`python -m pytest testes`) |

## Usar no seu computador

```bash
cd python
pip install -r requirements.txt
python app.py
```

## A cada versão nova

```bash
cd python
python gerar_python.py          # atualiza ppcpm/gerado/ a partir do index.html
python -m pytest testes         # confere tudo
```

## Caminho para virar Python de verdade

1. **Pronto:** estrutura separada, servidor Flask, Tela inicial calculada em Python (`/api/resumo`).
2. Trocar os quadros da Tela inicial para ler `/api/resumo` em vez de calcular no JavaScript.
3. Passar cada programa PPCP (`ppcpm/gerado/modulos/pgN.html`) para Python, um por vez, começando pelos que leem planilhas (Análise DBF × Focco, Agrupador | Base, Validação de Peso), usando `pandas` / `openpyxl`.
4. Login e cadastro de usuários pelo Python (o banco Supabase continua o mesmo).

Observação: a Vercel publica só o `index.html`. Esta pasta fica fora da publicação (`.vercelignore`).
