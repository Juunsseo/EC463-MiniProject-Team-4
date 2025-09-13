import ujson
import uasyncio as asyncio

from device_api import (
    sensor_payload,
    health_payload,
    play_tone_for_ms,
    play_melody,
    cancel_playback,
)

_STATUS_TEXT = {
    200: "OK",
    202: "Accepted",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    415: "Unsupported Media Type",
    500: "Internal Server Error",
}

async def send_json(writer, status: int, obj: dict):
    """Serialize obj to JSON and send an HTTP response."""
    try:
        body = ujson.dumps(obj).encode("utf-8")
    except Exception:
        status = 500
        body = b'{"error":"serialization"}'

    reason = _STATUS_TEXT.get(status, "OK")
    headers = (
        f"HTTP/1.1 {status} {reason}\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")

    writer.write(headers + body)
    if hasattr(writer, "drain"):
        await writer.drain()


async def handle_get_sensor(writer):
    data = sensor_payload()
    await send_json(writer, 200, data)

async def handle_get_health(writer):
    data = health_payload()
    await send_json(writer, 200, data)

async def handle_post_tone(body: dict, writer):
    try:
        freq = int(body.get("freq"))
        ms = int(body.get("ms", 250))
        duty = float(body.get("duty", 0.5))
    except Exception:
        await send_json(writer, 400, {"error": "Invalid tone parameters"})
        return

    await play_tone_for_ms(freq=freq, ms=ms, duty=duty)
    await send_json(writer, 202, {"status": "tone played", "freq": freq, "ms": ms, "duty": duty})

async def handle_post_melody(body: dict, writer):
    try:
        notes = body.get("notes", [])
        gap_ms = int(body.get("gap_ms", 50))
        duty = float(body.get("duty", 0.5))
        if not isinstance(notes, list) or any(
            not isinstance(n, (list, tuple)) or len(n) != 2 for n in notes
        ):
            raise ValueError("notes must be [[freq, ms], ...]")
    except Exception as e:
        await send_json(writer, 400, {"error": "Invalid melody payload", "detail": str(e)})
        return

    await play_melody(notes, gap_ms=gap_ms, duty=duty)
    await send_json(writer, 202, {"status": "melody played", "length": len(notes), "gap_ms": gap_ms, "duty": duty})

async def handle_post_cancel(writer):
    try:
        cancel_playback()
        await send_json(writer, 202, {"status": "canceled"})
    except Exception as e:
        await send_json(writer, 500, {"error": "internal", "detail": str(e)})


async def handle_client(reader, writer):
    try:
        req_line = await reader.readline()
        if not req_line:
            try:
                await writer.aclose()
            except AttributeError:
                writer.close()
            return

        parts = req_line.decode().strip().split()
        if len(parts) < 2:
            await send_json(writer, 400, {"error": "Bad Request"})
            return
        method, path = parts[0], parts[1]

        headers = {}
        while True:
            line = await reader.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
            kv = line.decode().split(":", 1)
            if len(kv) == 2:
                headers[kv[0].strip().lower()] = kv[1].strip()

        if method == "GET":
            if path == "/sensor":
                await handle_get_sensor(writer)
            elif path == "/health":
                await handle_get_health(writer)
            else:
                await send_json(writer, 404, {"error": "Not Found"})

        elif method == "POST":
            clen = int(headers.get("content-length", "0") or "0")
            body_bytes = b""
            while len(body_bytes) < clen:
                chunk = await reader.read(clen - len(body_bytes))
                if not chunk:
                    break
                body_bytes += chunk

            try:
                body = ujson.loads(body_bytes) if body_bytes else {}
            except Exception:
                await send_json(writer, 400, {"error": "Invalid JSON"})
                return

            if path == "/tone":
                await handle_post_tone(body, writer)
            elif path == "/melody":
                await handle_post_melody(body, writer)
            elif path == "/cancel":
                await handle_post_cancel(writer)
            else:
                await send_json(writer, 404, {"error": "Not Found"})

        else:
            await send_json(writer, 405, {"error": "Method Not Allowed"})

    except Exception as e:
        try:
            await send_json(writer, 500, {"error": "internal", "detail": str(e)})
        except Exception:
            pass
    finally:
        try:
            if hasattr(writer, "aclose"):
                await writer.aclose()
            else:
                writer.close()
        except Exception:
            pass


async def main(host="0.0.0.0", port=80):
    server = await asyncio.start_server(handle_client, host, port)
    try:
        async with server:
            await server.serve_forever()
    finally:
        try:
            server.close()
            if hasattr(server, "wait_closed"):
                await server.wait_closed()
        except Exception:
            pass
