"""
PhD-Scout 日志系统配置

提供统一的日志管理，支持控制台和文件输出。
"""

import logging
import os
from datetime import datetime


def setup_logger(name="phd_scout", level=logging.INFO, log_to_file=True):
    """
    配置并返回 logger
    
    Args:
        name (str): logger 名称
        level (int): 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_to_file (bool): 是否同时输出到文件
    
    Returns:
        logging.Logger: 配置好的 logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 日志格式：时间 [级别] 消息
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. 控制台输出 handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 2. 文件输出 handler (可选)
    if log_to_file:
        # 确保 logs 目录存在
        os.makedirs("logs", exist_ok=True)
        
        # 按日期命名日志文件
        log_filename = f"logs/phd_scout_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name="phd_scout"):
    """
    获取已配置的 logger 实例
    
    Args:
        name (str): logger 名称
    
    Returns:
        logging.Logger: logger 实例
    """
    return logging.getLogger(name)


# 全局 logger 实例，供其他模块导入使用
logger = setup_logger()


# 日志级别使用指南：
# logger.debug()   - 调试信息，正常运行时不显示
# logger.info()    - 正常流程信息，如开始/完成某个操作
# logger.warning() - 警告信息，不影响运行但需要注意
# logger.error()   - 错误信息，需要关注和处理