from __future__ import annotations

import math

from typing import Tuple, List, Union

from pydantic import BaseModel, Field

import numpy as np

class Point(BaseModel):
    x: float
    y: float

    def __mul__(self, r: TransformationMatrix) -> Point:
        return Point(
            x=self.x * r.a + self.y * r.c + r.e,
            y=self.x * r.b + self.y * r.d + r.f
        )

    def __truediv__(self, other: float) -> Point:
        return Point.construct(x=self.x / other, y = self.y / other)

    def __add__(self, other: Point) -> Point:
        return Point.construct(
            x=self.x + other.x,
            y = self.y + other.y,
        )
    
    def __sub__(self, other: Point) -> Point:
        return Point.construct(
            x=self.x - other.x,
            y = self.y - other.y,
        )

    def to_cv(self) -> Tuple[int, int]:
        return (int(self.x), int(self.y))

    def __lt__(self, other: Point) -> bool:
        if self.x < other.x:
            return True
        if self.x == other.x and self.y < other.y:
            return True
        return False

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def angle(self) -> float:
        return (180 * math.atan2(self.y, self.x)) / math.pi


def intersect_line_segments(a_left: float, a_right: float, b_left: float, b_right: float) -> Tuple[float, float]:
    left = max(a_left, b_left)
    right = min(a_right, b_right)
    return (left, right) if left <= right else (0, 0)


class Segment(BaseModel):
    a: Point
    b: Point

    def length(self) -> float:
        return math.sqrt((self.b.x - self.a.x) ** 2 + (self.b.y - self.a.y) ** 2)


