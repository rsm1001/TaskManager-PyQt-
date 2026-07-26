"""
managers/priority.py 单元测试
测试优先级元数据的正确性和工具函数的逻辑
"""
import pytest
from managers.tasks.priority import (
    PRIORITY_LEVELS,
    PRIORITY_KEYS,
    PRIORITY_LABELS,
    PRIORITY_RANK,
    PRIORITY_WEIGHTS,
    PRIORITY_BG_COLORS,
    PRIORITY_TEXT_COLORS,
    PRIORITY_DISPLAY_MAP,
    LABEL_TO_KEY,
    DEFAULT_PRIORITY,
    get_priority_label,
    get_priority_rank,
    get_priority_weight,
)


class TestPriorityMetadata:
    """PRIORITY_LEVELS 元数据完整性测试"""

    def test_priority_levels_count(self):
        """5 档优先级定义完整"""
        assert len(PRIORITY_LEVELS) == 5

    def test_all_keys_unique(self):
        """所有 key 唯一"""
        keys = [p["key"] for p in PRIORITY_LEVELS]
        assert len(keys) == len(set(keys))

    def test_rank_descending_order(self):
        """rank 从高到低排列（urgent=5 > idle=1）"""
        ranks = [p["rank"] for p in PRIORITY_LEVELS]
        assert ranks == sorted(ranks, reverse=True)

    def test_urgent_highest_rank(self):
        """urgent 的 rank 最高"""
        assert PRIORITY_RANK["urgent"] == 5

    def test_idle_lowest_rank(self):
        """idle 的 rank 最低"""
        assert PRIORITY_RANK["idle"] == 1

    def test_idle_weight_zero(self):
        """idle 不参与随机抽取（weight=0）"""
        assert PRIORITY_WEIGHTS["idle"] == 0.0

    def test_all_weights_non_negative(self):
        """所有权重非负"""
        for w in PRIORITY_WEIGHTS.values():
            assert w >= 0.0

    def test_all_keys_have_bg_and_fg(self):
        """所有 key 都有背景色和文字色"""
        for p in PRIORITY_LEVELS:
            assert "bg" in p and "fg" in p
            assert p["bg"].startswith("#")
            assert p["fg"].startswith("#")

    def test_priority_keys_matches_level_keys(self):
        """PRIORITY_KEYS 与 LEVELS 中的 key 一致"""
        assert PRIORITY_KEYS == [p["key"] for p in PRIORITY_LEVELS]

    def test_priority_labels_matches_level_labels(self):
        """PRIORITY_LABELS 与 LEVELS 中的 label 一致"""
        assert PRIORITY_LABELS == [p["label"] for p in PRIORITY_LEVELS]

    def test_label_to_key_bidirectional(self):
        """LABEL_TO_KEY 是 PRIORITY_DISPLAY_MAP 的反向映射"""
        for key, label in PRIORITY_DISPLAY_MAP.items():
            assert LABEL_TO_KEY[label] == key


class TestGetPriorityFunctions:
    """get_priority_* 工具函数测试"""

    def test_get_priority_label_known_keys(self):
        """已知 key 返回对应中文标签"""
        assert get_priority_label("urgent") == "紧急"
        assert get_priority_label("high") == "重要"
        assert get_priority_label("normal") == "普通"
        assert get_priority_label("low") == "低"
        assert get_priority_label("idle") == "闲置"

    def test_get_priority_label_unknown_key(self):
        """未知 key 回落到普通"""
        assert get_priority_label("unknown") == get_priority_label("normal")
        assert get_priority_label("") == get_priority_label("normal")

    def test_get_priority_rank_ordering(self):
        """rank 顺序：urgent > high > normal > low > idle"""
        assert get_priority_rank("urgent") > get_priority_rank("high")
        assert get_priority_rank("high") > get_priority_rank("normal")
        assert get_priority_rank("normal") > get_priority_rank("low")
        assert get_priority_rank("low") > get_priority_rank("idle")

    def test_get_priority_rank_unknown_key(self):
        """未知 key 回落到 normal 的 rank"""
        assert get_priority_rank("bad_key") == get_priority_rank("normal")

    def test_get_priority_weight_idle_zero(self):
        """idle weight 为 0（不参与随机）"""
        assert get_priority_weight("idle") == 0.0

    def test_get_priority_weight_others_positive(self):
        """除 idle 外其他权重均为正"""
        for key in ["urgent", "high", "normal", "low"]:
            assert get_priority_weight(key) > 0.0

    def test_get_priority_weight_unknown_key(self):
        """未知 key 回落到 1.0"""
        assert get_priority_weight("bad_key") == 1.0


class TestDefaultPriority:
    """DEFAULT_PRIORITY 一致性测试"""

    def test_default_priority_is_normal(self):
        """默认值必须是 normal"""
        assert DEFAULT_PRIORITY == "normal"

    def test_default_priority_has_rank(self):
        """默认优先级的 rank 正确"""
        assert PRIORITY_RANK[DEFAULT_PRIORITY] == PRIORITY_RANK["normal"]
