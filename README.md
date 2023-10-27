# Adversarial YOLO
This repository was originally based on the marvis YOLOv2 inplementation: https://github.com/marvis/pytorch-yolo2

This work corresponds to the following paper: https://arxiv.org/abs/1904.08653:
```
@inproceedings{thysvanranst2019,
    title={Fooling automated surveillance cameras: adversarial patches to attack person detection},
    author={Thys, Simen and Van Ranst, Wiebe and Goedem\'e, Toon},
    booktitle={CVPRW: Workshop on The Bright and Dark Sides of Computer Vision: Challenges and Opportunities for Privacy and Security},
    year={2019}
}
```

If you use this work, please cite this paper.

We at KSU have now adapted this repository to use YOLOv8 rather than YOLOv2 for the inference implementation

# What you need
We use Python 3.10.
Make sure that you have a working implementation of PyTorch installed, to do this see: https://pytorch.org/

This project has prerequisite packages that must be installed using pip before use:
```
pip install -r requirements.txt
```

No other installation for this project is necessary, you can simply run the python code straight from this directory.

(no longer used) original YOLOv2 model weights used on INRIA dataset
```
mkdir weights; curl https://pjreddie.com/media/files/yolov2.weights -o weights/yolo.weights
```

(no longer used) Get the INRIA dataset:
```
curl ftp://ftp.inrialpes.fr/pub/lear/douze/data/INRIAPerson.tar -o inria.tar
tar xf inria.tar
mv INRIAPerson inria
cp -r yolo-labels inria/Train/pos/
```

# Generating a patch
`patch_config.py` contains configuration of different experiments. You can design your own experiment by inheriting from the base `BaseConfig` class or an existing experiment. `ReproducePaperObj` reproduces the patch that minimizes object score from the paper (With a lower batch size to fit on a desktop GPU).

Here is a config for patch training on a small subset of satellite imagery of aircraft dataset:
```
python train_patch.py airbus-subset-8
```

Here is another config for patch training (not working currently):
```
python train_patch.py aircraft
```
