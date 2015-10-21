#!/bin/python27
import re

class Sketch_Info_Loader:

  def __init__(self, filename, Variables):

    Comment_re = re.compile('\A\s*#')
    
    Variable_name_re = re.compile('\A\s*(?P<the_variable_name>[.\w]*)(?=\s*=\s*)')
    Variable_string_re = re.compile('\A\s*[.\w]*\s*=\s*(?P<the_variable_value>[^#]*)')

    with open(filename) as f:
      platform_txt = f.readlines()
    
    ## Now, we'll iterate over the lines from our file check each one for a
    ##  match to any of our regular expressions, and sort them away as
    ##  appropriate.

   for line in platform_txt:

      ## If this line is a comment, just skip it.
      if Comment_re.match(line) != None:
        continue

      ## If this line has a variable in it, file it.
      if Variable_name_re.search(line) != None:
        tempList = []
        for match in Variable_name_re.findall(line):
          tempList.append(match)
        tempList.append(Variable_string_re.match(line).group('the_variable'))
        Variables.append(tempList)
        continue

