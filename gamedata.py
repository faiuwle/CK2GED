import sys
import zipfile
import os.path
from os import listdir
from string import digits, whitespace
from collections import defaultdict
from itertools import groupby

# Title ranks
NONE = 7
VICEKING = 6
VICEDUKE = 5
BARON = 4
COUNT = 3
DUKE = 2
KING = 1
EMPEROR = 0

class InstallDirNotFoundError(Exception):
    pass

class Date(object):
    gedcom_month_name = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP',
                         'OCT', 'NOV','DEC']
    full_month_name = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November',
                       'December']

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
        if self.day < 1:
            self.day = 1

    def is_null(self):
        return (self.year < 1 or self.month < 1 or self.month > 12
                or self.day < 1)

    def __lt__(self, other):
        if self.year != other.year:
            return self.year < other.year
        if self.month != other.month:
            return self.month < other.month
        return self.day < other.day

    def __le__(self, other):
        if self.year != other.year:
            return self.year < other.year
        if self.month != other.month:
            return self.month < other.month
        return self.day <= other.day

    def __eq__(self, other):
        return (self.year == other.year and self.month == other.month
                and self.day == other.day)

    def __ne__(self, other):
        return (self.year != other.year or self.month != other.month
                or self.day != other.day)

    def __gt__(self, other):
        if self.year != other.year:
            return self.year > other.year
        if self.month != other.month:
            return self.month > other.month
        return self.day > other.day

    def __ge__(self, other):
        if self.year != other.year:
            return self.year > other.year
        if self.month != other.month:
            return self.month > other.month
        return self.day >= other.day

    def __str__(self):
        if self.is_null():
            return ('Invalid date: ' + str(self.year) + '.' + str(self.month)
                    + '.' + str(self.day))
        return (Date.full_month_name[self.month-1] + ' ' + str(self.day) + ' '
                + str(self.year))

    def gedcom_string(self):
        if self.is_null():
            return ''

        s = str(self.day) + ' ' + Date.gedcom_month_name[self.month-1] + ' '

        if self.year < 1000:
            return s + '0' + str(self.year)
        else:
            return s + str(self.year)

class Range(object):
    def __init__(self, first, second):
        self.start = first
        self.end = second

    def __str__(self):
        return '(' + str(self.start) + ' - ' + str(self.end) + ')'

    def __lt__(self, other):
        return self.start < other.start

    def __le__(self, other):
        return self.start <= other.start

    def __eq__(self, other):
        return self.start == other.start

    def __ne__(self, other):
        return self.start != other.start

    def __gt__(self, other):
        return self.start > other.start

    def __ge__(self, other):
        return self.start >= other.start

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
        self.dynasty_name_first = False

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
        self.rank_name = [None, None]
        self.viceroyalty = False
        self.independent = True
        self.religious_head = False
        self.holders = []

    def __lt__(self, other):
        return self.rank < other.rank

    def __le__(self, other):
        return self.rank <= other.rank

    def __eq__(self, other):
        return self.rank == other.rank

    def __ne__(self, other):
        return self.rank != other.rank

    def __gt__(self, other):
        return self.rank > other.rank

    def __ge__(self, other):
        return self.rank >= other.rank

    def assign_regnal_numbers(self, character_map, name_map):
        name_counts = {}
        first_of_name = {}

        for h in self.holders:
            character = character_map[h]
            name = character.regnal_name

            if name in name_map:
                name = name_map[name]

            if (self.id in character.title_history.regnal_numbers
                or (name in first_of_name and first_of_name[name] == h)):
                continue

            if name in name_counts:
                name_counts[name] += 1

            else:
                name_counts[name] = 1

            if name_counts[name] > 1:
                regnal_numbers = character.title_history.regnal_numbers
                regnal_numbers[self.id] = name_counts[name]
                c = character_map[first_of_name[name]]
                c.title_history.regnal_numbers[self.id] = 1

            else:
                first_of_name[name] = h

    def get_full_name(self):
        if self.rank == COUNT:
            text = 'County of '
        elif self.rank == DUKE:
            text = 'Duchy of '
        elif self.rank == KING:
            text = 'Kingdom of '
        elif self.rank == EMPEROR:
            text = 'Empire of '
        else:
            text = ''

        return text + self.name

class TitleOwnership(object):
    def __init__(self, date_range):
        self.held_range = date_range
        self.gain_type = ''
        self.from_whom = 0
        self.lose_type = ''
        self.to_whom = 0
        self.current_owner = False
        self.exclude_from_history = False

