import imp
import os
from abc import ABCMeta, abstractmethod

#module-root dictionary of postprocessors
postprocessors = {}
class ABCPostProcRegister(ABCMeta):
    #handles postprocessors registration on instantation
    def __new__(cls, clsname, bases, attrs):
        newclass = super(ABCPostProcRegister, cls).__new__(cls, clsname, bases, attrs)
        if object not in bases:
            postprocessors[newclass.__name__] = newclass()  # here is your register function
        return newclass

class FlatCAMPostProc(object):
    __metaclass__ = ABCPostProcRegister

    @abstractmethod
    def start_code(self, p):
        pass

    @abstractmethod
    def lift_code(self, p):
        pass

    @abstractmethod
    def down_code(self, p):
        pass

    @abstractmethod
    def toolchange_code(self, p):
        pass

    @abstractmethod
    def up_to_zero_code(self, p):
        pass

    @abstractmethod
    def rapid_code(self, p):
        pass

    @abstractmethod
    def linear_code(self, p):
        pass

    @abstractmethod
    def end_code(self, p):
        pass

    @abstractmethod
    def feedrate_code(self, p):
        pass

    @abstractmethod
    def spindle_code(self,p):
        pass

    @abstractmethod
    def spindle_stop_code(self,p):
        pass



from postprocessors import default


def load_postprocessors(app):
    postprocessors_path_search = os.path.join(app.data_path,'postprocessors','*.py')
    import glob
    for file in glob.glob(postprocessors_path_search):
        try:
            imp.load_source('FlatCAMPostProcessor',file)
        except Exception,e:
            app.log.error(str(e))
    return postprocessors
