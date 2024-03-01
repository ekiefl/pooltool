"""A place for horrible stuff to happen"""

from typing import Dict, Union

import numpy as np
from numpy.typing import NDArray

from pooltool.objects.table.components import (
    CircularCushionSegment,
    CushionDirection,
    CushionSegments,
    LinearCushionSegment,
    Pocket,
)
from pooltool.objects.table.specs import (
    BilliardTableSpecs,
    PocketTableSpecs,
    SnookerTableSpecs,
)


def _arr(*args) -> NDArray[np.float64]:
    return np.array(args, dtype=np.float64)


def create_billiard_table_cushion_segments(
    specs: BilliardTableSpecs,
) -> CushionSegments:
    h = specs.cushion_height
    return CushionSegments(
        linear={
            # long segments
            "3": LinearCushionSegment(
                "3",
                p1=_arr(0, 0, h),
                p2=_arr(0, specs.l, h),
                direction=CushionDirection.SIDE2,
            ),
            "12": LinearCushionSegment(
                "12",
                p1=_arr(specs.w, specs.l, h),
                p2=_arr(specs.w, 0, h),
                direction=CushionDirection.SIDE1,
            ),
            "9": LinearCushionSegment(
                "9",
                p1=_arr(0, specs.l, h),
                p2=_arr(specs.w, specs.l, h),
                direction=CushionDirection.SIDE1,
            ),
            "18": LinearCushionSegment(
                "18",
                p1=_arr(0, 0, h),
                p2=_arr(specs.w, 0, h),
                direction=CushionDirection.SIDE2,
            ),
        },
        circular={},
    )


