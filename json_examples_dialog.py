"""
JSON导入示例对话框
显示每种任务类型的JSON导入示例
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QTabWidget, QWidget, QLabel, QFrame)
from PyQt6.QtCore import Qt
import json


class JsonExamplesDialog(QDialog):
    """JSON导入示例对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('JSON导入示例')
        self.setModal(True)
        self.resize(700, 500)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 说明文本
        info_label = QLabel('以下为各种任务类型的JSON导入示例。您可以根据这些示例格式准备您的JSON文件。')
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(info_label)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 每日任务示例
        self.add_example_tab("每日任务", self.get_daily_example())
        
        # 待办事项示例
        self.add_example_tab("待办事项", self.get_todo_example())
        
        # 娱乐任务示例
        self.add_example_tab("娱乐任务", self.get_entertainment_example())
        
        layout.addWidget(self.tab_widget)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_example_tab(self, title, example_json):
        """添加示例标签页"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        # 说明文字
        desc_label = QLabel(f'{title}的JSON结构示例:')
        desc_label.setStyleSheet("font-size: 12px; color: #34495e; padding: 5px 0;")
        tab_layout.addWidget(desc_label)
        
        # JSON预览文本框
        text_edit = QTextEdit()
        text_edit.setPlainText(example_json)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 10px;
            }
        """)
        tab_layout.addWidget(text_edit)
        
        # 添加到标签页
        self.tab_widget.addTab(tab, title)
    
    def get_daily_example(self):
        """获取每日任务示例"""
        example = {
            "daily": [
                {
                    "title": "晨间运动",
                    "description": "每天早上跑步30分钟",
                    "completed": False,
                    "week_day": "每天",
                    "category": "daily"
                },
                {
                    "title": "读书时间",
                    "description": "每天阅读至少30页书籍",
                    "completed": True,
                    "week_day": "星期一",
                    "category": "daily"
                }
            ],
            "todo": [],
            "entertainment": []
        }
        return json.dumps(example, ensure_ascii=False, indent=2)
    
    def get_todo_example(self):
        """获取待办事项示例"""
        example = {
            "daily": [],
            "todo": [
                {
                    "title": "完成项目报告",
                    "description": "完成Q1季度项目总结报告",
                    "completed": False,
                    "deadline": "2026-04-15",
                    "urgency_score": 5,
                    "category": "todo"
                },
                {
                    "title": "购买生日礼物",
                    "description": "为朋友准备生日礼物",
                    "completed": True,
                    "deadline": "2026-03-30",
                    "urgency_score": 3,
                    "category": "todo"
                }
            ],
            "entertainment": []
        }
        return json.dumps(example, ensure_ascii=False, indent=2)
    
    def get_entertainment_example(self):
        """获取娱乐任务示例"""
        example = {
            "daily": [],
            "todo": [],
            "entertainment": [
                {
                    "title": "看电影《流浪地球》",
                    "description": "观看最近上映的科幻电影",
                    "completed": False,
                    "fun_category": "movies",
                    "category": "entertainment"
                },
                {
                    "title": "打游戏",
                    "description": "玩新出的游戏",
                    "completed": True,
                    "fun_category": "games",
                    "category": "entertainment"
                }
            ]
        }
        return json.dumps(example, ensure_ascii=False, indent=2)