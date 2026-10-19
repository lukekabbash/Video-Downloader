# Scout Report: lukekabbash/Video-Downloader

**Date:** 2026-10-19  
**Repo:** https://github.com/lukekabbash/Video-Downloader  
**Scope:** Read-only assessment. No application code was changed.  
**Verdict:** A local PyQt5 desktop wrapper around `yt-dlp`. It is a personal prototype, not a product. It is not deployed, not packaged, and not worth shipping as-is.

---

## 1. What it is and how it works

This is a single-file desktop GUI named **Video Downloader - FREE**. The entire application lives in `VidDwn.py` (~762 lines). There is no web server, no API, no mobile app, and no installer.

The window is branded like early X/Twitter (dark `#14171A` → `#1DA1F2` gradient, `@LukeKabbash on X` credit). The main class is still called `YouTubeDownloader`. The advertised platforms are YouTube, X (Twitter), and Facebook.

### Entry point

```
python VidDwn.py
  → main()
    → QtWidgets.QApplication
    → YouTubeDownloader.show()
    → app.exec_()
```

On startup the window:

1. Builds the form (URL, save directory, quality, format, progress, history).
2. Loads `download_history.json` from the current working directory.
3. Checks for `ffmpeg` on `PATH`. If missing, it modal-prompts to download a third-party build or quit.

### Download flow

1. User pastes a URL and optionally changes folder / quality / export format.
2. `validate_url()` does a regex domain extract, then substring-matches against a tiny allowlist (`youtube.com`, `youtu.be`, `twitter.com`, `x.com`, `fb.watch`, `facebook.com`).
3. On the **UI thread**, `yt_dlp.YoutubeDL.extract_info(url, download=False)` fetches metadata so the app can guess a filename and offer overwrite.
4. If the guessed file already exists, it is **deleted immediately** on “overwrite,” before the new download succeeds.
5. A `QThread` + `DownloadWorker` runs `YoutubeDL.download([url])`.
6. Progress comes from yt-dlp’s progress hook (`_percent_str`).
7. On the hook’s `finished` status, the worker emits a **precomputed** filepath (not the path yt-dlp actually wrote).
8. That path is appended to an in-window list and persisted as JSON.
9. Double-click opens the parent folder; “Delete File” `os.remove`s the selected path.

### How media is actually downloaded

All fetching is delegated to **yt-dlp** (`from yt_dlp import YoutubeDL, utils`). There is no custom HTTP downloader, no official YouTube/X/Facebook API, and no cookies/auth UI.

Export format (not the quality dropdown) drives `ydl_opts`:

| UI format | yt-dlp format | Postprocessor |
|---|---|---|
| mp3 | `bestaudio/best` | `FFmpegExtractAudio` → mp3 @ 192 |
| wav | `bestaudio/best` | `FFmpegExtractAudio` → wav |
| mov | `bestvideo+bestaudio/best` | `FFmpegVideoConvertor` → mov |
| mp4 (default) | `bestvideo+bestaudio/best` | none, and **no `merge_output_format`** |

FFmpeg is required for merge/convert/extract. If it is not already installed, `download_and_install_ffmpeg()` pulls an unofficial build with `urllib.request.urlretrieve`, extracts it into `./ffmpeg_temp/`, and prepends that directory to the process `PATH`:

- Windows: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`
- Linux: `https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz` (x86_64 only)
- macOS: `https://evermeet.cx/ffmpeg/ffmpeg.zip` (ffmpeg binary only; no ffprobe)

No checksum, signature, or HTTPS pinning. Cleanup of the archive is commented out.

### Libraries and services

| Dependency | Declared? | Role |
|---|---|---|
| Python 3 | implicit | runtime |
| **PyQt5** | import only | desktop UI |
| **yt-dlp** | import only | extract + download |
| **FFmpeg** | runtime probe / auto-fetch | merge, audio extract, mov convert |
| stdlib (`urllib`, `zipfile`, `tarfile`, `json`, `logging`, …) | yes | FFmpeg bootstrap, history, logs |

There is **no** `requirements.txt`, `pyproject.toml`, `setup.py`, lockfile, Dockerfile, README, LICENSE, tests, or CI.

External *services* are the target sites themselves (YouTube / X / Facebook) via yt-dlp extractors, plus the three FFmpeg CDNs above. No keys, no OAuth, no backend.

---

## 2. Current state

### Runnable?

**Not out of the box.** The tree is two files:

```
.gitignore
VidDwn.py
```

