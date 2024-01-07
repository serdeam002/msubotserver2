import mysql.connector
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify, g
import jwt
import secrets
from functools import wraps
from contextlib import contextmanager

app = Flask(__name__)
load_dotenv()
CORS(app)

host = os.environ.get('JAWSDB_HOST')
user = os.environ.get('JAWSDB_USER')
password = os.environ.get('JAWSDB_PASSWORD')
database = os.environ.get('JAWSDB_DATABASE')

# Function to create a MySQL connection
def create_db_connection():
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

# Function to get a cursor and connection
@contextmanager
def get_cursor_and_connection():
    connection = create_db_connection()
    cursor = connection.cursor()
    try:
        yield cursor, connection
    finally:
        cursor.close()
        connection.close()

# Close the cursor and connection when the application context is popped
@app.teardown_appcontext
def close_db_context(error):
    if 'db_cursor' in g:
        g.db_cursor.close()
    if 'db_connection' in g:
        g.db_connection.close()

@app.route('/')
def home():
    return "API connected"

@app.route('/api/verify_serial', methods=['GET'])
def verify_serial():
    try:
        user_serial = request.args.get('serial')
        cursor, db_connection = get_cursor_and_connection()

        # Check if the serial exists in the database
        query = "SELECT * FROM computer_usage WHERE serial = %s"
        cursor.execute(query, (user_serial,))
        result = cursor.fetchone()
        print(result)

        if result:
            # Check if the serial in computer_usage matches the one entered by the user
            if result[2] == user_serial:
                # Serials match, open the program
                return jsonify({"error": "Serial is already in use.\nซีเรียลถูกใช้งานแล้ว"})
            else:
                # Serials don't match, proceed to insert the serial
                return insert_serial(user_serial)
        else:
            # Serial not found, proceed to insert the serial
            return insert_serial(user_serial)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/insert_serial', methods=['POST'])
