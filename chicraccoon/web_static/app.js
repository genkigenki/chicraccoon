/* Chicraccoon web view: theme, page navigation, calendar, owners */
(function () {
    'use strict';

    function store(key, value) {
        try {
            if (value === undefined) return localStorage.getItem(key);
            if (value === null) localStorage.removeItem(key);
            else localStorage.setItem(key, value);
        } catch (e) { return null; }
    }

    /* light/dark toggle */
    var toggle = document.querySelector('.theme-toggle');
    if (toggle) {
        toggle.addEventListener('click', function () {
            var root = document.documentElement;
            var cur = root.getAttribute('data-theme') ||
                (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
            var next = cur === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', next);
            store('chicraccoon-theme', next);
        });
    }

    /* page viewer: keys, swipe, "show lines" */
    var viewer = document.querySelector('.viewer');
    if (viewer) {
        var go = function (which) {
            var url = viewer.getAttribute('data-' + which);
            if (url) location.href = url;
        };
        document.addEventListener('keydown', function (e) {
            if (e.altKey || e.ctrlKey || e.metaKey) return;
            if (e.key === 'ArrowLeft' || e.key === 'PageUp') go('prev');
            else if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
                e.preventDefault(); go('next');
            } else if (e.key === 'Escape' || e.key === 'ArrowUp') go('up');
        });
        var x0 = null, y0 = null;
        viewer.addEventListener('touchstart', function (e) {
            x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
        }, { passive: true });
        viewer.addEventListener('touchend', function (e) {
            if (x0 === null) return;
            var dx = e.changedTouches[0].clientX - x0;
            var dy = e.changedTouches[0].clientY - y0;
            if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) go(dx < 0 ? 'next' : 'prev');
            x0 = null;
        });
        var formToggle = document.querySelector('.form-toggle');
        if (formToggle) {
            var apply = function () { document.body.classList.toggle('hide-form', !formToggle.checked); };
            formToggle.checked = store('chicraccoon-hide-form') !== '1';
            apply();
            formToggle.addEventListener('change', function () {
                store('chicraccoon-hide-form', formToggle.checked ? null : '1');
                apply();
            });
        }
    }

    /* calendar: highlight today */
    var d = new Date();
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var today = document.getElementById('day_' + d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()));
    if (today) today.classList.add('today');

    /* favourite pages: star on thumbnails and in the viewer, listed on
       favorites.html; kept in the browser, baked in via owners.json */
    var favDefault = [];
    try { favDefault = JSON.parse(document.getElementById('fav-data').textContent) || []; } catch (e) {}
    var getFavs = function () {
        try {
            var s = store('chicraccoon-favs');
            return s ? JSON.parse(s) : favDefault.slice();
        } catch (e) { return favDefault.slice(); }
    };
    var paintFavs = function () {
        var favs = getFavs();
        document.querySelectorAll('.star[data-page]').forEach(function (b) {
            b.setAttribute('aria-pressed', favs.indexOf(b.getAttribute('data-page')) >= 0 ? 'true' : 'false');
        });
        var count = document.querySelector('.fav-count');
        if (count) count.textContent = favs.length || '';
        var items = document.querySelectorAll('.fav-item');
        if (items.length) {
            var shown = 0;
            items.forEach(function (el) {
                var on = favs.indexOf(el.getAttribute('data-page')) >= 0;
                el.hidden = !on;
                if (on) shown++;
            });
            var empty = document.querySelector('.fav-empty');
            if (empty) empty.hidden = shown > 0;
            var txt = document.querySelector('.fav-count-text');
            if (txt) txt.textContent = shown ? shown + ' ★' : '';
        }
    };
    /* Shift+click on a star sets/clears every star between it and the
       previously clicked one (like ticking a range of books) */
    var lastStar = null;
    document.addEventListener('mousedown', function (e) {
        if (e.shiftKey && e.target.closest('.star[data-page]')) e.preventDefault(); // no text selection
    });
    document.addEventListener('click', function (e) {
        var b = e.target.closest('.star[data-page]');
        if (!b) return;
        e.preventDefault();
        var favs = getFavs(), key = b.getAttribute('data-page');
        var on = favs.indexOf(key) < 0;   // new state of the clicked star
        var targets = [b];
        if (e.shiftKey && lastStar && lastStar !== b && document.contains(lastStar)) {
            var all = Array.prototype.slice.call(document.querySelectorAll('.star[data-page]'));
            var a = all.indexOf(lastStar), z = all.indexOf(b);
            if (a >= 0 && z >= 0) targets = all.slice(Math.min(a, z), Math.max(a, z) + 1);
        }
        targets.forEach(function (t) {
            var k = t.getAttribute('data-page'), i = favs.indexOf(k);
            if (on && i < 0) favs.push(k);
            if (!on && i >= 0) favs.splice(i, 1);
        });
        lastStar = b;
        store('chicraccoon-favs', JSON.stringify(favs));
        /* on the favourites page, keep an un-starred page visible until reload */
        if (document.querySelector('.fav-item')) {
            targets.forEach(function (t) { t.setAttribute('aria-pressed', on ? 'true' : 'false'); });
            var c = document.querySelector('.fav-count');
            if (c) c.textContent = favs.length || '';
        } else {
            paintFavs();
        }
    });
    paintFavs();

    /* owners: who does each book belong to? */
    var dataEl = document.getElementById('owners-data');
    if (!dataEl) return;
    var data = { people: [], owners: {} };
    try { data = Object.assign(data, JSON.parse(dataEl.textContent)); } catch (e) {}
    try {
        var saved = JSON.parse(store('chicraccoon-owners') || 'null');
        if (saved) {
            if (saved.people && saved.people.length) data.people = saved.people;
            data.owners = Object.assign({}, data.owners, saved.owners || {});
        }
    } catch (e) {}

    var palette = ['#e5484d', '#12a594', '#8e4ec6', '#f76b15', '#0090ff', '#d6409f', '#46a758'];
    var colorOf = function (name) {
        var i = data.people.indexOf(name);
        return i < 0 ? '' : palette[i % palette.length];
    };
    var cards = Array.prototype.slice.call(document.querySelectorAll('.cover-card[data-key]'));
    var chipsEl = document.querySelector('.people-chips');
    var summaryEl = document.querySelector('.owner-summary');
    var input = document.querySelector('.people-input');
    var filter = store('chicraccoon-filter') || '';
    var pagesLabel = summaryEl.getAttribute('data-pages');
    var noneLabel = summaryEl.getAttribute('data-none');

    function save() {
        store('chicraccoon-owners', JSON.stringify({ people: data.people, owners: data.owners }));
    }

    function render() {
        document.body.classList.toggle('no-people', data.people.length === 0);
        if (data.people.indexOf(filter) < 0 && filter !== '-') filter = '';
        chipsEl.innerHTML = '';
        data.people.forEach(function (p) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'chip filter';
            b.setAttribute('data-filter', p);
            var dot = document.createElement('span');
            dot.className = 'dot';
            dot.style.background = colorOf(p);
            b.appendChild(dot);
            b.appendChild(document.createTextNode(p));
            chipsEl.appendChild(b);
        });
        if (input && document.activeElement !== input) input.value = data.people.join(', ');

        var stats = {};
        cards.forEach(function (card) {
            var key = card.getAttribute('data-key');
            var owner = data.owners[key] || '';
            if (data.people.indexOf(owner) < 0) owner = '';
            var sel = card.querySelector('.owner-select');
            sel.innerHTML = '';
            [''].concat(data.people).forEach(function (p) {
                var o = document.createElement('option');
                o.value = p;
                o.textContent = p || '—';
                if (p === owner) o.selected = true;
                sel.appendChild(o);
            });
            sel.classList.toggle('set', !!owner);
            sel.style.setProperty('--owner-color', colorOf(owner) || 'var(--accent)');
            var visible = !filter || (filter === '-' ? !owner : owner === filter);
            card.classList.toggle('hidden', !visible);
            var s = stats[owner || '-'] = stats[owner || '-'] || { books: 0, pages: 0 };
            s.books += 1;
            s.pages += parseInt(card.getAttribute('data-pages'), 10) || 0;
        });

        document.querySelectorAll('.filter').forEach(function (b) {
            b.classList.toggle('active', b.getAttribute('data-filter') === filter);
        });
        document.querySelectorAll('.shelf').forEach(function (shelf) {
            var shown = shelf.querySelectorAll('.cover-card:not(.hidden)').length;
            shelf.style.display = shown ? '' : 'none';
            var c = shelf.querySelector('.count');
            if (c) c.textContent = shown;
        });
        summaryEl.textContent = data.people.length ? data.people.concat(['-']).map(function (p) {
            var s = stats[p] || { books: 0, pages: 0 };
            return (p === '-' ? noneLabel : p) + ': ' + s.books + ' (' + s.pages + ' ' + pagesLabel + ')';
        }).join(' · ') : '';
    }

    document.addEventListener('click', function (e) {
        var b = e.target.closest('.filter');
        if (b) {
            filter = b.getAttribute('data-filter');
            store('chicraccoon-filter', filter || null);
            render();
        }
    });
    document.addEventListener('change', function (e) {
        if (!e.target.classList.contains('owner-select')) return;
        var key = e.target.closest('.cover-card').getAttribute('data-key');
        if (e.target.value) data.owners[key] = e.target.value;
        else delete data.owners[key];
        save();
        render();
    });
    if (input) {
        input.addEventListener('change', function () {
            data.people = input.value.split(',').map(function (s) { return s.trim(); })
                .filter(function (s, i, a) { return s && a.indexOf(s) === i; });
            save();
            render();
        });
    }
    var saveBtn = document.querySelector('.save-owners');
    if (saveBtn) {
        saveBtn.addEventListener('click', function () {
            var blob = new Blob([JSON.stringify(
                { people: data.people, owners: data.owners, favorites: getFavs() }, null, 2)],
                                { type: 'application/json' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'owners.json';
            document.body.appendChild(a);
            a.click();
            setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
        });
    }

    /* multi-select: tick a card's corner, Shift+click ticks the range
       between the last ticked card and this one (visible cards only) */
    var bar = document.querySelector('.selection-bar');
    if (bar) {
        var bulkOwner = bar.querySelector('.bulk-owner');
        var countEl = bar.querySelector('.sel-count');
        var anchor = null;
        var visibleCards = function () {
            return cards.filter(function (c) { return !c.classList.contains('hidden'); });
        };
        var setSelected = function (card, on) {
            card.classList.toggle('selected', on);
            card.querySelector('.pick-box').checked = on;
        };
        var updateBar = function () {
            var n = cards.filter(function (c) { return c.classList.contains('selected'); }).length;
            bar.hidden = n === 0;
            document.body.classList.toggle('selecting', n > 0);
            countEl.textContent = n + ' ' + countEl.getAttribute('data-label');
            var cur = bulkOwner.value;
            bulkOwner.innerHTML = '';
            [''].concat(data.people).forEach(function (p) {
                var o = document.createElement('option');
                o.value = p;
                o.textContent = p || '—';
                bulkOwner.appendChild(o);
            });
            bulkOwner.value = data.people.indexOf(cur) >= 0 ? cur : (data.people[0] || '');
        };
        document.addEventListener('click', function (e) {
            var box = e.target.closest('.pick-box');
            if (!box) return;
            var card = box.closest('.cover-card');
            var on = box.checked;
            var vis = visibleCards();
            if (e.shiftKey && anchor && vis.indexOf(anchor) >= 0) {
                var a = vis.indexOf(anchor), b = vis.indexOf(card);
                vis.slice(Math.min(a, b), Math.max(a, b) + 1).forEach(function (c) { setSelected(c, on); });
            } else {
                setSelected(card, on);
            }
            anchor = card;
            updateBar();
        });
        bar.querySelector('.bulk-apply').addEventListener('click', function () {
            var owner = bulkOwner.value;
            cards.forEach(function (c) {
                if (!c.classList.contains('selected')) return;
                var key = c.getAttribute('data-key');
                if (owner) data.owners[key] = owner;
                else delete data.owners[key];
                setSelected(c, false);
            });
            anchor = null;
            save();
            render();
            updateBar();
        });
        bar.querySelector('.bulk-visible').addEventListener('click', function () {
            visibleCards().forEach(function (c) { setSelected(c, true); });
            updateBar();
        });
        bar.querySelector('.bulk-clear').addEventListener('click', function () {
            cards.forEach(function (c) { setSelected(c, false); });
            anchor = null;
            updateBar();
        });
        /* changing the filter drops ticks on cards that are now hidden */
        document.addEventListener('click', function (e) {
            if (!e.target.closest('.filter')) return;
            cards.forEach(function (c) { if (c.classList.contains('hidden')) setSelected(c, false); });
            updateBar();
        });
        if (input) input.addEventListener('change', updateBar);
        updateBar();
    }
    render();
})();
