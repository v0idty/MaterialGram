# Upstream integration notes

MaterialGram is an unofficial Telegram client project. The current repository contains a lightweight Compose prototype plus a submodule reference to the Telegram Android source.

## Upstream source
- Repository: https://github.com/TelegramOrg/Telegram-Android
- License: GPL-2.0
- Submodule path: `upstream/Telegram-Android`

Initialize source locally:
```bash
git submodule update --init --recursive
```

Open `upstream/Telegram-Android` separately in Android Studio for upstream development/build setup. The upstream README documents its own Gradle project, required Android Studio, SDK/NDK versions, Firebase setup, and Telegram API credentials. Do not attempt to build it using the small Compose scaffold's Gradle files.

## MaterialGram branding plan
Branding must be applied to upstream app resources and build configuration, while preserving upstream copyright/license notices and publishing the corresponding source modifications. Do not use Telegram's official paper-plane logo or imply official affiliation.

## Credentials
Do not commit API hashes, signing keys, passwords, Firebase config, or other private credentials. Use local configuration or GitHub Actions secrets as appropriate. Never expose credential values in logs.

## Current limitations
The submodule is only a source dependency pointer. It is **not yet a branded MaterialGram APK**, and the Compose prototype is not connected to Telegram. Build and runtime validation is still required before calling this a usable client.
