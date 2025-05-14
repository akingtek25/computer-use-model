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
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
import asyncio


class MainWindow(QWidget):
    def __init__(self, vm_computer):
        self.vm_computer = vm_computer
        super().__init__()
        self.setWindowTitle("Computer Use Agent UI")
        self.resize(1200, 800)
        # ... add to layout ...
        self._instruction_future = None
        # Layouts
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        center_layout = QHBoxLayout()
        bottom_layout = QHBoxLayout()

        # Instruction box
        self.instruction_box = QLineEdit()
        self.instruction_box.setPlaceholderText("Enter initial instructions (--instructions)")
        self.instruction_submit = QPushButton("Submit Instructions")
        self.instruction_submit.clicked.connect(self.submit_instructions)
        top_layout.addWidget(QLabel("Instructions:"))
        top_layout.addWidget(self.instruction_box)
        top_layout.addWidget(self.instruction_submit)

        # User input box
        self.user_input_box = QLineEdit()
        self.user_input_box.setPlaceholderText("User input (when required)")
        self.user_input_submit = QPushButton("Submit")
        self.user_input_submit.clicked.connect(self.submit_user_input)
        bottom_layout.addWidget(QLabel("User Input:"))
        bottom_layout.addWidget(self.user_input_box)
        bottom_layout.addWidget(self.user_input_submit)

        # Acknowledge button (hidden by default)
        self.ack_button = QPushButton("Acknowledge")
        self.ack_button.setVisible(False)
        self.ack_button.clicked.connect(self._on_acknowledge)
        bottom_layout.addWidget(self.ack_button)

        # Chatbox (scrollable)
        self.chatbox = QTextEdit()
        self.chatbox.setReadOnly(True)
        chatbox_group = QGroupBox("Agent Chat")
        chatbox_layout = QVBoxLayout()
        chatbox_layout.addWidget(self.chatbox)
        chatbox_group.setLayout(chatbox_layout)
        chatbox_scroll = QScrollArea()
        chatbox_scroll.setWidget(chatbox_group)
        chatbox_scroll.setWidgetResizable(True)
        chatbox_scroll.setFixedWidth(900)
        center_layout.addWidget(chatbox_scroll)

        # Assemble layouts
        main_layout.addLayout(top_layout)
        main_layout.addLayout(center_layout)
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)

        # Placeholder for agent and VM
        self.agent = None
        self.vm = None

        # Async communication futures
        self._user_input_future = None
        self._ack_future = None
    async def get_instructions_async(self):
        self.instruction_box.setEnabled(True)
        self.instruction_submit.setEnabled(True)
        self.instruction_box.setFocus()
        self._instruction_future = asyncio.get_event_loop().create_future()
        return await self._instruction_future
    # Async method to get user input from the UI
    def submit_instructions(self):
        instructions = self.instruction_box.text()
        self.instruction_box.setEnabled(False)
        self.instruction_submit.setEnabled(False)
        if self._instruction_future and not self._instruction_future.done():
            self._instruction_future.set_result(instructions)
        # Optionally clear the box for next use
        self.instruction_box.clear()
    async def get_user_input_async(self):
        self.user_input_box.setEnabled(True)
        self.user_input_submit.setEnabled(True)
        self._user_input_future = asyncio.get_event_loop().create_future()
        return await self._user_input_future

    def submit_user_input(self):
        user_input = self.user_input_box.text()
        self.user_input_box.clear()
        self.append_chat(f"User: {user_input}")
        if self._user_input_future and not self._user_input_future.done():
            self._user_input_future.set_result(user_input)
        self.user_input_box.setEnabled(False)
        self.user_input_submit.setEnabled(False)

    # Async method to wait for user acknowledgment
    async def await_user_ack(self, prompt):
        self.append_chat(prompt)
        self.ack_button.setVisible(True)
        self._ack_future = asyncio.get_event_loop().create_future()
        result = await self._ack_future
        self.ack_button.setVisible(False)
        return result

    def _on_acknowledge(self):
        if self._ack_future and not self._ack_future.done():
            self._ack_future.set_result(True)
        self.ack_button.setVisible(False)

    def append_chat(self, text):
        self.chatbox.append(text)
        