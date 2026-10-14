"""Превью статьи в духе VC: article_v2_vc.md -> article_v2_vc.pdf.

Запуск: python3 preview/build_pdf.py  (из drafts/vc_coupon_ai)
Источник истины — MD; скрипт его только читает.
"""
import html
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "article_v2_vc.md"
OUT = ROOT / "preview"
VIDEO = ROOT / "out" / "01-produkt-demo.mp4"
POSTER = OUT / "video-poster.jpg"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FFMPEG = "ffmpeg"

CSS = """
@page { size: A4; margin: 18mm 0 18mm 0; }
* { box-sizing: border-box; }
html, body { margin: 0; background: #fff; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Roboto, Arial, sans-serif;
  font-size: 17px; line-height: 1.6; color: #000;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.page { width: 640px; margin: 0 auto; }
h1 { font-size: 30px; line-height: 1.25; font-weight: 700; margin: 0 0 22px; letter-spacing: -0.01em; }
h2 { font-size: 22px; line-height: 1.3; font-weight: 700; margin: 34px 0 12px; break-after: avoid; }
p { margin: 0 0 16px; }
p.lead-bold { margin-top: 22px; margin-bottom: 8px; break-after: avoid; }
strong { font-weight: 700; }
code { font-family: "SF Mono", Menlo, monospace; font-size: 14.5px; background: #f2f3f5; padding: 1px 5px; border-radius: 4px; }
ul, ol { margin: 0 0 18px; padding-left: 26px; }
li { margin: 0 0 8px; padding-left: 4px; }
figure { margin: 24px 0 26px; break-inside: avoid; }
figure img { display: block; width: 100%; border-radius: 8px; border: 1px solid #ececec; }
figcaption { font-size: 14px; line-height: 1.45; color: #595959; margin-top: 8px; }
.video { position: relative; }
.video .play {
  position: absolute; left: 50%; top: 50%; width: 76px; height: 76px; margin: -38px 0 0 -38px;
  border-radius: 50%; background: rgba(0, 0, 0, 0.55);
}
.video .play::after {
  content: ""; position: absolute; left: 30px; top: 22px;
  border-style: solid; border-width: 16px 0 16px 26px; border-color: transparent transparent transparent #fff;
}
.video .dur {
  position: absolute; right: 12px; bottom: 12px; font-size: 13px; color: #fff;
  background: rgba(0, 0, 0, 0.6); padding: 2px 8px; border-radius: 6px;
}
blockquote {
  margin: 26px 0 28px; padding: 2px 0 2px 22px; border-left: 4px solid #000;
  font-size: 20px; line-height: 1.5; font-weight: 500; break-inside: avoid;
}
blockquote p { margin: 0; }
blockquote .cap { font-size: 14px; font-weight: 400; color: #595959; margin-top: 10px; }
"""


def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return t


def caption_of(line: str) -> str:
    m = re.search(r"подпись:\s*(.+?)\]?\s*$", line, re.IGNORECASE)
    return m.group(1).strip("* ") if m else ""


def video_duration() -> str:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(VIDEO)],
        capture_output=True, text=True, check=True,
    ).stdout
    s = round(float(out))
    return f"{s // 60}:{s % 60:02d}"


def convert(md: str) -> str:
    lines = md.split("\n")
    out, para, i = [], [], 0

    def flush():
        if para:
            text = " ".join(para)
            cls = ' class="lead-bold"' if re.fullmatch(r"\*\*[^*]+\*\*", text) else ""
            out.append(f"<p{cls}>{inline(text)}</p>")
            para.clear()

    while i < len(lines):
        s = lines[i].strip()
        if not s:
            flush(); i += 1; continue
        if s.startswith("# "):
            flush(); out.append(f"<h1>{inline(s[2:])}</h1>")
        elif s.startswith("## "):
            flush(); out.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("![") :
            flush()
            m = re.match(r"!\[(.*)\]\((.+)\)", s)
            alt, src = m.group(1), m.group(2).lstrip("/")
            out.append(f'<figure><img src="../{src}" alt=""><figcaption>{inline(alt)}</figcaption></figure>')
        elif s.startswith("[Видео"):
            flush()
            out.append(
                f'<figure><div class="video"><img src="{POSTER.name}" alt=""><span class="play"></span>'
                f'<span class="dur">{video_duration()}</span></div><figcaption>{inline(caption_of(s))}</figcaption></figure>'
            )
        elif s.startswith(">"):
            flush()
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip().lstrip(">").strip()); i += 1
            cap = ""
            if i < len(lines) and lines[i].strip().startswith("[Блок-цитата"):
                cap = caption_of(lines[i].strip()); i += 1
            cap_html = f'<div class="cap">{inline(cap)}</div>' if cap else ""
            out.append(f"<blockquote><p>{inline(' '.join(q))}</p>{cap_html}</blockquote>")
            continue
        elif re.match(r"^(\*|-|\d+\.)\s", s):
            flush()
            ordered = bool(re.match(r"^\d+\.", s))
            items = []
            while i < len(lines):
                t = lines[i].strip()
                if re.match(r"^(\*|-|\d+\.)\s", t):
                    items.append(re.sub(r"^(\*|-|\d+\.)\s+", "", t)); i += 1
                elif not t and i + 1 < len(lines) and re.match(r"^(\*|-|\d+\.)\s", lines[i + 1].strip()):
                    i += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        else:
            para.append(s)
        i += 1
    flush()
    return "\n".join(out)


def main():
    subprocess.run(
        [FFMPEG, "-loglevel", "error", "-y", "-ss", "7", "-i", str(VIDEO), "-frames:v", "1",
         "-vf", "scale=1280:-1", "-q:v", "3", str(POSTER)],
        check=True,
    )
    body = convert(SRC.read_text(encoding="utf-8"))
    page = (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f"<title>{SRC.stem}</title><style>{CSS}</style></head>"
        f'<body><div class="page">{body}</div></body></html>'
    )
    html_path = OUT / f"{SRC.stem}.html"
    pdf_path = OUT / f"{SRC.stem}.pdf"
    html_path.write_text(page, encoding="utf-8")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, capture_output=True,
    )
    print(pdf_path)


if __name__ == "__main__":
    main()
