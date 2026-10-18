# Yazi Setup + Launcher

One project for Windows and Linux: Yazi dependencies, custom keybindings, ZIP
creation/extraction, and an application launcher. The Windows launcher source
and icon are included under `launcher/windows`; the separate launcher project
is no longer needed to install this package.

Requires **Python 3.11+** and **Yazi 26.9.1 or newer** for the bundled plugin API.
No pip packages are required. Run setup as your normal user. Linux package
installation uses sudo; Windows package installers may request elevation.

## Windows

1. Extract or clone this project.
2. If Python is missing, run `winget install -e --id Python.Python.3.13 --source winget`, then
   reopen your terminal.
3. Double-click **Install Yazi Scripts.bat**. It installs missing Yazi and
   dependency packages, adds the configuration, builds the launcher, and creates
   **Yazi Launcher** in Start. Choose a theme from the menu (keeping the existing
   theme is the default). It also installs a Nerd Font and configures a dedicated
   **Yazi Setup** Terminal profile to display the icons correctly.
4. Fully close Windows Terminal and reopen **Yazi Launcher** so Terminal sees the
   new font/profile. Pin its Start shortcut to the taskbar.

Equivalent command from the project directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\yazi-installer.ps1 -InstallYazi -InstallDependencies -Theme choose
```

Windows Terminal and .NET Framework's C# compiler are needed for the launcher.
The installer uses winget for Terminal, Yazi, Git for Windows, 7-Zip, FFmpeg, jq,
Poppler, fd, ripgrep, fzf, zoxide, and ImageMagick when commands are missing.
It adds 7-Zip and its user-installed SVG renderer to your user PATH and configures
`YAZI_FILE_ONE` from the detected Git installation. If a custom Git installation
cannot be detected, set that variable to its `usr\bin\file.exe` yourself.

The launcher retains its separate Windows taskbar identity, custom icon, new
Terminal window behavior, and logging at `%LOCALAPPDATA%\YaziLauncher\launcher.log`.
Setup does not open Yazi automatically.

## Linux

Install Python 3.11+ using your distribution's package manager, then run:

```sh
sh ./install.sh
```

Automatic package installation supports Debian/Ubuntu (`apt-get`), Fedora
(`dnf`), and Arch (`pacman`). Debian/Ubuntu setup adds the official Yazi stable
APT repository, which publishes amd64/arm64 builds. Fedora setup enables the
`lihaohong/yazi` COPR repository referenced by the official installation guide. Other
distributions can install Yazi and dependencies manually, then run:

```sh
sh ./install.sh --configure-only
```

Run setup as your normal user, not through `sudo`; it asks sudo only for package
and APT repository changes. The application menu entry uses Kitty when installed,
with the selected Nerd Font; otherwise it uses your desktop's configured terminal.
On a headless machine, run `yazi` in your existing terminal.
You can also run `~/.local/bin/yazi-launcher [directory]`.
The Linux entry point performs the same full setup as the Windows batch file:
Yazi, dependencies, font, theme menu, keymap prompt, previews and application entry.
Pass `--configure-only` first to skip package installation, or `--check-previews`
for read-only diagnostics. Other options are forwarded to `setup.py`:
`sh ./install.sh --theme tokyo-night --merge-keymap` is an unattended full install.
Unavailable optional Linux packages are reported individually while setup continues.

Dependencies include file, 7-Zip, zip/unzip, FFmpeg, jq, Poppler, fd, ripgrep,
fzf, zoxide, ImageMagick, Kitty, fontconfig, xdg-utils, and X11/Wayland clipboard tools. Setup supplies
an `fd` wrapper on distributions that call it `fdfind`. Add `~/.local/bin` to your
PATH to use that wrapper when launching Yazi directly; the launcher adds it.
SVG preview uses **resvg**. When missing, setup installs a checksum-verified
upstream x86-64 binary on Windows/Linux. Other CPUs need a native resvg package
(Arch installs its package automatically). A checksum-verified Nerd Font is
installed for the current user; other terminal profiles are left unchanged.

## Icons, themes and previews

Squares in place of file/folder icons mean the selected terminal font lacks the
Nerd Font glyphs. A Yazi theme changes colors; it cannot supply missing glyphs.
The dedicated **Yazi Setup** Windows Terminal profile selects
**CaskaydiaMono Nerd Font Mono**. Launching `yazi` in another profile still uses
that profile's font; select a Nerd Font in that terminal as well.

Theme choices are **Keep existing**, **Tokyo Night**, **Catppuccin Mocha**, and
**Default**. The batch installer shows the menu; command-line installs keep the
existing theme unless a choice is supplied:

```sh
python setup.py --theme choose
python setup.py --theme tokyo-night
python setup.py --theme catppuccin-mocha
```

PowerShell equivalents: `-Theme choose`, `-Theme tokyo-night`, `-Theme default`.
Theme downloads use pinned upstream revisions. Setup backs up theme.toml and
preserves custom sections; existing custom colors can override a flavor.
No existing terminal profile's font or global Terminal settings are changed.

Font options: `--install-font` installs just the Nerd Font, `--skip-font` skips
font installation, and `--font-face "Your Nerd Font Family"` selects an existing
font in the Yazi launcher's profile. PowerShell uses `-InstallFont`, `-SkipFont`,
and `-FontFace`. Installing dependencies includes the default font unless skipped.
For example, use `python setup.py --install-font --theme tokyo-night` to repair
icons and change themes without reinstalling dependencies.

| Preview | What a new machine needs |
| --- | --- |
| Text and MIME detection | `file`; Git for Windows plus `YAZI_FILE_ONE` on Windows |
| PNG/JPEG and other standard images | Yazi's built-in decoder and a compatible terminal |
| PDF thumbnail | Poppler's `pdftoppm` and a compatible terminal |
| Video thumbnail | FFmpeg and ffprobe, plus a compatible terminal |
| Archive listing | 7-Zip (`7z` or `7zz`) |
| SVG thumbnail | resvg and a compatible terminal |
| Additional font/HEIC/JXL previews | ImageMagick 7.1.1+ with the relevant codecs |

Image display requires **Windows Terminal 1.22.10352.0+**, current Kitty, or another
supported terminal. Dependency installs upgrade an older detected Windows Terminal.
To upgrade manually:
`winget upgrade -e --id Microsoft.WindowsTerminal --source winget`.
SSH, tmux, WSL, and an unsupported terminal can still require separate terminal
configuration. Do not override TERM/TERM_PROGRAM to force an image protocol.
Some Linux repositories provide ImageMagick 6; standard Yazi image previews work,
but the additional formats need ImageMagick 7 installed separately.

Dependency installs automatically exercise MIME detection and thumbnail tools on
temporary samples. A failure returns exit code 2 with a summary instead of claiming
all previews are ready. You can rerun the read-only checks without changing setup:

```sh
python setup.py --check-previews
python scripts/check_previews.py --json
```

These checks verify the tools' actual output. Visual display still depends on the
terminal. Run `ya env` from inside Yazi's shell to inspect its detected adapter.
Font, SVG renderer, and theme downloads use HTTPS with fixed SHA-256 checksums.

## Keys

Default Yazi bindings remain available. These bindings take precedence:

| Key | Action |
| --- | --- |
| `c z` | Create ZIP from selected files/directories, or the hovered item |
| `u z` | Extract hovered archive with Yazi/7-Zip (ZIP, 7z, tar, and other supported formats) |
| `u Z` | Extract a standard ZIP into a chosen new folder |
| `g d` | Downloads |
| `g a` | Work (`~/Work`; change the binding if your folder differs) |
| `g c` | Code (`~/OneDrive/Code` on Windows; `~/Desktop/code` on Linux) |
| `g z` | Documents |
| `g s` | Yazi configuration |
| `R` | Rename filename, keeping its extension |
| `u o` | Open the current directory in the desktop file manager |
| `g p` | Helper scripts (Windows) |
| `<Ctrl-n> x`, `<Ctrl-n> w`, `<Ctrl-n> p` | New Excel, Word, PowerPoint from templates (Windows) |
| `c a` | Copy the hovered file to the OS clipboard (Windows, Wayland, or X11) |
| `, d` | Modified time descending, without directories first |
| `Enter` | Linux: open hovered directories in VS Code, open files normally |

`u z` uses Yazi's built-in extractor and its normal unique-destination behavior;
it does not use the old shared temporary file or a hand-built PowerShell command.
It needs working `ya` and `7z`/`7zz` commands. Press `w` to inspect extraction tasks.
`c z` and `u Z` prompt inside Yazi for a new filename or destination folder, relative
to the current directory (absolute paths also work). For ZIP creation, include
`.zip` in the name. Existing files and folders are never overwritten. Nested and
empty directories and Unicode names are supported. Symbolic links and unsafe
ZIP paths are rejected. Standard ZIP files are supported, including ZIP64;
encrypted ZIPs and other archive formats are outside the Python-based `u Z`
action; use `u z` for those. Reference keymaps are included in
`yazi-config/keymap-windows.toml` and `yazi-config/keymap-linux.toml`.

Linux `Enter` uses the included `code-enter` plugin. Install VS Code's `code`
command to open directories in it; if unavailable, the plugin enters the directory
normally and shows a message. `l` / Right Arrow always enter a directory in Yazi.
An existing custom `code-enter` implementation is kept. Clipboard actions pass
paths as arguments and encode file URIs correctly for spaces/Unicode.

Useful bindings already provided by Yazi are retained: `.` toggles hidden files,
`s` searches filenames, `S` searches contents, `z` opens fzf, `Z` opens zoxide,
`y`/`x`/`p` copy/cut/paste, `c c` copies paths, `t t` opens a tab, `w` shows tasks,
and `~` / F1 opens help. Office shortcuts use Ctrl-n so they do not steal the
default `n` (next find result). Existing older `n x`/`n w`/`n p` mappings are kept.

Office shortcuts require your own blank `blank.xlsx`, `blank.docx`, and
`blank.pptx` in `%USERPROFILE%\User-Templates`. Existing Windows helper scripts
remain in `scripts`; they are copied to `%USERPROFILE%\Scripts`. The old
`yazi-extract-from-temp.ps1` remains for manual legacy use, but the new unzip
bindings use the built-in extractor or the bundled direct-argument plugin instead.

## Configuration and updates

Configuration goes to `%APPDATA%\yazi\config` on Windows and
`${XDG_CONFIG_HOME:-~/.config}/yazi` on Linux. `YAZI_CONFIG_HOME` overrides either.
Changed files receive timestamped `.backup-*` copies. If a keymap already exists,
setup asks whether to merge missing shortcuts. Answering no keeps that keymap
unchanged. Existing actions are never overwritten, including actions in an older
managed block. Different actions and overlapping key prefixes are reported after
installation; those bindings remain yours. A conflicting old unzip binding can
therefore remain in place: inspect the report and choose whether to replace it
manually with `shell -- ya pub extract --list %h`.
The older `plugin setup-archive extract` binding is also supported: the updated
plugin forwards that action to Yazi's built-in extractor, so retaining that older
binding does not retain the ZIP-only implementation.

Both inline `prepend_keymap = [...]` arrays and `[[mgr.prepend_keymap]]` tables are
supported. Existing full `keymap` and `append_keymap` mappings are respected, with
OS-specific scopes considered. Repeated installs do not duplicate shortcuts.
Invalid TOML or incomplete managed markers stop setup before configuration writes.
For unattended installs, `--merge-keymap` / PowerShell `-MergeKeymap` grants the
missing-only merge without a prompt. Non-interactive installs otherwise keep an
existing keymap unchanged. `--skip-keymap` / `-SkipKeymap` skips merging entirely.

Useful options, passed to `python setup.py` or `sh ./install.sh`:

```sh
python setup.py --dry-run
python setup.py --skip-launcher
python setup.py --skip-keymap
python setup.py --merge-keymap
```

The PowerShell wrapper also accepts `-DryRun`, `-SkipLauncher`, and `-SkipKeymap`.
Without install flags, setup changes configuration/launcher files only. Package
install flags install missing tools and update Yazi or Windows Terminal if below
the required version. Other existing dependencies are left at their installed versions.
The final dependency report lists missing tools. Preview tools are optional for
ZIP creation/extraction, which uses the Python interpreter recorded at install
time. Rerun setup if Python is moved or removed.

To remove only the Windows launcher, run
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\launcher\windows\uninstall.ps1`
and unpin it manually. On Linux remove `~/.local/bin/yazi-launcher` and
`${XDG_DATA_HOME:-~/.local/share}/applications/yazi-launcher.desktop`.
To undo configuration changes, restore the backups or remove the marked keymap
additions and `plugins/setup-archive.yazi`. Dependencies remain installed.

