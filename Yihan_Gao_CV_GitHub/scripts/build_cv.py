"""Build both CV languages and the GitHub Pages bundle from data/cv.json."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "cv.json"
BLUE = "#405b73"
GRAY = "#657080"
WIDTH = A4[0] - 88


def tr(value, lang):
    return value.get(lang, "") if isinstance(value, dict) else value


def esc(value):
    return html.escape(str(value or ""), quote=True)


def authors(value):
    return esc(value).replace("Gao, Y.", "<b>Gao, Y.</b>").replace("高一涵", "<b>高一涵</b>")


def prepare_fonts():
    folder = ROOT / "assets" / "fonts"
    for suffix, file in [("", "Regular"), ("-Bold", "Bold"), ("-Italic", "Italic"), ("-BoldItalic", "BoldItalic")]:
        pdfmetrics.registerFont(TTFont("Tinos" + suffix, str(folder / f"Tinos-{file}.ttf")))
    pdfmetrics.registerFontFamily("Tinos", normal="Tinos", bold="Tinos-Bold", italic="Tinos-Italic", boldItalic="Tinos-BoldItalic")
    # Instantiate the open-licensed variable font locally. All CJK characters remain
    # available, so later additions to the data file do not require font subsetting.
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    from fontTools.ttLib import TTFont as FontToolsFont
    from fontTools.varLib.instancer import instantiateVariableFont
    for name, weight in [("NotoSC", 400), ("NotoSC-Bold", 700)]:
        target = cache / f"{name}.ttf"
        if not target.exists():
            font = FontToolsFont(folder / "NotoSerifSC-Variable.ttf")
            instance = instantiateVariableFont(font, {"wght": weight}, inplace=True)
            instance.save(target)
            instance.close()
        # ReportLab deduplicates embedded faces by their internal PostScript name.
        # Give the two static instances distinct names rather than reusing the
        # variable font's shared name, so Chinese bold stays genuinely bold.
        check = FontToolsFont(target)
        ps_name = "NotoSerifSC-CV" + ("Bold" if weight == 700 else "Regular")
        if check["name"].getDebugName(6) != ps_name:
            for record in check["name"].names:
                if record.nameID in (1, 2, 4, 6):
                    value = ps_name if record.nameID in (1, 4, 6) else ("Bold" if weight == 700 else "Regular")
                    record.string = value.encode(record.getEncoding())
            check.save(target)
        check.close()
        pdfmetrics.registerFont(TTFont(name, str(target)))
    pdfmetrics.registerFontFamily("NotoSC", normal="NotoSC", bold="NotoSC-Bold", italic="NotoSC", boldItalic="NotoSC-Bold")


def pub_markup(item, lang):
    a = item.get("authors_zh", item["authors"]) if lang == "zh" else item["authors"]
    title = item.get("title_zh", item["title"]) if lang == "zh" else item["title"]
    venue = item.get("venue_zh", item.get("venue", "")) if lang == "zh" else item.get("venue", "")
    linked = f'<a href="{esc(item["url"])}" color="#26323b">{esc(title)}</a>' if item.get("url") else esc(title)
    bits = [f'{authors(a)} ({esc(item["year"])}). {linked}.']
    if venue:
        bits.append(f"<i>{esc(venue)}</i>" + (", " + esc(item["details"]) if item.get("details") else "") + ".")
    if item.get("language") == "Chinese" and lang == "en":
        bits.append("(In Chinese.)")
    if item.get("status"):
        bits.append(f'<i>{esc(tr(item["status"], lang))}.</i>')
    return " ".join(bits)


HEADINGS = {
    "education": ("Education", "教育背景"), "research": ("Research Interests", "研究方向"),
    "experience": ("Research Experience", "科研经历"), "working": ("Working Papers", "工作论文"),
    "journals": ("Journal Publications", "期刊论文"), "chapters": ("Book Chapters", "著作章节"),
    "teaching": ("Teaching Experience", "教学经历"), "presentations": ("Conference Presentations", "会议报告"),
    "projects": ("Research Projects", "科研项目"), "awards": ("Awards and Honors", "奖励与荣誉"),
}


def label(key, lang):
    return HEADINGS[key][0 if lang == "en" else 1]


def build_pdf(data, lang):
    family = "Tinos" if lang == "en" else "NotoSC"
    size, leading = (10.4, 12.8) if lang == "en" else (9.5, 13.8)
    body = ParagraphStyle("body", fontName=family, fontSize=size, leading=leading, textColor=colors.HexColor("#252a30"), spaceAfter=3, wordWrap="CJK" if lang == "zh" else None)
    small = ParagraphStyle("small", parent=body, fontSize=9.2, leading=12, textColor=colors.HexColor(GRAY))
    right = ParagraphStyle("right", parent=small, alignment=TA_RIGHT)
    title = ParagraphStyle("name", parent=body, fontName=family + "-Bold", fontSize=27, leading=32, alignment=TA_CENTER, spaceAfter=5)
    center = ParagraphStyle("contact", parent=small, alignment=TA_CENTER, fontSize=9.6, leading=13)
    sec = ParagraphStyle("section", parent=body, fontName=family + "-Bold", fontSize=11.1, leading=14, textColor=colors.HexColor(BLUE), spaceBefore=8, spaceAfter=1, keepWithNext=True)
    sub = ParagraphStyle("sub", parent=body, fontName=family + "-Bold", textColor=colors.HexColor(BLUE))
    story = []
    p = lambda text, style=body: Paragraph(text, style)

    def section(key):
        name = label(key, lang)
        rule = HRFlowable(width="100%", thickness=0.45, color=colors.HexColor("#c5d0da"), spaceAfter=4)
        rule.keepWithNext = True
        story.extend([p(esc(name.upper() if lang == "en" else name), sec), rule])

    def pair(left, text_right, detail=None):
        table = Table([[p(left), p(text_right, right)]], colWidths=[WIDTH - 172, 172])
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        group = [table]
        if detail:
            group.append(p(detail))
        group.append(Spacer(1, 2))
        story.append(KeepTogether(group))

    def numbered(items):
        for i, item in enumerate(items, 1):
            para = ParagraphStyle(f"entry{i}", parent=body, leftIndent=21, firstLineIndent=-21, spaceAfter=5)
            story.append(KeepTogether([p(f"[{i}] " + pub_markup(item, lang), para)]))

    story.append(p(esc(tr(data["name"], lang)), title))
    story.append(p(esc(tr(data["department"], lang)), center))
    story.append(p(esc(tr(data["institution"], lang)) + (" | Hong Kong, China" if lang == "en" else "｜中国香港"), center))
    links = [("Email" if lang == "en" else "邮箱", "mailto:" + data["email"]), ("Homepage" if lang == "en" else "个人主页", data["homepage"]), ("Google Scholar", data["scholar"]), ("ORCID", data["orcid"])]
    story.append(p(" &nbsp; | &nbsp; ".join(f'<a href="{esc(url)}" color="{BLUE}">{esc(text)}</a>' for text, url in links), center))
    story.append(p(esc(data["email"]), center))
    story.append(Spacer(1, 4))

    section("education")
    for item in data["education"]:
        pair(f'<b>{esc(tr(item["institution"], lang))}</b><br/>{esc(tr(item["degree"], lang))}', f'{esc(tr(item["location"], lang))}<br/>{esc(tr(item["dates"], lang))}', esc(tr(item["detail"], lang)))

    section("research")
    headings = ("Methodologies", "Application Areas") if lang == "en" else ("研究方法", "应用领域")
    rows = [[p(headings[0], sub), p(headings[1], sub)]]
    for i, (m, a) in enumerate(zip(data["research"]["methods"][lang], data["research"]["applications"][lang]), 1):
        rows.append([p(f"{i}. {esc(m)}"), p(f"{i}. {esc(a)}")])
    table = Table(rows, colWidths=[WIDTH * 0.49, WIDTH * 0.51])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story.append(table)

    section("experience")
    for item in data["experience"]:
        pair(f'<b>{esc(tr(item["institution"], lang))}</b><br/>{esc(tr(item["role"], lang))}', esc(tr(item["dates"], lang)), esc(tr(item["detail"], lang)))

    section("working")
    numbered(data["working_papers"])
    section("journals")
    numbered(data["journal_publications"])
    section("chapters")
    numbered(data["chapters"])

    section("teaching")
    story.append(p(esc(tr(data["institution"], lang)), small))
    for item in data["teaching"]:
        # A full-width course line avoids narrow columns for long official titles.
        story.append(KeepTogether([p(f'<b>{esc(item["code"])} {esc(tr(item["title"], lang))}</b>'), p(f'{esc(tr(item["role"], lang))} &nbsp; | &nbsp; {esc(tr(item["dates"], lang))}', small), Spacer(1, 4)]))

    section("presentations")
    for i, item in enumerate(data["presentations"], 1):
        title_text = esc(item["title"])
        if item.get("url"):
            title_text = f'<a href="{esc(item["url"])}" color="#26323b">{title_text}</a>'
        text = f'[{i}] {title_text}. <i>{esc(tr(item["event"], lang))}</i>. {esc(tr(item["location"], lang))}, {esc(tr(item["dates"], lang))}.'
        story.append(p(text, ParagraphStyle("talk", parent=body, leftIndent=21, firstLineIndent=-21, spaceAfter=6)))

    section("projects")
    for i, item in enumerate(data["projects"], 1):
        text = f'[{i}] {esc(tr(item["title"], lang))}. {esc(tr(item["funder"], lang))}. {esc(item["dates"])}. <b>{esc(tr(item["role"], lang))}.</b>'
        story.append(p(text, ParagraphStyle("project", parent=body, leftIndent=21, firstLineIndent=-21, spaceAfter=6)))

    section("awards")
    for item in data["awards"]:
        pair(esc(tr(item["title"], lang)), esc(item["year"]))

    output = ROOT / "cv" / f"Yihan_Gao_CV_{lang.upper()}.pdf"
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=44, leftMargin=44, topMargin=39, bottomMargin=39, title=f'{tr(data["name"], lang)} - Curriculum Vitae', author="Yihan Gao", allowSplitting=1)

    def decorate(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(GRAY))
        canvas.setFont("Tinos", 8)
        if document.page > 1:
            canvas.drawString(44, A4[1] - 24, "Yihan Gao")
            canvas.drawRightString(A4[0] - 44, A4[1] - 24, "Curriculum Vitae")
        canvas.drawString(44, 23, "Updated: " + data["updated"])
        canvas.drawRightString(A4[0] - 44, 23, "Page " + str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print("Built", output.relative_to(ROOT))


CSS = """
:root{--ink:#242b32;--muted:#657080;--blue:#405b73;--line:#d0dae3}
*{box-sizing:border-box}body{margin:0;background:#f4f5f6;color:var(--ink);font:17px/1.58 Georgia,'Noto Serif SC','Songti SC',serif}
.sheet{max-width:960px;margin:35px auto;background:white;padding:50px 65px;box-shadow:0 4px 24px #00000009}
header{text-align:center}h1{font-size:42px;line-height:1.2;margin:0 0 12px}header p{margin:3px 0}a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.links{display:flex;justify-content:center;gap:10px 20px;flex-wrap:wrap;font-size:15px}.toolbar{max-width:960px;margin:25px auto 0;display:flex;gap:12px;justify-content:flex-end;padding:0 15px;font:14px/1.6 system-ui,sans-serif}
.toolbar a{border:1px solid #cbd3db;padding:5px 14px;background:white;border-radius:4px}h2{color:var(--blue);font-size:19px;line-height:1.3;border-bottom:1px solid var(--line);margin:26px 0 10px;text-transform:uppercase;letter-spacing:.04em}
.entry{margin:0 0 12px;break-inside:avoid}.entry-head{display:flex;justify-content:space-between;gap:20px}.date{color:var(--muted);text-align:right;font-size:15px;flex-shrink:0}.detail{margin:1px 0}.research{display:grid;grid-template-columns:1fr 1fr;gap:30px}.research ol{padding-left:24px;margin:6px 0}.pubs{list-style:none;counter-reset:pub;padding-left:30px;margin:0}.pubs li{counter-increment:pub;margin-bottom:12px;position:relative;break-inside:avoid}.pubs li:before{content:'[' counter(pub) ']';position:absolute;left:-30px;color:var(--blue)}
.subtle{color:var(--muted);font-size:15px}footer{margin-top:30px;font-size:13px;color:var(--muted)}.zh{font-family:'Noto Serif SC','Songti SC','SimSun',serif}
@media(max-width:650px){body{font-size:16px}.sheet{margin:12px 0;padding:30px 22px}.toolbar{margin-top:12px;justify-content:flex-start;flex-wrap:wrap}.entry-head{display:block}.date{text-align:left}.research{grid-template-columns:1fr;gap:12px}h1{font-size:34px}}
@media print{body{background:white;font-size:10.5pt}.sheet{max-width:none;margin:0;padding:0;box-shadow:none}.toolbar{display:none}h2{break-after:avoid}.date{font-size:9pt}a{color:inherit}header h1{font-size:25pt}@page{size:A4;margin:17mm}}
"""


def build_html(data, lang):
    parts = []
    def section(key, content):
        parts.append(f'<section aria-labelledby="{key}"><h2 id="{key}">{esc(label(key, lang))}</h2>{content}</section>')
    def entry(left, right="", detail=""):
        return f'<div class="entry"><div class="entry-head"><div>{left}</div><div class="date">{right}</div></div>{f"<p class=detail>{detail}</p>" if detail else ""}</div>'
    section("education", "".join(entry(f'<b>{esc(tr(x["institution"], lang))}</b><br>{esc(tr(x["degree"], lang))}', esc(tr(x["dates"], lang)), esc(tr(x["detail"], lang))) for x in data["education"]))
    columns = []
    for key, h in [("methods", "Methodologies" if lang == "en" else "研究方法"), ("applications", "Application Areas" if lang == "en" else "应用领域")]:
        columns.append(f'<div><b>{h}</b><ol>' + "".join(f'<li>{esc(x)}</li>' for x in data["research"][key][lang]) + '</ol></div>')
    section("research", '<div class="research">' + "".join(columns) + '</div>')
    section("experience", "".join(entry(f'<b>{esc(tr(x["institution"], lang))}</b><br>{esc(tr(x["role"], lang))}', esc(tr(x["dates"], lang)), esc(tr(x["detail"], lang))) for x in data["experience"]))
    for key, field in [("working", "working_papers"), ("journals", "journal_publications"), ("chapters", "chapters")]:
        # ReportLab's optional color attribute has no effect on browser semantics.
        section(key, '<ol class="pubs">' + "".join('<li>' + pub_markup(x, lang) + '</li>' for x in data[field]) + '</ol>')
    section("teaching", '<p class="subtle">' + esc(tr(data["institution"], lang)) + '</p>' + "".join(entry(f'<b>{esc(x["code"])} {esc(tr(x["title"], lang))}</b>', "", f'{esc(tr(x["role"], lang))} | {esc(tr(x["dates"], lang))}') for x in data["teaching"]))
    section("presentations", '<ol class="pubs">' + "".join(f'<li>{esc(x["title"])}. <i>{esc(tr(x["event"], lang))}</i>. {esc(tr(x["location"], lang))}, {esc(tr(x["dates"], lang))}.</li>' for x in data["presentations"]) + '</ol>')
    section("projects", '<ol class="pubs">' + "".join(f'<li>{esc(tr(x["title"], lang))}. {esc(tr(x["funder"], lang))}. {esc(x["dates"])}. <b>{esc(tr(x["role"], lang))}.</b></li>' for x in data["projects"]) + '</ol>')
    section("awards", "".join(entry(esc(tr(x["title"], lang)), esc(x["year"])) for x in data["awards"]))
    nav = [('index.html', 'English'), ('zh.html', '中文'), (f'Yihan_Gao_CV_{lang.upper()}.pdf', 'Download PDF' if lang == 'en' else '下载 PDF'), ('../index.html', 'Homepage' if lang == 'en' else '返回主页')]
    text = f'''<!doctype html>
<html lang="{'en' if lang == 'en' else 'zh-CN'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{esc(tr(data['name'], lang))} academic curriculum vitae"><title>{esc(tr(data['name'], lang))} | Curriculum Vitae</title><style>{CSS}</style></head>
<body class="{lang}"><nav class="toolbar" aria-label="CV navigation">{''.join(f'<a href="{href}">{name}</a>' for href, name in nav)}</nav><main class="sheet"><header><h1>{esc(tr(data['name'], lang))}</h1><p>{esc(tr(data['department'], lang))}</p><p>{esc(tr(data['institution'], lang))}</p><p><a href="mailto:{esc(data['email'])}">{esc(data['email'])}</a></p><div class="links"><a href="{esc(data['homepage'])}">{'Homepage' if lang == 'en' else '个人主页'}</a><a href="{esc(data['scholar'])}">Google Scholar</a><a href="{esc(data['orcid'])}">ORCID</a></div></header>{''.join(parts)}<footer>{'Last updated' if lang == 'en' else '更新日期'}: {esc(data['updated'])}</footer></main></body></html>'''
    target = ROOT / "cv" / ("index.html" if lang == "en" else "zh.html")
    target.write_text(text, encoding="utf-8")
    print("Built", target.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", help="Copy only public files to this GitHub Pages output folder")
    args = parser.parse_args()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    prepare_fonts()
    (ROOT / "cv").mkdir(exist_ok=True)
    for lang in ["en", "zh"]:
        build_pdf(data, lang)
        build_html(data, lang)
    if args.site_dir:
        target = Path(args.site_dir)
        if not target.is_absolute():
            target = ROOT / target
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "index.html", target / "index.html")
        shutil.copytree(ROOT / "cv", target / "cv", dirs_exist_ok=True)
        (target / ".nojekyll").touch()
        print("Pages bundle:", target)


if __name__ == "__main__":
    main()
