# OANDA Trading Platform Setup Guide (macOS)

## Prerequisites
- MacOS operating system
- OANDA trading account with the following credentials:
  - Account ID
  - Access Token
  - Account Type (Live or Practice)
- Ports 3000 and 3001 available (close any applications using these ports)

## Installation Steps

### 1. Security Settings Configuration
Navigate to your System Settings to allow the installation:
1. Open System Settings
2. Go to Privacy & Security
3. Scroll down until you see the message:
   > "run.command" was blocked from use because it is not from an identified developer
4. Click "Open Anyway" to proceed

### 2. Terminal Setup
1. The Terminal will open automatically
2. You will be prompted to enter your OANDA credentials:
   - Account ID
   - Access Token
   - Account Type

### 3. Application Launch
1. The installation process will begin automatically
2. Once completed, your default browser will open
3. The application will be available at `localhost:3000`

## Troubleshooting
If you encounter any issues:
- Ensure ports 3000 and 3001 are not in use
- Verify your OANDA credentials are correct
- Check your internet connection


## Support
If you need assistance, please open an issue in this repository.
