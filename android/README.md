# Anki Vocab Android Companion

Minimal personal Android companion app for `ACTION_PROCESS_TEXT`.

## Build

Install Android Studio or Android SDK first, then run from the repository root:

```bash
make android-apk
```

The debug APK is written to:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## Install

Transfer `app-debug.apk` to the phone, open it on the phone, allow installation from
that source when Android asks, and install it.

Open the app once to set:

- `backend_url`
- `mobile_token` (`ANKI_SYNC_TOKEN` from the backend)
- `bot_username`

After that, select text in another app and choose `Vocab` from the Android text
selection menu.
