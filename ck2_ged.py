#!/usr/bin/python

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
    print 'Did not find CK2 install dir:', settings.ck2_install_dir
    print 'Please modify settings.py to use the correct path.'
    sys.stdin.readline()
    sys.exit()
  except Exception:
    if settings.debug:
      raise
    else:
      print 'Error initializing game data.'
      print 'Check that the locations in settings.py are correct.'
      print 'Otherwise please post to the Paradox Interactive Forums thread,',
      print 'noting any mods you are using.'
      sys.stdin.readline()
      sys.exit()

  print '\nPlease enter the name of your save file, without the .ck2: ',
  filename = sys.stdin.readline().strip()

  print '\n'

  if not os.path.exists(filename + '.ck2'):
    print 'Could not find save file: ', filename + '.ck2'
    sys.stdin.readline()
    sys.exit()

  try:
    game_data.read_save(filename + '.ck2', settings.generate_titles)
  except Exception:
    if settings.debug:
      raise
    else:
      print 'Error reading save file.'
      print 'Please post to the Paradox Interactive Forums thread, upload',
      print 'your save and note any mods you are using.'
      sys.stdin.readline()
      sys.exit()

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
      print 'Error generating GEDCOM family information.'
      print 'Please post to the Paradox Interactive Forums thread, upload',
      print 'your save and note any mods you are using.'
      sys.stdin.readline()
      sys.exit()

  try:
    gedcom_writer.write_gedcom(filename + '.ged')
  except Exception:
    if settings.debug:
      raise
    else:
      print 'Error writing GEDCOM file.'
      print 'Please post to the Paradox Interactive Forums thread, upload',
      print 'your save and note any mods you are using.'
      sys.stdin.readline()
      sys.exit()

  num_titles = [0, 0, 0, 0, 0, 0, 0, 0]

  for t in game_data.title_map:
    if '_dyn_' in t:
      continue

    num_titles[game_data.title_map[t].rank] += 1
    if game_data.title_map[t].rank == 0:
      print t

  print num_titles[0], 'empires'
  print num_titles[1] + num_titles[6], 'kingdoms'
  print num_titles[2] + num_titles[5], 'duchies'
  print num_titles[3], 'counties'
  print num_titles[4], 'holdings',
  print num_titles[7], 'unidentified'

if __name__ == '__main__':
  main()
