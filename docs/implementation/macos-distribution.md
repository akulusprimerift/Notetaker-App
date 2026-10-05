# Phase 6.9.5 — Mac installer and distribution

Active from 2026-10-02 after the user reported that the 6.9.4 test build works on their Apple Silicon Mac.

The 2026-10-05 build path now uses [SQLite standalone delivery](sqlite-standalone.md): only the frozen service, Ollama and account helper are staged. PostgreSQL/SeaweedFS downloads and builds are removed. The published October 2 DMG described below retains its earlier runtime; a new SQLite DMG has not been built or qualified on a Mac. Earlier libraries require explicit verified conversion into a new folder.

## Behavior

`.github/workflows/electron-macos.yml` builds on GitHub's macos-15 runner when a `macos-v*` tag is pushed and publishes a pre-release with a drag-to-Applications DMG (`UDZO`, Applications link). The app carries a 1024 px Mac icon (`apps/desktop/icon-mac.png`), version `0.1.0` with the CI run number as `CFBundleVersion`, the microphone purpose string, and the existing notices/licenses inside the native runtime.

Two signing modes, selected by repository secrets:

| Secrets present | Result |
| --- | --- |
| none | Ad-hoc signed, un-notarized `Notetaker-0.1.0-macOS-arm64-unsigned.dmg`. After copying to Applications run `xattr -dr com.apple.quarantine /Applications/Notetaker.app`. |
| `MACOS_CERTIFICATE_P12` (base64 Developer ID Application .p12), `MACOS_CERTIFICATE_PASSWORD`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID` | Developer ID signed with the hardened runtime and `apps/desktop/entitlements.mac.plist` (JIT, unsigned executable memory, library validation off, audio input), notarized and stapled; CI checks `stapler validate` and `spctl --assess`. |

The launcher verifies SHA-256 hashes of every native runtime file at startup, so Developer ID signing of Ollama, the frozen service and the account helper happens **before** the runtime inventory is locked; electron-builder skips `Contents/Resources/native-runtime`. Every build runs `codesign --verify --deep --strict` and `hdiutil verify`.

The library lives outside the app bundle, so replacing an older `Notetaker.app` keeps it. An ad-hoc build has a new code identity on each build; Keychain may ask again for stored credentials after an upgrade. A Developer ID build keeps a stable identity.

## Evidence

Tag `macos-v0.1.0-beta.1`, run 37075163831 (commit `256ebab`) passed: shared checks, component build, staging, ad-hoc signing, `codesign --verify --deep --strict` and `hdiutil verify`. No signing secrets were configured, so it published the pre-release asset `Notetaker-0.1.0-macOS-arm64-unsigned.dmg` (711,945,751 bytes, SHA-256 `63a6f0edbf1d44f1bbcf4a3613851a68c40468a1bfd56946b7746d3382d2b0b0`). It has not been opened on a Mac yet.

## Open

- No Developer ID certificate is configured yet; the notarized path has not run.
- Clean-Mac launch of the DMG, replacing an older build with an existing library, and Keychain behavior across upgrades need the user's Mac.
- 6.9.6 release qualification and the earlier 6.9.1–6.9.3 native gaps remain open.
