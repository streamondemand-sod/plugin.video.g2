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
import urllib
import datetime

from g2.libraries import log
from g2.libraries import client
from g2.libraries import workers
from g2.libraries import addon

from g2 import defs


info = {
    'domains': ['api.themoviedb.org'],
    'methods': ['resolve', 'movies', 'meta', 'persons', 'genres', 'certifications'],
}

_INFO_LANG = addon.setting('infoLang') or 'en'
_TMDB_APIKEY = addon.setting('tmdb_apikey') or defs.TMDB_APIKEY
_TMDB_IMAGE = 'http://image.tmdb.org/t/p/original/'
_TMDB_POSTER = 'http://image.tmdb.org/t/p/w500/'

_BASE_URL = 'http://api.themoviedb.org/3'
_COMMON_PARAMS = '&api_key=@APIKEY@&language={info_lang}&include_adult={include_adult}'
_URLS = {
    'movies{title}': '/search/movie?query={title}|168',
    'movies{year}': '/discover/movie?year={year}|168',
    'movies{person_id}': '/discover/movie?sort_by=primary_release_date.desc&with_people={person_id}|168',
    'movies{genre_id}': '/discover/movie?with_genres={genre_id}|168',
    'movies{certification}': '/discover/movie?certification={certification}&certification_country=US|168',
    'movies{title}{year}': '/search/movie?query={title}&year={year}|24',
    'movie_meta{tmdb_id}': '/movie/{tmdb_id}?append_to_response=credits,releases|168',
    'movie_meta{imdb_id}': '/movie/{imdb_id}?append_to_response=credits,releases|168',
    'persons{name}': '/search/person?query={name}|720',
    'movies_featured{}': ('/discover/movie?'
                          'primary_release_date.gte={one_year_ago}&primary_release_date.lte={two_months_ago}&'
                          'sort_by=primary_release_date.desc|720'),
    'movies_popular{}': '/movie/popular?|168',
    'movies_toprated{}': '/movie/top_rated?|168',
    'movies_theaters{}': '/movie/now_playing?|168',
    'genres{}': '/genre/movie/list?|720',
    'certifications{}': '/certification/movie/list?|720',
}


