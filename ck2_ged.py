#!/usr/bin/python3

import sys
import os.path

import settings
from gamedata import GameData, InstallDirNotFoundError
from gedcomwriter import GedcomWriter

def main():
    game_data = GameData()

    try:
        game_data.initialize(settings.ck2_install_dir, settings.mod_dir)
    except InstallDirNotFoundError:
        print('Did not find CK2 install dir:', settings.ck2_install_dir)
        print('Please modify settings.py to use the correct path.')
        sys.stdin.readline()
        sys.exit()
    except Exception:
        if settings.debug:
            raise
        else:
            print('Error initializing game data.')
            print('Check that the locations in settings.py are correct.')
            print('Otherwise please post to the Paradox Interactive Forums'
		  ' thread, noting any mods you are using.')
            sys.stdin.readline()
            sys.exit()

    print('\nPlease enter the name of your save file, without the .ck2: ', 
	  end=' ')
    filename = sys.stdin.readline().strip()
    if filename.endswith('.ck2'):
        filename = filename[:-4]

    print('\n')

    if not os.path.exists(filename + '.ck2'):
        print('Could not find save file: ', filename + '.ck2')
        sys.stdin.readline()
        sys.exit()

    try:
        game_data.read_save(filename + '.ck2', settings.generate_titles)
    except Exception:
        if settings.debug:
            raise
        else:
            print('Error reading save file.')
            print('Please ensure that your save is UNENCRYPTED.')
            print('If that is not the problem, please post to the Paradox'
		  ' Interactive Forums thread, upload your save and note any'
		  ' mods you are using.')
            sys.stdin.readline()
            sys.exit()

    if not game_data.mark_characters(settings.real_fathers):
        sys.stdin.readline()
        sys.exit()

    player_id = game_data.player_id
    character_map = game_data.character_map
    title_map = game_data.title_map
    history = character_map[player_id].get_title_history(character_map, title_map)
    for line in history:
        print(line)

    while True:
        print('>', end=' ')
        char_id = sys.stdin.readline().strip()
        try:
            char_id = int(char_id)
        except ValueError:
            break
        history = character_map[char_id].get_title_history(character_map, title_map)
        for line in history:
            print(line)

    gedcom_writer = GedcomWriter()

    try:
        gedcom_writer.initialize(game_data)
    except Exception:
        if settings.debug:
            raise
        else:
            print('Error generating GEDCOM family information.')
            print('Please post to the Paradox Interactive Forums thread,'
		  ' upload your save and note any mods you are using.')
            sys.stdin.readline()
            sys.exit()

    try:
        gedcom_writer.write_gedcom(filename + '.ged')
    except Exception:
        if settings.debug:
            raise
        else:
            print('Error writing GEDCOM file.')
            print('Please post to the Paradox Interactive Forums thread,'
		  ' upload your save and note any mods you are using.')
            sys.stdin.readline()
            sys.exit()

if __name__ == '__main__':
    main()
