import mysql.connector
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify, g

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
            insert_query = "INSERT INTO computer_usage (mac_address, serial, is_serial_used) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (client_mac_address, user_serial, True))
            db_connection.commit()

            # Update the status column in the serials table
            update_query = "UPDATE serials SET status = 1 WHERE serial = %s"
            cursor.execute(update_query, (user_serial,))
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

if __name__ == '__main__':
    app.run(debug=True)
