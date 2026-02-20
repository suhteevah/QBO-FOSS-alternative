# Desktop App Icons

Place the following icon files here before building:

- `icon.ico` — Windows icon (256x256, multi-resolution)
- `icon.png` — General PNG icon (1024x1024)
- `icon.icns` — macOS icon

You can generate these from a single 1024x1024 PNG source using:

```bash
# Using Tauri's icon generator
npx @tauri-apps/cli icon path/to/source-1024x1024.png
```

This will auto-generate all required formats in this directory.
