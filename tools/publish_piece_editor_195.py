"""Publish candidate derived ONLY from authenticated pilot 0.6.194 RBZ.

Focal change: restore original piece editor, remove unauthorized assembly panel,
preserve legacy multi-selection combine and display edge banding at the end.
No source code is copied from the private repo into the public pilot repository.
The resulting modified individual files MUST match exact Git blob SHAs from
private source commit 9a3f27c31644d685d50e720803a348a77d99a40f.
"""
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO='raullqueirozz9292/Plany-Piloto'
BASE_VERSION='0.6.194'
VERSION='0.6.195'
PILOT='17'
SOURCE='9a3f27c31644d685d50e720803a348a77d99a40f'
BASE_PACKAGE_SHA='2924107ff242de4b3bc1688c209d0f8e7dcaf65b27f5d4dc74feee4e1d29f641'
BASE=ROOT/'Plany-0.6.194.rbz'
BASE_MANIFEST=ROOT/'manifest-base.json'
OUT=ROOT/'Plany-0.6.195.rbz'
OUT_MANIFEST=ROOT/'manifest-195.json'

BASE_BLOBS={
  'plany/ui/app.js':'dee11305927825898226e786339f97fd3fa65b4a',
  'plany.rb':'7be1e5661e03400d72f91a5e700c4ba89ecaa684',
  'plany/distribution.json':'1226f3605953bf59a69db2edabf27d55e6f2a6d7',
}
EXPECTED_BLOBS={
  'plany/ui/app.js':'33d59a38230887dad62096f9f48348df3f8db2b2',
  'plany.rb':'14bd26a399f91b81be6f2468a0e34a40ae2ac895',
  'plany/distribution.json':'d440104e371ebca971a06c49fde75ffe8d27bc98',
}

def git_blob_sha(data):
    # Windows installer stores many text assets with CRLF even when Git blobs use LF.
    data=data.replace(b'\r\n',b'\n')
    return hashlib.sha1(('blob %s\0' % len(data)).encode()+data).hexdigest()

def once(s,old,new,desc):
    # Patch source exactly, preserving the physical archive's newline convention.
    if '\r\n' in s:
        old=old.replace('\n','\r\n')
        new=new.replace('\n','\r\n')
    n=s.count(old)
    assert n==1, '%s: expected unique anchor, found %s' % (desc,n)
    return s.replace(old,new,1)

def patch_app(s):
    s=once(s,
      "    $('assemble-selection').hidden=!canAssemblePieces()&&!selectionPayload.can_combine;\n    $('assembly-editor').hidden=!canAssemblePieces();",
      "    // Peças avulsas abrem somente sua ficha, nunca o antigo montador não solicitado.\n    $('assemble-selection').hidden=selectionKind==='piece'||!selectionPayload.can_combine;",
      'hide solo assembly')
    s=once(s,
      "    if(selectionKind==='piece'){ $('solo-piece').insertBefore(assemble,$('solo-piece').firstChild);return; }",
      "    if(selectionKind==='piece'){\n      // O formulário de edição mantém seu cartão e título como primeiro conteúdo.\n      if(assemble.parentNode!==$('bulk-selection'))$('bulk-selection').insertBefore(assemble,$('bulk-title').nextSibling);\n      return;\n    }",
      'preserve solo title')
    s=once(s,"    if(!same)renderAssemblyPieces();\n","",'no assembly renderer call')
    start=s.index("  function canAssemblePieces(){")
    end=s.index("  function colorLink(id,target,callback)",start)
    s=s[:start]+s[end:]
    s=once(s,
      """  $('assemble-pieces').addEventListener('click',function(){
    clearEdgeHover();if(canAssemblePieces()){
      var name=$('assembly-name').value.trim(),entries={};
      if(!name){message('Informe o nome do módulo.','error');$('assembly-name').focus();return;}
      $('assembly-pieces').querySelectorAll('select').forEach(function(select){entries[select.dataset.pieceId]=select.value;});
      request('assemble_selection',[name,entries]);return;
    }
    if(selectionPayload.module_count>1){$('combine-warning').hidden=false;return;}
    request('combine_selection',[selectionPayload.targets,false]);
  });""",
      """  $('assemble-pieces').addEventListener('click',function(){
    clearEdgeHover();
    // Preserva o comando de união já existente antes do formulário (Piloto 0.6.191).
    if(selectionPayload.module_count>1){$('combine-warning').hidden=false;return;}
    request('combine_selection',[selectionPayload.targets,false]);
  });""",
      'legacy combination only')
    s=once(s,
      "    ['solo','piece'].forEach(function(prefix){",
      """    // A ficha de peça avulsa segue o cartão simples dos módulos: nome, medidas
    // e, por último, informações de MDF e fitagem, sem três subtítulos extras.
    var soloRoot=$('solo-piece'),soloToolbar=soloRoot.querySelector('.piece-editor-toolbar'),soloDimensions=soloRoot.querySelector('.dimensions'),soloDetach=soloRoot.querySelector('.piece-name-row');
    if(soloToolbar&&soloDimensions){
      soloRoot.insertBefore(soloToolbar,soloDimensions.nextSibling);
      if(soloDetach)soloRoot.insertBefore(soloDetach,soloToolbar);
    }
    ['piece'].forEach(function(prefix){""",
      'flat solo editor')
    assert 'canAssemblePieces()' not in s
    assert 'renderAssemblyPieces()' not in s
    return s

