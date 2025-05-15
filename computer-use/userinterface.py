import sys
import subprocess
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QGroupBox,
    QApplication,
    QFrame,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QFont, QColor, QPalette
from PyQt5.QtCore import Qt, QTimer
import asyncio


class MainWindow(QWidget):
    def __init__(self, vm_computer):
        self.vm_computer = vm_computer
        super().__init__()

        # Set application font and style
        self.setWindowTitle("Computer Use Agent UI")
        self.resize(1200, 800)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #f5f5f5;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 1ex;
                padding: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #3498db;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                padding: 5px;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
            }
            QLabel {
                font-weight: bold;
                color: #2c3e50;
            }
            QScrollArea {
                border: none;
            }
        """
        )

        # Futures and state variables
        self._instruction_future = None
        self._user_input_future = None
        self._ack_future = None

        # Layouts with spacing
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Top section - Instructions
        instruction_group = QGroupBox("Instructions")
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.instruction_box = QLineEdit()
        self.instruction_box.setPlaceholderText(
            "Enter initial instructions (--instructions)"
        )
        self.instruction_box.setMinimumHeight(36)

        self.instruction_submit = QPushButton("Submit Instructions")
        self.instruction_submit.clicked.connect(self.submit_instructions)
        self.instruction_submit.setCursor(Qt.PointingHandCursor)

        top_layout.addWidget(self.instruction_box, 4)
        top_layout.addWidget(self.instruction_submit, 1)
        instruction_group.setLayout(top_layout)

        # Middle section - Chat
        center_layout = QVBoxLayout()

        # Chatbox (scrollable)
        chat_group = QGroupBox("Agent Chat")
        chat_layout = QVBoxLayout()

        self.chatbox = QTextEdit()
        self.chatbox.setReadOnly(True)
        self.chatbox.setMinimumHeight(400)
        self.chatbox.document().setDefaultStyleSheet(
            """
            .user { color: #2980b9; font-weight: bold; }
            .agent { color: #27ae60; font-weight: bold; }
            .system { color: #c0392b; font-style: italic; }
        """
        )

        chat_layout.addWidget(self.chatbox)
        chat_group.setLayout(chat_layout)
        center_layout.addWidget(chat_group)

        # Bottom section - User Input
        input_group = QGroupBox("User Input")
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.user_input_box = QLineEdit()
        self.user_input_box.setPlaceholderText("User input (when required)")
        self.user_input_box.setMinimumHeight(36)

        self.user_input_submit = QPushButton("Submit")
        self.user_input_submit.clicked.connect(self.submit_user_input)
        self.user_input_submit.setCursor(Qt.PointingHandCursor)

        self.ack_button = QPushButton("Acknowledge")
        self.ack_button.setVisible(False)
        self.ack_button.clicked.connect(self._on_acknowledge)
        self.ack_button.setCursor(Qt.PointingHandCursor)
        self.ack_button.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """
        )

        bottom_layout.addWidget(self.user_input_box, 4)
        bottom_layout.addWidget(self.user_input_submit, 1)
        bottom_layout.addWidget(self.ack_button, 1)
        input_group.setLayout(bottom_layout)

        # Assemble layouts
        main_layout.addWidget(instruction_group)
        main_layout.addLayout(center_layout)
        main_layout.addWidget(input_group)
        self.setLayout(main_layout)

        # Placeholder for agent and VM
        self.agent = None
        self.vm = None

    async def get_instructions_async(self):
        self.instruction_box.setEnabled(True)
        self.instruction_submit.setEnabled(True)
        self.instruction_box.setFocus()
        self._instruction_future = asyncio.get_event_loop().create_future()
        return await self._instruction_future

    def submit_instructions(self):
        instructions = self.instruction_box.text()
        self.instruction_box.setEnabled(False)
        self.instruction_submit.setEnabled(False)
        if self._instruction_future and not self._instruction_future.done():
            self._instruction_future.set_result(instructions)
            self.append_system_message("Instructions submitted")
        # Optionally clear the box for next use
        self.instruction_box.clear()

    async def get_user_input_async(self):
        self.user_input_box.setEnabled(True)
        self.user_input_submit.setEnabled(True)
        self.user_input_box.setFocus()
        self._user_input_future = asyncio.get_event_loop().create_future()
        return await self._user_input_future

    def submit_user_input(self):
        user_input = self.user_input_box.text()
        self.user_input_box.clear()
        self.append_user_message(user_input)
        if self._user_input_future and not self._user_input_future.done():
            self._user_input_future.set_result(user_input)
        self.user_input_box.setEnabled(False)
        self.user_input_submit.setEnabled(False)

    async def await_user_ack(self, prompt):
        self.append_system_message(prompt)
        self.ack_button.setVisible(True)
        self._ack_future = asyncio.get_event_loop().create_future()
        result = await self._ack_future
        self.ack_button.setVisible(False)
        return result

    def _on_acknowledge(self):
        if self._ack_future and not self._ack_future.done():
            self._ack_future.set_result(True)
            self.append_system_message("Acknowledged by user")
        self.ack_button.setVisible(False)

    def append_chat(self, text):
        self.chatbox.append(text)
        # Auto scroll to bottom
        scrollbar = self.chatbox.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_user_message(self, text):
        formatted_text = f'<div class="user">User: {text}</div>'
        self.append_chat(formatted_text)

    def append_agent_message(self, text):
        formatted_text = f'<div class="agent">Agent: {text}</div>'
        self.append_chat(formatted_text)

    def append_system_message(self, text):
        formatted_text = f'<div class="system">System: {text}</div>'
        self.append_chat(formatted_text)

    # Helper method to add visual separator in chat
    def add_chat_separator(self):
        self.append_chat('<hr style="border: 1px dashed #cccccc; margin: 10px 0;">')
