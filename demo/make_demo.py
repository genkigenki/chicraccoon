"""Build a demo website with made-up notes (no eNote needed).

    python demo/make_demo.py [output-folder] [--lang en|de|ja]

Creates the same folder layout a real backup produces (data.json + PNG layers)
and renders the website, so you can try the viewer before using your own backup.
"""
import datetime, math, os, random, sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from chicraccoon.sync import LocalNotebook  # noqa: E402

random.seed(3)
W, H = 600, 700


def font(size):
    for name in ('Inkfree.ttf', 'segoepr.ttf', 'Comic Sans MS.ttf', 'comic.ttf',
                 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def to_layer(img):
    """white paper / black ink (L) -> black ink with alpha, like a real backup"""
    a = img.point(lambda v: 255 - v)
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    out.putalpha(a)
    return out


class Sheet:
    def __init__(self, size=(W, H)):
        self.img = Image.new('L', size, 255)
        self.d = ImageDraw.Draw(self.img)

    def text(self, xy, s, size=34, fill=0):
        x, y = xy
        for line in s.split('\n'):
            self.d.text((x + random.uniform(-1, 1), y), line, font=font(size), fill=fill)
            y += int(size * 1.45)

    def line(self, pts, w=3, fill=0):
        self.d.line([(x + random.uniform(-.8, .8), y + random.uniform(-.8, .8)) for x, y in pts],
                    fill=fill, width=w, joint='curve')

    def circle(self, cx, cy, r, w=3, fill=0, steps=48):
        self.line([(cx + r * math.cos(2 * math.pi * k / steps), cy + r * math.sin(2 * math.pi * k / steps))
                   for k in range(steps + 1)], w, fill)

    def layer(self):
        return to_layer(self.img)


def lined_form():
    s = Sheet()
    for y in range(70, H, 52):
        s.d.line((0, y, W, y), fill=165, width=1)
    return s.layer()


def todo_form():
    s = Sheet()
    s.d.line((0, 62, W, 62), fill=120, width=2)
    for k in range(9):
        y = 90 + k * 66
        s.d.rectangle((24, y, 56, y + 32), outline=110, width=2)
        s.d.line((0, y + 50, W, y + 50), fill=190, width=1)
    return s.layer()


def week_form(monday):
    s = Sheet()
    s.d.line((0, 56, W, 56), fill=120, width=2)
    names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for k in range(7):
        y = 60 + k * 91
        s.d.line((0, y, W, y), fill=170, width=1)
        day = monday + datetime.timedelta(days=k)
        s.d.text((10, y + 6), '{} {}'.format(names[k], day.day), font=ImageFont.truetype('arial.ttf', 18)
                 if os.name == 'nt' else font(18), fill=110)
    return s.layer()


def save(nb, rel, layer, thumb=None):
    p = os.path.join(nb.path, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    layer.save(p)
    if thumb:
        p = os.path.join(nb.path, thumb)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        layer.resize((150, 175), Image.LANCZOS).save(p)


def cover(title, doodle=None):
    s = Sheet((220, 292))
    s.d.rounded_rectangle((8, 8, 212, 284), 14, outline=0, width=3)
    s.text((22, 40), title, size=30)
    if doodle:
        doodle(s)
    return s.layer()


# ------------------------------------------------------------------ page content
def physics_1(s):
    s.text((30, 12), 'Pendulum', 44)
    s.line([(300, 110), (300, 120)], 4)
    s.line([(200, 110), (400, 110)], 4)
    s.line([(300, 110), (390, 300)], 3)
    s.circle(398, 318, 22, 3)
    s.line([(300, 110), (300, 330)], 1, 120)
    s.text((316, 170), 'θ', 30)
    s.text((40, 380), 'T = 2π · sqrt(L / g)', 40)
    s.text((40, 460), 'L = 1 m  ->  T = 2.0 s', 32)
    s.text((40, 540), 'small angles only!', 30)


def physics_2(s):
    s.text((30, 12), 'Light & energy', 44)
    s.text((40, 120), 'E = mc²', 52)
    s.text((40, 230), 'E = hν = hc / λ', 40)
    s.line([(60, 400) ] + [(60 + x, 400 - 50 * math.sin(x / 22)) for x in range(0, 460, 6)], 3)
    s.text((230, 470), 'λ', 36)
    s.line([(120, 520), (260, 520)], 2)
    s.text((40, 580), 'red ~700 nm   blue ~450 nm', 28)


def yokohama_1(s):
    s.text((30, 12), 'Yokohama', 46)
    s.text((40, 110), '• Minato Mirai walk\n• Chinatown lunch\n• Cup Noodles Museum\n• Sankeien garden', 32)
    cx, cy, r = 430, 470, 110
    s.circle(cx, cy, r, 3)
    for k in range(12):
        a = 2 * math.pi * k / 12
        s.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], 1)
        s.circle(cx + r * math.cos(a), cy + r * math.sin(a), 9, 2)
    s.line([(cx, cy), (cx - 60, 660)], 3)
    s.line([(cx, cy), (cx + 60, 660)], 3)
    s.line([(20, 660), (580, 660)], 2)


