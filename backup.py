from flask import Flask, request, render_template, redirect, url_for, jsonify, session, send_from_directory
import requests
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "dsfasdfdafghtr"

# Directory to save uploaded files
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# bKash Sandbox API Credentials
APP_KEY = "0vWQuCRGiUX7EPVjQDr0EUAYtc"
APP_SECRET = "jcUNPBgbcqEDedNKdvE4G1cAK7D3hCjmJccNPZZBq96QIxxwAMEx"
USERNAME = "01770618567"
PASSWORD = "D7DaC<*E*eG"

# Set bKash API URLs
BKASH_BASE_URL = "https://tokenized.sandbox.bka.sh/v1.2.0-beta/tokenized/checkout/"
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

@app.route("/")
def index():
    return render_template("form.html")

@app.route("/initiate_booking_payment", methods=["POST"])
def initiate_booking_payment():
    # Capture form data and store it in session for later use in the webhook
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
            filename = secure_filename(photo.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(file_path)
            photo_url = url_for('uploaded_file', filename=filename, _external=True)
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
        donation_amount = int(request.form.get("donation_amount", 0))
    except ValueError:
        donation_amount = 0
    
    total_price = batch_price + donation_amount
    session["donation_amount"] = donation_amount
    session["total_price"] = total_price

    # Generate token for bKash payment
    id_token = generate_token()
    if not id_token:
        return "Failed to generate bKash token. Please try again later."

    # Step 2: Create Payment (Only send necessary data for payment)
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
        "merchantInvoiceNumber": f"INV{total_price}_{session['phone_number']}"
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
    # Retrieve token and payment ID from the session
    id_token = session.get("id_token")
    payment_id = session.get("payment_id")

    # Verify if token and payment ID are available
    if not id_token or not payment_id:
        return render_template("error.html", error_code="Missing Data", error_message="Token or Payment ID is missing.")

    # Set headers with both Authorization and X-APP-Key
    headers = {
        "Authorization": f"Bearer {id_token}",
        "X-APP-Key": APP_KEY,
        "accept": "application/json",
        "content-type": "application/json"
    }

    # Include paymentID in the JSON payload
    payload = {
        "paymentID": payment_id
    }

    # Send the POST request to bKash's execute endpoint
    response = requests.post(EXECUTE_PAYMENT_URL, json=payload, headers=headers)
    if response.status_code == 200:
        payment_result = response.json()

        # Check if payment execution was successful
        if payment_result.get("statusCode") == "0000":
            # Trigger webhook to the provided URL with session data
            webhook_url = "https://hook.us2.make.com/ai4iufhmog6guoisyc9qqw70jrivs119"
            webhook_payload = {
                "Name": session.get("full_name", "N/A"),
                "Number": session.get("phone_number", "N/A"),
                "Address": session.get("permanent_address", "N/A"),
                "Blood Group": session.get("blood_group", "N/A"),
                "Gender": session.get("gender", "N/A"),
                "Tshirt Size": session.get("tshirt_size", "N/A"),
                "Donation Amount": session.get("donation_amount", "N/A"),
                "Total Amount Paid": session.get("total_price", "N/A"),
                "Photo URL": session.get("photo_url", "N/A")
            }

            webhook_response = requests.post(webhook_url, json=webhook_payload)
            if webhook_response.status_code == 200:
                # If webhook is successful, clear session data and render success page
                session.clear()
                return render_template("success.html", payment_result=payment_result)
            else:
                # Handle webhook failure (optional logging or retry mechanism can be added)
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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return redirect(os.path.join(app.config['UPLOAD_FOLDER'], filename))

if __name__ == "__main__":
    # Create uploads folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
