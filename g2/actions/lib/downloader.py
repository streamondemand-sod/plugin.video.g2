# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2015 Blazetamer
    Copyright (C) 2015 lambda
    Copyright (C) 2015 spoyser
    Copyright (C) 2015 crzen
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


import os
import time
import urllib2
import urlparse
import datetime

from g2.libraries import fs
from g2.libraries import log
from g2.libraries import cache
from g2.libraries import workers
from g2.libraries import addon


_MIN_PERCENTAGE_FOR_COMPLETITION = 99 # %
_MIN_SAMPLE_TIME_FOR_DOWNLOAD_SPEED = 10 # secs
_MAX_SAMPLE_TIME_FOR_DOWNLOAD_SPEED = 60 # secs
_PERCENTAGE_DELTA_FOR_STATUS_UPDATE = 10 # %


def addDownload(name, url, ext, size, resumable, image):
    def download(result):
        return result
    result = cache.get(download, -1, [], hash_args=0, table='rel_dl', debug=log.debugactive())
    if name in [i['name'] for i in result]:
        return False

    if not ext:
        ext = os.path.splitext(urlparse.urlparse(url).path)[1][1:].lower()
        if ext not in ['mp4', 'mkv', 'flv', 'avi', 'mpg']:
            ext = 'mp4'

    # File name is derived by the title using these rules:
    # - Convert all contiguos spaces to a single '.'
    # - Remove leading and trailing spaces
    # - Remove special characters for typical FS
    filename = '.'.join(name.split()).translate(None, '\\/:*?"<>|').decode('utf-8').encode('latin1') + '.' + ext.encode('latin1')

    cache.get(download, 0,
              result + [{'name': name,
                         'url': url,
                         'filename': filename,
                         'size': size,
                         'resumable': resumable,
                         'image': image,
                        }], hash_args=0, table='rel_dl', debug=log.debugactive())

    try:
        filepath = _file_path(fs.translatePath(addon.freshsetting('downloads')), filename)
        if os.path.exists(filepath):
            fs.removeFile(filepath)
    except Exception as ex:
        log.notice('{m}.{f}: removing existing %s: %s', filename, ex)

    return True


def listDownloads():
    def download():
        return []
    return cache.get(download, -1, table='rel_dl', debug=log.debugactive())


def removeDownload(url):
    def download(result):
        return result
    result = cache.get(download, -1, [], hash_args=0, table='rel_dl', debug=log.debugactive())
    result = [i for i in result if not i['url'] == url]
    cache.get(download, 0, result, hash_args=0, table='rel_dl', debug=log.debugactive())

    return True


def status():
    return addon.prop('downloader', name='filepath')


def statusItem(item):
    downloads_path = fs.translatePath(addon.freshsetting('downloads'))
    filepath = _file_path(downloads_path, item['filename'])
    try:
        percentage = 0 if not item['size'] else int(100*os.path.getsize(filepath)/item['size'])
    except Exception:
        percentage = None

    completition_time = None \
        if addon.prop('downloader', name='filepath') != _file_path(downloads_path, item['filename']) else \
                        addon.prop('downloader', name='completition_time')

    return percentage, completition_time


def _file_path(directory, filename):
    return None if not directory else os.path.join(directory.encode('latin1'), filename)


_WORKER_LOCK = workers.Lock()


