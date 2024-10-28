from flask import Flask, request, render_template, redirect, url_for, jsonify, session
import requests

app = Flask(__name__)
app.secret_key = "dsfasdfdafghtr"

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
        return response.json()["id_token"]
    else:
        return None

@app.route("/")
def index():
    return render_template("form.html")

@app.route("/initiate_booking_payment", methods=["POST"])
def initiate_booking_payment():
    # Capture form data and calculate total amount
    session["full_name"] = request.form.get("full_name")
    session["phone_number"] = request.form.get("phone_number")
    session["address"] = request.form.get("address")
    session["donation_amount"] = request.form.get("donation_amount", 0)

    # Calculate total price
    batch_price = int(request.form.get("batch-selection", 0))
    donation_amount = int(session["donation_amount"] or 0)
    total_price = batch_price + donation_amount
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
        "merchantInvoiceNumber": f"INV{total_price}_{session['phone_number']}"
    }

    response = requests.post(CREATE_PAYMENT_URL, json=payload, headers=headers)
    if response.status_code == 200 and response.json().get("statusCode") == "0000":
        payment_data = response.json()
        session["payment_id"] = payment_data["paymentID"]
        session["id_token"] = id_token
        return redirect(payment_data["bkashURL"])
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
    
    # Define URL for the execute payment endpoint
    url = f"https://tokenized.sandbox.bka.sh/v1.2.0-beta/tokenized/checkout/execute"

    # Set headers with both Authorization and X-APP-Key
    headers = {
        "Authorization": f"Bearer {id_token}",
        "X-APP-Key": APP_KEY,  # Make sure APP_KEY is defined as your bKash app key
        "content-type": "application/json"
    }

    # Include paymentID in the JSON payload
    payload = {
        "paymentID": payment_id
    }

    # Send the POST request to bKash's execute endpoint
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        payment_result = response.json()
        
        # Check if payment execution was successful
        if payment_result.get("statusCode") == "0000":  # "0000" indicates success in bKash API
            session.clear()  # Clear session data
            return render_template("success.html", payment_result=payment_result)
        else:
            # Render error page with specific error message from bKash
            error_message = payment_result.get("statusMessage", "Unknown error")
            return render_template("error.html", error_code=payment_result.get("statusCode"), error_message=error_message)
    else:
        # Render error page for a failure in the HTTP response
        return render_template("error.html", error_code="Payment Execution Error", error_message="Failed to execute payment.")



# Step 4: Payment Callback
@app.route("/payment_callback")
def payment_callback():
    payment_id = request.args.get("paymentID")
    status = request.args.get("status")
    
    if status == "success":
        return redirect(url_for("execute_payment"))
    elif status == "failure":
        return render_template("failure.html")
    elif status == "cancel":
        return render_template("failure.html")
    else:
        return "Unknown payment status."

if __name__ == "__main__":
    app.run(debug=True)
