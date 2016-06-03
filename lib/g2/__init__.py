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


import os
import re
import sys
import json
import errno
import hashlib
import urllib2

import importer

from g2.libraries import log
from g2.libraries import cache
from g2.libraries import client
from g2.libraries import platform
from g2.libraries import language


_log_debug = True


_PACKAGES_KINDS = {
    'providers': {
        'order': 1,
        # User setting are generated for each package / module to enable/disable it
        'settings_category': language.msgcode('Sources'),
        # User settings are generated at the package kind level (e.g. providers:::id)
        # See the code below
        'settings': {},
    },
    'resolvers': {
        'order': 2,
        # User setting are generated for each package / module to enable/disable it
        # For resolvers, if there is a single module in the package,
        # the module setting is not displated.
        'settings_category': language.msgcode('Resolvers'),
        # User settings are generated at the package kind level (e.g. resolvers:::id)
        # See the code below
        'settings': {},
    },
    'dbs': {
        'order': 3,
        # No user settings
        'settings_category': 0,
    },
    'notifiers': {
        'order': 4,
        # No user settings
        'settings_category': 0,
    },
    'actions': {
        'order': 5,
        # No user settings
        'settings_category': 0,
    },
}

def _fill_packages_kinds():
    def _ordinal(num):
        return "%d%s" % (num, "tsnrhtdd"[(num/10%10 != 1)*(num%10 < 4)*num%10::4])

    for kind, name in [('providers', 'provider'), ('resolvers', 'host')]:
        settings = _PACKAGES_KINDS[kind]['settings']
        for i in range(1, 5):
            msgcode = language.msgcode('%s preferred source %s'%(_ordinal(i), name))
            if not msgcode:
                break
            settings['preferred_provider_%d'%i] = {
                'template': 'type="select" label="%s" values="-|{modules_names}"'%msgcode,
                'default': '-',
            }

# python2.6 doesn't support {} comprehensions
_fill_packages_kinds()

_RESOURCES_PATH = os.path.join(platform.addonInfo('path'), 'resources') 

# NOTE: This is the path relative to the one present in sys.path.
# Remember to update it if you move the hierarchy around relative to sys.path
_PACKAGES_RELATIVE_PATH = 'g2.'
# _PACKAGES_ABSOLUTE_PATH = os.path.join(platform.addonInfo('path'), 'lib', *_PACKAGES_RELATIVE_PATH.split('.'))
_PACKAGES_ABSOLUTE_PATH = __path__[0]


# (fixme) [code]: use contextmanager decorator: https://docs.python.org/2.6/library/contextlib.html
class Context:
    def __init__(self, kind, package=None, modules=[], search_paths=[], ignore_exc=False):
        self.kind = kind.split('.')[-1]
        self.fullname = _PACKAGES_RELATIVE_PATH + self.kind
        if package:
            self.fullname += '.' + package
        self.modules = modules
        self.search_paths = search_paths
        self.ignore_exc = ignore_exc
        self.stdout = None
        self.stderr = None
        self.urllib2_opener = None

    def __enter__(self):
        """Build the right context for executing the package methods"""
        for path in self.search_paths:
            sys.path.insert(0, path)
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = sys.stdout
        self.urllib2_opener = urllib2._opener #pylint: disable=W0212
        urllib2.install_opener(None)
        try:
            if self.modules == []:
                log.debug('%s: import %s'%(self.kind, self.fullname))
            else:
                log.debug('%s: from %s import %s'%(self.kind, self.fullname, ', '.join(self.modules)))
            mod = __import__(self.fullname, globals(), locals(), self.modules, -1)
        except Exception as ex:
            self.__exit__(None, None, None)
            if self.modules == []:
                log.error('%s: import %s: %s', self.kind, self.fullname, ex, trace=True)
            else:
                log.error('%s: from %s import %s: %s', self.kind, self.fullname, ', '.join(self.modules), ex, trace=True)
            return None

        if not self.modules:
            for module in self.fullname.split('.')[1:]:
                mod = getattr(mod, module)
            return mod
        else:
            return [getattr(mod, module) for module in self.modules]

    def __exit__(self, exc_type, exc_value, traceback):
        """Restore the previous context after the execution of the package methods"""
        urllib2.install_opener(self.urllib2_opener)
        sys.stdout.close()
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        # (fixme) [logic]: remove excactly the path il self.search_paths starting from the topmost!
        for dummy_path in self.search_paths:
            sys.path.pop(0)
        if not self.ignore_exc and exc_value:
            log.notice('%s: %s', self.fullname, exc_value, trace=True)
        return True


