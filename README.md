# jessegiddings.com

One-page portfolio for unit stills, BTS and social work in film and television.

## How it's put together

| Path | What it is |
|---|---|
| `content/site.json` | All copy, captions, production order and credits |
| `content/clips.json` | Video clips (Instagram, YouTube, Facebook, X) attached to productions |
| `photos/<folder>/` | Original images, one folder per production |
| `templates/` | Page template, styles and the lightbox script |
| `build.py` | Resizes photos to web-sized WebP and writes the finished site |
| `docs/` | The built site (generated; don't edit by hand) |

## Common edits

- **Swap in full-res originals:** replace the files in `photos/<folder>/`, then rebuild.
- **Add a production:** make a new `photos/<folder>/`, add an entry to `productions` in `content/site.json`, then rebuild. The first image (or the first one listed in `order`) is the cover.
- **Add a video clip:** add an entry to `clips` in `content/clips.json` and drop its thumbnail in `photos/clips/`, then rebuild. `posted` (the post date) only sorts clips newest first; the site never shows dates. Example:

  ```json
  {
    "production": "Snowpiercer",
    "network": "TNT",
    "posted": "2022-07-01",
    "url": "https://www.instagram.com/reel/XXXXXXXXXXX/",
    "thumbnail": "clips/snowpiercer-01.jpg",
    "credit": "TNT social, Snowpiercer. Includes on-set BTS footage shot by Jesse Giddings. Edit by TNT."
  }
  ```

  `production` must match a title in `site.json` for the clip to join that card; otherwise a clip-only card is added at the end of Work. For a short intro line above the clips, add the production under `productions` in `clips.json`. Videos are never downloaded or re-hosted: the page shows your thumbnail and loads the platform's own embed only when someone presses play, with a "Watch on …" link if it can't load.
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
