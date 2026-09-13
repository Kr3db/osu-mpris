# osu!lazer MPRIS Bridge (`osu-mpris`) 🎧⚡

A lightweight, zero-latency Python daemon that bridges **osu!lazer** (via `tosu` v2 WebSocket API) to the standard Linux **MPRIS DBus Interface** (`org.mpris.MediaPlayer2`).

This enables any Linux media player widget (**Quickshell, Waybar, Ags, Playerctl, Sway, KDE Plasma**) to display currently playing beatmap metadata, cover art, synchronized lyrics, and track position in real-time.

---

## ✨ Features

- **`selectPlay` State Support:** Correctly maps beatmap selection previews (`selectPlay`) to a "Playing" state so widgets don't pause while browsing songs in the menu.
- **Explicit `Seeked` Signal Emission:** Emits the DBus `Seeked` signal whenever song position jumps or restarts. Fixes lyrics widgets (like Quickshell) freezing at `0:00`.
- **Automatic Cover Art Caching:** Fetches beatmap background artwork from `tosu` and exposes it via `mpris:artUrl`.
- **Low Footprint:** Persistent HTTP connections with low CPU overhead.

---

## 🛠️ Prerequisites

1. **osu!lazer** running on Linux.
2. **tosu v2** running in the background (defaulting to `http://127.0.0.1:24050`).
3. **Python 3.10+** with `dbus-next`:
   ```bash
   pip install dbus-next
   ```

---

## 🚀 Installation & Running

### 1. Manual Execution
Clone this repository and run the daemon:
```bash
git clone https://github.com/YOUR_USERNAME/osu-mpris.git
cd osu-mpris
python3 osu-mpris.py
```

### 2. Systemd User Service (Autostart)
Copy `osu-mpris.py` to `~/.local/bin/` and install the systemd service:

```bash
mkdir -p ~/.config/systemd/user/
cp osu-mpris.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now osu-mpris.service
```

---

## 🧪 Verification

To test if `osu!lazer` is properly recognized by MPRIS:

```bash
playerctl -p osu_lazer status
playerctl -p osu_lazer metadata
```

---

## 📜 License

Licensed under the [MIT License](LICENSE).