class TitleHistory(object):
    rank_names = {}  # static member populated by GameData

    arabic = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    roman = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV',
             'I']

    gain_text = {'claim': 'conquered {0} as a claimant, taking {2} from {1}',
                 'host': 'conquered {0} as an adventurer, taking {2} from {1}',
                 'revolt': 'conquered {0} as a leader of a decadence revolt,'
                           ' taking {2} from {1}',
                 'usurp': 'peacefully usurped {0} from {1}',
                 'faction_demand': 'was installed as the ruler of {0} by'
                                   ' faction demand, taking {2} from {1}',
                 'inheritance': 'inherited {0} from {1}',
                 'invasion': 'conquered {0} in war, taking {2} from {1}',
                 'created': 'created {0}',
                 'election': 'was elected ruler of {0} after the death of {1}',
                 'revoke': 'revoked {0} from {1}',
                 'grant': 'was granted {0} by {1}',
                 'holy_war': 'conquered {0} in a holy war, taking {2} from {1}',
                 '': 'gained {0} from {1} in an unknown manner'}

    lose_text = {'claim': 'lost {0} to a {1}, a claimant',
                 'host': 'lost {0} to {1}, an adventurer',
                 'revolt': 'lost {0} to a decadence revolt lead by {1}',
                 'usurp': 'had {0} peacefully usurped by {1}',
                 'faction_demand': 'lost {0} when a faction installed {1}',
                 'inheritance': 'passed {0} on to {1}, the rightful heir',
                 'invasion': 'lost {0} to {1} in a war',
                 'created': 'error displaying loss of {0} to {1}',
                 'election': 'passed {0} on to {1}, the rightfully elected'
                             ' heir',
                 'revoke': 'had {0} revoked by {1}',
                 'grant': 'granted {0} to {1}',
                 'holy_war': 'lost {0} to {1} in a holy war',
                 '': 'destroyed {0} or lost {2} in an unknown way'}

    def __init__(self):
        self.titles = {}
        self.regnal_numbers = {}
        self.primary = ''
        self.primary_set = False
        self.highest_rank = NONE
        self.culture = Culture()
        self.religion = Religion()
        self.government = ''

    def add_title(self, title, ownership, primary_eligible):
        if title.id in self.titles:
            self.titles[title.id].append(ownership)
        else:
            self.titles[title.id] = [ownership]
        if (not self.primary_set and primary_eligible
            and title.rank < self.highest_rank):
            self.highest_rank = title.rank
            self.primary = title.id

    def assign_religious_head_primary(self):
        for t in self.titles:
            if t.religious_head:
                self.primary = t
                break

    @classmethod
    def int_to_roman(cls, number):
        result = ''

        for i in range(len(cls.arabic)):
            count = int(number / cls.arabic[i])
            result += cls.roman[i] * count
            number -= cls.arabic[i] * count

        return result

    def get_primary(self, title_map):
        if self.primary == '':
            return ''

        if self.primary in title_map:
            p = title_map[self.primary]

            if self.primary not in self.regnal_numbers:
                number = 0
            else:
                number = self.regnal_numbers[self.primary]

            if number > 0:
                number = self.int_to_roman(number)

            rank = p.rank

            if (rank == DUKE and self.independent
                and self.culture.dukes_called_kings):
                rank = KING

            if p.viceroyalty:
                if rank == DUKE:
                    rank = VICEDUKE
                if rank == KING:
                    rank = VICEKING

            if p.rank_name[self.gender] is None:
                s = self.get_rank(rank) + ' ' + self.name
            else:
                s = p.rank_name[self.gender] + ' ' + self.name

            if type(number) != int:
                s += ' ' + number

            if self.nickname != '':
                s += ' ' + self.nickname

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
            elif (self.primary.startswith('d_') and self.independent
                  and self.culture.dukes_called_kings):
                rank = KING
            elif self.primary.startswith('d_'):
                rank = DUKE
            elif self.primary.startswith('k_'):
                rank = KING
            elif self.primary.startswith('e_'):
                rank = EMPEROR
            else:
                rank = NONE

            s = self.get_rank(rank) + ' ' + name

            if self.nickname != '':
                s += ' ' + self.nickname

            return s + ' of ' + self.primary

    def get_years_of_rule(self, title_map):
        if len(self.titles) == 0:
            return []
        strings = []
        title_list = []

        for t in self.titles:
            title_list.append(title_map[t])
        title_list.sort()

        year_range = [[], [], [], [], [], []]

        for t in title_list:
            history = self.titles[t.id]

            for ownership in history:
                r = ownership.held_range

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

                if (rank == DUKE and self.independent
                    and self.culture.dukes_called_kings):
                    rank = KING

                if t.viceroyalty:
                    if rank == DUKE:
                        rank = VICEDUKE
                    if rank == KING:
                        rank = VICEKING

                if t.rank_name[self.gender] is None:
                    s = self.get_rank(rank) + ' of '

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

    def get_rank(self, rank):
        if rank >= NONE:
            return ''

        male_rank_names = []
        female_rank_names = []

        government = self.government
        gender = self.gender

        if government == 'temple':
            culture_religion = self.religion
        else:
            culture_religion = self.culture

        if government in TitleHistory.rank_names:
            r = TitleHistory.rank_names[government][rank]

            if culture_religion.id in r:
                male_rank_names.append(r[culture_religion.id][1])
                female_rank_names.append(r[culture_religion.id][0])

            if culture_religion.group in r:
                male_rank_names.append(r[culture_religion.group][1])
                female_rank_names.append(r[culture_religion.group][0])

            if '' in r:
                male_rank_names.append(r[''][1])
                female_rank_names.append(r[''][0])

            if government == 'temple':
                male_rank_names.append(culture_religion.priest_title)
                female_rank_names.append(culture_religion.priest_title)

        if '' in TitleHistory.rank_names and government != '':
            r = TitleHistory.rank_names[''][rank]

            if culture_religion.id in r:
                male_rank_names.append(r[culture_religion.id][1])
                female_rank_names.append(r[culture_religion.id][0])

            if culture_religion.group in r:
                male_rank_names.append(r[culture_religion.group][1])
                female_rank_names.append(r[culture_religion.group][0])

            if '' in r:
                male_rank_names.append(r[''][1])
                female_rank_names.append(r[''][0])

        if gender == 1:
            best_rank_names = male_rank_names + female_rank_names
        else:
            best_rank_names = female_rank_names + male_rank_names

        for rn in best_rank_names:
            if rn is not None and rn != '':
                return rn

        if gender == 1:
            return 'Count'
        else:
            return 'Countess'

    @classmethod
    def format_lose_gain_text(cls, gain, succ_type, other, titles):
        if other.culture is not None and other.culture.dynasty_name_first:
            other_text = other.dynasty_name + ' ' + other.birth_name
        else:
            other_text = other.birth_name + ' ' + other.dynasty_name
        other_text += ' (' + str(other.id) + ')'

        title_text = ''
        titles.sort()
        for i, title in enumerate(titles):
            title_text += title.get_full_name()
            if i == (len(titles) - 2):
                title_text += ' and '
            elif i < (len(titles) - 2):
                title_text += ', '

        it_them = 'it' if len(titles) == 1 else 'them'

        if succ_type not in TitleHistory.gain_text:
            succ_type = ''

        if gain:
            return cls.gain_text[succ_type].format(
                title_text, other_text, it_them
            )
        else:
            return cls.lose_text[succ_type].format(
                title_text, other_text, it_them
            )

    def generate_title_history(self, character_map, title_map):
        tuple_map = defaultdict(list)
        for title in self.titles:
            for ownership in self.titles[title]:
                if ownership.exclude_from_history:
                    continue

                gain_date = ownership.held_range.start
                lose_date = ownership.held_range.end
                gain_key = (gain_date.year, gain_date.month, gain_date.day)
                lose_key = (lose_date.year, lose_date.month, lose_date.day)

                tuple_map[gain_key].append(
                    (True, ownership.from_whom, ownership.gain_type, title)
                )
                if not ownership.current_owner:
                    tuple_map[lose_key].append(
                        (False, ownership.to_whom, ownership.lose_type, title)
                    )

        string_map = defaultdict(list)
        for (y, m, d) in tuple_map:
            event_list = tuple_map[(y, m, d)]
            event_list = sorted(event_list, key=lambda x: (x[0], x[1], x[2]))
            for k, g in groupby(event_list, lambda x: (x[0], x[1], x[2])):
                titles = [title_map[x[3]] for x in g]
                if k[1] in character_map:
                    other = character_map[k[1]]
                else:
                    other = Character()
                text = self.format_lose_gain_text(k[0], k[2], other, titles)
                string_map[(y, m, d)].append(text)

        string_list = string_map.items()
        string_list = sorted(string_list, key=lambda x: x[0])
        final_list = []
        for date_parts, text_list in string_list:
            date = Date()
            date.set_date(date_parts)
            for text in text_list:
                lines = []
                whole = 'On ' + str(date) + ', ' + self.name + ' ' + text
                while len(whole) > 76:
                    next_split = whole.rfind(' ', 0, 76)
                    lines.append('    ' + whole[0:next_split+1])
                    whole = whole[next_split+1:]
                lines.append('    ' + whole)
                lines[0] = lines[0][4:]
                final_list += lines

        return final_list

