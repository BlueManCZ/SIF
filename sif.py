#!/usr/bin/env python3

from gi import require_version
from json import load
from optparse import OptionParser
from re import sub
from requests import get
from signal import signal, SIGINT
from shutil import which

import os
import subprocess
import vdf


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def verbose_print(string):
    """Print function that prints only if --verbose flag is present."""
    if options.verbose:
        print(string)


def print_warning(string):
    """Print function that prints in WARNING color."""
    print(Colors.WARNING + string + Colors.END)


def print_bold(string):
    """Print function that prints bold text."""
    print(Colors.BOLD + string + Colors.END)


def get_icon_path(icon_name, size=48):
    """Returns icon path from system icon_theme based of icon_name and size."""
    icon_theme = Gtk.IconTheme.get_default()
    icon_file = icon_theme.lookup_icon(icon_name, size, IconLookupFlags(0))
    return icon_file.get_filename() if icon_file else None


def get_steam_libraries():
    """Returns list of found Steam library folders."""
    found_libraries = []
    if os.path.isdir(STEAM_INSTALL_DIR + "/steamapps/common"):
        found_libraries.append(STEAM_INSTALL_DIR)

    libraries_config = {}
    if LIBRARY_FOLDERS_FILE:
        libraries_config = vdf.load(open(LIBRARY_FOLDERS_FILE))

    if libraries_config:
        libraries = get_from_dict(libraries_config, ["LibraryFolders"], {})

        if not libraries:
            print_warning("[error] No LibraryFolders key found in %s" % LIBRARY_FOLDERS_FILE)
            exit(1)

        for library in libraries.values():
            library_path = ""
            if "path" in library:
                library_path = library["path"]
            elif isinstance(library, str):
                library_path = library

            if (
                library_path
                and library_path not in found_libraries
                and os.path.isdir(library_path + "/steamapps/common")
            ):
                found_libraries.append(library_path)
    return found_libraries


def get_installed_games(libraries):
    """Returns dictionary where keys are APP_IDs and values are names of installed games."""
    found_games = {}
    for library in libraries:
        found_files = next(os.walk(library + "/steamapps"))[2]
        for filename in found_files:
            if "appmanifest" in filename and ".acf" in filename:
                with open(library + "/steamapps/" + filename) as manifest:
                    content = manifest.readlines()
                app_id = ""
                app_name = ""
                for line in content:
                    if '"appid"' in line:
                        app_id = line.split('"')[3]
                    elif '"name"' in line:
                        app_name = line.split('"')[3]
                if app_id:
                    found_games[app_id] = app_name
    return found_games


def get_fixable_games(games):
    """Returns dictionary of games that have icon in system icon_theme."""
    fixable = games.copy()
    for app_id in games:
        icon = get_icon_path("steam_icon_" + app_id)
        if not icon or GTK_THEME not in icon:
            fixable.pop(app_id)
    return fixable


print_buffer = []


def try_to_create_desktop_file(filename, app_name, app_id, wm_class, lo_fix=False):
    """This function is a wrapper for create_desktop_file."""
    filename = HIDDEN_DESKTOP_FILES_DIR + "/" + filename + ".desktop"
    line = "%7s %s - %s%s" % (
        game,
        "*" if lo_fix else " ",
        game_name,
        f" ({filename})" if options.verbose else "",
    )
    if line not in print_buffer:
        print_buffer.append(line)
        print(line)

    if not options.pretend:
        create_desktop_file(file_name, app_name, app_id, wm_class)


def create_desktop_file(filename, app_name, app_id, wm_class):
    """Creates hidden desktop file for Steam game."""
    desktop_file = open(HIDDEN_DESKTOP_FILES_DIR + "/" + filename + ".desktop", "w+")
    desktop_file.write(
        """[Desktop Entry]
Type=Application
Name=%s
Icon=steam_icon_%s
Exec=steam steam://rungameid/%s
Terminal=false
StartupWMClass=%s
NoDisplay=true"""
        % (app_name, app_id, app_id, wm_class)
    )
    desktop_file.close()


def clear_directory(directory):
    """Removes all files in the directory."""
    directory_files = next(os.walk(directory))[2]
    if len(directory_files) > 0:
        print("\nClearing directory %s\n" % directory)
        for filename in directory_files:
            os.remove(directory + "/" + filename)
            print(" Removed", filename)


