"""Export every notebook, ToDo list and calendar of a chicraccoon output
folder (made by chicraccoon_sync) to PDF files:

    <prefix>_Note_<nr>_<title>_<last change>.pdf
    <prefix>_Todo_<nr>_<title>_<last change>.pdf
    <prefix>_Calendar_<nr>_<title>_<start>_<end>.pdf   (only pages with ink)

The numbers match the web view ("Notebook 7" -> eNote_Note_07_...).
<title> is optional and comes from a titles.json in the output folder:
    {"notebooks": {"<id>": "Shopping"}, "todos": {...}, "schedules": {...}}

Usage:
    python -m chicraccoon.export_pdf <html-folder> <pdf-folder> [--prefix eNote]
"""
import datetime
import json
import os
import sys

# explicit plugin imports: PIL's lazy plugin discovery fails under python -I
from PIL import Image, JpegImagePlugin, PdfImagePlugin  # noqa: F401

W, H, SCALE = 600, 700, 2  # device page size; PDF pages rendered at 2x

# gray value per layer: form lines light gray, layer 0 = marker (mid gray),
# layer 1 = pen (black); ToDo pages: layer 2 = "done" shading (very light)
FORM_GRAY, MARKER_GRAY, PEN_GRAY, TODO_DONE_GRAY = 175, 130, 0, 225


def _safe(text):
    text = ''.join(c if c.isalnum() or c == '-' else '_' for c in text)
    while '__' in text:
        text = text.replace('__', '_')
    return text.strip('_')


def _day(ts):
    if not ts:
        return 'unknown'
    return datetime.datetime.fromtimestamp(
        ts, datetime.timezone.utc).strftime('%Y-%m-%d')


def export_pdfs(html, out, prefix='eNote', log=print):
    """Write the PDFs for the chicraccoon folder <html> into <out>.
    Returns the list of written file paths."""
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(html, 'data.json'), encoding='utf-8') as f:
        d = json.load(f)
    P = lambda rel: os.path.join(html, rel)
    titles = {}
    if os.path.exists(P('titles.json')):
        with open(P('titles.json'), encoding='utf-8') as f:
            titles = json.load(f)

    def title(kind, k):
        t = _safe(titles.get(kind, {}).get(str(k), ''))
        return (t + '_') if t else ''

    def has_ink(ink):
        for rel in ink:
            with Image.open(P(rel)) as im:
                if im.getchannel('A').getbbox():
                    return True
        return False

    def form_path(fid):
        nb = d['forms'].get(str(fid), {}).get('notebook', 0)
        if nb == -1:
            return 'images/uform/f%07x_0.png' % fid
        if nb == 0:
            return 'images/form/f%07x_0.png' % fid
        return 'images/impt/n%06x/f%07x_0.png' % (nb, fid)

    def layers(fmt):
        found, i = [], 0
        while os.path.exists(P(fmt % i)):
            found.append(fmt % i)
            i += 1
        return found

    def compose(form, ink, todo=False):
        page = Image.new('L', (W, H), 255)
        stack = [(form, FORM_GRAY)] if form and os.path.exists(P(form)) else []
        for i, rel in enumerate(ink):
            if todo:
                gray = TODO_DONE_GRAY if i == 2 else PEN_GRAY
            else:
                gray = MARKER_GRAY if i == 0 else PEN_GRAY
            stack.append((rel, gray))
        for rel, gray in stack:
            with Image.open(P(rel)) as im:
                alpha = im.getchannel('A')
            if alpha.size != (W, H):
                alpha = alpha.resize((W, H))
            page.paste(Image.new('L', (W, H), gray), (0, 0), alpha)
        return page.resize((W * SCALE, H * SCALE), Image.LANCZOS)

    written = []

    def save(pages, name):
        if not pages:
            return
        path = os.path.join(out, name)
        pages[0].save(path, save_all=True, append_images=pages[1:],
                      resolution=100 * SCALE, quality=92)
        written.append(path)
        log('%-60s %3d pages' % (name, len(pages)))

    for n, nid in enumerate(sorted(d['notebooks'], key=int), 1):
        nb, k = d['notebooks'][nid], int(nid)
        pages = [compose(form_path(d['pages'][str(p)]['form']),
                         layers('images/page/n%06x/p%07x_%%d.png' % (k, p)))
                 for p in nb['pages'] if str(p) in d['pages']]
        save(pages, '%s_Note_%02d_%s%s.pdf' % (
            prefix, n, title('notebooks', k), _day(nb.get('modified'))))

    for n, tid in enumerate(sorted(d.get('todos', {}), key=int), 1):
        td, k = d['todos'][tid], int(tid)
        pages = [compose('images/todo_form/f%07x_0.png'
                         % d['todo_pages'][str(p)]['form'],
                         layers('images/todo_page/n%06x/p%07x_%%d.png' % (k, p)),
                         todo=True)
                 for p in td['pages'] if str(p) in d['todo_pages']]
        save(pages, '%s_Todo_%02d_%s%s.pdf' % (
            prefix, n, title('todos', k), _day(td.get('modified'))))

    for n, sid in enumerate(sorted(d['schedules'], key=int), 1):
        sc, k = d['schedules'][sid], int(sid)
        # calendars: only pages with handwriting on them
        ink = [(p, layers('images/sch_page/s%06x/p%07x_%%d.png' % (k, p)))
               for p in sc['pages'] if str(p) in d['sch_pages']]
        pages = [compose('images/sch_form/s%06x/f%07x_0.png' % (k, p), l)
                 for p, l in ink if has_ink(l)]
        save(pages, '%s_Calendar_%02d_%s%s_%s.pdf' % (
            prefix, n, title('schedules', k), _day(sc['start_date']),
            _day(sc['end_date'])))

    return written


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    prefix = 'eNote'
    if '--prefix' in args:
        i = args.index('--prefix')
        prefix = args[i + 1] if i + 1 < len(args) else ''
        del args[i:i + 2]
    if len(args) != 2 or not prefix:
        print('USAGE:')
        print('python -m chicraccoon.export_pdf <html-folder> <pdf-folder> '
              '[--prefix eNote]')
        return 1
    export_pdfs(args[0], args[1], _safe(prefix) or 'eNote')
    return 0


if __name__ == '__main__':
    sys.exit(main())
