#!/bin/python

from platform_txt_loader import Platform_File_Parser
from boards_txt_loader import Boards_File_Parser
from arduino_sketch_fixer import Arduino_Sketch

Patterns = []

Platform_Variables = []
Build_Variables = []
Upload_Variables = []

C_Compiler_cmd = ""
CPP_Compiler_cmd = ""
S_Assembler_cmd = ""
Archiver_cmd = ""
Linker_cmd = ""
Elf_cmd = ""
EEPROM_cmd = ""
Hex_cmd = ""
Size_cmd = ""
Prebuild_cmd = ""
Postbuild_cmd = ""

vendor = "arduino"
platform = "Simblee"
board = "Simblee"
toolpath = "/cygdrive/c/Dropbox/Arduino/arduino-1.6.1"
sketch_path = "/cygdrive/c/Dropbox/Projects/Simblee/Safety_Glue/Safety_Glue.ino"

platform_path = toolpath + "/hardware/" + vendor + "/" + platform
platform_txt_file =  platform_path + "/platform.txt"
boards_txt_file = platform_path + "/boards.txt"

Simblee_Platform_Information = Platform_File_Parser(platform_txt_file, Platform_Variables, Patterns)

Simblee_Board_Information = Boards_File_Parser(boards_txt_file, board, Upload_Variables, Build_Variables)

Arduino_Sketch_Contents = Arduino_Sketch(sketch_path)

'''for item in Build_Variables:
  print item

for item in Upload_Variables:
  print item
'''

