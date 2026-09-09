---
name: persian-text-shaping
description: Load this skill before touching the Persian/Arabic shaping engine in Persiantype.py — that is, any change to link_text, swap_lines, unlink_text, is_right_connectable, is_left_connectable, get_previous_alphabet, get_next_alphabet, the text_buffer / current_char_index globals, or the cursor operations init, update_text, insert_text, delete_previous, delete_next, move_previous, move_next, move_up, move_down, move_line_start, move_line_end, get_line_start, get_next_line_start, update_visual_cursor_position. Also load it for normalize_persian_text in __init__.py, for the buffer re-seeding inside create_persian_text in panel.py, and for any bug report about wrong letter joining, mirrored or reversed text, broken Lam-Alef ligatures, ZWNJ handling, Persian Yeh or Kaf turning into their Arabic forms, digits or Latin words appearing backwards, or a text object that shows one thing in the viewport and another after re-editing.
---

# Persian text shaping in Persiantype.py

## Why this engine exists

Blender FONT objects have **no HarfBuzz shaping and no bidi algorithm**. `curve.body`
is drawn glyph-by-glyph, left to right, with no contextual joining. So this add-on does
the shaping itself:

- The **logical** string (what the user typed, base letters, RTL order) lives only in the
  Python global `Ar.text_buffer` — a list of single base characters — with the caret in
  `Ar.current_char_index`.
- The **visual** string (Unicode presentation forms, already reversed so Blender's LTR
  drawing produces RTL reading order) is what gets written into `obj.data.body`.

Two representations, one source of truth. `text_buffer` is authoritative; `body` is a
render artifact regenerated wholesale by `update_text()` on every keystroke.

## The three-function contract

| Function | Input | Output |
|---|---|---|
| `link_text(unlinked_text)` | logical base-letter string | presentation forms, **visually reversed** (built with `insert(0, ...)`) |
| `swap_lines(linked_text)` | reversed multi-line output of `link_text` | same glyphs, line order restored (reversal flipped the lines too) |
| `unlink_text(linked_text)` | presentation forms | base letters, logical order |

Write path: `body = swap_lines(link_text(text_buffer))`.
Read path (re-editing an existing object): `text_buffer = list(unlink_text(body))`.

### Round-trip invariant

The write path is `body = swap_lines(link_text(s))`; the read path is
`unlink_text(swap_lines(body))`. So the full trip is

```
unlink_text(swap_lines(swap_lines(link_text(s)))) == s
```

`swap_lines` is an involution, so that reduces to `unlink_text(link_text(s))`. Writing it
with a single `swap_lines` is wrong for multi-line input and will send you chasing failures
that are an artefact of the formula.

**This invariant cannot hold for every input.** `link_text` is not injective: `سلام abc.`
and `سلام. abc` shape to one identical body, and no unshaper can choose between them.
Arabic Yeh is a second case — Unicode unifies its initial and medial forms with Persian
Yeh's, so `unlink_text` resolves towards Persian by design.

**The property that actually matters is re-shape stability:**

```
link_text(unlink_text(body)) == body
```

If that holds, the user never sees corruption even when the recovered logical text differs
from what they typed. Measure it over thousands of strings rather than asserting exact
equality over a handful.

Any edit to shaping must be checked in both directions, and any edit to `link_text` must
additionally be diffed against the previous engine over a large corpus, because `link_text`
is what Blender renders. Prove that every changed rendering is an improvement; strings with
no digits and no Latin should come back byte-identical.

## Unicode ranges in play

- **Base letters**: U+0600–U+06FF (Arabic block). This is what `text_buffer` holds.
- **Presentation Forms-B**: U+FE70–U+FEFF — isolated/final/initial/medial for the standard
  Arabic letters, plus the Lam-Alef ligatures.
- **Presentation Forms-A**: U+FB50–U+FDFF — the Persian-specific letters live here
  (Peh, Tcheh, Jeh, Keheh U+FB8E–FB91, Gaf U+FB92–FB95, Persian Yeh U+FBFC–FBFF).
- **Lam-Alef ligatures** (four, all mandatory — never emit Lam + Alef separately):
  - U+FEFB/FEFC — Lam + Alef
  - U+FEF7/FEF8 — Lam + Alef Hamza above
  - U+FEF9/FEFA — Lam + Alef Hamza below
  - U+FEF5/FEF6 — Lam + Alef Madda above
