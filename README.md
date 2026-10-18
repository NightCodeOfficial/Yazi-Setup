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
sh ./install.sh --install-yazi --install-dependencies --theme choose
```

Automatic package installation supports Debian/Ubuntu (`apt-get`), Fedora
(`dnf`), and Arch (`pacman`). Debian/Ubuntu setup adds the official Yazi stable
APT repository, which publishes amd64/arm64 builds. Fedora needs a repository
providing Yazi enabled first; see the official installation guide below. Other
distributions can install Yazi and dependencies manually, then run:

```sh
sh ./install.sh
```

Run setup as your normal user, not through `sudo`; it asks sudo only for package
and APT repository changes. The application menu entry uses Kitty when installed,
with the selected Nerd Font; otherwise it uses your desktop's configured terminal.
On a headless machine, run `yazi` in your existing terminal.
You can also run `~/.local/bin/yazi-launcher [directory]`.

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
| `u z` | Extract hovered ZIP into a new folder |
| `g d` | Downloads |
| `g z` | Documents |
| `g s` | Yazi configuration |
| `R` | Rename filename, keeping its extension |
| `u o` | Open the current directory in the desktop file manager |
| `g p` | Helper scripts (Windows) |
| `n x`, `n w`, `n p` | New Excel, Word, PowerPoint from templates (Windows) |
| `c a` | Copy the actual hovered file to Windows clipboard |

ZIP actions prompt inside Yazi for a new filename or destination folder, relative
to the current directory (absolute paths also work). For ZIP creation, include
`.zip` in the name. Existing files and folders are never overwritten. Nested and
empty directories and Unicode names are supported. Symbolic links and unsafe
ZIP paths are rejected. Standard ZIP files are supported, including ZIP64;
encrypted ZIPs and other archive formats are outside these custom ZIP actions.
Yazi's built-in archive browsing/opening still uses 7-Zip for other formats.

Office shortcuts require your own blank `blank.xlsx`, `blank.docx`, and
`blank.pptx` in `%USERPROFILE%\User-Templates`. Existing Windows helper scripts
remain in `scripts`; they are copied to `%USERPROFILE%\Scripts`. The old
`yazi-extract-from-temp.ps1` remains for manual legacy use, but the new unzip
binding uses the bundled plugin instead.

## Configuration and updates

Configuration goes to `%APPDATA%\yazi\config` on Windows and
`${XDG_CONFIG_HOME:-~/.config}/yazi` on Linux. `YAZI_CONFIG_HOME` overrides either.
Changed files receive timestamped `.backup-*` copies. Rerunning setup updates
its managed keymap block (including migrating the old Windows Scripts block),
keeps other keymap entries, and avoids duplicate blocks. Partial/duplicate
managed markers or invalid TOML stop setup before configuration files are written.
For an existing `[mgr] prepend_keymap = [...]` inline array, convert its entries
to `[[mgr.prepend_keymap]]` tables before merging, or use `--skip-keymap`.
Check existing custom keys
for conflicts with the table above.

Useful options, passed to `python setup.py` or `sh ./install.sh`:

```sh
python setup.py --dry-run
python setup.py --skip-launcher
python setup.py --skip-keymap
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
block and `plugins/setup-archive.yazi`. Dependencies remain installed.

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
The fresh-Linux CI job installs Yazi and dependencies before running real preview
smoke tests. Mocked clean-machine tests hide the developer machine's tools to
verify that the installation plan includes all required packages.

References: [Yazi installation](https://yazi-rs.github.io/docs/installation/),
[keymap reference](https://yazi-rs.github.io/docs/configuration/keymap/), and
[plugin API](https://yazi-rs.github.io/docs/plugins/utils/).
Icon and terminal references: [Yazi FAQ](https://yazi-rs.github.io/docs/faq/),
[image preview support](https://yazi-rs.github.io/docs/image-preview/),
[Terminal fragment profiles](https://learn.microsoft.com/en-us/windows/terminal/json-fragment-extensions).
Themes: [Tokyo Night](https://github.com/BennyOe/tokyo-night.yazi),
[Catppuccin flavors](https://github.com/yazi-rs/flavors).
