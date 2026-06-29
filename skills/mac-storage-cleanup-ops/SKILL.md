---
name: mac-storage-cleanup-ops
description: Evaluate and optionally perform conservative macOS disk cleanup and no-restart relief. Use when a user wants recurring Mac storage cleanup, safe-to-delete candidates, cache/log cleanup, startup-freeze triage, launch-agent review, CapCut draft/archive follow-up, APFS/purgeable-space explanation, or a risk-ranked cleanup plan that avoids breaking app state and user data.
memory_tags:
  - domain:storage
  - workflow:mac-cleanup
  - repo_boundary:tools
  - inputs:filesystem
  - outputs:cleanup-plan
  - risk:medium
---

# Mac Storage Cleanup Ops

## Trigger

Use when:
- A Mac is low on disk space and the user asks what can be cleaned without breaking anything.
- The user wants recurring cleanup evaluation with safe-to-delete candidates.
- The user wants to delete caches, logs, dev tool caches, Trash, or app temp files.
- The user wants to distinguish cache cleanup from user-data cleanup.
- The user asks how to save space without restarting.
- The user reports startup freezes and wants reversible login/background item triage.

Do not use when:
- The user needs low-level APFS repair, partition resizing, or disk health diagnosis.
- The user asks for forensic recovery of deleted files.
- The task is only to find large folders/files; use `disk-space-ops` first or alongside this skill.

## Inputs

- Required: target Mac/home directory context.
- Optional: external archive path, cleanup age threshold, whether deletion is explicitly approved, specific categories to clean.

## Workflow

1. Start read-only.
   Run:
   - `python3 skills/mac-storage-cleanup-ops/scripts/audit_mac_cleanup.py`
   - add `--fast` when the Mac is currently freezing, load is high, or the user wants quick no-restart relief
   - add `--home <path>` only when inspecting a non-current user home.
2. Check the current free space with `df -h / /System/Volumes/Data`.
3. Present candidates by risk, not just size:
   - safe-ish now
   - safe-ish but causes redownload/rebuild
   - review first
   - avoid direct deletion
4. Delete only after explicit user approval for a named category or path.
5. After deleting, re-run the audit or at least `du -sh <cleaned-path>` and `df -h / /System/Volumes/Data`.
6. Record any substantive cleanup in the daily log when the workspace logging rules apply.

For active freeze or no-restart relief, keep probes narrow:

1. Snapshot pressure with `uptime`, `df -h /System/Volumes/Data`, and `ps -A -o pid,ppid,stat,%cpu,%mem,etime,comm,args | sort -k4 -nr | head -40`.
2. Avoid broad recursive scans while load or disk I/O is high. Prefer known candidate paths and exact `du -sh` checks.
3. Clear only approved safe-ish caches/logs/Trash first.
4. Treat launch-agent changes as reversible: use `launchctl disable gui/$(id -u)/<label>` only for user-owned nonessential agents and record how to re-enable with `launchctl enable gui/$(id -u)/<label>`.
5. Do not force-quit active user apps with unsaved state. Recommend manual close or ask for explicit permission before quitting browsers, editors, or creative tools.
6. Explain APFS/Finder space swings: purgeable storage, update/mobile assets, Spotlight/Photos/Contacts indexing, caches, and local snapshots can make used space drop after startup without a restart.

## Safe-Ish Candidates

These are usually safe to delete when the related app is closed. They may be regenerated.

- `~/Library/Logs/<app>`: app diagnostic history. Good target when a single app log folder is large.
- `~/Library/Logs/Unity`: Unity logs can grow large and are usually disposable.
- `~/Library/Caches/<app-or-tool>`: app caches. Prefer deleting large children rather than the whole `~/Library/Caches` tree.
- `~/.cache/uv`: Python package/build cache; future installs may redownload.
- `~/.cache/whisper`: model/cache files; future transcription may redownload models.
- `~/.cache/codex-runtimes`: local runtime cache; future runs may redownload runtimes.
- `~/.npm`: npm cache; future installs may be slower.
- `~/Library/Caches/Homebrew`: Homebrew downloads; prefer `brew cleanup --prune=all` when available.
- `~/Library/Caches/pip`: pip cache; can be recreated.
- `~/Library/Caches/ms-playwright` and `~/.cache/ms-playwright` when present: Playwright browser cache; tests may redownload browsers.
- `~/Library/Application Support/app_shell_cache_*`: app shell package caches; usually safe when the owning app is closed, but delete only the exact cache directory after inspection.
- `~/Movies/CapCut/User Data/Cache`: CapCut cache, not project folders. Close CapCut first.
- `~/.Trash`: user Trash. Empty only when the user accepts permanent deletion.

## Review-First Candidates

Do not auto-delete these. Ask the user to confirm contents, archive first, or clean through the owning app.