def get_all_games_from_theme():
    """Returns list of APP_IDs of Steam games that have icon in system icon theme."""
    sample_icon = get_icon_path("nautilus")
    icon_theme_path = sample_icon[: -len(sample_icon.split("/")[-1])]
    games = [i.replace("_", ".").split(".")[2] for i in next(os.walk(icon_theme_path))[2] if "steam_icon" in i]
    return sorted(games, key=lambda item: int(item))


def fetch_json(app_id):
    """Fetches json file from Steam API for selected game."""
    url = "https://store.steampowered.com/api/appdetails?appids=" + app_id
    response = get(url)
    return response.json()


def get_game_name(json):
    """Returns game name from json file."""
    data = json
    app_id = ""
    if data is None:
        return None
    for dict_key in data.keys():
        app_id = dict_key
    if data[app_id]["success"]:
        return data[app_id]["data"]["name"]
    return None


def fix_launch_option(app_id, wm_name, wm_name_alt=""):
    """Add execution of fix-wm-class.sh file with wm_name of game as argument."""
    for conf_file in localconfig_paths:
        loaded = vdf.load(open(conf_file))

        steam = get_from_dict(loaded, ["UserLocalConfigStore", "Software", "Valve", "Steam"], {})
        apps = get_from_dict(steam, ["Apps"], {})

        if not apps:
            print_warning("[warning] No Apps key found in %s" % conf_file)
            continue

        if app_id in apps.keys():
            app = apps[app_id]
            if "LaunchOptions" not in app.keys():
                app["LaunchOptions"] = ""
            app["LaunchOptions"] = sub("&\\s/.*fix-wm-class\\.sh.*?;", "", app["LaunchOptions"])
            script = str(WM_CLASS_FIXER_SCRIPT)
            if wm_name_alt:
                app["LaunchOptions"] += '& %s "%s" "%s";' % (
                    script,
                    wm_name,
                    wm_name_alt,
                )
            # elif wm_name == "Pillars of Eternity":
            #     app["LaunchOptions"] += '& sleep 5 && %s "%s";' % (script, wm_name)
            else:
                app["LaunchOptions"] += '& %s "%s";' % (script, wm_name)
        vdf.dump(loaded, open(conf_file, "w"), pretty=True)


def restore_launch_options():
    """Removes changes made by "fix_launch_option" function."""
    for conf_file in localconfig_paths:
        loaded = vdf.load(open(conf_file))

        steam = get_from_dict(loaded, ["UserLocalConfigStore", "Software", "Valve", "Steam"], {})
        apps = get_from_dict(steam, ["Apps"], {})

        if not apps:
            continue

        for app_id in apps.keys():
            app = apps[app_id]
            if "LaunchOptions" in app.keys():
                app["LaunchOptions"] = sub("&\\s/.*fix-wm-class\\.sh.*?;", "", app["LaunchOptions"])
        vdf.dump(loaded, open(conf_file, "w"), pretty=True)


def find_processes(process_name):
    """Returns all PIDs of program processes specified by name."""
    processes = subprocess.Popen(["ps", "-A"], stdout=subprocess.PIPE)
    output, error = processes.communicate()
    pids = []
    for line in output.splitlines():
        if process_name in str(line):
            pids.append(int(line.split(None, 1)[0]))
    return pids


def terminate_processes(pids):
    """Terminate process by their PIDs"""
    for pid in pids:
        os.kill(pid, 15)


def steam_detect():
    """Prompt user to exit Steam if running. Returns True if Steam remains running, else False."""
    steam_pids = find_processes("steam")
    if steam_pids:
        print("\nRunning Steam instance was found.")
        print_warning("It is necessary to exit Steam for some changes to take effect.")
        text = f"\n{Colors.BOLD}Would you like to terminate Steam now?{Colors.END} [{Colors.BOLD}Y{Colors.END}/n]: "
        choice = input(text)
        print()
        if choice in ["Y", "y", "Yes", "yes", ""]:
            try:
                terminate_processes(steam_pids)
                print("Terminating Steam processes.")
            except ProcessLookupError:
                print("Steam processes already terminated.")
            while find_processes("steam"):
                pass
        return choice not in ["Y", "y", "Yes", "yes", ""]
    return False


def update_desktop_database():
    updater = which("update-desktop-database")
    if updater:
        subprocess.run([updater, HOME + "/.local/share/applications"])
    else:
        print_warning("\nUpdate the desktop database for the changes to take effect.")


