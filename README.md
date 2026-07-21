# Persian Type 3.0 — افزونه تایپ فارسی و عربی برای Blender

[![Latest Release](https://img.shields.io/github/v/release/damyarpro/PERSIAN-TYPE?label=Latest%20Release)](https://github.com/damyarpro/PERSIAN-TYPE/releases/latest)
![Blender](https://img.shields.io/badge/Blender-5.0.1%2B-orange)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue)](https://www.gnu.org/licenses/gpl-3.0.html)

ساخت، تایپ، چسباندن، تنظیم فونت و تبدیل متن فارسی یا عربی به Mesh تمیز، مستقیماً داخل Blender.

Create, type, paste, style, and convert Persian or Arabic text into a clean mesh directly inside Blender.

[دانلود نسخه 3.0](https://github.com/damyarpro/PERSIAN-TYPE/releases/tag/v3.0) · [Download version 3.0](https://github.com/damyarpro/PERSIAN-TYPE/releases/tag/v3.0)

---

## فارسی

### قابلیت‌های اصلی نسخه 3.0

- **Add Text:** ساخت فوری متن راست‌چین «پرشین تایپ 0.3» در محل 3D Cursor و ورود مستقیم به حالت تایپ فارسی.
- **Paste:** خواندن متن فارسی یا عربی از Clipboard، نرمال‌سازی حروف و آماده‌سازی برای ادامه تایپ و پاک‌کردن.
- **تایپ مستقیم فارسی و عربی:** پشتیبانی از تایپ، Backspace، Delete، حرکت مکان‌نما و خطوط چندگانه در Edit Mode.
- **تغییر جهت متن:** جابه‌جایی سریع میان راست‌به‌چپ و چپ‌به‌راست.
- **انتخاب فونت:** استفاده از فونت‌های همراه افزونه، فونت‌های Windows یا یک پوشه فونت سفارشی.
- **تنظیمات ظاهر فونت:** وزن Regular/Bold، اندازه، شیب، فاصله حروف، کلمات و خطوط، Offset، Extrude، Bevel و Curve Resolution.
- **Mesh Clean:** تبدیل Text انتخاب‌شده به Mesh و پاک‌سازی خودکار توپولوژی.
- **سازگار با Blender 5:** حداقل نسخه موردنیاز Blender `5.0.1` است و API نسخه `5.2 LTS` نیز بررسی شده است.

### نصب

1. فایل [`persiantype-3.0.0.zip`](https://github.com/damyarpro/PERSIAN-TYPE/releases/download/v3.0/persiantype-3.0.0.zip) را دانلود کنید.
2. در Blender وارد `Edit > Preferences > Get Extensions` شوید.
3. از منوی بالا گزینه `Install from Disk` را انتخاب کنید.
4. فایل ZIP را انتخاب و افزونه را فعال کنید.
5. در 3D Viewport، پنل کناری را با کلید `N` باز کنید و وارد تب **Persian type** شوید.

### شروع سریع

#### ساخت متن جدید

1. روی **Add Text** کلیک کنید.
2. یک Text Object راست‌چین در محل 3D Cursor ساخته می‌شود.
3. متن نمونه را با صفحه‌کلید ادامه دهید یا با Backspace پاک کنید.

#### چسباندن متن فارسی یا عربی

1. متن را در Clipboard کپی کنید.
2. روی **Paste** کلیک کنید.
3. افزونه حروف عربی `ي` و `ك` را به شکل استاندارد فارسی `ی` و `ک` تبدیل می‌کند، کشیده و ZWJ اضافی را حذف می‌کند و متن را راست‌چین تحویل می‌دهد.
4. مکان‌نما در انتهای متن قرار می‌گیرد و می‌توانید بلافاصله تایپ را ادامه دهید.

### تنظیم فونت

یک Text Object را انتخاب کنید و از بخش **Font Settings** استفاده کنید:

- انتخاب فونت‌های داخلی افزونه
- انتخاب و Apply کردن Windows Fonts
- افزودن پوشه فونت سفارشی
- ذخیره فونت فعلی در فهرست فونت‌های محبوب
- تغییر وزن به Regular یا Bold، در صورت وجود فایل Bold در خانواده فونت
- کنترل Size، Slant، Character/Word/Line Spacing
- کنترل Offset، Extrude، Bevel، Bevel Segments و Curve Resolution
- بازگردانی همه تنظیمات با **Reset Font Settings**

> Blender 5.1 محور وزن Variable Font را مستقیماً در Python API ارائه نمی‌کند. گزینه Bold زمانی اثر متفاوت دارد که خانواده انتخاب‌شده فایل Bold جداگانه داشته باشد.

### Mesh Clean

دکمه **Mesh Clean** روی Text انتخاب‌شده، چه در Object Mode و چه در Edit Mode، این مراحل را اجرا می‌کند:

1. تبدیل Text به Mesh
2. افزودن Decimate Modifier در حالت `Planar / Dissolve`
3. Apply کردن Decimate
4. اجرای `Mesh > Clean Up > Delete Loose`
5. اجرای Merge by Distance با مقدار دقیق `0.01401 m`
6. بازگشت به Object Mode و تحویل Mesh نهایی

Mesh Clean از چند Text Object انتخاب‌شده نیز پشتیبانی می‌کند. توجه کنید که پس از تبدیل به Mesh دیگر امکان تغییر فونت وجود ندارد؛ فونت و ظاهر متن را پیش از Mesh Clean تنظیم کنید.

### فونت‌های همراه

افزونه دارای ۷۶ فونت است. نسخه 3.0 خانواده‌های آزاد زیر را نیز اضافه می‌کند:

- Vazirmatn
- Estedad
- Lalezar
- Markazi Text
- Noto Sans Arabic
- Noto Naskh Arabic
- Amiri Regular / Bold
- Scheherazade New Regular / Bold

این فونت‌ها با متن فارسی در Blender آزمایش شده‌اند. فایل مجوز SIL Open Font License هر خانواده در مسیر `fonts/licenses` قرار دارد.

### میانبر و ابزارهای قدیمی

- `Ctrl + F1`: فعال‌سازی حالت تایپ فارسی برای Text Object در Edit Mode
- **Enable Persian/Arabic Text:** فعال‌سازی دستی حالت تایپ
- **Paste Persian (Normalize):** چسباندن و نرمال‌سازی متن در Text Object فعلی
- **Toggle Text Direction:** تغییر RTL/LTR
- **Refresh:** بازسازی فهرست فونت‌ها

---

## English

### What’s new in version 3.0

- **Add Text:** Creates the “Persian Type 0.3” RTL text at the 3D Cursor and immediately enables Persian typing.
- **Paste:** Creates right-aligned Persian/Arabic text from the clipboard, normalizes common Arabic characters, and leaves the caret ready for continued editing.
- **Direct Persian/Arabic editing:** Supports typing, Backspace, Delete, cursor navigation, and multiline text in Edit Mode.
- **Text direction:** Quickly switch between RTL and LTR alignment.
- **Font selection:** Use bundled fonts, Windows Fonts, or a custom font directory.
- **Font appearance:** Regular/Bold, size, slant, character/word/line spacing, offset, extrusion, bevel, and curve resolution.
- **Mesh Clean:** Converts selected Text objects to Mesh and runs the complete cleanup workflow automatically.
- **Blender 5 support:** Requires Blender `5.0.1` or newer; the Blender `5.2 LTS` API changes have also been reviewed.

### Installation

1. Download [`persiantype-3.0.0.zip`](https://github.com/damyarpro/PERSIAN-TYPE/releases/download/v3.0/persiantype-3.0.0.zip).
2. Open `Edit > Preferences > Get Extensions` in Blender.
3. Choose `Install from Disk` from the menu.
4. Select the ZIP file and enable the extension.
5. In the 3D Viewport, press `N` and open the **Persian type** tab.

### Quick start

#### Create new Persian text

1. Click **Add Text**.
2. A right-aligned Text Object is created at the 3D Cursor.
3. Continue typing immediately or remove the sample with Backspace.

#### Paste Persian or Arabic text

1. Copy Persian or Arabic text to the clipboard.
2. Click **Paste**.
3. The extension normalizes Arabic Yeh/Kaf, removes Tatweel and unnecessary ZWJ characters, and creates an RTL Text Object.
4. The caret remains at the end so typing can continue immediately.

### Font controls

Select a Text Object and use **Font Settings** to:

- Choose bundled, saved, custom, or Windows fonts
- Apply Regular or Bold when a separate Bold font file is available
- Adjust size, slant, and character/word/line spacing
- Adjust offset, extrusion, bevel depth, bevel segments, and curve resolution
- Restore defaults with **Reset Font Settings**

> Blender 5.1 does not expose Variable Font weight axes through its Python API. Bold produces a distinct result when the selected family includes a separate Bold file.

### Mesh Clean workflow

**Mesh Clean** accepts selected Text objects in Object Mode or Edit Mode and performs:

1. Text to Mesh conversion
2. Planar/Dissolve Decimate modifier creation and application
3. `Mesh > Clean Up > Delete Loose`
4. Merge by Distance at exactly `0.01401 m`
5. Return to Object Mode

Multiple selected Text Objects are supported. Font information is no longer editable after conversion, so finish font and appearance adjustments before using Mesh Clean.

### Bundled fonts

The extension includes 76 fonts. Version 3.0 adds the following open font families:

- Vazirmatn
- Estedad
- Lalezar
- Markazi Text
- Noto Sans Arabic
- Noto Naskh Arabic
- Amiri Regular / Bold
- Scheherazade New Regular / Bold

All newly bundled fonts were tested by generating Persian geometry in Blender. Their SIL Open Font License files are included under `fonts/licenses`.

## Compatibility

| Item | Support |
| --- | --- |
| Blender | 5.0.1 or newer |
| Blender 5.2 LTS | API reviewed |
| Windows | Full system-font browsing and caching |
| Linux / macOS | Bundled fonts and custom font folders |

## Version 3.0 validation

- Python compilation passed for all extension modules.
- Blender Extension Manifest validation passed.
- Add Text, clipboard normalization, continued Persian typing, and deletion were tested.
- Regular/Bold font handling and appearance reset were tested.
- The complete Text-to-Mesh cleanup workflow was tested in Blender 5.1.2.
- All newly bundled fonts loaded and produced Persian geometry successfully.

## License

- Persian Type source code: [GNU GPL 3.0 or later](https://www.gnu.org/licenses/gpl-3.0.html)
- Newly bundled font families: SIL Open Font License; individual licenses are available in [`fonts/licenses`](fonts/licenses)

## Links

- [Latest release](https://github.com/damyarpro/PERSIAN-TYPE/releases/latest)
- [Version 3.0 release notes](https://github.com/damyarpro/PERSIAN-TYPE/releases/tag/v3.0)
- [Report an issue](https://github.com/damyarpro/PERSIAN-TYPE/issues)
