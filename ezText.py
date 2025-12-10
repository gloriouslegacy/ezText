import sys
import os
import configparser
import winreg
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QMenu, QFileDialog, QCheckBox, QSystemTrayIcon)
from PyQt6.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QPalette, QColor, QFont, QAction, QIcon
import keyboard
import darkdetect
from updater import AutoUpdater

# Application version
VERSION = "1.0.0"


class UpdateCheckThread(QThread):
    """Thread for checking updates without blocking UI"""
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, updater):
        super().__init__()
        self.updater = updater

    def run(self):
        try:
            available, release_info = self.updater.check_for_updates()
            if available:
                self.update_available.emit(release_info)
            else:
                self.no_update.emit()
        except Exception as e:
            self.error.emit(str(e))


class TextShortcutApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Settings file in %LOCALAPPDATA%
        self.settings = QSettings('gloriouslegacy', 'ezText')

        # Initialize updater
        self.updater = AutoUpdater(
            current_version=VERSION,
            repo_owner='gloriouslegacy',
            repo_name='ezText'
        )

        # Load saved language or default to Korean
        self.current_language = self.settings.value('language', 'ko')

        # Load last opened file or use default
        self.config_file = self.settings.value('last_file', 'ezTextShortcut.ini')
        self.shortcuts_dict = {}
        self.active_shortcuts = []

        # System tray icon (will be initialized after translations)
        self.tray_icon = None
        
        # Windows system reserved shortcuts
        self.reserved_shortcuts = {
            'ctrl+c', 'ctrl+v', 'ctrl+x', 'ctrl+z', 'ctrl+y', 'ctrl+a', 
            'ctrl+s', 'ctrl+n', 'ctrl+o', 'ctrl+p', 'ctrl+w', 'ctrl+q',
            'ctrl+f', 'ctrl+h', 'alt+f4', 'alt+tab', 'win+d', 'win+e',
            'win+r', 'win+l', 'win+i', 'win+s', 'win+x', 'win+tab',
            'ctrl+alt+del', 'ctrl+shift+esc', 'win+p', 'win+k'
        }
        
        self.translations = {
            'ko': {
                'title': 'ezText',
                'text': '텍스트',
                'shortcut': '단축키',
                'add': '추가',
                'delete': '선택 삭제',
                'delete_all': '전체 삭제',
                'select_all': '전체 선택',
                'deselect_all': '선택 해제',
                'new': '새로 만들기',
                'save': '저장',
                'save_as': '다른 이름으로 저장',
                'load': '불러오기',
                'exit': '종료',
                'language': '언어',
                'autostart': '자동 실행',
                'enable_autostart': '시작프로그램 등록',
                'disable_autostart': '시작프로그램 해제',
                'file': '파일',
                'settings': '설정',
                'help': '도움말',
                'check_update': '업데이트 확인',
                'visit_github': 'GitHub 방문',
                'error': '오류',
                'success': '성공',
                'warning': '경고',
                'reserved_shortcut': '이 단축키는 Windows 시스템 예약 단축키입니다.',
                'duplicate_shortcut': '이 단축키는 이미 사용 중입니다.',
                'empty_fields': '텍스트와 단축키를 모두 입력해주세요.',
                'saved': '단축키가 저장되었습니다.',
                'saved_as': '{0}에 저장되었습니다.',
                'loaded': '단축키를 불러왔습니다.',
                'autostart_enabled': '자동 실행이 등록되었습니다.',
                'autostart_disabled': '자동 실행이 해제되었습니다.',
                'record_shortcut': '단축키 입력... (Esc로 취소)',
                'press_keys': '단축키를 눌러주세요',
                'shortcut_added': '단축키가 추가되었습니다: {0}',
                'shortcut_deleted': '{0}개의 단축키가 삭제되었습니다.',
                'all_deleted': '모든 단축키가 삭제되었습니다.',
                'no_selection': '삭제할 항목을 선택해주세요.',
                'confirm_delete_all': '모든 단축키를 삭제하시겠습니까?',
                'confirm_delete_selected': '선택한 {0}개의 단축키를 삭제하시겠습니까?',
                'confirm_new': '저장하지 않은 변경사항이 있을 수 있습니다. 새 파일을 만드시겠습니까?',
                'exit_title': 'ezText 종료',
                'exit_message': 'ezText를 종료하시겠습니까?',
                'exit_button': '종료',
                'minimize_to_tray': '트레이 아이콘으로 최소화',
                'cancel': '취소',
                'minimized_to_tray': '트레이 아이콘으로 최소화되었습니다. 아이콘을 더블클릭하면 복원됩니다.',
                'github_url': 'https://github.com/gloriouslegacy/ezText',
            },
            'en': {
                'title': 'ezText',
                'text': 'Text',
                'shortcut': 'Shortcut',
                'add': 'Add',
                'delete': 'Delete Selected',
                'delete_all': 'Delete All',
                'select_all': 'Select All',
                'deselect_all': 'Deselect All',
                'new': 'New',
                'save': 'Save',
                'save_as': 'Save As',
                'load': 'Load',
                'exit': 'Exit',
                'language': 'Language',
                'autostart': 'Auto Start',
                'enable_autostart': 'Enable Autostart',
                'disable_autostart': 'Disable Autostart',
                'file': 'File',
                'settings': 'Settings',
                'help': 'Help',
                'check_update': 'Check for Updates',
                'visit_github': 'Visit GitHub',
                'error': 'Error',
                'success': 'Success',
                'warning': 'Warning',
                'reserved_shortcut': 'This shortcut is reserved by Windows system.',
                'duplicate_shortcut': 'This shortcut is already in use.',
                'empty_fields': 'Please enter both text and shortcut.',
                'saved': 'Shortcuts have been saved.',
                'saved_as': 'Saved to {0}.',
                'loaded': 'Shortcuts have been loaded.',
                'autostart_enabled': 'Autostart has been enabled.',
                'autostart_disabled': 'Autostart has been disabled.',
                'record_shortcut': 'Recording shortcut... (Esc to cancel)',
                'press_keys': 'Press shortcut keys',
                'shortcut_added': 'Shortcut added: {0}',
                'shortcut_deleted': '{0} shortcut(s) deleted.',
                'all_deleted': 'All shortcuts have been deleted.',
                'no_selection': 'Please select an item to delete.',
                'confirm_delete_all': 'Are you sure you want to delete all shortcuts?',
                'confirm_delete_selected': 'Are you sure you want to delete {0} selected shortcut(s)?',
                'confirm_new': 'You may have unsaved changes. Create a new file?',
                'exit_title': 'Exit ezText',
                'exit_message': 'Do you want to exit ezText?',
                'exit_button': 'Exit',
                'minimize_to_tray': 'Minimize to Tray',
                'cancel': 'Cancel',
                'minimized_to_tray': 'Minimized to system tray. Double-click the icon to restore.',
                'github_url': 'https://github.com/gloriouslegacy/ezText',
            }
        }
        
        self.init_ui()
        self.apply_theme()
        self.setup_tray_icon()
        self.load_shortcuts()

        # Check for updates on startup (silent)
        self.check_for_updates_silent()
        
    def tr(self, key):
        """Get translated text"""
        return self.translations[self.current_language].get(key, key)
    
    def log_status(self, message, duration=3000):
        """Log message to status bar"""
        self.status_bar.showMessage(message, duration)
    
    def setup_tray_icon(self):
        """Setup system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon', 'ezText.ico')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction(self.tr('title'))
        show_action.triggered.connect(self.show_from_tray)
        
        tray_menu.addSeparator()
        
        exit_action = tray_menu.addAction(self.tr('exit'))
        exit_action.triggered.connect(self.exit_app)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()
    
    def show_from_tray(self):
        """Show window from system tray"""
        self.show()
        self.activateWindow()
    
    def minimize_to_tray(self):
        """Minimize to system tray"""
        self.hide()
        self.tray_icon.show()
        self.tray_icon.showMessage(
            self.tr('title'),
            self.tr('minimized_to_tray'),
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    
    def new_file(self):
        """Create a new file"""
        reply = QMessageBox.question(
            self,
            self.tr('warning'),
            self.tr('confirm_new'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear all shortcuts
            for shortcut in list(self.active_shortcuts):
                self.unregister_hotkey(shortcut)
            
            self.shortcuts_dict.clear()
            self.table.setRowCount(0)
            
            # Reset to default config file
            self.config_file = 'ezTextShortcut.ini'
            
            self.log_status("New file created")
    
    def on_text_mouse_press(self, event):
        """Handle text input mouse press"""
        # If shortcut input has focus, clear it first
        if self.shortcut_input.hasFocus():
            self.shortcut_input.clearFocus()
        
        # Then allow text input to receive focus
        self.original_text_mouse_press(event)
    
    def on_text_input_focus(self, event):
        """Handle text input focus - visually indicate shortcut input is inactive"""
        # Don't disable, just style it to look inactive
        is_dark = darkdetect.isDark()
        inactive_bg = "#1a1a1a" if is_dark else "#e0e0e0"
        self.shortcut_input.setStyleSheet(f"QLineEdit {{ background-color: {inactive_bg}; }}")
        QLineEdit.focusInEvent(self.text_input, event)
    
    def on_text_input_focus_out(self, event):
        """Handle text input focus out - restore shortcut input styling"""
        self.shortcut_input.setStyleSheet("")
        QLineEdit.focusOutEvent(self.text_input, event)
    
    def on_shortcut_mouse_press(self, event):
        """Handle shortcut input mouse press"""
        # Only allow if text input is not focused
        if self.text_input.hasFocus():
            # If text input has focus, clear it first
            self.text_input.clearFocus()
        
        # Call original mouse press to set focus
        self.original_shortcut_mouse_press(event)
        # Then start recording shortcut
        self.record_shortcut(event)
    
    def on_shortcut_input_focus(self, event):
        """Handle shortcut input focus - visually indicate text input is inactive"""
        # Don't disable, just style it to look inactive
        is_dark = darkdetect.isDark()
        inactive_bg = "#1a1a1a" if is_dark else "#e0e0e0"
        self.text_input.setStyleSheet(f"QLineEdit {{ background-color: {inactive_bg}; }}")
        QLineEdit.focusInEvent(self.shortcut_input, event)
    
    def on_shortcut_input_focus_out(self, event):
        """Handle shortcut input focus out - restore text input styling"""
        self.text_input.setStyleSheet("")
        QLineEdit.focusOutEvent(self.shortcut_input, event)
    
    def init_ui(self):
        self.setWindowTitle(self.tr('title'))
        
        # Restore window geometry or use default
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.setGeometry(100, 100, 800, 600)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon', 'ezText.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Menu bar
        self.create_menu_bar()
        
        # Status bar for logs
        self.status_bar = self.statusBar()
        self.status_bar.setFont(QFont('Segoe UI', 9))
        
        # Input section
        input_layout = QHBoxLayout()
        
        # Text input
        text_label = QLabel(self.tr('text') + ':')
        text_label.setFont(QFont('Segoe UI', 10))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText(self.tr('text'))
        self.text_input.setFont(QFont('Segoe UI', 10))
        self.text_input.setMinimumHeight(35)
        
        # Store original event handlers
        self.original_text_mouse_press = self.text_input.mousePressEvent
        self.original_text_focus_in = self.text_input.focusInEvent
        self.original_text_focus_out = self.text_input.focusOutEvent
        
        # Override event handlers
        self.text_input.mousePressEvent = self.on_text_mouse_press
        self.text_input.focusInEvent = self.on_text_input_focus
        self.text_input.focusOutEvent = self.on_text_input_focus_out
        
        # Shortcut input
        shortcut_label = QLabel(self.tr('shortcut') + ':')
        shortcut_label.setFont(QFont('Segoe UI', 10))
        self.shortcut_input = QLineEdit()
        self.shortcut_input.setPlaceholderText(self.tr('press_keys'))
        self.shortcut_input.setFont(QFont('Segoe UI', 10))
        self.shortcut_input.setMinimumHeight(35)
        self.shortcut_input.setReadOnly(True)
        
        # Store original event handlers
        self.original_shortcut_mouse_press = self.shortcut_input.mousePressEvent
        self.original_shortcut_focus_in = self.shortcut_input.focusInEvent
        self.original_shortcut_focus_out = self.shortcut_input.focusOutEvent
        
        # Override event handlers
        self.shortcut_input.mousePressEvent = self.on_shortcut_mouse_press
        self.shortcut_input.focusInEvent = self.on_shortcut_input_focus
        self.shortcut_input.focusOutEvent = self.on_shortcut_input_focus_out
        
        input_layout.addWidget(text_label)
        input_layout.addWidget(self.text_input, 2)
        input_layout.addWidget(shortcut_label)
        input_layout.addWidget(self.shortcut_input, 2)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton(self.tr('add'))
        self.add_button.setFont(QFont('Segoe UI', 10))
        self.add_button.setMinimumHeight(35)
        self.add_button.clicked.connect(self.add_shortcut)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.delete_button = QPushButton(self.tr('delete'))
        self.delete_button.setFont(QFont('Segoe UI', 10))
        self.delete_button.setMinimumHeight(35)
        self.delete_button.clicked.connect(self.delete_selected_shortcuts)
        self.delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.delete_all_button = QPushButton(self.tr('delete_all'))
        self.delete_all_button.setFont(QFont('Segoe UI', 10))
        self.delete_all_button.setMinimumHeight(35)
        self.delete_all_button.clicked.connect(self.delete_all_shortcuts)
        self.delete_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.select_all_button = QPushButton(self.tr('select_all'))
        self.select_all_button.setFont(QFont('Segoe UI', 10))
        self.select_all_button.setMinimumHeight(35)
        self.select_all_button.clicked.connect(self.select_all)
        self.select_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.deselect_all_button = QPushButton(self.tr('deselect_all'))
        self.deselect_all_button.setFont(QFont('Segoe UI', 10))
        self.deselect_all_button.setMinimumHeight(35)
        self.deselect_all_button.clicked.connect(self.deselect_all)
        self.deselect_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.delete_all_button)
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.deselect_all_button)
        button_layout.addStretch()
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['', self.tr('text'), self.tr('shortcut')])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setFont(QFont('Segoe UI', 10))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.itemChanged.connect(self.on_item_changed)  # Connect item change signal
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)  # Enable double-click editing
        self.table.verticalHeader().setVisible(False)  # Hide row numbers
        
        # Add layouts to main layout
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.table)
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setFont(QFont('Segoe UI', 10))
        
        # File menu
        file_menu = menubar.addMenu(self.tr('file'))
        
        new_action = QAction(self.tr('new'), self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        save_action = QAction(self.tr('save'), self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_shortcuts)
        file_menu.addAction(save_action)
        
        save_as_action = QAction(self.tr('save_as'), self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_shortcuts_as)
        file_menu.addAction(save_as_action)
        
        load_action = QAction(self.tr('load'), self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_shortcuts_dialog)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(self.tr('exit'), self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu(self.tr('settings'))
        
        # Language submenu
        language_menu = QMenu(self.tr('language'), self)
        
        korean_action = QAction('한국어', self)
        korean_action.triggered.connect(lambda: self.change_language('ko'))
        language_menu.addAction(korean_action)
        
        english_action = QAction('English', self)
        english_action.triggered.connect(lambda: self.change_language('en'))
        language_menu.addAction(english_action)
        
        settings_menu.addMenu(language_menu)
        
        # Autostart submenu
        autostart_menu = QMenu(self.tr('autostart'), self)
        
        enable_autostart_action = QAction(self.tr('enable_autostart'), self)
        enable_autostart_action.triggered.connect(lambda: self.set_autostart(True))
        autostart_menu.addAction(enable_autostart_action)
        
        disable_autostart_action = QAction(self.tr('disable_autostart'), self)
        disable_autostart_action.triggered.connect(lambda: self.set_autostart(False))
        autostart_menu.addAction(disable_autostart_action)
        
        settings_menu.addMenu(autostart_menu)
        
        # Help menu
        help_menu = menubar.addMenu(self.tr('help'))
        
        check_update_action = QAction(self.tr('check_update'), self)
        check_update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_update_action)
        
        visit_github_action = QAction(self.tr('visit_github'), self)
        visit_github_action.triggered.connect(self.visit_github)
        help_menu.addAction(visit_github_action)
    
    def apply_theme(self):
        is_dark = darkdetect.isDark()
        
        if is_dark:
            # Dark theme colors 
            bg_color = "#202020"
            surface_color = "#2b2b2b"
            text_color = "#ffffff"
            border_color = "#3d3d3d"
            hover_color = "#363636"
            accent_color = "#0078d4"
            table_alternate = "#252525"
        else:
            # Light theme colors
            bg_color = "#f3f3f3"
            surface_color = "#ffffff"
            text_color = "#000000"
            border_color = "#e0e0e0"
            hover_color = "#e8e8e8"
            accent_color = "#0067c0"
            table_alternate = "#f9f9f9"
        
        style = f"""
            QMainWindow {{
                background-color: {bg_color};
            }}
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
                font-family: 'Segoe UI';
            }}
            QLineEdit {{
                background-color: {surface_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px 10px;
                color: {text_color};
                min-height: 25px;
            }}
            QLineEdit:focus {{
                border: 2px solid {accent_color};
                background-color: {surface_color};
            }}
            QLineEdit:disabled {{
                background-color: {bg_color};
                color: {border_color};
                border: 1px solid {border_color};
            }}
            QLineEdit[readOnly="true"] {{
                background-color: {surface_color};
                color: {text_color};
            }}
            QLineEdit[readOnly="true"]:disabled {{
                background-color: {bg_color};
                color: {border_color};
            }}
            QPushButton {{
                background-color: {surface_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 8px 15px;
                color: {text_color};
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {border_color};
            }}
            QTableWidget {{
                background-color: {surface_color};
                alternate-background-color: {table_alternate};
                border: 1px solid {border_color};
                border-radius: 4px;
                gridline-color: {border_color};
                color: {text_color};
            }}
            QTableWidget::item {{
                padding: 8px;
                border: none;
            }}
            QTableWidget::item:hover {{
                background-color: {hover_color};
            }}
            QTableWidget::item:focus {{
                background-color: transparent;
                outline: none;
            }}
            QHeaderView::section {{
                background-color: {surface_color};
                border: 1px solid {border_color};
                padding: 8px;
                font-weight: bold;
                color: {text_color};
            }}
            QMenuBar {{
                background-color: {bg_color};
                color: {text_color};
                border-bottom: 1px solid {border_color};
            }}
            QMenuBar::item:selected {{
                background-color: {hover_color};
            }}
            QMenu {{
                background-color: {surface_color};
                border: 1px solid {border_color};
                color: {text_color};
            }}
            QMenu::item:selected {{
                background-color: {hover_color};
            }}
            QLabel {{
                color: {text_color};
                background-color: transparent;
            }}
            QCheckBox {{
                color: {text_color};
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid {border_color};
                background-color: {surface_color};
            }}
            QCheckBox::indicator:hover {{
                border-color: #10a37f;
            }}
            QCheckBox::indicator:checked {{
                background-color: #10a37f;
                border-color: #10a37f;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
            }}
        """
        self.setStyleSheet(style)
    
    def record_shortcut(self, event):
        """Record keyboard shortcut"""
        # Don't start recording if text input has focus
        if self.text_input.hasFocus():
            return
        
        self.shortcut_input.setText(self.tr('record_shortcut'))
        is_dark = darkdetect.isDark()
        recording_bg = "#4a4a2a" if is_dark else "#ffebcd"
        current_style = self.shortcut_input.styleSheet()
        self.shortcut_input.setStyleSheet(f"{current_style} QLineEdit {{ background-color: {recording_bg}; border: 2px solid #ffa500; }}")
        
        recorded_keys = set()
        key_mapping = {
            'left ctrl': 'ctrl',
            'right ctrl': 'ctrl',
            'left shift': 'shift',
            'right shift': 'shift',
            'left alt': 'alt',
            'right alt': 'alt',
            'left windows': 'win',
            'right windows': 'win',
        }
        
        def normalize_key(key_name):
            """Normalize key names"""
            key_lower = key_name.lower()
            return key_mapping.get(key_lower, key_name.lower())
        
        def on_key_event(e):
            if e.event_type == 'down':
                if e.name == 'esc':
                    keyboard.unhook_all()
                    self.shortcut_input.setText('')
                    self.shortcut_input.setStyleSheet("")
                    return
                
                key = normalize_key(e.name)
                recorded_keys.add(key)
                
                # Build shortcut string with proper order
                modifier_order = ['ctrl', 'alt', 'shift', 'win']
                modifiers = [k for k in modifier_order if k in recorded_keys]
                others = sorted([k for k in recorded_keys if k not in modifier_order])
                
                shortcut_list = modifiers + others
                shortcut_str = '+'.join(shortcut_list)
                self.shortcut_input.setText(shortcut_str)
        
        def on_key_up(e):
            if len(recorded_keys) > 0:
                keyboard.unhook_all()
                self.shortcut_input.setStyleSheet("")
        
        keyboard.on_press(on_key_event)
        keyboard.on_release(on_key_up, suppress=False)
    
    def add_shortcut(self):
        """Add new shortcut"""
        text = self.text_input.text().strip()
        shortcut = self.shortcut_input.text().strip()
        
        if not text or not shortcut:
            self.log_status(self.tr('empty_fields'))
            return
        
        # Check if shortcut is reserved
        if shortcut.lower() in self.reserved_shortcuts:
            self.log_status(self.tr('reserved_shortcut'))
            return
        
        # Check if shortcut already exists
        if shortcut in self.shortcuts_dict:
            self.log_status(self.tr('duplicate_shortcut'))
            return
        
        # Add to dictionary and table
        self.shortcuts_dict[shortcut] = text
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Temporarily disconnect signal to prevent triggering during setup
        self.table.itemChanged.disconnect(self.on_item_changed)
        
        # Add checkbox
        checkbox = QCheckBox()
        checkbox.setStyleSheet("QCheckBox { margin-left: 7px; }")
        self.table.setCellWidget(row, 0, checkbox)
        
        # Add text - editable
        text_item = QTableWidgetItem(text)
        self.table.setItem(row, 1, text_item)
        
        # Add shortcut - editable
        shortcut_item = QTableWidgetItem(shortcut)
        self.table.setItem(row, 2, shortcut_item)
        
        # Reconnect signal
        self.table.itemChanged.connect(self.on_item_changed)
        
        # Register hotkey
        self.register_hotkey(shortcut, text)
        
        # Clear inputs
        self.text_input.clear()
        self.shortcut_input.clear()
        
        # Auto save
        self.save_shortcuts(silent=True)
        
        # Log status
        self.log_status(self.tr('shortcut_added').format(shortcut))
    
    def on_item_changed(self, item):
        """Handle table item changes (editing)"""
        if item is None:
            return
        
        row = item.row()
        col = item.column()
        
        # Get old and new values
        if col == 1:  # Text column
            old_shortcut = self.table.item(row, 2).text()
            new_text = item.text().strip()
            
            if not new_text:
                self.log_status(self.tr('empty_fields'))
                # Restore old value
                self.table.itemChanged.disconnect(self.on_item_changed)
                item.setText(self.shortcuts_dict[old_shortcut])
                self.table.itemChanged.connect(self.on_item_changed)
                return
            
            # Update dictionary
            self.shortcuts_dict[old_shortcut] = new_text
            
            # Re-register hotkey with new text
            self.unregister_hotkey(old_shortcut)
            self.register_hotkey(old_shortcut, new_text)
            
        elif col == 2:  # Shortcut column
            old_shortcut = None
            # Find old shortcut
            for sc in self.shortcuts_dict.keys():
                if self.shortcuts_dict[sc] == self.table.item(row, 1).text():
                    old_shortcut = sc
                    break
            
            new_shortcut = item.text().strip()
            
            if not new_shortcut:
                self.log_status(self.tr('empty_fields'))
                # Restore old value
                self.table.itemChanged.disconnect(self.on_item_changed)
                item.setText(old_shortcut)
                self.table.itemChanged.connect(self.on_item_changed)
                return
            
            # Check if new shortcut is reserved
            if new_shortcut.lower() in self.reserved_shortcuts:
                self.log_status(self.tr('reserved_shortcut'))
                # Restore old value
                self.table.itemChanged.disconnect(self.on_item_changed)
                item.setText(old_shortcut)
                self.table.itemChanged.connect(self.on_item_changed)
                return
            
            # Check if new shortcut already exists (but not the same row)
            if new_shortcut in self.shortcuts_dict and new_shortcut != old_shortcut:
                self.log_status(self.tr('duplicate_shortcut'))
                # Restore old value
                self.table.itemChanged.disconnect(self.on_item_changed)
                item.setText(old_shortcut)
                self.table.itemChanged.connect(self.on_item_changed)
                return
            
            # Update dictionary
            text = self.shortcuts_dict.pop(old_shortcut)
            self.shortcuts_dict[new_shortcut] = text
            
            # Re-register hotkey
            self.unregister_hotkey(old_shortcut)
            self.register_hotkey(new_shortcut, text)
        
        # Auto save
        self.save_shortcuts(silent=True)
        self.log_status("Updated successfully")
    
    def delete_selected_shortcuts(self):
        """Delete selected shortcuts"""
        selected_rows = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_rows.append(row)
        
        if not selected_rows:
            self.log_status(self.tr('no_selection'))
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            self.tr('warning'),
            self.tr('confirm_delete_selected').format(len(selected_rows)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete in reverse order to maintain correct indices
            for row in reversed(selected_rows):
                shortcut = self.table.item(row, 2).text()
                
                # Unregister hotkey
                self.unregister_hotkey(shortcut)
                
                # Remove from dictionary
                del self.shortcuts_dict[shortcut]
                
                # Remove from table
                self.table.removeRow(row)
            
            # Auto save
            self.save_shortcuts(silent=True)
            
            # Log status
            self.log_status(self.tr('shortcut_deleted').format(len(selected_rows)))
    
    def select_all(self):
        """Select all checkboxes"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def deselect_all(self):
        """Deselect all checkboxes"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def delete_all_shortcuts(self):
        """Delete all shortcuts"""
        if self.table.rowCount() == 0:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            self.tr('warning'),
            self.tr('confirm_delete_all'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Unregister all hotkeys
            for shortcut in list(self.active_shortcuts):
                self.unregister_hotkey(shortcut)
            
            # Clear dictionary and table
            self.shortcuts_dict.clear()
            self.table.setRowCount(0)
            
            # Auto save
            self.save_shortcuts(silent=True)
            
            # Log status
            self.log_status(self.tr('all_deleted'))
    
    def register_hotkey(self, shortcut, text):
        """Register keyboard hotkey"""
        try:
            def callback():
                # Don't trigger if any input field in the app has focus
                focused_widget = QApplication.focusWidget()
                if focused_widget and (
                    isinstance(focused_widget, QLineEdit) or 
                    self.text_input.hasFocus() or 
                    self.shortcut_input.hasFocus()
                ):
                    return
                keyboard.write(text)
            
            keyboard.add_hotkey(shortcut, callback)
            self.active_shortcuts.append(shortcut)
        except Exception as e:
            print(f"Error registering hotkey {shortcut}: {e}")
    
    def unregister_hotkey(self, shortcut):
        """Unregister keyboard hotkey"""
        try:
            keyboard.remove_hotkey(shortcut)
            if shortcut in self.active_shortcuts:
                self.active_shortcuts.remove(shortcut)
        except Exception as e:
            print(f"Error unregistering hotkey {shortcut}: {e}")
    
    def save_shortcuts(self, silent=False):
        """Save shortcuts to ini file"""
        config = configparser.ConfigParser()
        
        for shortcut, text in self.shortcuts_dict.items():
            config[shortcut] = {'text': text}
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)
        
        if not silent:
            self.log_status(self.tr('saved'))
    
    def save_shortcuts_as(self):
        """Save shortcuts to a new file with dialog"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr('save_as'),
            '',
            'INI Files (*.ini)'
        )
        
        if file_path:
            # Ensure .ini extension
            if not file_path.endswith('.ini'):
                file_path += '.ini'
            
            config = configparser.ConfigParser()
            
            for shortcut, text in self.shortcuts_dict.items():
                config[shortcut] = {'text': text}
            
            with open(file_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            # Update current config file path
            self.config_file = file_path
            
            # Save last opened file path
            self.settings.setValue('last_file', file_path)
            
            # Log status with filename
            filename = os.path.basename(file_path)
            self.log_status(self.tr('saved_as').format(filename))
    
    def load_shortcuts(self):
        """Load shortcuts from ini file"""
        if not os.path.exists(self.config_file):
            return
        
        config = configparser.ConfigParser()
        config.read(self.config_file, encoding='utf-8')
        
        # Clear existing shortcuts
        for shortcut in list(self.active_shortcuts):
            self.unregister_hotkey(shortcut)
        
        self.shortcuts_dict.clear()
        self.table.setRowCount(0)
        
        # Temporarily disconnect signal
        self.table.itemChanged.disconnect(self.on_item_changed)
        
        # Load shortcuts
        for idx, shortcut in enumerate(config.sections()):
            text = config[shortcut]['text']
            self.shortcuts_dict[shortcut] = text
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Add checkbox
            checkbox = QCheckBox()
            checkbox.setStyleSheet("QCheckBox { margin-left: 7px; }")
            self.table.setCellWidget(row, 0, checkbox)
            
            # Add text - editable
            text_item = QTableWidgetItem(text)
            self.table.setItem(row, 1, text_item)
            
            # Add shortcut - editable
            shortcut_item = QTableWidgetItem(shortcut)
            self.table.setItem(row, 2, shortcut_item)
            
            self.register_hotkey(shortcut, text)
        
        # Reconnect signal
        self.table.itemChanged.connect(self.on_item_changed)
    
    def load_shortcuts_dialog(self):
        """Load shortcuts with dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            self.tr('load'), 
            '', 
            'INI Files (*.ini)'
        )
        
        if file_path:
            self.config_file = file_path
            
            # Save last opened file path
            self.settings.setValue('last_file', file_path)
            
            self.load_shortcuts()
            self.log_status(self.tr('loaded'))
    
    def change_language(self, lang):
        """Change application language"""
        self.current_language = lang
        
        # Save language preference
        self.settings.setValue('language', lang)
        
        self.update_ui_text()
        self.log_status(f"Language changed to {'한국어' if lang == 'ko' else 'English'}")
    
    def update_ui_text(self):
        """Update all UI text based on current language"""
        self.setWindowTitle(self.tr('title'))
        self.text_input.setPlaceholderText(self.tr('text'))
        self.shortcut_input.setPlaceholderText(self.tr('press_keys'))
        self.add_button.setText(self.tr('add'))
        self.delete_button.setText(self.tr('delete'))
        self.delete_all_button.setText(self.tr('delete_all'))
        self.select_all_button.setText(self.tr('select_all'))
        self.deselect_all_button.setText(self.tr('deselect_all'))
        self.table.setHorizontalHeaderLabels(['', self.tr('text'), self.tr('shortcut')])
        
        # Recreate menu bar
        self.menuBar().clear()
        self.create_menu_bar()
    
    def set_autostart(self, enable):
        """Enable or disable autostart on Windows login"""
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "TextShortcutApp"
            app_path = os.path.abspath(sys.argv[0])
            
            # If running as .py file, use pythonw.exe to run without console
            if app_path.endswith('.py'):
                python_path = sys.executable.replace('python.exe', 'pythonw.exe')
                app_path = f'"{python_path}" "{app_path}"'
            else:
                app_path = f'"{app_path}"'
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
                self.settings.setValue('autostart', True)
                self.log_status(self.tr('autostart_enabled'))
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    self.settings.setValue('autostart', False)
                    self.log_status(self.tr('autostart_disabled'))
                except FileNotFoundError:
                    pass
            
            winreg.CloseKey(key)
        except Exception as e:
            self.log_status(f"{self.tr('error')}: {str(e)}")
    
    def check_for_updates_silent(self):
        """Check for updates silently on startup"""
        self.update_thread = UpdateCheckThread(self.updater)
        self.update_thread.update_available.connect(self.on_update_available_silent)
        self.update_thread.start()

    def on_update_available_silent(self, release_info):
        """Handle update available (silent check on startup)"""
        if self.tray_icon:
            self.tray_icon.showMessage(
                self.tr('title'),
                f"New version {release_info['version']} is available!",
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )

    def check_for_updates(self):
        """Check for updates manually from menu"""
        self.log_status("Checking for updates...")

        self.update_thread = UpdateCheckThread(self.updater)
        self.update_thread.update_available.connect(self.on_update_available)
        self.update_thread.no_update.connect(self.on_no_update)
        self.update_thread.error.connect(self.on_update_error)
        self.update_thread.start()

    def on_update_available(self, release_info):
        """Handle update available"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Update Available")
        msg.setText(f"A new version ({release_info['version']}) is available!\n\nCurrent version: {VERSION}")
        msg.setInformativeText("Do you want to download and install the update?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        result = msg.exec()

        if result == QMessageBox.StandardButton.Yes:
            if release_info['download_url']:
                self.log_status("Downloading update...")
                success = self.updater.download_and_install(release_info['download_url'])
                if success:
                    QMessageBox.information(
                        self,
                        "Update",
                        "Update downloaded. The installer will run now.\nPlease close this application to complete the update."
                    )
                    # Exit to allow installer to run
                    self.exit_app()
                else:
                    QMessageBox.warning(self, "Update Error", "Failed to download update.")
            else:
                # Open releases page if no direct download
                webbrowser.open(release_info['html_url'])

    def on_no_update(self):
        """Handle no update available"""
        QMessageBox.information(
            self,
            "Up to Date",
            f"You are already using the latest version ({VERSION})."
        )
        self.log_status("No updates available")

    def on_update_error(self, error_msg):
        """Handle update check error"""
        QMessageBox.warning(
            self,
            "Update Check Failed",
            f"Could not check for updates.\n\nError: {error_msg}"
        )
        self.log_status("Update check failed")
    
    def visit_github(self):
        """Visit GitHub repository"""
        github_url = self.tr('github_url')
        webbrowser.open(github_url)
        self.log_status("Opening GitHub repository...")
    
    def exit_app(self):
        """Exit the application completely"""
        # Save window geometry
        self.settings.setValue('geometry', self.saveGeometry())
        
        # Cleanup hotkeys
        for shortcut in list(self.active_shortcuts):
            self.unregister_hotkey(shortcut)
        
        # Hide tray icon
        if self.tray_icon:
            self.tray_icon.hide()
        
        # Quit application
        QApplication.quit()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Create custom message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.tr('exit_title'))
        msg_box.setText(self.tr('exit_message'))
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # Add custom buttons
        exit_button = msg_box.addButton(self.tr('exit_button'), QMessageBox.ButtonRole.AcceptRole)
        tray_button = msg_box.addButton(self.tr('minimize_to_tray'), QMessageBox.ButtonRole.ActionRole)
        cancel_button = msg_box.addButton(self.tr('cancel'), QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        
        if clicked_button == exit_button:
            # Exit application
            event.accept()
            self.exit_app()
        elif clicked_button == tray_button:
            # Minimize to tray
            event.ignore()
            self.minimize_to_tray()
        else:
            # Cancel
            event.ignore()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = TextShortcutApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
