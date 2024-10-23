import os
import sys
import pandas as pd
import mplfinance as mpf
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class CandlestickApp(QMainWindow):
    def __init__(self, data_files):
        super().__init__()

        self.data_files = data_files
        self.current_file_index = 0
        self.data = self.load_data(self.data_files[self.current_file_index])
        self.current_index = 0
        self.running = False
        self.x_limit = 50  # Initial x-axis limit
        self.playback_speed = 1000  # Default speed in ms

        # Trade management
        self.buy_marker = None  # Store the buy marker index
        self.sell_marker = None  # Store the sell marker index
        self.active_trade = None  # Track active trade (None, 'buy', or 'sell')

        # Drawing variables
        self.lines = []  # List to store drawn horizontal lines
        self.drawing_line = False  # Flag to track line drawing mode

        # Set up the layout
        self.setWindowTitle("PLAYBACK")
        main_layout = QVBoxLayout()

        # Create controls layout
        controls_layout = QHBoxLayout()

        # Create speed selection buttons
        self.speed_buttons = {}
        speed_options = [100, 250, 500, 1000]  # Speed options in ms
        for speed in speed_options:
            button = QPushButton(f"{speed} ms")
            button.setFixedSize(80, 30)
            button.clicked.connect(lambda _, s=speed: self.set_speed(s))  # Set speed when clicked
            controls_layout.addWidget(button)
            self.speed_buttons[speed] = button

        # Create navigation buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.line_button = QPushButton("Line")
        self.clear_button = QPushButton("Clear All Lines")  # Button to clear all lines
        self.remove_last_button = QPushButton("Remove Line")  # Button to remove last line

        # Set button size
        self.prev_button.setFixedSize(100, 30)
        self.next_button.setFixedSize(100, 30)
        self.start_button.setFixedSize(100, 30)
        self.stop_button.setFixedSize(100, 30)
        self.line_button.setFixedSize(100, 30)
        self.clear_button.setFixedSize(120, 30)
        self.remove_last_button.setFixedSize(120, 30)

        # Connect button clicks
        self.start_button.clicked.connect(self.start_playback)
        self.stop_button.clicked.connect(self.stop_playback)
        self.prev_button.clicked.connect(self.load_previous_file)
        self.next_button.clicked.connect(self.load_next_file)
        self.line_button.clicked.connect(self.toggle_line_drawing)
        self.clear_button.clicked.connect(self.clear_all_lines)  # Connect to clear all lines
        self.remove_last_button.clicked.connect(self.remove_last_line)  # Connect to remove last line

        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addWidget(self.line_button)
        controls_layout.addWidget(self.remove_last_button)
        controls_layout.addWidget(self.clear_button)

        main_layout.addLayout(controls_layout)

        # Create a matplotlib figure and canvas
        self.fig, self.ax = plt.subplots(figsize=(10, 5))  # Create a figure
        self.canvas = FigureCanvas(self.fig)  # Create a canvas for the figure
        main_layout.addWidget(self.canvas)  # Add the canvas to the layout

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Create the initial plot
        self.plot_candlestick()  # Initial plot with only the first candle

        # Set fixed view limits for the plot
        self.update_view_limits()

        # Connect mouse events for drawing
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def load_data(self, file_path):
        # Load the CSV data
        data = pd.read_csv(file_path)
        # Rename columns to match mplfinance's expected names
        data.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'volume': 'Volume'}, inplace=True)
        data['time'] = pd.to_datetime(data['time'])
        data.set_index('time', inplace=True)  # Set time as index for mplfinance
        return data

    def plot_candlestick(self):
        # Clear the previous plot
        self.ax.clear()

        # Plot all candles up to the current index without changing the x/y limits
        mpf.plot(self.data.iloc[:self.current_index + 1],
                type='candle',
                style='classic',
                ax=self.ax,
                volume=False)

        # Plot buy and sell markers
        if self.buy_marker is not None:
            self.ax.annotate('Buy', (self.buy_marker, self.data['Low'].iloc[self.buy_marker]), 
                            xytext=(self.buy_marker, self.data['Low'].iloc[self.buy_marker] - 5),
                            arrowprops=dict(facecolor='green', shrink=0.05), color='green', fontsize=8)

        if self.sell_marker is not None:
            self.ax.annotate('Sell', (self.sell_marker, self.data['High'].iloc[self.sell_marker]), 
                            xytext=(self.sell_marker, self.data['High'].iloc[self.sell_marker] + 5),
                            arrowprops=dict(facecolor='red', shrink=0.05), color='red', fontsize=8)


        # Draw user-defined horizontal lines (blue)
        for line in self.lines:
            self.ax.axhline(y=line, color='blue', linewidth=1)

        self.ax.set_title('XAU/USD Candlestick Playback')  # Optional title
        self.update_view_limits()  # Update x and y limits based on the current index
        self.canvas.draw()  # Redraw the canvas

    def update_view_limits(self):
        # Update x-axis limits based on the number of candles plotted
        if self.current_index >= self.x_limit:
            self.x_limit += 30  # Increase limit in increments of 30

        self.ax.set_xlim(0, self.x_limit)  # Set the new x-axis limit

        # Set y-axis limits with padding
        self.ax.set_ylim(self.data['Low'].min() - 5, self.data['High'].max() + 5)

    def start_playback(self):
        if not self.running:
            self.running = True
            self.playback()

    def stop_playback(self):
        self.running = False

    def playback(self):
        if self.running and self.current_index < len(self.data) - 1:  # Update to not exceed the data length
            self.current_index += 1  # Increment to the next candle
            self.plot_candlestick()  # Plot current and previous candles
            QTimer.singleShot(self.playback_speed, self.playback)  # Call this function again after the set speed

    def set_speed(self, speed):
        self.playback_speed = speed  # Set the new playback speed

    def load_previous_file(self):
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self.load_data_and_plot()

    def load_next_file(self):
        if self.current_file_index < len(self.data_files) - 1:
            self.current_file_index += 1
            self.load_data_and_plot()

    def load_data_and_plot(self):
        # Stop playback before loading new data
        self.stop_playback()
        
        # Load new data and reset the index
        self.data = self.load_data(self.data_files[self.current_file_index])
        self.current_index = 0  # Reset to the first candle
        self.buy_marker = None  # Clear previous buy marker
        self.sell_marker = None  # Clear previous sell marker
        self.active_trade = None  # Reset active trade status
        self.lines.clear()  # Clear previous lines
        self.plot_candlestick()  # Plot with new data

    def keyPressEvent(self, event):
        # Handle key presses for buy/sell/close actions
        if event.key() == Qt.Key_Space:
            if self.running:
                self.stop_playback()
            else:
                self.start_playback()
        elif event.key() == Qt.Key_B:
            self.place_buy_order()
        elif event.key() == Qt.Key_S:
            self.place_sell_order()
        elif event.key() == Qt.Key_C:
            self.close_order()
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.remove_last_line()  # Remove last line on Ctrl+Z (or Command+Z on Mac)
        elif event.key() == Qt.Key_L:
            self.toggle_line_drawing()  # Toggle line drawing mode with 'L'
        self.plot_candlestick()  # Update plot after any key event

    def toggle_line_drawing(self):
        # Toggle line drawing mode
        self.drawing_line = not self.drawing_line
        if self.drawing_line:
            print("Line drawing mode activated. Click on the chart to set a horizontal line.")
        else:
            print("Line drawing mode deactivated.")

    def on_click(self, event):
        if self.drawing_line and event.inaxes == self.ax:
            y_position = event.ydata  # Get the y position where the user clicked
            self.lines.append(y_position)  # Save the y-coordinate of the line
            print(f"Horizontal line drawn at y={y_position}")
            self.plot_candlestick()  # Redraw the plot with the new line
            # Keep drawing mode activated to allow drawing more lines
            # self.drawing_line = False  # Commenting this line to allow placing multiple lines without deactivation

    def remove_last_line(self):
        if self.lines:  # Check if there are lines to remove
            removed_line = self.lines.pop()  # Remove the last line
            print(f"Removed last line at y={removed_line}")
            self.plot_candlestick()  # Redraw the plot after removal

    def clear_all_lines(self):
        self.lines.clear()  # Clear all lines
        print("Cleared all lines.")
        self.plot_candlestick()  # Redraw the plot after clearing lines

    def place_buy_order(self):
        if self.active_trade is None:  # No active trade, place buy
            self.buy_marker = self.current_index
            self.active_trade = 'buy'
            print(f"Buy order placed at index {self.current_index}")

    def place_sell_order(self):
        if self.active_trade is None:  # No active trade, place sell
            self.sell_marker = self.current_index
            self.active_trade = 'sell'
            print(f"Sell order placed at index {self.current_index}")

    def close_order(self):
        if self.active_trade == 'buy':
            print(f"Closing buy order placed at index {self.buy_marker}")
            self.buy_marker = None
        elif self.active_trade == 'sell':
            print(f"Closing sell order placed at index {self.sell_marker}")
            self.sell_marker = None
        self.active_trade = None  # Reset active trade

if __name__ == "__main__":
    # List all CSV files in the "data" directory
    data_folder = 'data'  # Update this path if needed
    data_files = [os.path.join(data_folder, f) for f in os.listdir(data_folder) if f.endswith('.csv')]

    app = QApplication(sys.argv)
    window = CandlestickApp(data_files)
    window.show()
    sys.exit(app.exec_())
