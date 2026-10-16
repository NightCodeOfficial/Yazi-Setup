-- Runtime paths are filled in by setup.py for this machine.
local runtime = __RUNTIME__
local snapshot = ya.sync(function()
  local paths = {}
  for _, file in pairs(cx.active.selected) do
    paths[#paths + 1] = tostring(file.url)
  end
  local hovered = cx.active.current.hovered
  if #paths == 0 and hovered then paths[1] = tostring(hovered.url) end
  return tostring(cx.active.current.cwd), paths, hovered and tostring(hovered.url)
end)

return {
  entry = function(self, job)
    local cwd, paths, hovered = snapshot()
    local action = job.args[1] or "zip"
    if action == "clipboard" then
      if not hovered then return end
      local output, err = Command("powershell.exe"):arg {
        "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File",
        runtime.clipboard, "-FilePath", hovered,
      }:output()
      ya.notify {
        title = "Yazi clipboard",
        content = output and (output.status.success and output.stdout or output.stderr) or tostring(err),
        level = output and output.status.success and "info" or "error", timeout = 8,
      }
      return
    end
    if action == "extract" then paths = hovered and { hovered } or {} end
    if #paths == 0 then return end
    local value, event = ya.input {
      title = action == "zip" and "New ZIP filename:" or "New extraction folder:",
      value = action == "zip" and "archive.zip" or "extracted",
      pos = { "top-center", y = 3, w = 60 },
    }
    if event ~= 1 or not value or value == "" then return end
    local args = { runtime.script, action, value }
    for _, path in ipairs(paths) do args[#args + 1] = path end
    local output, err = Command(runtime.python):arg(args):cwd(cwd):output()
    ya.notify {
      title = "Yazi archives",
      content = output and (output.status.success and output.stdout or output.stderr) or tostring(err),
      level = output and output.status.success and "info" or "error",
      timeout = 8,
    }
  end,
}
