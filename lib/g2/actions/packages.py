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

import ast

import xbmc
import xbmcaddon
import xbmcgui

import g2

from g2.libraries import log
from g2.libraries import client2
from g2.libraries import platform
from g2.libraries.language import _
from .lib import ui


_log_debug = True

_DEFAULT_PACKAGES_URLS = ['http://j0rdyz65.github.io/']


# (fixme) [code] move PackagesDialog class to resources.lib.ui.kodi.g2.py
class PackagesDialog(xbmcgui.WindowXMLDialog):
    kinds_listid = 101
    packages_listid = 201

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):
        self.kinds = []
        self.packages = []
        self.kindslst = None
        self.packageslst = None
        self.progress_dialog = None
        self.displayed_kind = None

    def onInit(self):
        self.kindslst = self.getControl(self.kinds_listid)
        self.packageslst = self.getControl(self.packages_listid)
        self.kindslst.reset()
        self.kindslst.addItems(self.kinds)
        self._update_packages_list('providers')

    def onClick(self, controlID):
        log.debug('onClick: %s', controlID)
        if controlID == self.kinds_listid:
            kind = self.kindslst.getSelectedItem().getLabel().lower()
            self._update_packages_list(kind)

        elif controlID == self.packages_listid:
            item = self.packageslst.getSelectedItem()
            kind = item.getProperty('kind')
            name = item.getProperty('name')
            if not g2.is_installed(kind, name):
                self.progress_dialog = ui.DialogProgressBG()
                self.progress_dialog.create(_('Download Package')+' '+name)
                self._update_progress_dialog(0)
                if g2.install_or_update(kind, name, item.getProperty('site'), self._update_progress_dialog):
                    _set_item_installed_status(item, True)
                self.progress_dialog.close()
                try:
                    missing = []
                    kindmod = __import__('g2.%s'%kind, globals(), locals(), [name], -1)
                    pkgmod = getattr(kindmod, name)
                    for addon in pkgmod.addons if pkgmod.addons else []:
                        if not xbmc.getCondVisibility('System.HasAddon(%s)'%addon):
                            missing.append(addon)
                    if not missing:
                        kindmod.info()
                    else:
                        xbmcgui.Dialog().ok('PACKAGE MANAGER', '[CR]'.join([
                            _('The installed package requires these addons:'),
                            ' '.join(missing),
                            _('Please, install them'),
                            ]))
                except Exception as ex:
                    log.error('packages.dialog: %s', ex)
                    ui.infoDialog(_('Failure to load the package'))

            elif ui.yesnoDialog(_('Are you sure?'), '', '', heading=_('Uninstall Package')+' '+name) and g2.uninstall(kind, name):
                _set_item_installed_status(item, False)
                if not item.getProperty('site'):
                    self.packages = [i for i in self.packages if i.getProperty('kind') != kind or i.getProperty('name') != name]
                    self._update_packages_list(force=True)
                try:
                    kindmod = getattr(__import__('g2', globals(), locals(), [kind], -1), kind)
                    kindmod.info()
                except Exception as ex:
                    log.error('packages.dialog: %s', ex)

    def _update_progress_dialog(self, curitem, numitems=1):
        self.progress_dialog.update(curitem*100/(numitems if numitems else 1))

    def _update_packages_list(self, kind=None, force=False):
        if self.displayed_kind != kind or force:
            if not kind:
                kind = self.displayed_kind
            self.packageslst.reset()
            self.packageslst.addItems([i for i in self.packages if i.getProperty('kind') == kind])
            self.displayed_kind = kind


def _set_item_installed_status(item, installed):
    if str(installed) != item.getProperty('installed'):
        item.setProperty('installed', str(installed))
        item.setInfo('video', {'overlay': 5 if installed else 4})


def dialog(**kwargs):
    addon_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path'))
    win = PackagesDialog('PackagesDialog.xml', addon_dir, 'Default', '720p')

    try:
        packages_urls = ast.literal_eval(platform.setting('packages_urls'))
        if not packages_urls:
            raise Exception()
    except Exception:
        packages_urls = _DEFAULT_PACKAGES_URLS

    listed = {}
    kinds = {}
    for url in packages_urls:
        try:
            res = client2.get(url, debug=True)
            res = client2.parseDOM(res.content, 'tbody')[0]
            res = client2.parseDOM(res, 'tr')
        except Exception:
            log.notice('{m}.{f}: %s: no packages directory found', url)
            continue

        for pkg in res:
            try:
                kind, desc, site = client2.parseDOM(pkg, 'td')
                log.debug('{m}.{f}: %s %s'%(kind, site))
                if kind not in g2.kinds():
                    log.notice('{m}.{f}: %s: kind %s not implemented', url, kind)
                    continue
 
                site = site.replace('<code>', '').replace('</code>', '')
                name = g2.local_name(site)
                if name is None:
                    log.notice('{m}.{f}: %s: site url %s not implemented', url, site)
                    continue

                html_trans = {
                    '<strong>': '[B]',
                    '</strong>': '[/B]',
                }
                for html_code, kodi_code in html_trans.iteritems():
                    desc = desc.replace(html_code, kodi_code)

                item = ui.ListItem()
                item.setLabel(desc)
                _set_item_installed_status(item, g2.is_installed(kind, name))
                item.setProperty('kind', kind)
                item.setProperty('name', name)
                item.setProperty('site', site)
                win.packages.append(item)

                listed[kind+'.'+name] = True
                kinds[kind] = True
            except Exception:
                pass

    for kind, name in g2.packages():
        if kind+'.'+name not in listed:
            log.notice('{m}.{f}: orphaned package %s.%s'%(kind, name))
            item = ui.ListItem()
            item.setLabel(_('[Orphaned]')+' '+name)
            _set_item_installed_status(item, True)
            item.setProperty('kind', kind)
            item.setProperty('name', name)
            win.packages.append(item)

    for kind in g2.kinds():
        if kind in kinds:
            item = ui.ListItem()
            item.setLabel(kind.upper())
            win.kinds.append(item)

    win.doModal()

    g2.update_settings_skema()

    del win
