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
import urllib

from g2.libraries import ui
from g2.libraries import addon
from g2.libraries.language import _

from g2 import dbs

from .lib import uid
from . import action, busyaction


@action
def menu():
    if dbs.resolve('movies_recently_added{}'):
        db_provider = dbs.resolve('movies_recently_added{}', return_db_provider=True)
        uid.additem(_('Latest Movies')+' ['+db_provider.upper()+']',
                    'movies.movielist&url='+dbs.resolve('movies_recently_added{}', quote_plus=True),
                    'moviesAdded', 'DefaultRecentlyAddedMovies.png')

    uid.additem(_('Search by Title'), 'movies.searchbytitle', 'movieSearch', 'DefaultMovies.png', isFolder=False)
    uid.additem(_('Search by Person'), 'movies.searchbyperson', 'moviePerson', 'DefaultMovies.png', isFolder=False)
    uid.additem(_('Search by Year'), 'movies.searchbyyear', 'movieYears', 'DefaultYear.png', isFolder=False)

    uid.additem(_('Genres'), 'movies.genres', 'movieGenres', 'DefaultGenre.png')
    uid.additem(_('Certificates'), 'movies.certifications', 'movieCertificates', 'DefaultMovies.png')

    if dbs.resolve('movies_featured{}'):
        uid.additem(_('Featured'), 'movies.movielist&url='+dbs.resolve('movies_featured{}', quote_plus=True),
                    'movies', 'DefaultRecentlyAddedMovies.png')
    if dbs.resolve('movies_trending{}'):
        uid.additem(_('People Watching'), 'movies.movielist&url='+dbs.resolve('movies_trending{}', quote_plus=True),
                    'moviesTrending', 'DefaultRecentlyAddedMovies.png')
    if dbs.resolve('movies_popular{}'):
        uid.additem(_('Most Popular'), 'movies.movielist&url='+dbs.resolve('movies_popular{}', quote_plus=True),
                    'moviesPopular', 'DefaultMovies.png')
    if dbs.resolve('movies_toprated{}'):
        uid.additem(_('Most Voted'), 'movies.movielist&url='+dbs.resolve('movies_toprated{}', quote_plus=True),
                    'moviesViews', 'DefaultMovies.png')
    if dbs.resolve('movies_boxoffice{}'):
        uid.additem(_('Box Office'), 'movies.movielist&url='+dbs.resolve('movies_boxoffice{}', quote_plus=True),
                    'moviesBoxoffice', 'DefaultMovies.png')
    if dbs.resolve('movies_oscar{}'):
        uid.additem(_('Oscar Winners'), 'movies.movielist&url='+dbs.resolve('movies_oscar{}', quote_plus=True),
                    'moviesOscars', 'DefaultMovies.png')
    if dbs.resolve('movies_theaters{}'):
        uid.additem(_('In Theaters'), 'movies.movielist&url='+dbs.resolve('movies_theaters{}', quote_plus=True),
                    'moviesTheaters', 'DefaultRecentlyAddedMovies.png')
    uid.finish()


@action
def searchbytitle():
    query = ui.keyboard(_('Movie search'))
    if query:
        url = dbs.resolve('movies{title}', title=query, quote_plus=True)
        ui.refresh('movies.movielist', url=url)


@action
def searchbyperson():
    query = ui.keyboard(_('Person search'))
    if query:
        url = dbs.resolve('persons{name}', name=query, quote_plus=True)
        ui.refresh('movies.personlist', url=url)


@action
def searchbyyear():
    query = ui.keyboard(_('Year search'))
    if query:
        url = dbs.resolve('movies{year}', year=query, quote_plus=True)
        ui.refresh('movies.movielist', url=url)


@action
def genres():
    items = dbs.genres()
    for i in items:
        image = i.get('image', '0')
        if image == '0':
            # (fixme) Need a table mapping genre 'id' to different icons
            image = 'DefaultGenre.png'
        i.update({
            'action': 'movies.movielist',
            'url': dbs.resolve('movies{genre_id}', genre_id=i['id']),
            'image': image,
        })
    # (fixme) Use addcontentitems(..., content='genres')
    uid.additems(items)


@action
def certifications():
    items = dbs.certifications()
    items = sorted(items, key=lambda c: c['order'])

    for i in items:
        image = i.get('image', '0')
        if image == '0':
            image = 'movieCertificates.jpg'
        i.update({
            'action': 'movies.movielist',
            'url': dbs.resolve('movies{certification}', certification=i['name']),
            'image': image,
        })
    uid.additems(items)


@action
def movielist(url):
    items = dbs.movies(url)
    if not items:
        ui.infoDialog(_('No results'))
    else:
        for i in items:
            meta = dict((k, v) for k, v in i.iteritems() if v and v != '0')
            # Movie directory item label when the year is kwnon
            i['name'] = _('{title} ({year})').format(
                title=i['title'],
                year=i['year']) if i.get('year') else i['title']
            i['action'] = addon.itemaction('sources.dialog',
                                           name=urllib.quote_plus(i['name']),
                                           content='movie',
                                           imdb=i['imdb'],
                                           meta=urllib.quote_plus(json.dumps(meta)))
            i['next_action'] = 'movies.movielist'
        dbs.meta(items)
    uid.addcontentitems(items, content='movies')


@action
def personlist(url):
    items = dbs.persons(url)
    if not items:
        ui.infoDialog(_('No results'))
    else:
        for i in items:
            i.update({
                'action': 'movies.movielist',
                'url': dbs.resolve('movies{person_id}', person_id=i['id']),
                'next_action': 'movies.personlist',
            })
    uid.additems(items, is_person=True)


@action
def lists(kind_user_id='trakt_user_id', kind_list_id='trakt_list_id', user_id=''):
    args = {kind_user_id: user_id}
    items = dbs.lists('lists{%s}'%kind_user_id, **args)
    if not items:
        items = []
    addon_userlists = ui.media('movieUserlists', 'DefaultVideoPlaylists.png')
    for i in items:
        args[kind_list_id] = i[kind_list_id]
        image = i.get('image', '0')
        if image == '0':
            image = addon_userlists
        poster = i.get('poster')
        if poster == '0':
            poster = addon_userlists
        i.update({
            'action': 'movies.movielist',
            'url': dbs.resolve('movies{%s}{%s}'%(kind_user_id, kind_list_id), **args),
            'image': image,
            'poster': poster,
        })
    if not items:
        ui.infoDialog(_('No results'))
    uid.additems(items, show_genre_as='genre')


@busyaction
def watched(imdb):
    dbs.watched('movie{imdb_id}', True, imdb_id=imdb)
    ui.refresh()


@busyaction
def unwatched(imdb):
    dbs.watched('movie{imdb_id}', False, imdb_id=imdb)
    ui.refresh()
