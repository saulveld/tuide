import importlib.util
import inspect
from pathlib import Path
from typing import Any, Dict, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from textual.app import App # Using App as a generic context type for now
    # If a more specific TUIDEApp type hint is available later, it could be used.

class MacroRunner:
    MACRO_FUNCTION_NAME = "run_macro"  # Standardized function name within macro files

    def __init__(
        self,
        app_context: 'App',
        project_macro_dir: Optional[Path] = None,
    ):
        """
        Initializes the MacroRunner.

        Args:
            app_context: The application context (e.g., the main Textual App instance)
                         that will be passed to macros.
            project_macro_dir: The directory to scan for project-specific macros.
        """
        self.app_context = app_context
        self.project_macro_dir = project_macro_dir
        self.macros: Dict[str, Callable[[Any], Any]] = {}  # Stores discovered macros: name -> function

        # Discover macros from the project directory if provided
        if self.project_macro_dir and self.project_macro_dir.is_dir():
            self.discover_macros(self.project_macro_dir)

        # Potentially discover user-level or system-level macros here too in the future

    def discover_macros(self, macro_dir: Path) -> None:
        """
        Discovers macros from Python files in the specified directory.
        A file is considered a macro if it's a .py file not starting with '_'
        and contains a function named self.MACRO_FUNCTION_NAME.

        Args:
            macro_dir: The directory to scan.
        """
        if not macro_dir.is_dir():
            # Optionally, log a warning if the directory doesn't exist
            # print(f"Warning: Macro directory '{macro_dir}' not found.")
            return

        for file_path in macro_dir.glob("*.py"):
            if file_path.name.startswith("_"):  # Skip private-like files (e.g., __init__.py)
                continue

            macro_name = file_path.stem  # Use the filename (without .py) as the macro name
            try:
                # Create a module spec from the file path
                spec = importlib.util.spec_from_file_location(macro_name, str(file_path))

                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    # Execute the module to make its contents available
                    spec.loader.exec_module(module)

                    if hasattr(module, self.MACRO_FUNCTION_NAME):
                        macro_function = getattr(module, self.MACRO_FUNCTION_NAME)
                        if callable(macro_function):
                            self.macros[macro_name] = macro_function
                            # print(f"Discovered macro: '{macro_name}'") # For debugging
                        # else:
                            # print(f"Warning: '{self.MACRO_FUNCTION_NAME}' in {file_path} is not callable.")
                    # else:
                        # print(f"Warning: No '{self.MACRO_FUNCTION_NAME}' function in {file_path}.")
                # else:
                    # print(f"Warning: Could not create module spec for {file_path}.")
            except Exception as e:
                # Handle errors during module loading/importing
                # In a real application, this should use the app's logging system
                # and potentially notify the user if a macro fails to load.
                print(f"Error loading macro '{macro_name}' from {file_path}: {e}") # Placeholder
                if hasattr(self.app_context, 'notify'):
                    try:
                        self.app_context.notify(f"Error loading macro '{macro_name}': {e}", severity="warning", timeout=5) # type: ignore
                    except Exception: # Guard against issues with notify itself
                        pass


    async def run_macro(self, macro_name: str) -> None:
        """
        Executes a named macro.

        Args:
            macro_name: The name of the macro to run.
        """
        if macro_name not in self.macros:
            # print(f"Macro '{macro_name}' not found.")
            if hasattr(self.app_context, 'notify'):
                try:
                    self.app_context.notify(f"Macro '{macro_name}' not found.", severity="error") # type: ignore
                except Exception:
                    pass
            return

        macro_function = self.macros[macro_name]

        # print(f"Running macro: '{macro_name}'") # For debugging
        try:
            if inspect.iscoroutinefunction(macro_function):
                await macro_function(self.app_context)
            else:
                # Consider running synchronous macros in a thread if they might block
                # For now, direct execution.
                macro_function(self.app_context)

            # print(f"Macro '{macro_name}' executed successfully.") # For debugging
            if hasattr(self.app_context, 'notify'):
                try:
                    self.app_context.notify(f"Macro '{macro_name}' executed.", severity="information", timeout=3) # type: ignore
                except Exception:
                    pass
        except Exception as e:
            # print(f"Error running macro '{macro_name}': {e}")
            if hasattr(self.app_context, 'notify'):
                try:
                    self.app_context.notify(f"Error in macro '{macro_name}': {str(e) or type(e).__name__}", severity="error") # type: ignore
                except Exception:
                    pass

    def reload_macros(self) -> None:
        """
        Clears existing macros and re-discovers them from the configured directory.
        """
        self.macros.clear()
        if self.project_macro_dir and self.project_macro_dir.is_dir():
            self.discover_macros(self.project_macro_dir)
        # Notify about reload, if desired
        # if hasattr(self.app_context, 'notify'):
        #     self.app_context.notify("Macros reloaded.", severity="information", timeout=2) # type: ignore
