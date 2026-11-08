"""Build both one-page CV variants from a shared, editable source.

python -m pip install reportlab pypdf
python tools/build_cv.py --output-dir .
Optional: --font-dir PATH containing arial.ttf and arialbd.ttf.
"""

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer


def build(source, output_dir, font_dir=None):
    data = json.loads(source.read_text(encoding="utf-8"))
    regular, bold = "Helvetica", "Helvetica-Bold"
    if font_dir:
        regular, bold = "CVSans", "CVSans-Bold"
        pdfmetrics.registerFont(TTFont(regular, str(font_dir / "arial.ttf")))
        pdfmetrics.registerFont(TTFont(bold, str(font_dir / "arialbd.ttf")))
        pdfmetrics.registerFontFamily(regular, normal=regular, bold=bold)
    base = ParagraphStyle("body", fontName=regular, fontSize=10.5,
                          leading=12.6, textColor=colors.HexColor("#181818"),
                          spaceAfter=3, alignment=TA_LEFT)
    styles = {
        "body": base,
        "name": ParagraphStyle("name", parent=base, fontName=bold, fontSize=23,
                               leading=27, spaceAfter=2),
        "role": ParagraphStyle("role", parent=base, fontName=bold, fontSize=12,
                               leading=15, spaceAfter=5),
        "contact": ParagraphStyle("contact", parent=base, fontSize=9.7,
                                  leading=12, spaceAfter=2),
        "section": ParagraphStyle("section", parent=base, fontName=bold,
                                  fontSize=11.3, leading=14, spaceBefore=7,
                                  spaceAfter=5, keepWithNext=True),
        "job": ParagraphStyle("job", parent=base, fontName=bold,
                              spaceBefore=3, spaceAfter=1, keepWithNext=True),
        "meta": ParagraphStyle("meta", parent=base, textColor=colors.HexColor("#444444"),
                               fontSize=9.8, leading=12.2, spaceAfter=3,
                               keepWithNext=True),
        "bullet": ParagraphStyle("bullet", parent=base, leftIndent=9,
                                 firstLineIndent=-9, spaceAfter=3),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for variant in data["variants"].values():
        story = []

        def p(text, style="body", raw=False):
            return Paragraph(text if raw else escape(text), styles[style])

        def add(text, style="body", raw=False):
            story.append(p(text, style, raw))

        add(data["name"], "name")
        add(variant["headline"], "role")
        add(data["contact"], "contact")
        contact = [(data["email"], "mailto:" + data["email"]), *data["links"]]
        add(" | ".join(f'<a href="{escape(url)}" color="#181818"><u>{escape(label)}</u></a>'
                       for label, url in contact), "contact", True)
        story.append(Spacer(1, 6))
        add(variant["summary"])
        add("Technical skills", "section")
        add("<b>Professional:</b> " + escape(data["professional_skills"]), raw=True)
        add("<b>Portfolio:</b> " + escape(variant["project_skills"]), raw=True)
        add("Experience", "section")
        for job in data["experience"]:
            block = [p(job["title"], "job"), p(job["company"] + " | " + job["dates"], "meta")]
            block.extend(p("- " + bullet, "bullet") for bullet in job["bullets"])
            story.append(KeepTogether(block))
        add("Selected projects", "section")
        for key in variant["projects"]:
            project = data["projects"][key]
            title = f'<a href="{escape(project["url"])}" color="#181818"><u>{escape(project["name"])}</u></a>'
            title += ' <font name="' + regular + '" size="9.8"> | ' + escape(project["stack"]) + '</font>'
            story.append(KeepTogether([p(title, "job", True), p(project["text"])]))
        add("Education and certifications", "section")
        for line in data["education"]:
            add(line)
        output = output_dir / variant["filename"]
        doc = SimpleDocTemplate(str(output), pagesize=A4,
                                rightMargin=39, leftMargin=39,
                                topMargin=30, bottomMargin=30,
                                title=data["name"] + " - " + variant["headline"],
                                author=data["name"])
        doc.build(story)
        reader = PdfReader(output)
        if len(reader.pages) != 1:
            raise ValueError(f"{output.name} must be one readable page; got {len(reader.pages)}")
        text = reader.pages[0].extract_text()
        for required in (data["name"], "30+", "10+", "15+", "40+", "Expected 2027"):
            if required not in text:
                raise ValueError(f"Missing extractable text: {required}")
        if "\ufffd" in text:
            raise ValueError("Invalid replacement character in PDF text extraction")
        links = [a.get_object().get("/A", {}).get("/URI")
                 for a in reader.pages[0].get("/Annots", [])]
        expected_urls = [url for _, url in contact]
        expected_urls += [data["projects"][key]["url"] for key in variant["projects"]]
        if not set(expected_urls).issubset(set(links)):
            raise ValueError("Missing clickable contact or project links")
        print(f"{output.name}: 1 page, extractable text, {len(links)} verified hyperlinks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name("cv_data.json"))
    parser.add_argument("--font-dir", type=Path)
    args = parser.parse_args()
    build(args.source, args.output_dir, args.font_dir)
