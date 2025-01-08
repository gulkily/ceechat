# CeeChat

A secure chat system with message signing. Messages are stored as text files and signed cryptographically.

## Features

- Secure message signing using RSA keypairs
- Message identification using SHA-256 fingerprints
- Simple and clean web interface
- Works with and without JavaScript
- Real-time message updates

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
cd app
python app.py
```

4. Open your browser and visit `http://localhost:5000`

## Security Features

- Each message is signed with RSA private key
- Messages are identified by SHA-256 fingerprint of author's public key
- All user input is properly sanitized to prevent XSS attacks
- Messages are stored in plain text files with signatures for verification

## File Structure

- `/app` - Main application directory
  - `/static` - Static assets (CSS, JavaScript)
  - `/templates` - HTML templates
  - `/messages` - Stored messages
  - `/keys` - RSA keypair storage
  - `app.py` - Main application file

## API Endpoints

- `GET /messages` - Retrieve all messages
- `POST /messages` - Send a new message
