"""Derive the approved 0.6.185 update RBZ byte-for-byte from public
0.6.184 pilot RBZ. Never fetch/clone private Plany source or weaken digest gate.

The package was independently generated and tested from the private source at
commit 233d5ff64a2a618adb9dddf0dfac47def194d2fa in Windows Actions.
Publication is prohibited unless the public-baseline-plus-patch ZIP digest is
IDENTICAL to that independently tested artifact.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
SOURCE='233d5ff64a2a618adb9dddf0dfac47def194d2fa'
EXPECTED='6e391489ddd19e65860ef1d80d5ffdf7d5791e8abe98f28ca5ff6180a69685b8'
BASE_SHA='07a0a1142d4701ee891a7b6184feca43f0481f1457ee0485665959542b17f404'
OLD=ROOT/'Plany-0.6.184.rbz'
OUT=ROOT/'Plany-0.6.185.rbz'
OLD_MANIFEST=ROOT/'manifest.json'
NEW_MANIFEST=ROOT/'manifest-185.json'

def must_replace(s,before,after,label):
    # Pilot 0.6.184 was packaged on Windows with CRLF text. Match the
    # original line endings rather than silently normalizing packaged bytes.
    if '\r\n' in s and '\n' in before and '\r\n' not in before:
        before=before.replace('\n','\r\n')
        after=after.replace('\n','\r\n')
    count=s.count(before)
    if count!=1:
        focus=s.find('f.finish.id') if label=='click intent' else s.find(before.splitlines()[0][:25])
        print('PATCH_ANCHOR_DEBUG', label, repr(s[max(0,focus-280):focus+650]), flush=True)
    assert count==1, f'{label}: expected exactly 1 old anchor, got {count}: {before[:140]}'
    return s.replace(before,after,1)

def patch_policy(old):
    s=old
    s=must_replace(s,
        "pending={operation:op.operation_id,frame:armed.frame,action:action,texts:",
        "pending={operation:op.operation_id,frame:armed.frame,intent:armed.intent,action:action,texts:",
        'pending native operation')
    s=must_replace(s,
        "var now=frameFor();if(now&&(now.key===p.frame.key||p.proven.retargeted_from===op.target_id&&now.kind===p.frame.kind))finish(now);",
        """var now=frameFor();if(now&&(now.key===p.frame.key||p.proven.retargeted_from===op.target_id&&now.kind===p.frame.kind)){
        // Enter applies and keeps the editing session open. Only explicit
        // Concluir may take the terminal close path after native proof.
        if(p.intent==='apply'){clearErrors(now);env.refresh();}
        else finish(now);
      }""",
        'native application result')
    s=must_replace(s,
        """if(e.target.closest('#'+f.finish.id)&&!f.finish.disabled&&!(e.detail&&e.detail.planyIntent==='apply')){
          armed={frame:f,requested:false,errors:errorSerial};""",
        """if(e.target.closest('#'+f.finish.id)&&!f.finish.disabled){
          if(pending){e.preventDefault();e.stopImmediatePropagation();return;}
          // Both explicit Concluir and Enter/Apply must arm the same native
          // receipt tracking. Only their terminal navigation differs.
          armed={frame:f,intent:e.detail&&e.detail.planyIntent==='apply'?'apply':'finish',requested:false,errors:errorSerial};""",
        'click intent')
    s=must_replace(s,
        "if(!intent.requested&&intent.errors===errorSerial)",
        "if(!intent.requested&&intent.intent==='finish'&&intent.errors===errorSerial)",
        'non-request fallback')
    return s

def patch_app(s):
    return must_replace(s,
        """    if(!button||button.hidden||button.disabled)return;
    event.preventDefault();event.stopPropagation();
    // Enter persists the current configuration without invoking Concluir.""",
        """    if(!button||button.hidden||button.disabled)return;
    // A module that is already canonical must not create an empty native
    // transaction (or discard the SketchUp Redo stack) just from Enter.
    if(button.id==='primary-action'&&selectionKind==='module'&&!state.dirty&&!insertSessionActive()&&!editorContext){
      event.preventDefault();event.stopPropagation();return;
    }
    event.preventDefault();event.stopPropagation();
    // Enter persists the current configuration without invoking Concluir.""",
        'Enter no-op guard')

def patch_loader(s):
    s=must_replace(s,
      "SketchupExtension.new('Plany — Módulos · Piloto 09', 'plany/main')",
      "SketchupExtension.new('Plany — Módulos · Piloto 10', 'plany/main')",
      'loader pilot')
    s=must_replace(s,"extension.version = '0.6.184'","extension.version = '0.6.185'",'loader version')
    return s

def patch_header(s):
    return must_replace(s,
      '<strong>Plany<span class="version">0.6.184</span></strong><small title="Plany 0.6.184 · Piloto 09">Piloto 09 · Extensão para marcenaria</small>',
      '<strong>Plany<span class="version">0.6.185</span></strong><small title="Plany 0.6.185 · Piloto 10">Piloto 10 · Extensão para marcenaria</small>',
      'HTML header')

def main():
    assert hashlib.sha256(OLD.read_bytes()).hexdigest()==BASE_SHA, 'Public baseline RBZ SHA mismatch'
    old_m=json.loads(OLD_MANIFEST.read_text(encoding='utf-8'))
    assert old_m['version']=='0.6.184'
    assert old_m['sha256']==BASE_SHA
    assert old_m['distribution_kind']=='update'
    assert old_m['distribution']['channel']=='pilot'
    assert old_m['distribution']['repository']=='raullqueirozz9292/Plany-Piloto'
    new_m=json.loads(json.dumps(old_m))
    new_m['version']='0.6.185'
    new_m['archive']=OUT.name
    new_m['source_commit']=SOURCE
    new_m['distribution']['pilot']='10'
    with ZipFile(OLD) as z:
        assert z.testzip() is None, 'Public RBZ corrupt'
        original_names=z.namelist()
        assert len(original_names)==len(set(original_names)), 'Duplicate paths in public baseline'
        # The historical 0.6.184 package order is not guaranteed to be sorted.
        # Current tools/package.py sorts source paths before writing the ZIP.
        names=sorted(original_names)
        assert len(names)==473 and set(names)==set(old_m['files']), 'Unexpected archived file set'
        policy_old=z.read('plany/ui/editor-policy.js').decode('utf-8')
        policy_new=patch_policy(policy_old)
        embedded=z.read('plany/ui/index.html').decode('utf-8')
        assert embedded.count(policy_old)==1, 'Cannot locate exactly one embedded editor policy'
        embedded=must_replace(embedded,policy_old,policy_new,'embedded native policy')
        embedded=patch_header(embedded)
        replacements={
            'plany/ui/editor-policy.js':policy_new.encode('utf-8'),
            'plany/ui/app.js':patch_app(z.read('plany/ui/app.js').decode('utf-8')).encode('utf-8'),
            'plany/ui/index.html':embedded.encode('utf-8'),
            'plany.rb':patch_loader(z.read('plany.rb').decode('utf-8')).encode('utf-8'),
        }
        dist=json.loads(z.read('plany/distribution.json'))
        assert dist==old_m['distribution']
        dist['pilot']='10'
        # The original source uses two-space pretty JSON with trailing newline.
        original_json=z.read('plany/distribution.json').decode('utf-8')
        replacements['plany/distribution.json']=must_replace(
            original_json, '"pilot": "09"', '"pilot": "10"','distribution version'
        ).encode('utf-8')
        with ZipFile(OUT,'w',ZIP_DEFLATED) as new:
            for name in names:
                new.writestr(name,replacements.get(name,z.read(name)))
    with ZipFile(OUT) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(old_m['files'])
        assert z.read('plany/ui/editor-policy.js')==policy_new.encode()
        assert policy_new.encode() in z.read('plany/ui/index.html')
    digest=hashlib.sha256(OUT.read_bytes()).hexdigest()
    assert digest==EXPECTED, (
        f'Refusing publication: public-baseline patched package SHA {digest} differs '
        f'from fully tested source artifact {EXPECTED}.'
    )
    new_m['sha256']=digest
    NEW_MANIFEST.write_text(json.dumps(new_m,ensure_ascii=True,indent=2),encoding='utf-8')
    print('MATCH',OUT.name,digest,'source',SOURCE,'files',len(names))

if __name__=='__main__':
    main()
