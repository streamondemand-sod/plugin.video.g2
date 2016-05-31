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
import urllib
import datetime

from g2.libraries import log
from g2.libraries import client
from g2.libraries import workers
from g2.libraries import platform


info = {
    'domains': ['api.themoviedb.org'],
    'methods': ['url', 'movies', 'metas', 'persons', 'genres', 'certifications'],
}


_info_lang = platform.setting('infoLang') or 'en'
_include_adult = 'false'

# TODO[port]: make this a configuration parameter or platform dependent (eg. raspberry xbmc)
_max_concurrent_threads = 10

# TODO[user]: extract the TMDB key from the official package "metadata.common.themoviedb.org"
_tmdb_key = 'f7f51775877e0bb6703520952b3c7840'
_tmdb_image = 'http://image.tmdb.org/t/p/original'
_tmdb_poster = 'http://image.tmdb.org/t/p/w500'
_tmdb_list_genres = 'http://api.themoviedb.org/3/genre/movie/list?api_key=@API_KEY@&language='+_info_lang
_tmdb_list_certifications = 'http://api.themoviedb.org/3/certification/movie/list?api_key=@API_KEY@'

_urls = {
    'movies{title}': 'http://api.themoviedb.org/3/search/movie?api_key=@API_KEY@&language={info_lang}&include_adult={include_adult}&query={title}',
    'movies{year}': 'http://api.themoviedb.org/3/discover/movie?api_key=@API_KEY@&language={info_lang}&include_adult={include_adult}&year={year}',
    'movies{person_id}': 'http://api.themoviedb.org/3/discover/movie?api_key=@API_KEY@&language={info_lang}&include_adult={include_adult}&sort_by=primary_release_date.desc&with_people={person_id}',
    'movies{genre_id}': 'http://api.themoviedb.org/3/discover/movie?api_key=@API_KEY@&language={info_lang}&include_adult={include_adult}&with_genres={genre_id}',
    'movies{certification}': 'http://api.themoviedb.org/3/discover/movie?api_key=@API_KEY@&language={info_lang}&include_adult={include_adult}&certification={certification}&certification_country=US',
    'movies{title}{year}': 'http://api.themoviedb.org/3/search/movie?api_key=@API_KEY@&language={info_lang}&query={title}&year={year}&include_adult={include_adult}',
    'movie_meta{tmdb_id}': 'http://api.themoviedb.org/3/movie/{tmdb_id}?api_key=@API_KEY@&language={info_lang}&append_to_response=credits,releases',
    'movie_meta{imdb_id}': 'http://api.themoviedb.org/3/movie/{imdb_id}?api_key=@API_KEY@&language={info_lang}&append_to_response=credits,releases',
    'persons{name}': 'http://api.themoviedb.org/3/search/person?api_key=@API_KEY@&query={name}',
    'movies_featured{}': 'http://api.themoviedb.org/3/discover/movie?api_key=@API_KEY@&language={info_lang}&primary_release_date.gte={one_year_ago}&primary_release_date.lte={two_months_ago}&sort_by=primary_release_date.desc',
    'movies_popular{}': 'http://api.themoviedb.org/3/movie/popular?api_key=@API_KEY@&language={info_lang}',
    'movies_toprated{}': 'http://api.themoviedb.org/3/movie/top_rated?api_key=@API_KEY@&language={info_lang}',
    'movies_theaters{}': 'http://api.themoviedb.org/3/movie/now_playing?api_key=@API_KEY@&language={info_lang}',
}


