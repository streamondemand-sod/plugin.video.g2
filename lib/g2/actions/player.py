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


import re
import json

import xbmc

from g2.libraries import log
from g2.libraries import platform
from g2.libraries.language import _
from g2.dbs import tmdb
from g2 import notifiers


_log_debug = True


_PLAYER = xbmc.Player()


def stop(push):
    log.debug('{m}.{f}: push=%s', push)
    if platform.property('playingtitle') == push['iden']:
        _PLAYER.stop()
        notifiers.notices(_('Forced player stop'))


def notify(action, **dummy_kwargs):
    if not _PLAYER.isPlaying():
        notice_id = platform.property('playingtitle')
        log.debug('{m}.{f}: deleting notice_id=%s...', notice_id)
        if notice_id:
            notifiers.notices([], targets='remote', identifier=[notice_id])
            platform.property('playingtitle', '')

    elif not _PLAYER.isPlayingVideo():
        return

    else:
        title = xbmc.getInfoLabel('VideoPlayer.Title')
        year = xbmc.getInfoLabel('VideoPlayer.Year')

        # Look for the MPAA rating if set by the player or the addons
        mpaa = xbmc.getInfoLabel('VideoPlayer.mpaa')
        if not mpaa:
            mpaa = platform.property('player', name='mpaa')

        # Look for the IMDB id, if set by the player or the addons
        imdb = xbmc.getInfoLabel('VideoPlayer.IMDBNumber')
        if not imdb:
            try:
                ids = json.loads(platform.property(addon='script.trakt', name='ids'))
            except Exception:
                ids = {}
            imdb = ids.get('imdb')

        db_item = _fetch_db_meta(imdb, title, year)
        if db_item:
            title = db_item['title']
            year = db_item['year']
            imdb = db_item['imdb']
            mpaa = db_item.get('mpaa')

        title = title + ('' if not year else ' (%s)'%year) + ('' if not mpaa or mpaa == '0' else ' [%s]'%mpaa)
        if not title:
            title = '???'
        url = '' if not imdb else 'http://www.imdb.com/title/' + imdb

        notice_id = []
        notifiers.notices(' '.join([_('Playing'), title, url]), targets='remote', identifier=notice_id)

        log.debug('{m}.{f}: created notice_id=%s', notice_id)
        if len(notice_id):
            platform.property('playingtitle', notice_id[0])


def _fetch_db_meta(imdb, title, year):
    if imdb:
        # If the IMDB id is known, fetch the metadata
        meta = {'url': tmdb.url('movie_meta{imdb_id}', imdb_id=imdb)}
        tmdb.metas([meta])
        log.debug('{m}.{f}: tmdb.metas([%s]): %s', imdb, meta)
        return meta.get('item')

    # If the IMDB id is not known, perform an heuristic check on the title / year
    log.debug('{m}.{f}: identifying title="%s" and year=%s...', title, year)
    if not year:
        try:
            year = re.search(r'\((\d{4})\)', title).group(1)
        except Exception:
            year = None

    if not title or not year:
        return None

    def cleantitle(title):
        if title:
            title = re.sub(r'\(.*\)', '', title) # Anything within ()
            title = re.sub(r'\[.*\]', '', title) # Anything within []
        return title

    items = tmdb.movies(tmdb.url('movies{title}{year}', title=cleantitle(title), year=year))
    log.debug('{m}.{f}: tmdb.movies("%s", %s): %s', title, year, items)
    if not items:
        return None

    meta = {'url': tmdb.url('movie_meta{tmdb_id}', tmdb_id=items[0]['tmdb'])}
    tmdb.metas([meta])
    log.debug('{m}.{f}: tmdb.metas([%s]): %s', items[0]['tmdb'], meta)
    return meta.get('item')
