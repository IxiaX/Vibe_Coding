from __future__ import annotations

import ipaddress
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .ip_lookup import lookup_ip_details
from .models import DeviceRecord
from .networking import get_arp_devices, get_default_gateway
from .script_runner import run_script


class NetworkUtilityApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Network Utility Workbench")
        self.geometry("980x680")

        self.script_queue: list[str] = []
        self.log_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self.after(200, self._pump_logs)

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.overview_tab = ttk.Frame(notebook)
        self.network_tab = ttk.Frame(notebook)
        self.lookup_tab = ttk.Frame(notebook)
        self.scripts_tab = ttk.Frame(notebook)

        notebook.add(self.overview_tab, text="Overview")
        notebook.add(self.network_tab, text="Network Mapper")
        notebook.add(self.lookup_tab, text="IP Lookup")
        notebook.add(self.scripts_tab, text="Script Queue")

        self._build_overview_tab()
        self._build_network_tab()
        self._build_lookup_tab()
        self._build_scripts_tab()

    def _build_overview_tab(self) -> None:
        ttk.Label(
            self.overview_tab,
            text="Network Utility Workbench",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w", pady=(12, 6), padx=12)

        overview = (
            "This app helps inspect your local network and run utility scripts.\n\n"
            "• Network Mapper: finds default gateway and ARP-discovered devices.\n"
            "• IP Lookup: fetches country and organization information for public IPs.\n"
            "• Script Queue: add .py, .bat/.cmd, and .bash/.sh scripts and run in sequence."
        )
        ttk.Label(
            self.overview_tab,
            text=overview,
            justify=tk.LEFT,
            wraplength=900,
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=12, pady=6)

    def _build_network_tab(self) -> None:
        top = ttk.Frame(self.network_tab)
        top.pack(fill=tk.X, padx=12, pady=10)

        ttk.Button(
            top,
            text="Scan Devices via Default Gateway",
            command=self.start_network_scan,
        ).pack(side=tk.LEFT)

        self.gateway_var = tk.StringVar(value="Gateway: (not scanned)")
        ttk.Label(top, textvariable=self.gateway_var).pack(side=tk.LEFT, padx=14)

        columns = ("ip", "mac", "note")
        self.device_tree = ttk.Treeview(self.network_tab, columns=columns, show="headings", height=18)
        self.device_tree.heading("ip", text="IP Address")
        self.device_tree.heading("mac", text="MAC Address")
        self.device_tree.heading("note", text="Info")
        self.device_tree.column("ip", width=180)
        self.device_tree.column("mac", width=230)
        self.device_tree.column("note", width=460)
        self.device_tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

    def _build_lookup_tab(self) -> None:
        controls = ttk.Frame(self.lookup_tab)
        controls.pack(fill=tk.X, padx=12, pady=10)

        ttk.Label(controls, text="IP Address:").pack(side=tk.LEFT)
        self.lookup_entry = ttk.Entry(controls, width=30)
        self.lookup_entry.pack(side=tk.LEFT, padx=8)
        ttk.Button(controls, text="Lookup", command=self.lookup_ip).pack(side=tk.LEFT)

        self.lookup_output = tk.Text(self.lookup_tab, height=28, wrap=tk.WORD)
        self.lookup_output.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

    def _build_scripts_tab(self) -> None:
        controls = ttk.Frame(self.scripts_tab)
        controls.pack(fill=tk.X, padx=12, pady=10)

        ttk.Button(controls, text="Add Script", command=self.add_script).pack(side=tk.LEFT)
        ttk.Button(controls, text="Remove Selected", command=self.remove_script).pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Run Selected", command=self.run_selected_script).pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Run Queue", command=self.run_all_scripts).pack(side=tk.LEFT, padx=6)

        body = ttk.Frame(self.scripts_tab)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.queue_list = tk.Listbox(body, height=12)
        self.queue_list.pack(side=tk.LEFT, fill=tk.Y)

        self.script_log = tk.Text(body, wrap=tk.WORD)
        self.script_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))

    def _pump_logs(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.script_log.insert(tk.END, msg + "\n")
                self.script_log.see(tk.END)
        except queue.Empty:
            pass
        self.after(200, self._pump_logs)

    def start_network_scan(self) -> None:
        for row in self.device_tree.get_children():
            self.device_tree.delete(row)
        self.gateway_var.set("Gateway: scanning...")

        def worker() -> None:
            try:
                gateway = get_default_gateway()
                devices = get_arp_devices()
                self.after(0, self._display_network_results, gateway, devices)
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: messagebox.showerror("Scan Error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _display_network_results(self, gateway: str, devices: list[DeviceRecord]) -> None:
        self.gateway_var.set(f"Gateway: {gateway or 'not found'}")
        if not devices:
            self.device_tree.insert("", tk.END, values=("-", "-", "No ARP devices found"))
            return
        for device in devices:
            note = "Default Gateway" if gateway and device.ip == gateway else device.note
            self.device_tree.insert("", tk.END, values=(device.ip, device.mac, note))

    def lookup_ip(self) -> None:
        ip = self.lookup_entry.get().strip()
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            messagebox.showwarning("Invalid IP", "Please enter a valid IPv4/IPv6 address.")
            return

        self.lookup_output.delete("1.0", tk.END)
        self.lookup_output.insert(tk.END, f"Looking up {ip}...\n")

        def worker() -> None:
            payload = lookup_ip_details(ip)
            self.after(0, self._render_lookup_result, payload)

        threading.Thread(target=worker, daemon=True).start()

    def _render_lookup_result(self, payload: dict[str, str]) -> None:
        self.lookup_output.delete("1.0", tk.END)
        if payload.get("status") != "success":
            self.lookup_output.insert(tk.END, f"Lookup failed: {payload.get('message', 'unknown error')}\n")
            return

        lines = [
            f"IP: {payload.get('query', '-')}",
            f"Country: {payload.get('country', '-')}",
            f"Region/City: {payload.get('regionName', '-')}, {payload.get('city', '-')}",
            f"ISP: {payload.get('isp', '-')}",
            f"Organization: {payload.get('org', '-')}",
            f"ASN: {payload.get('as', '-')}",
        ]
        self.lookup_output.insert(tk.END, "\n".join(lines) + "\n")

    def add_script(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select scripts",
            filetypes=[("Scripts", "*.py *.bat *.cmd *.bash *.sh"), ("All files", "*.*")],
        )
        for path in files:
            if path not in self.script_queue:
                self.script_queue.append(path)
                self.queue_list.insert(tk.END, path)

    def remove_script(self) -> None:
        selected = list(self.queue_list.curselection())
        for idx in reversed(selected):
            self.queue_list.delete(idx)
            self.script_queue.pop(idx)

    def run_selected_script(self) -> None:
        selection = self.queue_list.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Select a script to run.")
            return

        path = self.script_queue[selection[0]]
        threading.Thread(target=self._execute_script, args=(path,), daemon=True).start()

    def run_all_scripts(self) -> None:
        if not self.script_queue:
            messagebox.showinfo("Queue Empty", "Add scripts first.")
            return

        def worker() -> None:
            for path in self.script_queue:
                self._execute_script(path)

        threading.Thread(target=worker, daemon=True).start()

    def _execute_script(self, path: str) -> None:
        self.log_queue.put(f">>> Running: {path}")
        returncode, stdout, stderr, error = run_script(path)

        if error:
            self.log_queue.put(f"[error] {error}")
            return

        if stdout.strip():
            self.log_queue.put(stdout.strip())
        if stderr.strip():
            self.log_queue.put("[stderr] " + stderr.strip())
        self.log_queue.put(f"<<< Exit code: {returncode}\n")
