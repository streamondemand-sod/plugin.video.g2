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
import sys
import json
import time
import datetime
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from g2.libraries import fs
from g2.libraries import log
from g2.libraries import workers

from g2 import pkg
from g2 import defs
from g2 import resolvers

from .lib.fuzzywuzzy import fuzz


_MIN_FUZZINESS_VALUE = 84
_IGNORE_BODY_EXCEPTIONS = True


def info(force_refresh=False):
    def source_info(package, module, m, paths):
        content = set()
        if hasattr(m, 'get_movie'):
            content.add('movie')
        if hasattr(m, 'get_episode'):
            content.add('episode')
        if not hasattr(m, 'info'):
            nfo = {}
        elif callable(m.info):
            nfo = m.info(paths)
        else:
            nfo = m.info
        if type(nfo) != list:
            nfo = [nfo]
        for i in nfo:
            if 'content' not in i:
                i['content'] = list(content)
        return nfo

    return pkg.info(__name__, source_info, force_refresh)


def content_sources(content, meta, ui_update=None):
    # Collect all sources providers across all packages
    providers = {}
    for dummy_kind, package in pkg.packages([__name__]):
        providers[package] = [mi for mi in info().itervalues() if mi['package'] == package and content in mi['content']]
    all_providers = sum([len(providers[mi]) for mi in providers])

    sources = {}
    all_completed_providers = 0
    for package, modulesinfo in providers.iteritems():
        if not modulesinfo:
            continue

        modules = sorted(set([mi['module'] for mi in modulesinfo]))
        with pkg.Context(__name__, package, modules, modulesinfo[0]['search_paths'], ignore_exc=_IGNORE_BODY_EXCEPTIONS) as mods:
            if not mods:
                continue

            threads = []
            channel = []
            for mod, module in zip(mods, modules):
                # threads is a list of tuples: module_name, thread, heavy_methods_list
                threads.extend([(sm['name'],
                                 workers.Thread(_sources_worker, channel, mod, sm['name'], content, meta),
                                 sm.get('heavy', [])) for sm in modulesinfo if sm['module'] == module])

            log.debug('{m}.{f}: scheduling %s threads: %s', len(threads), threads)

            thd_i = 0
            while True:
                threads_chunk = []
                while thd_i < len(threads) and len(threads_chunk) < defs.MAX_CONCURRENT_THREADS:
                    thread_info = threads[thd_i]
                    thd_i += 1
                    threads_chunk.append(thread_info[1])
                    # if this is an heavy method, do not add any more threads
                    if content in thread_info[2]:
                        break

                if not threads_chunk:
                    break

                dummy = [t.start() for t in threads_chunk]

                completed_threads = []
                while len(completed_threads) < len(threads_chunk):
                    completed_threads = sorted([t for t in threads_chunk if not t.is_alive()], key=lambda t: t.elapsed)
                    new_sources = []
                    for thd in completed_threads:
                        if thd.result is not None:
                            for src in thd.result:
                                if src['url'] not in sources:
                                    new_sources.append(src)
                                    sources[src['url']] = src
                            all_completed_providers += 1
                            thd.result = None
                    if not ui_update:
                        time.sleep(1)
                        continue
                    try:
                        if not ui_update(all_completed_providers, all_providers, new_sources):
                            # Inform all threads to abort ASAP
                            channel.append('abort')
                            break
                    except Exception as ex:
                        log.notice('{m}.{f}(%s): %s', content, ex)

    return sources.values()


