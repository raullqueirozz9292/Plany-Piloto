"""Pilot 0.6.197 / 19: strictly scoped piece editor placement from authentic v0.6.196.
Preserve all other files byte-for-byte; validate modified Git blob hashes against
the isolated reviewed Plany source branch. No private checkout needed.
"""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'Plany-0.6.196.rbz'
BASE_MANIFEST=ROOT/'manifest-base.json'
OUT=ROOT/'Plany-0.6.197.rbz'
OUT_MANIFEST=ROOT/'manifest-197.json'
BASE_PACKAGE_SHA='a9240cba3452a0db384e63d976fcfcdbfd45b3b533d92d13ddbdae0705490e07'
SOURCE_SHA='c69b4f4975fd8c8d527f4544a34f6804eb0ba802'
BASE_BLOBS={
 'plany/ui/index.html':'86f7c9ce4dc17b0afc391ebb8e10fe72626086bf',
 'plany/ui/app.js':'bae2d6d5a2a4687b7829b5ce935ea20e48ed8147',
 'plany/ui/styles.css':'6efeaa15d4795affed1b4d080e24df0d86572609',
 'plany.rb':'88211d97883536cb8db033463a925849ab3c3af1',
 'plany/distribution.json':'2eaf917c882773a2171d7118bf1ca5bbd4b6a8d5',
}
EXPECTED_BLOBS={
 'plany/ui/app.js':'813ceb9cd67751ce2e3670e6bd47579d3904457c',
 'plany/ui/styles.css':'b00fccbfbbc804a39d9233d5828a6692fa73e5f7',
 'plany.rb':'297cd68b5efd37a2aff22d4ab686def3f63d1209',
 'plany/distribution.json':'df84e29764ad8db51a1519f54a8f316dc171aa72',
}
def blob_sha(data):
    data=data.replace(b'\r\n',b'\n')
    return hashlib.sha1(('blob %d\0'%len(data)).encode()+data).hexdigest()

def once(source,old,new,description):
    if '\r\n' in source:
        old=old.replace('\n','\r\n')
        new=new.replace('\n','\r\n')
    assert source.count(old)==1, '%s: expected 1 occurrence; found %d'%(description,source.count(old))
    return source.replace(old,new,1)

def patch_html(s):
    s=once(s,
'''<div class="piece-editor-toolbar"><button id="solo-back-to-pieces" type="button" class="text-button">Ver peças avulsas do projeto</button><button id="solo-delete-piece" type="button" class="text-button danger">Excluir peça</button></div>
          <div class="piece-name-row"><button title="Retira a peça do grupo e a coloca na raiz do modelo, mantendo posição, medidas e acabamentos." id="solo-detach-piece" type="button" class="text-button" hidden>Tornar peça avulsa</button></div>''',
'''<div class="piece-editor-toolbar" aria-label="Ações da peça"><button title="Retira a peça do grupo e a coloca na raiz do modelo, mantendo posição, medidas e acabamentos." id="solo-detach-piece" type="button" class="text-button" hidden>Tornar peça avulsa</button><button id="solo-delete-piece" type="button" class="text-button danger">Excluir peça</button></div>
          <button id="solo-back-to-pieces" type="button" hidden>Ver peças avulsas do projeto</button>''',
 'avulsa: duas ações no topo, retorno oculto')
    s=once(s,
'''  <div class="piece-editor-toolbar"><button id="back-to-pieces" type="button" class="text-button">← Voltar para peças do módulo</button><button id="delete-piece" type="button" class="text-button danger">Excluir peça</button></div>
  <input id="piece-role" type="hidden">
  <div class="piece-name-row"><button title="Retira a peça do grupo e a coloca na raiz do modelo, mantendo posição, medidas e acabamentos." id="detach-piece" type="button" class="text-button">Tornar peça avulsa</button></div>''',
'''  <div class="piece-editor-toolbar" aria-label="Ações da peça"><button title="Retira a peça do grupo e a coloca na raiz do modelo, mantendo posição, medidas e acabamentos." id="detach-piece" type="button" class="text-button">Tornar peça avulsa</button><button id="delete-piece" type="button" class="text-button danger">Excluir peça</button></div>
  <button id="back-to-pieces" type="button" hidden>← Voltar para peças do módulo</button>
  <input id="piece-role" type="hidden">''',
 'módulo: ações no topo, retorno oculto')
    s=once(s,
'''            <label class="field">Elevação<div class="unit-input"><input id="solo-elevation" inputmode="decimal" aria-label="Elevação da base da peça em milímetros"><span>mm</span></div></label>
          </div>
<label class="field">MDF da peça''',
'''            <label class="field">Elevação<div class="unit-input"><input id="solo-elevation" inputmode="decimal" aria-label="Elevação da base da peça em milímetros"><span>mm</span></div></label>
          </div>
          <div class="plany-piece-divider" aria-hidden="true"></div>
<label class="field">MDF da peça''',
 'avulsa: separador após medidas')
    s=once(s,
'''    <label class="field">Elevação<div class="unit-input"><input id="piece-elevation" inputmode="decimal" aria-label="Elevação da base da peça em milímetros"><span>mm</span></div></label>
  </div>
  <label class="field">MDF da peça''',
'''    <label class="field">Elevação<div class="unit-input"><input id="piece-elevation" inputmode="decimal" aria-label="Elevação da base da peça em milímetros"><span>mm</span></div></label>
  </div>
  <div class="plany-piece-divider" aria-hidden="true"></div>
  <label class="field">MDF da peça''',
 'módulo: separador após medidas')
    s=once(s,'<span class="version">0.6.196</span>','<span class="version">0.6.197</span>','versão cabeçalho')
    s=once(s,'title="Plany 0.6.196"','title="Plany 0.6.197"','versão hint')
    s=once(s,'Piloto 18 · Extensão para marcenaria','Piloto 19 · Extensão para marcenaria','piloto cabeçalho')
    return s

