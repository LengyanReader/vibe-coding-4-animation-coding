"""ebook route — markdown → EPUB3 (+ optional PDF twin) via pandoc.

The document medium the coverage audit called this machine's biggest blind
spot (roadmap §2.6): every binary is already installed (pandoc 3.8.2.1,
XeTeX 4.11, pypdf 6.19.0 on interpreter A) — this module is the contract
that turns them into a *route*: spec → render → measure → validate → manifest.

Determinism is **designed in**, not discovered by a red golden (the audio
route's float-association lesson, audit §F1):
  * ``dc:identifier`` comes from the spec, never generated at render time;
  * zip entry timestamps are pinned — SOURCE_DATE_EPOCH is derived from the
    spec's metadata date and the archive is rewritten with fixed timestamps
    regardless of what pandoc honours;
  * the content hash covers the **normalised payload** (spine-order XHTML
    documents + the OPF), never the zip bytes — container byte hashes are not
    the fingerprint, exactly as mp4/wav containers are not (README §12.2).

Validation is stdlib-only for the EPUB (Java is absent, so epubcheck is not
an option): zipfile integrity → ``mimetype`` first and stored → container.xml
→ OPF (manifest hrefs exist, spine complete, required dc metadata) → every
spine document well-formed → TOC counted from the nav document. The PDF twin
is measured with pypdf (page count, MediaBox paper size, embedded fonts,
header version); where pypdf is absent (interpreter-scoped) the PDF checks
report ``skipped`` with the reason — never a silent pass (M0.2).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from . import cli, ffmpeg, provenance, registry, spec as spec_mod, validate

_FIXED_DT = (1980, 1, 1, 0, 0, 0)   # the zip format's earliest legal timestamp


class DocumentError(RuntimeError):
    """A document-tool failure (pandoc/xelatex), named for the right binary —
    the audio route's EngineError lesson: mislabelling the failing tool sends
    the reader of the log to the wrong documentation."""


def _require_file(value: str | None, what: str, tried: list[str] | None = None) -> Path:
    if not value:
        raise spec_mod.SpecError(f"ebook spec needs {what} (none declared)")
    p = Path(value)
    if not p.is_file():
        hint = f"; tried: {', '.join(tried)}" if tried else ""
        raise spec_mod.SpecError(
            f"ebook spec {what} not found: {p}{hint} — render or fetch it first "
            f"(e.g. python -m vcac.<route> for a generated asset)")
    return p


def _resolve_chapters(spec_dict: dict) -> list[Path]:
    chapters = spec_dict.get("chapters") or []
    if not chapters:
        raise spec_mod.SpecError("ebook spec needs a non-empty chapters list")
    missing = [c for c in chapters if not Path(c).is_file()]
    if missing:
        raise spec_mod.SpecError(
            f"ebook chapters missing on disk: {missing} — write them or fix the paths")
    return [Path(c) for c in chapters]


def _epoch_from_date(date_str: str) -> int:
    """SOURCE_DATE_EPOCH derived from the spec's own metadata date — the build
    is reproducible from the spec alone, never from the wall clock."""
    try:
        dt = datetime.fromisoformat(str(date_str))
    except (ValueError, TypeError):
        dt = datetime(1980, 1, 1)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _run_pandoc(argv: list[str], env: dict) -> None:
    registry.require("pandoc")   # gate; pandoc resolves from PATH
    r = subprocess.run(["pandoc", *argv], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise DocumentError(f"pandoc failed ({r.returncode}):\n{r.stderr[-2000:]}")
    # §2.6's promised gate: missing figures/fonts surface as stderr warnings —
    # they must become failures, not silently degrade the deliverable
    low = (r.stderr or "").lower()
    for marker in ("could not fetch resource", "image not found", "error:",
                   "laTeX warning: reference", "missing character"):
        if marker in low:
            raise DocumentError(f"pandoc reported: {r.stderr.strip()[-800:]}")


def _render(spec_dict: dict, chapters: list[Path], out_dir: Path,
            fmt: str) -> Path:
    meta = spec_dict["metadata"]
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(_epoch_from_date(meta.get("date"))))
    out = out_dir / ("book.epub" if fmt.startswith("epub") else "book.pdf")
    argv = ["-f", "markdown", "--toc",
            f"--toc-depth={int(spec_dict.get('toc_depth', 2))}"]
    # pandoc's dc:language is fed by the `lang` key; pass both. TWO argv
    # tokens (-M, key=value): a fused single token makes the key carry a
    # leading space, the metadata silently lands nowhere, and pandoc then
    # generates a RANDOM dc:identifier per render — the determinism killer.
    for k, v in meta.items():
        argv += ["-M", f"{k}={v}"]
        if k == "language":
            argv += ["-M", f"lang={v}"]
    css = spec_dict.get("css")
    if css:
        argv += ["--css", str(Path(css).resolve())]
    if fmt.startswith("epub"):
        argv += ["-t", "epub3",
                 "--epub-cover-image", str(_require_file(spec_dict.get("cover"), "cover image"))]
        argv += ["--split-level", str(int(spec_dict.get("split_level", 1)))]
    else:
        argv += ["-t", "pdf", "--pdf-engine", str(_pdf_engine())]
        if spec_dict.get("papersize"):
            argv += ["-V", f"papersize={spec_dict['papersize']}"]
        # Latin Modern has no CJK glyphs; the template wires xecjk from these
        mainfont = spec_dict.get("pdf_mainfont", "Noto Serif SC")
        argv += ["-V", f"mainfont={mainfont}",
                 "-V", f"CJKmainfont={spec_dict.get('pdf_cjk_mainfont', mainfont)}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    argv += ["-o", str(out), *[str(c) for c in chapters]]
    _run_pandoc(argv, env)
    if not out.is_file():
        raise DocumentError(f"pandoc produced no {fmt} output at {out}")
    return out


def _pdf_engine() -> str:
    # the xelatex binary is registered under the "miktex" key; pandoc resolves
    # it from PATH, so the engine string is just the name
    registry.require("miktex")
    return "xelatex"


def _pin_zip_timestamps(epub: Path) -> None:
    """Rewrite every zip entry with a fixed timestamp (and keep ``mimetype``
    first + stored, per the OCF spec). Container bytes stop being a function
    of the wall clock; the normalised payload hash below is the fingerprint."""
    src = zipfile.ZipFile(epub)
    names = src.namelist()
    blobs = [(n, src.read(n), src.getinfo(n).compress_type) for n in names]
    src.close()
    tmp = epub.with_suffix(".epub.pin")
    with zipfile.ZipFile(tmp, "w") as z:
        for name, blob, method in blobs:
            info = zipfile.ZipInfo(name, date_time=_FIXED_DT)
            # OCF requires mimetype first and uncompressed
            info.compress_type = zipfile.ZIP_STORED if name == "mimetype" else method
            z.writestr(info, blob)
    tmp.replace(epub)


def _text_of(parent: ET.Element, tag: str, ns: dict) -> str | None:
    # ".//" — dc:* live under <metadata>, a grandchild of <package>; a direct
    # child search returns None. Same-shaped trap: Element.__bool__ is
    # "has children", so `elem or {}` swallows every self-closed <item/>.
    el = parent.find(f".//{tag}", ns)
    return el.text.strip() if el is not None and el.text else None


def _measure_epub(epub: Path) -> dict:
    """Stdlib EPUB3 checks. Keys feed the acceptance rules; a malformed spine
    document is a render defect and raises (never measured-as-passed)."""
    zf = zipfile.ZipFile(epub)
    if zf.testzip() is not None:
        raise DocumentError(f"epub zip integrity check failed: {epub}")
    names = zf.namelist()
    info0 = zf.getinfo("mimetype") if "mimetype" in names else None
    if info0 is None or names[0] != "mimetype" or info0.compress_type != zipfile.ZIP_STORED:
        raise DocumentError("epub violates OCF: mimetype must be the first, stored entry")
    if zf.read("mimetype") != b"application/epub+zip":
        raise DocumentError("epub mimetype content is wrong")

    container = ET.fromstring(zf.read("META-INF/container.xml"))
    opf_path = next(c.get("full-path") for c in container.iter()
                    if c.tag.endswith("rootfile"))
    opf = ET.fromstring(zf.read(opf_path))
    ns = {"opf": "http://www.idpf.org/2007/opf",
          "dc": "http://purl.org/dc/elements/1.1/"}
    manifest = {i.get("id"): i for i in opf.findall(".//opf:manifest/opf:item", ns)}
    _SCAFFOLD = ("nav", "cover-image", "titlepage")
    def _is_scaffold(idref):
        item = manifest.get(idref)
        if item is None:          # Element is falsy when self-closed: never `or {}`
            return False
        props = item.get("properties") or ""
        base = Path(item.get("href") or "").stem.lower()
        return (any(s in props for s in _SCAFFOLD)
                or base.startswith(("cover", "title_page")))
    spine = [i.get("idref") for i in opf.findall(".//opf:spine/opf:itemref", ns)
             if not _is_scaffold(i.get("idref"))]
    if any(idref not in manifest for idref in spine):
        raise DocumentError(f"spine references ids missing from manifest: {epub}")

    opf_dir = Path(opf_path).parent
    missing = []
    hrefs = {}
    for item in manifest.values():
        href = item.get("href")
        target = str(opf_dir / href) if opf_dir != Path(".") else href
        target = target.replace("\\", "/")
        exists = target in names or href in names
        if not exists:
            missing.append(href)
        hrefs[item.get("id")] = (href, target)

    language = _text_of(opf, "dc:language", ns)
    title = _text_of(opf, "dc:title", ns)
    identifier = _text_of(opf, "dc:identifier", ns)
    cover_present = any("cover-image" in (i.get("properties") or "")
                        for i in manifest.values())

    # TOC: the nav document's toc list (EPUB3) or NCX navMap (EPUB2 fallback)
    toc_entries = 0
    nav_id = next((i for i, it in manifest.items()
                   if "nav" in (it.get("properties") or "")), None)
    xhtml_ns = {"x": "http://www.w3.org/1999/xhtml",
                "epub": "http://www.idpf.org/2007/ops"}
    if nav_id is not None:
        _, target = hrefs[nav_id]
        nav = ET.fromstring(zf.read(target))
        toc_entries = len(nav.findall(".//x:nav[@epub:type='toc']//x:a", xhtml_ns))

    # well-formedness of every spine document — a render defect, not a gate
    for idref in spine:
        href, target = hrefs[idref]
        if href.endswith((".xhtml", ".html")):
            ET.fromstring(zf.read(target))

    # the normalised payload: spine-order documents + the OPF, in the open
    payload = b""
    for idref in spine:
        payload += zf.read(hrefs[idref][1])
    payload += zf.read(opf_path)
    zf.close()
    content_hash = "sha256:" + hashlib.sha256(payload).hexdigest()
    return {
        "spine_count": len(spine),
        "toc_entries": toc_entries,
        "cover_present": bool(cover_present),
        "missing_hrefs": missing,
        "language": language or "",
        "title": title or "",
        "identifier": identifier or "",
        "content_hash": content_hash,
    }


def _measure_pdf(pdf: Path) -> dict:
    """pypdf checks for the PDF twin. pypdf is interpreter-scoped (docs/tools.md
    §0: present on 3.13.5, absent on hy_py312) — when absent, measure nothing:
    run_acceptance's needs-missing machinery then reports the PDF rules as
    `skipped` with the reason, honestly (M0.2)."""
    try:
        from pypdf import PdfReader
    except Exception:
        return {"pdf_reason": "pypdf absent in this interpreter"}
    reader = PdfReader(str(pdf))
    box = reader.pages[0].mediabox
    fonts = set()
    for page in reader.pages:
        try:
            fonts |= set((page.get("/Resources") or {}).get("/Font", {}).keys())
        except Exception:
            continue
    return {
        "pdf_pages": len(reader.pages),
        "pdf_paper_pt": [round(float(box.width), 1), round(float(box.height), 1)],
        "pdf_fonts_n": len(fonts),
        "pdf_version": str(reader.pdf_header),
        "pdf_reason": None,
    }


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = spec_dict.get("metadata") or {}
    for field in ("title", "author", "language", "identifier", "date"):
        if not meta.get(field):
            raise spec_mod.SpecError(
                f"ebook metadata missing '{field}' — dc metadata and the pinned "
                f"identifier/determinism epoch are built from it")
    chapters = _resolve_chapters(spec_dict)
    formats = spec_dict.get("formats") or ["epub3"]
    registry.require("pandoc")

    artifacts = []
    epub = None
    if any(f.startswith("epub") for f in formats):
        epub = _render(spec_dict, chapters, out_dir, "epub3")
        _pin_zip_timestamps(epub)
        artifacts.append(epub)
    pdf = None
    if "pdf" in formats:
        registry.require("miktex")
        pdf = _render(spec_dict, chapters, out_dir, "pdf")
        artifacts.append(pdf)

    measured: dict = {}
    content_hash = ""
    if epub is not None:
        measured |= _measure_epub(epub)
        content_hash = measured.pop("content_hash")
        book = epub
    if pdf is not None:
        measured |= _measure_pdf(pdf)

    deterministic = True
    if epub is not None:            # re-render and compare normalised payloads
        again = _render(spec_dict, chapters, out_dir / "_det", "epub3")
        _pin_zip_timestamps(again)
        m2 = _measure_epub(again)
        deterministic = m2["content_hash"] == content_hash
        import shutil
        shutil.rmtree(out_dir / "_det", ignore_errors=True)
    measured["deterministic"] = deterministic

    report = validate.run_acceptance(spec_dict["acceptance"], measured)
    report["measured"] = measured
    report["formats"] = formats
    cli.write_report(out_dir, report)

    names = {}
    if epub is not None:
        names["book.epub"] = provenance.sha256_file(epub)
    if pdf is not None:
        names["book.pdf"] = provenance.sha256_file(pdf)
    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict,
        content_hash=content_hash or provenance.sha256_bytes(json.dumps(
            {k: v for k, v in measured.items()}, sort_keys=True).encode()),
        artifact_hashes=names,
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=[*names.keys(), "report.json", "manifest.json"],
        notes=[*(spec_dict.get("assumptions") or []),
               f"chapters: {[str(c) for c in chapters]}",
               f"SOURCE_DATE_EPOCH={_epoch_from_date(meta.get('date'))} pinned; "
               f"zip timestamps fixed; identifier {meta.get('identifier')}"],
        pipeline="vcac-ebook/0.1")
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    a = cli.parse_args("vcac ebook route (markdown → EPUB3/PDF)", argv)
    spec_dict = spec_mod.load_raw(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec_dict["id"]))
    m = r["report"]["measured"]
    return cli.finish("ebook", r, summaries=[
        f"{spec_dict['id']} -> {r['out_dir']}",
        f"spine={m.get('spine_count')} toc={m.get('toc_entries')} "
        f"lang={m.get('language')} cover={m.get('cover_present')} "
        f"missing_hrefs={len(m.get('missing_hrefs') or [])}"
        + (f" pages={m.get('pdf_pages')}" if m.get("pdf_pages") else "")])


if __name__ == "__main__":
    raise SystemExit(main())
