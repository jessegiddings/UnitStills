#!/usr/bin/env python3
"""Build jessegiddings.com into docs/.

Reads content/site.json and the originals in photos/<folder>/, writes
web-sized WebP images to docs/img/ and renders docs/index.html from
templates/index.html.

Adding or swapping a production never needs a code change: drop the
files into photos/<folder>/ and list the folder in content/site.json.
Images in a folder appear in filename order unless "order" names some
to go first; the first image is the production's cover.

    pip install Pillow
    python3 build.py
"""
import html
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
PHOTOS = ROOT / "photos"
OUT = ROOT / "docs"
IMG_OUT = OUT / "img"
WIDTHS = (480, 960, 1600, 2400)
QUALITY = 80
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

esc = html.escape


def slug(name):
    return Path(name).stem.replace(" ", "-")


def render_image(folder, file):
    """Write resized WebP copies of one original and return its metadata."""
    src = PHOTOS / folder / file
    if not src.exists():
        raise SystemExit(f"Missing image: {src}")
    dest_dir = IMG_OUT / folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        sources = []
        for target in WIDTHS:
            if target > w and sources:
                break
            tw = min(target, w)
            out = dest_dir / f"{slug(file)}-{tw}.webp"
            if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
                im.resize((tw, round(h * tw / w)), Image.LANCZOS).save(
                    out, "WEBP", quality=QUALITY, method=6)
            sources.append((f"img/{folder}/{out.name}", tw))
    return {"w": w, "h": h, "sources": sources}


def folder_files(folder, order=()):
    files = sorted(p.name for p in (PHOTOS / folder).iterdir()
                   if p.suffix.lower() in IMAGE_EXTS)
    first = [f for f in order if f in files]
    return first + [f for f in files if f not in first]


def img_tag(meta, alt, sizes, eager=False, cls=""):
    srcset = ", ".join(f"{src} {w}w" for src, w in meta["sources"])
    default = meta["sources"][min(1, len(meta["sources"]) - 1)][0]
    loading = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    cls = f' class="{cls}"' if cls else ""
    return (f'<img{cls} src="{default}" srcset="{srcset}" sizes="{sizes}" '
            f'width="{meta["w"]}" height="{meta["h"]}" alt="{esc(alt)}" {loading}>')


def lightbox_attrs(meta, group, alt, caption):
    """Data the lightbox reads: the largest file plus a mid size for phones."""
    big = meta["sources"][-1][0]
    mid = meta["sources"][min(2, len(meta["sources"]) - 1)][0]
    return (f'href="{big}" data-mid="{mid}" data-group="{esc(group)}" '
            f'data-alt="{esc(alt)}" data-caption="{esc(caption)}"')


def join(*parts):
    return " · ".join(p for p in parts if p)


def meta_line(*parts):
    return esc(join(*parts))


def card(folder, files, title, sub, alt, captions=None, alts=None, cover_class=""):
    """A production cover; the rest of the folder rides along for the lightbox."""
    captions, alts = captions or {}, alts or {}
    links = []
    for i, f in enumerate(files):
        meta = render_image(folder, f)
        a = alts.get(f) or alt
        cap = captions.get(f) or join(title, sub)
        attrs = lightbox_attrs(meta, folder, a, cap)
        if i == 0:
            cover = img_tag(meta, a, "(max-width: 640px) 100vw, (max-width: 1100px) 50vw, 33vw",
                            cls=cover_class)
            count = f'<span class="count">{len(files)} images</span>' if len(files) > 1 else ""
            links.append(
                f'<a class="card" {attrs}>{cover}<span class="card-info">'
                f'<span class="card-title">{esc(title)}</span>'
                f'<span class="card-sub">{esc(sub)}</span>{count}</span></a>')
        else:
            links.append(f'<a class="more" hidden {attrs}></a>')
    return f'<li>{"".join(links)}</li>'


def tile(meta, group, alt, caption=""):
    """A tile in a justified row; its flex share follows its aspect ratio."""
    ratio = meta["w"] / meta["h"]
    cap = f"<figcaption>{esc(caption)}</figcaption>" if caption else ""
    return (f'<figure class="tile" style="--r:{ratio:.4f}">'
            f'<a {lightbox_attrs(meta, group, alt, caption or alt)}>'
            f'{img_tag(meta, alt, "(max-width: 640px) 100vw, 50vw")}</a>{cap}</figure>')


def embed(url):
    yt = re.search(r"(?:youtu\.be/|v=|/shorts/|/embed/)([\w-]{11})", url)
    if yt:
        vid = yt.group(1)
        vertical = " vertical" if "/shorts/" in url else ""
        return (f'<div class="embed yt{vertical}"><iframe loading="lazy" '
                f'src="https://www.youtube-nocookie.com/embed/{vid}" title="YouTube video" '
                f'allow="encrypted-media; picture-in-picture" allowfullscreen></iframe></div>')
    if "instagram.com" in url:
        return (f'<div class="embed ig"><blockquote class="instagram-media" '
                f'data-instgrm-permalink="{esc(url)}" data-instgrm-version="14">'
                f'<a href="{esc(url)}" rel="noopener">View on Instagram</a></blockquote></div>')
    raise SystemExit(f"Unsupported embed URL: {url}")


