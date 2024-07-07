import boto3
import botocore
from flask import Flask, render_template, request, redirect, send_file, session, url_for, jsonify
import bcrypt
import json
import requests
import mysql.connector
import random
import hashlib
from datetime import datetime
from botocore.exceptions import ClientError


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

s3 = boto3.client('s3')
s3_bucket_name = 'test-bucket2305'
# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # Replace 'your_region' with your AWS region
client_table_name = 'Clients'  # Replace 'client_table' with your DynamoDB table for clients
designer_table_name = 'Designers'# Replace 'designer_table' with your DynamoDB table for designers
products = 'products'
client_table = dynamodb.Table(client_table_name)
designer_table = dynamodb.Table(designer_table_name)
table = dynamodb.Table('chat')
# product_table = dynamodb.Table(products)

db_config = {
    'user': 'admin',
    'password': 'homelane1234',
    'host': 'homelane.ckjdrkycbboj.us-east-1.rds.amazonaws.com',
    'database': 'homelane',  # Replace with your database name
}

# Initialize MySQL connection
mysql_conn = mysql.connector.connect(**db_config)
mysql_cursor = mysql_conn.cursor(buffered=True)

@app.route('/')
def login_signup():
    return render_template('index.html')


@app.route('/client-registration')
def client_registration():
    return render_template('client-registration.html')

@app.route('/designer-registration')
def designer_registration():
    return render_template('designer-registration.html')

# Handle login form submission for clients
@app.route('/login-client', methods=['POST'])
def loginClient():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        query = f"SELECT email, password FROM clients WHERE email = '{email}'"
        # Fetch user details from the MySQL database
        mysql_cursor.execute(query)
        user = mysql_cursor.fetchone()

        if user and password == user[1]:
            # Successful login
            session['client'] = email  # Store user's email in session
            return redirect(f"/clda/{email}")
        else:
            # Failed login
            return "Invalid credentials"

def login_required(route_function):
    def wrapper(*args, **kwargs):
        if 'client' not in session:
            return redirect(url_for('login-client'))  # Redirect to login page if not logged in
        return route_function(*args, **kwargs)
    wrapper.__name__ = route_function.__name__  # Preserve the original function name
    return wrapper

# Handle signup form submission for clients
@app.route('/signup-client', methods=['POST'])
def signupClient():
    if request.method == 'POST':
        # Get client signup details
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match"

        # Check if the user already exists in the database
        mysql_cursor.execute("SELECT * FROM clients WHERE email = %s", (email,))
        existing_user = mysql_cursor.fetchone()

        if existing_user:
            return "User already exists"

        # Hash the password before storing it
        # hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Store user details in the MySQL database
        sql = "INSERT INTO clients (email, password) VALUES (%s, %s)"
        mysql_cursor.execute(sql, (email, password))
        mysql_conn.commit()

        # Assign a designer to the newly registered client
        # Implement logic to randomly assign a designer or based on some criteria
        assigned_designer_id = assign_designer(email)  # Replace with your assignment logic

        # Create a new project associated with the client and assigned designer
        create_new_project(email, assigned_designer_id)  # Replace with project creation logic
        
        user_folder = f'client_uploads/{email}/'
        
        # Create a DynamoDB table for the user
        try:
            dynamodb.create_table(
                TableName=get_table_name(email),
                KeySchema=[
                        {
                            'AttributeName': 'product_name',  # 'product_name' as the primary key
                            'KeyType': 'HASH'  # You can add 'SORT' key type for composite keys if needed
                        },
                        {
                            'AttributeName': 'product_link',  # Add the second attribute for composite key
                            'KeyType': 'RANGE'  # Specify the key type if it's for a sort key in a composite key
                        }
                        ],
                AttributeDefinitions=[
                            {
                                'AttributeName': 'product_name',
                                'AttributeType': 'S'  # 'S' denotes string type
                            },
                            {
                                'AttributeName': 'product_link',
                                'AttributeType': 'S'
                            }
                        ],
                        ProvisionedThroughput={
                            'ReadCapacityUnits': 1,
                            'WriteCapacityUnits': 1
                        }
            )
        except Exception as e:
            return f"Error creating DynamoDB table: {str(e)}"
        
        # Create the folder in S3
        s3.put_object(Bucket=s3_bucket_name, Key=user_folder)
        
        # Start session for the user
        session['client'] = email

        # Redirect to the desired page after successful signup
        return redirect(f"/clda/{email}")

def get_table_name(email):
    # Hash the email to get a suitable table name
    hashed_email = hashlib.md5(email.encode()).hexdigest()
    
    # Replace invalid characters or add a prefix to the hashed email
    table_name = f"ClientTable_{hashed_email}"
    
    return table_name


def assign_designer(email):
    # Get all available designers from the database
    mysql_cursor.execute("SELECT designer_id FROM designers")
    all_designers = mysql_cursor.fetchall()

    # Example: Randomly assign a designer from the available list
    assigned_designer_id = random.choice(all_designers)[0] if all_designers else None

    # Update the client's record in the database with the assigned designer
    if assigned_designer_id:
        sql = "UPDATE clients SET assigned_designer_id = %s WHERE email = %s"
        mysql_cursor.execute(sql, (assigned_designer_id, email))
        mysql_conn.commit()

    return assigned_designer_id

