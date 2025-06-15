# TUIDE - Terminal User Interface Development Environment

**TUIDE** (pronounced "too-ee-dee" or like "GUIDE" with a "T") aims to be a lightweight, extensible, and keyboard-centric terminal-based IDE or code editor, built using Python and the [Textual](https://github.com/Textualize/textual) TUI framework.

It's designed for developers who love the terminal but desire features typically found in graphical IDEs, such as LSP support, code navigation, and a more integrated project management experience than a simple editor + terminal setup.

## ✨ Core Goals & Philosophy

*   **Terminal First**: Embrace the terminal environment. Fast, efficient, and available everywhere.
*   **Keyboard Centric**: Most operations should be achievable quickly via keyboard shortcuts and a command palette.
*   **Extensible**: Allow users to add functionality through Python macros/plugins and custom configurations.
*   **LSP Powered**: Leverage the Language Server Protocol for rich language features (completion, diagnostics, navigation).
*   **Python & Textual**: Built with modern Python and the excellent Textual framework for a rich TUI.
*   **Resource Efficient**: Aim to be lighter than many Electron-based IDEs.
*   **Configurable**: Hierarchical configuration system (default, user, project) for easy customization.

## 🚀 Getting Started

TUIDE is a terminal-based IDE built with Python and Textual.

1.  **Prerequisites**:
    *   Python 3.11 or newer.
    *   `pip` (Python package installer).

2.  **Installation / Setup**:
    *   Clone the repository:
      ```bash
      git clone [Repository URL Placeholder] # Replace with actual URL later
      cd tuide
      ```
    *   Install dependencies:
      ```bash
      pip install -r requirements.txt
      ```

3.  **Running TUIDE**:
    *   From the root `tuide` directory of the cloned repository, run:
      ```bash
      python tuide/main.py [path_to_project_directory_or_file]
      ```
    *   If no path is provided, TUIDE will open in the current working directory from where you execute the command.
    *   Examples:
        *   `python tuide/main.py .` (Opens current directory)
        *   `python tuide/main.py /path/to/your/project`
        *   `python tuide/main.py /path/to/your/file.py` (Opens the file and its directory in explorer)

4.  **Configuration**:
    *   TUIDE loads configurations in the following order (later files override earlier ones):
        1.  `tuide/config/default.json` (Ships with TUIDE)
        2.  User global: `~/.config/tuide/config.json` (on Linux/macOS) or platform equivalent (exact path might vary based on OS standards, currently `ConfigManager` needs explicit paths).
        3.  Project local: `[project_root]/.tuide/config.json`
    *   The system-wide configuration (e.g., `/etc/tuide/config.json`) is planned but not yet implemented in `ConfigManager`.
    *   To customize, copy `tuide/config/default.json` to your user or project location and modify it.
    *   **LSP Servers**: For language features like auto-completion and diagnostics, you need to install the respective Language Server Protocol (LSP) servers. For Python, `pylsp` is recommended (`pip install python-lsp-server[all]`). Check `default.json` for `lsp_servers` configurations and ensure the `command` is correct for your setup and the server is `enabled: true`.

5.  **Macros**:
    *   Create a directory named `.tuide/macros/` in your project's root.
    *   Place Python files (`*.py`) in this directory. Each file should contain a function `run_macro(app_context)` which will be callable from TUIDE (e.g., via command palette, planned).


## 🌟 Features

*   **Project Configuration Cascade**: ✅ Implemented. (Default, User, Project settings via `ConfigManager`).
*   **LSP Integration**: 🟡 Initial stub implemented for LSP client communication. Full support for specific languages (e.g., Python via pylsp) is in progress.
*   **Syntax Highlighting & Folding**: ✅ Textual's `TextArea` provides syntax highlighting via Pygments if language is set. Tree-sitter integration for advanced highlighting and folding is planned. Basic folding is inherent to `TextArea`.
*   **Python Macros**: ✅ Implemented. (Macros loaded from `[project_root]/.tuide/macros/` via `MacroRunner`).
*   **Debug/Run/Test Instructions**: ✅ Implemented. (Custom commands via `CommandRunner`, output in `TerminalWidget`).
*   **Textual-based TUI Interface**:
    *   Tabbed code editors (`EditorWidget` based on `TextArea`): ✅ Implemented.
    *   Dockable file explorer (`FileExplorerWidget`): ✅ Implemented (defaults to left dock).
    *   Integrated terminal output area (`TerminalWidget`): ✅ Implemented (for command output, not yet a fully interactive user-toggleable panel).
    *   Resizable panels: ✅ Provided by Textual's layout system.
    *   Command palette (`Ctrl+P`): 🟡 Bound, but placeholder/planned.
    *   Status bar and notifications: ✅ Basic status via Footer; `app.notify` for notifications.
    *   Themeable via config: ✅ Basic theming supported via `default.json` (theme colors can be set).
*   **Code Navigation and Refactoring**: ⏳ LSP-powered (Planned).
*   **Build System Integration**: ⏳ (Planned).
*   **Version Control (Git) Integration**: ⏳ (Planned).
*   **Tooling and Templates**: ⏳ (Planned - e.g., project creation from templates, common tasks).


## 🏗️ Core Architecture

### Directory Structure
```markdown
tuide/
├── core/       # Core logic, state, configuration (ConfigManager, Workspace, CommandRunner, MacroRunner)
├── ui/         # Main Textual UI components (EditorWidget, FileExplorerWidget, TerminalWidget)
├── lsp/        # LSP client integration (LSPClient stub)
├── widgets/    # Shared custom widgets (e.g., WelcomeWidget)
├── macros/     # Example macros (directory for user project would be .tuide/macros/)
├── config/     # Default configurations (default.json)
├── plugins/    # Structure for optional external integrations (planned)
├── main.py     # Application entry point
└── main.tcss   # Main stylesheet for the application
```

### Core Components
*   `ConfigManager`: Loads and merges hierarchical JSON configurations (default, user, project) and resolves placeholders.
*   `EditorWidget`: Textual `TextArea`-based widget for code editing, supports file I/O and language-specific syntax highlighting.
*   `TerminalWidget`: Uses Textual's `RichLog` to display output from shell commands executed asynchronously.
*   `CommandRunner`: Resolves command strings with dynamic placeholders and executes them, typically via the `TerminalWidget`.
*   `MacroRunner`: Discovers, loads, and executes Python macros (sync/async) from `[project_root]/.tuide/macros/`, providing an application context.
*   `LSPClient`: Initial stub for managing Language Server Protocol communications (start/stop server, send/receive messages).
*   `Workspace`: Manages the state of the current project, including root path, open files, and the active file.
*   `FileExplorerWidget`: UI widget based on Textual's `DirectoryTree` for browsing and selecting files/directories.
*   `WelcomeWidget`: A simple placeholder widget displayed in the editor area when no files are open.
*   `main.py (TUIDEApp)`: The main Textual application class, orchestrating UI and core components.

## ⌨️ Key Features and Shortcuts (Current)

*   `Ctrl+Q`: Quit Application
*   `Ctrl+S`: Save Active Editor
*   `Ctrl+W`: Close Active Tab
*   `Ctrl+P`: Command Palette (Placeholder)
*   File selection in Explorer: Opens file in a new tab or focuses existing tab.

(More to be added as development progresses)

## 🧩 Extensibility

*   **Configuration**: Most aspects will be configurable via JSON files.
*   **Macros**: Users can write custom Python scripts (macros) to automate tasks or add simple features. These macros will have access to parts of the TUIDE application context.
*   **Plugin API (Planned)**: A more formal plugin API is planned to allow deeper integration of new functionalities, such as version control integration, debug adapters, custom panels, etc.

## 🗺️ Roadmap & Status

*   [✅] Minimal TUI editor with file I/O and tabbing.
*   [✅] Configuration loader and command runner.
*   [🟡] LSP integration (Client stub implemented, full features in progress).
*   [✅] Macros and basic UI panels (File Explorer, Editor Tabs, Welcome Screen, Terminal Output).
*   [🔜] Plugin API design and initial implementation.
*   [⏳] Debugger support (via DAP - Debug Adapter Protocol).
*   [⏳] Advanced Tree-sitter integration for syntax highlighting and code intelligence.
*   [⏳] Git integration.
*   [⏳] More UI elements (fully interactive terminal panel, status bar enhancements, etc.).
*   [⏳] Comprehensive test suite.

*(✅ Implemented, 🟡 In Progress, 🔜 Planning, ⏳ Planned)*

## 📋 Requirements

*   Python 3.11+
*   Dependencies (see `requirements.txt`):
    *   `textual`
    *   `pygls` (for LSP types, and potentially server-side features if TUIDE ever hosts one)
    *   `watchdog` (planned for file system watching)
    *   `jsonschema` (planned for config validation)

## 🙌 Contributing

Contributions are welcome! If you're interested in helping, please check out the open issues or propose new features.
(Detailed contribution guidelines will be added later.)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
