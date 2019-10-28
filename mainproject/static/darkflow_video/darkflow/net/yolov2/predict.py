import numpy as np
import math
import cv2
import os
import json

# from scipy.special import expit
# from utils.box import BoundBox, box_iou, prob_compare
# from utils.box import prob_compare2, box_intersection
from ...utils.box import BoundBox
from ...cython_utils.cy_yolo2_findboxes import box_constructor


# count_f = 0

def expit(x):
    return 1. / (1. + np.exp(-x))


def _softmax(x):
    e_x = np.exp(x - np.max(x))
    out = e_x / e_x.sum()
    return out


def findboxes(self, net_out):
    # meta
    meta = self.meta
    boxes = list()
    boxes = box_constructor(meta, net_out)
    return boxes


def postprocess(self, net_out, im, save=True):
    """
    Takes net output, draw net_out, save to disk
    """

    boxes = self.findboxes(net_out)
    count = 0  # 人群计数

    # meta
    meta = self.meta
    threshold = meta['thresh']
    colors = meta['colors']
    labels = meta['labels']
    if type(im) is not np.ndarray:
        imgcv = cv2.imread(im)
    else:
        imgcv = im
    h, w, _ = imgcv.shape

    resultsForJSON = []
    for b in boxes:
        boxResults = self.process_box(b, h, w, threshold)
        if boxResults is None:
            continue
        left, right, top, bot, mess, max_indx, confidence = boxResults
        thick = int((h + w) // 300)
        if self.FLAGS.json:
            resultsForJSON.append(
                {"label": mess, "confidence": float('%.2f' % confidence), "topleft": {"x": left, "y": top},
                 "bottomright": {"x": right, "y": bot}})

            continue
        # print(mess)
        if mess == 'person':
            count = count + 1
            cv2.rectangle(imgcv, (left, top), (right, bot), colors[max_indx], thick)
            cv2.putText(imgcv, mess, (left, top - 12), 0, 1e-3 * h, colors[max_indx], thick // 3)
    # cv2.putText(imgcv, 'number of people  ' + str(count), (70, 70), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 3)

    # cv2.namedWindow('result', 0)
    # cv2.imshow('result', imgcv)
    # cv2.waitKey(2)
    # count = 0

    # cv2.destroyAllWindows()
    # print(count)

    if not save: return imgcv, count

    outfolder = os.path.join(self.FLAGS.imgdir, 'out')
    img_name = os.path.join(outfolder, os.path.basename(im))

    if self.FLAGS.json:
        textJSON = json.dumps(resultsForJSON)
        textFile = os.path.splitext(img_name)[0] + ".json"
        with open(textFile, 'w') as f:
            f.write(textJSON)
        return
    cv2.imwrite(img_name, imgcv)
