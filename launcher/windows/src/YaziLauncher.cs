using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

[assembly: AssemblyTitle("Yazi Launcher")]
[assembly: AssemblyDescription("Launches Yazi in Windows Terminal under a separate taskbar identity.")]
[assembly: AssemblyCompany("")]
[assembly: AssemblyProduct("Yazi Launcher")]
[assembly: AssemblyVersion("0.1.4.0")]
[assembly: AssemblyFileVersion("0.1.4.0")]

namespace YaziLauncher
{
    internal static class Program
    {
        private const string AppUserModelId = "YaziLauncher.PowerShell";
        private const string WindowTitle = "Yazi";
        private const int TerminalWindowWaitMs = 25000;
        private const int PollIntervalMs = 75;
        private const int WindowRetryIntervalMs = 200;
        private const int SingleNewWindowFallbackMs = 4500;
        private const int IdentityConfirmationMs = 4000;
        private const int InvalidWindowHandleHr = unchecked((int)0x80070578);
        private const int InvalidHandleHr = unchecked((int)0x80070006);

        private static readonly Guid AppUserModelPropertySet = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");
        private static readonly PROPERTYKEY PkeyRelaunchCommand = new PROPERTYKEY(AppUserModelPropertySet, 2);
        private static readonly PROPERTYKEY PkeyRelaunchIconResource = new PROPERTYKEY(AppUserModelPropertySet, 3);
        private static readonly PROPERTYKEY PkeyRelaunchDisplayName = new PROPERTYKEY(AppUserModelPropertySet, 4);
        private static readonly PROPERTYKEY PkeyAppUserModelId = new PROPERTYKEY(AppUserModelPropertySet, 5);

        [STAThread]
        private static int Main(string[] args)
        {
            try
            {
                if (args.Length > 0 && string.Equals(args[0], "--set-shortcut-appid", StringComparison.OrdinalIgnoreCase))
                {
                    if (args.Length < 2 || string.IsNullOrWhiteSpace(args[1]))
                    {
                        Log("--set-shortcut-appid was called without a shortcut path.");
                        return 2;
                    }

                    SetShortcutAppId(args[1]);
                    Log("Tagged Start Menu shortcut with AppUserModelID: " + args[1]);
                    return 0;
                }

                int processAppIdResult = SetCurrentProcessExplicitAppUserModelID(AppUserModelId);
                if (processAppIdResult < 0)
                {
                    Marshal.ThrowExceptionForHR(processAppIdResult);
                }

                return LaunchYazi();
            }
            catch (Exception ex)
            {
                Log("Fatal error: " + ex);
                ShowError("Yazi Launcher could not start.\n\n" + ex.Message + "\n\nLog: " + GetLogPath());
                return 1;
            }
        }

        private static int LaunchYazi()
        {
            string terminalPath = FindWindowsTerminal();
            if (string.IsNullOrEmpty(terminalPath))
            {
                throw new FileNotFoundException("Windows Terminal (wt.exe) was not found. Install Windows Terminal or restore its App Execution Alias.");
            }

            string shellPath = FindPowerShell();
            string yaziPath = FindYazi();
            if (string.IsNullOrEmpty(yaziPath))
            {
                throw new FileNotFoundException(
                    "Yazi (yazi.exe) was not found. Install Yazi, then reopen setup.bat or make sure yazi.exe is available in PATH / your Windows app aliases.");
            }

            string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            if (string.IsNullOrEmpty(home))
            {
                home = Environment.CurrentDirectory;
            }

            Log("Runtime: " + Environment.OSVersion +
                ", 64-bit OS=" + Environment.Is64BitOperatingSystem +
                ", 64-bit process=" + Environment.Is64BitProcess + ".");
            Log("Resolved Windows Terminal: " + terminalPath);
            Log("Resolved shell: " + shellPath);
            Log("Resolved Yazi: " + yaziPath);

            // Snapshot the real Terminal host windows before launch. A newer Terminal build can
            // recycle/replace HWNDs during startup, so we also keep each initial title and allow
            // a pre-existing host to become the launch target if it changes to the requested Yazi title.
            Dictionary<string, string> initialTerminalWindows = GetTerminalWindowSnapshot();
            Log("Existing Windows Terminal host windows: " + initialTerminalWindows.Count + ".");

            string shellCommand = "& " + QuotePowerShellLiteral(yaziPath);
            string arguments =
                "-w new nt " +
                "-d " + Quote(home) + " " +
                "--title " + Quote(WindowTitle) + " " +
                "--suppressApplicationTitle " +
                Quote(shellPath) + " -NoLogo -NoExit -Command " + Quote(shellCommand);

            Log("Launching: " + terminalPath + " " + arguments);

            ProcessStartInfo startInfo = new ProcessStartInfo();
            startInfo.FileName = terminalPath;
            startInfo.Arguments = arguments;
            startInfo.WorkingDirectory = home;
            startInfo.UseShellExecute = false;
            startInfo.CreateNoWindow = true;

            Process process = Process.Start(startInfo);
            if (process != null)
            {
                process.Dispose();
            }

            if (!WaitForAndConfigureNewTerminalWindow(initialTerminalWindows, TerminalWindowWaitMs))
            {
                ShowWarning(
                    "Yazi may have opened, but the launcher could not attach the Yazi Launcher taskbar identity to the final Windows Terminal host window.\n\n" +
                    "Log: " + GetLogPath());
                return 3;
            }

            return 0;
        }

