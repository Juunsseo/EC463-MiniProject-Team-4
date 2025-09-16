# Dashboard.py
# To be run on a student's computer (not the Pico)

import requests
import time
from typing import Dict, List, Optional
import sys

# --- Configuration ---
# Students should populate this list with the IP address(es) of their Pico
PICO_IPS = [
    "192.168.137.116",
]


def fetch_health(ip: str, timeout: float = 1.0) -> Dict:
    """
    Input:
      - ip: Pico IP address (e.g. "192.168.1.101")
      - timeout: float, seconds for the HTTP request
    Output:
      - dict parsed from /health JSON, expected keys:
        {"status": str, "device_id": str, "api": str}
      - Raises requests.exceptions.RequestException on errors
    Side-effects:
      - Network GET to http://{ip}/health
    """
    response = requests.get(f"http://{ip}/health", timeout=timeout)
    # This will raise an exception for bad status codes (like 4xx or 5xx)
    response.raise_for_status()
    return response.json()


def fetch_sensor(ip: str, timeout: float = 1.0) -> Dict:
    """
    Input:
      - ip: Pico IP address
      - timeout: float, seconds for the HTTP request
    Output:
      - dict parsed from /sensor JSON, expected keys:
        {"raw": int, "norm": float, "lux_est": float}
      - Raises requests.exceptions.RequestException on errors
    Side-effects:
      - Network GET to http://{ip}/sensor
    """
    response = requests.get(f"http://{ip}/sensor", timeout=timeout)
    # This will raise an exception for bad status codes
    response.raise_for_status()
    return response.json()


def get_device_status(ip: str, timeout: float = 1.0) -> Dict:
    """
    Input:
      - ip: Pico IP address
      - timeout: per-request timeout
    Output:
      - combined status dict, example:
        {
          "ip": "192.168.1.101",
          "device_id": "pico-w-A1B2C3",
          "status": "ok" | "Offline" | "Error",
          "norm": float
        }
      - Should capture network errors and return Offline/Error instead of raising.
    Side-effects:
      - Calls fetch_health and fetch_sensor.
    """
    status = {"ip": ip, "device_id": "N/A", "status": "Error", "norm": 0.0}
    try:
        # Fetch data using the designated functions
        health_data = fetch_health(ip, timeout)
        sensor_data = fetch_sensor(ip, timeout)

        # Update the status dictionary with data from both fetches
        status["device_id"] = health_data.get("device_id", "Unknown")
        status["status"] = health_data.get("status", "Unknown")
        status["norm"] = sensor_data.get("norm", 0.0)
        
    except requests.exceptions.RequestException as e:
        # Catch any network-related errors and set the status accordingly
        status["status"] = f"Offline ({type(e).__name__})"
    except Exception as e:
        # Catch any other general errors
        status["status"] = f"Error ({type(e).__name__})"

    return status


def collect_all_statuses(ips: List[str], timeout: float = 0.8) -> List[Dict]:
    """
    Input:
      - ips: list of Pico IP strings
      - timeout: per-request timeout
    Output:
      - list of status dicts, one per IP
    Side-effects:
      - Calls get_device_status for each IP
    """
    return [get_device_status(ip, timeout=timeout) for ip in ips]


def render_dashboard(statuses: List[Dict]) -> None:
    """
    Input:
      - statuses: list of status dicts
    Output:
      - None (prints console dashboard)
    Side-effects:
      - Console output (stdout)
    Notes:
      - Renders in a simple, human-readable format.
    """
    print("\033[H\033[J", end="")  # ANSI escape codes to clear the console
    print("--- Pico Orchestra Dashboard --- (Press Ctrl+C to exit)")
    print("-" * 60)
    print(f"{'IP Address':<16} {'Device ID':<25} {'Status':<10} {'Light Level':<20}")
    print("-" * 60)

    for status in statuses:
        # Create a simple bar graph for the light level
        light_level = status.get("norm", 0.0)
        # Ensure bar length is a valid integer between 0 and 10
        bar_length = int(max(0, min(light_level * 10, 10)))
        bar = "█" * bar_length + "─" * (10 - bar_length)

        print(
            f"{status['ip']:<16} {status['device_id']:<25} {status['status'].capitalize():<10} "
            f"[{bar}] {light_level:.2f}"
        )

    print("-" * 60)
    # Add a note about the last refresh time
    print(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    sys.stdout.flush() # Forces the output to be displayed immediately


def run_loop(
    ips: Optional[List[str]] = None,
    poll_interval: float = 1.0,
    iterations: Optional[int] = None,
) -> None:
    """
    Input:
      - ips: list of IPs (defaults to module PICO_IPS)
      - poll_interval: seconds between polls
      - iterations: number of times to run, or None for infinite
    Output:
      - None
    Side-effects:
      - Repeatedly polls devices and prints dashboard
    Notes:
      - Stoppable with KeyboardInterrupt
    """
    target_ips = ips if ips is not None else PICO_IPS
    count = 0
    
    while True:
        try:
            statuses = collect_all_statuses(target_ips)
            render_dashboard(statuses)
            
            # Stop after a certain number of iterations if specified
            if iterations is not None:
                count += 1
                if count >= iterations:
                    print(f"\nCompleted {iterations} iterations.")
                    break
                    
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            print("\nDashboard stopped.")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            break


if __name__ == "__main__":
    # The main entry point now calls the run_loop function
    run_loop()
