from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from datetime import datetime, timedelta
import requests
import os
from werkzeug.utils import secure_filename
import random
import string
import uuid


app = Flask(__name__)
app.secret_key = "dsfasdfdafghtr"

# Directory to save uploaded files
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Form Values

BATCH_PRICE = [
    {"label": "Batch-(1974-1985)year - ৳ 2500", "value": 1000},
    {"label": "Batch-(1986-2000)year - ৳ 2000", "value": 1000},
    {"label": "Batch-(2001-2015)year - ৳ 1500", "value": 1000},
    {"label": "Batch-(2016-2023)year - ৳ 1000", "value": 1000},
    {"label": "Running Student ( Class 6 - 10 ) - ৳ 1000", "value": 500}
]

GUEST_PRICE = 500



# bKash Sandbox API Credentials
APP_KEY = "tVMpxtyMQCL1ULF7YvD2FWI9tc"
APP_SECRET = "n5EE1Q2U0rft3jVsfHAnNaOZ2WE4d6O64TX8uX3c4NtXAFbds1JM"
USERNAME = "01841886558"
PASSWORD = ";3Ti^j=iu[Y"

# Set bKash API URLs
BKASH_BASE_URL = "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout/"
TOKEN_URL = BKASH_BASE_URL + "token/grant"
CREATE_PAYMENT_URL = BKASH_BASE_URL + "create"
EXECUTE_PAYMENT_URL = BKASH_BASE_URL + "execute/"

# Step 1: Generate Access Token
def generate_token():
    headers = {
        "username": USERNAME,
        "password": PASSWORD,
        "content-type": "application/json",
        "accept": "application/json"
    }
    payload = {
        "app_key": APP_KEY,
        "app_secret": APP_SECRET
    }
    response = requests.post(TOKEN_URL, json=payload, headers=headers)
    if response.status_code == 200 and response.json().get("statusCode") == "0000":
        return response.json().get("id_token")
    else:
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_booking_id():
    # Use UUID for additional randomness
    unique_id = uuid.uuid4().hex[:6].upper()  # Take first 6 chars of UUID and make it uppercase
    
    # Combine everything to ensure uniqueness, with uppercase unique_id
    return f"REU-{unique_id}"

@app.route("/")
def index():
    # Clear session data when accessing the index page
    session.clear()
    
    countdown_end_time_str = "Jan 10, 2025 23:59:59"
    countdown_end_datetime = datetime.strptime(countdown_end_time_str, "%b %d, %Y %H:%M:%S")
    
    # Format the countdown date for display
    formatted_date = countdown_end_datetime.strftime('%a, %b %d %Y')
    
    # Determine if the countdown is in the future
    is_future_event = datetime.now() < countdown_end_datetime

    # Batch options to be passed to the form
    batch_options = BATCH_PRICE
    guest_price = GUEST_PRICE
    
    return render_template(
        "form.html", 
        current_date=formatted_date,  # Now passing the formatted countdown date
        countdown_end_time_str=countdown_end_time_str,
        batch_options=batch_options,
        guest_price=guest_price,
        is_future_event=is_future_event
    )

@app.route("/initiate_booking_payment", methods=["POST"])
def initiate_booking_payment():
    # Capture form data and store it in session for later use
    session["full_name"] = request.form.get("full_name")
    session["phone_number"] = request.form.get("phone_number")
    session["email"] = request.form.get("email")
    session["profession"] = request.form.get("profession")
    session["gender"] = request.form.get("gender")
    session["blood_group"] = request.form.get("blood_group")
    session["permanent_address"] = request.form.get("permanent_address")
    session["present_address"] = request.form.get("present_address")
    session["tshirt_size"] = request.form.get("tshirt_size")

    # Handle file upload for photo
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo and allowed_file(photo.filename):
            unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            filename = f"photo_{unique_id}.jpg"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(file_path)
            photo_url = url_for('static', filename=f'uploads/{filename}', _external=True)
            session["photo_url"] = photo_url
        else:
            photo_url = "N/A"
            session["photo_url"] = photo_url
    else:
        photo_url = "N/A"
        session["photo_url"] = photo_url

    # Capture batch selection and calculate total price
    try:
        batch_price = int(request.form.get("batch-selection", 0))
    except ValueError:
        batch_price = 0

    try:
        guest_count = int(request.form.get("guest_count", 0))
    except ValueError:
        guest_count = 0
    
    try:
        donation_amount = int(request.form.get("donation_amount", 0))
    except ValueError:
        donation_amount = 0

    # Define the price per guest
    guest_price = GUEST_PRICE  # Assuming each guest costs 800

    # Calculate total guest price
    guest_total_price = guest_count * guest_price

    # Calculate the total price correctly
    total_price = batch_price + guest_total_price + donation_amount
    
    # Update session data
    session["guest_count"] = guest_count
    session["donation_amount"] = donation_amount
    session["total_price"] = total_price

    # Generate token for bKash payment
    id_token = generate_token()
    if not id_token:
        return "Failed to generate bKash token. Please try again later."

    # Step 2: Create Payment
    headers = {
        "Authorization": f"Bearer {id_token}",
        "accept": "application/json",
        "content-type": "application/json",
        "X-APP-Key": APP_KEY
    }
    payload = {
        "mode": "0011",
        "payerReference": session["phone_number"],
        "callbackURL": url_for("payment_callback", _external=True),
        "amount": str(total_price),
        "currency": "BDT",
        "intent": "sale",
        "merchantInvoiceNumber": generate_booking_id()
    }

    response = requests.post(CREATE_PAYMENT_URL, json=payload, headers=headers)
    if response.status_code == 200 and response.json().get("statusCode") == "0000":
        payment_data = response.json()
        session["payment_id"] = payment_data.get("paymentID")
        session["id_token"] = id_token
        return redirect(payment_data.get("bkashURL"))
    else:
        error_message = response.json().get("statusMessage", "Unknown error")
        return f"Payment creation failed: {error_message}"

