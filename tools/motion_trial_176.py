#!/usr/bin/env python3
"""One-shot, reproducible 0.6.176 PILOT movement experiment.

Builds on publicly released 0.6.175 complete RBZ. Modifies ONLY the
hardware fix from private PR #73 and three pilot version/identity files.
Fails closed on any unexpected source, content, structure or digest.
No official channel, personal files, or repository source are modified.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

BASE_VERSION = "0.6.175"
NEW_VERSION = "0.6.176"
BASE_SHA256 = "c08459896d5927cf117b43bb2a887a97e60b95a9461b6b38bcd4ff5c3d35ad95"
BASE_HARDWARE_BLOB = "cf7dc1e1d72583d333f631b0ce3e331dfeb3f008"
PATCHED_HARDWARE_BLOB = "cec17a8d7824afaa4a1e1f920d3f6c87c0012317"
PATCHED_LOADER_BLOB = "4503e1f9b062505483c02050a0480799b07a2ff7"
PATCHED_DISTRIBUTION_BLOB = "ab1e0df14e54368dbb8b608a4d8a31016847c305"
SOURCE_COMMIT = "1c00f29851ebbe9abe2fb323fb229097018e6420"
BASE_ARCHIVE = Path(f"Plany-{BASE_VERSION}.rbz")
TARGET_ARCHIVE = Path(f"Plany-{NEW_VERSION}.rbz")
MUTATED = {"plany/hardware.rb", "plany.rb", "plany/ui/index.html", "plany/distribution.json"}

def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def replace_once(data: bytes, old: str, new: str) -> bytes:
    before = old.encode("utf-8")
    count = data.count(before)
    if count != 1:
        raise RuntimeError(f"Expected one match, got {count}: {old[:80]!r}")
    return data.replace(before, new.encode("utf-8"))

HARDWARE_ANCHOR = """      instance.definition.set_attribute(D, 'motion_key', spec['key'])
      if spec['kind'] == 'drawer'
"""
HARDWARE_REPLACEMENT = """      instance.definition.set_attribute(D, 'motion_key', spec['key'])
      # A front keeps its motion_key when changed from hinged to lift (or
      # another mobile type). Never let an old ROTZ, ROTX, X or Y expression
      # survive alongside the new motor. Otherwise DC can recompute a pose
      # from two incompatible axes during Interagir/redraw. This touches only
      # dynamic metadata; it does NOT clamp gaps or change the MDF recipe.
      active_axis = case spec['kind']
                    when 'drawer' then 'y'
                    when 'sliding' then 'x'
                    when 'lift' then 'rotx'
                    else 'rotz'
                    end
      [instance, instance.definition].each do |owner|
        %w[x y rotz rotx].each do |axis|
          # Even the active axis must not inherit a previously calculated
          # position formula: ANIMATE controls that axis from this point on.
          owner.delete_attribute(DC, "_#{axis}_formula") if owner.respond_to?(:delete_attribute)
          next if axis == active_axis
          owner.delete_attribute(DC, axis) if owner.respond_to?(:delete_attribute)
        end
      end
      if spec['kind'] == 'drawer'
