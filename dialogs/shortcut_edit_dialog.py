"""
快捷入口编辑对话框
支持拖拽文件/文件夹到对话框中，存储路径，点击按钮直接打开
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                              QLabel, QPushButton, QFileDialog, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from widgets.tag_selector_widget import TagSelectorWidget
from managers.application.data_manager import TaskType
import os


class DragDropLabel(QLabel):
    """支持拖拽文件/文件夹的标签控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.hint_text = "将文件或文件夹拖拽到此处\n\n或者"
        self.setText(self.hint_text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #888;
                border-radius: 8px;
                padding: 24px;
                color: #666;
                font-size: 14px;
                background-color: #fafafa;
            }
        """)
        self.file_path = ""

    def setHintText(self, text):
        """设置拖拽提示文字"""
        self.hint_text = text
        if not self.file_path:
            self.setText(text)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入时检查是否包含本地文件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #2196F3;
                    border-radius: 8px;
                    padding: 24px;
                    color: #2196F3;
                    font-size: 14px;
                    background-color: #e3f2fd;
                }
            """)
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """文件放下时获取路径"""
        urls = event.mimeData().urls()
        if urls:
            # 取第一个文件/文件夹路径
            self.file_path = urls[0].toLocalFile()
            if os.path.isfile(self.file_path):
                name = os.path.basename(self.file_path)
                self.setText(f"📄 {name}\n{self.file_path}")
            elif os.path.isdir(self.file_path):
                name = os.path.basename(self.file_path) or self.file_path
                self.setText(f"📁 {name}\n{self.file_path}")
            else:
                self.setText(f"📎 {self.file_path}")
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    padding: 24px;
                    color: #4CAF50;
                    font-size: 14px;
                    background-color: #e8f5e9;
                }
            """)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """拖拽离开时恢复样式"""
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #888;
                border-radius: 8px;
                padding: 24px;
                color: #666;
                font-size: 14px;
                background-color: #fafafa;
            }
        """)
        if not self.file_path:
            self.setText(self.hint_text)