## Verification

If winget reports `InternetOpenUrl() failed` with `0x80072ee7`, it could not
resolve the download server name. Check the connection, DNS, VPN or proxy and
retry. Setup detects 7-Zip in standard Program Files locations even when it is
absent from PATH, so an installed copy does not need downloading again.
Optional package failures allow configuration and launcher setup to continue;
the final report prints retry commands and setup exits with code 2 for incomplete
dependencies. Failures installing Yazi or Windows Terminal still stop setup.

```sh
python -m unittest discover -s tests -v
```

Tests use Python 3.11+ for TOML validation. They cover ZIP round trips, overwrite
refusal, unsafe ZIP paths, Unicode filenames, keymap migration and repeatability,
and both platforms' generated configuration. CI runs these on Windows and Linux
and compiles the Windows launcher. Windows checks also exercise helper scripts
with dots/brackets in filenames and validate launcher argument quoting.
GUI/taskbar behavior and native package
installation should also be checked on the target machine.
The fresh-Linux CI job uses the Linux installer, runs real preview checks, and
exercises ZIP/unzip keys in an actual Yazi PTY session. It can also be run manually
with `python tests/smoke_yazi_linux.py` after installation. Mocked clean-machine tests hide the developer machine's tools to
verify that the installation plan includes all required packages.

References: [Yazi installation](https://yazi-rs.github.io/docs/installation/),
[keymap reference](https://yazi-rs.github.io/docs/configuration/keymap/), and
[plugin API](https://yazi-rs.github.io/docs/plugins/utils/).
Icon and terminal references: [Yazi FAQ](https://yazi-rs.github.io/docs/faq/),
[image preview support](https://yazi-rs.github.io/docs/image-preview/),
[Terminal fragment profiles](https://learn.microsoft.com/en-us/windows/terminal/json-fragment-extensions).
Themes: [Tokyo Night](https://github.com/BennyOe/tokyo-night.yazi),
[Catppuccin flavors](https://github.com/yazi-rs/flavors).
