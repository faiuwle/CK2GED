#!/usr/bin/python

import sys
import zipfile
from os import listdir
import os.path

## User Options ######################################################
# Your CK2 install directory:
#ck2_install_dir = r'C:\Program Files (x86)\Steam\steamapps\common\Crusader Kings II'
ck2_install_dir = r'/home/ruth/.local/share/Steam/steamapps/common/Crusader Kings II'
# Your mod directory where mods get installed:
#mod_dir = r'C:\Users\User\Documents\Paradox Interactive\Crusader Kings II\mod'
mod_dir = r'/home/ruth/.paradoxinteractive/Crusader Kings II/mod'
# Remove characters with no family? (Mainly only has an effect if you generate the entire tree)
cull_loners = True
# Remove otherwise unrelated spouses that produced no children?
cull_childless_spouses = False
# Use real fathers (as opposed to presumed fathers?
real_fathers = False
# Generate primary title in "occupation" field and years of rule in "notes" field?
generate_titles = True

#Create .csv files
create_dynasty_csv = False
create_character_csv = False
create_family_csv = False

## Initialization ####################################################
#Debugging Toggles
debug_parse = False

if create_dynasty_csv or create_character_csv or create_family_csv:
  create_csv = True
else:
  create_csv = False

#Constants
digits = ['0','1','2','3','4','5','6','7','8','9']
month_name = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
full_month_name = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
whitespace = [' ', '\t', '\n', '\r']
special_chars = ['{', '}', '=', '"', '#']

NONE = 7
VICEKING = 6
VICEDUKE = 5
BARON = 4
COUNT = 3
DUKE = 2
KING = 1
EMPEROR = 0
#rank_names = [['Empress', 'Queen', 'Duchess', 'Countess', 'Baroness', ''], ['Emperor', 'King', 'Duke', 'Count', 'Baron', '']]

#Data Objects
class Date(object):
  def __init__(self):
    self.year = 0
    self.month = 0
    self.day = 0
  def set_date(self, date_parts):
    self.year = date_parts[0]
    self.month = date_parts[1]
    self.day = date_parts[2]
    if self.month < 1:
      self.month = 1
    if self.month > 12:
      self.month = 12
  def is_null(self):
    return self.year < 1 or self.month < 1 or self.month > 12 or self.day < 1
  def __cmp__(self, other):
    if self.year != other.year:
      return self.year - other.year
    elif self.month != other.month:
      return self.month - other.month
    else:
      return self.day - other.day
  def __str__(self):
    if self.is_null():
      return ''
    return full_month_name[self.month-1] + ' ' + str(self.day) + ' ' + str(self.year)
  def gedcom_string(self):
    if self.is_null():
      return ''
    return str(self.day) + ' ' + month_name[self.month-1] + ' ' + str(self.year)
    
class Range(object):
  def __init__(self, first, second):
    self.start = first
    self.end = second
  def __str__(self):
    return '(' + str(self.start) + ' - ' + str(self.end) + ')'
  def __cmp__(self, other):
    if self.start < other.start:
      return -1
    elif self.start > other.start:
      return 1
    else:
      return 0
  def is_null(self):
    return self.start.is_null() or self.end.is_null()
  def contains(self, other):
    if self.is_null() or other.is_null():
      return False
    if type(other) == Date:
      return other >= self.start and other <= self.end
    elif type(other) == Range:
      return other.start >= self.start and other.end <= self.end
  def overlaps(self, other):
    if other.start > self.end:
      return False
    if self.start > other.end:
      return False
    return True
  def append(self, other):
    if self.is_null() or other.is_null():
      return
    if other.start < self.start:
      self.start = other.start
    if other.end > self.end:
      self.end = other.end
      
class Dynasty(object):
  def __init__(self):
    self.id = -1
    self.name = ''
    self.culture = ''
    self.religion = ''
      
class Culture(object):
  def __init__(self):
    self.id = ''
    self.group = ''
    self.dukes_called_kings = False
    
class Religion(object):
  def __init__(self):
    self.id = ''
    self.group = ''
    self.priest_title = ''
      
class Title(object):
  def __init__(self):
    self.id = ''
    self.name = ''
    self.cultural_names = {}
    self.rank = NONE
    self.rank_name = ['', '']
    self.viceroyalty = False
    self.independent = True
    self.religious_head = False
  def __cmp__(self, other):
    return self.rank - other.rank
      
class TitleHistory(object):
  def __init__(self):
    self.titles = {}
    self.primary = ''
    self.primary_set = False
    self.highest_rank = NONE
    self.culture = Culture()
    self.religion = Religion()
    self.government = ''
  def add_title(self, title, r, primary_eligible):
    if title.id in self.titles:
      self.titles[title.id].append(r)
    else:
      self.titles[title.id] = [r]
    if not self.primary_set and primary_eligible and title.rank < self.highest_rank:
      self.highest_rank = title.rank
      self.primary = title.id
  def assign_religious_head_primary(self, religious_head_titles):
    for t in self.titles:
      if t in religious_head_titles:
        self.primary = t
        break
  def get_primary(self, rank_names, title_map):
    if self.primary == '':
      return ''
    if self.government == 'temple':
      cul_rel = self.religion
    else:
      cul_rel = self.culture
    if self.primary in title_map:
      p = title_map[self.primary]
      rank = p.rank
      if rank == DUKE and self.independent and self.culture.dukes_called_kings:
        rank = KING
      if p.viceroyalty:
        if rank == DUKE:
          rank = VICEDUKE
        if rank == KING:
          rank = VICEKING
      if p.rank_name[self.gender] == '':
        s = get_rank(rank_names, rank, self.government, cul_rel, self.gender) + ' ' + self.name
      else:
        s = p.rank_name[self.gender] + ' ' + self.name
      if not p.religious_head:
        if self.culture.id in p.cultural_names:
          s += ' of ' + p.cultural_names[self.culture.id]
        else:
          s += ' of ' + p.name
      return s
    else:
      if self.primary.startswith('b_'):
        rank = BARON
      elif self.primary.startswith('c_'):
        rank = COUNT
      elif self.primary.startswith('d_') and self.independent and self.culture.dukes_called_kings:
        rank = KING
      elif self.primary.startswith('d_'):
        rank = DUKE
      elif self.primary.startswith('k_'):
        rank = KING
      elif self.primary.startswith('e_'):
        rank = EMPEROR
      else:
        rank = NONE
      return get_rank(rank_names, rank, self.government, cul_rel, self.gender) + ' ' + name + ' of ' + self.primary
  def get_years_of_rule(self, rank_names, title_map):
    if len(self.titles) == 0:
      return []
    strings = []
    title_list = []
    for t in self.titles:
      title_list.append(title_map[t])
    title_list.sort()
    year_range = [[], [], [], [], [], []]
    if self.government == 'temple':
      cul_rel = self.religion
    else:
      cul_rel = self.culture
    for t in title_list:
      history = self.titles[t.id]
      for r in history:
        if r.is_null():
          continue
        if t.rank != EMPEROR:
          skip = False
          for rank in range(EMPEROR, t.rank):
            for ran in year_range[rank]:
              if ran.contains(r) and not t.religious_head:
                skip = True
          if skip:
            continue
        rank = t.rank
        if rank == DUKE and self.independent and self.culture.dukes_called_kings:
          rank = KING
        if t.viceroyalty:
          if rank == DUKE:
            rank = VICEDUKE
          if rank == KING:
            rank = VICEKING
        if t.rank_name[self.gender] == '':
          s = get_rank(rank_names, rank, self.government, cul_rel, self.gender) + ' of '
        else:
          s = t.rank_name[self.gender] + ' of '
        if self.culture.id in t.cultural_names:
          s += t.cultural_names[self.culture.id] + ' ' + str(r)
        else:
          s += t.name + ' ' + str(r)
        strings.append((s, r))
        range_added = False
        for ran in year_range[t.rank]:
          if ran.overlaps(r):
            ran.append(r)
            range_added = True
        if not range_added:
          year_range[t.rank].append(Range(r.start, r.end))
    strings = sorted(strings, key=lambda x: x[1])
    return [x[0] for x in strings]

