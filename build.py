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


def stills_tile(folder, files, title, sub, alt, ar="4 / 5"):
    """A cover tile in the clip grid that opens the production's photos in the lightbox."""
    links = []
    n = len(files)
    for i, f in enumerate(files):
        meta = render_image(folder, f)
        attrs = lightbox_attrs(meta, folder, alt, join(title, sub))
        if i == 0:
            cover = img_tag(meta, "", "(max-width: 640px) 100vw, 460px")
            links.append(
                f'<a class="clip-play stills" {attrs} aria-label="View {n} production stills from {esc(title)}">'
                f'{cover}<span class="clip-platform" aria-hidden="true">Stills</span></a>')
        else:
            links.append(f'<a hidden {attrs}></a>')
    label = f"{n} production stills" if n > 1 else "Production still"
    return f'<li class="clip" style="--ar: {ar}">{"".join(links)}<p class="clip-credit">{label}</p></li>'


def tile(meta, group, alt, caption=""):
    """A tile in a justified row; its flex share follows its aspect ratio."""
    ratio = meta["w"] / meta["h"]
    cap = f"<figcaption>{esc(caption)}</figcaption>" if caption else ""
    return (f'<figure class="tile" style="--r:{ratio:.4f}">'
            f'<a {lightbox_attrs(meta, group, alt, caption or alt)}>'
            f'{img_tag(meta, alt, "(max-width: 640px) 100vw, 50vw")}</a>{cap}</figure>')


# Video clips. Nothing from the platform loads until a visitor presses play;
# site.js then swaps in the official embed inside the lightbox.

PLATFORM_NAMES = {"instagram": "Instagram", "youtube": "YouTube", "facebook": "Facebook", "x": "X"}
FORMATS = {"9:16": "9 / 16", "4:5": "4 / 5", "1:1": "1 / 1", "16:9": "16 / 9"}


def clip_source(url, platform=None):
    """Return (platform, canonical URL, embed id, default format) for a clip URL."""
    url = url.strip()
    host = re.sub(r"^www\.|^m\.", "", re.match(r"https?://([^/]+)", url).group(1).lower())
    platform = platform or {
        "instagram.com": "instagram", "youtube.com": "youtube", "youtu.be": "youtube",
        "facebook.com": "facebook", "fb.watch": "facebook", "x.com": "x", "twitter.com": "x",
    }.get(host)
    if platform == "instagram":
        # Profile-style links (/user/reel/CODE/) and tracking params confuse embed.js.
        m = re.search(r"/(p|reel|reels|tv)/([\w-]+)", url)
        if not m:
            raise SystemExit(f"Can't read Instagram post code from {url}")
        kind = "reel" if m.group(1) in ("reel", "reels") else m.group(1)
        return platform, f"https://www.instagram.com/{kind}/{m.group(2)}/", m.group(2), \
            "9:16" if kind in ("reel", "tv") else "4:5"
    if platform == "youtube":
        m = re.search(r"(?:youtu\.be/|v=|/shorts/|/embed/|/live/)([\w-]{11})", url)
        if not m:
            raise SystemExit(f"Can't read YouTube video id from {url}")
        return platform, url, m.group(1), "9:16" if "/shorts/" in url else "16:9"
    if platform in ("facebook", "x"):
        return platform, url.split("?")[0] if platform == "x" else url, "", \
            "9:16" if "/reel" in url else "16:9"
    raise SystemExit(f"Unsupported clip platform for {url}")


def load_clips():
    path = ROOT / "content" / "clips.json"
    if not path.exists():
        return {}, {}
    data = json.loads(path.read_text())
    by_production = {}
    for c in data.get("clips", []):
        platform, url, embed_id, fmt = clip_source(c["url"], c.get("platform"))
        c = {**c, "platform": platform, "url": url, "embed_id": embed_id,
             "format": c.get("format") or fmt}
        by_production.setdefault(c["production"], []).append(c)

    def season_no(c):
        m = re.search(r"\d+", c.get("season", ""))
        return int(m.group()) if m else 0

    for clips in by_production.values():
        clips.sort(key=lambda c: (c.get("posted", ""), c.get("year", ""), season_no(c)), reverse=True)
    return by_production, data.get("productions", {})


