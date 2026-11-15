# Chicraccoon – view your Sharp eNote notes on the computer

Turns a backup of a **Sharp electronic notebook (電子ノート / eNote)** into a website you can open in any browser, plus PDF files of every notebook, ToDo list and calendar. Tested with backups from the **WG-PN1** and **WG-S20**; the original project was made for the WG-S30.

Everything runs on your own computer; nothing is uploaded anywhere.

[English](#for-non-technical-users) · [日本語](#パソコンに詳しくない方へ) · [Deutsch](#für-nicht-techniker)

## For non-technical users

1. **Make a backup on the eNote:** in the device's settings choose *Backup*. Then connect the eNote to the computer with the USB cable; it shows up like a USB stick. Copy the file **`enote.bkup`** from its `BACKUP` folder to your computer (for example into *Documents*).
2. **Install Python (once):** go to <https://www.python.org/downloads/>, download Python and run the installer. **Important:** on the first screen tick **“Add python.exe to PATH”**, then click *Install Now*.
3. **Download this program:** on this GitHub page click the green **Code** button → **Download ZIP**, and unzip it (right-click → *Extract All*).
4. **Start it:** in the unzipped folder double-click **`START_Windows.bat`**. The first start installs two small libraries, which needs an internet connection. (Mac: double-click `START_macOS_Linux.command`; the first time right-click → *Open*.)
5. **Choose your backup:** click *Choose backup file (enote.bkup)*, keep *Also create PDF files* ticked and press **Start**. The first run takes a few minutes.
6. **Done:** your notes open in the browser and the PDF folder opens too. Everything is saved in a folder next to the backup (`enote_html`). Next time just make a new backup and press Start again – only changed pages are converted.

## パソコンに詳しくない方へ

1. **電子ノートでバックアップを作成：** 本体の設定で「バックアップ」を実行します。USBケーブルでパソコンにつなぐとUSBメモリのように表示されるので、`BACKUP` フォルダの **`enote.bkup`** をパソコン（例：「ドキュメント」）にコピーします。
2. **Python をインストール（初回のみ）：** <https://www.python.org/downloads/> から Python をダウンロードしてインストーラーを実行します。**重要：** 最初の画面で **「Add python.exe to PATH」にチェック** を入れてから「Install Now」をクリックしてください。
3. **このプログラムをダウンロード：** このGitHubページの緑色の **「Code」** ボタン → **「Download ZIP」** をクリックし、ZIPを展開します（右クリック →「すべて展開」）。
4. **起動：** 展開したフォルダの **`START_Windows.bat`** をダブルクリックします。初回は小さなライブラリを2つインストールするため、インターネット接続が必要です。（Mac の場合は `START_macOS_Linux.command` をダブルクリック。初回は右クリック →「開く」。）
5. **バックアップを選ぶ：** 「バックアップファイル（enote.bkup）を選ぶ」をクリックし、「PDFファイルも作成する」にチェックを入れたまま **「スタート」** を押します。初回は数分かかります。
6. **完了：** ノートがブラウザで開き、PDFのフォルダも開きます。結果はバックアップと同じ場所のフォルダ（`enote_html`）に保存されます。次回は新しいバックアップを作ってもう一度「スタート」を押すだけです。変更されたページだけが変換されます。

## Für Nicht-Techniker

1. **Backup auf dem eNote erstellen:** in den Einstellungen des Geräts *Backup* ausführen. Dann das eNote per USB-Kabel an den Computer anschließen – es erscheint wie ein USB-Stick. Die Datei **`enote.bkup`** aus dem Ordner `BACKUP` auf den Computer kopieren (z. B. nach *Dokumente*).
2. **Python installieren (einmalig):** auf <https://www.python.org/downloads/> Python herunterladen und das Installationsprogramm starten. **Wichtig:** im ersten Fenster das Häkchen bei **„Add python.exe to PATH“** setzen, dann *Install Now* klicken.
3. **Dieses Programm herunterladen:** auf dieser GitHub-Seite den grünen Knopf **Code** → **Download ZIP** klicken und die ZIP-Datei entpacken (Rechtsklick → *Alle extrahieren*).
4. **Starten:** im entpackten Ordner **`START_Windows.bat`** doppelklicken. Beim ersten Start werden zwei kleine Bibliotheken installiert, dafür braucht es Internet. (Mac: `START_macOS_Linux.command` doppelklicken, beim ersten Mal Rechtsklick → *Öffnen*.)
5. **Backup wählen:** *Backup-Datei wählen (enote.bkup)* klicken, *Auch PDF-Dateien erstellen* angehakt lassen und **Start** drücken. Beim ersten Mal dauert es einige Minuten.
6. **Fertig:** die Notizen öffnen sich im Browser, der PDF-Ordner ebenfalls. Alles liegt in einem Ordner neben dem Backup (`enote_html`). Beim nächsten Mal einfach ein neues Backup machen und wieder Start drücken – nur geänderte Seiten werden neu umgewandelt.

---

# Technical documentation

## Sharp electronic notebooks

Sharp electronic notebooks ("enote") are extremely inexpensive pocket-sized devices designed for note-taking. More information about them is available on [Sharp's website (Japanese)](http://www.sharp.co.jp/enote/) or on [this unofficial English website](https://enote.neocities.org/).

Although Sharp provides a Windows-only utility that can be used to interface with the notebook, it can only either export notes as BMPs (a cumbersome process that can only be applied to one notebook at a time, and loses metadata/layer separation in the process) or create opaque backups of the entire device in Sharp's proprietary that cannot be viewed with the utility.

The `docs/` folder in this repository contains some information about this backup format, obtained by reverse-engineering.

## Chicraccoon

Chicraccoon is a set of utilities for working with the backup files generated by the electronic notebooks. Note that the Windows utility is not required to actually generate the backups --- generation is initiated on the notebook, and backups can then be copied from the `BACKUP` folder on the notebook when it is connected to a computer.

Chicraccoon has been developed with the WG-S30 model in mind and only tested with backup files generated by this model. Some components will likely fail on backups generated by older models, because they'll be looking for things that aren't there. If you have an older model and would like Chicraccoon to support it, let me know and we'll figure something out.

### Command-line scripts

- `chicraccoon_cli` is a utility for analysis of `.bkup` files. It can list the contents of a `.bkup` file, extract files from them, and, when extracting images, can also optionally convert them to standard image formats like PNG or BMP.

- `chicraccoon_sync` is a utility that can maintain a local copy of your electronic notebook's state. You give it a backup, and it copies & converts all the files to a folder on your computer and creates a bunch of HTML files that let you navigate your notes from a computer ([screenshots](sync_screenshots)). After an initial synchronization, all further synchronizations will only update files that were changed in the new backup.

### This fork: WG-PN1 support, a new web view, PDF export and a simple window

This fork adds support for the **Sharp WG-PN1** (firmware 1.50: ToDo lists and handwritten page tags) and a redesigned web view:

```
chicraccoon_sync [--lang en|de|ja] <output-folder> <path/to/enote.bkup>
```

- Open `<output-folder>/index.html` in any browser (works straight from disk). Notebooks, ToDo lists and calendars are shown as cards; pages open in a viewer with ←/→ keys, swipe, and a "show lines" toggle. Light/dark theme follows the system and can be toggled.
- `--lang de` / `--lang ja` switch the pages to German / Japanese.
- **PDF export:** `python -m chicraccoon.export_pdf <output-folder> <pdf-folder> [--prefix eNote]` (or `chicraccoon_pdf` after `pip install .`) writes `eNote_Note_07_<date>.pdf`, `eNote_Todo_..`, `eNote_Calendar_..` (calendars: only pages with writing; numbers match the web view). Form lines are light gray, marker strokes mid gray, pen strokes black. Optional `titles.json` in the output folder (`{"notebooks": {"<id>": "Shopping"}, "todos": {}, "schedules": {}}`) adds a title to the file names.
- **Window for non-technical users:** `python -m chicraccoon.gui` (what `START_Windows.bat` / `START_macOS_Linux.command` run; tkinter, standard library only). It remembers the last backup and folder in `~/.chicraccoon_gui.json`.
- Optional `summaries.json` in the output folder (`{"notebooks": {"<id>": "text"}, ...}`) shows a short note under each book.
- **Owners** (for shared devices): put an `owners.json` like `{"people": ["Anna", "Ben"], "owners": {}}` into the output folder, or type the names under "People & saving" on the home page. Assign each book with its drop-down, or tick several cards (Shift+click ticks a range) and assign them at once, then filter by person. Assignments are remembered in the browser; "Download owners.json" and saving it into the output folder makes them permanent.

### Programming interfaces

- `EnoteBackup` is a class that operates on `.bkup` files. It can open one, list the files contained in it and extract them. There's a function that attempts to replace a file, but it currently doesn't work as the resulting backups fail some validity check on the notebook.

- `EnoteImage` is a class that operates on images stored in `.RAW` files inside the backups. It can extract all the layers from an image and convert them to PIL Images, which can later be saved in any format supported by PIL or processed.

### Requirements & installation

Chicraccoon requires Python 3.7+ and two Python libraries: Pillow (for image processing) and Jinja2 (for HTML generation): `python -m pip install -r requirements.txt`.

Running `pip install .` in the root of this repository should install all of the requirements as well. This package is not currently available on pip.

### License & authorship

Chicraccoon is licensed under the terms of the [MIT License](LICENSE.txt).

Chicraccoon was developed by Aleksejs Popovs (aleksejs@popovs.lv). I am not affiliated with Sharp, and this project is not supported or approved by Sharp in any manner.

The WG-PN1 support, the new web view, the PDF export and the launcher in this fork were added by genkigenki, under the same MIT license. This fork is not affiliated with Sharp either.
