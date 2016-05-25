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


import datetime
import urlparse

import xbmc
import xbmcgui

from g2.libraries import log
from g2.libraries import workers


# TODO[contrib]: cloneit or keep this url?!?
_host_images = "https://offshoregit.com/boogiepop/dataserver/ump/images/"


class SourcesDialog(xbmcgui.WindowXMLDialog):
    title_label_id = 1
    progress_id = 2
    elapsed_label_id = 3
    progress_label_id = 4
    left_image_id = 11
    left_label_id = 12
    list_id = 21
    counter_label_id = 22
    info_label_id = 23
    ok_button_id = 31
    stop_button_id = 32
    cancel_button_id = 33

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback,
                 sourcesGenerator=None, sourcePriority=None, sourceResolve=None, posterData=None):
        self.title_label = None
        self.progress = None
        self.elapsed_label = None
        self.progress_label = None
        self.list = None
        self.counter_label = None
        self.info_label = None
        self.ok_button = None
        self.stop_button = None
        self.left_image = None
        self.left_label = None

        self.items = []

        self.resolver_lock = workers.Lock()

        self.list_focused = False
        self.ok_button_focused = False
        self.stop_button_flag = False
        self.dialog_closed = False
        self.selected = None
        self.start_time = None

        self.thread = None
        self.sources_generator = sourcesGenerator
        self.source_priority = sourcePriority
        self.source_resolve = sourceResolve
        self.posterdata = posterData

    def close(self):
        self.dialog_closed = True
        xbmcgui.WindowXMLDialog.close(self)

    def addItems(self, items):
        for source in items:
            item = xbmcgui.ListItem()
            item.setLabel(source['label'])
            item.setIconImage(_host_images+source['source'].lower()+'.png')
            item.setProperty('source_provider', source['provider'])
            item.setProperty('source_quality', source['quality'])
            item.setProperty('source_host', source['source'])
            item.setProperty('source_info', source['info'])
            item.setProperty('source_url', source['url'])
            item.setProperty('url', '')
            item.setProperty('resolution', '0')
            self.items.append(item)

    def onInit(self):
        log.notice('onInit')

        self.ok_button_focused = False
        self.stop_button_flag = False
        self.dialog_closed = False
        self.selected = None
        self.start_time = None

        self.title_label = self.getControl(self.title_label_id)
        self.list = self.getControl(self.list_id)
        self.counter_label = self.getControl(self.counter_label_id)
        self.info_label = self.getControl(self.info_label_id)
        self.progress = self.getControl(self.progress_id)
        self.elapsed_label = self.getControl(self.elapsed_label_id)
        self.progress_label = self.getControl(self.progress_label_id)
        self.ok_button = self.getControl(self.ok_button_id)
        self.stop_button = self.getControl(self.stop_button_id)
        self.left_image = self.getControl(self.left_image_id)
        self.left_label = self.getControl(self.left_label_id)
        if not self.posterdata:
            self.left_image.setImage(platform.addonPoster())
            self.left_label.setLabel('')
        elif self.posterdata.startswith('poster://'):
            self.left_image.setImage(self.posterdata[9:])
            self.left_label.setLabel('')
        else:
            self.left_image.setImage(platform.addonPoster())
            self.left_label.setLabel(self.posterdata)

        self.updateDialog()

        if not self.thread:
            self.thread = workers.Thread(self.sources_worker)
            self.thread.start()

    def onClick(self, controlID):
        log.notice('onClick: %s'%controlID)
        if controlID == self.list_id:               # Selected source: looks for it...
            selected = self.list.getSelectedItem()
        elif controlID == self.ok_button_id:        # OK button: looks for the best source...
            selected = self.list.getListItem(0)
        elif controlID == self.cancel_button_id:    # Cancel button: close without any selection
            self.close()
            return
        elif controlID == self.stop_button_id:
            self.stop_button_flag = True
            return
        else:
            return
        while not selected.getProperty('url'):
            xbmc.executebuiltin('ActivateWindow(busydialog)')
            self.resolver(selected)
            if selected.getProperty('url'):         # Found a good source: close with the selected item
                break
            self.updateDialog()                     # No more sources: close without any selection
            if controlID == self.ok_button_id:      # Failed source; looks for the next best source...
                selected = self.list.getListItem(0)
            else:                                   # Failed source; notify that it was not good
                xbmcgui.Dialog().notification(platform.addonInfo('name'), 'Source not valid', platform.addonIcon(), 3000, sound=False)
                xbmc.executebuiltin('Dialog.Close(busydialog)')
                return
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        self.selected = selected
        self.close()

    def onAction(self, action):
        if self.list_focused:
            self.info_label.setLabel(self.list.getSelectedItem().getProperty('source_info'))
        xbmcgui.WindowXMLDialog.onAction(self, action)

    def onFocus(self, controlID):
        log.notice('onFocus: %s'%controlID)
        if controlID == self.ok_button_id:
            self.list.selectItem(0)
        self.list_focused = controlID == self.list_id

    def sources_worker(self):
        if self.sources_generator:
            log.notice('sources.dialog: sources_worker: calling the source generator function')
            self.updateDialog(title='SEARCHING SOURCES', elapsed_time=True)
            self.sources_generator(self)
            self.sources_generator = None

        log.notice('sources.dialog: sources_worker: %d url listed, %d already processed (OK/KO: %d/%d)'%(
                   len(self.items),
                   len([i for i in self.items if i.getProperty('url') or not i.getProperty('source_url')]),
                   len([i for i in self.items if i.getProperty('url')]),
                   len([i for i in self.items if not i.getProperty('source_url')])))

        if not len(self.items):
            self.stop_button_flag = True
            self.updateDialog(title='NO SOURCES'+('' if self.sources_generator else ' FOUND'), elapsed_time=False)
            return

        self.updateDialog(title='CHECKING SOURCES', elapsed_time=True)

        self.stop_button_flag = False
        all_sources_resolved = False
        while not self.dialog_closed and not self.stop_button_flag:
            all_sources_resolved = True
            for index in range(len(self.items)):
                try:
                    item = self.list.getListItem(index)
                except:
                    break
                if item.getProperty('source_url') and not item.getProperty('url'):
                    all_sources_resolved = False
                    break
            if all_sources_resolved:
                break

            self.resolver(item)
            self.updateDialog()
            xbmc.sleep(500)

        self.updateDialog(elapsed_time=False)

        if self.dialog_closed:
            status = 'DIALOG CLOSED'
        else:
            if all_sources_resolved:
                status = 'CHECKING COMPLETE'
            elif self.stop_button_flag:
                status = 'CHECKING STOPPED'
            self.stop_button_flag = True
            self.updateDialog(title='SELECT SOURCE', progress=status)

        log.notice('sources.dialog: sources_worker stopped (%s): %d url listed, %d processed (OK/KO: %d/%d)'%(
                   status,
                   len(self.items),
                   len([i for i in self.items if i.getProperty('url') or not i.getProperty('source_url')]),
                   len([i for i in self.items if i.getProperty('url')]),
                   len([i for i in self.items if not i.getProperty('source_url')])))
        self.thread = None

    def resolver(self, item):
        # Ensure that only one thread is resolving
        if not self.source_resolve:
            item.setProperty('url', item.getProperty('source_url'))
            return
        with self.resolver_lock:
            log.notice('sources.dialog: resolving %s...'%item.getLabel())
            provider = item.getProperty('source_provider')
            url = item.getProperty('source_url')
            label = item.getLabel()
            label_fmt = '[COLOR FF009933][%s][/COLOR] %s'
            self.ellipsis = 0
            def item_label_update():
                self.ellipsis %= 3
                self.ellipsis += 1
                item.setLabel(label_fmt%('.' * self.ellipsis, label))
                return not self.dialog_closed

            item_label_update()
            t = self.source_resolve(provider, url, ui_update=item_label_update)

            # NOTE: a URL is considered not resolved if:
            # - The resolver thread has been cancelled or
            # - The resolver thread is still running (hence it timeout) or
            # - The resolver failed the resolution or
            # - The url resolved to plugin://
            if not t or t.is_alive() or not t.result or t.result.startswith('plugin://'):
                item.setProperty('source_url', '')
            else:
                url = t.result
                item.setProperty('url', url)
                media_label = '?'
                if hasattr(url, 'meta') and url.meta:
                    if url.meta['type']: media_label = url.meta['type']
                    if url.meta['width'] and url.meta['height']:
                        media_label += ' %sx%s'%(url.meta['width'], url.meta['height'])
                        item.setProperty('media', media_label)
                        item.setProperty('resolution', str(url.meta['width']*url.meta['height']))
                item.setLabel(label_fmt%(media_label.upper(), label))

            log.notice('sources.dialog: completed %s: %s'%(label, 'OK' if item.getProperty('url') else 'KO'))

    def updateDialog(self, title=None, progress=None, elapsed_time=None):
        if title: self.title_label.setLabel(title)

        if elapsed_time is not None:
            self.start_time = None if not elapsed_time else datetime.datetime.now()
        self.elapsed_label.setLabel('' if not self.start_time else '%ds'%(datetime.datetime.now()-self.start_time).seconds)

        if progress is None:
            progress = len([i for i in self.items if i.getProperty('url') or not i.getProperty('source_url')])
            total = len(self.items)
        elif type(progress) in [list, tuple]:
            progress, total = progress
        else:
            total = None
        if total:
            self.progress.setPercent(100 * progress / total)
            self.progress_label.setLabel('%d / %d'%(progress, total))
        elif progress:
            self.progress_label.setLabel(progress)

        items_active = [i for i in self.items if i.getProperty('source_url')]
        last_selected_position = self.list.getSelectedPosition()
        self.list.reset()
        if callable(self.source_priority):
            items_active = sorted(items_active,key=lambda i: self.source_priority(i.getProperty('source_host'),
                                                                i.getProperty('source_provider'),
                                                                i.getProperty('source_quality'),
                                                                int(i.getProperty('resolution'))), reverse=True)
        self.list.addItems(items_active)
        if last_selected_position >= 0:
            self.list.selectItem(last_selected_position)

        if self.items and not items_active:
            self.title_label.setLabel('NO VALID SOURCES')

        self.counter_label.setLabel('' if len(items_active) <= 10 else '%d'%len(items_active))

        self.ok_button.setEnabled(len(items_active) > 0)
        if len(items_active) > 0 and not self.ok_button_focused:
            self.setFocus(self.ok_button)
            self.ok_button_focused = True

        self.stop_button.setEnabled(not self.stop_button_flag)