        private static void ConfigureTerminalWindow(TerminalWindow window)
        {
            EnsureWindowStillBelongsToProcess(window);

            Guid propertyStoreGuid = typeof(IPropertyStore).GUID;
            IPropertyStore store = null;

            try
            {
                int hr = SHGetPropertyStoreForWindow(window.Handle, ref propertyStoreGuid, out store);
                if (hr < 0)
                {
                    Marshal.ThrowExceptionForHR(hr);
                }

                EnsureWindowStillBelongsToProcess(window);

                string executablePath = Assembly.GetExecutingAssembly().Location;
                string iconPath = Path.Combine(Path.GetDirectoryName(executablePath) ?? string.Empty, "yazi.ico");
                string relaunchCommand = Quote(executablePath);

                // Microsoft recommends setting relaunch metadata before the AppUserModelID.
                SetStringProperty(store, PkeyRelaunchCommand, relaunchCommand);
                SetStringProperty(store, PkeyRelaunchDisplayName, "Yazi");

                if (File.Exists(iconPath))
                {
                    SetStringProperty(store, PkeyRelaunchIconResource, iconPath + ",0");
                }

                // Set the ID last so the taskbar refresh sees all of the metadata above.
                EnsureWindowStillBelongsToProcess(window);
                SetStringProperty(store, PkeyAppUserModelId, AppUserModelId);
                EnsureWindowStillBelongsToProcess(window);
            }
            finally
            {
                if (store != null && Marshal.IsComObject(store))
                {
                    Marshal.ReleaseComObject(store);
                }
            }
        }

        private static void SetShortcutAppId(string shortcutPath)
        {
            shortcutPath = Path.GetFullPath(shortcutPath);
            if (!File.Exists(shortcutPath))
            {
                throw new FileNotFoundException("The shortcut was not found.", shortcutPath);
            }

            Guid propertyStoreGuid = typeof(IPropertyStore).GUID;
            IPropertyStore store;
            int hr = SHGetPropertyStoreFromParsingName(shortcutPath, IntPtr.Zero, GETPROPERTYSTOREFLAGS.GPS_READWRITE, ref propertyStoreGuid, out store);
            if (hr < 0)
            {
                Marshal.ThrowExceptionForHR(hr);
            }

            try
            {
                SetStringProperty(store, PkeyAppUserModelId, AppUserModelId);
                hr = store.Commit();
                if (hr < 0)
                {
                    Marshal.ThrowExceptionForHR(hr);
                }
            }
            finally
            {
                if (store != null && Marshal.IsComObject(store))
                {
                    Marshal.ReleaseComObject(store);
                }
            }
        }

        private static void SetStringProperty(IPropertyStore store, PROPERTYKEY key, string value)
        {
            PROPVARIANT propVariant = PROPVARIANT.FromString(value);
            try
            {
                int hr = store.SetValue(ref key, ref propVariant);
                if (hr < 0)
                {
                    Marshal.ThrowExceptionForHR(hr);
                }
            }
            finally
            {
                PropVariantClear(ref propVariant);
            }
        }

