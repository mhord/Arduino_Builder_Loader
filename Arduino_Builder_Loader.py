#!/bin/python
import os.path
import os
import itertools
import subprocess
from subprocess import call
import shlex

import platform_txt_loader
import arduino_sketch_fixer
from object_builder import builder

# Deriving values for these settings: 
#  "sketch_path" is the location of the main .ino file of this project.
sketch_path = "c:/Dropbox/Projects/Simblee/Safety_Glue"

#  "vendor" is the subdirectory of the "hardware" directory within which the
#    information for your particular target board resides
vendor = "arduino"

#  "platform" is the subdirectory within the "vendor" directory within which
#    all the actual files and folders defining the board exist
platform = "Simblee"

#  "board" defines the name prepending all the variables in the "boards.txt"
#    file which apply to your target. This may be different to the name in 
#    the boards menu and you should look it up!
board = "Simblee"

#  "runtime_ide_path" defines the location of the IDE. This is important
#    mainly because this is where we expect to find the tools for building and
#    uploading the sketch.
runtime_ide_path = "c:/Dropbox/Arduino/arduino-1.6.1"

# You may be able to leave this out, if you're not referencing any libraries
#  that exist only in the sketchbook/libraries folder, or using a platform that
#  resides in the sketchbook/hardware folder.
sketchbook_path = "c:/Dropbox/Projects"

# This is the ide version you're spoofing.
runtime_ide_version = "10601"

#  "runtime_platform_path" is where we expect to find all the files that make
#    building possible: the core, the libraries, variant information, all of
#    that stuff. It *may* be in the runtime_ide_path, or the sketchbook path
runtime_platform_path = runtime_ide_path + "/hardware/" + vendor + "/" + \
                        platform

# Use this line if your hardware definition is in the sketchbook.
#runtime_platform_path = sketchbook_path + "/hardware/" + vendor + "/" + \ 
#                        platform

# Use these lines if you used the boards manager to download the hardware
#  definition for this board.

# In Windows Vista or later, the path will be
# C:\Users\<username>\AppData\Roaming\Arduino15\packages\something
# We can automatically get at least the first bit by using 
#user_home = os.getenv('USERPROFILE')
#runtime_platform_path = user_home + "/AppData/Roaming/Arduino15/packages/" +\
#        vendor + "/hardware/"

# In Mac OS, we expect it to be here:
#user_home = os.path.expanduser('~')
#runtime_platform_path = user_home + "/Library/Arduino15/packages/" + \
#        vendor + "/hardware/"

# In Linux, we expect it to be here:
#user_home = os.path.expanduser('~')
#runtime_platform_path = user_home + "/.Arduino15/packages/" + \
#        vendor + "/hardware/"


#############################################################################
# Above this line are the per-project settings.

