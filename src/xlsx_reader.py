"""Small, dependency-free XLSX reader for the tabular assessment input.

It intentionally supports only the OOXML features used by this prototype's input:
shared/inline strings, numbers, booleans and ISO/date-formatted values.
"""

from __future__ import annotations

import posixpath
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET
from zipfile import ZipFile

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": MAIN, "r": REL}


def _column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref).group(0)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def _excel_date(value: str) -> str:
    return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()


def read_workbook(path: Path) -> dict[str, list[list[str]]]:
    with ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.findall(".//m:t", NS))
                for item in root.findall("m:si", NS)
            ]

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {node.attrib["Id"]: node.attrib["Target"] for node in rels}
        result: dict[str, list[list[str]]] = {}

        for sheet in workbook.findall(".//m:sheet", NS):
            target = targets[sheet.attrib[f"{{{REL}}}id"]].lstrip("/")
            target = target if target.startswith("xl/") else posixpath.join("xl", target)
            root = ET.fromstring(archive.read(posixpath.normpath(target)))
            rows: list[list[str]] = []
            for row in root.findall(".//m:sheetData/m:row", NS):
                values: list[str] = []
                for cell in row.findall("m:c", NS):
                    index = _column_index(cell.attrib["r"])
                    while len(values) <= index:
                        values.append("")
                    value_node = cell.find("m:v", NS)
                    value = "" if value_node is None else (value_node.text or "")
                    kind = cell.attrib.get("t")
                    if kind == "s" and value:
                        value = shared[int(value)]
                    elif kind == "inlineStr":
                        value = "".join(n.text or "" for n in cell.findall(".//m:t", NS))
                    values[index] = value
                rows.append(values)
            result[sheet.attrib["name"]] = rows
        return result


def table_records(rows: list[list[str]], header_row: int) -> Iterator[dict[str, str]]:
    headers = rows[header_row]
    for row in rows[header_row + 1 :]:
        padded = row + [""] * (len(headers) - len(row))
        if any(value.strip() for value in padded):
            yield dict(zip(headers, padded))