def _sources_worker(channel, mod, provider, content, meta):
    imdb = meta.get('imdb', '0')
    key_video = _key_video(**meta)
    video_ref = None
    if imdb == '0':
        dbcon = None
    else:
        try:
            # (fixme) move the db handling into libraries.database
            fs.makeDir(fs.PROFILE_PATH)
            dbcon = database.connect(fs.CACHE_DB_FILENAME, timeout=10)
            dbcon.row_factory = database.Row
            dbcon.execute('CREATE TABLE IF NOT EXISTS rel_url'
                          ' (provider TEXT, key_video TEXT, video_ref TEXT, UNIQUE(provider, key_video))')
            dbcon.execute('CREATE TABLE IF NOT EXISTS rel_src'
                          ' (provider TEXT, key_video TEXT, sources TEXT, timestamp TEXT, UNIQUE(provider, key_video));')
            dbcon.commit()
        except Exception:
            pass

        try:
            # Check if the sources are already cached and still valid
            # (fixme) move the db handling into libraries.database
            dbcur = dbcon.execute("SELECT * FROM rel_src WHERE provider = ? AND key_video = ?",
                                  (provider, key_video))
            sqlrow = dbcur.fetchone()

            sql_ts = int(str(sqlrow['timestamp']).translate(None, '- :'))
            now_ts = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            if (now_ts - sql_ts) / 3600 < defs.SOURCE_CACHE_LIFETIME:
                sources = json.loads(sqlrow['sources'])
                log.debug('{m}.{f}.%s: %d sources found in the cache', provider, len(sources))
                return sources
        except Exception:
            pass

        try:
            # Check if the video url is already cached [fixme) no expiration?]
            # (fixme) move the db handling into libraries.database
            dbcur = dbcon.execute("SELECT * FROM rel_url WHERE provider = ? AND key_video = ?",
                                  (provider, key_video))
            sqlrow = dbcur.fetchone()
            video_ref = json.loads(sqlrow['video_ref'])
        except Exception:
            pass

    if not video_ref:
        get_function_name = 'get_movie' if content == 'movie' else 'get_episode'
        if 'abort' in channel:
            log.debug('{m}.{f}.%s: aborted at %s', provider, get_function_name)
            return []

        try:
            # (fixme) replace **meta w/ meta or explicit meta[] args (API change)
            video_matches = getattr(mod, get_function_name)(provider.split('.'), **meta)
        except Exception as ex:
            log.notice('{m}.{f}.%s.%s: %s', provider, get_function_name, repr(ex), trace=True)
            video_matches = None

        video_ref = _best_match(provider, video_matches, meta)
        if not video_ref:
            log.debug('{m}.{f}.%s: no valid match found', provider)

        if video_ref and dbcon:
            # (fixme) move the db handling into libraries.database
            try:
                with dbcon:
                    dbcon.execute("DELETE FROM rel_url WHERE provider = ? AND key_video = ?",
                                  (provider, key_video))
                    dbcon.execute("INSERT INTO rel_url Values (?, ?, ?)",
                                  (provider, key_video, json.dumps(video_ref)))
            except Exception as ex:
                log.notice('{m}.{f}.%s: %s: %s', provider, key_video, ex)

    if 'abort' in channel:
        log.debug('{m}.{f}.%s: aborted at get_sources', provider)
        return []

    sources = []
    if video_ref:
        try:
            sources = mod.get_sources(provider.split('.'), video_ref)
        except Exception as ex:
            log.debug('{m}.{f}.%s: %s: %s', provider, video_ref, repr(ex), trace=True)

        if not sources:
            sources = []

    for src in sources:
        src.update({
            'provider': provider,
        })

    # NOTE: for episodes, the get_sources might returns additional seasons/episodes, which are saved as well
    # However, only the sources for the requested season/episode are returned.
    sources_groups = _sources_groups(imdb, sources).iteritems()
    sources = []
    for key, srcs in sources_groups:
        if dbcon:
            # (fixme) move the db handling into libraries.database
            try:
                with dbcon:
                    log.debug('{m}.{f}.%s: %s: saving %d sources', provider, key, len(srcs))
                    dbcon.execute("DELETE FROM rel_src WHERE provider = ? AND key_video = ?",
                                  (provider, key))
                    dbcon.execute("INSERT INTO rel_src Values (?, ?, ?, ?)",
                                  (provider, key, json.dumps(srcs), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            except Exception as ex:
                log.notice('{m}.{f}.%s: %s: %s', provider, key, ex)
        if key == key_video:
            sources = srcs

    log.debug('{m}.{f}.%s: %s: %d sources found', provider, key_video, len(sources))

    return sources


def _best_match(provider, matches, meta):
    if not matches:
        return None

    # Remove the matches with empty url and/or titles
    matches = [[0, m] for m in matches if m[0] and m[1].strip()]
    if not matches:
        return None

    def cleantitle(title):
        if title:
            # Remove from the title anything within () if preceded/followed by spaces
            title = re.sub(r'(^|\s)\(.*\)(\s|$)', r'\1\2', title)
            # Remove from the title anything within []
            title = re.sub(r'\[.*\]', '', title)
        return title

    title = meta['tvshowtitle'] if 'tvshowtitle' in meta else meta['title']

    def match_confidence(match):
        mtitle = cleantitle(match[1][1])
        ftsr = fuzz.token_sort_ratio(mtitle, title)
        if ftsr < _MIN_FUZZINESS_VALUE and '-' in mtitle and '-' not in title:
            ftsr = max(fuzz.token_sort_ratio(mtitle.split('-')[0], title),
                       fuzz.token_sort_ratio(mtitle.split('-')[1], title))
        match[0] = ftsr
        return ftsr

    best_match = max(matches, key=match_confidence)
    confidence = best_match[0]
    best_match = best_match[1]

    log.debug('{m}.{f}.%s: %d matches found; best has confidence %d ("%s" vs "%s")',
              provider, len(matches), confidence, best_match[1], title)

    return None if confidence < _MIN_FUZZINESS_VALUE else best_match


def _sources_groups(imdb, sources):
    groups = {}
    for src in sources:
        key_video = _key_video(imdb=imdb, **src)
        if key_video not in groups:
            groups[key_video] = []
        groups[key_video].append(src)

    return groups


def clear_sources_cache(**kwargs):
    # (fixme) move the db handling into libraries.database
    try:
        key_video = _key_video(**kwargs)
        fs.makeDir(fs.PROFILE_PATH)
        dbcon = database.connect(fs.CACHE_DB_FILENAME, timeout=10)
        with dbcon:
            dbcon.execute("DELETE FROM rel_src WHERE key_video = ?", (key_video,))
            dbcon.execute("DELETE FROM rel_url WHERE key_video = ?", (key_video,))
        return key_video
    except Exception as ex:
        log.error('{m}.{f}: %s: %s', kwargs, repr(ex))
        return None


def _key_video(**kwargs):
    # (fixme) move the db handling into libraries.database
    return '/'.join([kwargs.get(k) or '0' for k in ['imdb', 'season', 'episode']])


def get_movie(provider, **kwargs):
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    with pkg.Context(__name__, provider['package'], [provider['module']], provider['search_paths'],
                     ignore_exc=_IGNORE_BODY_EXCEPTIONS) as mod:
        return mod[0].get_movie(provider['name'].split('.'), **kwargs)


def get_episode(provider, **kwargs):
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    with pkg.Context(__name__, provider['package'], [provider['module']], provider['search_paths'],
                     ignore_exc=False) as mod:
        return mod[0].get_episode(provider['name'].split('.'), **kwargs)


def get_sources(provider, url):
    if not url:
        return []
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    with pkg.Context(__name__, provider['package'], [provider['module']], provider['search_paths'],
                     ignore_exc=_IGNORE_BODY_EXCEPTIONS) as mod:
        sources = mod[0].get_sources(provider['name'].split('.'), url)
        for src in sources:
            src.update({
                'provider': provider['name'],
            })
    return sources


def resolve(provider, url):
    if not url:
        return None
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    # First try the resolution with the resolvers
    rurl = resolvers.resolve(url)

    # If the resolvers have sucessfully resolved the url, then bypass the source resolver
    if isinstance(rurl, basestring):
        return rurl

    # If the resolvers return any error other than the 'No resolver for', then stop the resolution
    if 'No resolver for' not in str(rurl):
        return rurl

    # Otherwise, try with the source resolver and then give the url back to the resolvers again
    try:
        with pkg.Context(__name__, provider['package'], [provider['module']], provider['search_paths'],
                         ignore_exc=_IGNORE_BODY_EXCEPTIONS) as mod:
            url = mod[0].resolve(provider['name'].split('.'), url)
    except Exception:
        # On any failure of the source resolver, return the error of the first resolvers invocation
        return rurl

    # Abort if the source resolver return a None or an error class, otherwise give a try again to the resolvers
    return resolvers.resolve(url) if isinstance(url, basestring) else url