        private static string GetWindowAppUserModelId(IntPtr windowHandle)
        {
            Guid propertyStoreGuid = typeof(IPropertyStore).GUID;
            IPropertyStore store = null;
            PROPVARIANT value = new PROPVARIANT();

            try
            {
                int hr = SHGetPropertyStoreForWindow(windowHandle, ref propertyStoreGuid, out store);
                if (hr < 0)
                {
                    Marshal.ThrowExceptionForHR(hr);
                }

                PROPERTYKEY key = PkeyAppUserModelId;
                hr = store.GetValue(ref key, out value);
                if (hr < 0)
                {
                    Marshal.ThrowExceptionForHR(hr);
                }

                if (value.vt == 31 && value.pointerValue != IntPtr.Zero)
                {
                    return Marshal.PtrToStringUni(value.pointerValue);
                }

                return null;
            }
            finally
            {
                PropVariantClear(ref value);
                if (store != null && Marshal.IsComObject(store))
                {
                    Marshal.ReleaseComObject(store);
                }
            }
        }

        private sealed class TerminalWindow
        {
            internal IntPtr Handle;
            internal uint ProcessId;
            internal string ClassName;
            internal string Title;
            internal bool Visible;

            internal string Key
            {
                get { return ProcessId + ":" + Handle.ToInt64().ToString("X"); }
            }

            internal string Description
            {
                get { return "HWND 0x" + Handle.ToInt64().ToString("X") + ", PID " + ProcessId; }
            }
        }

        private static bool WaitForAndConfigureNewTerminalWindow(Dictionary<string, string> initialWindows, int timeoutMs)
        {
            Stopwatch stopwatch = Stopwatch.StartNew();
            Dictionary<string, long> lastAttemptAtMs = new Dictionary<string, long>();
            HashSet<string> loggedCandidates = new HashSet<string>();
            string lastTransientFailure = null;

            while (stopwatch.ElapsedMilliseconds < timeoutMs)
            {
                long now = stopwatch.ElapsedMilliseconds;
                List<TerminalWindow> current = GetTerminalWindows();
                List<TerminalWindow> matching = new List<TerminalWindow>();
                List<TerminalWindow> launchChangedHosts = new List<TerminalWindow>();

                foreach (TerminalWindow window in current)
                {
                    if (!window.Visible || !IsWindowOwnedByProcess(window))
                    {
                        continue;
                    }

                    string initialTitle;
                    bool existedBeforeLaunch = initialWindows.TryGetValue(window.Key, out initialTitle);
                    bool becameYazi = existedBeforeLaunch &&
                                      !HasYaziTitle(initialTitle) &&
                                      HasYaziTitle(window.Title);
                    bool newHost = !existedBeforeLaunch;

                    bool changedExistingHost = existedBeforeLaunch &&
                                               !string.Equals(initialTitle ?? string.Empty, window.Title ?? string.Empty, StringComparison.Ordinal);

                    if (newHost || changedExistingHost)
                    {
                        launchChangedHosts.Add(window);
                    }

                    if ((newHost || becameYazi) && HasYaziTitle(window.Title))
                    {
                        matching.Add(window);
                    }

                    if ((newHost || becameYazi) && loggedCandidates.Add(window.Key))
                    {
                        Log("Observed Terminal host candidate: " + window.Description +
                            ", class '" + window.ClassName + "', title '" + window.Title + "'.");
                    }
                }

                TerminalWindow selected = null;
                bool fallback = false;

                if (matching.Count == 1)
                {
                    selected = matching[0];
                }
                else if (matching.Count == 0 &&
                         now >= SingleNewWindowFallbackMs &&
                         launchChangedHosts.Count == 1)
                {
                    // Newer Terminal builds can briefly replace a correctly titled CASCADIA window
                    // with another host whose title regresses to cmd.exe/Windows Terminal, and can
                    // occasionally recycle an existing host HWND. Because wt.exe was explicitly asked
                    // for a new window, one host that is new or changed since launch is a safer fallback
                    // than waiting forever for a title that may never return.
                    selected = launchChangedHosts[0];
                    fallback = true;
                }

                if (selected != null)
                {
                    long previousAttempt;
                    if (!lastAttemptAtMs.TryGetValue(selected.Key, out previousAttempt) ||
                        now - previousAttempt >= WindowRetryIntervalMs)
                    {
                        lastAttemptAtMs[selected.Key] = now;

                        try
                        {
                            if (fallback)
                            {
                                Log("Using the single launch-changed Terminal host despite title '" +
                                    selected.Title + "': " + selected.Description + ".");
                            }

                            ConfigureTerminalWindow(selected);
                            string observedAppId = GetWindowAppUserModelId(selected.Handle);
                            if (!string.Equals(observedAppId, AppUserModelId, StringComparison.Ordinal))
                            {
                                Log("Terminal host did not retain the requested AppUserModelID; observed '" +
                                    (observedAppId ?? "<none>") + "' on " + selected.Description + "; retrying.");
                            }
                            else if (ConfirmTerminalWindowIdentity(selected, stopwatch, timeoutMs))
                            {
                                Log("Applied Yazi Launcher taskbar identity to final Terminal host " +
                                    selected.Description + ".");
                                return true;
                            }
                            else
                            {
                                Log("Configured Terminal host was replaced during confirmation: " +
                                    selected.Description + "; continuing discovery.");
                            }
                        }
                        catch (Exception ex)
                        {
                            int hr = Marshal.GetHRForException(ex);
                            if (hr != InvalidWindowHandleHr && hr != InvalidHandleHr)
                            {
                                Log("Non-transient taskbar configuration error for " + selected.Description + ": " + ex);
                                throw;
                            }

                            lastTransientFailure = "0x" + unchecked((uint)hr).ToString("X8");
                            Log("Terminal host changed while applying Yazi Launcher identity (" +
                                lastTransientFailure + ") for " + selected.Description + "; retrying immediately.");
                        }
                    }
                }

                Thread.Sleep(PollIntervalMs);
            }

            Log("Timed out after " + timeoutMs + " ms waiting for the final Yazi Terminal host." +
                (lastTransientFailure == null ? "" : " Last transient error: " + lastTransientFailure + ".") +
                " Yazi may still have opened, but taskbar separation was not applied.");
            return false;
        }