def local_name(site):
    if site.startswith('github://'):
        url = site.split('/')
        return '%s_by_%s_at_github'%(url[-1].lower(), url[2].lower())
    else:
        return None


def kinds():
    return [k for k, dummy_v in sorted(_PACKAGES_KINDS.items(), key=lambda i: i[1]['order'])]


def packages(kinds_=kinds()):
    for kind in kinds_:
        kind = kind.split('.')[-1]
        for dummy_package, name, is_pkg in importer.walk_packages([os.path.join(_PACKAGES_ABSOLUTE_PATH, kind)]):
            if is_pkg and name != 'lib':
                yield kind, name


def is_installed(kind, name):
    return os.path.exists(os.path.join(_path(kind, name), ''))


def _path(kind, name):
    return os.path.join(_PACKAGES_ABSOLUTE_PATH, kind, name)


def install_or_update(kind, name, site, gui_update=None):
    try:
        if not site.startswith('github://'):
            raise
        url = site.split('/')
        site = 'https://api.github.com/repos/' + '/'.join(url[2:4]) + '/contents/' + '/'.join(url[4:])
    except Exception:
        return False

    try:
        repo = json.loads(client.request(site))
    except Exception as ex:
        log.error('g2.install %s.%s: failed download from %s: %s'%(kind, name, site, ex))
        return False

    package_path = os.path.join(_PACKAGES_ABSOLUTE_PATH, kind, name)
    try:
        platform.makeDir(package_path)
    except Exception as ex:
        log.error('name %s.%s: %s'%(kind, name, ex))

    def git_sha(path):
        try:
            sha1 = hashlib.sha1()
            with open(path, 'rb') as fil:
                data = fil.read()
            sha1.update("blob " + str(len(data)) + "\0" + data)
            return sha1.hexdigest()
        except Exception:
            return None

    actives = []
    for i, mod in enumerate(repo):
        try:
            if mod['type'] == 'dir':
                install_or_update(kind, '%s/%s'%(name, mod['name']), '%s/%s'%(site, mod['name']))
            else:
                module_path = os.path.join(package_path, mod['name'])
                if mod['sha'] != git_sha(module_path):
                    module = client.request(mod['download_url'])
                    module_path_new = module_path + '.new'
                    with open(module_path_new, 'w') as fil:
                        fil.write(module)
                    if mod.get('sha') == git_sha(module_path_new):
                        os.rename(module_path_new, module_path)
                        log.notice('g2.install %s.%s: %s'%(kind, name, mod['name']))

            actives.append(mod['name'])
            if gui_update:
                gui_update(i+1, len(repo))
        except Exception as ex:
            log.error('g2.install %s.%s.%s: %s'%(kind, name, mod.get('name'), ex))

    for mod in os.listdir(package_path):
        if mod not in actives and not re.search(r'\.py[co]$', mod):
            module_path = os.path.join(package_path, mod)
            try:
                log.notice('g2.install %s.%s: %s is obsolete, removing it...'%(kind, name, mod))
                _remove(module_path)
                if re.search(r'\.py$', mod):
                    _remove(os.path.join(module_path+'c'))
                    _remove(os.path.join(module_path+'o'))
            except Exception as ex:
                log.error('g2.install %s.%s.%s: %s'%(kind, name, mod, ex))

    return True


def uninstall(kind, name):
    try:
        return _remove(_path(kind, name))
    except Exception as ex:
        log.error('g2.uninstall %s.%s: %s'%(kind, name, ex))
        return False


