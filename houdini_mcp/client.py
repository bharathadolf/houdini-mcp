import socket
import logging
from typing import Any, Dict, Optional
from .framing import send_framed_json, read_framed_json, ProtocolError, ConnectionClosedError

logger = logging.getLogger("houdini_mcp.client")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT = 30.0

class HoudiniClientError(Exception):
    """Base exception for Houdini Client communication errors."""
    pass

class HoudiniConnectionError(HoudiniClientError):
    """Raised when connection to Houdini listener fails."""
    pass

class HoudiniCommandError(HoudiniClientError):
    """Raised when Houdini returns an error status for a command."""
    pass


class HoudiniClient:
    """Client for communicating with the embedded Houdini socket listener."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_command(self, cmd_type: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        """Sends a framed command to Houdini and returns the command result."""
        effective_timeout = timeout if timeout is not None else self.timeout
        payload = {
            "type": cmd_type,
            "params": params or {}
        }

        try:
            with socket.create_connection((self.host, self.port), timeout=effective_timeout) as sock:
                send_framed_json(sock, payload)
                response = read_framed_json(sock)

                status = response.get("status")
                if status == "success":
                    return response.get("result")
                elif status == "error":
                    msg = response.get("message", "Unknown error returned from Houdini.")
                    raise HoudiniCommandError(f"Houdini error on command '{cmd_type}': {msg}")
                else:
                    raise HoudiniClientError(f"Malformed response status from Houdini: {status}")

        except (socket.error, ConnectionClosedError) as e:
            raise HoudiniConnectionError(
                f"Could not connect to Houdini MCP listener at {self.host}:{self.port}. "
                f"Ensure Houdini is running and the MCP Listener is started inside Houdini. Error: {e}"
            ) from e
        except ProtocolError as e:
            raise HoudiniClientError(f"Protocol error during '{cmd_type}' execution: {e}") from e
