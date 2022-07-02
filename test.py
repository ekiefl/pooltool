import simplepbr
from panda3d.core import *
from direct.showbase.ShowBase import ShowBase

loadPrcFileData('', 'gl-check-errors true')

class Demo(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        simplepbr.init()


demo = Demo()
demo.run()
