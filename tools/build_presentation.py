"""Generate an ODP deck with stdlib only; LibreOffice converts it to PPTX."""

from __future__ import annotations

import html
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation" / "health_expenditure_prototype.odp"

SLIDES = [
    ("From heterogeneous extracts to reviewable evidence", [
        "Regional health expenditure harmonisation prototype",
        "Technical assessment · September 2026",
        "A compact, auditable path from country financial extracts to analyst decisions",
    ]),
    ("Interpretation and design principles", [
        "Preserve source truth and make every transformation traceable.",
        "Separate country-specific ingestion from the common analytical model.",
        "Never hide uncertainty: auto-classify only defensible mappings.",
        "Keep currencies separate without governed exchange rates.",
        "Optimize the prototype for explanation, adaptation and analyst review.",
    ]),
    ("Architecture and data flow", [
        "CSV · XLSX · JSON",
        "↓  country adapters",
        "Harmonised record contract  →  validation and coded issues",
        "↓",
        "Account rules + cautious text fallback  →  SQLite",
        "↓",
        "FastAPI  →  analyst review UI  →  audited decisions",
        "Invalid amounts branch to a visible quarantine—not silent loss.",
    ]),
    ("Harmonised model and end-to-end lineage", [
        "One fact grain; Country C children replace parents when supplied.",
        "Original amount/currency, entity, account, description, supplier and period.",
        "Source file + SHA-256 + locator + source/parent IDs + preserved raw JSON.",
        "Separate quality issues, rejected records and classification history.",
        "Country-owned charts of accounts avoid false code equivalence.",
    ]),
    ("Country-specific differences stay at the edge", [
        "A · CSV · English · DD/MM/YYYY · KES · quoted amount anomalies",
        "B · XLSX · 7-row preamble · French · DD-MM-YYYY · XOF · CoA sheet",
        "C · JSON · nested splits · null descriptions · RWF and USD",
        "All adapters emit the same typed contract.",
        "New country = adapter + configuration + references + contract tests.",
    ]),
    ("Classification with a safe failure mode", [
        "Exact country/account rules are primary, transparent and configurable.",
        "Normalized-text matching is a lower-confidence fallback only.",
        "SHA and SRHR are independent labels with method, rationale and confidence.",
        "≥ 85% confidence auto-classifies; everything else enters review.",
        "Unknown ≠ zero: unsupported assignments remain unmapped.",
    ]),
    ("Profiling found material, manageable uncertainty", [
        "7,094 usable facts · 31 blank-amount records quarantined",
        "54 negatives retained as possible reversals · 13 amount formats normalized",
        "216 stored Country C facts in USD · no silent FX conversion",
        "26 missing descriptions · 2 duplicate-ID rows · 1 missing date",
        "5,176 explicit-rule facts · 1,918 unmapped · 2,886 in review queue",
    ]),
    ("Analyst workflow", [
        "1  Review currency-specific totals and queue size.",
        "2  Search or filter by country, SHA, SRHR and review status.",
        "3  Inspect rationale, issues, raw source, locator and checksum.",
        "4  Confirm or override using controlled reference codes.",
        "5  Retain analyst, time, before/after values and decision note.",
    ]),
    ("Technology choices and honest trade-offs", [
        "Python · clear adapters and a strong future data ecosystem",
        "SQLite · zero-operations demo, integrity, portable relational model",
        "FastAPI · typed, documented API; plain JS keeps the UI light",
        "Standard-library XLSX reader · bounded scope, no Excel dependency",
        "Trade-off · batch rebuild and single-user store are prototype choices.",
    ]),
    ("Production path and engagement model", [
        "Govern mappings: versions, effective dates, dual approval and gold-set evaluation.",
        "PostgreSQL + immutable landing + orchestration + reconciliation controls.",
        "RBAC/SSO, encryption, privacy review, observability, backup and DR.",
        "Reconcile extracts with country teams before interpreting classifications.",
        "Iterate with SHA/SRHR experts: review → validate → measure → improve.",
    ]),
]


