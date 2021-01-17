#! /usr/bin/env python

import psim.utils as utils
import psim.ani.action as action

import sys

class Tasks(object):
    def menu_task(self, task):
        if self.keymap[action.exit]:
            sys.exit()

        return task.cont


    def should_quit_task(self, task):
        if self.keymap[action.quit]:
            self.keymap[action.quit] = False
            self.close_scene()
            self.change_mode('menu')

        return task.cont


    def aim_task(self, task):
        self.update_camera()

        return task.cont


    def monitor(self, task):
        print(f"Tasks: {list(self.tasks.keys())}")
        print(f"Memory: {utils.get_total_memory_usage()}")
        print(f"Actions: {[k for k in self.keymap if self.keymap[k]]}")
        print()

        return task.cont



