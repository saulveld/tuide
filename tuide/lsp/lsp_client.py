import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable

class LSPClient:
    def __init__(
        self,
        language_id: str,
        server_command: List[str],
        project_root: Path,
        on_notification: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_error: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        self.language_id = language_id
        self.server_command = server_command
        self.project_root = project_root.resolve()
        self.process: Optional[asyncio.subprocess.Process] = None
        self._message_id_counter = 1
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self.is_initialized = False
        self.on_notification = on_notification
        self.on_error = on_error
        self._reader_task: Optional[asyncio.Task] = None
        self._stderr_reader_task: Optional[asyncio.Task] = None # For reading stderr

    def _create_jsonrpc_request(self, method: str, params: Dict[str, Any], msg_id: Optional[int] = None) -> bytes:
        message: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        if msg_id is not None:
            message["id"] = msg_id

        content = json.dumps(message).encode('utf-8')
        header = f"Content-Length: {len(content)}\r\n\r\n".encode('utf-8')
        return header + content

    async def _write_to_server(self, data: bytes) -> bool:
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(data)
                await self.process.stdin.drain()
                # print(f"LSP SENT ({self.language_id}): {data.decode('utf-8', errors='ignore')[:200]}") # Debug
                return True
            except (ConnectionResetError, BrokenPipeError) as e:
                # print(f"LSP Error writing to server ({self.language_id}): {e}") # Debug
                if self.on_error: await self.on_error(f"Connection to LSP server ({self.language_id}) lost: {e}")
                await self.shutdown_server(force=True)
                return False
            except Exception as e: # Catch other potential errors like OSError if process closed unexpectedly
                # print(f"LSP Unexpected error writing to server ({self.language_id}): {e}") # Debug
                if self.on_error: await self.on_error(f"Unexpected error writing to LSP server ({self.language_id}): {e}")
                await self.shutdown_server(force=True)
                return False
        return False

    async def _read_stderr_loop(self):
        if not self.process or not self.process.stderr:
            return
        try:
            while True:
                line_bytes = await self.process.stderr.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode('utf-8', errors='replace').rstrip()
                # print(f"LSP STDERR ({self.language_id}): {line}") # Debug
                if self.on_error: # Use on_error for stderr for now
                    await self.on_error(f"LSP Server STDERR ({self.language_id}): {line}")
        except asyncio.CancelledError:
            pass # Task cancelled
        except Exception as e:
            # print(f"LSP Error in stderr_read_loop ({self.language_id}): {e}") # Debug
            if self.on_error:
                await self.on_error(f"LSP critical error in stderr read loop ({self.language_id}): {e}")


    async def start_server(self) -> bool:
        if self.process and self.process.returncode is None:
            # print(f"LSP server for {self.language_id} already running.") # Debug
            return True

        try:
            # print(f"LSP Starting server for {self.language_id}: {' '.join(self.server_command)}") # Debug
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except FileNotFoundError:
            # print(f"LSP Server command not found ({self.language_id}): {self.server_command[0]}") # Debug
            if self.on_error: await self.on_error(f"LSP server command not found ({self.language_id}): {self.server_command[0]}")
            return False
        except Exception as e:
            # print(f"LSP Failed to start server ({self.language_id}): {e}") # Debug
            if self.on_error: await self.on_error(f"Failed to start LSP server ({self.language_id}): {e}")
            return False

        if not self.process: return False

        self._reader_task = asyncio.create_task(self._read_loop())
        self._stderr_reader_task = asyncio.create_task(self._read_stderr_loop()) # Start stderr reader
        # print(f"LSP Server for {self.language_id} started. PID: {self.process.pid}") # Debug

        initialize_params = {
            "processId": self.process.pid,
            "rootUri": self.project_root.as_uri(),
            "capabilities": {
                "textDocument": {
                    "synchronization": {"willSave": True, "willSaveWaitUntil": False, "didSave": True},
                    "completion": {"completionItem": {"snippetSupport": True}},
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "signatureHelp": {"signatureInformation": {"parameterInformation": {"labelOffsetSupport":True}}},
                    "definition": {"linkSupport": True},
                    "references": {},
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                },
                "workspace": {
                    "didChangeConfiguration": {"dynamicRegistration": True},
                    "symbol": {"symbolKind": {"valueSet": list(range(1,27))}}, # Support all symbol kinds
                     "executeCommand":{"dynamicRegistration":True}
                }
            },
            # "trace": "verbose", # Useful for debugging
            # "clientInfo": {"name": "TUIDE", "version": "0.1.0"}, # Optional
        }

        try:
            init_response = await self.send_request("initialize", initialize_params, timeout=10.0)
            if init_response is None:
                # print(f"LSP Initialize for {self.language_id} failed or timed out.") # Debug
                if self.on_error: await self.on_error(f"LSP Initialize for {self.language_id} timed out or failed.")
                await self.shutdown_server(force=True)
                return False

            # print(f"LSP Initialize response for {self.language_id}: {json.dumps(init_response, indent=2)[:500]}") # Debug
            # TODO: Store server_capabilities = init_response.get('capabilities')

            await self.send_notification("initialized", {})
            self.is_initialized = True
            # print(f"LSP for {self.language_id} initialized successfully.") # Debug
            return True
        except Exception as e:
            # print(f"LSP Error during initialization ({self.language_id}): {e}") # Debug
            if self.on_error: await self.on_error(f"LSP error during initialization ({self.language_id}): {e}")
            await self.shutdown_server(force=True)
            return False

    async def _read_loop(self):
        if not self.process or not self.process.stdout: return

        buffer = bytearray()
        content_length: Optional[int] = None

        while True:
            try:
                if content_length is None:
                    header_buffer = bytearray()
                    while True:
                        if not self.process or self.process.stdout.at_eof(): return
                        line = await self.process.stdout.readline()
                        if not line: return
                        header_buffer.extend(line)
                        if b'\r\n\r\n' in header_buffer:
                            header_part, _, body_start_buffer = header_buffer.partition(b'\r\n\r\n')
                            buffer.extend(body_start_buffer)
                            headers_str = header_part.decode('ascii', errors='ignore')
                            for h_line in headers_str.split('\r\n'):
                                if h_line.lower().startswith("content-length:"):
                                    content_length = int(h_line.split(":")[1].strip())
                                    break
                            if content_length is None and header_part:
                                # print(f"LSP Warning ({self.language_id}): Received headers without Content-Length: {headers_str}") # Debug
                                buffer = header_part + b'\r\n\r\n' + buffer # Put it all back
                            break

                    if content_length is None:
                        if buffer:
                            # print(f"LSP Malformed headers ({self.language_id}), buffer: {buffer[:100]}") # Debug
                            buffer.clear()
                        await asyncio.sleep(0.01)
                        continue

                if len(buffer) < content_length:
                    if not self.process or self.process.stdout.at_eof(): return
                    required_bytes = content_length - len(buffer)
                    chunk = await self.process.stdout.read(required_bytes)
                    if not chunk: return
                    buffer.extend(chunk)

                if len(buffer) >= content_length:
                    body_bytes = buffer[:content_length]
                    buffer = buffer[content_length:]
                    current_content_length = content_length # Store for this message processing
                    content_length = None # Reset for next message's headers

                    try:
                        message_data = json.loads(body_bytes.decode('utf-8'))
                        # print(f"LSP RECV ({self.language_id}): {json.dumps(message_data, indent=2)[:500]}") # Debug
                        if "id" in message_data:
                            msg_id = message_data["id"]
                            if msg_id in self._pending_requests:
                                if "error" in message_data:
                                     self._pending_requests.pop(msg_id).set_exception(
                                         RuntimeError(f"LSP Error Response: {message_data['error']}")
                                     )
                                else:
                                    self._pending_requests.pop(msg_id).set_result(message_data.get("result"))
                            # else:
                                # print(f"LSP Warning ({self.language_id}): Received response for unknown message ID: {msg_id}") # Debug
                        else:
                            if self.on_notification:
                                await self.on_notification(message_data)
                    except json.JSONDecodeError:
                        # print(f"LSP JSONDecodeError ({self.language_id}): {body_bytes.decode('utf-8',errors='ignore')[:200]}") # Debug
                        if self.on_error: await self.on_error(f"LSP ({self.language_id}) received invalid JSON")
                    except Exception as e:
                        # print(f"LSP Error processing message ({self.language_id}): {e}") # Debug
                        if self.on_error: await self.on_error(f"LSP ({self.language_id}) error processing message: {e}")
                else:
                     await asyncio.sleep(0.01) # Not enough data yet for full body

            except asyncio.CancelledError:
                # print(f"LSP Reader task cancelled ({self.language_id}).") # Debug
                break
            except Exception as e:
                # print(f"LSP Error in read_loop ({self.language_id}): {e}") # Debug
                if self.on_error: await self.on_error(f"LSP critical error in read loop ({self.language_id}): {e}")
                await self.shutdown_server(force=True)
                break
        # print(f"LSP Reader task finished ({self.language_id}).") # Debug

    async def send_request(self, method: str, params: Dict[str, Any], timeout: Optional[float] = 5.0) -> Optional[Any]:
        if not self.process or self.process.returncode is not None: # Check if process is running
            # print(f"LSP ({self.language_id}): Cannot send request, server not running.") # Debug
            return None

        self._message_id_counter += 1
        msg_id = self._message_id_counter

        future: asyncio.Future[Any] = asyncio.Future()
        self._pending_requests[msg_id] = future

        data = self._create_jsonrpc_request(method, params, msg_id)
        if not await self._write_to_server(data):
            self._pending_requests.pop(msg_id, None)
            return None

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            # print(f"LSP Request {method} (id: {msg_id}) timed out for {self.language_id}.") # Debug
            self._pending_requests.pop(msg_id, None)
            if self.on_error: await self.on_error(f"LSP request {method} (id: {msg_id}) timed out for {self.language_id}.")
            return None
        except RuntimeError as e: # Catch error set by _read_loop for LSP error responses
            # print(f"LSP Request {method} (id: {msg_id}) failed for {self.language_id}: {e}") # Debug
            # self._pending_requests.pop(msg_id, None) # Already popped in _read_loop
            if self.on_error: await self.on_error(f"LSP request {method} (id: {msg_id}) failed for {self.language_id}: {e}")
            return None
        except Exception as e: # Other unexpected errors
            # print(f"LSP Error in send_request for {method} (id: {msg_id}, lang: {self.language_id}): {e}") # Debug
            self._pending_requests.pop(msg_id, None)
            if self.on_error: await self.on_error(f"LSP error for {method} (id: {msg_id}, lang: {self.language_id}): {e}")
            return None

    async def send_notification(self, method: str, params: Dict[str, Any]) -> bool:
        if not self.process or self.process.returncode is not None:
            # print(f"LSP ({self.language_id}): Cannot send notification, server not running.") # Debug
            return False
        data = self._create_jsonrpc_request(method, params)
        return await self._write_to_server(data)

    async def notify_did_open(self, file_path: Path, file_content: str, language_id_override: Optional[str] = None) -> None:
        if not self.is_initialized: return
        params = {
            "textDocument": {
                "uri": file_path.resolve().as_uri(),
                "languageId": language_id_override or self.language_id,
                "version": 1, "text": file_content,
            }
        }
        await self.send_notification("textDocument/didOpen", params)

    async def notify_did_change(self, file_path: Path, new_content: str, version: int, language_id_override: Optional[str] = None) -> None:
        if not self.is_initialized: return
        params = {
            "textDocument": {"uri": file_path.resolve().as_uri(), "version": version},
            "contentChanges": [{"text": new_content}]
        }
        await self.send_notification("textDocument/didChange", params)

    async def notify_did_save(self, file_path: Path) -> None:
        if not self.is_initialized: return
        params = {"textDocument": {"uri": file_path.resolve().as_uri()}}
        await self.send_notification("textDocument/didSave", params)

    async def request_hover(self, file_path: Path, line: int, character: int) -> Optional[Dict[str, Any]]:
        if not self.is_initialized: return None
        params = {
            "textDocument": {"uri": file_path.resolve().as_uri()},
            "position": {"line": line, "character": character},
        }
        return await self.send_request("textDocument/hover", params)

    async def shutdown_server(self, force: bool = False) -> None:
        # print(f"LSP Shutting down server for {self.language_id} (force={force})...") # Debug

        # Cancel reader tasks first
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try: await self._reader_task
            except asyncio.CancelledError: pass
        if self._stderr_reader_task and not self._stderr_reader_task.done():
            self._stderr_reader_task.cancel()
            try: await self._stderr_reader_task
            except asyncio.CancelledError: pass

        self._reader_task = None
        self._stderr_reader_task = None

        if self.process and self.process.returncode is None:
            if self.is_initialized and not force:
                try:
                    await self.send_request("shutdown", {}, timeout=2.0)
                except Exception: # Ignore errors during shutdown sequence if force=False
                    pass
                # send_notification returns bool, but we don't act on it here
                await self.send_notification("exit", {})

            if not force:
                try: await asyncio.wait_for(self.process.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    # print(f"LSP Server ({self.language_id}) didn't exit gracefully, will terminate.") # Debug
                    pass

            if self.process.returncode is None: # Still running
                try:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=1.0)
                    if self.process.returncode is None:
                        self.process.kill()
                        await self.process.wait()
                except ProcessLookupError: pass # Already gone
                except asyncio.TimeoutError: # Failed to kill or terminate in time
                     # print(f"LSP Server ({self.language_id}) failed to terminate/kill in time.") # Debug
                     pass
                except Exception as e:
                     # print(f"LSP Exception during server termination ({self.language_id}): {e}") # Debug
                     pass

        self.is_initialized = False
        self.process = None
        # Clear pending requests, potentially failing them
        for fut in self._pending_requests.values():
            if not fut.done():
                fut.set_exception(ConnectionError(f"LSP Client ({self.language_id}) shutting down"))
        self._pending_requests.clear()
        # print(f"LSP Server for {self.language_id} shut down complete.") # Debug

async def main_lsp_test():
    import shutil
    test_project_dir = Path.cwd() / "temp_lsp_project_client_test"
    test_project_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_project_dir / "test_sample.py"
    test_file.write_text("import os\nos.path.join('a', 'b')\nprint(1)\n")

    async def _on_note(data): print(f"LSP NOTIFICATION: {json.dumps(data, indent=2)[:200]}")
    async def _on_err(msg): print(f"LSP CLIENT ERROR: {msg}")

    pylsp_exe = shutil.which("pylsp") or shutil.which("python3-pylsp") # common names
    if pylsp_exe:
        pylsp_command = [pylsp_exe]
    else:
        python_exe = shutil.which("python3") or shutil.which("python")
        if python_exe: pylsp_command = [python_exe, "-m", "pylsp"]
        else:
            print("ERROR: Cannot find python or pylsp executable for test.")
            if test_project_dir.exists(): shutil.rmtree(test_project_dir)
            return

    print(f"Using pylsp command: {' '.join(pylsp_command)}")
    lsp_client = LSPClient("python", pylsp_command, test_project_dir, _on_note, _on_err)

    if await lsp_client.start_server():
        print("Python LSP server started.")
        await lsp_client.notify_did_open(test_file, test_file.read_text())
        print(f"didOpen for {test_file}")

        hover1 = await lsp_client.request_hover(test_file, 0, 8) # 'os'
        print(f"Hover for 'os': {hover1}")
        hover2 = await lsp_client.request_hover(test_file, 1, 9) # 'join'
        print(f"Hover for 'join': {hover2}")

        await asyncio.sleep(3) # Time for diagnostics (pylsp might send some for 'print(1)')

        await lsp_client.shutdown_server()
        print("Python LSP server shut down.")
    else:
        print("Failed to start Python LSP server.")

    if test_project_dir.exists(): shutil.rmtree(test_project_dir)

if __name__ == "__main__":
    try:
        asyncio.run(main_lsp_test())
    except KeyboardInterrupt:
        print("LSP test run interrupted.")
    except Exception as e:
        print(f"LSP test run failed with exception: {e}")
