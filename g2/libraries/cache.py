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


_log_debug = True


def get(function, timeout, *args, **kwargs):
    table = kwargs.get('table', 'rel_list')
    response_info = kwargs.get('response_info', {})
    hash_args = kwargs.get('hash_args', 0)

    log.debug('{m}.{f}: %s: timeout=%d, args=%s, kwargs=%s', function, timeout, args, kwargs)

    try:
        fname = repr(function)
        fname = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', fname)
        hashargs = hashlib.md5()
        for i, arg in enumerate(args):
            if hash_args and i >= hash_args:
                break
            if callable(arg):
                arg = re.sub(r'\sat\s[^>]*', '', str(arg))
            else:
                arg = str(arg)
            hashargs.update(arg)
        hashargs = str(hashargs.hexdigest())
    except Exception as ex:
        log.notice('{m}.{f}: %s: %s', function, repr(ex))
        return function(args)

    try:
        platform.makeDir(platform.dataPath)
        dbcon = database.connect(platform.cacheFile)
        dbcon.row_factory = database.Row
        dbcur = dbcon.execute("SELECT * FROM %s WHERE func = ? AND args = ?"%table, (fname, hashargs,))
        match = dbcur.fetchone()
    except Exception:
        match = None

    if not match:
        log.debug('{m}.{f}: %s: cache miss in table %s', fname, table)
    else:
        try:
            res = ast.literal_eval(match['response'].encode('utf-8'))
            t_cache = int(match['timestamp'])
            t_now = int(time.time())
            if timeout < 0 or (t_now-t_cache)/60 < timeout:
                log.debug('{m}.{f}: %s: found valid cache entry in %s [%d secs]: %s', fname, table, t_now-t_cache, res)
                response_info['cached'] = t_cache
                return res

            log.debug('{m}.{f}: %s: expired cache entry in %s [%s secs]', fname, table, t_now-t_cache)
        except Exception as ex:
            log.notice('{m}.{f}: %s: cached entry %s: %s', fname, match['response'], repr(ex))

    try:
        res = function(*args)
    except Exception as ex:
        log.notice('{m}.{f}: %s: %s', fname, repr(ex), trace=True)
        res = None

    # (fixme) shouldn't we save also negative results?!?
    if res is not None and res is not []:
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
            log.notice('{m}.{f}: %s: new entry %s: %s', fname, res, repr(ex))

    log.debug('{m}.{f}: %s: %s', fname, res)

    return res


def clear(tables=None):
    try:
        if tables == None:
            tables = ['rel_list', 'rel_lib']
        elif type(tables) not in [list, tuple]:
            tables = [tables]

        dbcon = database.connect(platform.cacheFile)
        with dbcon:
            for table in tables:
                try:
                    dbcon.execute("DROP TABLE IF EXISTS ?", (table,))
                    dbcon.execute("VACUUM")
                except Exception as ex:
                    log.notice('{m}.{f}: %s: %s', table, repr(ex))

        return True
    except Exception as ex:
        log.notice('{m}.{f}: %s: %s', tables, repr(ex))
        return False
