# -*- coding: utf-8 -*-
"""候选尺码生成测试。"""
from smart_alloc import size_matcher, schemas
from smart_alloc.config import DEFAULT_CONFIG
from helpers import make_uniform, make_boots, make_member


def test_rule_predicted():
    equipment = make_uniform("M", "175/92", 1)
    m = make_member("M1", "A", height=175, chest=92, foot=260)
    cands = size_matcher.uniform_candidates(m, equipment, [], DEFAULT_CONFIG)
    assert any(c["size_code"] == "175/92" and c["source"] == "规则预测" for c in cands)


def test_no_fit_excluded():
    equipment = make_uniform("M", "175/92", 1) + make_uniform("M", "180/96", 1)
    m = make_member("M1", "A", height=175, chest=92, foot=260)
    rec = schemas.new_fit_record(member_id="M1", category="uniform",
                                 size_code="175/92", fit_level="no", verified=True)
    cands = size_matcher.uniform_candidates(m, equipment, [rec], DEFAULT_CONFIG)
    sizes = [c["size_code"] for c in cands]
    assert "175/92" not in sizes
    assert "180/96" in sizes


def test_previous_year_priority():
    equipment = make_uniform("M", "175/92", 1)
    m = make_member("M1", "A", status="returning", prev_u="M175/92-1",
                    height=175, chest=92, foot=260)
    cands = size_matcher.uniform_candidates(m, equipment, [], DEFAULT_CONFIG)
    assert any(c["size_code"] == "175/92" and c["source"] == "上年沿用" for c in cands)


def test_no_data_no_candidates():
    equipment = make_uniform("M", "175/92", 1)
    m = make_member("M1", "A")
    cands = size_matcher.uniform_candidates(m, equipment, [], DEFAULT_CONFIG)
    assert cands == []


def test_boot_rule_predicted():
    equipment = make_boots(42, 2) + make_boots(43, 2)
    m = make_member("M1", "A", height=175, chest=92, foot=260)
    cands = size_matcher.boot_candidates(m, equipment, [], DEFAULT_CONFIG)
    sizes = {c["size_code"] for c in cands}
    assert "42" in sizes and "43" in sizes
