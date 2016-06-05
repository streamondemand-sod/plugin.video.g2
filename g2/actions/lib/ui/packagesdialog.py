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


import xbmc
import xbmcgui

import g2

from g2.libraries import log
from g2.libraries.language import _

from . import DialogProgressBG, infoDialog, yesnoDialog


__all__ = ['PackagesDialog']


_log_debug = True


class PackagesDialog(xbmcgui.WindowXMLDialog):
    kinds_listid = 101
    packages_listid = 201

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):
        self.kinds = []
        self.packages = []
        self.kinds_lst = None
        self.packages_lst = None
        self.progress_dialog = None
        self.displayed_kind = None

    def onInit(self):
        self.kinds_lst = self.getControl(self.kinds_listid)
        self.packages_lst = self.getControl(self.packages_listid)
        self.kinds_lst.reset()
        self.kinds_lst.addItems(self.kinds)
        dummy = [_update_package_item(i) for i in self.packages]
        self._update_packages_list('providers')

    def onClick(self, controlID):
        log.debug('onClick: %s', controlID)
        if controlID == self.kinds_listid:
            kind = self.kinds_lst.getSelectedItem().getLabel().lower()
            self._update_packages_list(kind)

        elif controlID == self.packages_listid:
            item = self.packages_lst.getSelectedItem()
            kind = item.getProperty('kind')
            name = item.getProperty('name')

            if not g2.is_installed(kind, name):
                self.progress_dialog = DialogProgressBG()
                self.progress_dialog.create(_('Download Package')+' '+name)
                self._update_progress_dialog(0)
                if g2.install_or_update(kind, name, item.getProperty('site'), self._update_progress_dialog):
                    _update_package_item(item, 'true')
                self.progress_dialog.close()
                try:
                    missing = []
                    kindmod = __import__('g2.%s'%kind, globals(), locals(), [name], -1)
                    pkgmod = getattr(kindmod, name)
                    for addon in pkgmod.addons if pkgmod.addons else []:
                        if not xbmc.getCondVisibility('System.HasAddon(%s)'%addon):
                            missing.append(addon)
                    if not missing:
                        kindmod.info(force=True)
                    else:
                        xbmcgui.Dialog().ok('PACKAGE MANAGER', '[CR]'.join([
                            _('The installed package requires these addons:'),
                            ' '.join(missing),
                            _('Please, install them'),
                            ]))
                except Exception as ex:
                    log.error('packages.dialog: %s', ex)
                    infoDialog(_('Failure to load the package'))

            # (fixme) warn if the package is orphaned...
            elif yesnoDialog(_('Are you sure?'), '', '', heading=_('Uninstall Package')+' '+name) and g2.uninstall(kind, name):
                _update_package_item(item, 'false')
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
            self.packages_lst.reset()
            self.packages_lst.addItems([i for i in self.packages if i.getProperty('kind') == kind])
            self.displayed_kind = kind

def _update_package_item(item, installed=None):
    if installed:
        item.setProperty('installed', installed)
    item.setInfo('video', {'overlay': 5 if item.getProperty('installed') == 'true' else 4})
