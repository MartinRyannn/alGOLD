#!/bin/bash

# Set base directory to the directory where the script is located
BASE_DIR=$(dirname "$0")

# Define color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Lock file and PID files
LOCK_FILE="$BASE_DIR/start_stream.lock"
PID_FILE="$BASE_DIR/start_stream.pid"
REACT_PID_FILE="$BASE_DIR/react_frontend.pid"

# Function to kill both backend (3001) and frontend (3000) processes
cleanup() {
    echo -e "${RED}\nTerminating backend and frontend processes...${NC}"

    # Kill the backend process (port 3001)
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null; then
            echo -e "${YELLOW}Killing backend (port 3001) process with PID $PID...${NC}"
            kill $PID
        fi
        rm -f "$PID_FILE"
    else
        echo -e "${RED}No PID file found for backend. Backend might not be running.${NC}"
    fi

    # Kill the React frontend process (port 3000)
    if [[ -f "$REACT_PID_FILE" ]]; then
        REACT_PID=$(cat "$REACT_PID_FILE")
        if ps -p $REACT_PID > /dev/null; then
            echo -e "${YELLOW}Killing React frontend (port 3000) process with PID $REACT_PID...${NC}"
            kill $REACT_PID
        fi
        rm -f "$REACT_PID_FILE"
    else
        echo -e "${RED}No PID file found for React frontend. Frontend might not be running.${NC}"
    fi

    # Remove the lock file
    rm -f "$LOCK_FILE"

    echo -e "${GREEN}Backend and frontend processes terminated.${NC}"
}

# Ensure cleanup is called on script exit
trap cleanup EXIT

# Clear terminal and display title
clear
echo -e "${CYAN}"
cat << "EOF"
          _      _____  ____  _      _____  
    /\   | |    / ____|/ __ \| |    |  __ \ 
   /  \  | |   | |  __| |  | | |    | |  | |
  / /\ \ | |   | | |_ | |  | | |    | |  | |
 / ____ \| |___| |__| | |__| | |____| |__| |
/_/    \_\______\_____|\____/|______|_____/ 
EOF
echo -e "${NC}"

# Prompt the user for OANDA configuration details
echo -e "${WHITE}Please enter your OANDA configuration details:${NC}"
read -p "Account ID: " account_id

# Validate Account ID format
while [[ -z "$account_id" || ! "$account_id" =~ ^[0-9]{3}-[0-9]{3}-[0-9]{8}-[0-9]{3}$ ]]; do
    echo -e "${RED}Invalid Account ID. It should match the pattern 'xxx-xxx-xxxxxxxx-xxx'.${NC}"
    read -p "Please enter a valid Account ID: " account_id
done

read -p "Access Token: " access_token

# Validate Access Token length and format
while [[ -z "$access_token" || ${#access_token} -ne 65 || ! "$access_token" =~ ^[0-9a-f-]{65}$ ]]; do
    echo -e "${RED}Invalid Access Token. It must be exactly 65 characters long.${NC}"
    read -p "Please enter a valid Access Token: " access_token
done

# Prompt for account type (live/practice)
echo -e "${WHITE}Account Type (live/practice):${NC}"
PS3="Choose an option (1 or 2): "
options=("live" "practice")
select account_type in "${options[@]}"
do
    if [[ "$account_type" == "live" || "$account_type" == "practice" ]]; then
        break
    else
        echo -e "${RED}Invalid option. Please select 1 for live or 2 for practice.${NC}"
    fi
done

# Create or overwrite the oanda.cfg file in the backend folder
CONFIG_FILE="$BASE_DIR/backend/oanda.cfg"
cat <<EOF > "$CONFIG_FILE"
[oanda]
account_id = $account_id
access_token = $access_token
account_type = $account_type
EOF

echo -e "${GREEN}oanda.cfg file created successfully in the backend folder.${NC}"

# Check if another instance of start_stream is running
if [[ -f "$LOCK_FILE" ]]; then
    echo -e "${RED}Another instance of start_stream is already running. Exiting...${NC}"
    exit 1
fi

# Create the lock file to prevent multiple instances
touch "$LOCK_FILE"

# Start the backend service (start_stream.py)
echo -e "${WHITE}Starting backend service...${NC}"

cd "$BASE_DIR/backend"

# Ensure that any existing instance of start_stream is terminated
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo -e "${YELLOW}Existing start_stream process found with PID $PID. Terminating it...${NC}"
        kill $PID
        rm "$PID_FILE"
        sleep 3  # Give it time to fully terminate
    fi
fi

# Start start_stream and save its PID
if [[ -f "./start_stream.py" ]]; then
    echo -e "${WHITE}Starting ./start_stream.py...${NC}"
    python3 start_stream.py > start_stream.log 2>&1 &  # Redirect output to a log file
    BACKEND_PID=$!
    echo $BACKEND_PID > "$PID_FILE"
    echo -e "${GREEN}Backend service started with PID $BACKEND_PID.${NC}"
else
    echo -e "${RED}Error: start_stream.py not found in the backend folder.${NC}"
    rm -f "$LOCK_FILE"
    exit 1
fi

# Wait for backend to initialize
echo -e "${WHITE}Waiting for backend service to initialize...${NC}"
sleep 10  # Initial wait time

# Check if the backend service is running on port 3001
max_retries=6  # Retry 6 times (30 seconds total)
retry_interval=5  # Retry every 5 seconds
retry_count=0

while [[ $retry_count -lt $max_retries ]]; do
    if lsof -iTCP:3001 -sTCP:LISTEN | grep -q "Python"; then
        echo -e "${GREEN}Backend is running on port 3001.${NC}"
        break
    else
        retry_count=$((retry_count+1))
        echo -e "${YELLOW}Backend not yet available on port 3001. Retrying ($retry_count/$max_retries)...${NC}"
        sleep $retry_interval
    fi
done

if [[ $retry_count -ge $max_retries ]]; then
    echo -e "${RED}Error: Backend failed to start after multiple attempts.${NC}"
    cleanup
    exit 1
fi

# Start the React frontend
echo -e "${WHITE}Starting React frontend...${NC}"

# Navigate to the design directory and clean up old node modules
DESIGN_DIR="$BASE_DIR/design"
cd "$DESIGN_DIR" || { echo -e "${RED}Error: design directory not found. Check your project structure.${NC}"; cleanup; exit 1; }

# Remove existing node_modules and package-lock.json, then install npm packages
echo -e "${WHITE}Cleaning up old node_modules and package-lock.json...${NC}"
rm -rf node_modules package-lock.json

if [[ -f "package.json" ]]; then
    echo -e "${WHITE}Installing npm packages...${NC}"
    npm install
    echo -e "${GREEN}npm packages installed successfully.${NC}"

    # Start the React frontend
    npm start > react_frontend.log 2>&1 &
    REACT_PID=$!
    echo $REACT_PID > "$REACT_PID_FILE"
    echo -e "${GREEN}React frontend started with PID $REACT_PID.${NC}"
else
    echo -e "${RED}Error: package.json not found in the design folder.${NC}"
    cleanup
    exit 1
fi

# Inform the user
echo -e "${WHITE}The application is now running at http://localhost:3000.${NC}"

# Wait for user input before exiting the script
read -p "Press enter to exit..."

# Cleanup after user input
cleanup