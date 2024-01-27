import mysql.connector
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify, g
import secrets
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from datetime import timedelta

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
def get_cursor_and_connection():
    if 'db_connection' not in g:
        g.db_connection = create_db_connection()
    if 'db_cursor' not in g:
        g.db_cursor = g.db_connection.cursor()
    return g.db_cursor, g.db_connection

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
        db_connection.commit()
        print(result)

        # Check if the serial in computer_usage matches the one entered by the user
        if result and result[2] == user_serial:
            # Serials match, open the program
            return jsonify({"error": "Serial is already in use.\nซีเรียลถูกใช้งานแล้ว"})
        else:
            # Serials don't match, proceed to insert the serial
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

        if result and result[2] != 1:
            serial_id = result[0]
            # Serial exists, store data in computer_usage table
            insert_query = "INSERT INTO computer_usage (id, mac_address, serial) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (serial_id, client_mac_address, user_serial))
            db_connection.commit()

            # Update the status column in the serials table
            update_query = "UPDATE serials SET status = %s WHERE serial = %s"
            cursor.execute(update_query, (True, user_serial))
            db_connection.commit()

            # Display success message
            return jsonify({"message": "Serial successfully used. Program is opening.\nซีเรียลสำเร็จแล้วโปรแกรมกำลังเปิด"})
        else:
            if result and result[2] == 1:
                return jsonify({"error": "Serial is already in use.\nซีเรียลถูกใช้งานแล้ว"})
            else:
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

################### serial PAGE ######################

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# เพิ่มข้อมูล
@app.route('/api/adddata', methods=['POST'])
@jwt_required()
def add_data():
    try:
        cursor, connection = get_cursor_and_connection()

        data = request.get_json()
        serial = data['serial']

        cursor.execute("INSERT INTO serials (serial) VALUES (%s)", (serial,))
        connection.commit()
        return jsonify({'message': 'Add Data successfully'}), 200
    except Exception as e:
        # กรณีเกิดข้อผิดพลาดในการดึงข้อมูลหรือประมวลผล
        return jsonify({"error": str(e)}), 422

# แก้ไขข้อมูล
@app.route('/api/updatedata/<int:item_id>', methods=['PUT'])
@jwt_required()
def edit_data(item_id):
    try:
        # Get data from request
        data = request.get_json()
        updated_serial = data.get('serial')
        updated_status = data.get('status')

        # Check if both serial and status are provided
        if updated_serial is None or updated_status is None:
            return jsonify({'error': 'Both serial and status are required'}), 400

        # Get the existing serial data
        cursor, connection = get_cursor_and_connection()
        cursor.execute('SELECT * FROM serials WHERE id = %s', (item_id,))
        existing_data = cursor.fetchone()

        if existing_data:
            # Check if serial or status has been changed
            if existing_data[1] != updated_serial or existing_data[2] != updated_status:
                # Delete data from computer_usage table for the given ID
                cursor.execute('DELETE FROM computer_usage WHERE id = %s', (item_id,))

            # Update data in the serials table
            cursor.execute('UPDATE serials SET serial = %s, status = %s WHERE id = %s',
                           (updated_serial, updated_status, item_id))
            connection.commit()

            return jsonify({'message': 'Data updated successfully'})
        else:
            return jsonify({'error': 'Item not found'}), 404

    except Exception as e:
        # Print the exception to the console for debugging
        print(f"Error: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

# ลบข้อมูล
@app.route('/api/deletedata/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_data(id):
    try:
        cursor, connection = get_cursor_and_connection()

        cursor.execute("DELETE FROM serials WHERE id = %s", (id,))
        connection.commit()

        return jsonify({"message": "Data deleted successfully"})
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

# ดึงข้อมูลทั้งหมด
@app.route('/api/getdata', methods=['GET'])
@jwt_required()
def get_data():

    dataselect = request.args.get('dataselect')

    try:
        if(dataselect == 'dataserials'):
            cursor, connection = get_cursor_and_connection()

            cursor.execute("SELECT * FROM serials")
            result = cursor.fetchall()

            response = jsonify(result)
            return response, 200
        elif(dataselect == 'dataused'):
            cursor, connection = get_cursor_and_connection()

            cursor.execute("SELECT * FROM computer_usage")
            result = cursor.fetchall()

            response = jsonify(result)
            return response, 200
    except Exception as e:
        # กรณีเกิดข้อผิดพลาดในการดึงข้อมูลหรือประมวลผล
        return jsonify({"error": str(e)}), 422

############################# computer_usage PAGE ########################################
@app.route('/api/getused', methods=['GET'])
@jwt_required()
def get_used():
    try:
        cursor, connection = get_cursor_and_connection()

        cursor.execute("SELECT * FROM computer_usage")
        result = cursor.fetchall()
        connection.commit()

        response = jsonify(result)
        return response, 200
    except Exception as e:
        # กรณีเกิดข้อผิดพลาดในการดึงข้อมูลหรือประมวลผล
        return jsonify({"error": str(e)}), 422


    #####################################################################
# login
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
        token = create_access_token(identity={'user_id': user[0], 'username': user[1]})
        return jsonify({'token': token})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    # ส่วนนี้จะถูกเรียกเมื่อ Token ถูกส่งมาพร้อมกับ request และถูกตรวจสอบว่าถูกต้อง
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

if __name__ == '__main__':
    app.run()