def create_new_project(email, designer_id):
    # Get client_id based on the email
    mysql_cursor.execute("SELECT client_id FROM clients WHERE email = %s", (email,))
    client_id = mysql_cursor.fetchone()[0] if mysql_cursor.rowcount > 0 else None

    if designer_id and client_id:
        # Insert the new project into the database
        sql = "INSERT INTO projects (client_id, client_email, designer_id) VALUES (%s, %s, %s)"
        mysql_cursor.execute(sql, (client_id, email, designer_id))
        mysql_conn.commit()


# Handle login form submission for designers
@app.route('/login-dsg', methods=['POST'])
def loginDesigner():
    if request.method == 'POST':
        designer_email = request.form['email']
        password = request.form['password']
        
        query = f"SELECT designer_id, password FROM designers WHERE email = '{designer_email}'"
        # Fetch user details from the MySQL database
        mysql_cursor.execute(query)
        user = mysql_cursor.fetchone()

        if user and password == user[1]:
            # Successful login
            session['designer'] = designer_email  # Store user's email in session
            return redirect("/designer-home")
        else:
            # Failed login
            return "Invalid credentials"


# Handle signup form submission for designers
@app.route('/signup-dsg', methods=['POST'])
def signupDesigner():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match"

        # Check if the user already exists in the database
        mysql_cursor.execute("SELECT * FROM designers WHERE email = %s", (email,))
        existing_user = mysql_cursor.fetchone()

        if existing_user:
            return "User already exists"

        # Hash the password before storing it
        

        # Store user details in the MySQL database
        sql = "INSERT INTO designers (email, password) VALUES (%s, %s)"
        mysql_cursor.execute(sql, (email, password))
        mysql_conn.commit()

        return redirect('/designer-home')

