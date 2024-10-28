import os
import sys
import pandas as pd
import tpqoa
from datetime import datetime
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, 
    QComboBox, QLabel, QDateEdit, QLineEdit, QFormLayout, 
    QMessageBox, QToolBar
)
from PyQt5.QtCore import QDate
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import mplfinance as mpf

class HistoricalChartApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = tpqoa.tpqoa('oanda.cfg')
        
        self.setWindowTitle("Historical Chart Viewer")
        main_layout = QVBoxLayout()

        form_layout = QFormLayout()
        
        self.instrument_dropdown = QComboBox()
        self.instrument_dropdown.addItems(["XAU_USD", "EUR_USD", "CAD_USD"])
        form_layout.addRow(QLabel("Instrument:"), self.instrument_dropdown)
        
        self.start_date_picker = QDateEdit(calendarPopup=True)
        self.start_date_picker.setDate(QDate.currentDate())
        self.start_date_picker.dateChanged.connect(self.sync_end_date)
        form_layout.addRow(QLabel("Start Date:"), self.start_date_picker)
        
        self.end_date_picker = QDateEdit(calendarPopup=True)
        self.end_date_picker.setDate(QDate.currentDate())
        form_layout.addRow(QLabel("End Date:"), self.end_date_picker)

        self.period_input = QLineEdit()
        self.period_input.setPlaceholderText("Enter period in minutes (e.g., 1 for M1)")
        self.period_input.setValidator(self.period_input.validator()) 
        form_layout.addRow(QLabel("Period (minutes):"), self.period_input)

        self.submit_button = QPushButton("Load Data")
        self.submit_button.clicked.connect(self.load_and_plot_data)
        form_layout.addWidget(self.submit_button)

        main_layout.addLayout(form_layout)

        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.canvas = FigureCanvas(self.fig)
        main_layout.addWidget(self.canvas)

        toolbar = NavigationToolbar(self.canvas, self)
        main_layout.addWidget(toolbar)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def sync_end_date(self):
        """ Sync the end date to be the same as the start date when the start date changes. """
        self.end_date_picker.setDate(self.start_date_picker.date())

    def load_and_plot_data(self):
        """ Load historical data based on user input and plot it. """
        instrument = self.instrument_dropdown.currentText()
        start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        end_date = self.end_date_picker.date().toString("yyyy-MM-dd")
        period = self.period_input.text()

        if not period.isdigit():
            self.show_error_message("Please enter a valid numeric period.")
            return

        try:
            period_minutes = int(period)
            granularity = f'M{period_minutes}'

            data = self.api.get_history(
                instrument=instrument,
                start=start_date + "T00:00:00",
                end=end_date + "T23:59:59",
                granularity=granularity,
                price='M',
                localize=False
            )

            if data.empty:
                self.show_error_message("No data available for the selected date range.")
            else:
                if 'time' not in data.columns:
                    data.reset_index(inplace=True) 
                
                # Plot the data
                self.plot_data(data)

        except Exception as e:
            self.show_error_message(f"Error downloading data: {e}")

    def plot_data(self, data):
        """ Plot the historical candlestick data. """
        self.ax.clear()

        # Rename columns as required by mplfinance and set 'time' as index
        data.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'volume': 'Volume'}, inplace=True)
        data['time'] = pd.to_datetime(data['time'])  # Convert time to datetime
        data.set_index('time', inplace=True)  # Set time as index for mplfinance

        # Plot candlestick chart without title
        mpf.plot(data, type='candle', style='classic', ax=self.ax, volume=False)
        self.canvas.draw()

    def show_error_message(self, message):
        """ Display an error message box. """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    def closeEvent(self, event):
        """ Override close event to notify the Flask app. """
        try:
            response = requests.post("http://localhost:3001/history-app-closed")
            if response.status_code == 200:
                print("Successfully notified Flask app that the trading app is closing.")
            else:
                print(f"Failed to notify Flask app. Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"Error notifying Flask app: {e}")

        event.accept()  # Accept the close event

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HistoricalChartApp()
    window.show()
    sys.exit(app.exec_())
