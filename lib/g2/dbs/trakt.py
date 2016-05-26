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
import time
import base64
import urllib
import urlparse

from g2.libraries import log
from g2.libraries import cache
from g2.libraries import client
from g2.libraries import platform


# _log_debug = True
_log_trace_on_error = True


"""
    When adding a DBS method please include its name in info['methods']!!!
"""
info = {
    'domains': ['api-v2launch.trakt.tv'],
    'methods': ['url', 'movies', 'lists', 'watched'],
}


_trakt_base = 'https://api-v2launch.trakt.tv'
_urls = {
    'lists{trakt_user_id}': _trakt_base+'/users/{trakt_user_id}/lists',
    'movies{trakt_user_id}{trakt_list_id}': _trakt_base+'/users/{trakt_user_id}/lists/{trakt_list_id}/items',
    'movies_collection{trakt_user_id}': _trakt_base+'/users/{trakt_user_id}/collection/movies',
    'movies_watchlist{trakt_user_id}': _trakt_base+'/users/{trakt_user_id}/watchlist/movies',
    'movies_ratings{trakt_user_id}': _trakt_base+'/users/{trakt_user_id}/ratings/movies',
    'movies_trending{}': _trakt_base+'/movies/trending?limit=20',
    'movies_recommendations{}': _trakt_base+'/recommendations/movies?limit=20',
    'watched.movie{imdb_id}': 'movie.imdb.{imdb_id}',
}

_trakt_user = platform.setting('trakt_user') 
_trakt_client_id = 'c67fa3018aa2867c183261f4b2bb12ebb606c2b3fbb1449e24f2fbdbc3a8ffdb'
_common_post_vars = {
    'client_id': _trakt_client_id,
    'client_secret': '9899db3e81158f6ebbb7b5afbce043b99caa13fba98c527c00c44ca44eca72c5',
    'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
}

_common_headers = {
    'Content-Type': 'application/json',
    'trakt-api-key': _trakt_client_id,
    'trakt-api-version': '2',
}


def url(kind=None, **kwargs):
    if not kind: return _urls.keys()
    if kind not in _urls: return None

    for k, v in kwargs.iteritems():
        kwargs[k] = urllib.quote_plus(str(v))

    return _urls[kind].format(**kwargs)


