# Purple syntax (VS Code / Cursor)

TextMate highlighting for `.pr` files only (no LSP).

## Use it every day (recommended: install the `.vsix`)

You need **Node.js** once, to build the package.

1. In a terminal:

   ```bash
   cd editors/vscode-purple
   npx --yes @vscode/vsce package
   ```

   This creates **`purple-syntax-0.1.0.vsix`** in that folder (version comes from `package.json`).

2. **Install the VSIX**

   **Cursor**

   - `Ctrl+Shift+P` → **Extensions: Install from VSIX…** → pick `purple-syntax-0.1.0.vsix`  
   - Or, if the `cursor` shell command is on your `PATH`:

     ```bash
     cursor --install-extension purple-syntax-0.1.0.vsix
     ```

   **VS Code**

   - Same palette command **Extensions: Install from VSIX…**
   - Or:

     ```bash
     code --install-extension purple-syntax-0.1.0.vsix
     ```

3. Reload the window if prompted. Open any `.pr` file — the language mode should be **Purple**.

After this, the extension lives in your user extensions folder (e.g. Cursor: `%USERPROFILE%\.cursor\extensions`), same as store extensions.

---

## Optional: global `vsce` instead of `npx`

```bash
npm i -g @vscode/vsce
cd editors/vscode-purple
vsce package
```

---

## Dev-only: Extension Development Host

1. Open **`editors/vscode-purple`** as the workspace folder.
2. **Run > Start Debugging** (F5) (**Run Extension**).
3. In the new window, open `.pr` files from your Purple repo.

Use this when you are editing the grammar, not for day-to-day editing of Purple programs.

---

## Optional: install without Node (copy folder)

You can copy the whole **`editors/vscode-purple`** directory into the extensions folder with this exact name:

`purple-local.purple-syntax-0.1.0`

Examples:

| App    | Typical folder |
|--------|----------------|
| Cursor | `%USERPROFILE%\.cursor\extensions` |
| VS Code | `%USERPROFILE%\.vscode\extensions` |

Restart Cursor/VS Code. This is brittle if you change `version` in `package.json` without renaming the folder.