def main():

    # We'll need the sketch name, at times, to do stuff, and we can identify that
    #  from the sketch path.
    sketch_name = os.path.basename(sketch_path) + ".ino"

    build_system_path = runtime_platform_path + "/system"
    platform_txt_file =  runtime_platform_path + "/platform.txt"
    boards_txt_file = runtime_platform_path + "/boards.txt"

    # We may need to create a folder to store all of our temporary files in. We
    #  don't want to pollute our sketch folder with that crap.
    if not os.path.exists(sketch_path + "/build"):
        os.makedirs(sketch_path + "/build")

    # We need to retrieve from the boards.txt and platform.txt files a bunch of
    #  information. They contain all we need to know to build and upload our
    #  sketch.
    Variables = platform_txt_loader.Variable_Manager(boards_txt_file, board)
    Variables.parse_file(platform_txt_file)
    Patterns  = platform_txt_loader.Pattern_Manager(platform_txt_file)

    # These are things that are normally provided by the IDE.
    build_variant_path = runtime_platform_path + "/variants/" + board
    build_path = sketch_path + "/build"
    Variables.add_variable(["runtime.ide.path",runtime_ide_path])
    Variables.add_variable(["runtime.platform.path", runtime_platform_path])
    Variables.add_variable(["build.path", build_path])
    Variables.add_variable(["build.project_name",
                            sketch_name[0:-4] + R'.cpp'])
    Variables.add_variable(["build.variant.path", build_variant_path])
    Variables.add_variable(["build.system.path", build_system_path])
    Variables.add_variable(["software", "ARDUINO"])
    Variables.add_variable(["runtime.ide.version", runtime_ide_version])

    build_includes_path = runtime_platform_path + "/cores/" + \
            Variables.fetch_variable("build.core")
    Variables.add_variable(["build.includes.path", build_includes_path])
    Variables.add_variable(["archive_file", "core.a"])

    # Here's the part where we convert the .ino files into a .cpp file. We
    # concatenate the ino files, magic up some function declarations, and then
    # return a list of likely library includes (according to Arduino standards).
    # Note that library includes are expected to all be above everything that is
    # not a comment or preproc statement; that's kinda dumb but it *does* make
    # turning a #include into a path to find a library easier.
    library_includes = arduino_sketch_fixer.fix_sketch(sketch_path + "/" + \
                                                       sketch_name)

    include_path_list = []
    
    # Now, we don't *know* that these are all actually libraries; the only way we
    # can find out is to look and see if they exist as #include files in the sketch
    # folder.
    for library in library_includes:
        # Of course, no library is likely to have a subdirectory in its include;
        # we can discard anything that does.
        if "/" not in library:
            # If we don't find it in the sketch path, we expect to find it in one
            # of our library paths.
            if not os.path.exists(sketch_path + "/" + library + ".h"):
                # This is the "standard" library path. We want it to overtake any
                # other library of the same name which may exist elsewhere.
                if os.path.exists(runtime_platform_path + "/libraries/" + library):
                    include_path_list.append(runtime_platform_path + \
                                         "/libraries/" + library)
                # Failing that, our next best guess is that it'll be in the
                # sketchbook library folder. This is where the library manager puts
                # things when it downloads them.
                elif os.path.exists(sketchbook_path + "/libraries/" + library):    
                    include_path_list.append(sketchbook_path + \
                                         "/libraries/" + library)
                # Finally, if all else fails, look in the libraries folder in the
                # ide directory. Of course, this is risky, because that's only
                # really reliable for super normal boards released by or cloned
                # from Arduino designs.
                elif os.path.exists(runtime_ide_path + "/libraries/" + library):
                    include_path_list.append(runtime_ide_path + \
                                         "/libraries/" + library)

    include_path_list.append(build_includes_path)
    include_path_list.append(build_variant_path)
    include_path_list.append(sketch_path)
    includes = ""
    for path in include_path_list:
        includes = includes + R'\"-I' + path + R'\" '
    Variables.add_variable(["includes",includes])

    # We now know everything we need to build our sketch into a hex file. Let's
    #  create our build commands. 
    c_file_build = Patterns.fetch_pattern("recipe.c.o.pattern")
    cpp_file_build = Patterns.fetch_pattern("recipe.cpp.o.pattern")
    s_file_build = Patterns.fetch_pattern("recipe.S.o.pattern")

    # It's possible that one or more of those patterns may not exist, so check
    # before attempting to build on it.
    if c_file_build:
        c_build_recipe = Variables.replace_variables(c_file_build)
    if cpp_file_build:
        cpp_build_recipe = Variables.replace_variables(cpp_file_build)
    if s_file_build:
        s_build_recipe = Variables.replace_variables(s_file_build)

    # Here's the crappy part: we have to identify *all* the various files that must
    # be built into object files and, if they've changed since the last change time
    # on the corresponding .o file, delete the .o file and rebuild them.
    # There are *so many* places they could be: in the sketch folder or the build
    # subdirectory thereof, in any of the library folders we included, in the
    # appropriate core directory, maybe even the variants subfolder or any of its
    # subfolders!

    cpp_file_list = []
    c_file_list = []
    s_file_list = []

    builder_list = []

    # First up, find all the files we need and then make a list of each one.
    for path in include_path_list:
        c_file_list.extend(build_source_file_list(path, '.c'))
        cpp_file_list.extend(build_source_file_list(path, '.cpp'))
        s_file_list.extend(build_source_file_list(path, '.s'))
        s_file_list.extend(build_source_file_list(path, '.S'))

    # For each one of these file lists, we'll create a builder object. That
    #  object holds all the necessary data to make a command to build the
    #  object file in question, UNLESS the object file already exists and is
    #  newer than the source file; then it simply is None
    for source_file in cpp_file_list:
        builder_list.append(builder(build_path, source_file,
                                       cpp_build_recipe))
            
    for source_file in c_file_list:
        builder_list.append(builder(build_path, source_file,
                                       c_build_recipe))

    for source_file in s_file_list:
        builder_list.append(builder(build_path, source_file,
                                       s_build_recipe))

    for command in builder_list:
        command.remove_duplicate_args()

    for builder_item in builder_list:
        if builder_item.fetch_build_pattern():
            builder_cmd = builder_item.make_win_cmd()
            subprocess.check_call(builder_cmd)

    # Must put all object files into an archive file; we can do that
    #  incrementally, but not linking. We can't just directly link the files
    #  because the line length of all the object files would be way too long
    #  for most operating systems to manage.
    object_files = build_source_file_list(build_path, ".o")
    archive_recipe = Variables.replace_variables(\
                     Patterns.fetch_pattern('recipe.ar.pattern'))
    for obj in object_files:
        ar_cmd = archive_recipe.replace('{object_file}', obj).replace('\\\"', '\"')
        subprocess.check_call(ar_cmd)

    # Time to link.
    link_recipe = Variables.replace_variables(\
                  Patterns.fetch_pattern('recipe.c.combine.pattern').\
                  replace("{object_files}", ""))
    link_cmd = link_recipe.replace('\\\"', '\"')
    subprocess.check_call(link_cmd)

    # 

    hex_recipe = Variables.replace_variables(\
                 Patterns.fetch_pattern('recipe.objcopy.hex.pattern'))
    hex_cmd = hex_recipe.replace('\\\"', '\"')
    print hex_cmd
    subprocess.check_call(hex_cmd)

    upload_tool_var_name = board + ".upload.tool"
    upload_tool_name = Variables.fetch(upload_tool_var_name)
    upload_tool_path_name = "tools." + upload_tool_name + ".path"
    upload_tool_path = Variables.fetch(upload_tool_path_name)
    upload_tool_compiler_path_name = "tools." + upload_tool_name +\
                                     ".compiler.path"
    upload_tool_compiler_path = Variables.fetch(upload_tool_compiler_path_name)
    
    upload_tool_pattern_name = "tools." + upload_tool_name + ".upload.pattern"
    upload_tool_pattern = Patterns.fetch_pattern(upload_tool_pattern_name)
    print upload_tool_pattern
    
    return
        
# build_source_file_list() returns a list of strings, each of which is the full
#  absolute path to one file with the provided source extension. It walks down
#  the full path of base_path--be careful! If that tree is too big, it might
#  take a really long time!
def build_source_file_list(base_path, source_extension):
    source_list = []
    # slice_size is the size of the sliced off extension; we'll compare this
    #  many characters at the end of each file name to the source_extension.
    slice_size = -1 * len(source_extension)

    # This iterates over the entire directory tree rooted at base path.
    for dir in  os.walk(base_path):
        # For each file in this tree...
        for file in dir[2]:
            # ...check the slice_size characters at the end of the filename
            #  against the source_extension we passed in.
            if file[slice_size:] == source_extension:
                # if they match, append it to the list.
                source_list.append(os.path.join(dir[0],file).replace("\\","/"))
    return source_list

if __name__ == '__main__':
    main()

