# Persian Type 3.4.0 — Blender compatibility

## فارسی

در تاریخ 2026-11-21 نسخهٔ پایدار رسمی Blender، نسخهٔ 5.3.0 است. افزونه در سه نسخهٔ نصب‌شده روی Windows با پروفایل موقت بررسی شد.

- **Blender 5.0.1:** ۸۵ بررسی موفق، صفر شکست. API مربوط به Line Spacing و Text Style Presets وجود ندارد؛ ردیف‌های مربوطه نمایش داده نمی‌شوند.
- **Blender 5.2.0 LTS و 5.3.0:** هرکدام ۸۸ بررسی موفق، صفر شکست؛ کنترل‌های کامل حفظ شده‌اند.
- **اصلاح سازگاری:** پنل به API غایب ارجاع نمی‌دهد. محدودیت حداقل Blender همچنان 5.0.1 است.
- **بسته‌بندی:** پوشه‌های `.agents` و `.codex`، فایل `AGENTS.md` و خروجی‌های `dist` و `build` از بستهٔ کاربران کنار گذاشته شدند.

## English

On 2026-11-21 the official stable Blender release is 5.3.0. The add-on was checked on three installed Windows builds in isolated profiles.

- **Blender 5.0.1:** 85 checks passed, zero failures. Line Spacing and Text Style Presets APIs are absent; their controls are hidden.
- **Blender 5.2.0 LTS and 5.3.0:** 88 checks passed on each, zero failures; full controls retained.
- **Compatibility fix:** the panel no longer references unavailable APIs. Minimum Blender remains 5.0.1.
- **Packaging:** exclude `.agents`, `.codex`, `AGENTS.md`, `dist` and `build` from the installed extension.

## Validation scope

- Compile all four Python modules; register all operators and both panels; remove Scene properties and repeat registration.
- Persian shaping and read-back: Yeh, Keheh, Lam-Alef, ZWNJ, mixed Latin/Persian, decimal/date/time/version numbers, multiline text.
- 3D text: create, insert, Backspace, Delete, move cursor, apply bundled/system/custom font, Regular/Bold, reset and direction toggle.
- Persian font produces vertices; Mesh Clean retains filled polygons.
- 76 bundled fonts and custom-folder enumeration; system discovery; repeated cached callbacks create zero font datablocks.
- VSE: add distinct strips/channels, apply/load multiline text, add/remove/reorder lines, apply all font groups, reset to visible RTL appearance, invalid-selection poll guards.
- Presets: save into isolated user scripts folder and restore color/outline in Blender 5.2/5.3.
- Render a Persian TextStrip to PNG with Blender itself.
- Eight appearance-draw contract cases per version using real RNA and a recording layout: no strip, spacing modes, effects enabled/disabled. This is a property-contract check, not a native GUI test.

### Limits

No macOS/Linux runtime testing; no full interactive modal lifecycle or undo/redo exercise; no exhaustive new shaping corpus. The shaping engine is unchanged. Known modal/global-buffer limitations documented in project rules remain.

## Official references

- [Blender 5.3 release](https://www.blender.org/releases/5-3/)
- [Blender 5.3 Python API release notes](https://developer.blender.org/docs/release_notes/5.3/python_api/)
- [Blender 5.3 API reference](https://docs.blender.org/api/5.3/)
