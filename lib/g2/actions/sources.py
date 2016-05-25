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


import sys
import json
import time
import urllib
import urlparse

import g2

from g2.libraries import log
from g2.libraries import workers
from g2.libraries import platform
from g2.libraries.language import _
from g2 import providers
from .lib import ui
from .lib import downloader


_resolver_timeout = 30 # seconds

_addon = sys.argv[0]
_thread = int(sys.argv[1])


def usefolderonce(action, **kwargs):
    platform.property('actions.sources', True, name='usefolderonce')


def dialog(action, title=None, year=None, imdb=None, tvdb=None, meta=None, **kwargs):
    if platform.property('actions.sources', name='usefolderonce'):
        platform.property('actions.sources', False, name='usefolderonce')
        return folder(action, title=title, year=year, imdb=imdb, tvdb=tvdb, meta=meta, **kwargs)

    metadata = json.loads(meta)
    log.notice('sources.dialog(imdb=%s): certification=%s'%(imdb, metadata.get('mpaa')))

    try:
        ui.idle()

        if not ui.infoLabel('Container.FolderPath').startswith('plugin://'):
            ui.PlayList.clear()

        ui.execute('Action(Back,10025)')

        if imdb == '0': imdb = '0000000'
        imdb = 'tt' + imdb.translate(None, 't')
        content = 'movie'
        name = '%s (%s)'%(title, year)

        def sources_generator(self):
            def ui_addsources(progress, total, new_results):
                self.addItems(_sources_label(new_results, index=len(self.items)))
                self.updateDialog(progress=(progress, total))
                stop_searching = self.dialog_closed or self.stop_button_flag
                if not stop_searching:
                    ui.sleep(1000)
                return not stop_searching

            providers.video_sources(ui_addsources, content, title=title, year=year, imdb=imdb, tvdb=tvdb, meta=meta, **kwargs)

        posterdata = name if metadata.get('poster', '0') == '0' else 'poster://'+metadata['poster']

        w = ui.SourcesDialog('SourcesDialog.xml', platform.addonPath, 'Default', '720p',
                             sourcesGenerator=sources_generator,
                             sourcePriority=_source_priority,
                             sourceResolve=source_resolve,
                             posterData=posterdata)

        # TODO[code]: make a ui that is simply called ui.resolvedPlugin()
        if _thread > 0: ui.resolvedPlugin(_thread, True, ui.ListItem(path=''))

        while True:
            w.doModal()

            # User-abort
            if not w.selected: break

            source = w.selected.getLabel()
            url = w.selected.getProperty('url')

            if ui.Player().run(title, year, None, None, imdb, tvdb, meta, url,
                                   credits=_credits_message(w.selected.getProperty('source_provider'),
                                                            w.selected.getProperty('source_host'),
                                                            w.selected.getProperty('media'))):
                break

            # Invalidate the erroneous stream item
            w.selected.setProperty('source_url', '')
            w.selected.setProperty('url', '')

            ui.infoDialog(_('Not a valid stream'), heading=source)
            ui.sleep(2000)

            log.notice('sources.dialog: player.run("%s", %s) FAILED'%(name, url))

            w.show()

        del w

    except:
        ui.infoDialog(_('No stream available'))