class Character(object):
  """Stores information relevant to a character."""
  def __init__(self):
    self.id = [] #Game ID
    self.birth_name = ''
    self.regnal_name = ''
    self.nickname = ''
    self.gender = 1
    self.birthday = []
    self.deathday = []
    self.culture = ''
    self.religion = ''
    self.father = ''
    self.real_father = ''
    self.mother = ''
    self.spouse = []
    self.children = []
    self.dynasty_id = -1
    self.dynasty_name = ''
    self.title_history = TitleHistory()
    self.government = ''
    self.independent = True
    self.loner = True
    self.GEDCOM_id = ''
    self.FAMS = []
    self.FAMC = ''
    self.mark = False
    self.family_marked = False
  def inform_title_history(self, culture_map, religion_map, government_map):
    if self.culture in culture_map:
      self.title_history.culture = culture_map[self.culture]
    else:
      print 'Character', self.id, 'has no culture'
    if self.religion in religion_map:
      self.title_history.religion = religion_map[self.religion]
    else:
      print 'Character', self.id, 'has no religion'
    if self.government in government_map:
      self.title_history.government = government_map[self.government]
    self.title_history.gender = self.gender
    self.title_history.independent = self.independent
    if self.nickname == '': 
      self.title_history.name = self.regnal_name
    else:
      self.title_history.name = self.regnal_name + ' ' + self.nickname
  def get_primary_title(self, rank_names, title_map):
    return self.title_history.get_primary(rank_names, title_map)
  def get_years_of_rule(self, rank_names, title_map):
    return self.title_history.get_years_of_rule(rank_names, title_map)

class Family(object):
  """Stores information relevant to a family (GEDCOM definition)."""
  def __init__(self):
    self.id = ''
    self.father = []
    self.mother = []
    self.children = []
    
#Helper Functions
def debug_write(message):
  if debug_parse:
    debug_out.write(message + '\n')

def parse_date(date_string):
  parts = date_string.split('.')
  if len(parts) != 3:
    return []
  try:
    int_parts = map(int, parts)
  except ValueError:
    return []
  date = Date()
  date.set_date(int_parts)
  return date
  
def is_integer(string):
  for c in string:
    if c not in digits:
      return False
      
  return True
  
def guess_title_name(title_id):
  parts = title_id.split('_')
  for i, p in enumerate(parts):
    parts[i] = p[0].upper() + p[1:]
  return ' '.join(parts[1:])
  
def parse_ck2_data(string, is_save = False, empty_values = False):
  current_keys = []
  current_value = ''
  current_line = 1
  
  if is_save:
    state = 'begin'
  else:
    state = 'expect_key'
    
  saved_state = ''
  temp_string = ''
  
  chars_per_increment = len(string) / 80 + 1
  chars_until_progress = chars_per_increment

  for x in string:
    chars_until_progress -= 1
    if chars_until_progress == 0:
      sys.stdout.write('=')
      chars_until_progress = chars_per_increment

    if x == '\n':
      current_line += 1
        
    if state == 'begin':
      if temp_string == 'CK2txt':
        state = 'expect_key'
        temp_string = ''
      else:
        temp_string += x
        
    elif state == 'expect_key':
      if x == '}' and len(current_keys) > 0:
        if empty_values:
          yield (current_keys, current_value)
        current_keys = current_keys[:-1]
      elif x == '{':
        current_keys.append('')
      elif x == '#':
        saved_state = 'expect_key'
        state = 'comment'
      elif x in special_chars:
        debug_write('Unexpected character ' + x + ' on line ' + repr(current_line) + ' (expect_key)')
      elif x not in whitespace:
        temp_string = x
        state = 'key'
          
    elif state == 'key':
      if x == '=':
        current_keys.append(temp_string)
        temp_string = ''
        state = 'expect_value'
      elif x == '}':      # e.g. societies={2}, the 2 is read as a key because it follows a {
        current_value = [temp_string]
        yield (current_keys, current_value)
        temp_string = ''
        current_value = ''
        if len(current_keys) > 0:
          current_keys = current_keys[:-1]
        state = 'expect_key'
      elif x in special_chars:
        debug_write('Unexpected character in key: ' + x + ' on line ' + repr(current_line) + ' (key)')
      elif x not in whitespace:
        temp_string += x
      elif temp_string != '':
        current_value = [temp_string]
        temp_string = ''
        state = 'list'
          
    elif state == 'expect_value':
      if x == '"':
        state = 'quoted_value'
        temp_string = ''
      elif x == '{':
        state = 'expect_key'
      elif x in special_chars:
        debug_write('Unexpected character ' + x + ' on line ' + repr(current_line) + ' (expect_value)')
      elif x not in whitespace:
        temp_string = x
        state = 'value'
          
    elif state == 'value':
      if x in whitespace or x == '}':
        current_value = temp_string
        temp_string = ''
        yield (current_keys, current_value)
        current_value = ''
        if len(current_keys) > 0:
          current_keys = current_keys[:-1]
        if x == '}' and len(current_keys) > 0:
          current_keys = current_keys[:-1]
        state = 'expect_key'
      elif x == '{':
        current_value = temp_string
        temp_string = ''
        yield (current_keys, current_value)
        current_value = ''
        if len(current_keys) > 0:
          current_keys = current_keys[:-1]
        current_keys.append('')
        state = 'expect_key'
      elif x == '#':
        current_value = temp_string
        temp_string = ''
        yield (current_keys, current_value)
        current_value = ''
        if len(current_keys) > 0:
          current_keys = current_keys[:-1]
        saved_state = 'expect_key'
        state = 'comment'
      elif x in special_chars:
        debug_write('Unexpected character ' + x + ' on line ' + current_line + ' (value)')
      else:
        temp_string += x
        
    elif state == 'quoted_value':
      if x == '"':
        current_value = temp_string
        temp_string = ''
        yield (current_keys, current_value)
        current_value = ''
        if len(current_keys) > 0:
          current_keys = current_keys[:-1]
        state = 'expect_key'
      else:
        temp_string += x
         
    elif state == 'list':
      if x == '}':
        yield (current_keys, current_value)
        current_value = ''
        if len(current_keys) > 0:
          current_keys = current_keys[:-1]
        state = 'expect_key'
      elif x == '=' and len(current_value) == 1:  # oops it's actually a key
        current_keys.append(current_value[0])
        current_value = ''
        temp_string = ''
        state = 'expect_value'
      elif x == '#':
        saved_state = 'list'
        state = 'comment'
      elif x == '"':
        state = 'quoted_list_item'
        temp_string = ''
      elif x in special_chars:
        debug_write('Unexpected character ' + x + ' on line ' + repr(current_line) + ' (list)')
      elif x not in whitespace:
        temp_string = x
        state = 'list_item'
         
    elif state == 'list_item':
      if x == '}':
        current_value.append(temp_string)
        temp_string = ''
        yield (current_keys, current_value)
        current_value = ''
        if len(current_keys) > 0:
          current_keys = current_keys[:-1]
        state = 'expect_key'
      elif x in whitespace:
        current_value.append(temp_string)
        temp_string = ''
        state = 'list'
      elif x == '#':
        current_value.append(temp_string)
        temp_string = ''
        saved_state = 'list'
        state = 'comment'
      elif x in special_chars:
        debug_write('Unexpected character ' + x + ' on line ' + repr(current_line) + ' (list_item)')
      else:
        temp_string += x
        
    elif state == 'quoted_list_item':
      if x == '"':
        current_value.append(temp_string)
        temp_string = ''
        state = 'list'
      else:
        temp_string += x
          
    elif state == 'comment':
      if x == '\n':
        state = saved_state
        saved_state = ''  

  print ''
  
