from flask import Flask
from flask_mail import Mail, Message
import json

app = Flask(__name__)

# Load email configuration from config.json
with open('config.json', 'r') as f:
    params = json.load(f)["params"]

# Initialize Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = params['gmail_user']
app.config['MAIL_PASSWORD'] = params['gmail_password']
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

@app.route("/")
def index():
    # Create a message
    msg = Message("Important Mail", sender="ashish2002ruke@gmail.com", recipients=["ashish2002manoj@gmail.com"])
    msg.body = "Hello! A new video of Flask tutorial is published."

    # Send the message
    mail.send(msg)
    
    return "Message sent successfully!"

if __name__ == "__main__":
    app.run(debug=True)
