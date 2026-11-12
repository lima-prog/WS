"""
ATALHO NA ÁREA DE TRABALHO — "SISTEMA - PPCPM" com o ícone do P da Projeart.

Toda vez que o sistema abre, confere se o atalho está na Área de Trabalho (mesmo quando ela
fica no OneDrive). Se sumiu, cria de novo e anota em dados_locais/atalho.log (dia e hora),
para descobrir o que anda apagando.

Cria o atalho pelo próprio Windows (IShellLink): primeiro pelo pywin32, se estiver instalado;
senão direto pelo ctypes (biblioteca padrão). Não usa PowerShell nem VBScript.
"""
from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from .config import PASTA_APP, PASTA_DADOS

NOME = "SISTEMA - PPCPM.lnk"
ARQ_LOG = PASTA_DADOS / "atalho.log"


def _log(msg: str) -> None:
    try:
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        with open(ARQ_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%d/%m/%Y %H:%M:%S}  {msg}\n")
    except OSError:
        pass


def _areas_de_trabalho() -> list[Path]:
    from .arquivos_pc import _pasta_usuario
    pastas = []
    minha = _pasta_usuario("Desktop", "Desktop")
    if minha:
        pastas.append(Path(minha))
    publica = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop"
    if publica.is_dir():
        pastas.append(publica)
    return pastas


def _aponta_para_mim(lnk: Path, bat: Path) -> bool:
    """O atalho abre o ABRIR_SISTEMA.bat DESTA pasta? (lê o caminho gravado dentro do .lnk)"""
    try:
        dados = lnk.read_bytes().lower()
    except OSError:
        return False
    alvo = str(bat).lower()
    for cod in ("utf-16-le", "mbcs" if sys.platform.startswith("win") else "latin-1"):
        try:
            if alvo.encode(cod).lower() in dados:
                return True
        except (LookupError, UnicodeError):
            continue
    return False


def _criar_pywin32(lnk: Path, bat: Path, icone: Path) -> None:
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    sc = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(lnk))
    sc.TargetPath = str(bat)
    sc.WorkingDirectory = str(bat.parent)
    sc.IconLocation = f"{icone},0"
    sc.Description = "SISTEMA - PPCPM | Grupo Projeart"
    sc.WindowStyle = 7          # minimizada (a janela preta fica na barra de tarefas)
    sc.Save()


def _criar_ctypes(lnk: Path, bat: Path, icone: Path) -> None:
    import ctypes
    import uuid
    from ctypes import POINTER, WINFUNCTYPE, byref, c_int, c_ulong, c_void_p, c_wchar_p

    class GUID(ctypes.Structure):
        _fields_ = [("a", ctypes.c_uint32), ("b", ctypes.c_uint16), ("c", ctypes.c_uint16), ("d", ctypes.c_ubyte * 8)]

    def guid(texto: str) -> GUID:
        u = uuid.UUID(texto)
        return GUID(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))

    HRESULT = ctypes.HRESULT

    def chamar(obj, indice, restype, *tipos):
        tabela = ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents
        return WINFUNCTYPE(restype, c_void_p, *tipos)(tabela[indice])

    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)
    link, arquivo = c_void_p(), c_void_p()
    clsid = guid("00021401-0000-0000-C000-000000000046")       # ShellLink
    iid_link = guid("000214F9-0000-0000-C000-000000000046")    # IShellLinkW
    iid_arq = guid("0000010b-0000-0000-C000-000000000046")     # IPersistFile
    hr = ole32.CoCreateInstance(byref(clsid), None, 1, byref(iid_link), byref(link))
    if hr != 0 or not link:
        raise OSError(f"CoCreateInstance falhou ({hr})")
    try:
        chamar(link, 20, HRESULT, c_wchar_p)(link, str(bat))                  # SetPath
        chamar(link, 9, HRESULT, c_wchar_p)(link, str(bat.parent))            # SetWorkingDirectory
        chamar(link, 7, HRESULT, c_wchar_p)(link, "SISTEMA - PPCPM | Grupo Projeart")  # SetDescription
        chamar(link, 17, HRESULT, c_wchar_p, c_int)(link, str(icone), 0)      # SetIconLocation
        chamar(link, 15, HRESULT, c_int)(link, 7)                             # SetShowCmd: minimizada
        chamar(link, 0, HRESULT, POINTER(GUID), POINTER(c_void_p))(link, byref(iid_arq), byref(arquivo))
        try:
            chamar(arquivo, 6, HRESULT, c_wchar_p, c_int)(arquivo, str(lnk), 1)   # IPersistFile.Save
        finally:
            chamar(arquivo, 2, c_ulong)(arquivo)
    finally:
        chamar(link, 2, c_ulong)(link)


def existe() -> bool:
    """Tem um atalho na Área de Trabalho que abre o sistema DESTA pasta? (só confere, não cria)"""
    if not sys.platform.startswith("win"):
        return True
    bat = PASTA_APP / "ABRIR_SISTEMA.bat"
    for pasta in _areas_de_trabalho():
        try:
            if any(_aponta_para_mim(lnk, bat) for lnk in pasta.glob("*.lnk")):
                return True
        except OSError:
            continue
    return False


def garantir(forcar: bool = False) -> str:
    """Confere/cria o atalho. Devolve uma frase com o que aconteceu."""
    if not sys.platform.startswith("win"):
        return "Atalho: só no Windows."
    from .acesso_rapido import _rede
    if _rede(str(PASTA_APP)):
        return "Atalho: cópia do drive da rede, não mexo no atalho (o atalho é da instalação no PC)."
    bat = PASTA_APP / "ABRIR_SISTEMA.bat"
    icone = PASTA_APP / "icone.ico"
    if not icone.exists():
        icone = PASTA_APP / "ppcpm" / "web" / "icone.ico"
    pastas = _areas_de_trabalho()
    if not pastas:
        return "Atalho: Área de Trabalho não encontrada."
    if not forcar:
        for pasta in pastas:
            try:
                for lnk in pasta.glob("*.lnk"):
                    if _aponta_para_mim(lnk, bat):
                        return f"Atalho OK: {lnk}"
            except OSError:
                continue
    destino = pastas[0] / NOME
    existia_antes = ARQ_LOG.exists()
    erros = []
    for criar in (_criar_pywin32, _criar_ctypes):
        try:
            criar(destino, bat, icone)
            if destino.exists():
                _log(("Atalho tinha sumido da Área de Trabalho: criado de novo em " if existia_antes
                      else "Atalho criado em ") + str(destino))
                return f"Atalho criado: {destino}"
        except Exception as e:  # noqa: BLE001
            erros.append(f"{criar.__name__}: {e}")
    _log("Não consegui criar o atalho: " + " | ".join(erros))
    return "Atalho: não consegui criar (" + " | ".join(erros) + ")"


def garantir_em_segundo_plano() -> None:
    """Roda num processo à parte (sem janela): se o Windows falhar, o sistema não é afetado."""
    if not sys.platform.startswith("win"):
        return

    def rodar():
        import subprocess
        try:
            subprocess.run([sys.executable, str(PASTA_APP / "app.py"), "--criar-atalho"],
                           cwd=str(PASTA_APP), timeout=60, capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as e:  # noqa: BLE001
            _log(f"Não consegui conferir o atalho: {e}")

    threading.Thread(target=rodar, name="atalho", daemon=True).start()
