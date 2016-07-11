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


import ast
import time
import urllib
import urlparse
import hashlib
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from g2.libraries import fs
from g2.libraries import log
from g2.libraries import cache
from g2.libraries import addon
from g2.libraries import client

from g2 import pkg
from g2 import defs


_INFO_LANG = addon.language('infoLang')


def info(force_refresh=False):
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
            'priority': nfo.get('priority', defs.DEFAULT_PACKAGE_PRIORITY),
        })
        return [nfo]

    return pkg.info('dbs', db_info, force_refresh)


def resolve(kind=None, **kwargs):
    url = _alldbs_method('resolve', None, kind, **kwargs)
    return '' if not url else urllib.quote_plus(url) if kwargs.get('quote_plus') else url


def movies(url, **kwargs):
    url = resolve(url, **kwargs) or url
    return _alldbs_method('movies', url, url)


def series(url, **kwargs):
    url = resolve(url, **kwargs) or url
    return _alldbs_method('series', url, url)


def meta(items, content='movie', lang=_INFO_LANG):
    metas = _fetch_meta(items, lang)

    work_items = []
    for met in metas:
        if met['item']:
            continue
        if met.get('tmdb', '0') != '0':
            # (fixme) add {lang} like tvshows
            met['url'] = resolve('%s_meta{tmdb_id}'%content, tmdb_id=met['tmdb'])
        elif met.get('tvdb', '0') != '0':
            met['url'] = resolve('%s_meta{tvdb_id}{lang}'%content, tvdb_id=met['tvdb'], lang=lang)
        elif met.get('imdb', '0') != '0':
            # (fixme) add {lang} like tvshows
            met['url'] = resolve('%s_meta{imdb_id}'%content, imdb_id=met['imdb'])
        if met.get('url'):
            work_items.append(met)

    started = time.time()
    dbmods = sorted([d for d in info().itervalues() if 'meta' in d.get('methods', [])], key=lambda d: d['priority'])
    for dbm in dbmods:
        package_work_items = [w for w in work_items
                              if not w['item'] and urlparse.urlparse(w['url']).netloc.lower() in dbm['domains']]
        if package_work_items:
            _db_method(dbm, 'meta', package_work_items)

    log.notice('{m}.{f}: %d submitted, %d scheduled, %d completed in %.2f seconds',
               len(items), len(work_items), len([w for w in work_items if w['item']]), time.time()-started)

    # Update all item attributes except fanart and rating if present
    for met, item in zip(metas, items):
        if met['item']:
            item.update(dict((k, v) for k, v in met['item'].iteritems()
                             if k not in ['fanart', 'rating'] or (k in ['fanart', 'rating'] and item.get(k, '0') == '0')))

    _save_meta(metas)


def persons(url, **kwargs):
    url = resolve(url, **kwargs) or url
    return _alldbs_method('persons', url, url)


def genres():
    url = resolve('genres{}')
    return _alldbs_method('genres', url, url)


def certifications(country='US'):
    url = resolve('certifications{}')
    return _alldbs_method('certifications', url, url, country)


def lists(url, **kwargs):
    url = resolve(url, **kwargs) or url
    return _alldbs_method('lists', url, url)


def watched(kind, seen=None, **kwargs):
    return _alldbs_method('watched', None, 'watched.'+kind, seen, **kwargs)


def _alldbs_method(method, url, urlarg, *args, **kwargs):
    netloc = urlparse.urlparse(url).netloc.lower() if url else None
    dbmods = sorted([d for d in info().itervalues() if method in d.get('methods', []) and (not netloc or netloc in d['domains'])],
                    key=lambda d: d['priority'])
    for dbm in dbmods:
        if not url or '|' not in urlarg:
            result = _db_method(dbm, method, urlarg, *args, **kwargs)
            log.debug('{m}.%s.%s: %s %s %s: %s'%(dbm['name'], method, urlarg, args, kwargs, result))
        else:
            timeout = urlarg.split('|')[1]
            response_info = {}
            result = cache.get(_db_method, int(timeout)*60, dbm, method, urlarg, *args, response_info=response_info)
            log.debug('{m}.%s.%s: %s %s (timeout=%s): %s%s',
                      dbm['name'], method, urlarg, args, timeout,
                      '' if 'cached' not in response_info else '[cached] ', result)
        if result is not None:
            return result if not kwargs.get('return_db_provider') else dbm['module']

    return None


