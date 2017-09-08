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


import json
import time

import xbmc
import xbmcgui

from g2.libraries import ui
from g2.libraries import addon


class PlayerDialog(xbmc.Player):
    def __init__(self):
        self.name = None
        self.offset = 0
        self.info = None
        self.loading_time = 0
        self.current_time = 0
        self.play_started = False
        self.play_stopped = False
        xbmc.Player.__init__(self)

    def run(self, name, url, meta=None, offset=0, info=None):
        self.loading_time = time.time()

        self.name = name

        if meta is None:
            meta = {}
        ids = {}
        for dbid in ['imdb', 'tvdb']:
            dbidvalue = meta.get(dbid)
            if dbidvalue and dbidvalue != '0':
                ids.update({dbid: dbidvalue})

        self.offset = offset
        self.info = info

        poster = meta.get('poster', '0')
        if poster == '0':
            poster = ui.addon_poster()
        thumb = meta.get('thumb', poster)

        addon.prop(addon='script.trakt', name='ids', value=json.dumps(ids))
        addon.prop('player', name='mpaa', value=meta.get('mpaa', ''))

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

        for dummy in range(0, 120):
            if self.isPlayingVideo() or self.play_stopped:
                break
            xbmc.sleep(1000)

        total_time = 0
        self.current_time = 0
        while self.isPlayingVideo():
            try:
                if not total_time:
                    total_time = self.getTotalTime()
                self.current_time = self.getTime()
            except Exception:
                pass
            xbmc.sleep(1000)

        addon.prop(addon='script.trakt', name='ids', value='')
        addon.prop('player', name='mpaa', value='')

        return -1 if not self.play_started else 0 if not total_time else int(100*self.current_time/total_time)

    def elapsed(self):
        return self.current_time

    def onPlayBackStarted(self):
        self.play_started = True

        try:
            if self.offset:
                self.seekTime(self.offset)
        except Exception:
            pass

        for dummy in range(200):
            if xbmc.getCondVisibility('Window.IsActive(busydialog)') == 1:
                xbmc.executebuiltin('Dialog.Close(busydialog)')
            else:
                break
            xbmc.sleep(100)

        if self.info:
            for i in range(len(self.info)):
                self.info[i] = self.info[i].format(
                    elapsed_time=int(time.time()-self.loading_time),
                )
            xbmcgui.Dialog().ok(self.info[0], '[CR]'.join(self.info[1:]))

    def onPlayBackEnded(self):
        self.onPlayBackStopped()

    def onPlayBackStopped(self):
        self.play_stopped = True
