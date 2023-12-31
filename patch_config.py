from torch import optim


class BaseConfig(object):
    """
    Default parameters for all config files.
    """

    def __init__(self):
        """
        Set the defaults.
        """
        self.data_type = "INRIA"
        self.img_dir = "inria/Train/pos"
        self.lab_dir = "inria/Train/pos/yolo-labels"
        self.cfgfile = "cfg/yolo.cfg"
        self.weightfile = "weights/yolo.weights"
        self.printfile = "non_printability/30values.txt"
        #Convenience Additions
        self.img_height = 512
        self.img_width = 512
        self.model_path = 'best.pt'
        self.nps_weight = 0.01
        self.tv_weight = 2.5
        self.patch_size = 300
        # self.max_epochs = 10000
        self.max_epochs = 500000
        self.max_labels = 20

        self.start_learning_rate = 0.03

        self.patch_name = 'base'

        self.scheduler_factory = lambda x: optim.lr_scheduler.ReduceLROnPlateau(x, 'min', patience=50)
        self.max_tv = 0

        self.batch_size = 16

        self.loss_target = lambda obj, cls: obj * cls


class Experiment1(BaseConfig):
    """
    Model that uses a maximum total variation, tv cannot go below this point.
    """

    def __init__(self):
        """
        Change stuff...
        """
        super().__init__()

        self.patch_name = 'Experiment1'
        self.max_tv = 0.165


class Experiment2HighRes(Experiment1):
    """
    Higher res
    """

    def __init__(self):
        """
        Change stuff...
        """
        super().__init__()

        self.max_tv = 0.165
        self.patch_size = 400
        self.patch_name = 'Exp2HighRes'

class Experiment3LowRes(Experiment1):
    """
    Lower res
    """

    def __init__(self):
        """
        Change stuff...
        """
        super().__init__()

        self.max_tv = 0.165
        self.patch_size = 100
        self.patch_name = "Exp3LowRes"

class Experiment4ClassOnly(Experiment1):
    """
    Only minimise class score.
    """

    def __init__(self):
        """
        Change stuff...
        """
        super().__init__()

        self.patch_name = 'Experiment4ClassOnly'
        self.loss_target = lambda obj, cls: cls




class Experiment1Desktop(Experiment1):
    """
    """

    def __init__(self):
        """
        Change batch size.
        """
        super().__init__()

        self.batch_size = 16
        self.patch_size = 400


class ReproducePaperObj(BaseConfig):
    """
    Reproduce the results from the paper: Generate a patch that minimises object score.
    """

    def __init__(self):
        super().__init__()

        #self.batch_size = 8 # original batch size
        self.batch_size = 16 # batch size of 8 takes about 5Gb of VRAM, 16 should take about 10Gb
        self.patch_size = 300

        self.patch_name = 'ObjectOnlyPaper'
        self.max_tv = 0.165

        self.loss_target = lambda obj, cls: obj

class AirbusFull(BaseConfig):
    def __init__(self):
        super().__init__()
        self.batch_size = 12 # bs 12 for 12 Gb GPU VRAM, yours may vary
        self.patch_size = 300
        self.data_type = "AIRBUS"
        self.img_dir='airbusdata/train/images'
        self.lab_dir='airbusdata/train/labels'
        self.start_learning_rate = 0.045 # scale this linearly with bs

class AirbusEight(BaseConfig):
    def __init__(self):
        super().__init__()
        self.batch_size = 12 # bs 12 for 12 Gb GPU VRAM, yours may vary
        self.patch_size = 300
        self.data_type = "AIRBUS"
        self.img_dir='airbus-subset-8/images'
        self.lab_dir='airbus-subset-8/labels'
        self.start_learning_rate = 0.045 # scale this linearly with bs

patch_configs = {
    "base": BaseConfig,
    "exp1": Experiment1,
    "exp1_des": Experiment1Desktop,
    "exp2_high_res": Experiment2HighRes,
    "exp3_low_res": Experiment3LowRes,
    "exp4_class_only": Experiment4ClassOnly,
    "paper_obj": ReproducePaperObj,
    "aircraft": AirbusFull,
    "airbus-subset-8": AirbusEight
}
