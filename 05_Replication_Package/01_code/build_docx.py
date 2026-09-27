# -*- coding: utf-8 -*-
"""Build the submittable .docx from the manuscript Markdown source.

Renders inline bold/italic/code markup, sub- and super-scripts (_{...}, ^{...}),
display equations (indented blocks), real Word tables with booktabs-style rules
and merged multi-row headers, numbered lists, figures with captions, continuous
line numbers, page numbers, and hyperlinked URLs.

Usage:  python build_docx.py [source.md] [output.docx]
Defaults are resolved relative to this script's location.
"""
import os, re, sys
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '01_Manuscript', 'Manuscript_EMSE_Submission_Ready.md')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, '01_Manuscript', 'Manuscript_EMSE_Submission_Ready.docx')
FIGDIR = os.path.join(ROOT, '02_Figures')

SERIF, MONO, EASIA = 'Times New Roman', 'Consolas', '宋体'

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)   # A4
sec.left_margin = sec.right_margin = Inches(1)
sec.top_margin = sec.bottom_margin = Inches(1)

st = doc.styles['Normal']
st.font.name = SERIF
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn('w:eastAsia'), EASIA)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15
st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# continuous line numbering (for review)
ln = OxmlElement('w:lnNumType')
ln.set(qn('w:countBy'), '1')
ln.set(qn('w:restart'), 'continuous')
ln.set(qn('w:distance'), '360')
sec._sectPr.append(ln)

def set_font(run, name=SERIF, size=None, bold=None, italic=None):
    run.font.name = name
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if italic is not None: run.italic = italic
    run._element.rPr.rFonts.set(qn('w:eastAsia'), EASIA)

# ---- footer page number ---------------------------------------------------
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run()
for el, attrs, txt in [('w:fldChar', {'w:fldCharType': 'begin'}, None),
                       ('w:instrText', {'xml:space': 'preserve'}, 'PAGE'),
                       ('w:fldChar', {'w:fldCharType': 'end'}, None)]:
    e = OxmlElement(el)
    for k, v in attrs.items(): e.set(qn(k), v)
    if txt: e.text = txt
    r._r.append(e)
set_font(r, size=9)

# ---- inline markup --------------------------------------------------------
TOKEN = re.compile(r'(\*\*.+?\*\*|`[^`]+`|\*[^*]+?\*|_\{[^}]*\}|\^\{[^}]*\}|https?://\S+)')

def add_sub_sup(p, text, size=None, bold=False, italic=False, sub=True):
    # subscript/superscript content may itself carry *italic* markup
    for part in re.split(r'(\*[^*]+?\*)', text):
        if not part:
            continue
        if part.startswith('*') and part.endswith('*') and len(part) >= 2:
            rr = p.add_run(part[1:-1]); set_font(rr, size=size, bold=bold, italic=True)
        else:
            rr = p.add_run(part); set_font(rr, size=size, bold=bold, italic=italic)
        rr.font.subscript = sub
        rr.font.superscript = not sub

def add_rich(p, text, size=None, bold=False, italic=False):
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**') and len(part) >= 4:
            set_font(p.add_run(part[2:-2]), size=size, bold=True, italic=italic)
        elif part.startswith('`') and part.endswith('`') and len(part) >= 2:
            set_font(p.add_run(part[1:-1]), name=MONO, size=(size or 11) - 1.5, bold=bold, italic=italic)
        elif part.startswith('*') and part.endswith('*') and not part.startswith('**') and len(part) >= 2:
            set_font(p.add_run(part[1:-1]), size=size, italic=True, bold=bold)
        elif part.startswith('_{') and part.endswith('}'):
            add_sub_sup(p, part[2:-1], size=size, bold=bold, italic=italic, sub=True)
        elif part.startswith('^{') and part.endswith('}'):
            add_sub_sup(p, part[2:-1], size=size, bold=bold, italic=italic, sub=False)
        elif part.startswith('http'):
            rr = p.add_run(part); set_font(rr, size=size, bold=bold, italic=italic)
            rid = doc.part.relate_to(part, RT.HYPERLINK, is_external=True)
            h = OxmlElement('w:hyperlink'); h.set(qn('r:id'), rid)
            rr._r.getparent().remove(rr._r)
            c = OxmlElement('w:color'); c.set(qn('w:val'), '0563C1')
            rr._element.get_or_add_rPr().append(c)
            h.append(rr._r); p._p.append(h)
        else:
            set_font(p.add_run(part), size=size, bold=bold, italic=italic)

