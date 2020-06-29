#!/usr/bin/env python3

import os
import gi
import json

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from optparse import OptionParser


def verbose_print(string):
    if options.verbose:
        print(string)


def get_icon_path(filename, size=48):
    """Returns icon path from system icon_theme based of filename and size."""
    icon_theme = Gtk.IconTheme.get_default()
    icon_file = icon_theme.lookup_icon(filename, size, 0)
    return icon_file.get_filename() if icon_file else None


def get_steam_libraries():
    """Returns list of Steam library folders."""
    found_libraries = []

    if os.path.isdir(STEAM_INSTALL_DIR + '/steamapps/common'):
        found_libraries.append(STEAM_INSTALL_DIR)

    with open(STEAM_CONFIG_FILE) as config:
        content = config.readlines()

    for line in content:
        if 'BaseInstallFolder' in line:
            _path = line.split('"')[3]
            if not _path in found_libraries and os.path.isdir(_path + '/steamapps/common'):
                found_libraries.append(_path)

    return found_libraries


def get_installed_games(libraries):
    """Returns dictionary where key is app_id and value is name of the game."""
    found_games = {}

    for folder in libraries:
        files = next(os.walk(folder + '/steamapps'))[2]
        for file in files:
            if 'appmanifest' in file and '.acf' in file:
                with open(folder + '/steamapps/' + file) as manifest:
                    data = manifest.readlines()
                app_id = ''
                game_name = ''
                for line in data:
                    if '"appid"' in line:
                        app_id = line.split('"')[3]
                    elif '"name"' in line:
                        game_name = line.split('"')[3]
                found_games[app_id] = game_name
    return found_games


def get_fixable_games(games):
    """Returns dictionary of games that have icon in system icon_theme."""
    fixable = games.copy()
    for app_id in games:
        if not get_icon_path('steam_icon_' + app_id):
            fixable.pop(app_id)
    return fixable


def create_desktop_file(file_name, app_name, app_id, wm_class):
    """Creates hidden desktop file for Steam game."""
    file = open(HIDDEN_DESKTOP_FILES_DIR + '/' + file_name + '.desktop', 'w+')

    file.write('''[Desktop Entry]
Name=%s
Icon=steam_icon_%s
Terminal=false
Type=Application
StartupWMClass=%s
NoDisplay=true''' % (app_name, app_id, wm_class))

    file.close()


def clear_directory(directory):
    items = next(os.walk(directory))[2]
    if len(items) > 0:
        print('Clearing directory %s\n' % directory)
        for item in items:
            os.remove(directory + '/' + item)
            print(' Removed', item)


