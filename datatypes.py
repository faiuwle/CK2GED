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

asciify_dict = {
    'à': 'a',
    'á': 'a',
    'â': 'a',
    'ã': 'a',
    'ä': 'a',
    'å': 'a',
    'æ': 'ae',
    'ç': 'c',
    'è': 'e',
    'é': 'e',
    'ê': 'e',
    'ë': 'e',
    'ì': 'i',
    'í': 'i',
    'î': 'i',
    'ï': 'i',
    'ð': 'dh',
    'ñ': 'n',
    'ò': 'o',
    'ó': 'o',
    'ô': 'o',
    'õ': 'o',
    'ö': 'o',
    'ø': 'o',
    'ù': 'u',
    'ú': 'u',
    'û': 'u',
    'ü': 'u',
    'ý': 'y',
    'þ': 'th',
    'ÿ': 'y',
    'ß': 'ss',
    'š': 's',
    'œ': 'oe',
    'ž': 'z'
}

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
        self.mercenary = False
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
    realm_names = {}  # static member populated by GameData

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

    lose_text = {'claim': 'lost {0} to {1}, a claimant',
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

    def get_primary(self, title_map, always=False):
        if self.primary == '':
            return self.name if always else ''

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

    def get_realm_name(self, rank, cultural_titles):
        if rank >= BARON:
            return ''

        if self.government in TitleHistory.realm_names:
            r = TitleHistory.realm_names[self.government][rank]

            if self.religion.id in r:
                return r[self.religion.id]
            elif self.religion.group in r:
                return r[self.religion.group]
            elif cultural_titles and self.culture.id in r:
                return r[self.culture.id]
            elif cultural_titles and self.culture.group in r:
                return r[self.culture.group]
            elif '' in r:
                return r['']

        if '' in TitleHistory.realm_names:
            r = TitleHistory.realm_names[''][rank]

            if self.religion.id in r:
                return r[self.religion.id]
            elif self.religion.group in r:
                return r[self.religion.group]
            elif cultural_titles and self.culture.id in r:
                return r[self.culture.id]
            elif cultural_titles and self.culture.group in r:
                return r[self.culture.group]
            elif '' in r:
                return r['']

        return ''

    def format_lose_gain_text(self, gain, succ_type, other, titles,
                              cultural_titles, show_tags):
        if other.id == -1:
            other_text = 'an unknown person'
        elif other.culture is not None and other.culture.dynasty_name_first:
            other_text = other.dynasty_name + ' ' + other.birth_name
        else:
            other_text = other.birth_name + ' ' + other.dynasty_name
        if other.id > 0:
            other_text += ' [' + str(other.id) + ']'

        title_text = ''
        titles.sort()
        for i, title in enumerate(titles):
            rank = title.rank
            if title.viceroyalty:
                if rank == DUKE:
                    rank = VICEDUKE
                elif rank == KING:
                    rank = VICEKING

            if not title.religious_head and not title.mercenary:
                realm_name = self.get_realm_name(rank, cultural_titles)
            else:
                realm_name = ''

            title_text += '' if len(realm_name) == 0 else realm_name + ' '
            if self.culture.id in title.cultural_names and cultural_titles:
                title_text += title.cultural_names[self.culture.id]
            else:
                title_text += title.name
            if show_tags:
                title_text += ' [' + title.id + ']'

            if i == (len(titles) - 2):
                title_text += ' and '
            elif i < (len(titles) - 2):
                title_text += ', '

        it_them = 'it' if len(titles) == 1 else 'them'

        if succ_type not in TitleHistory.gain_text:
            succ_type = ''

        if gain:
            return TitleHistory.gain_text[succ_type].format(
                title_text, other_text, it_them
            )
        else:
            return TitleHistory.lose_text[succ_type].format(
                title_text, other_text, it_them
            )

    def generate_title_history(self, character_map, title_map, cultural_titles,
                               show_tags):
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
            event_list = sorted(event_list, 
                key=lambda x: (not x[0], x[1], x[2]))
            for k, g in groupby(event_list, lambda x: (x[0], x[1], x[2])):
                titles = [title_map[x[3]] for x in g]
                if k[1] in character_map:
                    other = character_map[k[1]]
                else:
                    other = Character()
                text = self.format_lose_gain_text(k[0], k[2], other, titles,
                                                  cultural_titles, show_tags)
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

    def get_primary_title(self, title_map, always=False):
        return self.title_history.get_primary(title_map, always)

    def get_years_of_rule(self, title_map):
        return self.title_history.get_years_of_rule(title_map)

    def get_title_history(self, character_map, title_map, cultural_titles,
                          show_tags):
        return self.title_history.generate_title_history(
            character_map, title_map, cultural_titles, show_tags
        )
    @staticmethod
    def asciify(text):
        new_text = ''
        for c in text:
            new_text += asciify_dict[c] if c in asciify_dict else c
        return new_text
    def matches_search(self, tokens):
        titles = [t for t in self.title_history.titles 
                  if len([o for o in self.title_history.titles[t]
                          if not o.exclude_from_history]) > 0]
        if len(titles) == 0:
            return False

        tokens = set([self.asciify(t) for t in tokens])
        searchable = [self.birth_name, self.regnal_name, self.dynasty_name]
        searchable += titles
        searchable = set([self.asciify(s.lower()) for s in searchable])
        return tokens.issubset(searchable)
