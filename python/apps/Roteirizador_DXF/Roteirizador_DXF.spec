# -*- mode: python ; coding: utf-8 -*-
"""
.exe do app "Roteirizador DXF" (separado do PPCP Ferramentas). Gerar no Windows, de dentro desta pasta:

    pip install pyinstaller
    pyinstaller Roteirizador_DXF.spec

Sai em dist/PPCP_Roteirizador_DXF/. Feito a partir do main.spec do PPCP Ferramentas, só com o que este app usa.
Lembrete: ao lado do .exe coloque o pasta_dados.txt (com o caminho ABSOLUTO da pasta de dados).
"""
from PyInstaller.utils.hooks import collect_all

block_cipher = None
PACOTES_COM_COLLECT_ALL = ['ezdxf', 'openpyxl']

datas = [('nucleo/assets', 'nucleo/assets')]
binaries = []
hiddenimports = ['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.simpledialog', 'tkinter.colorchooser', 'tkinter.font', 'roteirizador_original.roteirizador_dxf_projeart']

for pacote in PACOTES_COM_COLLECT_ALL:
    d, b, h = collect_all(pacote)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(['main.py'], pathex=[], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PPCP_Roteirizador_DXF', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, console=False,
          disable_windowed_traceback=False, argv_emulation=False, target_arch=None,
          codesign_identity=None, entitlements_file=None, icon='nucleo/assets/icone_projeart.ico')
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, upx_exclude=[], name='PPCP_Roteirizador_DXF')
