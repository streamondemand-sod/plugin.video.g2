# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016 J0rdyZ65

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import time
import urllib
import urlparse

import importer

import g2

from g2.libraries import log
from g2.libraries import platform


# _log_debug = True
# _log_trace_on_error = True

_info_lang = platform.setting('infoLang') or 'en'
_default_db_priority = 10


def info(force=False):
    def db_info(package, module, m, paths):
        if not hasattr(m, 'info'):
            return []
        if callable(m.info):
            nfo = m.info(paths)
        else:
            nfo = m.info
        nfo = dict(nfo)
        nfo.update({
            # Fixed priority defined at the module level
            'priority': nfo.get('priority', _default_db_priority),
        })
        return [nfo]

    return g2.info('dbs', db_info, force)


def url(kind=None, **kwargs):
    url = _alldbs_method('url', None, kind, **kwargs)
    return '' if not url else urllib.quote_plus(url) if kwargs.get('quote_plus') else url


def movies(url):
    return _alldbs_method('movies', url, url)


def metas(metas):
    # (fixme) cache the results using cachemeta, move cachemeta here!
    work_items = []
    for m in metas:
        if m['item']:
            continue
        if m.get('tmdb', '0') != '0':
            m['url'] = url('movie_meta{tmdb_id}', tmdb_id=m['tmdb'], info_lang=m['lang'])
        elif m.get('imdb', '0') != '0':
            m['url'] = url('movie_meta{imdb_id}', imdb_id=m['imdb'], info_lang=m['lang'])
        if m.get('url'):
            work_items.append(m)

    for db in sorted([d for d in info().itervalues() if 'metas' in d['methods']], key=lambda d: d['priority']):
        package_work_items = [w for w in work_items if not w['item'] and urlparse.urlparse(w['url']).netloc.lower() in db['domains']]
        if package_work_items:
            _db_method(db, 'metas', package_work_items)

    # (fixme) add time taken
    log.notice('dbs.metas: %d submitted, %d processed, %d completed'%(len(metas), len(work_items), len([w for w in work_items if w['item']])))


def persons(url):
    return _alldbs_method('persons', url, url)


def genres():
    return _alldbs_method('genres', None)


def certifications(country='US'):
    return _alldbs_method('certifications', None, country)


def lists(url):
    return _alldbs_method('lists', url, url)


def watched(kind, seen=None, **kwargs):
    return _alldbs_method('watched', None, 'watched.'+kind, seen, **kwargs)


def _alldbs_method(method, url, *args, **kwargs):
    netloc = urlparse.urlparse(url).netloc.lower() if url else None
    for dbp in sorted([d for d in info().itervalues() if method in d['methods'] and (not netloc or netloc in d['domains'])],
                    key=lambda d: d['priority']):
        result = _db_method(dbp, method, *args, **kwargs)
        if result is not None:
            return result if not kwargs.get('db_provider') else dbp['module']

    return None


def _db_method(db, method, *args, **kwargs):
    log.debug('dbs.%s.%s(%s, %s)'%(db['name'], method, args, kwargs))
    result = None
    try:
        if 'package' in db:
            with g2.Context('dbs', db['package'], [db['module']], db['search_paths']) as mod:
                result = getattr(mod[0], method)(*args, **kwargs)
        else:
            with g2.Context('dbs', db['module'], [], []) as mod:
                result = getattr(mod, method)(*args, **kwargs)
    except Exception as ex:
        log.error('dbs.%s.%s(): %s'%(db['name'], method, ex))

    return result
