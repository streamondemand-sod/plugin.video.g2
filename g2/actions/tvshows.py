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


from g2.libraries import ui
from g2.libraries import addon
from g2.libraries.language import _

from g2 import dbs

from .lib import uid
from . import action, busyaction


@action
def menu():
    uid.additem(_('Search by Title'), 'tvshows.searchbytitle',
                'tvSearch', 'DefaultTVShows.png', isFolder=False)

    url = dbs.resolve('tvshows_trending{}', quote_plus=True)
    if url:
        uid.additem(_('People Watching'), 'tvshows.tvshowlist&url='+url,
                    'tvshowsTrending.jpg', 'DefaultRecentlyAddedEpisodes.png')

    url = dbs.resolve('tvshows_popular{}', quote_plus=True)
    if url:
        uid.additem(_('Most Popular'), 'tvshows.tvshowlist&url='+url,
                    'tvshowsPopular', 'DefaultTVShows.png')

    uid.finish()


@action
def searchbytitle():
    query = ui.keyboard(_('TV show search'))
    if query:
        url = dbs.resolve('tvshows{title}', title=query, quote_plus=True)
        ui.refresh('tvshows.tvshowlist', url=url)


@action
def tvshowlist(url):
    items = dbs.tvshows(url)
    if not items:
        ui.infoDialog(_('No results'))
    else:
        dbs.meta(items, content='tvshow')
        for i in items:
            i['name'] = uid.nameitem('tvshow', i)
            i['action'] = addon.itemaction('tvshows.seasons', tvdb=i['tvdb'], imdb=i['imdb'])
            i['next_action'] = 'tvshows.tvshowlist'

    uid.addcontentitems(items, content='tvshows')


@action
def seasons(tvdb, imdb):
    item = {
        'tvdb': tvdb,
        'imdb': imdb,
    }
    dbs.meta([item], content='tvshow_seasons')

    items = item.get('seasons', [])
    if not items:
        ui.infoDialog(_('No seasons'))
    else:
        for i in items:
            i['name'] = uid.nameitem('season', i)
            i['action'] = addon.itemaction('tvshows.episodes', tvdb=i['tvdb'], imdb=i['imdb'], season=i['season'])

    uid.addcontentitems(items, content='seasons')


@action
def episodes(tvdb, imdb, season):
    item = {
        'tvdb': tvdb,
        'imdb': imdb,
    }
    dbs.meta([item], content='tvshow_episodes')

    items = [e for e in item.get('episodes', []) if e['season'] == season]
    if not items:
        ui.infoDialog(_('No episodes'))
    else:
        for i in items:
            i['name'] = uid.nameitem('episode', i)
            i['action'] = addon.itemaction('sources.dialog',
                                           name=i['name'],
                                           content='episode',
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