@app.route('/client-upload', methods=['POST'])
@login_required
def client_upload():
    try:
        s3 = boto3.client('s3')
        uploaded_files = request.files.getlist('file')
        user_folder = f"client_uploads/{session['client']}/"  # Get the user's folder

        for uploaded_file in uploaded_files:
            s3_key = f"{user_folder}{uploaded_file.filename}"
            s3.upload_fileobj(uploaded_file, s3_bucket_name, s3_key)
        
        

        return redirect(f'/clda/{session["client"]}')
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/clda/<email>')
@login_required
def display_client_folder_images(email):
    try:
        s3 = boto3.client('s3')
        user_folder = f'client_uploads/{session["client"]}/'  # Get the user's folder
        response = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix=user_folder)
        
        image_urls = []
        if 'Contents' in response:
            images = [obj['Key'] for obj in response['Contents'] if obj['Key'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
            
            for image_key in images:
                image_url = s3.generate_presigned_url('get_object', Params={'Bucket': s3_bucket_name, 'Key': image_key})
                image_urls.append((image_key, image_url))
                
        table_name = f"{get_table_name(email)}"
        cl_product_table = dynamodb.Table(table_name)
        
        response = cl_product_table.scan()
        items = response.get('Items', [])
        
        return render_template('clda.html', image_urls=image_urls, items = items)
        
    except Exception as e:
        return str(e)
        
@app.route('/deda')
def display_specific_folder_images():
    try:
        if 'designer' not in session:
            return redirect('/loginDesigner')  # Redirect if designer is not logged in

        if 'client_email' not in session:
            return "No client selected"  # Handle case where no client email is available
        
        s3 = boto3.client('s3')
        designer_email = session['designer']  # Retrieve the logged-in designer's email from the session
        client_email = session['client_email']  # Get the client's email related to the selected project
        
        folder_path = f'client_uploads/{client_email}/'  # Path specific to the client's email
        
        response = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix=folder_path)
        
        image_urls = []
        if 'Contents' in response:
            images = [obj['Key'] for obj in response['Contents'] if obj['Key'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
            
            for image_key in images:
                image_url = s3.generate_presigned_url('get_object', Params={'Bucket': s3_bucket_name, 'Key': image_key})
                image_urls.append((image_key, image_url))
        product_table = dynamodb.Table(get_table_name(client_email))
        response = product_table.scan()
        items = response.get('Items', [])
        
        return render_template('deda.html', image_urls=image_urls, items=items)
    except Exception as e:
        return str(e)
        
@app.route('/update_product', methods=['POST'])
def update_product():
    product_name = request.form['product-name']
    product_link = request.form['product-link']
    client_email = session['client_email']
    product_table = dynamodb.Table(get_table_name(client_email))
    # Add data to DynamoDB
    product_table.put_item(
        Item={
            'product_name': product_name,
            'product_link': product_link
        }
    )
    return redirect('/deda')
    
@app.route('/download/<path:image_key>')
def download_image(image_key):
    bucket = s3_bucket_name  # Assuming s3_bucket_name is defined somewhere
    s3 = boto3.resource('s3')

    try:
        s3.Bucket(bucket).download_file(image_key, 'my_local_image.jpg')
        # Send the downloaded file as a response
        return send_file('my_local_image.jpg', as_attachment=True)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise Exception("An error occurred while downloading the file.")


@app.route('/designer-home')
def designer_home():
    if 'designer' not in session:
        return redirect(url_for('loginDesigner'))  # Redirect if designer is not logged in

    designer_email = session['designer']  # Get the logged-in designer's email
    
    
    mysql_cursor.execute("SELECT  designer_id FROM designers WHERE email = %s", (designer_email,))
    get_id = mysql_cursor.fetchall()
    designer_id =  f"{get_id[0][0]}"
    # Fetch assigned clients for the designer from MySQL
    mysql_cursor.execute("SELECT email FROM clients WHERE assigned_designer_id = %s", (designer_id,))
    get_clients = mysql_cursor.fetchall()
    # assigned_clients = f"{get_clients[0]}"
    # return assigned_clients
    return render_template('designer-dashboard.html', assigned_clients=get_clients)


@app.route('/choose-client')
def choose_client():
    selected_client_email = request.args.get('client_email')

    if selected_client_email:
        # Store the selected client's email in the session
        session['client_email'] = selected_client_email

        # Redirect to the page displaying files related to the selected client
        return redirect(url_for('display_specific_folder_images'))
    else:
        return "Invalid client selection"
@app.route('/designer-upload', methods=['POST'])
@login_required
def designer_upload():
    try:
        s3 = boto3.client('s3')
        uploaded_files = request.files.getlist('file')
        user_folder = f'client_uploads/{session["client_email"]}/'  # Get the user's folder

        for uploaded_file in uploaded_files:
            s3_key = f"{user_folder}{uploaded_file.filename}"
            s3.upload_fileobj(uploaded_file, s3_bucket_name, s3_key)
        
        

        return redirect('/deda')
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

def get_sender_receiver_ids(email):
    
    # Fetch client_id and assigned_designer_id for the given email
    mysql_cursor.execute("SELECT client_id, assigned_designer_id FROM clients WHERE email = %s", (email,))
    result = mysql_cursor.fetchone()

    return result if result else (None, None)

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        sender_email = session['client']  # Replace with actual client's email or get it from the session
        sender_id, receiver_id = get_sender_receiver_ids(sender_email)
        message_content = request.json.get('message_content')

        if not sender_id or not receiver_id:
            return jsonify({"error": "Sender or receiver ID not found"}), 404
            
        timestamp = datetime.now().timestamp()
        
        # Define the sender_type based on who is sending the message
        sender_type = 'c'  # Assuming the sender is the client

        table.put_item(
            Item={
                'message_id': str(timestamp),  # Using timestamp as the message_id for simplicity
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'timestamp': int(timestamp),
                'message_content': message_content,
                'sender_type': sender_type  # Add sender_type attribute
            }
        )
        return jsonify({"message": "Message sent successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/send_message_dsg', methods=['POST'])
def send_message_dsg():
    try:
        sender_email = session['client']  # Replace with actual client's email or get it from the session
        sender_id, receiver_id = get_sender_receiver_ids(sender_email)
        message_content = request.json.get('message_content')

        if not sender_id or not receiver_id:
            return jsonify({"error": "Sender or receiver ID not found"}), 404
            
        timestamp = datetime.now().timestamp()
        
        # Define the sender_type based on who is sending the message
        sender_type = 'd'  # Assuming the sender is the client

        table.put_item(
            Item={
                'message_id': str(timestamp),  # Using timestamp as the message_id for simplicity
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'timestamp': int(timestamp),
                'message_content': message_content,
                'sender_type': sender_type  # Add sender_type attribute
            }
        )
        return jsonify({"message": "Message sent successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500      
        
@app.route('/get_messages', methods=['GET'])
def get_messages():
    try:
        sender_email = session['client']  # Replace with actual client's email or get it from the session
        sender_id, receiver_id = get_sender_receiver_ids(sender_email)

        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Key('sender_id').eq(sender_id) &
                             boto3.dynamodb.conditions.Key('receiver_id').eq(receiver_id)
        )

        messages = response.get('Items', [])
        return jsonify({"messages": messages}), 200

    except ClientError as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_messages_dsg', methods=['GET'])
def get_messages_dsg():
    try:
        sender_email = session['client_email']  # Replace with actual client's email or get it from the session
        sender_id, receiver_id = get_sender_receiver_ids(sender_email)

        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Key('sender_id').eq(sender_id) &
                             boto3.dynamodb.conditions.Key('receiver_id').eq(receiver_id)
        )

        messages = response.get('Items', [])
        return jsonify({"messages": messages}), 200

    except ClientError as e:
        return jsonify({"error": str(e)}), 500
bucket_name = 'test-bucket'
if __name__ == '__main__':
    app.run(debug=True,port=9000,host='0.0.0.0')