def patch_app(s):
    s=once(s,
'''    // A ficha de peça avulsa segue o cartão simples dos módulos: nome, medidas
    // e, por último, informações de MDF e fitagem, sem três subtítulos extras.
    var soloRoot=$('solo-piece'),soloToolbar=soloRoot.querySelector('.piece-editor-toolbar'),soloDimensions=soloRoot.querySelector('.dimensions'),soloDetach=soloRoot.querySelector('.piece-name-row');
    if(soloToolbar&&soloDimensions){
      soloRoot.insertBefore(soloToolbar,soloDimensions.nextSibling);
      if(soloDetach)soloRoot.insertBefore(soloDetach,soloToolbar);
    }
''',
'''    // Nas fichas de peças, as ações ficam no topo do cartão;
    // medidas e MDF/fitagem são separados pelo divisor aprovado.
    // Não deslocar a barra de ações para o meio dos campos.
''',
 'não mover ações ao meio')
    s=once(s,
'''      groupChildren(root,[{title:'Identificação',nodes:[name]},{title:'Medidas',nodes:[dimensions,position]},{title:'Materiais e acabamento',nodes:rest}]);
    });''',
'''      groupChildren(root,[{title:'Identificação',nodes:[name]},{title:'Medidas',nodes:[dimensions,position]},{title:'Materiais e acabamento',nodes:rest}]);
      // A ficha vinculada tem famílias próprias: posicionar a divisória
      // entre Medidas e Materiais, não dentro dos campos de MDF.
      var divider=root.querySelector('.plany-piece-divider');
      var groups=Array.prototype.filter.call(root.children,function(node){return node.classList&&node.classList.contains('plany-config-group');});
      if(divider&&groups.length===3)root.insertBefore(divider,groups[2]);
    });''',
 'divisor entre famílias')
    return s