def resolve(kind=None, **kwargs):
    if not kind:
        return _URLS.keys()
    if kind not in _URLS or not _TMDB_APIKEY:
        return None

    for key, val in {
            'info_lang': _INFO_LANG,
            'include_adult': defs.TMDB_INCLUDE_ADULT,
            'one_year_ago': (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
            'two_months_ago': (datetime.datetime.now() - datetime.timedelta(days=60)).strftime('%Y-%m-%d'),
        }.iteritems():
        if key not in kwargs:
            kwargs[key] = val

    for key, val in kwargs.iteritems():
        kwargs[key] = urllib.quote_plus(str(val))

    url, timeout = _URLS[kind].split('|')[0:2]
    return _BASE_URL+(url+_COMMON_PARAMS).format(**kwargs)+'|'+timeout


def movies(url):
    url, timeout = url.split('|')[0:2]
    result = client.get(url.replace('@APIKEY@', _TMDB_APIKEY, 1)).json()
    results = result['results']

    log.debug('{m}.{f}: %s: %d movies', url.replace(_BASE_URL, ''), len(results))

    next_url, next_page, max_pages = _tmdb_next_item(url, timeout, result)

    items = []
    for i, item in enumerate(results):
        try:
            title = item['title']
            title = client.replaceHTMLCodes(title)
            title = title.encode('utf-8')

            year = item['release_date']
            year = re.compile(r'(\d{4})').findall(year)[-1]
            year = year.encode('utf-8')

            name = '%s (%s)' % (title, year)
            try:
                name = name.encode('utf-8')
            except Exception:
                pass

            tmdb = item['id']
            tmdb = re.sub('[^0-9]', '', str(tmdb))
            tmdb = tmdb.encode('utf-8')

            poster = item['poster_path']
            if poster:
                poster = '%s%s' % (_TMDB_POSTER, poster)
                poster = poster.encode('utf-8')

            fanart = item['backdrop_path']
            if not fanart:
                fanart = '0'
            if fanart != '0':
                fanart = '%s%s' % (_TMDB_IMAGE, fanart)
            fanart = fanart.encode('utf-8')

            premiered = item['release_date']
            try:
                premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
            except Exception:
                premiered = '0'
            premiered = premiered.encode('utf-8')

            rating = str(item['vote_average'])
            if not rating:
                rating = '0'
            rating = rating.encode('utf-8')

            votes = str(item['vote_count'])
            try:
                votes = str(format(int(votes), ',d'))
            except Exception:
                pass
            if not votes:
                votes = '0'
            votes = votes.encode('utf-8')

            plot = item['overview']
            if not plot:
                plot = '0'
            plot = client.replaceHTMLCodes(plot)
            plot = plot.encode('utf-8')

            tagline = re.compile(r'[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]
            try:
                tagline = tagline.encode('utf-8')
            except Exception:
                pass

            items.append({
                'title': title,
                'originaltitle': title,
                'year': year,
                'premiered': premiered,
                'studio': '0',
                'genre': '0',
                'duration': '0',
                'rating': rating,
                'votes': votes,
                'mpaa': '0',
                'director': '0',
                'writer': '0',
                'cast': '0',
                'plot': plot,
                'tagline': tagline,
                'name': name,
                'code': '0',
                'imdb': '0',
                'tmdb': tmdb,
                'tvdb': '0',
                'tvrage': '0',
                'poster': poster,
                'banner': '0',
                'fanart': fanart,
                'next_url': next_url,
                'next_page': next_page,
                'max_pages': max_pages,
            })
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', i, repr(ex))

    return items


def meta(metas):
    for i in range(0, len(metas), defs.MAX_CONCURRENT_THREADS):
        threads = [workers.Thread(_meta_worker, metas[j]) for j in range(i, min(len(metas), i+defs.MAX_CONCURRENT_THREADS))]
        dummy = [t.start() for t in threads]
        dummy = [t.join() for t in threads]


def _meta_worker(meta):
    url = meta['url'].split('|')[0]
    result = client.get(url.replace('@APIKEY@', _TMDB_APIKEY, 1), timeout=10).json()

    log.debug('{m}.{f}: %s: %s', url.replace(_BASE_URL, ''), result)

    item = {}

    # (fixme) really really repetitive code...
    title = result.get('title', '')
    title = client.replaceHTMLCodes(title)
    title = title.encode('utf-8')
    if title:
        item.update({'title': title})

    year = result.get('release_date', '')
    try:
        # Update the release date with the local release date if existing
        for localrel in result['releases']['countries']:
            if localrel['iso_3166_1'].lower() == _INFO_LANG:
                localyear = localrel.get('release_date')
                if localyear:
                    year = localyear
                    break
    except Exception:
        pass
    try:
        year = re.compile(r'(\d{4})').findall(year)[-1]
    except Exception:
        year = ''
    year = year.encode('utf-8')
    if year:
        item.update({'year': year})

    name = title if not year else '%s (%s)'%(title, year)
    try:
        name = name.encode('utf-8')
    except Exception:
        pass
    if name:
        item.update({'name': name})

    tmdb = result.get('id')
    if not tmdb:
        tmdb = '0'
    tmdb = re.sub('[^0-9]', '', str(tmdb))
    tmdb = tmdb.encode('utf-8')
    if tmdb != '0':
        item.update({'tmdb': tmdb})

    imdb = result.get('imdb_id')
    if not imdb:
        imdb = '0'
    if imdb != '0':
        imdb = 'tt%07d'%int(str(imdb).translate(None, 't'))
    imdb = imdb.encode('utf-8')
    if imdb != '0':
        item.update({'imdb': imdb, 'code': imdb})

    poster = result.get('poster_path')
    if not poster:
        poster = '0'
    if poster != '0':
        poster = '%s%s' % (_TMDB_POSTER, poster)
    poster = poster.encode('utf-8')
    if poster != '0':
        item.update({'poster': poster})

    fanart = result.get('backdrop_path')
    if not fanart:
        fanart = '0'
    if fanart != '0':
        fanart = '%s%s' % (_TMDB_IMAGE, fanart)
    fanart = fanart.encode('utf-8')
    if fanart != '0':
        item.update({'fanart': fanart})

    premiered = result.get('release_date')
    try:
        premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
    except Exception:
        premiered = '0'
    if not premiered:
        premiered = '0'
    premiered = premiered.encode('utf-8')
    if premiered != '0':
        item.update({'premiered': premiered})

    studio = result.get('production_companies')
    try:
        studio = [x['name'] for x in studio][0]
    except Exception:
        studio = '0'
    if not studio:
        studio = '0'
    studio = studio.encode('utf-8')
    if studio != '0':
        item.update({'studio': studio})

    genre = result.get('genres')
    try:
        genre = [x['name'] for x in genre]
    except Exception:
        genre = ''
    genre = '0' if not genre else ' / '.join(genre)
    genre = genre.encode('utf-8')
    if genre != '0':
        item.update({'genre': genre})

    duration = str(result.get('runtime', 0))
    if not duration:
        duration = '0'
    duration = duration.encode('utf-8')
    if duration != '0':
        item.update({'duration': duration})

    rating = str(result.get('vote_average', 0))
    if not rating:
        rating = '0'
    rating = rating.encode('utf-8')
    if rating != '0':
        item.update({'rating': rating})

    votes = str(result.get('vote_count', 0))
    try:
        votes = str(format(int(votes), ',d'))
    except Exception:
        pass
    if not votes:
        votes = '0'
    votes = votes.encode('utf-8')
    if votes != '0':
        item.update({'votes': votes})

    try:
        mpaa = result['releases']['countries']
        try:
            mpaa = [x for x in mpaa if not x['certification'] == '']
        except Exception:
            mpaa = '0'
        try:
            mpaa = ([x for x in mpaa if x['iso_3166_1'].encode('utf-8') == 'US'] +
                    [x for x in mpaa if x['iso_3166_1'].encode('utf-8') != 'US'])[0]['certification']
        except Exception:
            mpaa = '0'
        mpaa = mpaa.encode('utf-8')
    except Exception:
        mpaa = '0'
    if mpaa != '0':
        item.update({'mpaa': mpaa})

    try:
        director = result['credits']['crew']
        try:
            director = [x['name'] for x in director if x['job'].encode('utf-8') == 'Director']
        except Exception:
            director = ''
        director = '0' if not director else ' / '.join(director)
        director = director.encode('utf-8')
    except Exception:
        director = '0'
    if director != '0':
        item.update({'director': director})

    try:
        writer = result['credits']['crew']
        try:
            writer = [x['name'] for x in writer if x['job'].encode('utf-8') in ['Writer', 'Screenplay']]
        except Exception:
            writer = ''
        try:
            writer = [x for n, x in enumerate(writer) if x not in writer[:n]]
        except Exception:
            writer = ''
        writer = '0' if not writer else ' / '.join(writer)
        writer = writer.encode('utf-8')
    except Exception:
        writer = '0'
    if writer != '0':
        item.update({'writer': writer})

    try:
        cast = result['credits']['cast']
        try:
            cast = [(x['name'].encode('utf-8'), x['character'].encode('utf-8')) for x in cast]
        except Exception:
            cast = []
        if len(cast):
            item.update({'cast': cast})
    except Exception:
        pass

    plot = result.get('overview')
    if not plot:
        plot = '0'
    plot = plot.encode('utf-8')
    if plot != '0':
        item.update({'plot': plot})

    tagline = result.get('tagline')
    if not tagline and plot != '0':
        tagline = re.compile(r'[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]
    elif not tagline:
        tagline = '0'
    try:
        tagline = tagline.encode('utf-8')
    except Exception:
        pass
    if tagline != '0':
        item.update({'tagline': tagline})

    meta['item'] = item


def persons(url):
    url, timeout = url.split('|')[0:2]
    result = client.get(url.replace('@APIKEY@', _TMDB_APIKEY, 1)).json()
    results = result['results']

    log.debug('{m}.{f}: %s: %d persons', url.replace(_BASE_URL, ''), len(results))

    next_url, next_page, max_pages = _tmdb_next_item(url, timeout, result)

    items = []
    for item in results:
        try:
            name = item['name']
            name = name.encode('utf-8')

            person_id = str(item['id'])
            person_id = person_id.encode('utf-8')

            image = '%s%s' % (_TMDB_IMAGE, item['profile_path'])
            image = image.encode('utf-8')

            items.append({
                'name': name,
                'id': person_id,
                'image': image,
                'next_url': next_url,
                'next_page': next_page,
                'max_pages': max_pages,
            })
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', item, repr(ex))

    return items


def _tmdb_next_item(url, timeout, result):
    page = str(result['page'])
    total = str(result['total_pages'])
    if page == total:
        return ('', 0, 0)
    else:
        page = int(page) + 1
        next_url = '%s&page=%s%s' % (url.split('&page=', 1)[0], page, '' if not timeout else '|'+timeout)
        return (next_url.encode('utf-8'), page, total)


def genres(url):
    url = url.split('|')[0]
    # For some reason, Finnish, Croatians and Norvegians doesn't like the traslated genre names
    url = re.sub('language=(fi|hr|no)', '', url)
    result = client.get(url.replace('@APIKEY@', _TMDB_APIKEY, 1)).json()
    results = result['genres']

    log.debug('{m}.{f}: %d genres', len(results))

    items = []
    for item in results:
        try:
            name = item['name']
            name = name.encode('utf-8')

            genre_id = str(item['id'])
            genre_id = genre_id.encode('utf-8')

            items.append({
                'name': name,
                'id': genre_id,
                # (fixme) it would be nice to have an icon per genre
                'image': 'movieGenres.jpg',
            })
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', item, repr(ex))

    return items


def certifications(url, country):
    url = url.split('|')[0]
    result = client.get(url.replace('@APIKEY@', _TMDB_APIKEY, 1)).json()
    results = result['certifications'][country]

    log.debug('{m}{f}: %s: %d certifications', country, len(results))

    items = []
    for item in results:
        try:
            name = item['certification']
            name = name.encode('utf-8')

            meaning = item['meaning']
            meaning = meaning.encode('utf-8')

            order = item['order']

            items.append({
                'name': name,
                'meaning': meaning,
                'order': order,
                # (fixme) it would be nice to have an icon per certification type:
                'image': 'movieCertificates.jpg',
            })
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', item, repr(ex))

    return items