def get_from_dict(data: dict, keys: list, default=None):
    """Get value from nested dictionary by list of keys. Try to find key in lower case if not found."""
    current = data
    for key in keys:
        if key in current:
            current = current[key]
        elif key.lower() in current:
            current = current[key.lower()]
        else:
            return default
    return current


def exit_with_message(message_text, exit_code=1):
    print_warning("\n[error] " + message_text)
    exit(exit_code)


def quit_handler(_, __):
    """Handler for exit signal."""
    print("\nSIGINT or CTRL-C detected. Exiting")
    quit()


if __name__ == "__main__":

    signal(SIGINT, quit_handler)

    # Create options parsing

    parser = OptionParser()

    parser.add_option(
        "-b",
        "--browse",
        action="store_true",
        dest="browse",
        default=False,
        help="show all games with icon in system icon theme",
    )
    parser.add_option(
        "-c",
        "--clear",
        action="store_true",
        dest="clear",
        default=False,
        help="clear previous fixes before making new ones",
    )
    parser.add_option(
        "-d",
        "--database",
        action="store_true",
        dest="database",
        default=False,
        help="list all games in database",
    )
    parser.add_option(
        "-g",
        "--games",
        action="store_true",
        dest="games",
        default=False,
        help="show all installed games from your Steam library",
    )
    parser.add_option(
        "-i",
        "--icons",
        action="store_true",
        dest="icons",
        default=False,
        help="show available icons for installed Steam games",
    )
    parser.add_option(
        "-p",
        "--pretend",
        action="store_true",
        dest="pretend",
        default=False,
        help="show which icons can be fixed but do nothing",
    )
    parser.add_option(
        "-r",
        "--restore",
        action="store_true",
        dest="restore",
        default=False,
        help="remove all changes and restore default settings",
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="run script in verbose mode",
    )
    parser.add_option(
        "-s",
        "--single",
        dest="single",
        help="fix only one icon with specific APP_ID",
        metavar="APP_ID",
    )
    parser.add_option(
        "--proton",
        action="store_true",
        dest="proton",
        default=False,
        help="works only with --single option and forces a Proton specific WM_CLASS",
    )

    (options, args) = parser.parse_args()

    # Set constant variables

    HOME = os.getenv("HOME")

    try:
        require_version("Gtk", "3.0")
        from gi.repository import Gtk
        from gi.repository.Gtk import IconLookupFlags
    except NameError and ValueError:
        exit_with_message("Gtk 3 is required to run this script.")

    gtk_settings = Gtk.Settings.get_default()

    GTK_THEME = "unknown"
    if gtk_settings:
        GTK_THEME = gtk_settings.get_property("gtk-icon-theme-name")
    else:
        exit_with_message("GTK settings not found.")

    verbose_print("Current icon theme: %s\n" % GTK_THEME)

    paths = [
        HOME + "/.local/share/Steam",
        HOME + "/.steam/steam",
        HOME + "/.var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    STEAM_INSTALL_DIR = ""
    for path in paths:
        if os.path.isdir(path):
            STEAM_INSTALL_DIR = path
            version_file = STEAM_INSTALL_DIR + "/ubuntu12_32/steam-runtime/version.txt"
            if os.path.isfile(version_file):
                with open(version_file, "r") as file:
                    version = file.readline()
                    verbose_print("Steam version: %s" % version)

            verbose_print("[ok] Found Steam installation directory:")
            verbose_print("   - %s\n" % STEAM_INSTALL_DIR)
            break

    if not STEAM_INSTALL_DIR:
        message = "Steam installation directory not found."
        if HOME == "/root":
            message += "\nRun script as a normal user, not root."
        exit_with_message(message)

    REAL_PATH = os.path.dirname(os.path.realpath(__file__))
    STEAM_CONFIG_FILE = STEAM_INSTALL_DIR + "/config/config.vdf"
    HIDDEN_DESKTOP_FILES_DIR = HOME + "/.local/share/applications/steam-icons-fixed"
    DATABASE_FILE = REAL_PATH + "/database.json"
    WM_CLASS_FIXER_SCRIPT = REAL_PATH + "/fix-wm-class.sh"

    # --browse

    if options.browse:
        print("These Steam games have icon in %s icon theme:" % GTK_THEME)
        print("(Fetching names from https://store.steampowered.com/api. This may take a while.)\n")
        for game in get_all_games_from_theme():
            name = get_game_name(fetch_json(game))
            if options.verbose:
                desktop = HIDDEN_DESKTOP_FILES_DIR + "/" + name + ".desktop"
                print("%7s - %s (%s)" % (game, name, get_icon_path("steam_icon_" + game)))
            else:
                print("%7s - %s" % (game, name))
        quit()

    # Check for the presence of directories and files

    steam_config_file = {}

    if os.path.isfile(STEAM_CONFIG_FILE):
        verbose_print("[ok] Found Steam configuration file:")
        verbose_print("   - %s\n" % STEAM_CONFIG_FILE)
        steam_config_file = vdf.load(open(STEAM_CONFIG_FILE))
    else:
        exit_with_message("Steam configuration file %s not found." % STEAM_CONFIG_FILE)

    files = [
        STEAM_INSTALL_DIR + "/config/libraryfolders.vdf",
        STEAM_INSTALL_DIR + "/steamapps/libraryfolders.vdf",
    ]
    LIBRARY_FOLDERS_FILE = ""
    for file in files:
        if os.path.isfile(file):
            LIBRARY_FOLDERS_FILE = file
            verbose_print("[ok] Found Steam libraryfolders.vdf file:")
            verbose_print("   - %s\n" % LIBRARY_FOLDERS_FILE)
            break

    if not STEAM_INSTALL_DIR:
        print_warning("[warning] Steam libraryfolders.vdf file not found.")

    # this variable contains list of Steam library folders
    library_folders = get_steam_libraries()

    if len(library_folders) > 0:
        verbose_print("[ok] Found Steam library folders:")
        for path in library_folders:
            verbose_print("   - %s/steamapps" % path)
        verbose_print("")
    else:
        exit_with_message("Steam library not found.")

    # Find localconfig.vdf files

    localconfig_paths = []
    ids = next(os.walk(STEAM_INSTALL_DIR + "/userdata"))[1]
    if len(ids) > 0:
        for folder in ids:
            vdf_file = STEAM_INSTALL_DIR + "/userdata/" + folder + "/config/localconfig.vdf"
            if os.path.isfile(vdf_file):
                localconfig_paths.append(vdf_file)
        if len(localconfig_paths) > 0:
            verbose_print("[ok] Found Steam localconfig.vdf file:")
            for vdf_file in localconfig_paths:
                verbose_print("   - %s" % vdf_file)
            verbose_print("")
    else:
        print_warning("[warning] Steam localconfig.vdf file not found.")

    # --restore

    if options.restore:
        if os.path.isdir(HIDDEN_DESKTOP_FILES_DIR):
            print("Removing all changes and restoring default settings.")
            clear_directory(HIDDEN_DESKTOP_FILES_DIR)
            if not steam_detect():
                restore_launch_options()
                print("\nDefault Steam launch options restored.")
                os.rmdir(HIDDEN_DESKTOP_FILES_DIR)
                print("\nDirectory %s removed." % HIDDEN_DESKTOP_FILES_DIR)
            else:
                print("Couldn't restore default launch options. Exit Steam and try it again.")
                quit()
            update_desktop_database()
        else:
            print("Default settings are already restored. Nothing to do here.")
        quit()

    raw_installed_games = get_installed_games(library_folders).items()
    installed_games = {key: val for key, val in sorted(raw_installed_games, key=lambda item: int(item[0]))}
    fixable_games = get_fixable_games(installed_games)

    # --games

    if options.games:
        print("These Steam games are currently installed:\n")
        for game in installed_games:
            print("%7s - %s" % (game, installed_games[game]))
        quit()

    # Load wm-class-database file

    if os.path.isfile(DATABASE_FILE):
        verbose_print("[ok] Found database.json file:")
        verbose_print("   - %s\n" % DATABASE_FILE)
        with open(DATABASE_FILE) as json_file:
            database = load(json_file)
    else:
        exit_with_message("Database file %s not found." % DATABASE_FILE)

    games_with_compat = get_from_dict(
        steam_config_file,
        ["InstallConfigStore", "Software", "Valve", "Steam", "CompatToolMapping"],
        {},
    )
    proton_games = []

    verbose_print("[proton] These games are using Proton compatibility tool:")

    for game in games_with_compat:
        game_dict = games_with_compat[game]
        if game in fixable_games:
            verbose_print("   - %s - %s" % (fixable_games[game], get_from_dict(game_dict, ["Name"])))
        if any(x in get_from_dict(game_dict, ["Name"], []) for x in ["proton", "Proton"]):
            proton_games.append(game)
    verbose_print("")

    # --icons

    if options.icons:
        print(f"These icons for your installed Steam games were found in {GTK_THEME} icon theme:\n")
        margin = 0
        for name in fixable_games.values():
            if len(name) > margin:
                margin = len(name)
        for key in fixable_games:
            icon_path = get_icon_path("steam_icon_" + key)
            symbol = " "
            if key in database["wm_classes"] or key in proton_games:
                symbol = "*"
            elif key in database["wm_names"]:
                symbol = "~"
            print(f"{symbol} {Colors.BOLD}{fixable_games[key]:<{margin}}{Colors.END} - {icon_path}")
        print("\n* - game is in our database and can be fixed")
        print("~ - script will edit launch options of the game")
        quit()

    # --database

    if options.database:
        print("These games are in the database:\n")
        print("WM_CLASS:")
        for key in database["wm_classes"]:
            name = get_game_name(fetch_json(key))
            print(f"{key} - {name}")
        print("\nWM_NAME:")
        for key in database["wm_names"]:
            name = get_game_name(fetch_json(key))
            print(f"{key} - {name}")
        quit()

    # --single

    if options.single:
        if options.single in fixable_games:
            fixable_games = {k: v for k, v in fixable_games.items() if k == options.single}

    if not fixable_games:
        print_warning("No games found to fix.")
        quit()

    # Look for target directory or create new

    if not options.pretend:
        if os.path.isdir(HIDDEN_DESKTOP_FILES_DIR):
            verbose_print("[ok] Found target directory:")
            verbose_print("   - %s\n" % HIDDEN_DESKTOP_FILES_DIR)
            if options.clear:
                clear_directory(HIDDEN_DESKTOP_FILES_DIR)
                print()
        else:
            verbose_print("[!!] Creating target directory.")
            try:
                os.mkdir(HIDDEN_DESKTOP_FILES_DIR)
            except OSError:
                print_warning("[error] Creation of the directory failed!")
                print("   -", HIDDEN_DESKTOP_FILES_DIR)
                quit(1)
            else:
                verbose_print("[ok] Successfully created the directory:")
                verbose_print("   - %s" % HIDDEN_DESKTOP_FILES_DIR)

    wm_classes = database["wm_classes"]
    wm_names = database["wm_names"]

    steam_termination_required = False

    for game in fixable_games:
        if game in wm_names:
            steam_termination_required = True
            break

    steam_detected = False

    if options.pretend:
        print("Installed games whose icons can be fixed:\n")
    else:
        print("Creating .desktop files in %s" % HIDDEN_DESKTOP_FILES_DIR)

        if steam_termination_required:
            steam_detected = steam_detect()

        if not steam_detected:
            print()

    # All important work here

    launch_option_counter = 0

    for game in fixable_games:
        game_name = fixable_games[game]
        file_name = game_name.replace(" ", "-")

        if game in proton_games or options.single and options.proton:
            # Game uses Proton compatibility tool

            game_wm_class = "steam_app_" + game
            try_to_create_desktop_file(file_name, game_name, game, game_wm_class)

        elif game in wm_classes:
            # Game is Linux native with WM_CLASS

            if isinstance(wm_classes[game], list):
                for record in wm_classes[game]:
                    game_name = fixable_games[game]
                    game_wm_class = record
                    if "=" in record:
                        game_wm_class = record.split("=")[0]
                        game_name = record.split("=")[1] or fixable_games[game]
                    file_name = game_wm_class.replace(" ", "-")
                    try_to_create_desktop_file(file_name, game_name, game, game_wm_class)

            else:
                try_to_create_desktop_file(file_name, game_name, game, wm_classes[game])

        elif game in wm_names:
            # Game is Linux native without WM_CLASS. Using WM_NAME instead.
            # Steam instance must be terminated for this to work.

            launch_option_counter += 1

            if steam_detected:
                continue
            else:
                split = wm_names[game].split("=")
                game_wm_name = split[0]
                game_wm_name_alt = ""
                if len(split) > 1:
                    game_wm_name_alt = split[1]
                fix_launch_option(game, game_wm_name, game_wm_name_alt)
                try_to_create_desktop_file(
                    file_name,
                    fixable_games[game],
                    game,
                    game_wm_name_alt or game_wm_name,
                    True,
                )

    if launch_option_counter > 0:
        if steam_detected:
            print_warning("\nSome games couldn't be fixed due to running Steam.\nExit Steam and try it again.")
        else:
            print("\n * - added fix to game launch options")

    if options.pretend:
        print_warning("\nNo changes were made because --pretend option was used.")
    else:
        update_desktop_database()