        private static bool ConfirmTerminalWindowIdentity(TerminalWindow window, Stopwatch launchStopwatch, int timeoutMs)
        {
            Stopwatch confirmation = Stopwatch.StartNew();

            while (confirmation.ElapsedMilliseconds < IdentityConfirmationMs &&
                   launchStopwatch.ElapsedMilliseconds < timeoutMs)
            {
                if (!IsWindowOwnedByProcess(window) || !IsWindowVisible(window.Handle))
                {
                    return false;
                }

                string currentAppId;
                try
                {
                    currentAppId = GetWindowAppUserModelId(window.Handle);
                }
                catch (Exception ex)
                {
                    int hr = Marshal.GetHRForException(ex);
                    if (hr == InvalidWindowHandleHr || hr == InvalidHandleHr)
                    {
                        return false;
                    }
                    throw;
                }

                if (!string.Equals(currentAppId, AppUserModelId, StringComparison.Ordinal))
                {
                    // Reapply immediately if Terminal cleared the property without replacing the HWND.
                    ConfigureTerminalWindow(window);
                }

                Thread.Sleep(PollIntervalMs);
            }

            return IsWindowOwnedByProcess(window) &&
                   string.Equals(GetWindowAppUserModelId(window.Handle), AppUserModelId, StringComparison.Ordinal);
        }

        private static void EnsureWindowStillBelongsToProcess(TerminalWindow window)
        {
            if (!IsWindowOwnedByProcess(window))
            {
                throw new COMException("Windows Terminal replaced or closed its window before configuration completed.", InvalidWindowHandleHr);
            }
        }

        private static bool IsWindowOwnedByProcess(TerminalWindow window)
        {
            if (!IsWindow(window.Handle))
            {
                return false;
            }

            uint currentProcessId;
            GetWindowThreadProcessId(window.Handle, out currentProcessId);
            return currentProcessId != 0 && currentProcessId == window.ProcessId;
        }

        private static bool HasYaziTitle(string title)
        {
            return !string.IsNullOrEmpty(title) &&
                   title.StartsWith(WindowTitle, StringComparison.OrdinalIgnoreCase) &&
                   (title.Length == WindowTitle.Length || !char.IsLetterOrDigit(title[WindowTitle.Length]));
        }


        private static Dictionary<string, string> GetTerminalWindowSnapshot()
        {
            Dictionary<string, string> windows = new Dictionary<string, string>();
            foreach (TerminalWindow window in GetTerminalWindows())
            {
                windows[window.Key] = window.Title ?? string.Empty;
            }
            return windows;
        }