def folder(action, title=None, year=None, imdb=None, tvdb=None, meta=None, **kwargs):
    try:
        ui.idle()

        metadata = json.loads(meta)
        log.notice('sources.folder(imdb=%s): certification=%s'%(imdb, metadata.get('mpaa')))

        if imdb == '0': imdb = '0000000'
        imdb = 'tt' + imdb.translate(None, 't')
        # TODO[func]: episode/tvshow
        content = 'movie'
        name = '%s (%s)'%(title, year)

        dialog_progress = ui.DialogProgress()
        dialog_progress.create(platform.addonInfo('name'))
        dialog_progress.update(0)

        all_sources = []
        time_start = time.time()
        def dialog_update(progress, total, new_results=[]):
            all_sources.extend(new_results)
            dialog_progress.update(100 * progress / total,
                                   '%s: %s %s' % (_('Time elapsed'), int(time.time() - time_start), _('seconds')),
                                   '%s: %s' % (_('Sources'), len(all_sources)))

            ui.sleep(1000)
            return not ui.abortRequested() and not dialog_progress.iscanceled()

        providers.video_sources(dialog_update, content, title=title, year=year, imdb=imdb, tvdb=tvdb, meta=meta, **kwargs)

        dialog_progress.close()

        log.notice('sources.folder(name=%s, ...): found  %d sources'%(name, len(all_sources)))

        if not all_sources: raise Exception()

        all_sources = sorted(all_sources, key=lambda s: _source_priority(s['source'], s['provider'], s['quality']), reverse=True)
        all_sources = _sources_label(all_sources)

        poster = metadata.get('poster', '0')
        banner = metadata.get('banner', '0')
        thumb = metadata.get('thumb', '0')
        fanart = metadata.get('fanart', '0')
        if poster == '0':
            poster = platform.addonPoster()
        if banner == '0' and poster == '0':
            banner = platform.addonBanner()
        elif banner == '0':
            banner = poster
        if thumb == '0' and fanart == '0':
            thumb = platform.addonFanart()
        elif thumb == '0':
            thumb = fanart
        if platform.setting('fanart') != 'true' or fanart == '0':
            fanart = platform.addonFanart()

        for i, source in enumerate(all_sources):
            try:
                url, label, provider, info = source['url'], source['label'], source['provider'], source.get('info', '')
                sysname, sysurl, sysimage, sysprovider = urllib.quote_plus(name), urllib.quote_plus(url), urllib.quote_plus(poster), urllib.quote_plus(provider)
                syssource = urllib.quote_plus(json.dumps([source]))

                if i == 0:
                    query = 'action=sources.playitem&title=%s&year=%s&imdb=%s&tvdb=%s&source=%s&meta=%s' % (title, year, imdb, tvdb, syssource, urllib.quote_plus(meta))
                else:
                    query = 'action=sources.playitem&title=%s&year=%s&imdb=%s&tvdb=%s&source=%s' % (title, year, imdb, tvdb, syssource)

                cm = []
                cm.append((_('Download item'), 'RunPlugin(%s?action=sources.download&name=%s&image=%s&url=%s&provider=%s)' % (_addon, sysname, sysimage, sysurl, sysprovider)))
                cm.append((_('Add-on settings'), 'RunPlugin(%s?action=tools.settings)' % _addon))

                item = ui.ListItem(label=label, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                try:
                    item.setArt({'poster': poster, 'tvshow.poster': poster, 'season.poster': poster, 'banner': banner, 'tvshow.banner': banner, 'season.banner': banner})
                except:
                    pass
                item.setInfo(type='Video', infoLabels=metadata)
                item.setInfo(type='Video', infoLabels={'genre': info})
                if fanart: item.setProperty('Fanart_Image', fanart)
                item.setProperty('Video', 'true')
                item.setProperty('IsPlayable', 'true')
                item.addContextMenuItems(cm, replaceItems=True)
                # NOTE: leave isFolder=True always and ensure that the invoked action, if doesn't display a directory,
                # does an Action(Back,10025) to remove the empty directory (see playitem)
                ui.addItem(handle=int(_thread), url='%s?%s' % (_addon, query), listitem=item, isFolder=True)
            except:
                import traceback
                log.notice(traceback.format_exc())
                pass

        # To display the genre (actually the provider info) below the label
        ui.setContent(int(_thread), 'movies')
        ui.finishDirectory(int(_thread), cacheToDisc=True)
    except:
        ui.infoDialog(_('No stream available'))


def playitem(action, title=None, year=None, imdb=None, tvdb=None, source=None, **kwargs):
    try:
        ui.execute('Action(Back,10025)')

        ui.execute('Dialog.Close(okdialog)')

        ui.idle()

        next = [] ; prev = [] ; total = []
        meta = None

        for i in range(1,10000):
            try:
                u = ui.infoLabel('ListItem(%s).FolderPath' % str(i))
                if u in total: raise Exception()
                total.append(u)
                u = dict(urlparse.parse_qsl(u.replace('?','')))
                if 'meta' in u: meta = u['meta']
                u = json.loads(u['source'])[0]
                next.append(u)
            except:
                break
        for i in range(-10000,0)[::-1]:
            try:
                u = ui.infoLabel('ListItem(%s).FolderPath' % str(i))
                if u in total: raise Exception()
                total.append(u)
                u = dict(urlparse.parse_qsl(u.replace('?','')))
                if 'meta' in u: meta = u['meta']
                u = json.loads(u['source'])[0]
                prev.append(u)
            except:
                break

        items = json.loads(source)

        source, quality = items[0]['source'], items[0]['quality']
        items = [i for i in items+next+prev if i['quality'] == quality and i['source'] == source][:10]
        items += [i for i in next+prev if i['quality'] == quality and not i['source'] == source][:10]

        dialog_progress = ui.DialogProgress()
        dialog_progress.create(platform.addonInfo('name'))
        dialog_progress.update(0)

        ui.resolvedPlugin(_thread, True, ui.ListItem(path=''))

        block = None
        for i, source in enumerate(items):
            try:
                dialog_progress.update(100*i/len(items), str(source['label']))
                if source['source'] == block: break

                def dialog_progress_update():
                    return not dialog_progress.iscanceled() and not ui.abortRequested()

                w = source_resolve(source['provider'], source['url'], ui_update=dialog_progress_update)
                if not w: break

                if w.is_alive(): block = source['source']
                url = w.result
                if not url: continue

                try:
                    dialog_progress.close()
                except:
                    pass

                ui.sleep(200)

                media_label = '?'
                if hasattr(url, 'meta') and url.meta:
                    if url.meta['type']: media_label = url.meta['type']
                    if url.meta['width'] and url.meta['height']:
                        media_label += ' %sx%s'%(url.meta['width'], url.meta['height'])

                ui.Player().run(title, year, None, None, imdb, tvdb, meta, url,
                                    credits=_credits_message(source['provider'], source['source'], media_label))

                return
            except:
                pass

        dialog_progress.close()

        raise Exception()
    except:
        ui.infoDialog(_('No stream available'))


def download(action, name=None, provider=None, url=None, image=None, **kwargs):
    ui.busydialog()
    def ui_cancel():
        ui.sleep(1000)
        return not ui.abortRequested()
    w = source_resolve(provider, url, ui_update=ui_cancel)
    ui.busydialog(stop=True)

    if not w or w.is_alive():
        return

    if not isinstance(w.result, basestring):
        ui.infoDialog(_('Not a valid stream'))
        return

    url = w.result
    if not hasattr(url, 'size'):
        media_size = ''
    else:
        media_size = _('Complete file is %dMB')%int(url.size/(1024*1024))
        if hasattr(url, 'acceptbyteranges') and url.acceptbyteranges:
            media_size += ' (r)'
    if not hasattr(url, 'meta'):
        media_format = ''
    else:
        media_format = _('Media format is %s')%url.meta['type']
        if url.meta['width'] and url.meta['height']:
            media_format += ', ' + _('Resolution %dx%d')%(url.meta['width'], url.meta['height'])

    if ui.yesnoDialog(media_size , media_format, _('Continue with download?')):
        if downloader.addDownload(name, url, image):
            ui.infoDialog(_('Item Added to Queue'), name)
        else:
            ui.infoDialog(_('Item Already In Your Queue'), name)


def clearsourcescache(action, **kwargs):
    providers.clear_sources_cache(**kwargs)
    ui.idle()


def _credits_message(provider, host, media_format):
    return [
        '[B]~*~ Credits ~*~[/B]',
        'Source provided by [B]%s[/B]'%provider.split('.')[-1].upper(),
        'Content hosted by [COLOR orange]%s[/COLOR]'%host.upper(),
        '%sLoaded in {elapsed_time} seconds'%('' if not media_format else 'Format is [COLOR FF009933]%s[/COLOR]; '%media_format.upper()),
    ]


def _sources_label(sources, index=0):
    for source in sources:
        index += 1

        s = source['source'].lower()
        p = source['provider'].split('.')[-1]
        q = source['quality']

        label = '%02d' % index

        # Second the quality
        if q in ['1080p', 'HD']: label += ' | [B][I]%s [/I][/B]' % (q)
        else: label += ' | [I]%s [/I]' % (q)

        # Third the provider and source
        label += ' | [B]%s[/B] | %s' % (p, s)

        source['label'] = label.upper()
    return sources


def _source_priority(host, provider, quality_tag=None, resolution=0):
    """Calculate the source priority based on:
    - Stream resolution if derived from the stream metadata
    - Source quality as indicated by the source provider
    - User preference for the source provider
    - User preference for the source host
    """
    # Actual resolution wins all over criteria
    priority = resolution * 1000

    # (fixme) [code]: define the labels as class constants in lib/sources/__init__.py:
    # class SourceQuality:
    #   res_8K = '8K',
    #   res_4K = '4K',
    # ...
    # so that sources/providers modules can use SourceQuality.res_8K as tag
    _quality_priority = {
        '8K': 400,
        '4K': 300,
        '1080p': 200,
        'HD': 100,
        'SD': 0,
    }

    # then use quality tags set by the providers
    priority += _quality_priority.get(quality_tag, 0)

    # then use the user preference for the source providers
    if provider:
        provider = provider.split('.')[-1].lower()
        for top in range(1, 10):
            pref = g2.setting('providers', info='preferred_provider_%d'%top)
            if not pref:
                break
            if pref.lower() == provider:
                priority += 10 * (10 - top)

    # finally use the user preference for the content hosts
    if host:
        host = host.split('.')[-1].lower()
        for top in range(1, 10):
            pref = g2.setting('resolvers', info='preferred_host_%d'%top)
            if not pref:
                break
            if  pref.lower() == host:
                priority += 10 - top

    return priority


def source_resolve(provider, url, ui_update=None):
    thread = workers.Thread(providers.resolve, provider, url)
    thread.start()

    keyboard_opened = False
    ui_cancelled = False
    for x in range(3600):
        key_open = ui.condition('Window.IsActive(virtualkeyboard)')
        if key_open: keyboard_opened = True
        if x > _resolver_timeout and not key_open: break
        if not thread.is_alive(): break
        if ui_update and not ui_update():
            ui_cancelled = True
            break
        ui.sleep(500)

    for x in range(_resolver_timeout):
        if keyboard_opened or ui_cancelled: break
        if not thread.is_alive(): break
        if ui_update and not ui_update():
            ui_cancelled = True
            break
        ui.sleep(500)

    extrainfo = ''
    if ui_cancelled:
        what = 'cancelled by the user after'
    elif thread.is_alive():
        what = 'timeout after'
    elif thread.exc:
        what = 'raised an exception after'
        extrainfo = ' ['+str(thread.exc)+']'
    elif not isinstance(thread.result, basestring):
        what = 'unsuccessfully completed in'
        extrainfo = ' []' if not thread.result else ' '+str(thread.result)
        thread.result = None
    else:
        what = 'successfully completed in'
        try:
            urlparsed = urlparse.urlparse(thread.result)
            host = '%s://%s/.../%s'%(urlparsed.scheme, urlparsed.netloc, urlparsed.path.split('/')[-1])
        except:
            host = thread.result
        extrainfo = ' "'+host+'"'

    log.notice('providers.resolve(%s, %s): %s %.3f secs%s'%(provider, url, what, thread.elapsed(), extrainfo))

    # (fixme): [obs] caching and stats
    # - cache successes and failures for 10mins
    # - keep a statistics of the failed host/domains: total call/success

    return None if ui_cancelled else thread
