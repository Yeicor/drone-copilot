# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

from_dir_add_extensions = {
    'src'+os.path.sep: ['.kv', '.png', '.jpg', '.glsl', '.gz', '.tflite']
}

datas_auto = []
for dir, exts in from_dir_add_extensions.items():
    for root, dirs, files in os.walk(dir):
        for file in files:
            if os.path.splitext(file)[1] in exts:
                datas_auto.append((os.path.join(root, file), root.replace(dir, '')))

a = Analysis(
    [os.path.join('src', 'main.py')],
    pathex=[],
    binaries=[],
    datas=datas_auto,
    # Help PyInstaller locate required *.kv modules:
    hiddenimports=['ui.video.video.MyVideo', 'ui.util.joystick.MyJoystick'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
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
    icon=os.path.join('..', 'src', 'assets', 'other', 'icon.png'),
)