def read_dynasties_file(file, dynasty_map):
  file_contents = file.read()
  
  for keys, value in parse_ck2_data(file_contents, False):
    if len(keys) >= 2 and is_integer(keys[0]):
      id = int(keys[0])
      if id not in dynasty_map:
        dynasty = Dynasty()
        dynasty.id = id
        dynasty_map[id] = dynasty
        
      dynasty = dynasty_map[id]
    
      if keys[1] == 'name':
        dynasty.name = value
      elif keys[1] == 'culture':
        dynasty.culture = value
      elif keys[1] == 'religion' and dynasty.religion == '':
        dynasty.religion = value
      elif len(keys) == 3 and keys[1] == 'coat_of_arms' and keys[2] == 'religion':
        dynasty.religion = value
   
  return dynasty_map
  
def read_cultures_file(file, culture_map):
  file_contents = file.read()
  
  for keys, value in parse_ck2_data(file_contents, False):
    if len(keys) == 3 and keys[2] == 'color':
      culture = Culture()
      culture.id = keys[1]
      culture.group = keys[0]
      culture_map[keys[1]] = culture
      
    if len(keys) == 3 and keys[2] == 'dukes_called_kings' and value == 'yes':
      culture_map[keys[1]].dukes_called_kings = True
      
  return culture_map
  
def read_religions_file(file, religion_map, misc_localization):
  file_contents = file.read()
  
  for keys, value in parse_ck2_data(file_contents, False):
    if len(keys) == 3 and keys[2] == 'color' and keys[1] not in religion_map:
      religion = Religion()
      religion.id = keys[1]
      religion.group = keys[0]
      religion_map[keys[1]] = religion
      
    if len(keys) == 3 and keys[2] == 'priest_title':
      if keys[1] not in religion_map:
        religion = Religion()
        religion.id = keys[1]
        religion.group = keys[0]
        religion_map[keys[1]] = religion
      
      religion_map[keys[1]].priest_title = value
      misc_localization.append(value)
      
  return (religion_map, misc_localization)
  
def read_landed_titles_file(file, title_map, culture_map, misc_localization, religious_head_titles):
  file_contents = file.read()
  
  for keys, value in parse_ck2_data(file_contents, False, True):
    if len(keys) > 1 and keys[-2] not in title_map \
       and (keys[-1] in ['color', 'title', 'title_female', 'controls_religion'] or keys[-1] in culture_map):
      title = Title()
      title.id = keys[-2]
      title.name = guess_title_name(keys[-2])
      
      rank = NONE
      if keys[-2].startswith('e_'):
        rank = EMPEROR
      elif keys[-2].startswith('k_'):
        rank = KING
      elif keys[-2].startswith('d_'):
        rank = DUKE
      elif keys[-2].startswith('c_'):
        rank = COUNT
      elif keys[-2].startswith('b_'):
        rank = BARON

      title.rank = rank
      title_map[keys[-2]] = title
    
    if len(keys) > 1 and keys[-1] in culture_map:
      title = title_map[keys[-2]]
      title.cultural_names[keys[-1]] = value
      
    if len(keys) > 1 and keys[-1] == 'title':
      title_map[keys[-2]].rank_name[1] = value
      misc_localization.append(value)
      
    if len(keys) > 1 and keys[-1] == 'title_female':
      title_map[keys[-2]].rank_name[0] = value
      misc_localization.append(value)
      
    if len(keys) > 1 and keys[-1] == 'controls_religion':
      title_map[keys[-2]].religious_head = True
      religious_head_titles.append(keys[-2])
      
    if value == '' and keys[-1].startswith('b_') and keys[-1] not in title_map:
      title = Title()
      title.id = keys[-1]
      title.name = keys[-1]
      title.rank = BARON
      title_map[keys[-1]] = title
      
  return (title_map, misc_localization, religious_head_titles)
  
def read_governments_file(file, government_map):
  file_contents = file.read()
  
  for keys, value in parse_ck2_data(file_contents):
    if len(keys) == 3 and keys[2] == 'allowed_holdings':
      if keys[1] not in government_map:
        government_map[keys[1]] = ''
  
    if len(keys) == 3 and keys[2] == 'title_prefix':
      government_map[keys[1]] = value.strip('_')
      
  return government_map
  