class ShortcutEditDialog(QDialog):
    """快捷入口编辑对话框"""

    def __init__(self, parent=None, data_manager=None,
                 initial_title: str = "", initial_path: str = "", initial_tags: str = "",
                 initial_action_type: str = "open", initial_parent_id=None,
                 excluded_parent_ids=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.initial_title = initial_title
        self.initial_path = initial_path
        self.initial_tags = initial_tags
        self.initial_action_type = initial_action_type
        self.initial_parent_id = initial_parent_id
        self.excluded_parent_ids = set(excluded_parent_ids or [])
        self.current_path = initial_path
        self.current_action_type = initial_action_type
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("快捷入口")
        self.setModal(True)
        self.resize(600, 380)

        layout = QVBoxLayout()

        # 操作类型选择
        action_type_layout = QHBoxLayout()
        action_type_layout.addWidget(QLabel("操作类型:"))
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(["打开文件/文件夹", "执行脚本"])
        self.action_type_combo.setCurrentIndex(0 if self.initial_action_type == "open" else 1)
        self.action_type_combo.currentIndexChanged.connect(self.on_action_type_changed)
        action_type_layout.addWidget(self.action_type_combo)
        action_type_layout.addStretch()
        layout.addLayout(action_type_layout)

        # Parent selector: empty means a root shortcut; the first release is two-level.
        parent_layout = QHBoxLayout()
        parent_layout.addWidget(QLabel("Parent shortcut:"))
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("None (root)", None)
        if self.data_manager is not None:
            try:
                roots = [
                    item for item in self.data_manager.get_all_shortcuts()
                    if not item.get("parent_id") and item.get("id") not in self.excluded_parent_ids
                ]
                for item in roots:
                    self.parent_combo.addItem(item.get("title", ""), item.get("id"))
            except Exception:
                pass
        current_index = self.parent_combo.findData(self.initial_parent_id)
        self.parent_combo.setCurrentIndex(current_index if current_index >= 0 else 0)
        parent_layout.addWidget(self.parent_combo)
        parent_layout.addStretch()
        layout.addLayout(parent_layout)

        # 名称输入区
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.initial_title)
        self.name_edit.setPlaceholderText("给这个快捷入口起个名字，例如：项目文档、工作文件夹")
        self.name_edit.setMinimumWidth(300)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # 路径输入区（支持手动输入或拖拽）
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("路径:"))
        self.path_edit = QLineEdit()
        self.path_edit.setText(self.initial_path)
        self.path_edit.setPlaceholderText("输入文件或文件夹的完整路径" if self.current_action_type == "open" else "输入脚本文件的完整路径")
        self.path_edit.setMinimumWidth(300)
        path_layout.addWidget(self.path_edit)

        # 浏览按钮
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)

        # 拖拽区域
        self.drop_label = DragDropLabel()
        self.drop_label.setHintText("将文件或文件夹拖拽到此处\n\n或者" if self.current_action_type == "open" else "将脚本文件拖拽到此处\n\n或者")
        if self.initial_path:
            if os.path.isfile(self.initial_path):
                name = os.path.basename(self.initial_path)
                self.drop_label.setText(f"📄 {name}\n{self.initial_path}")
                self.drop_label.file_path = self.initial_path
                self.drop_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #4CAF50;
                        border-radius: 8px;
                        padding: 24px;
                        color: #4CAF50;
                        font-size: 14px;
                        background-color: #e8f5e9;
                    }
                """)
            elif os.path.isdir(self.initial_path):
                name = os.path.basename(self.initial_path) or self.initial_path
                self.drop_label.setText(f"📁 {name}\n{self.initial_path}")
                self.drop_label.file_path = self.initial_path
                self.drop_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #4CAF50;
                        border-radius: 8px;
                        padding: 24px;
                        color: #4CAF50;
                        font-size: 14px;
                        background-color: #e8f5e9;
                    }
                """)

        layout.addWidget(self.drop_label)

        # 标签选择组件（使用独立的 SHORTCUT 类型）
        class ShortcutTaskType:
            value = "shortcut"
        self.tag_selector = TagSelectorWidget(
            parent=self,
            data_manager=self.data_manager,
            initial_tags=self.initial_tags,
            task_type=ShortcutTaskType()
        )
        layout.addWidget(self.tag_selector)

        # 打开按钮（预览用）
        self.open_btn = QPushButton("打开位置")
        self.open_btn.clicked.connect(self.open_location)
        self.open_btn.setEnabled(bool(self.initial_path))
        layout.addWidget(self.open_btn)

        # 按钮区
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 路径变化时同步 drop_label
        self.path_edit.textChanged.connect(self.on_path_changed)

    def on_action_type_changed(self, index):
        """操作类型变化时更新界面"""
        self.current_action_type = "open" if index == 0 else "script"
        self.path_edit.setPlaceholderText("输入文件或文件夹的完整路径" if self.current_action_type == "open" else "输入脚本文件的完整路径")
        self.drop_label.setHintText("将文件或文件夹拖拽到此处\n\n或者" if self.current_action_type == "open" else "将脚本文件拖拽到此处\n\n或者")
        if not self.drop_label.file_path:
            self.drop_label.setText(self.drop_label.hint_text)

    def on_path_changed(self, text):
        """路径手动修改时更新 drop_label 和打开按钮"""
        self.current_path = text
        self.drop_label.file_path = text
        if os.path.isfile(text):
            name = os.path.basename(text)
            self.drop_label.setText(f"📄 {name}\n{text}")
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    padding: 24px;
                    color: #4CAF50;
                    font-size: 14px;
                    background-color: #e8f5e9;
                }
            """)
            self.open_btn.setEnabled(True)
        elif os.path.isdir(text):
            name = os.path.basename(text) or text
            self.drop_label.setText(f"📁 {name}\n{text}")
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    padding: 24px;
                    color: #4CAF50;
                    font-size: 14px;
                    background-color: #e8f5e9;
                }
            """)
            self.open_btn.setEnabled(True)
        elif text:
            self.drop_label.setText(f"📎 {text}")
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #F44336;
                    border-radius: 8px;
                    padding: 24px;
                    color: #F44336;
                    font-size: 14px;
                    background-color: #ffebee;
                }
            """)
            self.open_btn.setEnabled(False)
        else:
            self.drop_label.setText("将文件或文件夹拖拽到此处\n\n或者")
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #888;
                    border-radius: 8px;
                    padding: 24px;
                    color: #666;
                    font-size: 14px;
                    background-color: #fafafa;
                }
            """)
            self.open_btn.setEnabled(False)

    def browse_path(self):
        """浏览按钮：弹出文件/文件夹选择框"""
        if self.current_action_type == "script":
            # 脚本类型：只选择文件
            path, _ = QFileDialog.getOpenFileName(
                self, "选择脚本文件", "",
                "脚本文件 (*.bat *.cmd *.ps1 *.py *.exe *.lnk);;所有文件 (*.*)"
            )
            if path:
                self.path_edit.setText(path)
        else:
            # 打开类型：先尝试文件夹，再尝试文件
            path = QFileDialog.getExistingDirectory(
                self, "选择文件夹", ""
            )
            if not path:
                path, _ = QFileDialog.getOpenFileName(
                    self, "选择文件", "", "所有文件 (*.*)"
                )
            if path:
                self.path_edit.setText(path)

    def open_location(self):
        """打开文件/文件夹位置"""
        path = self.drop_label.file_path or self.path_edit.text()
        if not path:
            return
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        if os.path.isfile(path):
            # 打开所在文件夹并选中文件
            folder = os.path.dirname(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        elif os.path.isdir(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def get_data(self) -> dict:
        """获取对话框数据"""
        return {
            "title": self.name_edit.text().strip(),
            "shortcut_path": self.drop_label.file_path or self.path_edit.text().strip(),
            "tags": self.tag_selector.get_selected_tags(),
            "action_type": self.current_action_type,
            "parent_id": self.parent_combo.currentData(),
        }
