// Solid nav once the hero scrolls away.
const nav = document.querySelector(".nav");
const onScroll = () => nav.classList.toggle("solid", window.scrollY > window.innerHeight * 0.5);
addEventListener("scroll", onScroll, { passive: true });
onScroll();

// Lightbox: steps through every image in a group (one production, BTS, etc.).
const box = document.querySelector(".lightbox");
const boxImg = box.querySelector("img");
const boxCap = box.querySelector("figcaption");
const small = matchMedia("(max-width: 1100px)");
let group = [];
let index = 0;
let opener = null;

const srcFor = (link) => (small.matches && link.dataset.mid) || link.href;

function show(i) {
  index = (i + group.length) % group.length;
  const link = group[index];
  boxImg.src = srcFor(link);
  boxImg.alt = link.dataset.alt || "";
  boxCap.textContent = group.length > 1
    ? `${link.dataset.caption}  ·  ${index + 1} / ${group.length}`
    : link.dataset.caption;
  // Warm the next image so swiping feels instant.
  const next = group[(index + 1) % group.length];
  if (next !== link) new Image().src = srcFor(next);
}

function open(link) {
  opener = link;
  group = [...document.querySelectorAll(`a[data-group="${CSS.escape(link.dataset.group)}"]`)];
  show(group.indexOf(link));
  box.hidden = false;
  document.body.style.overflow = "hidden";
  box.querySelector(".lb-close").focus({ preventScroll: true });
}

function close() {
  box.hidden = true;
  boxImg.removeAttribute("src");
  document.body.style.overflow = "";
  opener?.focus({ preventScroll: true });
}

document.addEventListener("click", (e) => {
  const link = e.target.closest("a[data-group]");
  if (!link) return;
  e.preventDefault();
  open(link);
});
box.querySelector(".lb-close").addEventListener("click", close);
box.querySelector(".lb-prev").addEventListener("click", () => show(index - 1));
box.querySelector(".lb-next").addEventListener("click", () => show(index + 1));
box.addEventListener("click", (e) => { if (e.target === box) close(); });
document.addEventListener("keydown", (e) => {
  if (box.hidden) return;
  if (e.key === "Escape") close();
  if (e.key === "ArrowLeft") show(index - 1);
  if (e.key === "ArrowRight") show(index + 1);
});

// Swipe left/right to navigate, swipe down to close.
let touchX = 0;
let touchY = 0;
box.addEventListener("touchstart", (e) => {
  touchX = e.touches[0].clientX;
  touchY = e.touches[0].clientY;
}, { passive: true });
box.addEventListener("touchend", (e) => {
  const dx = e.changedTouches[0].clientX - touchX;
  const dy = e.changedTouches[0].clientY - touchY;
  if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) show(index + (dx < 0 ? 1 : -1));
  else if (dy > 80 && Math.abs(dy) > Math.abs(dx)) close();
}, { passive: true });