def worker():
    this = workers.current_thread()

    downloads_path = fs.translatePath(addon.freshsetting('downloads'))
    if not downloads_path:
        return log.error('%s aborted: downloads path setting not specified', this.name)

    items = None
    with workers.non_blocking(_WORKER_LOCK):
        items = listDownloads()

        if not items:
            return log.error('%s aborted: no downloads to process', this.name)

        this.result = log.notice('%s started with %d items', this.name, len(items))

        for item in items:
            try:
                addon.prop('downloader', '-', name='filepath')

                url = item['url']
                dest = _file_path(downloads_path, item['filename'])
                resumable = item['resumable']

                try:
                    downloaded = 0 if not resumable else os.path.getsize(dest)
                except Exception:
                    downloaded = 0

                response, downloaded, contentlength = _make_http_request(url, downloaded)

                resumable = True
                if downloaded is None:
                    fs.makeDir(os.path.dirname(dest))    
                    destf = open(dest, 'wb')
                    downloaded = 0
                    resumable = False
                elif not downloaded:
                    destf = open(dest, 'wb')
                else:
                    destf = open(dest, 'r+b')
                    destf.seek(downloaded, 0)
                    destf.truncate(downloaded)

                start_time = _meter(downloaded, start=True)

                log.notice('%s: %s: %s (%sresumable)',
                           this.name, os.path.basename(dest),
                           'started download of %d bytes'%contentlength if not downloaded else
                           'restarted download at %d of %d bytes'%(downloaded, contentlength),
                           '' if resumable else 'not ')

                errors = 0
                resumes = 0
                log_progress = None

                completed = False
                while not this.die:
                    percent = int(100 * downloaded / contentlength)

                    mbps = _meter(downloaded)
                    try:
                        completition_time = int(((contentlength-downloaded)*8)/float(1024*1024)/mbps)
                        completition_time = str(datetime.timedelta(seconds=completition_time))
                    except Exception:
                        completition_time = '...'
                    addon.prop('downloader', completition_time, name='completition_time')
                    addon.prop('downloader', dest, name='filepath')

                    # json.loads(json.dumps(unicode(a, 'ISO-8859-1'))).encode('ISO-8859-1')
                    progress = '[%s%%, %s] %s'%(percent, completition_time, unicode(os.path.basename(dest), 'ISO-8859-1'))
                    if log_progress is None:
                        log_progress = percent + (_PERCENTAGE_DELTA_FOR_STATUS_UPDATE-percent%_PERCENTAGE_DELTA_FOR_STATUS_UPDATE)
                    if percent > log_progress:
                        log.notice('%s: %dMB, %.1f Mb/s, %s', this.name, int(downloaded/float(1024*1024)), mbps, progress)
                        log_progress += _PERCENTAGE_DELTA_FOR_STATUS_UPDATE
                        this.result = progress

                    error = False
                    try:        
                        chunk = response.read(min(contentlength-downloaded, 128*1024))
                        if chunk:
                            errors = 0
                            destf.write(chunk)
                            downloaded += len(chunk)
                        elif percent >= _MIN_PERCENTAGE_FOR_COMPLETITION:
                            completed = True
                            break
                        else:
                            errors = 10
                            raise Exception('premature end of stream')

                    except Exception as ex:
                        log.notice('%s: %s: %s', this.name, os.path.basename(dest), ex)
                        error = True
                        sleep = 10
                        errno = ex.errno if hasattr(ex, 'errno') else 0
                        if errno in [10054, 11001]:
                            errors = 10
                            sleep = 30

                    if not error:
                        continue

                    time.sleep(sleep)
                    errors += 1

                    # Up to 10 non fatal consecutive errors, try again the read on the current response
                    if errors <= 10:
                        continue

                    resumes += 1
                    if not resumable:
                        if resumes >= 50:
                            log.notice('%s: %s: download canceled - too many errors (%d)',
                                       this.name, os.path.basename(dest), errors)
                            break
                    else:
                        if resumes >= 500:
                            log.notice('%s: %s: download canceled - too many resumes (%d)',
                                       this.name, os.path.basename(dest), resumes)
                            break

                    log.notice('%s: %s: download restarted at %d of %d bytes (#%d)',
                               this.name, os.path.basename(dest), downloaded, contentlength, resumes)

                    if resumable:
                        response, downloaded, contentlength = _make_http_request(url, downloaded)

                        resumable = True
                        if downloaded is None:
                            resumable = False
                            downloaded = 0
                        destf.truncate(downloaded)

                        _meter(downloaded, start=True)
                        log_progress = None

                destf.close()

                if completed:
                    removeDownload(url)

                log.notice('%s: %s: %s (%d secs, %d resumes)',
                           this.name, os.path.basename(dest), 'completed' if completed else 'stopped',
                           int(time.time()-start_time), resumes)

            except Exception as ex:
                log.error('{m}.{f}: %s: %s', os.path.basename(dest), ex)

            addon.prop('downloader', '', name='filepath')

            if this.die:
                break

    reason = 'other thread alreay active' if not items else \
             'user request / system shutdown' if this.die else \
             'completed all items'

    return log.notice('%s stopped (%s)', this.name, reason)


def _make_http_request(url, downloaded):
    try:
        headers = dict(urlparse.parse_qsl(urlparse.urlparse(url)[4]))
    except Exception:
        headers = dict('')

    if downloaded > 0:
        headers['Range'] = 'bytes=%d-'%downloaded

    try:
        request = urllib2.Request(url, headers=headers)
        response = urllib2.urlopen(request, timeout=30)
    except:
        removeDownload(url)
        raise

    try:
        contentlength = int(response.headers['Content-Length'])
        log.debug('{m}.{f}: response.headers=\n%s'%response.headers)
        if contentlength <= 0:
            raise Exception('empty stream')
    except:
        removeDownload(url)
        raise

    try:
        if downloaded > 0:
            if 'bytes' not in response.headers['Content-Range'].lower():
                raise       # for some reason this source is not resumable anymore
            else:
                range_start = int(response.headers['Content-Range'].split(' ')[1].split('-')[0])
                contentlength += range_start
                if range_start > downloaded:
                    raise   # the offered range miss some data
                downloaded = range_start
        else:
            downloaded = 0 if 'bytes' in response.headers['Accept-Ranges'].lower() else None
    except Exception:
        downloaded = None

    log.debug('{m}.{f}: %s; contentlength=%s',
              'not resumable' if downloaded is None else 'downloaded=%s'%downloaded, contentlength)

    return response, downloaded, contentlength


def _meter(downloaded, start=False):
    if start:
        _meter.samples = [(time.time(), downloaded)]
        return _meter.samples[0][0]

    _meter.samples.append((time.time(), downloaded))
    deltatime = _meter.samples[-1][0] - _meter.samples[0][0]
    deltabytes = _meter.samples[-1][1] - _meter.samples[0][1]
    if deltatime <= _MIN_SAMPLE_TIME_FOR_DOWNLOAD_SPEED:
        mbps = 0
    else:
        mbps = (deltabytes * 8) / float(1024*1024) / deltatime
        if deltatime > _MAX_SAMPLE_TIME_FOR_DOWNLOAD_SPEED and len(_meter.samples) > 2:
            _meter.samples.pop(0)

    log.debug('{m}.{f}: #samples=%d, deltatime=%.3f, deltabytes=%d: %.3f Mb/s',
              len(_meter.samples), deltatime, deltabytes, mbps)

    return mbps