def info(kind, infofunc):
    kind = kind.split('.')[-1]
    response_infos = {}
    try:
        infos_paths, infos_modules = cache.get(_info_get, 1, kind, infofunc, hash_args=1, response_info=response_infos) 
        if 'cached' in response_infos:
            log.debug('{m}.{f}: info cached %s, paths=%s', response_infos['cached'], infos_paths)
            update_needed = False
            for path in infos_paths:
                try:
                    if not os.path.exists(path) or platform.Stat(path).st_mtime() > response_infos['cached']:
                        raise
                except Exception:
                    update_needed = True
            if update_needed:
                infos_paths, infos_modules = cache.get(_info_get, 0, kind, infofunc, hash_args=1)
    except Exception as ex:
        log.error('packages.info(%s): %s', kind, ex, trace=True)
        return {}

    return infos_modules


def _info_get(kind, infofunc):
    def addonSettingsFile(addon_id=''):
        return os.path.join(platform.addonInfo2(addon_id, 'profile').decode('utf-8'), 'settings.xml')

    def ignore(dummy_name):
        pass

    if not os.path.isdir(_PACKAGES_ABSOLUTE_PATH):
        log.error('_info_get: %s: packages directory not found', _PACKAGES_ABSOLUTE_PATH)
        return ([], [])

    infos_paths = set()
    infos_paths.add(addonSettingsFile())
    infos_modules = {}
    for dummy_package, name, is_pkg in importer.walk_packages([os.path.join(_PACKAGES_ABSOLUTE_PATH, kind)], onerror=ignore):
        log.debug('{m}.{f}: name=%s.%s, is_pkg=%s, enabled=%s'%(kind, name, is_pkg, setting(kind, name, name='enabled')))

        if '.' in name or (is_pkg and name == 'lib'):
            continue

        if not is_pkg:
            _info_get_module(infofunc, infos_modules, kind, name)
            continue

        if setting(kind, name, name='enabled') == 'false':
            log.notice('{m}: package %s ignored, user enable setting is %s'%(name, setting(kind, name, name='enabled')))
            continue

        with Context(kind, name) as pac:
            if not pac:
                continue

            if not hasattr(pac, 'site'):
                log.debug('{m}.{f}: %s package %s does not specify a site origin; skip it!', kind, name)
                continue

            addonpaths = []
            if hasattr(pac, 'addons') and pac.addons:
                required_addons_installed = True
                addon_ids = [pac.addons] if isinstance(pac.addons, basestring) else pac.addons
                for addon_id in addon_ids:
                    if not platform.condition('System.HasAddon(%s)'%addon_id):
                        required_addons_installed = False
                    else:
                        addonpaths.extend(_get_addon_paths(addon_id))
                        infos_paths.add(addonSettingsFile(addon_id))
                    log.debug('{m}.{f}: package=%s.%s, addon=%s, paths=%s'%(kind, name, addon_id, addonpaths))

                if not required_addons_installed:
                    log.notice('{m}: %s: required addons (%s) not installed'%(name, ', '.join(pac.addons)))
                    continue
            addonpaths = addonpaths[0:1] + list(set(addonpaths[1:]))

            infos_paths.add(os.path.join(_PACKAGES_ABSOLUTE_PATH, kind, name))

            for dummy_package, sname, is_pkg in importer.walk_packages(pac.__path__, onerror=ignore):
                log.debug('{m}.{f}: sname=%s is_pkg=%s enabled=%s'%(sname, is_pkg, setting(kind, name, sname, name='enabled')))

                # (fixme) found a way to disable providers configured with content == none
                if is_pkg or '.' in sname or setting(kind, name, sname, name='enabled') == 'false':
                    if not is_pkg and '.' not in sname:
                        log.debug('{m}.{f}: module %s.%s ignored, user enable setting is %s',
                                  name, sname, setting(kind, name, sname, name='enabled'))
                    continue

                _info_get_module(infofunc, infos_modules, kind, sname, name, addonpaths)

    return (infos_paths, infos_modules)