This scout environment has Python 3.12.3 and system FFmpeg 6.1.1, but **PyQt5 and yt-dlp are not installed**. `python3 -m py_compile VidDwn.py` succeeds (syntax is valid). A user who already has `pip install PyQt5 yt-dlp` and FFmpeg on PATH can launch the window. That is the only supported “install path,” and it is undocumented.

### Deployed?

**No.** GitHub shows:

- Public repo, 0 stars, 0 forks, 0 issues, 0 PRs, 0 releases, 0 tags
- Description: *“Free video downloader. Use at your own risk.”*
- No license metadata
- No GitHub Actions, Pages, or deployments
- Disk usage ~14 KB
- Created 2025-01-15, last push 2026-07-15 (gitignore only)

This is a local script with a GUI, not a hosted product. It does not appear on [lkdigitalsolutions.com](https://lkdigitalsolutions.com/portfolio).

### Project structure and half-finished work

Three commits total:

1. `8ec52ca` (2025-01-14) — initial 764-line dump
2. `09066f1` (2025-01-14) — history now records a **guessed** final path instead of yt-dlp’s real path (workaround for audio/video temp files)
3. `371df8f` (2026-07-15) — ignore `ffmpeg/` and `ffmpeg_temp/`; commit message talks about removing bundled FFmpeg binaries, but **no binaries were ever in git**. Only `.gitignore` changed.

Half-finished / leftover:

- `QUALITY_OPTIONS` (`720p`, `1080p`, `4K`, “Best Video Only”, etc.) is wired into a dropdown and then **ignored**. `selected_quality` is assigned and unused.
- Comment: `# Add more supported platforms here` — never happened.
- `import webbrowser` unused.
- `self.downloader = None` unused.
- FFmpeg cleanup (`os.remove` / `shutil.rmtree`) is written and commented out.
- Progress bar still has a leftover `setGeometry(50, 230, 700, 30)` from an absolute-layout era; the window now uses layouts + `setFixedSize(800, 580)`.
- History label is added to a layout, then reparented into a header row.
- Class name `YouTubeDownloader` vs window title “Video Downloader - FREE”.
- Cancel calls `YoutubeDL.process_interrupt()`, which **does not exist** on current yt-dlp.

This reads as a one-evening prototype that got one filename bugfix the same night, then sat for 18 months.

---

## 3. Problems, risks, and anti-patterns

### Broken or fragile behavior

**Quality picker is cosmetic.** Every mp4/mov download uses `bestvideo+bestaudio/best`. Users who pick 720p or 4K still get “best.” Combined with no `merge_output_format: mp4`, “mp4” often lands as `.mkv`/`.webm` after a merge. History then points at `Title.mp4`, which may not exist.

**Filename / history mismatch.** The overwrite check and history entry use a homemade sanitize (`re.sub(r'[\\/*?:"<>|]', "", title)`). yt-dlp uses its own sanitizer, templates, and id/ext rules. Spaces, unicode, restricted filenames, playlists, and postprocessors all diverge. Delete and “open folder” then fail with “file does not exist.” The Jan 2025 commit made this worse on purpose: it stopped recording the path yt-dlp reported.

**Cancel is broken.** `self.worker.downloader.process_interrupt()` will raise `AttributeError`. The UI still re-enables buttons and `thread.quit()`, but the download keeps running. Leftover `.part` files are likely.

**Progress is unreliable.** `_percent_str` can include ANSI color codes or extra text. Parse failure → 0%. The `finished` hook fires **per downloaded format** (video, then audio, then merge), so `download_complete` can fire multiple times, duplicate history rows, and flip the UI to “finished” while FFmpeg is still muxing.

**URL allowlist is a substring trap.** `if key in domain` means:

- `https://www.xbox.com/...` matches `x.com`
- `https://notfacebook.com` matches `facebook.com`
- `https://youtube.com.attacker.tld` matches `youtube.com`

After that weak check, the raw URL is handed to yt-dlp, which will happily try any extractor. The allowlist is both bypassable and accidentally strict (Instagram/TikTok/Vimeo URLs are rejected even though yt-dlp supports them).

**UI thread blocking.** Metadata `extract_info` and the entire FFmpeg download/extract run on the GUI thread. A slow YouTube handshake or a 100MB FFmpeg zip freezes the window. Failure paths call `sys.exit(1)` from a message-box handler.

**Overwrite is destructive.** Existing file is deleted *before* the new download. A failed retry leaves the user with nothing.

**Thread hygiene.** Worker is not `deleteLater`’d; `finished` and `download_complete` both re-enable controls; a second download can start while the first thread is still winding down. `format_choice` is stored on the worker and never used.

**Linux/mac FFmpeg bootstrap is incomplete.** Linux URL is amd64-static only (ARM/Raspberry/Apple-on-Linux fail). macOS zip is ffmpeg-only; some yt-dlp paths want ffprobe. Archives are `extractall`’d with no path sanitization (zip/tar slip if a mirror is compromised).

**Platform reality (2025–2026).** YouTube often needs a JS runtime / `po_token` / updated yt-dlp. X and Facebook frequently need cookies for anything beyond public embeds. This app has no cookie import, no browser-cookie helper, no JS runtime pin, and no pinned yt-dlp version. Many “supported” URLs will fail in practice.

**No playlists, no queue, no resume, no rate-limit/retry config, no age-gate/auth.**

### Missing project hygiene

- No README, no install steps, no usage, no disclaimer beyond the GitHub one-liner.
- Unpinned `PyQt5` + `yt-dlp`. yt-dlp is a moving target; unpinned installs break extractors weekly.
- Logs (`downloader.log`) and history written to **CWD**, not a user data dir. Run it from the wrong folder and you scatter files. Run it twice from different folders and you get two histories.
- No tests. No type hints. No packaging (no `.app` / `.exe` / wheel).

### Secrets

**None found.** No API keys, tokens, or credentials in the tree. That is the one clean security finding.

### Security

The serious issue is **unsigned binary execution**:

1. App downloads FFmpeg from third-party sites over HTTPS with no hash verify.
2. Extracts with `zipfile.extractall` / `tarfile.extractall` (directory traversal if the archive is hostile).
3. Drops whatever is named `ffmpeg` / `ffmpeg.exe` onto `PATH` and later execs it via yt-dlp.

That is a supply-chain footgun. gyan.dev / johnvansickle / evermeet are commonly used, but they are not a vendor relationship, and this code cannot tell a real build from a poisoned one.

Secondary issues:

- History JSON is trusted file paths later passed to `os.remove` and `xdg-open`/`open`/`os.startfile`. A corrupted or user-edited history can delete unexpected files (user-assisted, local).
- Logging may record full URLs (including tokens in some share links).
- Public “free video downloader” framing invites drive-by clones that add malware. There is no code signing, no update channel.

### Licensing

| Component | License | Implication |
|---|---|---|
| This repo | **none** (all rights reserved by default) | Cannot legally redistribute even if someone wants to |
| PyQt5 | **GPL v3** | If you *distribute* a binary that links PyQt5, the app must be GPL and source must be offered. Riverbank is strict about this. |
| yt-dlp | Unlicense | Fine |
| FFmpeg static builds (esp. johnvansickle) | typically **GPL** | Same distribution duty if you ship the binary |

PySide6 (LGPL) would be the usual way to avoid forcing the whole app GPL. Right now the project is in the worst of both worlds: GPL obligations if shipped, no LICENSE file, no source offer text.

### Legal / ToS

This is the largest non-technical risk, and the repo already half-admits it (“Use at your own risk”).

- YouTube, X, and Facebook **Terms of Service prohibit** unauthorized downloading / scraping of media. yt-dlp exists in a well-known gray zone; a GUI that markets “FREE video downloader” for those three names is a more explicit product.
- Copyright: the tool does not check ownership. Default use is saving other people’s videos. Personal offline copies and fair-use arguments do not make a public, branded downloader safe to operate or sell.
- **Do not turn this into a hosted web service.** That is how you get DMCA notices, platform blocks, bandwidth bills, and (in some jurisdictions) secondary-liability arguments. A public “paste URL, we fetch it” API is a magnet for abuse.
- Even as a local tool, publishing it with Luke’s X handle in the chrome ties personal/brand identity to a ToS-hostile utility.

This scout is not legal advice. It is a product-risk call: the legal surface is larger than the code surface.

---

## 4. Mobile and UX

**There is no web UI.** The mobile-save class of bugs (blob download that never lands in Photos/Files, missing `download` attribute, iOS Safari ignoring `Content-Disposition`, in-app browsers eating the file) **does not apply** unless this is rewritten as a website.

What *does* apply:

- Desktop-only, fixed 800×580, no HiDPI/scaling work, Segoe UI hardcoded (wrong default on Linux/macOS).
- Contrast: white text on a gradient that becomes Twitter blue at the bottom.
- Quality control lies to the user.
- No drag-and-drop, no clipboard “paste and go,” no queue, no speed/ETA, no thumbnail/title preview after probe (probe result is discarded except for the filename).
- FFmpeg “install or we quit” is a harsh first-run.
- History is raw paths, not titles.
- Double-click opens the folder, not the file.
- Not accessible (no shortcuts beyond defaults, no high-contrast theme).

If the goal is “save a video on my phone,” this repo cannot help. It is a laptop app. Building a web wrapper around it would *create* the mobile-save problem and the legal problem at the same time.

---

## 5. Recommendations (practical, prioritized)

### Do first (if this stays a personal local tool)

1. **Do not deploy it.** No Vercel, no public proxy, no “free online downloader.” Keep it local or archive it.
2. **Stop auto-downloading FFmpeg.** Require a system install (`brew`, `apt`, `winget`, `choco`) and fail with a link. That removes the worst security issue in one decision.
3. **Add the missing project files:** `README.md` (what it is, personal-use disclaimer, install), `requirements.txt` with **pinned** `yt-dlp` and a Qt binding, and a `LICENSE` that matches the binding (GPL-3.0 if PyQt5 stays; prefer PySide6 + a simple MIT/GPL choice).
4. **Make the quality dropdown real or delete it.** Map 720p/1080p/4K to yt-dlp format strings; set `merge_output_format` to the chosen container.
5. **Record the path yt-dlp actually wrote** (`prepare_filename` / postprocessor hook / `info_dict['_filename']`), not a guessed name. Cancel via a cooperative flag or subprocess, not `process_interrupt()`.
6. **Move `extract_info` off the UI thread.** Don’t delete the existing file until the new file is complete (download to temp, then replace).

### Modernize only if you will actually use it

- PyQt5 → **PySide6** (maintained, LGPL).
- Split the 762-line file: `ffmpeg.py`, `worker.py`, `window.py`.
- Store history/logs under the platform user-data dir.
- Optional: cookies-from-browser for X/Facebook; document that YouTube breakage is an upstream yt-dlp problem.
- Optional CLI mode (`python -m viddwn URL`) so the GUI is not required.

Do **not** invest in: playlists, batch queues, theming, “50+ platforms,” auto-update of yt-dlp, installers, or a website. Mature tools already do this (yt-dlp CLI, [Unrud/video-downloader](https://github.com/Unrud/video-downloader), various existing GUIs). Competing with them is unpaid maintenance against YouTube’s extractor churn.

### Worth deploying? Worth folding in?

| Option | Recommendation |
|---|---|
| Hosted web downloader | **No.** Legal, abuse, cost, and mobile-save pain. |
| Public desktop product / “FREE” marketing | **No.** GPL/FFmpeg obligations, ToS, support burden, extractor rot. |
| Personal local script | **Yes, barely** — after FFmpeg/quality/cancel/filename hygiene. |
| Fold into another LK product (AI Integrator, EVE OS, Dandy Horse, etc.) | **No.** Wrong domain, wrong risk profile, nothing reusable except “call yt-dlp.” |
| Archive / leave public with a stronger disclaimer | **Reasonable.** Add README + LICENSE or make the repo private. A public untitled script with Luke’s handle in the UI is all downside. |

**Honest bottom line:** this is a fine weekend experiment from January 2025 and it shows. The interesting part is yt-dlp; the rest is unfinished GUI glue with a dangerous FFmpeg installer and a quality dropdown that does nothing. It is not a foundation for a product. If you need local downloads for yourself, use current `yt-dlp` on the command line (or a maintained GUI) and treat this repo as historical. If you need “save video on mobile,” that is a different project — and should not be a general-purpose YouTube/X/Facebook grabber.

---

## Appendix: verification notes

- Tree inspected: `.gitignore`, `VidDwn.py`, full git history (`8ec52ca`, `09066f1`, `371df8f`).
- GitHub API: public, no issues/PRs/releases/tags/license/Actions/Pages/deployments.
- Local: `py_compile` OK; `PyQt5` and `yt_dlp` missing in this environment; system `ffmpeg` present. GUI was not launched (headless + missing Qt).
- `process_interrupt` was searched in yt-dlp; no such public API.
- No secrets scanned in the two tracked files.
- Related public Luke repos (Lean proofs, AI Integrator releases, Secunda, mac-directory-statistics, Context Weaver) do not share code with this app.