class Box(BaseModel):
    min_x: Union[int, float]
    min_y: Union[int, float]
    max_x: Union[int, float]
    max_y: Union[int, float]

    def __contains__(self, other: Box) -> bool:
        return self.min_x <= other.min_x and other.min_x <= self.max_x \
        and self.min_x <= other.max_x and other.max_x <= self.max_x \
        and self.min_y <= other.max_y and other.max_y <= self.max_y \
        and self.min_y <= other.min_y and other.min_y <= self.max_y 

    def as_int(self) -> Box:
        return Box.construct(
            min_x=int(self.min_x),
            min_y=int(self.min_y),
            max_x=int(self.max_x),
            max_y=int(self.max_y),
        )

    def width(self) -> float:
        return self.max_x - self.min_x

    def height(self) -> float:
        return self.max_y - self.min_y

    def largest_side(self) -> float:
        return max(self.width(), self.height())

    def min_point(self) -> Point:
        return Point.construct(
            x=self.min_x,
            y=self.min_y,
        )

    def max_point(self) -> Point:
        return Point.construct(
            x=self.max_x,
            y=self.max_y,
        )

    def center(self) -> Point:
        return Point.construct(
            x = (self.min_x + self.max_x) / 2,
            y = (self.min_y + self.max_y) / 2,
        )

    def extract_from(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 2:
            return img[max(0, int(self.min_y)): int(self.max_y), max(0, int(self.min_x)): int(self.max_x)]
        return img[max(0, int(self.min_y)): int(self.max_y), max(0, int(self.min_x)): int(self.max_x), :]

    @staticmethod
    def from_array(box: np.ndarray) -> Box:
        return Box.construct(
            min_x=box[0],
            min_y=box[1],
            max_x=box[2],
            max_y=box[3],
        )
    @staticmethod
    def from_cv_array(bb: np.ndarray) -> Box:
        return Box.construct(
            min_x=bb[0],
            min_y=bb[1],
            max_x=bb[0] + bb[2],
            max_y=bb[1] + bb[3],
        )

    def to_array(self) -> np.ndarray:
        return np.array([int(self.min_x), int(self.min_y), int(self.max_x), int(self.max_y)])

    # def to_array(self) -> np.array:
    #     return np.array([int(self.min_y), int(self.min_x), int(self.max_y), int(self.max_x)])

    def area(self) -> float:
        return (self.max_x - self.min_x) * (self.max_y - self.min_y)

    def intersect(self, other: Box) -> Box:
        min_x, max_x = intersect_line_segments(
            self.min_x, self.max_x, other.min_x, other.max_x)
        min_y, max_y = intersect_line_segments(
            self.min_y, self.max_y, other.min_y, other.max_y)
        box = Box.construct(
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y,
        )
        return box if box.area() > 0 else EMPTY_BOX

    def intersection_over_union(self, other: Box) -> float:
        intersection = self.intersect(other)
        union_area = self.area() + other.area() - intersection.area()
        if union_area < 1e-9:
            return 0
        return intersection.area() / float(union_area)

    def intersection_over_self_area(self, other: Box) -> float:
        intersection = self.intersect(other)
        area = self.area()
        if area < 1e-9:
            return 0
        return intersection.area() / float(area)

    def __mul__(self, tm: TransformationMatrix) -> Box:
        a = Point.construct(x=self.min_x, y=self.min_y) * tm
        b = Point.construct(x=self.max_x, y=self.max_y) * tm
        return Box.construct(
            min_x=min(a.x, b.x),
            min_y=min(a.y, b.y),
            max_x=max(a.x, b.x),
            max_y=max(a.y, b.y),
        )

    def extend_relative(self, relative_increase: float) -> Box:
        w = self.width()
        h = self.height()
        dx = (w * relative_increase) / 2
        dy = (h * relative_increase) / 2
        return self.extend(dx, dy)

    def extend_at_least(self, min_width: float, min_height: float) -> Box:
        return self.extend(
            dx=max(0, min_width - self.width()) / 2,
            dy=max(0, min_height - self.height()) / 2,
        )

    def extend(self, dx: float = 0, dy: float = 0) -> Box:
        return Box(
            min_x=self.min_x - dx,
            min_y=self.min_y - dy,
            max_x=self.max_x + dx,
            max_y=self.max_y + dy
        )

    def clip(self, shape: np.ndarray) -> Box:
        return Box(
            min_x=max(self.min_x, 0),
            min_y=max(self.min_y, 0),
            max_x=min(self.max_x, shape[1]),
            max_y=min(self.max_y, shape[0]),
        )

    def make_square(self) -> Box:
        if self.width() < self.height():
            return self.extend(dx=(self.height() - self.width()) / 2)
        return self.extend(dy=(self.width() - self.height()) / 2)


def points_bounding_box(points: List[Point]) -> Box:
    return Ring.construct(points=points).bounding_box()

class Ring(BaseModel):
    points: List[Point] = Field(default_factory=list)

    def __mul__(self, tm: TransformationMatrix) -> Ring:
        ring = Ring.construct(points=[])
        for point in self.points:
            ring.points.append(point * tm)
        return ring

    def segments(self) -> List[Segment]:
        i = 0
        j = len(self.points) - 1
        result = []
        while i < len(self.points):
            result.append(Segment.construct(
                a=self.points[j],
                b=self.points[i]
            ))
            j = i
            i += 1
        return result

    def bounding_box(self) -> Box:
        if not self.points:
            return Box.construct(min_x=0, min_y=0, max_x=0, max_y=0)
        min_x = self.points[0].x
        min_y = self.points[0].y
        max_x = self.points[0].x
        max_y = self.points[0].y
        for p in self.points[1:]:
            min_x = min(min_x, p.x)
            min_y = min(min_y, p.y)
            max_x = max(max_x, p.x)
            max_y = max(max_y, p.y)
        return Box.construct(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)

    def perimeter(self) -> float:
        return sum(s.length() for s in self.segments())

    def signed_area(self) -> float:
        result = 0.0
        for s in self.segments():
            result += (s.a.x + s.b.x) * (s.b.y - s.a.y)
        return result / 2

    def area(self) -> float:
        return abs(self.signed_area())


class Polygon(BaseModel):
    exterior: Ring = Field(default_factory=Ring)
    interior: List[Ring] = Field(default_factory=list)


class TransformationMatrix(BaseModel):
    a: float = 1
    b: float = 0
    c: float = 0
    d: float = 1
    e: float = 0
    f: float = 0

    def __mul__(self, other: TransformationMatrix) -> TransformationMatrix:
        return TransformationMatrix.construct(
            a=self.a * other.a + self.b * other.c,
            b=self.a * other.b + self.b * other.d,
            c=self.c * other.a + self.d * other.c,
            d=self.c * other.b + self.d * other.d,
            e=self.e * other.a + self.f * other.c + other.e,
            f=self.e * other.b + self.f * other.d + other.f,
        )

    def inverse(self) -> TransformationMatrix:
        det = self.a * self.d - self.b * self.c
        return TransformationMatrix.construct(
            a=self.d / det,
            b=-self.b / det,
            c=-self.c / det,
            d=self.a / det,
            e=(self.c * self.f - self.d * self.e) / det,
            f=(self.b * self.e - self.a * self.f) / det,
        )


def vector_length(x: float, y: float) -> float:
    return math.sqrt(x**2 + y**2)


def tm_rotate(x: float, y: float) -> TransformationMatrix:
    length = vector_length(x, y)
    cos = x / length
    sin = y / length
    return TransformationMatrix.construct(
        a=cos,
        b=-sin,
        c=sin,
        d=cos,
        e=0,
        f=0,
    )

def rm_rotate_angle_degrees(angle: float) -> TransformationMatrix:
    angle = (angle * math.pi) / 180
    return TransformationMatrix.construct(
        a=math.cos(angle),
        b=-math.sin(angle),
        c=math.sin(angle),
        d=math.cos(angle),
        e=0,
        f=0,
    )


def tm_translate(dx: float, dy: float) -> TransformationMatrix:
    return TransformationMatrix.construct(
        a=1,
        b=0,
        c=0,
        d=1,
        e=dx,
        f=dy,
    )


def tm_scale(x_scale: float, y_scale: float) -> TransformationMatrix:
    return TransformationMatrix.construct(
        a=x_scale,
        b=0,
        c=0,
        d=y_scale,
        e=0,
        f=0
    )


def tm_flip_vertical() -> TransformationMatrix:
    return TransformationMatrix.construct(
        a=1,
        b=0,
        c=0,
        d=-1,
        e=0,
        f=0
    )


def tm_flip_horizontal() -> TransformationMatrix:
    return TransformationMatrix.construct(a=-1, b=0, c=0, d=1, e=0, f=0)


def tm_box(from_box: Box, to_box: Box) -> TransformationMatrix:
    return tm_translate(
        dx= - from_box.min_x,
        dy= - from_box.min_y,
    ) * scale_transform(
        from_width=from_box.width(),
        from_height=from_box.height(),
        to_width=to_box.width(),
        to_height=to_box.height(),
    ) * tm_translate(
        dx= to_box.min_x,
        dy= to_box.min_y,
    )


def scale_transform(from_width: float, from_height: float, to_width: float, to_height: float) -> TransformationMatrix:
    return tm_scale(to_width / float(from_width), to_height / float(from_height))


EMPTY_BOX = Box.construct(min_x=0, min_y=0, max_x=0, max_y=0)


_INSIDE = 0
_LEFT = 1
_RIGHT = 2
_BOTTOM = 4
_TOP = 8

def _compute_out_code(x: float, y: float, r: np.ndarray) -> int:
    code = _INSIDE         

    if x < r[0]:           # to the left of clip window
        code |= _LEFT
    elif x > r[2]:      # to the right of clip window
        code |= _RIGHT
    if y < r[1]:           # below the clip window
        code |= _BOTTOM
    elif y > r[3]:      # above the clip window
        code |= _TOP

    return code


def cohen_sutherland_line_clip(s: np.ndarray, r: np.ndarray) -> Tuple[np.ndarray, bool]:
    outcode0 = _compute_out_code(s[0], s[1], r)
    outcode1 = _compute_out_code(s[2], s[3], r)
    x0, y0, x1, y1 = s
    xmin, ymin, xmax, ymax = r

    accept = False

    while True:
        if not (outcode0 | outcode1):
            # bitwise OR is 0: both points inside window trivially accept and exit loop
            accept = True
            break
        elif outcode0 & outcode1:
            # bitwise AND is not 0: both points share an outside zone (LEFT, RIGHT, TOP,
            # or BOTTOM), so both must be outside window exit loop (accept is false)
            break
        else:
            # failed both tests, so calculate the line segment to clip
            # from an outside point to an intersection with clip edge
            x = 0
            y = 0

            # At least one endpoint is outside the clip rectangle pick it.
            out_code_out = outcode1 if outcode1 > outcode0 else outcode0


            # Now find the intersection point
            # use formulas:
            #   slope = (y1 - y0) / (x1 - x0)
            #   x = x0 + (1 / slope) * (ym - y0), where ym is ymin or ymax
            #   y = y0 + slope * (xm - x0), where xm is xmin or xmax
            # No need to worry about divide-by-zero because, in each case, the
            # outcode bit being tested guarantees the denominator is non-zero
            if out_code_out & _TOP:            # point is above the clip window
                x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
                y = ymax
            elif out_code_out & _BOTTOM:  # point is below the clip window
                x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
                y = ymin
            elif out_code_out & _RIGHT:   # point is to the right of clip window
                y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
                x = xmax
            elif out_code_out & _LEFT:    # point is to the left of clip window
                y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
                x = xmin
            

            # Now we move outside point to intersection point to clip
            # and get ready for next pass.
            if out_code_out == outcode0:
                x0 = x
                y0 = y
                outcode0 = _compute_out_code(x0, y0, r)
            else:
                x1 = x
                y1 = y
                outcode1 = _compute_out_code(x1, y1, r)

    return np.array([x0, y0, x1, y1]), accept
            
        
def length(x0: float, y0: float, x1: float, y1: float) -> float:
    return math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)

def angle_to_radians(angle: float) -> float:
    return (angle * math.pi) / 180