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


import json
import urllib

from g2.libraries import ui
from g2.libraries import log
from g2.libraries import addon
from g2.libraries.language import _

from g2 import dbs

from .lib import uid
from . import action


@action
def menu():
    uid.additem(_('Search by Title'), 'tvshows.searchbytitle', 'tvSearch', 'DefaultTVShows.png', isFolder=False)
    uid.finish()


@action
def searchbytitle():
    query = ui.keyboard(_('Title to search'))
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
            i['name'] = '%s (%s)'%(i['title'], i['year']) if i.get('year') else i['title']
            i['action'] = addon.itemaction('tvshows.seasons', tvdb=i['tvdb'], imdb=i['imdb'])
            i['next_action'] = 'tvshows.serieslist'
            # Deleting all this info otherwise the Kodi listitem chokes! :)
            for info in ['seasons', 'episodes']:
                try:
                    del i[info]
                except Exception:
                    pass

    uid.addcontentitems(items, content='tvshows')


@action
def seasons(tvdb, imdb):
    item = {
        'tvdb': tvdb,
        'imdb': imdb,
    }
    dbs.meta([item], content='serie')

    items = item['seasons']
    if not items:
        ui.infoDialog(_('No seasons'))
    else:
        for i in items:
            i['name'] = _('Season {season} ({year})').format(season=i['season'], year=i['premiered'][0:4])
            i['action'] = addon.itemaction('tvshows.episodes', tvdb=i['tvdb'], imdb=i['imdb'], season=i['season'])

    uid.addcontentitems(items, content='seasons')


@action
def episodes(tvdb, imdb, season):
    item = {
        'tvdb': tvdb,
        'imdb': imdb,
    }
    dbs.meta([item], content='serie')

    items = [e for e in item['episodes'] if e['season'] == season]
    if not items:
        ui.infoDialog(_('No episodes'))
    else:
        for i in items:
            meta = dict((k, v) for k, v in i.iteritems() if not v == '0')
            i['name'] = i['title']
            i['action'] = addon.itemaction('sources.dialog',
                                           name='season . episode . title', # xxx
                                           content='episode',
                                           imdb=i['imdb'],
                                           meta=urllib.quote_plus(json.dumps(meta)))

    uid.addcontentitems(items, content='episodes')