# ---- structural helpers ----------------------------------------------------
def heading(text, level):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_font(r, size=13 if level == 1 else 11.5, bold=True)
    if level == 1:
        r.font.color.rgb = RGBColor(0x1F, 0x3B, 0x63)

def body(text):
    p = doc.add_paragraph()
    p.paragraph_format.keep_together = True
    add_rich(p, text)

def caption(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    add_rich(p, text, size=9.5, italic=True)

def figure_note(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    add_rich(p, text, size=9.5, italic=True)

def table_note(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    add_rich(p, text, size=8.5)

def display_equation(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    add_rich(p, text, size=11.5)

def add_figure(fn):
    doc.add_picture(os.path.join(FIGDIR, fn), width=Inches(6.27))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

def set_cell_border(cell, edge, sz):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn('w:tcBorders'))
    if borders is None:
        borders = OxmlElement('w:tcBorders'); tcPr.append(borders)
    el = borders.find(qn('w:' + edge))
    if el is None:
        el = OxmlElement('w:' + edge); borders.append(el)
    el.set(qn('w:val'), 'single'); el.set(qn('w:sz'), str(sz)); el.set(qn('w:color'), '000000')

def split_row(line):
    """Split a space-aligned row into ordered cell values."""
    return [part.strip() for part in re.split(r'\s{2,}', line.strip()) if part.strip()]

def build_table(groups):
    hdr_lines = groups[0]
    ncols = len(split_row(hdr_lines[-1]))
    if not ncols:
        raise ValueError('table has an empty header')

    # A header row either names every column or uses equally sized group spans.
    headers = []
    for ln in hdr_lines:
        values = split_row(ln)
        if len(values) == ncols:
            headers.append((values, 1))
        elif values and ncols % len(values) == 0:
            headers.append((values, ncols // len(values)))
        else:
            raise ValueError(f'header has {len(values)} cells; expected {ncols}: {ln!r}')

    # Preserve order and reject malformed data rows instead of guessing cells.
    data, notes = [], []
    for group in groups[1:]:
        for ln in group:
            values = split_row(ln)
            if not values:
                continue
            if len(values) == 1 and not ln.startswith(' '):
                notes.append(values[0])
                continue
            if len(values) != ncols:
                raise ValueError(f'data row has {len(values)} cells; expected {ncols}: {ln!r}')
            data.append(values)

    tbl = doc.add_table(rows=0, cols=ncols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False

    # Keep the table within the A4 text width. Long labels receive more room;
    # numeric columns stay compact and wrap only when needed.
    def display_width(value):
        return len(re.sub(r'[*_`{}]', '', value))

    weights = []
    for i in range(ncols):
        candidates = [display_width(row[i]) for row in data]
        candidates.extend(display_width(row[i]) for row, span in headers if span == 1)
        weights.append(max(5, min(34, max(candidates or [8]))))
    table_width_twips = Inches(6.27).twips
    weight_sum = sum(weights)
    col_widths = [int(table_width_twips * weight / weight_sum) for weight in weights]
    col_widths[-1] += table_width_twips - sum(col_widths)
    for col, width_twips in zip(tbl.columns, col_widths):
        col.width = Pt(width_twips / 20)

    for values, span in headers:
        row = tbl.add_row()
        for j, value in enumerate(values):
            i = j * span
            cell = row.cells[i]
            if span > 1:
                cell = cell.merge(row.cells[i + span - 1])
                cell.width = Inches(sum(col_widths[i:i + span]) / 1440)
            else:
                cell.width = Pt(col_widths[i] / 20)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_rich(p, value, size=8.5, bold=True)

    numeric_pattern = r'[+\-−–—<>≥≤=0-9.,%:/()\[\] χφε*^_{}×x]+'
    for values in data:
        row = tbl.add_row()
        for i, value in enumerate(values):
            cell = row.cells[i]
            cell.width = Pt(col_widths[i] / 20)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            if i > 0 and re.fullmatch(numeric_pattern, value) and re.search(r'\d', value):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_rich(p, value, size=8.5)

    # Repeat headers and prevent individual rows from splitting across pages.
    for ri, row in enumerate(tbl.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:cantSplit'))
        if ri < len(headers):
            repeat = OxmlElement('w:tblHeader')
            repeat.set(qn('w:val'), 'true')
            trPr.append(repeat)

    # Booktabs-style horizontal rules; no vertical grid lines.
    for cell in tbl.rows[0].cells:
        set_cell_border(cell, 'top', 12)
    for cell in tbl.rows[len(headers) - 1].cells:
        set_cell_border(cell, 'bottom', 6)
    for cell in tbl.rows[-1].cells:
        set_cell_border(cell, 'bottom', 12)
    for nt in notes:
        table_note(nt)

# ---- main parse loop -------------------------------------------------------
raw = open(SRC, encoding='utf-8').read()
lines = raw.split('\n')
i, n = 0, len(lines)

def is_sep(ln):
    s = ln.strip()
    return bool(s) and set(s) <= set('-=')

def para_until_blank(i):
    out = []
    while i < n and lines[i].strip() and not is_sep(lines[i]) and not lines[i].startswith('    '):
        out.append(lines[i].strip())
        i += 1
    return ' '.join(out), i

# title: leading non-blank lines until 'Abstract'
title_lines = []
while i < n and lines[i].strip() != 'Abstract':
    if lines[i].strip() and not is_sep(lines[i]):
        title_lines.append(lines[i].strip())
    i += 1

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(10)
r = p.add_run('\n'.join(title_lines)); set_font(r, size=16, bold=True)
for txt, sz in [('Liufeng Zhang^{a,*}, Ke Zhuang^{a}', 11),
                ('^{a} College of Science and Technology, Ningbo University, Ningbo 315300, Zhejiang Province, China', 10),
                ('*Corresponding author: zhangliufeng@nbu.edu.cn', 10)]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_rich(p, txt, size=sz)

stats = {'headings': 0, 'tables': 0, 'figures': 0, 'paras': 0}

while i < n:
    line = lines[i]
    s = line.strip()

    if not s or is_sep(line):
        i += 1; continue

    if s.startswith('[FIGURE:'):
        add_figure(s[len('[FIGURE:'):-1].strip())
        stats['figures'] += 1
        i += 1
        if i < n and re.match(r'^Figure \d+\.', lines[i].strip()):
            cap, i = para_until_blank(i)
            figure_note(cap)
        continue

    # a real table caption is followed by a separator line
    if re.match(r'^Table \d+\.', s) and i + 1 < n and is_sep(lines[i + 1]):
        cap, i = para_until_blank(i)
        caption(cap)
        if re.match(r'^Table 18\.', cap):
            doc.paragraphs[-1].paragraph_format.page_break_before = True
        groups, cur = [], []
        while i < n and lines[i].strip():
            ln = lines[i]
            if is_sep(ln):
                if cur: groups.append(cur); cur = []
                i += 1; continue
            if re.match(r'^(Table|Figure) \d+\.', ln.strip()) and not ln.startswith(' '):
                break
            cur.append(ln.rstrip()); i += 1
        if cur: groups.append(cur)
        if groups:
            build_table(groups)
            stats['tables'] += 1
        continue

    if s in ('Abstract', 'References') or s.startswith('Appendix '):
        heading(s, 1); stats['headings'] += 1; i += 1; continue

    if s in ('Acknowledgments', 'Statements and Declarations'):
        heading(s, 1); stats['headings'] += 1; i += 1; continue

    if s in ('Competing interests', 'Funding', 'Data and code availability'):
        heading(s, 2); stats['headings'] += 1; i += 1; continue

    if re.match(r'^\d+\.\d+\s+[A-Z]', s) and len(s) < 90 and not s.rstrip().endswith(('.', ',', ';')):
        heading(s, 2); stats['headings'] += 1; i += 1; continue

    if re.match(r'^\d+\s+[A-Z]', s) and len(s) < 90 and not s.rstrip().endswith(('.', ',', ';')):
        heading(s, 1); stats['headings'] += 1; i += 1; continue

    if line.startswith('    '):
        eq = []
        while i < n and lines[i].startswith('    '):
            eq.append(lines[i].strip()); i += 1
        display_equation(' '.join(eq))
        continue

    if re.match(r'^\d+\.\s', s):
        item, i = para_until_blank(i)
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.32)
        p.paragraph_format.first_line_indent = Inches(-0.32)
        add_rich(p, item)
        stats['paras'] += 1
        continue

    txt, i = para_until_blank(i)
    if txt.startswith('Keywords:'):
        p = doc.add_paragraph()
        add_rich(p, txt)
        if p.runs: p.runs[0].bold = True
    else:
        body(txt)
    stats['paras'] += 1

doc.core_properties.title = 'Two Scales of Failure Dependence in LLM Agent Trajectories'
doc.core_properties.subject = 'Empirical Software Engineering special issue submission'
doc.core_properties.author = 'Liufeng Zhang, Ke Zhuang'
doc.core_properties.comments = 'Built from ' + os.path.basename(SRC)

doc.save(OUT)
print('saved:', OUT)
print('stats:', stats, '| tables:', len(doc.tables), 'images:', len(doc.inline_shapes))
