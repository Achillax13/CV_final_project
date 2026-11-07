"""Create an editable Word counterpart from the exact PDF report story."""
import sys
from html.parser import HTMLParser
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from reportlab.platypus import Paragraph, Table, Image, PageBreak, Spacer

from build_final_report import ROOT, build


OUTPUT = ROOT / 'output/word/group6_patchcore_final_report.docx'


def hyperlink(paragraph, label, url):
    rel = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    node = OxmlElement('w:hyperlink')
    node.set(qn('r:id'), rel)
    run = OxmlElement('w:r')
    props = OxmlElement('w:rPr')
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '0563C1')
    props.append(color)
    run.append(props)
    t = OxmlElement('w:t')
    t.text = label
    run.append(t)
    node.append(run)
    paragraph._p.append(node)


class Inline(HTMLParser):
    def __init__(self, paragraph):
        super().__init__()
        self.paragraph = paragraph
        self.bold = 0
        self.italic = 0
        self.link = None

    def handle_starttag(self, tag, attrs):
        if tag == 'b':
            self.bold += 1
        elif tag == 'i':
            self.italic += 1
        elif tag == 'link':
            self.link = dict(attrs).get('href')
        elif tag == 'br':
            self.paragraph.add_break()

    def handle_endtag(self, tag):
        if tag == 'b':
            self.bold = max(0, self.bold - 1)
        elif tag == 'i':
            self.italic = max(0, self.italic - 1)
        elif tag == 'link':
            self.link = None

    def handle_data(self, data):
        if self.link:
            hyperlink(self.paragraph, data, self.link)
        else:
            run = self.paragraph.add_run(data)
            run.bold = bool(self.bold)
            run.italic = bool(self.italic)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), fill)
    tc_pr.append(shd)


def set_cell_border(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    for side in ('top', 'left', 'bottom', 'right'):
        edge = OxmlElement('w:' + side)
        edge.set(qn('w:val'), 'single')
        edge.set(qn('w:sz'), '4')
        edge.set(qn('w:color'), 'D9D9D9')
        borders.append(edge)
    tc_pr.append(borders)


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11)
    sec.top_margin = Inches(.62)
    sec.bottom_margin = Inches(.65)
    sec.left_margin = Inches(.62)
    sec.right_margin = Inches(.62)

    styles = doc.styles
    for style_name in ('Normal', 'Title', 'Subtitle', 'Heading 1', 'Caption'):
        styles[style_name].font.name = 'Arial'
        styles[style_name].font.color.rgb = RGBColor(0, 0, 0)
    styles['Normal'].font.size = Pt(9)
    styles['Normal'].paragraph_format.space_after = Pt(7)
    styles['Title'].font.size = Pt(19)
    styles['Title'].font.bold = True
    styles['Title'].paragraph_format.space_after = Pt(7)
    styles['Subtitle'].font.size = Pt(10.5)
    styles['Subtitle'].paragraph_format.space_after = Pt(12)
    styles['Heading 1'].font.size = Pt(12)
    styles['Heading 1'].font.bold = True
    styles['Heading 1'].paragraph_format.space_before = Pt(10)
    styles['Heading 1'].paragraph_format.space_after = Pt(5)
    styles['Heading 1'].paragraph_format.keep_with_next = True
    styles['Caption'].font.size = Pt(7.5)
    styles['Caption'].paragraph_format.space_after = Pt(8)

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run('Group 6 | PatchCore small-defect localization | Windows RTX 5060')
    footer.runs[0].font.size = Pt(8)

    for item in build(return_story=True):
        if isinstance(item, Paragraph):
            kind = item.style.name
            style = {'ReportTitle': 'Title', 'Deck': 'Subtitle', 'SectionX': 'Heading 1',
                     'CaptionX': 'Caption', 'ReferenceX': 'Normal'}.get(kind, 'Normal')
            para = doc.add_paragraph(style=style)
            Inline(para).feed(item.text)
            if kind == 'ReferenceX':
                para.paragraph_format.left_indent = Inches(.24)
                para.paragraph_format.first_line_indent = Inches(-.24)
                for run in para.runs:
                    run.font.size = Pt(8)
        elif isinstance(item, Table):
            rows = item._cellvalues
            tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
            tbl.autofit = False
            widths = [w / 72 for w in item._colWidths]
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    cell = tbl.cell(i, j)
                    cell.width = Inches(widths[j])
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    cell.text = str(value)
                    set_cell_border(cell)
                    if i == 0:
                        set_cell_shading(cell, '17324D')
                    elif i % 2 == 0:
                        set_cell_shading(cell, 'EDF4F8')
                    for para in cell.paragraphs:
                        para.paragraph_format.space_after = Pt(0)
                        for run in para.runs:
                            run.font.size = Pt(7.5)
                            if i == 0:
                                run.bold = True
                                run.font.color.rgb = RGBColor(255, 255, 255)
            for row in tbl.rows:
                for j, cell in enumerate(row.cells):
                    cell.width = Inches(widths[j])
            tbl.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
        elif isinstance(item, Image):
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            width = 6.5 if 'defect_area_histograms' in str(item.filename) else min(item.drawWidth / 72, 7.2)
            para.add_run().add_picture(str(item.filename), width=Inches(width))
            para.paragraph_format.space_after = Pt(2)
        elif isinstance(item, PageBreak):
            doc.add_page_break()
        elif isinstance(item, Spacer):
            continue

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == '__main__':
    main()
