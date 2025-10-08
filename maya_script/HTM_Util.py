# -*- coding: utf-8 -*-
import sys
import os
import importlib
from time import time
from glob import iglob
from contextlib import contextmanager
from functools import wraps
from re import fullmatch
import time

import maya.cmds as mc
import maya.mel as mel
import maya.api.OpenMaya as om2

python_version = sys.version_info.major

# ---------------------------------------------------------
# 処理速度計測用のコンテキストマネージャー
# ---------------------------------------------------------
class Timer:
    """ 処理速度計測用コンテキストマネージャー
    """
    def __init__(self):
        self.start = None
        self.end = None
        self.elapsed = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.perf_counter()
        self.elapsed = self.end - self.start

        print(u'経過時間: {:.6f} 秒'.format(self.elapsed))


# ---------------------------------------------------------
# プラグイン・モジュールのロード関連
# ---------------------------------------------------------
def load_plugin(plugin_name):
    """ プラグインのリロード処理
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


def reload_plugin(plugin_name):
    """ プラグインのロード
    """
    unload_plugin(plugin_name)
    load_plugin(plugin_name)


def unload_plugin(plugin_name):
    """ プラグインのアンロード
    """
    mc.flushUndo() # プラグインコマンドによるUndo履歴があるとまずいので消す
    mc.unloadPlugin(plugin_name)


def reload_module(keyword='HTM_'):
    """ 特定の文字列を含むモジュールの全リロード
    """
    global python_version
    mod_list = sys.modules

    msg = '// ' + ('-' * 60) + '\n'
    if python_version == 3: # バージョンによって処理を分岐
        for mod_str in mod_list:
            if keyword in mod_str:
                try:
                    mod_obj = importlib.import_module(mod_str)
                    importlib.reload(mod_obj)
                    msg += '// {} was loaded.\n'.format(mod_str)
                except Exception as e:
                    om2.MGlobal.displayError('{} --- "{}" can not be loaded.'.format(str(e), mod_str))
                    return

    else:
        for mod_str, mod in mod_list.items():
            if keyword in mod_str and mod is not None:
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


# ---------------------------------------------------------
# 1Undoで元に戻すができるようにするデコレータ
# ---------------------------------------------------------
def undo_ctx(func):
    """ 
    1Undoで処理をもとに戻せるようにする
    あと何が起きてもUndoChunkを閉じれるようにして事故を防ぐ
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


