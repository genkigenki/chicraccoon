"""Simple window for non-technical users (tkinter, standard library only).

Pick an enote.bkup, press Start: the notes are converted into a website
(<backup>_html/index.html) and, optionally, into PDF files
(<backup>_html/PDF). Running it again with the same output folder only
converts pages that changed.

Start with:  python -m chicraccoon.gui   (or double-click START_Windows.bat)
"""
import contextlib
import glob
import json
import locale
import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

LANGS = [('ja', '日本語'), ('en', 'English'), ('de', 'Deutsch')]

TEXT = {
    'en': {
        'title': 'eNote backup viewer',
        'intro': 'Turns a Sharp eNote backup (enote.bkup) into a website you '
                 'can open in your browser, and optionally into PDF files.',
        'language': 'Language:',
        'backup': '1. Backup file:',
        'choose_backup': 'Choose backup file (enote.bkup)…',
        'output': '2. Save to folder:',
        'choose_output': 'Change…',
        'pdf': 'Also create PDF files',
        'start': 'Start',
        'open': 'Open result',
        'no_backup': 'Please choose a backup file (enote.bkup) first.',
        'not_found': 'The backup file was not found:',
        'working': 'Working… this can take a few minutes the first time.',
        'reading': 'Reading backup and converting pages…',
        'converted': 'pages converted, {} unchanged',
        'making_pdf': 'Creating PDF files…',
        'done': 'Done! Your notes open in the browser now.',
        'done_pdf': 'PDF files are in:',
        'error': 'Something went wrong:',
        'error_title': 'Error',
        'filetypes': 'eNote backup',
        'allfiles': 'All files',
    },
    'ja': {
        'title': '電子ノート バックアップビューア',
        'intro': 'シャープ電子ノートのバックアップ（enote.bkup）を、ブラウザで'
                 '見られるウェブページとPDFファイルに変換します。',
        'language': '言語：',
        'backup': '1. バックアップファイル：',
        'choose_backup': 'バックアップファイル（enote.bkup）を選ぶ…',
        'output': '2. 保存先フォルダ：',
        'choose_output': '変更…',
        'pdf': 'PDFファイルも作成する',
        'start': 'スタート',
        'open': '結果を開く',
        'no_backup': '先にバックアップファイル（enote.bkup）を選んでください。',
        'not_found': 'バックアップファイルが見つかりません：',
        'working': '処理中です… 初回は数分かかることがあります。',
        'reading': 'バックアップを読み込み、ページを変換しています…',
        'converted': 'ページを変換しました（変更なし：{}）',
        'making_pdf': 'PDFファイルを作成しています…',
        'done': '完了しました！ブラウザでノートを開きます。',
        'done_pdf': 'PDFファイルの保存先：',
        'error': 'エラーが発生しました：',
        'error_title': 'エラー',
        'filetypes': '電子ノートのバックアップ',
        'allfiles': 'すべてのファイル',
    },
    'de': {
        'title': 'eNote-Backup-Betrachter',
        'intro': 'Macht aus einem Sharp-eNote-Backup (enote.bkup) eine '
                 'Webseite für den Browser und auf Wunsch PDF-Dateien.',
        'language': 'Sprache:',
        'backup': '1. Backup-Datei:',
        'choose_backup': 'Backup-Datei wählen (enote.bkup)…',
        'output': '2. Speichern in Ordner:',
        'choose_output': 'Ändern…',
        'pdf': 'Auch PDF-Dateien erstellen',
        'start': 'Start',
        'open': 'Ergebnis öffnen',
        'no_backup': 'Bitte zuerst eine Backup-Datei (enote.bkup) wählen.',
        'not_found': 'Die Backup-Datei wurde nicht gefunden:',
        'working': 'Bitte warten… beim ersten Mal kann das einige Minuten '
                   'dauern.',
        'reading': 'Backup wird gelesen, Seiten werden umgewandelt…',
        'converted': 'Seiten umgewandelt, {} unverändert',
        'making_pdf': 'PDF-Dateien werden erstellt…',
        'done': 'Fertig! Die Notizen öffnen sich jetzt im Browser.',
        'done_pdf': 'Die PDF-Dateien liegen in:',
        'error': 'Etwas ist schiefgegangen:',
        'error_title': 'Fehler',
        'filetypes': 'eNote-Backup',
        'allfiles': 'Alle Dateien',
    },
}

