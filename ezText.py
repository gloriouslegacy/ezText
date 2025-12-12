import sys
import os
import configparser
import winreg
import webbrowser
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QMenu, QFileDialog, QCheckBox, QSystemTrayIcon,
                             QComboBox)
from PyQt6.QtCore import Qt, QSettings, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QPalette, QColor, QFont, QAction, QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
import keyboard
import darkdetect
from updater import AutoUpdater

# Application version - automatically set during build
def get_version():
    """Get application version from version.txt or default"""
    try:
        version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'version.txt')
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception:
        pass
    # Default version for development
    return "0.0.0"

VERSION = get_version()


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

        # Get the directory where the script is located (for reference)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Use %localAppData%\ezText\ for config file to persist across updates
        local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
        self.config_dir = os.path.join(local_app_data, 'ezText')

        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

        default_config = os.path.join(self.config_dir, 'ezTextShortcut.ini')

        # Migration: Check for old config file in script directory and move it
        old_config = os.path.join(self.script_dir, 'ezTextShortcut.ini')
        if os.path.exists(old_config) and not os.path.exists(default_config):
            try:
                import shutil
                shutil.copy2(old_config, default_config)
            except Exception:
                pass  # If migration fails, just use the new location

        # Load last opened file or use default
        last_file = self.settings.value('last_file', default_config)
        # If last file doesn't exist, fall back to default
        if not os.path.exists(last_file):
            self.config_file = default_config
            self.settings.setValue('last_file', default_config)
        else:
            self.config_file = last_file
        self.shortcuts_dict = {}
        self.active_shortcuts = []

        # System tray icon (will be initialized after translations)
        self.tray_icon = None

        # Single instance server
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self.handle_new_connection)
        # Remove any existing server with the same name
        QLocalServer.removeServer('ezText_SingleInstance')
        self.server.listen('ezText_SingleInstance')

        # Theme tracking
        self.current_theme = None
        self.theme_mode = self.settings.value('theme_mode', 'auto')  # auto, light, dark

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
                'restart': '재시작',
                'restart_program': '프로그램 재시작',
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
                'shortcut_conflict_warning': '⚠️ 다른 프로그램과 단축키 충돌되지 않도록 유의하세요.',
                'theme': '테마',
                'theme_auto': '자동 (시스템 따라가기)',
                'theme_light': '라이트 테마',
                'theme_dark': '다크 테마',
                'update_available_title': '업데이트 사용 가능',
                'update_available_text': '새 버전 ({0})이 사용 가능합니다!\n\n현재 버전: {1}',
                'update_confirm': '지금 업데이트를 다운로드하고 설치하시겠습니까?',
                'update_declined': '업데이트를 취소하였습니다.',
                'update_downloading': '{0} 버전으로 자동 업데이트 중...',
                'download_starting': 'GitHub에서 다운로드 시작 중...',
                'download_progress': '업데이트 다운로드 중: {0}% ({1}/{2} MB)',
                'download_completed': '다운로드 완료: {0}',
                'installer_launching': '설치 프로그램 실행 중...',
                'installer_started': '설치 프로그램이 시작되었습니다. 설치 마법사를 따라주세요.',
                'update_downloaded': '업데이트 다운로드 완료. 설치 프로그램이 자동으로 열립니다.',
                'update_failed_msg': '업데이트 다운로드에 실패했습니다. 도움말 메뉴에서 수동으로 업데이트해주세요.',
                'update_auto_failed': '자동 업데이트 실패',
                'new_version_available': '새 버전 {0}이 사용 가능합니다!',
                'update_title': '업데이트',
                'update_success_msg': '업데이트 다운로드 성공!\n\n설치 프로그램이 지금 열립니다.\n설치 마법사를 따라주세요.',
                'update_error_title': '업데이트 오류',
                'update_error_msg': '업데이트 다운로드에 실패했습니다.',
                'update_checking': '업데이트 확인 중...',
                'no_updates': '최신 버전을 사용 중입니다',
                'up_to_date': '최신 버전',
                'up_to_date_msg': '이미 최신 버전 ({0})을 사용하고 있습니다.',
                'update_check_failed': '업데이트 확인 실패',
                'update_check_failed_msg': '업데이트를 확인할 수 없습니다.\n\n오류: {0}',
                'update_installer_launched': '업데이트 설치 프로그램 시작됨',
                'github_url': 'https://github.com/gloriouslegacy/ezText/releases',
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
                'restart': 'Restart',
                'restart_program': 'Restart Program',
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
                'shortcut_conflict_warning': '⚠️ Be careful not to conflict with shortcuts in other programs.',
                'theme': 'Theme',
                'theme_auto': 'Auto (Follow System)',
                'theme_light': 'Light Theme',
                'theme_dark': 'Dark Theme',
                'update_available_title': 'Update Available',
                'update_available_text': 'A new version ({0}) is available!\n\nCurrent version: {1}',
                'update_confirm': 'Do you want to download and install the update now?',
                'update_declined': 'Update declined by user',
                'update_downloading': 'Auto-updating to version {0}...',
                'download_starting': 'Starting download from GitHub...',
                'download_progress': 'Downloading update: {0}% ({1}/{2} MB)',
                'download_completed': 'Download completed: {0}',
                'installer_launching': 'Launching installer...',
                'installer_started': 'Installer started. Please follow the installation wizard.',
                'update_downloaded': 'Update downloaded. Installer will open automatically.',
                'update_failed_msg': 'Failed to download update. Please update manually from Help menu.',
                'update_auto_failed': 'Auto-update failed',
                'new_version_available': 'New version {0} is available!',
                'update_title': 'Update',
                'update_success_msg': 'Update downloaded successfully!\n\nThe installer will open now.\nPlease follow the installation wizard.',
                'update_error_title': 'Update Error',
                'update_error_msg': 'Failed to download update.',
                'update_checking': 'Checking for updates...',
                'no_updates': 'No updates available',
                'up_to_date': 'Up to Date',
                'up_to_date_msg': 'You are already using the latest version ({0}).',
                'update_check_failed': 'Update Check Failed',
                'update_check_failed_msg': 'Could not check for updates.\n\nError: {0}',
                'update_installer_launched': 'Update installer launched',
                'github_url': 'https://github.com/gloriouslegacy/ezText/releases',
            }
        }
        
        self.init_ui()
        self.setup_tray_icon()
        self.load_shortcuts()

        # Apply theme after UI is fully initialized
        self.apply_theme()

        # Setup theme monitoring timer
        self.setup_theme_monitor()

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
            default_config = os.path.join(self.config_dir, 'ezTextShortcut.ini')
            self.config_file = default_config

            self.log_status("New file created")
    
    def on_text_mouse_press(self, event):
        """Handle text input mouse press"""
        # Allow text input to receive focus
        self.original_text_mouse_press(event)

    def on_text_input_focus(self, event):
        """Handle text input focus"""
        QTextEdit.focusInEvent(self.text_input, event)

    def on_text_input_focus_out(self, event):
        """Handle text input focus out"""
        QTextEdit.focusOutEvent(self.text_input, event)
    
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
        
        # Input section - Text input (first row)
        text_layout = QHBoxLayout()

        # Text input
        text_label = QLabel(self.tr('text') + ':')
        text_label.setFont(QFont('Segoe UI', 10))
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(self.tr('text'))
        self.text_input.setFont(QFont('Segoe UI', 10))
        # Set height for 5 lines
        font_metrics = self.text_input.fontMetrics()
        line_height = font_metrics.lineSpacing()
        self.text_input.setFixedHeight(line_height * 5 + 10)  # 5 lines + padding

        # Store original event handlers
        self.original_text_mouse_press = self.text_input.mousePressEvent
        self.original_text_focus_in = self.text_input.focusInEvent
        self.original_text_focus_out = self.text_input.focusOutEvent

        # Override event handlers
        self.text_input.mousePressEvent = self.on_text_mouse_press
        self.text_input.focusInEvent = self.on_text_input_focus
        self.text_input.focusOutEvent = self.on_text_input_focus_out

        text_layout.addWidget(text_label)
        text_layout.addWidget(self.text_input)

        # Shortcut input section (second row)
        shortcut_layout = QHBoxLayout()
        
        # Shortcut input - Modifier keys and main key
        shortcut_label = QLabel(self.tr('shortcut') + ':')
        shortcut_label.setFont(QFont('Segoe UI', 10))

        # Modifier keys checkboxes
        self.ctrl_checkbox = QCheckBox('Ctrl')
        self.ctrl_checkbox.setFont(QFont('Segoe UI', 10))
        self.ctrl_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

        self.win_checkbox = QCheckBox('Win')
        self.win_checkbox.setFont(QFont('Segoe UI', 10))
        self.win_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

        self.alt_checkbox = QCheckBox('Alt')
        self.alt_checkbox.setFont(QFont('Segoe UI', 10))
        self.alt_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

        self.shift_checkbox = QCheckBox('Shift')
        self.shift_checkbox.setFont(QFont('Segoe UI', 10))
        self.shift_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

        # Main key combobox
        self.key_combo = QComboBox()
        self.key_combo.setFont(QFont('Segoe UI', 10))
        self.key_combo.setMinimumHeight(35)
        self.key_combo.setCursor(Qt.CursorShape.PointingHandCursor)

        # Populate combobox with keys
        keys = []
        # A-Z
        for i in range(ord('A'), ord('Z') + 1):
            keys.append(chr(i))
        # 0-9
        for i in range(10):
            keys.append(str(i))
        # Function keys
        for i in range(1, 13):
            keys.append(f'F{i}')
        # Special keys
        special_keys = ['Space', 'Tab', 'Enter', 'Esc', 'Backspace', 'Delete',
                       'Insert', 'Home', 'End', 'PageUp', 'PageDown',
                       'Left', 'Right', 'Up', 'Down']
        keys.extend(special_keys)

        self.key_combo.addItems(keys)
        self.key_combo.setCurrentIndex(0)  # Default to 'A'

        # Add button (create early to add to shortcut layout)
        self.add_button = QPushButton(self.tr('add'))
        self.add_button.setFont(QFont('Segoe UI', 10))
        self.add_button.setMinimumHeight(35)
        self.add_button.clicked.connect(self.add_shortcut)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)

        shortcut_layout.addWidget(shortcut_label)
        shortcut_layout.addWidget(self.ctrl_checkbox)
        shortcut_layout.addWidget(self.win_checkbox)
        shortcut_layout.addWidget(self.alt_checkbox)
        shortcut_layout.addWidget(self.shift_checkbox)
        shortcut_layout.addWidget(self.key_combo)
        shortcut_layout.addWidget(self.add_button)

        # Warning label
        self.warning_label = QLabel(self.tr('shortcut_conflict_warning'))
        self.warning_label.setFont(QFont('Segoe UI', 9))
        self.warning_label.setWordWrap(False)
        self.warning_label.setObjectName("warningLabel")
        warning_layout = QHBoxLayout()
        warning_layout.addStretch()
        warning_layout.addWidget(self.warning_label)
        warning_layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

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

        self.restart_button = QPushButton(self.tr('restart_program'))
        self.restart_button.setFont(QFont('Segoe UI', 10))
        self.restart_button.setMinimumHeight(35)
        self.restart_button.clicked.connect(self.restart_program)
        self.restart_button.setCursor(Qt.CursorShape.PointingHandCursor)

        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.delete_all_button)
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.deselect_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.restart_button)
        
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
        main_layout.addLayout(text_layout)
        main_layout.addLayout(shortcut_layout)
        main_layout.addLayout(warning_layout)
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

        restart_action = QAction(self.tr('restart'), self)
        restart_action.setShortcut('Ctrl+R')
        restart_action.triggered.connect(self.restart_program)
        file_menu.addAction(restart_action)

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
        
        # Autostart checkbox action
        self.autostart_action = QAction(self.tr('enable_autostart'), self)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(self.is_autostart_enabled())
        self.autostart_action.triggered.connect(self.toggle_autostart)
        settings_menu.addAction(self.autostart_action)

        # Theme submenu
        theme_menu = QMenu(self.tr('theme'), self)

        auto_theme_action = QAction(self.tr('theme_auto'), self)
        auto_theme_action.triggered.connect(lambda: self.change_theme('auto'))
        theme_menu.addAction(auto_theme_action)

        light_theme_action = QAction(self.tr('theme_light'), self)
        light_theme_action.triggered.connect(lambda: self.change_theme('light'))
        theme_menu.addAction(light_theme_action)

        dark_theme_action = QAction(self.tr('theme_dark'), self)
        dark_theme_action.triggered.connect(lambda: self.change_theme('dark'))
        theme_menu.addAction(dark_theme_action)

        settings_menu.addMenu(theme_menu)

        # Help menu
        help_menu = menubar.addMenu(self.tr('help'))
        
        check_update_action = QAction(self.tr('check_update'), self)
        check_update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_update_action)
        
        visit_github_action = QAction(self.tr('visit_github'), self)
        visit_github_action.triggered.connect(self.visit_github)
        help_menu.addAction(visit_github_action)
    
    def setup_theme_monitor(self):
        """Setup timer to monitor system theme changes"""
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.check_theme_change)
        self.theme_timer.start(1000)  # Check every 1 second

    def check_theme_change(self):
        """Check if system theme has changed and update if necessary"""
        # Only check if in auto mode
        if self.theme_mode != 'auto':
            return

        is_dark = darkdetect.isDark()
        new_theme = 'dark' if is_dark else 'light'

        if self.current_theme != new_theme:
            self.current_theme = new_theme
            self.apply_theme()

    def change_theme(self, mode):
        """Change theme mode (auto, light, dark)"""
        self.theme_mode = mode
        self.settings.setValue('theme_mode', mode)
        self.apply_theme()

        mode_names = {
            'auto': self.tr('theme_auto'),
            'light': self.tr('theme_light'),
            'dark': self.tr('theme_dark')
        }
        self.log_status(f"Theme changed to {mode_names.get(mode, mode)}")

    def apply_theme(self):
        # Determine theme based on mode
        if self.theme_mode == 'auto':
            is_dark = darkdetect.isDark()
        elif self.theme_mode == 'dark':
            is_dark = True
        else:  # light
            is_dark = False

        self.current_theme = 'dark' if is_dark else 'light'

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
            QTextEdit {{
                background-color: {surface_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px 10px;
                color: {text_color};
            }}
            QTextEdit:focus {{
                border: 2px solid {accent_color};
                background-color: {surface_color};
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
            QLabel#warningLabel {{
                color: #ff9800;
                background-color: transparent;
                padding: 5px;
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
    
    def add_shortcut(self):
        """Add new shortcut"""
        text = self.text_input.toPlainText().strip()

        # Build shortcut from checkboxes and combobox
        modifiers = []
        if self.ctrl_checkbox.isChecked():
            modifiers.append('ctrl')
        if self.win_checkbox.isChecked():
            modifiers.append('win')
        if self.alt_checkbox.isChecked():
            modifiers.append('alt')
        if self.shift_checkbox.isChecked():
            modifiers.append('shift')

        main_key = self.key_combo.currentText().lower()

        # Build shortcut string
        if modifiers:
            shortcut = '+'.join(modifiers) + '+' + main_key
        else:
            shortcut = main_key

        if not text:
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

        # Clear inputs and reset checkboxes
        self.text_input.clear()
        self.ctrl_checkbox.setChecked(False)
        self.win_checkbox.setChecked(False)
        self.alt_checkbox.setChecked(False)
        self.shift_checkbox.setChecked(False)
        self.key_combo.setCurrentIndex(0)  # Reset to first item (A)

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
                    isinstance(focused_widget, (QLineEdit, QTextEdit)) or
                    self.text_input.hasFocus()
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
        # If config file doesn't exist, create an empty one
        if not os.path.exists(self.config_file):
            config = configparser.ConfigParser()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
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
        self.add_button.setText(self.tr('add'))
        self.delete_button.setText(self.tr('delete'))
        self.delete_all_button.setText(self.tr('delete_all'))
        self.select_all_button.setText(self.tr('select_all'))
        self.deselect_all_button.setText(self.tr('deselect_all'))
        self.restart_button.setText(self.tr('restart_program'))
        self.warning_label.setText(self.tr('shortcut_conflict_warning'))
        self.table.setHorizontalHeaderLabels(['', self.tr('text'), self.tr('shortcut')])

        # Recreate menu bar
        self.menuBar().clear()
        self.create_menu_bar()
    
    def is_autostart_enabled(self):
        """Check if autostart is currently enabled"""
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "TextShortcutApp"

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, app_name)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    def toggle_autostart(self):
        """Toggle autostart on/off"""
        current_state = self.is_autostart_enabled()
        self.set_autostart(not current_state)
        # Update checkbox state
        self.autostart_action.setChecked(not current_state)

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
        """Check for updates automatically on startup"""
        self.update_thread = UpdateCheckThread(self.updater)
        self.update_thread.update_available.connect(self.on_update_available_auto)
        self.update_thread.start()

    def on_update_available_auto(self, release_info):
        """Handle update available (automatic update on startup)"""
        # Show notification that update is available
        if self.tray_icon:
            self.tray_icon.showMessage(
                self.tr('title'),
                self.tr('new_version_available').format(release_info['version']),
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )

        # Ask user if they want to update
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(self.tr('update_available_title'))
        msg.setText(self.tr('update_available_text').format(release_info['version'], VERSION))
        msg.setInformativeText(self.tr('update_confirm'))
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        result = msg.exec()

        if result == QMessageBox.StandardButton.Yes:
            # User confirmed - download and install
            if release_info['download_url']:
                self.log_status(self.tr('update_downloading').format(release_info['version']))
                QApplication.processEvents()  # Force UI update
                success = self.download_and_run_installer(release_info['download_url'])

                if success:
                    # Show message that installer is running
                    if self.tray_icon:
                        self.tray_icon.showMessage(
                            self.tr('title'),
                            self.tr('update_downloaded'),
                            QSystemTrayIcon.MessageIcon.Information,
                            3000
                        )
                    self.log_status(self.tr('update_installer_launched'))
                else:
                    # Show error notification
                    if self.tray_icon:
                        self.tray_icon.showMessage(
                            self.tr('title'),
                            self.tr('update_failed_msg'),
                            QSystemTrayIcon.MessageIcon.Warning,
                            5000
                        )
                    self.log_status(self.tr('update_auto_failed'))
            else:
                # No download URL - open releases page
                webbrowser.open(release_info['html_url'])
        else:
            # User declined update
            self.log_status(self.tr('update_declined'))

    def check_for_updates(self):
        """Check for updates manually from menu"""
        self.log_status(self.tr('update_checking'))
        QApplication.processEvents()  # Force UI update

        self.update_thread = UpdateCheckThread(self.updater)
        self.update_thread.update_available.connect(self.on_update_available)
        self.update_thread.no_update.connect(self.on_no_update)
        self.update_thread.error.connect(self.on_update_error)
        self.update_thread.start()

    def on_update_available(self, release_info):
        """Handle update available"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(self.tr('update_available_title'))
        msg.setText(self.tr('update_available_text').format(release_info['version'], VERSION))
        msg.setInformativeText(self.tr('update_confirm'))
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        result = msg.exec()

        if result == QMessageBox.StandardButton.Yes:
            if release_info['download_url']:
                self.log_status(self.tr('update_downloading').format(release_info['version']))
                QApplication.processEvents()  # Force UI update

                # Setup version: Download and run installer directly (no updater.exe)
                # The installer will handle closing the app and updating files
                success = self.download_and_run_installer(release_info['download_url'])

                if success:
                    QMessageBox.information(
                        self,
                        self.tr('update_title'),
                        self.tr('update_success_msg')
                    )
                    # Don't exit here - let the installer close us
                else:
                    QMessageBox.warning(self, self.tr('update_error_title'), self.tr('update_error_msg'))
            else:
                # Open releases page if no direct download
                webbrowser.open(release_info['html_url'])

    def download_and_run_installer(self, download_url):
        """
        Download and run installer directly (for setup version only)
        Does not use updater.exe - installer handles everything

        Args:
            download_url: URL to download the installer

        Returns:
            bool: True if successful, False otherwise
        """
        import tempfile
        import urllib.request

        def download_progress(block_count, block_size, total_size):
            """Show download progress"""
            if total_size > 0:
                downloaded = block_count * block_size
                percent = min(100, (downloaded * 100) // total_size)
                downloaded_mb = downloaded / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                self.log_status(self.tr('download_progress').format(percent, f"{downloaded_mb:.1f}", f"{total_mb:.1f}"))
                QApplication.processEvents()  # Force UI update

        try:
            # Create temp directory
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, 'ezText_Setup.exe')

            # Download the installer with progress
            self.log_status(self.tr('download_starting'))
            QApplication.processEvents()  # Force UI update
            urllib.request.urlretrieve(download_url, installer_path, reporthook=download_progress)
            self.log_status(self.tr('download_completed').format(installer_path))
            QApplication.processEvents()  # Force UI update

            # Run the installer in normal mode (not silent)
            # The installer will:
            # 1. Show installation wizard to user
            # 2. Close ezText.exe automatically (via setup.iss code)
            # 3. Update all files
            # 4. Optionally restart the app
            self.log_status(self.tr('installer_launching'))
            QApplication.processEvents()  # Force UI update
            subprocess.Popen([installer_path])
            self.log_status(self.tr('installer_started'))
            QApplication.processEvents()  # Force UI update

            return True

        except Exception as e:
            error_msg = f"{self.tr('update_error_msg')} {e}"
            self.log_status(error_msg)
            print(error_msg)
            return False

    def on_no_update(self):
        """Handle no update available"""
        QMessageBox.information(
            self,
            self.tr('up_to_date'),
            self.tr('up_to_date_msg').format(VERSION)
        )
        self.log_status(self.tr('no_updates'))

    def on_update_error(self, error_msg):
        """Handle update check error"""
        QMessageBox.warning(
            self,
            self.tr('update_check_failed'),
            self.tr('update_check_failed_msg').format(error_msg)
        )
        self.log_status(f"{self.tr('update_check_failed')}: {error_msg}")
    
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

    def restart_program(self):
        """Restart the program"""
        try:
            # Save current shortcuts before restart
            self.save_shortcuts(silent=True)

            # Get the current executable path
            python = sys.executable

            # Close the current application
            self.tray_icon.hide()

            # Restart using the same executable and arguments
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                os.execl(sys.executable, sys.executable)
            else:
                # Running as Python script
                os.execl(python, python, *sys.argv)
        except Exception as e:
            QMessageBox.critical(self, self.tr('error'), f"Restart failed: {str(e)}")

    def handle_new_connection(self):
        """Handle new connection from another instance"""
        # Show and activate the window
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        """Handle window close event"""
        # Create custom message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.tr('exit_title'))
        msg_box.setText(self.tr('exit_message'))
        msg_box.setIcon(QMessageBox.Icon.Question)

        # Add custom buttons (order: Tray, Exit, Cancel)
        # Using ActionRole for all buttons to maintain left-to-right order
        tray_button = msg_box.addButton(self.tr('minimize_to_tray'), QMessageBox.ButtonRole.ActionRole)
        exit_button = msg_box.addButton(self.tr('exit_button'), QMessageBox.ButtonRole.ActionRole)
        cancel_button = msg_box.addButton(self.tr('cancel'), QMessageBox.ButtonRole.RejectRole)

        # Set cancel button as escape button
        msg_box.setEscapeButton(cancel_button)

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

    # Check if another instance is already running
    socket = QLocalSocket()
    socket.connectToServer('ezText_SingleInstance')

    if socket.waitForConnected(500):
        # Another instance is running, send signal and exit
        socket.write(b'SHOW')
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        return 0

    # First instance - start normally
    window = TextShortcutApp()
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
