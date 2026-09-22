# -*- coding: utf-8 -*-
"""独立冲突复核器测试。"""
from smart_alloc import schemas, conflict_checker


def _alloc(mid, uid, bid):
    return schemas.new_allocation(member_id=mid, uniform_id=uid, boot_id=bid)


def _member(mid, name, duty_class=None):
    return schemas.new_member(member_id=mid, name=name, gender="M",
                              duty_class=duty_class, member_status="new",
                              active_in_hq=True)


def _eq(eid, category, status="available", size_code=""):
    return schemas.new_equipment(equipment_id=eid, category=category,
                                 size_code=size_code, status=status)


def test_three_share_detected():
    members = [_member("M1", "A"), _member("M2", "B"), _member("M3", "C")]
    allocs = [_alloc("M1", "U1", "B1"), _alloc("M2", "U1", "B2"), _alloc("M3", "U1", "B3")]
    equipment = [_eq("U1", "uniform"), _eq("B1", "boots"), _eq("B2", "boots"), _eq("B3", "boots")]
    _, summary = conflict_checker.check(allocs, members, equipment, [])
    assert summary["三人共用"] >= 1


def test_same_class_detected():
    members = [_member("M1", "A", "周一"), _member("M2", "B", "周一")]
    allocs = [_alloc("M1", "U1", "B1"), _alloc("M2", "U1", "B2")]
    equipment = [_eq("U1", "uniform"), _eq("B1", "boots"), _eq("B2", "boots")]
    _, summary = conflict_checker.check(allocs, members, equipment, [])
    assert summary["同班共用"] >= 1


def test_damaged_used():
    members = [_member("M1", "A")]
    allocs = [_alloc("M1", "U1", "B1")]
    equipment = [_eq("U1", "uniform", status="damaged"), _eq("B1", "boots")]
    _, summary = conflict_checker.check(allocs, members, equipment, [])
    assert summary["损坏装备"] >= 1


def test_no_equipment():
    members = [_member("M1", "A")]
    allocs = []
    equipment = []
    _, summary = conflict_checker.check(allocs, members, equipment, [])
    assert summary["无装备"] >= 1


def test_clean_allocation_passes():
    members = [_member("M1", "A", "周一"), _member("M2", "B", "周二")]
    allocs = [_alloc("M1", "U1", "B1"), _alloc("M2", "U2", "B2")]
    equipment = [_eq("U1", "uniform"), _eq("U2", "uniform"),
                 _eq("B1", "boots"), _eq("B2", "boots")]
    _, summary = conflict_checker.check(allocs, members, equipment, [])
    assert all(v == 0 for v in summary.values())
