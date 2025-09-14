# conductor.py
# To be run on a student's computer (not the Pico)
# Requires the 'requests' library: pip install requests.

from typing import List, Dict, Optional
import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuration ---
# Students should populate this list with the IP address(es of their Picos
PICO_IPS: List[str] = [
    "192.168.1.101",
]

logger = logging.getLogger("conductor")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Music Definition ---
# Notes mapped to frequencies (in Hz)
C4 = 262
D4 = 294
E4 = 330
F4 = 349
G4 = 392
A4 = 440
B4 = 494
C5 = 523

# A simple melody: "Twinkle, Twinkle, Little Star"
# Format: (note_frequency, duration_in_ms)
SONG = [
    {"freq": C4, "ms": 400, "duty": 0.5},
    {"freq": C4, "ms": 400, "duty": 0.5},
    {"freq": G4, "ms": 400, "duty": 0.5},
    {"freq": G4, "ms": 400, "duty": 0.5},
    {"freq": A4, "ms": 400, "duty": 0.5},
    {"freq": A4, "ms": 400, "duty": 0.5},
    {"freq": G4, "ms": 800, "duty": 0.5},
    {"freq": F4, "ms": 400, "duty": 0.5},
    {"freq": F4, "ms": 400, "duty": 0.5},
    {"freq": E4, "ms": 400, "duty": 0.5},
    {"freq": E4, "ms": 400, "duty": 0.5},
    {"freq": D4, "ms": 400, "duty": 0.5},
    {"freq": D4, "ms": 400, "duty": 0.5},
    {"freq": C4, "ms": 800, "duty": 0.5},
]

# --- Conductor Logic ---

def load_picos(path: Optional[str] = None) -> List[str]:
    """
    Input:
      - path: Optional path to file with one IP per line
    Output:
      - list of Pico IP strings (e.g., ["192.168.1.101", "192.168.1.102"])
    Side-effects:
      - None
    Notes:
      - If path is None, returns default PICO_IPS constant
    """
    if path is None:
        return list(PICO_IPS)
    ips: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                ips.append(s)
    except FileNotFoundError:
        logger.warning("Pico list file not found: %s. Using default list.", path)
        return list(PICO_IPS)
    return ips


def send_post(ip: str, path: str, payload: Dict, timeout: float = 0.2) -> requests.Response:
    """
    Input:
      - ip: "192.168.1.101" or "host:port"
      - path: API path, e.g. "/tone" or "/melody"
      - payload: dict representing JSON body
      - timeout: float seconds
    Output:
      - requests.Response object (may raise RequestException on errors)
    Side-effects:
      - Network: a JSON POST to http://{ip}{path}.
      - Ensures path starts with '/'.
      - May raise requests.RequestException on network errors.
    """
    if not path.startswith("/"):
        path = "/" + path
    url = f"http://{ip}{path}"
    logger.debug("POST %s payload=%s timeout=%s", url, payload, timeout)
    resp = requests.post(url, json=payload, timeout=timeout)
    logger.debug("Response %s: %s", url, resp.status_code)
    return resp


def play_note_on_all(freq, ms):
    """Sends a /tone POST request to every Pico in the list."""
    print(f"Playing note: {freq}Hz for {ms}ms on all devices.")

    payload = {"freq": freq, "ms": ms, "duty": 0.5}

    for ip in PICO_IPS:
        url = f"http://{ip}/tone"
        try:
            # We use a short timeout because we don't need to wait for a response
            # This makes the orchestra play more in sync.
            requests.post(url, json=payload, timeout=0.1)
        except requests.exceptions.Timeout:
            # This is expected, we can ignore it
            pass
        except requests.exceptions.RequestException as e:
            print(f"Error contacting {ip}: {e}")  


