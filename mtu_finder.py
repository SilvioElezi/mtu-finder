"""
MTU Finder - Find the optimal MTU for your network connection
Run as: python mtu_finder.py
Build with: pyinstaller --onefile --windowed --name MTU_Finder mtu_finder.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import platform
import re

# ── Colours & fonts ────────────────────────────────────────────────────────────
BG       = "#1e1e2e"
CARD     = "#2a2a3e"
ACCENT   = "#7c3aed"
ACCENT2  = "#a855f7"
SUCCESS  = "#22c55e"
WARNING  = "#f59e0b"
DANGER   = "#ef4444"
TEXT     = "#e2e8f0"
MUTED    = "#94a3b8"
FONT_H   = ("Segoe UI", 13, "bold")
FONT_N   = ("Segoe UI", 10)
FONT_S   = ("Segoe UI", 9)
FONT_M   = ("Consolas", 9)


def get_interfaces():
    """Return list of (adapter_name, mtu) tuples from netsh."""
    adapters = []
    try:
        result = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "subinterfaces"],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        for line in result.stdout.splitlines():
            # Lines look like: "  1500  ...  ...  Local Area Connection"
            parts = line.split()
            if parts and re.match(r'^\d+$', parts[0]):
                mtu_val = int(parts[0])
                # Adapter name is everything after the first 3 numeric columns
                name = " ".join(parts[3:]).strip()
                if name:
                    adapters.append((name, mtu_val))
    except Exception:
        pass
    return adapters


def ping_with_size(host: str, size: int, timeout: int = 2) -> bool:
    """Ping host with a packet of exact IP size (header=28 bytes, data=size-28)."""
    data = max(0, size - 28)
    try:
        if platform.system() == "Windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), "-l", str(data), "-f", host]
            flags = 0x08000000  # CREATE_NO_WINDOW — stops CMD flashing
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout), "-s", str(data), "-M", "do", host]
            flags = 0
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout + 1, creationflags=flags)
        output = result.stdout + result.stderr
        if "fragmented" in output.lower() or "fragment" in output.lower():
            return False
        if result.returncode != 0:
            return False
        return True
    except Exception:
        return False


def find_mtu(host, low, high, log_fn, progress_fn, stop_flag):
    """Binary-search for the highest MTU that succeeds."""
    log_fn(f"Starting MTU discovery for host: {host}\n")
    log_fn(f"Search range: {low} – {high} bytes\n\n")

    if not ping_with_size(host, 576):
        log_fn("⚠  Cannot reach host at minimum MTU (576). Check connectivity.\n")
        return None

    best = low
    iterations = 0
    total = (high - low).bit_length() + 1

    while low <= high:
        if stop_flag():
            log_fn("\n⛔  Scan cancelled by user.\n")
            return None

        mid = (low + high) // 2
        iterations += 1
        progress_fn(min(int(iterations / total * 100), 99))

        log_fn(f"  Testing {mid:>5} bytes … ")
        if ping_with_size(host, mid):
            log_fn("✔  OK\n")
            best = mid
            low = mid + 1
        else:
            log_fn("✘  Too large / no reply\n")
            high = mid - 1

    progress_fn(100)
    return best


class MTUApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MTU Finder")
        self.geometry("700x680")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._stop = False
        self._build_ui()
        # Load interfaces after window is ready
        self.after(100, self._load_interfaces)

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=ACCENT, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍  MTU Finder", font=("Segoe UI", 16, "bold"),
                 bg=ACCENT, fg="white").pack()
        tk.Label(hdr, text="Discover the optimal MTU for your network",
                 font=FONT_N, bg=ACCENT, fg="#ddd6fe").pack()

        # ── Current interfaces card ───────────────────────────────────────────
        iface_outer = tk.Frame(self, bg=BG)
        iface_outer.pack(fill="x", padx=16, pady=(12, 0))

        iface_header = tk.Frame(iface_outer, bg=BG)
        iface_header.pack(fill="x")
        tk.Label(iface_header, text="Current MTU — All Interfaces",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=MUTED, anchor="w").pack(side="left")
        self.refresh_btn = tk.Button(iface_header, text="↻ Refresh", font=FONT_S,
                                     bg=CARD, fg=MUTED, activebackground="#3b3b54",
                                     activeforeground=TEXT, relief="flat", padx=6, pady=2,
                                     cursor="hand2", command=self._load_interfaces)
        self.refresh_btn.pack(side="right")

        # Scrollable frame for interfaces
        self.iface_frame = tk.Frame(self, bg=CARD, padx=12, pady=8)
        self.iface_frame.pack(fill="x", padx=16, pady=(4, 0))
        self.iface_placeholder = tk.Label(self.iface_frame, text="Loading interfaces…",
                                          font=FONT_S, bg=CARD, fg=MUTED, anchor="w")
        self.iface_placeholder.pack(fill="x")

        # ── Scan settings card ────────────────────────────────────────────────
        card = tk.Frame(self, bg=CARD, padx=16, pady=12)
        card.pack(fill="x", padx=16, pady=(10, 4))

        r1 = tk.Frame(card, bg=CARD)
        r1.pack(fill="x", pady=3)
        tk.Label(r1, text="Target host:", font=FONT_N, bg=CARD, fg=TEXT,
                 width=14, anchor="w").pack(side="left")
        self.host_var = tk.StringVar(value="8.8.8.8")
        tk.Entry(r1, textvariable=self.host_var, font=FONT_N, bg="#3b3b54", fg=TEXT,
                 insertbackground=TEXT, relief="flat", width=28).pack(side="left", padx=(0, 12))
        tk.Label(r1, text="(IP or hostname)", font=FONT_N, bg=CARD, fg=MUTED).pack(side="left")

        r2 = tk.Frame(card, bg=CARD)
        r2.pack(fill="x", pady=3)
        tk.Label(r2, text="MTU range:", font=FONT_N, bg=CARD, fg=TEXT,
                 width=14, anchor="w").pack(side="left")
        self.low_var  = tk.StringVar(value="576")
        self.high_var = tk.StringVar(value="1500")
        tk.Entry(r2, textvariable=self.low_var,  font=FONT_N, bg="#3b3b54", fg=TEXT,
                 insertbackground=TEXT, relief="flat", width=7).pack(side="left")
        tk.Label(r2, text=" to ", font=FONT_N, bg=CARD, fg=MUTED).pack(side="left")
        tk.Entry(r2, textvariable=self.high_var, font=FONT_N, bg="#3b3b54", fg=TEXT,
                 insertbackground=TEXT, relief="flat", width=7).pack(side="left")
        tk.Label(r2, text="bytes", font=FONT_N, bg=CARD, fg=MUTED).pack(side="left", padx=4)

        btn_row = tk.Frame(card, bg=CARD)
        btn_row.pack(fill="x", pady=(8, 0))
        self.run_btn = tk.Button(btn_row, text="▶  Start Scan", font=FONT_H,
                                 bg=ACCENT, fg="white", activebackground=ACCENT2,
                                 activeforeground="white", relief="flat", padx=16, pady=6,
                                 cursor="hand2", command=self._start)
        self.run_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = tk.Button(btn_row, text="⏹  Stop", font=FONT_N,
                                  bg="#374151", fg=TEXT, activebackground="#4b5563",
                                  activeforeground=TEXT, relief="flat", padx=12, pady=6,
                                  cursor="hand2", state="disabled", command=self._stop_scan)
        self.stop_btn.pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="🗑  Clear", font=FONT_N, bg="#374151", fg=TEXT,
                  activebackground="#4b5563", activeforeground=TEXT, relief="flat",
                  padx=12, pady=6, cursor="hand2", command=self._clear).pack(side="left")

        # Progress bar
        pf = tk.Frame(self, bg=BG)
        pf.pack(fill="x", padx=16, pady=(6, 0))
        self.progress = ttk.Progressbar(pf, mode="determinate", maximum=100)
        self.progress.pack(fill="x")

        # Log
        lf = tk.Frame(self, bg=BG)
        lf.pack(fill="both", expand=True, padx=16, pady=(6, 0))
        tk.Label(lf, text="Output log:", font=FONT_N, bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.log = scrolledtext.ScrolledText(lf, font=FONT_M, bg="#11111b", fg=TEXT,
                                             insertbackground=TEXT, relief="flat",
                                             state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)
        self.log.tag_config("result", foreground=SUCCESS, font=("Segoe UI", 11, "bold"))
        self.log.tag_config("warn",   foreground=WARNING)
        self.log.tag_config("err",    foreground=DANGER)

        # Result bar
        rb = tk.Frame(self, bg=CARD, pady=8)
        rb.pack(fill="x", padx=16, pady=(6, 12))
        self.result_lbl = tk.Label(rb, text="Optimal MTU: —",
                                   font=("Segoe UI", 13, "bold"), bg=CARD, fg=MUTED)
        self.result_lbl.pack()

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor="#2a2a3e", background=ACCENT, thickness=10)

    # ── Interface list ─────────────────────────────────────────────────────────
    def _load_interfaces(self):
        self.refresh_btn.config(state="disabled", text="…")
        threading.Thread(target=self._fetch_interfaces, daemon=True).start()

    def _fetch_interfaces(self):
        adapters = get_interfaces()
        self.after(0, self._render_interfaces, adapters)

    def _render_interfaces(self, adapters):
        # Clear old widgets
        for w in self.iface_frame.winfo_children():
            w.destroy()

        if not adapters:
            tk.Label(self.iface_frame, text="No interfaces found (try running as Administrator)",
                     font=FONT_S, bg=CARD, fg=WARNING, anchor="w").pack(fill="x")
        else:
            # Column headers
            hdr = tk.Frame(self.iface_frame, bg=CARD)
            hdr.pack(fill="x", pady=(0, 4))
            tk.Label(hdr, text="MTU", font=("Segoe UI", 9, "bold"),
                     bg=CARD, fg=MUTED, width=7, anchor="w").pack(side="left")
            tk.Label(hdr, text="Status", font=("Segoe UI", 9, "bold"),
                     bg=CARD, fg=MUTED, width=10, anchor="w").pack(side="left")
            tk.Label(hdr, text="Adapter", font=("Segoe UI", 9, "bold"),
                     bg=CARD, fg=MUTED, anchor="w").pack(side="left")

            tk.Frame(self.iface_frame, bg="#3b3b54", height=1).pack(fill="x", pady=(0, 4))

            for name, mtu in adapters:
                row = tk.Frame(self.iface_frame, bg=CARD)
                row.pack(fill="x", pady=1)

                # MTU value
                mtu_color = SUCCESS if mtu == 1500 else WARNING
                tk.Label(row, text=str(mtu), font=("Consolas", 10, "bold"),
                         bg=CARD, fg=mtu_color, width=7, anchor="w").pack(side="left")

                # Status badge
                if mtu == 1500:
                    badge_text, badge_fg, badge_bg = "standard", "#166534", "#dcfce7"
                elif mtu >= 1400:
                    badge_text, badge_fg, badge_bg = "custom",   "#92400e", "#fef3c7"
                else:
                    badge_text, badge_fg, badge_bg = "low",      "#991b1b", "#fee2e2"

                badge = tk.Label(row, text=f" {badge_text} ", font=FONT_S,
                                 bg=badge_bg, fg=badge_fg, relief="flat")
                badge.pack(side="left", padx=(0, 10))

                # Adapter name (truncate if very long)
                display_name = name if len(name) <= 52 else name[:49] + "…"
                tk.Label(row, text=display_name, font=FONT_S,
                         bg=CARD, fg=TEXT, anchor="w").pack(side="left")

        self.refresh_btn.config(state="normal", text="↻ Refresh")

    # ── Scan ───────────────────────────────────────────────────────────────────
    def _start(self):
        host = self.host_var.get().strip()
        if not host:
            messagebox.showwarning("Input error", "Please enter a target host.")
            return
        try:
            low  = int(self.low_var.get())
            high = int(self.high_var.get())
            assert 28 < low < high <= 9000
        except Exception:
            messagebox.showwarning("Input error", "MTU range must be integers, e.g. 576–1500.")
            return

        self._stop = False
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress["value"] = 0
        self.result_lbl.config(text="Optimal MTU: scanning…", fg=MUTED)
        self._log_clear()

        threading.Thread(target=self._worker, args=(host, low, high), daemon=True).start()

    def _worker(self, host, low, high):
        mtu = find_mtu(host, low, high,
                       log_fn=lambda m: self.after(0, self._log, m),
                       progress_fn=lambda v: self.after(0, self._set_progress, v),
                       stop_flag=lambda: self._stop)

        def done():
            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            if mtu:
                self._log(f"\n{'─'*50}\n", "result")
                self._log(f"✅  Optimal MTU found: {mtu} bytes\n", "result")
                if mtu == 1500:
                    note = "Standard Ethernet — no changes needed."
                elif mtu >= 1480:
                    note = f"Typical for PPPoE. Set interface MTU to {mtu}."
                elif mtu >= 1400:
                    note = f"Possibly VPN tunnel. Set interface MTU to {mtu}."
                else:
                    note = f"Unusual — check your ISP. Set interface MTU to {mtu}."
                self._log(f"💡  {note}\n", "result")
                self._log(f"\nWindows command to apply:\n", None)
                self._log(f'   netsh interface ipv4 set subinterface "<YourAdapter>" mtu={mtu} store=persistent\n', "warn")
                self.result_lbl.config(text=f"✅  Optimal MTU: {mtu} bytes", fg=SUCCESS)
                # Refresh interface list to reflect any changes
                self._load_interfaces()
            elif not self._stop:
                self.result_lbl.config(text="⚠  Scan failed — check host", fg=DANGER)

        self.after(0, done)

    def _stop_scan(self):
        self._stop = True
        self.stop_btn.config(state="disabled")

    def _clear(self):
        self._log_clear()
        self.progress["value"] = 0
        self.result_lbl.config(text="Optimal MTU: —", fg=MUTED)

    def _log(self, msg, tag=None):
        self.log.config(state="normal")
        if tag:
            self.log.insert("end", msg, tag)
        else:
            self.log.insert("end", msg)
        self.log.see("end")
        self.log.config(state="disabled")

    def _log_clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _set_progress(self, v):
        self.progress["value"] = v


if __name__ == "__main__":
    app = MTUApp()
    app.mainloop()
