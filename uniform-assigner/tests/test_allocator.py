# -*- coding: utf-8 -*-
"""自动分配求解器测试（CP-SAT）。"""
from smart_alloc import allocation_engine
from smart_alloc.config import DEFAULT_CONFIG
from helpers import make_uniform, make_boots, make_member


def test_two_share_ok():
    equipment = make_uniform("M", "175/92", 1) + make_boots(42, 1) + make_boots(43, 1)
    members = [
        make_member("M1", "A", height=175, chest=92, foot=260, duty_class="周一"),
        make_member("M2", "B", height=175, chest=92, foot=260, duty_class="周二"),
    ]
    res = allocation_engine.solve(members, equipment, [], {}, DEFAULT_CONFIG)
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    shared_u = [s for s in res["shared"] if s["category"] == "uniform"]
    assert len(shared_u) == 1 and len(shared_u[0]["members"]) == 2


def test_three_share_infeasible():
    equipment = make_uniform("M", "175/92", 1) + make_boots(42, 1) + make_boots(43, 1) + make_boots(44, 1)
    members = [
        make_member("M1", "A", height=175, chest=92, foot=260, duty_class="周一"),
        make_member("M2", "B", height=175, chest=92, foot=260, duty_class="周二"),
        make_member("M3", "C", height=175, chest=92, foot=260, duty_class="周三"),
    ]
    res = allocation_engine.solve(members, equipment, [], {}, DEFAULT_CONFIG)
    assert res["status"] == "INFEASIBLE"
    assert any(s["size_code"] == "175/92" for s in res["shortage"])


def test_same_class_infeasible():
    equipment = make_uniform("M", "175/92", 1) + make_boots(42, 1) + make_boots(43, 1)
    members = [
        make_member("M1", "A", height=175, chest=92, foot=260, duty_class="周一"),
        make_member("M2", "B", height=175, chest=92, foot=260, duty_class="周一"),
    ]
    res = allocation_engine.solve(members, equipment, [], {}, DEFAULT_CONFIG)
    assert res["status"] == "INFEASIBLE"


def test_locked_preserved():
    u1 = make_uniform("M", "175/92", 1)[0]
    u2 = make_uniform("M", "180/96", 1)[0]
    b1 = make_boots(42, 1)[0]
    b2 = make_boots(43, 1)[0]
    equipment = [u1, u2, b1, b2]
    members = [
        make_member("M1", "A", height=175, chest=92, foot=260, duty_class="周一"),
        make_member("M2", "B", height=175, chest=92, foot=265, duty_class="周二"),
    ]
    locked = {"M1": {"uniform_id": u1["equipment_id"], "boot_id": b1["equipment_id"]}}
    res = allocation_engine.solve(members, equipment, [], locked, DEFAULT_CONFIG)
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    a = next(x for x in res["allocations"] if x["member_id"] == "M1")
    assert a["uniform_id"] == u1["equipment_id"]


def test_scarce_reserved():
    u1 = make_uniform("M", "175/92", 1)[0]
    u2 = make_uniform("M", "180/96", 1)[0]
    equipment = [u1, u2] + make_boots(42, 2) + make_boots(43, 2)
    members = [
        make_member("M1", "A", height=179, chest=95, foot=265, duty_class="周一"),  # 更合 180/96
        make_member("M2", "B", height=172, chest=90, foot=265, duty_class="周二"),  # 只能 175/92
    ]
    res = allocation_engine.solve(members, equipment, [], {}, DEFAULT_CONFIG)
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    b = next(x for x in res["allocations"] if x["member_id"] == "M2")
    a = next(x for x in res["allocations"] if x["member_id"] == "M1")
    assert b["uniform_id"] == u1["equipment_id"]
    assert a["uniform_id"] == u2["equipment_id"]


def test_damaged_excluded():
    u = make_uniform("M", "175/92", 1)[0]
    u["status"] = "damaged"
    equipment = [u] + make_boots(42, 1) + make_boots(43, 1)
    members = [make_member("M1", "A", height=175, chest=92, foot=260, duty_class="周一")]
    res = allocation_engine.solve(members, equipment, [], {}, DEFAULT_CONFIG)
    assert res["status"] == "INFEASIBLE"


def test_fit_no_excluded_from_solution():
    """试穿不可穿的尺码不得出现在最终分配。"""
    u1 = make_uniform("M", "175/92", 1)[0]
    u2 = make_uniform("M", "180/96", 1)[0]
    equipment = [u1, u2] + make_boots(42, 1) + make_boots(43, 1)
    members = [make_member("M1", "A", height=175, chest=92, foot=260, duty_class="周一")]
    from smart_alloc import schemas
    rec = schemas.new_fit_record(member_id="M1", category="uniform",
                                 size_code="175/92", fit_level="no", verified=True)
    res = allocation_engine.solve(members, equipment, [rec], {}, DEFAULT_CONFIG)
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    a = res["allocations"][0]
    assert a["uniform_size"] != "175/92"
