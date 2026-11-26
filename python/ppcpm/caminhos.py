"""
CAMINHOS QUE VALEM EM QUALQUER PC — cada usuário pode ter a pasta da rede numa letra diferente
(X: num PC, Z: no outro). Por isso, quando uma pasta é fixada para todos, guardamos também o caminho
de rede verdadeiro (\\\\servidor\\compartilhamento\\...). Em cada PC o sistema acha a pasta de novo:
  1) o caminho de rede (funciona em qualquer PC com acesso à rede);
  2) o caminho como foi escolhido;
  3) a mesma pasta em OUTRA letra (troca X: por Y:, Z:, ...);
  4) a letra deste PC que está ligada ao mesmo compartilhamento de rede.
"""
from __future__ import annotations

import os
import string
import sys


def _win() -> bool:
    return sys.platform.startswith("win")


def unc_da_letra(letra: str) -> str:
    """'X:' -> '\\\\servidor\\compart' (ou '' se a letra não é de rede)."""
    if not _win():
        return ""
    import ctypes
    from ctypes import wintypes
    buf = ctypes.create_unicode_buffer(1024)
    n = wintypes.DWORD(1024)
    try:
        r = ctypes.windll.mpr.WNetGetConnectionW(letra[:2], buf, ctypes.byref(n))
    except Exception:
        return ""
    return buf.value.rstrip("\\") if r == 0 else ""


def para_unc(caminho: str) -> str:
    """Troca a letra da unidade de rede pelo caminho de rede. Pasta local fica como está."""
    c = (caminho or "").strip()
    if len(c) >= 2 and c[1] == ":":
        u = unc_da_letra(c[:2])
        if u:
            return u + c[2:]
    return c


def _letras() -> list[str]:
    if not _win():
        return []
    return [f"{l}:" for l in string.ascii_uppercase if os.path.exists(f"{l}:\\")]


def achar(candidatos: list[str]) -> str:
    """Acha neste PC a pasta (devolve o caminho que existe aqui, ou '')."""
    cs = [c.strip() for c in candidatos if c and c.strip()]
    for c in cs:                                   # 1 e 2: como está
        if os.path.isdir(c):
            return c
    letras = _letras()
    for c in cs:                                   # 3: mesma pasta em outra letra
        if len(c) >= 3 and c[1] == ":":
            resto = c[2:]
            for l in letras:
                if os.path.isdir(l + resto):
                    return l + resto
    for c in cs:                                   # 4: letra deste PC ligada ao mesmo compartilhamento
        if c.startswith("\\\\"):
            cl = c.lower()
            for l in letras:
                u = unc_da_letra(l)
                if u and cl.startswith(u.lower() + "\\") or (u and cl == u.lower()):
                    p = l + c[len(u):]
                    if os.path.isdir(p):
                        return p
    return ""


def pasta_downloads() -> str:
    """V282: pasta Downloads do usuário (a de verdade, mesmo movida/OneDrive). Todo arquivo GERADO pelo sistema
    vai para cá, em qualquer PC e para qualquer usuário. Se não achar, usa a pasta do usuário."""
    if _win():
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                v = os.path.expandvars(winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")[0])
                if os.path.isdir(v):
                    return v
        except OSError:
            pass
    for nome in ("Downloads", "Transferências"):
        p = os.path.join(os.path.expanduser("~"), nome)
        if os.path.isdir(p):
            return p
    return os.path.expanduser("~")
