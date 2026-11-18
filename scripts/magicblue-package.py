#!/usr/bin/env python3
"""Adapt a bounded upstream EmulatorJS bundle; preserve the original WASM bytes."""
import argparse, hashlib, importlib.util, json, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ALLOWED = {'coolbaremu_libretro.js', 'coolbaremu_libretro.wasm', 'core.json', 'build.json', 'license.txt'}

def adapt(bundle, output, seven, source):
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'bridge-work'
    work.mkdir(exist_ok=True)
    with zipfile.ZipFile(bundle) as z:
        infos = z.infolist()
        if len(infos) > 40 or sum(i.file_size for i in infos) > 64 * 1024 * 1024:
            raise ValueError('bundle directory exceeds budget')
        for i in infos:
            path = PurePosixPath(i.filename)
            if path.is_absolute() or '..' in path.parts or any(':' in x for x in path.parts):
                raise ValueError('unsafe bundle path')
        for name in ['cores/coolbaremu-wasm.data', 'cores/coolbaremu-legacy-wasm.data']:
            info = z.getinfo(name)
            if info.file_size > 32 * 1024 * 1024:
                raise ValueError('core archive too large')
            (work / Path(name).name).write_bytes(z.read(name))
    spec = importlib.util.spec_from_file_location('input_bridge', Path(__file__).with_name('magicblue-input-bridge.py'))
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    hashes = []
    for variant, name in [('normal','coolbaremu-wasm.data'),('legacy','coolbaremu-legacy-wasm.data')]:
        archive = work / name
        listing = subprocess.run([seven,'l','-slt',str(archive)], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True).stdout
        entries = []
        for block in listing.replace('\r','').split('\n\n'):
            fields = dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
            if 'Size' in fields and 'Path' in fields:
                if fields['Path'] not in ALLOWED:
                    raise ValueError('unexpected core archive member')
                entries.append(int(fields['Size']))
        if len(entries) != 5 or sum(entries) > 64 * 1024 * 1024:
            raise ValueError('inner archive exceeds budget')
        directory = work / variant
        directory.mkdir(exist_ok=True)
        subprocess.run([seven,'x','-y',str(archive),'-o'+str(directory.resolve())], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        wasm = directory / 'coolbaremu_libretro.wasm'
        raw = wasm.read_bytes()
        if raw[:4] != b'\0asm':
            raise ValueError('invalid WASM signature')
        hashes.append(hashlib.sha256(raw).hexdigest())
        javascript = directory / 'coolbaremu_libretro.js'
        javascript.write_text(bridge.patch(javascript.read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
        subprocess.run(['node','--check',str(javascript)], check=True)
    identity = hashlib.sha256(''.join(hashes).encode()).hexdigest()
    build_id = datetime.now(timezone.utc).isoformat(timespec='microseconds')
    metadata = {'core':'coolbaremu','sourceCommit':source,'coreIdentity':identity,'inputBridgeVersion':2,'buildStart':build_id,'wasmSha256':dict(zip(['normal','legacy'],hashes))}
    cores = output / 'cores'
    (cores/'reports').mkdir(parents=True,exist_ok=True)
    for variant,name in [('normal','coolbaremu-wasm.data'),('legacy','coolbaremu-legacy-wasm.data')]:
        directory = work / variant
        build = json.loads((directory/'build.json').read_text())
        build.update({'buildStart':build_id,'inputBridgeVersion':2,'coreIdentity':identity})
        (directory/'build.json').write_text(json.dumps(build),encoding='utf-8')
        target = cores/name
        if target.exists():
            raise ValueError('output already exists; use a fresh output directory')
        subprocess.run([seven,'a','-t7z',str(target.resolve()),*sorted(ALLOWED)],cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
        if hashlib.sha256((directory/'coolbaremu_libretro.wasm').read_bytes()).hexdigest() != hashes[0 if variant=='normal' else 1]:
            raise ValueError('WASM unexpectedly changed')
    report = {'core':'coolbaremu','buildStart':build_id,'buildEnd':build_id,'options':{'defaultWebGL2':True}}
    (cores/'reports/coolbaremu.json').write_text(json.dumps(report),encoding='utf-8')
    (output/'core-build.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    result = output/'magicblue-coolbaremu.zip'
    with zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(cores.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(output))
        z.write(output/'core-build.json','core-build.json')
    print(json.dumps(metadata,indent=2))
    print('Adapted core bundle:',result)

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('bundle',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--seven',default='7z')
    p.add_argument('--source',required=True)
    a=p.parse_args()
    adapt(a.bundle,a.output,a.seven,a.source)
