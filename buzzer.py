import machine

# Setup PWM on GP16
_buzzer_pin = machine.Pin(16)
_pwm = machine.PWM(_buzzer_pin)
_pwm.duty_u16(0)

def start_tone(freq: int, duty: float = 0.5) -> None:
    """
    Start playing a tone at given frequency and duty cycle.
    Args:
        freq: frequency in Hz
        duty: duty cycle [0.0, 1.0]
    """
    if freq <= 0:
        stop_tone()
        return
    _pwm.freq(freq)
    duty_val = int(65535 * duty)
    _pwm.duty_u16(duty_val)

def stop_tone() -> None:
    """Stop playing sound (set duty to 0)."""
    _pwm.duty_u16(0)


