import settings
from datatypes import Date
import sys

class Family(object):
    """Stores information relevant to a family (GEDCOM definition)."""
    def __init__(self):
        self.id = ''
        self.father = []
        self.mother = []
        self.children = []

class GedcomWriter(object):
    def __init__(self):
        self.family_map = {}
        self.gedcom_map = {}

    def initialize(self, game_data):
        self.character_map = game_data.character_map
        self.title_map = game_data.title_map

        self.generate_gedcom_families()

    def generate_gedcom_families(self):
        print('### Generating GEDCOM family information...', end=' ')

        family_id = 1

        for c in self.character_map:
            character = self.character_map[c]

            if not character.mark:
                continue

            if (settings.real_fathers 
                and character.real_father in self.character_map):
                father_id = character.real_father
            else:
                father_id = character.father

            mother_id = character.mother

            if (father_id in self.character_map 
                and self.character_map[father_id].mark):
                generate_parents = True
            elif (mother_id in self.character_map 
                  and self.character_map[mother_id].mark):
                generate_parents = True
            else:
                generate_parents = False

            if generate_parents:
                character.loner = False

                
                if father_id < mother_id:
                    temp = (father_id, mother_id)
                else:
                    temp = (mother_id, father_id)

                if temp not in self.family_map:
                    family = Family()
                    family.id = family_id
                    family.father = father_id
                    family.mother = mother_id
                    family.children.append(c)
                    self.family_map[temp] = family

                    if father_id in self.character_map:
                        self.character_map[father_id].FAMS.append(family_id)
                        self.character_map[father_id].loner = False
                    if mother_id in self.character_map:
                        self.character_map[mother_id].FAMS.append(family_id)
                        self.character_map[mother_id].loner = False

                    character.FAMC = family_id

                    family_id += 1

                else:
                    family = self.family_map[temp]
                    family.children.append(c)
                    character.FAMC = family.id

            if (len(character.spouse) > 0 
                and not settings.cull_childless_spouses):
                for s in character.spouse:
                    spouse = self.character_map[s]

                    if not spouse.mark:
                        continue

                    character.loner = False

                    #if character.gender == 1 and spouse.gender == 0:
                    #  temp = (c, s)
                    #elif character.gender == 0 and spouse.gender == 1:
                    #  temp = (s, c)
                    #else:
                    #  continue
                    if character.id < spouse.id:
                        temp = (c, s)
                    elif character.id > spouse.id:
                        temp = (s, c)
                    else:
                        continue

                    if temp not in self.family_map:
                        family = Family()
                        family.id = family_id

                        if character.gender == 1:
                            family.father = character.id
                            family.mother = spouse.id
                        else:
                            family.father = spouse.id
                            family.mother = character.id

                        self.family_map[temp] = family

                        character.FAMS.append(family_id)
                        spouse.FAMS.append(family_id)
                        spouse.loner = False

                        family_id += 1

        gedcom_id = 1

        for c in self.character_map:
            character = self.character_map[c]

            if not character.mark:
                continue

            if not character.loner or not settings.cull_loners:
                character.GEDCOM_id = gedcom_id
                self.gedcom_map[gedcom_id] = c
                gedcom_id += 1

        print('Done. ###')

    def write_gedcom(self, filename):
        print('### Writing .ged file...', end=' ')

        with open(filename, 'w', encoding='utf-8') as file:
            file.write('0 HEAD\n1 FILE ' + filename + '\n1 GEDC\n2 VERS 5.5\n')
            file.write('2 FORM LINEAGE-LINKED\n1 CHAR UTF-8')

            for g in self.gedcom_map:
                line = ''

                character = self.character_map[self.gedcom_map[g]]

                if character.gender == 0:
                    gender_string = 'F'
                else:
                    gender_string = 'M'

                line += '\n0 @I' + str(g) + '@ INDI'
                line += '\n1 NAME ' + character.birth_name + ' /'
                line += character.dynasty_name.upper() + '/'
                line += '\n2 GIVN ' + character.birth_name
                line += '\n2 SURN ' + character.dynasty_name
                line += '\n1 SEX ' + gender_string
                line += '\n1 OCCU ' 
                line += character.get_primary_title(self.title_map)

                years_of_rule = character.get_years_of_rule(self.title_map)

                for s in years_of_rule:
                    line += '\n1 NOTE ' + s

                line += '\n1 NOTE Game ID# ' + str(character.id)

                if (settings.real_fathers 
                    and character.real_father in self.character_map
                    and character.father in self.character_map):
                    line += '\n1 NOTE Presumed father is '
                    line += self.character_map[character.father].birth_name
                    line += ' '
                    line += self.character_map[character.father].dynasty_name
                    line += ' (' + str(character.father) + ')'

                elif (settings.real_fathers 
                      and character.real_father in self.character_map):
                    line += '\n1 NOTE Father unknown'

                elif (not settings.real_fathers
                      and character.real_father in self.character_map):
                    real_father = character.real_father
                    line += '\n1 NOTE Real father is '
                    line += self.character_map[real_father].birth_name + ' '
                    line += self.character_map[real_father].dynasty_name + ' ('
                    line += str(real_father) + ')'

                if type(character.birthday) is Date:
                    line += '\n1 BIRT\n2 DATE '
                    line += character.birthday.gedcom_string()

                if type(character.deathday) is Date:
                    line += '\n1 DEAT\n2 DATE '
                    line += character.deathday.gedcom_string()

                for f in character.FAMS:
                    line += '\n1 FAMS @F' + str(f) + '@'

                if character.FAMC > 0:
                    line += '\n1 FAMC @F' + str(character.FAMC) + '@'

                file.write(line)

            for f in self.family_map:
                line = ''

                family = self.family_map[f]

                line += '\n0 @F' + str(family.id) + '@ FAM'

                if family.father in self.character_map:
                    character = self.character_map[family.father]
                    if character.GEDCOM_id > 0:
                        line += '\n1 HUSB @I' + str(character.GEDCOM_id) + '@'

                if family.mother in self.character_map:
                    character = self.character_map[family.mother]
                    if character.GEDCOM_id > 0:
                        line += '\n1 WIFE @I' + str(character.GEDCOM_id) + '@'

                for c in family.children:
                    character = self.character_map[c]
                    if character.GEDCOM_id > 0:
                        line += '\n1 CHIL @I' + str(character.GEDCOM_id) + '@'

                file.write(line)

            file.close()

        print('Done. ###')
