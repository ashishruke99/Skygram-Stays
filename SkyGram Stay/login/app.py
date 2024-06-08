from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Mock users for demonstration
users = {
    "user@example.com": {"password": "userpassword", "role": "user"},
    "admin@example.com": {"password": "adminpassword", "role": "admin"}
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form.get('userId') or request.form.get('adminId') or request.form.get('signInId')
        password = request.form.get('password') or request.form.get('adminPassword') or request.form.get('signInPassword')

        if user_id in users and users[user_id]["password"] == password:
            if users[user_id]["role"] == "user":
                return redirect(url_for('user_dashboard'))
            elif users[user_id]["role"] == "admin":
                return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid ID or password.'

    return render_template('login.html', error=error)

@app.route('/user_dashboard')
def user_dashboard():
    return 'Welcome to the User Dashboard'

@app.route('/admin_dashboard')
def admin_dashboard():
    return 'Welcome to the Admin Dashboard'

@app.route('/forgot_password')
def forgot_password():
    return 'Forgot Password page - To be implemented'

@app.route('/create_account')
def create_account():
    return 'Create New Account page - To be implemented'

if __name__ == '__main__':
    app.run(debug=True)
