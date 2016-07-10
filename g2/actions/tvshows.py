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


from g2.libraries import ui
from g2.libraries import log
from g2.libraries import addon
from g2.libraries.language import _

from g2 import dbs

from .lib import uid
from . import action, busyaction


@action
def menu():
    uid.additem(_('Search by Title'), 'tvshows.searchbytitle', 'tvSearch', 'DefaultTVShows.png', isFolder=False)
    uid.finish()


@action
def searchbytitle():
    query = ui.keyboard(_('TV series search'))
    if query:
        url = dbs.resolve('series{title}', title=query, quote_plus=True)
        ui.refresh('tvshows.serieslist', url=url)


@action
def serieslist(url):
    log.debug('{m}.{f}: %s', url)
    items = dbs.series(url)
    if not items:
        ui.infoDialog(_('No results'))
    else:
        dbs.meta(items, content='serie')
        for i in items:
            # TV show directory item label when the year is kwnon
            i['name'] = _('{title} ({year})').format(
                title=i['title'],
                year=i['year']) if i.get('year') else i['title']
            i['action'] = addon.itemaction('tvshows.seasons', tvdb=i['tvdb'], imdb=i['imdb'])
            i['next_action'] = 'tvshows.serieslist'
            # Deleting all this info otherwise the Kodi listitem chokes! :)
            for nfo in ['seasons', 'episodes']:
                if nfo in i:
                    del i[nfo]

    uid.addcontentitems(items, content='tvshows')


@action
def seasons(tvdb, imdb):
    item = {
        'tvdb': tvdb,
        'imdb': imdb,
    }
    dbs.meta([item], content='serie')

    items = item.get('seasons', [])
    if not items:
        ui.infoDialog(_('No seasons'))
    else:
        for i in items:
            # Season directory item label 
            i['name'] = _('Season {season} ({year})').format(
                season=i['season'],
                year=i['premiered'][0:4])
            i['action'] = addon.itemaction('tvshows.episodes', tvdb=i['tvdb'], imdb=i['imdb'], season=i['season'])

    uid.addcontentitems(items, content='seasons')


@action
def episodes(tvdb, imdb, season):
    item = {
        'tvdb': tvdb,
        'imdb': imdb,
    }
    dbs.meta([item], content='serie')

    items = [e for e in item.get('episodes', []) if e['season'] == season]
    if not items:
        ui.infoDialog(_('No episodes'))
    else:
        for i in items:
            i['name'] = _('{season:2d}x{episode:02d} . {title}').format(
                season=int(i['season']),
                episode=int(i['episode']),
                title=i['title'])
            i['action'] = addon.itemaction('sources.dialog',
                                           name=i['name'],
                                           content='episode',
                                           imdb=i['imdb'],
                                           meta='@META@')

    uid.addcontentitems(items, content='episodes')


@busyaction
def watched(imdb, season, episode):
    dbs.watched('episode{imdb_id}{season}{episode}', True,
                imdb_id=imdb, season=season, episode=episode)
    ui.refresh()


@busyaction
def unwatched(imdb, season, episode):
    dbs.watched('episode{imdb_id}{season}{episode}', False,
                imdb_id=imdb, season=season, episode=episode)
    ui.refresh()
