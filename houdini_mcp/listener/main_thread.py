"""
Main thread dispatcher for Houdini API calls.
"""
import logging
from typing import Callable, Any

logger = logging.getLogger("houdini_mcp.main_thread")

def run_in_main_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Executes a callable safely on Houdini's main GUI thread.
    Uses `hdefereval.executeInMainThreadWithResult` when running inside Houdini GUI,
    or falls back to direct execution when running headless in hython or test scripts.
    """
    try:
        import hdefereval
        return hdefereval.executeInMainThreadWithResult(func, *args, **kwargs)
    except ImportError:
        # Fallback for standalone scripts, unit tests, or hython headless execution
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing function on Houdini main thread: {e}")
        raise
