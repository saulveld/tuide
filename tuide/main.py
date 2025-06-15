import sys
from pathlib import Path
from typing import Optional, Type

from textual.app import App, ComposeResult, Binding # Binding was imported twice
from textual.containers import Horizontal, Vertical
from textual.css.query import DOMQuery # Added DOMQuery import
from textual.widgets import Header, Footer, TabbedContent, TabPane, Label, Markdown # Markdown not used
from textual.reactive import reactive

# Assuming these are in tuide.ui and tuide.core respectively
from tuide.ui.file_explorer_widget import FileExplorerWidget
from tuide.ui.editor_widget import EditorWidget # EditorWidget was imported twice
from tuide.core.workspace import Workspace
from tuide.widgets.welcome import WelcomeWidget # A new simple placeholder widget

class TUIDEApp(App[None]): # App[None] is fine, or App without typevar if no result needed on exit
    TITLE = "TUIDE - Terminal IDE"

    CSS_PATH = "main.tcss" # Optional: for external CSS file

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
        Binding("ctrl+s", "save_active_editor", "Save", show=True),
        Binding("ctrl+w", "close_active_tab", "Close Tab", show=True),
        Binding("ctrl+p", "command_palette", "Cmd Palette", show=True), # Placeholder
        # Add more bindings: e.g. new file, open file dialog
    ]

    # Reactive variable to store the Workspace instance
    workspace: reactive[Optional[Workspace]] = reactive(None) # type: ignore

    def __init__(self, **kwargs): # Added **kwargs to pass to super
        super().__init__(**kwargs)
        project_path_arg: Optional[Path] = None
        self._initial_file_to_open: Optional[Path] = None # Ensure this is initialized

        if len(sys.argv) > 1:
            path_arg = Path(sys.argv[1])
            if path_arg.is_dir():
                project_path_arg = path_arg.resolve()
            elif path_arg.is_file(): # If a single file is passed, use its parent dir
                project_path_arg = path_arg.parent.resolve()
                self._initial_file_to_open = path_arg.resolve() # Store the file to open

        self.workspace = Workspace(project_root=project_path_arg)


    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main_container"):
            if self.workspace: # Ensure workspace is initialized
                yield FileExplorerWidget(path=self.workspace.project_root, id="file_explorer")
            else: # Fallback if workspace somehow isn't there, though __init__ should ensure it
                yield Label("Error: Workspace not initialized.", id="file_explorer_error")

            with TabbedContent(id="editor_tabs", initial="welcome_tab"):
                yield TabPane("Welcome", WelcomeWidget(), id="welcome_tab")
        yield Footer()

    async def on_mount(self) -> None:
        try:
            self.query_one(FileExplorerWidget).focus()
        except Exception: # If FileExplorerWidget failed to load, e.g. due to bad path
            pass # Error already potentially shown by compose

        if self._initial_file_to_open and self.workspace:
            # Ensure workspace is available and path is valid before trying to open
            if self._initial_file_to_open.exists():
                await self._open_file_in_editor(self._initial_file_to_open)
            else:
                self.notify(f"Initial file not found: {self._initial_file_to_open}", severity="warning")


    async def _open_file_in_editor(self, file_path: Path) -> None:
        if not self.workspace:
            self.notify("Workspace not available.", severity="error")
            return

        # Ensure file_path is absolute and resolved
        abs_file_path = file_path.resolve()

        if not abs_file_path.is_file():
            self.notify(f"Cannot open: '{abs_file_path.name}' is not a file or does not exist.", severity="error")
            return

        self.workspace.open_file(abs_file_path) # Manage workspace state

        editor_tabs = self.query_one(TabbedContent)

        tab_id_to_activate = f"tab_{abs_file_path}" # Use resolved path for ID

        try:
            existing_pane_query: DOMQuery[TabPane] = editor_tabs.query(f"#{tab_id_to_activate}")
            if existing_pane_query and not existing_pane_query.is_empty: # Check if query returned anything
                active_pane = existing_pane_query.first()
                editor_tabs.active = tab_id_to_activate
                editor_widget = active_pane.query_one(EditorWidget)
                editor_widget.focus()
                return
        except Exception as e: # Catch potential errors if query syntax is bad or widget missing
            self.notify(f"Error focusing existing tab: {e}", severity="error")


        # If welcome tab is the only one and active, remove it
        if editor_tabs.active == "welcome_tab" and editor_tabs.tab_count == 1:
            try:
                await editor_tabs.remove_pane("welcome_tab")
            except Exception as e: # Tab might not exist
                self.notify(f"Could not remove welcome tab: {e}", severity="warning")


        language = abs_file_path.suffix.lstrip(".") if abs_file_path.suffix else None

        editor_widget = EditorWidget(file_path=abs_file_path, language=language)
        new_tab_pane = TabPane(
            abs_file_path.name,
            editor_widget,
            id=tab_id_to_activate
        )
        await editor_tabs.add_pane(new_tab_pane)
        editor_tabs.active = tab_id_to_activate
        # EditorWidget's on_mount should handle focusing itself after loading content.

    async def on_directory_tree_file_selected(
        self, event: FileExplorerWidget.FileSelected # Corrected class name
    ) -> None:
        event.stop()
        await self._open_file_in_editor(event.path)

    async def action_save_active_editor(self) -> None:
        editor_tabs = self.query_one(TabbedContent)
        active_tab_id = editor_tabs.active
        if active_tab_id and active_tab_id != "welcome_tab":
            try:
                active_pane = editor_tabs.get_pane(active_tab_id)
                editor_widget = active_pane.query_one(EditorWidget)
                if editor_widget.file_path:
                    success = await editor_widget.save_file()
                    if success:
                        self.notify(f"File '{editor_widget.file_path.name}' saved.")
                    else:
                        self.notify(f"Failed to save '{editor_widget.file_path.name}'.", severity="error")
                else:
                    # TODO: Implement Save As functionality (e.g., prompt for filename)
                    self.notify("Save As not yet implemented (file has no path).", severity="warning")
            except Exception as e: # Catch errors like pane not found or widget missing
                self.notify(f"Error saving file: {e}", severity="error")


    async def action_close_active_tab(self) -> None:
        if not self.workspace:
            self.notify("Workspace not available.", severity="error")
            return

        editor_tabs = self.query_one(TabbedContent)
        active_tab_id = editor_tabs.active

        if not active_tab_id or active_tab_id == "welcome_tab":
            return

        try:
            active_pane = editor_tabs.get_pane(active_tab_id)
            editor_widget = active_pane.query_one(EditorWidget)
            file_to_close = editor_widget.file_path # This should be Path object from EditorWidget

            await editor_tabs.remove_pane(active_tab_id) # Remove tab first

            if file_to_close: # file_to_close could be None if it's a new, unsaved editor
                self.workspace.close_file(file_to_close)

                new_active_ws_file = self.workspace.active_file # Get new active file from workspace
                if new_active_ws_file:
                    new_active_tab_id = f"tab_{new_active_ws_file.resolve()}"
                    try:
                        # Check if pane exists before trying to activate
                        if editor_tabs.get_pane_by_id(new_active_tab_id):
                             editor_tabs.active = new_active_tab_id
                             # Focus editor in the new active tab
                             newly_active_pane = editor_tabs.get_pane(new_active_tab_id)
                             newly_active_pane.query_one(EditorWidget).focus()
                        # else:
                            # The new active file from workspace doesn't have a tab,
                            # this can happen if it was never opened in a tab or its tab was closed independently.
                            # Optionally open it, or let it be without a tab for now.
                            # For now, do nothing if tab doesn't exist.
                    except Exception: # Catch if get_pane_by_id or query fails
                        pass # Silently fail to switch tab if it's problematic

            # If no tabs left, or last tab was closed and no new active file, show welcome
            if editor_tabs.tab_count == 0 and not editor_tabs.query("#welcome_tab"):
                await editor_tabs.add_pane(TabPane("Welcome", WelcomeWidget(), id="welcome_tab"))
                editor_tabs.active = "welcome_tab"

        except Exception as e: # Catch errors like pane not found or widget missing
            self.notify(f"Error closing tab: {e}", severity="error")

    # Placeholder for command palette
    async def action_command_palette(self) -> None:
        self.notify("Command Palette not yet implemented.", severity="info")


