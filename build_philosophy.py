#!/usr/bin/env python3
"""Build static site for 哲学 knowledge graph — aligned with lhx-knowledge-graph quality."""
import os
import re
import yaml
from pathlib import Path

VAULT = Path(__file__).parent / "vault" / "哲学"
OUT = Path(__file__).parent / "output"
SITE_TITLE = "哲学知识图谱"
SITE_LOGO = "哲"
BASE_PATH = "/philosophy-knowledge-graph"

CATEGORY_DIRS = {"concepts": "concepts"}
CATEGORY_LABELS = {"concepts": "概念"}

# --- helpers ---

def parse_md(fp):
    t = fp.read_text(encoding="utf-8")
    fm, body = {}, t
    if t.startswith("---"):
        p = t.split("---", 2)
        if len(p) >= 3:
            try:
                fm = yaml.safe_load(p[1]) or {}
            except Exception:
                pass
            body = p[2]
    return fm, body


def collect_files():
    files = []
    for cat, dn in CATEGORY_DIRS.items():
        d = VAULT / dn
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            fm, body = parse_md(f)
            files.append({"path": f, "stem": f.stem, "category": cat, "fm": fm, "body": body})
    return files


def build_link_map(files):
    lm = {}
    for f in files:
        s, c = f["stem"], f["category"]
        lm[s] = f"{BASE_PATH}/{c}/{s}.html"
        for a in f["fm"].get("aliases", []):
            if a not in lm:
                lm[a] = lm[s]
    return lm


def convert_wikilinks(text, lm):
    def r(m):
        inner = m.group(1)
        t = inner.split("|", 1)[0].strip() if "|" in inner else inner.strip()
        url = lm.get(t)
        return f'<a href="{url}">{t}</a>' if url else t
    return re.sub(r'\[\[([^\]]+)\]\]', r, text)


def md_to_html(t, lm):
    t = convert_wikilinks(t, lm)
    # tables
    lines = t.split("\n")
    out, in_tbl = [], False
    for line in lines:
        if "|" in line and line.strip().startswith("|"):
            if not in_tbl:
                out.append("<table>")
                in_tbl = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.match(r"^[-:]+$", c) for c in cells):
                continue
            tag = "th" if not any(re.match(r"^[-:]+$", c) for c in cells) else "td"
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        else:
            if in_tbl:
                out.append("</table>")
                in_tbl = False
            out.append(line)
    if in_tbl:
        out.append("</table>")
    t = "\n".join(out)
    # blockquotes
    t = re.sub(r"^> (.+)$", r"<blockquote><p>\1</p></blockquote>", t, flags=re.MULTILINE)
    # headings
    t = re.sub(r"^### (.+)$", r"<h3>\1</h3>", t, flags=re.MULTILINE)
    t = re.sub(r"^## (.+)$", r"<h2>\1</h2>", t, flags=re.MULTILINE)
    t = re.sub(r"^# (.+)$", r"<h1>\1</h1>", t, flags=re.MULTILINE)
    # bold/italic
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    # lists
    t = re.sub(r"^- (.+)$", r"<li>\1</li>", t, flags=re.MULTILINE)
    t = re.sub(r"^(\d+)\. (.+)$", r"<li>\2</li>", t, flags=re.MULTILINE)
    t = re.sub(r"(<li>.*</li>\n?)+", lambda m: "<ul>" + m.group(0) + "</ul>", t)
    # paragraphs
    t = re.sub(r"\n\n+", "</p><p>", t)
    t = "<p>" + t + "</p>"
    t = t.replace("<p></p>", "").replace("<p><h", "<h").replace("</h1></p>", "</h1>").replace("</h2></p>", "</h2>").replace("</h3></p>", "</h3>")
    t = t.replace("<p><ul>", "<ul>").replace("</ul></p>", "</ul>").replace("<p><table>", "<table>").replace("</table></p>", "</table>").replace("<p><blockquote>", "<blockquote>").replace("</blockquote></p>", "</blockquote>")
    return t