def patch_html(s):
    old="""          <div id="assembly-editor" class="item-editor" hidden>
            <label class="field">Nome do módulo<input id="assembly-name" maxlength="60" value="Módulo de peças" autocomplete="off"></label>
            <div id="assembly-pieces"></div>
          </div>
"""
    s=once(s,old,'','remove unwanted HTML')
    s=once(s,'<span class="version">0.6.194</span>','<span class="version">0.6.195</span>','visible version')
    s=once(s,'title="Plany 0.6.194"','title="Plany 0.6.195"','tooltip version')
    s=once(s,'Piloto 16 · Extensão para marcenaria','Piloto 17 · Extensão para marcenaria','pilot badge')
    assert 'id="assembly-editor"' not in s and 'id="assembly-name"' not in s
    return s

def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_PACKAGE_SHA,'Base RBZ digest differs'
    m=json.loads(BASE_MANIFEST.read_text(encoding='utf-8'))
    assert m['version']==BASE_VERSION and m['sha256']==BASE_PACKAGE_SHA,'Wrong baseline manifest'
    assert m['distribution_kind']=='update','Never switch to a complete installer'
    assert m['distribution']['repository']==REPO and m['distribution']['channel']=='pilot'
    assert str(m['distribution']['pilot'])=='16','Unexpected pilot sequence'
    with zipfile.ZipFile(BASE) as z:
        assert z.testzip() is None,'Corrupt baseline ZIP'
        entries=z.namelist()
        assert len(entries)==len(set(entries)) and set(entries)==set(m['files']), 'ZIP/manifest file list mismatch'
        for name,blob in BASE_BLOBS.items():
            assert git_blob_sha(z.read(name))==blob, 'Packaged source differs from immutable pilot 0.6.194: '+name
        updates={
          'plany/ui/app.js':patch_app(z.read('plany/ui/app.js').decode('utf-8')).encode('utf-8'),
          'plany/ui/index.html':patch_html(z.read('plany/ui/index.html').decode('utf-8')).encode('utf-8'),
          'plany.rb':once(z.read('plany.rb').decode('utf-8'),"extension.version = '0.6.194'","extension.version = '0.6.195'",'loader version').encode('utf-8'),
          'plany/distribution.json':once(z.read('plany/distribution.json').decode('utf-8'),'"pilot": "16"','"pilot": "17"','pilot channel').encode('utf-8'),
        }
        for name,blob in EXPECTED_BLOBS.items():
            assert git_blob_sha(updates[name])==blob,'Candidate changed file differs from private source: '+name
        dist=json.loads(updates['plany/distribution.json'])
        assert dist['channel']=='pilot' and dist['repository']==REPO and dist['pilot']==PILOT
        assert len(updates)==4,'Unexpected changes to package files'
        assert all(name in entries for name in updates)
        with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as out:
            for info in z.infolist():
                out.writestr(info,updates.get(info.filename,z.read(info.filename)))
    with zipfile.ZipFile(OUT) as check,zipfile.ZipFile(BASE) as baseline:
        assert check.testzip() is None
        assert set(check.namelist())==set(m['files'])
        for path in m['files']:
            if path not in updates:
                assert check.read(path)==baseline.read(path), 'Unauthorized change to inherited file '+path
        js=check.read('plany/ui/app.js').decode('utf-8')
        html=check.read('plany/ui/index.html').decode('utf-8')
        assert 'canAssemblePieces' not in js and 'id="assembly-editor"' not in html
        assert 'src="app.js"' in html and 'id="solo-preview"' in html
        assert 'version">0.6.195' in html
    digest=hashlib.sha256(OUT.read_bytes()).hexdigest()
    next_manifest=json.loads(json.dumps(m))
    next_manifest.update(version=VERSION,archive=OUT.name,sha256=digest,source_commit=SOURCE)
    next_manifest['distribution']['pilot']=PILOT
    OUT_MANIFEST.write_text(json.dumps(next_manifest,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print('PASS package generated; changed exactly 4 files; SHA256',digest,'files',len(m['files']))

if __name__=='__main__':main()
