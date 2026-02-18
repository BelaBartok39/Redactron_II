# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('C:\\Users\\jackt\\Redactron_II\\frontend\\dist', 'frontend/dist'), ('C:\\Program Files\\Tesseract-OCR', 'tesseract')]
datas += collect_data_files('en_core_web_lg')
datas += collect_data_files('spacy')
datas += collect_data_files('thinc')
datas += collect_data_files('presidio_analyzer')
datas += collect_data_files('pydantic')
datas += collect_data_files('reportlab')


a = Analysis(
    ['C:\\Users\\jackt\\Redactron_II\\run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['en_core_web_lg', 'spacy', 'spacy.lang.en', 'spacy.pipeline', 'spacy.tokenizer', 'spacy.vocab', 'spacy.util', 'cymem', 'cymem.cymem', 'preshed', 'preshed.maps', 'murmurhash', 'murmurhash.mrmr', 'blis', 'blis.py', 'srsly', 'srsly.msgpack', 'srsly.json_api', 'catalogue', 'confection', 'thinc', 'thinc.api', 'thinc.backends.numpy_ops', 'thinc.shims', 'presidio_analyzer', 'presidio_anonymizer', 'pydantic', 'pydantic.deprecated.decorator', 'pydantic_core', 'reportlab', 'uvicorn', 'uvicorn.logging', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.http.httptools_impl', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.protocols.websockets.wsproto_impl', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'fastapi', 'starlette', 'starlette.responses', 'starlette.routing', 'starlette.middleware', 'starlette.middleware.cors', 'multiprocessing', 'multiprocessing.pool', 'multiprocessing.process', 'multiprocessing.spawn', 'multiprocessing.popen_spawn_win32', 'multiprocessing.reduction', 'pytesseract', 'PIL', 'PIL.Image', 'fitz', 'pymupdf', 'aiofiles', 'aiofiles.os'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['spacy.tests', 'thinc.tests', 'pydantic.deprecated', 'pytest', 'hypothesis', 'IPython', 'notebook', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RedactQC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RedactQC',
)