def _info_get_module(infofunc, infos, kind, module, package='', paths=[]):
    log.debug('{m}.{f}: %s.%s%s', kind, package+'.' if package else '', module)
    with Context(kind, package, [module], paths) as mods:
        if not mods:
            return
        try:
            # (fixme) [code] if infofunc is missing, use a default version that looks for the packages infos:
            # - callable(m.info) returning a dict or [] of dicts
            # - list(m.INFO)
            # - dict(m.INFO)
            # Uniform all the g2.packages and integrated modules developed so far
            nfo = infofunc(package, module, mods[0], paths)
        except Exception as ex:
            log.error('{m}: infofunc(%s, %s, ...): %s', package, module, ex, trace=True)
            nfo = []

        log.debug('{m}.{f}: nfo=%s', nfo)
        for i in nfo:
            fullname = ('' if not package else package+'.') + module + ('' if 'name' not in i else '.'+i['name'])
            infos[fullname] = dict(i)
            if package:
                infos[fullname]['package'] = package
            infos[fullname].update({
                'search_paths': paths,
                'module': module,
                'name': fullname,
                'setting_enable': i.get('setting_enable', False),
            })


def update_settings_skema():
    settings = {}
    templates = {}
    defaults = {}
    def add_setting(name, default, kind, package='', module='', template=None):
        setid = _setting_id(kind, package, module, name)
        settings[setid] = platform.setting(setid)
        if settings[setid] == '':
            settings[setid] = default
            platform.setSetting(setid, default)
        defaults[setid] = default
        if template:
            templates[setid] = template

    for kind, kindesc in _PACKAGES_KINDS.iteritems():
        log.debug('update_settings_skema: kind=%s, kindesc=%s'%(kind, kindesc))
        if not kindesc['settings_category']:
            continue    # This kind of packages doesn't require any setting

        if 'settings' in kindesc:
            import_path = _PACKAGES_RELATIVE_PATH+kind
            mod = __import__(import_path, globals(), locals(), [], -1)
            for module in import_path.split('.')[1:]:
                mod = getattr(mod, module)

            modules_names = sorted(set([nfo.split('.')[-1] for nfo in mod.info()]))
            for setid, template in kindesc['settings'].iteritems():
                add_setting(setid, template['default'], kind,
                            template=template['template'].format(
                                modules_names='|'.join(modules_names),
                            ))

        for dummy_imp, name, is_pkg in importer.walk_packages([os.path.join(_PACKAGES_ABSOLUTE_PATH, kind)]):
            log.debug('update_settings_skema: name=%s, is_pkg=%s'%(name, is_pkg))

            if not is_pkg or '.' in name or name == 'lib':
                continue

            add_setting('enabled', 'true', kind, name)
            add_setting('priority', '10', kind, name)
            for dummy_imp, sname, is_pkg in importer.walk_packages([os.path.join(_PACKAGES_ABSOLUTE_PATH, kind, name)]):
                log.debug('update_settings_skema: name=%s.%s, is_pkg=%s'%(name, sname, is_pkg))
                if is_pkg or '.' in sname:
                    continue
                add_setting('enabled', 'true', kind, name, sname)

    settings_skema_path = os.path.join(_RESOURCES_PATH, 'settings.xml')
    new_settings_skema = ''
    with open(settings_skema_path) as fil:
        suppress_skema = False
        line = ''
        for line in fil:
            if any('label="%s"'%d['settings_category'] in line for d in _PACKAGES_KINDS.itervalues()):
                suppress_skema = True
            if '</settings>' in line:
                break
            if not suppress_skema:
                new_settings_skema += line

        current_category = None
        settings_ids = sorted(settings.keys())
        for index, setid in enumerate(settings_ids):
            category = setid.split(':')[0]
            default_value = defaults[setid]
            if category != current_category:
                if current_category:
                    new_settings_skema += '\t</category>\n'
                new_settings_skema += '\t<category label="%s">\n'%_PACKAGES_KINDS[category]['settings_category']
                current_category = category
                current_package = None

            if ':::' in setid:
                new_settings_skema += '\t\t<setting id="%s" %s default="%s" />\n'%(
                    setid, templates[setid] if setid in templates else
                    'type="text" label="%s"'%setid.split(':')[-1], default_value)
                current_package = '-'

            elif setid.endswith('::enabled'):
                if current_package:
                    new_settings_skema += '\t\t<setting type="lsep" label="[CR]" />\n'
                new_settings_skema += '\t\t<setting id="%s" type="bool" label="%s" default="%s" />\n'%(
                    setid, setid.split(':')[1].title().replace('_', ' '), default_value)
                current_package = setid.split(':')[0:2]
                current_module = 0

            elif setid.endswith('::priority'):
                current_module += 1
                # (fixme)[int]: localize the label
                new_settings_skema += '\t\t<setting id="%s" type="number" label="Priority" default="%s" enable="eq(-%d,true)" subsetting="true" />\n'%(
                    setid, default_value, current_module)

            else:
                current_module += 1
                if category in ['resolvers']:
                    settype = 'bool'
                    setlvalues = ''
                    visible = 'true' if current_module > 2 or (index < len(settings_ids)-1 and settings_ids[index+1].split(':')[0:2] == current_package) else 'false'

                elif category in ['providers']:
                    settype = 'enum'
                    setlvalues = 'lvalues="%s" '%('|'.join([str(language.msgcode(t)) for t in ['None', 'Movies&TV', 'Movies', 'TV'] if language.msgcode(t)]))
                    visible = 'true'

                new_settings_skema += '\t\t<setting id="%s" type="%s" label="%s" %sdefault="%s" enable="eq(-%d,true)" visible="%s" subsetting="true" />\n'%(
                                        setid, settype, setid.split(':')[2].title(), setlvalues, default_value, current_module, visible)

        if current_category:
            new_settings_skema += '\t</category>\n'

        # Collect the rest of the settings file
        new_settings_skema += line
        for line in fil:
            new_settings_skema += line

    # log.debug(new_settings_skema)
    if new_settings_skema != '':
        with open(settings_skema_path, 'w') as fil:
            fil.write(new_settings_skema)


