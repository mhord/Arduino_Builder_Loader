#!/bin/python
import os.path
import os
import sys
import itertools
import subprocess
import shlex
from platform import system
from time import sleep

import Variable_Loader
import Sketch_to_Cpp
from Command_Creator import Obj_Builder

# Deriving values for these settings: 
#  "sketch_path" is the location of the main .ino file of this project.
sketch_path = "c:/Dropbox/Projects/Simblee/Safety_Glue"

serial_port = "COM28"

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

    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    # We'll need the sketch name, at times, to do stuff, and we can identify that
    #  from the sketch path.
    sketch_name = os.path.basename(sketch_path) + ".ino"

    build_system_path = runtime_platform_path + "/system"
    platform_txt_file =  runtime_platform_path + "/platform.txt"
    boards_txt_file = runtime_platform_path + "/boards.txt"
    archive_filename = "core.a"

    # We may need to create a folder to store all of our temporary files in. We
    #  don't want to pollute our sketch folder with that crap.
    if not os.path.exists(sketch_path + "/build"):
        os.makedirs(sketch_path + "/build")

    print "Retrieving variables from platform.txt and boards.txt..."

    # We need to retrieve from the boards.txt and platform.txt files a bunch of
    #  information. They contain all we need to know to build and upload our
    #  sketch.
    Variables = Variable_Loader.Variable_Manager(boards_txt_file, board)
    Variables.parse_file(platform_txt_file)
    Patterns  = Variable_Loader.Pattern_Manager(platform_txt_file)

    print "Initializing variables..."

    # These are things that are normally provided by the IDE.
    Variables.add_variable(["serial.port", serial_port])
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

    print "Converting .ino files to .cpp..."

    # Here's the part where we convert the .ino files into a .cpp file. We
    # concatenate the ino files, magic up some function declarations, and then
    # return a list of likely library includes (according to Arduino standards).
    # Note that library includes are expected to all be above everything that is
    # not a comment or preproc statement; that's kinda dumb but it *does* make
    # turning a #include into a path to find a library easier.
    Sketch_Info = Sketch_to_Cpp.Sketch(sketch_path + "/" +  sketch_name)
    library_includes = Sketch_Info.fetch_include_file_list()
    sketch_cpp_filename_list = Sketch_Info.fetch_sketch_cpp_files()

    print "Assembling include file path list..."

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

    # include_path_list has a nice list of paths, but gcc doesn't *want* a list
    #  of paths. It wants each path formatted like this:
    #  -I"/path/to/include/files"
    #  That's a problem, because Python is going to want to strip out those
    #  quotes when printing those strings. So, we make a string, with escaped
    #  quotation marks (to protect against the shell stripping them away) and
    #  store THAT as the includes variable instead.
    includes = ""
    for path in include_path_list:
        includes = includes + R'\"-I' + path + R'\" '
    Variables.add_variable(["includes",includes])

    print "Creating build commands..."

    # We now know everything we need to build our sketch into a hex file. Let's
    #  create our build commands. 
    c_file_build = Patterns.fetch_pattern("recipe.c.o.pattern")
    cpp_file_build = Patterns.fetch_pattern("recipe.cpp.o.pattern")
    s_file_build = Patterns.fetch_pattern("recipe.S.o.pattern")

    # It's possible that one or more of those patterns may not exist, so check
    # before attempting to build on it.
    if c_file_build:
        c_build_recipe = Variables.replace_variables(c_file_build)
    else:
        c_build_recipe = None
    if cpp_file_build:
        cpp_build_recipe = Variables.replace_variables(cpp_file_build)
    else:
        cpp_build_recipe = None
    if s_file_build:
        s_build_recipe = Variables.replace_variables(s_file_build)
    else:
        s_build_recipe = None

    print "Aggregating source file list..."

    # Here's the crappy part: we have to identify *all* the various files that must
    # be built into object files and, if they've changed since the last change time
    # on the corresponding .o file, delete the .o file and rebuild them.
    # There are *so many* places they could be: in the sketch folder or the build
    # subdirectory thereof, in any of the library folders we included, in the
    # appropriate core directory, maybe even the variants subfolder or any of its
    # subfolders!

    # These files are all the "core" files. They're located anywhere *but* the
    #  sketch directory. We make the distinction because, in normal operation,
    #  these are unlikely to change, so we can *probably* skip rebuilding them
    #  most of the time and just link the "core.a" file that already exists.
    potential_core_cpp_file_list = []
    core_c_file_list = []
    core_s_file_list = []

    # First up, find all the files we need and then make a list of each one.
    for path in include_path_list:
        core_c_file_list.extend(build_source_file_list(path, '.c'))
        potential_core_cpp_file_list.extend(build_source_file_list(path, '.cpp'))
        core_s_file_list.extend(build_source_file_list(path, '.s'))
        core_s_file_list.extend(build_source_file_list(path, '.S'))

    core_cpp_file_list = []
    sketch_cpp_file_list = []

    # We need to iterate over our core_cpp_file_list and remove anything that
    #  exists as a source file for the sketch. This is any CPP file in the 
    #  Sketch_Name folder, as well as sketch_name.cpp
    for cpp_file in potential_core_cpp_file_list:
        is_sketch_file = False
        for sketch_cpp_file in sketch_cpp_filename_list:
            if sketch_cpp_file in cpp_file:
                sketch_cpp_file_list.append(cpp_file)
                is_sketch_file = True
                break
        if is_sketch_file:
            continue
        core_cpp_file_list.append(cpp_file)

    core_builder_list = []
    sketch_builder_list = []
    core_object_file_list = []
    sketch_object_file_list = []

    # For each file in each of these file lists, we're going to check and see
    #  if the .o file exists, and, if it does, whether the modification time
    #  on the file is newer or older than the source file. If the file doesn't
    #  need to be updated, we'll get a None appended to the list. If it *does*
    #  need to be updated, we'll get an Obj_Builder instance on the list that
    #  can be used later to build that source file.
    for source_file in core_cpp_file_list:
        core_builder_list.append(Obj_Builder(build_path, source_file,
                                       cpp_build_recipe))

    for source_file in core_c_file_list:
        core_builder_list.append(Obj_Builder(build_path, source_file,
                                       c_build_recipe))

    for source_file in core_s_file_list:
        core_builder_list.append(Obj_Builder(build_path, source_file,
                                       s_build_recipe))

    for source_file in sketch_cpp_file_list:
        sketch_builder_list.append(Obj_Builder(build_path, source_file,
                                       cpp_build_recipe))
            
    # At least once, I've seen a recipe in a platforms.txt file that has a
    #  hardcoded parameter in it which collides with an automatically
    #  generated parameter. Apparently, the Arduino IDE can cope with this,
    #  so we must, too.
    for command in itertools.chain(core_builder_list, sketch_builder_list):
        command.remove_duplicate_args()

    print "Building object files..."

    # We're going to assume, because it's usually the case, that the core.a
    #  file is going to be valid after the build step. We won't actually do a
    #  build on a file if the source isn't newer than the existing object file.
    core_archive_valid = True

    # This is where the actual builds occur. We want to make sure that we build
    #  the absolute minimum number of files, because it takes a couple of
    #  seconds to build each one, and we want to cut that down as far as
    #  possible. To that end, if we make it through the core_builder_list
    #  without having to rebuild a single item, we'll leave the
    #  core_archive_valid flag True so we don't rebuild the core archive later.
    for builder_item in core_builder_list:
        builder_cmd = builder_item.fetch_cmd()
        if builder_cmd:
            core_archive_valid = False
            core_object_file_list.append(builder_item.fetch_out_file())
            subprocess.check_call(builder_cmd)

    for builder_item in sketch_builder_list:
        builder_cmd = builder_item.fetch_cmd()
        if builder_cmd:
            sketch_object_file_list.append(builder_item.fetch_out_file())
            subprocess.check_call(builder_cmd)

    print "Placing core files into archive..."

    # Must put all core object files into an archive file; we can do that
    #  incrementally, but not linking. We can't just directly link the files
    #  because the line length of all the object files would be way too long
    #  for most operating systems to manage.
    if os.path.exists(os.path.join(build_path, archive_filename)):
        if core_archive_valid == False:    
            os.remove(os.path.join(build_path, archive_filename))
        archive_recipe = Variables.replace_variables(\
                         Patterns.fetch_pattern('recipe.ar.pattern'))
        for obj in core_object_file_list:
            ar_cmd = archive_recipe.replace('{object_file}', obj).replace('\\\"', '\"')
            subprocess.check_call(ar_cmd) 
            # This pause allows your antivirus program to stop snuffling around
            #  the archive file before re-invoking gcc-ar. 100ms wasn't enough
            #  on my machine, but 150 seems to work okay. I *know* this isn't a
            #  good solution but I don't have a better one: I can't lock the
            #  file in python because gcc-ar is spawned as a different process,
            #  I can't check to see if the file is locked, because it could be
            #  locked after I check it but before I start gcc-ar. Grrr.
            sleep(0.150)

    print "Linking files..."

    # Time to link. By and large, the recipe contains most of the stuff that
    #  needs to get linked, either in the form of pre-built archive files, the
    #  archive file we just finished, or something else. However, any object
    #  files created from .ino or .cpp files in the sketch folder won't be on
    #  the list, so we need to make them into a string (out of the
    #  sketch_object_file_list list) and then sub them in for the
    #  {object_files} variable in the link recipe.

    sketch_object_file_string = ''
    for obj_file in sketch_object_file_list:
        sketch_object_file_string += R'\"' + obj_file + R'\" '

    Variables.add_variable(["object_files", sketch_object_file_string]) 
    link_recipe = Variables.replace_variables(\
                  Patterns.fetch_pattern('recipe.c.combine.pattern'))
    link_cmd = link_recipe.replace('\\\"', '\"')
    subprocess.check_call(link_cmd)

     
    print "Creating hex file..."

    hex_recipe = Variables.replace_variables(\
                 Patterns.fetch_pattern('recipe.objcopy.hex.pattern'))
    hex_cmd = hex_recipe.replace('\\\"', '\"')
    subprocess.check_call(hex_cmd)

    print "Uploading..."
    upload_tool_var_name = "upload.tool"
    upload_tool_name = Variables.fetch_variable(upload_tool_var_name)
    upload_tool_prefix = "tools." + upload_tool_name
    upload_tool_path_name = upload_tool_prefix + ".path"
    upload_tool_path = Variables.fetch_variable(upload_tool_path_name)
    system_os = system().lower()

    script_name = ""
    cmd_name = ""

    if "windows" in system_os:
        script_name = Variables.fetch_variable(upload_tool_prefix
                                               +".script.windows")
        cmd_name = Variables.fetch_variable(upload_tool_prefix + ".cmd.windows")
    elif "mac" in system_os:
        script_name = Variables.fetch_variable(upload_tool_prefix
                                               +".script")
        cmd_name = Variables.fetch_variable(upload_tool_prefix + ".cmd.macosx")
    elif "linux" in system_os:
        script_name = Variables.fetch_variable(upload_tool_prefix
                                               +".script")
        cmd_name = Variables.fetch_variable(upload_tool_prefix + ".cmd.linux")

    Variables.add_variable(["cmd", cmd_name])
    Variables.add_variable(["script", script_name])
    upload_tool_pattern_name = "tools." + upload_tool_name + ".upload.pattern"
    upload_tool_pattern = Patterns.fetch_pattern(upload_tool_pattern_name)
    tool_path = upload_tool_prefix + ".path"
    Variables.add_variable(["path", Variables.fetch_variable(tool_path)])
    upload_tool_cmd = Variables.replace_variables(upload_tool_pattern).replace('\\\"', '\"')
    if system_os == "windows":
        upload_tool_cmd = "cmd /c \"" + upload_tool_cmd + "\""
    upload_tool_cmd_shlex = shlex.split(upload_tool_cmd)
    subprocess.check_call(upload_tool_cmd_shlex)
    
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

