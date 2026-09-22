# -*- coding: utf-8 -*-
"""物资仓库数据 → 装备实体 的 seed 测试（用真实结构样例）。"""
from smart_alloc import seed


def _wh_data():
    return {
        "grid": [
            [{"code": "N43/43-01", "person": "章晏华"},
             {"code": "X44-05", "person": "孜英"},
             {"code": "N42/42.5-02", "person": "（鞋面损坏）"}],
        ],
        "belts": [
            {"code": "M01", "uniform_size": "M175/88-01", "person": "陈思骆", "cabinet": "一柜"},
        ],
        "uniforms": [
            {"code": "M175/88-01", "belt": "M01", "person": "陈思骆", "cabinet": "一柜"},
            {"code": "M185/100-02", "belt": "M25", "person": "顾铭文、韦景浩、林育臣", "cabinet": "六柜"},
        ],
    }


def test_seed_equipment():
    equipment, prev = seed.build_equipment(_wh_data())
    # 2 礼服 + 3 马靴
    uniforms = [e for e in equipment if e["category"] == "uniform"]
    boots = [e for e in equipment if e["category"] == "boots"]
    assert len(uniforms) == 2
    assert len(boots) == 3

    # 礼服性别/尺码解析
    u1 = next(e for e in uniforms if e["equipment_id"] == "M175/88-01")
    assert u1["gender"] == "M" and u1["size_code"] == "175/88"
    assert u1["paired_belt_id"] == "M01"

    # 损坏马靴
    dmg = next(e for e in boots if e["equipment_id"] == "N42/42.5-02")
    assert dmg["status"] == "damaged"
    # 正常马靴尺码
    ok = next(e for e in boots if e["equipment_id"] == "N43/43-01")
    assert ok["size_code"] == "43" and ok["status"] == "available"


def test_seed_prev_assignment():
    _, prev = seed.build_equipment(_wh_data())
    assert prev["章晏华"]["boots"] == "N43/43-01"
    assert prev["陈思骆"]["uniform"] == "M175/88-01"
    # 3 人共用礼服 → 每人都记录到同一件
    assert prev["顾铭文"]["uniform"] == "M185/100-02"
    assert prev["韦景浩"]["uniform"] == "M185/100-02"
    assert prev["林育臣"]["uniform"] == "M185/100-02"
    # 损坏靴的“使用人”不应被记录
    assert "（鞋面损坏）" not in prev
