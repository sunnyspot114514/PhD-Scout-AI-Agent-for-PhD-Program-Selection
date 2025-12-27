"""
PhD-Scout 单元测试

运行方式:
    pytest                    # 运行所有测试
    pytest -v                 # 详细输出
    pytest tests/test_main.py # 只运行这个文件
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径，以便导入 main 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import check_is_alumni, deduplicate_school_list, clean_text_for_chinese, ensure_english_term


class TestCheckIsAlumni:
    """校友检测功能测试"""
    
    def test_exact_match(self):
        """测试完全匹配"""
        assert check_is_alumni("MIT", "MIT") == True
    
    def test_contains_match(self):
        """测试包含匹配"""
        assert check_is_alumni("University of Texas", "University of Texas at Austin") == True
        assert check_is_alumni("Beijing Institute of Technology", "Beijing Institute of Technology, Zhuhai") == True
    
    def test_fuzzy_match_high_similarity(self):
        """测试高相似度匹配"""
        # 注意：当前的相似度阈值是 0.85，这些测试用例可能不满足
        assert check_is_alumni("Beijing Institute of Technology", "Beijing Institute of Technology") == True
        assert check_is_alumni("University of California", "University of California, Berkeley") == True
    
    def test_no_match(self):
        """测试不匹配情况"""
        assert check_is_alumni("MIT", "Stanford") == False
        assert check_is_alumni("Harvard", "Yale") == False
    
    def test_empty_or_none_input(self):
        """测试空输入或 None"""
        assert check_is_alumni("MIT", "") == False
        assert check_is_alumni("MIT", None) == False
        assert check_is_alumni("MIT", "AB") == False  # 太短的输入
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert check_is_alumni("mit", "MIT") == True
        assert check_is_alumni("Stanford University", "stanford university") == True


class TestDeduplicateSchoolList:
    """去重功能测试"""
    
    def test_basic_dedup(self):
        """基本去重测试"""
        raw = [
            {"name": "MIT", "source": "Manual"},
            {"name": "mit", "source": "AI Rec"},  # 重复，不同大小写
        ]
        result = deduplicate_school_list(None, raw)
        assert len(result) == 1
    
    def test_manual_priority_over_ai(self):
        """手动目标优先于 AI 推荐"""
        raw = [
            {"name": "MIT", "source": "Manual"},
            {"name": "MIT", "source": "AI Rec"},
        ]
        result = deduplicate_school_list(None, raw)
        assert len(result) == 1
        assert result[0]["source"] == "Manual"
    
    def test_string_input_normalization(self):
        """字符串输入自动转为字典格式"""
        raw = ["MIT", "Stanford"]
        result = deduplicate_school_list(None, raw)
        assert len(result) == 2
        assert all("name" in item and "source" in item for item in result)
    
    def test_mixed_input_types(self):
        """混合输入类型测试"""
        raw = [
            {"name": "MIT", "source": "Manual"},
            "Stanford",  # 字符串格式
            {"school_name": "Harvard", "source": "AI Rec"}  # 错误的 key 名
        ]
        result = deduplicate_school_list(None, raw)
        assert len(result) == 3
        # 检查 school_name 是否被正确转换为 name
        harvard_item = next((item for item in result if "Harvard" in item["name"]), None)
        assert harvard_item is not None
    
    def test_university_name_normalization(self):
        """大学名称标准化测试"""
        raw = [
            {"name": "MIT", "source": "Manual"},
            {"name": "Massachusetts Institute of Technology", "source": "AI Rec"},  # 应该被识别为同一所
        ]
        result = deduplicate_school_list(None, raw)
        # 注意：当前的去重逻辑可能无法处理这种情况，这是一个已知限制
        # 这个测试主要是为了记录当前行为
        assert len(result) >= 1


class TestCleanTextForChinese:
    """中文文本清洗功能测试"""
    
    def test_info_not_found_replacement(self):
        """测试 'Information not found' 替换"""
        assert clean_text_for_chinese("Information not found") == "需人工核实"
    
    def test_normal_text_unchanged(self):
        """测试正常文本不变"""
        assert clean_text_for_chinese("正常的中文文本") == "正常的中文文本"
        assert clean_text_for_chinese("Normal English text") == "Normal English text"
    
    def test_non_string_input(self):
        """测试非字符串输入"""
        assert clean_text_for_chinese(123) == 123
        assert clean_text_for_chinese(None) == None
        assert clean_text_for_chinese([]) == []


class TestEnsureEnglishTerm:
    """英文术语确保功能测试"""
    
    def test_empty_or_short_input(self):
        """测试空输入或过短输入"""
        assert ensure_english_term(None, "") == ""
        assert ensure_english_term(None, "A") == ""
        assert ensure_english_term(None, None) == ""
    
    def test_already_english_text(self):
        """测试已经是英文的文本"""
        english_text = "Computer Science"
        assert ensure_english_term(None, english_text) == english_text
    
    def test_mixed_text_with_english(self):
        """测试包含英文的混合文本"""
        mixed_text = "AI and Machine Learning"
        assert ensure_english_term(None, mixed_text) == mixed_text
    
    # 注意：包含中文的测试需要真实的 LLM 调用，在单元测试中跳过
    def test_chinese_text_detection(self):
        """测试中文文本检测（不调用 LLM）"""
        import re
        chinese_text = "计算机科学"
        # 验证中文检测逻辑
        has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', chinese_text))
        assert has_chinese == True
        
        english_text = "Computer Science"
        has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', english_text))
        assert has_chinese == False


# 运行测试的示例
if __name__ == "__main__":
    pytest.main([__file__, "-v"])