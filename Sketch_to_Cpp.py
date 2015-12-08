#!/bin/python
import re
import os
import sys



def fix_sketch(filepath):
    # The filepath is going to point to the sketchname.ino file. We want to
    # take that file, append any other .ino files in the directory, then
    # scan it to make function declarations for all the functions in it.
    path_only = os.path.dirname(filepath)
    sketch_name = os.path.basename(filepath)

    with open(filepath) as f:
        cpp_file = list(f)

    for code_file in os.listdir(path_only):
        if code_file.endswith(".ino"):
            if code_file not in sketch_name:
                with open(path_only + "/" + code_file) as f:
                    for line in f:
                        cpp_file.append(line)

    # At this point, cpp_file contains all the sketch files concatenated
    # into one file. We need to do a couple of things to make this ready to
    # compile: adding in #include<Arduino.h> and scan the file to find all
    # function definitions so we can construct declarations for them.

    # First, let's come up with a regex that describes what a function
    # declarator looks like. Broadly, it looks like this:
    #
    # return_type function_name(type0 arg0, type1 arg1, ..., typen argn)
    #
    # HOWEVER, there are *exceptions* to this. For instance, the return
    # type could be a pointer. Putting a space between the function name
    # and the first paren is valid. The brace could be on this line, or the
    # next, or several lines later. A newline can be inserted in the
    # declarator, with or without comments. So many options! We could even
    # have a function *pointer*!!!! I *am* going to make an assumption,
    # here: the programmer should be following some kind of decent style
    # and not doing two things: 
    # 1. Putting comments (or anything other than whitespace) before the
    #    declarator; 
    # 2. Returning anything other than a value or a pointer. No references!
    #
    # So, where does that leave us? Well, there are three basic elements we
    # need to discover: return type, function name, and parameters. The
    # return type may or may not be in parens, but *must* be a valid C++
    # identifier, meaning it must start with an underscore or alpha and can
    # only contain alphas, underscores, and numbers. After the return type,
    # there may or may not be white space, may or may not be stars, and may
    # or may not be a close paren. Then, there may or may not be whitespace
    # (there MUST be whitespace if there are no parens or stars), and the
    # function name (which also must be a valid C++ identifier) can be in
    # parens, and may be preceded by whitespace and one or more stars.
    # Lastly we come to the parameters, a paren-enclosed group of comma
    # separated items, each of which must have at least some white space in
    # it.  Ugh.  Let's take it in pieces. It's easier to say something
    # *isn't* a declarator than that it is. For instance, no line ending in
    # a semicolon is a declarator, or starting with a left brace, or with a
    # comment identifier, or having a # at the beginning, or *within* a
    # comment block.

    # This lets us track whether we're in a multi-line comment or not.
    in_comment = False

    # It's useful to know how deep we are into a parenthesis nesting. 
    # ( causes an increment, ) causes a decrement.
    parens_stack = 0
    braces_stack = 0

    # These regular expressions are helpful in telling what kind of line
    # you are looking at.

    # Any line with any amount of whitespace followed by either // or by /*
    # ... */ with nothing after the close block comment could be stripped
    # out. Maybe not?
    Comment_Line_re = re.compile('^\s*(//.*|/\*.*\*/$)')
    
    # Any pure whitespace line can be ignored.
    Whitespace_Line_re = re.compile('^\s*$')

    # /* on a line without */ means you've opened a block comment.
    Comment_Opener_re = re.compile('.*/\*.*(?!\*/)')
    # */ on a line means a block comment was closed, there.
    Comment_Closer_re = re.compile('.*\*/')

    # if we have seen a { without a corresponding }, we aren't seeing a
    # declarator, as we're currently IN a function.
    Brace_Open_re = re.compile('.*(?<!//).*\{')
    Brace_Close_re = re.compile('^\s*\}')
    Nonleading_Brace_Open_re = re.compile('\S+\s*\{')
    Nonleading_Brace_Close_re = re.compile('(\S+\s*\})|(^\s*\})')

    # Obviously, any line with a leading sharp is a preprocessor directive
    # and can be ignored. I'm not even going to try to cope with preproc
    # conditionals. That's just too much.
    Preprocessor_re = re.compile('^\s*#')

    # HOWEVER! We do need to find SOME #include statements and keep the file
    # name, as those represent directories that we'll need to search for 
    # library files later. Arduino only expects those to be on lines that are
    # right at the top of the file, so we can limit our search range by that
    # fact. We'll also make sure the files names aren't located in the sketch
    # directory.
    Include_re = \
        re.compile('^\s*#include\s*(<|")(?P<include_name>[\w/-]*)\.h("|>)')

    # If a line has a semicolon at the end, but no open brace, we can skip
    # it.
    Semicolon_no_open_brace_re = re.compile('^\s*\{*[^}].*;')

    # We'll want to strip out any unclosed block comments, any one-line
    #  comments, everything up to a block comment close,  and any fully 
    #  closed block comments. Here are regexes for doing just that.
    Comment_strip_re = \
    re.compile('(/\*.*\*/)|(/\*.*$)|(//.*$)|(/\*.*$)|(^.*\*/)')

    # We'll want to strip off any rogue open braces, too.
    Open_brace_strip_re = re.compile('\s*\{.*')

    # RegEx to discover parens. All we need to do is make sure all opens
    # have a close with them.
    Open_paren_re = re.compile('\(')
    Close_paren_re = re.compile('\)')

    declarator_line_list = []

    for line in cpp_file:

        # This line is nothing but comments; don't save it.
        if Comment_Line_re.search(line) != None:
            continue

        # This line is a preprocessor statement; don't save it.
        if Preprocessor_re.search(line) != None:
            continue

        # This line is whitespace only. Skip it.
        if Whitespace_Line_re.search(line) != None:
            continue

        # This line is *in* a comment block. Check to see if the comment is
        # closed on this line, and if not, don't save it.
        if in_comment:
            if Comment_Closer_re.search(line) != None:
                in_comment = False
            else:
                continue

        # This line opens a comment, but doesn't close it. Mark that.

        if Comment_Opener_re.search(line) != None:
            in_comment = True

        if Comment_Closer_re.search(line) != None:
            in_comment = False

        # This line opens braces; mark that.
        if Brace_Open_re.search(line) != None:
            braces_stack += 1

        # This line closes braces; mark that.
        if Brace_Close_re.search(line) != None:
            braces_stack -= 1

        # Now, if we are inside a brace set, what do we do?
        if braces_stack > 0:
            if (Brace_Open_re.search(line)) != None:
                if braces_stack > 1:
                    continue
                else:
                    pass
            else:
                continue

        # IF we reach this point, we can make several suppositions about 
        #  this line of code.
        # 1. It's not in a function.
        # 2. It's not in a comment block.
        # 3. It's not a comment.
        # 4. It's not a preprocessor directive.

        # Okay, what can we winnow out now? Well, anything that has a 
        #  semicolon at the end of the line, but not an open brace, is 
        #  probably not a declarator.
        if Semicolon_no_open_brace_re.search(line) != None:
            continue

        # Things that may be removed from the string at this point: any
        #  fully closed comment, any open comment that isn't closed before
        #  the end of the line, any one-line comment, and anything up to a
        #  close block comment.

        line = Comment_strip_re.sub('', line)

        # At this point, we should be 100% declarators or subsections
        #  thereof. 
        declarator_line_list.append(line.strip())

    ##### End of file parsing.

    declarator_string = ''.join(declarator_line_list)

    # Declarator string is all the declarators, separated by {}. We can
    #  easily break them up.
    declarator_list = declarator_string.rstrip('{}').split('{}')

    # cpp_file is a list of the lines in the .ino files found in the
    #  sketch directory. Insertion at the top of a list is slow; we
    #  could use the deque type to speed it up, but that's not really
    #  necessary; the better way is just to iterate over cpp_file and
    #  stick the data into a file object, inserting other data as we go
    #  as needed.

    with open(path_only + "/build/" + sketch_name[0:-3] + "cpp", 'w') as f_out:
        f_out.write("#include<Arduino.h>\n")
        include_files = []
        include_section = True
        for line in cpp_file:
            if include_section:
                if "include" in line:
                    f_out.write(line)
                    include_files.append(Include_re.search(line).group('include_name'))
                    continue
                else:
                    include_section = False
                    for declaration in declarator_list:
                        f_out.write(declaration + ";\n")
            else:
               f_out.write(line) 

        return include_files