- `~/Downloads`, especially folders named `to-process`, `delete-after-review`, `inbox`, or similar.
- `~/Movies/CapCut/User Data/Projects`: CapCut project data. Archive old non-template projects with symlinks instead of deleting.
- `~/Library/Messages`: iMessage attachments/history. Prefer Messages settings or manual attachment review.
- `~/Library/Mail`: mail cache and local mail data. Prefer Mail app/account cleanup.
- `~/Library/Application Support/Notion`: local Notion app state/cache. Avoid direct deletion unless the user accepts re-sync risk.
- `~/Library/Application Support/Notion/Partitions`: Chromium/Electron partition data can be very large. Prefer Notion's app controls or explicit user acceptance of re-sync/session risk.
- `~/Library/Application Support/Claude`: Claude app runtime/state. VM bundles may be large but direct deletion can force repair/redownload.
- `~/Library/Application Support/Claude/vm_bundles`: Claude local VM/runtime bundles. Review first; deletion may force repair, redownload, or local runtime rebuild.
- `~/Library/Application Support/Cursor/User/globalStorage` and `workspaceStorage`: IDE state/history/extensions. Review before deleting.
- Browser profiles under `~/Library/Application Support/Google/Chrome` or similar: contain profiles, sessions, extensions, and history.
- `~/Library/Developer/CoreSimulator/Devices`: simulator device data. Prefer `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcrun simctl delete unavailable` and review before deleting all devices.
- VM images, disk images, backups, photo libraries, archives, and external-drive mirrors.

## Startup Freeze Triage

When cleanup is connected to startup freezing:

1. Separate storage pressure from CPU/process pressure.
   - Storage: `df -h /System/Volumes/Data`, targeted `du -sh`.
   - CPU/process: `uptime`, `ps ... | sort -k4 -nr | head`.
2. Identify whether the current spike is Apple background work, browser/editor load, Rosetta (`oahd-helper`), Spotlight (`mds`, `mdworker`, `mdsync`), Software Update, Photos, Contacts, or third-party login items.
3. List normal login items with:
   - `osascript -e 'tell application "System Events" to get the name of every login item'`
4. List background items with:
   - `sfltool dumpbtm`
5. Inspect user launch agents with:
   - `find ~/Library/LaunchAgents /Library/LaunchAgents /Library/LaunchDaemons -maxdepth 1 -name '*.plist' -print 2>/dev/null`
   - `plutil -p <plist>` for specific suspects.
6. Disable only user-owned, nonessential launch agents when the user approves or when the current request clearly asks for startup mitigation.
7. Re-enable any mistakenly disabled required agent immediately with `launchctl enable gui/$(id -u)/<label>`.

Do not disable Apple system services as a cleanup tactic. Prefer letting indexing/update jobs finish while plugged in and awake.

## Avoid Direct Deletion

- System paths under `/System`, `/usr`, `/bin`, `/sbin`, `/private`, or `/Library` unless the user asks for a specific, understood cleanup.
- Opaque app support directories that contain databases, account state, project files, local-only documents, or sync state.
- Symlink targets on external archives unless the user explicitly wants to remove the archived copy.

## Deletion Procedure

For approved safe-ish paths:

1. Confirm the relevant app is closed when cleaning app-specific caches/logs.
2. Re-measure the exact path with `du -sh <path>`.
3. Delete the specific approved path, not a broader parent.
4. Recreate the parent folder only when an app expects it and deletion removed the folder itself.
5. Verify:
   - `du -sh <parent-or-path>`
   - `df -h / /System/Volumes/Data`
6. Report reclaimed size and any expected side effect, such as redownloads or lost diagnostic history.

For no-restart cleanup, favor this order:

1. Empty `~/.Trash` after confirmation.
2. Clear selected large children of `~/Library/Caches`.
3. Clear `~/Library/Logs` or large app-specific log folders.
4. Run package-manager cleanup such as `brew cleanup --prune=all` when Homebrew is present.
5. Clear exact reviewed app-shell/cache directories.
6. Run Xcode simulator cleanup for unavailable devices using the full Xcode `DEVELOPER_DIR` when needed.
7. Stop before deleting app databases, profiles, VM bundles, or sync state unless the user explicitly accepts the side effect.

Prefer examples like:

```bash
rm -rf "$HOME/Library/Logs/Unity"
rm -rf "$HOME/Movies/CapCut/User Data/Cache"
npm cache clean --force
brew cleanup --prune=all
```

Use direct `rm -rf` only after explicit approval and only for the exact reviewed path.

## CapCut Archive Pattern

When CapCut project folders are large:

1. Quit CapCut.
2. Keep templates and recent projects local.
3. Move old non-template project folders to an external archive.
4. Leave symlinks at the original local project paths.
5. Verify there are no broken symlinks.
6. Open CapCut with the external drive mounted and spot-check archived projects.

Never delete CapCut project folders merely because they are old unless the user explicitly chooses deletion over archive.

## Script Surface

Primary audit:
- `skills/mac-storage-cleanup-ops/scripts/audit_mac_cleanup.py`

Useful flags:
- `--home <path>`: inspect a specific home directory.
- `--top <n>`: number of largest children to show under broad folders.
- `--fast`: skip heavier review-first app-data scans for active freeze/no-restart triage.
- `--json`: emit machine-readable JSON.

## Outputs

- Current cleanup candidate table with size, risk, expected side effect, and recommended action.
- Clear separation of safe-ish deletion candidates from review-first user/app data.
- Concrete deletion commands only after the user approves a named target.
- Post-cleanup verification with before/after sizes.

## Boundaries

- Default to read-only evaluation.
- Never silently delete.
- Keep examples generic and public-safe.
- Keep user-specific paths, credentials, external drive names, and private archive conventions outside this skill unless provided by the user at runtime.
