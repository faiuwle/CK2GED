#!/usr/bin/python3

import sys
import os.path

import settings
from gamedata import prepare_game_data
from titlehistorybrowser import TitleHistoryBrowser

def main():
    settings.generate_titles = True
    game_data, filename = prepare_game_data()
    title_history_browser = TitleHistoryBrowser(game_data)

    try:
        title_history_browser.run()
    except Exception:
        if settings.debug:
            raise
        else:
            print('Error running the title history browser.')
            print('Please post to the Paradox Interactive forums, describing'
                  ' what you were trying to do when the tool crashed, along'
                  ' with a copy of your save.')
            sys.stdin.readline()
            sys.exit()

if __name__ == '__main__':
    main()
