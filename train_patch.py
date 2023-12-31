"""
Training code for Adversarial patch training


"""

import PIL
import load_data
from tqdm import tqdm

from load_data import *
import gc
import matplotlib.pyplot as plt
from torch import autograd
from torchvision import transforms
from tensorboardX import SummaryWriter
import subprocess

import patch_config
import sys
import time

import os
#patch trainer class
#takes patch config class as argument
class PatchTrainer(object):
    def __init__(self, mode):
        #get the patch config
        self.config = patch_config.patch_configs[mode]()
        #load the model
        self.yolo_model = YOLO(self.config.model_path)

        #patch helpers
        self.patch_applier = PatchApplier().cuda()
        self.patch_transformer = PatchTransformer().cuda()
        #self.prob_extractor = MaxProbExtractor(0, 80, self.config).cuda()
        self.prob_extractor = NewMaxProbExtractor(0).cuda()
        self.nps_calculator = NPSCalculator(self.config.printfile, self.config.patch_size).cuda()
        self.total_variation = TotalVariation().cuda()

        #tensorboard writer
        self.writer = self.init_tensorboard(mode)

    #init tensorboard writer
    def init_tensorboard(self, name=None):
        subprocess.Popen(['tensorboard', '--logdir=runs'])
        if name is not None:
            time_str = time.strftime("%Y%m%d-%H%M%S")
            return SummaryWriter(f'runs/{time_str}_{name}')
        else:
            return SummaryWriter()

    #patch training loop
    def train(self):
        """
        Optimize a patch to generate an adversarial example.
        :return: Nothing
        """

        #define image size, batch size, epochs, as well as max labels
        #note: max labels should ALWAYS be >= the actual max label count inside the data
        #img_size = self.darknet_model.height
        img_size = self.config.img_height
        batch_size = self.config.batch_size
        n_epochs = self.config.max_epochs
        max_labels  = self.config.max_labels

        time_str = time.strftime("%Y%m%d-%H%M%S")

        # Generate stating point
        # adv_patch_cpu = self.generate_patch("gray")
        adv_patch_cpu = self.generate_patch("random")
        #adv_patch_cpu = self.read_image("saved_patches/patchnew0.jpg")

        adv_patch_cpu.requires_grad_(True)
        #Loads the data set
        if self.config.data_type == "AIRBUS":
            train_loader = torch.utils.data.DataLoader(AirbusDataset(self.config.img_dir, self.config.lab_dir,max_labels,shuffle=True),batch_size=batch_size,shuffle=True,num_workers=10)
        elif self.config.data_type == "INRIA":
            train_loader = torch.utils.data.DataLoader(InriaDataset(self.config.img_dir, self.config.lab_dir,max_labels,img_size,shuffle=True),batch_size=batch_size,shuffle=True,num_workers=10)

        #print epoch length
        self.epoch_length = len(train_loader)
        print(f'One epoch is {len(train_loader)}')

        #define optimizer and scheduler
        optimizer = optim.Adam([adv_patch_cpu], lr=self.config.start_learning_rate, amsgrad=True)
        scheduler = self.config.scheduler_factory(optimizer)

        et0 = time.time()
        #main training loop
        for epoch in range(n_epochs):
            ep_det_loss = 0
            ep_nps_loss = 0
            ep_tv_loss = 0
            ep_loss = 0
            bt0 = time.time()
            #image batch loaded from dataset
            for i_batch, (img_batch, lab_batch) in tqdm(enumerate(train_loader), desc=f'Running epoch {epoch}',
                                                        total=self.epoch_length):
                with autograd.detect_anomaly():
                    img_batch = img_batch.cuda()
                    lab_batch = lab_batch.cuda()
                    #print('TRAINING EPOCH %i, BATCH %i'%(epoch, i_batch))
                    #define the patch, transform it, and apply it to the image batch
                    adv_patch = adv_patch_cpu.cuda()
                    adv_batch_t = self.patch_transformer(adv_patch, lab_batch, img_size, do_rotate=True, rand_loc=False)
                    p_img_batch = self.patch_applier(img_batch, adv_batch_t)
                    #scale the image batch to the proper size(darknet.model.height, darknet.model.width)
                    p_img_batch = F.interpolate(p_img_batch, (self.config.img_height, self.config.img_width))

                    #gets the image?
                    #probably unnecessary
                    img = p_img_batch[1, :, :,]
                    #img = transforms.ToPILImage()(img.detach().cpu())
                    #img.show()

                    #get output from patch
                    #calculate probabilities
                    #and define printability and smoothness
                    output = self.yolo_model(p_img_batch)

                    #get the max confidence loss
                    # for an image that has the patch applied
                    max_prob = self.prob_extractor(output)
                    det_loss = torch.tensor(0).cuda()
                    if max_prob:
                      max_prob = torch.cat(max_prob)
                      det_loss = torch.mean(max_prob)

                    nps = self.nps_calculator(adv_patch)
                    tv = self.total_variation(adv_patch)

                    #calculate loss
                    nps_loss = nps*self.config.nps_weight
                    tv_loss = tv*self.config.tv_weight
                    #det_loss = torch.mean(max_prob)
                    loss = det_loss + nps_loss + torch.max(tv_loss, torch.tensor(0.1).cuda())

                    ep_det_loss += det_loss.detach().cpu().numpy()
                    ep_nps_loss += nps_loss.detach().cpu().numpy()
                    ep_tv_loss += tv_loss.detach().cpu().numpy()
                    ep_loss += loss

                    #optimize the patch
                    loss.backward()
                    optimizer.step()
                    optimizer.zero_grad()
                    adv_patch_cpu.data.clamp_(0,1)       #keep patch in image range

                    bt1 = time.time()
                    if i_batch%5 == 0:
                        iteration = self.epoch_length * epoch + i_batch

                        #tensorboard output
                        self.writer.add_scalar('total_loss', loss.detach().cpu().numpy(), iteration)
                        self.writer.add_scalar('loss/det_loss', det_loss.detach().cpu().numpy(), iteration)
                        self.writer.add_scalar('loss/nps_loss', nps_loss.detach().cpu().numpy(), iteration)
                        self.writer.add_scalar('loss/tv_loss', tv_loss.detach().cpu().numpy(), iteration)
                        self.writer.add_scalar('misc/epoch', epoch, iteration)
                        self.writer.add_scalar('misc/learning_rate', optimizer.param_groups[0]["lr"], iteration)

                        self.writer.add_image('patch', adv_patch_cpu, iteration)
                        self.writer.add_image('applied_patch', img, iteration)
                    if i_batch + 1 >= len(train_loader):
                        print('\n')
                    else:
                        del adv_batch_t, output, max_prob, det_loss, p_img_batch, nps_loss, tv_loss, loss
                        torch.cuda.empty_cache()
                    bt0 = time.time()
            et1 = time.time()
            ep_det_loss = ep_det_loss/len(train_loader)
            ep_nps_loss = ep_nps_loss/len(train_loader)
            ep_tv_loss = ep_tv_loss/len(train_loader)
            ep_loss = ep_loss/len(train_loader)

            #im = transforms.ToPILImage('RGB')(adv_patch_cpu)
            #plt.imshow(im)
            #plt.savefig(f'pics/{time_str}_{self.config.patch_name}_{epoch}.png')

            scheduler.step(ep_loss)
            if True:
                print('  EPOCH NR: ', epoch),
                print('EPOCH LOSS: ', ep_loss)
                print('  DET LOSS: ', ep_det_loss)
                print('  NPS LOSS: ', ep_nps_loss)
                print('   TV LOSS: ', ep_tv_loss)
                print('EPOCH TIME: ', et1-et0)
                # uncommented (matthew)
                im = transforms.ToPILImage('RGB')(adv_patch_cpu)
                # plt.imshow(im)
                # plt.show()
                if not os.path.exists('saved_patches'):
                    os.makedirs('saved_patches') # create saved_patches folder in CWD
                im.save("saved_patches/patchnew1.jpg")
                del adv_batch_t, output, max_prob, det_loss, p_img_batch, nps_loss, tv_loss, loss
                torch.cuda.empty_cache()
            et0 = time.time()

    def generate_patch(self, type):
        """
        Generate a random patch as a starting point for optimization.

        :param type: Can be 'gray' or 'random'. Whether or not generate a gray or a random patch.
        :return:
        """
        if type == 'gray':
            adv_patch_cpu = torch.full((3, self.config.patch_size, self.config.patch_size), 0.5)
        elif type == 'random':
            adv_patch_cpu = torch.rand((3, self.config.patch_size, self.config.patch_size))

        return adv_patch_cpu

    def read_image(self, path):
        """
        Read an input image to be used as a patch

        :param path: Path to the image to be read.
        :return: Returns the transformed patch as a pytorch Tensor.
        """
        patch_img = Image.open(path).convert('RGB')
        tf = transforms.Resize((self.config.patch_size, self.config.patch_size))
        patch_img = tf(patch_img)
        tf = transforms.ToTensor()

        adv_patch_cpu = tf(patch_img)
        return adv_patch_cpu


def main():
    if len(sys.argv) != 2:
        print('You need to supply (only) a configuration mode.')
        print('Possible modes are:')
        print(patch_config.patch_configs)


    trainer = PatchTrainer(sys.argv[1])
    trainer.train()

if __name__ == '__main__':
    main()
