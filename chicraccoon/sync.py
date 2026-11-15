import calendar
import datetime
import json
import os
import os.path
import re
import shutil
import sqlite3
import struct
import sys

from jinja2 import Environment, PackageLoader, select_autoescape
from PIL import Image

from chicraccoon.enotebackup import EnoteBackup

# UI strings for the generated web pages (select with --lang)
STRINGS = {
    'en': {
        'lang': 'en', 'app': 'My eNote', 'back': 'Back', 'filled_pages': 'Filled pages', 'notebooks': 'Notebooks',
        'notebook': 'Notebook', 'todos': 'ToDo lists', 'todo': 'ToDo list',
        'schedules': 'Calendars', 'schedule': 'Calendar', 'pages': 'pages',
        'page': 'Page', 'home': 'Home', 'prev': 'Previous page',
        'next': 'Next page', 'theme': 'Switch light/dark',
        'show_form': 'Show lines', 'keys': 'Use ← → or swipe',
        'latest': 'Last change', 'today': 'Today', 'done': 'done',
        'weekdays': ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
        'months': ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November',
                   'December'],
        'date_fmt': '%Y-%m-%d', 'empty': 'Nothing here yet.',
        'owner': 'Belongs to', 'all': 'All', 'unassigned': 'Unassigned',
        'people': 'People & saving', 'people_hint': 'Names, comma separated:',
        'save_owners': 'Download owners.json',
        'select': 'Select', 'selected': 'selected', 'assign_to': 'Assign to',
        'assign': 'Assign', 'select_visible': 'Select all shown',
        'clear_selection': 'Clear selection',
        'select_hint': 'Tick the corner; Shift+click ticks a whole range.',
        'save_hint': 'Assignments are kept in this browser. To keep them '
                     'for good, save owners.json into this folder; it is '
                     'picked up the next time the pages are generated.',
    },
    'de': {
        'lang': 'de', 'app': 'Mein eNote', 'back': 'Zurück',
        'filled_pages': 'Ausgefüllte Seiten', 'notebooks': 'Hefte',
        'notebook': 'Heft', 'todos': 'ToDo-Listen', 'todo': 'ToDo-Liste',
        'schedules': 'Kalender', 'schedule': 'Kalender', 'pages': 'Seiten',
        'page': 'Seite', 'home': 'Start', 'prev': 'Vorherige Seite',
        'next': 'Nächste Seite', 'theme': 'Hell/Dunkel umschalten',
        'show_form': 'Linien zeigen',
        'keys': 'Mit ← → oder Wischen blättern',
        'latest': 'Zuletzt geändert', 'today': 'Heute', 'done': 'erledigt',
        'weekdays': ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'],
        'months': ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                   'Juli', 'August', 'September', 'Oktober', 'November',
                   'Dezember'],
        'date_fmt': '%d.%m.%Y', 'empty': 'Noch nichts da.',
        'owner': 'Gehört', 'all': 'Alle', 'unassigned': 'Ohne Zuordnung',
        'people': 'Personen & Speichern',
        'people_hint': 'Namen, mit Komma getrennt:',
        'save_owners': 'owners.json herunterladen',
        'select': 'Auswählen', 'selected': 'ausgewählt',
        'assign_to': 'Zuordnen zu', 'assign': 'Zuordnen',
        'select_visible': 'Alle sichtbaren auswählen',
        'clear_selection': 'Auswahl aufheben',
        'select_hint': 'Häkchen oben links; mit Shift+Klick eine ganze '
                       'Reihe von–bis.',
        'save_hint': 'Die Zuordnung wird in diesem Browser gemerkt. Damit '
                     'sie dauerhaft bleibt, owners.json in diesen Ordner '
                     'speichern – sie wird beim nächsten Erzeugen '
                     'übernommen.',
    },
}

def grayscale_to_mask(image):
    pixels = image.tobytes()
    new_pixels = []
    for pixel in pixels:
        new_pixels.append(0)
        new_pixels.append(0)
        new_pixels.append(0)
        new_pixels.append(255 - pixel)
    return Image.frombuffer('RGBA', image.size, bytes(new_pixels),
        'raw', 'RGBA', 0, 1)

