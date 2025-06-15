🛠️ TUIDE – Specification Document
📌 Overview
Name: TUIDE
Type: Terminal IDE
UI Framework: Textual (Textualize)
Language: Python 3.11+
Audience: Senior developers, tinkerers, systems developers, terminal lovers
Goals:

Terminal-native IDE experience

Fully programmable via Python

JSON-driven configuration cascade

Out-of-the-box support for Python and SQL

Extensible support for Language Server Protocol (LSP)

Integration for run/debug/test macros and string-substitution-based commands

🔧 Features

1. 📂 Project Configuration Cascade
   TUIDE reads a hierarchy of JSON configuration files:

.tuide/config.json (project-local)

~/.config/tuide/config.json (user-global)

/etc/tuide/config.json (system-global)

Each config file can define:

json5
Copy
Edit
{
"colors": {
"background": "#1e1e1e",
"keyword": "#569CD6"
},
"file_associations": {
".py": "python",
".sql": "sql"
},
"python": {
"run": "/bin/python3 %current_file_path%",
"debug": "python-debugger %current_file_path%",
"test": "pytest %current_dir%"
},
"macros": {
"sort_imports": "python -m isort %current_file_path%"
}
} 2. 🧠 Language Service Provider Integration (LSP)
Built-in Python and SQL LSP clients

Extendable via Python plugin modules (tuide/lsp_plugins)

Supports hover, go-to-definition, completion, diagnostics

LSP configurations mapped per extension/language in config files

3. 🖍️ Syntax Highlighting & Folding
   Tree-sitter-based syntax highlighting (planned)

Built-in support for folding by bracket pairs and indentation

Language grammars defined via config

4. 🧩 Python Macros
   User-defined Python scripts inside .tuide/macros/\*.py

Macros can:

Modify files

Interact with the terminal

Define UI dialogs

Executed via keybindings or commands in the command palette

5. 🧪 Debug/Run/Test Instructions
   Commands are configured in JSON using string substitution:

bash
Copy
Edit
"/bin/python3 %current_file_path%"
Supported substitutions:

%current_file_name%

%current_file_path%

%current_dir%

%workspace_root%

%config:python.run% (nested resolution)

Executed in a terminal widget or external process pane.

6. 🧵 Textual-based TUI Interface
   Tabbed code editors (TextArea widgets)

Dockable file explorer, terminal, outline/symbols

Resizable panels (SplitPane layout)

Command palette (Ctrl+P)

Status bar and notifications

Themeable via config

7. 🔎 Code Navigation and Refactoring
   LSP-powered go-to-definition, find references, rename symbol

Outline view for symbols (classes, functions)

Cross-file search via grep or LSP

Refactoring actions via macro or LSP

8. 🧰 Tooling and Templates
   Snippet and file template engine

Triggered on file creation via config

Template variables support same %...% substitutions

json
Copy
Edit
"templates": {
"python": {
"main": {
"trigger": "main.py",
"content": "def main():\n print(\"Hello World\")\n\nif **name** == \"**main**\":\n main()"
}
}
}
🧱 Core Architecture
📁 Directory Structure
bash
Copy
Edit
tuide/
├── core/ # Core logic, state, configuration
├── ui/ # Textual UI components
├── lsp/ # LSP client integration
├── macros/ # Built-in and user macros
├── config/ # Default config, theme presets
├── plugins/ # Optional external integrations
├── main.py # Entry point
⚙️ Core Components
Module Responsibility
ConfigManager Load/merge JSON configs, resolve substitutions
EditorWidget Code editor with highlighting, folding
TerminalWidget Embedded terminal pane for command output
CommandRunner Runs commands with variable interpolation
MacroRunner Loads and executes Python macros
LSPClient Manages LSP sessions per file/language
Workspace Tracks open files, tabs, project root

⌨️ Key Features and Shortcuts
Action Shortcut
Save File Ctrl+S
Open Command Palette Ctrl+P
Run File F5
Debug File F6
Toggle Terminal Ctrl+`
Search in Files Ctrl+Shift+F
Symbol Navigation Ctrl+O
Rename Symbol F2
Run Macro Ctrl+Alt+M

🔌 Extensibility
Plugin System
Each plugin is a Python package with setup() function

Hook points: file save, open, command palette, editor context menu

Register new commands and panels

python
Copy
Edit
def setup(app):
app.register_command("myplugin.say_hello", lambda: print("Hello!"))
Custom Panels
Users can define panels/widgets in Python and load via config:

json
Copy
Edit
"panels": {
"outline": "myplugin.panels.OutlinePanel"
}
📤 External Tools Support
Ability to spawn background tasks (build systems, linters)

File watchers via watchdog

Git integration planned

📅 Roadmap
Milestone Status
Minimal TUI editor ✅ In Dev
Config loader + runner ✅ In Dev
LSP integration 🔜 Planning
Macros and panels 🔜 Planning
Plugin API 🔜 Planning
Debugger support ⏳ Planned
Tree-sitter integration ⏳ Planned
Git integration ⏳ Planned

✅ Requirements
Python 3.11+

textual, watchdog, jsonschema, pygls (for LSP)

Unix-like terminal recommended, Windows supported via rich-console
