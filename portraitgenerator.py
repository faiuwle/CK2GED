import zipfile
import os.path

class PortraitGenerator(object):
  letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',  \
             'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']

  def __init__(self, character_map, portrait_map, sprite_map):
    self.character_map = character_map
    self.portrait_map = portrait_map
    self.sprite_map = sprite_map

    for c in self.character_map:
      self.resolve_properties(c)

  # Here we attempt to determine properties by reproducing logic from
  # 00_portrait_properties.txt
  def resolve_properties(c):
    character = self.character_map[c]
    properties = character.properties

    # background
    if properties[0] == '0':
      weights = []

      # castle 1
      if character.religion.group != 'christian':
        weights.append(0)
      elif character.government == 'nomadic':
        weights.append(0)
      else:
        weights.append(1)

      # throne room
      primary = character.title_history.primary
      if len(primary) < 2:
        weights.append(0)
      elif primary[:2] not in ['k_', 'e_']:
        weights.append(0)
      elif character.government == 'nomadic':
        weights.append(0)
      elif character.government == 'tribal':
        weights.append(0)
      else:
        weights.append(50)

      # dungeon
      weights.append(0)

      # forest
      factor = 1
      if character.religion.group == 'muslim':
        factor = 0
      if character.government == 'nomadic':
        factor *= 0.01
      if character.government == 'tribal':
        factor *= 10
      weights.append(factor)

      # bed
      weights.append(0)

      # tavern
      if 33 in character.traits or 64 in character.traits  \
         or 73 in character.traits:
        weights.append(100)
      else:
        weights.append(0)

      # military camp
      weights.append(0)

      # dolmen
      factor = 5
      if character.religion.group != 'pagan_group':
        factor = 0
      if character.government == 'temple' and primary != '':
        factor *= 2
      weights.append(factor)

      # gallows
      if 68 in character.traits:
        weights.append(100)
      elif 101 in character.traits:
        weights.append(5)
      else:
        weights.append(0)

      # church
      if character.religion.group != 'christian':
        weights.append(0)
      elif primary == '' or character.government != 'temple':
        weights.append(0)
      else:
        weights.append(100)
