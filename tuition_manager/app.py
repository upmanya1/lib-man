from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from fpdf import FPDF
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret_key"

# SQLite Database Connection
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database if not present
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        course TEXT,
                        admission_date TEXT,
                        fee_paid REAL
                    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS fee_payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER,
                        amount REAL,
                        payment_date TEXT,
                        FOREIGN KEY (student_id) REFERENCES students(id)
                    )''')
    conn.commit()
    conn.close()

# Initialize database on app start
init_db()

# Home route (dashboard)
@app.route('/')
def index():
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    total_income = conn.execute('SELECT SUM(amount) FROM fee_payments').fetchone()[0] or 0
    return render_template('index.html', students=students, total_income=total_income)

# Add new student
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        course = request.form['course']
        admission_date = request.form['admission_date']
        conn = get_db_connection()
        conn.execute('INSERT INTO students (name, course, admission_date, fee_paid) VALUES (?, ?, ?, ?)',
                     (name, course, admission_date, 0))
        conn.commit()
        conn.close()
        flash('Student added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_student.html')

# Submit fee for a student
@app.route('/submit_fee/<int:student_id>', methods=['GET', 'POST'])
def submit_fee(student_id):
    if request.method == 'POST':
        amount = float(request.form['amount'])
        payment_date = request.form['payment_date']
        conn = get_db_connection()
        conn.execute('INSERT INTO fee_payments (student_id, amount, payment_date) VALUES (?, ?, ?)',
                     (student_id, amount, payment_date))
        conn.execute('UPDATE students SET fee_paid = fee_paid + ? WHERE id = ?', (amount, student_id))
        conn.commit()
        conn.close()
        flash('Fee submitted successfully!', 'success')
        return redirect(url_for('index'))
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    conn.close()
    return render_template('fee_submission.html', student=student)

# Generate fee receipt
@app.route('/generate_receipt/<int:payment_id>')
def generate_receipt(payment_id):
    conn = get_db_connection()
    payment = conn.execute('SELECT * FROM fee_payments WHERE id = ?', (payment_id,)).fetchone()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (payment['student_id'],)).fetchone()
    conn.close()

    # PDF Receipt
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Fee Payment Receipt", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Student Name: {student['name']}", ln=True)
    pdf.cell(200, 10, txt=f"Course: {student['course']}", ln=True)
    pdf.cell(200, 10, txt=f"Amount Paid: {payment['amount']}", ln=True)
    pdf.cell(200, 10, txt=f"Payment Date: {payment['payment_date']}", ln=True)
    pdf.output(f"receipt_{payment_id}.pdf")
    return redirect(url_for('index'))

# Export data to CSV
@app.route('/export_data')
def export_data():
    conn = get_db_connection()
    students = pd.read_sql_query('SELECT * FROM students', conn)
    payments = pd.read_sql_query('SELECT * FROM fee_payments', conn)
    conn.close()
    with pd.ExcelWriter('student_data.xlsx') as writer:
        students.to_excel(writer, sheet_name='Students')
        payments.to_excel(writer, sheet_name='Payments')
    flash('Data exported successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
