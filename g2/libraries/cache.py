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


import re
import ast
import time
import hashlib
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from g2.libraries import log
from g2.libraries import platform


def get(function, timeout, *args, **kwargs):
    debug = kwargs.get('debug')
    table = kwargs.get('table', 'rel_list')
    response_info = kwargs.get('response_info', {})
    hash_args = kwargs.get('hash_args', -1)

    try:
        fname = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function))
        log.debug('{m}.{f}: %s%s: timeout=%d, kwargs=%s', fname, args, timeout, kwargs, debug=debug)

        if not hash_args or not len(args):
            hashargs = ''
        else:
            hashargs = hashlib.md5()
            for i, arg in enumerate(args):
                if hash_args > 0 and i >= hash_args:
                    break
                if callable(arg):
                    arg = re.sub(r'\sat\s[^>]*', '', str(arg))
                else:
                    arg = str(arg)
                hashargs.update(arg)
            hashargs = str(hashargs.hexdigest())
    except Exception as ex:
        log.notice('{m}.{f}: %s%s: computing argument hash: %s', fname, args, repr(ex))
        hashargs = None

    match = None
    if hashargs is not None:
        try:
            platform.makeDir(platform.dataPath)
            dbcon = database.connect(platform.cacheFile)
            dbcon.row_factory = database.Row
            dbcur = dbcon.execute("SELECT * FROM %s WHERE func = ? AND args = ?"%table, (fname, hashargs,))
            match = dbcur.fetchone()
        except Exception:
            pass

    if not match:
        log.debug('{m}.{f}: %s%s: cache miss in table %s', fname, args, table, debug=debug)
    else:
        try:
            res = ast.literal_eval(match['response'].encode('utf-8'))
            t_cache = int(match['timestamp'])
            t_now = int(time.time())
            if timeout < 0 or (t_now-t_cache)/60 < timeout:
                log.debug('{m}.{f}: %s%s: found valid cache entry in %s [%d secs]: %s',
                          fname, args, table, t_now-t_cache, res, debug=debug)
                response_info['cached'] = t_cache
                return res

            log.debug('{m}.{f}: %s%s: expired cache entry in %s [%s secs]', fname, args, table, t_now-t_cache, debug=debug)
        except Exception as ex:
            log.notice('{m}.{f}: %s%s: retrieving cached entry %s: %s', fname, args, match['response'], repr(ex))

    try:
        res = function(*args)
    except Exception as ex:
        log.notice('{m}.{f}: %s%s: refreshing cache entry: %s', fname, args, repr(ex), trace=True)
        raise

    if hashargs is not None:
        try:
            t_now = int(time.time())
            with dbcon:
                dbcon.execute("CREATE TABLE IF NOT EXISTS %s ("
                              " func TEXT,"
                              " args TEXT,"
                              " response TEXT,"
                              " timestamp TEXT,"
                              " UNIQUE(func, args));"%table)
                dbcon.execute("DELETE FROM %s WHERE func = ? AND args = ?"%table, (fname, hashargs,))
                dbcon.execute("INSERT INTO %s VALUES (?, ?, ?, ?)"%table, (fname, hashargs, repr(res), t_now,))
        except Exception as ex:
            log.notice('{m}.{f}: %s%s: storing new cache entry %s: %s', fname, args, res, repr(ex))

    log.debug('{m}.{f}: %s%s: %s', fname, args, res, debug=debug)

    return res


def clear(tables=None):
    try:
        if tables == None:
            tables = ['rel_list', 'rel_trakt']
        elif type(tables) not in [list, tuple]:
            tables = [tables]

        dbcon = database.connect(platform.cacheFile)
        with dbcon:
            for table in tables:
                try:
                    dbcon.execute("DROP TABLE IF EXISTS %s"%table)
                    dbcon.execute("VACUUM")
                except Exception as ex:
                    log.notice('{m}.{f}: %s: %s', table, repr(ex))

        return True
    except Exception as ex:
        log.notice('{m}.{f}: %s: %s', tables, repr(ex))
        return False
