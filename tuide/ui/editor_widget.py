from pathlib import Path
from typing import Optional

from textual.widget import Widget
from textual.widgets import TextArea
# Binding is not used in the provided code, but might be useful later
# from textual.binding import Binding


class EditorWidget(Widget):
    DEFAULT_CSS = """
    EditorWidget {
        height: 100%;
    }
    TextArea {
        height: 100%;
    }
    """

    def __init__(
        self,
        file_path: Optional[Path] = None,
        language: Optional[str] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.file_path = file_path
        self.language = language # Store for future use (e.g. LSP, TreeSitter)

        # Initialize TextArea with some default options
        # The language parameter in TextArea is for syntax highlighting if supported by its theme
        # However, as of Textual 0.47, language parameter in TextArea constructor is for lexer name for pygments.
        # If a specific lexer isn't needed at init, it can be omitted or set to None.
        ta_name = f"text_area_{file_path.name if file_path else 'untitled'}"
        if name is not None: # If a name is provided for EditorWidget, use it for TextArea too for simplicity
             ta_name = name

        self.text_area = TextArea(
            "", # Initial content
            language=language, # Pass language if provided, else None. Pygments will try to guess if None.
            show_line_numbers=True,
            name=ta_name
        )

    def compose(self):
        yield self.text_area

    async def on_mount(self) -> None: # Added type hint for consistency
        if self.file_path and self.file_path.exists():
            await self.load_file(self.file_path)
        else:
            # You could set some default text or leave it empty
            # self.text_area.load_text("# New file")
            pass
        self.text_area.focus()


    async def load_file(self, file_path: Path) -> None:
        self.file_path = file_path
        # Update language if it's None or we want to infer from new file_path
        if self.language is None and file_path.suffix:
            # Basic inference, can be improved
            lang_map = {".py": "python", ".md": "markdown", ".json": "json", ".js": "javascript", ".html": "html", ".css": "css"}
            self.language = lang_map.get(file_path.suffix.lower())
            if self.text_area.language != self.language : # Check if TextArea has language attribute to set
                 try:
                    self.text_area.language = self.language
                 except AttributeError: # Should not happen with recent Textual versions
                    pass


        try:
            content = file_path.read_text(encoding='utf-8') # Specify encoding
            self.text_area.load_text(content) # load_text is synchronous
            # Update the name of the TextArea to reflect the file, if not explicitly named.
            if self.text_area.name is None or self.text_area.name.startswith("text_area_"):
                 self.text_area.name = f"text_area_{file_path.name}"
        except Exception as e:
            # Log error or show notification to user
            # For now, print to console. In a real app, use app.notify or a status bar.
            print(f"Error loading file {file_path}: {e}")

    async def save_file(self, file_path: Optional[Path] = None) -> bool:
        target_path = file_path or self.file_path
        if not target_path:
            # Handle case where no path is specified (e.g., prompt user for path)
            # For now, print to console. In a real app, use app.notify or a status bar.
            print("Error: No file path specified for saving.")
            return False

        try:
            content = self.text_area.text
            target_path.write_text(content, encoding='utf-8') # Specify encoding
            self.file_path = target_path # Update file_path if saved to a new location
            # Update language if it was inferred and path changed
            if target_path.suffix and self.language is None: # or some other logic to re-infer
                lang_map = {".py": "python", ".md": "markdown", ".json": "json", ".js": "javascript", ".html": "html", ".css": "css"}
                new_language = lang_map.get(target_path.suffix.lower())
                if new_language and self.text_area.language != new_language:
                    self.language = new_language
                    try:
                        self.text_area.language = new_language
                    except AttributeError:
                        pass
            return True
        except Exception as e:
            print(f"Error saving file {target_path}: {e}")
            return False

    @property
    def text(self) -> str:
        return self.text_area.text

    @text.setter
    def text(self, new_text: str) -> None:
        self.text_area.load_text(new_text) # load_text is synchronous

    # Delegate focus to the TextArea
    def focus(self, scroll_visible: bool = True) -> None: # Return type is None for focus method
        self.text_area.focus(scroll_visible)

# Example usage (for testing within this file, if needed)
if __name__ == '__main__':
    from textual.app import App

    class EditorApp(App):
        BINDINGS = [("s", "save_current_editor", "Save")]

        def compose(self):
            # Create a dummy file to load
            self.dummy_file = Path("dummy_editor_test.py")
            self.dummy_file.write_text("print('Hello from EditorWidget')\n# Test comment\n")

            self.editor = EditorWidget(file_path=self.dummy_file, language="python", id="editor1")
            yield self.editor

        async def on_quit(self):
            # Clean up dummy file
            if self.dummy_file.exists():
                self.dummy_file.unlink()

        async def action_save_current_editor(self) -> None:
            editor = self.query_one(EditorWidget)
            saved = await editor.save_file()
            if saved:
                self.notify(f"File {editor.file_path} saved!")
            else:
                self.notify(f"Failed to save {editor.file_path}", severity="error")


    app = EditorApp()
    app.run()