        private static List<TerminalWindow> GetTerminalWindows()
        {
            List<TerminalWindow> windows = new List<TerminalWindow>();
            EnumWindows(delegate(IntPtr handle, IntPtr lParam)
            {
                if (!IsWindow(handle))
                {
                    return true;
                }

                uint processId;
                GetWindowThreadProcessId(handle, out processId);
                if (processId == 0)
                {
                    return true;
                }

                StringBuilder className = new StringBuilder(256);
                GetClassName(handle, className, className.Capacity);

                // Only the Cascadia hosting window owns the actual Terminal taskbar button.
                // Treating every top-level window in the WindowsTerminal process as a candidate
                // also captures DDE, IME and hidden implementation windows and caused the recent
                // taskbar-identity regression.
                bool terminal = className.ToString().StartsWith(
                    "CASCADIA_HOSTING_WINDOW_CLASS", StringComparison.OrdinalIgnoreCase);

                if (terminal)
                {
                    windows.Add(new TerminalWindow
                    {
                        Handle = handle,
                        ProcessId = processId,
                        ClassName = className.ToString(),
                        Title = GetWindowTitle(handle),
                        Visible = IsWindowVisible(handle)
                    });
                }
                return true;
            }, IntPtr.Zero);
            return windows;
        }

        private static string GetWindowTitle(IntPtr handle)
        {
            StringBuilder title = new StringBuilder(512);
            GetWindowText(handle, title, title.Capacity);
            return title.ToString();
        }

        private static string FindWindowsTerminal()
        {
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string aliasPath = CombineIfRooted(localAppData, "Microsoft", "WindowsApps", "wt.exe");
            if (File.Exists(aliasPath))
            {
                return aliasPath;
            }

            string onPath = FindOnPath("wt.exe");
            if (!string.IsNullOrEmpty(onPath))
            {
                return onPath;
            }

            return null;
        }

        private static string FindPowerShell()
        {
            string pwsh = FindOnPath("pwsh.exe");
            if (!string.IsNullOrEmpty(pwsh))
            {
                return pwsh;
            }

            string programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            string programFilesPwsh = CombineIfRooted(programFiles, "PowerShell", "7", "pwsh.exe");
            if (File.Exists(programFilesPwsh))
            {
                return programFilesPwsh;
            }

            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string localPwsh = CombineIfRooted(localAppData, "Microsoft", "PowerShell", "7", "pwsh.exe");
            if (File.Exists(localPwsh))
            {
                return localPwsh;
            }

            string windowsPowerShell = FindOnPath("powershell.exe");
            if (!string.IsNullOrEmpty(windowsPowerShell))
            {
                return windowsPowerShell;
            }

            string systemPowerShell = CombineIfRooted(Environment.SystemDirectory, "WindowsPowerShell", "v1.0", "powershell.exe");
            if (File.Exists(systemPowerShell))
            {
                return systemPowerShell;
            }

            string windowsDirectory = Environment.GetEnvironmentVariable("WINDIR");
            string windowsPowerShellFallback = CombineIfRooted(windowsDirectory, "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
            if (File.Exists(windowsPowerShellFallback))
            {
                return windowsPowerShellFallback;
            }

            throw new FileNotFoundException("PowerShell was not found. Windows PowerShell is normally included with Windows 11; restore it or install PowerShell 7.");
        }

        private static string FindYazi()
        {
            string onPath = FindOnPath("yazi.exe");
            if (!string.IsNullOrEmpty(onPath))
            {
                return onPath;
            }

            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string windowsAppsAlias = CombineIfRooted(localAppData, "Microsoft", "WindowsApps", "yazi.exe");
            if (File.Exists(windowsAppsAlias))
            {
                return windowsAppsAlias;
            }

            string wingetLink = CombineIfRooted(localAppData, "Microsoft", "WinGet", "Links", "yazi.exe");
            if (File.Exists(wingetLink))
            {
                return wingetLink;
            }

            return null;
        }

        private static string CombineIfRooted(string root, params string[] parts)
        {
            if (string.IsNullOrWhiteSpace(root))
            {
                return string.Empty;
            }

            string result = root;
            for (int i = 0; i < parts.Length; i++)
            {
                result = Path.Combine(result, parts[i]);
            }
            return result;
        }

        private static string FindOnPath(string executableName)
        {
            string path = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
            string[] folders = path.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries);

            for (int i = 0; i < folders.Length; i++)
            {
                string folder = folders[i].Trim().Trim('"');
                if (folder.Length == 0)
                {
                    continue;
                }

                try
                {
                    string candidate = Path.Combine(folder, executableName);
                    if (File.Exists(candidate))
                    {
                        return candidate;
                    }
                }
                catch
                {
                    // Ignore malformed PATH entries and keep searching.
                }
            }

            return null;
        }

