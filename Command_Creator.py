#!/bin/python
import os.path
import subprocess
import shlex
import re

class Cmd_Builder:

    def __init__(self):
        pass

    def remove_duplicate_args(self): 
        if self.cmd_arg_list:
            seen_items = set()
            return [x for x in self.cmd_arg_list\
                    if not (x in seen_items or seen_items.add(x))]

    def fetch_out_file(self):
        return self.out_file

    def fetch_cmd_pattern(self):
        return self.cmd_arg_list

    def fetch_cmd(self):
        if self.cmd_arg_list:
            return " ".join(self.cmd_arg_list)
        else:
            return None

class Obj_Builder(Cmd_Builder):

    def __init__(self, build_path, source_file, build_cmd_pattern):
        self.obj_file = build_path + "/" +\
                source_file.rsplit("/",1)[1] + '.o'

        if ((os.path.exists(self.obj_file) == False) or
           (os.path.exists(self.obj_file) and
           (os.path.getmtime(source_file) > os.path.getmtime(self.obj_file)))):
            self.cmd_arg_list = shlex.split(build_cmd_pattern.\
                    replace('{source_file}', source_file).\
                    replace('{object_file}', self.obj_file))
        else:
            self.cmd_arg_list = None

class Archive_Builder(Cmd_Builder):

    def __init__(self, build_path, source_file, build_cmd_pattern):
        self.obj_file = build_path + "/" +\
                source_file.rsplit("/",1)[1] + '.o'

        if ((os.path.exists(self.obj_file) == False) or
           (os.path.exists(self.obj_file) and
           (os.path.getmtime(source_file) > os.path.getmtime(self.obj_file)))):
            self.cmd_arg_list = shlex.split(build_cmd_pattern.\
                    replace('{source_file}', source_file).\
                    replace('{object_file}', self.obj_file))
        else:
            self.cmd_arg_list = None
