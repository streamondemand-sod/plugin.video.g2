# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016-2017 J0rdyZ65

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
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from g2.libraries import fs
from g2.libraries import log
from g2.libraries import addon


_SETTINGS_DB_FILENAME = os.path.join(addon.PROFILE_PATH, 'settings.db')


def video_key(keydict):
    """Unique identifier for videos in database records"""
    if type(keydict) != dict:
        raise KeyError
    keys = [keydict.get(k) or '0' for k in ['imdb', 'season', 'episode']]
    if not keys[0] or keys[0] == '0':
        raise KeyError
    return '/'.join(keys)


class Database(dict):
    def __init__(self, path, create_cmd, insert_cmd, select_cmd, delete_cmd):
        dict.__init__(self)
        self.path = path
        self.create_cmd = create_cmd
        self.insert_cmd = insert_cmd
        self.select_cmd = select_cmd
        self.delete_cmd = delete_cmd
        self.dbcon = None

    def _dbconnect(self):
        if not self.dbcon:
            fs.makeDir(os.path.dirname(self.path))
            self.dbcon = database.connect(self.path, timeout=10)
            self.dbcon.row_factory = database.Row

    def _get(self, key):
        try:
            self._dbconnect()
            dbcur = self.dbcon.execute(self.select_cmd, (key,))
            return dbcur.fetchone()
        except Exception as ex:
            log.debug('{m}.{f}: %s: %s', key, repr(ex))
            return {}

    def _set(self, key, fields):
        try:
            self._dbconnect()
            with self.dbcon:
                self.dbcon.execute(self.create_cmd)
                self.dbcon.execute(self.delete_cmd, (key,))
                self.dbcon.execute(self.insert_cmd, (key,)+fields)
        except Exception as ex:
            log.debug('{m}.{f}: %s, %s: %s', key, fields, repr(ex))

    def _del(self, key):
        try:
            self._dbconnect()
            with self.dbcon:
                self.dbcon.execute(self.delete_cmd, (key,))
        except Exception as ex:
            log.debug('{m}.{f}: %s: %s', key, repr(ex))

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default


class Bookmarks(Database):
    def __init__(self):
        Database.__init__(self,
                          _SETTINGS_DB_FILENAME,
                          "CREATE TABLE IF NOT EXISTS bookmarks (video_key TEXT, bookmarktime INTEGER, UNIQUE(video_key))",
                          "INSERT INTO bookmarks Values (?, ?)",
                          "SELECT * FROM bookmarks WHERE video_key = ?",
                          "DELETE FROM bookmarks WHERE video_key = ?")

    def __getitem__(self, keydict):
        row = Database._get(self, video_key(keydict))
        if not row:
            raise KeyError
        return row['bookmarktime']

    def __setitem__(self, keydict, bookmarktime):
        Database._set(self, video_key(keydict), (int(bookmarktime),))

    def __delitem__(self, keydict):
        Database._del(self, video_key(keydict))