# (fixme) abort the calls if trakt_enabled is false!
def movies(url):
    try:
        q = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
        q.update({'extended': 'full,images'})
        q = (urllib.urlencode(q)).replace('%2C', ',')
        u = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + q

        result = _get_trakt(u)
        if not result: raise Exception('_get_trakt(%s) failed'%u)
        result = json.loads(result)

        results = []
        for i in result:
            if 'movie' in i:
                item = i['movie']
                if 'rating' in i:
                    item['rating'] = i['rating']
                results.append(item)
        if not results:
            results = result
        log.debug('trackt.movies(%s): %s'%(url, results))
    except Exception as e:
        log.notice('trackt.movies(%s): %s'%(url, e))
        return None

    try:
        q = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
        p = str(int(q['page']) + 1)
        if p == '5': raise Exception()
        q.update({'page': p})
        q = (urllib.urlencode(q)).replace('%2C', ',')
        next_url = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + q
        next_url = next_url.encode('utf-8')
        next_page = int(p)
    except:
        next_url = ''
        next_page = 0

    items = []
    for item in results:
        try:
            title = item['title']
            title = client.replaceHTMLCodes(title)
            title = title.encode('utf-8')

            year = item['year']
            year = re.sub('[^0-9]', '', str(year))
            year = year.encode('utf-8')

            name = '%s (%s)' % (title, year)
            try: name = name.encode('utf-8')
            except: pass

            tmdb = item['ids']['tmdb']
            if tmdb == None or tmdb == '': tmdb = '0'
            tmdb = re.sub('[^0-9]', '', str(tmdb))
            tmdb = tmdb.encode('utf-8')

            imdb = item['ids']['imdb']
            if imdb == None or imdb == '': raise Exception()
            imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
            imdb = imdb.encode('utf-8')

            poster = '0'
            try: poster = item['images']['poster']['medium']
            except: pass
            if poster == None or not '/posters/' in poster: poster = '0'
            poster = poster.rsplit('?', 1)[0]
            poster = poster.encode('utf-8')

            banner = poster
            try: banner = item['images']['banner']['full']
            except: pass
            if banner == None or not '/banners/' in banner: banner = '0'
            banner = banner.rsplit('?', 1)[0]
            banner = banner.encode('utf-8')

            fanart = '0'
            try: fanart = item['images']['fanart']['full']
            except: pass
            if fanart == None or not '/fanarts/' in fanart: fanart = '0'
            fanart = fanart.rsplit('?', 1)[0]
            fanart = fanart.encode('utf-8')

            premiered = item['released']
            try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
            except: premiered = '0'
            premiered = premiered.encode('utf-8')

            genre = item['genres']
            genre = [i.title() for i in genre]
            if genre == []: genre = '0'
            genre = ' / '.join(genre)
            genre = genre.encode('utf-8')

            try: duration = str(item['runtime'])
            except: duration = '0'
            if duration == None: duration = '0'
            duration = duration.encode('utf-8')

            try: rating = str(item['rating'])
            except: rating = '0'
            if rating == None or rating == '0.0': rating = '0'
            rating = rating.encode('utf-8')

            try: votes = str(item['votes'])
            except: votes = '0'
            try: votes = str(format(int(votes),',d'))
            except: pass
            if votes == None: votes = '0'
            votes = votes.encode('utf-8')

            mpaa = item['certification']
            if mpaa == None: mpaa = '0'
            mpaa = mpaa.encode('utf-8')

            plot = item['overview']
            if plot == None: plot = '0'
            plot = client.replaceHTMLCodes(plot)
            plot = plot.encode('utf-8')

            try: tagline = item['tagline']
            except: tagline = None
            if tagline == None and not plot == '0': tagline = re.compile('[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]
            elif tagline == None: tagline = '0'
            tagline = client.replaceHTMLCodes(tagline)
            try: tagline = tagline.encode('utf-8')
            except: pass

            items.append({
                'title': title,
                'originaltitle': title,
                'year': year,
                'premiered': premiered,
                'studio': '0',
                'genre': genre,
                'duration': duration,
                'rating': rating,
                'votes': votes,
                'mpaa': mpaa,
                'director': '0',
                'writer': '0',
                'cast': '0',
                'plot': plot,
                'tagline': tagline,
                'name': name,
                'code': imdb,
                'imdb': imdb,
                'tmdb': tmdb,
                'tvdb': '0',
                'tvrage': '0',
                'poster': poster,
                'banner': banner,
                'fanart': fanart,
                'next_url': next_url,
                'next_page': next_page,
            })
        except:
            import traceback
            log.notice(traceback.format_exc())

    return items


def lists(url):
    try:
        result = _get_trakt(url)
        results = json.loads(result)
        log.debug('trakt.lists(%s): %d lists'%(url, len(results)))
    except Exception as e:
        log.notice('trakt.lists(%s): %s'%(url, e))
        return None

    items = []
    for item in results:
        try:
            name = item['name']
            name = client.replaceHTMLCodes(name)
            name = name.encode('utf-8')

            listid = item['ids']['slug']
            listid = listid.encode('utf-8')

            items.append({
                'name': name,
                'trakt_list_id': listid,
                'image': 'movieUserlists.jpg',
            })
        except:
            pass

    return items


def watched(kind, seen=None, **kwargs):
    url_ = url(kind, **kwargs)
    log.debug('trakt.watched: url(%s, %s)=%s'%(kind, kwargs, url_))
    if not url_:
        return None

    content, id_type, id_value = url_.split('.')
    if seen is None:
        indicators = _sync_movies(timeout=720)
        indicators = json.loads(indicators)
        log.debug('trakt.watched: getSymcMovies()=%s'%indicators)
        return True if len([i for i in indicators if str(i[content]['ids'][id_type]) == id_value]) else None
    else:
        log.debug('trakt.watched: getTrackt(seen=%s, %s, %s=%s)'%(seen, content+'s', id_type, id_value))
        r = _get_trakt('/sync/history' if seen else '/sync/history/remove', {content+'s': [{'ids': {id_type: id_value}}]})
        _sync_movies() # Update the local cache
        log.debug('trakt.watched: getTrackt(seen=%s, %s, %s=%s)=%s'%(seen, content+'s', id_type, id_value, r))
        return None # Give a change to the other backends to store the flag too!


def authDevice(ui_update):
    try:
        phase = 'code generation'
        result = client.request(urlparse.urljoin(_trakt_base, '/oauth/device/code'), post=json.dumps(_common_post_vars), headers=_common_headers, debug=True)
        result = json.loads(result)

        code = result['user_code']
        url = result['verification_url']
        device_code = result['device_code']
        expires_in = result['expires_in']
        interval = result['interval']

        post = _common_post_vars
        post.update({
            'code': str(device_code),
        })

        phase = 'device authorization'
        start_time = time.time()
        next_check_at = start_time + interval
        while time.time()-start_time < expires_in:
            if not ui_update(code, url, time.time()-start_time, expires_in):
                raise Exception('user aborted')
            if time.time() < next_check_at:
                continue

            result = client.request(urlparse.urljoin(_trakt_base, '/oauth/device/token'), post=json.dumps(post), headers=_common_headers, output='response', error=True, debug=True)
            next_check_at = time.time() + interval

            if 'HTTP Error 400' in result[0] or 'HTTP Error 429' in result[0]:
                pass

            elif 'HTTP Error' in result[0]:
                raise Exception(result[0])

            else:
                result = json.loads(result[1])
                platform.setSetting('trakt.token', str(result['access_token']))
                platform.setSetting('trakt.refresh', str(result['refresh_token']))
                return _trakt_fetch_user()

        raise Exception('auhorization code expired')

    except Exception as e:
        log.error('trakt.authDevice: %s: %s'%(phase, e))
        raise Exception('%s %s'%('Failed', phase))


def _sync_movies(timeout=0):
    try:
        return cache.get(_get_trakt, timeout, '/users/%s/watched/movies'%_trakt_user, table='rel_trakt')
    except:
        pass


def _get_trakt(url, post=None):
    try:
        if not post == None: post = json.dumps(post)

        url = urlparse.urljoin(_trakt_base, url)

        if not _trakt_user:
            return client.request(url, post=post, headers=_common_headers)

        token = platform.setting('trakt.token')
        refresh_token = platform.setting('trakt.refresh')
        if not token: return None

        _common_headers['Authorization'] = 'Bearer %s' % token

        result = client.request(url, post=post, headers=_common_headers, output='response', error=True)
        if 'HTTP Error 401' not in result[0] and 'HTTP Error 405' not in result[0]:
            return result[1]

        oauth = urlparse.urljoin(_trakt_base, '/oauth/token')
        opost = _common_post_vars
        opost.update({
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        })

        result = client.request(oauth, post=json.dumps(opost), headers=_common_headers)
        if not result: raise Exception('failure to refresh the token')
        result = json.loads(result)

        token = str(result['access_token'])
        refresh = str(result['refresh_token'])

        platform.setSetting('trakt.token', token)
        platform.setSetting('trakt.refresh', refresh)

        _common_headers['Authorization'] = 'Bearer %s' % token

        return client.request(url, post=post, headers=_common_headers)
    except Exception as e:
        log.error('_get_trakt(%s): %s'%(url, e))


def _trakt_fetch_user():
    token = platform.setting('trakt.token')
    if not token: return None

    _common_headers['Authorization'] = 'Bearer %s' % token

    result = client.request(urlparse.urljoin(_trakt_base, '/users/me'), headers=_common_headers, debug=True)
    if not result: return None
    result = json.loads(result)

    return result.get('username')
