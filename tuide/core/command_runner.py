import asyncio
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tuide.core.config_manager import ConfigManager # type: ignore
    from tuide.ui.terminal_widget import TerminalWidget # type: ignore

class CommandRunner:
    def __init__(
        self,
        config_manager: 'ConfigManager',
        terminal_widget: Optional['TerminalWidget'] = None,
    ):
        self.config_manager = config_manager
        self.terminal_widget = terminal_widget

    def resolve_command_string(
        self,
        command_template: str,
        current_file_path: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
    ) -> str:
        resolved_command = str(command_template) # Ensure it's a string

        # First, resolve any %config:key% placeholders from ConfigManager
        # This is done before other placeholders to allow config values to contain other placeholders
        # Example: "my_command": "echo %workspace_root%/output"
        # We use the get method which itself can resolve nested %config:...% references
        if "%config:" in resolved_command:
            # This simple replacement assumes %config:...% doesn't contain other %config:...%
            # that would be circularly dependent in a way not handled by ConfigManager.get's own check.
            # A more robust parser might be needed for complex cases, but ConfigManager.get already does one layer.
            # We are essentially letting ConfigManager handle its own placeholder type.
            # The `get` method itself calls `_resolve_value`, which handles %config:...%
            # So, we just need to call get on the string if it looks like a config placeholder.
            # This logic might be too simple if the entire string IS a placeholder vs containing one.
            # Let's assume for now command_template can be directly a key like "%config:mycommand%"
            # OR a string containing them like "my_script --path %config:default_path%"

            # If the entire string is a %config:...% placeholder
            if resolved_command.startswith("%config:") and resolved_command.endswith("%"):
                config_key = resolved_command[len("%config:"):-1]
                # The ConfigManager.get method will handle resolving this, including internal %config:...%
                resolved_command = str(self.config_manager.get(config_key, default_value=resolved_command))
            else:
                # If it contains %config:...% then ConfigManager's get method should be used by _resolve_value
                # This means we should pass the command string through a general resolve method
                # similar to what ConfigManager does for its values.
                # For now, let's assume ConfigManager.get is sufficient for direct config lookups
                # and other placeholders are handled next.
                # A more advanced approach would be to use ConfigManager's _resolve_value here.
                # For simplicity now, we only handle the case where the *entire* command_template is a %config lookup
                # or placeholders are resolved in the next block.
                # This can be enhanced by making resolve_command_string in ConfigManager more generic
                # and callable from here.
                pass


        effective_ws_root = workspace_root or self.config_manager.workspace_root or Path.cwd()

        # Iterative replacement for up to N levels of nesting (e.g., %config:val% which resolves to "%workspace_root%/foo")
        # Max 3 passes to prevent infinite loops with badly formed placeholders, and allow simple nesting.
        for _ in range(3):
            original_command = resolved_command
            resolved_command = resolved_command.replace("%workspace_root%", str(effective_ws_root))

            if current_file_path and isinstance(current_file_path, Path):
                resolved_command = resolved_command.replace("%current_file_path%", str(current_file_path))
                resolved_command = resolved_command.replace("%current_file_name%", current_file_path.name)
                resolved_command = resolved_command.replace("%current_dir%", str(current_file_path.parent))
            else:
                # If no file context, replace with empty strings or a specific marker if needed
                resolved_command = resolved_command.replace("%current_file_path%", "")
                resolved_command = resolved_command.replace("%current_file_name%", "")
                resolved_command = resolved_command.replace("%current_dir%", "")

            # If no changes in this pass, substitutions are complete
            if resolved_command == original_command:
                break

        return resolved_command.strip() # Strip whitespace from the final command

    async def execute_command(
        self,
        command_template: str,
        current_file_path: Optional[Path] = None,
        workspace_root_override: Optional[Path] = None,
        execution_cwd_override: Optional[Path] = None,
    ) -> None:
        if not self.terminal_widget:
            # In a real app, this might log to a file or a different UI element.
            print(f"CommandRunner: No TerminalWidget. Command '{command_template}' with file '{current_file_path}' not executed.")
            return

        ws_root_for_res = workspace_root_override or self.config_manager.workspace_root

        resolved_command = self.resolve_command_string(
            command_template,
            current_file_path,
            ws_root_for_res
        )

        if not resolved_command: # Check if empty after stripping in resolve_command_string
            if hasattr(self.terminal_widget, 'rich_log'): # Check if rich_log exists
                self.terminal_widget.rich_log.write("[yellow]Warning: CommandRunner: resolved command is empty.[/yellow]")
            else:
                 # Fallback if terminal_widget exists but not rich_log (e.g. if it's a different widget type)
                 print("Warning: CommandRunner: resolved command is empty.")
            return

        # Determine execution CWD
        exec_cwd: Optional[Path] = None
        if execution_cwd_override:
            exec_cwd = execution_cwd_override
        elif "%workspace_root%" in command_template.lower() or "%current_dir%" not in command_template.lower():
            # If command seems to explicitly use workspace_root, or doesn't use current_dir,
            # prefer workspace_root as CWD. This is a heuristic.
            if ws_root_for_res:
                exec_cwd = ws_root_for_res
            elif current_file_path and isinstance(current_file_path, Path): # Fallback to file's dir
                exec_cwd = current_file_path.parent
            else: # Ultimate fallback
                exec_cwd = self.config_manager.workspace_root or Path.cwd()
        elif current_file_path and isinstance(current_file_path, Path):
            # If current_dir is likely used or no explicit workspace_root, prefer file's directory
            exec_cwd = current_file_path.parent
        elif ws_root_for_res: # Fallback if no file path
             exec_cwd = ws_root_for_res
        else: # Ultimate fallback
            exec_cwd = self.config_manager.workspace_root or Path.cwd()

        await self.terminal_widget.run_command(resolved_command, cwd=exec_cwd)
