import sys
import os
import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from main import CandlestickApp  # Import the candlestick playback app

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set the main window properties
        self.setWindowTitle("Candlestick Dataset Selector")
        self.setGeometry(200, 200, 300, 200)

        # Create the main layout
        main_layout = QVBoxLayout()

        # Create the folder paths for each timeframe
        self.folders = {
            "1 Minute": "data/1min",
            "5 Minute": "data/5min",
            "10 Minute": "data/10min",
            "15 Minute": "data/15min",
            "30 Minute": "data/30min"
        }

        # Create a button for each timeframe and add it to the layout
        for label, folder in self.folders.items():
            button = QPushButton(label)
            button.clicked.connect(lambda checked, f=folder: self.open_candlestick_app(f))
            main_layout.addWidget(button)

        # Create a central widget and set the layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def open_candlestick_app(self, folder):
        # Get all CSV files from the selected folder
        csv_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]

        # Check if there are any CSV files in the folder
        if not csv_files:
            print(f"No CSV files found in {folder}")
            return

        # Open the CandlestickApp with the selected CSV files
        self.candlestick_window = CandlestickApp(csv_files)
        self.candlestick_window.show()

    def closeEvent(self, event):
        # Notify the Flask app that the trading app is closing
        try:
            requests.post("http://localhost:3001/trading-app-closed")
        except Exception as e:
            print(f"Error notifying Flask app: {e}")

        event.accept()  # Accept the close event

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create and show the main window
    window = MainWindow()
    window.show()

    # Run the application
    sys.exit(app.exec_())
