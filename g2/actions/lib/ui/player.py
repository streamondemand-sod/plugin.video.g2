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
    def run(self, title, year, season, episode, imdb, tvdb, meta, url, credits=None):
        log.debug('ui.Player.run: meta=%s', meta)

        self.loadingTime = time.time()
        self.totalTime = 0 ; self.currentTime = 0

        self.content = 'movie' if season == None or episode == None else 'episode'

        self.title = title
        self.year = year
        self.name = '%s%s'%(title, '' if not year else ' (%s)'%year) if self.content == 'movie' else\
                    '%s S%02dE%02d'%(title, int(season), int(episode))
        self.season = '%01d' % int(season) if self.content == 'episode' else None
        self.episode = '%01d' % int(episode) if self.content == 'episode' else None

        self.imdb = imdb if not imdb == None else '0'
        self.tvdb = tvdb if not tvdb == None else '0'
        self.ids = {'imdb': self.imdb, 'tvdb': self.tvdb}
        self.ids = dict((k,v) for k, v in self.ids.iteritems() if not v == '0')

        self.credits = credits

        poster, thumb, meta = self.getMeta(meta)

        platform.property(addon='script.trakt', name='ids', value=json.dumps(self.ids))
        platform.property('player', name='mpaa', value=meta.get('mpaa', ''))

        self.getBookmark()

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

        for i in range(0, 120):
            if self.isPlayingVideo() or self.play_stopped:
                break
            xbmc.sleep(1000)

        self.totalTime = 0
        self.currentTime = 0
        while self.isPlayingVideo():
            try:
                self.totalTime = self.getTotalTime()
                self.currentTime = self.getTime()
                if not watched and self.currentTime / self.totalTime >= .9:
                    watched = True
                    dbs.watched('movie{imdb_id}', watched, imdb_id=self.imdb)
            except Exception:
                pass
            xbmc.sleep(2000)

        platform.property(addon='script.trakt', name='ids', value='')
        platform.property('player', name='mpaa', value='')

        log.debug('ui.Player.run: started=%s, time=%s/%s', self.play_started, self.currentTime, self.totalTime)

        return -1 if not self.play_started else 0 if not self.totalTime else int(100*self.currentTime/self.totalTime)


    def getMeta(self, meta):
        try:
            meta = json.loads(meta)

            poster = meta['poster'] if 'poster' in meta else '0'
            thumb = meta['thumb'] if 'thumb' in meta else poster

            if poster == '0':
                poster = platform.addonPoster()

            return (poster, thumb, meta)
        except:
            poster, thumb, meta = '', '', {'title': self.name}
            return (poster, thumb, meta)


    def getBookmark(self):
        try:
            self.offset = _get_bookmark(self.name, self.year)
            if self.offset == '0': raise Exception()

            minutes, seconds = divmod(float(self.offset), 60) ; hours, minutes = divmod(minutes, 60)
            if xbmcgui.Dialog().yesno('%s %02d:%02d:%02d' % (_('Resume from'), hours, minutes, seconds),
                                      '', '', self.name, _('Resume'), _('Start from beginning')):
                self.offset = '0'
        except:
            pass


    def resetBookmark(self):
        try:
            _del_bookmark(self.name, self.year)
            if int(self.currentTime) > 180 and (self.currentTime / self.totalTime) <= .92:
                _add_bookmark(self.currentTime, self.name, self.year)
        except:
            pass


    def setBookmark(self):
        try:
            if self.offset == '0': raise Exception()
            self.seekTime(float(self.offset))
        except:
            pass


    def idleForPlayback(self):
        for i in range(0, 200):
            if xbmc.getCondVisibility('Window.IsActive(busydialog)') == 1:
                xbmc.executebuiltin('Dialog.Close(busydialog)')
            else:
                break
            xbmc.sleep(100)


    def showPlaybackInfo(self):
        if self.credits:
            for i in range(len(self.credits)):
                self.credits[i] = self.credits[i].format(elapsed_time=int(time.time()-self.loadingTime))
            xbmcgui.Dialog().ok(self.name, '[CR]'.join(self.credits))


    def onPlayBackStarted(self):
        self.idleForPlayback()
        self.showPlaybackInfo()
        self.setBookmark()
        self.play_started = True

    def onPlayBackStopped(self):
        self.resetBookmark()
        self.play_stopped = True


    def onPlayBackEnded(self):
        self.onPlayBackStopped()


def _get_bookmark(name, imdb='0'):
    try:
        offset = '0'
        idFile = hashlib.md5()
        for i in name: idFile.update(str(i))
        for i in imdb: idFile.update(str(i))
        idFile = str(idFile.hexdigest())
        dbcon = database.connect(platform.databaseFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM bookmark WHERE idFile = '%s'" % idFile)
        match = dbcur.fetchone()
        offset = str(match[1])
        dbcon.commit()
        return offset
    except:
        return '0'


def _add_bookmark(currentTime, name, imdb='0'):
    try:
        idFile = hashlib.md5()
        for i in name: idFile.update(str(i))
        for i in imdb: idFile.update(str(i))
        idFile = str(idFile.hexdigest())
        timeInSeconds = str(currentTime)
        platform.mkdirs(platform.dataPath)
        dbcon = database.connect(platform.databaseFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS bookmark (""idFile TEXT, ""timeInSeconds TEXT, ""UNIQUE(idFile)"");")
        dbcur.execute("DELETE FROM bookmark WHERE idFile = '%s'" % idFile)
        dbcur.execute("INSERT INTO bookmark Values (?, ?)", (idFile, timeInSeconds))
        dbcon.commit()
    except:
        pass


def _del_bookmark(name, imdb='0'):
    try:
        idFile = hashlib.md5()
        for i in name: idFile.update(str(i))
        for i in imdb: idFile.update(str(i))
        idFile = str(idFile.hexdigest())
        platform.mkdirs(platform.dataPath)
        dbcon = database.connect(platform.databaseFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS bookmark (""idFile TEXT, ""timeInSeconds TEXT, ""UNIQUE(idFile)"");")
        dbcur.execute("DELETE FROM bookmark WHERE idFile = '%s'" % idFile)
        dbcon.commit()
    except:
        pass
