# PhD-Scout 日志系统使用指南

## 概述

PhD-Scout 现在集成了专业的日志系统，提供比 `print()` 更强大的日志管理功能。

## 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| `DEBUG` | 调试信息，默认不显示 | 翻译调用、搜索词构建 |
| `INFO` | 正常流程信息 | 开始分析、完成分析 |
| `WARNING` | 警告但不影响运行 | API 返回空结果 |
| `ERROR` | 错误，需要关注 | 分析失败、API 调用失败 |

## 日志输出

### 控制台输出
```
2025-12-27 23:19:51 [INFO] 开始分析学校: MIT
2025-12-27 23:19:52 [WARNING] Semantic Scholar 初始化失败: API key missing
2025-12-27 23:19:53 [INFO] 学校分析完成: MIT (匹配分: 85)
```

### 文件输出
日志同时保存到 `logs/phd_scout_YYYYMMDD.log` 文件中，按日期自动分文件。

## 使用方式

### 在代码中使用
```python
from logger import logger

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("正常信息") 
logger.warning("警告信息")
logger.error("错误信息")
```

### 调整日志级别
```python
from logger import setup_logger
import logging

# 只显示 WARNING 及以上级别
logger = setup_logger(level=logging.WARNING)

# 不输出到文件
logger = setup_logger(log_to_file=False)
```

## 兼容性

- ✅ 保持所有原有的 `print()` 输出
- ✅ 不影响现有功能
- ✅ 所有测试通过
- ✅ 日志文件自动忽略 (已加入 .gitignore)

## 日志文件管理

- 日志文件位置: `logs/phd_scout_YYYYMMDD.log`
- 自动按日期分文件
- 文件编码: UTF-8
- Git 自动忽略日志文件

## 好处

1. **专业性**: 标准的日志格式，带时间戳和级别
2. **可控性**: 可以调整显示级别，生产环境只显示重要信息
3. **可追溯**: 日志保存到文件，方便排查问题
4. **兼容性**: 不破坏现有代码，渐进式改进