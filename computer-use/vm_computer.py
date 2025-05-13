import asyncio
import base64
import io
import paramiko
from PIL import Image
from basecomputer import BaseComputer
import time


class VMComputer(BaseComputer):
    """Use paramiko to take screenshots and perform actions on a remote VM."""

    def __init__(self, hostname, username, password):
        self.size = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.client = None
        self.sftp = None
        self.port = 22

    async def _connect(self):
        if self.client is None or self.sftp is None:

            def sync_connect():
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(
                    self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                )
                self.sftp = self.client.open_sftp()

            await asyncio.to_thread(sync_connect)

    @property
    def environment(self):
        return "linux"

    @property
    async def dimensions(self):
        if not self.size:
            # Take a screenshot from the VM
            await self._connect()
            screenshot_path = "/tmp/vm_screenshot.png"
            # Take screenshot using ImageMagick's import#
            display = ":0"
            xauth = f"/home/{self.username}/.Xauthority"
            cmd = f"DISPLAY={display} XAUTHORITY={xauth} gnome-screenshot -f {screenshot_path}"
            await asyncio.to_thread(self.client.exec_command, cmd)
            await asyncio.sleep(1)
            with io.BytesIO() as buf:
                await asyncio.to_thread(self.sftp.getfo, screenshot_path, buf)
                buf.seek(0)
                img = Image.open(buf)
                self.size = img.size
            await asyncio.to_thread(self.sftp.remove, screenshot_path)
        return self.size

    async def screenshot(self) -> str:
        await self._connect()
        screenshot_path = "/tmp/vm_screenshot.png"
        # Take screenshot using ImageMagick's import#
        display = ":0"
        xauth = f"/home/{self.username}/.Xauthority"
        cmd = f"DISPLAY={display} XAUTHORITY={xauth} gnome-screenshot -f {screenshot_path}"
        await asyncio.to_thread(self.client.exec_command, cmd)
        # Wait for screenshot to be saved
        await asyncio.sleep(1)
        # Download screenshot
        with io.BytesIO() as buf:
            await asyncio.to_thread(self.sftp.getfo, screenshot_path, buf)
            buf.seek(0)
            img_bytes = buf.read()
        # Remove screenshot from VM
        await asyncio.to_thread(self.sftp.remove, screenshot_path)
        # Encode as base64
        return base64.b64encode(img_bytes).decode("utf-8")

    async def click(self, x: int, y: int, button: str = "left") -> None:
        await self._connect()
        btn = {"left": 1, "middle": 2, "right": 3}.get(button, 1)
        display = ":0"
        xauth = f"/home/{self.username}/.Xauthority"
        cmd = f"DISPLAY={display} XAUTHORITY={xauth} xdotool mousemove {x} {y} click {btn}"
        await asyncio.to_thread(self.client.exec_command, cmd)

    async def double_click(self, x: int, y: int) -> None:
        await self._connect()
        display = ":0"
        xauth = f"/home/{self.username}/.Xauthority"
        cmd = f"DISPLAY={display} XAUTHORITY={xauth} xdotool mousemove {x} {y} click --repeat 2 1"
        await asyncio.to_thread(self.client.exec_command, cmd)

    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        await self._connect()
        # xdotool doesn't support scroll directly, but mouse wheel events are buttons 4 (up) and 5 (down)
        # Positive scroll_y = up, negative = down
        display = ":0"
        xauth = f"/home/{self.username}/.Xauthority"
        if scroll_y != 0:
            btn = 4 if scroll_y > 0 else 5
            for _ in range(abs(scroll_y)):
                cmd = f"DISPLAY={display} XAUTHORITY={xauth} xdotool mousemove {x} {y} click {btn}"
                await asyncio.to_thread(self.client.exec_command, cmd)
        # For horizontal scroll, buttons 6 (left) and 7 (right)
        if scroll_x != 0:
            btn = 6 if scroll_x > 0 else 7
            for _ in range(abs(scroll_x)):
                cmd = f"DISPLAY={display} XAUTHORITY={xauth} xdotool mousemove {x} {y} click {btn}"
                await asyncio.to_thread(self.client.exec_command, cmd)

    async def type(self, text: str) -> None:
        await self._connect()
        display = ":0"
        xauth = f"/home/{self.username}/.Xauthority"
        # Escape double quotes in text
        safe_text = text.replace('"', r"\"")
        cmd = f'DISPLAY={display} XAUTHORITY={xauth} xdotool type --delay 50 "{safe_text}"'
        await asyncio.to_thread(self.client.exec_command, cmd)

    async def wait(self, ms: int = 1000) -> None:
        await asyncio.sleep(ms / 1000)

    async def move(self, x: int, y: int) -> None:
        await self._connect()
        display = ":0"
        xauth = f"/home/{self.username}/.Xauthority"
        cmd = f"DISPLAY={display} XAUTHORITY={xauth} xdotool mousemove {x} {y}"
        await asyncio.to_thread(self.client.exec_command, cmd)

    async def keypress(self, keys: list[str]) -> None:
        await self._connect()
        # Join keys for xdotool
        display = ":0"
        xauth = f"/home/{self.username}/.Xauthority"
        key_str = " ".join(keys)
        if("ENTER" in key_str):
            key_str = key_str.replace("ENTER", "Return")
        cmd = f"DISPLAY={display} XAUTHORITY={xauth} xdotool key {key_str}"
        await asyncio.to_thread(self.client.exec_command, cmd)

    async def drag(self, path: list[tuple[int, int]]) -> None:
        await self._connect()
        display = ":0"
        xauth = f"/home/{self.username}/.Xauthority"
        if not path:
            return
        # Move to start
        x0, y0 = path[0]
        await self.move(x0, y0)
        # Mouse down
        await asyncio.to_thread(
            self.client.exec_command,
            f"DISPLAY={display} XAUTHORITY={xauth} xdotool mousedown 1",
        )
        # Move along path
        for x, y in path[1:]:
            await self.move(x, y)
            await asyncio.sleep(0.05)
        # Mouse up
        await asyncio.to_thread(
            self.client.exec_command,
            f"DISPLAY={display} XAUTHORITY={xauth} xdotool mouseup 1",
        )
