#! /usr/bin/env python

import pooltool.terminal as terminal

class PlayerCam(object):
    def __init__(self):
        self.node = base.camera
        self.lens = base.camLens
        self.lens.setNear(0.02)

        self.states = {}
        self.last_state = None
        self.has_focus = False


    def create_focus(self, parent=None, pos=None):
        if parent is None:
            parent = render

        self.focus = parent.attachNewNode("camera_focus")
        self.focus.setH(-90)

        # create visible object
        self.focus_object = loader.loadModel('smiley.egg')
        self.focus_object.setScale(0.0002)
        self.focus_object.setH(-90) # Smiley faces away from camera ways
        self.focus.setR(-10) # Move 'head' up so you're not staring at the butt of the cue
        self.focus_object.setColor(1,0,0,1)
        self.focus_object.reparentTo(self.focus)

        if pos is not None:
            self.focus.setPos(*pos)

        self.node.reparentTo(self.focus)
        self.node.setPos(2, 0, 0)
        self.node.lookAt(self.focus)

        self.has_focus = True


    def update_focus(self, pos):
        self.focus.setPos(pos)


    def get_state(self):
        return {
            'CamHpr': self.node.getHpr(),
            'CamPos': self.node.getPos(),
            'FocusHpr': self.focus.getHpr() if self.has_focus else None,
            'FocusPos': self.focus.getPos() if self.has_focus else None,
        }


    def store_state(self, name, overwrite=False):
        if name in self.states:
            if overwrite:
                self.remove_state(name)
            else:
                raise Exception(f"PlayerCam :: '{name}' is already a camera state")

        self.states[name] = self.get_state()
        self.last_state = name


    def load_state(self, name, ok_if_not_exists=False):
        if name not in self.states:
            if ok_if_not_exists:
                return
            else:
                raise Exception(f"PlayerCam :: '{name}' is not a camera state")

        self.node.setPos(self.states[name]['CamPos'])
        self.node.setHpr(self.states[name]['CamHpr'])

        if self.has_focus:
            self.focus.setPos(self.states[name]['FocusPos'])
            self.focus.setHpr(self.states[name]['FocusHpr'])


    def load_last(self, ok_if_not_exists=False):
        """Loads the last state that was stored"""
        self.load_state(self.last_state, ok_if_not_exists=ok_if_not_exists)


    def remove_state(self, name):
        del self.states[name]


    def has_state(self, name):
        return True if name in self.states else False