def url(kind=None, **kwargs):
    if not kind: return _urls.keys()
    if kind not in _urls: return None

    for k, v in {
        'info_lang': _info_lang,
        'include_adult': _include_adult,
        'one_year_ago': (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
        'two_months_ago': (datetime.datetime.now() - datetime.timedelta(days=60)).strftime('%Y-%m-%d'),
    }.iteritems():
        if k not in kwargs: kwargs[k] = v

    for k, v in kwargs.iteritems():
        kwargs[k] = urllib.quote_plus(str(v))

    return _urls[kind].format(**kwargs)


def movies(url):
    try:
        result = client.request(url.replace('@API_KEY@', _tmdb_key, 1))
        result = json.loads(result)
        results = result['results']
        log.debug('tmdb.movies(%s): %s'%(url, results))
    except Exception as e:
        log.notice('tmdb.movies(%s): %s'%(url, e))
        return None

    next_url, next_page = _tmdb_next_item(url, result)

    items = []
    for i, item in enumerate(results):
        try:
            title = item['title']
            title = client.replaceHTMLCodes(title)
            title = title.encode('utf-8')

            year = item['release_date']
            year = re.compile('(\d{4})').findall(year)[-1]
            year = year.encode('utf-8')

            name = '%s (%s)' % (title, year)
            try: name = name.encode('utf-8')
            except: pass

            tmdb = item['id']
            tmdb = re.sub('[^0-9]', '', str(tmdb))
            tmdb = tmdb.encode('utf-8')

            poster = item['poster_path']
            if poster:
                poster = '%s%s' % (_tmdb_poster, poster)
                poster = poster.encode('utf-8')

            fanart = item['backdrop_path']
            if fanart == '' or fanart == None: fanart = '0'
            if not fanart == '0': fanart = '%s%s' % (_tmdb_image, fanart)
            fanart = fanart.encode('utf-8')

            premiered = item['release_date']
            try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
            except: premiered = '0'
            premiered = premiered.encode('utf-8')

            rating = str(item['vote_average'])
            if rating == '' or rating == None: rating = '0'
            rating = rating.encode('utf-8')

            votes = str(item['vote_count'])
            try: votes = str(format(int(votes),',d'))
            except: pass
            if votes == '' or votes == None: votes = '0'
            votes = votes.encode('utf-8')

            plot = item['overview']
            if plot == '' or plot == None: plot = '0'
            plot = client.replaceHTMLCodes(plot)
            plot = plot.encode('utf-8')

            tagline = re.compile('[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]
            try: tagline = tagline.encode('utf-8')
            except: pass

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
            })
        except Exception as e:
            log.debug('tmdb.movies(%s): item %d: FAILED (%s)'%(url, i, e))
            pass

    return items


def metas(metas):
    for r in range(0, len(metas), _max_concurrent_threads):
        threads = [workers.Thread(_meta_worker, metas[i]) for i in range(r, min(len(metas), r+_max_concurrent_threads))]
        [t.start() for t in threads]
        [t.join() for t in threads]


