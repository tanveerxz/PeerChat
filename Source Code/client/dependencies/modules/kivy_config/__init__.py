# -*- coding: utf-8 -*-
r"""
This module configures kivy settings like window height, width, logger
path,etc. It also creates the necessary folders for the application to
run and loads all the api keys from the .env file.
Settings, Logs, app data are stored in the following path:

"C:\\Users\\<UserName>\\AppData\Local\\<Project Name>"

This folder is created, and data is stored in it as after compilation
of the application the home directory (Program Files Folder), it is not
easily writable. The app data should be edited in the home directory
which would be copied to the AppData folder for use by the application.
"""

import main # noqa

__PROJECT__ = main.__PROJECT__
# List of screens for the main screen manger in the application
__SCREENS__ = ['Empty', 'Splash', 'UserName', 'Home']

import os
import ctypes
import configparser
import logging
from tblib import pickling_support

# Create the necessary folders
for folder in [main.main_folder_path, main.data_folder_path]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Important to set the KIVY_HOME environment variable before importing
# kivy modules
os.environ['KIVY_HOME'] = main.main_folder_path

from kivy.logger import Logger  # noqa PEP 8: E402
from kivy.config import Config  # noqa PEP 8: E402

pickling_support.install()
logging.getLogger().setLevel(logging.INFO)

try:

    MIN_HEIGHT: str = '650'
    MAX_HEIGHT: str = str(ctypes.windll.user32.GetSystemMetrics(1))
    MIN_WIDTH: str = '850'
    MAX_WIDTH: str = str(ctypes.windll.user32.GetSystemMetrics(0))

    while True:
        try:
            height: int = int(Config.get('graphics', 'height'))
            width: int = int(Config.get('graphics', 'width'))
            screen: str = str(Config.get('app', 'current_screen'))
            theme: str = str(Config.get('app', 'theme'))
            colors: dict[str] = eval(Config.get('app', 'colors'))
            host = str(Config.get('Server', 'host'))
            port = int(Config.get('Server', 'port'))

            # Perform settings check before proceeding
            if not int(MAX_HEIGHT) >= height >= int(MIN_HEIGHT):
                raise ValueError
            if screen not in __SCREENS__:
                raise ValueError
            if not int(MAX_WIDTH) >= width >= int(MIN_WIDTH):
                raise ValueError
            if theme not in colors:
                raise ValueError

            Config.set('graphics', 'width', str(width))
            Config.set('graphics', 'height', str(height))
            Logger.info('kivy_config: Kivy successfully configured')
            break
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError, TypeError):

            Config.set('kivy', 'log_name', f'%H-%M-%S_{__PROJECT__.lower()}_%y-%m-%d_%_.txt')
            Config.set('kivy', 'window_icon', rf'{__path__[0]}\icon\Icon.png')
            Config.set('kivy', 'exit_on_escape', '0')
            Config.set('kivy', 'log_maxfiles', '25')
            Config.set('graphics', 'height', '650')
            Config.set('graphics', 'width', '850')
            Config.set('graphics', 'resizable', '0')
            Config.set('graphics', 'minimum_height', MIN_HEIGHT)
            Config.set('graphics', 'minimum_width', MIN_WIDTH)
            Config.set('input', 'mouse', 'mouse,disable_multitouch')

            # Add extra settings for the application
            try:
                Config.add_section('app')
                Config.add_section('Server')
            except configparser.DuplicateSectionError:
                pass
            Config.set('app', 'current_screen', __SCREENS__[0])
            Config.set('app', 'theme', 'Gray')
            Config.set('app', 'colors',
                       '''{
"Gray": {"200": "#212121","500": "#212121","700": "#323232"},
 }''')
            Config.set('Server', 'host', '45.79.122.7')
            Config.set('Server', 'port', '8080')
            Config.write()
            continue

except Exception as error:
    raise error
