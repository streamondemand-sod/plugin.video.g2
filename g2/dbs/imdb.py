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
import urlparse

from g2.libraries import log
from g2.libraries import client


info = {
    'domains': ['www.imdb.com'],
    'methods': ['resolve', 'movies', 'lists'],
}


_IMDB_PAGE_COUNT = 20

_BASE_URL = 'http://www.imdb.com'
_URLS = {
    'lists{imdb_user_id}': '/user/{imdb_user_id}/lists|168',
    'movies{imdb_user_id}{imdb_list_id}': ('/list/{imdb_list_id}/?view=detail&sort=title:asc&'
                                           'title_type=feature,short,tv_movie,tv_special,video,documentary,game&start=1|168'),
    'movies_boxoffice{}': ('/search/title?title_type=feature,tv_movie&sort=boxoffice_gross_us,desc&count=%d|168'%
                           _IMDB_PAGE_COUNT),
    'movies_oscar{}': ('/search/title?title_type=feature,tv_movie&groups=oscar_best_picture_winners&'
                       'sort=year,desc&count=%d|720'%
                       _IMDB_PAGE_COUNT),
}


def resolve(kind=None, **kwargs):
    if not kind:
        return _URLS.keys()
    if kind not in _URLS:
        return None

    for key, val in kwargs.iteritems():
        kwargs[key] = urllib.quote_plus(str(val))

    return _BASE_URL+_URLS[kind].format(**kwargs)