def read_localization_file(file, title_map, rank_names, misc_localization, cultures, 
                           religions, gov_types):
  base_rank = ['emperor', 'king', 'duke', 'count', 'baron']

  for line in file:
    if line.startswith('#'):
      continue
    
    parts = line.split(';')
    if len(parts) < 2:
      continue
    key = parts[0]
    value = parts[1]
    
    if key in title_map:
      title_map[key].name = value
    elif key in misc_localization:
      misc_localization[key] = value
      
    else:
      key_base_rank = NONE
      key_gov_type = ''
      key_gender = 1
      key_culture_religion = ''
      key_viceroyalty = False
      
      key_parts = key.split('_')
      key_parts_used = []
      
      for r in base_rank:
        if r in key_parts:
          key_base_rank = base_rank.index(r)
          key_parts_used.append(key_parts.index(r))
          
      if key_base_rank == NONE:
        continue
        
      for g in gov_types:
        if g in key_parts:
          key_gov_type = g
          key_parts_used.append(key_parts.index(g))
          
      if 'female' in key_parts:
        key_gender = 0
        key_parts_used.append(key_parts.index('female'))
      
      if 'vice' in key_parts and 'royalty' in key_parts and key_parts.index('vice') == key_parts.index('royalty') - 1:
        key_viceroyalty = True
        key_parts_used.append(key_parts.index('vice'))
        key_parts_used.append(key_parts.index('royalty'))
        
      # Remaining key parts must be culture or religion
      remainder = ''
      for i, k in enumerate(key_parts):
        if i not in key_parts_used:
          remainder += k + '_'
      remainder = remainder.strip('_')
      
      if key_gov_type == 'temple' and remainder in religions:
        key_culture_religion = remainder
      elif key_gov_type != 'temple' and remainder in cultures:
        key_culture_religion = remainder
      elif remainder != '':
        continue
        
      if key_gov_type not in rank_names:
        rank_names[key_gov_type] = [{}, {}, {}, {}, {}, {}, {}]
        
      if key_viceroyalty:
        if key_base_rank == DUKE:
          key_base_rank = VICEDUKE
        elif key_base_rank == KING:
          key_base_rank = VICEKING
        else:
          continue
        
      if key_culture_religion not in rank_names[key_gov_type][key_base_rank]:
        rank_names[key_gov_type][key_base_rank][key_culture_religion] = ['', '']
        
      rank_names[key_gov_type][key_base_rank][key_culture_religion][key_gender] = value
      
  return (title_map, rank_names, misc_localization)
  
def read_save(filename, dynasty_map):
  character_map = {}
  nicknames = []
  
  player_id = -1
  date = []
  
  title_id = ''
  title_date = []
  title_holder = 0
  title_map = {}
  
  debug_write('Parsing ' + filename)

  with zipfile.ZipFile(filename+'.ck2','r') as file:
    file_contents = file.read(filename + '.ck2')
    
    for keys, value in parse_ck2_data(file_contents, True):
      if len(keys) == 2 and keys[0] == 'player' and keys[1] == 'id' and is_integer(value):
        player_id = int(value)
        
      if len(keys) == 1 and keys[0] == 'date':
        date = parse_date(value)
      
      if len(keys) >= 3 and keys[0] == 'dynasties' and is_integer(keys[1]):
        id = int(keys[1])
        if id not in dynasty_map:
          dynasty = Dynasty()
          dynasty.id = id
          dynasty_map[id] = dynasty
          
        dynasty = dynasty_map[id]
      
        if keys[2] == 'name':
          dynasty.name = value
        elif keys[2] == 'culture':
          dynasty.culture = value
        elif keys[2] == 'religion' and dynasty.religion == '':
          dynasty.religion = value
        elif len(keys) == 4 and keys[2] == 'coat_of_arms' and keys[3] == 'religion':
          dynasty.religion = value
        
      if len(keys) >= 3 and keys[0] == 'character' and is_integer(keys[1]):
        id = int(keys[1])
        if id not in character_map:
          character_map[id] = Character()
          
        character = character_map[id]
        character.id = id
          
        if keys[2] == 'bn':
          character.birth_name = value
          if character.regnal_name == '':
            character.regnal_name = value
        elif keys[2] == 'name':
          character.regnal_name = value
        elif keys[2] == 'b_d':
          character.birthday = parse_date(value)
        elif keys[2] == 'd_d':
          character.deathday = parse_date(value)
        elif keys[2] == 'fem' and value == 'yes':
          character.gender = 0
        elif keys[2] == 'cul':
          character.culture = value
        elif keys[2] == 'rel':
          character.religion = value
        elif keys[2] == 'fat' and is_integer(value):
          character.father = int(value)
        elif keys[2] == 'rfat' and is_integer(value):
          character.real_father = int(value)
        elif keys[2] == 'mot' and is_integer(value):
          character.mother = int(value)
        elif keys[2] == 'dnt' and is_integer(value):
          character.dynasty_id = int(value)
          character.dynasty_name = dynasty_map[int(value)].name
          if character.culture == '':
            character.culture = dynasty_map[int(value)].culture
          if character.religion == '':
            character.religion = dynasty_map[int(value)].religion
        elif keys[2] == 'spouse' and is_integer(value):
          character.spouse.append(int(value))
        elif keys[2] == 'gov':
          character.government = value
        elif keys[2] == 'lge':
          character.independent = False
        elif generate_titles and keys[2] == 'oh' and not character.title_history.primary_set:
          character.title_history.primary = value
          character.title_history.primary_set = True
        elif len(keys) == 4 and keys[2] == 'nick' and keys[3] == 'nickname':
          character.nickname = value
          nicknames.append(value)
        elif generate_titles and len(keys) == 5 and keys[2] == 'dmn' and keys[3] == 'primary' and keys[4] == 'title':
          character.title_history.primary = value
          character.title_history.primary_set = True
          
      if not generate_titles and keys[0] == 'delayed_event':
        break
          
      if len(keys) >= 2 and keys[0] == 'title':
        if keys[1] not in title_map:
          rank = NONE
          if keys[1].startswith('e_'):
            rank = EMPEROR
          elif keys[1].startswith('k_'):
            rank = KING
          elif keys[1].startswith('d_'):
            rank = DUKE
          elif keys[1].startswith('c_'):
            rank = COUNT
          elif keys[1].startswith('b_'):
            rank = BARON
          title_map[keys[1]] = Title()
          title_map[keys[1]].id = keys[1]
          title_map[keys[1]].name = guess_title_name(keys[1])
          title_map[keys[1]].rank = rank
          
        if len(keys) == 3 and keys[1].startswith('b_') and not keys[1].startswith('b_dyn_') and keys[2] == 'holder' and is_integer(value):
          character_map[int(value)].title_history.add_title(title_map[keys[1]], Range(Date(), Date()), True)
          
        if keys[1].startswith('b_dyn_'):
          founder_id = keys[1].split('_')[-1]
          if is_integer(founder_id):
            dynasty_id = character_map[int(founder_id)].dynasty_id
            title_map[keys[1]].name = 'House ' + dynasty_map[dynasty_id].name
            title_map[keys[1]].rank_name[1] = 'Patrician'
            
        if keys[2] == 'liege':
          title_map[keys[1]].independent = False
          
        if keys[2] == 'vice_royalty' and value == 'yes':
          title_map[keys[1]].viceroyalty = True
          
      if len(keys) >= 5 and keys[0] == 'title' and keys[2] == 'history' and keys[4] == 'holder':
        if len(keys) == 6 and keys[5] == 'type':
          continue
            
        if title_id != '' and title_id != keys[1] and type(title_date) == Date and title_holder in character_map:
          character = character_map[title_holder]
          r = Range(title_date, date)
          character.title_history.add_title(title_map[title_id], r, True)
          if character.title_history.primary == title_id:
            character.independent = title_map[title_id].independent
          
        elif title_id != '' and type(parse_date(keys[3])) == Date and type(title_date) == Date and title_holder in character_map:
          character = character_map[title_holder]
          r = Range(title_date, parse_date(keys[3]))
          character.title_history.add_title(title_map[title_id], r, False)
          
        title_id = keys[1]
        title_date = parse_date(keys[3])
        if len(keys) == 5 and is_integer(value):
          title_holder = int(value)
        elif len(keys) == 6 and (keys[5] == 'character' or keys[5] == 'who') and is_integer(value):
          title_holder = int(value)
        else:
          title_holder = 0       
    
    if title_id != '' and type(title_date) == Date and title_holder in character_map:
      character = character_map[title_holder]
      r = Range(title_date, date)
      character.title_history.add_title(title_map[title_id], r, True)
      if character.title_history.primary == title_id:
        character.independent = title_map[title_id].independent
    
    file.close()
  
  return (player_id, dynasty_map, character_map, title_map, nicknames)
  
