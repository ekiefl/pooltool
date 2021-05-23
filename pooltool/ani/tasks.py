#! /usr/bin/env python

import pooltool.utils as utils

class Tasks(object):
    frame = 0

    def monitor(self, task):
        print(f"Mode: {self.mode}")
        print(f"Tasks: {list(self.tasks.keys())}")
        print(f"Memory: {utils.get_total_memory_usage()}")
        print(f"Actions: {[k for k in self.keymap if self.keymap[k]]}")
        print(f"Keymap: {self.keymap}")
        print(f"Frame: {self.frame}")
        print()
        self.frame += 1

        return task.cont



