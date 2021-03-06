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


import re
import json

from g2.libraries import ui
from g2.libraries import log
from g2.libraries import addon
from g2.libraries.language import _

from g2 import dbs
from g2 import notifiers

from . import action


_PLAYER = ui.Player()


@action
def notify():
    if addon.freshsetting('player_notify') != 'true':
        return

    if not _PLAYER.isPlaying():
        identifiers = addon.prop('player.notice.ids')
        log.debug('{m}.{f}: deleting notices with ids=%s...', identifiers)
        if identifiers:
            notifiers.notices([], targets='remote', identifiers=identifiers)
            addon.prop('player.notice.ids', '')

    elif not _PLAYER.isPlayingVideo():
        return

    else:
        title = ui.infoLabel('VideoPlayer.Title')
        year = ui.infoLabel('VideoPlayer.Year')

        # Look for the MPAA rating if set by the player or the addons
        mpaa = ui.infoLabel('VideoPlayer.mpaa')
        if not mpaa:
            mpaa = addon.prop('player', name='mpaa')

        # Look for the IMDB id, if set by the player or the addons
        imdb = ui.infoLabel('VideoPlayer.IMDBNumber')
        if not imdb:
            try:
                ids = json.loads(addon.prop(addon='script.trakt', name='ids'))
            except Exception:
                ids = {}
            imdb = ids.get('imdb')

        db_item = _fetch_db_meta(imdb, title, year)
        if db_item:
            title = db_item['title']
            year = db_item['year']
            imdb = db_item['imdb']
            mpaa = db_item.get('mpaa')

        # Movie label in case the year is known
        title = ((_('{title} ({year})').format(title=title, year=year) if year else title) +
                 ('' if not mpaa or mpaa == '0' else ' [%s]'%mpaa))
        if not title:
            title = '???'
        url = '' if not imdb else 'http://www.imdb.com/title/' + imdb

        identifiers = {}
        notifiers.notices(_('Playing {title}{dashes_if_url}{url}').
                          format(
                              title=title,
                              dashes_if_url='--' if url else '',
                              url=url,
                          ), targets='remote', identifiers=identifiers)

        if identifiers:
            log.debug('{m}.{f}: created notices with ids=%s', identifiers)
            addon.prop('player.notice.ids', identifiers)


def _fetch_db_meta(imdb, title, year):
    if imdb:
        # If the IMDB id is known, fetch the metadata
        meta = {'imdb': imdb}
        dbs.meta([meta])

        log.debug('{m}.{f}: %s: meta=%s', imdb, meta)

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

    items = dbs.movies('movies{title}{year}', title=cleantitle(title), year=year)

    log.debug('{m}.{f}: %s (%s): %d movies', title, year, len(items))

    if not items:
        return None

    meta = {'tmdb': items[0]['tmdb']}
    dbs.meta([meta])

    log.debug('{m}.{f}: %s: meta=%s', items[0]['tmdb'], meta)

    return meta.get('item')
