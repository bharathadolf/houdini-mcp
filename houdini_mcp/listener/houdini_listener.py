"""
Embedded TCP Socket Listener for Houdini.
"""
import socket
import threading
import logging
from typing import Optional
from ..framing import send_framed_json, read_framed_json, ProtocolError, ConnectionClosedError
from .main_thread import run_in_main_thread
from .handlers import dispatch_command

logger = logging.getLogger("houdini_mcp.listener")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876

class HoudiniMCPListener:
    """TCP Listener server running inside Houdini."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        if self._running:
            logger.info("Houdini MCP Listener is already running.")
            return

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self._running = True

        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()
        print(f"[Houdini MCP] Listener started on {self.host}:{self.port}")

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        print("[Houdini MCP] Listener stopped.")

    def is_running(self) -> bool:
        return self._running

    def _server_loop(self):
        while self._running and self._server_socket:
            try:
                conn, addr = self._server_socket.accept()
                client_thread = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                client_thread.start()
            except Exception as e:
                if self._running:
                    logger.error(f"Error accepting connection: {e}")

    def _handle_client(self, conn: socket.socket, addr: tuple):
        with conn:
            try:
                command_payload = read_framed_json(conn)
                cmd_type = command_payload.get("type", "")
                params = command_payload.get("params", {})

                # Execute command on Houdini main thread
                try:
                    result = run_in_main_thread(dispatch_command, cmd_type, params)
                    response = {"status": "success", "result": result}
                except Exception as e:
                    logger.error(f"Command '{cmd_type}' failed: {e}", exc_info=True)
                    response = {"status": "error", "message": str(e)}

                send_framed_json(conn, response)

            except (ConnectionClosedError, ProtocolError) as e:
                logger.warning(f"Connection error with client {addr}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error handling client {addr}: {e}", exc_info=True)


# Global singleton instance for shelf tool control
_GLOBAL_LISTENER: Optional[HoudiniMCPListener] = None

def get_listener() -> HoudiniMCPListener:
    global _GLOBAL_LISTENER
    if _GLOBAL_LISTENER is None:
        _GLOBAL_LISTENER = HoudiniMCPListener()
    return _GLOBAL_LISTENER

def start_listener(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> HoudiniMCPListener:
    listener = get_listener()
    listener.host = host
    listener.port = port
    listener.start()
    return listener

def stop_listener():
    global _GLOBAL_LISTENER
    if _GLOBAL_LISTENER:
        _GLOBAL_LISTENER.stop()

def toggle_listener(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    listener = get_listener()
    if listener.is_running():
        listener.stop()
        return False
    else:
        listener.start()
        return True

if __name__ == "__main__":
    start_listener()
