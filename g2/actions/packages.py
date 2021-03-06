# -*- coding: utf-8 -*-

"""
    G2 Add-on
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


from g2.libraries import ui
from g2.libraries import log
from g2.libraries import addon
from g2.libraries import client
from g2.libraries.language import _

from g2 import pkg
from g2 import defs

from . import action
from . import tools

from .lib.packagesdialog import PackagesDialog


@action
def dialog():
    win = PackagesDialog('PackagesDialog.xml', addon.PATH, 'Default', '720p',
                         onPackageSelected=_manage_package,
                         pkgInstalledStatus=pkg.status)

    listed = {}
    kinds = {}
    for url in defs.PACKAGES_DIRECTORY_URLS:
        try:
            res = client.get(url)
            pkgentries = client.parseDOM(res.content, 'tbody')[0]
            pkgentries = client.parseDOM(pkgentries, 'tr')
        except Exception:
            log.notice('{m}.{f}: %s: no packages directory found', url)
            continue

        for pkgentry in pkgentries:
            try:
                kind, desc, site = client.parseDOM(pkgentry, 'td')
                log.debug('{m}.{f}: %s %s'%(kind, site))
                if kind not in pkg.kinds():
                    log.notice('{m}.{f}: %s: kind %s not implemented', url, kind)
                    continue

                site = site.replace('<code>', '').replace('</code>', '')
                name, url = pkg.parse_site(site)
                if name is None:
                    log.notice('{m}.{f}: %s: site url %s not implemented', url, site)
                    continue

                html_trans = {
                    '<strong>': '[B]',
                    '</strong>': '[/B]',
                }
                for html_code, kodi_code in html_trans.iteritems():
                    desc = desc.replace(html_code, kodi_code)

                # (fixme) - identify packages to be upgraded and signal them on the GUI.
                # - if a package installed w/ an upgrade is selected, a dialog with:
                #   upgrade - uninstall - cancel is shown
                # - on the dialog place an upgrade all button and a cancel button

                win.addPackage(kind, name, desc, site)

                listed[kind+'.'+name] = True
                kinds[kind] = True
            except Exception:
                pass

    for kind, name in pkg.packages():
        if kind+'.'+name not in listed:
            log.notice('{m}.{f}: orphaned package %s.%s'%(kind, name))
            win.addPackage(kind, name, '[%s] %s'%(_('Orphaned'), name))

    for kind in pkg.kinds():
        if kind in kinds:
            win.addKind(kind)

    win.doModal()

    del win

    pkg.update_settings_skema()

    ui.refresh()


@action
def updatemedia():
    appearance = addon.setting('appearance')
    themes = ui.resource_themes()
    if appearance.lower() not in themes:
        appearance = '-'
        addon.setSetting('appearance', appearance)

    if pkg.update_appearance_setting_skema(themes):
        ui.infoDialog(_('{g2_name} media setting skema updated').format(g2_name=addon.addonInfo('name')))

    tools.settings()


def check_upgrades():
    log.debug('{m}.{f}: called')
    # (fixme) excludive lock with the main thread:
    # - actions threads locks in read mode (multiple)
    # - this thread locks in write mode (only one and no active read)
    # - if the OS doesn't support read/write locks, the auto-upgrade is aborted.

    # for all installed packages,
    # - if the package auto-upgrade setting is enabled, do an _install_package
    #   - If the new version requires additional addons not installed, do not auto-upgrade!


def _manage_package(kind, name, site):
    if pkg.status(kind, name) == 'NotInstalled':
        _install_package(site)
    else:
        _uninstall_package(kind, name, site)


def _install_package(site):
    try:
        progress_dialog = ui.DialogProgressBG()
        progress_dialog.create(site)

        def update_progress_dialog(curitem, numitems=1):
            progress_dialog.update(curitem*100/(numitems if numitems else 1))

        update_progress_dialog(0)
        kind, name = pkg.install_or_update(site, ui_update=update_progress_dialog)

        if not kind:
            raise Exception('package at %s not installed'%site)

        missing_addons = []
        mod = getattr(__import__(pkg.PACKAGES_RELATIVE_PATH+kind, globals(), locals(), [name], -1), name)
        for addon_id in mod.addons if hasattr(mod, 'addons') and mod.addons else []:
            if not addon.condition('System.HasAddon(%s)'%addon_id):
                missing_addons.append(addon_id)

        if not missing_addons:
            pkg.kindinfo(kind, refresh=True)
        else:
            ui.Dialog().ok('PACKAGE MANAGER',
                           '[CR]'.join([m.format(
                               package_name='%s.%s'%(kind, name),
                           ) for m in [
                               _('The {package_name} package requires these addons:'),
                               ' '.join(missing_addons),
                               _('Please, install the missing addons'),   
                           ]]))

        progress_dialog.close()
    except Exception as ex:
        progress_dialog.close()
        log.error('packages.dialog: %s: %s', site, repr(ex))
        ui.infoDialog(_('Package installation failed'))


def _uninstall_package(kind, name, site):
    if not ui.yesnoDialog('[CR]'.join([m.format(
            heading=_('PACKAGE MANAGER'),
            package_name='%s.%s'%(kind, name),
        ) for m in [
            _('About to remove the {package_name} package'),
            _('Are you sure?'),
            _('Please note that this package is missing from the packages directory') if not site else '',
        ]])):
        return

    try:
        pkg.uninstall(kind, name)
        pkg.kindinfo(kind, refresh=True)
    except Exception as ex:
        log.error('packages.dialog: %s.%s: %s', kind, name, repr(ex))
        ui.infoDialog(_('Package removal failed'))