def play_note_on_pico(ip: str, freq: int, ms: int, duty: float = 0.5) -> None:
    """
    Sends POST /tone to a single Pico. Best-effort: swallow network errors.
    
    Input:
      - ip: Pico IP address
      - freq: frequency in Hz
      - ms: duration in milliseconds
      - duty: duty cycle (volume) 0.0-1.0
    Output:
      - None
    Side-effects:
      - Sends POST /tone to the specified Pico
    Notes:
      - Best effort: ignores network exceptions to avoid blocking orchestration
    """
    payload = {"freq": int(freq), "ms": int(ms), "duty": float(duty)}
    try:
        send_post(ip, "/tone", payload, timeout=0.15)
        logger.debug("Sent /tone to %s payload=%s", ip, payload)
    except requests.RequestException as e:
        logger.warning("play_note_on_pico: %s error: %s", ip, e)


def play_melody_on_all(picos: List[str], notes: List[Dict], gap_ms: int = 20) -> None:
    """
    Broadcast a queued melody to all Picos concurrently.
    Expects notes like: [{"freq":440, "ms":300, "duty":0.5}, ...]

    Input:
      - picos: list of Pico IPs
      - notes: list of {"freq":int,"ms":int,"duty"?:float}
      - gap_ms: gap between notes in ms
    Output:
      - None
    Side-effects:
      - Sends POST /melody to each Pico
    """
    if not picos:
        logger.debug("play_melody_on_all: empty pico list")
        return
    if not notes:
        logger.debug("play_melody_on_all: empty notes list")
        return

    # Normalize and filter notes
    norm_notes: List[Dict] = []
    for n in notes:
        if "freq" in n and "ms" in n:
            norm_notes.append({
                "freq": int(n["freq"]),
                "ms": int(n["ms"]),
                "duty": float(n.get("duty", 0.5)),
            })
    if not norm_notes:
        logger.debug("play_melody_on_all: no valid notes after normalization")
        return

    payload = {"notes": norm_notes, "gap_ms": int(gap_ms)}

    def _send(ip: str) -> None:
        try:
            send_post(ip, "/melody", payload, timeout=0.2)
        except requests.RequestException:
            # Best-effort; ignore per device
            pass

    max_workers = min(16, max(1, len(picos)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for ip in picos:
            ex.submit(_send, ip)
    logger.debug("Broadcast /melody to %d devices payload=%s", len(picos), payload)

def conductor_play_song(picos: List[str], song: List[Dict] = SONG, gap_factor: float = 1.1) -> None:
    """
    High-level broadcast composition.
    Input:
      - picos: list of Pico IPs
      - song: list of {"freq":int,"ms":int,"duty":float}
      - gap_factor: multiplier to stretch pause between notes
    Output:
      - None
    Side-effects:
      - Iteratively calls play_note_on_all
      - Sleeps locally to pace the song
    """
    if not song:
        logger.debug("Empty song passed to conductor_play_song")
        return
    logger.info("Starting song: %d notes across %d devices", len(song), len(picos))
    try:
        for idx, note in enumerate(song, start=1):
            freq = int(note["freq"])
            ms = int(note["ms"])
            duty = float(note.get("duty", 0.5))
            logger.info("Note %d/%d: %dHz %dms duty=%s", idx, len(song), freq, ms, duty)
            play_note_on_all(picos, freq, ms, duty)
            # Local pacing: stretch the sleep slightly to give devices time to play
            sleep_s = (ms / 1000.0) * float(gap_factor)
            time.sleep(max(0.0, sleep_s))
    except KeyboardInterrupt:
        logger.info("Conductor stopped by user.")


if __name__ == "__main__":
    print("--- Pico Light Orchestra Conductor ---")
    print(f"Found {len(PICO_IPS)} devices in the orchestra.")
    print("Press Ctrl+C to stop.")

    try:
        # Give a moment for everyone to get ready
        print("\nStarting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("Go!\n")

        # Play the song
        for note, duration in SONG:
            play_note_on_all(note, duration)
            # Wait for the note's duration plus a small gap before playing the next one
            time.sleep(duration / 1000 * 1.1)

        print("\nSong finished!")

    except KeyboardInterrupt:
        print("\nConductor stopped by user.")
