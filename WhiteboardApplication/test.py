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
    QScrollArea, QMessageBox,
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
    Qt, QRectF, QSizeF, QPointF, QSize, QRect
)

import json
from WhiteboardApplication.UI.board import Ui_MainWindow
from WhiteboardApplication.text_box import TextBox
from WhiteboardApplication.new_notebook import NewNotebook
from WhiteboardApplication.Collab_Functionality.host_window import HostWindow


class BoardScene(QGraphicsScene):
    def __init__(self):
        super().__init__()

        self.setSceneRect(0, 0, 600, 500)

        self.path = None
        self.previous_position = None
        self.drawing = False
        self.color = QColor("#000000")
        self.size = 1
        self.pathItem = None

        # Added flags to check which button is being pressed, and if text boxes are being dragged
        self.is_text_box_selected = False
        self.dragging_text_box = False
        self.drawing_enabled = False
        self.highlighting_enabled = False
        self.erasing_enabled = False
        self.active_tool = None

        self.undo_list = []
        self.redo_list = []
        self.highlight_items = []

    def get_main_window(self):
        """Helper method to get the MainWindow instance"""
        views = self.views()
        if views:
            current_view = views[0]
            return current_view.window()
        return None

    # Adds an action to the undo list (or a list of items in the case of textbox), by treating every action as a list
    def add_item_to_undo(self, item):
        """Add a single item or group of items to the undo list and clear redo list"""
        # Clear redo list to ensure correct redo functionality
        self.redo_list.clear()

        # Add item (or list of items if it's a group) to the undo list
        self.undo_list.append([item])
        print("Added to undo:", item)

    # Pops action of undo stack to undo, and adds it to redo in case user wants to redo the action
    def undo(self):
        if not self.undo_list:
            print("Undo list is empty")
            return

        # Pop the last group of items from the undo stack
        item_group = self.undo_list.pop()
        for item in item_group:
            self.removeItem(item)
            print("Removed from scene (undo):", item)

        # Push the removed items to the redo stack
        self.redo_list.append(item_group)
        print("Added to redo stack:", item_group)

    # Pops an action off the redo stack and adds it back to undo to redo and action
    def redo(self):
        if not self.redo_list:
            print("Redo list is empty")
            return

        # Pop the last group of items from the redo stack
        item_group = self.redo_list.pop()
        for item in item_group:
            self.addItem(item)
            print("Added back to scene (redo):", item)

        # Push the redone items back to the undo stack
        self.undo_list.append(item_group)
        print("Restored to undo stack:", item_group)

    '''
    #Adds text box and resizing handles as a group so they are undone at once
    def add_text_box(self, text_box_item):
        self.addItem(text_box_item)
        self.add_item_to_undo(text_box_item)  # For complex items, group with handles if needed
        print("TextBox added to scene:", text_box_item)


    def add_image(self, pixmap_item):
        self.addItem(pixmap_item)
        self.add_item_to_undo(pixmap_item)
        print("Image added to scene:", pixmap_item)
    '''

    def change_color(self, color):
        self.color = color

    def change_size(self, size):
        self.size = size

    # Used to turn drawing on or off so it doesn't interfere with dragging text boxes
    def enable_drawing(self, enable):
        self.drawing_enabled = enable
        # Ensure eraser is off when drawing is on
        if enable:
            self.erasing_enabled = False
            self.highlighting_enabled = False

    # Used to turn eraser on or off so it doesn't interfere with dragging text boxes
    def enable_eraser(self, enable):
        self.erasing_enabled = enable
        # Ensure drawing is off when erasing is on
        if enable:
            self.drawing_enabled = False
            self.highlighting_enabled = False

    def enable_highlighter(self, enable):
        self.highlighting_enabled = enable
        if enable:
            self.drawing_enabled = False
            self.erasing_enabled = False

    # A basic eraser, created as a hold so text box function could be implemented
    def erase(self, position):
        eraser_radius = 10

        # Creates a 20 x 20 rectangle, using the current position and moving further left and up to set the left corner of the rectangle
        erase_item = self.items(
            QRectF(position - QPointF(eraser_radius, eraser_radius), QSizeF(eraser_radius * 2, eraser_radius * 2)))

        # Removes all items within the rectangle
        for item in erase_item:
            if item in self.highlight_items:
                self.removeItem(item)
                self.highlight_items.remove(item)
            elif isinstance(item, QGraphicsPathItem):
                self.removeItem(item)

    def highlight(self, position):
        highlight_color = QColor(255, 255, 0, 10)
        highlight_brush = QBrush(highlight_color)
        highlight_radius = 18
        highlight_circle = QGraphicsEllipseItem(position.x() - highlight_radius, position.y() - highlight_radius,
                                                highlight_radius * 2, highlight_radius * 2)

        highlight_circle.setBrush(highlight_brush)
        highlight_circle.setPen(Qt.NoPen)

        self.addItem(highlight_circle)
        self.highlight_items.append(highlight_circle)

    def mousePressEvent(self, event):
        item = self.itemAt(event.scenePos(), QTransform())
        print(f"Active Tool: {self.active_tool}")  # Debugging print

        if event.button() == Qt.LeftButton:
            if isinstance(item, TextBox):
                print("Box selected")
                self.drawing = False
                self.is_text_box_selected = True
                self.selected_text_box = item
                self.start_pos = event.scenePos()  # Store the start position for dragging
                self.dragging_text_box = True
            else:
                if self.active_tool == "pen":
                    print("Pen tool active")
                    self.drawing = True
                    self.path = QPainterPath()
                    self.previous_position = event.scenePos()
                    self.path.moveTo(self.previous_position)
                    self.pathItem = QGraphicsPathItem()
                    my_pen = QPen(self.color, self.size)
                    my_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    self.pathItem.setPen(my_pen)
                    self.addItem(self.pathItem)
                elif self.active_tool == "highlighter":
                    print("Highlight tool active")
                    self.drawing = False
                    self.highlight(event.scenePos())
                elif self.active_tool == "eraser":
                    print("Eraser tool active")
                    self.drawing = False
                    self.erase(event.scenePos())
                elif self.active_tool == "cursor":
                    print("Cursor active")
                    self.drawing = False

        super().mousePressEvent(event)

    '''
    def mouseMoveEvent(self, event):
        if self.dragging_text_box and self.selected_text_box:
            self.drawing = False
            print("Dragging box")
            delta = event.scenePos() - self.start_pos
            self.selected_text_box.setPos(self.selected_text_box.pos() + delta)
            self.start_pos = event.scenePos()
        elif self.drawing:
            print("drawing")
            curr_position = event.scenePos()
            self.path.lineTo(curr_position)
            self.pathItem.setPath(self.path)
            self.previous_position = curr_position
        elif self.active_tool == "highlighter":
            print("highlighting")
            self.highlight(event.scenePos())

        super().mouseMoveEvent(event)
    '''

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.dragging_text_box:
                print("Finished dragging box")
                self.dragging_text_box = False
            elif self.drawing:
                # Add the completed path to the undo stack when drawing is finished so it can be deleted or added back with undo
                self.add_item_to_undo(self.pathItem)
                print("Path item added to undo stack:", self.pathItem)
            self.drawing = False
            self.is_text_box_selected = False

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.drawing and self.active_tool == "pen":
            curr_position = event.scenePos()
            self.path.lineTo(curr_position)
            self.pathItem.setPath(self.path)

            # Send complete path data to collaborators
            main_window = self.get_main_window()
            if main_window:
                # Correctly extract points from the path
                path_points = [
                    {'x': point.x(), 'y': point.y()}
                    for point in [self.path.elementAt(i) for i in range(self.path.elementCount())]
                    if isinstance(point, QPointF)
                ]

                drawing_data = {
                    'type': 'path',
                    'points': path_points,
                    'color': self.color.name(),
                    'size': self.size
                }

                if hasattr(main_window, 'collab_client') and main_window.collab_client:
                    main_window.collab_client.send_drawing(drawing_data)
                elif hasattr(main_window, 'collab_server') and main_window.collab_server:
                    main_window.collab_server._broadcast(
                        json.dumps({'type': 'drawing', 'data': drawing_data})
                    )

            self.previous_position = curr_position

    '''
    def apply_remote_drawing(self, drawing_data: dict):
        """Apply drawing data received from remote users"""
        if drawing_data['type'] == 'path':
            path = QPainterPath()
            points = drawing_data['points']
            path.moveTo(points[0]['x'], points[0]['y'])
            path.lineTo(points[1]['x'], points[1]['y'])

            path_item = QGraphicsPathItem(path)
            pen = QPen(QColor(drawing_data['color']), drawing_data['size'])
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            path_item.setPen(pen)

            self.addItem(path_item)
            self.add_item_to_undo(path_item)
    '''

    # Marks which tool (pen, eraser) is being used so multiple don't run at once
    def set_active_tool(self, tool):
        self.active_tool = tool

    def add_text_box(self, text_box_item):
        self.addItem(text_box_item)
        self.add_item_to_undo(text_box_item)

        # Broadcast text box addition to collaborators
        main_window = self.get_main_window()
        if main_window:
            text_box_data = {
                'type': 'text_box',
                'text': text_box_item.toPlainText(),
                'x': text_box_item.pos().x(),
                'y': text_box_item.pos().y(),
                'font_family': text_box_item.font().family(),
                'font_size': text_box_item.font().pixelSize(),
                'color': text_box_item.defaultTextColor().name()
            }

            if hasattr(main_window, 'collab_client') and main_window.collab_client:
                main_window.collab_client.send_drawing(text_box_data)
            elif hasattr(main_window, 'collab_server') and main_window.collab_server:
                main_window.collab_server._broadcast(
                    json.dumps({'type': 'drawing', 'data': text_box_data})
                )

    def add_image(self, pixmap_item):
        self.addItem(pixmap_item)
        self.add_item_to_undo(pixmap_item)

        # Broadcast image addition to collaborators
        main_window = self.get_main_window()
        if main_window:
            image_data = {
                'type': 'image',
                'x': pixmap_item.pos().x(),
                'y': pixmap_item.pos().y(),
                'width': pixmap_item.pixmap().width(),
                'height': pixmap_item.pixmap().height()
                # If you want to send actual image data, you'd need to base64 encode it
            }

            if hasattr(main_window, 'collab_client') and main_window.collab_client:
                main_window.collab_client.send_drawing(image_data)
            elif hasattr(main_window, 'collab_server') and main_window.collab_server:
                main_window.collab_server._broadcast(
                    json.dumps({'type': 'drawing', 'data': image_data})
                )

    def apply_remote_drawing(self, drawing_data: dict):
        """Apply drawing data received from remote users"""
        if drawing_data['type'] == 'path':
            self._apply_remote_path(drawing_data)
        elif drawing_data['type'] == 'text_box':
            self._apply_remote_text_box(drawing_data)
        elif drawing_data['type'] == 'image':
            self._apply_remote_image(drawing_data)

    def _apply_remote_path(self, drawing_data):
        path = QPainterPath()
        points = drawing_data['points']

        if points:
            path.moveTo(points[0]['x'], points[0]['y'])
            for point in points[1:]:
                path.lineTo(point['x'], point['y'])

        path_item = QGraphicsPathItem(path)
        pen = QPen(QColor(drawing_data['color']), drawing_data['size'])
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        path_item.setPen(pen)

        self.addItem(path_item)
        self.add_item_to_undo(path_item)

    def _apply_remote_text_box(self, drawing_data):
        from text_box import TextBox
        text_box = TextBox()
        text_box.setPlainText(drawing_data['text'])
        text_box.setPos(drawing_data['x'], drawing_data['y'])

        font = QFont()
        font.setFamily(drawing_data['font_family'])
        font.setPixelSize(drawing_data['font_size'])
        text_box.setFont(font)

        text_box.setDefaultTextColor(QColor(drawing_data['color']))

        self.addItem(text_box)
        self.add_item_to_undo(text_box)