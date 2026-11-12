"""Generate pilot 0.6.196 from authenticated pilot 0.6.195 with only approved UI changes.
No checkout or access to private Plany source; transformed files match immutable Git blob hashes.
"""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'Plany-0.6.195.rbz'
BASE_MANIFEST=ROOT/'manifest-base.json'
OUTPUT=ROOT/'Plany-0.6.196.rbz'
OUTPUT_MANIFEST=ROOT/'manifest-196.json'
BASE_SHA='996a60af6ab383b22d6376d1999b10b2d00ef12403a14d42d68e7b7e569bfd53'
SOURCE_SHA='914b983964189a1014428a9737a3eefc013b3795'
EXPECTED_BASE={
  'plany/ui/app.js':'33d59a38230887dad62096f9f48348df3f8db2b2',
  'plany/ui/styles.css':'b05a00bc55ac6bff85d2bb40a9fda1efeb124e40',
  'plany/ui/standards.css':'c404389eed10ddad9d00e9b7cbc6796225575ff6',
  'plany/central/app.js':'5e03fe000da8da32a697ee83ee5c043f200ebf60',
  'plany.rb':'14bd26a399f91b81be6f2468a0e34a40ae2ac895',
  'plany/distribution.json':'d440104e371ebca971a06c49fde75ffe8d27bc98',
}
EXPECTED_FINAL={
  'plany/ui/app.js':'bae2d6d5a2a4687b7829b5ce935ea20e48ed8147',
  'plany/ui/styles.css':'6efeaa15d4795affed1b4d080e24df0d86572609',
  'plany/ui/standards.css':'23e118496d46654d0c5e1ce4b685e591b3a4a41c',
  'plany/central/app.js':'dee9574b46dc0882d0dd21ad4b763f680612cedf',
  'plany.rb':'88211d97883536cb8db033463a925849ab3c3af1',
  'plany/distribution.json':'2eaf917c882773a2171d7118bf1ca5bbd4b6a8d5',
}

def blob_sha(data):
    # Git normalizes CRLF, but the Windows-packaged asset can retain CRLF.
    data=data.replace(b'\r\n',b'\n')
    return hashlib.sha1(('blob %d\0'%len(data)).encode()+data).hexdigest()

def replace_one(s,old,new,name,normalize=True):
    if normalize and '\r\n' in s:
        old=old.replace('\n','\r\n')
        new=new.replace('\n','\r\n')
    assert s.count(old)==1, '%s: anchor occurs %d times'%(name,s.count(old))
    return s.replace(old,new,1)

def patch_app(s):
    s=replace_one(s,
      '    if(mainTabs)mainTabs.hidden=settingsVisible||moduleSelected&&focusedEditor||catalogPicker||!!standaloneTrim||pieceActionVisible;',
      '    // A peça isolada mantém a navegação principal; somente a segunda faixa (de módulos) desaparece.\n    if(mainTabs)mainTabs.hidden=settingsVisible||moduleSelected&&focusedEditor||catalogPicker||!!standaloneTrim||moduleSelected&&piecesView&&pieceEditorOpen;',
      'top bar for loose pieces')
    start=s.index('      var inventory=state.moduleInventory')
    stop=s.index('      if(!(state.moduleMaterials||[]).length)return;',start)
    assert 'function renderCustomMaterials()' in s[:start] and 'Inventário do conjunto' in s[start:stop]
    s=s[:start]+('      // Sem inventário visual: os dados de produção permanecem no estado e no backend.\r\n' if '\r\n' in s else '      // Sem inventário visual: os dados de produção permanecem no estado e no backend.\n')+s[stop:]
    s=replace_one(s,
      "    var title=document.createElement('h3');title.textContent='Configurar prateleira composta';editor.appendChild(title);\n",
      '', 'shelf heading')
    s=replace_one(s,
      "      if(!root.querySelector('h2,h3')){var title=document.createElement('h3');title.className='plany-config-title';",
      "      // Aba Propriedades já nomeia este painel; manter Configurar módulo/peça nas fichas.\n      if(id!=='construction-settings'&&!root.querySelector('h2,h3')){var title=document.createElement('h3');title.className='plany-config-title';",
      'property heading')
    s=replace_one(s,
      'name.textContent=entry.name; dimensions.textContent=format(entry.params.width)',
      "name.textContent=entry.name; dimensions.className='plany-card-measure'; dimensions.textContent=format(entry.params.width)",
      'module measures')
    s=replace_one(s,
      "symbol.textContent='▱';title.textContent=creating&&labels[entry.id]||entry.name;sizes.textContent=",
      "symbol.textContent='▱';title.textContent=creating&&labels[entry.id]||entry.name;sizes.className='plany-card-measure';sizes.textContent=",
      'piece measures')
    return s

