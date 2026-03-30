import sys
import asyncio
from collections import deque
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

# Global circular buffer for stdout capturing
log_buffer = deque(maxlen=500)
log_clients = set()

class ConsoleLogger:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout

    def write(self, message):
        self.original_stdout.write(message)
        # Avoid routing empty newlines as independent events if we can help it, 
        # but keep it truthful to stdout.
        if message:
            log_buffer.append(message)
            # Notify connected SSE clients
            # Some processes use threads, so we need to inject into the Main Event Loop securely.
            for queue in log_clients:
                try:
                    queue.put_nowait(message)
                except Exception:
                    pass

    def flush(self):
        self.original_stdout.flush()

# Hook sys.stdout globally to capture prints
if not hasattr(sys.stdout, "original_stdout"):
    sys.stdout = ConsoleLogger(sys.stdout)

async def log_generator():
    # Flush existing history
    for msg in list(log_buffer):
        safe_msg = msg.replace("\n", "\\n")
        yield f"data: {safe_msg}\n\n"
        
    queue = asyncio.Queue()
    log_clients.add(queue)
    try:
        while True:
            msg = await queue.get()
            safe_msg = msg.replace("\n", "\\n")
            yield f"data: {safe_msg}\n\n"
    except asyncio.CancelledError:
        log_clients.remove(queue)
    except Exception:
        if queue in log_clients:
            log_clients.remove(queue)

@router.get("/stream")
async def stream_console():
    return StreamingResponse(log_generator(), media_type="text/event-stream")
