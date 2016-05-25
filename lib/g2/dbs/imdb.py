# -*- coding: utf-8 -*-

"""
    Genesi2 Add-on
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
    'methods': ['url', 'movies', 'lists'],
}


_imdb_page_count = 20

_urls = {
    'lists{imdb_user_id}': 'http://www.imdb.com/user/ur{imdb_user_id}/lists',
    'movies{imdb_list_id}': 'http://www.imdb.com/list/{imdb_list_id}/?view=detail&sort=title:asc&title_type=feature,short,tv_movie,tv_special,video,documentary,game&start=1',
    'movies_boxoffice{}': 'http://www.imdb.com/search/title?title_type=feature,tv_movie&sort=boxoffice_gross_us,desc&count=%d' % _imdb_page_count,
    'movies_oscar{}': 'http://www.imdb.com/search/title?title_type=feature,tv_movie&groups=oscar_best_picture_winners&sort=year,desc&count=%d' % _imdb_page_count,
}


def url(kind=None, **kwargs):
    if not kind: return _urls.keys()
    if kind not in _urls: return None

    for k, v in kwargs.iteritems():
        kwargs[k] = urllib.quote_plus(str(v))

    return _urls[kind].format(**kwargs)


def movies(url):
    try:
        result = client.request(url)
        result = result.decode('iso-8859-1').encode('utf-8')
        results = client.parseDOM(result, 'tr', attrs = {'class': '.+?'})
        results += client.parseDOM(result, 'div', attrs = {'class': 'list_item.+?'})
        log.debug('imdb.movies(%s): %d movies'%(url, len(results)))
    except Exception as e:
        log.notice('imdb.movies(%s): %s'%(url, e))
        return None

    try:
        next_url = client.parseDOM(result, 'span', attrs = {'class': 'pagination'})
        next_url = client.parseDOM(next_url[0], 'a', ret='href')[-1]
        next_url = url.replace(urlparse.urlparse(url).query, urlparse.urlparse(next_url).query)
        next_url = client.replaceHTMLCodes(next_url)
        next_url = next_url.encode('utf-8')
        next_page = (int(re.search(r'&start=(\d+)', next_url).group(1))-1)/_imdb_page_count + 1
    except:
        next_url = ''
        next_page = 0

    items = []
    for item in results:
        try:
            try: title = client.parseDOM(item, 'a')[1]
            except: pass
            try: title = client.parseDOM(item, 'a', attrs = {'onclick': '.+?'})[-1]
            except: pass
            title = client.replaceHTMLCodes(title)
            title = title.encode('utf-8')

            year = client.parseDOM(item, 'span', attrs = {'class': 'year_type'})[0]
            year = re.compile('(\d{4})').findall(year)[-1]
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
            poster = re.sub('_SX\d*|_SY\d*|_CR\d+?,\d+?,\d+?,\d*','_SX500', poster)
            poster = client.replaceHTMLCodes(poster)
            poster = poster.encode('utf-8')

            genre = client.parseDOM(item, 'span', attrs = {'class': 'genre'})
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
            })
        except:
            pass

    return items


def lists(url):
    try:
        result = client.request(url)
        result = result.decode('iso-8859-1').encode('utf-8')
        results = client.parseDOM(result, 'div', attrs={'class': 'list-preview .*?'})
        log.debug('imdb.lists(%s): %d lists'%(url, len(results)))
    except Exception as e:
        log.notice('imdb.lists(%s): %s'%(url, e))

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
            image = client.parseDOM(image, 'img', ret='loadlate')[0]

            items.append({
                'name': name,
                'imdb_list_id': listid,
                'genre': meta,
                'image': image,
                'poster': 'movieUserlists.jpg',
            })
        except:
            pass

    return items
