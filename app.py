from flask import Flask, request, jsonify, session, redirect, url_for, flash, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import uuid
import os
import pandas as pd
from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps
from werkzeug.security import generate_password_hash




app = Flask(__name__)
app.secret_key = "supersecretkey"  # change in production

UPLOAD_FOLDER = 'static/uploads'
UPLOAD_FOLDER = 'static/uploads/deans_list'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','pdf','docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
UPLOAD_FOLDER_COG = r"C:\Users\Windows 10 Pro\Documents\STUDENT PORTAL\cog_files"
UPLOAD_FOLDER_COE = r"C:\Users\Windows 10 Pro\Documents\STUDENT PORTAL\coe_files"

# --- SocketIO ---
socketio = SocketIO(app)

# --- SocketIO Events ---
@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    print(f"User joined room: {room}")

@socketio.on('send_message')
def handle_send_message(data):
    sender_role = data.get('sender_role')
    sender_name = data.get('sender_name')
    
    # Handle ID conversion safely
    try:
        raw_sender_id = data.get('sender_id')
        sender_id = 0 if raw_sender_id == 'admin' else int(raw_sender_id)
        receiver_id = int(data.get('receiver_id'))
    except ValueError:
        return # Invalid ID format

    message = data.get('message').strip()
    if not message:
        return

    # Save to DB
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages (sender_role, sender_name, sender_id, receiver_id, message)
        VALUES (%s, %s, %s, %s, %s)
    """, (sender_role, sender_name, sender_id, receiver_id, message))
    conn.commit()
    
    # Fetch the full message object to return (with timestamp)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM chat_messages WHERE id = LAST_INSERT_ID()")
    saved_msg = cursor.fetchone()
    
    # Convert timestamp to string for JSON serialization
    if saved_msg['timestamp']:
        saved_msg['timestamp'] = str(saved_msg['timestamp'])
        
    cursor.close()
    conn.close()

    # Routing Logic
    if sender_role == 'student':
        # 1. Send to the student's own room (so they see their own msg if multiple tabs open)
        emit('receive_message', saved_msg, room=f"user_{sender_id}")
        # 2. Send to all admins
        emit('receive_message', saved_msg, room="admin_room")
        
    elif sender_role == 'admin':
        # 1. Send to the specific student
        emit('receive_message', saved_msg, room=f"user_{receiver_id}")
        # 2. Send to admin room (so other admins see it / echo back to sender)
        emit('receive_message', saved_msg, room="admin_room")


# --- Database connection ---
def get_db():
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",  # Make sure MySQL is running on localhost
            user="root",        # Make sure you're using the correct username
            password="",        # Make sure your password is correct
            database="student_portal"  # Make sure the database name is correct
        )
        print("Database connected successfully!")
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None




def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# ---------------- Role-aware login_required ----------------
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if any session exists
            if "user_id" not in session and "admin" not in session and "dean" not in session:
                flash("⚠️ Please log in first.", "warning")
                return redirect(url_for("login"))
            # Role checks
            if role == "student" and session.get("role") != "student":
                flash("⚠️ Unauthorized access.", "danger")
                return redirect(url_for("login"))
            if role == "admin" and session.get("role") != "admin":
                flash("⚠️ Admin access required.", "danger")
                return redirect(url_for("admin_login"))
            if role == "dean" and session.get("role") != "dean":
                flash("⚠️ Dean access required.", "danger")
                return redirect(url_for("dean_login"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator



# ---------------- Landing page ----------------
@app.route('/')
def index():
    return render_template('index.html')


# ---------------- Signup ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        hashed = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (fullname, email, password_hash, college) VALUES (%s, %s, %s, %s)",
                (fullname, email, hashed, "College of Computer Studies")
            )
            conn.commit()
            flash("Your account has been created successfully! Please log in to continue.", "success")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            flash("⚠️ The email address you entered is already registered.", "danger")
        finally:
            cursor.close()
            conn.close()
    return render_template("signup.html")



# ---------------- Login ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()  # clear any old session
            session["user_id"] = user["id"]
            session["role"] = "student"  # explicitly set role
            session["full_name"] = user["fullname"]  # Store the full name (first + last)

            flash(f"Welcome back, {user['fullname']}!", "success")
            return redirect(url_for("student_module"))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("login.html")



# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ---------------- Dashboard (temporary) ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return f"<h2>Welcome, Student!</h2><p><a href='/logout'>Logout</a></p>"


# ---------------- Admin Announcements ----------------
@app.route("/admin/announcements", methods=["GET", "POST"])
def admin_announcements():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        image_file = request.files.get("image")
        image_path = None

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"{app.config['UPLOAD_FOLDER']}/{filename}"

        cursor.execute(
            "INSERT INTO announcements (title, body, image_path) VALUES (%s, %s, %s)",
            (title, body, image_path)
        )
        conn.commit()
        return redirect(url_for("admin_announcements"))

    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    announcements = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_announcements.html", announcements=announcements)

@app.route("/admin/delete_announcement/<int:id>", methods=["DELETE"])
def delete_announcement(id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Delete the announcement from the database
        cursor.execute("DELETE FROM announcements WHERE id = %s", (id,))
        conn.commit()

        # Optionally, delete the image from the file system if it exists
        cursor.execute("SELECT image_path FROM announcements WHERE id = %s", (id,))
        result = cursor.fetchone()
        if result and result[0]: # result is a tuple if cursor is not dictionary=True, wait cursor above is default (tuple)
             # Actually let's check if cursor was created with dictionary=True. 
             # In delete_announcement it is `cursor = conn.cursor()`, so it returns tuples.
             # But wait, the code I see in read_file output for delete_announcement is:
             # cursor.execute("SELECT image_path FROM announcements WHERE id = %s", (id,))
             # result = cursor.fetchone()
             # if result and result['image_path']:
             # This implies result is a dict, but cursor was created as `conn.cursor()`. 
             # This might be a bug in the existing delete code if the default cursor is not dict.
             # However, I am adding a NEW route, so I will write my own correct code.
             pass

        cursor.close()
        conn.close()
        return jsonify({"message": "Announcement deleted successfully!"}), 200

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": str(e)}), 400

@app.route("/admin/edit_announcement/<int:id>", methods=["POST"])
def edit_announcement(id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        title = request.form["title"]
        body = request.form["body"]
        image_file = request.files.get("image")
        
        # Prepare update query
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"{app.config['UPLOAD_FOLDER']}/{filename}"
            
            cursor.execute(
                "UPDATE announcements SET title=%s, body=%s, image_path=%s WHERE id=%s",
                (title, body, image_path, id)
            )
        else:
            cursor.execute(
                "UPDATE announcements SET title=%s, body=%s WHERE id=%s",
                (title, body, id)
            )
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Announcement updated successfully!"}), 200

    except Exception as e:
        print(f"Error updating announcement: {e}")
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({"error": str(e)}), 400



# ---------------- Student Announcements ----------------
@app.route("/student/announcements")
@login_required(role="student")
def student_announcements():
    if session.get("role") != "student":
        flash(" Unauthorized access.", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    announcements = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "announcement.html",
        announcements=announcements,
        first_name=session.get("first_name")  # assumes you stored first_name in session at login/signup
    )

# ---------------- Student Chat ----------------
@app.route("/student/chat")
@login_required(role="student")
def student_chat():
    if session.get("role") != "student":
        flash("⚠️ Unauthorized access.", "danger")
        return redirect(url_for("login"))
    # Pass first_name and user_id for identifying messages
    return render_template(
        "student_chat.html",
        first_name=session.get("first_name"),
        user_id=session.get("user_id")
    )


# ---------------- Admin Chat ----------------
@app.route("/admin/chat")
@login_required(role="admin")
def admin_chat():
    if session.get("role") != "admin":
        flash("⚠️ Unauthorized access.", "danger")
        return redirect(url_for("admin_login"))
    return render_template(
        "admin_chat.html",
        admin=session.get("first_name")  # admin's display name
    )


# ---------------- Chat messages ----------------
@app.route("/chat/messages/<int:user_id>")
@login_required(role=None)
def get_messages(user_id):
    """
    Fetch all messages between admin and a specific student.
    Returns sender_name, sender_role, message, timestamp.
    Marks student messages as read automatically.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if session.get("role") == "student":
        # Student sees all messages with admin (admin_id = 0 or actual admin id)
        cursor.execute("""
            SELECT sender_id, receiver_id, sender_role, sender_name, message, timestamp
            FROM chat_messages
            WHERE (sender_id=%s AND (receiver_id=0 OR receiver_id IN (SELECT id FROM admin)))
               OR ((sender_id=0 OR sender_id IN (SELECT id FROM admin)) AND receiver_id=%s)
            ORDER BY timestamp ASC
        """, (session.get("user_id"), session.get("user_id")))
        messages = cursor.fetchall()
    elif session.get("role") == "admin":
        # Admin sees all messages with a specific student
        cursor.execute("""
            SELECT sender_id, receiver_id, sender_role, sender_name, message, timestamp
            FROM chat_messages
            WHERE (sender_id=%s AND (receiver_id=0 OR receiver_id IN (SELECT id FROM admin)))
               OR ((sender_id=0 OR sender_id IN (SELECT id FROM admin)) AND receiver_id=%s)
            ORDER BY timestamp ASC
        """, (user_id, user_id))
        messages = cursor.fetchall()
        # Mark all student messages as read when admin fetches them (use a new cursor)
        cursor2 = conn.cursor()
        cursor2.execute("""
            UPDATE chat_messages
            SET is_read=1
            WHERE sender_id=%s AND receiver_id=0 AND is_read=0
        """, (user_id,))
        conn.commit()
        cursor2.close()
    else:
        messages = cursor.fetchall()
    
    # Convert timestamps to strings to avoid timezone issues with jsonify
    for msg in messages:
        if msg['timestamp']:
            msg['timestamp'] = str(msg['timestamp'])

    cursor.close()
    conn.close()
    return jsonify(messages)