- **ZWNJ U+200C** is meaningful Persian orthography (`می‌رود`, `خانه‌ها`). It must survive
  into `text_buffer` and must break the join without producing a visible glyph.
  **ZWJ U+200D is not** — `normalize_persian_text` in `__init__.py` strips it, along with
  Tatweel U+0640.
- **Persian vs Arabic look-alikes** — normalize on input, never mix:
  - Yeh: Persian `ی` U+06CC vs Arabic `ي` U+064A
  - Kaf: Persian `ک` U+06A9 vs Arabic `ك` U+0643
  `normalize_persian_text` maps U+064A→U+06CC and U+0643→U+06A9. Every path that ingests
  outside text (`PT_OT_PastePersianNormalize`, `VIEW3D_OT_PastePersianText`, the Ctrl+V /
  Shift+Insert branch of `VIEW3D_OT_PersianTextMode`) must run it before touching
  `text_buffer`.

## Connectivity rules

A letter's form is chosen by two neighbour tests, `is_right_connectable(prev)` and
`is_left_connectable(next)`:

| prev joins | next joins | form |
|---|---|---|
| no | no | isolated |
| yes | no | final |
| no | yes | initial |
| yes | yes | medial |

- **Dual-joining** letters (ب پ ت ث ج چ ح خ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن ه ی) have all
  four forms.
- **Right-joining only** — `ا د ذ ر ز ژ و` (and Alef with hamza/madda) **never connect
  leftward**. They accept a join from the preceding letter but force the *following*
  letter into initial or isolated form. This is the single most common source of shaping
  bugs: if you add a letter to a table, decide first which of these two classes it is in.
- Non-letters (space, ZWNJ, digits, Latin, punctuation) break the join on both sides.

## Digits, Latin runs and punctuation

Numbers and Latin words are LTR islands inside an RTL line. Because `link_text` builds its
output with `insert(0, ...)`, naively appending a Latin run would reverse it. The engine
avoids that by probing the surrounding context with `get_previous_alphabet` and
`get_next_alphabet`: when a character is a digit, an ASCII letter, or common punctuation,
the run is emitted so that its own internal order stays logical while the run as a whole
lands in the right visual slot. Any change here must be tested with a run at the **start**,
in the **middle**, and at the **end** of a Persian line — the three cases have different
neighbour probes.

## Mandatory manual verification checklist

Before declaring a shaping change done, type each of these in the viewport (Ctrl+F1 →
Persian Text Mode), and for each one also exit and re-enter edit mode so the `unlink_text`
path runs:

1. `سلام دنیا` — basic dual-joining words, plus the space break.
2. `لاله` — Lam-Alef ligature (U+FEFB) *and* a following letter; a wrong ligature shows as
   two separate glyphs or eats the following `ه`.
3. `کتاب کوچک` — Keheh in initial, medial and final position; this is the string that
   exposes the U+FB8E defect on the re-edit path.
4. `۱۲۳ و abc` — Persian-Indic digits, a right-joining `و`, and a Latin run in one line.
5. A **two-line** string (`سلام` + RET + `دنیا`) — verifies `swap_lines`; a regression here
   shows as the lines appearing in the wrong order.
6. A mixed string such as `قیمت 1500 تومان است` — Persian + Latin digits + Persian, with
   the number in the middle.

Additionally exercise: ZWNJ (`می‌رود`), Persian Yeh initial/medial (`یاری`), and paste of
Arabic-typed text containing `ي` and `ك` to confirm normalization.

## Rules for editing this file

- Never write to `obj.data.body` directly from new code — go through `Ar.update_text()`,
  which is the only place allowed to rebuild the body.
- Never mutate `text_buffer` without keeping `current_char_index` in range; use
  `is_valid_char_index` and the existing `move_*` helpers.
- `text_buffer` and `current_char_index` are **module-level globals**, shared by every text
  object in the scene. Switching the active object without calling `Ar.init()` desyncs the
  buffer from the body and the next keystroke will corrupt the text. If you touch object
  switching, `Ar.init()` is mandatory.
- `update_text()` replaces the whole body (`font.select_all` → `font.delete` →
  `font.text_insert`), which destroys per-character `body_format` data, and
  `update_visual_cursor_position()` issues `bpy.ops.font.move` in a loop proportional to
  text length. Both are O(n) per keystroke — do not make them worse, and do not add another
  full-body rewrite on top.
- Keep shaping logic in `Persiantype.py`. It is pure Python with no `bpy` dependency in the
  `link_text`/`unlink_text`/`swap_lines` core; keeping it that way is what makes it testable
  outside Blender.