def get_rank(rank_names, rank, government, culture_religion, gender):
  if culture_religion.id in rank_names[government][rank]:
    final = rank_names[government][rank][culture_religion.id]
  elif culture_religion.group in rank_names[government][rank]:
    final = rank_names[government][rank][culture_religion.group]
  elif '' in rank_names[government][rank]:
    final = rank_names[government][rank]['']
  elif government == 'temple':
    final = ['', culture_religion.priest_title]
  elif '' in rank_names:
    final = rank_names[''][rank]['']
  else:
    final = ['Countess', 'Count']
    
  if gender == 0 and final[0] != '':
    return final[0]
  else:
    return final[1]
  
def mark_character_and_family(character_map, character_id):
  c_character = character_map[character_id]
  c_character.mark = True
  
  if c_character.family_marked == True:
    return character_map
  else:
    c_character.family_marked = True
  
  if real_fathers and type(c_character.real_father) is int:
    father_id = c_character.real_father
  else:
    father_id = c_character.father
    
  if type(father_id) is int:
    character_map[father_id].mark = True
  if type(c_character.mother) is int:
    character_map[c_character.mother].mark = True
  for s in c_character.spouse:
    character_map[s].mark = True
  for c in c_character.children:
    character_map = mark_character_and_family(character_map, c)
      
  return character_map
  
def mark_characters(character_map, player_dynasty, mode):
  if mode == 1:
    for c in character_map:
      character_map[c].mark = True
    
  elif mode == 2:
    for c in character_map:
      c_character = character_map[c]
      
      if real_fathers and type(c_character.real_father) is int:
        father_id = c_character.real_father
      else:
        father_id = c_character.father
        
      if type(father_id) is int:
        character_map[father_id].children.append(c_character.id)
      if type(c_character.mother) is int:
        character_map[c_character.mother].children.append(c_character.id)
        
    for c in character_map:
      c_character = character_map[c]
      if c_character.dynasty_id == player_dynasty:
        character_map = mark_character_and_family(character_map, c)
        
  elif mode == 3:
    for c in character_map:
      c_character = character_map[c]
      
      if c_character.dynasty_id == player_dynasty:
        character_map = mark_character_and_family(character_map, c)
        
      else:
        if real_fathers and type(c_character.real_father) is int:
          father_id = c_character.real_father
        else:
          father_id = c_character.father
          
        if type(father_id) is int and character_map[father_id].dynasty_id == player_dynasty:
          c_character.mark = True
        if type(c_character.mother) is int and character_map[c_character.mother].dynasty_id == player_dynasty:
          c_character.mark = True
          
  else:
    for c in character_map:
      c_character = character_map[c]
      
      if c_character.dynasty_id == player_dynasty:
        character_map = mark_character_and_family(character_map, c)
        
  return character_map   
  
def generate_gedcom_families(character_map):
  family_map = {}
  family_id = 1
      
  for i_character in character_map:
    c_character = character_map[i_character]
    
    if not c_character.mark:
      continue
      
    if real_fathers and type(c_character.real_father) is int:
      father_id = c_character.real_father
    else:
      father_id = c_character.father
      
    #If the character has a parent or spouse, place it into a family.
    generate_parents = False
    if type(father_id) is int and character_map[father_id].mark:
      generate_parents = True
    if type(c_character.mother) is int and character_map[c_character.mother].mark:
      generate_parents = True
      
    if generate_parents:
      c_character.loner = False
      temp = (father_id, c_character.mother)
      
      if temp not in family_map:
        family_map[temp] = Family()
        c_family = family_map[temp]
        c_family.id = family_id
        c_family.father = father_id
        c_family.mother = c_character.mother
        c_family.children.append(c_character.id)
        
        if type(c_family.father) is int:
          character_map[c_family.father].FAMS.append(c_family.id)
          character_map[c_family.father].loner = False
        if type(c_family.mother) is int:
          character_map[c_family.mother].FAMS.append(c_family.id)
          character_map[c_family.mother].loner = False
          
        c_character.FAMC = c_family.id
        family_id += 1
        
      else:
        c_family = family_map[temp]
        c_family.children.append(c_character.id)
        c_character.FAMC = c_family.id
        
    if len(c_character.spouse) > 0 and not cull_childless_spouses:
      for i_spouse in c_character.spouse:
        c_spouse = character_map[i_spouse]
        
        if not c_spouse.mark:
          continue
          
        c_character.loner = False
          
        if c_character.gender == 1 and c_spouse.gender == 0:
          temp = (c_character.id, c_spouse.id)
        elif c_character.gender == 0 and c_spouse.gender == 1:
          temp = (c_spouse.id, c_character.id)
        else:
          continue      
      
        if temp not in family_map:
          family_map[temp] = Family()
          c_family = family_map[temp]
          c_family.id = family_id
          c_family.father = temp[0]
          c_family.mother = temp[1]
          c_character.FAMS.append(c_family.id)
          c_spouse.FAMS.append(c_family.id)
          c_spouse.loner = False
          family_id += 1
              
  GEDCOM_map = {}
  GEDCOM_id = 1
  
  for i_character in character_map:
    c_character = character_map[i_character]
    
    if not c_character.mark:
      continue
      
    if not c_character.loner or not cull_loners:
      c_character.GEDCOM_id = GEDCOM_id
      GEDCOM_map[GEDCOM_id] = c_character.id
      GEDCOM_id += 1
  
  return (character_map, family_map, GEDCOM_map)
  
