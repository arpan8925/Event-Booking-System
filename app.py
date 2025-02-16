from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from datetime import datetime
import requests
import os
import random
import string
import uuid
import json
from hashlib import md5

with open("config.json", "r") as f:
    config = json.load(f)

app = Flask(__name__)
app.secret_key = "dsfasdfdafghtr"

# Directory to save uploaded files
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# Form Values

GUEST_PRICE = 500

# bKash Sandbox API Credentials
APP_KEY = "4f6o0cjiki2rfm34kfdadl1eqq"
APP_SECRET = "2is7hdktrekvrbljjh44ll3d9l1dtjo4pasmjvs5vl5qr3fug4b"
USERNAME = "sandboxTokenizedUser02"
PASSWORD = "sandboxTokenizedUser02@12345"

# Set bKash API URLs
BKASH_BASE_URL = "https://tokenized.sandbox.bka.sh/v1.2.0-beta/tokenized/checkout/"
TOKEN_URL = BKASH_BASE_URL + "token/grant"
CREATE_PAYMENT_URL = BKASH_BASE_URL + "create"
EXECUTE_PAYMENT_URL = BKASH_BASE_URL + "execute/"

# Add SSLCommerz API URLs
SSLCOMMERZ_SANDBOX_URL = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
SSLCOMMERZ_LIVE_URL = "https://securepay.sslcommerz.com/gwprocess/v4/api.php"

# Step 1: Generate Access Token
def generate_token():
    headers = {
        "username": USERNAME,
        "password": PASSWORD,
        "content-type": "application/json",
        "accept": "application/json",
    }
    payload = {"app_key": APP_KEY, "app_secret": APP_SECRET}
    response = requests.post(TOKEN_URL, json=payload, headers=headers)
    if response.status_code == 200 and response.json().get("statusCode") == "0000":
        return response.json().get("id_token")
    else:
        return None


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_booking_id():
    # Use UUID for additional randomness
    unique_id = (
        uuid.uuid4().hex[:6].upper()
    )  # Take first 6 chars of UUID and make it uppercase
    booking_id = f"REU-{unique_id}"
    print(f"[DEBUG] Booking ID Generated: {booking_id}")  # Debugging line
    # Combine everything to ensure uniqueness, with uppercase unique_id
    return booking_id


@app.route("/")
def index():
    # Clear session data when accessing the index page
    session.clear()

    countdown_end_time_str = "Jan 10, 2025 23:59:59"
    countdown_end_datetime = datetime.strptime(
        countdown_end_time_str, "%b %d, %Y %H:%M:%S"
    )

    # Format the countdown date for display
    formatted_date = countdown_end_datetime.strftime("%a, %b %d %Y")

    # Determine if the countdown is in the future
    is_future_event = datetime.now() < countdown_end_datetime

    # Get available payment gateways from config
    available_gateways = []
    if config.get("sslcommerz", {}).get("enabled", False):
        available_gateways.append({
            "value": "sslcommerz",
            "label": "SSLCommerz (Card/Mobile Banking)"
        })
    if config.get("bkash", {}).get("enabled", False):
        available_gateways.append({
            "value": "bkash",
            "label": "bKash"
        })

    default_gateway = config.get("default_gateway", "sslcommerz")
    guest_price = GUEST_PRICE

    return render_template(
        "form.html",
        current_date=formatted_date,
        countdown_end_time_str=countdown_end_time_str,
        guest_price=guest_price,
        is_future_event=is_future_event,
        available_gateways=available_gateways,
        default_gateway=default_gateway
    )


