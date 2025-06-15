import asyncio
from pathlib import Path
from typing import Optional

from textual.widget import Widget
from textual.widgets import RichLog
# from textual.binding import Binding # Not used in this version

class TerminalWidget(Widget):
    DEFAULT_CSS = """
    TerminalWidget {
        height: 100%;
        border: round white;
        padding: 1;
    }
    RichLog {
        height: 100%;
    }
    """

    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.rich_log = RichLog(highlight=True, markup=True, wrap=False, auto_scroll=True)

    def compose(self):
        yield self.rich_log

    def focus(self, scroll_visible: bool = True) -> None: # Return type is None
        self.rich_log.focus(scroll_visible)

    def clear_log(self) -> None:
        self.rich_log.clear()

    async def run_command(self, command: str, cwd: Optional[Path] = None) -> None:
        self.rich_log.write(f"[b]$ {command}[/b]")

        cwd_str = str(cwd) if cwd else None

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd_str
            )

            async def stream_output(stream: Optional[asyncio.StreamReader], prefix=""): # Added type hint
                if stream is None:
                    return
                while True:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break
                    try:
                        line = line_bytes.decode('utf-8', errors='replace').rstrip() # Added errors='replace'
                        self.rich_log.write(f"{prefix}{line}")
                    except UnicodeDecodeError: # Should be less likely with errors='replace'
                        self.rich_log.write(f"{prefix}[dim](undecodable bytes)[/dim]")

            await asyncio.gather(
                stream_output(process.stdout, ""),
                stream_output(process.stderr, "[red]ERR: [/red]")
            )

            # Ensure the process has actually finished and streams are drained.
            await process.wait()

            if process.returncode == 0:
                self.rich_log.write(f"[green]Command finished successfully (exit code {process.returncode})[/green]")
            else:
                self.rich_log.write(f"[red]Command failed (exit code {process.returncode})[/red]")

        except FileNotFoundError:
            self.rich_log.write(f"[red]Error: Command not found: {command.split()[0]}[/red]")
        except Exception as e:
            self.rich_log.write(f"[red]Error running command '{command}': {e}[/red]")

        self.rich_log.write("") # Add a blank line for separation

if __name__ == '__main__':
    from textual.app import App, ComposeResult
    from textual.containers import Vertical
    from textual.widgets import Button

    class TerminalApp(App):
        CSS = """
        Vertical {
            height: auto;
            padding: 1;
            align: center middle; /* Center buttons horizontally and vertically */
        }
        Button {
            width: 80%;
            margin-bottom: 1;
        }
        #terminal_output { /* ID for the TerminalWidget */
            height: 20;
            border-title: "Output Log";
        }
        """

        def on_mount(self) -> None:
            # TerminalWidget is already composed with an ID, so it can be queried.
            pass

        def compose(self) -> ComposeResult:
            with Vertical():
                yield Button("Run 'ls -la' (or 'dir')", id="ls", variant="primary")
                yield Button("Run 'echo Hello TUIDE'", id="echo", variant="primary")
                yield Button("Run 'python --version'", id="python_ver", variant="primary")
                yield Button("Run failing command", id="fail_cmd", variant="error")
                yield Button("Run non-existent command", id="no_cmd", variant="error")
                yield Button("Clear Log", id="clear", variant="warning")
            yield TerminalWidget(id="terminal_output")

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            terminal_widget = self.query_one(TerminalWidget) # Query by type

            command_to_run = ""
            current_dir = Path.cwd() # Example CWD

            if event.button.id == "ls":
                import platform
                command_to_run = "dir" if platform.system() == "Windows" else "ls -la"
            elif event.button.id == "echo":
                command_to_run = "echo Hello TUIDE from TerminalWidget"
            elif event.button.id == "python_ver":
                # Ensure python is in PATH, or specify full path if necessary
                command_to_run = "python --version"
            elif event.button.id == "fail_cmd":
                command_to_run = "python -c \"import sys; sys.exit(1)\""
            elif event.button.id == "no_cmd":
                command_to_run = "hopefully_non_existent_command_12345_abcdef"
            elif event.button.id == "clear":
                terminal_widget.clear_log()
                self.notify("Log cleared.")
                return

            if command_to_run:
                self.notify(f"Running: {command_to_run}")
                await terminal_widget.run_command(command_to_run, cwd=current_dir)

    app = TerminalApp()
    app.run()