class Character(object):
    """Stores information relevant to a character."""
    def __init__(self):
        self.id = -1 #Game ID
        self.birth_name = ''
        self.regnal_name = ''
        self.nickname = ''
        self.gender = 1
        self.birthday = []
        self.deathday = []
        self.culture = None
        self.religion = None
        self.father = -1
        self.real_father = -1
        self.mother = -1
        self.spouse = []
        self.children = []
        self.dynasty_id = -1
        self.dynasty_name = ''
        self.title_history = TitleHistory()
        self.government = ''
        self.independent = True
        self.loner = True
        self.GEDCOM_id = -1
        self.FAMS = []
        self.FAMC = -1
        self.mark = False
        self.family_marked = False

    def inform_title_history(self):
        if self.culture is not None:
            self.title_history.culture = self.culture

        if self.religion is not None:
            self.title_history.religion = self.religion

        self.title_history.government = self.government
        self.title_history.gender = self.gender
        self.title_history.independent = self.independent

        if (self.culture is not None and self.culture.dynasty_name_first
            and self.dynasty_name != '' 
            and self.dynasty_name != self.regnal_name):
            self.title_history.name = (self.dynasty_name + ' ' + 
                                       self.regnal_name)
        else:
            self.title_history.name = self.regnal_name

        self.title_history.nickname = self.nickname

    def get_primary_title(self, title_map):
        return self.title_history.get_primary(title_map)

    def get_years_of_rule(self, title_map):
        return self.title_history.get_years_of_rule(title_map)

    def get_title_history(self, character_map, title_map):
        return self.title_history.generate_title_history(
            character_map, title_map
        )


class GameFiles(object):
    def __init__(self):
        self.dir_lists = {'dynasties': [], 'landed_titles': [], 'cultures': [],
                          'religions': [], 'governments': []}
        self.localization = []

    def initialize(self, ck2_install_dir, mod_dir):
        if not os.path.exists(ck2_install_dir):
            raise InstallDirNotFoundError

        if not os.path.exists(mod_dir):
            print('Did not find mod directory.  No mods will be loaded.')

        self.get_mod_files(mod_dir)
        self.get_game_files(ck2_install_dir)

        self.dynasties = [(x[0], x[2]) for x in self.dir_lists['dynasties']]
        self.landed_titles = [(x[0], x[2]) 
                              for x in self.dir_lists['landed_titles']]
        self.cultures = [(x[0], x[2]) for x in self.dir_lists['cultures']]
        self.religions = [(x[0], x[2]) for x in self.dir_lists['religions']]
        self.governments = [(x[0], x[2]) for x in self.dir_lists['governments']]
        self.localization = [(x[0], x[2]) for x in self.localization]

        self.dir_lists = {}

    def get_mod_files(self, mod_dir):
        mods = []

        if not os.path.exists(mod_dir):
            return mods

        while True:
            mod_names = [d for d in listdir(mod_dir)
                         if (os.path.isdir(os.path.join(mod_dir, d))
                             or d.endswith('.zip'))]

            print('Please specify which mods you used with this save, by'
                  ' number. You can enter multiple numbers separated by'
                  ' spaces.')

            for i, m in enumerate(mod_names):
                print(i + 1, m)
            print('Mods in use (press enter for no mods): ', end=' ')

            try:
                mod_numbers = sys.stdin.readline().strip().split()
                mod_numbers = [int(x) for x in mod_numbers]
            except ValueError:
                print('Please enter only numbers and spaces.')
                continue

            try:
                mods = [mod_names[i-1] for i in mod_numbers]
                break
            except KeyError:
                print('Please only type numbers that appear on this list.')

        mods = sorted(mods, key=lambda x: x, reverse=True)

        print('')

        for m in mods:
            is_dir = os.path.isdir(os.path.join(mod_dir, m))

            if is_dir:
                common_path = os.path.join(mod_dir, m, 'common')
                localization_path = os.path.join(mod_dir, m, 'localisation')

            else:
                common_path = 'common'
                localization_path = 'localisation'

            for dir_name in self.dir_lists:
                path = os.path.join(common_path, dir_name)
                path = path.replace('\\', '/')
                dir_list = self.dir_lists[dir_name]
                files = []

                if is_dir and os.path.exists(path):
                    files = [os.path.join(path, f) for f in listdir(path)]
                    files = list(filter(os.path.isfile, files))
                    files = [(f, os.path.basename(f), '') for f in files]

                elif not is_dir:
                    with zipfile.ZipFile(os.path.join(mod_dir, m)) as mod_file:
                        files = [f for f in mod_file.namelist()
                                 if path in f and f.endswith('.txt')]
                        files = [(f, os.path.basename(f), 
                                  os.path.join(mod_dir, m)) for f in files]

                files = [f for f in files 
                         if f[1] not in [x[1] for x in dir_list]]
                dir_list.extend(files)

            if is_dir and os.path.exists(localization_path):
                files = [os.path.join(localization_path, f)
                         for f in listdir(localization_path)]
                files = list(filter(os.path.isfile, files))
                files = [(f, os.path.basename(f), '') for f in files]

            elif not is_dir:
                with zipfile.ZipFile(os.path.join(mod_dir, m)) as mod_file:
                    files = [f for f in mod_file.namelist()
                             if localization_path in f and f.endswith('.csv')]
                    files = [(f, os.path.basename(f), os.path.join(mod_dir, m))
                             for f in files]

            files = [f for f in files 
                     if f[1] not in [x[1] for x in self.localization]]
            self.localization += files

    def get_game_files(self, ck2_install_dir):
        common_path = os.path.join(ck2_install_dir, 'common')
        localization_path = os.path.join(ck2_install_dir, 'localisation')

        for dir_name in self.dir_lists:
            path = os.path.join(common_path, dir_name)
            dir_list = self.dir_lists[dir_name]

            if os.path.exists(path):
                files = [os.path.join(path, f) for f in listdir(path)]
                files = list(filter(os.path.isfile, files))
                files = [(f, os.path.basename(f), '') for f in files]
                files = [f for f in files 
                         if f[1] not in [x[1] for x in dir_list]]
                dir_list.extend(files)

        if os.path.exists(localization_path):
            files = [os.path.join(localization_path, f)
                     for f in listdir(localization_path)]
            files = list(filter(os.path.isfile, files))
            files = [(f, os.path.basename(f), '') for f in files]
            files = [f for f in files 
                     if f[1] not in [x[1] for x in self.localization]]
            self.localization += files

