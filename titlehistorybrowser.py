import sys
import re
from datatypes import Date

class TitleHistoryBrowser(object):
    date_regex = re.compile(r'\d{3,4}\.\d{2}\.\d{2}')

    def __init__(self, game_data):
        character_map = game_data.character_map
        self.character_map = {c: character_map[c] for c in character_map
            if len(character_map[c].title_history.titles) > 0}
        self.title_map = game_data.title_map
        self.current_query = ''
        self.current_loc = 0
        self.current_results = []
        self.cultural_titles = False
        self.show_tags = False

    @staticmethod
    def show_help():
        print('The tool recognizes the following commands:\n'
              '(All commands are case-insensitive)\n'
              'General commands:\n'
              '"help": Display this message\n'
              '"quit": Quit\n'
              '"option <option> <value>": Sets an option to a particular\n'
              '    value.  Currently the only options are "cultural_titles"\n'
              '    (indicating whether to display cultural versions of title\n'
              '    names) and "show_tags" (indicating whether or not to show\n'
              '    title tags/ids) and they can both be set to either "on" or\n'
              '    "off".  They are both off by default.\n'
              '\n'
              'Displaying title histories:\n'
              'Type the number that corresponds to a character\'s character\n'
              'ID in order to view their title history.\n'
              '\n'
              'Searching for characters:\n'
              '<one or more search terms>: displays a list of characters who\n'
              '    match all search terms.\n'
              '"next": Advances one page of 20 search results in the current\n'
              '    search.\n'
              '"back": Goes back one page of 20 search results in the current\n'
              '    search.\n'
              '<(Y)YYY.MM.DD>: Typing a date in this pattern will jump to\n'
              '    that date in the current search results.\n'
              '<return>: Simply hitting return displays the search results at\n'
              '    the current position, if you were, say, previously looking\n'
              '    at a title history.\n'
              '\n(Press enter to continue)')
        sys.stdin.readline()
        print('You can search for characters by typing their birth name,\n'
              'their regnal name, their dynasty name, or the id/tag of any\n'
              'title they have ever held.  Names with spaces must be enclosed\n'
              'in double quotes.  Special characters can generally be found\n'
              'by searching for their ASCII equivalents as well (note that\n'
              'ð = dh, þ = th, ß = ss).  You can type as many of these search\n'
              'terms as you want and the tool will find all characters that\n'
              'match all search terms.  Note that it checks their entire\n'
              'title history, so if you search for e.g. "e_byzantium e_hre"\n'
              'your search will not be limited to characters who held both\n'
              'titles at the same time, but will also include characters who\n'
              'held one title at one time and the other title at a different\n'
              'time.\n'
              '\n'
              'The list of search results will be sorted in other of birth\n'
              'date.  In addition to the "next" and "back" commands that you\n'
              'can use to browse it, you can also type a date in form of\n'
              '(Y)YYY.MM.DD and the tool will skip to the first person in the\n'
              'search results who was born on or after that day.  The date\n'
              'must be in that exact format.\n'
              '\n'
              'If you have chosen to name your characters "help" or "next" or\n'
              '"option show_tags on" or a number that corresponds to someone\n'
              'else\'s character ID, you can force the tool to interpret\n'
              'these as search terms by enclosing them with double quotes.\n'
              '\n'
              'Note that title histories prior to game start are missing a\n'
              'lot of information and this tool is not very good at figuring\n'
              'it out.')

    def show_title_history(self, character):
        lines = character.get_title_history(self.character_map, self.title_map,
                                            self.cultural_titles,
                                            self.show_tags)
        while len(lines) > 20:
            line_index = 20
            while line_index >= 0 and lines[line_index].startswith('    '):
                line_index -= 1
            if line_index == -1:
                text = '\n'.join(lines[:20])
            else:
                text = '\n'.join(lines[:line_index])
            print(text)
            print('\n(Press enter for more)')
            lines = lines[line_index:]
            sys.stdin.readline()
        if len(lines) > 0:
            print('\n'.join(lines))

    def show_search_results(self):
        if self.current_query == '':
            return

        if len(self.current_results) == 0:
            print('No results.')
            return

        if self.current_loc + 20 < len(self.current_results):
            end_loc = self.current_loc + 20
        else:
            end_loc = len(self.current_results)

        print('Current search: ' + self.current_query + ' ('
              + str(self.current_loc + 1) + ' - ' + str(end_loc) 
              + ' of ' + str(len(self.current_results)) + ')\n')
                
        if self.current_loc >= len(self.current_results):
            print('No more results.')

        else:
            results = self.current_results[self.current_loc:end_loc]
            for result in results:
                character = self.character_map[result]
                text = character.get_primary_title(self.title_map, True)
                text += ' (born ' + str(character.birthday) + ')'
                text += ' [' + str(result) + ']'
                text_list = []
                while len(text) > 76:
                    loc = text.rfind(' ', 0, 76)
                    text_list.append('    ' + text[:loc])
                    text = text[loc+1:]
                text_list.append('    ' + text)
                text_list[0] = text_list[0][4:]
                print('\n'.join(text_list))


    def skip_to_date(self, date):
        for i, c_id in enumerate(self.current_results):
            if self.character_map[c_id].birthday >= date:
                self.current_loc = i
                return

    @staticmethod
    def tokenize_query(text):
        tokens = []
        current_token = ''
        for c in text:
            if current_token.startswith('"'):
                if c == '"':
                    tokens.append(current_token.strip('"'))
                    current_token = ''
                else:
                    current_token += c
            elif current_token != '':
                if c == '"':
                    tokens.append(current_token)
                    current_token = c
                elif c == ' ':
                    tokens.append(current_token)
                    current_token = ''
                else:
                    current_token += c
            else:
                current_token += c
        if current_token != '':
            tokens.append(current_token.strip('"'))

        return tokens

    def run(self):
        print('Type "help" for help.  Type "quit" to quit.')

        while True:
            print('>', end=' ')
            sys.stdout.flush()

            command = sys.stdin.readline().strip()
            command = command.lower()

            if command == '':
                self.show_search_results()

            elif command == 'quit':
                break

            elif command == 'help':
                self.show_help()

            elif command == 'next':
                if self.current_query != '':
                    self.current_loc += 20
                self.show_search_results()

            elif command == 'back':
                if self.current_query != '':
                    if self.current_loc < 20:
                        self.current_loc = 0
                    else:
                        self.current_loc -= 20
                self.show_search_results()

            elif command.startswith('option '):
                parts = command.split()
                if len(parts) < 3:
                    print('Usage: "option <option> <value>"')
                elif parts[1] not in ['cultural_titles', 'show_tags']:
                    print('Error: No such option "' + parts[1] + '"')
                elif parts[2] not in ['on', 'off']:
                    print('Error: "' + parts[2] + '" is not a valid value for '
                          'option "' + parts[1] + '"')
                elif parts[1] == 'cultural_titles':
                    self.cultural_titles = (parts[2] == 'on')
                else:
                    self.show_tags = (parts[2] == 'on')

            elif (re.match(r'^\d+$', command) 
                  and int(command) in self.character_map):
                self.show_title_history(self.character_map[int(command)])

            elif self.date_regex.match(command):
                date_parts = list(map(int, command.split('.')))
                date = Date()
                date.set_date(date_parts)
                self.skip_to_date(date)
                self.show_search_results()

            else:
                self.current_query = command
                self.current_loc = 0
                tokens = self.tokenize_query(command)
                results = [c for c in self.character_map 
                           if self.character_map[c].matches_search(tokens)]
                self.current_results = sorted(
                    results, key=lambda x: self.character_map[x].birthday
                )
                self.show_search_results()
