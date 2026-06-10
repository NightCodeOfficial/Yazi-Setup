# Yazi Windows Scripts

Windows helper scripts and keybindings for the [Yazi](https://yazi-rs.github.io/) terminal file manager.

This package is designed for normal Windows user accounts. It installs helper PowerShell scripts into your user profile and can optionally add the included keybindings to your Yazi config.

## Simple Install Method

1. Extract the ZIP.
2. Double-click:

```txt
Install Yazi Scripts.bat
```

The installer will:

- Create `%USERPROFILE%\Scripts`
- Create `%USERPROFILE%\User-Templates`
- Create `%APPDATA%\yazi\config`
- Create `%APPDATA%\yazi\config\flavors`
- Copy the helper scripts into `%USERPROFILE%\Scripts`
- Ask to install Yazi if it is missing
- Ask to install recommended Yazi dependencies
- Safely add the keybindings to `keymap.toml`
- Open the template folder so you can add blank Office templates

## Manual Install Command

From the extracted package folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\yazi-installer.ps1
```

Installer flags:

```powershell
# Preview what would happen without changing files
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\yazi-installer.ps1 -DryRun

# Install Yazi without prompting, if missing
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\yazi-installer.ps1 -InstallYazi

# Install recommended dependencies without prompting
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\yazi-installer.ps1 -InstallDependencies

# Install scripts but skip keymap changes
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\yazi-installer.ps1 -SkipKeymap
```

## Yazi Installation

If Yazi is missing, the installer can install it using winget:

```powershell
winget install --id sxyazi.yazi -e
```

The installer will also ask to install recommended optional dependencies:

```powershell
winget install --id Gyan.FFmpeg -e
winget install --id 7zip.7zip -e
winget install --id jqlang.jq -e
winget install --id oschwartz10612.Poppler -e
winget install --id sharkdp.fd -e
winget install --id BurntSushi.ripgrep.MSVC -e
winget install --id junegunn.fzf -e
winget install --id ajeetdsouza.zoxide -e
winget install --id ImageMagick.ImageMagick -e
```


## Office Template Files

The `new-office-file.ps1` helper creates new Office files by copying blank template files.

You will need to create these template files.

After installation, place these files in:

```txt
%USERPROFILE%\User-Templates
```

Manually create these files:

```txt
blank.docx
blank.xlsx
blank.pptx
```


## Installed Helper Scripts

The installer copies these files to `%USERPROFILE%\Scripts`:

```txt
new-office-file.ps1
move-most-recent-file.ps1
move-png-from-downloads.ps1
yazi-copy-actual-file.ps1
yazi-extract-from-temp.ps1
```

## Keybindings

The installer can add the included keybindings to:

```txt
%APPDATA%\yazi\config\keymap.toml
```

If `keymap.toml` already exists, the installer creates a timestamped backup before appending the managed block.

The managed block is marked with:

```toml
# >>> Yazi Windows Scripts keybindings >>>
# <<< Yazi Windows Scripts keybindings <<<
```

This prevents duplicate installs if you run the installer again.

Included bindings:

| Binding | Action |
|---|---|
| `g d` | Go to Downloads |
| `g z` | Go to Documents |
| `g p` | Go to Scripts |
| `g s` | Go to Yazi settings |
| `n x` | Create new Excel workbook |
| `n w` | Create new Word document |
| `n p` | Create new PowerPoint presentation |
| `R` | Rename filename without changing extension |
| `u z` | Extract hovered archive |
| `u o` | Open current directory in Explorer |
| `c a` | Copy actual hovered file to Windows clipboard |

## Themes and Flavors

Yazi supports custom colors through `theme.toml` and pre-made themes called **flavors**.

On Windows, Yazi config files are stored here:

```txt
%APPDATA%\yazi\config
```

Flavors should be installed into:

```txt
%APPDATA%\yazi\config\flavors
```

Example structure:

```txt
%APPDATA%\yazi\config\
├─ theme.toml
└─ flavors\
   └─ catppuccin-mocha.yazi\
      ├─ flavor.toml
      ├─ tmtheme.xml
      ├─ README.md
      └─ preview.png
```

To enable a flavor, edit:

```txt
%APPDATA%\yazi\config\theme.toml
```

Example:

```toml
[flavor]
dark  = "catppuccin-mocha"
light = "catppuccin-latte"
```

A sample file is included at:

```txt
yazi-config\theme-example.toml
```

The installer creates the `flavors` folder, but it does not install a theme by default.

## Official Yazi Documentation

Useful Yazi links:

- Official Yazi site/docs: https://yazi-rs.github.io/
- Installation guide: https://yazi-rs.github.io/docs/installation/
- Configuration overview: https://yazi-rs.github.io/docs/configuration/overview/
- Keymap documentation: https://yazi-rs.github.io/docs/configuration/keymap/
- Theme documentation: https://yazi-rs.github.io/docs/configuration/theme/
- Flavors overview: https://yazi-rs.github.io/docs/flavors/overview/
- Official flavors repository: https://github.com/yazi-rs/flavors
- Yazi GitHub repository: https://github.com/sxyazi/yazi
- WinGet documentation: https://learn.microsoft.com/windows/package-manager/winget/

## Additional Consideration

- This package is Windows-only as it is powershell focused.
- If PowerShell opens in `C:\Windows\System32`, run the included `.bat` launcher as a user account instead.
- After installing Yazi or dependencies with winget, close and reopen your terminal if commands are not immediately found.