def _db_method(dbm, method, *args, **kwargs):
    result = None
    try:
        if 'package' in dbm:
            with pkg.Context('dbs', dbm['package'], [dbm['module']], dbm['search_paths']) as mod:
                result = getattr(mod[0], method)(*args, **kwargs)
        else:
            with pkg.Context('dbs', dbm['module'], [], []) as mod:
                result = getattr(mod, method)(*args, **kwargs)
    except Exception as ex:
        log.error('{m}.%s.%s: %s'%(dbm['name'], method, repr(ex)))

    return result


def _fetch_meta(items, lang):
    try:
        dbcon = database.connect(fs.META_DB_FILENAME)
        dbcon.row_factory = database.Row
    except Exception as ex:
        log.error('{m}.{f}: %s: %s', fs.META_DB_FILENAME, repr(ex))
        return []

    metas = []
    for i in items:
        try:
            metas.append({
                'lang': lang,
                'tmdb': i.get('tmdb', '0'),
                'imdb': i.get('imdb', '0'),
                'tvdb': i.get('tvdb', '0'),
                'item': None,
            })

            dbcur = dbcon.execute("SELECT * FROM meta"
                                  " WHERE lang = ? AND"
                                  "  ((imdb = ? and imdb <> '0') OR"
                                  "   (tmdb = ? and tmdb <> '0') OR"
                                  "   (tvdb = ? and tvdb <> '0'))",
                                  (metas[-1]['lang'], metas[-1]['imdb'], metas[-1]['tmdb'], metas[-1]['tvdb'],))
            sqlrow = dbcur.fetchone()
            if not sqlrow or (time.time()-int(sqlrow['timestamp']))/3600 > defs.METADATA_CACHE_LIFETIME:
                continue

            item = ast.literal_eval(sqlrow['item'].encode('utf-8'))
            if item:
                item = dict((k, v) for k, v in item.iteritems() if v is not None and v != '0')
                metas[-1]['item'] = item

        except Exception as ex:
            log.error('{m}.{f}: %s: %s', i, repr(ex))

    return metas


def _save_meta(metas):
    try:
        fs.makeDir(fs.PROFILE_PATH)
        dbcon = database.connect(fs.META_DB_FILENAME)
        dbcon.row_factory = database.Row
        dbcon.execute("CREATE TABLE IF NOT EXISTS meta ("
                      " lang TEXT,"
                      " imdb TEXT,"
                      " tmdb TEXT,"
                      " tvdb TEXT,"
                      " item TEXT,"
                      " timestamp TEXT,"
                      " UNIQUE(lang, imdb, tmdb, tvdb))")
    except Exception as ex:
        log.error('{m}.{f}: %s: %s', fs.META_DB_FILENAME, repr(ex))
        return

    now = int(time.time())
    for i in metas:
        with dbcon:
            try:
                dbcon.execute("DELETE FROM meta"
                              " WHERE lang = ? AND"
                              "  ((imdb = ? and imdb <> '0') OR"
                              "   (tmdb = ? and tmdb <> '0') OR"
                              "   (tvdb = ? and tvdb <> '0'))",
                              (i['lang'], i['imdb'], i['tmdb'], i['tvdb'],))
            except Exception as ex:
                log.debug('{m}.{f}: %s: %s', i, repr(ex))

            if i.get('item'):
                try:
                    dbcon.execute("INSERT INTO meta VALUES (?, ?, ?, ?, ?, ?)",
                                  (i['lang'], i['imdb'], i['tmdb'], i['tvdb'], repr(i['item']), now,))
                except Exception as ex:
                    log.error('{m}.{f}: %s: %s', i, repr(ex))


def normalize_imdb(imdb):
    if not imdb or imdb == '0':
        raise Exception('Missing imdb')
    imdb = 'tt%07d'%int(str(imdb).translate(None, 't'))
    return imdb.encode('utf-8')


def fields_mapping_xml(src, mappings_desc):
    item = {}
    for desc in mappings_desc:
        name = desc['name']
        value = ''
        if 'tag' in desc:
            values = client.parseDOM(src, desc['tag'])
            if values:
                value = values[0]
                if value is None:
                    value = ''
                value = client.replaceHTMLCodes(value)
        if callable(desc.get('map')):
            try:
                value = desc['map'](item, value)
            except Exception:
                if not desc.get('optional'):
                    raise
                value = desc.get('default', '')
        if not value:
            value = desc.get('default', '' if isinstance(value, basestring) else [])
        if value:
            if isinstance(value, basestring):
                try:
                    value = value.encode('utf-8', 'ignore')
                except Exception:
                    pass
            item[name] = value
        elif not desc.get('optional'):
            raise Exception('mandatory %s field missing'%name)
        elif value is []:
            item[name] = value

    return item
