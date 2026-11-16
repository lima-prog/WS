# -*- coding: utf-8 -*-
"""
Abre a página de envio do intranet (Alteração de Roteiro PCP) num navegador e ANEXA a planilha gerada no campo
de arquivo — quem confere a pré-visualização e clica em "Enviar Planilha" é a PESSOA. Este script nunca envia.

Roda como programa à parte (o app chama: python envio_intranet.py <planilha.xlsx> <url>), porque o navegador
automatizado fecha junto com o processo que o abriu. Por isso é autônomo (não importa nada do projeto).

Como funciona:
  - usa o Playwright (pip install playwright) com o Edge ou o Chrome JÁ instalados no PC (não baixa navegador);
  - perfil próprio e persistente em %LOCALAPPDATA%\\PPCP_Ferramentas\\navegador_envio: se o intranet pedir login,
    entra uma vez e o navegador lembra nas próximas;
  - espera o campo de arquivo aparecer (dá tempo de fazer login), anexa a planilha e fica aberto até a pessoa
    fechar o navegador;
  - se algo falhar (sem Playwright, sem navegador, página diferente), cai no modo manual: abre a página no
    navegador padrão, mostra a planilha no Explorer e copia o caminho dela.

Código de saída: 0 ok · 2 uso errado · 3 sem Playwright · 4 falhou e caiu no modo manual.
Copiado do app "Alteração de Roteiro" (PPCP Ferramentas) para o SISTEMA - PPCPM; só a pasta do perfil mudou.
"""
import os
import subprocess
import sys
import traceback
import webbrowser

SELETOR_ARQUIVO = "input[type=file]"
ESPERA_CAMPO_MS = 10 * 60 * 1000          # 10 min: tempo pra fazer login, se pedir


def _pasta_perfil():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".ppcp_ferramentas")
    return os.path.join(base, "SISTEMA-PPCPM", "navegador_envio")


def _log(msg):
    try:
        pasta = os.path.dirname(_pasta_perfil())
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "envio_intranet.log"), "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


def modo_manual(caminho, url):
    """Plano B: página no navegador padrão + planilha selecionada no Explorer + caminho na área de transferência."""
    try:
        if sys.platform == "win32":
            subprocess.run(["clip"], input=os.path.normpath(caminho).encode("utf-16-le"), check=False)
            subprocess.Popen(f'explorer /select,"{os.path.normpath(caminho)}"')
    except Exception:
        _log(traceback.format_exc())
    webbrowser.open(url)


def abrir_navegador(p, pasta_perfil, canais=("msedge", "chrome", None)):
    """Abre o navegador com perfil persistente. Devolve o contexto."""
    os.makedirs(pasta_perfil, exist_ok=True)
    ultimo = None
    for canal in canais:
        try:
            kw = dict(headless=False, no_viewport=True, args=["--start-maximized"])
            if canal:
                kw["channel"] = canal
            return p.chromium.launch_persistent_context(pasta_perfil, **kw)
        except Exception as e:                      # canal não instalado: tenta o próximo
            ultimo = e
    raise ultimo


def anexar(p, caminho, url, pasta_perfil=None, canais=("msedge", "chrome", None)):
    """Abre a página e anexa a planilha. Devolve (contexto, página). Não envia nada."""
    ctx = abrir_navegador(p, pasta_perfil or _pasta_perfil(), canais)
    pagina = ctx.pages[0] if ctx.pages else ctx.new_page()
    pagina.goto(url)
    campo = pagina.locator(SELETOR_ARQUIVO).first
    campo.wait_for(state="attached", timeout=ESPERA_CAMPO_MS)
    campo.set_input_files(caminho)
    return ctx, pagina


def main(argv):
    if len(argv) < 3:
        print("uso: envio_intranet.py <planilha.xlsx> <url>")
        return 2
    caminho, url = argv[1], argv[2]
    if not os.path.isfile(caminho):
        print(f"planilha não encontrada: {caminho}")
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        _log("playwright não instalado — modo manual")
        modo_manual(caminho, url)
        return 3
    anexou = False
    try:
        with sync_playwright() as p:
            ctx, _pagina = anexar(p, caminho, url)
            anexou = True
            _log(f"planilha anexada: {caminho}")
            ctx.wait_for_event("close", timeout=0)      # fica aberto até a pessoa fechar o navegador
        return 0
    except Exception:
        _log("falha ao anexar automaticamente:\n" + traceback.format_exc())
        if anexou:                                      # já anexou; o erro foi só ao fechar o navegador
            return 0
        modo_manual(caminho, url)
        return 4


if __name__ == "__main__":
    sys.exit(main(sys.argv))