def _meta_worker(meta):
    try:
        url = meta['url']
        response = client.request(url.replace('@API_KEY@', _tmdb_key, 1), error=True, output='response', timeout='10')
        if 'HTTP Error' in response[0]: raise Exception(response[0])
        result = json.loads(response[1])
        log.debug('tmdb.metas(%s): %s'%(url, result))
    except Exception as e:
        log.notice('tmdb.metas(%s): %s'%(url, e))
        return

    try:
        item = {}

        title = result['title']
        title = client.replaceHTMLCodes(title)
        title = title.encode('utf-8')
        if title: item.update({'title': title})

        year = result['release_date']
        year = re.compile('(\d{4})').findall(year)[-1]
        year = year.encode('utf-8')
        if year: item.update({'year': year})

        name = '%s (%s)' % (title, year)
        try: name = name.encode('utf-8')
        except: pass
        if name: item.update({'name': name})

        tmdb = result['id']
        if tmdb == '' or tmdb == None: tmdb = '0'
        tmdb = re.sub('[^0-9]', '', str(tmdb))
        tmdb = tmdb.encode('utf-8')
        if not tmdb == '0': item.update({'tmdb': tmdb})

        imdb = result['imdb_id']
        if imdb == '' or imdb == None: imdb = '0'
        if not imdb == '0': imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
        imdb = imdb.encode('utf-8')
        if not imdb == '0': item.update({'imdb': imdb, 'code': imdb})

        poster = result['poster_path']
        if poster == '' or poster == None: poster = '0'
        if not poster == '0': poster = '%s%s' % (_tmdb_poster, poster)
        poster = poster.encode('utf-8')
        if not poster == '0': item.update({'poster': poster})

        fanart = result['backdrop_path']
        if fanart == '' or fanart == None: fanart = '0'
        if not fanart == '0': fanart = '%s%s' % (_tmdb_image, fanart)
        fanart = fanart.encode('utf-8')
        if not fanart == '0': item.update({'fanart': fanart})

        premiered = result['release_date']
        try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
        except: premiered = '0'
        if premiered == '' or premiered == None: premiered = '0'
        premiered = premiered.encode('utf-8')
        if not premiered == '0': item.update({'premiered': premiered})

        studio = result['production_companies']
        try: studio = [x['name'] for x in studio][0]
        except: studio = '0'
        if studio == '' or studio == None: studio = '0'
        studio = studio.encode('utf-8')
        if not studio == '0': item.update({'studio': studio})

        genre = result['genres']
        try: genre = [x['name'] for x in genre]
        except: genre = '0'
        if genre == '' or genre == None or genre == []: genre = '0'
        genre = ' / '.join(genre)
        genre = genre.encode('utf-8')
        if not genre == '0': item.update({'genre': genre})

        try: duration = str(result['runtime'])
        except: duration = '0'
        if duration == '' or duration == None: duration = '0'
        duration = duration.encode('utf-8')
        if not duration == '0': item.update({'duration': duration})

        rating = str(result['vote_average'])
        if rating == '' or rating == None: rating = '0'
        rating = rating.encode('utf-8')
        if not rating == '0': item.update({'rating': rating})

        votes = str(result['vote_count'])
        try: votes = str(format(int(votes),',d'))
        except: pass
        if votes == '' or votes == None: votes = '0'
        votes = votes.encode('utf-8')
        if not votes == '0': item.update({'votes': votes})

        mpaa = result['releases']['countries']
        try: mpaa = [x for x in mpaa if not x['certification'] == '']
        except: mpaa = '0'
        try: mpaa = ([x for x in mpaa if x['iso_3166_1'].encode('utf-8') == 'US'] + [x for x in mpaa if not x['iso_3166_1'].encode('utf-8') == 'US'])[0]['certification']
        except: mpaa = '0'
        mpaa = mpaa.encode('utf-8')
        if not mpaa == '0': item.update({'mpaa': mpaa})

        director = result['credits']['crew']
        try: director = [x['name'] for x in director if x['job'].encode('utf-8') == 'Director']
        except: director = '0'
        if director == '' or director == None or director == []: director = '0'
        director = ' / '.join(director)
        director = director.encode('utf-8')
        if not director == '0': item.update({'director': director})

        writer = result['credits']['crew']
        try: writer = [x['name'] for x in writer if x['job'].encode('utf-8') in ['Writer', 'Screenplay']]
        except: writer = '0'
        try: writer = [x for n,x in enumerate(writer) if x not in writer[:n]]
        except: writer = '0'
        if writer == '' or writer == None or writer == []: writer = '0'
        writer = ' / '.join(writer)
        writer = writer.encode('utf-8')
        if not writer == '0': item.update({'writer': writer})

        cast = result['credits']['cast']
        try: cast = [(x['name'].encode('utf-8'), x['character'].encode('utf-8')) for x in cast]
        except: cast = []
        if len(cast) > 0: item.update({'cast': cast})

        plot = result['overview']
        if plot == '' or plot == None: plot = '0'
        plot = plot.encode('utf-8')
        if not plot == '0': item.update({'plot': plot})

        tagline = result['tagline']
        if (tagline == '' or tagline == None) and not plot == '0': tagline = re.compile('[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]
        elif tagline == '' or tagline == None: tagline = '0'
        try: tagline = tagline.encode('utf-8')
        except: pass
        if not tagline == '0': item.update({'tagline': tagline})

        meta['item'] = item
    except:
        import traceback
        log.notice(traceback.format_exc())


def persons(url):
    try:
        result = client.request(url.replace('@API_KEY@', _tmdb_key, 1))
        result = json.loads(result)
        results = result['results']
        log.debug('tmdb.persons(%s): %s'%(url, results))
    except Exception as e:
        log.notice('tmdb.persons(%s): %s'%(url, e))
        return None

    next_url, next_page = _tmdb_next_item(url, result)

    items = []
    for item in results:
        try:
            name = item['name']
            name = name.encode('utf-8')

            person_id = str(item['id'])
            person_id = person_id.encode('utf-8')

            image = '%s%s' % (_tmdb_image, item['profile_path'])
            image = image.encode('utf-8')

            items.append({
                'name': name,
                'id': person_id,
                'image': image,
                'next_url': next_url,
                'next_page': next_page,
            })
        except:
            import traceback
            log.notice(traceback.format_exc())
            pass

    return items


def _tmdb_next_item(url, result):
    page = str(result['page'])
    total = str(result['total_pages'])
    if page == total:
        return ('', 0)
    else:
        page = int(page) + 1
        next_url = '%s&page=%s' % (url.split('&page=', 1)[0], page)
        return (next_url.encode('utf-8'), page)


def genres():
    try:
        # For some reason, Finnish, Croatians and Norvegians doesn't like the traslated genre names
        url = re.sub('language=(fi|hr|no)', '', _tmdb_list_genres)
        result = client.request(url.replace('@API_KEY@', _tmdb_key, 1))
        result = json.loads(result)
        results = result['genres']
        log.debug('tmdb.genres(): %s'%results)
    except Exception as e:
        log.notice('tmdb.genres(): %s'%e)
        return None

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
                # TODO[look]: it would be nice to have an icon per genre
                'image': 'movieGenres.jpg',
            })
        except:
            pass

    return items


def certifications(country):
    try:
        result = client.request(_tmdb_list_certifications.replace('@API_KEY@', _tmdb_key, 1))
        result = json.loads(result)
        results = result['certifications'][country]
        log.debug('tmdb.certifications(%s): %s'%(country, results))
    except Exception as e:
        log.notice('tmdb.certifications(%s): %s'%(country, e))
        return None

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
                # TODO[look]: it would be nice to have an icon per certification type:
                # [https://en.wikipedia.org/wiki/Motion_Picture_Association_of_America_film_rating_system]
                'image': 'movieCertificates.jpg',
            })
        except:
            pass

    return items