PDF_PREFIX = 'eNote'
SETTINGS = os.path.join(os.path.expanduser('~'), '.chicraccoon_gui.json')


def system_language():
    """'ja', 'de' or 'en' from the operating system's language."""
    codes = []
    if sys.platform == 'win32':
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            codes.append({0x11: 'ja', 0x07: 'de'}.get(langid & 0x3ff, 'en'))
        except Exception:
            pass
    for var in ('LC_ALL', 'LC_MESSAGES', 'LANG', 'LANGUAGE'):
        if os.environ.get(var):
            codes.append(os.environ[var])
    try:
        codes.append(locale.getlocale()[0] or '')
    except Exception:
        pass
    for code in codes:
        code = code.lower()
        if code.startswith(('ja', 'japanese')):
            return 'ja'
        if code.startswith(('de', 'german')):
            return 'de'
        if code.startswith('en'):
            return 'en'
    return 'en'


def default_output(backup):
    base = os.path.splitext(os.path.basename(backup))[0] or 'enote'
    return os.path.join(os.path.dirname(os.path.abspath(backup)),
                        base + '_html')


def open_path(path):
    """Open a file or folder with the system's default program."""
    try:
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
    except Exception:
        pass


class _QueueWriter:
    """File-like object that forwards printed lines to the GUI."""

    def __init__(self, q):
        self.q, self.buf = q, ''

    def write(self, s):
        self.buf += s
        while '\n' in self.buf:
            line, self.buf = self.buf.split('\n', 1)
            self.q.put(('line', line))
        return len(s)

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.running = False
        self.result = None
        self.converted = self.unchanged = 0

        settings = self._load_settings()
        lang = settings.get('lang')
        self.lang = lang if lang in TEXT else system_language()
        self.backup = tk.StringVar(value=settings.get('backup', ''))
        self.output = tk.StringVar(value=settings.get('output', ''))
        self.pdf = tk.BooleanVar(value=settings.get('pdf', True))
        self.status = tk.StringVar()

        root.minsize(620, 480)
        root.geometry('720x600')
        self._build()
        self._apply_language()
        root.after(100, self._poll)

    # --- settings ----------------------------------------------------------
    def _load_settings(self):
        try:
            with open(SETTINGS, encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_settings(self):
        try:
            with open(SETTINGS, 'w', encoding='utf-8') as f:
                json.dump({'lang': self.lang, 'backup': self.backup.get(),
                           'output': self.output.get(),
                           'pdf': bool(self.pdf.get())}, f)
        except Exception:
            pass

    # --- layout ------------------------------------------------------------
    def _build(self):
        pad = {'padx': 12, 'pady': 6}
        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill='both', expand=True)
        frm.columnconfigure(1, weight=1)

        top = ttk.Frame(frm)
        top.grid(row=0, column=0, columnspan=3, sticky='ew', **pad)
        self.lbl_lang = ttk.Label(top)
        self.lbl_lang.pack(side='left')
        self.lang_box = ttk.Combobox(top, state='readonly', width=12,
                                     values=[name for _, name in LANGS])
        self.lang_box.current([c for c, _ in LANGS].index(self.lang))
        self.lang_box.bind('<<ComboboxSelected>>', self._on_lang)
        self.lang_box.pack(side='left', padx=6)

        self.lbl_intro = ttk.Label(frm, wraplength=580, justify='left')
        self.lbl_intro.grid(row=1, column=0, columnspan=3, sticky='w', **pad)

        self.lbl_backup = ttk.Label(frm)
        self.lbl_backup.grid(row=2, column=0, sticky='w', **pad)
        self.btn_backup = ttk.Button(frm, command=self._choose_backup)
        self.btn_backup.grid(row=2, column=1, columnspan=2, sticky='ew', **pad)
        ttk.Entry(frm, textvariable=self.backup).grid(
            row=3, column=0, columnspan=3, sticky='ew', padx=12)

        self.lbl_output = ttk.Label(frm)
        self.lbl_output.grid(row=4, column=0, sticky='w', **pad)
        ttk.Entry(frm, textvariable=self.output).grid(
            row=4, column=1, sticky='ew', pady=6)
        self.btn_output = ttk.Button(frm, command=self._choose_output)
        self.btn_output.grid(row=4, column=2, sticky='e', **pad)

        self.chk_pdf = ttk.Checkbutton(frm, variable=self.pdf)
        self.chk_pdf.grid(row=5, column=0, columnspan=3, sticky='w', **pad)

        big = tkfont.nametofont('TkDefaultFont').copy()
        big.configure(size=14, weight='bold')
        self._big_font = big  # keep a reference
        ttk.Style().configure('Big.TButton', font=big, padding=10)
        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=3, sticky='ew', **pad)
        btns.columnconfigure(0, weight=1)
        self.btn_start = ttk.Button(btns, style='Big.TButton',
                                    command=self._start)
        self.btn_start.grid(row=0, column=0, sticky='ew')
        self.btn_open = ttk.Button(btns, command=self._open_result,
                                   state='disabled')
        self.btn_open.grid(row=0, column=1, sticky='e', padx=(8, 0))

        self.progress = ttk.Progressbar(frm, mode='indeterminate')
        self.progress.grid(row=7, column=0, columnspan=3, sticky='ew', **pad)
        ttk.Label(frm, textvariable=self.status, wraplength=580).grid(
            row=8, column=0, columnspan=3, sticky='w', padx=12)

        logf = ttk.Frame(frm)
        logf.grid(row=9, column=0, columnspan=3, sticky='nsew', **pad)
        frm.rowconfigure(9, weight=1)
        self.log = tk.Text(logf, height=10, wrap='word', state='disabled')
        sb = ttk.Scrollbar(logf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

    def _apply_language(self):
        t = TEXT[self.lang]
        self.root.title(t['title'])
        self.lbl_lang.configure(text=t['language'])
        self.lbl_intro.configure(text=t['intro'])
        self.lbl_backup.configure(text=t['backup'])
        self.btn_backup.configure(text=t['choose_backup'])
        self.lbl_output.configure(text=t['output'])
        self.btn_output.configure(text=t['choose_output'])
        self.chk_pdf.configure(text=t['pdf'])
        self.btn_start.configure(text=t['start'])
        self.btn_open.configure(text=t['open'])

    def _on_lang(self, _event=None):
        self.lang = LANGS[self.lang_box.current()][0]
        self._apply_language()

    # --- actions -----------------------------------------------------------
    def _choose_backup(self):
        t = TEXT[self.lang]
        start = os.path.dirname(self.backup.get()) or os.path.expanduser('~')
        path = filedialog.askopenfilename(
            parent=self.root, title=t['choose_backup'], initialdir=start,
            filetypes=[(t['filetypes'], '*.bkup'), (t['allfiles'], '*.*')])
        if path:
            path = os.path.normpath(path)
            self.backup.set(path)
            self.output.set(default_output(path))

    def _choose_output(self):
        start = self.output.get() or os.path.dirname(self.backup.get())
        path = filedialog.askdirectory(parent=self.root,
                                       initialdir=start or None)
        if path:
            self.output.set(os.path.normpath(path))

    def _write_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _start(self):
        if self.running:
            return
        t = TEXT[self.lang]
        backup = self.backup.get().strip().strip('"')
        if not backup:
            messagebox.showinfo(t['title'], t['no_backup'], parent=self.root)
            return
        if not os.path.isfile(backup):
            messagebox.showerror(t['error_title'],
                                 '{}\n{}'.format(t['not_found'], backup),
                                 parent=self.root)
            return
        output = self.output.get().strip().strip('"') or default_output(backup)
        self.output.set(output)
        self._save_settings()

        self.running = True
        self.result = None
        self.converted = self.unchanged = 0
        self.btn_start.configure(state='disabled')
        self.btn_open.configure(state='disabled')
        self.progress.configure(mode='indeterminate', value=0)
        self.progress.start(12)
        self.status.set(t['working'])
        self._write_log(t['reading'])
        threading.Thread(target=self._work, daemon=True,
                         args=(backup, output, self.lang,
                               bool(self.pdf.get()))).start()

    def _work(self, backup, output, lang, pdf):
        from chicraccoon.sync import sync
        writer = _QueueWriter(self.q)
        try:
            with contextlib.redirect_stdout(writer):
                sync(output, backup, lang)
                pdf_dir = None
                if pdf:
                    from chicraccoon.export_pdf import export_pdfs
                    self.q.put(('msg', 'making_pdf'))
                    pdf_dir = os.path.join(output, 'PDF')
                    # remove PDFs of an earlier run (names contain dates)
                    for old in glob.glob(os.path.join(
                            pdf_dir, PDF_PREFIX + '_*.pdf')):
                        os.remove(old)
                    export_pdfs(output, pdf_dir, PDF_PREFIX)
            self.q.put(('done', (output, pdf_dir)))
        except Exception as e:
            self.q.put(('line', traceback.format_exc()))
            self.q.put(('error', str(e) or type(e).__name__))

    def _poll(self):
        t = TEXT[self.lang]
        try:
            while True:
                kind, value = self.q.get_nowait()
                if kind == 'line':
                    # per-file messages from the converter: show a counter
                    # instead of thousands of lines
                    if value.startswith('file ') and 'not updated' in value:
                        self.unchanged += 1
                    elif value.startswith('file ') and 'converting' in value:
                        self.converted += 1
                    elif value.strip():
                        self._write_log(value)
                    if value.startswith('file '):
                        self.status.set('{} {}'.format(
                            self.converted,
                            t['converted'].format(self.unchanged)))
                elif kind == 'msg':
                    self._write_log('{} {}'.format(
                        self.converted, t['converted'].format(self.unchanged)))
                    self._write_log(t[value])
                elif kind == 'done':
                    self._finish(*value)
                elif kind == 'error':
                    self._finished_ui()
                    self.status.set('{} {}'.format(t['error'], value))
                    messagebox.showerror(t['error_title'],
                                         '{}\n{}'.format(t['error'], value),
                                         parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _finished_ui(self, ok=False):
        self.running = False
        self.progress.stop()
        self.progress.configure(mode='determinate', value=100 if ok else 0)
        self.btn_start.configure(state='normal')

    def _finish(self, output, pdf_dir):
        t = TEXT[self.lang]
        self._finished_ui(ok=True)
        self.result = (output, pdf_dir)
        self.btn_open.configure(state='normal')
        if not pdf_dir:
            self._write_log('{} {}'.format(
                self.converted, t['converted'].format(self.unchanged)))
        self._write_log(t['done'])
        self._write_log(os.path.join(output, 'index.html'))
        if pdf_dir:
            self._write_log('{} {}'.format(t['done_pdf'], pdf_dir))
        self.status.set(t['done'])
        self._open_result()

    def _open_result(self):
        if not self.result:
            return
        output, pdf_dir = self.result
        index = os.path.abspath(os.path.join(output, 'index.html'))
        if os.path.exists(index):
            try:
                from pathlib import Path
                webbrowser.open(Path(index).as_uri())
            except Exception:
                open_path(index)
        if pdf_dir and os.path.isdir(pdf_dir):
            open_path(pdf_dir)


def main():
    if sys.platform == 'win32':
        try:  # sharp text on high-DPI screens
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