def insert_serial(user_serial):
    try:
        cursor, db_connection = get_cursor_and_connection()
        client_mac_address = request.headers.get('mac_address')

        # Check if the serial exists in the database
        query = "SELECT * FROM serials WHERE serial = %s"
        cursor.execute(query, (user_serial,))
        result = cursor.fetchone()
        print(result)

        if result:
            # Serial exists, store data in computer_usage table
            insert_query = "INSERT INTO computer_usage (mac_address, serial) VALUES (%s, %s)"
            cursor.execute(insert_query, (client_mac_address, user_serial))
            db_connection.commit()

            # Update the status column in the serials table
            update_query = "UPDATE serials SET status = %s WHERE serial = %s"
            cursor.execute(update_query, (True, user_serial))
            db_connection.commit()

            # Display success message
            return jsonify({"message": "Serial successfully used. Program is opening.\nซีเรียลสำเร็จแล้วโปรแกรมกำลังเปิด"})
        else:
            # Display error message for incorrect serial
            return jsonify({"error": "The serial is invalid!.\nซีเรียลไม่ถูกต้อง"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/version', methods=['GET'])
def check_version_server():
    try:
        cursor, db_connection = get_cursor_and_connection()

        # Get the client's MAC address from the request headers
        version = request.headers.get('version')

        # Check if the current computer has used the serial before
        query = "SELECT * FROM version WHERE version = %s"
        cursor.execute(query, (version,))
        result = cursor.fetchone()
        print(result)
        if result:
            # Check if the serial in computer_usage matches the one entered by the user
            if result[1] == version:
                # Serials match, open the program
                return jsonify({"message": "Version ok"})
            else:
                # Serials don't match, proceed to insert the serial
                return jsonify({"error": "Press the OK button to download the new version.\nคุณไม่ได้ใช้เวอร์ชั่นปัจจุบัน ดาวโหลดเวอร์ชั่นใหม่กดปุ่ม OK"})
        else:
            # Serial not found, proceed to insert the serial
            return jsonify({"error": "Press the OK button to download the new version.\nคุณไม่ได้ใช้เวอร์ชั่นปัจจุบัน ดาวโหลดเวอร์ชั่นใหม่กดปุ่ม OK"})

    except Exception as e:
        # Log the error for debugging
        print(f"Error in '/api/version' route: {str(e)}")
        return jsonify({"error": "Internal server error."})

@app.route('/api/computer_usage', methods=['GET'])
def check_computer_usage_server():
    try:
        cursor, db_connection = get_cursor_and_connection()

        # Get the client's MAC address from the request headers
        client_mac_address = request.headers.get('mac_address')

        # Check if the current computer has used the serial before
        query = "SELECT * FROM computer_usage WHERE mac_address = %s"
        cursor.execute(query, (client_mac_address,))
        result = cursor.fetchone()
        print(result)

        if result:
            # Display message for a computer already using the serial
            return jsonify({"message": "This computer already uses serial\nคอมพิวเตอร์เครื่องนี้ใช้ซีเรียลแล้ว.."})
        else:
            return jsonify({"error": "This computer is not running serial yet."})

    except Exception as e:
        # Log the error for debugging
        print(f"Error in '/api/computer_usage' route: {str(e)}")
        return jsonify({"error": "Internal server error."})

###################showdatainwebsite######################

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        try:
            data = jwt.decode(token, secret_key)
            print(f"Decoded Token Data: {data}")
        except jwt.ExpiredSignatureError:
            print("Token has expired")
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            print("Invalid token")
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            print(f"Error during token verification: {str(e)}")
            return jsonify({'error': str(e)}), 401

        return f(*args, **kwargs)

    return decorated

# เพิ่มข้อมูล
@app.route('/api/adddata', methods=['POST'])
@token_required
def add_data():
    cursor, connection = get_cursor_and_connection()

    data = request.get_json()
    serial = data['serial']

    cursor.execute("INSERT INTO serials (serial) VALUES (%s)", (serial,))
    connection.commit()

    return jsonify({"message": "Data added successfully"})

# แก้ไขข้อมูล
@app.route('/api/updatedata/<int:item_id>', methods=['PUT'])
@token_required
def edit_data(item_id):
    try:
        # Get data from request
        data = request.get_json()
        updated_serial = data.get('serial')
        updated_status = data.get('status')

        # Check if both serial and status are provided
        if updated_serial is None or updated_status is None:
            return jsonify({'error': 'Both serial and status are required'}), 400

        # Update data in the database
        cursor, connection = get_cursor_and_connection()
        cursor.execute('UPDATE serials SET serial = %s, status = %s WHERE id = %s',
                          (updated_serial, updated_status, item_id))
        connection.commit()

        return jsonify({'message': 'Data updated successfully'})

    except Exception as e:
        # Print the exception to the console for debugging
        print(f"Error: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

# ลบข้อมูล
@app.route('/api/deletedata/<int:id>', methods=['DELETE'])
@token_required
def delete_data(id):
    cursor, connection = get_cursor_and_connection()

    cursor.execute("DELETE FROM serials WHERE id = %s", (id,))
    connection.commit()

    return jsonify({"message": "Data deleted successfully"})

# ดึงข้อมูลทั้งหมด
@app.route('/api/getdata', methods=['GET'])
@token_required
def get_data():
    cursor, connection = get_cursor_and_connection()

    cursor.execute("SELECT * FROM serials")
    result = cursor.fetchall()

    response = jsonify(result)
    return response

#################login######################

secret_key = secrets.token_urlsafe(32)

# Decorator to require a valid token for protected routes
def get_user_from_database(user_id, cursor, connection):
    try:
        query = "SELECT * FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        connection.commit()  # Commit the changes to the database
        return user
    except Exception as e:
        print(f"Error getting user from database: {e}")
        return None



# Route for user login

def check_user_credentials(username, password, cursor, connection):
    try:
        query = "SELECT * FROM users WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        connection.commit()  # Commit the changes to the database
        return user
    except Exception as e:
        print(f"Error checking user credentials: {e}")
        return None
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    username = data.get('username')
    password = data.get('password')

    cursor, connection = get_cursor_and_connection()

    user = check_user_credentials(username, password, cursor, connection)

    if user:
        # Create a JWT token with user information
        token = jwt.encode({'user_id': user[0], 'username': user[1]}, secret_key, algorithm='HS256')
        return jsonify({'token': token})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

# Protected route requiring a valid token
@app.route('/protected', methods=['GET'])
@token_required
def protected():
    return jsonify({'message': 'Protected route', 'user': {'id': request.user[0], 'username': request.user[1]}})

if __name__ == '__main__':
    app.run(debug=True)
