from pathlib import Path
from typing import Optional

from textual.widgets import DirectoryTree
# from textual.app import ComposeResult # Not strictly needed for the widget itself
# from textual.message import Message # Not used as we are propagating DirectoryTree's message

class FileExplorerWidget(DirectoryTree):
    """
    A file explorer widget based on Textual's DirectoryTree.
    It displays the file system tree starting from a given path.
    When a file is selected, it emits the standard DirectoryTree.FileSelected message.
    """

    def __init__(
        self,
        path: Path, # The root path to display in the tree
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
        # Add any other DirectoryTree parameters you might want to expose here
    ):
        """
        Initializes the FileExplorerWidget.

        Args:
            path: The root directory path for the file explorer.
            name: The name of the widget.
            id: The ID of the widget.
            classes: CSS classes for the widget.
        """
        # The 'path' argument for DirectoryTree's constructor must be a string.
        super().__init__(path=str(path), name=name, id=id, classes=classes)

    # The DirectoryTree widget itself handles file/directory selection (mouse clicks, Enter key)
    # and emits a `DirectoryTree.FileSelected` message when a file is selected,
    # or a `DirectoryTree.DirectorySelected` message when a directory is selected (if configured, or by default).
    #
    # We are intentionally not overriding the event handling here to keep this widget simple
    # and allow the application to directly listen for `DirectoryTree.FileSelected` or
    # `DirectoryTree.DirectorySelected` messages from this widget.
    #
    # If custom behavior or a different message type were needed upon selection,
    # one would subscribe to `on_directory_tree_file_selected` (or `...directory_selected`),
    # stop the original event using `event.stop()`, and then post a new custom message.
    # Example:
    #
    # class MyCustomFileSelected(Message):
    #     def __init__(self, path: Path, some_other_data: Any) -> None:
    #         super().__init__()
    #         self.path = path
    #         self.some_other_data = some_other_data
    #
    # async def on_directory_tree_file_selected(
    #     self, event: DirectoryTree.FileSelected
    # ) -> None:
    #     """Handles the FileSelected message from the underlying DirectoryTree."""
    #     event.stop() # Prevent the original DirectoryTree.FileSelected from propagating further
    #     # Perform any custom logic here
    #     custom_data = f"Selected from {self.id or 'FileExplorer'}"
    #     self.post_message(MyCustomFileSelected(path=event.path, some_other_data=custom_data))
    #
    # For now, this widget remains a direct extension of DirectoryTree, leveraging its
    # default event emissions.

# Example Usage (for testing, can be removed or put in a test file later)
if __name__ == '__main__':
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Label # Added Label for feedback
    from textual.containers import VerticalScroll

    class ExplorerApp(App):
        TITLE = "File Explorer Test"
        BINDINGS = [("q", "quit", "Quit")]

        def compose(self) -> ComposeResult:
            yield Header()
            # Use current working directory for the test, or a specific test directory
            # Ensure the path exists for DirectoryTree to load correctly.
            test_path = Path.cwd()
            # You might want to create a dummy directory structure for more robust testing.
            # For example:
            # test_path = Path.cwd() / "explorer_test_dir"
            # test_path.mkdir(exist_ok=True)
            # (test_path / "file1.txt").write_text("Hello")
            # (test_path / "subdir").mkdir(exist_ok=True)
            # (test_path / "subdir" / "file2.py").write_text("print('world')")

            self.feedback_label = Label("Selected: None", id="feedback")

            with VerticalScroll(): # Ensure content scrolls if tree is too large
                yield self.feedback_label
                yield FileExplorerWidget(path=test_path, id="file_explorer")
            yield Footer()

        async def on_directory_tree_file_selected(
            self, event: DirectoryTree.FileSelected
        ) -> None:
            """Handles file selection events from any DirectoryTree."""
            # Check if the event comes from our specific file explorer instance
            if event.control.id == "file_explorer":
                message = f"File Selected: {event.path}"
                self.feedback_label.update(message)
                self.sub_title = message # Update app subtitle as well
                print(message) # Log to console for testing

        async def on_directory_tree_directory_selected(
            self, event: DirectoryTree.DirectorySelected
        ) -> None:
            """Handles directory selection events from any DirectoryTree."""
            if event.control.id == "file_explorer":
                message = f"Directory Selected: {event.path}"
                self.feedback_label.update(message)
                self.sub_title = message
                print(message)

        # To clean up test directory if created:
        # async def on_quit(self) -> None:
        #     import shutil
        #     test_path = Path.cwd() / "explorer_test_dir"
        #     if test_path.exists():
        #         shutil.rmtree(test_path)

    app = ExplorerApp()
    app.run()
