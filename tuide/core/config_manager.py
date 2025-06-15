import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

class ConfigManager:
    def __init__(
        self,
        project_config_path: Optional[Path] = None,
        user_config_path: Optional[Path] = None,
        system_config_path: Optional[Path] = None,
        workspace_root: Optional[Path] = None, # Added for placeholder
    ):
        self.project_config_path = project_config_path
        self.user_config_path = user_config_path
        self.system_config_path = system_config_path
        self.workspace_root = workspace_root or Path.cwd() # Default to CWD

        self.config: Dict[str, Any] = {}
        self.load_config()

    def _load_single_config(self, path: Path) -> Dict[str, Any]:
        if path and path.exists() and path.is_file():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {path}") # Replace with logging later
            except Exception as e:
                print(f"Warning: Could not load config file {path}: {e}") # Replace with logging
        return {}

    def load_config(self) -> None:
        self.config = {} # Reset config

        # System config (lowest precedence)
        if self.system_config_path:
            system_cfg = self._load_single_config(self.system_config_path)
            self._deep_update(self.config, system_cfg)

        # User config
        if self.user_config_path:
            user_cfg = self._load_single_config(self.user_config_path)
            self._deep_update(self.config, user_cfg)

        # Project config (highest precedence)
        if self.project_config_path:
            project_cfg = self._load_single_config(self.project_config_path)
            self._deep_update(self.config, project_cfg)

    def _deep_update(self, target: Dict, source: Dict) -> None:
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def _resolve_value(self, value: Any, processing_key: Optional[str] = None) -> Any:
        if isinstance(value, str):
            # Resolve %config:path.to.value%
            # This needs to be careful about circular references
            # A simple way to start, might need more robustness
            parts = value.split('%config:')
            if len(parts) > 1:
                resolved_parts = [parts[0]]
                for part in parts[1:]:
                    end_index = part.find('%')
                    if end_index != -1:
                        config_key = part[:end_index]
                        rest_of_string = part[end_index+1:]
                        # Avoid resolving the same key again if it caused this resolution
                        if config_key != processing_key:
                             resolved_config_val = self.get(config_key, default_value=f"%config:{config_key}%")
                             resolved_parts.append(str(resolved_config_val) + rest_of_string)
                        else:
                            # Circular reference detected or attempted re-resolution
                            resolved_parts.append(f"%config:{config_key}%" + rest_of_string)
                    else:
                        resolved_parts.append(part) # Should not happen if format is correct
                value = "".join(resolved_parts)

            # Resolve %workspace_root%
            if self.workspace_root:
                 value = value.replace("%workspace_root%", str(self.workspace_root))

            # Add other substitutions like %current_file_path% later
            # For now, these will remain as literal strings if not handled above
            value = value.replace("%current_file_path%", "%current_file_path%") # Placeholder
            value = value.replace("%current_file_name%", "%current_file_name%") # Placeholder
            value = value.replace("%current_dir%", "%current_dir%") # Placeholder


        elif isinstance(value, dict):
            return {k: self._resolve_value(v, processing_key) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_value(item, processing_key) for item in value]
        return value

    def get(self, key_path: Union[str, List[str]], default_value: Any = None) -> Any:
        keys: List[str]
        if isinstance(key_path, str):
            keys = key_path.split('.')
        else:
            keys = key_path

        current_level = self.config
        for key in keys:
            if isinstance(current_level, dict) and key in current_level:
                current_level = current_level[key]
            else:
                return default_value

        # Pass the original key_path for circular reference check during resolution
        original_key_str = key_path if isinstance(key_path, str) else ".".join(keys)
        return self._resolve_value(current_level, processing_key=original_key_str)

