# -*- coding: utf-8 -*-
import numpy as np
from model import netG
# from gen_test import netG
# from high_extra import high_extra
from sporco.util import tikhonov_filter
import scipy.misc
import time
import os
import glob
import cv2
import torch

def imread(path, is_grayscale=True):
    """
    Read image using its path.
    Default value is gray-scale, and image is read by YCbCr format as the paper said.
    """

    if is_grayscale:
        # 将图像转换为灰度图
        return scipy.misc.imread(path, flatten=True, mode='YCbCr').astype(np.float)
    else:
        return scipy.misc.imread(path, mode='YCbCr').astype(np.float)

def imsave(image, path):
    return scipy.misc.imsave(path, image)

def prepare_data(dataset):
    data_dir = os.path.join(os.sep, (os.path.join(os.getcwd(), dataset)))
    data = glob.glob(os.path.join(data_dir, "*.jpg"))
    data.extend(glob.glob(os.path.join(data_dir, "*.bmp")))
    data.sort(key=lambda x: int(x[len(data_dir)+1:-4]))
    return data

# 分解得到图像的低频和高频区域
# 通过滤波将图像分解为低频图像和高频图像
def decomp_combine_image(ir_image, vi_image):
    # 转换为float类型 .astype(np.float)
    ir_low, ir_high = tikhonov_filter((ir_image-127.5)/127.5, 5, 16)
    vi_low, vi_high = tikhonov_filter((vi_image-127.5)/127.5, 5, 16)

    # 对红外和可见光图像的高频区域进行融合
    combine_high = ir_high
    row, col = ir_high.shape
    for m in range(row):
        for n in range(col):
            if abs(ir_high[m][n]) > abs(vi_high[m][n]):
                combine_high[m][n] = ir_high[m][n]
            else:
                combine_high[m][n] = vi_high[m][n]

    combine_low = (ir_low + vi_low) / 2
    combine_average = (ir_image + vi_image) /2

    return combine_low

def input_setup(index):

    ir_image = imread(data_ir[index], True)
    vi_image = imread(data_vi[index], True)
    # cv2.imshow('ir_image', ir_image.astype(np.uint8))
    # cv2.imshow('vi_image', vi_image.astype(np.uint8))
    # cv2.waitKey(0)

    combine_low = decomp_combine_image(ir_image, vi_image)
    input_ir = (ir_image-127.5)/127.5  # 将该幅图像的数据归一化
    input_vi = (vi_image-127.5)/127.5

    # 扩充输入数据的维度
    train_data_ir = np.expand_dims(input_ir, axis=0)
    train_data_vi = np.expand_dims(input_vi, axis=0)
    train_data_ir = np.expand_dims(train_data_ir, axis=3)
    train_data_vi = np.expand_dims(train_data_vi, axis=3)
    return train_data_ir, train_data_vi, combine_low

# 加载模型参数进行图像融合测试
fusion_model = netG().cuda().eval()
# print(fusion_model)
# discriminator = netD().cuda()
ep = 4
model_path = os.path.join(os.getcwd(), 'weight', 'epoch' + str(ep))
netG_path = os.path.join(model_path, 'netG.pth')
# netD_path = os.path.join(model_path, 'netD.pth')
fusion_model.load_state_dict(torch.load(netG_path))
# discriminator.load_state_dict(torch.load(netD_path))
data_ir = prepare_data('Test_ir')
data_vi = prepare_data('Test_vi')
for i in range(0, len(data_ir)):
    start = time.time()
    train_data_ir, train_data_vi, combine_low = input_setup(i)
    # 去掉尺寸为1的维度，得到可处理的图像数据
    # from_numpy得到的是DoubleTensor类型的，需要转成FloatTensor
    train_data_ir = torch.FloatTensor(train_data_ir)
    train_data_vi = torch.FloatTensor(train_data_vi)
    input_image = torch.cat((train_data_ir, train_data_vi), -1)
    # input_image = (train_data_ir + train_data_vi)/2.0
    input_image = input_image.permute(0, 3, 1, 2)
    input_image = torch.autograd.Variable(input_image.cuda(), volatile=True)

    # # 防止显存溢出
    # try:
    #     result_low = fusion_model(input_image)
    # except RuntimeError as exception:
    #     if "out of memory" in str(exception):
    #         print("WARNING: out of memory")
    #         if hasattr(torch.cuda, 'empty_cache'):
    #             torch.cuda.empty_cache()
    #     else:
    #         raise exception

    result_high = fusion_model(input_image)
    result = fusion_model.fusion_res
    result = result * 127.5 + 127.5
    result_high = result_high * 127.5 + 127.5
    # 将生成的variable数据转成numpy类型
    # 查看生成的图片以及低频、高频区域
    result = result.squeeze().cpu().detach().numpy()
    result_high = result_high.squeeze().cpu().detach().numpy()
    image_path = os.path.join(os.getcwd(), 'result_0504', 'epoch' + str(ep))
    if not os.path.exists(image_path):
        os.makedirs(image_path)
    if i <= 9:
        result_path = os.path.join(image_path, 'result_0'+str(i)+".bmp")
    else:
        result_path = os.path.join(image_path, 'result_'+str(i)+".bmp")
    end = time.time()
    # print(out.shape)
    imsave(result.astype(np.uint8), result_path)
    imsave(result_high.astype(np.uint8), reshigh_path)
    print("Testing [%d] success, Testing time is [%f]" % (i, end-start))
