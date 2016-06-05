# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2015 lambda

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
import hashlib
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from g2.libraries import platform


_metadata_cache_lifetime = (30*24)


def fetch(items, lang):
    try:
        dbcon = database.connect(platform.metacacheFile)
        dbcur = dbcon.cursor()
    except:
        return None

    metas = []
    for i in items:
        try:
            metas.append({
                'tmdb': i.get('tmdb', '0'),
                'imdb': i.get('imdb', '0'),
                'tvdb': i.get('tvdb', '0'),
                'lang': lang,
                'item': None,
            })

            dbcur.execute("SELECT * FROM meta WHERE (imdb = '%s' and lang = '%s' and not imdb = '0') or (tmdb = '%s' and lang = '%s' and not tmdb = '0') or (tvdb = '%s' and lang = '%s' and not tvdb = '0')" % (i['imdb'], lang, i['tmdb'], lang, i['tvdb'], lang))
            match = dbcur.fetchone()

            if (time.time() - int(match[5])) / 3600 < _metadata_cache_lifetime:
                item = eval(match[4].encode('utf-8'))
                item = dict((k,v) for k, v in item.iteritems() if v is not None and v != '0')
                metas[-1]['item'] = item
        except:
            pass

    return metas


def insert(metas):
    if not metas:
        return
    try:
        platform.makeDir(platform.dataPath)
        dbcon = database.connect(platform.metacacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS meta (""imdb TEXT, ""tmdb TEXT, ""tvdb TEXT, ""lang TEXT, ""item TEXT, ""time TEXT, ""UNIQUE(imdb, tmdb, tvdb, lang)"");")
        t = int(time.time())
        for m in metas:
            try:
                i = repr(m['item'])
                try: dbcur.execute("DELETE * FROM meta WHERE (imdb = '%s' and lang = '%s' and not imdb = '0') or (tmdb = '%s' and lang = '%s' and not tmdb = '0') or (tvdb = '%s' and lang = '%s' and not tvdb = '0')" % (m['imdb'], m['lang'], m['tmdb'], m['lang'], m['tvdb'], m['lang']))
                except: pass
                dbcur.execute("INSERT INTO meta Values (?, ?, ?, ?, ?, ?)", (m['imdb'], m['tmdb'], m['tvdb'], m['lang'], i, t))
            except:
                pass

        dbcon.commit()
    except:
        pass
