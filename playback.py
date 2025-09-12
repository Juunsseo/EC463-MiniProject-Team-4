import uasyncio as asyncio
import config
from drivers.buzzer import start_tone, stop_tone #function names can be changed

_current_task = None