def build():
    site = json.loads((ROOT / "content" / "site.json").read_text())
    if IMG_OUT.exists():
        # Drop resized copies whose originals were removed.
        keep = {(p.parent.name, slug(p.name)) for p in PHOTOS.glob("*/*")}
        for f in IMG_OUT.glob("*/*.webp"):
            if (f.parent.name, f.stem.rsplit("-", 1)[0]) not in keep:
                f.unlink()

    hero = site["hero"]
    hero_meta = render_image(hero["folder"], hero["file"])
    hero_img = img_tag(hero_meta, hero["caption"], "100vw", eager=True)

    strip = "".join(f"<li>{esc(n)}</li>" for n in site["credits_strip"])

    cards = []
    for p in site["productions"]:
        files = folder_files(p["folder"], p.get("order", []))
        title = p["title"] + (f" ({p['detail']})" if p.get("detail") else "")
        sub = join(p.get("network"), p.get("year"), p.get("location"))
        cards.append(card(p["folder"], files, p["title"], sub,
                          join(title, p.get("network"), p.get("year")), p.get("captions")))
    pk = site["portraits"]
    cards.append(card(pk["folder"], folder_files(pk["folder"], pk.get("order", [])),
                      pk["title"], "Portrait sessions and key art", pk["title"],
                      pk.get("captions"), cover_class="top"))

    mw = site.get("more_work")
    more = ""
    if mw:
        small = []
        for p in mw["productions"]:
            files = folder_files(p["folder"], p.get("order", []))[:p.get("limit")]
            sub = join(p.get("network"), p.get("year"))
            small.append(card(p["folder"], files, p["title"], sub,
                              join(p["title"], p.get("network"), p.get("year"))))
        more = (f'<div class="more-work"><h3 class="label">{esc(mw["title"])}</h3>'
                f'<p class="note">{esc(mw["note"])}</p>'
                f'<ul class="cards small">{"".join(small)}</ul></div>')

    bts = site["bts"]
    bts_tiles = "".join(tile(render_image(i["folder"], i["file"]), "bts", i["caption"], i["caption"])
                        for i in bts["images"])
    embeds = [embed(u) for u in bts.get("embeds", [])]
    bts_embeds = f'<div class="embeds">{"".join(embeds)}</div>' if embeds else ""
    ig_script = ('<script async src="https://www.instagram.com/embed.js"></script>'
                 if any("instagram.com" in u for u in bts.get("embeds", [])) else "")
    bts_recent = "".join(f"<li>{esc(r)}</li>" for r in bts["recent"])

    nt = site["network_tests"]
    nt_tiles = "".join(tile(render_image(i["folder"], i["file"]), "tests",
                            i.get("caption", "Network test"), i.get("caption", ""))
                       for i in nt["images"])
    nt_gallery = f'<div class="rows">{nt_tiles}</div>' if nt_tiles else ""

    a = site["assignment"]
    items = a["images"] or [{"file": f} for f in folder_files(a["folder"])]
    assignment = '<div class="rows">' + "".join(
        tile(render_image(a["folder"], i["file"]), "assignment",
             i.get("alt") or i.get("caption") or "On assignment", i.get("caption", ""))
        for i in items) + "</div>"

    credits = []
    for group in site["credits"]:
        rows = "".join(
            f'<li><span class="show">{esc(s)}</span>'
            f'<span class="meta">{meta_line(season, year)}</span>'
            f'<span class="role">{esc(role)}</span></li>'
            for s, season, year, role in group["shows"])
        credits.append(f'<section><h3 class="label">{esc(group["network"])}</h3><ul>{rows}</ul></section>')

    tpl = (ROOT / "templates" / "index.html").read_text()
    values = {
        "NAME": esc(site["name"]),
        "TAGLINE": esc(site["tagline"]),
        "DESCRIPTION": esc(site["description"]),
        "HERO_IMG": hero_img,
        "HERO_CAPTION": esc(hero["caption"]),
        "OG_IMAGE": hero_meta["sources"][2][0],
        "CREDITS_STRIP": strip,
        "WORK_INTRO": esc(site["work_intro"]),
        "CARDS": "".join(cards),
        "MORE_WORK": more,
        "BTS_INTRO": esc(bts["intro"]),
        "BTS_EMBEDS": bts_embeds,
        "BTS_TILES": bts_tiles,
        "BTS_RECENT": bts_recent,
        "IG_SCRIPT": ig_script,
        "NT_TEXT": esc(nt["text"]),
        "NT_GALLERY": nt_gallery,
        "ASSIGNMENT_INTRO": esc(a["intro"]),
        "ASSIGNMENT": assignment,
        "CREDITS": "".join(credits),
        "ABOUT": esc(site["about"]),
        "CONTACT_HEADING": esc(site["contact"]["heading"]),
        "CONTACT_NOTE": esc(site["contact"]["note"]),
        "EMAIL": esc(site["email"]),
        "INSTAGRAM": esc(site["instagram"]),
    }
    for key, val in values.items():
        tpl = tpl.replace("{{" + key + "}}", val)
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(tpl)
    for asset in ("styles.css", "site.js"):
        shutil.copy(ROOT / "templates" / asset, OUT / asset)
    (OUT / ".nojekyll").touch()
    print(f"Built {OUT / 'index.html'}")


if __name__ == "__main__":
    build()