        private static string Quote(string value)
        {
            // CommandLineToArgvW rules: backslashes before quotes and at the
            // closing quote must be doubled; other path separators stay literal.
            StringBuilder result = new StringBuilder("\"");
            int slashes = 0;
            foreach (char character in value)
            {
                if (character == '\\')
                {
                    slashes++;
                    continue;
                }
                if (character == '"')
                {
                    result.Append('\\', slashes * 2 + 1);
                }
                else
                {
                    result.Append('\\', slashes);
                }
                result.Append(character);
                slashes = 0;
            }
            result.Append('\\', slashes * 2);
            result.Append('"');
            return result.ToString();
        }

        private static string QuotePowerShellLiteral(string value)
        {
            return "'" + value.Replace("'", "''") + "'";
        }

        private static string GetLogPath()
        {
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string folder = string.IsNullOrEmpty(localAppData)
                ? Path.Combine(Path.GetTempPath(), "YaziLauncher")
                : Path.Combine(localAppData, "YaziLauncher");
            return Path.Combine(folder, "launcher.log");
        }

        private static void Log(string message)
        {
            try
            {
                string logPath = GetLogPath();
                Directory.CreateDirectory(Path.GetDirectoryName(logPath));
                File.AppendAllText(logPath, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + message + Environment.NewLine);
            }
            catch
            {
                // Logging should never block the launcher.
            }
        }

        private static void ShowError(string message)
        {
            MessageBox(IntPtr.Zero, message, "Yazi Launcher", 0x00000010u);
        }

        private static void ShowWarning(string message)
        {
            MessageBox(IntPtr.Zero, message, "Yazi Launcher", 0x00000030u);
        }

        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool IsWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int MessageBox(IntPtr hWnd, string text, string caption, uint type);

        [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
        private static extern int SetCurrentProcessExplicitAppUserModelID(string appID);

        [DllImport("shell32.dll")]
        private static extern int SHGetPropertyStoreForWindow(
            IntPtr hwnd,
            ref Guid riid,
            [MarshalAs(UnmanagedType.Interface)] out IPropertyStore propertyStore);

        [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
        private static extern int SHGetPropertyStoreFromParsingName(
            string pszPath,
            IntPtr pbc,
            GETPROPERTYSTOREFLAGS flags,
            ref Guid riid,
            [MarshalAs(UnmanagedType.Interface)] out IPropertyStore propertyStore);

        [DllImport("ole32.dll")]
        private static extern int PropVariantClear(ref PROPVARIANT pvar);

        [Flags]
        private enum GETPROPERTYSTOREFLAGS
        {
            GPS_DEFAULT = 0x0,
            GPS_HANDLERPROPERTIESONLY = 0x1,
            GPS_READWRITE = 0x2,
            GPS_TEMPORARY = 0x4,
            GPS_FASTPROPERTIESONLY = 0x8,
            GPS_OPENSLOWITEM = 0x10,
            GPS_DELAYCREATION = 0x20,
            GPS_BESTEFFORT = 0x40,
            GPS_NO_OPLOCK = 0x80,
            GPS_PREFERQUERYPROPERTIES = 0x100,
            GPS_EXTRINSICPROPERTIES = 0x200,
            GPS_EXTRINSICPROPERTIESONLY = 0x400,
            GPS_VOLATILEPROPERTIES = 0x800,
            GPS_VOLATILEPROPERTIESONLY = 0x1000,
            GPS_MASK_VALID = 0x1FFF
        }

        [ComImport]
        [Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IPropertyStore
        {
            [PreserveSig]
            int GetCount(out uint propertyCount);

            [PreserveSig]
            int GetAt(uint propertyIndex, out PROPERTYKEY key);

            [PreserveSig]
            int GetValue(ref PROPERTYKEY key, out PROPVARIANT pv);

            [PreserveSig]
            int SetValue(ref PROPERTYKEY key, ref PROPVARIANT pv);

            [PreserveSig]
            int Commit();
        }

        [StructLayout(LayoutKind.Sequential, Pack = 4)]
        private struct PROPERTYKEY
        {
            public Guid fmtid;
            public uint pid;

            public PROPERTYKEY(Guid formatId, uint propertyId)
            {
                fmtid = formatId;
                pid = propertyId;
            }
        }

        [StructLayout(LayoutKind.Explicit, Size = 24)]
        private struct PROPVARIANT
        {
            [FieldOffset(0)]
            public ushort vt;

            [FieldOffset(8)]
            public IntPtr pointerValue;

            public static PROPVARIANT FromString(string value)
            {
                PROPVARIANT result = new PROPVARIANT();
                result.vt = 31; // VT_LPWSTR
                result.pointerValue = Marshal.StringToCoTaskMemUni(value);
                return result;
            }
        }
    }
}
