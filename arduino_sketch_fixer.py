#!/bin/python
import re
import os

class Arduino_Sketch:

  Function_Declarations = []

  def __init__(self, filepath):
    ## The filepath is going to point to the sketchname.ino file. We want to
    ##  take that file, append any other .ino files in the directory, then
    ##  scan it to make function declarations for all the functions in it.
    path_only = os.path.dirname(filepath)
    sketch_name = os.path.basename(filepath)

    with open(filepath) as f:
      cpp_file = list(f)

    for code_file in os.listdir(path_only):
      if code_file.endswith(".ino"):
        if code_file not in sketch_name:
          with open(path_only +"/"+ code_file) as f:
            for line in f:
              cpp_file.append(line)

    ## At this point, cpp_file contains all the sketch files concatenated
    ##  into one file. We need to do a couple of things to make this ready
    ##  to compile: adding in #include<Arduino.h> and scan the file to find all
    ##  function definitions so we can construct declarations for them.

    ## First, let's come up with a regex that describes what a function
    ##  declarator looks like. Broadly, it looks like this:
    ##
    ##  return_type function_name(type0 arg0, type1 arg1, ..., typen argn)
    ##
    ##  HOWEVER, there are *exceptions* to this. For instance, the return type
    ##  could be a pointer. Putting a space between the function name and
    ##  the first paren is valid. The brace could be on this line, or the next,
    ##  or several lines later. A newline can be inserted in the declarator,
    ##  with or without comments. So many options! We could even have a function
    ##  *pointer*!!!! I *am* going to make an assumption, here: the programmer
    ##  should be following some kind of decent style and not doing two things:
    ##   1. Putting comments (or anything other than whitespace) before the 
    ##      declarator;
    ##   2. Returning anything other than a value or a pointer. No references!
    ##
    ## So, where does that leave us? Well, there are three basic elements we
    ##  need to discover: return type, function name, and parameters. The
    ##  return type may or may not be in parens, but *must* be a valid C++
    ##  identifier, meaning it must start with an underscore or alpha and can
    ##  only contain alphas, underscores, and numbers. After the return type,
    ##  there may or may not be white space, may or may not be stars, and may
    ##  or may not be a close paren. Then, there may or may not be whitespace
    ##  (there MUST be whitespace if there are no parens or stars), and the
    ##  function name (which also must be a valid C++ identifier) can be in
    ##  parens, and may be preceded by whitespace and one or more stars. Lastly
    ##  we come to the parameters, a paren-enclosed group of comma separated
    ##  items, each of which must have at least some white space in it.
    ## Ugh.
    ## Let's take it in pieces. It's easier to say something *isn't* a
    ##  declarator than that it is. For instance, no line ending in a semicolon
    ##  is a declarator, or starting with a left brace, or with a comment
    ##  identifier, or having a # at the beginning, or *within* a comment
    ##  block.
    
    ## This lets us track whether we're in a multi-line comment or not.
    in_comment = False

    ## It's useful to know how deep we are into a parenthesis nesting. ( causes
    ##  an increment, ) causes a decrement.
    parens_stack  = 0
    braces_stack = 0

    ## These regular expressions are helpful in telling what kind of line you
    ##  are looking at.

    ## Any line with any amount of whitespace followed by either // or by
    ## /* ... */ with nothing after the close block comment could be stripped
    ## out. Maybe not?
    Comment_Line_re = re.compile('^\s*(//.*|/\*.*\*/$)')

    ## /* on a line without */ means you've opened a block comment.
    Comment_Opener_re = re.compile('.*/\*.*(?!\*/)')
    ## */ on a line means a block comment was closed, there.
    Comment_Closer_re = re.compile('.*\*/')

    ## if we have seen a { without a corresponding }, we aren't seeing a
    ##  declarator, as we're currently IN a function.
    Brace_Open_re = re.compile('.*(?<!//).*\{')
    Brace_Close_re = re.compile('\}')
    Nonleading_Brace_Open_re = re.compile('\S+\s*\{')
    Nonleading_Brace_Close_re = re.compile('(\S+\s*\})|(^\s*\})')

    ## Obviously, any line with a leading sharp is a preprocessor directive
    ##  and can be ignored. I'm not even going to try to cope with preproc
    ##  conditionals. That's just too much.
    Preprocessor_re = re.compile('^\s*\#')

    for line in cpp_file:  
      if Comment_Line_re.search(line) != None:
        # This line is *all* comments!
        continue

      if Preprocessor_re.search(line) != None:
        continue

      if in_comment:
        if Comment_Closer_re.search(line) != None:
          in_comment = False
        else:
          continue

      if Comment_Opener_re.search(line) != None:
        # This line has an open block comment, but not a close block comment.
        in_comment = True

      if Brace_Open_re.search(line) != None:
        braces_stack = braces_stack + 1
      
      if Brace_Close_re.search(line) != None:
        braces_stack = braces_stack - 1

      if braces_stack > 0:
        ## There is one case where we *don't* want to continue if there's an
        ##  open brace set: the open brace is on *this* line. Some degenerates
        ##  insist on writing code with the open brace on the same line as
        ##  the opening statement. I don't get it either.
        if Nonleading_Brace_Open_re.search(line) == None:
          continue
        #elif Nonleading_Brace_Close_re.search(line) == None:
          continue

      print str(braces_stack) + "  " +line

      ## IF we reach this point, we can make several suppositions about this
      ##  line of code.
      ##   1. It's not in a function.
      ##   2. It's not in a comment block.
      ##   3. It's not a comment.
      ##   4. It's not a preprocessor directive.