# Example Usage (for testing, can be removed or put in a test file)
if __name__ == '__main__':
    # Create dummy config files for testing
    Path("test_project_config.json").write_text(json.dumps({
        "colors": {"background": "#111111", "text": "%config:project.text_color%"},
        "project": {"name": "MyProject", "text_color": "#FFFFFF"},
        "python": {"run": "/bin/python3 %current_file_path% from project"}
    }))
    Path("test_user_config.json").write_text(json.dumps({
        "colors": {"background": "#222222", "user_specific": "abc"},
        "python": {"debug": "pdb %current_file_path%"},
        "macros": {"sort_imports": "isort %current_file_path%"}
    }))
    Path("test_system_config.json").write_text(json.dumps({
        "colors": {"background": "#333333", "font": "monospace"},
         "python": {"run": "/usr/bin/python %current_file_path% from system"}
    }))

    print("Testing ConfigManager...")
    # Test with only project config
    print("\n--- Project Only ---")
    cm_project = ConfigManager(project_config_path=Path("test_project_config.json"), workspace_root=Path("/test/ws"))
    print(f"Background: {cm_project.get('colors.background')}") # Expected: #111111
    print(f"Text Color: {cm_project.get('colors.text')}") # Expected: #FFFFFF
    print(f"Project Name: {cm_project.get('project.name')}")   # Expected: MyProject
    print(f"Python Run: {cm_project.get('python.run')}") # Expected: /bin/python3 %current_file_path% from project (path not resolved yet)

    # Test with project and user config
    print("\n--- Project & User ---")
    cm_user_proj = ConfigManager(
        project_config_path=Path("test_project_config.json"),
        user_config_path=Path("test_user_config.json"),
        workspace_root=Path("/test/ws")
    )
    print(f"Background: {cm_user_proj.get('colors.background')}") # Expected: #111111 (project overrides user)
    print(f"User Specific: {cm_user_proj.get('colors.user_specific')}") # Expected: abc
    print(f"Python Debug: {cm_user_proj.get('python.debug')}") # Expected: pdb %current_file_path%
    print(f"Python Run: {cm_user_proj.get('python.run')}") # Expected: /bin/python3 %current_file_path% from project

    # Test with all three
    print("\n--- Project, User & System ---")
    cm_all = ConfigManager(
        project_config_path=Path("test_project_config.json"),
        user_config_path=Path("test_user_config.json"),
        system_config_path=Path("test_system_config.json"),
        workspace_root=Path("/test/ws")
    )
    print(f"Background: {cm_all.get('colors.background')}") # Expected: #111111
    print(f"Font: {cm_all.get('colors.font')}")             # Expected: monospace (from system)
    print(f"Python Run (all): {cm_all.get('python.run')}")  # Expected: /bin/python3 %current_file_path% from project
    print(f"Workspace Test: {cm_all.get('project.name')} in %workspace_root%/src") # Expected: MyProject in /test/ws/src

    # Test non-existent key
    print(f"Non-existent: {cm_all.get('non.existent.key', 'default_val')}") # Expected: default_val

    # Test resolving %config:...% that points to another %config:...%
    Path("test_circular_config.json").write_text(json.dumps({
        "level1": "%config:level2%",
        "level2": "%config:level3%",
        "level3": "final_value",
        "text": "Hello %config:user.name%",
        "user": {"name": "TUIDE User"}
    }))
    cm_circular = ConfigManager(project_config_path=Path("test_circular_config.json"))
    print(f"Multi-level config resolve: {cm_circular.get('level1')}") # Expected: final_value
    print(f"Text with user: {cm_circular.get('text')}") # Expected: Hello TUIDE User

    # Test circular dependency in %config:...%
    Path("test_circ_ref_config.json").write_text(json.dumps({
        "cycle1": "%config:cycle2%",
        "cycle2": "%config:cycle1%",
        "safe": "is_safe"
    }))
    cm_circ_ref = ConfigManager(project_config_path=Path("test_circ_ref_config.json"))
    print(f"Circular dependency test (cycle1): {cm_circ_ref.get('cycle1')}") # Expected: %config:cycle1% or %config:cycle2%
    print(f"Circular dependency test (safe): {cm_circ_ref.get('safe')}")     # Expected: is_safe

    # Clean up dummy files
    Path("test_project_config.json").unlink()
    Path("test_user_config.json").unlink()
    Path("test_system_config.json").unlink()
    Path("test_circular_config.json").unlink()
    Path("test_circ_ref_config.json").unlink()
