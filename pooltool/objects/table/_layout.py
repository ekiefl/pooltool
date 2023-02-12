"""A place for horrible stuff to happen"""

from typing import Dict

import numpy as np

from pooltool.objects.table.components import (
    CircularCushionSegment,
    CushionDirection,
    CushionSegment,
    LinearCushionSegment,
    Pocket,
)


def _create_billiard_table_cushion_segments(
    specs,
) -> Dict[str, Dict[str, CushionSegment]]:
    h = specs.cushion_height
    cushion_segments = {
        "linear": {
            # long segments
            "3": LinearCushionSegment(
                "3_edge",
                p1=np.array((0, 0, h), dtype=np.float64),
                p2=np.array((0, specs.l, h), dtype=np.float64),
                direction=CushionDirection.SIDE2,
            ),
            "12": LinearCushionSegment(
                "12_edge",
                p1=np.array((specs.w, specs.l, h), dtype=np.float64),
                p2=np.array((specs.w, 0, h), dtype=np.float64),
                direction=CushionDirection.SIDE1,
            ),
            "9": LinearCushionSegment(
                "9_edge",
                p1=np.array((0, specs.l, h), dtype=np.float64),
                p2=np.array((specs.w, specs.l, h), dtype=np.float64),
                direction=CushionDirection.SIDE1,
            ),
            "18": LinearCushionSegment(
                "18_edge",
                p1=np.array((0, 0, h), dtype=np.float64),
                p2=np.array((specs.w, 0, h), dtype=np.float64),
                direction=CushionDirection.SIDE2,
            ),
        },
        "circular": {},
    }

    return cushion_segments  # type: ignore


