#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""透明悬浮笔记本：悬浮清晰可编辑，离开缩成可贴边小条。"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QCursor, QFont, QGuiApplication, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizeGrip,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

DATA_PATH = Path.home() / ".culinux" / "notebook_transparent.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "hover_opacity": 0.92,
    "leave_opacity": 0.12,
    "leave_width": 40,
    "leave_height": 120,
    "hover_geometry": [120, 120, 420, 520],
    "leave_pos": [40, 200],
    "note_text": "",
}


def loadConfig() -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if not DATA_PATH.is_file():
        return config
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            config.update(raw)
    except (OSError, json.JSONDecodeError):
        pass
    return config


def saveConfig(config: dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class SettingsDialog(QDialog):
    """设置：悬浮/离开透明度与离开尺寸。"""

    def __init__(self, config: dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("笔记本设置")
        self.setModal(True)
        self.setMinimumWidth(320)
        form = QFormLayout()
        self.hoverOpacity = QDoubleSpinBox()
        self.hoverOpacity.setRange(0.2, 1.0)
        self.hoverOpacity.setSingleStep(0.05)
        self.hoverOpacity.setDecimals(2)
        self.hoverOpacity.setValue(float(config.get("hover_opacity", 0.92)))
        self.leaveOpacity = QDoubleSpinBox()
        self.leaveOpacity.setRange(0.05, 0.5)
        self.leaveOpacity.setSingleStep(0.02)
        self.leaveOpacity.setDecimals(2)
        self.leaveOpacity.setValue(max(0.05, float(config.get("leave_opacity", 0.12))))
        self.leaveWidth = QSpinBox()
        self.leaveWidth.setRange(24, 200)
        self.leaveWidth.setValue(int(config.get("leave_width", 40)))
        self.leaveHeight = QSpinBox()
        self.leaveHeight.setRange(60, 400)
        self.leaveHeight.setValue(int(config.get("leave_height", 120)))
        form.addRow("悬浮透明度", self.hoverOpacity)
        form.addRow("离开透明度", self.leaveOpacity)
        form.addRow("离开宽度", self.leaveWidth)
        form.addRow("离开高度", self.leaveHeight)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root = QVBoxLayout(self)
        hint = QLabel("离开时缩成小条；悬浮时更清晰。离开透明度建议不低于 0.05，否则小条很难找到。")
        hint.setWordWrap(True)
        root.addWidget(hint)
        root.addLayout(form)
        root.addWidget(buttons)

    def values(self) -> dict[str, Any]:
        return {
            "hover_opacity": self.hoverOpacity.value(),
            "leave_opacity": self.leaveOpacity.value(),
            "leave_width": self.leaveWidth.value(),
            "leave_height": self.leaveHeight.value(),
        }


class TitleBar(QWidget):
    """可拖动标题栏。"""

    def __init__(self, host: "NotebookWindow") -> None:
        super().__init__(host)
        self.host = host
        self.dragOrigin: Optional[QPoint] = None
        self.setFixedHeight(36)
        self.setObjectName("titleBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 8, 4)
        self.title = QLabel("透明笔记本")
        self.title.setObjectName("titleLabel")
        layout.addWidget(self.title)
        layout.addStretch(1)
        self.btnSettings = QPushButton("设置")
        self.btnSettings.setObjectName("toolBtn")
        self.btnSettings.clicked.connect(host.openSettings)
        self.btnClose = QPushButton("×")
        self.btnClose.setObjectName("closeBtn")
        self.btnClose.setFixedSize(28, 28)
        self.btnClose.setToolTip("关闭")
        self.btnClose.clicked.connect(host.close)
        layout.addWidget(self.btnSettings)
        layout.addWidget(self.btnClose)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragOrigin = event.globalPosition().toPoint() - self.host.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.dragOrigin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.host.move(event.globalPosition().toPoint() - self.dragOrigin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.dragOrigin = None
        if self.host.isHoverMode:
            self.host.persistHoverGeometry()
        else:
            self.host.persistLeavePos()
        super().mouseReleaseEvent(event)


class LeaveStrip(QWidget):
    """离开态小条：可拖动改位置，带关闭按钮。"""

    def __init__(self, host: "NotebookWindow") -> None:
        super().__init__(host)
        self.host = host
        self.dragOrigin: Optional[QPoint] = None
        self.setObjectName("leaveStrip")
        self.setMinimumSize(24, 60)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(4)
        self.btnClose = QPushButton("×")
        self.btnClose.setObjectName("stripCloseBtn")
        self.btnClose.setFixedSize(22, 22)
        self.btnClose.setToolTip("关闭")
        self.btnClose.clicked.connect(host.close)
        label = QLabel("笔\n记")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("leaveLabel")
        layout.addWidget(self.btnClose, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(label, 1)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child is self.btnClose or (child is not None and self.btnClose.isAncestorOf(child)):
                return
            self.dragOrigin = event.globalPosition().toPoint() - self.host.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.dragOrigin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.host.move(event.globalPosition().toPoint() - self.dragOrigin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.dragOrigin = None
        self.host.persistLeavePos()
        super().mouseReleaseEvent(event)


class NotebookWindow(QMainWindow):
    """主窗口：悬浮 / 离开两态。"""

    def __init__(self) -> None:
        super().__init__()
        self.config = loadConfig()
        self.isHoverMode = True
        self.suppressLeave = False
        self.isSwitchingMode = False
        self.leaveTimer = QTimer(self)
        self.leaveTimer.setSingleShot(True)
        self.leaveTimer.setInterval(180)
        self.leaveTimer.timeout.connect(self.enterLeaveMode)
        self.setWindowTitle("透明笔记本")
        # 不用 Qt.Tool：macOS 上 Tool 窗口失焦会自动隐藏，看起来像「意外退出」
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, True)
        self.setMinimumSize(280, 200)
        self.buildUi()
        self.applyStyles()
        self.restoreHoverGeometry()
        self.setWindowOpacity(float(self.config["hover_opacity"]))
        self.editor.setPlainText(str(self.config.get("note_text", "")))
        self.editor.textChanged.connect(self.onTextChanged)

    def buildUi(self) -> None:
        self.root = QWidget()
        self.root.setObjectName("rootPanel")
        self.setCentralWidget(self.root)
        self.mainLayout = QVBoxLayout(self.root)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.titleBar = TitleBar(self)
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("noteEditor")
        self.editor.setPlaceholderText("在这里记点什么…")
        font = QFont("PingFang SC", 13)
        self.editor.setFont(font)
        self.footer = QWidget()
        footerLayout = QHBoxLayout(self.footer)
        footerLayout.setContentsMargins(8, 0, 4, 4)
        footerLayout.addStretch(1)
        self.sizeGrip = QSizeGrip(self.footer)
        footerLayout.addWidget(self.sizeGrip, 0, Qt.AlignmentFlag.AlignRight)
        self.leaveStrip = LeaveStrip(self)
        self.leaveStrip.hide()
        self.mainLayout.addWidget(self.titleBar)
        self.mainLayout.addWidget(self.editor, 1)
        self.mainLayout.addWidget(self.footer)
        self.mainLayout.addWidget(self.leaveStrip, 1)

    def applyStyles(self) -> None:
        self.setStyleSheet(
            """
            #rootPanel {
                background: rgba(250, 248, 242, 230);
                border: 1px solid rgba(40, 40, 40, 90);
                border-radius: 10px;
            }
            #titleBar {
                background: rgba(35, 35, 35, 210);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            #titleLabel {
                color: #f5f5f5;
                font-size: 13px;
                font-weight: 600;
            }
            #toolBtn, #closeBtn {
                background: rgba(255, 255, 255, 28);
                color: #fff;
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
            }
            #toolBtn:hover, #closeBtn:hover {
                background: rgba(255, 255, 255, 55);
            }
            #noteEditor {
                background: transparent;
                border: none;
                color: #222;
                padding: 10px 12px;
            }
            #leaveStrip {
                background: rgba(35, 35, 35, 220);
                border: 1px solid rgba(87, 191, 125, 180);
                border-radius: 10px;
            }
            #leaveLabel {
                color: #eee;
                font-size: 14px;
                font-weight: 600;
            }
            #stripCloseBtn {
                background: rgba(255, 255, 255, 35);
                color: #fff;
                border: none;
                border-radius: 11px;
                font-size: 14px;
                padding: 0;
            }
            #stripCloseBtn:hover {
                background: rgba(220, 60, 60, 200);
            }
            """
        )

    def restoreHoverGeometry(self) -> None:
        geo = self.config.get("hover_geometry", [120, 120, 420, 520])
        if isinstance(geo, list) and len(geo) == 4:
            self.setGeometry(int(geo[0]), int(geo[1]), int(geo[2]), int(geo[3]))
        else:
            self.resize(420, 520)

    def persistHoverGeometry(self) -> None:
        if self.isSwitchingMode or not self.isHoverMode:
            return
        g = self.geometry()
        if g.width() < 200 or g.height() < 160:
            return
        self.config["hover_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.flushConfig()

    def persistLeavePos(self) -> None:
        g = self.geometry()
        self.config["leave_pos"] = [g.x(), g.y()]
        self.flushConfig()

    def flushConfig(self) -> None:
        try:
            saveConfig(self.config)
        except OSError:
            traceback.print_exc()

    def onTextChanged(self) -> None:
        self.config["note_text"] = self.editor.toPlainText()
        self.flushConfig()

    def openSettings(self) -> None:
        self.suppressLeave = True
        self.leaveTimer.stop()
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.update(dialog.values())
            self.flushConfig()
            if self.isHoverMode:
                self.setWindowOpacity(float(self.config["hover_opacity"]))
            else:
                self.setWindowOpacity(max(0.05, float(self.config["leave_opacity"])))
                self.resize(
                    int(self.config["leave_width"]),
                    int(self.config["leave_height"]),
                )
        self.suppressLeave = False
        if self.isHoverMode and not self.frameGeometry().contains(QCursor.pos()):
            self.enterLeaveMode()

    def enterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.leaveTimer.stop()
        if not self.isHoverMode and not self.isSwitchingMode:
            self.enterHoverMode()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self.suppressLeave and self.isHoverMode and not self.isSwitchingMode:
            self.leaveTimer.start()
        super().leaveEvent(event)

    def changeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        # 失焦时不要藏窗；仅由鼠标离开触发缩小
        super().changeEvent(event)

    def enterHoverMode(self) -> None:
        if self.isSwitchingMode or self.isHoverMode:
            return
        self.isSwitchingMode = True
        try:
            leavePos = self.pos()
            self.isHoverMode = True
            self.leaveStrip.hide()
            self.titleBar.show()
            self.editor.show()
            self.footer.show()
            self.setMinimumSize(280, 200)
            geo = self.config.get("hover_geometry", [leavePos.x(), leavePos.y(), 420, 520])
            if isinstance(geo, list) and len(geo) == 4:
                width = max(280, int(geo[2]))
                height = max(200, int(geo[3]))
                x = leavePos.x()
                y = leavePos.y()
                screen = QGuiApplication.screenAt(leavePos) or QGuiApplication.primaryScreen()
                if screen is not None:
                    avail = screen.availableGeometry()
                    x = min(max(avail.left(), x), max(avail.left(), avail.right() - width))
                    y = min(max(avail.top(), y), max(avail.top(), avail.bottom() - height))
                self.setGeometry(x, y, width, height)
            self.setWindowOpacity(float(self.config["hover_opacity"]))
            self.show()
            self.raise_()
            self.editor.setFocus()
        finally:
            self.isSwitchingMode = False

    def enterLeaveMode(self) -> None:
        if self.suppressLeave or not self.isHoverMode or self.isSwitchingMode:
            return
        cursor = QCursor.pos()
        if self.frameGeometry().contains(cursor):
            return
        self.isSwitchingMode = True
        try:
            self.persistHoverGeometry()
            self.isHoverMode = False
            self.titleBar.hide()
            self.editor.hide()
            self.footer.hide()
            self.leaveStrip.show()
            self.setMinimumSize(24, 60)
            leaveW = int(self.config["leave_width"])
            leaveH = int(self.config["leave_height"])
            # 离开时就地缩小，避免跳到旧 leave_pos 导致找不到
            x, y = self.x(), self.y()
            screen = QGuiApplication.screenAt(QPoint(x, y)) or QGuiApplication.primaryScreen()
            if screen is not None:
                avail = screen.availableGeometry()
                x = min(max(avail.left(), x), max(avail.left(), avail.right() - leaveW))
                y = min(max(avail.top(), y), max(avail.top(), avail.bottom() - leaveH))
            self.setGeometry(x, y, leaveW, leaveH)
            self.setWindowOpacity(max(0.05, float(self.config["leave_opacity"])))
            self.config["leave_pos"] = [x, y]
            self.flushConfig()
            self.show()
            self.raise_()
        finally:
            self.isSwitchingMode = False

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.isHoverMode:
            self.persistHoverGeometry()
        else:
            self.persistLeavePos()
        self.config["note_text"] = self.editor.toPlainText()
        self.flushConfig()
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if self.isHoverMode and self.isVisible() and not self.isSwitchingMode:
            QTimer.singleShot(200, self.persistHoverGeometry)


def main() -> int:
    def handleException(excType, excValue, excTraceback) -> None:  # type: ignore[no-untyped-def]
        traceback.print_exception(excType, excValue, excTraceback)

    sys.excepthook = handleException
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = NotebookWindow()
    window.show()
    window.raise_()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
