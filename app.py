from flask import Flask, request, redirect, url_for, render_template, session
import requests

app = Flask(__name__)
app.secret_key = 'dsfasdfdafghtr'

# SSLCOMMERZ configuration
SSL_STORE_ID = 'abc653382f863118'
SSL_STORE_PASS = 'abc653382f863118@ssl'
SSL_SANDBOX_MODE = True  # Set to False for live mode

# Set the SSLCOMMERZ API URL based on the environment
SSL_URL = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php" if SSL_SANDBOX_MODE else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"

@app.route('/')
def home():
    # Renders the main booking form
    return render_template('form.html')

@app.route('/initiate_booking_payment', methods=['POST'])
def initiate_booking_payment():
    # Capture form data and store in session
    session["full_name"] = request.form.get("full_name")
    session["phone_number"] = request.form.get("phone_number")
    session["address"] = request.form.get("address")
    session["total_price"] = request.form.get("total_price")
    session["donation_amount"] = request.form.get("donation_amount", 0)
    session["transaction_id"] = f'booking_tran_{int(session["total_price"])}'

    # Debugging prints
    print("Full Name:", session.get("full_name"))
    print("Phone Number:", session.get("phone_number"))
    print("Address:", session.get("address"))  # Check if address is captured
    print("Total Price:", session.get("total_price"))
    print("Donation Amount:", session.get("donation_amount"))

    # Prepare the payload for payment initiation
    payload = {
        'store_id': SSL_STORE_ID,
        'store_passwd': SSL_STORE_PASS,
        'total_amount': session["total_price"],
        'currency': 'BDT',
        'tran_id': session["transaction_id"],
        'success_url': url_for('payment_success', _external=True),
        'fail_url': url_for('payment_fail', _external=True),
        'cancel_url': url_for('payment_cancel', _external=True),
        'cus_name': session["full_name"],
        'cus_email': 'user@example.com',  # Replace with actual email if available
        'cus_add1': session["address"],   # This should now contain the address
        'cus_city': 'Dhaka',
        'cus_postcode': '1000',
        'cus_country': 'Bangladesh',
        'cus_phone': session["phone_number"],
        'shipping_method': 'NO',
        'product_name': 'Ticket Booking',
        'product_category': 'Service',
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
    # Prepare data payload for the webhook with dynamic values from session
    payload = {
        "full_name": session.get("full_name"),
        "phone_number": session.get("phone_number"),
        "address": session.get("address"),
        "total_price": session.get("total_price"),
        "donation_amount": session.get("donation_amount"),
        "transaction_id": session.get("transaction_id"),
        "status": "success"
    }

    # Trigger the webhook with the payload (this part assumed to be working)

    # Send the webhook request to the specified URL
    webhook_url = "https://hook.us2.make.com/ai4iufhmog6guoisyc9qqw70jrivs119"
    response = requests.post(webhook_url, json=payload)

    # Check if webhook was successful (optional logging)
    if response.status_code == 200:
        print("Webhook triggered successfully.")
    else:
        print(f"Webhook failed with status code {response.status_code}.")

        
    # Clear session data to avoid duplication in future requests
    session.pop("full_name", None)
    session.pop("phone_number", None)
    session.pop("address", None)
    session.pop("total_price", None)
    session.pop("donation_amount", None)
    session.pop("transaction_id", None)

    return "Ticket booking completed successfully."



@app.route('/fail', methods=['GET', 'POST'])
def payment_fail():
    return "Ticket booking failed. Please try again."

@app.route('/cancel', methods=['GET', 'POST'])
def payment_cancel():
    return "Ticket booking was canceled."

if __name__ == '__main__':
    app.run(debug=True)