"""

def patch(name: str, original: bytes) -> bytes:
    # Windows release packaging preserves CRLF even though Git sources use LF.
    # Normalize only the three source-controlled files that are replaced.
    if name in {"plany/hardware.rb", "plany.rb", "plany/distribution.json"}:
        original = original.replace(b"\\r\\n", b"\\n")
    if name == "plany/hardware.rb":
        if blob_sha(original) != BASE_HARDWARE_BLOB:
            raise RuntimeError("Base RBZ hardware differs: actual " + blob_sha(original) + " expected " + BASE_HARDWARE_BLOB + " ; anchor=" + str(HARDWARE_ANCHOR.encode("utf-8") in original) + " ; context=" + repr(original[original.find(b"def self.dynamic_motion"):original.find(b"def self.dynamic_motion")+650]))
        new = replace_once(original, HARDWARE_ANCHOR, HARDWARE_REPLACEMENT)
        if blob_sha(new) != PATCHED_HARDWARE_BLOB:
            raise RuntimeError("Movement patch differs from private PR #73")
        return new
    if name == "plany.rb":
        new = replace_once(original, "Plany — Módulos · Piloto 01", "Plany — Módulos · Piloto 02")
        new = replace_once(new, "extension.version = '0.6.175'", "extension.version = '0.6.176'")
        if blob_sha(new) != PATCHED_LOADER_BLOB:
            raise RuntimeError("Versioned loader differs from private source")
        return new
    if name == "plany/ui/index.html":
        new = replace_once(original, '<span class="version">0.6.175</span>', '<span class="version">0.6.176</span>')
        new = replace_once(new, "Plany 0.6.175 · Piloto 01", "Plany 0.6.176 · Piloto 02")
        new = replace_once(new, "Piloto 01 · Extensão para marcenaria", "Piloto 02 · Extensão para marcenaria")
        if b'<span class="version">0.6.176</span>' not in new:
            raise RuntimeError("Updated version not visible in UI")
        return new
    if name == "plany/distribution.json":
        new = replace_once(original, '"pilot": "01"', '"pilot": "02"')
        if blob_sha(new) != PATCHED_DISTRIBUTION_BLOB:
            raise RuntimeError("Pilot identity differs from private source")
        data = json.loads(new.decode("utf-8"))
        if data.get("schema") != 1 or data.get("channel") != "pilot" or data.get("repository") != "raullqueirozz9292/Plany-Piloto":
            raise RuntimeError("Pilot channel identity changed")
        if data.get("packages") != ["01", "02", "03"]:
            raise RuntimeError("Unexpected scope expansion into Package 04")
        return new
    return original

if not BASE_ARCHIVE.is_file() or sha256(BASE_ARCHIVE) != BASE_SHA256:
    raise RuntimeError("Base 0.6.175 is absent or does not match public release")
if TARGET_ARCHIVE.exists():
    raise RuntimeError("Candidate already exists: refusing overwrite")

changed = set()
all_entries = []
with zipfile.ZipFile(BASE_ARCHIVE) as base, zipfile.ZipFile(TARGET_ARCHIVE, "x") as target:
    entries = base.infolist()
    names = [item.filename for item in entries]
    if len(names) != len(set(names)) or not MUTATED.issubset(set(names)):
        raise RuntimeError("Base RBZ has unexpected or duplicate paths")
    if not names or any((n != "plany.rb" and not n.startswith("plany/")) or
                        ".." in n.split("/") or "\\" in n for n in names):
        raise RuntimeError("Invalid archive paths")
    for item in entries:
        data = base.read(item)
        new = patch(item.filename, data)
        if new != data:
            changed.add(item.filename)
        target.writestr(item, new)
        all_entries.append(item.filename)
if changed != MUTATED:
    TARGET_ARCHIVE.unlink(missing_ok=True)
    raise RuntimeError(f"Unexpected modified files: {changed ^ MUTATED}")
with zipfile.ZipFile(TARGET_ARCHIVE) as created:
    if created.testzip() is not None:
        raise RuntimeError("Corrupt candidate RBZ")
    if created.namelist() != all_entries:
        raise RuntimeError("File count/order changed")

release_digest = sha256(TARGET_ARCHIVE)
manifest = {
    "version": NEW_VERSION, "archive": TARGET_ARCHIVE.name, "sha256": release_digest,
    "files": sorted(all_entries), "distribution_kind": "complete",
    "source_commit": SOURCE_COMMIT,
    "distribution": json.loads(zipfile.ZipFile(TARGET_ARCHIVE).read("plany/distribution.json")),
    "experimental": True, "based_on": BASE_VERSION,
    "base_rbz_sha256": BASE_SHA256,
    "modified_files": sorted(changed),
    "known_limitation": "SketchUp 2024 native Interagir test not executed; historical drawer-spacing.rb fails on baseline",
}
Path("manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
Path("release_notes.md").write_text(
    "PILOTO EXPERIMENTAL 0.6.176 — correção focal de atributos dinâmicos antigos.\n\n"
    "Somente canal Plany-Piloto; Pacotes 01–03 preservados, Pacote 04 NÃO incluído.\n"
    "Mudança: ao reutilizar um wrapper para outro tipo de frente, limpar eixos antigos "
    "antes de registrar o novo ANIMATE. Valores negativos de folga permanecem permitidos.\n\n"
    "Este é um teste assistido, NÃO uma confirmação de que o erro de gavetas e basculantes está resolvido. "
    "Testes Ruby focais passaram no PR #73; a suíte histórica drawer-spacing.rb falha no baseline. "
    "Teste nativo real da interação de portas/gavetas ainda não executado.\n\n"
    f"Fonte experimental: https://github.com/raullqueirozz9292/Plany/commit/{SOURCE_COMMIT}\n"
    f"Integridade RBZ SHA-256: {release_digest}\n"
    f"Base preservada: v{BASE_VERSION}, SHA-256 {BASE_SHA256}\n"
    "Rollback: não sobrescreva a 0.6.175; se houver regressão, interrompa o uso em projetos reais.\n",
    encoding="utf-8",
)
print(json.dumps({"result":"READY", "archive":str(TARGET_ARCHIVE), "bytes":TARGET_ARCHIVE.stat().st_size,
                  "sha256":release_digest, "count":len(all_entries), "changed":sorted(changed)}, ensure_ascii=False))
