import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
import boto3
from boto3.dynamodb.conditions import Key, Attr
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "medtrack-dev-secret-key-123")

# AWS Clients (boto3 picks up IAM Role credentials automatically on EC2)
REGION = os.environ.get("AWS_REGION", "ap-south-1")
dynamodb = boto3.resource("dynamodb", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "arn:aws:sns:ap-south-1:815553975926:MedTrack-Alerts")

users_table = dynamodb.Table("MedTrack_Users")
appointments_table = dynamodb.Table("MedTrack_Appointments")
records_table = dynamodb.Table("MedTrack_Records")

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"] # "Patient" or "Doctor"
        name = request.form["name"]

        # Check existing user
        res = users_table.get_item(Key={"UserID": email})
        if "Item" in res:
            flash("User already exists. Please login.", "warning")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)
        users_table.put_item(
            Item={
                "UserID": email,
                "Password": hashed_pw,
                "Role": role,
                "Name": name
            }
        )
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    res = users_table.get_item(Key={"UserID": email})
    user = res.get("Item")

    if user and check_password_hash(user["Password"], password):
        session["user_id"] = user["UserID"]
        session["role"] = user["Role"]
        session["name"] = user["Name"]

        if user["Role"] == "Doctor":
            return redirect(url_for("doctor_dashboard"))
        return redirect(url_for("patient_dashboard"))
    
    flash("Invalid credentials.", "danger")
    return redirect(url_for("index"))

@app.route("/patient/dashboard")
def patient_dashboard():
    if "user_id" not in session or session.get("role") != "Patient":
        return redirect(url_for("index"))
    
    # Query patient appointments
    res = appointments_table.scan(
        FilterExpression=Attr("PatientID").eq(session["user_id"])
    )
    my_appointments = res.get("Items", [])
    return render_template("patient_dashboard.html", appointments=my_appointments, name=session.get("name"))

@app.route("/book", methods=["GET", "POST"])
def book_appointment():
    if "user_id" not in session or session.get("role") != "Patient":
        return redirect(url_for("index"))

    if request.method == "POST":
        doctor_id = request.form["doctor_id"]
        appt_date = request.form["date"]
        appt_time = request.form["time"]
        appt_id = str(uuid.uuid4())[:8]

        appointments_table.put_item(
            Item={
                "AppointmentID": appt_id,
                "PatientID": session["user_id"],
                "DoctorID": doctor_id,
                "Date": appt_date,
                "Time": appt_time,
                "Status": "Confirmed"
            }
        )

        # Trigger SNS Notification
        try:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="MedTrack: Appointment Confirmed",
                Message=f"Appointment {appt_id} booked for {session['user_id']} with Dr. {doctor_id} on {appt_date} at {appt_time}."
            )
        except Exception as e:
            print(f"SNS Publish Error: {e}")

        flash("Appointment booked successfully!", "success")
        return redirect(url_for("patient_dashboard"))

    # Fetch list of doctors for dropdown
    res = users_table.scan(FilterExpression=Attr("Role").eq("Doctor"))
    doctors = res.get("Items", [])
    return render_template("book_appointment.html", doctors=doctors)

@app.route("/doctor/dashboard")
def doctor_dashboard():
    if "user_id" not in session or session.get("role") != "Doctor":
        return redirect(url_for("index"))

    # Query doctor appointments
    res = appointments_table.scan(
        FilterExpression=Attr("DoctorID").eq(session["user_id"])
    )
    doctor_appts = res.get("Items", [])
    return render_template("doctor_dashboard.html", appointments=doctor_appts, name=session.get("name"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
