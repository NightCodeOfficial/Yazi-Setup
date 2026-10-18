local hovered = ya.sync(function()
  local file = cx.active.current.hovered
  return file and tostring(file.url), file and file.cha.is_dir
end)

return {
  entry = function()
    local path, directory = hovered()
    if not path then return end
    if not directory then return ya.emit("open", {}) end
    local status, err = Command("code"):arg { "--reuse-window", "--", path }:status()
    if not status or not status.success then
      ya.notify { title = "VS Code", content = "Could not open directory in VS Code; entering it in Yazi instead. " .. tostring(err or "Check the code command."), level = "warn", timeout = 6 }
      ya.emit("enter", {})
    end
  end,
}
