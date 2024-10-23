from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re

# Chrome WebDriver options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
)

# Helper function to format 'due' field into the desired format
def format_due_time(due):
    # Handle cases like "1 hr 31 min"
    if "hr" in due or "min" in due:
        hours = re.search(r'(\d+)\s*hr', due)
        minutes = re.search(r'(\d+)\s*min', due)
        hours_formatted = f"{hours.group(1)}H" if hours else ""
        minutes_formatted = f"{minutes.group(1)}m" if minutes else ""
        return f"{hours_formatted}{minutes_formatted}"

    # Handle cases like "10th-15th"
    elif "-" in due:
        return re.sub(r"(\d+)(?:th|st|nd|rd)", r"\1", due)

    # Return unchanged if no specific pattern found
    return due

# Function to fetch the events from the target website
def fetch_events():
    """Fetch upcoming events from the specified website."""
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    url = "https://www.metalsmine.com/market/goldusd"
    driver.get(url)

    events_data = []

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "alternating")))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        table = soup.find("table", class_="alternating")

        if table:
            rows = table.find_all("tr")
            for row in rows:
                columns = row.find_all("td")
                if len(columns) > 0:
                    due = columns[1].text.strip()
                    impact_span = columns[3].find("span", class_="icon")
                    if impact_span:
                        impact_class = impact_span["class"]
                        impact = (
                            "mid"
                            if "icon--mm-impact-yel" in impact_class
                            else "high"
                            if "icon--mm-impact-red" in impact_class
                            else "low"
                            if "icon--mm-impact-grn" in impact_class
                            else "unknown"
                        )
                    else:
                        impact = "unknown"

                    forecast = columns[7].text.strip() if len(columns) > 7 and columns[7].text.strip() else "N/A"

                    # Format the 'due' field to match the requested format
                    formatted_due = format_due_time(due)

                    if formatted_due or impact != "unknown":  # Only log if there's valid data
                        events_data.append({"due": formatted_due, "impact": impact, "forecast": forecast})

    finally:
        driver.quit()

    return events_data

# Function to periodically scrape the data
def scrape_periodically(interval):
    """Fetch data every 'interval' seconds."""
    while True:
        print(f"Fetching new data at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        events = fetch_events()
        print(events)  # You might want to save this data somewhere or handle it as needed
        time.sleep(interval)