def write_gedcom(filename, GEDCOM_map, character_map, family_map, rank_names, title_map):
  with open(filename+'.ged','w') as file2:
    file2.write('0 HEAD\n1 FILE '+filename+'.ged\n1 GEDC\n2 VERS 5.5\n2 FORM LINEAGE-LINKED\n1 CHAR ANSI')
    
    for i_character in GEDCOM_map:
      line = ''
    
      c_character = character_map[GEDCOM_map[i_character]]
      
      if c_character.gender is 0:
        gender_string = 'F'
      else:
        gender_string = 'M'
        
      line += '\n0 @I'+str(i_character)+'@ INDI'
      line += '\n1 NAME '+c_character.birth_name+' /'+c_character.dynasty_name.upper()+'/'
      line += '\n2 GIVN '+c_character.birth_name
      line += '\n2 SURN '+c_character.dynasty_name
      line += '\n1 SEX '+gender_string
      line += '\n1 OCCU ' + c_character.get_primary_title(rank_names, title_map)
      
      years_of_rule = c_character.get_years_of_rule(rank_names, title_map)
      for s in years_of_rule:
        line += '\n1 NOTE ' + s
      
      line += '\n1 NOTE Game ID# '+str(c_character.id)
      
      if real_fathers and type(c_character.real_father) is int and type(c_character.father) is int:
        line += "\n1 NOTE Presumed father is " + character_map[c_character.father].birth_name + " "
        line += character_map[c_character.father].dynasty_name + " (" + str(c_character.father) + ")"
      elif real_fathers and type(c_character.real_father) is int:
        line += "\n1 NOTE Father unknown"
      elif not real_fathers and type(c_character.real_father) is int:
        line += "\n1 NOTE Real father is " + character_map[c_character.real_father].birth_name + " "
        line += character_map[c_character.real_father].dynasty_name + " (" + str(c_character.real_father) + ")"
        
      if type(c_character.birthday) is Date:
        line += '\n1 BIRT'
        line += '\n2 DATE '+ c_character.birthday.gedcom_string()
        
      if type(c_character.deathday) is Date:
        line += '\n1 DEAT'
        line += '\n2 DATE '+ c_character.deathday.gedcom_string()
        
      for i_ in c_character.FAMS:
        line += '\n1 FAMS @F'+str(i_)+'@'
      if c_character.FAMC != '':
        line += '\n1 FAMC @F'+str(c_character.FAMC)+'@'
        
      file2.write(line)
        
    for i_family in family_map:
      line = ''
    
      family = family_map[i_family]
      line += '\n0 @F'+str(family.id)+'@ FAM'
      
      if family.father != '':
        c_character = character_map[family.father]
        line += '\n1 HUSB @I'+str(c_character.GEDCOM_id)+'@'
      if family.mother != '':
        c_character = character_map[family.mother]
        line += '\n1 WIFE @I'+str(c_character.GEDCOM_id)+'@'
      for i_child in family.children:
        c_character = character_map[i_child]
        line += '\n1 CHIL @I'+str(c_character.GEDCOM_id)+'@'
        
      file2.write(line)
  
    file2.close()
    
  print '### Finished creating .ged file. ###'

def write_csv(filename, dynasty_map, character_map, family_map):
  print '### Creating .csv files. ###'

  if create_dynasty_csv:
    with open(filename+'_dynasty.csv','w') as file:
      file.write('ID#;Name')
      for i_ in dynasty_map:
        file.write('\n'+str(i_)+';'+dynasty_map[i_].name)
    
      file.close()

  if create_character_csv:
    with open(filename+'_character.csv','w') as file:
      file.write('Game ID#;GEDCOM ID#;Dynasty ID#;Dynasty Name;Given Name;Gender ID#;Loner?;Birth Year;')
      file.write('Birth Month;Birth Day;Death Year;Death Month;Death Day;Father ID#;Real Father ID#;')
      file.write('Mother ID#;Spouse ID#s;FAMS;FAMC')
      
      for i_ in character_map:
        line = ''
      
        c_ = character_map[i_]
      
        line += '\n'+str(i_)+';'+str(c_.GEDCOM_id)+';'+str(c_.dynasty_id)+';'
        line += str(c_.dynasty_name)+';'+str(c_.birth_name)+';'+str(c_.gender)+';'
        line += str(c_.loner)+';'
        
        if type(c_.birthday) is Date:
          line += str(c_.birthday.year)+';'+str(c_.birthday.month)+';'+str(c_.birthday.day)
        else:
          line += ';;'
        if type(c_.deathday) is Date:
          line += ';'+str(c_.deathday.year)+';'+str(c_.deathday.month)+';'+str(c_.deathday.day)
        else:
          line += ';;;'
          
        line += ';'+str(c_.father)+';'+str(c_.real_father)+';'+str(c_.mother)+';'+str(c_.spouse)+';'
        line += str(c_.FAMS)+';'+str(c_.FAMC)
        
        file.write(line)
    
      file.close()

  if create_family_csv:
    with open(filename+'_family.csv','w') as file:
      file.write('ID#;Father ID#;Mother ID#;Children ID#s')
      
      for i_ in family_map:
        f_ = family_map[i_]
        file.write('\n'+str(f_.id)+';'+str(f_.father)+';'+str(f_.mother)+';'+str(f_.children))
    
      file.close()

  ## Finalize ##########################################################
  print '### Finished creating .csv files. ###'
    
