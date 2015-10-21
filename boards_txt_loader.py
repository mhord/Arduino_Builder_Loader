#!/bin/python27
import re

class Boards_File_Parser:

  def __init__(self, filename, board, Upload_Variables, Build_Variables):
    
    ## Comment lines must be any amount of whitespace at the beginning of the
    ##  line, followed by a sharp. We can just ignore these.
    Comment_re = re.compile('\A\s*#')

    ## Board identifier. Finds variables associated with this board by checking
    ##  for the board name (passed in by the "board" variable) at the start of
    ##  the line, immediately preceding a '.' character.
    Board_Variable_re_string = r'^\s*' + re.escape(board) + r'\.'
    Board_Variable_re = re.compile(Board_Variable_re_string)

    Upload_Variable_re = re.compile('^\s*\w*\.upload\.')
    Build_Variable_re = re.compile('^\s*\w*\.build\.')
    Variable_Name_re = re.compile('^\s*\w*\.\w*.(?P<the_var_name>\w*)')
    Variable_Value_re = re.compile('^\s*\w*\.\w*.\w*.\s*=\s*(?P<the_var_value>[^#\n]*)')
  
    with open(filename) as f:
      platform_txt = f.readlines()

    for line in platform_txt:  
      ## If this line is a comment, just skip it.
      if Comment_re.match(line) != None:
        continue

      if Board_Variable_re.search(line) != None:
        tempList = []
        if Upload_Variable_re.search(line) != None:
          tempList.append(Variable_Name_re.match(line).group('the_var_name'))
          tempList.append(Variable_Value_re.match(line).group('the_var_value'))
          Upload_Variables.append(tempList)
          continue
        if Build_Variable_re.search(line) != None:
          tempList = []
          tempList.append(Variable_Name_re.match(line).group('the_var_name'))
          tempList.append(Variable_Value_re.match(line).group('the_var_value'))
          Build_Variables.append(tempList)
          continue

