from typing import List, Tuple, Union
import cv2

import matplotlib.pyplot as plt

import numpy as np

from kd_splicing.location.models import Location
from kd_splicing import database
from kd_common import logutil, geometry
from kd_splicing.database.models import Isoform

_logger = logutil.get_logger(__name__)

Color = Union[int, Tuple[int, ...]]

def draw_filled_ring(img: np.ndarray, points: List[geometry.Point], color: Tuple[int, ...]) -> None:
    pts = []
    for p in points:
        pts.append(p.to_cv())
    pts = np.array(pts)
    cv2.fillPoly(img, [pts], color, cv2.LINE_8)


def draw_bounding_box(img: np.ndarray, bb: geometry.Box, background: Color, color: Color, thickness: int = 1) -> None:
    points = [
        geometry.Point.construct(x = bb.min_x, y = bb.min_y),
        geometry.Point.construct(x = bb.min_x, y = bb.max_y),
        geometry.Point.construct(x = bb.max_x, y = bb.max_y),
        geometry.Point.construct(x = bb.max_x, y = bb.min_y),
    ]
    draw_filled_ring(img, points, background)
    cv2.rectangle(img, bb.min_point().to_cv(), bb.max_point().to_cv(), color, thickness, cv2.LINE_8)


def draw_boxes(img: np.ndarray, boxes: List[geometry.Box], background: Color, color: Color, thickness: int = 1) -> None:
    for box in boxes:
        draw_bounding_box(img, box, background, color, thickness)

def convert_to_bounding_boxes(location: Location, height: int, y_start: int, tm: geometry.TransformationMatrix) -> List[geometry.Box]:
    result = []
    for loc in location.parts: 
        result.append(geometry.Box.construct(
            min_x = loc.start,
            min_y = y_start,
            max_x = loc.end,
            max_y = y_start + height,
        ) * tm)
    return result

def draw_isoforms(db: database.models.DB, protein_ids_str: str) -> np.ndarray:
    protein_ids = [protein_id.strip()
                   for protein_id in protein_ids_str.split(",")]
    
    if len(protein_ids) != 2:
        _logger.exception("Must be two protein ids 'protein_id1, protein_id2'")
    if protein_ids[0] not in db.protein_id_to_isoform:
        _logger.exception(f"Can't find protein id '{protein_ids[0]}'")
    if protein_ids[1] not in db.protein_id_to_isoform:
        _logger.exception(f"Can't find protein id '{protein_ids[1]}'")

    iso0 = db.isoforms[db.protein_id_to_isoform[protein_ids[0]]]
    rna0 = db.rnas.get(iso0.rna_uuid)
    rna0_location = rna0.location if rna0 else None
    iso1 = db.isoforms[db.protein_id_to_isoform[protein_ids[1]]]
    rna1 = db.rnas.get(iso1.rna_uuid)
    rna1_location = rna1.location if rna1 else None

    loc_height = 50
    img_width = 4000
    x_padding = 100
    loc_width = img_width - 2 * x_padding
    img_height = loc_height * 5
    min_x = 1000000000
    max_x = -1
    for loc in [iso0.location, rna0_location, iso1.location, rna1_location]:
        if loc is None: continue
        for p in loc.parts:
            min_x = min(min_x, p.start)
            min_x = min(min_x, p.end)
            max_x = max(max_x, p.start)
            max_x = max(max_x, p.end)

    tm = geometry.tm_translate(
        dx= - min_x,
        dy= 0,
    ) * geometry.scale_transform(
        from_width=max_x - min_x,
        from_height=1,
        to_width=loc_width,
        to_height=1,
    ) * geometry.tm_translate(
        dx= x_padding,
        dy= 0,
    ) 
    if iso0.location.parts[0].strand == -1:
        tm = tm  * geometry.tm_flip_horizontal(
            ) * geometry.tm_translate(
            dx= 2 * x_padding + loc_width,
            dy= 0,
        )

    img = np.zeros((img_height, img_width, 3))
    print(img.shape, img_height, img_width)
    img[:, :, :] = 255

    iso_boxes0 = convert_to_bounding_boxes(iso0.location, loc_height, loc_height, tm)
    iso_boxes1 = convert_to_bounding_boxes(iso1.location, loc_height, 3 * loc_height, tm)

    if rna0_location: 
        rna_boxes0 = convert_to_bounding_boxes(rna0_location, loc_height, loc_height, tm)
        draw_boxes(img, rna_boxes0, [200, 200, 200], [0, 0, 0], 2)
    if rna1_location: 
        rna_boxes1 = convert_to_bounding_boxes(rna1_location, loc_height, 3 * loc_height, tm)
        draw_boxes(img, rna_boxes1, [200, 200, 200], [0, 0, 0], 2)
    draw_boxes(img, iso_boxes0, [255, 0, 0], [0, 0, 0], 2)
    draw_boxes(img, iso_boxes1, [255, 0, 0], [0, 0, 0], 2)
    img = img.astype(int)
    
    visualize(img=img)
    return img

def visualize(**images):
    n = len(images)
    plt.figure(figsize=(30, 20))
    for i, (name, image) in enumerate(images.items()):
        if len(image.shape) == 3 and image.shape[2] == 2:
            image = np.concatenate((image, np.zeros((image.shape[0], image.shape[1], 1))), axis=2)
        plt.subplot(1, n, i + 1)
        plt.xticks([])
        plt.yticks([])
        plt.title(' '.join(name.split('_')).title())
        plt.imshow(image)
    plt.show()