def build_backlinks(files, lm):
    a2s = {}
    for f in files:
        a2s[f["stem"]] = f["stem"]
        for a in f["fm"].get("aliases", []):
            a2s[a] = f["stem"]
    bl = {}
    for f in files:
        seen = set()
        for m in re.finditer(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', f["body"]):
            tgt = a2s.get(m.group(1).strip(), m.group(1).strip())
            if tgt == f["stem"] or tgt in seen:
                continue
            seen.add(tgt)
            s_idx = max(0, m.start() - 60)
            e_idx = min(len(f["body"]), m.end() + 60)
            ex = f["body"][s_idx:e_idx].replace("\n", " ").strip()
            ex = re.sub(r'\*\*([^*]+)\*\*', r'\1', ex)
            ex = re.sub(r'\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]', lambda x: x.group(2) or x.group(1), ex)
            if s_idx > 0:
                ex = "…" + ex
            if e_idx < len(f["body"]):
                ex = ex + "…"
            bl.setdefault(tgt, []).append({
                "stem": f["stem"],
                "category": f["category"],
                "title": f["fm"].get("title", f["stem"]),
                "excerpt": ex,
            })
    return bl


CSS = r"""
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#F7F3ED;--bg2:#EDE8DF;--text:#433D50;--text2:#6B7889;
  --primary:#7A6296;--primary-light:#9B85B5;--primary-glow:rgba(122,98,150,.10);
  --accent:#B98A5C;--accent-light:#D4A873;
  --navy:#433D50;--navy-light:#5A5268;--cream:#F0EBE3;
  --border:#D5CFC5;--card:#FFFFFF;--link:#7A6296;
  --serif:'Noto Serif SC','Crimson Pro',Georgia,serif;
  --sans:'DM Sans',-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;
  --sidebar-w:260px;
}
html{font-size:15px;scroll-behavior:smooth}
body{font-family:var(--sans);color:var(--text);background:var(--bg);display:flex;min-height:100vh;line-height:1.8;-webkit-font-smoothing:antialiased}

.sidebar{width:var(--sidebar-w);background:var(--navy);position:fixed;top:0;left:0;bottom:0;overflow-y:auto;z-index:100;display:flex;flex-direction:column}
.sidebar-header{padding:20px 16px 16px;border-bottom:1px solid rgba(255,255,255,.08)}
.logo{color:#fff;font-size:17px;font-weight:700;text-decoration:none;letter-spacing:.5px;font-family:var(--serif);display:block}
.logo:hover{color:var(--accent-light)}
.sidebar-nav{flex:1;padding:8px 0;overflow-y:auto;display:flex;flex-direction:column}
.sidebar-nav::-webkit-scrollbar{width:4px}
.sidebar-nav::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:2px}
.nav-link{display:block;padding:6px 16px;color:#cbd5e1;text-decoration:none;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-left:3px solid transparent;transition:all .15s}
.nav-link:hover{background:rgba(255,255,255,.06);color:#fff}
.nav-link.active{color:#fff;background:rgba(122,98,150,.2);border-left-color:var(--accent-light);font-weight:600}
.nav-home{font-size:14px;padding:10px 16px;font-weight:500;margin-bottom:4px}
.nav-group{margin-bottom:2px}
.nav-group-title{padding:8px 16px;color:#cbd5e1;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;cursor:pointer;display:flex;align-items:center;gap:6px;user-select:none;transition:color .15s}
.nav-group-title:hover{color:#fff}
.caret{display:inline-block;width:0;height:0;border-left:5px solid #cbd5e1;border-top:4px solid transparent;border-bottom:4px solid transparent;transition:transform .2s}
.nav-group.open .nav-group-title .caret{transform:rotate(90deg);border-left-color:#fff}
.nav-group-title .badge{margin-left:auto;background:rgba(255,255,255,.1);color:#cbd5e1;font-size:11px;padding:1px 6px;border-radius:8px;font-weight:400}
.nav-group-items{display:none;padding-left:8px}
.nav-group.open .nav-group-items{display:block}
.hamburger{display:none;position:fixed;top:12px;left:12px;z-index:200;background:var(--navy);color:#fff;border:none;font-size:20px;padding:6px 10px;border-radius:6px;cursor:pointer}

.main{margin-left:max(var(--sidebar-w),calc((100vw - 1160px)/2));flex:1;position:relative;max-width:1160px;padding:0}
.article{max-width:820px;padding:48px 48px 80px}
.meta{font-size:13px;color:var(--text2);margin-bottom:16px;display:flex;align-items:center;gap:8px}
.type-badge{font-size:11px;padding:2px 8px;border-radius:4px;color:#fff;font-weight:600}
.type-概念{background:var(--primary)}.type-人物{background:#B85C1E}.type-索引{background:#6B6560}

.article h1{font-family:var(--serif);font-size:28px;line-height:1.3;margin-bottom:24px;font-weight:900;color:var(--navy);letter-spacing:-.5px}
.article h2{font-family:var(--serif);font-size:21px;margin:36px 0 14px;padding-bottom:8px;border-bottom:2px solid var(--border);font-weight:700;color:var(--navy)}
.article h3{font-family:var(--serif);font-size:17px;margin:24px 0 10px;font-weight:600;color:var(--navy-light)}
.article p{margin:10px 0}.article ul,.article ol{padding-left:24px;margin:10px 0}.article li{margin:4px 0}
.article a{color:var(--link);text-decoration:none;background:linear-gradient(to bottom,transparent 60%,var(--primary-glow) 60%);transition:background .2s}
.article a:hover{background:linear-gradient(to bottom,transparent 40%,rgba(122,98,150,.2) 40%)}
.article blockquote{background:var(--cream);border-left:4px solid var(--accent);padding:14px 20px;margin:16px 0;border-radius:0 8px 8px 0;font-style:italic;color:#5A4A3A;font-family:var(--serif)}
.article blockquote p{margin:0}.article blockquote a{background:none;color:var(--accent)}
.article table{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px}
.article th,.article td{border:1px solid var(--border);padding:8px 12px;text-align:left}
.article th{background:var(--bg2);font-weight:600;color:var(--navy)}
.article strong{font-weight:700}.article hr{border:none;border-top:1px solid var(--border);margin:32px 0}

.main.has-backlinks{display:grid;grid-template-columns:minmax(0,820px) 280px;gap:0 24px;max-width:1160px}
.main-content{min-width:0}
.backlinks-panel{grid-column:2;grid-row:1/-1;position:sticky;top:24px;max-height:calc(100vh - 48px);overflow-y:auto;padding:24px 0 24px 20px;border-left:1px solid var(--border);font-size:13px;align-self:start}
.backlinks-panel::-webkit-scrollbar{width:3px}.backlinks-panel::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.bl-panel-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.bl-panel-title{font-family:var(--serif);font-size:14px;font-weight:700;color:var(--navy);display:flex;align-items:center;gap:8px}
.bl-count{font-size:11px;background:var(--bg2);padding:1px 7px;border-radius:10px;color:var(--text2);font-weight:600}
.bl-group{margin-bottom:4px}
.bl-group-header{display:flex;align-items:center;gap:6px;background:none;border:none;cursor:pointer;padding:5px 0;width:100%;text-align:left;font-size:13px;font-family:var(--sans)}
.bl-group-header:hover{background:rgba(0,0,0,.02);border-radius:4px}
.bl-caret{display:inline-block;width:0;height:0;border:4px solid transparent;border-left:5px solid var(--text2);transition:transform .15s;flex-shrink:0}
.bl-group.open .bl-caret{transform:rotate(90deg)}
.bl-source-name{color:var(--navy);font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bl-mention-cat{font-size:10px;color:var(--text2);background:var(--bg2);padding:0 5px;border-radius:8px;flex-shrink:0;margin-left:4px}
.bl-snippets{display:none;padding:4px 0 4px 14px}
.bl-group.open .bl-snippets{display:block}
.bl-snippet{padding:6px 0;border-bottom:1px solid var(--border);line-height:1.6;color:var(--text2);font-size:12px}
.bl-snippet:last-child{border-bottom:none}
.bl-go-link{display:inline-block;font-size:11px;color:var(--link);text-decoration:none;padding:4px 0 2px;font-weight:600}

.hero-section{position:relative;padding:72px 48px 56px;max-width:900px;margin:0 auto}
.hero-eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--accent);margin-bottom:20px;opacity:0;animation:fadeUp .6s ease forwards}
.hero-eyebrow::before{content:'';width:24px;height:1px;background:var(--accent)}
.hero-title{font-family:var(--serif);font-size:clamp(32px,5vw,48px);font-weight:900;line-height:1.25;letter-spacing:-1px;color:var(--navy);margin-bottom:6px;opacity:0;animation:fadeUp .6s ease .1s forwards}
.hero-title .accent{color:var(--accent)}
.hero-sub{font-size:17px;color:var(--text2);line-height:1.8;margin-top:16px;max-width:640px;font-family:var(--serif);font-weight:400;opacity:0;animation:fadeUp .6s ease .2s forwards}
.hero-sub b{color:var(--navy);font-weight:700}

.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:0;max-width:900px;margin:0 auto 48px;padding:0 48px;border-top:1px solid var(--border);border-bottom:1px solid var(--border);opacity:0;animation:fadeUp .6s ease .3s forwards}
.stat-item{text-align:center;padding:28px 12px;position:relative;transition:background .3s;text-decoration:none;color:inherit}
.stat-item:not(:last-child)::after{content:'';position:absolute;right:0;top:20%;height:60%;width:1px;background:var(--border)}
.stat-item:hover{background:var(--primary-glow)}
.stat-num{font-family:var(--serif);font-size:42px;font-weight:900;color:var(--navy);line-height:1;margin-bottom:6px;letter-spacing:-2px}
.stat-label{font-size:13px;color:var(--text2);font-weight:500;letter-spacing:.5px}

.main-inner{max-width:900px;padding:0 48px 80px;margin:0 auto}
.nav-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-bottom:56px;opacity:0;animation:fadeUp .6s ease .4s forwards}
.nav-card{position:relative;padding:28px 20px 24px;background:var(--card);border:1px solid var(--border);border-radius:14px;text-decoration:none;transition:all .3s cubic-bezier(.4,0,.2,1);overflow:hidden;display:block;color:inherit}
.nav-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--accent);opacity:0;transition:opacity .3s}
.nav-card:hover{transform:translateY(-4px);box-shadow:0 12px 32px rgba(0,0,0,.08);border-color:var(--accent-light)}
.nav-card:hover::before{opacity:1}
.nav-card-icon{font-size:32px;margin-bottom:14px;display:block;line-height:1}
.nav-card-title{font-family:var(--serif);font-size:16px;font-weight:700;color:var(--navy);margin-bottom:4px}
.nav-card-sub{font-size:13px;color:var(--text2)}
.nav-card-arrow{position:absolute;bottom:20px;right:20px;font-size:18px;color:var(--border);transition:all .3s}
.nav-card:hover .nav-card-arrow{color:var(--accent);transform:translateX(4px)}

.section{margin-bottom:48px}
.section-header{display:flex;align-items:center;gap:12px;margin-bottom:20px}
.section-line{flex:1;height:1px;background:var(--border)}
.section-title{font-family:var(--serif);font-size:22px;font-weight:700;color:var(--navy);white-space:nowrap}
.section-count{font-size:12px;color:var(--accent);font-weight:600;background:var(--primary-glow);padding:3px 10px;border-radius:12px;white-space:nowrap}
.tag-cloud{display:flex;flex-wrap:wrap;gap:10px}
.tag{display:inline-flex;align-items:center;gap:6px;padding:8px 18px;background:var(--card);border:1px solid var(--border);border-radius:24px;font-size:14px;color:var(--text);text-decoration:none;transition:all .25s cubic-bezier(.4,0,.2,1);font-weight:500}
.tag:hover{border-color:var(--accent);color:var(--navy);box-shadow:0 4px 16px var(--primary-glow);transform:translateY(-2px)}
.tag-n{font-size:11px;font-weight:700;color:#fff;background:var(--accent);padding:2px 8px;border-radius:10px;min-width:20px;text-align:center}

.media-section{margin:48px 0;padding:40px;background:var(--card);border:1px solid var(--border);border-radius:20px}
.media-section h2{font-family:var(--serif);font-size:22px;font-weight:700;color:var(--navy);margin-bottom:24px;border:none;padding:0}
.media-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}
.media-card{border-radius:14px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);transition:all .3s;text-decoration:none;color:var(--text);display:block;border:1px solid var(--border);background:var(--card)}
.media-card:hover{transform:translateY(-4px);box-shadow:0 12px 32px rgba(0,0,0,.1);border-color:var(--accent-light)}
.media-card-thumb{position:relative;aspect-ratio:16/9;background:#000;overflow:hidden}
.media-card-thumb img{width:100%;height:100%;object-fit:cover}
.media-card-info{padding:14px 18px}
.media-card-info h3{font-family:var(--serif);font-size:16px;font-weight:700;color:var(--navy);margin-bottom:4px}
.media-card-info p{font-size:13px;color:var(--text2);margin:0}

.media-video-container{position:relative;width:100%;max-width:960px;margin:24px 0;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.1);background:#000}
.media-video-container video{width:100%;display:block}
.media-video-label{position:absolute;top:12px;left:12px;background:rgba(0,0,0,.6);color:#fff;padding:4px 12px;border-radius:8px;font-size:13px;z-index:2}
.media-infographic{float:right;width:280px;margin:0 0 16px 24px;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.08);cursor:pointer;transition:transform .2s}
.media-infographic:hover{transform:scale(1.02)}
.media-infographic img{width:100%;display:block}
.media-diagram{margin:24px 0;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.06)}
.media-diagram img{width:100%;display:block}
.media-diagram figcaption{padding:12px 16px;font-size:14px;color:var(--text2);background:var(--bg2)}

.gold-divider{display:flex;align-items:center;gap:16px;margin:56px 0}
.gold-divider::before,.gold-divider::after{content:'';flex:1;height:1px;background:linear-gradient(to right,transparent,var(--border),transparent)}
.gold-divider-diamond{width:8px;height:8px;background:var(--accent);transform:rotate(45deg);flex-shrink:0}

.footer-promo{position:relative;overflow:hidden;padding:40px;background:var(--navy);border-radius:20px;color:#fff;display:flex;gap:40px;align-items:center;margin-top:56px}
.footer-promo::before{content:'';position:absolute;top:-50%;right:-20%;width:400px;height:400px;border-radius:50%;background:radial-gradient(circle,rgba(122,98,150,.2),transparent 70%)}
.promo-story{flex:1;position:relative;z-index:1;min-width:0}
.promo-story h3{font-family:var(--serif);font-size:20px;font-weight:700;margin-bottom:12px;color:var(--accent-light)}
.promo-story p{font-size:14px;color:rgba(255,255,255,.75);line-height:1.8;margin:8px 0}

@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.section{opacity:0;animation:fadeUp .5s ease forwards}
.section:nth-child(1){animation-delay:.45s}.section:nth-child(2){animation-delay:.55s}
.section:nth-child(3){animation-delay:.65s}.section:nth-child(4){animation-delay:.75s}

@media(max-width:1024px){.main.has-backlinks{display:block}.backlinks-panel{position:static;max-height:none;overflow-y:visible;border-left:none;border-top:1px solid var(--border);padding:24px 16px;margin-top:24px;max-width:820px}}
@media(max-width:768px){.sidebar{transform:translateX(-100%);transition:transform .3s}.sidebar.open{transform:translateX(0)}.hamburger{display:block}.main{margin-left:0;max-width:100%}.article{padding:48px 16px 60px}.hero-section{padding:44px 20px 20px}.hero-title{font-size:26px}.hero-sub{font-size:14px;line-height:1.6;margin-top:10px}.stats-row{padding:0 16px;margin:0 0 20px;grid-template-columns:repeat(2,1fr)}.stat-item{padding:16px 4px}.stat-num{font-size:28px}.stat-label{font-size:11px}.main-inner{padding:0 20px 60px}.nav-cards{grid-template-columns:1fr 1fr}.media-grid{grid-template-columns:1fr}.media-infographic{float:none;width:100%;margin:16px 0}}
"""

JS = """
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.nav-group-title').forEach(function(el){el.addEventListener('click',function(){this.parentElement.classList.toggle('open')})});
  document.querySelectorAll('.bl-group-header').forEach(function(h){h.addEventListener('click',function(){this.closest('.bl-group').classList.toggle('open')})});
  document.querySelector('.hamburger')?.addEventListener('click',function(){document.querySelector('.sidebar').classList.toggle('open')});
});
"""


def build():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(OUT / "concepts", exist_ok=True)
    os.makedirs(OUT / "media", exist_ok=True)

    files = collect_files()
    lm = build_link_map(files)
    bl = build_backlinks(files, lm)

    # Collect all tags
    all_tags = {}
    for f in files:
        for t in f["fm"].get("tags", []):
            all_tags[t] = all_tags.get(t, 0) + 1

    # Sidebar HTML
    nav_links = []
    nav_links.append(f'<a href="{BASE_PATH}/index.html" class="nav-link nav-home">首页</a>')
    for cat, label in CATEGORY_LABELS.items():
        cat_files = [f for f in files if f["category"] == cat]
        if not cat_files:
            continue
        nav_links.append(f'<div class="nav-group open"><div class="nav-group-title"><span class="caret"></span>{label} <span class="badge">{len(cat_files)}</span></div><div class="nav-group-items">')
        for f in cat_files:
            nav_links.append(f'<a href="{BASE_PATH}/{cat}/{f["stem"]}.html" class="nav-link">{f["stem"]}</a>')
        nav_links.append('</div></div>')
    sidebar_nav = "\n".join(nav_links)

    # --- Homepage ---
    stats_html = f"""
<div class="stats-row">
  <div class="stat-item"><div class="stat-num">{len(files)}</div><div class="stat-label">概念卡片</div></div>
  <div class="stat-item"><div class="stat-num">{sum(len(f['fm'].get('tags',[])) for f in files)}</div><div class="stat-label">标签总数</div></div>
  <div class="stat-item"><div class="stat-num">{sum(len(v) for v in bl.values())}</div><div class="stat-label">内部链接</div></div>
  <div class="stat-item"><div class="stat-num">{len(all_tags)}</div><div class="stat-label">分类标签</div></div>
</div>"""

    # Nav cards
    nav_cards = []
    for f in files:
        media = f["fm"].get("media", {})
        icon = "🎬" if media.get("video") else "📖"
        tags = ", ".join(f["fm"].get("tags", [])[:3])
        nav_cards.append(f"""<a class="nav-card" href="{BASE_PATH}/{f['category']}/{f['stem']}.html">
  <span class="nav-card-icon">{icon}</span>
  <div class="nav-card-title">{f['stem']}</div>
  <div class="nav-card-sub">{tags}</div>
  <span class="nav-card-arrow">→</span>
</a>""")

    # Media section
    media_cards = []
    for f in files:
        media = f["fm"].get("media", {})
        if media.get("diagram") and (OUT / "media" / os.path.basename(media["diagram"])).exists():
            media_cards.append(f"""<a class="media-card" href="{BASE_PATH}/{f['category']}/{f['stem']}.html">
  <div class="media-card-thumb"><img src="{BASE_PATH}/media/{os.path.basename(media['diagram'])}" alt="{f['stem']}" loading="lazy"></div>
  <div class="media-card-info"><h3>{f['stem']}</h3><p>查看概念解析</p></div>
</a>""")
    media_section = ""
    if media_cards:
        media_section = f"""<div class="media-section">
  <h2>概念图谱</h2>
  <div class="media-grid">{"".join(media_cards)}</div>
</div>"""

    # Tag cloud
    tag_items = []
    for t, n in sorted(all_tags.items(), key=lambda x: -x[1])[:12]:
        tag_items.append(f'<a class="tag" href="{BASE_PATH}/concepts/{files[0]["stem"]}.html"><span class="tag-n">{n}</span>{t}</a>')

    homepage = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{SITE_TITLE}</title><style>{CSS}</style></head><body>
<button class="hamburger">☰</button>
<div class="layout"><nav class="sidebar"><div class="sidebar-header"><a href="{BASE_PATH}/index.html" class="logo">{SITE_LOGO} {SITE_TITLE}</a></div><div class="sidebar-nav">{sidebar_nav}</div></nav>
<main class="main">
<div class="hero-section">
  <div class="hero-eyebrow">哲学 · 知识图谱</div>
  <h1 class="hero-title">爱<span class="accent">智慧</span>的旅程</h1>
  <p class="hero-sub">从古希腊到东方，从本体论到伦理学，探索<b>人类思想的根基</b>。涵盖 {len(files)} 个核心概念，构建完整的哲学知识网络。</p>
</div>
{stats_html}
<div class="main-inner">
  <div class="section"><div class="section-header"><span class="section-title">核心概念</span><span class="section-line"></span><span class="section-count">{len(files)} 个</span></div><div class="nav-cards">{"".join(nav_cards)}</div></div>
  <div class="gold-divider"><div class="gold-divider-diamond"></div></div>
  <div class="section"><div class="section-header"><span class="section-title">标签云</span><span class="section-line"></span></div><div class="tag-cloud">{"".join(tag_items)}</div></div>
  {media_section}
  <div class="footer-promo"><div class="promo-story"><h3>关于本站</h3><p>本知识图谱由滔哥构建，基于中西方哲学经典文献，涵盖从古希腊三贤到中国诸子百家的核心思想。每个概念卡片都包含详细解释、相互引用和视觉配图。</p></div></div>
</div>
</main></div><script>{JS}</script></body></html>"""

    (OUT / "index.html").write_text(homepage, encoding="utf-8")

    # --- Article pages ---
    for f in files:
        title = f["fm"].get("title", f["stem"])
        tags = f["fm"].get("tags", [])
        cat = f["category"]
        media = f["fm"].get("media", {})
        backlinks = bl.get(f["stem"], [])

        html_body = md_to_html(f["body"], lm)

        # Type badge
        type_label = CATEGORY_LABELS.get(cat, cat)
        badge = f'<span class="type-badge type-{type_label}">{type_label}</span>'
        tags_html = " ".join(f'<span class="type-badge" style="background:var(--text2)">{t}</span>' for t in tags)

        # Video embed
        video_html = ""
        if media.get("video") and (OUT / "media" / os.path.basename(media["video"])).exists():
            video_html = f'<div class="media-video-container"><span class="media-video-label">视频讲解</span><video controls preload="metadata"><source src="{BASE_PATH}/media/{os.path.basename(media["video"])}" type="video/mp4"></video></div>'

        # Infographic (float right)
        info_html = ""
        if media.get("infographic") and (OUT / "media" / os.path.basename(media["infographic"])).exists():
            info_html = f'<figure class="media-infographic"><img src="{BASE_PATH}/media/{os.path.basename(media["infographic"])}" alt="{title} 信息图" loading="lazy"></figure>'

        # Diagram (inline)
        diag_html = ""
        if media.get("diagram") and (OUT / "media" / os.path.basename(media["diagram"])).exists():
            diag_html = f'<figure class="media-diagram"><img src="{BASE_PATH}/media/{os.path.basename(media["diagram"])}" alt="{title} 概念图" loading="lazy"><figcaption>{title} 概念解析</figcaption></figure>'

        # Inject media into body
        enhanced_body = video_html + html_body
        if info_html:
            enhanced_body = enhanced_body.replace("</p>", f"</p>{info_html}", 1)
        if diag_html:
            if "<h2" in enhanced_body:
                enhanced_body = re.sub(r"(<h2)", diag_html + r"\1", enhanced_body, count=1)
            else:
                enhanced_body += diag_html

        # Backlinks panel
        bl_html = ""
        if backlinks:
            bl_groups = []
            for bl_item in backlinks:
                bl_groups.append(f"""<div class="bl-group">
  <button class="bl-group-header"><span class="bl-caret"></span><span class="bl-source-name">{bl_item['title']}</span><span class="bl-mention-cat">{CATEGORY_LABELS.get(bl_item['category'], bl_item['category'])}</span></button>
  <div class="bl-snippets"><div class="bl-snippet">{bl_item['excerpt']}</div><a class="bl-go-link" href="{BASE_PATH}/{bl_item['category']}/{bl_item['stem']}.html">前往查看 →</a></div>
</div>""")
            bl_html = f"""<aside class="backlinks-panel">
  <div class="bl-panel-header"><span class="bl-panel-title">🔗 链接到本页</span><span class="bl-count">{len(backlinks)}</span></div>
  {"".join(bl_groups)}
</aside>"""

        has_bl = "has-backlinks" if backlinks else ""

        page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · {SITE_TITLE}</title><style>{CSS}</style></head><body>
<button class="hamburger">☰</button>
<div class="layout"><nav class="sidebar"><div class="sidebar-header"><a href="{BASE_PATH}/index.html" class="logo">{SITE_LOGO} {SITE_TITLE}</a></div><div class="sidebar-nav">{sidebar_nav}</div></nav>
<main class="main {has_bl}">
<div class="main-content"><div class="article">
  <div class="meta">{badge} {tags_html}</div>
  <h1>{title}</h1>
  {enhanced_body}
</div></div>
{bl_html}
</main></div><script>{JS}</script></body></html>"""

        (OUT / cat / f"{f['stem']}.html").write_text(page, encoding="utf-8")

    # Copy media
    media_src = VAULT / "media"
    if media_src.is_dir():
        for mf in media_src.iterdir():
            if mf.suffix in (".png", ".jpg", ".mp4", ".gif"):
                shutil.copy2(mf, OUT / "media" / mf.name)

    print(f"Built {len(files)} pages → {OUT}/")


if __name__ == "__main__":
    import shutil
    build()