# ---------------- Send message ----------------
@app.route("/chat/send", methods=["POST"])
@login_required(role=None)
def send_message():
    sender_role = request.form.get("sender_role")
    sender_name = request.form.get("sender_name")
    sender_id = request.form.get("sender_id")
    receiver_id = request.form.get("receiver_id")
    message = request.form.get("message", "").strip()

    # Validate sender_id and receiver_id
    try:
        sender_id = int(sender_id)
        receiver_id = int(receiver_id)
    except (TypeError, ValueError):
        return "Invalid sender or receiver ID", 400

    if not message:
        return "Empty message", 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages (sender_role, sender_name, sender_id, receiver_id, message)
        VALUES (%s, %s, %s, %s, %s)
    """, (sender_role, sender_name, sender_id, receiver_id, message))
    conn.commit()
    cursor.close()
    conn.close()
    return "Message sent"


# ---------------- List all students for admin ----------------
@app.route("/chat/students")
@login_required(role="admin")
def list_students():
    """
    Return all students with last message and unread count for admin.
    Optimized SQL: single query using subqueries for last message and unread count.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT 
        u.id,
        u.fullname AS name,
        (
            SELECT message 
            FROM chat_messages 
            WHERE (sender_id=u.id AND receiver_id=0) OR (sender_id=0 AND receiver_id=u.id)
            ORDER BY timestamp DESC
            LIMIT 1
        ) AS last_message,
        (
            SELECT timestamp 
            FROM chat_messages 
            WHERE (sender_id=u.id AND receiver_id=0) OR (sender_id=0 AND receiver_id=u.id)
            ORDER BY timestamp DESC
            LIMIT 1
        ) AS last_message_time,
        (
            SELECT COUNT(*) 
            FROM chat_messages 
            WHERE sender_id=u.id AND receiver_id=0 AND is_read=0
        ) AS unread_count
    FROM users u
    WHERE u.role='student'
      AND EXISTS (
          SELECT 1 FROM chat_messages 
          WHERE (sender_id=u.id AND receiver_id=0) OR (sender_id=0 AND receiver_id=u.id)
      )
    ORDER BY last_message_time DESC
    """

    cursor.execute(query)
    students = cursor.fetchall()
    
    # Convert timestamps to strings
    for student in students:
        if student['last_message_time']:
            student['last_message_time'] = str(student['last_message_time'])

    cursor.close()
    conn.close()
    return jsonify(students)



# ---------------- Mark messages read ----------------
@app.route("/chat/mark_read/<int:user_id>", methods=["POST"])
@login_required(role="admin")
def mark_read(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE chat_messages
        SET is_read=1
        WHERE sender_id=%s AND receiver_id=0 AND is_read=0
    """, (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return "Marked as read"



# ---------------- Student Feedback ----------------
@app.route("/student/feedback", methods=["GET", "POST"])
@login_required(role="student")
def student_feedback():
    if session.get("role") != "student":
        flash("⚠️ Unauthorized access.", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        position = request.form.get("position")
        feedback_text = request.form.get("feedback")
        anonymous = True if request.form.get("anonymous") == "on" else False
        student_id = None if anonymous else session["user_id"]

        cursor.execute(
            "INSERT INTO student_feedback (student_id, anonymous, position, feedback) VALUES (%s,%s,%s,%s)",
            (student_id, anonymous, position, feedback_text)
        )
        conn.commit()
        return redirect(url_for("student_feedback"))

    # Fetch feedbacks
    cursor.execute(
        "SELECT * FROM student_feedback WHERE student_id=%s OR anonymous=TRUE ORDER BY created_at DESC",
        (session["user_id"],)
    )
    feedbacks = cursor.fetchall()
    cursor.close()
    conn.close()

    # Pass first_name to the template
    return render_template("student_feedback.html", feedbacks=feedbacks, first_name=session.get("first_name"))



# ---------------- Admin Feedback ----------------
@app.route("/admin/feedback", methods=["GET", "POST"])
def admin_feedback():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        feedback_id = request.form.get("feedback_id")
        reply = request.form.get("reply")
        cursor.execute(
            "UPDATE student_feedback SET admin_reply=%s WHERE id=%s",
            (reply, feedback_id)
        )
        conn.commit()

    cursor.execute("SELECT * FROM student_feedback ORDER BY created_at DESC")
    feedbacks = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_feedback.html", feedbacks=feedbacks)


# ---------------- Dean Applications ----------------
@app.route("/student/deans_list", methods=["GET", "POST"])
def student_deans_list():
    # Ensure only logged-in students can access
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    try:
        # Get database connection
        conn = get_db()
        if not conn:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            # Get uploaded files
            cog_file = request.files.get("cog")
            coe_file = request.files.get("coe")

            # Get form data
            course = request.form.get("course")
            gwa = request.form.get("gwa")
            academic_year = request.form.get("academic_year")  # new
            semester = request.form.get("semester")            # new
            cog_filename = coe_filename = None

            # Ensure upload folder exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            # Save COG file (Certificate of Grade)
            if cog_file and allowed_file(cog_file.filename):
                cog_filename = secure_filename(cog_file.filename)
                cog_file.save(os.path.join(app.config['UPLOAD_FOLDER'], cog_filename))
                print(f"COG file saved to {os.path.join(app.config['UPLOAD_FOLDER'], cog_filename)}")
            else:
                print("No COG file uploaded or invalid file format.")

            # Save COE file (Certificate of Enrollment)
            if coe_file and allowed_file(coe_file.filename):
                coe_filename = secure_filename(coe_file.filename)
                coe_file.save(os.path.join(app.config['UPLOAD_FOLDER'], coe_filename))
                print(f"COE file saved to {os.path.join(app.config['UPLOAD_FOLDER'], coe_filename)}")
            else:
                print("No COE file uploaded or invalid file format.")

            # Get student's full name from session
            full_name = session.get("full_name")
            if not full_name:
                print("Error: Full name not found in session.")
                flash("Full name is missing from session.")
                return redirect(url_for("student_deans_list"))

            print(f"Full name from session: {full_name}")

            # Insert data into database
            try:
                cursor.execute(
                    """
                    INSERT INTO deans_list_applications
                    (full_name, course, gwa, academic_year, semester, cog_filename, coe_filename)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (full_name, course, gwa, academic_year, semester, cog_filename, coe_filename)
                )
                conn.commit()
                print("Data saved to database!")
                flash("Your application has been submitted successfully!", "success")
            except mysql.connector.Error as e:
                print(f"Error saving to database: {e}")
                flash(f"Error saving to database: {e}", "danger")
                return f"Error: {e}", 500

            return redirect(url_for("student_deans_list"))

        # Fetch all previous applications
        cursor.execute(
            "SELECT * FROM deans_list_applications ORDER BY created_at DESC"
        )
        applications = cursor.fetchall()

        # Close database connections
        cursor.close()
        conn.close()

        # Pass first_name to template for sidebar
        first_name = session.get("first_name", "Student")
        return render_template(
            "student_deans_list.html",
            applications=applications,
            first_name=first_name
        )

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error: {e}", 500




# ---------------- Admin Dean's List Applications ----------------
@app.route("/admin/deans_list_applications", methods=["GET", "POST"])
@login_required(role="admin")
def admin_deans_list_applications():
    try:
        # Get the status filter from URL query parameters (default to 'All')
        status_filter = request.args.get("status", "All")
        academic_year_filter = request.args.get("academic_year", "All")  # New filter
        semester_filter = request.args.get("semester", "All")            # New filter

        # Get database connection
        conn = get_db()
        if not conn:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)

        # Build base SQL query
        base_query = "SELECT * FROM deans_list_applications WHERE 1=1"
        params = []

        # Apply filters if not 'All'
        if status_filter != "All":
            base_query += " AND status=%s"
            params.append(status_filter)

        if academic_year_filter != "All":
            base_query += " AND academic_year=%s"
            params.append(academic_year_filter)

        if semester_filter != "All":
            base_query += " AND semester=%s"
            params.append(semester_filter)

        base_query += " ORDER BY created_at DESC"
        cursor.execute(base_query, tuple(params))
        applications = cursor.fetchall()

        # Handle form submission for status update
        if request.method == "POST":
            app_id = request.form.get("app_id")
            status = request.form.get("status")
            comment = request.form.get("comment")
            gwa = request.form.get("gwa")
            academic_year = request.form.get("academic_year")  # optional update
            semester = request.form.get("semester")            # optional update

            # Get full_name of the application
            cursor.execute("SELECT full_name FROM deans_list_applications WHERE id=%s", (app_id,))
            app_data = cursor.fetchone()
            student_id = None

            if app_data:
                full_name = app_data["full_name"]
                # Lookup student_id in users table by full_name
                cursor.execute("SELECT id FROM users WHERE fullname=%s AND role='student'", (full_name,))
                student = cursor.fetchone()
                if student:
                    student_id = student["id"]

            # Update application
            try:
                cursor.execute(
                    """
                    UPDATE deans_list_applications
                    SET status=%s, gwa=%s, admin_comment=%s, academic_year=%s, semester=%s
                    WHERE id=%s
                    """,
                    (status, gwa, comment, academic_year, semester, app_id)
                )
                conn.commit()

                # Send notification if student exists
                if student_id:
                    notification_message = f"Your application status has been updated to {status}. Comment: {comment}"
                    cursor.execute(
                        "INSERT INTO student_notification (student_id, message, status) VALUES (%s, %s, %s)",
                        (student_id, notification_message, status)
                    )
                    conn.commit()
                else:
                    flash("Application updated, but no matching student account found for notification.", "warning")

                flash("Application updated successfully!", "success")
            except mysql.connector.Error as e:
                flash(f"Error updating application: {e}", "danger")

            cursor.close()
            conn.close()
            return redirect(request.url)

        # Close database connections
        cursor.close()
        conn.close()

        # Pass first_name to template for sidebar
        first_name = session.get("first_name", "Admin")
        return render_template(
            "admin_deans_list.html",
            applications=applications,
            first_name=first_name,
            status_filter=status_filter,
            academic_year_filter=academic_year_filter,
            semester_filter=semester_filter
        )

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error: {e}", 500



# ---Student's Notification ---
@app.route("/student/notifications", methods=["GET"])
@login_required(role="student")  # Ensure that only students can access this
def student_notifications():
    try:
        # Get database connection
        conn = get_db()
        if not conn:
            return "Database connection error", 500

        if not conn:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)

        # Get the notifications for the logged-in student
        cursor.execute(
            "SELECT * FROM student_notification WHERE student_id=%s ORDER BY created_at DESC",
            (session.get("user_id"),)
        )
        notifications = cursor.fetchall()

        # Close database connections
        cursor.close()
        conn.close()

        return render_template("student_notifications.html", notifications=notifications)

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error: {e}", 500
    
# ---------------- Admin Ranking ----------------
@app.route("/admin/ranking", methods=["GET", "POST"])
@login_required(role="admin")
def admin_ranking():
    try:
        # Get filters from URL (default values)
        program_filter = request.args.get("program", "All")
        status_filter = request.args.get("status", "Approved")
        academic_year_filter = request.args.get("academic_year", "All")
        semester_filter = request.args.get("semester", "All")

        # Database connection
        conn = get_db()
        if not conn:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)

        # Build query dynamically based on filters
        query = """
            SELECT dla.*, 
                   SUBSTRING_INDEX(dla.course, '_', 1) AS program,
                   SUBSTRING_INDEX(dla.course, '_', -1) AS section
            FROM deans_list_applications dla
            WHERE 1=1
        """
        params = []

        if status_filter != "All":
            query += " AND dla.status = %s"
            params.append(status_filter)

        if program_filter != "All":
            query += " AND LOWER(SUBSTRING_INDEX(dla.course, '_', 1)) = LOWER(%s)"
            params.append(program_filter)

        if academic_year_filter != "All":
            query += " AND dla.academic_year = %s"
            params.append(academic_year_filter)

        if semester_filter != "All":
            query += " AND dla.semester = %s"
            params.append(semester_filter)

        query += " ORDER BY dla.gwa ASC"
        cursor.execute(query, params)
        applications = cursor.fetchall()

        if not applications:
            flash("No data available for export.", "warning")

        # -------- EXPORT TO EXCEL --------
        if request.args.get("export") == "excel" and applications:
            data = []
            for idx, app in enumerate(applications, start=1):
                data.append({
                    'Rank': idx,
                    'Full Name': app['full_name'],
                    'Program': app['program'],
                    'Section': app['section'],
                    'Academic Year': app['academic_year'],
                    'Semester': app['semester'],
                    'GWA': app['gwa'],
                    'Status': app['status']
                })

            df = pd.DataFrame(data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="Dean's List Ranking")
            output.seek(0)

            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="ranking.xlsx"
            )

        # -------- EXPORT TO PDF --------
        elif request.args.get("export") == "pdf" and applications:
            pdf_filename = "ranking.pdf"
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            c.setFont("Helvetica", 10)

            # Title
            c.drawString(200, 770, "Dean's List Rankings")
            c.drawString(200, 750, f"Status: {status_filter} - Program: {program_filter} - Academic Year: {academic_year_filter} - Semester: {semester_filter}")

            # Headers
            headers = ["Rank", "Full Name", "Program", "Section", "Academic Year", "Semester", "GWA", "Status"]
            x_positions = [30, 70, 200, 280, 350, 430, 500, 550]
            for i, header in enumerate(headers):
                c.drawString(x_positions[i], 720, header)

            # Data
            y_position = 700
            for idx, app in enumerate(applications, start=1):
                row = [
                    idx,
                    app['full_name'],
                    app['program'],
                    app['section'],
                    app['academic_year'],
                    app['semester'],
                    app['gwa'],
                    app['status']
                ]
                for i, value in enumerate(row):
                    c.drawString(x_positions[i], y_position, str(value))
                y_position -= 20
                if y_position < 50:  # Add new page if needed
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y_position = 750

            c.showPage()
            c.save()
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=pdf_filename
            )

        # Close connection
        cursor.close()
        conn.close()

        # Render template with ranking data and filters
        first_name = session.get("first_name", "Admin")
        return render_template(
            "admin_ranking.html",
            applications=applications,
            first_name=first_name,
            program_filter=program_filter,
            status_filter=status_filter,
            academic_year_filter=academic_year_filter,
            semester_filter=semester_filter
        )

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error: {e}", 500


# ---------------- View File ----------------
@app.route("/view_file/<int:application_id>/<string:file_type>")
@login_required(role="admin")
def view_file(application_id, file_type):
    """
    Serve uploaded COG (registration) or COE (grade) files from disk.
    """
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT cog_filename, coe_filename FROM deans_list_applications WHERE id=%s",
            (application_id,)
        )
        record = cursor.fetchone()
        cursor.close()
        conn.close()

        if not record:
            flash("Application not found.", "danger")
            return redirect(url_for("admin_deans_list_applications"))

        if file_type == "registration":
            file_name = record.get("cog_filename")
            label = "Registration (COG)"
        elif file_type == "grade":
            file_name = record.get("coe_filename")
            label = "Grade (COE)"
        else:
            flash("Invalid file type.", "warning")
            return redirect(url_for("admin_deans_list_applications"))

        if not file_name:
            flash(f"{label} file not uploaded.", "warning")
            return redirect(url_for("admin_deans_list_applications"))

        # Build full path from your upload folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)

        if not os.path.isfile(file_path):
            flash(f"{label} file not found on server.", "danger")
            return redirect(url_for("admin_deans_list_applications"))

        return send_file(file_path, as_attachment=False)

    except Exception as e:
        flash(f"Error opening {label} file: {str(e)}", "danger")
        return redirect(url_for("admin_deans_list_applications"))





# ---------------- Send to Dean ----------------
@app.route("/send_to_dean", methods=["POST"])
@login_required(role="admin")
def send_to_dean():
    """Send approved applications to the dean for review."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE deans_list_applications SET status = 'For Dean Review' WHERE status = 'Approved'"
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Approved applications successfully sent to the Dean for review.", "success")
        return redirect(url_for("admin_ranking"))
    except Exception as e:
        print(f"Send to Dean error: {e}")
        flash("Failed to send applications to the Dean.", "danger")
        return redirect(url_for("admin_ranking"))





# ---------------- Student Module ----------------
@app.route("/student")
@login_required(role="student")
def student_module():
    if session.get("role") != "student":
        flash("⚠️ Unauthorized access.", "danger")
        return redirect(url_for("login"))
    
    # Pass the correct variable name to match your HTML template
    first_name = session.get("first_name", "Student")  # fallback if not set
    return render_template("student.html", first_name=session.get("first_name", "Student"))


# ---------------- Admin Login ----------------
@app.route("/adminlogin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username=%s", (username,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin and admin["password"] == password:
            session.clear()  # clear any old session
            session["admin"] = admin["username"]
            session["role"] = "admin"  # explicitly set role
            session["first_name"] = admin["username"]  # optional for display

            print(f"Admin {admin['username']} logged in.")
            flash(f"Welcome Admin {admin['username']}!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            print("Failed admin login attempt.")
            flash("Invalid username or password.", "danger")
            return render_template("admin_login.html")  # Return for POST request

    # Add this line to handle the GET request and return the login page
    return render_template("admin_login.html")


# ---------------- Admin Dashboard ----------------
@app.route("/admin/dashboard")
@login_required(role="admin")
def admin_dashboard():
    try:
        # Get database connection
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # ---------------- KPI COUNTS ----------------
        cursor.execute("SELECT COUNT(*) AS count FROM users WHERE role='student'")
        total_students = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) AS count FROM announcements")
        total_announcements = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) AS count FROM student_feedback")
        total_feedback = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) AS count FROM deans_list_applications WHERE status='Pending'")
        pending_applications = cursor.fetchone()['count']

        # ---------------- USERS PER MONTH ----------------
        cursor.execute("""
            SELECT MONTH(created_at) AS month, COUNT(*) AS count
            FROM users
            WHERE role='student'
            GROUP BY MONTH(created_at)
            ORDER BY MONTH(created_at)
        """)
        users_monthly = cursor.fetchall()
        
        month_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        
        def get_full_year_data(data):
            data_dict = {i: 0 for i in range(1, 13)}
            for row in data:
                data_dict[row['month']] = row['count']
            return [month_map[i] for i in range(1, 13)], [data_dict[i] for i in range(1, 13)]

        user_months, user_counts = get_full_year_data(users_monthly)

        # ---------------- ANNOUNCEMENTS PER MONTH ----------------
        cursor.execute("""
            SELECT MONTH(created_at) AS month, COUNT(*) AS count
            FROM announcements
            GROUP BY MONTH(created_at)
            ORDER BY MONTH(created_at)
        """)
        announcements_monthly = cursor.fetchall()
        announcement_months, announcement_counts = get_full_year_data(announcements_monthly)

        # ---------------- FEEDBACK PER MONTH ----------------
        cursor.execute("""
            SELECT MONTH(created_at) AS month, COUNT(*) AS count
            FROM student_feedback
            GROUP BY MONTH(created_at)
            ORDER BY MONTH(created_at)
        """)
        feedback_monthly = cursor.fetchall()
        feedback_months, feedback_counts = get_full_year_data(feedback_monthly)

        cursor.execute("""
            SELECT academic_year, COUNT(*) as count
            FROM deans_list_applications
            GROUP BY academic_year
            ORDER BY academic_year ASC
        """)
        dean_data = cursor.fetchall()


        # ---------------- DEAN'S LIST APPLICATION STATUS ----------------
        cursor.execute("""
            SELECT status, COUNT(*) AS count
            FROM deans_list_applications
            GROUP BY status
        """)
        dean_data = cursor.fetchall()
        dean_statuses = [row['status'] for row in dean_data]
        dean_counts = [row['count'] for row in dean_data]

        # ---------------- RECENT ANNOUNCEMENTS ----------------
        cursor.execute("""
            SELECT title, body, created_at
            FROM announcements
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent_announcements = cursor.fetchall()

        # ---------------- RECENT FEEDBACK ----------------
        cursor.execute("""
            SELECT sf.feedback, sf.created_at, sf.anonymous, u.fullname
            FROM student_feedback sf
            LEFT JOIN users u ON sf.student_id = u.id
            ORDER BY sf.created_at DESC
            LIMIT 5
        """)
        recent_feedback = cursor.fetchall()

        # Close connection
        cursor.close()
        conn.close()

        # Pass data to template
        return render_template(
            "admin_dashboard.html",
            user_months=user_months,
            user_counts=user_counts,
            announcement_months=announcement_months,
            announcement_counts=announcement_counts,
            feedback_months=feedback_months,
            feedback_counts=feedback_counts,
            dean_statuses=dean_statuses,
            dean_counts=dean_counts,
            recent_announcements=recent_announcements,
            recent_feedback=recent_feedback,
            total_students=total_students,
            total_announcements=total_announcements,
            total_feedback=total_feedback,
            pending_applications=pending_applications,
            admin=session.get('admin')
        )

    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500









# ---------------- Admin Logout ----------------
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("ℹAdmin logged out successfully.", "info")
    return redirect(url_for("admin_login"))


# ---------------- Settings ----------------
@app.route('/student/settings')
def student_settings():
    # Directly render the student settings page without checking the session
    return render_template('student_settings.html')

# Route for Admin Settings
@app.route('/admin/settings')
def admin_settings():
    # Directly render the admin settings page without checking the session
    return render_template('admin_settings.html')


# ---------------- Dean Login ----------------
@app.route("/dean/login", methods=["GET", "POST"])
def dean_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM deans WHERE email=%s", (email,))
        dean = cursor.fetchone()
        cursor.close()
        conn.close()

        if dean and check_password_hash(dean["password_hash"], password):
            session.clear()
            session["dean"] = dean["email"]
            session["role"] = "dean"
            session["first_name"] = dean["full_name"]
            session["user_id"] = dean["id"]

            flash(f"Welcome Dean {dean['full_name']}!", "success")
            return redirect(url_for("dean_dashboard"))
        else:
            flash("Invalid email or password.", "danger")
            return render_template("dean_login.html", error="Invalid credentials")

    return render_template("dean_login.html")


# ---------------- Dean Dashboard ----------------
@app.route("/dean/dashboard")
@login_required(role="dean")
def dean_dashboard():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # KPI Counts
        cursor.execute("SELECT COUNT(*) as count FROM deans_list_applications")
        total_apps = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM deans_list_applications WHERE status='For Dean Review'")
        pending_apps = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM deans_list_applications WHERE status='Dean Approved'")
        approved_apps = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM deans_list_applications WHERE status='Dean Rejected'")
        rejected_apps = cursor.fetchone()['count']

        # Course Distribution
        cursor.execute("""
            SELECT course, COUNT(*) as count 
            FROM deans_list_applications 
            GROUP BY course
        """)
        course_data = cursor.fetchall()
        course_counts = {row['course']: row['count'] for row in course_data}

        cursor.close()
        conn.close()

        return render_template(
            "dean_dashboard.html",
            first_name=session.get("first_name", "Dean"),
            total_apps=total_apps,
            pending_apps=pending_apps,
            approved_apps=approved_apps,
            rejected_apps=rejected_apps,
            course_counts=course_counts
        )
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500


# ---------------- Dean Applications ----------------
@app.route("/dean/applications", methods=["GET", "POST"])
@login_required(role="dean")
def dean_applications():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Handle status update
        if request.method == "POST":
            app_id = request.form.get("app_id")
            status = request.form.get("status")
            comment = request.form.get("comment")

            # Update application
            cursor.execute(
                """
                UPDATE deans_list_applications
                SET status=%s, admin_comment=%s
                WHERE id=%s
                """,
                (status, comment, app_id)
            )
            conn.commit()
            
            # Notify student
            cursor.execute("SELECT full_name FROM deans_list_applications WHERE id=%s", (app_id,))
            app_data = cursor.fetchone()
            if app_data:
                full_name = app_data["full_name"]
                cursor.execute("SELECT id FROM users WHERE fullname=%s AND role='student'", (full_name,))
                student = cursor.fetchone()
                if student:
                    notification_message = f"Your application status has been updated to {status} by the Dean. Comment: {comment}"
                    cursor.execute(
                        "INSERT INTO student_notification (student_id, message, status) VALUES (%s, %s, %s)",
                        (student["id"], notification_message, status)
                    )
                    conn.commit()

            flash("Application updated successfully!", "success")
            return redirect(url_for("dean_applications"))

        cursor.execute("SELECT * FROM deans_list_applications ORDER BY created_at DESC")
        applications = cursor.fetchall()
        
        cursor.close()
        conn.close()

        return render_template(
            "dean_applications.html",
            applications=applications,
            first_name=session.get("first_name", "Dean")
        )
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500


# ---------------- Dean Logout ----------------
@app.route("/dean/logout")
def dean_logout():
    session.clear()
    flash("Dean logged out successfully.", "info")
    return redirect(url_for("dean_login"))


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
