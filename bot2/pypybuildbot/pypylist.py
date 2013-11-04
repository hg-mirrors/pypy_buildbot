import os.path
import datetime
import itertools
import py
import cgi
import urllib
import sys
from twisted.web.static import File, DirectoryLister
from buildbot.status.web.base import path_to_root

class PyPyTarball(object):

    # to get the desired order keep in mind that they are reversed at the end,
    # so the highest the value, the bigger the priority
    VCS_PRIORITY = {
        'latest': 150,
        'hg': 100,
        'svn': 50,
        }

    FEATURES_PRIORITY = {
        'jit':      100,
        'nojit':     50,
        'stackless': 10
        }

    PLATFORM_PRIORITY = {
        'linux':    100,
        'linux64':   50,
        'osx':       30,
        'win32':     10,
        'linux_armhf_raspbian': 7,
        'linux_armhf_raring': 6,
        'linux_armel': 5,
        }

    PLATFORMS = {
        'linux':   'linux-x86-32',
        'linux64': 'linux-x86-64',
        'osx':     'macosx-x86-32',
        'win32':   'win-x86-32',
        }

    DESCRIPTIONS = {
        'nojit':     'app-level',
        'jit':       'jit',
        'stackless': 'stackless-app-level',
        }

    def __init__(self, filename):
        self.filename = filename
        try:
            self.parse_filename()
        except ValueError:
            self.vcs = None
            self.exe = None
            self.backend = None
            self.features = None
            self.rev = -1
            self.numrev = -1
            self.platform = None

    def parse_filename(self):
        for ext in ['.tar.bz2', '.zip']:
            if self.filename.endswith(ext):
                break
        else:
            raise ValueError
        name = self.filename.replace(ext, '')
        # remove the dash from linux-armel, else the split does not work
        name = name.replace('-armel', '_armel')
        name = name.replace('-libc2', '_libc2')
        name = name.replace('-armhf-ra', '_armhf_ra')
        dashes = name.count('-')
        if dashes == 4:
            # svn based
            self.exe, self.backend, self.features, self.rev, self.platform = name.split('-')
            if self.rev == 'latest':
                self.rev = -1
                self.numrev = -1
                self.vcs = 'latest'
            else:
                self.numrev = int(self.rev)
                self.vcs = 'svn'
        elif dashes == 5:
            # mercurial based
            self.exe, self.backend, self.features, num, hgid, self.platform = name.split('-')
            self.numrev = int(num)
            self.rev = '%s:%s' % (num, hgid)
            self.vcs = 'hg'
        else:
            raise ValueError

    def key(self):
        return (self.VCS_PRIORITY.get(self.vcs, -1),
                self.numrev,
                self.FEATURES_PRIORITY.get(self.features, -1),
                self.PLATFORM_PRIORITY.get(self.platform, -1))

    def get_builder_names(self):
        platform = self.PLATFORMS.get(self.platform, self.platform)
        description = self.DESCRIPTIONS.get(self.features, self.features)
        own_builder = 'own-%s' % platform
        app_builder = '%s-%s-%s-%s' % (self.exe, self.backend, description, platform)
        return own_builder, app_builder

    def display_in_italic(self):
        return self.vcs == 'latest'

class PyPyDirectory(object):
    def __init__(self, filePath):
        self.filename = filePath.basename()
        self.filePath = filePath
        self.parse_filename()

    def parse_filename(self):
        if self.filename == 'trunk':
            self.last_mod_time = sys.maxsize
            return
        self.last_mod_time = self.filePath.getmtime()

    def key(self):
        return (self.last_mod_time)

class PyPyList(File):

    def sortBuildNames(self, names):
        items = map(PyPyTarball, names)
        items.sort(key=PyPyTarball.key, reverse=True)
        return [item.filename for item in items]

    def sortDirectoryNames(self, filePaths):
        items = map(PyPyDirectory, filePaths)
        items.sort(key=PyPyDirectory.key, reverse=True)
        return [item.filename for item in items]

    def directoryListing(self):
        def is_pypy_dir(names):
            for name in names:
                if name.startswith('pypy-c'):
                    return True
            return False
        names = File.listNames(self)
        if is_pypy_dir(names):
            names = self.sortBuildNames(names)
            Listener = PyPyDirectoryLister
        else:
            names = self.sortDirectoryNames(File.listEntities(self))
            Listener = PyPyDirectoryLister
        return Listener(self.path,
                        names,
                        self.contentTypes,
                        self.contentEncodings,
                        self.defaultType)

class NumpyStatusList(File):
    pass

