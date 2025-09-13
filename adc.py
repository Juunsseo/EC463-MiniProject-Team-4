import machine

# Initialize ADC on GP28 (ADC2)
adc = machine.ADC(28)

#Calibrated Values
RAW_MIN = 600      # Dark
RAW_MAX = 65338    # Flashlight

def read_sensor_raw() -> int:
    """
    Read raw ADC from the photoresistor.
    Returns 16-bit value.
    """
    return adc.read_u16()

def normalize_raw(raw: int, min_in: RAW_MIN, max_in: RAW_MAX) -> float:
    """
    Normalize raw ADC value to a float in [0.0, 1.0].
    Returns: float in [0.0, 1.0]
    """
    if raw < min_in:
        raw = min_in
    elif raw > max_in:
        raw = max_in
    return (raw - min_in) / (max_in - min_in)

def estimate_lux(norm: float) -> float:
    """Rough estimate of lux  from normalized value."""
    return norm * 1000