def clip_tile(c, group):
    name = PLATFORM_NAMES[c["platform"]]
    label_bits = [c.get("network"), "social clip for", c["production"]]
    label = "Play " + " ".join(b for b in label_bits if b) + (f', {c["season"]}' if c.get("season") else "")
    thumb_path = PHOTOS / c.get("thumbnail", "")
    if c.get("thumbnail") and thumb_path.is_file():
        meta = render_image(thumb_path.parent.relative_to(PHOTOS).as_posix(), thumb_path.name)
        thumb = img_tag(meta, "", "(max-width: 640px) 100vw, (max-width: 1100px) 50vw, 33vw")
    else:
        if c.get("thumbnail"):
            print(f"  note: no thumbnail yet at photos/{c['thumbnail']}; showing a placeholder")
        thumb = (f'<span class="clip-ph" aria-hidden="true"><span>{esc(c["production"])}</span>'
                 f'<span>{esc(join(c.get("season"), c.get("year")))}</span></span>')
    caption = join(c["production"], c.get("season"), c.get("year"))
    return (
        f'<li class="clip" style="--ar: {FORMATS.get(c["format"], "9 / 16")}">'
        f'<button type="button" class="clip-play" aria-label="{esc(label)}" '
        f'data-group="{esc(group)}" data-platform="{c["platform"]}" data-platform-name="{name}" '
        f'data-url="{esc(c["url"])}" data-embed-id="{esc(c["embed_id"])}" '
        f'data-format="{esc(c["format"])}" data-caption="{esc(caption)}" data-credit="{esc(c.get("credit", ""))}">'
        f'{thumb}<span class="play" aria-hidden="true"></span>'
        f'<span class="clip-platform" aria-hidden="true">{name}</span></button>'
        f'<p class="clip-credit">{esc(c.get("credit", ""))}</p></li>')


def clip_card(title, sub, intro, clips, photos=""):
    """A full-width production card with its clip grid (and stills, if any)."""
    group = "clips-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    tiles = "".join(clip_tile(c, group) for c in clips)
    intro = f'<p class="feature-intro">{esc(intro)}</p>' if intro else ""
    return (f'<li class="feature"><header><h3>{esc(title)}</h3>'
            f'<p class="card-sub">{esc(sub)}</p></header>{intro}'
            f'<ul class="clip-grid">{photos}{tiles}</ul></li>')


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

    clips_by_production, clip_meta = load_clips()
    cards = []
    listed = set()
    for p in site["productions"]:
        listed.add(p["title"])
        files = folder_files(p["folder"], p.get("order", [])) if p.get("folder") else []
        title = p["title"] + (f" ({p['detail']})" if p.get("detail") else "")
        sub = join(p.get("network"), p.get("year"), p.get("location"))
        alt = join(title, p.get("network"), p.get("year"))
        clips = clips_by_production.get(p["title"])
        if clips:
            intro = p.get("clips_intro") or clip_meta.get(p["title"], {}).get("intro", "")
            cards.append(clip_card(p["title"], sub, intro, clips,
                                   stills_tile(p["folder"], files, p["title"], sub, alt,
                                               FORMATS.get(clips[0]["format"], "4 / 5")) if files else ""))
        elif files:
            cards.append(card(p["folder"], files, p["title"], sub, alt, p.get("captions")))
    for name, clips in clips_by_production.items():
        if name not in listed:  # clip-only production that isn't in site.json yet
            m = clip_meta.get(name, {})
            cards.append(clip_card(name, join(m.get("network") or clips[0].get("network"), m.get("years")),
                                   m.get("intro", ""), clips))
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
        "BTS_TILES": bts_tiles,
        "BTS_RECENT": bts_recent,
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