def patch_styles(s):
    s=replace_one(s,
      '.tabs{display:flex;flex-wrap:nowrap;overflow-x:visible;gap:0}\n.tabs .tab{flex:1 1 0;min-width:0;margin-left:0;text-align:center;white-space:normal;padding:14px 3px 12px;font-size:11px}',
      '.tabs{display:flex;flex-wrap:nowrap;justify-content:space-between;overflow-x:visible;gap:0}\n.tabs .tab{flex:1 1 auto;min-width:0;margin-left:0;text-align:center;white-space:nowrap;padding:14px 3px 12px;font-size:11px}',
      'main tab 1 line')
    anchor='#piece-starters .piece-library-symbol,#saved-pieces .piece-library-symbol{height:76px;padding:0;display:flex;align-items:center;justify-content:center}'
    extra="""/* Tipografia exclusivamente dos tamanhos; o grid continua com 3 colunas. */
#starters .library-card .plany-card-measure,#saved-library .library-card .plany-card-measure,#piece-starters .library-card .plany-card-measure,#saved-pieces .library-card .plany-card-measure{font-size:8px;line-height:1.5;letter-spacing:-.25px;white-space:nowrap}
@media(min-width:480px){#starters .library-card .plany-card-measure,#saved-library .library-card .plany-card-measure,#piece-starters .library-card .plany-card-measure,#saved-pieces .library-card .plany-card-measure{font-size:9px}}
@media(min-width:700px){#starters .library-card .plany-card-measure,#saved-library .library-card .plany-card-measure,#piece-starters .library-card .plany-card-measure,#saved-pieces .library-card .plany-card-measure{font-size:10px}}"""
    return replace_one(s,anchor,anchor+'\n'+extra,'library measurement typography')

def patch_standards(s):
    return replace_one(s,
      'body[data-plany-surface="panel"] .tab{font-size:12px;white-space:normal}',
      'body[data-plany-surface="panel"] .tab{font-size:11px;white-space:nowrap}', 'later cascade override')

def patch_central(s):
    return replace_one(s,
      "const stockEssentials=PlanyUi.group(document,'Essenciais',true);$('stocks').parentNode.insertBefore(stockEssentials.node,$('stocks'));stockEssentials.body.appendChild($('stocks'));\n",
      '// Chapas ficam visíveis diretamente, sem o acordeão Essenciais não solicitado.\n',
      'stock essentials')

def patch_html(s,old_css,new_css):
    # standards.css is inlined by package_contract.py. It uses LF independent of
    # physical Windows CRLF. Preserve that exact packaging requirement.
    orig=old_css.replace('\r\n','\n')
    final=new_css.replace('\r\n','\n')
    assert s.count(orig)==1, 'standards.css embedding is not unique'
    s=s.replace(orig,final,1)
    s=replace_one(s,'<span class="version">0.6.195</span>','<span class="version">0.6.196</span>','ui version')
    s=replace_one(s,'title="Plany 0.6.195"','title="Plany 0.6.196"','version tooltip')
    s=replace_one(s,'Piloto 17 · Extensão para marcenaria','Piloto 18 · Extensão para marcenaria','pilot badge')
    return s