def yokohama_2(s):
    s.text((30, 12), 'Bay at night', 46)
    for x, h in ((60, 160), (120, 240), (190, 200), (260, 330), (330, 210), (400, 280), (470, 180)):
        s.line([(x, 520), (x, 520 - h), (x + 52, 520 - h), (x + 52, 520)], 3)
        for wy in range(520 - h + 20, 510, 34):
            s.d.rectangle((x + 12, wy, x + 20, wy + 10), fill=0)
    for k in range(5):
        y = 560 + k * 22
        s.line([(40 + (k % 2) * 30 + x, y + 6 * math.sin(x / 15)) for x in range(0, 500, 10)], 2, 90)


def wolf_page(path):
    def draw(s):
        s.text((30, 12), 'Wolf cub sketch', 44)
        if path and os.path.exists(path):
            w = Image.open(path).convert('L')
            w.thumbnail((440, 560))
            s.img.paste(w, ((W - w.width) // 2, 110))
        else:
            s.circle(300, 380, 150, 4)
    return draw


def ideas(s):
    s.text((30, 12), 'Ideas', 46)
    s.circle(300, 360, 70, 3)
    s.text((248, 340), 'e-note', 32)
    for (x, y, t) in ((70, 150, 'PDF export'), (380, 150, 'web view'), (40, 560, 'favourites'),
                      (380, 560, '3 languages')):
        s.line([(300, 360), (x + 80, y + 20)], 2)
        s.text((x, y), t, 30)


def shopping(s):
    s.text((30, 12), 'Shopping', 46)
    for k, item in enumerate(('milk', 'rice', 'miso', 'apples', 'pencils', 'batteries')):
        y = 120 + k * 78
        s.text((70, y), item, 36)
        if k in (0, 2, 3):
            s.line([(60, y + 30), (70 + 30 * len(item), y + 26)], 3)


TODO_ITEMS = [
    ['water the plants', 'call grandma', 'fix the bike light', 'book train tickets',
     'return library books', 'bake bread'],
    ['make a backup', 'run the website generator', 'print the overview', 'share the link',
     'thank the professor :)'],
]


def todo_page(items, checked):
    s = Sheet()
    s.text((24, 6), 'To-Do', 36)
    for k, it in enumerate(items):
        y = 90 + k * 66
        s.text((76, y - 8), it, 32)
        if checked >> k & 1:
            s.line([(28, y + 14), (40, y + 28), (60, y - 4)], 4)
    return s.layer()


def main():
    args = sys.argv[1:]
    lang = 'en'
    if '--lang' in args:
        i = args.index('--lang'); lang = args[i + 1]; del args[i:i + 2]
    out = os.path.abspath(args[0] if args else os.path.join(HERE, 'demo_site'))
    wolf = os.path.join(HERE, 'wolf_sketch.png')
    nb = LocalNotebook(out)
    d = nb.d
    for k in d:
        d[k] = {}
    t0 = int(datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc).timestamp())
    day = 86400

    d['forms'][1] = {'notebook': 0}
    save(nb, 'images/form/f0000001_0.png', lined_form(), 'images/thumbnail/form/f0000001_0.png')

    books = [
        ('Physics', [physics_1, physics_2], lambda s: (s.circle(110, 200, 40, 3), s.text((92, 182), 'E', 32))),
        ('Yokohama', [yokohama_1, yokohama_2], lambda s: s.circle(110, 200, 50, 2)),
        ('Sketches', [wolf_page(wolf)], None),
        ('Ideas', [ideas], None),
        ('Shopping', [shopping], None),
    ]
    page_id = 1
    for n, (title, pages, doodle) in enumerate(books, 1):
        ids = []
        for fn in pages:
            s = Sheet(); fn(s)
            save(nb, 'images/page/n{:06x}/p{:07x}_0.png'.format(n, page_id), s.layer(),
                 'images/thumbnail/page/n{:06x}/t{:07x}_0.png'.format(n, page_id))
            d['pages'][page_id] = {'form': 1}
            ids.append(page_id); page_id += 1
        d['notebooks'][n] = {'pages': ids, 'modified': t0 + (10 - n) * day}
        save(nb, 'images/note/n{:07x}_0.png'.format(n), cover(title, doodle))

    save(nb, 'images/todo_form/f0000001_0.png', todo_form(), 'images/todo_thumbnail/todo_form/f0000001_0.png')
    tp = 1
    for n, (items, checked) in enumerate(zip(TODO_ITEMS, (0b100101, 0b00011)), 1):
        save(nb, 'images/todo_page/n{:06x}/p{:07x}_0.png'.format(n, tp), todo_page(items, checked),
             'images/todo_thumbnail/todo_page/n{:06x}/t{:07x}_0.png'.format(n, tp))
        d['todo_pages'][tp] = {'form': 1, 'checked': checked, 'starred': 0}
        d['todos'][n] = {'pages': [tp], 'modified': t0 + (5 - n) * day}
        save(nb, 'images/todo/n{:07x}_0.png'.format(n), cover(['Home', 'Project'][n - 1]))
        tp += 1

    # one calendar: December 2026, one page per week
    monday = datetime.date(2026, 11, 30)
    notes = {1: [(1, 'dentist 10:00'), (4, 'Kai birthday!')], 3: [(2, 'piano'), (5, 'Christmas market')]}
    ids = []
    for k in range(5):
        start = monday + datetime.timedelta(weeks=k)
        ts = lambda dt: int(datetime.datetime(dt.year, dt.month, dt.day, tzinfo=datetime.timezone.utc).timestamp())
        sid = k + 1
        save(nb, 'images/sch_form/s000001/f{:07x}_0.png'.format(sid), week_form(start))
        if k in notes:
            s = Sheet()
            for dd, txt in notes[k]:
                s.text((150, 60 + dd * 91 + 20), txt, 32)
            save(nb, 'images/sch_page/s000001/p{:07x}_0.png'.format(sid), s.layer())
        d['sch_pages'][sid] = {'start_date': ts(start), 'end_date': ts(start + datetime.timedelta(days=6)),
                               'touched': k in notes}
        ids.append(sid)
    d['schedules'][1] = {'start_date': d['sch_pages'][1]['start_date'],
                         'end_date': d['sch_pages'][5]['end_date'], 'pages': ids, 'modified': t0 + 2 * day}
    save(nb, 'images/schedule/s0000001_0.png', cover('2026\nDecember'))

    nb.save()
    nb.regenerate_web(lang)
    print('Demo website:', os.path.join(out, 'index.html'))


if __name__ == '__main__':
    main()
