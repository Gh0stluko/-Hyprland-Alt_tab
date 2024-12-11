import os
import subprocess
import json
import sys
import signal
import atexit
import fcntl
from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QHBoxLayout
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QCoreApplication

class Worker(QObject):
    # Define signals to communicate with the main thread
    windows_updated = Signal(list)
    
    def __init__(self):
        super().__init__()
        
    def run(self):
        # This method will be executed in a separate thread
        windows = self.get_open_windows()
        self.windows_updated.emit(windows)
    
    def get_open_windows(self):
        result = subprocess.run(['hyprctl', 'clients', '-j'], stdout=subprocess.PIPE)
        windows = json.loads(result.stdout.decode('utf-8'))
        return [{
            'address': w['address'],
            'title': w['title'],
            'class': w['class']
        } for w in windows]

class WindowItem(QWidget):
    def __init__(self, window_info, parent=None, selected=False):
        super().__init__(parent)
        self.selected = selected
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)
        
        icon_container = QWidget()
        icon_container.setFixedSize(80, 80)
        icon_container.setStyleSheet(f"""
            background: rgba(255, 255, 255, {0.15 if selected else 0.1});
            border-radius: 20px;
        """)
        
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(16, 16, 16, 16)
        
        icon_label = QLabel()
        icon_size = 48
        pixmap = None
        icon = self.find_window_icon(window_info['class'])
        
        if icon and not icon.isNull():
            pixmap = icon.pixmap(icon_size, icon_size)
        else:
            arch_icon = QIcon.fromTheme("archlinux")
            if not arch_icon.isNull():
                pixmap = arch_icon.pixmap(icon_size, icon_size)
            else:
                arch_icon_path = "/usr/share/icons/hicolor/48x48/apps/archlinux.png"
                if os.path.exists(arch_icon_path):
                    pixmap = QPixmap(arch_icon_path).scaled(
                        icon_size, icon_size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )

        if pixmap and not pixmap.isNull():
            icon_label.setPixmap(pixmap)
                
        icon_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        
        title_label = QLabel(window_info['title'])
        title_label.setStyleSheet("""
            color: white;
            font-size: 13px;
            font-weight: 500;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setFixedWidth(120)
        title_label.setMinimumHeight(40)
        
        layout.addWidget(icon_container, alignment=Qt.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(title_label, alignment=Qt.AlignCenter)
        
        self.setFixedWidth(140)
        self.setStyleSheet(f"""
            WindowItem {{
                background: {f"rgba(40, 40, 40, 0.95)" if selected else "rgba(25, 25, 25, 0.95)"};
                border: 1px solid {f"rgba(60, 60, 60, 0.9)" if selected else "rgba(40, 40, 40, 0.9)"};
                border-radius: 15px;
                padding: 5px;
            }}
            WindowItem:hover {{
                background: rgba(50, 50, 50, 0.95);
                border: 1px solid rgba(70, 70, 70, 0.9);
            }}
        """)

    def find_window_icon(self, class_name):
        icon = QIcon.fromTheme(class_name.lower())
        if not icon.isNull():
            return icon
            
        desktop_file = f"/usr/share/applications/{class_name.lower()}.desktop"
        if os.path.exists(desktop_file):
            return QIcon.fromTheme(class_name.lower())
            
        return QIcon.fromTheme("application-x-executable")

class Hyprtab(QWidget):
    def __init__(self):
        super().__init__()
        
        # Ensure the mutex is released on exit
        
        self.set_hypr_rules()

        
        self.selected_index = 0
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setWindowOpacity(1.0)
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(1, 1, 1);
                color: rgb(200, 200, 200);
                border: 1px solid rgb(40, 40, 40);
                border-radius: 5px;
            }
        """)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        self.window_container = QHBoxLayout()
        self.window_container.setSpacing(10)
        self.window_container.setContentsMargins(20, 20, 20, 20)
        main_layout.addLayout(self.window_container)

        screen = QApplication.primaryScreen().geometry()
        self.setFixedSize(900, 200)
        self.move(
            screen.width()//2 - self.width()//2,
            screen.height()//4
        )

        self.setStyleSheet("""
            Hyprtab {
                background: rgba(20, 20, 20, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
            }
        """)

        self.windows = []
        
        # Start worker thread
        self.worker = Worker()
        self.worker.windows_updated.connect(self.update_window_list)
        self.thread = QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

        QCoreApplication.instance().aboutToQuit.connect(self.cleanup)
        self.hide()

    def update_window_list(self, windows):
        # Update window list from the background task
        for i in reversed(range(self.window_container.count())):
            widget = self.window_container.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.windows = windows
        for i, window in enumerate(self.windows):
            window_item = WindowItem(window, selected=(i == self.selected_index))
            window_item.mousePressEvent = lambda _, w=window: self.switch_to_window(w['address'])
            self.window_container.addWidget(window_item)

    def switch_to_window(self, window_address):
        subprocess.run(['hyprctl', 'dispatch', 'focuswindow', f"address:{window_address}"])
        subprocess.run(['hyprctl', 'dispatch', 'movetofront', f"address:{window_address}"])
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()  # Trigger the closeEvent
        elif event.key() == Qt.Key_Tab:
            self.selected_index = (self.selected_index + 1) % len(self.windows)
            self.update_window_list(self.windows)
        elif event.key() == Qt.Key_Return:
            if self.windows:
                self.switch_to_window(self.windows[self.selected_index]['address'])
        elif event.key() == Qt.Key_Alt:  # Detect Alt key press
            self.show()  # Show the window when Alt is pressed

    def closeEvent(self, event):
        self.cleanup()
        event.accept()  # Accept the event to ensure the window is closed properly.

    def cleanup(self):
        # Stop the worker thread and clean up the application
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()  # Wait for the thread to finish before exiting
        os._exit(0)  # Forcefully exit to ensure proper cleanup


    def set_hypr_rules(self):
        window_class = self.__class__.__name__ or "python3"
        subprocess.run(['hyprctl', 'keyword', 'windowrule', f"plugin:hyprbars:nobar,^({window_class})$",])

if __name__ == "__main__":
    # Create a lock file
    lock_file = '/tmp/hyprtab.lock'
    fp = open(lock_file, 'w')
    try:
        # Try to acquire an exclusive lock on the file
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("Another instance is already running.")
        sys.exit(1)

    app = QApplication(sys.argv)
    switcher = Hyprtab()
    switcher.show()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    try:
        sys.exit(app.exec())
    except SystemExit:
        switcher.cleanup()
        sys.exit(0)