if __name__ == "__main__":

    # Create options parsing

    parser = OptionParser()

    parser.add_option("-c", "--clear",
                      action="store_true", dest="clear", default=False,
                      help="clear previous fixes before making new ones")
    parser.add_option("-i", "--icons",
                      action="store_true", dest="icons", default=False,
                      help="show available icons for installed Steam games")
    parser.add_option("-p", "--pretend",
                      action="store_true", dest="pretend", default=False,
                      help="show which icons can be fixed but do nothing")
    parser.add_option("-r", "--restore",
                      action="store_true", dest="restore", default=False,
                      help="remove all changes and restore default settings")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="run script in verbose mode")
    parser.add_option("-s", "--single", dest="single",
                      help="fix only one icon with specific APP_ID",
                      metavar="APP_ID")

    (options, args) = parser.parse_args()

    # Set constant variables

    HOME = os.getenv('HOME')
    STEAM_INSTALL_DIR = HOME + '/.local/share/Steam'
    STEAM_CONFIG_FILE = STEAM_INSTALL_DIR + '/config/config.vdf'
    HIDDEN_DESKTOP_FILES_DIR = HOME + '/.local/share/applications/steam-icons-fixed'
    GTK_THEME = Gtk.Settings.get_default().get_property('gtk-icon-theme-name')

    verbose_print('Working with %s icon theme.\n' % GTK_THEME)

    # --restore

    if options.restore:
        if os.path.isdir(HIDDEN_DESKTOP_FILES_DIR):
            clear_directory(HIDDEN_DESKTOP_FILES_DIR)
            os.rmdir(HIDDEN_DESKTOP_FILES_DIR)
            print('\nDirectory %s removed\n' % HIDDEN_DESKTOP_FILES_DIR)
            print('Update the desktop database for the changes to take effect.')
        else:
            print('Default settings are already restored. Nothing to do here.')
        quit()

    # Check for the presence of directories and files

    if os.path.isdir(STEAM_INSTALL_DIR):
        verbose_print('[ok] Found Steam installation directory:')
        verbose_print('   - %s\n' % STEAM_INSTALL_DIR)
    else:
        print('[error] Steam installation directory %s not found.' % STEAM_INSTALL_DIR)
        if HOME == '/root':
            print('\nRun script as a normal user, not root.')
        quit()

    if os.path.isfile(STEAM_CONFIG_FILE):
        verbose_print('[ok] Found Steam configuration file:')
        verbose_print('   - %s\n' % STEAM_CONFIG_FILE)
    else:
        print('[error] Steam configuration file %s not found.' % STEAM_CONFIG_FILE)
        quit()

    # this variable contains list of Steam library folders
    library_folders = get_steam_libraries()

    if len(library_folders) > 0:
        verbose_print('[ok] Found Steam library folders:')
        for path in library_folders:
            verbose_print('   - %s/steamapps' % path)
        verbose_print('')
    else:
        print('[error] Steam library not found.')
        quit()

    installed_games = dict(sorted(get_installed_games(library_folders).items(), key=lambda item: int(item[0])))
    fixable_games = get_fixable_games(installed_games)

    with open('wm-class-database.json') as json_file:
        database = json.load(json_file)

    # --icons

    if options.icons:
        print('These icons for your installed Steam games were found in %s icon theme:\n' % GTK_THEME)
        for key in fixable_games:
            icon_path = get_icon_path('steam_icon_' + key)
            print('%s%s - %s' % ('* ' if key in database.keys() else '  ', fixable_games[key], icon_path))
        print('\n* - game is in our database and can be fixed (if your icon theme supports it)')
        quit()

    if options.single:
        tmp = fixable_games.copy()
        for game in fixable_games:
            if game != options.single:
                tmp.pop(game)
        fixable_games = tmp

    if len(fixable_games) == 0:
        print('No games found to fix.')
        quit()

    # Look for target directory or create new

    if not options.pretend:
        if os.path.isdir(HIDDEN_DESKTOP_FILES_DIR):
            verbose_print('[ok] Found target directory:')
            verbose_print('   - %s\n' % HIDDEN_DESKTOP_FILES_DIR)
            if options.clear:
                clear_directory(HIDDEN_DESKTOP_FILES_DIR)
                print()
        else:
            verbose_print('[!!] Creating target directory.')
            try:
                os.mkdir(HIDDEN_DESKTOP_FILES_DIR)
            except OSError:
                print('[error] Creation of the directory failed!')
                print('   -', HIDDEN_DESKTOP_FILES_DIR)
                quit()
            else:
                verbose_print('[ok] Successfully created the directory:')
                verbose_print('   - %s' % HIDDEN_DESKTOP_FILES_DIR)

    # Pretend or apply fixes

    if options.pretend:
        print('Installed games whose icons can be fixed:\n')
    else:
        print('Creating .desktop files in %s\n' % HIDDEN_DESKTOP_FILES_DIR)

    for game in fixable_games:
        if game in database.keys():
            name = fixable_games[game].replace(' ', '-')
            if options.pretend:
                if options.verbose:
                    print('%7s - %s - %s' % (game, fixable_games[game], get_icon_path('steam_icon_' + game)))
                else:
                    print('%7s - %s' % (game, fixable_games[game]))
            else:
                create_desktop_file(name, fixable_games[game], game, database[game])
                if options.verbose:
                    desktop = HIDDEN_DESKTOP_FILES_DIR + '/' + name + '.desktop'
                    print('%7s - %s (%s)' % (game, fixable_games[game], desktop))
                else:
                    print('%7s - %s' % (game, fixable_games[game]))

    if options.pretend:
        print('\nNo changes were made.')
    else:
        print('\nUpdate the desktop database for the changes to take effect.')
