import uasyncio as asyncio
import config
from buzzer import start_tone, stop_tone #function names can be changed

_current_task = None

async def _play_note_async(freq: int, ms: int, duty: float) -> None:
    """High-level playback (async)."""
    try:
        start_tone(freq, duty)
        await asyncio.sleep_ms(ms)
    finally:
        stop_tone()

def cancel_current_playback() -> None:
    """Cancel currently scheduled/playing task."""
    global _current_task
    if _current_task and not _current_task.done():
        _current_task.cancel()
        stop_tone()
    _current_task = None
    
def play_tone_for_ms(freq: int, ms: int, duty: float = config.DEFAULT_DUTY) -> None:
    """Schedule immediate tone (non-blocking). Cancels any existing."""
    global _current_task
    cancel_current_playback()
    _current_task = asyncio.create_task(_play_note_async(freq, ms, duty))

async def _play_melody_async(notes: list, gap_ms: int, duty: float):
    """Coroutine that plays a melody sequentially."""
    try:
        for note in notes:
            if isinstance(note, (list, tuple)):
                freq, ms = note
            else:
                freq, ms = note["freq"], note["ms"]
            start_tone(freq, duty)
            await asyncio.sleep_ms(ms)
            stop_tone()
            await asyncio.sleep_ms(gap_ms)
    finally:
        stop_tone()

def play_melody(notes: list, gap_ms: int = config.DEFAULT_GAP_MS, duty: float = config.DEFAULT_DUTY) -> int:
    """Cancel current and queue a melody. Returns count queued."""
    global _current_task
    cancel_current_playback()
    _current_task = asyncio.create_task(_play_melody_async(notes, gap_ms, duty))
    return len(notes)