class PyPyDirectoryLister(DirectoryLister):
    template = """<html>
<head>
<title>%%(header)s</title>
    <link rel="stylesheet" href="%(path_to_root)sdefault.css" type="text/css" />
    <link rel="alternate" type="application/rss+xml" title="RSS" href="%(path_to_root)srss">
    <link rel="shortcut icon" href="%(path_to_root)sfavicon.ico">
<style>
.even        { background-color: #eee    }
.odd         { background-color: #dedede }
.even-passed { background-color: #caffd8 }
.odd-passed  { background-color: #a3feba }
.even-failed { background-color: #ffbbbb }
.odd-failed  { background-color: #ff9797 }

.summary_link {
    color: black;
    text-decoration: none;
}
.summary_link:hover {
    color: blue;
    text-decoration: underline;
}

.icon { text-align: center }
.listing {
    margin-left: auto;
    margin-right: auto;
    width: 50%%%%;
    padding: 0.1em;
    }

body { border: 0; padding: 0; margin: 0; background-color: #efefef; }
h1 {padding: 0.1em; background-color: #777; color: white; border-bottom: thin white dashed;}
td,th {padding-left: 0.5em; padding-right: 0.5em; }

</style>
</head>

<body class="interface">
   <div class="header">
        <a href="%(path_to_root)s">Home</a>
        -
        <!-- PyPy specific items -->
        <a href="http://speed.pypy.org/">Speed</a>
        <a href="%(path_to_root)ssummary?branch=&lt;trunk&gt;">Summary (trunk)</a>
        <a href="%(path_to_root)ssummary">Summary</a>
        <a href="%(path_to_root)snightly/">Nightly builds</a>
        <!-- end of PyPy specific items -->

        <a href="%(path_to_root)swaterfall">Waterfall</a>
        <!-- <a href="%(path_to_root)sgrid">Grid</a> -->
        <!-- <a href="%(path_to_root)stgrid">T-Grid</a> -->
        <!-- <a href="%(path_to_root)sconsole">Console</a> -->
        <a href="%(path_to_root)sbuilders">Builders</a>
        <!-- <a href="%(path_to_root)sone_line_per_build">Recent Builds</a> -->
        <!-- <a href="%(path_to_root)sbuildslaves">Buildslaves</a> -->
        <!-- <a href="%(path_to_root)schanges">Changesources</a> -->
        <!-- - <a href="%(path_to_root)sjson/help">JSON API</a> -->
        - <a href="%(path_to_root)sabout">About</a>
    </div>
<h1>%%(header)s</h1>

<table>
    <thead>
        <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Date</th>
            <th><i>own</i> tests</th>
            <th><i>applevel</i> tests</th>
        </tr>
    </thead>
    <tbody>
%%(tableContent)s
    </tbody>
</table>

</body>
</html>
"""

    linePattern = """<tr class="%(class)s">
    <td><a href="%(href)s">%(text)s</a></td>
    <td>%(size)s</td>
    <td>%(date)s</td>
    <td class="%(own_summary_class)s">%(own_summary)s</td>
    <td class="%(app_summary_class)s">%(app_summary)s</td>
</tr>
"""

    def render(self, request):
        self.status = request.site.buildbot_service.getStatus()
        self.template = self.template % {'path_to_root': path_to_root(request)}
        return DirectoryLister.render(self, request)

    def _buildTableContent(self, elements):
        tableContent = []
        rowClasses = itertools.cycle(['odd', 'even'])
        for element, rowClass in zip(elements, rowClasses):
            element["class"] = rowClass
            self._add_test_results(element, rowClass)
            tableContent.append(self.linePattern % element)
        return tableContent

    def _add_test_results(self, element, rowClass):
        filename = urllib.unquote(element['href'])
        f = py.path.local(self.path).join(filename)
        date = datetime.date.fromtimestamp(f.mtime())
        element['date'] = date.isoformat()
        t = PyPyTarball(filename)
        if t.display_in_italic():
            element['text'] = '<i>%s</i>' % (element['text'],)
        own_builder, app_builder = t.get_builder_names()
        self._add_result_for_builder(element, own_builder, 'own_', t.rev, rowClass)
        self._add_result_for_builder(element, app_builder, 'app_', t.rev, rowClass)

    def _add_result_for_builder(self, element, builder_name, prefix, rev, rowClass):
        if rev == -1:
            summary = None
            str_summary = ''
        else:
            branch = self._get_branch()
            summary, category = self._get_summary_and_category(builder_name, branch, rev)
            if branch == 'trunk':
                branch = '%3Ctrunk%3E' # <trunk>
            if category:
                href = cgi.escape('/summary?category=%s&branch=%s&recentrev=%s' % (category, branch, rev))
                str_summary = '<a class="summary_link" href="%s">%s</a>' % (href, summary)
            else:
                str_summary = str(summary)
        element[prefix + 'summary'] = str_summary
        element[prefix + 'summary_class'] = self._get_summary_class(summary, rowClass)

    def _get_branch(self):
        parts = self.path.split(os.path.sep)
        i = parts.index('nightly')
        branch = os.path.sep.join(parts[i+1:])
        return branch

    def _get_summary_and_category(self, builder_name, branch, rev):
        try:
            builder = self.status.getBuilder(builder_name)
            return builder.summary_by_branch_and_revision[(branch, rev)], builder.category
        except (AttributeError, KeyError):
            return None, None
            # for testing
            ## from pypybuildbot.summary import OutcomeSummary
            ## import random
            ## if random.choice([True, True, True, False]):
            ##     return OutcomeSummary(1000, 0, 2, 4), None
            ## else:
            ##     return OutcomeSummary(990, 10, 2, 4), None

    def _get_summary_class(self, summary, rowClass):
        if summary is None:
            return rowClass
        elif summary.is_ok():
            return rowClass + '-passed'
        else:
            return rowClass + '-failed'