def _remove(path):
    if not os.path.isdir(path):
        try:
            platform.removeFile(path)
        except OSError as ex:
            if ex.errno != errno.ENOENT:
                raise
        return True
    directories, filenames = platform.listDir(path)
    for directory in directories:
        _remove(os.path.join(path, directory))
    for filename in filenames:
        platform.removeFile(os.path.join(path, filename))
    return platform.removeDir(path)


def setting(kind, package='', module='', name='enabled'):
    if not _PACKAGES_KINDS[kind]['settings_category']:
        # Implicit setting values for kind packages missing user settings
        return 'true' if name == 'enabled' else '10' if name == 'priority' else 'false'
    return platform.setting(_setting_id(kind, package, module, name))


def _setting_id(kind, package, module='', name='enabled'):
    return ':'.join([kind, package, module, name])


def _get_addon_paths(addon_id):
    paths = []
    path, imported_addons = _get_addon_details(addon_id)
    if path:
        paths.append(path)
        for addon_id in imported_addons:
            paths.extend(_get_addon_paths(addon_id))
    return paths


def _get_addon_details(addon_id):
    path = platform.addonInfo2(addon_id, 'path')
    try:
        with open(os.path.join(path, 'addon.xml')) as fil:
            addon_xml = fil.read()
    except Exception:
        return (None, [])

    # <extension point="xbmc.python.module" library="<subdir>" />
    # <extension library="<subdir>" point="xbmc.python.module" />
    for pat in [r'<extension.*?point\s*=\s*"xbmc.python.module".*?library\s*=\s*"([^"]+)"',
                r'<extension.*?library\s*=\s*"([^"]+)".*?point\s*=\s*"xbmc.python.module"']:
        match = re.search(pat, addon_xml, re.DOTALL)
        if match:
            path = os.path.join(path, match.group(1))
            break

    # <import addon="script.module.simplejson" version="3.3.0"/>
    imported_addons = re.compile(r'<import.*?addon\s*=\s*"([^"]+)"', re.DOTALL).findall(addon_xml)

    log.debug('_get_addon_details(%s): path=%s, imported_addons=%s'%(addon_id, path, imported_addons))

    return (path, imported_addons)
