from flask import Flask, request, render_template, redirect, url_for, jsonify, session, send_from_directory
from datetime import datetime, timedelta
import requests
import os
from werkzeug.utils import secure_filename
import random
import string


app = Flask(__name__)
app.secret_key = "dsfasdfdafghtr"

# Directory to save uploaded files
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# SSLCOMMERZ configuration
SSL_STORE_ID = 'abc653382f863118'
SSL_STORE_PASS = 'abc653382f863118@ssl'
SSL_SANDBOX_MODE = True  # Set to False for live mode

# Set the SSLCOMMERZ API URL
SSL_URL = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php" if SSL_SANDBOX_MODE else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_booking_id():
    random_letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    random_numbers = ''.join(random.choices(string.digits, k=2))
    return f"REU-{random_letters}-{random_numbers}"

# Set the countdown end time to 5 minutes from now
COUNTDOWN_END_TIME = datetime.now() + timedelta(minutes=400)

# Set the event date here
EVENT_DATE_STR = "2024-12-31 23:59:59"  # Change this to your desired date
EVENT_DATE = datetime.strptime(EVENT_DATE_STR, "%Y-%m-%d %H:%M:%S")

@app.route("/")
def index():
    current_date = datetime.now()
    # Check if the event date is in the future
    is_future_event = current_date < EVENT_DATE
    countdown_end_time_str = EVENT_DATE.strftime("%b %d, %Y %H:%M:%S")
    
    return render_template(
        "form.html", 
        current_date=current_date.strftime('%a, %b %d %Y'), 
        countdown_end_time_str=countdown_end_time_str,
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
    guest_price = 10  # Assuming each guest costs 10

    # Calculate total guest price
    guest_total_price = guest_count * guest_price

    # Calculate the total price correctly
    total_price = batch_price + guest_total_price + donation_amount
    
    # Update session data
    session["guest_count"] = guest_count
    session["donation_amount"] = donation_amount
    session["total_price"] = total_price
    batch_selection = request.form.get("batch-selection", "N/A")
    batch_name = {
        "3000": "Batch-(1974-1985)year - ৳ 3000",
        "2500": "Batch-(1986-2000)year - ৳ 2500",
        "2000": "Batch-(2001-2015)year - ৳ 2000",
        "1500": "Batch-(2016-2023)year - ৳ 1500",
        "1000": "Running Student ( Class 6-9 ) - ৳ 1000"
    }.get(batch_selection, "N/A")
    session["batch_selection"] = batch_name
    
    # Prepare the payload for SSLCOMMERZ payment initiation
    payload = {
        'store_id': SSL_STORE_ID,
        'store_passwd': SSL_STORE_PASS,
        'total_amount': str(total_price),
        'currency': 'BDT',
        'tran_id': generate_booking_id(),
        'success_url': url_for('payment_success', _external=True),
        'fail_url': url_for('payment_fail', _external=True),
        'cancel_url': url_for('payment_cancel', _external=True),
        'cus_name': session["full_name"],
        'cus_email': session["email"],
        'cus_add1': session["permanent_address"],
        'cus_city': 'Dhaka',
        'cus_postcode': '1000',
        'cus_country': 'Bangladesh',
        'cus_phone': session["phone_number"],
        'shipping_method': 'NO',
        'product_name': 'Batch Registration',
        'product_category': 'Event',
        'product_profile': 'general'
    }

    # Send the request to SSLCOMMERZ
    response = requests.post(SSL_URL, data=payload)
    response_data = response.json()

    # Redirect to the payment gateway URL
    if response_data['status'] == 'SUCCESS':
        return redirect(response_data['GatewayPageURL'])
    else:
        return f"Payment initiation failed: {response_data.get('failedreason', 'Unknown error')}"

@app.route('/success', methods=['GET', 'POST'])
def payment_success():
    # Generate a booking ID for successful transactions
    booking_id = generate_booking_id()
    session["booking_id"] = booking_id

    # Trigger webhook to the provided URL with session data
    webhook_url = "https://hook.us2.make.com/ai4iufhmog6guoisyc9qqw70jrivs119"
    webhook_payload = {
        "Transaction Date & Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "Name": session.get("full_name", "N/A"),
        "Number": session.get("phone_number", "N/A"),
        "Address": session.get("permanent_address", "N/A"),
        "Blood Group": session.get("blood_group", "N/A"),
        "Gender": session.get("gender", "N/A"),
        "Tshirt Size": session.get("tshirt_size", "N/A"),
        "Donation Amount": session.get("donation_amount", "N/A"),
        "Total Amount Paid": session.get("total_price", "N/A"),
        "Photo URL": session.get("photo_url", "N/A"),
        "Guest": session.get("guest_count", "N/A"),
        "Booking ID": session.get("booking_id", "N/A"),
        "Batch": session.get("batch_selection", "N/A")
    }

    webhook_response = requests.post(webhook_url, json=webhook_payload)
    if webhook_response.status_code == 200:
        booking_id = session["booking_id"]
        # If webhook is successful, clear session data and render success page
        session.clear()
        return render_template("success.html", booking_id=booking_id)
    else:
        # Handle webhook failure (optional logging or retry mechanism can be added)
        return render_template("error.html", error_code="Webhook Error", error_message=f"Failed to send webhook after successful payment. Webhook Response: {webhook_response.text}")

@app.route('/fail', methods=['GET', 'POST'])
def payment_fail():
    return render_template("error.html", error_code="Payment Failed", error_message="Payment failed. Please try again.")

@app.route('/cancel', methods=['GET', 'POST'])
def payment_cancel():
    return render_template("error.html", error_code="Payment Canceled", error_message="Payment was canceled.")

if __name__ == "__main__":
    # Create uploads folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
