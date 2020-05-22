import cv2
import numpy as np

from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg


def setup_config():
    """
    Create configs and perform basic setups.
    """
    config_file = "COCO-Keypoints/keypoint_rcnn_R_50_FPN_3x.yaml"
    cfg = get_cfg()
    cfg.merge_from_file(
        model_zoo.get_config_file(config_file))
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7  # set threshold for this model
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(config_file)
    cfg.freeze()
    return cfg


def get_largest_centred_bounding_box(bboxes, orig_w, orig_h):
    """
    Given an array of bounding boxes, return the index of the largest + roughly-centred
    bounding box.
    :param bboxes: (N, 4) array of [x1 y1 x2 y2] bounding boxes
    :param orig_w: original image width
    :param orig_h: original image height
    """
    bboxes_area = (bboxes[:, 2] - bboxes[:, 0]) * (bboxes[:, 3] - bboxes[:, 1])
    sorted_bbox_indices = np.argsort(bboxes_area)[::-1]  # Indices of bboxes sorted by area.
    bbox_found = False
    i = 0
    while not bbox_found and i < sorted_bbox_indices.shape[0]:
        bbox_index = sorted_bbox_indices[i]
        bbox = bboxes[bbox_index]
        bbox_centre = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)  # Centre (width, height)
        if abs(bbox_centre[0] - orig_w / 2.0) < orig_w/6.0 and abs(bbox_centre[1] - orig_h / 2.0) < orig_w/6.0:
            largest_centred_bbox_index = bbox_index
            bbox_found = True
        i += 1

    # If can't find bbox sufficiently close to centre, just use biggest bbox as prediction
    if not bbox_found:
        largest_centred_bbox_index = sorted_bbox_indices[0]

    return largest_centred_bbox_index


def predict_joints2D(input_image):
    """
    Predicts 2D joints (17 2D joints in COCO convention along with prediction confidence)
    given a cropped and centred input image.
    :param input_images: (wh, wh)
    """
    cfg = setup_config()
    predictor = DefaultPredictor(cfg)

    image = np.copy(input_image)
    orig_h, orig_w = image.shape[:2]
    outputs = predictor(image)  # Multiple bboxes + keypoints predictions if there are multiple people in the image
    bboxes = outputs['instances'].pred_boxes.tensor.cpu().numpy()
    if bboxes.shape[0] == 0:  # Can't find any people in image
        keypoints = np.zeros((17, 3))
    else:
        largest_centred_bbox_index = get_largest_centred_bounding_box(bboxes, orig_w, orig_h)  # Picks out centred person that is largest in the image.
        keypoints = outputs['instances'].pred_keypoints.cpu().numpy()
        keypoints = keypoints[largest_centred_bbox_index]

        for j in range(keypoints.shape[0]):
            cv2.circle(image, (keypoints[j, 0], keypoints[j, 1]), 5, (0, 255, 0), -1)
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 0.5
            fontColor = (0, 0, 255)
            cv2.putText(image, str(j), (keypoints[j, 0], keypoints[j, 1]),
                                     font, fontScale, fontColor, lineType=2)

    return keypoints, image
