#!/bin/python27
import re
import copy

class Variable_Manager:
    ''' Variable_Manager is a class that parses a file and finds all of the
    Arduino variables defined within. It can parse multiple files, through
    the existence of a "parse" fuction, and has a getter function that will
    return the variable value for a name passed to it, or None, if no variable
    matches.
    '''
    def __init__(self, filename, board_name=None):
        """ 
        Class constructor. This gathers the data from filename (a platform.txt,
        boards.txt, or arduino.txt file) and parses it to enable the main
        program to call other functions later to handle the steps required to
        produce the HEX file.  
        """
        self.Variables = []
        self.parse_file(filename, board_name)

    def parse_file(self, filename, board_name=None):
        '''
        parse_file scans all the lines in a file and adds any that fit the
        variable RegEx above. We won't do more than capture them here; any
        post-processing will occur later.
        '''

        # Comment lines must be any amount of whitespace at the beginning of 
        #  the line, followed by a sharp. We can just ignore these.
        Comment_re = re.compile('\A\s*#')

        # A "variable" can be invoked later by surrounding its name in braces
        # in another string. It looks a lot like a pattern, EXCEPT it doesn't
        # have "pattern" at the end of it.
        if board_name:
            Variable_name_string = "(?<=^" + board_name + \
                    "\.)[\w.]*(?!pattern)(?=\s*=\s*)"
        else:
            Variable_name_string = "^\s*[\w.]*(?!pattern)(?=\s*=\s*)"

        Variable_name_re = re.compile(Variable_name_string)
        Variable_string_re = re.compile(
            '((?:^\s*)[.\w]*(?!pattern)\s*=\s*)(?P<the_variable>[^#]*)')

        with open(filename) as file:

            # Now, we'll iterate over the lines from our file check each one
            # for a match to any of our regular expressions, and sort them away
            # as appropriate.

            for line in file:

                # If this line is a comment, just skip it.
                if Comment_re.match(line) != None:
                    continue

                # If this line has a variable in it, file it.
                if Variable_name_re.search(line) != None:
                    tempList = []
                    for match in Variable_name_re.findall(line):
                        tempList.append(match)

                    variable_string = Variable_string_re.match(line).\
                                    group('the_variable').strip()
                    tempList.append(variable_string)

                    self.Variables.append(tempList)
                    continue

    def fetch_variable(self, variable_name):
        for item in self.Variables:
            if item[0] == variable_name:
                return item[1]
        return None

    def fetch_variable_list(self):
        return self.Variables

    def add_variable(self, new_variable):
        self.Variables.append(new_variable)

    def replace_variables(self, incomplete_pattern):

        # Use this RegEx to identify variables within the string.
        Variable_re = re.compile('(?<=\{)[\w.]+(?=\})')
        ## Make a list of the variables to look for in this item.
        vars_in_object = Variable_re.findall(incomplete_pattern)


        ## If that list is empty, bail. We should *probably* not get here,
        ##  since the user probably won't call this unless necessary, but
        ##  still, it's good to check.
        if vars_in_object == []:
            return incomplete_pattern

        ## Iterate over the list of variables, scanning for each one in the
        ##  lists of avaialble variables passed to this object.
        for var_to_replace in vars_in_object:
            replacement_var = self.fetch_variable(var_to_replace)
            if replacement_var:
                if (Variable_re.search(replacement_var) != None):
                    replacement_var = self.replace_variables(replacement_var)
                incomplete_pattern = \
                    incomplete_pattern.replace("{" + var_to_replace + "}",\
                                                   replacement_var)                    

        return incomplete_pattern

    def find_variable(self, search_string):
        for var in Variables:
            if search_string in var[0]:
                return var[1]
        return None

## End Variable_Manager class definition
###############################################################################

class Pattern_Manager:

    def __init__(self, filename):
        """ 
        Class constructor. This gathers the data from filename (a platform.txt,
        boards.txt, or arduino.txt file) and parses it to enable the main
        program to call other functions later to handle the steps required to
        produce the HEX file.  
        """
        self.Patterns = []
        self.parse_file(filename)

    def parse_file(self, filename):
        '''
        parse_file scans all the lines in a file and adds any that fit the
        variable RegEx above. We won't do more than capture them here; any
        post-processing will occur later.
        '''
        # Comment lines must be any amount of whitespace at the beginning of 
        #  the line, followed by a sharp. We can just ignore these.
        Comment_re = re.compile('\A\s*#')

        # A "pattern" line gives us a recipe for building a command to execute.
        # We expect to see any amount of whitespace, a dot-separated string
        # with the last dot-group being "pattern", followed by possibly
        # whitespace, an equal sign, whitespace, and a string of characters
        # containing any ASCII character, whitespace, etc. End at either EOL
        # *or* an unescaped sharp character. TODO: Handle escaped sharps!
        Pattern_name_re = re.compile('(?:\A\s*)[.\w]*pattern')
        Pattern_string_re = re.compile(
            '((?:\A\s*)[.\w]*pattern)\s*=\s*(?P<the_pattern>[^#]*)')

        # There's a special case within patterns: if a chunk of the pattern
        #  is a -D flag for gcc, AND the define is an assignment, AND the
        #  assignment is in quotes, we need to do a special escape sequence to
        #  be sure that the quotes pass through Python, the shell, and gcc to
        #  show up in the preprocessor. Otherwise, that string will get sent
        #  in to the compiler wrong.
        Define_Flag_Assignment_re = re.compile('(-D[\w]*=)"(\{[\w.]*\})"')

        with open(filename) as file:
            # Now, we'll iterate over the lines from our file check each one
            # for a match to any of our regular expressions, and sort them away
            # as appropriate.
            for line in file:

                # If this line is a comment, just skip it.
                if Comment_re.match(line) != None:
                    continue

                # If this is line has a pattern in it, file it.
                if Pattern_name_re.search(line) != None:
                    tempList = []
                    for match in Pattern_name_re.findall(line):
                        tempList.append(match)
                    a_pattern = Pattern_string_re.match(line).\
                                    group('the_pattern').strip()
                    if Define_Flag_Assignment_re.search(a_pattern):
                        a_pattern = Define_Flag_Assignment_re.sub(R'\1\\\"\2\\\"', a_pattern)
                    tempList.append(a_pattern.replace(R'"',R'\"'))
                    self.Patterns.append(tempList)
                    continue

    def fetch_pattern(self, pattern_name):
        for item in self.Patterns:
            if item[0] == pattern_name:
                return item[1]
        return None

    def fetch_pattern_list(self):
        return self.Patterns

