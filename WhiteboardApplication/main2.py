import os
import pickle
import sys
import socket
import threading
import time

from PySide6.QtWidgets import (
    QMainWindow,
    QGraphicsScene,
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QColorDialog,
    QPushButton,
    QGraphicsTextItem,
    QToolBar,
    QFileDialog,
    QApplication,
    QLabel,
    QFileDialog,
    QGraphicsPixmapItem, QWidget, QTabWidget, QAbstractScrollArea, QSizePolicy, QGraphicsView, QHBoxLayout, QGridLayout,
    QScrollArea, QMessageBox, QDialog
)

from PySide6.QtGui import (
    QPen,
    Qt,
    QPainter,
    QPainterPath,
    QColor,
    QBrush,
    QAction,
    QTransform, QBrush, QFont, QPixmap, QImageReader, QCursor
)

from PySide6.QtCore import (
    Qt, QRectF, QSizeF, QPointF, QSize, QRect, QFile, QIODevice
)

import ssl
import json

from WhiteboardApplication.UI.board import Ui_MainWindow
from WhiteboardApplication.text_box import TextBox
from WhiteboardApplication.new_notebook import NewNotebook
from WhiteboardApplication.Collab_Functionality.host_window import HostWindow
from WhiteboardApplication.board_scene import BoardScene
from WhiteboardApplication.database import UserDatabase
from WhiteboardApplication.collab_dialogs import HostDialog, JoinDialog, UserRegistry
from WhiteboardApplication.Collab_Functionality.collab_manager import CollabServer, CollabClient
from WhiteboardApplication.Collab_Functionality.discover_server import start_discovery_server

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.client = False  # Default state (not logged in)

        self.config = self.load_config()
        print("Loaded config:", self.config)  # Add this for debugging
        self.ssl_key_path = self.config.get('ssl_key_path')  # Use .get() to avoid KeyError
        self.ssl_cert_path = self.config.get('ssl_cert_path')  # Same here

        if not self.ssl_key_path or not self.ssl_cert_path:
            print("Warning: SSL key or certificate path is missing.")

        if hasattr(self, 'actionImages'):
            print("actionImages is initialized.")
        else:
            print("actionImages is NOT initialized.")

        # Menus Bar: Files
        self.actionSave.triggered.connect(self.save)
        self.actionLoad.triggered.connect(self.load)
        self.actionNew.triggered.connect(self.new_tab)

        #Menu Bar: Hosting and Joining
        # Add collab-related members
        self.user_db = UserDatabase()
        self.user_reg = UserRegistry()

        self.client = False  # Default state (not logged in)

        # Setup collaboration client and server
        self.collab_server = CollabServer()
        self.collab_client = CollabClient()
        self.username = None

        # Add collab menu actions
        self.actionHost.triggered.connect(self.host_session)
        self.actionJoin.triggered.connect(self.join_session)

        ############################################################################################################
        # Ensure all buttons behave properly when clicked
        self.list_of_buttons = [self.tb_actionPen, self.tb_actionHighlighter, self.tb_actionEraser]

        self.tb_actionPen.setChecked(True)
        self.tb_actionPen.triggered.connect(self.button_clicked)
        self.tb_actionHighlighter.triggered.connect(self.button_clicked)
        self.tb_actionEraser.triggered.connect(self.button_clicked)

        #sharon helped me out by showing this below
        self.tb_actionText.triggered.connect(self.create_text_box)
        self.tb_actionEraser.triggered.connect(self.button_clicked)
        self.tb_actionPen.triggered.connect(self.button_clicked)

        self.current_color = QColor("#000000")

        ############################################################################################################

        self.actionClear.triggered.connect(self.clear_canvas)

        # Define what the tool buttons do
        ###########################################################################################################
        self.current_color = QColor("#000000")
        self.tb_actionUndo.triggered.connect(self.undo)
        self.tb_actionRedo.triggered.connect(self.redo)

        # Image
        self.tb_actionImages.triggered.connect(self.upload_image)

        self.redo_list = []

        self.new_tab()

    def set_username(self, username):
        """Pass the username to BoardScene and other components."""
        self.username = username
        print(f"Username set in MainWindow: {username}")

        # Ensure the board scene receives the username
        self.scene.set_username(username)

    def set_collab_client(self, collab_client):
        print("Collab client passed main")
        self.scene.set_collab_client(collab_client)

    #Upload Image
    def upload_image(self):
        print("Image Button clicked")
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.bmp)")
        if file_name:
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
                pixmap_item = QGraphicsPixmapItem(pixmap)
                pixmap_item.setPos(0, 0)  # Adjust position as needed
                pixmap_item.setFlag(QGraphicsPixmapItem.ItemIsMovable)
                self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().add_image(pixmap_item)

    # this finds the current tab and locates the canvas
    # inside that tab to access its scene
    def undo(self):
        self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().undo()

    def redo(self):
        self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().redo()

    def clear_canvas(self):
        self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().clear()

    #Depending on which button is clicked, sets the appropriate flag so that operations
    #don't overlap
    def button_clicked(self):
        sender_button = self.sender()

        # Toggle Cursor
        if sender_button == self.tb_actionCursor:
            if self.tb_actionCursor.isChecked():
                # disable pen, disable eraser
                print("Cursor activated")  # Debugging print
                self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().set_active_tool("cursor")
                self.tb_actionEraser.setChecked(False)
                self.tb_actionPen.setChecked(False)
                self.tb_actionHighlighter.setChecked(False)

        # Toggle Pen
        if sender_button == self.tb_actionPen:
            if self.tb_actionPen.isChecked():
                # Enable pen mode, disable eraser
                print("Pen activated")  # Debugging print
                self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().set_active_tool("pen")
                self.tb_actionEraser.setChecked(False)  # Ensure eraser is not active
                self.tb_actionCursor.setChecked(False)
                self.tb_actionHighlighter.setChecked(False)
            else:
                # Deactivate drawing mode when button is clicked again
                print("Pen deactivated")  # Debugging print
                self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().set_active_tool(None)

        # Toggle Eraser
        elif sender_button == self.tb_actionEraser:
            if self.tb_actionEraser.isChecked():
                # Enable eraser mode, disable pen
                print("Eraser activated")  # Debugging print
                # self.color_changed(QColor("#F3F3F3"))
                self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().set_active_tool("eraser")
                self.tb_actionPen.setChecked(False)  # Ensure pen is not active
                self.tb_actionCursor.setChecked(False)
                self.tb_actionHighlighter.setChecked(False)
            else:
                # Deactivate erasing mode when button is clicked again
                print("Eraser deactivated")  # Debugging print
                self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().set_active_tool(None)

        elif sender_button == self.tb_actionHighlighter:
            if self.tb_actionHighlighter.isChecked():
                # Enable highlighter mode, disable pen & eraser
                print("Highlighter activated")  # Debugging print
                self.scene.set_active_tool("highlighter")
                self.tb_actionPen.setChecked(False)  # Ensure pen is not active
                self.tb_actionCursor.setChecked(False)
                self.tb_actionEraser.setChecked(False)
            else:
                # Deactivate erasing mode when button is clicked again
                print("Highlighter deactivated")  # Debugging print
                self.scene.set_active_tool(None)

    #Adds a text box using the method in BoardScene
    def create_text_box(self):
        # Create a text box item and add it to the scene
        text_box_item = TextBox()
        self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().add_text_box(text_box_item)

    def enable_eraser(self, enable):
        self.erasing_enabled = enable
        # Ensure drawing is off when erasing is on
        if enable:
            self.drawing_enabled = False
            self.highlighting_enabled = False

    def enable_highlighter(self, enable):
        self.highlighting_enabled = enable
        if enable:
            self.erasing_enabled = False
            self.drawing_enabled = False

    def save(self):
        directory, _filter = QFileDialog.getSaveFileName(self, "Save as Pickle", '', "Pickle (*.pkl)")

        if directory == "":
            return

        with open(directory, 'wb') as file:
            # noinspection PyTypeChecker
            pickle.dump(self.serialize_items(), file, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self):
        self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().clear()
        directory, _filter = QFileDialog.getOpenFileName()
        with open(directory, 'rb') as file:
            items_data = pickle.load(file)
            self.deserialize_items(items_data)

    def serialize_items(self):
        items_data = []
        for item in self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().items():
            if isinstance(item, TextBox):
                items_data.append({
                    'type': 'TextBox',
                    'text': item.toPlainText(),
                    'font': self.serialize_font(item.font()),
                    'color': self.serialize_color(item.defaultTextColor()),
                    'rotation': item.rotation(),
                    'transform': self.serialize_transform(item.transform()),
                    'x': item.pos().x(),
                    'y': item.pos().y(),
                    'name': item.toolTip(),
                })

            elif isinstance(item, QGraphicsPathItem):
                path_data = {
                    'type': 'QGraphicsPathItem',
                    'pen': self.serialize_pen(item.pen()),
                    'brush': self.serialize_brush(item.brush()),
                    'rotation': item.rotation(),
                    'transform': self.serialize_transform(item.transform()),
                    'x': item.pos().x(),
                    'y': item.pos().y(),
                    'name': item.toolTip(),
                    'elements': self.serialize_path(item.path()),
                }
                items_data.append(path_data)

        return items_data

    def serialize_color(self, color: QColor):
        return {
            'red': color.red(),
            'green': color.green(),
            'blue': color.blue(),
            'alpha': color.alpha(),
        }

    def serialize_pen(self, pen: QPen):
        return {
            'width': pen.width(),
            'color': self.serialize_color(pen.color()),
            'style': pen.style(),
            'capstyle': pen.capStyle(),
            'joinstyle': pen.joinStyle()
        }

    def serialize_brush(self, brush: QBrush):
        return {
            'color': self.serialize_color(brush.color()),
            'style': brush.style()
        }

    def serialize_font(self, font: QFont):
        return {
            'family': font.family(),
            'pointsize': font.pixelSize(),
            'letterspacing': font.letterSpacing(),
            'bold': font.bold(),
            'italic': font.italic(),
            'underline': font.underline(),
        }

    def serialize_transform(self, transform: QTransform):
        return {
            'm11': transform.m11(),
            'm12': transform.m12(),
            'm13': transform.m13(),
            'm21': transform.m21(),
            'm22': transform.m22(),
            'm23': transform.m23(),
            'm31': transform.m31(),
            'm32': transform.m32(),
            'm33': transform.m33()
        }

    def serialize_path(self, path: QPainterPath):
        elements = []
        for i in range(path.elementCount()):
            element = path.elementAt(i)
            if element.isMoveTo():
                elements.append({'type': 'moveTo', 'x': element.x, 'y': element.y})
            elif element.isLineTo():
                elements.append({'type': 'lineTo', 'x': element.x, 'y': element.y})
            elif element.isCurveTo():
                elements.append({'type': 'curveTo', 'x': element.x, 'y': element.y})
        return elements

    def deserialize_items(self, items_data):
        for item_data in items_data:
            if item_data['type'] == 'TextBox':
                item = self.deserialize_text_item(item_data)
            elif item_data['type'] == 'QGraphicsPathItem':
                item = self.deserialize_path_item(item_data)

            # Add item
            self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().addItem(item)

    def deserialize_color(self, color):
        return QColor(color['red'], color['green'], color['blue'], color['alpha'])

    def deserialize_pen(self, data):
        pen = QPen()
        pen.setWidth(data['width'])
        pen.setColor(self.deserialize_color(data['color']))
        pen.setStyle(data['style'])
        pen.setCapStyle(data['capstyle'])
        pen.setJoinStyle(data['joinstyle'])
        return pen

    def deserialize_brush(self, data):
        brush = QBrush()
        brush.setColor(self.deserialize_color(data['color']))
        brush.setStyle(data['style'])
        return brush

    def deserialize_font(self, data):
        font = QFont()
        font.setFamily(data['family'])
        font.setPixelSize(data['pointsize'])
        font.setLetterSpacing(QFont.AbsoluteSpacing, data['letterspacing'])
        font.setBold(data['bold'])
        font.setItalic(data['italic'])
        font.setUnderline(data['underline'])
        return font

    def deserialize_transform(self, data):
        transform = QTransform(
            data['m11'], data['m12'], data['m13'],
            data['m21'], data['m22'], data['m23'],
            data['m31'], data['m32'], data['m33']
        )
        return transform

    def deserialize_text_item(self, data):
        from text_box import TextBox
        text_item = TextBox()
        text_item.setFont(self.deserialize_font(data['font']))
        text_item.setDefaultTextColor(self.deserialize_color(data['color']))
        text_item.setRotation(data['rotation'])
        text_item.setTransform(self.deserialize_transform(data['transform']))
        text_item.setPos(data['x'], data['y'])
        text_item.setToolTip(data['name'])
        text_item.setPlainText(data['text'])
        return text_item

    def deserialize_path_item(self, data):
        sub_path = QPainterPath()
        for element in data['elements']:
            if element['type'] == 'moveTo':
                sub_path.moveTo(element['x'], element['y'])
            elif element['type'] == 'lineTo':
                sub_path.lineTo(element['x'], element['y'])
            elif element['type'] == 'curveTo':
                sub_path.cubicTo(element['x'],
                                 element['y'],
                                 element['x'],
                                 element['y'],
                                 element['x'],
                                 element['y'])

        path_item = QGraphicsPathItem(sub_path)
        path_item.setPen(self.deserialize_pen(data['pen']))
        path_item.setBrush(self.deserialize_brush(data['brush']))
        path_item.setRotation(data['rotation'])
        path_item.setTransform(self.deserialize_transform(data['transform']))
        path_item.setPos(data['x'], data['y'])
        path_item.setToolTip(data['name'])

        return path_item

    def new_tab(self):
        #adds a new tab that contains the widget canvas
        self.tabWidget.addTab(NewNotebook.add_new_notebook(NewNotebook), "Notebook %d" % (self.tabWidget.count()+1))

        # attaches a new instance of scene to the new tab's canvas
        self.scene = BoardScene()
        NewNotebook.get_canvas(NewNotebook).setScene(self.scene)
        NewNotebook.get_canvas(NewNotebook).setRenderHint(QPainter.RenderHint.Antialiasing, True)

    def set_active_tool(self):
        """Set the active tool based on the button clicked."""
        tool_map = {
            self.tb_actionPen: "pen",
            self.tb_actionHighlighter: "highlighter",
            self.tb_actionEraser: "eraser"
        }
        for button, tool in tool_map.items():
            if button.isChecked():
                self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().set_active_tool(tool)

    def load_config(self):
        try:
            # Get the current directory of the script
            current_dir = os.path.dirname(os.path.abspath(__file__))

            # Move up one directory
            project_root = os.path.dirname(current_dir)

            # Construct the config file path
            config_path = os.path.join(project_root, 'config.json')

            # Check if the config file exists
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Configuration file not found at: {config_path}")

            # Load the config file
            with open(config_path, 'r') as file:
                config = json.load(file)

            # Resolve SSL paths relative to the project root
            config['ssl_key_path'] = os.path.abspath(os.path.join(project_root, config.get('ssl_key_path', 'ssl/server.key')))
            config['ssl_cert_path'] = os.path.abspath(os.path.join(project_root, config.get('ssl_cert_path', 'ssl/server.crt')))

            return config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading config: {e}")
            return {}


    def host_session(self):
        """Host a collaborative drawing session."""
        dialog = HostDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.username = dialog.get_username()

            if not self.user_db.user_exists(self.username):
                self.user_db.add_user(self.username)

            port = self.user_reg.register_host(self.username)
            print(f"Port used is {port} \n")

            try:
                # Get the actual network IP address first
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.connect(("8.8.8.8", 80))
                        host_ip = s.getsockname()[0]
                except Exception as e:
                    print(f"Could not determine external IP address: {e}")
                    host_ip = "127.0.0.1"  # Fallback to localhost

                print("IP Address found for hosting is " + host_ip + "\n")

                # Now, create the collab server with the correct host IP
                self.collab_server = CollabServer(discovery_host=host_ip, server_port=5050)
                print("Created collab server\n")
                self.setup_ssl_context(self.collab_server)

                # Start the collab server with the correct host IP
                self.collab_server.start(username=self.username)
                self.collab_server.clientConnected.connect(self._handle_client_connected)
                self.collab_server.clientDisconnected.connect(self._handle_client_disconnected)
                QMessageBox.information(self, "Hosting", f"Session started at {host_ip}:{port}")

                # Now, pass collab_server to BoardScene after it's created
                self.scene.collab_server = self.collab_server

            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to host session: {e}")


    def join_session(self):
        """Join a collaborative drawing session."""
        dialog = JoinDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.username = dialog.get_username()
            host_username = dialog.get_host_username()

            if not self.user_db.user_exists(self.username):
                self.user_db.add_user(self.username)

            try:
                host_address, port = self.user_reg.get_host_address(host_username)

                self.collab_client = CollabClient(self)
                self.setup_ssl_context(self.collab_client)

                if self.collab_client.connect_to_host(host_address, port, self.username):
                    self.collab_client.drawingReceived.connect(self._handle_remote_drawing)
                    QMessageBox.information(self, "Connected", f"Joined session at {host_address}:{port}")

                    # Pass collab_client to BoardScene after it's created
                    self.scene.collab_client = self.collab_client
                else:
                    QMessageBox.warning(self, "Error", "Failed to join session.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to join session: {e}")

    def setup_ssl_context(self, instance):
        """Set up SSL context for secure communication."""
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_cert_chain(
                certfile=self.config['ssl_cert_path'],
                keyfile=self.config['ssl_key_path']
            )
            instance.ssl_context = ssl_context
        except Exception as e:
            raise RuntimeError(f"Failed to set up SSL context: {e}")

    def _handle_client_connected(self, username):
        QMessageBox.information(self, "User Connected", f"{username} has joined the session.")

    def _handle_client_disconnected(self, username):
        QMessageBox.information(self, "User Disconnected", f"{username} has left the session.")

    def _handle_remote_drawing(self, data):
        """Handle incoming drawing data."""
        self.tabWidget.currentWidget().findChild(QGraphicsView, 'gv_Canvas').scene().apply_remote_drawing(data)

    def closeEvent(self, event):
        """Clean up resources on close."""
        if self.username:
            self.user_reg.remove_user(self.username)
        super().closeEvent(event)

def main():
    # Start the discovery server in a separate thread
    discovery_thread = threading.Thread(target=start_discovery_server, args=(9000,), daemon=True)
    discovery_thread.start()
    print("Discovery server started.")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()