# -*- coding: utf-8 -*-

"""
    Genesis Add-on
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

import os
import re
import time
import hashlib
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from g2.libraries import log
from g2.libraries import platform


def get(function, timeout, *args, **kwargs):
    # TODO[code]: remove explicit use of traceback, use trace=True on log.*
    import traceback

    table = kwargs.get('table', 'rel_list')
    response_info = kwargs.get('response_info', {})
    hash_args = kwargs.get('hash_args', 0)

    try:
        response = None

        f = repr(function)
        f = re.sub('.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i, arg in enumerate(args):
            if hash_args and i >= hash_args:
                break
            if callable(arg):
                arg = re.sub(r'\sat\s[^>]*', '', str(arg))
            else:
                arg = str(arg)
            log.debug('cache.get: hash argument: %s'%arg)
            a.update(arg)
        a = str(a.hexdigest())
    except:
        pass

    try:
        platform.makeDir(platform.dataPath)
        dbcon = database.connect(platform.cacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM %s WHERE func = '%s' AND args = '%s'" % (table, f, a))
        match = dbcur.fetchone()
    except:
        match = None

    if not match:
        log.debug('cache.get(%s, %d, %s): cache miss in %s'%(f, timeout, a, table))
    else:
        try:
            response = eval(match[2].encode('utf-8'))
            t_cache = int(match[3])
            t_now = int(time.time())
            if timeout < 0 or (t_now-t_cache)/3600 < timeout:
                log.debug('cache.get(%s, %d, %s): returning cached value in %s at %d [now is %d]: %s'%(f, timeout, a, table, t_cache, t_now, response))
                response_info['cached'] = t_cache
                return response
            log.debug('cache.get(%s, %d, %s): cache (%d) is %dsecs older than now (%d)'%(f, timeout, a, t_cache, t_now-t_cache, t_now))
        except:
            log.notice('cache.get(%s, %d, %s):\n%s'%(f, timeout, a, traceback.format_exc()))

    try:
        log.debug('cache.get(%s, %d, %s): refreshing the value...'%(f, timeout, a))
        r = function(*args)
        if (r == None or r == []) and not response == None:
            log.debug('cache.get(%s, %d, %s): returning cached value in %s: %s'%(f, timeout, a, table, response))
            response_info['cached'] = t_cache
            return response

        log.debug('cache.get(%s, %d, %s): returning fresh value: %s'%(f, timeout, a, r))
        if (r == None or r == []):
            return r
    except:
        log.notice('cache.get(%s, %d, %s):\n%s'%(f, timeout, a, traceback.format_exc()))
        response_info['error'] = traceback.format_exc()
        return None

    try:
        r = repr(r)
        t = int(time.time())
        dbcur.execute("CREATE TABLE IF NOT EXISTS %s (""func TEXT, ""args TEXT, ""response TEXT, ""added TEXT, ""UNIQUE(func, args)"");" % table)
        dbcur.execute("DELETE FROM %s WHERE func = '%s' AND args = '%s'" % (table, f, a))
        dbcur.execute("INSERT INTO %s Values (?, ?, ?, ?)" % table, (f, a, r, t))
        dbcon.commit()
    except:
        log.notice('cache.get(%s, %d, %s):\n%s'%(f, timeout, a, traceback.format_exc()))

    try:
        r = eval(r.encode('utf-8'))
        return r
    except:
        log.notice('cache.get(%s, %d, %s):\n%s'%(f, timeout, a, traceback.format_exc()))
        response_info['error'] = traceback.format_exc()
        return None


def clear(table=None):
    try:
        if table == None: table = ['rel_list', 'rel_lib']
        elif not type(table) == list: table = [table]

        dbcon = database.connect(platform.cacheFile)
        dbcur = dbcon.cursor()

        for t in table:
            try:
                dbcur.execute("DROP TABLE IF EXISTS %s" % t)
                dbcur.execute("VACUUM")
                dbcon.commit()
            except:
                pass

        return True
    except:
        return False
