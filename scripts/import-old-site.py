"""One-time import: turns the mirrored WordPress pages (reference/old-site, on the
old-site-snapshot branch) into clean static pages under src/. Run from the repo root:
    python3 scripts/import-old-site.py <path-to-reference-dir>
"""
import hashlib, json, os, re, shutil, sys
from pathlib import Path
from urllib.parse import unquote

REF = Path(sys.argv[1]).resolve()
MIRROR = REF / "old-site"
SITE = MIRROR / "moniquemartin.net"
OUT = Path("src").resolve()

PAGES = {"index.html": "index.html",
         "index.html?page_id=1386.html": "mintyfresh/index.html",
         "index.html?page_id=7126.html": "bio/index.html"}
PAGE_LINKS = {"1386": "/mintyfresh/", "7126": "/bio/"}

# ---------- images: pick the largest Jetpack (i0.wp.com) variant of each upload ----------
best = {}
for f in (MIRROR / "i0.wp.com/moniquemartin.net/wp-content/uploads").rglob("*"):
    if f.is_file():
        rel = str(f.relative_to(MIRROR / "i0.wp.com/moniquemartin.net")).split("?")[0]
        if rel not in best or f.stat().st_size > best[rel].stat().st_size:
            best[rel] = f

def copy(src: Path, rel: str) -> str:
    dst = OUT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        if src.suffix == ".css" or rel.endswith(".css"):
            dst.write_text(fix_css(src.read_text(errors="replace"), src.parent))
        else:
            shutil.copyfile(src, dst)
    return "/" + rel

def resolve(url: str, base: Path) -> str:
    """Map a URL found in a mirrored file (relative to `base`) to its new site URL."""
    u = url.strip().replace("&amp;", "&")
    if not u or u.startswith(("data:", "#", "mailto:", "tel:", "javascript:")):
        return url
    m = re.match(r"https?://(?:www\.)?moniquemartin\.net/?(\?page_id=(\d+))?$", u)
    if m:
        return PAGE_LINKS.get(m.group(2), "/") if m.group(2) else "/"
    if re.match(r"https?://i\d\.wp\.com/moniquemartin\.net/", u):
        u = os.path.relpath(MIRROR / "i0.wp.com" / u.split("wp.com/", 1)[1], base)
    if u.startswith(("http://", "https://", "//")):
        return url
    frag = ""
    if "#" in u:
        u, frag = u.split("#", 1)
        frag = "#" + frag
    if u == "index.html":
        return "/" + frag
    m = re.match(r"index\.html\?page_id=(\d+)\.html$", u)
    if m:
        return PAGE_LINKS.get(m.group(1), "/") + frag
    p = (base / unquote(u)).resolve()
    try:
        r = p.relative_to(MIRROR)
    except ValueError:
        return url
    host, _, rest = str(r).partition("/")
    clean = rest.split("?")[0]
    if host.startswith("i") and host.endswith("wp.com"):
        key = clean.split("/", 1)[1]           # drop leading moniquemartin.net/
        if key in best:
            return copy(best[key], key)
        print("missing image", key); return url
    if not p.exists():
        print("missing file", r); return url
    if host == "moniquemartin.net":
        return copy(p, clean) + frag
    if host == "fonts.gstatic.com":
        return copy(p, "fonts/" + clean)
    if host == "fonts.googleapis.com":
        return copy(p, "fonts/" + hashlib.md5(rest.encode()).hexdigest()[:10] + ".css")
    return url

def fix_css(css: str, base: Path) -> str:
    def rep(m):
        q, u = m.group(1), m.group(2)
        return f"url({q}{resolve(u, base)}{q})"
    return re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", rep, css)

DROP_SCRIPT_SRC = re.compile(r"give|custom-twitter-feeds|stats\.wp\.com|wp-includes/js/dist/(?!hooks|i18n)|turnstile|jetpack|wpforms|monsterinsights|wp-emoji")
DROP_INLINE = re.compile(r"give_global_vars|var ctf =|wp\.apiFetch|wp\.data|moment\.updateLocale|wp\.date\.setSettings|preferencesPersistence|_stq|emoji|gtag|__gaTracker|monsterinsights|turnstile|wpforms|givewp|window\.Give", re.I)
DROP_LINK = re.compile(r"rel=[\"'](?:alternate|EditURI|shortlink|https://api\.w\.org/|profile|pingback|dns-prefetch|preconnect|canonical)[\"']", re.I)
DROP_CSS = re.compile(r"plugins/give|custom-twitter-feeds|jetpack|wpforms")

