from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import pandas as pd
app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        college = request.form["college"]
        role = request.form["role"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        # Simple password validation
        if not any(char.isalpha() for char in password):
            return "Password must contain at least one letter"

        # Save data in session (temporary storage)
        session["college"] = college
        session["role"] = role
        session["username"] = username
        session["email"] = email

        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return render_template("dashboard.html",
                               college=session["college"],
                               role=session["role"],
                               username=session["username"])
    return redirect(url_for("register"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("register"))
@app.route("/admin_dashboard")
def admin_dashboard():

    if "username" not in session:
        return redirect(url_for("register"))

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # Total Students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    # Low Risk
    cursor.execute("SELECT COUNT(*) FROM students WHERE risk_level = 'Low'")
    low_risk = cursor.fetchone()[0]

    # High Risk
    cursor.execute("SELECT COUNT(*) FROM students WHERE risk_level = 'High'")
    high_risk = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        username=session["username"],
        role=session["role"],
        college=session["college"],
        total_students=total_students,
        low_risk=low_risk,
        high_risk=high_risk
    )
@app.route("/view_analytics")
def view_analytics():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # Total students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    # Average risk
    cursor.execute("SELECT AVG(risk_score) FROM students")
    avg = cursor.fetchone()[0]
    avg_risk = round(avg, 1) if avg else 0

    # High risk students
    cursor.execute("SELECT COUNT(*) FROM students WHERE risk_level='High'")
    high_risk = cursor.fetchone()[0]

    # Risk distribution
    cursor.execute("SELECT COUNT(*) FROM students WHERE risk_level='Low'")
    low_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE risk_level='Moderate'")
    medium_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE risk_level='High'")
    high_count = cursor.fetchone()[0]

    # Attendance distribution
    cursor.execute("SELECT COUNT(*) FROM students WHERE attendance > 75")
    att_75 = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE attendance BETWEEN 60 AND 75")
    att_60_75 = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE attendance BETWEEN 30 AND 60")
    att_30_60 = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM students WHERE attendance < 30")
    att_below_30 = cursor.fetchone()[0]

    # Department-wise average risk
    cursor.execute("""
        SELECT department, AVG(risk_score)
        FROM students
        GROUP BY department
    """)
    dept_data = cursor.fetchall()
    dept_labels = [row[0] for row in dept_data]
    dept_risk = [round(row[1],1) for row in dept_data]

    # Department-wise Fee Payment (Stacked Chart)
    cursor.execute("""
        SELECT department,
               SUM(CASE WHEN fee_payment='Paid' THEN 1 ELSE 0 END),
               SUM(CASE WHEN fee_payment='Pending' THEN 1 ELSE 0 END)
        FROM students
        GROUP BY department
    """)
    fee_data = cursor.fetchall()
    fee_departments = [row[0] for row in fee_data]
    fee_paid = [row[1] for row in fee_data]
    fee_pending = [row[2] for row in fee_data]

    conn.close()

    return render_template(
        "view_analytics.html",
        total_students=total_students,
        avg_risk=avg_risk,
        high_risk=high_risk,
        low_count=low_count,
        medium_count=medium_count,
        high_count=high_count,
        att_75=att_75,
        att_60_75=att_60_75,
        att_30_60=att_30_60,
        att_below_30=att_below_30,
        dept_labels=dept_labels,
        dept_risk=dept_risk,
        fee_departments=fee_departments,
        fee_paid=fee_paid,
        fee_pending=fee_pending
    )
@app.route("/performance_calculator", methods=["GET", "POST"])
def performance_calculator():

    name = None
    department = None
    semester = None
    attendance = None
    cgpa = None
    backlogs = None
    risk_score = None
    risk_level = None

    subjects = []
    obtained_marks = []
    overall_percentage = None

    if request.method == "POST":

        name = request.form["name"]
        department = request.form["department"]
        semester = request.form["semester"]

        attendance = float(request.form["attendance"])
        backlogs = int(request.form["backlogs"])
        cgpa = float(request.form["cgpa"])

        # Attendance risk
        if attendance <= 30:
            attendance_risk = 100
        elif attendance <= 60:
            attendance_risk = 80
        elif attendance <= 75:
            attendance_risk = 50
        else:
            attendance_risk = 10

        # CGPA risk
        if cgpa <= 5:
            cgpa_risk = 90
        elif cgpa <= 7:
            cgpa_risk = 50
        else:
            cgpa_risk = 10

        # Backlog risk
        if backlogs == 0:
            backlog_risk = 10
        elif backlogs <= 2:
            backlog_risk = 50
        else:
            backlog_risk = 90

        # Final weighted score
        risk_score = (
            attendance_risk * 0.40 +
            cgpa_risk * 0.35 +
            backlog_risk * 0.25
        )

        risk_score = round(risk_score, 2)

        # Final risk level
        if risk_score < 40:
            risk_level = "Low"
        elif risk_score < 70:
            risk_level = "Moderate"
        else:
            risk_level = "High"

        # SUBJECT CALCULATION
        total_obtained = 0
        total_max = 0

        for i in range(1, 11):
            subject_name = request.form.get(f"subject{i}")
            obtained = request.form.get(f"obtained{i}")
            total = request.form.get(f"total{i}")

            if subject_name and obtained and total:
                obtained = float(obtained)
                total = float(total)

                subjects.append(subject_name)
                obtained_marks.append(obtained)

                total_obtained += obtained
                total_max += total

        if total_max > 0:
            overall_percentage = round((total_obtained / total_max) * 100, 2)

    return render_template(
        "performance_calculator.html",
        name=name,
        department=department,
        semester=semester,
        attendance=attendance,
        cgpa=cgpa,
        backlogs=backlogs,
        risk_score=risk_score,
        risk_level=risk_level,
        subjects=subjects,
        obtained_marks=obtained_marks,
        overall_percentage=overall_percentage
    )


def init_db():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        department TEXT,
        semester INTEGER,
        attendance REAL,
        fee_payment TEXT,
        class_performance TEXT,
        study_hours REAL,
        stress_level TEXT,
        risk_score REAL,
        risk_level TEXT
    )
    """)

    conn.commit()
    conn.close()

@app.route("/view_students")
def view_students():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    conn.close()

    return render_template("view_students.html", students=students)
@app.route("/add_student", methods=["POST"])
def add_student():
    name = request.form["name"]
    department = request.form["department"]
    semester = request.form["semester"]
    attendance = request.form["attendance"]
    fee_payment = request.form["fee_payment"]
    class_performance = request.form["class_performance"]
    study_hours = request.form["study_hours"]
    stress_level = request.form["stress_level"]

    # Simple risk logic
    if float(attendance) < 50 or float(class_performance) < 50:
        risk_level = "High"
        risk_score = 80
    elif float(attendance) < 75:
        risk_level = "Moderate"
        risk_score = 50
    else:
        risk_level = "Low"
        risk_score = 20

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO students 
        (name, department, semester, attendance, fee_payment, class_performance, study_hours, stress_level, risk_score, risk_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, department, semester, attendance, fee_payment, class_performance, study_hours, stress_level, risk_score, risk_level))

    conn.commit()
    conn.close()

    return redirect("/view_students")
@app.route("/delete_student/<int:id>")
def delete_student(id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/view_students")
@app.route("/clear_all")
def clear_all():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    conn.commit()
    conn.close()

    return redirect("/view_students")
    import pandas as pd
from flask import flash

@app.route("/import_csv", methods=["POST"])
def import_csv():
    if 'file' not in request.files:
        flash("No file selected", "error")
        return redirect("/view_students")

    file = request.files['file']

    if file.filename == '':
        flash("No file selected")
        return redirect("/view_students")

    try:
        df = pd.read_csv(file)

        # Required Columns
        required_columns = [
            "Name",
            "Department",
            "Semester",
            "Attendance",
            "Fee Payment",
            "Class Performance",
            "Study Hours",
            "Stress Level"
        ]

        # Validate Columns
        if list(df.columns) != required_columns:
            flash("Invalid CSV format! Columns must match exactly.", "error")
            return redirect("/view_students")

        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        for _, row in df.iterrows():

            attendance = float(row["Attendance"])
            performance = float(row["Class Performance"])

            # Risk Logic
            if attendance < 50 or performance < 50:
                risk_level = "High"
                risk_score = 80
            elif attendance < 75:
                risk_level = "Moderate"
                risk_score = 50
            else:
                risk_level = "Low"
                risk_score = 20

            cursor.execute("""
                INSERT INTO students 
                (name, department, semester, attendance, fee_payment,
                 class_performance, study_hours, stress_level,
                 risk_score, risk_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["Name"],
                row["Department"],
                row["Semester"],
                attendance,
                row["Fee Payment"],
                performance,
                row["Study Hours"],
                row["Stress Level"],
                risk_score,
                risk_level
            ))

        conn.commit()
        conn.close()

        flash("CSV Imported Successfully!", "success")
        return redirect("/view_students")

    except Exception as e:
        flash("Error processing CSV file.", "error")
        return redirect("/view_students")

init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)