if __name__ == "__main__":
    # Ensure tuide/widgets directory exists for WelcomeWidget import
    widgets_dir = Path("tuide") / "widgets"
    widgets_dir.mkdir(parents=True, exist_ok=True)
    (widgets_dir / "__init__.py").touch(exist_ok=True)

    # Recreate welcome.py if it was missed or for isolated testing
    welcome_py_path = widgets_dir / "welcome.py"
    if not welcome_py_path.exists():
        with open(welcome_py_path, "w") as f:
            f.write("""
from textual.widgets import Static
class WelcomeWidget(Static):
    def __init__(self):
        super().__init__("Welcome to TUIDE!\\n\\nSelect a file from the explorer to begin.")
""")

    # Recreate main.tcss if it was missed
    main_tcss_path = Path("main.tcss") # Assuming it's in the root for the app to find
    if not main_tcss_path.exists():
         with open(main_tcss_path, "w") as f:
            f.write("""
Screen { layout: vertical; overflow-y: hidden; }
Header { dock: top; }
Footer { dock: bottom; }
#main_container { layout: horizontal; height: 1fr; width: 100%; }
FileExplorerWidget { width: 30%; max-width: 60; min-width: 20; height: 100%; dock: left; overflow-y: auto; border-right: solid $primary-lighten-2; }
TabbedContent { width: 1fr; height: 100%; }
WelcomeWidget { width: 100%; height: 100%; content-align: center middle; padding: 2; }
""")

    app = TUIDEApp()
    app.run()
