# -*- coding: utf-8 -*-
import sys
import os
import importlib
from time import time
from glob import iglob
from contextlib import contextmanager
from functools import wraps
from re import fullmatch

import maya.cmds as mc
import maya.mel as mel
import maya.api.OpenMaya as om2


python_version = sys.version_info.major


def load_plugin(plugin_name):
    """ プラグインのロード処理
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


def undo_ctx(func):
    """ エラーが出ても絶対UndoChunk閉じるマン
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        @contextmanager
        def undo_context():
            try:
                print('// Open Undo Chunk //')
                mc.undoInfo(openChunk=True)
                yield

            except Exception as e:
                print(e)

            finally:
                print('// Close Undo Chunk //')
                mc.undoInfo(closeChunk=True)

        with undo_context():
            func(*args, **kwargs)

    return wrapper


def reload_htm_module():
    """ htm系モジュールの全リロード
    """
    global python_version
    mod_list = sys.modules

    msg = '// ' + ('-' * 60) + '\n'
    if python_version == 3:
        for mod_str in mod_list:
            if 'HTM_' in mod_str:
                try:
                    mod_obj = importlib.import_module(mod_str)
                    importlib.reload(mod_obj)
                    msg += '// {} was loaded.\n'.format(mod_str)
                except Exception as e:
                    om2.MGlobal.displayError('{} --- "{}" can not be loaded.'.format(str(e), mod_str))
                    return

    else:
        for mod_str, mod in mod_list.items():
            if 'HTM_' in mod_str and mod is not None:
                try:
                    reload(mod)
                    msg += '// {} was loaded.\n'.format(mod_str)
                except Exception as e:
                    om2.MGlobal.displayError('{} --- "{}" can not be loaded.'.format(str(e), mod_str))
                    return

    msg += '// ' + ('-' * 60)

    match = fullmatch('//--+\n//--+', msg)
    if match is None:
        print(msg)
    else:
        print('// Nothing was loaded.')