def main():
  if not os.path.exists(ck2_install_dir):
    print ''
    print ' #############################################'
    print ' # Error: cannot find CK2 install directory. #'
    print ' # Please edit the script with your path.    #'
    print ' #############################################'
    print ''
    sys.exit()
    
  if not os.path.exists(mod_dir):
    print 'Did not find mod directory.  No mods will not be loaded.'

  ## Get Information from User #########################################
  print 'Enter the name of the save file without extension: ',
  savefilename = sys.stdin.readline().strip ()
  print ''
  
  # Get list of mods
  mods = []
  
  if os.path.exists(mod_dir):  
    while True:
      mod_names = [d for d in listdir(mod_dir) if (os.path.isdir(os.path.join(mod_dir, d)) or d.endswith('.zip'))]
      print 'Please specify which mods you used with this save, by number. You can enter multiple numbers',
      print 'separated by spaces.'
      for i, m in enumerate(mod_names):
        print i + 1, m
      print 'Mods in use (press enter for no mods): ',
      try:
        mod_numbers = sys.stdin.readline().strip().split()
        mod_numbers = [int(x) for x in mod_numbers]
      except ValueError:
        print 'Please enter only numbers and spaces.'
        continue
      try:
        mods = [mod_names[i-1] for i in mod_numbers]
        break
      except KeyError:
        print 'Please only type numbers that appear on this list.'
    mods.sort()
    print ''
  
  # dir_names_lists is a dictionary of lists of files in certain directories in common/, from both 
  # vanilla and mods. At first we add just the full path to the list, but eventually list entries
  # will be tuples of (full path, base filename, location) where location is '' for the filesystem
  # and otherwise the name of the zipfile where the file can be found. We keep base filenames so that we
  # don't load files with the same base names from two different mods, or from both a mod and vanilla.
  # localization_files is a similar list for the localization files, which are not in common/
  dir_names_lists = {'dynasties': [], 'landed_titles': [], 'cultures': [], 'religions': [], 'governments': []}
  localization_files = []
  
  # Populate dir_names_lists and localization_files from mod directories and zipfiles.
  for m in mods:
    is_dir = os.path.isdir(os.path.join(mod_dir, m))  # mods can also be zipfiles
  
    if is_dir:
      common_path = os.path.join(mod_dir, m, 'common')
      localization_path = os.path.join(mod_dir, m, 'localisation')
    else:
      common_path = 'common'
      localization_path = 'localisation'
    
    for dir_name in dir_names_lists:
      path = os.path.join(common_path, dir_name)
      path = path.replace('\\', '/')  # paths in zipfiles always use /, and python doesn't care
      list = dir_names_lists[dir_name]
      files = []
      if is_dir and os.path.exists(path):
        files = [os.path.join(path, f) for f in listdir(path)]
        files = filter(os.path.isfile, files)
        files = [(f, os.path.basename(f), '') for f in files]
        files = [f for f in files if f[1] not in [x[1] for x in list]]
      elif not is_dir:
        with zipfile.ZipFile(os.path.join(mod_dir, m)) as mod_file:
          files = [f for f in mod_file.namelist() if path in f and f.endswith('.txt')]
          files = [(f, os.path.basename(f), m) for f in files]
          files = [f for f in files if f[1] not in [x[1] for x in list]]
      list.extend(files)
      
    if is_dir and os.path.exists(localization_path):
      files = [os.path.join(localization_path, f) for f in listdir(localization_path)]
      files = filter(os.path.isfile, files)
      files = [(f, os.path.basename(f), '') for f in files]
      files = [f for f in files if f[1] not in [x[1] for x in localization_files]]
      localization_files += files
    elif not is_dir:
      with zipfile.ZipFile(os.path.join(mod_dir, m)) as mod_file:
        files = [f for f in mod_file.namelist() if localization_path in f and f.endswith('.csv')]
        files = [(f, os.path.basename(f), m) for f in files]
        files = [f for f in files if f[1] not in [x[1] for x in localization_files]]
        localization_files += files
      
  # Populate dir_names_lists and localization_files from vanilla. We load this last to allow mods
  # to override vanilla files of the same name.
  common_path = os.path.join(ck2_install_dir, 'common')
  localization_path = os.path.join(ck2_install_dir, 'localisation')
  
  for dir_name in dir_names_lists:
    path = os.path.join(common_path, dir_name)
    list = dir_names_lists[dir_name]
    if os.path.exists(path):
      files = [os.path.join(path, f) for f in listdir(path)]
      files = filter(os.path.isfile, files)
      files = [(f, os.path.basename(f), '') for f in files]
      files = [f for f in files if f[1] not in [x[1] for x in list]]
      list.extend(files)
      
  if os.path.exists(localization_path):
    files = [os.path.join(localization_path, f) for f in listdir(localization_path)]
    files = filter(os.path.isfile, files)
    files = [(f, os.path.basename(f), '') for f in files]
    files = [f for f in files if f[1] not in [x[1] for x in localization_files]]
    localization_files += files

  if len(dir_names_lists['dynasties']) == 0:
    print ''
    print ' ##################################################'
    print ' # Warning: no dynasties files found.             #'
    print ' # Check ck2 install and mod directory locations. #'
    print ' ##################################################'
    print ''
    
  ## Opening dynasties files ###########################################
  try:
    dynasty_map = {}
    for filename, base, location in dir_names_lists['dynasties']:
      if location == '':
        print '### Now reading', filename, '###'
        debug_write('Parsing ' + filename)
        with open(filename) as file:
          dynasty_map = read_dynasties_file(file, dynasty_map)
      else:
        print '### Now reading', filename, 'in', location, '###'
        debug_write('Parsing ' + filename + ' in ' + location)
        with zipfile.ZipFile(os.path.join(mod_dir, location)) as mod_file:
          file = mod_file.open(filename)
          dynasty_map = read_dynasties_file(file, dynasty_map)
  except IOError:
    print ''
    print ' #######################'
    print ' # Error reading file. #'
    print ' #######################'
    print ''
    sys.exit ()
  
  ## Opening the Save File #############################################
  print '### Now reading save file. ###'
  try:
    player_id, dynasty_map, character_map, title_map, misc_localization = read_save (savefilename, dynasty_map)
  except IOError:
    print ''
    print ' #######################'
    print ' # Error reading file. #'
    print ' #######################'
    print ''
    sys.exit ()
    
  print '### Finished reading save file. ###'
  
  if len(dir_names_lists['cultures']) == 0:
    print ''
    print ' ##################################################'
    print ' # Warning: no cultures files found.              #'
    print ' # Check ck2 install and mod directory locations. #'
    print ' ##################################################'
    print ''
  
  ## Opening culture files #############################################
  try:
    culture_map = {}
    for filename, base, location in dir_names_lists['cultures']:
      if location == '':
        print '### Now reading', filename, '###'
        debug_write('Parsing ' + filename)
        with open(filename) as file:
          culture_map = read_cultures_file(file, culture_map)
      else:
        print '### Now reading', filename, 'in', location, '###'
        debug_write('Parsing ' + filename + ' in ' + location)
        with zipfile.ZipFile(os.path.join(mod_dir, location)) as mod_file:
          file = mod_file.open(filename)
          culture_map = read_cultures_file(file, culture_map)
  except IOError:
    print ''
    print ' #######################'
    print ' # Error reading file. #'
    print ' #######################'
    print ''
    sys.exit ()
    
  if len(dir_names_lists['religions']) == 0:
    print ''
    print ' ##################################################'
    print ' # Warning: no religions files found.             #'
    print ' # Check ck2 install and mod directory locations. #'
    print ' ##################################################'
    print ''
  
  ## Opening religion files #############################################
  try:
    religion_map = {}
    for filename, base, location in dir_names_lists['religions']:
      if location == '':
        print '### Now reading', filename, '###'
        debug_write('Parsing ' + filename)
        with open(filename) as file:
          religion_map, misc_localization = read_religions_file(file, religion_map, misc_localization)
      else:
        print '### Now reading', filename, 'in', location, '###'
        debug_write('Parsing ' + filename + ' in ' + location)
        with zipfile.ZipFile(os.path.join(mod_dir, location)) as mod_file:
          file = mod_file.open(filename)
          religion_map, misc_localization = read_religions_file(file, religion_map, misc_localization)
  except IOError:
    print ''
    print ' #######################'
    print ' # Error reading file. #'
    print ' #######################'
    print ''
    sys.exit ()
    
  if len(dir_names_lists['landed_titles']) == 0:
    print ''
    print ' ##################################################'
    print ' # Warning: no landed titles files found.         #'
    print ' # Check ck2 install and mod directory locations. #'
    print ' ##################################################'
    print ''
  
  ## Opening landed titles files #############################################
  try:
    religious_head_titles = []
    for filename, base, location in dir_names_lists['landed_titles']:
      if location == '':
        print '### Now reading', filename, '###'
        debug_write('Parsing ' + filename)
        with open(filename) as file:
          title_map, misc_localization, religious_head_titles = \
            read_landed_titles_file(file, title_map, culture_map, misc_localization, religious_head_titles)
      else:
        print '### Now reading', filename, 'in', location, '###'
        debug_write('Parsing ' + filename + ' in ' + location)
        with zipfile.ZipFile(os.path.join(mod_dir, location)) as mod_file:
          file = mod_file.open(filename)
          title_map, misc_localization, religious_head_titles = \
            read_landed_titles_file(file, title_map, culture_map, misc_localization, religious_head_titles)
  except IOError:
    print ''
    print ' #######################'
    print ' # Error reading file. #'
    print ' #######################'
    print ''
    sys.exit ()
    
  # Make sure religious heads have the religious head title as primary
  for c in character_map:
    character_map[c].title_history.assign_religious_head_primary(religious_head_titles)
    
  if len(dir_names_lists['governments']) == 0:
    print ''
    print ' ##################################################'
    print ' # Warning: no governments files found.           #'
    print ' # Check ck2 install and mod directory locations. #'
    print ' ##################################################'
    print ''
  
  ## Opening governments files #############################################
  try:
    government_map = {}
    for filename, base, location in dir_names_lists['governments']:
      if location == '':
        print '### Now reading', filename, '###'
        debug_write('Parsing ' + filename)
        with open(filename) as file:
          government_map = read_governments_file(file, government_map)
      else:
        print '### Now reading', filename, 'in', location, '###'
        debug_write('Parsing ' + filename + ' in ' + location)
        with zipfile.ZipFile(os.path.join(mod_dir, location)) as mod_file:
          file = mod_file.open(filename)
          government_map = read_governments_file(file, government_map)
  except IOError:
    print ''
    print ' #######################'
    print ' # Error reading file. #'
    print ' #######################'
    print ''
    sys.exit ()
    
  if len(localization_files) == 0:
    print ''
    print ' ##################################################'
    print ' # Warning: no localization files found.          #'
    print ' # Check ck2 install and mod directory locations. #'
    print ' ##################################################'
    print ''
  
  ## Opening governments files #############################################
  try:
    gov_types = [government_map[x] for x in government_map]
    misc_localization_map = {}
    rank_names = {}
    cultures = [c for c in culture_map] + [culture_map[c].group for c in culture_map]
    religions = [r for r in religion_map] + [religion_map[r].group for r in religion_map]
    for l in misc_localization:
      misc_localization_map[l] = ''
    for filename, base, location in localization_files:
      if location == '':
        print '### Now reading', filename, '###'
        with open(filename) as file:
          title_map, rank_names, misc_localization_map = \
            read_localization_file(file, title_map, rank_names, misc_localization_map,
                                   cultures, religions, gov_types)
      else:
        print '### Now reading', filename, 'in', location, '###'
        debug_write('Parsing ' + filename + ' in ' + location)
        with zipfile.ZipFile(os.path.join(mod_dir, location)) as mod_file:
          file = mod_file.open(filename)
          title_map, rank_names, misc_localization_map = \
            read_localization_file(file, title_map, rank_names, misc_localization_map,
                                   cultures, religions, gov_types)
  except IOError:
    print ''
    print ' #######################'
    print ' # Error reading file. #'
    print ' #######################'
    print ''
    sys.exit ()
    
  # Assign remaining localization strings.
  for t in title_map:
    rank_name = title_map[t].rank_name
    if rank_name[0] != '' and rank_name[0] in misc_localization_map and misc_localization_map[rank_name[0]] != '':
      rank_name[0] = misc_localization_map[rank_name[0]]
    if rank_name[1] != '' and rank_name[1] in misc_localization_map and misc_localization_map[rank_name[1]] != '':
      rank_name[1] = misc_localization_map[rank_name[1]]
      
  for r in religion_map:
    if religion_map[r].priest_title != '' and misc_localization_map[religion_map[r].priest_title] != '':
      religion_map[r].priest_title = misc_localization_map[religion_map[r].priest_title]
      
  # Transfer information to title histories
  for c in character_map:
    if character_map[c].nickname != '' and misc_localization_map[character_map[c].nickname] != '':
      character_map[c].nickname = misc_localization_map[character_map[c].nickname]
    character_map[c].inform_title_history(culture_map, religion_map, government_map)
  
  ## Processing the Save File ##########################################
  print '### Now processing data. ###'
  while True:
    print '\nPossible modes:'
    print '1) Entire tree (warning: probably very large)'
    print '2) Your dynasty members, their spouses, their parents, and all of their descendents'
    print '3) Your dynasty members, their spouses, their parents, and their children (ala in-game dynasty tree)'
    print '4) Your dynasty members, and their spouses and parents (for very large dynasties)'
    print "Enter a number: ",
    mode = sys.stdin.readline ().strip()
    try:
      mode = int(mode)
      break
    except ValueError:
      print 'Please enter a number.'
      
  if mode == 1:
    print 'Ok. Generating entire tree.\n'
  elif mode == 2:
    print 'Ok. Generating extended dynasty tree.\n'
  elif mode == 3:
    print 'Ok. Generating standard dynasty tree.\n'
  else:
    print 'Ok. Generating abbreviated dynasty tree.\n'
    
  if mode != 1 and player_id != 0:
    player_dynasty = character_map[player_id].dynasty_id
  elif mode != 1:
    print 'Your game appears to have been saved in observer mode.',
    print 'Please reload it and select a character in order to use mode 2, 3, or 4.'
    sys.exit ()
  else:
    player_dynasty = 0
    
  character_map = mark_characters(character_map, player_dynasty, mode)

  #Create families.
  character_map, family_map, GEDCOM_map = generate_gedcom_families(character_map)

  ## Creating the .ged File ############################################
  print '### Finished processing data. Now creating .ged file. ###'
  write_gedcom(savefilename, GEDCOM_map, character_map, family_map, rank_names, title_map)

  ## Creating .csv Files ###############################################
  if create_csv:
    write_csv(savefilename, dynasty_map, character_map, family_map)

  print 'Processed',str(len(dynasty_map)),'dynasties.'
  print 'Processed',str(len(character_map)),'characters.'
  print 'Processed',str(len(family_map)),'families.'
  print 'Processed', len(title_map), 'titles.'

if __name__ == '__main__':
  if debug_parse:
    debug_out = open ("debug.log", "w")
    
  main()
  
  if debug_parse:
    debug_out.close()
  
"""
Authored by Leyic
2012.02.18: Support for childless spouses. Fix for parentless parents.
            Implemented .csv output for dynasties, characters, and families.
2012.02.17: Clean up and organization.
            Implemented 'state_change' function.
            Reports number of dynasties, characters, and families processed.
2012.02.16: Finished processing and GEDCOM sections. Initial release.
2012.02.15: Initial version. Finished file reading sections. Started processing section.
            Based on sengoku2gedcom.py (2011.09.21-2011.09.26)
"""
