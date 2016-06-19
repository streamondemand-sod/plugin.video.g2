# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2015 lambda
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


import json
import time
import hashlib
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

import xbmc
import xbmcgui

from g2.libraries import log
from g2.libraries import platform
from g2.libraries.language import _
from g2 import dbs


__all__ = ['Player']


class Player(xbmc.Player):
    def __init__(self):
        self.name = None
        self.imdb = None
        self.offset = 0
        self.loading_time = 0
        self.current_time = 0
        self.total_time = 0
        self.credits = None
        self.play_started = False
        self.play_stopped = False
        xbmc.Player.__init__(self)

    def run(self, title, year, season, episode, imdb, tvdb, meta, url, credits=None):
        self.loading_time = time.time()
        self.current_time = 0
        self.total_time = 0

        # self.title = title
        # self.year = year

        content = 'movie' if not season or not episode else 'episode'
        self.name = '%s%s'%(title, '' if not year else ' (%s)'%year) if content == 'movie' else\
                    '%s S%02dE%02d'%(title, int(season), int(episode))
        self.imdb = imdb or '0'
        # self.season = '%01d' % int(season) if content == 'episode' else None
        # self.episode = '%01d' % int(episode) if content == 'episode' else None

        tvdb = tvdb or '0'
        ids = {'imdb': self.imdb, 'tvdb': tvdb}
        ids = dict((k, v) for k, v in ids.iteritems() if v != '0')

        self.credits = credits

        poster, thumb, meta = self.getMeta(meta)

        platform.property(addon='script.trakt', name='ids', value=json.dumps(ids))
        platform.property('player', name='mpaa', value=meta.get('mpaa', ''))

        try:
            offset = _get_bookmark(self.name, self.imdb)
            if offset:
                minutes, seconds = divmod(float(offset), 60)
                hours, minutes = divmod(minutes, 60)
                if xbmcgui.Dialog().yesno(_('Resume from %02d:%02d:%02d')%(hours, minutes, seconds), '', '', self.name,
                                          _('Resume'), _('Start from beginning')):
                    offset = 0
            self.offset = offset
        except Exception as ex:
            log.debug('{m}.{f}: %s: %s', self.name, repr(ex))

        item = xbmcgui.ListItem(path=url, iconImage='DefaultVideo.png', thumbnailImage=thumb)
        item.setProperty('Video', 'true')
        item.setProperty('IsPlayable', 'true')
        item.setInfo(type='Video', infoLabels=meta)
        try:
            item.setArt({'poster': poster, 'tvshow.poster': poster, 'season.poster': poster})
        except Exception:
            pass

        self.play_started = False
        self.play_stopped = False
        xbmc.Player.play(self, url, item)

        watched = dbs.watched('movie{imdb_id}', imdb_id=self.imdb)

        for dummy in range(0, 120):
            if self.isPlayingVideo() or self.play_stopped:
                break
            xbmc.sleep(1000)

        self.total_time = 0
        self.current_time = 0
        while self.isPlayingVideo():
            try:
                self.total_time = self.getTotalTime()
                self.current_time = self.getTime()
                if not watched and self.current_time / self.total_time >= .9:
                    watched = True
                    dbs.watched('movie{imdb_id}', watched, imdb_id=self.imdb)
            except Exception:
                pass
            xbmc.sleep(2000)

        platform.property(addon='script.trakt', name='ids', value='')
        platform.property('player', name='mpaa', value='')

        return -1 if not self.play_started else 0 if not self.total_time else int(100*self.current_time/self.total_time)

    def getMeta(self, meta):
        try:
            meta = json.loads(meta)

            poster = meta['poster'] if 'poster' in meta else '0'
            thumb = meta['thumb'] if 'thumb' in meta else poster

            if poster == '0':
                poster = platform.addonPoster()

            return (poster, thumb, meta)
        except Exception:
            poster, thumb, meta = '', '', {'title': self.name}
            return (poster, thumb, meta)

    def onPlayBackStarted(self):
        for i in range(0, 200):
            if xbmc.getCondVisibility('Window.IsActive(busydialog)') == 1:
                xbmc.executebuiltin('Dialog.Close(busydialog)')
            else:
                break
            xbmc.sleep(100)

        if self.credits:
            for i in range(len(self.credits)):
                self.credits[i] = self.credits[i].format(elapsed_time=int(time.time()-self.loading_time))
            xbmcgui.Dialog().ok(self.name, '[CR]'.join(self.credits))

        try:
            if self.offset:
                self.seekTime(self.offset)
        except Exception:
            pass

        self.play_started = True

    def onPlayBackEnded(self):
        self.onPlayBackStopped()

    def onPlayBackStopped(self):
        try:
            _del_bookmark(self.name, self.imdb)
            if int(self.current_time) > 180 and (self.current_time / self.total_time) <= .92:
                _add_bookmark(self.current_time, self.name, self.imdb)
        except Exception:
            pass
        self.play_stopped = True


def _add_bookmark(bookmarktime, name, imdb):
    try:
        idfile = _bookmark_id(name, imdb)
        platform.makeDir(platform.dataPath)
        dbcon = database.connect(platform.databaseFile)
        with dbcon:
            dbcon.execute("CREATE TABLE IF NOT EXISTS bookmark (idfile TEXT, bookmarktime INTEGER, UNIQUE(idfile))")
            dbcon.execute("DELETE FROM bookmark WHERE idfile = ?", (idfile,))
            dbcon.execute("INSERT INTO bookmark Values (?, ?)", (idfile, bookmarktime,))
    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', name, repr(ex))


def _get_bookmark(name, imdb):
    try:
        idfile = _bookmark_id(name, imdb)
        dbcon = database.connect(platform.databaseFile)
        dbcon.row_factory = database.Row
        dbcur = dbcon.execute("SELECT * FROM bookmark WHERE idfile = ?", (idfile,))
        match = dbcur.fetchone()
        return match['bookmarktime'] if match else 0
    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', name, repr(ex))
        return 0


def _del_bookmark(name, imdb):
    try:
        idfile = _bookmark_id(name, imdb)
        dbcon = database.connect(platform.databaseFile)
        dbcon.row_factory = database.Row
        with dbcon:
            dbcon.execute("DELETE FROM bookmark WHERE idfile = ?", (idfile,))
    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', name, repr(ex))


def _bookmark_id(name, imdb):
    idfile = hashlib.md5()
    idfile.update(name)
    idfile.update(imdb)
    return str(idfile.hexdigest())
