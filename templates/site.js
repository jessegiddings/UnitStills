// Solid nav once the hero scrolls away.
const nav = document.querySelector(".nav");
const onScroll = () => nav.classList.toggle("solid", window.scrollY > window.innerHeight * 0.5);
addEventListener("scroll", onScroll, { passive: true });
onScroll();

// ---------------------------------------------------------------------------
// Platform embeds. Nothing loads until a clip is played; each platform's
// script is fetched once and reused.
// ---------------------------------------------------------------------------
const EMBED_TIMEOUT = 5000;
const scripts = {};

function loadScript(src) {
  scripts[src] ??= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = resolve;
    s.onerror = () => { delete scripts[src]; s.remove(); reject(new Error(`Failed to load ${src}`)); };
    document.head.append(s);
  });
  return scripts[src];
}

// Each builder fills `slot` and resolves once the platform has rendered.
const embedders = {
  instagram(slot, clip) {
    const q = document.createElement("blockquote");
    q.className = "instagram-media";
    q.dataset.instgrmPermalink = clip.url;
    q.dataset.instgrmVersion = "14";
    const a = document.createElement("a");
    a.href = clip.url;
    q.append(a);
    slot.append(q);
    return loadScript("https://www.instagram.com/embed.js")
      .then(() => window.instgrm.Embeds.process())
      .then(() => waitFor(() => slot.querySelector("iframe.instagram-media-rendered")));
  },

  youtube(slot, clip) {
    const f = document.createElement("iframe");
    f.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(clip.embedId)}?autoplay=1&playsinline=1&rel=0`;
    f.title = clip.caption;
    f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    f.allowFullscreen = true;
    const loaded = new Promise((resolve) => f.addEventListener("load", resolve, { once: true }));
    slot.append(f);
    return loaded;
  },

  facebook(slot, clip) {
    if (!document.getElementById("fb-root")) {
      const root = document.createElement("div");
      root.id = "fb-root";
      document.body.prepend(root);
    }
    const v = document.createElement("div");
    v.className = "fb-video";
    v.dataset.href = clip.url;
    v.dataset.autoplay = "true";
    v.dataset.allowfullscreen = "true";
    slot.append(v);
    return loadScript("https://connect.facebook.net/en_US/sdk.js#xfbml=0&version=v19.0")
      .then(() => { window.FB.init({ xfbml: false, version: "v19.0" }); window.FB.XFBML.parse(slot); })
      .then(() => waitFor(() => slot.querySelector("iframe")));
  },

  x(slot, clip) {
    const q = document.createElement("blockquote");
    q.className = "twitter-tweet";
    q.dataset.dnt = "true";
    q.dataset.theme = "dark";
    const a = document.createElement("a");
    a.href = clip.url;
    q.append(a);
    slot.append(q);
    return loadScript("https://platform.twitter.com/widgets.js")
      .then(() => window.twttr.widgets.load(slot))
      .then(() => waitFor(() => slot.querySelector("iframe")));
  },
};

// Resolves when check() returns something truthy. Stops polling after the
// embed timeout; the caller's race has already shown the fallback by then.
function waitFor(check) {
  const giveUp = Date.now() + EMBED_TIMEOUT + 500;
  return new Promise((resolve) => {
    const tick = () => {
      if (check()) resolve();
      else if (Date.now() < giveUp) setTimeout(tick, 150);
    };
    tick();
  });
}

// ---------------------------------------------------------------------------
// Lightbox: steps through every item in a group (a production's photos,
// its clips, BTS stills). Only one item, and so one embed, exists at a time.
// ---------------------------------------------------------------------------
const box = document.querySelector(".lightbox");
const boxImg = box.querySelector("img");
const slot = box.querySelector(".lb-embed");
const capEl = box.querySelector(".lb-caption");
const creditEl = box.querySelector(".lb-credit");
const sourceEl = box.querySelector(".lb-source");
const prevBtn = box.querySelector(".lb-prev");
const nextBtn = box.querySelector(".lb-next");
const small = matchMedia("(max-width: 1100px)");
let group = [];
let index = 0;
let opener = null;
let showToken = 0;

const srcFor = (link) => (small.matches && link.dataset.mid) || link.href;

function clearEmbed() {
  showToken++;
  slot.replaceChildren();
  slot.hidden = true;
  slot.removeAttribute("data-platform");
}

function fallback(clip) {
  slot.replaceChildren();
  sourceEl.hidden = true;
  const p = document.createElement("p");
  p.className = "lb-fallback";
  p.textContent = "This clip couldn't load here.";
  const a = document.createElement("a");
  a.href = clip.url;
  a.target = "_blank";
  a.rel = "noopener";
  a.className = "btn ghost";
  a.textContent = `Watch on ${clip.platformName} ↗`;
  p.append(a);
  slot.append(p);
  a.focus({ preventScroll: true });
}

function showClip(el) {
  const clip = { ...el.dataset };
  const token = showToken;
  boxImg.hidden = true;
  boxImg.removeAttribute("src");
  slot.hidden = false;
  slot.dataset.platform = clip.platform;
  slot.style.setProperty("--ar", clip.format.replace(":", " / "));
  creditEl.textContent = clip.credit || "";
  sourceEl.hidden = false;
  sourceEl.href = clip.url;
  sourceEl.textContent = `Watch on ${clip.platformName} ↗`;

  const build = embedders[clip.platform];
  if (!build) return fallback(clip);
  const timeout = new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), EMBED_TIMEOUT));
  Promise.race([build(slot, clip), timeout]).catch(() => {
    if (token === showToken) fallback(clip);
  });
}

function show(i) {
  clearEmbed();
  index = (i + group.length) % group.length;
  const item = group[index];
  const count = group.length > 1 ? `  ·  ${index + 1} / ${group.length}` : "";
  capEl.textContent = (item.dataset.caption || "") + count;
  creditEl.textContent = "";
  sourceEl.hidden = true;

  if (item.dataset.platform) return showClip(item);

  boxImg.hidden = false;
  boxImg.src = srcFor(item);
  boxImg.alt = item.dataset.alt || "";
  // Warm the next photo so swiping feels instant.
  const next = group[(index + 1) % group.length];
  if (next !== item && !next.dataset.platform) new Image().src = srcFor(next);
}

function open(item) {
  opener = item;
  group = [...document.querySelectorAll(`[data-group="${CSS.escape(item.dataset.group)}"]`)];
  const isClip = Boolean(item.dataset.platform);
  box.setAttribute("aria-label", isClip ? "Video player" : "Image viewer");
  prevBtn.setAttribute("aria-label", isClip ? "Previous clip" : "Previous image");
  nextBtn.setAttribute("aria-label", isClip ? "Next clip" : "Next image");
  prevBtn.hidden = nextBtn.hidden = group.length < 2;
  box.hidden = false;
  document.body.style.overflow = "hidden";
  show(group.indexOf(item));
  box.querySelector(".lb-close").focus({ preventScroll: true });
}

function close() {
  clearEmbed();
  box.hidden = true;
  boxImg.removeAttribute("src");
  document.body.style.overflow = "";
  opener?.focus({ preventScroll: true });
}

document.addEventListener("click", (e) => {
  const item = e.target.closest("a[data-group], button[data-group]");
  if (!item) return;
  e.preventDefault();
  open(item);
});
box.querySelector(".lb-close").addEventListener("click", close);
prevBtn.addEventListener("click", () => show(index - 1));
nextBtn.addEventListener("click", () => show(index + 1));
box.addEventListener("click", (e) => { if (e.target === box) close(); });
document.addEventListener("keydown", (e) => {
  if (box.hidden) return;
  if (e.key === "Escape") close();
  if (group.length > 1 && e.key === "ArrowLeft") show(index - 1);
  if (group.length > 1 && e.key === "ArrowRight") show(index + 1);
  // Keep Tab inside the dialog.
  if (e.key === "Tab") {
    const focusables = [...box.querySelectorAll("button:not([hidden]), a[href]:not([hidden])")]
      .filter((el) => el.offsetParent !== null);
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
});

// Swipe left/right to navigate, swipe down to close. (Touches that land
// inside an embed belong to the platform player, so the arrows cover those.)
let touchX = 0;
let touchY = 0;
box.addEventListener("touchstart", (e) => {
  touchX = e.touches[0].clientX;
  touchY = e.touches[0].clientY;
}, { passive: true });
box.addEventListener("touchend", (e) => {
  const dx = e.changedTouches[0].clientX - touchX;
  const dy = e.changedTouches[0].clientY - touchY;
  if (group.length > 1 && Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) show(index + (dx < 0 ? 1 : -1));
  else if (dy > 80 && Math.abs(dy) > Math.abs(dx) && slot.hidden) close();
}, { passive: true });