@app.route("/ssl_success", methods=["GET", "POST"])
def ssl_success():
    val_id = request.args.get("val_id")
    tran_id = request.args.get("tran_id")

    # Validate transaction
    if session.get("ssl_tran_id") != tran_id:
        return render_template("error.html", error_code="Invalid Transaction")

    ssl_config = config["sslcommerz"]
    validation_url = (
        f"https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
        f"?val_id={val_id}&store_id={ssl_config['STORE_ID']}"
        f"&store_passwd={ssl_config['STORE_PASS']}&format=json"
    )

    validation_res = requests.get(validation_url)
    if validation_res.status_code != 200:
        return render_template("error.html", error_code="Validation Failed")

    data = validation_res.json()
    if data["status"] not in ("VALID", "VALIDATED"):
        return render_template("error.html", error_code=data["status"])

    # Process successful payment
    booking_id = generate_booking_id()
    # ... [Webhook and success page logic as in execute_payment] ...
    return render_template("success.html", booking_id=booking_id)


@app.route("/ssl_fail")
def ssl_fail():
    return render_template("error.html", error_code="Payment Failed")


@app.route("/ssl_cancel")
def ssl_cancel():
    return render_template("error.html", error_code="Payment Canceled")


@app.route("/initiate_booking_payment", methods=["POST"])
def initiate_booking_payment():
    # Get selected payment method
    payment_method = request.form.get("payment_method")
    
    # Validate payment method is enabled
    if not config.get(payment_method, {}).get("enabled", False):
        return render_template(
            "error.html",
            error_code="INVALID_PAYMENT_METHOD",
            error_message="Selected payment method is not available"
        )

    # Store form data in session
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
    if "photo" in request.files:
        photo = request.files["photo"]
        if photo and allowed_file(photo.filename):
            unique_id = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            filename = f"photo_{unique_id}.jpg"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            photo.save(file_path)
            photo_url = url_for(
                "static", filename=f"uploads/{filename}", _external=True
            )
            session["photo_url"] = photo_url
        else:
            photo_url = "N/A"
            session["photo_url"] = photo_url
    else:
        photo_url = "N/A"
        session["photo_url"] = photo_url

    # Calculate total price
    try:
        guest_count = int(request.form.get("guest_count", 0))
        donation_amount = int(request.form.get("donation_amount", 0))
    except ValueError:
        guest_count = 0
        donation_amount = 0

    guest_total_price = guest_count * GUEST_PRICE
    total_price = 500 + guest_total_price + donation_amount

    # Update session data
    session["guest_count"] = guest_count
    session["donation_amount"] = donation_amount
    session["total_price"] = total_price

    if payment_method == "sslcommerz":
        # Generate SSL Commerz transaction
        tran_id = str(uuid.uuid4())
        session["ssl_tran_id"] = tran_id

        ssl_config = config["sslcommerz"]
        ssl_url = (
            SSLCOMMERZ_SANDBOX_URL
            if ssl_config["SANDBOX_MODE"]
            else SSLCOMMERZ_LIVE_URL
        )

        payload = {
            # Basic Information
            "store_id": ssl_config["STORE_ID"],
            "store_passwd": ssl_config["STORE_PASS"],
            "total_amount": f"{total_price:.2f}",
            "currency": "BDT",
            "tran_id": tran_id,
            
            # URLs
            "success_url": url_for("ssl_success", _external=True),
            "fail_url": url_for("ssl_fail", _external=True),
            "cancel_url": url_for("ssl_cancel", _external=True),
            
            # Customer Information
            "cus_name": session["full_name"],
            "cus_email": session["email"],
            "cus_phone": session["phone_number"],
            
            # Customer Address
            "cus_add1": session["present_address"],
            "cus_add2": session["permanent_address"],
            "cus_city": "Chittagong",  # Added required field
            "cus_state": "Chittagong",
            "cus_postcode": "4000",
            "cus_country": "Bangladesh",
            
            # Shipping Information (Required even for non-physical goods)
            "shipping_method": "NO",
            "ship_name": session["full_name"],
            "ship_add1": session["present_address"],
            "ship_add2": session["permanent_address"],
            "ship_city": "Chittagong",
            "ship_state": "Chittagong",
            "ship_postcode": "4000", 
            "ship_country": "Bangladesh",
            
            # Product Information
            "product_name": "Event Registration",
            "product_category": "Registration",
            "product_profile": "non-physical-goods",
            
            # Additional Information
            "value_a": session.get("guest_count", "0"),
            "value_b": session.get("donation_amount", "0"),
            "value_c": session.get("tshirt_size", "N/A"),
            "value_d": session.get("blood_group", "N/A")
        }

        response = requests.post(ssl_url, data=payload)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "SUCCESS":
                return redirect(data["GatewayPageURL"])
            else:
                return render_template(
                    "error.html",
                    error_code="PAYMENT_INIT_FAILED",
                    error_message=data.get("failedreason", "Payment initialization failed"),
                )
        else:
            return render_template(
                "error.html",
                error_code="PAYMENT_INIT_FAILED",
                error_message="Failed to connect to payment gateway",
            )

    else:  # bkash payment
        # Existing bKash logic
        id_token = generate_token()
        if not id_token:
            return "Failed to generate bKash token. Please try again later."

        headers = {
            "Authorization": f"Bearer {id_token}",
            "accept": "application/json",
            "content-type": "application/json",
            "X-APP-Key": APP_KEY,
        }
        payload = {
            "mode": "0011",
            "payerReference": session["phone_number"],
            "callbackURL": url_for("payment_callback", _external=True),
            "amount": str(total_price),
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": "TEMP-ID",
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


@app.route("/execute_payment")
def execute_payment():
    id_token = session.get("id_token")
    payment_id = session.get("payment_id")

    if not id_token or not payment_id:
        return render_template(
            "error.html",
            error_code="Missing Data",
            error_message="Token or Payment ID is missing.",
        )

    headers = {
        "Authorization": f"Bearer {id_token}",
        "X-APP-Key": APP_KEY,
        "accept": "application/json",
        "content-type": "application/json",
    }

    payload = {"paymentID": payment_id}

    response = requests.post(EXECUTE_PAYMENT_URL, json=payload, headers=headers)
    if response.status_code == 200:
        payment_result = response.json()

        if payment_result.get("statusCode") == "0000":  # Payment success
            # Generate the booking ID here, after success
            booking_id = generate_booking_id()
            session["booking_id"] = booking_id  # Store the booking ID in the session
            print(
                f"[DEBUG] Booking ID Stored in Session: {booking_id}"
            )  # Debugging line

            # Prepare webhook payload with additional fields
            webhook_url = "https://hook.us2.make.com/ai4iufhmog6guoisyc9qqw70jrivs119"
            webhook_payload = {
                "Transaction Date & Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Name": session.get("full_name", "N/A"),
                "Number": session.get("phone_number", "N/A"),
                "Address": session.get("permanent_address", "N/A"),
                "Email": session.get("email", "N/A"),
                "Blood Group": session.get("blood_group", "N/A"),
                "Profession": session.get("profession", "N/A"),
                "Gender": session.get("gender", "N/A"),
                "Tshirt Size": session.get("tshirt_size", "N/A"),
                "Donation Amount": session.get("donation_amount", "N/A"),
                "Total Amount Paid": session.get("total_price", "N/A"),
                "Photo URL": session.get("photo_url", "N/A"),
                "Guest": session.get("guest_count", "N/A"),
                "Booking ID": booking_id,  # Add the generated booking ID here
                "customerMsisdn": payment_result.get("customerMsisdn", "N/A"),
                "trxID": payment_result.get("trxID", "N/A"),
            }

            # Send the webhook request
            webhook_response = requests.post(webhook_url, json=webhook_payload)
            print(webhook_payload)
            if webhook_response.status_code == 200:
                return render_template("success.html", booking_id=booking_id)
            else:
                return render_template(
                    "error.html",
                    error_code="Webhook Error",
                    error_message=f"Failed to send webhook. Webhook Response: {webhook_response.text}",
                )
        else:
            error_message = payment_result.get("statusMessage", "Unknown error")
            return render_template(
                "error.html",
                error_code=payment_result.get("statusCode"),
                error_message=f"Payment execution failed. bKash Response: {payment_result}",
            )
    else:
        return render_template(
            "error.html",
            error_code="Payment Execution Error",
            error_message=f"Failed to execute payment. HTTP Response: {response.status_code}, Message: {response.text}",
        )


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


def get_sslcommerz_session(payment_data):
    """Generate SSLCommerz payment session"""
    store_id = config["sslcommerz"]["STORE_ID"]
    store_passwd = config["sslcommerz"]["STORE_PASS"]
    is_sandbox = config["sslcommerz"]["SANDBOX_MODE"]

    post_data = {
        'store_id': store_id,
        'store_passwd': store_passwd,
        'total_amount': payment_data['total_amount'],
        'currency': "BDT",
        'tran_id': payment_data['transaction_id'],
        'success_url': url_for('payment_success', _external=True),
        'fail_url': url_for('payment_failure', _external=True),
        'cancel_url': url_for('payment_cancel', _external=True),
        'ipn_url': url_for('payment_ipn', _external=True),
        'cus_name': payment_data['customer_name'],
        'cus_email': payment_data['customer_email'],
        'cus_phone': payment_data['customer_phone'],
        'shipping_method': 'NO',
        'product_name': 'Event Registration',
        'product_category': 'Registration',
        'product_profile': 'non-physical-goods'
    }

    # Add signature
    signature = md5((store_passwd + '|' + store_id + '|' + str(post_data['total_amount']) + '|' + post_data['currency']).encode()).hexdigest()
    post_data['signature_key'] = signature

    url = SSLCOMMERZ_SANDBOX_URL if is_sandbox else SSLCOMMERZ_LIVE_URL
    response = requests.post(url, data=post_data)
    
    return response.json()


@app.route('/process_payment', methods=['POST'])
def process_payment():
    # Get form data
    payment_data = {
        'transaction_id': str(uuid.uuid4()),
        'total_amount': float(request.form.get('total_price')),
        'customer_name': request.form.get('name'),
        'customer_email': request.form.get('email'),
        'customer_phone': request.form.get('phone')
    }
    
    # Store transaction data in session
    session['payment_data'] = payment_data
    
    # Initialize SSLCommerz payment
    response = get_sslcommerz_session(payment_data)
    
    if response.get('status') == 'SUCCESS':
        return redirect(response['GatewayPageURL'])
    else:
        return render_template('error.html', 
                             error_code='PAYMENT_INIT_FAILED',
                             error_message=response.get('failedreason', 'Payment initialization failed'))


@app.route('/payment/success', methods=['POST'])
def payment_success():
    payment_data = request.form
    
    # Verify payment with SSLCommerz
    if verify_sslcommerz_payment(payment_data):
        # Process successful payment
        # Update database, send confirmation email, etc.
        return render_template('success.html', 
                             transaction_id=payment_data.get('tran_id'))
    return render_template('error.html', 
                         error_code='PAYMENT_VERIFICATION_FAILED',
                         error_message='Payment verification failed')


@app.route('/payment/failure', methods=['POST'])
def payment_failure():
    return render_template('failure.html', 
                         error_message=request.form.get('error_message', 'Payment failed'))


@app.route('/payment/cancel', methods=['POST'])
def payment_cancel():
    return render_template('failure.html', 
                         error_message='Payment was cancelled')


@app.route('/payment/ipn', methods=['POST'])
def payment_ipn():
    """Handle Instant Payment Notification from SSLCommerz"""
    payment_data = request.form
    
    if verify_sslcommerz_payment(payment_data):
        # Update payment status in database
        return 'IPN Processed', 200
    return 'IPN Verification Failed', 400


def verify_sslcommerz_payment(payment_data):
    """Verify SSLCommerz payment data"""
    store_id = config["sslcommerz"]["STORE_ID"]
    store_passwd = config["sslcommerz"]["STORE_PASS"]
    
    # Verify signature
    provided_signature = payment_data.get('verify_sign')
    calculated_signature = md5((store_passwd + '|' + store_id + '|' + 
                              payment_data.get('tran_id', '') + '|' + 
                              payment_data.get('amount', '')).encode()).hexdigest()
    
    return (provided_signature == calculated_signature and 
            payment_data.get('status') == 'VALID')


if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(debug=True)
