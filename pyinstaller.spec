# -*- mode: python ; coding: utf-8 -*-

import os
import platform


datas = []

# Import all non-python files in the src directory (recursively)
datas += [(os.path.join(dp, f), os.path.dirname(os.path.join(dp, f).replace('src/', '')))
          for dp, dn, fs in os.walk('src') for f in fs if os.path.splitext(f)[1] not in ['.py', '.pyc']]

# print('datas:', datas)


hiddenimports = []

# Import all python modules in the src directory (recursively), as some of them are dynamically imported
hiddenimports += [os.path.join(dp, f).replace('src/', '').replace('.py', '').replace('/', '.')
                  for dp, dn, fs in os.walk('src') for f in fs if os.path.splitext(f)[1] == '.py']

# print('hiddenimports:', hiddenimports)


block_cipher = None


a = Analysis(
    [os.path.join('src', 'main.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['pyinstaller-hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

splash = None
if platform.system() != 'Darwin':  # Splash screen is not supported on macOS
    splash = Splash(
        os.path.join('src', 'assets', 'other', 'icon.png'),
        binaries=a.binaries,
        datas=a.datas,
        text_pos=(2, 20),
        text_color='white',
        text_size=12,
        minify_script=True,
        always_on_top=True,
    )

exe = EXE(  # One-file mode.
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    *([splash, splash.binaries] if splash else []),
    [],
    name='drone-copilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('src', 'assets', 'other', 'icon.png'),
)