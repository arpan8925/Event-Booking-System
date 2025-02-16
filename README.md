# Flask Payment & Registration System

![Flask Logo](https://upload.wikimedia.org/wikipedia/commons/3/3c/Flask_logo.svg)

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Steps](#steps)
- [Configuration](#configuration)
- [Usage](#usage)
- [Endpoints](#endpoints)
- [Dependencies](#dependencies)
- [Security Considerations](#security-considerations)
- [Project Screenshots](#project-screenshots)
- [License](#license)

## Introduction
This is a Flask-based web application that facilitates event registration and payment processing using the bKash API. Users can select their batch, pay for their registration, and optionally donate additional funds. The system securely handles file uploads, payment authentication, and webhook notifications.

![bKash Logo](https://upload.wikimedia.org/wikipedia/commons/5/5b/BKash-Logo.wine.svg)

## Features
- **User Registration:** Users provide personal details and select their batch category.
- **File Upload Support:** Users can upload profile pictures with secure handling.
- **bKash Payment Gateway Integration:** Supports payment initiation, execution, and confirmation.
- **Session-based Data Storage:** Temporary storage of user information using Flask sessions.
- **Webhook Integration:** Sends payment confirmations to external services.
- **Secure Booking ID Generation:** Uses UUIDs to ensure unique transactions.

## Installation

### Prerequisites
Ensure you have the following installed:

- Python 3.x
- pip (Python package manager)
- virtualenv (Optional but recommended)

### Steps

Clone the repository:

```sh
git clone https://github.com/your-repo/flask-payment-system.git
cd flask-payment-system
```

Create a virtual environment (optional but recommended):

```sh
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

Install dependencies:

```sh
pip install -r requirements.txt
```

Run the application:

```sh
python app.py
```

The application should now be running on `http://127.0.0.1:5000/`.

## Configuration

### Environment Variables
Replace the sensitive information in `app.py` with environment variables:

```python
import os

APP_KEY = os.getenv("BKASH_APP_KEY")
APP_SECRET = os.getenv("BKASH_APP_SECRET")
USERNAME = os.getenv("BKASH_USERNAME")
PASSWORD = os.getenv("BKASH_PASSWORD")
```

Set these in your environment:

```sh
export BKASH_APP_KEY="your_app_key"
export BKASH_APP_SECRET="your_app_secret"
export BKASH_USERNAME="your_username"
export BKASH_PASSWORD="your_password"
```

Alternatively, create a `.env` file and use `python-dotenv` to load them.

## Usage
1. Open the application in your browser (`http://127.0.0.1:5000/`).
2. Fill out the registration form and upload your photo.
3. Choose your batch category and enter additional details.
4. Proceed with the bKash payment process.
5. On successful payment, a confirmation page is displayed, and data is sent to a webhook.

## Endpoints

| Route                     | Method | Description                                         |
|---------------------------|--------|-----------------------------------------------------|
| `/`                       | GET    | Displays the registration form                     |
| `/initiate_booking_payment` | POST   | Captures user data and initiates bKash payment     |
| `/execute_payment`        | GET    | Executes the payment after user confirmation       |
| `/payment_callback`       | GET    | Handles payment callback response from bKash       |

## Dependencies

The project uses the following dependencies:

- **Flask** - Web framework
- **Werkzeug** - Secure file handling
- **Requests** - HTTP requests for bKash API
- **UUID** - Unique booking ID generation

Install dependencies using:

```sh
pip install -r requirements.txt
```

## Security Considerations
- **Avoid Hardcoded Credentials:** Use environment variables instead.
- **Secure File Uploads:** Only allow specific extensions (`png, jpg, jpeg, gif`).
- **Session Protection:** Flask session keys should be securely stored.
- **HTTPS Usage:** Always deploy using HTTPS to encrypt sensitive payment data.

## Project Screenshots

![Project Screenshot 1](path/to/your/screenshot1.png)

![Project Screenshot 2](path/to/your/screenshot2.png)

## License
This project is licensed under the MIT License.
