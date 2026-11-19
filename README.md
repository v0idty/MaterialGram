# MaterialGram

A native Android Telegram client project. The project is currently at the Android foundation stage; Telegram networking, authentication, and chat features are **not implemented yet**.

## Stack
- Kotlin
- Jetpack Compose / Material 3
- Android Gradle Plugin 8.7.3
- Android SDK 35

## Telegram upstream source
Telegram Android is linked as a real Git submodule, pinned to a specific upstream revision. Clone with submodules:

```bash
git clone --recurse-submodules https://github.com/v0idty/MaterialGram.git
# If you already cloned it:
git submodule update --init --recursive
```

The CI workflow checks out the submodule and verifies that its README exists, then builds the current Compose prototype APK. The prototype Gradle project does **not** compile the Telegram upstream code yet.

## Roadmap
- [x] Add Telegram Android source as a pinned submodule
- [x] CI checks out and verifies upstream source
- [ ] Integrate and audit upstream into the MaterialGram build
- [ ] Establish Telegram API / MTProto client configuration
- [ ] Authentication flow
- [ ] Chat list and conversation UI
- [x] Material 3 light/dark theme prototype
- [ ] Client settings and additional features

## License
Telegram Android upstream is GPL-2.0. Preserve upstream notices and publish required source modifications before distributing builds.
