import gc, utime
from adc import read_sensor_raw, normalize_raw, estimate_lux #function names can be changed

def sensor_payload() -> dict:
    """Build /sensor response body."""
    raw = read_sensor_raw()
    norm = normalize_raw(raw)
    lux = estimate_lux(norm)
    return {"raw": raw, "norm": norm, "lux": lux}

def health_payload(device_id: str = "pico-w-unknown") -> dict:
    """Health & sensor payloads."""
    return {
        "device_id": device_id,
        "uptime_ms": utime.ticks_ms(),
        "heap_free": gc.mem_free(),
        "sensor": sensor_payload()
    }