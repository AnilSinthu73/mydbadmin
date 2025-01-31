from flask import Flask, render_template, request, redirect, url_for, session
from mysql.connector import Error

import mysql.connector

app = Flask(__name__)
app.secret_key = 'jntugv'  # Change this to a secure secret key

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username.lower() == 'root' or  'admin' in [username.lower(), password.lower()] or 'jntugv' in [username.lower(), password.lower()] or 'Jntugv' in password:
            # Disallow root login for security reasons. Replace 'root' with your desired default username.
            
            error = "Root login is not allowed for security reasons"
            return render_template('login.html', error=error)
        try:
            conn = mysql.connector.connect(
                host='localhost',
                user=username,
                password=password,
                database='jntugv', 
                port=3306
            )
            conn.close()
            session['username'] = username
            session['password'] = password
            return redirect(url_for('dashboard'))
        except Error as e:
            # Log detailed error for debugging
            app.logger.error(f"Database connection failed for user '{username}': {str(e)}")
            
            if "Access denied" in str(e):
                error = "Access denied: Invalid username or password"
            elif "Unknown database" in str(e):
                error = "Database 'jntugv' does not exist or you don't have access to it"
            elif "Can't connect" in str(e):
                error = "Unable to connect to database server. Please check if MySQL is running"
            else:
                error = f"Database error: {str(e)}"
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'username' in session and 'password' in session:
        try:
            username = session['username']
            password = session['password']
            conn = mysql.connector.connect(
                host='localhost',
                user=username,
                password=password,
                database='jntugv',
                port=3306
            )
            
            cursor = conn.cursor()
            
            # Get current database name
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]
            
            if not current_db:
                # If no database is selected, use information_schema
                current_db = 'information_schema'
            
            # Get database information
            cursor.execute("USE information_schema")
            cursor.execute("SELECT * FROM SCHEMATA WHERE SCHEMA_NAME = %s", (current_db,))
            db_info = cursor.fetchone()
            
            # Get table count
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (current_db,))
            table_count = cursor.fetchone()[0]
            
            # Get database size
            cursor.execute("""
                SELECT COALESCE(ROUND(SUM(data_length + index_length) / 1024 / 1024, 1), 0) AS size
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, (current_db,))
            db_size = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return render_template('dashboard.html', 
                                   database_name=current_db,
                                   table_count=table_count,
                                   db_size=db_size)
        except Error as e:
            app.logger.error(f"Database error: {str(e)}")
            return "An error occurred while accessing the database. Please try again later."
    return redirect(url_for('login'))

@app.route('/tables')
@app.route('/tables/<table_name>')
def tables(table_name=None):
    if 'username' in session and 'password' in session:
        try:
            username = session['username']
            password = session['password']
            conn = mysql.connector.connect(
                host='localhost',
                user=username,
                password=password,
                database='jntugv',
                port=3306
            )
            cursor = conn.cursor(dictionary=True)
            
            # Get list of tables
            cursor.execute("SHOW TABLES")
            tables = [list(table.values())[0] for table in cursor.fetchall()]
            
            table_data = None
            table_structure = None
            
            if table_name:
                # Get table structure
                cursor.execute(f"DESCRIBE {table_name}")
                table_structure = cursor.fetchall()
                
                # Get table data
                cursor.execute(f"SELECT * FROM {table_name}")
                table_data = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return render_template('tables.html', 
                                tables=tables,
                                selected_table=table_name,
                                table_structure=table_structure,
                                table_data=table_data)
        except Error as e:
            return f"Database error: {str(e)}"
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/query', methods=['GET', 'POST'])
def query():
    if 'username' in session and 'password' in session:
        if request.method == 'POST':
            query = request.form['query'].strip()
            # Check if the query is a SELECT statement
            if not query.lower().startswith('select'):
                return "You do not have privileges to execute this type of query."

            try:
                username = session['username']
                password = session['password']
                conn = mysql.connector.connect(
                    host='localhost',
                    user=username,
                    password=password,
                    database='jntugv',
                    port=3306
                )
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute(query)
                result = cursor.fetchall()
                result_columns = [desc[0] for desc in cursor.description]
                result_rows=[tuple(row.values()) for row in result]

                result = {
                    'columns': result_columns,
                    'data': result_rows,
                }
                
                cursor.close()
                conn.close()
                
                return render_template('query.html', query=query, result=result)
            except Error as e:
                return f"Database error: {str(e)}"
        return render_template('query.html', query='', result=None)
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# Run the Flask app in debug mode (with reloading on code changes)
app.config['DEBUG'] = True

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Uncomment this line to allow remote access to the application. However, this exposes the application to potential security risks.
    app.run(debug=True)
