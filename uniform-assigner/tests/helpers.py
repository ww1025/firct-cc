# -*- coding: utf-8 -*-
"""测试用构造辅助。"""
from smart_alloc import schemas


def make_uniform(gender, size, n=1, prefix="U"):
    out = []
    for i in range(1, n + 1):
        out.append(schemas.new_equipment(
            equipment_id=f"{prefix}-{gender}{size.replace('/', '_')}-{i}",
            category="uniform", gender=gender, size_code=size,
            status="available", location=""))
    return out


def make_boots(size, n=1, prefix="B"):
    out = []
    for i in range(1, n + 1):
        out.append(schemas.new_equipment(
            equipment_id=f"{prefix}-{size}-{i}",
            category="boots", gender="", size_code=str(size),
            status="available", location=""))
    return out


def make_member(mid, name, gender="M", height=None, chest=None, foot=None,
                duty_class=None, status="new", prev_u=None, prev_b=None, resize=False):
    return schemas.new_member(
        member_id=mid, name=name, gender=gender, duty_class=duty_class,
        member_status=status, active_in_hq=True,
        height_cm=height, chest_cm=chest, foot_length_mm=foot,
        previous_uniform_id=prev_u, previous_boot_id=prev_b,
        request_resize=resize)
