from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import boto3
import json
import os

app = Flask(__name__)
app.secret_key = 'QJ0trbsxKmiDa5QHWOntfuYQVixPJeyqFYSLDlpx'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    recipient_emails = request.form.getlist('emails')
    file_name = file.filename
    
    s3 = boto3.client('s3')
    S3_BUCKET = 'fileiopython'
    s3.upload_fileobj(file, S3_BUCKET, file_name)
    
    dynamodb = boto3.client('dynamodb')
    dynamodb.put_item(
        TableName='FileSharing',
        Item={
            'file_name': {'S': file_name},
            'recipient_emails': {'SS': recipient_emails},
            'click_count': {'N': '0'}
        }
    )
    
    lambda_client = boto3.client('lambda')
    response = lambda_client.invoke(
        FunctionName='yash.namdev.399@gmail.com',
        InvocationType='Event',
        Payload=json.dumps({
            'file_name': file_name,
            'recipient_emails': recipient_emails
        })
    )
    return redirect(url_for('index'))

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
