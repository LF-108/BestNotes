import os
import sys
import sqlite3
import bcrypt
import json
import threading
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QPainter, QColor, QFont, QLinearGradient
from PySide6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress, QSslConfiguration, QSsl, QSslKey, QSslCertificate

# You can import your server and client modules here (replace 'login_2.py' and 'client.py' with actual file names)
from WhiteboardApplication.network_manager import CollabServer, CollabClient  # Import the Server class
from WhiteboardApplication.main import MainWindow
from WhiteboardApplication.board_scene import BoardScene

# Encryption-related functions
def init_database():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Creates table if it doesn't already exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

# Encrypts password with bcrypt
def encrypt_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Verifies entered password against the stored hash
def check_password(stored_hash, password):
    try:
        # Check if the entered password matches the stored hash
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except Exception as e:
        # General exception handler for unexpected errors
        print(f"Error during password check: {e}")
        return False

# The CollabServer class, handling the server's functionality
class CollabServer(QThread):
    def __init__(self, parent=None, ssl_key_path=None, ssl_cert_path=None):
        super().__init__(parent)
        self.server = None  # Replace with actual server logic, using QTcpServer or similar
        self.ssl_key_path = ssl_key_path
        self.ssl_cert_path = ssl_cert_path

    def run(self):
        # Start the server in the background thread
        pass

    def start(self, port):
        # Set up SSL for the server
        ssl_config = QSslConfiguration()
        ssl_config.setPrivateKey(QSslKey(self.ssl_key_path, QSsl.Pem))
        ssl_config.setLocalCertificate(QSslCertificate(self.ssl_cert_path))
        self.server.setSslConfiguration(ssl_config)

        # Bind and listen
        if not self.server.listen(QHostAddress.Any, port):
            raise RuntimeError(f"Failed to start server: {self.server.errorString()}")
        print(f"Server started on port {port} with SSL.")

# The CollabClient class, handling the client-side functionality
class CollabClient:
    def __init__(self):
        self.socket = None  # Use QSslSocket or QTcpSocket for secure connection

    def connect_to_host(self):
        try:
            # Implement connection logic here (use SSL if needed)
            self.socket = None  # Replace with actual socket connection
            return True
        except Exception as e:
            print(f"Error connecting to host: {e}")
            return False

# Login Window
class LoginWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Creates window
        self.setWindowTitle("Login")
        self.setMinimumSize(1060, 702)

        # Layout setup
        layout = QVBoxLayout()

        # Username Section
        self.username_input = QLineEdit()
        self.username_input.setFixedHeight(50)
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFont(QFont("Arial", 12))
        self.username_input.setStyleSheet("QLineEdit { padding: 10px 20px; margin-left: 30px; margin-right: 30px;}")
        layout.addWidget(self.username_input)

        # Password Section
        self.password_input = QLineEdit()
        self.password_input.setFixedHeight(50)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFont(QFont("Arial", 12))
        self.password_input.setStyleSheet("QLineEdit { padding: 10px 20px; margin-left: 30px; margin-right: 30px;}")
        layout.addWidget(self.password_input)

        # Login Button
        self.login_button = QPushButton("LOGIN")
        self.login_button.setFixedHeight(50)
        self.login_button.clicked.connect(self.login)
        self.login_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px 20px; font-size: 20px; margin-left: 30px; margin-right: 30px; font-weight: bold;}")
        layout.addWidget(self.login_button)

        # Register Button
        self.register_button = QPushButton("REGISTER")
        self.register_button.setFixedHeight(50)
        self.register_button.clicked.connect(self.register)
        self.register_button.setStyleSheet(
            "QPushButton { background-color: #4682B4; color: white; padding: 10px 20px; font-size: 20px; margin-left: 30px; margin-right: 30px; font-weight: bold;}")
        layout.addWidget(self.register_button)

        self.setLayout(layout)
        self.db_conn = init_database()

        # Load configuration file
        self.load_config()

    def load_config(self):
        # Get the base directory (two levels up from the script)
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        print("BASE_DIR for login.py: " + BASE_DIR)
        config_dir = os.path.abspath(os.path.join(BASE_DIR, "../.."))  # Go two levels up
        config_path = os.path.join(config_dir, 'config.json')

        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # Resolve SSL paths relative to the config directory
        self.ssl_key_path = os.path.join(config_dir, self.config['ssl_key_path'])
        self.ssl_cert_path = os.path.join(config_dir, self.config['ssl_cert_path'])

        # Verify the paths
        if not os.path.exists(self.ssl_key_path):
            raise FileNotFoundError(f"SSL key file not found at {self.ssl_key_path}.")
        if not os.path.exists(self.ssl_cert_path):
            raise FileNotFoundError(f"SSL certificate file not found at {self.ssl_cert_path}.")

    # Draws and resizes the background color
    def paintEvent(self, event):
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(0, 0, 0))  # Black
        gradient.setColorAt(1.0, QColor(65, 105, 225))  # Royal Blue at the bottom

        painter = QPainter(self)
        painter.setBrush(gradient)
        painter.drawRect(self.rect())  # Fill the entire widget with the gradient

        super().paintEvent(event)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        cursor = self.db_conn.cursor()

        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()

        if result:
            stored_password = result[0]
            if check_password(stored_password, password):
                # Login Success
                QMessageBox.information(self, "Login Success", "Welcome!")

                # After successful login, initialize the client
                self.client = CollabClient()  # Create the client instance
                if self.client.connect_to_host():  # Connect to the server
                    self.parent().set_client(self.client)  # Pass client to the parent (ApplicationWindow)
                else:
                    QMessageBox.warning(self, "Login Failed", "Could not connect to the server.")
            else:
                QMessageBox.warning(self, "Login Failed", "Invalid password.")
        else:
            QMessageBox.warning(self, "Login Failed", "User not found.")

    # Allows a new user to register their credentials
    def register(self):
        username = self.username_input.text()
        password = self.password_input.text()
        cursor = self.db_conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, encrypt_password(password)))
            self.db_conn.commit()
            QMessageBox.information(self, "Registration Success", "User registered successfully!")

        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "Username already exists.")

class ApplicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Collaborative Whiteboard")
        self.client = None  # Initially, no client

        # Create the login window
        self.login_window = LoginWindow(self)

        # Start with login window
        self.setCentralWidget(self.login_window)

    def start_server(self):
        # Here you start the server, assuming it's blocking.
        self.server = CollabServer(ssl_key_path=self.login_window.ssl_key_path, ssl_cert_path=self.login_window.ssl_cert_path)  # Pass the SSL paths
        self.server.start(5000)  # Start the server on a specified port

    def show_whiteboard(self):
        if self.client:
            self.board_scene = BoardScene()
            self.main_window = MainWindow()  # Create your MainWindow instance
            self.main_window.client = self.client  # Pass client state to the MainWindow
            self.setCentralWidget(self.main_window)
        else:
            QMessageBox.warning(self, "Error", "You must be logged in first.")

    def set_client(self, client):
        """Set the client after successful login."""
        self.client = client
        self.show_whiteboard()  # After login, show the whiteboard

def main():
    app = QApplication(sys.argv)
    main_window = ApplicationWindow()
    main_window.show()
    sys.exit(app.exec())

# Execute the main application
if __name__ == "__main__":
    main()