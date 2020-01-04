#!/usr/bin/python3

import sys
import os.path

import settings
from gamedata import prepare_game_data
from gedcomwriter import GedcomWriter

def main():
    game_data, filename = prepare_game_data()

    if not game_data.mark_characters(settings.real_fathers):
        sys.stdin.readline()
        sys.exit()

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
            sys.stdout.flush()
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
            sys.stdout.flush()
            sys.stdin.readline()
            sys.exit()

if __name__ == '__main__':
    main()
