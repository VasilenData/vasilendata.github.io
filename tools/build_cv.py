"""Build two readable A4 CVs with a Jake's Resume-inspired layout.

python tools/build_cv.py --font-dir C:/Windows/Fonts
Requires reportlab and pypdf. See TEMPLATE_NOTICE.txt for layout attribution.
"""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = colors.HexColor('#20272C')
MUTED = colors.HexColor('#52616B')
ACCENT = colors.HexColor('#245348')
RULE = colors.HexColor('#B4BEC0')
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 44
WIDTH = PAGE_WIDTH - 2 * MARGIN


def register_fonts(directory):
    if directory:
        for filenames in [('calibri.ttf', 'calibrib.ttf', 'calibrii.ttf')]:
            paths = [directory / name for name in filenames]
            if all(path.exists() for path in paths):
                for name, path in zip(('CVSans', 'CVSans-Bold', 'CVSans-Italic'), paths):
                    pdfmetrics.registerFont(TTFont(name, str(path)))
                pdfmetrics.registerFontFamily('CVSans', normal='CVSans', bold='CVSans-Bold', italic='CVSans-Italic', boldItalic='CVSans-Bold')
                return 'CVSans', 'CVSans-Bold', 'CVSans-Italic'
    raise FileNotFoundError('Pass --font-dir with licensed Calibri regular, bold and italic TTF files. The published one-page layout is validated with Calibri.')


class Section(Flowable):
    def __init__(self, title, font):
        super().__init__()
        self.title, self.font = title.upper(), font
        self.width, self.height = WIDTH, 30
        self.keepWithNext = True

    def draw(self):
        text = self.canv.beginText(0, 12)
        text.setFont(self.font, 10.4)
        text.setFillColor(ACCENT)
        text.setCharSpace(1.15)
        text.textOut(self.title)
        self.canv.drawText(text)
        self.canv.setStrokeColor(RULE)
        self.canv.setLineWidth(0.5)
        self.canv.line(0, 6, self.width, 6)


def project_text(data, variant, project_key):
    """Use optional role-specific copy, falling back to shared project text."""
    text = variant.get('project_texts', {}).get(project_key, data['projects'][project_key]['text'])
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f'{project_key}: project text must be a non-empty string')
    return text


