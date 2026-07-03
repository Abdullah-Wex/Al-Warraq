# Al-Warraq — brand assets

**Display brand:** Al-Warraq · **PyPI:** `al-warraq` · **Import/package:** `al_warraq` · **CLI:** `al-warraq` · **Arabic:** الورّاق (al-warrāq — the golden-age book craftsman; shadda on the rāʾ).

## The logo

One emblem is the logo everywhere: two serrated quill feathers over a classic glass inkwell; teal ink drops fall from the well, transform into golden "bits," and land in an open book (swept pages, seamed fore-edge, teal ribbon). The story is the library's pipeline: **process → split into passages → store**.

| File | Use |
|---|---|
| `emblem.svg` | The logo. Avatar, favicon, README, anywhere. |
| `icon.svg` | Same art as `emblem.svg`, kept as the icon-slot file. |
| `lockup-dark.svg` | Emblem + "Al-Warraq" wordmark, for dark backgrounds. |
| `lockup-light.svg` | Emblem + "Al-Warraq" wordmark, for light backgrounds. |

All finals are **fully outlined** — zero `<text>` elements, no font dependencies; they render identically everywhere.

## Palette

| Role | Hex |
|---|---|
| Gold (primary) | `#C9A227` |
| Pale gold / parchment | `#E8D49A` · `#F2E6C0` |
| Bronze browns (plate/ring) | `#57441F` · `#3B2B18` · `#6B5426` |
| Verdigris teal (ink accent) | `#3F7268` · `#5E8B7E` · `#2A9D8F` |

## Rules

1. **The tagline is never inside a logo file.** "Ancient craft | Digital knowledge | Libraries | Books | Manuscripts" lives as plain text next to the lockup.
2. **No text in the emblem/icon.** The wordmark exists only in the lockups, as outlined paths.
3. **Edit the masters, not the finals.** `masters/*.svg` keep live `<text>`; after editing, outline with `rsvg-convert -f svg master.svg -o final.svg`.
4. `masters/design-lab.html` is the browser workbench used to iterate the design (open it and view at multiple sizes on dark/light).
