"""Minimal single-page PDF writer (stdlib only) for DMS invoices."""

from __future__ import annotations

from pathlib import Path


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def write_simple_pdf(path: Path | str, lines: list[str], *, title: str = "Invoice") -> Path:
    """Write a basic Helvetica text PDF. No external deps."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # PDF content stream: start near top, 12pt leading
    y = 760
    content_ops = ["BT", "/F1 11 Tf", "50 760 Td", "14 TL"]
    first = True
    for raw in lines:
        line = _escape(str(raw)[:110])
        if first:
            content_ops.append(f"({line}) Tj")
            first = False
        else:
            content_ops.append("T*")
            content_ops.append(f"({line}) Tj")
        y -= 14
        if y < 72:
            break
    content_ops.append("ET")
    stream = "\n".join(content_ops).encode("latin-1", errors="replace")

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    add(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    add(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Assemble
    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf.extend(f"{i} 0 obj\n".encode())
        buf.extend(obj)
        buf.extend(b"\nendobj\n")
    xref_pos = len(buf)
    buf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    buf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.extend(f"{off:010d} 00000 n \n".encode())
    buf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info << /Title ({_escape(title)}) >> >>\n".encode()
    )
    buf.extend(f"startxref\n{xref_pos}\n%%EOF\n".encode())
    out.write_bytes(bytes(buf))
    return out
