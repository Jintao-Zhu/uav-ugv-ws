"""
任务（Tasks）模块

包含：
- task.py - Task 数据结构
- stream.py - TaskStream 任务流生成器
- manager.py - TaskManager 任务管理器
- executor.py - VirtualUAVExecutor 虚拟执行器（Day4）
- catalog.py - TaskCatalog 任务目录（Day8 Step 6.1）
"""

from .task import Task
from .stream import TaskStream, TaskConfig
from .manager import TaskManager
from .executor import VirtualUAVExecutor, estimate_travel_time
from .catalog import TaskCatalog, generate_and_save_catalog, load_catalog

__all__ = [
    'Task', 'TaskStream', 'TaskConfig', 'TaskManager',
    'VirtualUAVExecutor', 'estimate_travel_time',
    'TaskCatalog', 'generate_and_save_catalog', 'load_catalog'
]
