# Upstream integration

MaterialGram is an unofficial Android client based on Telegram Android upstream.

## Pinned source
- Repository: https://github.com/TelegramOrg/Telegram-Android
- Pinned revision: `21f7d109da6ab3506c9e9577f98c6a38771ab335`
- License: GPL-2.0
- Submodule: `upstream/Telegram-Android`

Initialize source locally:
```bash
git submodule update --init --recursive
```

## Real APK build
Use **Actions → MaterialGram Telegram APK → Run workflow** after adding repository Actions secrets:
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

Obtain these from your own app entry at https://my.telegram.org/apps. Do not use the upstream app's API credentials, publish your values, or commit them to source control.

The workflow installs the upstream-required Java/Android toolchain, runs `tools/prepare_materialgram_upstream.py`, and invokes:
```bash
cd upstream/Telegram-Android
./gradlew :TMessagesProj_App:assembleAfatDebug
```

The preparation script applies `org.materialgram`, app label/icon branding, injects API values only in the temporary CI checkout, disables upstream-only account features and upstream update links, and removes the upstream Google Maps key. API values are never printed in logs.

Firebase is optional for the initial build. To configure push notifications, add `MATERIALGRAM_GOOGLE_SERVICES_JSON_BASE64` with your own Firebase config for package `org.materialgram`. Without this optional secret, the Google Services Gradle plugin and upstream Firebase config are removed in the temporary build checkout, so push notifications will not be configured. Google Maps features also need a separately configured key.

## Separate prototype
The top-level `app/` directory is a Compose UI prototype for design experiments. The Telegram APK workflow does not package this prototype; it builds the app from `TMessagesProj_App` and `TMessagesProj` in the pinned upstream.

## Security and licensing
Never commit API hashes, signing keys, passwords, or Firebase files. Preserve Telegram Android's GPL-2.0 license and notices, and publish source modifications as required when distributing builds. Do not use Telegram's official app name/logo or imply official affiliation.
