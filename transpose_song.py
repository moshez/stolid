"""Transpose an Ultimate-Guitar chord/lyric PDF into a new key.

Every word of lyric and every chord symbol is taken verbatim from the
source PDF via positional text extraction (``pdfplumber``).  Nothing is
reproduced from memory: the script only *moves* and *re-spells* the chord
symbols it reads out of the file, and copies the lyric characters through
untouched.  The result is rendered to a fresh PDF with ``reportlab``.

Usage::

    python transpose_song.py INPUT.pdf OUTPUT.pdf [--to-key A] [--from-key D]

``--from-key`` defaults to whatever the source PDF declares on its
``Key:`` line.
"""

from __future__ import annotations

import argparse
import re
import statistics
from dataclasses import dataclass

import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# --- music theory -----------------------------------------------------------

SHARP_NAMES = [
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
]
PITCH = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
    "B#": 0,
}

CHORD_RE = re.compile(
    r"^(?P<root>[A-G][#b]?)"
    r"(?P<qual>(?:m|maj|min|dim|aug|sus|add|M)?\d*(?:sus\d|add\d|[#b]\d)*)"
    r"(?:/(?P<bass>[A-G][#b]?))?$"
)


def transpose_note(note: str, semitones: int) -> str:
    """Move a single note name up by ``semitones``, spelled with sharps."""
    return SHARP_NAMES[(PITCH[note] + semitones) % 12]


def transpose_chord(token: str, semitones: int) -> str:
    """Transpose one chord token, preserving quality and bass note."""
    if token == "|":
        return "|"
    match = CHORD_RE.match(token)
    if match is None:  # pragma: no cover - guarded by is_chord_token
        return token
    root = transpose_note(match["root"], semitones)
    chord = root + match["qual"]
    if match["bass"]:
        chord += "/" + transpose_note(match["bass"], semitones)
    return chord


def is_chord_token(token: str) -> bool:
    return token == "|" or CHORD_RE.match(token) is not None


def is_chord_row(tokens: list[str]) -> bool:
    """A row of nothing but chords (and bar lines), with >=1 real chord."""
    if not tokens:
        return False
    if not all(is_chord_token(tok) for tok in tokens):
        return False
    return any(tok != "|" for tok in tokens)


# --- PDF text extraction ----------------------------------------------------


@dataclass(frozen=True)
class Row:
    """One visual line: tokens placed at monospace character columns."""

    cells: tuple[tuple[int, str], ...]  # (column, text), sorted by column

    @property
    def text(self) -> str:
        return " ".join(text for _, text in self.cells)

    @property
    def tokens(self) -> list[str]:
        return [text for _, text in self.cells]

    def render(self, transform=lambda text: text) -> str:
        """Lay the (possibly transformed) cells out on a blank line."""
        line = ""
        for column, text in self.cells:
            text = transform(text)
            if len(line) > column:
                line += " " + text
            else:
                line += " " * (column - len(line)) + text
        return line.rstrip()


SECTION_RE = re.compile(r"^\[.+\]$")


def extract_rows(path: str) -> tuple[list[Row], float]:
    """Return the song's rows plus the original key parsed from the PDF.

    Rows are clustered from positioned words; columns are derived from the
    monospace character width measured on the page itself.
    """
    words = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_words = page.extract_words()
            for word in page_words:
                words.append(
                    (
                        page.page_number,
                        word["top"],
                        word["x0"],
                        word["x1"],
                        word["text"],
                    )
                )

    raw_rows = _cluster_rows(words)
    from_key = _find_key(raw_rows)
    body = _select_body(raw_rows)
    base_x, char_width = _column_metrics(body)
    rows = [
        Row(
            cells=tuple(
                sorted((round((x0 - base_x) / char_width), text) for x0, text in cells)
            )
        )
        for cells in body
    ]
    return rows, from_key


def _cluster_rows(words):
    """Group positioned words into visual lines, keeping page order."""
    words = sorted(words, key=lambda w: (w[0], w[1], w[2]))
    rows = []
    current = []
    current_key = None
    for page, top, x0, x1, text in words:
        key = (page, top)
        if (
            current_key is None
            or page != current_key[0]
            or abs(top - current_key[1]) > 4
        ):
            if current:
                rows.append(current)
            current = []
            current_key = key
        current.append((x0, x1, text))
    if current:
        rows.append(current)
    return rows