def clean_page(html: str, out_rel: str) -> str:
    # scripts
    def script(m):
        tag, body = m.group(1), m.group(2)
        src = re.search(r"src=[\"']([^\"']+)", tag)
        if src:
            return "" if DROP_SCRIPT_SRC.search(unquote(src.group(1))) else m.group(0)
        if 'type="application/json"' in tag and "emoji" in body: return ""
        return "" if DROP_INLINE.search(body) else m.group(0)
    html = re.sub(r"(<script\b[^>]*>)(.*?)</script>", script, html, flags=re.S)
    html = re.sub(r"<link\b[^>]*>", lambda m: "" if DROP_LINK.search(m.group(0)) or (
        "stylesheet" in m.group(0) and DROP_CSS.search(m.group(0))) else m.group(0), html)
    html = re.sub(r"<meta name=[\"']generator[\"'][^>]*>\s*", "", html)
    # remove WordPress nonces from inline config
    html = re.sub(r'"(restNonce|nonce|checkout_nonce)":"[0-9a-f]+"', r'"\1":""', html)
    # inline config (Elementor, theme) uses absolute URLs to the old server
    html = html.replace("https:\\/\\/moniquemartin.net\\/wp-content", "\\/wp-content")
    # srcset lists were mangled by the mirror (commas inside image URLs); one full-size image each is enough
    html = re.sub(r"\s(?:data-)?srcset=([\"']).*?\1", "", html, flags=re.S)
    html = re.sub(r"\ssizes=([\"']).*?\1", "", html)
    # URLs in attributes
    def attr(m):
        name, q, val = m.group(1), m.group(2), m.group(3)
        if name.endswith("srcset"):
            parts = [p.strip().rsplit(" ", 1) for p in val.split(",") if p.strip()]
            return f'{name}={q}{", ".join(" ".join([resolve(p[0], SITE)] + p[1:]) for p in parts)}{q}'
        return f"{name}={q}{resolve(val, SITE)}{q}"
    html = re.sub(r"\b(src|href|srcset|data-src|data-srcset|data-bg|poster)=([\"'])(.*?)\2", attr, html)
    html = re.sub(r'content="(https://i\d\.wp\.com/[^"]+)"', lambda m: f'content="https://moniquemartin.net{resolve(m.group(1), SITE)}"', html)
    html = fix_css(html, SITE)  # inline style="" and <style> blocks
    html = re.sub(r"(href=[\"'])/index\.html", r'\1/', html)
    # canonical + old ?page_id= links keep working
    canon = "https://moniquemartin.net/" + out_rel.replace("index.html", "")
    head_extra = f'<link rel="canonical" href="{canon}" />\n'
    if out_rel == "index.html":
        head_extra += ('<script>(function(){var m=location.search.match(/page_id=(\\d+)/),t={"1386":"/mintyfresh/","7126":"/bio/"};'
                       'if(m&&t[m[1]])location.replace(t[m[1]]);})();</script>\n')
    html = html.replace("</head>", head_extra + "</head>", 1)
    return html

for src_name, out_rel in PAGES.items():
    html = (SITE / src_name).read_text(errors="replace")
    out = OUT / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(clean_page(html, out_rel))
    print("wrote", out_rel)

chunks = REF / "elementor-4.4.0/chunks"
if chunks.exists():
    shutil.copytree(chunks, OUT / "wp-content/plugins/elementor/assets/js/chunks", dirs_exist_ok=True)
else:
    print("Elementor chunks not found in", chunks)

left = [str(l) for l in OUT.rglob("*.html") if re.search(r"i\d\.wp\.com|=[\"']\.\./", l.read_text())]
print("pages still pointing at old hosts or ../ paths:", left)
