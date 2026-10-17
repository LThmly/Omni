#!/usr/bin/env python3
"""Deploy a clean Git commit over SCP; the Pi doesn't need a Git checkout."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import tempfile
import uuid


REMOTE = r'''
import hashlib,json,os,signal,subprocess,sys,tarfile,time
from pathlib import Path
archive,target,commit,verify,backend=sys.argv[1:]
root=Path(target).expanduser()
if not root.is_absolute():root=Path.home()/root
root=root.resolve()
if root in (Path('/'),Path.home()):raise SystemExit('Choose a dedicated deployment directory')
with tarfile.open(archive) as source:
    manifest=json.load(source.extractfile('.omni-deployed.json'))
    if manifest['commit']!=commit:raise SystemExit('Commit mismatch')
    for member in source:
        if not (root/member.name).resolve().is_relative_to(root):raise SystemExit('Unsafe archive path')
    def check():
        bad=[name for name,digest in manifest['files'].items()
             if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest]
        if bad:raise RuntimeError('File verification failed: '+', '.join(bad))
    if verify=='yes':
        check()
        saved=json.loads((root/'.omni-deployed.json').read_text())
        if saved['commit']!=commit:raise SystemExit('Recorded deployment is a different commit')
        print('Verified %s: %s files match GitHub commit %s' % (root,len(manifest['files']),commit),flush=True)
        Path(archive).unlink()
        raise SystemExit(0)
    root.mkdir(parents=True,exist_ok=True)
    state=Path.home()/'.omni';state.mkdir(exist_ok=True)
    python=str(root/'.venv/bin/python') if (root/'.venv/bin/python').exists() else 'python3'
    # Stop the launcher first, then the UI it owns, so an old loop cannot restart it.
    pid_path=state/'shell.pid'
    try:
        pid=int(pid_path.read_text())
        command=Path('/proc/%s/cmdline'%pid).read_bytes()
        if b'phone.py' in command or b'shell.py' in command:
            parent=int(subprocess.check_output(['ps','-o','ppid=','-p',str(pid)],text=True).strip())
            if b'start-demo.sh' in Path('/proc/%s/cmdline'%parent).read_bytes():os.kill(parent,signal.SIGTERM)
            os.kill(pid,signal.SIGTERM)
            for _ in range(50):
                if not Path('/proc/%s'%pid).exists():break
                time.sleep(.1)
            else:raise RuntimeError('Previous UI did not stop')
    except (FileNotFoundError,ProcessLookupError,ValueError):pass
    retired=['sim/index.html','sim/shell.css','sim/shell.js','sim/neuropolitical.woff']
    names=list(manifest['files'])+retired+['.omni-deployed.json']
    present={name for name in names if (root/name).is_file()}
    backups=state/'deploy-backups';backups.mkdir(exist_ok=True)
    backup=backups/('before-'+commit[:12]+'-'+str(time.time_ns())+'.tar.gz')
    with tarfile.open(backup,'w:gz') as saved:
        for name in sorted(present):saved.add(root/name,arcname=name,recursive=False)
    def launch():
        env=os.environ.copy()
        env['XDG_RUNTIME_DIR']='/run/user/%s'%os.getuid()
        env['WAYLAND_DISPLAY']=env.get('WAYLAND_DISPLAY','wayland-0')
        env['SDL_VIDEODRIVER']='wayland'
        with (state/'ui-deploy.log').open('w') as log:
            return subprocess.Popen(['sh',str(root/'firmware/start-demo.sh')],cwd=root,env=env,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        print('Installing commit '+commit,flush=True)
        source.extractall(root,filter='data')
        for name in retired:
            if name not in manifest['files']:(root/name).unlink(missing_ok=True)
        check()
        env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
        for folder in ('firmware','cloud'):
            subprocess.run([python,'-m','unittest','discover','-s',folder,'-p','test_*.py'],cwd=root,env=env,check=True)
    except Exception:
        for name in names:
            if name not in present:(root/name).unlink(missing_ok=True)
        with tarfile.open(backup) as saved:saved.extractall(root,filter='data')
        launch()
        raise
    if backend:(state/'app-backend').write_text(backend+'\n')
    print('Starting UI; backup: '+str(backup),flush=True)
    process=launch()
    for _ in range(60):
        if process.poll() is not None:raise RuntimeError('Launcher exited; see '+str(state/'ui-deploy.log'))
        if 'App backend:' in (state/'ui-deploy.log').read_text():break
        time.sleep(.5)
    else:raise RuntimeError('UI startup timed out; see '+str(state/'ui-deploy.log'))
    print('Deployed and verified %s (%s files). UI started.'%(commit,len(manifest['files'])),flush=True)
Path(archive).unlink()
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',help='SSH target, e.g. omni@100.124.54.78')
    parser.add_argument('--path',default='Omni',help='Pi deployment directory, relative to its home by default')
    parser.add_argument('--backend',choices=('demo','stub','gemini'),help='Save the Pi app backend preference')
    parser.add_argument('--verify',action='store_true',help='Only compare the deployed files with this commit')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.@-]+',args.target):parser.error('Invalid SSH target')
    root=Path(__file__).resolve().parents[1]
    if subprocess.run(['git','diff','--quiet','HEAD'],cwd=root).returncode:
        parser.error('Commit tracked changes before deploying so the version is reproducible')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    with tempfile.TemporaryDirectory(prefix='omni-deploy-') as temporary:
        archive=Path(temporary)/'release.tar'
        subprocess.run(['git','archive','--format=tar','-o',str(archive),commit],cwd=root,check=True)
        with tarfile.open(archive) as source:
            files={member.name:hashlib.sha256(source.extractfile(member).read()).hexdigest()
                   for member in source if member.isfile()}
        body=json.dumps({'commit':commit,'files':files},indent=2).encode()
        with tarfile.open(archive,'a') as output:
            info=tarfile.TarInfo('.omni-deployed.json');info.size=len(body)
            output.addfile(info,io.BytesIO(body))
        remote='/tmp/omni-release-%s.tar'%uuid.uuid4().hex
        subprocess.run(['scp',str(archive),args.target+':'+remote],check=True)
        command=shlex.join(['python3','-c',REMOTE,remote,args.path,commit,'yes' if args.verify else 'no',args.backend or ''])
        subprocess.run(['ssh',args.target,command],check=True)


if __name__=='__main__':main()