def _row_text(cells) -> str:
    return " ".join(text for _, _, text in sorted(cells))


def _find_key(raw_rows) -> float:
    for cells in raw_rows:
        text = _row_text(cells)
        match = re.match(r"^Key:\s*([A-G][#b]?)", text)
        if match:
            return PITCH[match.group(1)]
    return PITCH["C"]  # pragma: no cover - source always declares a key


def _select_body(raw_rows):
    """Trim chrome: keep from the first section header to before notes."""
    start = next(
        i for i, cells in enumerate(raw_rows) if SECTION_RE.match(_row_text(cells))
    )
    body = []
    for cells in raw_rows[start:]:
        text = _row_text(cells)
        if text == "Author notes:":
            break
        if text == "ADVERTISEMENT":
            continue
        body.append([(x0, text) for x0, _, text in sorted(cells)])
    return body


def _column_metrics(body):
    base_x = min(x0 for cells in body for x0, _ in cells)
    widths = []
    # The source is monospace, so the gap between two adjacent token
    # starts divided by the leading token's length (plus its trailing
    # space) recovers the per-character cell width.
    for cells in body:
        ordered = sorted(cells)
        for (x0a, ta), (x0b, _) in zip(ordered, ordered[1:]):
            widths.append((x0b - x0a) / (len(ta) + 1))
    char_width = statistics.median(widths)
    return base_x, char_width


# --- rendering --------------------------------------------------------------


@dataclass(frozen=True)
class Line:
    style: str  # "header" | "chord" | "lyric"
    text: str


def build_lines(rows: list[Row], semitones: int) -> list[Line]:
    """Interleave transposed chord rows above the lyric rows they sit on."""
    lines: list[Line] = []
    pending: Row | None = None

    def flush() -> None:
        nonlocal pending
        if pending is not None:
            lines.append(
                Line(
                    "chord", pending.render(lambda tok: transpose_chord(tok, semitones))
                )
            )
            pending = None

    for row in rows:
        if SECTION_RE.match(row.text):
            flush()
            lines.append(Line("header", row.text))
        elif is_chord_row(row.tokens):
            flush()
            pending = row
        else:
            if pending is not None:
                lines.append(
                    Line(
                        "chord",
                        pending.render(lambda tok: transpose_chord(tok, semitones)),
                    )
                )
                pending = None
            lines.append(Line("lyric", row.render()))
    flush()
    return lines


def render_pdf(lines: list[Line], title: str, out_path: str) -> None:
    width, height = letter
    margin = 0.75 * inch
    pdf = canvas.Canvas(out_path, pagesize=letter)
    pdf.setTitle(title)
    leading = 12.0
    y = height - margin

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, title)
    y -= 26

    for line in lines:
        gap = leading
        if line.style == "header":
            gap = leading + 8
        if y - gap < margin:
            pdf.showPage()
            y = height - margin
        y -= gap
        if line.style == "header":
            pdf.setFont("Helvetica-Bold", 12)
        elif line.style == "chord":
            pdf.setFont("Courier-Bold", 10)
        else:
            pdf.setFont("Courier", 10)
        pdf.drawString(margin, y, line.text)
    pdf.save()


def _title(rows_path: str, to_key: str) -> str:
    with pdfplumber.open(rows_path) as pdf:
        text = pdf.pages[0].extract_text()
    headline = next(
        (line for line in text.splitlines() if " Chords by " in line),
        text.splitlines()[0],
    )
    headline = headline.replace(" Chords by ", " - ")
    return f"{headline}  (Key of {to_key})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="source chord/lyric PDF")
    parser.add_argument("output", help="destination PDF")
    parser.add_argument("--to-key", default="A", help="target key (default: A)")
    parser.add_argument(
        "--from-key",
        default=None,
        help="source key (default: read from the PDF's 'Key:' line)",
    )
    args = parser.parse_args()

    rows, pdf_from_pitch = extract_rows(args.input)
    from_pitch = PITCH[args.from_key] if args.from_key else pdf_from_pitch
    semitones = (PITCH[args.to_key] - from_pitch) % 12

    lines = build_lines(rows, semitones)
    render_pdf(lines, _title(args.input, args.to_key), args.output)


if __name__ == "__main__":
    main()
