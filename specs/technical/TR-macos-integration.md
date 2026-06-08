# TR-macos-integration — Login item, Keychain, Shortcuts, Calendar

## Purpose

Native macOS conveniences: launch-at-login, secure token storage, Shortcuts/Siri
intents, and Calendar/Reminders access.

## Requirements

**TR-OS-001** App SHALL register/unregister launch-at-login via `SMAppService` and surface its status.

**TR-OS-002** The daemon API token SHALL be stored in and read from the Keychain (file fallback).

**TR-OS-003** App SHALL expose Shortcuts intents: Ask, Speak, Add Mission.

**TR-OS-004** App SHALL read upcoming Calendar events and read/create Reminders via EventKit, permission-gated, with Info.plist usage strings.

## Acceptance criteria

```bash
# macOS only — verified via the Swift build job.
cd KMacAgentFriendApp && xcodegen generate && xcodebuild -scheme KMacAgentFriend -configuration Debug build
```