def movies(url):
    result = client.get(url).content
    result = result.decode('iso-8859-1').encode('utf-8')
    results = client.parseDOM(result, 'tr', attrs={'class': '.+?'})
    results += client.parseDOM(result, 'div', attrs={'class': 'list_item.+?'})

    log.debug('{m}.{f}: %s: %d movies', url.replace(_BASE_URL, ''), len(results))

    max_pages = 0
    try:
        try:
            max_pages = client.parseDOM(result, 'div', attrs={'id': 'left'})[0]
            max_pages = int(re.search(r'of (\d+)', max_pages).group(1)/_IMDB_PAGE_COUNT+.5)
        except Exception:
            max_pages = 0
        next_url = client.parseDOM(result, 'span', attrs={'class': 'pagination'})[0]
        next_url = client.parseDOM(next_url, 'a', ret='href')[-1]
        next_url = url.replace(urlparse.urlparse(url).query, urlparse.urlparse(next_url).query)
        next_url = client.replaceHTMLCodes(next_url)
        next_url = next_url.encode('utf-8')
        next_page = (int(re.search(r'&start=(\d+)', next_url).group(1))-1)/_IMDB_PAGE_COUNT + 1
        if next_page > max_pages:
            raise Exception('last page reached')
    except Exception:
        next_url = ''
        next_page = 0

    log.debug('{m}.{f}: %s: next_url=%s, next_page=%s, max_pages=%s',
              url.replace(_BASE_URL, ''), next_url.replace(_BASE_URL, ''), next_page, max_pages)

    items = []
    for item in results:
        try:
            try: title = client.parseDOM(item, 'a')[1]
            except: pass
            try: title = client.parseDOM(item, 'a', attrs={'onclick': '.+?'})[-1]
            except: pass
            title = client.replaceHTMLCodes(title)
            title = title.encode('utf-8')

            year = client.parseDOM(item, 'span', attrs={'class': 'year_type'})[0]
            year = re.compile(r'(\d{4})').findall(year)[-1]
            year = year.encode('utf-8')

            name = '%s (%s)' % (title, year)
            try: name = name.encode('utf-8')
            except: pass

            imdb = client.parseDOM(item, 'a', ret='href')[0]
            imdb = 'tt' + re.sub('[^0-9]', '', imdb.rsplit('tt', 1)[-1])
            imdb = imdb.encode('utf-8')

            poster = '0'
            try: poster = client.parseDOM(item, 'img', ret='src')[0]
            except: pass
            try: poster = client.parseDOM(item, 'img', ret='loadlate')[0]
            except: pass
            if not ('_SX' in poster or '_SY' in poster): poster = '0'
            poster = re.sub(r'_SX\d*|_SY\d*|_CR\d+?,\d+?,\d+?,\d*', '_SX500', poster)
            poster = client.replaceHTMLCodes(poster)
            poster = poster.encode('utf-8')

            genre = client.parseDOM(item, 'span', attrs={'class': 'genre'})
            genre = client.parseDOM(genre, 'a')
            genre = ' / '.join(genre)
            if genre == '': genre = '0'
            genre = client.replaceHTMLCodes(genre)
            genre = genre.encode('utf-8')

            try: duration = re.compile('(\d+?) mins').findall(item)[-1]
            except: duration = '0'
            duration = client.replaceHTMLCodes(duration)
            duration = duration.encode('utf-8')

            try: rating = client.parseDOM(item, 'span', attrs = {'class': 'rating-rating'})[0]
            except: rating = '0'
            try: rating = client.parseDOM(rating, 'span', attrs = {'class': 'value'})[0]
            except: rating = '0'
            if rating == '' or rating == '-': rating = '0'
            rating = client.replaceHTMLCodes(rating)
            rating = rating.encode('utf-8')

            try: votes = client.parseDOM(item, 'div', ret='title', attrs = {'class': 'rating rating-list'})[0]
            except: votes = '0'
            try: votes = re.compile('[(](.+?) votes[)]').findall(votes)[0]
            except: votes = '0'
            if votes == '': votes = '0'
            votes = client.replaceHTMLCodes(votes)
            votes = votes.encode('utf-8')

            try: mpaa = client.parseDOM(item, 'span', attrs = {'class': 'certificate'})[0]
            except: mpaa = '0'
            try: mpaa = client.parseDOM(mpaa, 'span', ret='title')[0]
            except: mpaa = '0'
            if mpaa == '' or mpaa == 'NOT_RATED': mpaa = '0'
            mpaa = mpaa.replace('_', '-')
            mpaa = client.replaceHTMLCodes(mpaa)
            mpaa = mpaa.encode('utf-8')

            director = client.parseDOM(item, 'span', attrs = {'class': 'credit'})
            director += client.parseDOM(item, 'div', attrs = {'class': 'secondary'})
            try: director = [i for i in director if 'Director:' in i or 'Dir:' in i][0]
            except: director = '0'
            director = director.split('With:', 1)[0].strip()
            director = client.parseDOM(director, 'a')
            director = ' / '.join(director)
            if director == '': director = '0'
            director = client.replaceHTMLCodes(director)
            director = director.encode('utf-8')

            cast = client.parseDOM(item, 'span', attrs = {'class': 'credit'})
            cast += client.parseDOM(item, 'div', attrs = {'class': 'secondary'})
            try: cast = [i for i in cast if 'With:' in i or 'Stars:' in i][0]
            except: cast = '0'
            cast = cast.split('With:', 1)[-1].strip()
            cast = client.replaceHTMLCodes(cast)
            cast = cast.encode('utf-8')
            cast = client.parseDOM(cast, 'a')
            if cast == []: cast = '0'

            plot = '0'
            try: plot = client.parseDOM(item, 'span', attrs = {'class': 'outline'})[0]
            except: pass
            try: plot = client.parseDOM(item, 'div', attrs = {'class': 'item_description'})[0]
            except: pass
            plot = plot.rsplit('<span>', 1)[0].strip()
            if plot == '': plot = '0'
            plot = client.replaceHTMLCodes(plot)
            plot = plot.encode('utf-8')

            tagline = re.compile('[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]
            try: tagline = tagline.encode('utf-8')
            except: pass

            items.append({
                'title': title,
                'originaltitle': title,
                'year': year,
                'premiered': '0',
                'studio': '0',
                'genre': genre,
                'duration': duration,
                'rating': rating,
                'votes': votes,
                'mpaa': mpaa,
                'director': director,
                'writer': '0',
                'cast': cast,
                'plot': plot,
                'tagline': tagline,
                'name': name,
                'code': imdb,
                'imdb': imdb,
                'tmdb': '0',
                'tvdb': '0',
                'tvrage': '0',
                'poster': poster,
                'banner': '0',
                'fanart': '0',
                'next_url': next_url,
                'next_page': next_page,
                'max_pages': max_pages,
            })
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', item, repr(ex))

    return items


def lists(url):
    result = client.get(url).content
    result = result.decode('iso-8859-1').encode('utf-8')
    results = client.parseDOM(result, 'div', attrs={'class': 'list-preview .*?'})

    log.debug('{m}.{f}: %s: %d lists', url.replace(_BASE_URL, ''), len(results))

    items = []
    for item in results:
        try:
            name = client.parseDOM(item, 'div', attrs={'class': 'list_name'})[0]
            name = client.parseDOM(name, 'a')[0]
            name = client.replaceHTMLCodes(name)
            name = name.encode('utf-8')

            listid = client.parseDOM(item, 'a', ret='href')[0]
            listid = listid.split('/list/', 1)[-1].replace('/', '')

            meta = client.parseDOM(item, 'div', attrs={'class': 'list_meta'})[0]
            meta = client.replaceHTMLCodes(meta)
            meta = meta.encode('utf-8')

            image = client.parseDOM(item, 'div', attrs={'class': 'list-preview-item-wide'})[0]
            image = client.parseDOM(image, 'img', ret='src')
            if not image:
                image = client.parseDOM(image, 'img', ret='loadlate')

            items.append({
                'name': name,
                'imdb_list_id': listid,
                'genre': meta,
                'poster': 'movieUserlists.jpg',
            })
            if image:
                items[-1].update({
                    'image': image[0],
                })
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', item, repr(ex))

    return items
