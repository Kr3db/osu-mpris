#!/usr/bin/env python3
import asyncio
import http.client
import json
from pathlib import Path

from dbus_next import Variant, PropertyAccess
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, dbus_property, method, signal


TOSU_HOST = "127.0.0.1"
TOSU_PORT = 24050
TOSU_PATH = "/json/v2"
ART_PATH = "/files/beatmap/background"

BUS_NAME = "org.mpris.MediaPlayer2.osu_lazer"
OBJECT_PATH = "/org/mpris/MediaPlayer2"

CACHE_DIR = Path.home() / ".cache" / "osu-mpris"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class TosuClient:
    """Reusable HTTP client for tosu to avoid continuous TCP socket recreation."""

    def __init__(self, host: str = TOSU_HOST, port: int = TOSU_PORT):
        self.host = host
        self.port = port
        self._conn: http.client.HTTPConnection | None = None

    def get_json(self, path: str = TOSU_PATH, timeout: float = 2.0) -> dict | None:
        if self._conn is None:
            self._conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)

        try:
            self._conn.request("GET", path, headers={"User-Agent": "osu-mpris"})
            res = self._conn.getresponse()
            if res.status == 200:
                data = res.read()
                return json.loads(data.decode("utf-8"))
            else:
                self.close()
                return None
        except Exception:
            self.close()
            raise

    def get_bytes(self, path: str = ART_PATH, timeout: float = 5.0) -> bytes | None:
        if self._conn is None:
            self._conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)

        try:
            self._conn.request("GET", path, headers={"User-Agent": "osu-mpris"})
            res = self._conn.getresponse()
            if res.status == 200:
                return res.read()
            else:
                self.close()
                return None
        except Exception:
            self.close()
            raise

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


class MPRISRoot(ServiceInterface):
    def __init__(self):
        super().__init__("org.mpris.MediaPlayer2")

    @dbus_property(access=PropertyAccess.READ)
    def CanQuit(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanRaise(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def HasTrackList(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> "s":
        return "osu!lazer"

    @dbus_property(access=PropertyAccess.READ)
    def DesktopEntry(self) -> "s":
        return "osu"

    @dbus_property(access=PropertyAccess.READ)
    def SupportedUriSchemes(self) -> "as":
        return []

    @dbus_property(access=PropertyAccess.READ)
    def SupportedMimeTypes(self) -> "as":
        return []

    @method()
    def Quit(self):
        pass

    @method()
    def Raise(self):
        pass


class MPRISPlayer(ServiceInterface):
    def __init__(self):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self._playback_status = "Stopped"
        self._metadata = {}
        self._position_us = 0
        self._rate = 1.0

    @signal()
    def Seeked(self, Position: "x") -> "x":
        return Position

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> "s":
        return self._playback_status

    @dbus_property(access=PropertyAccess.READ)
    def Rate(self) -> "d":
        return self._rate

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":
        return self._metadata

    @dbus_property(access=PropertyAccess.READ)
    def Volume(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def Position(self) -> "x":
        return self._position_us

    @dbus_property(access=PropertyAccess.READ)
    def MinimumRate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MaximumRate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanSeek(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> "b":
        return True

    @method()
    def Next(self):
        pass

    @method()
    def Previous(self):
        pass

    @method()
    def Pause(self):
        pass

    @method()
    def PlayPause(self):
        pass

    @method()
    def Stop(self):
        pass

    @method()
    def Play(self):
        pass

    @method()
    def Seek(self, Offset: "x"):
        pass

    @method()
    def SetPosition(self, TrackId: "o", Position: "x"):
        pass

    @method()
    def OpenUri(self, Uri: "s"):
        pass

    def update_state(self, status: str, metadata: dict, position_us: int, seeked: bool = False):
        changed_props = {}

        if status != self._playback_status:
            self._playback_status = status
            changed_props["PlaybackStatus"] = Variant("s", status)

        if metadata != self._metadata:
            self._metadata = metadata
            changed_props["Metadata"] = Variant("a{sv}", metadata)

        position_jumped = abs(position_us - self._position_us) > 2000000
        self._position_us = position_us

        if changed_props:
            self.emit_properties_changed(changed_props)

        if seeked or position_jumped:
            self.Seeked(position_us)


async def main():
    bus = await MessageBus().connect()

    root = MPRISRoot()
    player = MPRISPlayer()

    bus.export(OBJECT_PATH, root)
    bus.export(OBJECT_PATH, player)
    await bus.request_name(BUS_NAME)

    tosu = TosuClient()
    current_art_id = None
    last_position_ms = 0

    while True:
        try:
            data = await asyncio.to_thread(tosu.get_json)
        except Exception:
            data = None

        if not data:
            player.update_state("Stopped", {}, 0)
            current_art_id = None
            last_position_ms = 0
            await asyncio.sleep(1.0)
            continue

        state_str = str(data.get("state", {}).get("number", 0))

        # state map: 2 = play, 7 = result, "selectPlay" = song selection menu
        if state_str in ("2", "7", "selectPlay"):
            playback_status = "Playing"
        else:
            playback_status = "Paused"

        beatmap = data.get("beatmap", {}) or {}
        artist = beatmap.get("artist", "Unknown Artist")
        title = beatmap.get("title", "Unknown Title")
        map_id = str(beatmap.get("id", 0))
        set_id = str(beatmap.get("setId", 0))
        length_ms = beatmap.get("time", {}).get("live", 0) or beatmap.get("time", {}).get("firstObject", 0)

        position_ms = data.get("performance", {}).get("songTime", 0) or data.get("directPath", {}).get("songTime", 0) or 0
        position_us = int(position_ms * 1000)

        art_url = ""
        art_key = f"{set_id}_{map_id}"
        if set_id != "0":
            art_file = CACHE_DIR / f"{art_key}.jpg"
            if not art_file.exists() or current_art_id != art_key:
                try:
                    img_bytes = await asyncio.to_thread(tosu.get_bytes)
                    if img_bytes:
                        art_file.write_bytes(img_bytes)
                        current_art_id = art_key
                except Exception:
                    pass

            if art_file.exists():
                art_url = art_file.as_uri()

        metadata = {
            "mpris:trackid": Variant("o", f"/org/mpris/MediaPlayer2/track/{art_key}"),
            "mpris:length": Variant("x", int(length_ms * 1000)),
            "mpris:artUrl": Variant("s", art_url),
            "xesam:title": Variant("s", title),
            "xesam:artist": Variant("as", [artist]),
            "xesam:album": Variant("s", "osu!lazer"),
        }

        seeked = abs(position_ms - last_position_ms) > 2000
        last_position_ms = position_ms

        player.update_state(playback_status, metadata, position_us, seeked=seeked)
        await asyncio.sleep(0.2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