def text_frame(x: float, y: float, w: float, h: float, style: str, paragraphs: list[str]) -> str:
    content = "".join(f'<text:p text:style-name="{style}">{html.escape(p)}</text:p>' for p in paragraphs)
    return (f'<draw:frame draw:style-name="fr" svg:x="{x}cm" svg:y="{y}cm" '
            f'svg:width="{w}cm" svg:height="{h}cm"><draw:text-box>{content}</draw:text-box></draw:frame>')


def content_xml() -> str:
    pages = []
    for index, (title, lines) in enumerate(SLIDES, 1):
        body_style = "Subtitle" if index == 1 else "Body"
        body_lines = lines if index == 1 else [f"•  {line}" for line in lines]
        page = [f'<draw:page draw:name="Slide {index}" draw:style-name="page" draw:master-page-name="Default">']
        page.append('<draw:rect draw:style-name="accent" svg:x="0cm" svg:y="0cm" svg:width="0.32cm" svg:height="19.05cm"/>')
        page.append(text_frame(1.35, 1.15, 30.0, 2.1, "Title", [title]))
        page.append(text_frame(1.45, 4.05 if index == 1 else 4.0, 29.0, 12.5, body_style, body_lines))
        page.append(text_frame(1.45, 18.1, 20.0, .5, "Footer", ["REGIONAL HEALTH EXPENDITURE PROTOTYPE"]))
        page.append(text_frame(30.4, 18.1, 1.0, .5, "Footer", [str(index)]))
        page.append('</draw:page>')
        pages.append("".join(page))
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" office:version="1.3">
<office:automatic-styles>
<style:style style:name="page" style:family="drawing-page"><style:drawing-page-properties draw:fill="solid" draw:fill-color="#F5F7F5"/></style:style>
<style:style style:name="fr" style:family="graphic"><style:graphic-properties draw:fill="none" draw:stroke="none" draw:auto-grow-height="false" fo:padding="0cm"/></style:style>
<style:style style:name="accent" style:family="graphic"><style:graphic-properties draw:fill="solid" draw:fill-color="#087F73" draw:stroke="none"/></style:style>
<style:style style:name="Title" style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0cm"/><style:text-properties fo:font-family="Liberation Sans" fo:font-size="26pt" fo:font-weight="bold" fo:color="#102F3B"/></style:style>
<style:style style:name="Subtitle" style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0.45cm"/><style:text-properties fo:font-family="Liberation Sans" fo:font-size="20pt" fo:color="#315C67"/></style:style>
<style:style style:name="Body" style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0.48cm"/><style:text-properties fo:font-family="Liberation Sans" fo:font-size="17pt" fo:color="#23384A"/></style:style>
<style:style style:name="Footer" style:family="paragraph"><style:text-properties fo:font-family="Liberation Sans" fo:font-size="8pt" fo:font-weight="bold" fo:color="#617087"/></style:style>
</office:automatic-styles><office:body><office:presentation>{''.join(pages)}</office:presentation></office:body></office:document-content>'''


STYLES = '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" office:version="1.3"><office:styles/><office:automatic-styles><style:page-layout style:name="screen"><style:page-layout-properties fo:page-width="33.867cm" fo:page-height="19.05cm" style:print-orientation="landscape"/></style:page-layout></office:automatic-styles><office:master-styles><style:master-page style:name="Default" style:page-layout-name="screen" draw:style-name="standard"/></office:master-styles></office:document-styles>'''

MANIFEST = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.presentation"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/></manifest:manifest>'''

META = '''<?xml version="1.0" encoding="UTF-8"?><office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:dc="http://purl.org/dc/elements/1.1/" office:version="1.3"><office:meta><dc:title>Health Expenditure Harmonisation Prototype</dc:title><dc:creator>Assessment candidate</dc:creator></office:meta></office:document-meta>'''


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUT, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.presentation", compress_type=ZIP_STORED)
        archive.writestr("content.xml", content_xml(), compress_type=ZIP_DEFLATED)
        archive.writestr("styles.xml", STYLES, compress_type=ZIP_DEFLATED)
        archive.writestr("meta.xml", META, compress_type=ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", MANIFEST, compress_type=ZIP_DEFLATED)
    print(OUT)


if __name__ == "__main__":
    main()