class GameData(object):
    special_chars = ['{', '}', '=', '"', '#']

    def __init__(self):
        self.debug_all = False
        self.debug_save = False
        self.debug_dynasties = False
        self.debug_landed_titles = False
        self.debug_cultures = False
        self.debug_religions = False
        self.debug_governments = False

        self.game_files = GameFiles()

        if os.path.exists('parse.log'):
            os.remove('parse.log')

    def initialize(self, ck2_install_dir, mod_dir):
        self.game_files.initialize(ck2_install_dir, mod_dir)

        self.read_dynasties()
        self.read_cultures()
        self.read_religions()
        self.read_landed_titles()
        self.read_governments()
        self.read_localization()

    @staticmethod
    def parse_date(date_string):
        parts = date_string.split('.')
        if len(parts) != 3:
            return []
        try:
            int_parts = list(map(int, parts))
        except ValueError:
            return []
        date = Date()
        date.set_date(int_parts)
        return date

    @staticmethod
    def is_integer(string):
        for c in string:
            if c not in digits:
                return False

        return True

    @staticmethod
    def guess_title_name(title_id):
        parts = title_id.split('_')

        for i, p in enumerate(parts):
            parts[i] = p[0].upper() + p[1:]

        return ' '.join(parts[1:])

    @classmethod
    def parse_ck2_data(cls, data, debug=False, is_save=False, 
                       empty_values=False):
        current_keys = []
        current_value = ''
        current_line = 1

        if is_save:
            state = 'begin'
        else:
            state = 'expect_key'

        saved_state = ''
        temp_string = ''

        chars_per_increment = int(len(data) / 80) + 1
        chars_until_progress = chars_per_increment

        if debug:
            debug_file = open('parse.log', 'a')

        for x in data:
            chars_until_progress -= 1
            if chars_until_progress == 0:
                print('=', end='')
                sys.stdout.flush()
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
                elif x in cls.special_chars and debug:
                    debug_file.write('Unexpected character ' + x + ' on line '
                                     + repr(current_line) + ' (expect_key)')
                elif x not in whitespace:
                    temp_string = x
                    state = 'key'

            elif state == 'key':
                if x == '=':
                    current_keys.append(temp_string)
                    temp_string = ''
                    state = 'expect_value'
                elif x == '}':      # e.g. societies={2}
                    current_value = [temp_string]
                    yield (current_keys, current_value)
                    temp_string = ''
                    current_value = ''
                    if len(current_keys) > 0:
                        current_keys = current_keys[:-1]
                    state = 'expect_key'
                elif x in cls.special_chars and debug:
                    debug_file.write('Unexpected character in key: ' + x + 
                                     ' on line ' + repr(current_line) + 
                                     ' (key)')
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
                elif x in cls.special_chars and debug:
                    debug_file.write('Unexpected character ' + x + ' on line '
                                     + repr(current_line) + ' (expect_value)')
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
                elif x in cls.special_chars and debug:
                    debug_file.write('Unexpected character ' + x + ' on line '
                                     + current_line + ' (value)')
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
                elif x == '=' and len(current_value) == 1:  
                    # oops it's actually a key
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
                elif x in cls.special_chars and debug:
                    debug_file.write('Unexpected character ' + x + ' on line '
                                     + repr(current_line) + ' (list)')
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
                elif x in cls.special_chars and debug:
                    debug_file.write('Unexpected character ' + x + ' on line '
                                     + repr(current_line) + ' (list_item)')
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

        print('')

        if debug:
            debug_file.close()

    @staticmethod
    def read_file(filename, location, debug):
        if location == '':
            print('### Now reading', filename, '###')

            try:
                with open(filename, encoding='cp1252', errors='replace')  \
                        as file:
                    file_contents = file.read()
            except IOError:
                print('')
                print(' #######################')
                print(' # Error reading file. #')
                print(' #######################')
                return ''

            if debug:
                debug_file = open('parse.log', 'a')
                debug_file.write('Parsing ' + filename)
                debug_file.close()

        else:
            print('### Now reading', filename, 'in', location, '###')

            try:
                with zipfile.ZipFile(location) as mod_file:
                    file = mod_file.open(filename)
                    file_contents = file.read().decode(encoding='cp1252',
                                                       errors='replace')
            except IOError:
                print('')
                print(' #######################')
                print(' # Error reading file. #')
                print(' #######################')
                return ''

            if debug:
                debug_file = open('parse.log', 'a')
                debug_file.write('Parsing ' + filename + ' in ' + location)
                debug_file.close()

        return file_contents

    def read_dynasties(self):
        if len(self.game_files.dynasties) == 0:
            print('')
            print(' ##########################################')
            print(' # Warning: no dynasties files found.     #')
            print(' # Check CK2 install and mod directories. #')
            print(' ##########################################')

        self.dynasty_map = {}
        debug = self.debug_all or self.debug_dynasties

        for filename, location in self.game_files.dynasties:
            file_contents = self.read_file(filename, location, debug)

            for keys, value in self.parse_ck2_data(file_contents, debug):
                if len(keys) >= 2 and self.is_integer(keys[0]):
                    id = int(keys[0])

                    if id not in self.dynasty_map:
                        dynasty = Dynasty()
                        dynasty.id = id
                        self.dynasty_map[id] = dynasty

                    dynasty = self.dynasty_map[id]

                    if keys[1] == 'name':
                        dynasty.name = value
                    elif keys[1] == 'culture':
                        dynasty.culture = value
                    elif keys[1] == 'religion' and dynasty.religion == '':
                        dynasty.religion = value
                    elif (len(keys) == 3 and keys[1] == 'coat_of_arms' and
                          keys[2] == 'religion'):
                        dynasty.religion = value

    def read_cultures(self):
        if len(self.game_files.cultures) == 0:
            print('')
            print(' ##########################################')
            print(' # Warning: no cultures files found.      #')
            print(' # Check CK2 install and mod directories. #')
            print(' ##########################################')

        self.culture_map = {}
        self.name_map = {}
        debug = self.debug_all or self.debug_cultures

        for filename, location in self.game_files.cultures:
            file_contents = self.read_file(filename, location, debug)

            for keys, value in self.parse_ck2_data(file_contents, debug):
                if len(keys) == 3 and keys[1] not in self.culture_map:
                    culture = Culture()
                    culture.id = keys[1]
                    culture.group = keys[0]
                    self.culture_map[keys[1]] = culture

                if (len(keys) == 3 and keys[2] == 'dukes_called_kings'
                    and value == 'yes'):
                    self.culture_map[keys[1]].dukes_called_kings = True

                if (len(keys) == 3 and keys[2] == 'dynasty_name_first'
                    and value == 'yes'):
                    self.culture_map[keys[1]].dynasty_name_first = True

                if len(keys) == 3 and keys[2] in ['male_names', 'female_names']:
                    for name in value:
                        parts = name.split('_')
                        if len(parts) < 2:
                            continue

                        self.name_map[parts[0]] = parts[1]

    def read_religions(self):
        if len(self.game_files.religions) == 0:
            print('')
            print(' ##########################################')
            print(' # Warning: no religions files found.     #')
            print(' # Check CK2 install and mod directories. #')
            print(' ##########################################')

        self.religion_map = {}
        self.misc_localization = {}
        debug = self.debug_all or self.debug_religions

        for filename, location in self.game_files.religions:
            file_contents = self.read_file(filename, location, debug)

            for keys, value in self.parse_ck2_data(file_contents, debug):
                if len(keys) == 3 and keys[1] not in self.religion_map:
                    religion = Religion()
                    religion.id = keys[1]
                    religion.group = keys[0]
                    self.religion_map[keys[1]] = religion

                if len(keys) == 3 and keys[2] == 'priest_title':
                    self.religion_map[keys[1]].priest_title = value
                    self.misc_localization[value] = ''

    def read_landed_titles(self):
        if len(self.game_files.landed_titles) == 0:
            print('')
            print(' ##########################################')
            print(' # Warning: no landed_titles files found. #')
            print(' # Check CK2 install and mod directories. #')
            print(' ##########################################')

        self.title_map = {}
        debug = self.debug_all or self.debug_landed_titles

        for filename, location in self.game_files.landed_titles:
            file_contents = self.read_file(filename, location, debug)

            for keys, value in self.parse_ck2_data(file_contents, debug,
                                                   empty_values=True):
                if len(keys) > 1 and keys[-2] not in self.title_map:
                    title = Title()
                    title.id = keys[-2]
                    title.name = self.guess_title_name(keys[-2])

                    rank = NONE
                    if keys[-2].startswith('e_'):
                        rank = EMPEROR
                    if keys[-2].startswith('k_'):
                        rank = KING
                    if keys[-2].startswith('d_'):
                        rank = DUKE
                    if keys[-2].startswith('c_'):
                        rank = COUNT
                    if keys[-2].startswith('b_'):
                        rank = BARON

                    title.rank = rank
                    self.title_map[keys[-2]] = title

                if len(keys) > 1 and keys[-1] in self.culture_map:
                    self.title_map[keys[-2]].cultural_names[keys[-1]] = value

                if len(keys) > 1 and keys[-1] == 'title':
                    self.title_map[keys[-2]].rank_name[1] = value
                    self.misc_localization[value] = ''

                if len(keys) > 1 and keys[-1] == 'title_female':
                    self.title_map[keys[-2]].rank_name[0] = value
                    self.misc_localization[value] = ''

                if len(keys) > 1 and keys[-1] == 'controls_religion':
                    self.title_map[keys[-2]].religion_head = True

                if (value == '' and keys[-1].startswith('b_')  \
                    and keys[-1] not in self.title_map):
                    title = Title()
                    title.id = keys[-1]
                    title.name = self.guess_title_name(keys[-1])
                    title.rank = BARON
                    self.title_map[keys[-1]] = title

    def read_governments(self):
        if len(self.game_files.governments) == 0:
            print('')
            print(' ##########################################')
            print(' # Warning: no governments files found.   #')
            print(' # Check CK2 install and mod directories. #')
            print(' ##########################################')

        self.government_map = {}
        debug = self.debug_all or self.debug_governments

        for filename, location in self.game_files.governments:
            file_contents = self.read_file(filename, location, debug)

            for keys, value in self.parse_ck2_data(file_contents, debug):
                if len(keys) == 3 and keys[1] not in self.government_map:
                    self.government_map[keys[1]] = ''

                if len(keys) == 3 and keys[2] == 'title_prefix':
                    self.government_map[keys[1]] = value.strip('_')

    def read_localization(self):
        if len(self.game_files.localization) == 0:
            print('')
            print(' ##########################################')
            print(' # Warning: no localization files found.  #')
            print(' # Check CK2 install and mod directories. #')
            print(' ##########################################')

        gov_types = [self.government_map[x] for x in self.government_map]
        cultures = [c for c in self.culture_map]
        cultures += set([self.culture_map[c].group for c in self.culture_map])
        religions = [r for r in self.religion_map]
        religions +=  \
            set([self.religion_map[r].group for r in self.religion_map])
        base_rank = ['emperor', 'king', 'duke', 'count', 'baron']

        for filename, location in self.game_files.localization:
            try:
                if location == '':
                    print('### Now reading', filename, '###')
                    file = open(filename, encoding='cp1252', errors='replace')
                    lines = [line.strip() for line in file.readlines()]
                else:
                    print('### Now reading', filename, 'in', location, '###')
                    with zipfile.ZipFile(location) as mod_file:
                        file = mod_file.open(filename)
                        file_content = file.read().decode(encoding='cp1252',
                                                          errors='replace')
                        lines = [line.strip() for line in file_content]
            except IOError:
                print('')
                print(' #######################')
                print(' # Error reading file. #')
                print(' #######################')
                continue

            for line in lines:
                if line.startswith('#'):
                    continue

                parts = line.split(';')

                if len(parts) < 2:
                    continue

                key = parts[0]
                value = parts[1]

                if key in self.title_map:
                    self.title_map[key].name = value

                elif key in self.misc_localization:
                    self.misc_localization[key] = value

                elif key.startswith('nick_'):
                    self.misc_localization[key] = value

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

                    if ('vice' in key_parts and 'royalty' in key_parts
                        and (key_parts.index('vice') == 
                             key_parts.index('royalty') - 1)):
                        key_viceroyalty = True
                        key_parts_used.append(key_parts.index('vice'))
                        key_parts_used.append(key_parts.index('royalty'))

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

                    if key_gov_type not in TitleHistory.rank_names:
                        TitleHistory.rank_names[key_gov_type] = [
                            {}, {}, {}, {}, {}, {}, {}
                        ]

                    if key_viceroyalty:
                        if key_base_rank == DUKE:
                            key_base_rank = VICEDUKE
                        elif key_base_rank == KING:
                            key_base_rank = VICEKING
                        else:
                            continue

                    r = TitleHistory.rank_names[key_gov_type][key_base_rank]

                    if key_culture_religion not in r:
                        r[key_culture_religion] = ['', '']

                    r[key_culture_religion][key_gender] = value

        for t in self.title_map:
            rank_name = self.title_map[t].rank_name

            if (rank_name[0] is not None and rank_name[0] != ''
                and rank_name[0] in self.misc_localization
                and self.misc_localization[rank_name[0]] != ''):
                rank_name[0] = self.misc_localization[rank_name[0]]

            if (rank_name[1] is not None and rank_name[1] != ''
                and rank_name[1] in self.misc_localization
                and self.misc_localization[rank_name[1]] != ''):
                rank_name[1] = self.misc_localization[rank_name[1]]

        for r in self.religion_map:
            priest_title = self.religion_map[r].priest_title

            if (priest_title != ''
                and priest_title in self.misc_localization
                and self.misc_localization[priest_title] != ''):
                priest_title = self.misc_localization[priest_title]

    def read_save(self, filename, generate_titles):
        self.character_map = {}
        self.player_id = -1
        debug = self.debug_all or self.debug_save

        filename = os.path.basename(filename)

        try:
            file_contents = self.read_file(filename, filename, debug)
        except zipfile.BadZipfile:
            file_contents = self.read_file(filename, '', debug)

        date = []
        title_id = ''
        title_date = []
        title_holder = 0
        prev_holder = 0
        succession_type = ''

        for keys, value in self.parse_ck2_data(file_contents, debug, 
                                               is_save=True):
            if (len(keys) == 2 and keys[0] == 'player' and keys[1] == 'id'
                and self.is_integer(value)):
                self.player_id = int(value)

            if len(keys) == 1 and keys[0] == 'date':
                date = self.parse_date(value)

            if (len(keys) >= 3 and keys[0] == 'dynasties'
                and self.is_integer(keys[1])):
                id = int(keys[1])

                if id not in self.dynasty_map:
                    dynasty = Dynasty()
                    dynasty.id = id
                    self.dynasty_map[id] = dynasty

                dynasty = self.dynasty_map[id]

                if keys[2] == 'name':
                    dynasty.name = value
                elif keys[2] == 'culture':
                    dynasty.culture = value
                elif keys[2] == 'religion' and dynasty.religion == '':
                    dynasty.religion = value
                elif (len(keys) == 4 and keys[2] == 'coat_of_arms'
                      and keys[3] == 'religion'):
                    dynasty.religion = value

            if (len(keys) >= 3 and keys[0] == 'character'
                and self.is_integer(keys[1])):
                id = int(keys[1])

                if id not in self.character_map:
                    self.character_map[id] = Character()
                    self.character_map[id].id = id

                character = self.character_map[id]

                if keys[2] == 'bn':
                    character.birth_name = value
                    if character.regnal_name == '':
                        character.regnal_name = value
                elif keys[2] == 'name':
                    character.regnal_name = value

                elif keys[2] == 'nick':
                    if len(keys) == 3:
                        nickname = value
                    elif len(keys) == 4 and keys[3] == 'name':
                        nickname = value
                    elif (len(keys) == 4 and keys[3] == 'nickname'
                          and character.nickname == ''):
                        nickname = value
                    else:
                        continue
                    if nickname in self.misc_localization:
                        nickname = self.misc_localization[nickname]
                    character.nickname = nickname

                elif keys[2] == 'b_d':
                    character.birthday = self.parse_date(value)
                elif keys[2] == 'd_d':
                    character.deathday = self.parse_date(value)
                elif keys[2] == 'fem' and value == 'yes':
                    character.gender = 0
                elif keys[2] == 'cul':
                    if value in self.culture_map:
                        character.culture = self.culture_map[value]
                elif keys[2] == 'rel':
                    if value in self.religion_map:
                        character.religion = self.religion_map[value]
                elif keys[2] == 'fat' and self.is_integer(value):
                    character.father = int(value)
                elif keys[2] == 'rfat' and self.is_integer(value):
                    character.real_father = int(value)
                elif keys[2] == 'mot' and self.is_integer(value):
                    character.mother = int(value)
                elif keys[2] == 'spouse' and self.is_integer(value):
                    character.spouse.append(int(value))

                elif keys[2] == 'dnt' and self.is_integer(value):
                    character.dynasty_id = int(value)
                    character.dynasty_name = self.dynasty_map[int(value)].name
                    if character.culture is None:
                        culture = self.dynasty_map[int(value)].culture
                        if culture in self.culture_map:
                            character.culture = self.culture_map[culture]
                    if character.religion is None:
                        religion = self.dynasty_map[int(value)].religion
                        if religion in self.religion_map:
                            character.religion = self.religion_map[religion]

                elif keys[2] == 'gov':
                    if value in self.government_map:
                        value = self.government_map[value]
                    character.government = value
                elif keys[2] == 'lge':
                    character.independent = False
                elif (generate_titles and keys[2] == 'oh' and value != '---'
                      and '_dyn_reb_' not in value
                      and not character.title_history.primary_set):
                    character.title_history.primary = value
                    character.title_history.primary_set = True
                elif (generate_titles and len(keys) == 5 and keys[2] == 'dmn'
                      and keys[3] == 'primary' and keys[4] == 'title'
                      and value != '---' and '_dyn_reb_' not in value):
                    character.title_history.primary = value
                    character.title_history.primary_set = True

            if not generate_titles and keys[0] == 'delayed_event':
                break

            if len(keys) >= 2 and keys[0] == 'title':
                if '_dyn_reb_' in keys[1]:
                    continue

                if keys[1] not in self.title_map:
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
                    title = Title()
                    title.id = keys[1]
                    title.name = self.guess_title_name(keys[1])
                    title.rank = rank
                    self.title_map[keys[1]] = title

                if keys[2] == 'name' and self.title_map[keys[1]].name == '':
                    self.title_map[keys[1]].name = value

                if (len(keys) == 3 and keys[1].startswith('b_')
                    and not keys[1].startswith('b_dyn_') and keys[2] == 'holder'
                    and self.is_integer(value) 
                    and int(value) in self.character_map):
                    ownership = TitleOwnership(Range(Date(), Date()))
                    ownership.exclude_from_history = True
                    title_history = self.character_map[int(value)].title_history
                    title_history.add_title(self.title_map[keys[1]],
                                            ownership, True)

                if keys[2] == 'liege':
                    self.title_map[keys[1]].independent = False

                if keys[2] == 'vice_royalty' and value == 'yes':
                    self.title_map[keys[1]].viceroyalty = True

                if (keys[2] == 'holding_dynasty' and self.is_integer(value)
                    and int(value) in self.dynasty_map):
                    dynasty_name = self.dynasty_map[int(value)].name
                    self.title_map[keys[1]].name = 'House ' + dynasty_name

                if (len(keys) >= 5 and keys[2] == 'history' 
                    and keys[4] == 'holder'):
                    parsed_date = self.parse_date(keys[3])

                    # We're still on the same date as last iteration
                    if (keys[1] == title_id and type(parsed_date) == Date 
                        and type(title_date) == Date 
                        and parsed_date == title_date and len(keys) == 6):
                        if (keys[5] in ['character', 'who']
                            and self.is_integer(value)):
                            title_holder = int(value)
                        elif keys[5] == 'type':
                            succession_type = value
                        continue

                    # Past this point, we have come to a new date, so we need
                    # to store information collected for the last date
                    if title_id != '':
                        title = self.title_map[title_id]

                    # Set previous owner's TitleOwnership correctly
                    if title_id != '' and  prev_holder in self.character_map:
                        history = self.character_map[prev_holder].title_history
                        ownership = history.titles[title_id][-1]
                        ownership.lose_type = succession_type
                        ownership.to_whom = title_holder

                    # Not only a new date, but also a new title - finalize the
                    # last holder of the previous title
                    if (title_id != '' and title_id != keys[1]
                        and type(title_date) == Date
                        and title_holder in self.character_map):
                        character = self.character_map[title_holder]
                        ownership = TitleOwnership(Range(title_date, date))
                        ownership.gain_type = succession_type
                        ownership.from_whom = prev_holder
                        ownership.current_owner = True
                        character.title_history.add_title(title, ownership, 
                                                          True)
                        prev_holder = 0

                        if character.title_history.primary == title_id:
                            character.independent = title.independent

                        title.holders.append(title_holder)
                        title.assign_regnal_numbers(self.character_map, 
                                                    self.name_map)

                    # Otherwise, this is just the next date in the same title
                    elif (title_id != '' and type(parsed_date) == Date
                          and type(title_date) == Date
                          and title_holder in self.character_map):
                        character = self.character_map[title_holder]
                        r = Range(title_date, parsed_date)
                        ownership = TitleOwnership(r)
                        ownership.gain_type = succession_type
                        ownership.from_whom = prev_holder
                        character.title_history.add_title(title, ownership, 
                                                          False)
                        prev_holder = title_holder
                        title.holders.append(title_holder)

                    # Some checks to assign title names to patrician houses and
                    # non-de-jure nomad titles
                    # All b_dyn_ titles with histories are patrician houses
                    if (title_id.startswith('b_dyn_')
                        and title.rank_name[1] is None
                        and title_holder in self.character_map):
                        title.rank_name[1] = 'Patrician'

                    # k_dyn_ and e_dyn_ titles with nomadic holders are nomad
                    # clans and khaganates
                    if ((title_id.startswith('k_dyn_') 
                         or title_id.startswith('e_dyn'))
                        and title.name == '' 
                        and title_holder in self.character_map):
                        character = self.character_map[title_holder]

                        if character.government == 'nomadic':
                            dynasty_name = character.dynasty_name

                            if title_id.startswith('k_dyn_'):
                                title.name = dynasty_name + ' Clan'
                            else:
                                title.name = dynasty_name + ' Khaganate'

                    # Update information for next iteration
                    title_id = keys[1]
                    title_date = parsed_date
                    succession_type = ''

                    if len(keys) == 5 and self.is_integer(value):
                        title_holder = int(value)
                        if title_holder == 0:
                            prev_holder = 0
                    elif (len(keys) == 6 and keys[5] in ['character', 'who']
                          and self.is_integer(value)):
                        title_holder = int(value)
                        if title_holder == 0:
                            prev_holder = 0
                    elif len(keys) == 6 and keys[5] == 'type':
                        succession_type = value

        # Record information for the last title holder
        if title_id != '' and prev_holder in self.character_map:
            history = self.character_map[prev_holder].title_history
            ownership = history.titles[title_id][-1]
            ownership.lose_type = succession_type
            ownership.to_whom = title_holder

        if (title_id != '' and type(title_date) == Date
            and title_holder in self.character_map):
            character = self.character_map[title_holder]
            ownership = TitleOwnership(Range(title_date, date))
            ownership.gain_type = succession_type
            ownership.from_whom = prev_holder
            ownership.current_owner = True
            character.title_history.add_title(self.title_map[title_id], 
                                              ownership, True)

            if character.title_history.primary == title_id:
                character.independent = self.title_map[title_id].independent

            self.title_map[title_id].assign_regnal_numbers(self.character_map,
                                                           self.name_map)

        for c in self.character_map:
            self.character_map[c].inform_title_history()

    def mark_characters(self, real_fathers):
        while True:
            print('Possible modes:')
            print('1) Entire tree (warning: probably very large)')
            print('2) Your dynasty members, their spouses, their parents, and')
            print('   all of their descendants')
            print('3) Your dynasty members, their spouses, their parents, and')
            print('   their children')
            print('4) Your dynasty members, and their spouses and parents') 
            print('   (for very large dynasties)')
            print('Enter a number: ', end=' ')
            mode = sys.stdin.readline().strip()
            try:
                mode = int(mode)
                if 1 <= mode <= 4:
                    break
            except ValueError:
                print('Please enter a number.')

        if mode == 1:
            print('Ok. Generating entire tree.\n')
        elif mode == 2:
            print('Ok. Generating extended dynasty tree.\n')
        elif mode == 3:
            print('Ok. Generating standard dynasty tree.\n')
        else:
            print('Ok. Generating abbreviated dynasty tree.\n')

        if self.player_id not in self.character_map and mode != 1:
            print('Your game appears to have been saved in observer mode.'
                  ' Please reload it and select a character in order to use'
                  '  mode 2, 3, or 4.')
            return False

        elif self.player_id in self.character_map:
            player_dynasty = self.character_map[self.player_id].dynasty_id

        if mode == 1:
            for c in self.character_map:
                self.character_map[c].mark = True

        elif mode == 2:
            for c in self.character_map:
                character = self.character_map[c]

                if (real_fathers 
                    and character.real_father in self.character_map):
                    father_id = character.real_father
                else:
                    father_id = character.father

                if father_id in self.character_map:
                    self.character_map[father_id].children.append(c)
                if character.mother in self.character_map:
                    self.character_map[character.mother].children.append(c)

            for c in self.character_map:
                character = self.character_map[c]

                if character.dynasty_id == player_dynasty:
                    self.mark_character_and_family(c, real_fathers)

        elif mode == 3:
            for c in self.character_map:
                character = self.character_map[c]

                if character.dynasty_id == player_dynasty:
                    self.mark_character_and_family(c, real_fathers)

                else:
                    if (real_fathers 
                        and character.real_father in self.character_map):
                        father_id = character.real_father
                    else:
                        father_id = character.father

                    mother_id = character.mother

                    if (father_id in self.character_map
                        and (self.character_map[father_id].dynasty_id == 
                                player_dynasty)):
                        character.mark = True
                    if (mother_id in self.character_map
                        and (self.character_map[mother_id].dynasty_id == 
                                 player_dynasty)):
                        character.mark = True

        else:
            for c in self.character_map:
                character = self.character_map[c]

                if character.dynasty_id == player_dynasty:
                    self.mark_character_and_family(c, real_fathers)

        return True

    def mark_character_and_family(self, character_id, real_fathers):
        character = self.character_map[character_id]
        character.mark = True

        if character.family_marked:
            return
        else:
            character.family_marked = True

        if real_fathers and character.real_father in self.character_map:
            father_id = character.real_father
        else:
            father_id = character.father

        if father_id in self.character_map:
            self.character_map[father_id].mark = True
        if character.mother in self.character_map:
            self.character_map[character.mother].mark = True
        for s in character.spouse:
            self.character_map[s].mark = True
        for c in character.children:
            self.mark_character_and_family(c, real_fathers)
