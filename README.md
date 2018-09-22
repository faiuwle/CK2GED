ck2\_ged for Crusader Kings II    

    Requires:         Crusader Kings II (version 2.6.3 through 2.8.3.3)   
                      Python (version 3.5+)    
    Utility version:  2018.09.22
    Readme version:   2018.09.22    

----------------------------------------------------------------------
Description:

ck2\_ged:

Converts a Crusader Kings II save file (.ck2) into a GEDCOM file
(.ged). This file can be interpreted by many different genealogy
software packages, providing the player a way to view the family
relations occuring within their game.

ck2\_title\_history:

Allows the user to browse personal title histories (histories of which titles
they held, gained, lost, inherited, conquered, revoked, granted, etc, during
their lifetimes).  It has a command-line interface.

----------------------------------------------------------------------
Instructions:

ck2\_ged:

Place copies of the following files into the same directory:
  - ck2\_ged.py
  - settings.py
  - datatypes.py
  - gamedata.py
  - gedcomwriter.py
  - The .ck2 file you wish to convert

Open settings.py in your favorite text editor or word processor and make 
sure ck2\_install\_dir and mod\_dir are set to your CKII install directory 
and the directory where you install mods, respectively.  Set other 
options as you desire.

Run ck2\_ged.py, follow the prompts, and wait a moment. When finished,
you will find a .ged file with the same name as the .ck2 file in the
directory.

Report any problems to the Paradox Interactive Forums thread: https://forum.paradoxplaza.com/forum/index.php?threads/tool-extract-family-trees-from-your-save-and-browse-personal-title-histories.1120670/.  I probably need you to upload your save and tell me what mods you are using.


ck2\_title\_history:

Place copies of the following files into the same directory:
  - ck2\_title\_history
  - settings.py
  - datatypes.py
  - gamedata.py
  - titlehistorybrowser.py
  - the .ck2 file you wish to browse

Open settings.py and make sure that ck2\_install\_dir and mod\_dir are set to
your CK@ install directory and the directory where you install mods,
respectively.  The other options do no matter.

Run ck2\_title\_history, and follow the prompts.  When finished, it will launch
the title browser interface, where you can type commands and see the results.
Start by typing "help" to get a help message telling you what commands are
recognized.  You should then be able to use the browser to browse title
histories.

Report any problems to the Paradox Interactive Forums thread: https://forum.paradoxplaza.com/forum/index.php?threads/tool-extract-family-trees-from-your-save-and-browse-personal-title-histories.1120670/.  I probably need you to upload your save and tell me what
mods you are using, and what you were doing when the problem happened.

----------------------------------------------------------------------
Credits:

- Leyic
- Shawn Moore
- Ruth Morrison
- Paradox Interactive / the Crusader Kings II team
- Everyone who developed GEDCOM

----------------------------------------------------------------------
Permissions:

So long as you give credit where credit is due, you are free to use,
redistribute, and modify this mod however you wish. I'd appreciate it
if you'd let me know of any changes you make and release, however.

----------------------------------------------------------------------
History:

After this, the script was moved to github.

2017.07.31 - Rewrote parser.  Updated to work with CK2 2.6.3 and 2.7.1.  Fixed some bugs.  Added primary titles and years of rule feature.

2013.03.26: -Updated code to work with newer updates of CKII. Changed behavior
of arrays that pulled info from dynastiesi.txt since they were being overwritten by information from the save file. Added code to proceed if a character has a single parent but not both.

2012.02.18: -.csv output for dynasties, characters, and families.
            -Minor changes.
2012.02.16: -Initial release.
