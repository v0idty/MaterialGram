# MaterialGram

A native Android Telegram client project. The project is currently at the Android foundation stage; Telegram networking, authentication, and chat features are **not implemented yet**.

## Stack
- Kotlin
- Jetpack Compose / Material 3
- Android Gradle Plugin 8.7.3
- Android SDK 35

## Build
The current Compose prototype is buildable separately. The Telegram upstream source is a submodule and must be initialized before working with it:

\`\`\`bash
git submodule update --init --recursive
\`\`\`

Open \`upstream/Telegram-Android\` separately in Android Studio and follow its upstream README for SDK/NDK and credential setup. This repository's simple Gradle project does not build the upstream Telegram source.


## Roadmap
- [x] Add upstream Telegram Android source as a submodule reference
- [ ] Integrate and audit upstream into the MaterialGram build
- [ ] Establish Telegram API / MTProto client configuration
- [ ] Authentication flow
- [ ] Chat list and conversation UI
- [ ] Material You theming and customization
- [ ] Client settings and additional features

## License
The app's license and upstream attribution must be finalized before importing or distributing upstream Telegram code. Keep upstream notices and comply with the source project's license.