class LocalNotebook:
    def __init__(self, path):
        self.path = path
        self.d = {
            'forms': {},
            'pages': {},
            'notebooks': {},
            'images': {},
            'schedules': {},
            'sch_pages': {},
            'todos': {},
            'todo_pages': {}
        }

        if not os.path.exists(path):
            os.mkdir(path)

        if os.path.exists(self._path('data.json')):
            with open(self._path('data.json'), encoding='utf-8') as f:
                # JSON doesn't allow integral keys, so they're actually
                # stored as strings. the hook converts them back.
                int_maybe = lambda x: int(x) if x.isnumeric() else x
                pairs_hook = lambda pairs: {int_maybe(k):v for k,v in pairs}
                self.d.update(json.load(f, object_pairs_hook=pairs_hook))

    def save(self):
        with open(self._path('data.json'), 'w', encoding='utf-8') as f:
            json.dump(self.d, f)

    def _path(self, *parts):
        return os.path.join(self.path, *parts)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.save()

    def load_page_order(self, id_, backup, folder='PAGE'):
        filename = '{folder}/N{id:06X}/PAGE_ORDER.bin'.format(
            folder=folder, id=id_)
        f = backup.find_file(filename)
        if f is None:
            return None
        data = backup.extract_file(f)
        return [x for (x, ) in struct.iter_unpack('<L', data)]

    def update_metadata(self, kind, db, backup):
        table_name = {
            'forms': 'forms',
            'pages': 'pages',
            'notebooks': 'notes',
            'schedules': 'schedules',
            'sch_pages': 'schedule_pages',
            'todos': 'todos',
            'todo_pages': 'todo_pages'
            }[kind]

        self.d[kind] = {}

        # ToDo books only exist on newer models (e.g. WG-PN1 firmware 1.50)
        has_table = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name, )).fetchone()
        if not has_table:
            return

        # SQL prepared statements don't support placeholders in the
        # FROM clause
        cursor = db.execute('SELECT * FROM {}'.format(table_name))
        objects = cursor.fetchmany()

        while objects:
            for obj in objects:
                id_ = obj['id']

                if kind == 'forms':
                    self.d[kind][id_] = {
                        'notebook': obj['owner_id']
                    }
                elif kind == 'pages':
                    self.d[kind][id_] = {
                        'form': obj['form_id']
                    }
                elif kind == 'notebooks':
                    self.d[kind][id_] = {
                        'pages': self.load_page_order(id_, backup) or [],
                        'modified': obj['modify_date']
                    }
                elif kind == 'todos':
                    cursor_pages = db.execute(
                        '''SELECT id
                           FROM todo_pages
                           WHERE todo_id=?
                           ORDER BY id ASC''',
                        (id_, ))
                    pages = [x['id'] for x in cursor_pages.fetchall()]
                    order = self.load_page_order(id_, backup, 'TODO_PAGE')
                    if order:
                        # keep the on-device order, drop stale entries
                        ordered = [p for p in order if p in pages]
                        pages = ordered + [p for p in pages
                                           if p not in ordered]
                    self.d[kind][id_] = {
                        'pages': pages,
                        'modified': obj['modify_date']
                    }
                elif kind == 'todo_pages':
                    self.d[kind][id_] = {
                        'form': obj['form_id'],
                        # bitmasks over the (up to 9) rows of a ToDo page
                        'checked': obj['checked'],
                        'starred': obj['priority']
                    }
                elif kind == 'schedules':
                    cursor_pages = db.execute(
                        '''SELECT id
                           FROM schedule_pages
                           WHERE schedule_id=?
                           ORDER BY id ASC''',
                        (id_, ))
                    pages = [x['id'] for x in cursor_pages.fetchall()]

                    self.d[kind][id_] = {
                        'start_date': obj['start_date'],
                        'end_date': obj['end_date'],
                        'pages': pages,
                        'modified': obj['modify_date']
                    }
                elif kind == 'sch_pages':
                    self.d[kind][id_] = {
                        'start_date': obj['start_date'],
                        'end_date': obj['end_date'],
                        'touched': bool(obj['modify'])
                    }

            objects = cursor.fetchmany()

        # uforms (imported forms) have owner_id = 0, just like built-in forms
        # which is kinda inconvenient, so we fix that
        if kind == 'forms':
            cursor = db.execute('SELECT * FROM uforms')
            uforms = cursor.fetchmany()
            while uforms:
                for uform in uforms:
                    self.d[kind][uform['form_id']]['notebook'] = -1
                uforms = cursor.fetchmany()

    def _image_path(self, basename, layer):
        basename = basename[:-4] # removing '.raw'
        return self._path('images', '{}_{}.png'.format(basename, layer))

    def _mkdir(self, *path):
        os.makedirs(self._path(*path), exist_ok=True)

    def convert_image(self, basename, image):
        for i, layer in enumerate(image.list_layers()):
            image = grayscale_to_mask(layer.to_pil())
            # backups don't always list a directory before its files
            os.makedirs(os.path.dirname(self._image_path(basename, i)),
                        exist_ok=True)
            image.save(self._image_path(basename, i))

    def update_images(self, backup):
        self._mkdir('images')

        seen_images = set()
        for f in backup.list_files():
            filename = f.filename.decode('utf-8').lower()

            if f.is_dir:
                self._mkdir('images', filename)

            if not filename.endswith('.raw'):
                continue

            # flatten directories that are unnecessarily subdivided
            filename = re.sub(r'/[\da-f]{2}/', '/', filename)

            seen_images.add(filename)
            if filename not in self.d['images']:
                self.d['images'][filename] = {
                    'mtime': 0,
                    'layers': 0
                }

            if f.mtime > self.d['images'][filename]['mtime']:
                print('file {} updated, converting'.format(filename))
                try:
                    image = backup.extract_image(f)
                except ValueError as e:
                    # unknown image type (e.g. from a newer model): skip it
                    # instead of aborting the whole sync
                    print('file {} skipped: {}'.format(filename, e))
                    continue
                self.d['images'][filename]['mtime'] = f.mtime
                self.d['images'][filename]['layers'] = image.layer_count()
                self.convert_image(filename, image)
            else:
                print('file {} not updated, skipping'.format(filename))

        files_to_delete = []
        for filename in self.d['images']:
            if filename not in seen_images:
                print('file {} deleted, deleting'.format(filename))
                for i in range(self.d['images'][filename]['layers']):
                    os.remove(self._image_path(filename, i))
                files_to_delete.append(filename)
        for filename in files_to_delete:
            del self.d['images'][filename]

    def regenerate_web(self, lang='en'):
        t = STRINGS.get(lang, STRINGS['en'])
        to_date = lambda x: datetime.datetime.fromtimestamp(
            x, datetime.timezone.utc).date()
        fmt_date = lambda x: to_date(x).strftime(t['date_fmt']) if x else ''

        notebook_dirname = lambda x: 'n{:03}'.format(x)
        page_filename = lambda p, n: 'n{:03}/p{:06}.html'.format(n, p)
        notebook_covername = lambda x: 'images/note/n{:07x}_0.png'.format(x)
        schedule_dirname = lambda x: 's{:03}'.format(x)
        sch_page_filename = lambda p, n: 's{:03}/p{:06}.html'.format(n, p)
        schedule_covername = lambda x: 'images/schedule/s{:07x}_0.png'.format(x)
        todo_dirname = lambda x: 't{:03}'.format(x)
        todo_page_filename = lambda p, n: 't{:03}/p{:06}.html'.format(n, p)
        todo_covername = lambda x: 'images/todo/n{:07x}_0.png'.format(x)
        def form_filename(id_, thumb=False):
            notebook = self.d['forms'].get(id_, {}).get('notebook', 0)
            if notebook == -1:
                # uform
                return 'images/{thumb}uform/f{id:07x}_0.png'.format(
                    thumb='thumbnail/' if thumb else '', id=id_)
            elif notebook == 0:
                # built-in form
                return 'images/{thumb}form/f{id:07x}_0.png'.format(
                    thumb='thumbnail/' if thumb else '', id=id_)
            else:
                # imported form
                return 'images/{thumb}impt/n{nb:06x}/f{id:07x}_0.png'.format(
                    thumb='thumbnail/' if thumb else '', id=id_, nb=notebook)
        def page_imagename(id_, notebook, layer, thumb=False):
            return 'images/{thumb}page/n{nb:06x}/{tp}{id:07x}_{layer}.png'.format(
                thumb='thumbnail/' if thumb else '',
                tp='t' if thumb else 'p',
                id=id_, nb=notebook, layer=layer)
        def todo_form_filename(id_, thumb=False):
            return 'images/{thumb}todo_form/f{id:07x}_0.png'.format(
                thumb='todo_thumbnail/' if thumb else '', id=id_)
        def todo_page_imagename(id_, todo, layer, thumb=False):
            return 'images/{thumb}todo_page/n{nb:06x}/{tp}{id:07x}_{layer}.png'.format(
                thumb='todo_thumbnail/' if thumb else '',
                tp='t' if thumb else 'p',
                id=id_, nb=todo, layer=layer)
        def sch_form_filename(id_, schedule):
            return 'images/sch_form/s{sch:06x}/f{id:07x}_0.png'.format(
                sch=schedule, id=id_)
        def sch_page_imagename(id_, schedule, layer, thumb=False):
            return 'images/{thumb}sch_page/s{sch:06x}/{tp}{id:07x}_{layer}.png'.format(
                thumb='thumbnail/' if thumb else '',
                tp='t' if thumb else 'p',
                id=id_, sch=schedule, layer=layer)
        def existing_layers(name_for_layer):
            # pages have a varying number of layers (ToDo pages have three)
            layers = []
            while os.path.exists(self._path(name_for_layer(len(layers)))):
                layers.append(name_for_layer(len(layers)))
            return layers
        def layer_list(paths):
            # first layer is the form (template), the rest are ink layers
            return [{'src': p, 'cls': 'form' if i == 0 else 'l{}'.format(i)}
                    for i, p in enumerate(paths)
                    if i > 0 or os.path.exists(self._path(p))]
        def existing_or(path, fallback):
            return path if os.path.exists(self._path(path)) else fallback
        def cover_image(path, key):
            # notebook and calendar covers are stored as light ink on a dark
            # background (ToDo covers are not); normalize them to dark ink on
            # a transparent background like the pages. None = no cover.
            if not os.path.exists(self._path(path)):
                return None
            out = 'images/covers/{}.png'.format(key)
            src = Image.open(self._path(path)).convert('RGBA')
            alpha = src.getchannel('A').histogram()
            if sum(alpha[128:]) > sum(alpha[:128]):
                flat = Image.new('RGBA', src.size, (255, 255, 255, 255))
                flat.alpha_composite(src)
                src = Image.new('RGBA', src.size, (0, 0, 0, 255))
                src.putalpha(flat.convert('L'))
            self._mkdir('images', 'covers')
            src.save(self._path(out))
            return out

        # copy over static files
        self._mkdir('static')
        static_dir = os.path.join(os.path.dirname(__file__), 'web_static')
        for entry in os.scandir(static_dir):
            shutil.copy(entry.path, self._path('static'))

        env = Environment(
            loader=PackageLoader('chicraccoon', 'web_templates'),
            autoescape=select_autoescape(['html']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        env.globals['t'] = t
        valid = lambda pages, data: [p for p in pages if p in data]
        env.globals['stats'] = [
            {'id': 'notebooks', 'label': t['notebooks'],
             'count': len(self.d['notebooks'])},
            {'id': 'todos', 'label': t['todos'], 'count': len(self.d['todos'])},
            {'id': 'schedules', 'label': t['schedules'],
             'count': sum(1 for x in self.d['schedules'].values()
                          if valid(x['pages'], self.d['sch_pages']))},
            {'id': None, 'label': t['pages'],
             'count': sum(len(valid(x['pages'], self.d['pages']))
                          for x in self.d['notebooks'].values()) +
                      sum(len(valid(x['pages'], self.d['todo_pages']))
                          for x in self.d['todos'].values())},
        ]
        page_template = env.get_template('page.html')
        book_template = env.get_template('book.html')

        def write(path, template, **kwargs):
            with open(self._path(path), 'w', encoding='utf-8') as f:
                f.write(template.render(**kwargs))

        def render_book(kind, id_, title, page_ids, page_data, dirname,
                        page_fn, form_fn, image_fn, cover, modified):
            self._mkdir(dirname(id_))
            # skip page ids that have no metadata (stale PAGE_ORDER entries)
            page_ids = [p for p in page_ids if p in page_data]
            crumbs = [{'label': t[kind + 's'],
                       'link': '../index.html#' + kind + 's'},
                      {'label': title, 'link': 'index.html'}]

            pages = []
            for i, page_id in enumerate(page_ids):
                page = page_data[page_id]
                layers = layer_list([form_fn(page['form'])] + existing_layers(
                    lambda l: image_fn(page_id, id_, l)))
                thumbs = layer_list([form_fn(page['form'], True)] +
                    existing_layers(lambda l: image_fn(page_id, id_, l, True)))
                badge = None
                if kind == 'todo':
                    done = bin((page.get('checked') or 0) & 0x1ff).count('1')
                    if done:
                        badge = '✓ {}'.format(done)

                label = '{} {} / {}'.format(t['page'], i + 1, len(page_ids))
                write(page_fn(page_id, id_), page_template,
                      base_dir='../', kind=kind, title=title,
                      crumbs=crumbs + [{'label': label}], up_link='index.html',
                      layers=layers, label=label,
                      progress=100.0 * (i + 1) / len(page_ids),
                      prev_link=page_fn(page_ids[i - 1], id_)
                          if i > 0 else None,
                      next_link=page_fn(page_ids[i + 1], id_)
                          if i < len(page_ids) - 1 else None)
                pages.append({'layers': thumbs, 'link': page_fn(page_id, id_),
                              'num': i + 1, 'badge': badge})

            write(os.path.join(dirname(id_), 'index.html'), book_template,
                  base_dir='../', kind=kind, title=title,
                  crumbs=crumbs[:1] + [{'label': title}],
                  up_link='../index.html#' + kind + 's',
                  cover=cover, pages=pages, date=fmt_date(modified))
            return {'link': '{}/index.html'.format(dirname(id_)),
                    'key': dirname(id_), 'cover': cover, 'title': title,
                    'subtitle': '{} {}'.format(len(pages), t['pages']),
                    'date': fmt_date(modified), 'sort': modified or 0,
                    'count': len(pages)}

        # notebooks and ToDo books
        notebooks = []
        for n, id_ in enumerate(sorted(self.d['notebooks']), 1):
            nb = self.d['notebooks'][id_]
            notebooks.append(render_book(
                'notebook', id_, '{} {}'.format(t['notebook'], n),
                nb['pages'], self.d['pages'], notebook_dirname,
                page_filename, form_filename, page_imagename,
                cover_image(notebook_covername(id_), notebook_dirname(id_)),
                nb.get('modified')))
        todos = []
        for n, id_ in enumerate(sorted(self.d['todos']), 1):
            td = self.d['todos'][id_]
            todos.append(render_book(
                'todo', id_, '{} {}'.format(t['todo'], n),
                td['pages'], self.d['todo_pages'], todo_dirname,
                todo_page_filename, todo_form_filename, todo_page_imagename,
                cover_image(todo_covername(id_), todo_dirname(id_)),
                td.get('modified')))

        # schedules: one calendar per schedule, one page per spread
        schedule_template = env.get_template('schedule.html')
        cal = calendar.Calendar(firstweekday=0)
        schedules = []
        for n, id_ in enumerate(sorted(self.d['schedules']), 1):
            schedule = self.d['schedules'][id_]
            page_objects = [(x, self.d['sch_pages'][x])
                            for x in schedule['pages']
                            if x in self.d['sch_pages']]
            if not page_objects:
                continue
            self._mkdir(schedule_dirname(id_))
            title = '{} {}'.format(t['schedule'], n)
            crumbs = [{'label': t['schedules'],
                       'link': '../index.html#schedules'},
                      {'label': title, 'link': 'index.html'}]
            start_date = to_date(schedule['start_date'])
            end_date = to_date(schedule['end_date'])

            def page_for(day):
                for page_id, page in page_objects:
                    if (to_date(page['start_date']) <= day
                            <= to_date(page['end_date'])):
                        return page_id, page
                return None, None

            months = []
            y, m = start_date.year, start_date.month
            while (y, m) <= (end_date.year, end_date.month):
                weeks = []
                for week in cal.monthdatescalendar(y, m):
                    row = []
                    for day in week:
                        if day.month != m or not (start_date <= day <= end_date):
                            row.append(None)
                            continue
                        page_id, page = page_for(day)
                        row.append({
                            'day': day.day,
                            'date': day.isoformat(),
                            'link': sch_page_filename(page_id, id_)
                                if page_id else None,
                            'touched': bool(page and page['touched'])
                        })
                    weeks.append(row)
                months.append({'name': '{} {}'.format(t['months'][m - 1], y),
                               'weeks': weeks})
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)

            date_range = '{} – {}'.format(
                fmt_date(schedule['start_date']),
                fmt_date(schedule['end_date']))
            filled = []
            for i, (page_id, page) in enumerate(page_objects):
                ink = existing_layers(
                    lambda l: sch_page_imagename(page_id, id_, l))
                layers = layer_list([sch_form_filename(page_id, id_)] + ink)
                label = '{} – {}'.format(fmt_date(page['start_date']),
                                              fmt_date(page['end_date']))
                if ink:
                    # calendar pages have no thumbnails: reuse full images
                    filled.append({'layers': layers, 'label': label,
                                   'link': sch_page_filename(page_id, id_),
                                   'sort': page['start_date']})
                write(sch_page_filename(page_id, id_), page_template,
                      base_dir='../', kind='schedule', title=title,
                      crumbs=crumbs + [{'label': label}], up_link='index.html',
                      layers=layers, label=label,
                      progress=100.0 * (i + 1) / len(page_objects),
                      prev_link=sch_page_filename(page_objects[i - 1][0], id_)
                          if i > 0 else None,
                      next_link=sch_page_filename(page_objects[i + 1][0], id_)
                          if i < len(page_objects) - 1 else None)

            filled.sort(key=lambda x: x['sort'])
            write(os.path.join(schedule_dirname(id_), 'index.html'),
                  schedule_template, base_dir='../', kind='schedule',
                  title=title, crumbs=crumbs[:1] + [{'label': title}],
                  up_link='../index.html#schedules', months=months,
                  range=date_range, filled=filled)

            touched = sum(1 for _, p in page_objects if p['touched'])
            schedules.append({
                'link': '{}/index.html'.format(schedule_dirname(id_)),
                'key': schedule_dirname(id_),
                'cover': cover_image(schedule_covername(id_),
                                     schedule_dirname(id_)),
                'title': title,
                'subtitle': date_range,
                'date': fmt_date(schedule.get('modified')),
                'sort': schedule.get('modified') or 0,
                'count': touched})

        # index page: most recently changed first
        sections = []
        for key, items in (('notebooks', notebooks), ('todos', todos),
                           ('schedules', schedules)):
            items.sort(key=lambda x: x['sort'], reverse=True)
            sections.append({'id': key, 'title': t[key], 'entries': items})
        latest = max([x['sort'] for s in sections for x in s['entries']] or [0])

        # optional owners.json in the output folder: {"people": [...],
        # "owners": {"n003": "Anna", ...}}; editable from the index page
        owners = {'people': [], 'owners': {}}
        if os.path.exists(self._path('owners.json')):
            with open(self._path('owners.json'), encoding='utf-8') as f:
                owners.update(json.load(f))
        owners_json = json.dumps(owners, ensure_ascii=False).replace(
            '</', '<\\/')
        write('index.html', env.get_template('index.html'),
              base_dir='', kind='home', title=t['app'], crumbs=[],
              up_link=None,
              sections=sections,
              total_pages=sum(x['count'] for x in notebooks + todos),
              latest=fmt_date(latest), owners_json=owners_json)

    def update(self, backup, lang='en'):
        with open(self._path('tmp.sqlite3'), 'wb') as f:
            f.write(backup.extract_file(backup.find_file('enotes.db3')))

        db = sqlite3.connect(self._path('tmp.sqlite3'))
        db.row_factory = sqlite3.Row

        self.update_metadata('forms', db, backup)
        self.update_metadata('notebooks', db, backup)
        self.update_metadata('pages', db, backup)
        self.update_metadata('schedules', db, backup)
        self.update_metadata('sch_pages', db, backup)
        self.update_metadata('todos', db, backup)
        self.update_metadata('todo_pages', db, backup)

        db.close()
        os.remove(self._path('tmp.sqlite3'))

        self.update_images(backup)
        self.regenerate_web(lang)

def main():
    args = sys.argv[1:]
    lang = 'en'
    if '--lang' in args:
        i = args.index('--lang')
        lang = args[i + 1] if i + 1 < len(args) else ''
        del args[i:i + 2]
    if len(args) != 2 or lang not in STRINGS:
        print('USAGE:')
        print('{} [--lang {}] <notebook-directory> <path/to/enote.bkup>'.format(
            sys.argv[0], '|'.join(STRINGS)))
        return

    notebook_dir, backup_path = args

    with LocalNotebook(notebook_dir) as notebook:
        with EnoteBackup(backup_path) as backup:
            notebook.update(backup, lang)

if __name__ == '__main__':
    main()
