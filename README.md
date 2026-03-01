# 🔍 MTU Finder

A clean, lightweight desktop app for Windows that finds the **optimal MTU (Maximum Transmission Unit)** for your network connection — no command line knowledge required.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## What is MTU and why does it matter?

MTU is the largest packet size your network can send without fragmentation. When it's set too high, packets get silently split up — causing slower speeds, higher latency, and dropped connections, especially on:

- **PPPoE** connections (DSL / fibre via router)
- **VPN** tunnels
- **Wireless** networks with strict path limits

Setting the correct MTU eliminates this overhead and can noticeably improve your connection.

---

## Features

- 📊 **Shows current MTU** for every network adapter on startup
- ⚡ **Binary search algorithm** — finds the optimal MTU in ~10 pings instead of hundreds
- 🎯 **Smart recommendation** — explains what your result means (PPPoE, VPN, standard Ethernet, etc.)
- 📋 **Copy-ready `netsh` command** to apply the MTU directly
- 🚫 **No CMD flashing** — all pings run silently in the background
- 🖥️ **No install needed** — single `.exe` or run directly with Python

---

## Screenshot

https://github.com/SilvioElezi/mtu-finder/blob/main/MTUfinderScreenshot.png

---

## Getting Started

### Option A — Run the `.exe` (easiest)

1. Go to the [Releases](../../releases) page
2. Download `MTU_Finder.exe`
3. Double-click to run — **no Python or install required**

> **Note:** Windows may show a SmartScreen warning for unsigned executables. Click **"More info" → "Run anyway"** to proceed.

### Option B — Run with Python

**Requirements:** Python 3.8+ (tkinter is included by default)

```bash
python mtu_finder.py
```

### Option C — Build the `.exe` yourself

**Requirements:** Python 3.8+, PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name MTU_Finder mtu_finder.py
```

The executable will appear in the `dist/` folder.

---

## How it works

MTU Finder uses a **binary search** approach with ICMP ping packets:

1. Sends a ping with the **Don't Fragment (DF)** flag set at the midpoint of the search range
2. If the packet goes through → MTU is at least that size, search higher
3. If it fragments or fails → MTU is too large, search lower
4. Repeats until the exact maximum is found

This typically takes **10–12 pings** to find the answer across any range.

---

## Applying the result

Once the scan finishes, the app shows the exact command to apply your optimal MTU. Open **Command Prompt as Administrator** and run:

```cmd
netsh interface ipv4 set subinterface "YOUR ADAPTER NAME" mtu=XXXX store=persistent
```

Replace `YOUR ADAPTER NAME` with your adapter (e.g. `Ethernet` or `Wi-Fi`) and `XXXX` with the recommended value. The change is **persistent** across reboots.

---

## Common MTU values

| MTU   | Typical cause                        |
|-------|--------------------------------------|
| 1500  | Standard Ethernet — no change needed |
| 1492  | PPPoE (DSL / fibre via modem-router) |
| 1480  | Some PPPoE or ISP-specific setups    |
| 1400–1460 | VPN or tunnel connection        |
| <1400 | Highly restricted or nested tunnel   |

---

## License

MIT — free to use, modify, and distribute. See [LICENSE](LICENSE) for details.

---

## Contributing

Bug reports and pull requests are welcome! Feel free to open an issue if you hit a problem or have a feature idea.
