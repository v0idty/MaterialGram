# MaterialGram

MaterialGram is an unofficial Android client project based on the open-source Telegram Android codebase. The real client source is pinned under `upstream/Telegram-Android`; the separate root `app/` module is only a small Compose UI prototype.

## Build the real Android client

The **MaterialGram Telegram APK** workflow builds the actual upstream Android application (not the Compose prototype). Before running it, add these repository Actions secrets:

- `TELEGRAM_API_ID` — your app ID from [my.telegram.org/apps](https://my.telegram.org/apps).
- `TELEGRAM_API_HASH` — the matching API hash from the same page.

Do not paste these values into chat, commit them, or place them in a source file. Add them in GitHub: **Settings → Secrets and variables → Actions → New repository secret**.

Then open **Actions → MaterialGram Telegram APK → Run workflow**. The workflow checks out the pinned Telegram source and its submodules, applies MaterialGram branding, and builds the `AfatDebug` APK. The artifact is named `MaterialGram-Android-debug`.

Optional: add `MATERIALGRAM_GOOGLE_SERVICES_JSON_BASE64` containing your own base64-encoded Firebase `google-services.json` for Firebase push notifications. Without it, the APK can still be built, but Firebase push notifications are not configured. Google Maps credentials are also intentionally not copied from the upstream app.

## Toolchain
- Telegram Android upstream revision: `21f7d109da6ab3506c9e9577f98c6a38771ab335`
- Java 17
- Gradle 8.13 (upstream wrapper)
- Android SDK 36
- Android NDK 27.2.12479018
- CMake 3.22.1

## Repository layout
- `upstream/Telegram-Android` — pinned Telegram Android source and its nested submodules.
- `tools/prepare_materialgram_upstream.py` — reproducible, CI-only package/branding/API configuration.
- `app/` — separate Compose UI prototype; it is not the Telegram client APK.

## Status
- [x] Pin Telegram Android source as a real Git submodule
- [x] Add a reproducible MaterialGram branding/configuration step
- [x] Add a workflow for building the real upstream Android app
- [ ] Complete the first successful upstream APK build
- [ ] Install and verify login, chat sync, calls, media, and notifications on a device
- [ ] Continue adapting the UI to Material You

## License and attribution
Telegram Android upstream is GPL-2.0. Keep its copyright notices and license, and publish corresponding source modifications when distributing builds. MaterialGram is unofficial and is not affiliated with Telegram.