def build(source, output_dir, font_dir=None):
    data = json.loads(source.read_text(encoding='utf-8'))
    regular, bold, italic = register_fonts(font_dir)
    base = ParagraphStyle('base', fontName=regular, fontSize=10.7,
                          leading=12.9, textColor=INK, alignment=TA_LEFT)
    styles = {
        'body': base,
        'name': ParagraphStyle('name', parent=base, fontName=bold, fontSize=28,
                               leading=31, alignment=TA_CENTER, spaceAfter=2),
        'headline': ParagraphStyle('headline', parent=base, fontName=bold, fontSize=11.3,
                                   leading=14, textColor=ACCENT, alignment=TA_CENTER, spaceAfter=5),
        'contact': ParagraphStyle('contact', parent=base, fontSize=9.5, leading=12,
                                  textColor=MUTED, alignment=TA_CENTER, spaceAfter=2),
        'summary': ParagraphStyle('summary', parent=base, fontSize=10.7, leading=13.2),
        'company': ParagraphStyle('company', parent=base, fontName=bold, fontSize=11.2,
                                  leading=14, spaceAfter=1),
        'role': ParagraphStyle('role', parent=base, fontSize=10.1, leading=12.5),
        'date': ParagraphStyle('date', parent=base, fontSize=9.8, leading=12.5,
                               textColor=MUTED, alignment=TA_RIGHT),
        'project': ParagraphStyle('project', parent=base, fontName=bold, fontSize=11,
                                  leading=14),
        'stack': ParagraphStyle('stack', parent=base, fontSize=9.2, leading=12,
                                textColor=MUTED, alignment=TA_RIGHT),
        'bullet': ParagraphStyle('bullet', parent=base, leftIndent=10, firstLineIndent=0,
                                 bulletIndent=0, bulletFontName=regular,
                                 bulletFontSize=7.2, spaceBefore=3),
        'skills': ParagraphStyle('skills', parent=base, fontSize=10.1, leading=12.5),
        'education': ParagraphStyle('education', parent=base, fontSize=10.1, leading=12.5),
    }

    def p(text, style='body', raw=False):
        return Paragraph(text if raw else escape(text), styles[style])

    def pair(left, right, left_style='role', right_style='date', right_width=151):
        row = Table([[p(left, left_style, True), p(right, right_style)]],
                    colWidths=[WIDTH-right_width, right_width], hAlign='LEFT')
        row.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                ('TOPPADDING', (0, 0), (-1, -1), 0),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
        return row

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for key, variant in data['variants'].items():
        selected = variant['projects']
        if len(selected) != 3 or len(set(selected)) != 3:
            raise ValueError('Each CV must feature three distinct projects')
        if not isinstance(variant.get('project_texts', {}), dict):
            raise ValueError('project_texts must map selected project keys to copy')
        if set(variant.get('project_texts', {})) - set(selected):
            raise ValueError('project_texts contains an unselected project')
        selected_copy = {project_key: project_text(data, variant, project_key)
                         for project_key in selected}
        story = [p(data['name'], 'name'), p(variant['headline'], 'headline'),
                 p(data['contact'], 'contact')]
        contacts = [(data['email'], 'mailto:' + data['email']), *data['links']]
        story.append(p(' &nbsp; | &nbsp; '.join(
            f'<a href="{escape(url)}" color="#20272C">{escape(label)}</a>'
            for label, url in contacts), 'contact', True))
        story.extend([Spacer(1, 8), p(variant['summary'], 'summary'), Spacer(1, 3)])

        story.append(Section('Professional experience', bold))
        for idx, job in enumerate(data['experience']):
            block = []
            if idx:
                block.append(Spacer(1, 8))
            block.append(p(job['company'], 'company'))
            if 'roles' in job:
                for role in job['roles']:
                    block.append(pair(escape(role['title']), role['dates']))
            else:
                block.append(pair(escape(job['title']), job['dates']))
            for bullet in job['bullets']:
                block.append(Paragraph(escape(bullet), styles['bullet'], bulletText='\u2022'))
            story.append(KeepTogether(block))

        story.append(Section('Selected projects', bold))
        for idx, project_key in enumerate(variant['projects']):
            project = data['projects'][project_key]
            title = f'<a href="{escape(project["url"])}" color="#20272C">{escape(project["name"])}</a>'
            block = [Spacer(1, 6)] if idx else []
            block.extend([pair(title, project['stack'], 'project', 'stack', right_width=238),
                          p(selected_copy[project_key])])
            story.append(KeepTogether(block))

        story.append(Section('Technical skills', bold))
        story.append(p('<b>Professional:</b> ' + escape(data['professional_skills']), 'skills', True))
        story.append(Spacer(1, 3))
        story.append(p('<b>Portfolio:</b> ' + escape(variant['project_skills']), 'skills', True))

        story.append(Section('Education & certifications', bold))
        for line in data['education']:
            story.append(p(line, 'education'))
            story.append(Spacer(1, 2))

        output = output_dir / variant['filename']
        document = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=MARGIN,
                                     rightMargin=MARGIN, topMargin=30, bottomMargin=30,
                                     title=data['name'] + ' - ' + variant['headline'],
                                     author=data['name'])
        document.build(story)
        reader = PdfReader(output)
        if len(reader.pages) != 1:
            raise ValueError(f'{output.name}: {len(reader.pages)} pages; edit copy/spacing, not body size')
        text = reader.pages[0].extract_text()
        normalized_text = ' '.join(text.split())
        for project_key, copy in selected_copy.items():
            if ' '.join(copy.split()) not in normalized_text:
                raise ValueError(f'Missing role-specific project text: {project_key}')
        for item in (data['name'], '30+', '10+', '15+', '40+', 'Expected 2027'):
            if item not in text:
                raise ValueError(f'Missing extractable fact: {item}')
        for job in data['experience']:
            for role in job.get('roles', []):
                for item in (role['title'], role['dates']):
                    if item not in text:
                        raise ValueError(f'Missing role or date: {item}')
        if '\ufffd' in text:
            raise ValueError('Replacement character in text extraction')
        urls = [a.get_object().get('/A', {}).get('/URI') for a in reader.pages[0].get('/Annots', [])]
        expected = [url for _, url in contacts] + [data['projects'][x]['url'] for x in variant['projects']]
        if not set(expected).issubset(set(urls)):
            raise ValueError('Missing contact or project link')
        if len(variant['projects']) != 3:
            raise ValueError('Each CV must feature three projects')
        result = {'variant': key, 'file': output.name, 'pages': 1, 'hyperlinks': len(urls),
                  'body_font_pt': 10.7, 'font': regular, 'projects': variant['projects'],
                  'role_dates_extractable': True}
        results.append(result)
        print(json.dumps(result))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).with_name('cv_data.json'))
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--font-dir', type=Path)
    args = parser.parse_args()
    build(args.source, args.output_dir, args.font_dir)