def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,'Unexpected base package'
    manifest=json.loads(BASE_MANIFEST.read_text(encoding='utf-8'))
    assert manifest['version']=='0.6.195' and manifest['sha256']==BASE_SHA
    assert manifest['distribution_kind']=='update'
    assert manifest['distribution']['channel']=='pilot'
    assert manifest['distribution']['repository']=='raullqueirozz9292/Plany-Piloto'
    assert str(manifest['distribution']['pilot'])=='17'
    with zipfile.ZipFile(BASE) as z:
        assert z.testzip() is None
        original=z.namelist()
        assert len(set(original))==len(original) and set(original)==set(manifest['files'])
        for path,sha in EXPECTED_BASE.items():
            assert blob_sha(z.read(path))==sha,'Unexpected packaged base '+path
        read=lambda name:z.read(name).decode('utf-8')
        css_old=read('plany/ui/standards.css')
        css_new=patch_standards(css_old)
        changed={
          'plany/ui/app.js':patch_app(read('plany/ui/app.js')).encode('utf-8'),
          'plany/ui/styles.css':patch_styles(read('plany/ui/styles.css')).encode('utf-8'),
          'plany/ui/standards.css':css_new.encode('utf-8'),
          'plany/central/app.js':patch_central(read('plany/central/app.js')).encode('utf-8'),
          'plany/ui/index.html':patch_html(read('plany/ui/index.html'),css_old,css_new).encode('utf-8'),
          'plany.rb':replace_one(read('plany.rb'),"extension.version = '0.6.195'","extension.version = '0.6.196'",'loader version').encode('utf-8'),
          'plany/distribution.json':replace_one(read('plany/distribution.json'),'"pilot": "17"','"pilot": "18"','pilot number').encode('utf-8')
        }
        assert set(changed)==set(EXPECTED_FINAL)|{'plany/ui/index.html'}
        for name,sha in EXPECTED_FINAL.items():
            assert blob_sha(changed[name])==sha, 'Not byte-equivalent to reviewed private source '+name
        dist=json.loads(changed['plany/distribution.json'])
        assert dist['pilot']=='18' and dist['channel']=='pilot'
        assert 'id="solo-piece"' in changed['plany/ui/index.html'].decode()
        assert 'id="assembly-editor"' not in changed['plany/ui/index.html'].decode()
        with zipfile.ZipFile(OUTPUT,'w',zipfile.ZIP_DEFLATED) as out:
            for info in z.infolist():
                out.writestr(info,changed.get(info.filename,z.read(info.filename)))
    with zipfile.ZipFile(OUTPUT) as z,zipfile.ZipFile(BASE) as original:
        assert z.testzip() is None and set(z.namelist())==set(manifest['files'])
        for name in manifest['files']:
            if name not in changed:
                assert z.read(name)==original.read(name),'Inherited file unexpectedly modified '+name
        app=z.read('plany/ui/app.js')
        assert b"selectionKind==='piece'||!selectionPayload.can_combine" in app
        assert b"Configurar prateleira composta" not in app
        assert b'Invent\xc3\xa1rio do conjunto' not in app
        assert b"moduleSelected&&piecesView&&pieceEditorOpen" in app
        assert z.read('plany/ui/index.html').count(css_new.replace('\r\n','\n').encode())==1
    new=json.loads(json.dumps(manifest))
    new.update(version='0.6.196',archive=OUTPUT.name,source_commit=SOURCE_SHA,sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest())
    new['distribution']['pilot']='18'
    OUTPUT_MANIFEST.write_text(json.dumps(new,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print('PASS',OUTPUT.name,new['sha256'],'total_files',len(manifest['files']),'modified',len(changed))
if __name__=='__main__':main()
