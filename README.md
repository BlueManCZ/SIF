# SIF (Steam Icons Fixer)

**SIF is a simple Python script that allows the user to fix icons 
of installed Steam games on Linux.**

I created this script because it was very frustrating how the game
icons didn't fit the selected icon theme.

# Description

In this paragraph is explained, how SIF script works.

1. Finds all Steam library folders and installed games.
2. For each one game checks:
    1. If game has a record in [wm-class-database.json](https://github.com/BlueManCZ/SIF/blob/master/wm-class-database.json).
    2. If particular icon is available in the selected icon theme.
3. Creates hidden .desktop file with correct **Name**, **Icon** and **StartupWMClass** for each game.

# Installation

All you need to do is clone this repository and set the script executable:
```
git clone https://github.com/BlueManCZ/SIF.git
cd SIF
chmod +x sif.py
```

# Usage

You can check which games can be fixed before applying the fix:
```
./sif.py --icons
```
or:
```
./sif.py --pretend
```
If commands above worked without problem, you can apply the fix:
```
./sif.py 
```
If you want to clear previous fixes before applying new ones:
```
./sif.py --clear
```
If you want remove all changes and restore default icons:
```
./sif.py --restore
```

# Contribution

For the fix to work, I need to know WM_CLASS of each individual game.
I can create fixes only for games which I have installed and I can get
WM_CLASS from them.

If you want append your game to our database, you have to know **APP_ID**
and **WM_CLASS** of this game.

#### Get APP_ID

There are multiple ways, how to get APP_ID of Steam game.

1. From the [steamdb.info](https://steamdb.info/).
2. From the [store.steampowered.com](https://store.steampowered.com/) URL address.
3. If the game has icon available in icon theme, you can use `./sif.py --icons` and determine APP_ID from icon name.

#### Get WM_CLASS

Users with xorg can use xprop tool.

1. Start your game from Steam library.
2. Open new terminal window and run `xprop WM_CLASS`.
3. Switch to the game window and left click with mouse on it.
4. Switch back to the terminal and get your WM_CLASS.

#### Create issue or append database 

You can open a [new issue](https://github.com/BlueManCZ/SIF/issues), where you insert APP_ID, WM_CLASS (and your icon theme),
and I will add your game to the database as soon as possible.

You can also fork this repository, edit  [wm-class-database.json](https://github.com/BlueManCZ/SIF/blob/master/wm-class-database.json)
yourself and create a [pull request](https://github.com/BlueManCZ/SIF/pulls). Please keep the file sorted by APP_ID.

Your contribution is welcome.