# Step 3: Execute Payment
@app.route("/execute_payment")
def execute_payment():
    id_token = session.get("id_token")
    payment_id = session.get("payment_id")

    if not id_token or not payment_id:
        return render_template("error.html", error_code="Missing Data", error_message="Token or Payment ID is missing.")

    headers = {
        "Authorization": f"Bearer {id_token}",
        "X-APP-Key": APP_KEY,
        "accept": "application/json",
        "content-type": "application/json"
    }

    payload = {
        "paymentID": payment_id
    }

    response = requests.post(EXECUTE_PAYMENT_URL, json=payload, headers=headers)
    if response.status_code == 200:
        payment_result = response.json()

        if payment_result.get("statusCode") == "0000":
            # Extract customerMsisdn and trxID from the payment result
            customer_msisdn = payment_result.get("customerMsisdn", "N/A")
            trx_id = payment_result.get("trxID", "N/A")

            booking_id = generate_booking_id()
            session["booking_id"] = booking_id

            # Prepare webhook payload with additional fields
            webhook_url = "https://hook.us2.make.com/ai4iufhmog6guoisyc9qqw70jrivs119"
            webhook_payload = {
                "Transaction Date & Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Name": session.get("full_name", "N/A"),
                "Number": session.get("phone_number", "N/A"),
                "Address": session.get("permanent_address", "N/A"),
                "Email": session.get("email", "N/A"),
                "Blood Group": session.get("blood_group", "N/A"),
                "Gender": session.get("gender", "N/A"),
                "Tshirt Size": session.get("tshirt_size", "N/A"),
                "Donation Amount": session.get("donation_amount", "N/A"),
                "Total Amount Paid": session.get("total_price", "N/A"),
                "Photo URL": session.get("photo_url", "N/A"),
                "Guest": session.get("guest_count", "N/A"),
                "Booking ID": session.get("booking_id", "N/A"),
                "Batch": session.get("batch_selection", "N/A"),
                "customerMsisdn": customer_msisdn,  # Add customerMsisdn to webhook payload
                "trxID": trx_id  # Add trxID to webhook payload
            }

            webhook_response = requests.post(webhook_url, json=webhook_payload)
            if webhook_response.status_code == 200:
                booking_id = session["booking_id"]
                return render_template("success.html", booking_id=booking_id)
            else:
                return render_template("error.html", error_code="Webhook Error", error_message=f"Failed to send webhook after successful payment. Webhook Response: {webhook_response.text}")
        else:
            error_message = payment_result.get("statusMessage", "Unknown error")
            return render_template("error.html", error_code=payment_result.get("statusCode"), error_message=f"Payment execution failed. bKash Response: {payment_result}")
    else:
        return render_template("error.html", error_code="Payment Execution Error", error_message=f"Failed to execute payment. HTTP Response: {response.status_code}, Message: {response.text}")


# Step 4: Payment Callback
@app.route("/payment_callback")
def payment_callback():
    payment_id = request.args.get("paymentID")
    status = request.args.get("status")

    if status == "success":
        return redirect(url_for("execute_payment"))
    elif status == "failure" or status == "cancel":
        return "Payment failed or was canceled."
    else:
        return "Unknown payment status."

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
