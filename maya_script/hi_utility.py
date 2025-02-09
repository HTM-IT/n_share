# -*- coding: utf-8 -*-
import sys
import os
import importlib
from time import time
from glob import iglob
from contextlib import contextmanager
from functools import wraps

import maya.cmds as mc
import maya.mel as mel
import maya.api.OpenMaya as om2

python_version = sys.version_info.major


def load_plugin(plugin_name):
    """ Load skin weight import plugin to use
        import weight command as undoable.
    """
    loaded = mc.pluginInfo(plugin_name, q=True, l=True)
    if not loaded:
        for path in sys.path:
            if 'Documents' in path:
                # Python 3x
                if sys.version_info.major == 3:
                    for file in iglob(r'{}*\**\{}.py'.format(path, plugin_name), recursive=True):
                        mc.loadPlugin(file, quiet=True)
                        return

                # Python 2x
                else:
                    for current_path, _, files in os.walk(path):
                        for file in files:
                            if plugin_name in file: # Name check
                                plugin_path = current_path + '\\' + file
                                plugin_path = os.path.realpath(plugin_path)
                                mc.loadPlugin(plugin_path, quiet=True)
                                return

    else:
        om2.MGlobal.displayInfo('{} has been loaded.'.format(plugin_name))


def unload_plugin(plugin_name):
    mc.flushUndo()
    mc.unloadPlugin(plugin_name)


def reload_plugin(plugin_name):
    unload_plugin(plugin_name)
    load_plugin(plugin_name)


def reload_hi_module():
    """ Reload all hi_tools related modules
    """
    global python_version
    mod_list = sys.modules
    names = [name for name in mod_list if 'hi_tools.' in name]
    max = len(sorted(names, key=lambda x: len(x))[-1])

    msg = '// ' + ('-' * 60) + '\n'
    if python_version == 3:

        for mod_str in mod_list:
            if 'hi_tools.' in mod_str:
                try:
                    mod_obj = importlib.import_module(mod_str)
                    importlib.reload(mod_obj)
                    msg += '// {} was loaded.\n'.format(mod_str.ljust(max))
                except Exception as e:
                    om2.MGlobal.displayError('{} --- "{}" can not be loaded.'.format(str(e), mod_str))
                    return

    else:
        for mod_str, mod in mod_list.items():
            if 'hi_tools.' in mod_str and mod is not None:
                try:
                    reload(mod)
                    msg += '// {} was loaded.\n'.format(mod_str.ljust(max))
                except Exception as e:
                    om2.MGlobal.displayError('{} --- "{}" can not be loaded.'.format(str(e), mod_str))
                    return

    msg += '// ' + ('-' * 60)
    print(msg)


class ProgressBar:
    """ Progress bar
    """
    def __init__(self, max_count, status='Progress ...'):
        progressbar = mel.eval('$tmp = $gMainProgressBar')
        self.progressbar = mc.progressBar(progressbar, edit=True,
                                    beginProgress=True,
                                    status=status,
                                    minValue=0,
                                    maxValue=max_count,
                                    isInterruptable=False)

    def count(self):
        mc.progressBar(self.progressbar, edit=True, step=1)

    def end(self):
        mc.progressBar(self.progressbar, edit=True, endProgress=True)


class ProgressContext:
    """ Progress Bar Context
    """
    def create(self, max_count, status = u'Progress ...', interrupt=False, win=True):

        self._win = win
        if win:
            win_title = u'Progress Bar'
            self._window = mc.window(title=win_title, mnb=False, mxb=False, sizeable=False)
            self._layout = mc.columnLayout(adj=True, w=200)
            self._text = mc.text(u'Executing an operation...')
            self._bar = mc.progressBar(beginProgress=True, status=status, minValue=0, p=self._layout,
                                      maxValue=max_count, isInterruptable=interrupt)
            mc.showWindow(self._window)
        else:
            self._bar = mel.eval(u'$tmp = $gMainProgressBar')
            mc.progressBar(self._bar, beginProgress=True, e=True, status=status, minValue=0,
                           maxValue=max_count, isInterruptable=interrupt)

    def count(self):
        try:
            mc.progressBar(self._bar, edit=True, step=1)
        except:
            return

    def end(self):
        mc.progressBar(self._bar, edit=True, endProgress=True)
        if self._win:
            mc.deleteUI(self._window)

    def is_canceled(self):
        return mc.progressBar(self._bar, q=True, isCancelled = True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            mc.progressBar(self._bar, edit=True, endProgress=True)
            if self._win:
                mc.deleteUI(self._window)
        except:
            return


class Decorators:
    """ Decorators set
    """
    @classmethod
    def undo_ctx(cls, func):
        """ Anytime close undo chunk.
            If you use this with classmethod/staticmethod,
            you should add this under @classmethod/@staticmethod.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            @contextmanager
            def undo_context():
                print('// In undo_ctx')
                mc.undoInfo(openChunk=True)
                yield
                mc.undoInfo(closeChunk=True)

            with undo_context():
                func(*args, **kwargs)

        return wrapper

    @classmethod
    def rectime(cls, func):
        """ Simple timer
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time()
            val = func(*args, **kwargs)
            end = time()

            result = end - start
            print('---------------------------------------------------')
            print('"{}" done in {:.4f} sec.'.format(func.__name__, result))
            print('---------------------------------------------------')
            return val

        return wrapper


class UndoContext: # OLD METHOD
    """ Use this with 'with' statement to prevent
        not to execute 'undoInfo -closeChunk True'.
    """
    def __enter__(self):
        print('// In undo_ctx')
        mc.undoInfo(openChunk=True)

    def __exit__(self, *exc_info):
        mc.undoInfo(closeChunk=True)


# -----------------------------------------------------
# Storage for handy function, currently not used
# -----------------------------------------------------
import sys, re, string
import maya.cmds as mc

""" Enable this if needed
python_version = sys.version_info.major
if python_version == 2:
    maketrans = string.maketrans
else:
    maketrans = str.maketrans
"""

def get_symmetry_name(name):
    """
    Params:
        src_name(str): source joint's fullpath
                       In Python 2.x, this may be unicode.
    """
    def convert_lr(match_obj):
        """ Replacement function for L(l) to R(r) and vise versa,
            which is called whenever a matching string found.
            Note : This is only for string object.
        """
        table = maketrans('LlRr', 'RrLl')
        if match_obj.group(1) is not None:
            return match_obj.group(1).translate(table)

        if match_obj.group(2) is not None:
            return match_obj.group(2).translate(table)

        if match_obj.group(3) is not None:
            return match_obj.group(3).translate(table)

    if python_version == 2:
        if isinstance(src_name, unicode):
            src_name = src_name.encode('utf-8') # convert to byte

    src_name = src_name.split('|')
    dst_name = []
    for name in src_name:
        name_split = name.split(':')
        if len(name_split) == 1: # --> no namespace
            dst_name.append(re.sub(r'(_[LlRr]$)|(^[LlRr]_)|(_[LlRr]_)', convert_lr, name_split[-1]))
        else:
            tmp = re.sub(r'(_[LlRr]$)|(^[LlRr]_)|(_[LlRr]_)', convert_lr, name_split[-1])
            dst_name.append(name_split[0] + ':'+ tmp)

    # make dst math
    dst_path = '|'.join(dst_name)
    if python_version == 2:
        if isinstance(dst_path, str):
            return dst_path.decode()

    return dst_path