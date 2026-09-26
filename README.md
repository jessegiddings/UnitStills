# jessegiddings.com

One-page portfolio for unit stills, BTS and social work in film and television.

## How it's put together

| Path | What it is |
|---|---|
| `content/site.json` | All copy, captions, production order, credits and BTS embed links |
| `photos/<folder>/` | Original images, one folder per production |
| `templates/` | Page template, styles and the lightbox script |
| `build.py` | Resizes photos to web-sized WebP and writes the finished site |
| `docs/` | The built site (generated; don't edit by hand) |

## Common edits

- **Swap in full-res originals:** replace the files in `photos/<folder>/`, then rebuild.
- **Add a production:** make a new `photos/<folder>/`, add an entry to `productions` in `content/site.json`, then rebuild. The first image (or the first one listed in `order`) is the cover.
- **Add Instagram or YouTube posts:** paste the URLs into `bts.embeds` in `content/site.json`, then rebuild.
- **Change copy:** edit `content/site.json`, then rebuild.

## Build

```sh
pip install Pillow
python3 build.py
```

Preview with `python3 -m http.server -d docs` and open http://localhost:8000.

## Publish

GitHub Pages: Settings → Pages → Deploy from a branch → `main` / `docs`.
Any static host (Netlify, Vercel, Cloudflare Pages) also works with `docs` as the output folder and no build command.
