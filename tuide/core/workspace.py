from pathlib import Path
from typing import List, Optional, Set

class Workspace:
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initializes the Workspace.

        Args:
            project_root: The root directory of the project. Defaults to current working directory.
        """
        self.project_root: Path = (project_root or Path.cwd()).resolve()

        # _open_files stores paths in the order they were opened.
        # Useful for determining tab order or next file to activate.
        self._open_files: List[Path] = []

        # _open_files_set provides fast O(1) average time complexity for checking if a file is open.
        self._open_files_set: Set[Path] = set()

        self._active_file: Optional[Path] = None

    @property
    def active_file(self) -> Optional[Path]:
        """The currently active file in the workspace. Returns None if no file is active."""
        return self._active_file

    @property
    def open_files(self) -> List[Path]:
        """A list of all currently open files, in the order they were opened. Returns a copy."""
        return list(self._open_files)

    def open_file(self, file_path: Path) -> bool:
        """
        Opens a file, adds it to the list of open files if not already present,
        and sets it as the active file. Ensures the path is absolute and resolves symlinks.

        Args:
            file_path: The path to the file to open.

        Returns:
            True if the file was newly added to the list of open files (i.e., it wasn't open already),
            False otherwise (e.g., file was already open, or file does not exist).
        """
        abs_path = file_path.resolve() # Resolves to absolute, handles symlinks

        if not abs_path.is_file():
            # In a real application, this would use logging or notify the user through the UI.
            print(f"Workspace Warning: Cannot open non-existent or non-file path: {abs_path}")
            return False

        is_newly_opened = False
        if abs_path not in self._open_files_set:
            self._open_files.append(abs_path)
            self._open_files_set.add(abs_path)
            is_newly_opened = True

        self._active_file = abs_path
        # print(f"Workspace: Opened and activated '{abs_path}'. Newly opened: {is_newly_opened}") # Debug
        return is_newly_opened

    def close_file(self, file_path: Path) -> None:
        """
        Closes a file, removing it from the list of open files.
        If the closed file was the active file, it attempts to set a new active file
        (typically the last one in the list of remaining open files).
        """
        abs_path = file_path.resolve()
        if abs_path in self._open_files_set:
            self._open_files.remove(abs_path)
            self._open_files_set.remove(abs_path)
            # print(f"Workspace: Closed '{abs_path}'.") # Debug

            if self._active_file == abs_path:
                self._active_file = self.get_next_file_to_focus()
                # if self._active_file:
                #     print(f"Workspace: New active file is '{self._active_file}'.") # Debug
                # else:
                #     print("Workspace: No files left open, active file is None.") # Debug
        # else:
            # print(f"Workspace Warning: File not open, cannot close: {abs_path}") # Debug/Log

    def set_active_file(self, file_path: Path) -> bool:
        """
        Sets the given file_path as the active file.
        If the file is not already open, it will be opened first.

        Args:
            file_path: The path to the file to set as active.

        Returns:
            True if the file had to be newly opened to be set active,
            False if it was already open and just switched to active.
            Returns False if the file_path does not point to a valid file.
        """
        abs_path = file_path.resolve()
        if not self.is_file_open(abs_path):
            # open_file handles non-existent files and sets active status
            return self.open_file(abs_path)
        else:
            if abs_path.is_file(): # Ensure it's still a file (though is_file_open implies it was)
                self._active_file = abs_path
                # print(f"Workspace: Set active file to '{abs_path}'.") # Debug
                return False # Not newly opened, just switched
            else: # Should ideally not happen if is_file_open was true based on a valid file
                # print(f"Workspace Warning: Cannot set non-file as active: {abs_path}") # Debug/Log
                return False


    def is_file_open(self, file_path: Path) -> bool:
        """Checks if the given file_path is currently in the list of open files."""
        return file_path.resolve() in self._open_files_set

    def get_next_file_to_focus(self) -> Optional[Path]:
        """
        Determines which file should become active if the current active_file is closed
        or if a "next tab" action is performed.
        Currently returns the last file in the open_files list (most recently opened or focused).

        Returns:
            The path of the next file to focus, or None if no other files are open.
        """
        if not self._open_files:
            return None
        return self._open_files[-1] # Simple strategy: last opened becomes active

    # Placeholder for future functionality
    def get_active_file_content(self) -> Optional[str]:
        """
        Placeholder for retrieving the content of the active file.
        This would typically involve interacting with an editor component.
        For now, it could just read from disk or return None.
        """
        if self.active_file and self.active_file.is_file():
            # This is a direct disk read, in reality, it might come from an editor buffer
            try:
                return self.active_file.read_text(encoding='utf-8')
            except Exception as e:
                # print(f"Workspace Error: Could not read active file content: {e}") # Debug/Log
                return None
        return None

# Example Usage (for testing, can be removed or put in a test file later)
if __name__ == '__main__':
    import shutil # Make sure shutil is imported for cleanup

    # Setup a dummy project root and some files for testing
    test_proj_root = Path.cwd() / "temp_ws_test_project_workspace_cls" # Unique name
    test_proj_root.mkdir(parents=True, exist_ok=True)
    (test_proj_root / "file1.py").write_text("print('file1 content')")
    (test_proj_root / "file2.txt").write_text("text content for file2")
    (test_proj_root / "subdir").mkdir(exist_ok=True)
    (test_proj_root / "subdir" / "file3.md").write_text("# Markdown File 3")

    ws = Workspace(project_root=test_proj_root)
    print(f"Workspace initialized with root: {ws.project_root}")

    file1 = test_proj_root / "file1.py"
    file2 = test_proj_root / "file2.txt"
    file3 = test_proj_root / "subdir" / "file3.md"
    non_existent_file = test_proj_root / "no_such_file.foo"

    print(f"\n--- Testing open_file ---")
    print(f"Opening {file1.name}:")
    opened_new1 = ws.open_file(file1)
    print(f"Newly opened: {opened_new1}, Active: {ws.active_file.name if ws.active_file else 'None'}, Open: {[p.name for p in ws.open_files]}")

    print(f"\nOpening {file2.name}:")
    opened_new2 = ws.open_file(file2)
    print(f"Newly opened: {opened_new2}, Active: {ws.active_file.name if ws.active_file else 'None'}, Open: {[p.name for p in ws.open_files]}")

    print(f"\nAttempting to re-open {file1.name}:")
    opened_new_re1 = ws.open_file(file1) # Should set file1 active, but not newly opened
    print(f"Newly opened: {opened_new_re1}, Active: {ws.active_file.name if ws.active_file else 'None'}, Open: {[p.name for p in ws.open_files]}")

    print(f"\n--- Testing is_file_open ---")
    print(f"Is {file1.name} open? {ws.is_file_open(file1)}") # True
    print(f"Is {file3.name} open? {ws.is_file_open(file3)}") # False (not opened yet)

    print(f"\n--- Testing set_active_file ---")
    print(f"Setting {file2.name} (already open) active:")
    set_active_opened_new = ws.set_active_file(file2)
    print(f"Newly opened by set_active_file: {set_active_opened_new}, Active: {ws.active_file.name if ws.active_file else 'None'}")

    print(f"\nSetting {file3.name} (not open yet) active:")
    set_active_opened_new3 = ws.set_active_file(file3)
    print(f"Newly opened by set_active_file: {set_active_opened_new3}, Active: {ws.active_file.name if ws.active_file else 'None'}, Open: {[p.name for p in ws.open_files]}")

    print(f"\n--- Testing open_file with non-existent file ---")
    print(f"Attempting to open non-existent file: {non_existent_file.name}")
    opened_non_existent = ws.open_file(non_existent_file)
    print(f"Opened non_existent_file successfully? {opened_non_existent}")
    print(f"Active file: {ws.active_file.name if ws.active_file else 'None'}") # Should still be file3
    print(f"Open files: {[p.name for p in ws.open_files]}")

    print(f"\n--- Testing close_file ---")
    print(f"Open files before close: {[p.name for p in ws.open_files]}, Active: {ws.active_file.name if ws.active_file else 'None'}")

    print(f"\nClosing {file2.name} (not active):")
    ws.close_file(file2)
    print(f"Active file: {ws.active_file.name if ws.active_file else 'None'}, Open files: {[p.name for p in ws.open_files]}")

    print(f"\nClosing {file3.name} (was active):") # file3 is currently active
    ws.close_file(file3)
    print(f"Active file: {ws.active_file.name if ws.active_file else 'None'}, Open files: {[p.name for p in ws.open_files]}") # Should revert to file1 (last in list)

    print(f"\nClosing {file1.name} (last file):")
    ws.close_file(file1)
    print(f"Active file: {ws.active_file.name if ws.active_file else 'None'}, Open files: {[p.name for p in ws.open_files]}")

    print(f"\n--- Testing get_active_file_content (basic) ---")
    print(f"Opening {file1.name} again for content test...")
    ws.open_file(file1)
    print(f"Active file: {ws.active_file.name if ws.active_file else 'None'}")
    content = ws.get_active_file_content()
    print(f"Content of {ws.active_file.name if ws.active_file else 'None'}: '{content}'")


    # Clean up dummy project
    if test_proj_root.exists(): # Check before deleting
        shutil.rmtree(test_proj_root)
        print(f"\nCleaned up {test_proj_root}")
    else:
        print(f"\nTest project root {test_proj_root} not found for cleanup.")
