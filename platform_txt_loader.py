#!/bin/python27
import re

class Platform_File_Parser:

  """
  Class constructor. This gathers the data from filename (a platform.txt
  file) and parses it to enable the main program to call other functions later
  to handle the steps required to produce the HEX file.
  """

  def __init__(self, filename, Variables, Patterns):

    ## Comment lines must be any amount of whitespace at the beginning of the
    ##  line, followed by a sharp. We can just ignore these.
    Comment_re = re.compile('\A\s*#')
    
    ## A "pattern" line gives us a recipe for building a command to execute.
    ##  We expect to see any amount of whitespace, a dot-separated string with
    ##  the last dot-group being "pattern", followed by possibly whitespace, an
    ##  equal sign, whitespace, and a string of characters containing any
    ##  ASCII character, whitespace, etc. End at either EOL *or* an unescaped
    ##  sharp character. TODO: Handle escaped sharps!
    Pattern_name_re = re.compile('(?:\A\s*)[.\w]*pattern')
    Pattern_string_re = re.compile('((?:\A\s*)[.\w]*pattern)\s*=\s*(?P<the_pattern>[^#]*)')

    ## A "variable" can be invoked later by surrounding its name in braces in
    ##  another string. It looks a lot like a pattern, EXCEPT it doesn't have
    ##  "pattern" at the end of it.
    Variable_name_re = re.compile('(?:\A\s*)[.\w]*(?!pattern)(?=\s*=\s*)')
    Variable_string_re = re.compile('((?:\A\s*)[.\w]*(?!pattern)\s*=\s*)(?P<the_variable>[^#]*)')

    with open(filename) as f:
      platform_txt = f.readlines()
    
    ## Now, we'll iterate over the lines from our file check each one for a
    ##  match to any of our regular expressions, and sort them away as
    ##  appropriate.

    for line in platform_txt:

      ## If this line is a comment, just skip it.
      if Comment_re.match(line) != None:
        continue

      ## If this is line has a pattern in it, file it.
      if Pattern_name_re.search(line) != None:
        tempList = []
        for match in Pattern_name_re.findall(line):
          tempList.append(match)
        tempList.append(Pattern_string_re.match(line).group('the_pattern'))
        Patterns.append(tempList)
        continue

      ## If this line has a variable in it, file it.
      if Variable_name_re.search(line) != None:
        tempList = []
        for match in Variable_name_re.findall(line):
          tempList.append(match)
        tempList.append(Variable_string_re.match(line).group('the_variable'))
        Variables.append(tempList)
        continue

