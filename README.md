# Yazi Setup + Launcher

One project for Windows and Linux: Yazi dependencies, custom keybindings, ZIP
creation/extraction, and an application launcher. The Windows launcher source
and icon are included under `launcher/windows`; the separate launcher project
is no longer needed to install this package.

Requires **Python 3.10+** and **Yazi 26.9.1 or newer** for the bundled plugin API.
No pip packages are required. Run setup as your normal user. Linux package
installation uses sudo; Windows package installers may request elevation.

## Windows

1. Extract or clone this project.
2. If Python is missing, run `winget install -e --id Python.Python.3.13`, then
   reopen your terminal.
3. Double-click **Install Yazi Scripts.bat**. It installs missing Yazi and
   dependency packages, adds the configuration, builds the launcher, and creates
   **Yazi Launcher** in Start.
4. Close and reopen your terminal / sign out and back in to refresh environment
   variables, then launch **Yazi Launcher**. Pin its Start shortcut to the taskbar.

Equivalent command from the project directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\yazi-installer.ps1 -InstallYazi -InstallDependencies
```

Windows Terminal and .NET Framework's C# compiler are needed for the launcher.
The installer uses winget for Terminal, Yazi, Git for Windows, 7-Zip, FFmpeg, jq,
Poppler, fd, ripgrep, fzf, zoxide, and ImageMagick when commands are missing.
It adds the standard 7-Zip directory to your user PATH and configures
`YAZI_FILE_ONE` when Git is in its standard Program Files location. With a custom
Git installation, set that variable to its `usr\bin\file.exe` yourself.

The launcher retains its separate Windows taskbar identity, custom icon, new
Terminal window behavior, and logging at `%LOCALAPPDATA%\YaziLauncher\launcher.log`.
Setup does not open Yazi automatically.

## Linux

Install Python 3.10+ using your distribution's package manager, then run:

```sh
sh ./install.sh --install-yazi --install-dependencies
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
and APT repository changes. The application menu entry uses your desktop's
configured terminal. On a headless machine, run `yazi` in your existing terminal.
You can also run `~/.local/bin/yazi-launcher [directory]`.

Dependencies include file, 7-Zip, zip/unzip, FFmpeg, jq, Poppler, fd, ripgrep,
fzf, zoxide, ImageMagick, xdg-utils, and X11/Wayland clipboard tools. Setup supplies
an `fd` wrapper on distributions that call it `fdfind`. Add `~/.local/bin` to your
PATH to use that wrapper when launching Yazi directly; the launcher adds it.
SVG preview needs **resvg**, installed automatically on Arch; install it
separately on other distributions. Windows winget does not currently provide
resvg. A Nerd Font is also recommended for icons.

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
managed markers stop setup with a repair message. Check existing custom keys
for conflicts with the table above.

Useful options, passed to `python setup.py` or `sh ./install.sh`:

```sh
python setup.py --dry-run
python setup.py --skip-launcher
python setup.py --skip-keymap
```

The PowerShell wrapper also accepts `-DryRun`, `-SkipLauncher`, and `-SkipKeymap`.
Without install flags, setup changes configuration/launcher files only. Package
install flags install missing tools and update Yazi if it is below the required
version. Other existing dependencies are left at their installed versions.
The final dependency report lists missing tools. Preview tools are optional for
ZIP creation/extraction, which uses the Python interpreter recorded at install
time. Rerun setup if Python is moved or removed. Theme setup is optional; see
`yazi-config/theme-example.toml` and install matching flavors before enabling it.

To remove only the Windows launcher, run
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\launcher\windows\uninstall.ps1`
and unpin it manually. On Linux remove `~/.local/bin/yazi-launcher` and
`${XDG_DATA_HOME:-~/.local/share}/applications/yazi-launcher.desktop`.
To undo configuration changes, restore the backups or remove the marked keymap
block and `plugins/setup-archive.yazi`. Dependencies remain installed.

## Verification

```sh
python -m unittest discover -s tests -v
```

Tests use Python 3.11+ for TOML validation. They cover ZIP round trips, overwrite
refusal, unsafe ZIP paths, Unicode filenames, keymap migration and repeatability,
and both platforms' generated configuration. CI runs these on Windows and Linux
and compiles the Windows launcher. GUI/taskbar behavior and native package
installation should also be checked on the target machine.

References: [Yazi installation](https://yazi-rs.github.io/docs/installation/),
[keymap reference](https://yazi-rs.github.io/docs/configuration/keymap/), and
[plugin API](https://yazi-rs.github.io/docs/plugins/utils/).