def create_pocket_table_cushion_segments(
    specs: Union[PocketTableSpecs, SnookerTableSpecs],
) -> CushionSegments:
    # https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-cushion-collision-times
    # for diagram
    cw = specs.cushion_width
    ca = (specs.corner_pocket_angle + 45) * np.pi / 180
    sa = specs.side_pocket_angle * np.pi / 180
    pw = specs.corner_pocket_width
    sw = specs.side_pocket_width
    h = specs.cushion_height
    rc = specs.corner_jaw_radius
    rs = specs.side_jaw_radius
    dc = specs.corner_jaw_radius / np.tan((np.pi / 2 + ca) / 2)
    ds = specs.side_jaw_radius / np.tan((np.pi / 2 + sa) / 2)

    return CushionSegments(
        linear={
            # long segments
            "3": LinearCushionSegment(
                "3",
                p1=_arr(0, pw * np.cos(np.pi / 4) + dc, h),
                p2=_arr(0, (specs.l - sw) / 2 - ds, h),
                direction=CushionDirection.SIDE2,
            ),
            "6": LinearCushionSegment(
                "6",
                p1=_arr(0, (specs.l + sw) / 2 + ds, h),
                p2=_arr(0, -pw * np.cos(np.pi / 4) + specs.l - dc, h),
                direction=CushionDirection.SIDE2,
            ),
            "15": LinearCushionSegment(
                "15",
                p1=_arr(specs.w, pw * np.cos(np.pi / 4) + dc, h),
                p2=_arr(specs.w, (specs.l - sw) / 2 - ds, h),
                direction=CushionDirection.SIDE1,
            ),
            "12": LinearCushionSegment(
                "12",
                p1=_arr(specs.w, (specs.l + sw) / 2 + ds, h),
                p2=_arr(specs.w, -pw * np.cos(np.pi / 4) + specs.l - dc, h),
                direction=CushionDirection.SIDE1,
            ),
            "18": LinearCushionSegment(
                "18",
                p1=_arr(pw * np.cos(np.pi / 4) + dc, 0, h),
                p2=_arr(-pw * np.cos(np.pi / 4) + specs.w - dc, 0, h),
                direction=CushionDirection.SIDE2,
            ),
            "9": LinearCushionSegment(
                "9",
                p1=_arr(pw * np.cos(np.pi / 4) + dc, specs.l, h),
                p2=_arr(-pw * np.cos(np.pi / 4) + specs.w - dc, specs.l, h),
                direction=CushionDirection.SIDE1,
            ),
            # side jaw segments
            "5": LinearCushionSegment(
                "5",
                p1=_arr(-cw, (specs.l + sw) / 2 - cw * np.sin(sa), h),
                p2=_arr(-ds * np.cos(sa), (specs.l + sw) / 2 - ds * np.sin(sa), h),
                direction=CushionDirection.SIDE1,
            ),
            "4": LinearCushionSegment(
                "4",
                p1=_arr(-cw, (specs.l - sw) / 2 + cw * np.sin(sa), h),
                p2=_arr(-ds * np.cos(sa), (specs.l - sw) / 2 + ds * np.sin(sa), h),
                direction=CushionDirection.SIDE2,
            ),
            "13": LinearCushionSegment(
                "13",
                p1=_arr(specs.w + cw, (specs.l + sw) / 2 - cw * np.sin(sa), h),
                p2=_arr(
                    specs.w + ds * np.cos(sa),
                    (specs.l + sw) / 2 - ds * np.sin(sa),
                    h,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "14": LinearCushionSegment(
                "14",
                p1=_arr(specs.w + cw, (specs.l - sw) / 2 + cw * np.sin(sa), h),
                p2=_arr(
                    specs.w + ds * np.cos(sa),
                    (specs.l - sw) / 2 + ds * np.sin(sa),
                    h,
                ),
                direction=CushionDirection.SIDE2,
            ),
            # corner jaw segments
            "1": LinearCushionSegment(
                "1",
                p1=_arr(pw * np.cos(np.pi / 4) - cw * np.tan(ca), -cw, h),
                p2=_arr(pw * np.cos(np.pi / 4) - dc * np.sin(ca), -dc * np.cos(ca), h),
                direction=CushionDirection.SIDE2,
            ),
            "2": LinearCushionSegment(
                "2",
                p1=_arr(-cw, pw * np.cos(np.pi / 4) - cw * np.tan(ca), h),
                p2=_arr(-dc * np.cos(ca), pw * np.cos(np.pi / 4) - dc * np.sin(ca), h),
                direction=CushionDirection.SIDE1,
            ),
            "8": LinearCushionSegment(
                "8",
                p1=_arr(pw * np.cos(np.pi / 4) - cw * np.tan(ca), cw + specs.l, h),
                p2=_arr(
                    pw * np.cos(np.pi / 4) - dc * np.sin(ca),
                    specs.l + dc * np.cos(ca),
                    h,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "7": LinearCushionSegment(
                "7",
                p1=_arr(-cw, -pw * np.cos(np.pi / 4) + cw * np.tan(ca) + specs.l, h),
                p2=_arr(
                    -dc * np.cos(ca),
                    -pw * np.cos(np.pi / 4) + specs.l + dc * np.sin(ca),
                    h,
                ),
                direction=CushionDirection.SIDE2,
            ),
            "11": LinearCushionSegment(
                "11",
                p1=_arr(
                    cw + specs.w,
                    -pw * np.cos(np.pi / 4) + cw * np.tan(ca) + specs.l,
                    h,
                ),
                p2=_arr(
                    specs.w + dc * np.cos(ca),
                    -pw * np.cos(np.pi / 4) + specs.l + dc * np.sin(ca),
                    h,
                ),
                direction=CushionDirection.SIDE2,
            ),
            "10": LinearCushionSegment(
                "10",
                p1=_arr(
                    -pw * np.cos(np.pi / 4) + cw * np.tan(ca) + specs.w,
                    cw + specs.l,
                    h,
                ),
                p2=_arr(
                    -pw * np.cos(np.pi / 4) + specs.w + dc * np.sin(ca),
                    specs.l + dc * np.cos(ca),
                    h,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "16": LinearCushionSegment(
                "16",
                p1=_arr(cw + specs.w, +pw * np.cos(np.pi / 4) - cw * np.tan(ca), h),
                p2=_arr(
                    specs.w + dc * np.cos(ca),
                    pw * np.cos(np.pi / 4) - dc * np.sin(ca),
                    h,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "17": LinearCushionSegment(
                "17",
                p1=_arr(-pw * np.cos(np.pi / 4) + cw * np.tan(ca) + specs.w, -cw, h),
                p2=_arr(
                    -pw * np.cos(np.pi / 4) + specs.w + dc * np.sin(ca),
                    -dc * np.cos(ca),
                    h,
                ),
                direction=CushionDirection.SIDE2,
            ),
        },
        circular={
            "1t": CircularCushionSegment(
                "1t",
                center=_arr(pw * np.cos(np.pi / 4) + dc, -rc, h),
                radius=rc,
            ),
            "2t": CircularCushionSegment(
                "2t",
                center=_arr(-rc, pw * np.cos(np.pi / 4) + dc, h),
                radius=rc,
            ),
            "4t": CircularCushionSegment(
                "4t",
                center=_arr(-rs, specs.l / 2 - sw / 2 - ds, h),
                radius=rs,
            ),
            "5t": CircularCushionSegment(
                "5t",
                center=_arr(-rs, specs.l / 2 + sw / 2 + ds, h),
                radius=rs,
            ),
            "7t": CircularCushionSegment(
                "7t",
                center=_arr(-rc, specs.l - (pw * np.cos(np.pi / 4) + dc), h),
                radius=rc,
            ),
            "8t": CircularCushionSegment(
                "8t",
                center=_arr(pw * np.cos(np.pi / 4) + dc, specs.l + rc, h),
                radius=rc,
            ),
            "10t": CircularCushionSegment(
                "10t",
                center=_arr(specs.w - pw * np.cos(np.pi / 4) - dc, specs.l + rc, h),
                radius=rc,
            ),
            "11t": CircularCushionSegment(
                "11t",
                center=_arr(specs.w + rc, specs.l - (pw * np.cos(np.pi / 4) + dc), h),
                radius=rc,
            ),
            "13t": CircularCushionSegment(
                "13t",
                center=_arr(specs.w + rs, specs.l / 2 + sw / 2 + ds, h),
                radius=rs,
            ),
            "14t": CircularCushionSegment(
                "14t",
                center=_arr(specs.w + rs, specs.l / 2 - sw / 2 - ds, h),
                radius=rs,
            ),
            "16t": CircularCushionSegment(
                "16t",
                center=_arr(specs.w + rc, pw * np.cos(np.pi / 4) + dc, h),
                radius=rc,
            ),
            "17t": CircularCushionSegment(
                "17t",
                center=_arr(specs.w - pw * np.cos(np.pi / 4) - dc, -rc, h),
                radius=rc,
            ),
        },
    )


def create_pocket_table_pockets(
    specs: Union[PocketTableSpecs, SnookerTableSpecs],
) -> Dict[str, Pocket]:
    cr = specs.corner_pocket_radius
    sr = specs.side_pocket_radius
    cd = specs.corner_pocket_depth
    sd = specs.side_pocket_depth

    # When corner_pocket_depth is 0, the center of the pocket should be at the cushion
    # intersection. As corner_pocket_depth increases, the pocket center moves diagonally
    # outwards. The corner pocket radius does not affect the initial position of the
    # pocket center
    cD = cd / np.sqrt(2)

    # For side pockets, the center position is simply moved out by the side_pocket_depth
    sD = sd

    pockets = {
        "lb": Pocket("lb", center=_arr(-cD, -cD, 0), radius=cr),
        "lc": Pocket("lc", center=_arr(-sD, specs.l / 2, 0), radius=sr),
        "lt": Pocket("lt", center=_arr(-cD, specs.l + cD, 0), radius=cr),
        "rb": Pocket("rb", center=_arr(specs.w + cD, -cD, 0), radius=cr),
        "rc": Pocket("rc", center=_arr(specs.w + sD, specs.l / 2, 0), radius=sr),
        "rt": Pocket(
            "rt",
            center=_arr(specs.w + cD, specs.l + cD, 0),
            radius=cr,
        ),
    }

    return pockets