def _create_pocket_table_cushion_segments(
    specs,
) -> Dict[str, Dict[str, CushionSegment]]:
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

    cushion_segments = {
        "linear": {
            # long segments
            "3": LinearCushionSegment(
                "3_edge",
                p1=np.array((0, pw * np.cos(np.pi / 4) + dc, h), dtype=np.float64),
                p2=np.array((0, (specs.l - sw) / 2 - ds, h), dtype=np.float64),
                direction=CushionDirection.SIDE2,
            ),
            "6": LinearCushionSegment(
                "6_edge",
                p1=np.array((0, (specs.l + sw) / 2 + ds, h), dtype=np.float64),
                p2=np.array(
                    (0, -pw * np.cos(np.pi / 4) + specs.l - dc, h), dtype=np.float64
                ),
                direction=CushionDirection.SIDE2,
            ),
            "15": LinearCushionSegment(
                "15_edge",
                p1=np.array(
                    (specs.w, pw * np.cos(np.pi / 4) + dc, h), dtype=np.float64
                ),
                p2=np.array((specs.w, (specs.l - sw) / 2 - ds, h), dtype=np.float64),
                direction=CushionDirection.SIDE1,
            ),
            "12": LinearCushionSegment(
                "12_edge",
                p1=np.array((specs.w, (specs.l + sw) / 2 + ds, h), dtype=np.float64),
                p2=np.array(
                    (specs.w, -pw * np.cos(np.pi / 4) + specs.l - dc, h),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "18": LinearCushionSegment(
                "18_edge",
                p1=np.array((pw * np.cos(np.pi / 4) + dc, 0, h), dtype=np.float64),
                p2=np.array(
                    (-pw * np.cos(np.pi / 4) + specs.w - dc, 0, h), dtype=np.float64
                ),
                direction=CushionDirection.SIDE2,
            ),
            "9": LinearCushionSegment(
                "9_edge",
                p1=np.array(
                    (pw * np.cos(np.pi / 4) + dc, specs.l, h), dtype=np.float64
                ),
                p2=np.array(
                    (-pw * np.cos(np.pi / 4) + specs.w - dc, specs.l, h),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE1,
            ),
            # side jaw segments
            "5": LinearCushionSegment(
                "5_edge",
                p1=np.array(
                    (-cw, (specs.l + sw) / 2 - cw * np.sin(sa), h), dtype=np.float64
                ),
                p2=np.array(
                    (-ds * np.cos(sa), (specs.l + sw) / 2 - ds * np.sin(sa), h),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "4": LinearCushionSegment(
                "4_edge",
                p1=np.array(
                    (-cw, (specs.l - sw) / 2 + cw * np.sin(sa), h), dtype=np.float64
                ),
                p2=np.array(
                    (-ds * np.cos(sa), (specs.l - sw) / 2 + ds * np.sin(sa), h),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE2,
            ),
            "13": LinearCushionSegment(
                "13_edge",
                p1=np.array(
                    (specs.w + cw, (specs.l + sw) / 2 - cw * np.sin(sa), h),
                    dtype=np.float64,
                ),
                p2=np.array(
                    (
                        specs.w + ds * np.cos(sa),
                        (specs.l + sw) / 2 - ds * np.sin(sa),
                        h,
                    ),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "14": LinearCushionSegment(
                "14_edge",
                p1=np.array(
                    (specs.w + cw, (specs.l - sw) / 2 + cw * np.sin(sa), h),
                    dtype=np.float64,
                ),
                p2=np.array(
                    (
                        specs.w + ds * np.cos(sa),
                        (specs.l - sw) / 2 + ds * np.sin(sa),
                        h,
                    ),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE2,
            ),
            # corner jaw segments
            "1": LinearCushionSegment(
                "1_edge",
                p1=np.array(
                    (pw * np.cos(np.pi / 4) - cw * np.tan(ca), -cw, h), dtype=np.float64
                ),
                p2=np.array(
                    (pw * np.cos(np.pi / 4) - dc * np.sin(ca), -dc * np.cos(ca), h),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE2,
            ),
            "2": LinearCushionSegment(
                "2_edge",
                p1=np.array(
                    (-cw, pw * np.cos(np.pi / 4) - cw * np.tan(ca), h), dtype=np.float64
                ),
                p2=np.array(
                    (-dc * np.cos(ca), pw * np.cos(np.pi / 4) - dc * np.sin(ca), h),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "8": LinearCushionSegment(
                "8_edge",
                p1=np.array(
                    (pw * np.cos(np.pi / 4) - cw * np.tan(ca), cw + specs.l, h),
                    dtype=np.float64,
                ),
                p2=np.array(
                    (
                        pw * np.cos(np.pi / 4) - dc * np.sin(ca),
                        specs.l + dc * np.cos(ca),
                        h,
                    ),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "7": LinearCushionSegment(
                "7_edge",
                p1=np.array(
                    (-cw, -pw * np.cos(np.pi / 4) + cw * np.tan(ca) + specs.l, h),
                    dtype=np.float64,
                ),
                p2=np.array(
                    (
                        -dc * np.cos(ca),
                        -pw * np.cos(np.pi / 4) + specs.l + dc * np.sin(ca),
                        h,
                    ),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE2,
            ),
            "11": LinearCushionSegment(
                "11_edge",
                p1=np.array(
                    (
                        cw + specs.w,
                        -pw * np.cos(np.pi / 4) + cw * np.tan(ca) + specs.l,
                        h,
                    ),
                    dtype=np.float64,
                ),
                p2=np.array(
                    (
                        specs.w + dc * np.cos(ca),
                        -pw * np.cos(np.pi / 4) + specs.l + dc * np.sin(ca),
                        h,
                    ),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE2,
            ),
            "10": LinearCushionSegment(
                "10_edge",
                p1=np.array(
                    (
                        -pw * np.cos(np.pi / 4) + cw * np.tan(ca) + specs.w,
                        cw + specs.l,
                        h,
                    ),
                    dtype=np.float64,
                ),
                p2=np.array(
                    (
                        -pw * np.cos(np.pi / 4) + specs.w + dc * np.sin(ca),
                        specs.l + dc * np.cos(ca),
                        h,
                    ),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "16": LinearCushionSegment(
                "16_edge",
                p1=np.array(
                    (cw + specs.w, +pw * np.cos(np.pi / 4) - cw * np.tan(ca), h),
                    dtype=np.float64,
                ),
                p2=np.array(
                    (
                        specs.w + dc * np.cos(ca),
                        pw * np.cos(np.pi / 4) - dc * np.sin(ca),
                        h,
                    ),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE1,
            ),
            "17": LinearCushionSegment(
                "17_edge",
                p1=np.array(
                    (-pw * np.cos(np.pi / 4) + cw * np.tan(ca) + specs.w, -cw, h),
                    dtype=np.float64,
                ),
                p2=np.array(
                    (
                        -pw * np.cos(np.pi / 4) + specs.w + dc * np.sin(ca),
                        -dc * np.cos(ca),
                        h,
                    ),
                    dtype=np.float64,
                ),
                direction=CushionDirection.SIDE2,
            ),
        },
        "circular": {
            "1t": CircularCushionSegment(
                "1t",
                center=np.array(
                    (pw * np.cos(np.pi / 4) + dc, -rc, h), dtype=np.float64
                ),
                radius=rc,
            ),
            "2t": CircularCushionSegment(
                "2t",
                center=np.array(
                    (-rc, pw * np.cos(np.pi / 4) + dc, h), dtype=np.float64
                ),
                radius=rc,
            ),
            "4t": CircularCushionSegment(
                "4t",
                center=np.array((-rs, specs.l / 2 - sw / 2 - ds, h), dtype=np.float64),
                radius=rs,
            ),
            "5t": CircularCushionSegment(
                "5t",
                center=np.array((-rs, specs.l / 2 + sw / 2 + ds, h), dtype=np.float64),
                radius=rs,
            ),
            "7t": CircularCushionSegment(
                "7t",
                center=np.array(
                    (-rc, specs.l - (pw * np.cos(np.pi / 4) + dc), h), dtype=np.float64
                ),
                radius=rc,
            ),
            "8t": CircularCushionSegment(
                "8t",
                center=np.array(
                    (pw * np.cos(np.pi / 4) + dc, specs.l + rc, h), dtype=np.float64
                ),
                radius=rc,
            ),
            "10t": CircularCushionSegment(
                "10t",
                center=np.array(
                    (specs.w - pw * np.cos(np.pi / 4) - dc, specs.l + rc, h),
                    dtype=np.float64,
                ),
                radius=rc,
            ),
            "11t": CircularCushionSegment(
                "11t",
                center=np.array(
                    (specs.w + rc, specs.l - (pw * np.cos(np.pi / 4) + dc), h),
                    dtype=np.float64,
                ),
                radius=rc,
            ),
            "13t": CircularCushionSegment(
                "13t",
                center=np.array(
                    (specs.w + rs, specs.l / 2 + sw / 2 + ds, h), dtype=np.float64
                ),
                radius=rs,
            ),
            "14t": CircularCushionSegment(
                "14t",
                center=np.array(
                    (specs.w + rs, specs.l / 2 - sw / 2 - ds, h), dtype=np.float64
                ),
                radius=rs,
            ),
            "16t": CircularCushionSegment(
                "16t",
                center=np.array(
                    (specs.w + rc, pw * np.cos(np.pi / 4) + dc, h), dtype=np.float64
                ),
                radius=rc,
            ),
            "17t": CircularCushionSegment(
                "17t",
                center=np.array(
                    (specs.w - pw * np.cos(np.pi / 4) - dc, -rc, h), dtype=np.float64
                ),
                radius=rc,
            ),
        },
    }

    return cushion_segments  # type: ignore


def _create_pocket_table_pockets(specs):
    pw = specs.corner_pocket_width
    cr = specs.corner_pocket_radius
    sr = specs.side_pocket_radius
    cd = specs.corner_pocket_depth
    sd = specs.side_pocket_depth

    cD = cr + cd - pw / 2
    sD = sr + sd

    pockets = {
        "lb": Pocket("lb", center=(-cD / np.sqrt(2), -cD / np.sqrt(2), 0), radius=cr),
        "lc": Pocket("lc", center=(-sD, specs.l / 2, 0), radius=sr),
        "lt": Pocket(
            "lt", center=(-cD / np.sqrt(2), specs.l + cD / np.sqrt(2), 0), radius=cr
        ),
        "rb": Pocket(
            "rb", center=(specs.w + cD / np.sqrt(2), -cD / np.sqrt(2), 0), radius=cr
        ),
        "rc": Pocket("rc", center=(specs.w + sD, specs.l / 2, 0), radius=sr),
        "rt": Pocket(
            "rt",
            center=(specs.w + cD / np.sqrt(2), specs.l + cD / np.sqrt(2), 0),
            radius=cr,
        ),
    }

    return pockets