def patch_css(s):
    s=once(s,
'''.piece-editor-toolbar{margin-bottom:16px}
.piece-editor-toolbar .text-button,.piece-name-row .text-button{padding:2px 0;font-size:11px;white-space:nowrap}''',
'''.piece-editor-toolbar{margin:0 0 16px;min-height:28px;min-width:0}
.piece-editor-toolbar .text-button,.piece-name-row .text-button{padding:2px 0;font-size:11px;white-space:nowrap;flex:0 0 auto}
.piece-editor-toolbar .text-button.danger{margin-left:auto}
.plany-piece-divider{display:block;height:0;border:0;border-top:1px solid var(--line);margin:16px 0;padding:0}
/* A ficha vinculada já possui três famílias; o separador substitui a
   borda superior da família de MDF para não criar duas linhas. */
#module-piece-editor>.plany-piece-divider+.plany-config-family{border-top:0;margin-top:0;padding-top:0}''',
 'CSS de linha única, alinhamento e divisor')
    return s

def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_PACKAGE_SHA,'invalid base RBZ'
    m=json.loads(BASE_MANIFEST.read_text(encoding='utf-8'))
    assert m['version']=='0.6.196' and m['sha256']==BASE_PACKAGE_SHA
    assert m['distribution_kind']=='update' and m['distribution']['channel']=='pilot'
    assert m['distribution']['repository']=='raullqueirozz9292/Plany-Piloto'
    assert str(m['distribution']['pilot'])=='18'
    with zipfile.ZipFile(BASE) as z:
        assert z.testzip() is None
        originals=z.namelist()
        assert len(originals)==len(set(originals)) and set(originals)==set(m['files'])
        for p,sha in BASE_BLOBS.items():
            if p!='plany/ui/index.html': # inlined standards.css makes HTML distinct from source Git blob
                assert blob_sha(z.read(p))==sha,'baseline source mismatch: '+p
        read=lambda path:z.read(path).decode('utf-8')
        changed={
         'plany/ui/index.html':patch_html(read('plany/ui/index.html')).encode('utf-8'),
         'plany/ui/app.js':patch_app(read('plany/ui/app.js')).encode('utf-8'),
         'plany/ui/styles.css':patch_css(read('plany/ui/styles.css')).encode('utf-8'),
         'plany.rb':once(read('plany.rb'),"extension.version = '0.6.196'","extension.version = '0.6.197'",'version loader').encode('utf-8'),
         'plany/distribution.json':once(read('plany/distribution.json'),'"pilot": "18"','"pilot": "19"','pilot number').encode('utf-8')
        }
        for p,sha in EXPECTED_BLOBS.items():
            assert blob_sha(changed[p])==sha,'source Git hash mismatch: '+p
        with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as dest:
            for info in z.infolist():
                dest.writestr(info,changed.get(info.filename,z.read(info.filename)))
    with zipfile.ZipFile(OUT) as z,zipfile.ZipFile(BASE) as base:
        assert z.testzip() is None and set(z.namelist())==set(m['files'])
        for name in m['files']:
            if name not in changed:
                assert z.read(name)==base.read(name),'unapproved changed file '+name
        a=z.read('plany/ui/app.js').decode('utf-8')
        h=z.read('plany/ui/index.html').decode('utf-8')
        css=z.read('plany/ui/styles.css').decode('utf-8')
        assert 'soloRoot.insertBefore(soloToolbar' not in a
        assert a.count("root.insertBefore(divider,groups[2])")==1
        for id in ['solo-detach-piece','solo-delete-piece','detach-piece','delete-piece','solo-back-to-pieces','back-to-pieces']:
            assert h.count('id="'+id+'"')==1,id
        assert h.count('class="plany-piece-divider"')==2
        assert h.count('class="piece-editor-toolbar" aria-label="Ações da peça"')==2
        assert 'piece-editor-toolbar .text-button.danger{margin-left:auto}' in css
        assert 'version">0.6.197' in h
        d=json.loads(z.read('plany/distribution.json'))
        assert d['channel']=='pilot' and d['pilot']=='19'
    final=json.loads(json.dumps(m))
    final.update(version='0.6.197',archive=OUT.name,source_commit=SOURCE_SHA,sha256=hashlib.sha256(OUT.read_bytes()).hexdigest())
    final['distribution']['pilot']='19'
    OUT_MANIFEST.write_text(json.dumps(final,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print('PASS item12 package',OUT.name,'sha256',final['sha256'],'files',len(m['files']),'changed',len(changed))
if __name__=='__main__': main()
