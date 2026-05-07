# ===============================
# School Data Entry Web App
# Tech: Python Flask + SQLite + Excel Export
# ===============================

# STEP 1: Install dependencies
# pip install flask pandas openpyxl

from flask import Flask, render_template_string, request, redirect, session, send_file
import sqlite3
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect('school.db')
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        school TEXT,
        category TEXT,
        remarks TEXT
    )''')

    cur.execute("INSERT OR IGNORE INTO users (id, username, password) VALUES (1,'admin','admin123')")

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN =================
login_page = '''
<!DOCTYPE html>
<html>
<head>
<style>
body {
    font-family: Arial;
    background-color: #f2f2f2;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    margin: 0;
}

.login-box {
    background: white;
    padding: 30px;
    border-radius: 10px;
    box-shadow: 0 0 10px rgba(0,0,0,0.2);
    text-align: center;
}

input {
    padding: 8px;
    width: 200px;
}

button {
    padding: 8px 15px;
}
</style>
</head>
<body>

<div class="login-box">
<h2>Login</h2>
<form method="post">
Username:<br>
<input name="username"><br><br>

Password:<br>
<input type="password" name="password"><br><br>

<button type="submit">Login</button>
</form>

<p style="color:red;">{{error}}</p>
</div>

</body>
</html>
'''

@app.route('/', methods=['GET','POST'])
def login():
    error = ""
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = sqlite3.connect('school.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = u
            return redirect('/dashboard')
        else:
            error = "Invalid login"

    return render_template_string(login_page, error=error)

# ================= DASHBOARD =================
dashboard_page = '''
<h2>Data Entry Form</h2>
<a href="/logout">Logout</a> | <a href="/export">Download Excel</a><br><br>

<form method="post">
Name:<br>
<input name="name"><br><br>

School:<br>
<input name="school"><br><br>

Category:<br>
<select name="category">
<option>RO</option>
<option>Toilet</option>
<option>Smart Class</option>
</select><br><br>

Remarks:<br>
<textarea name="remarks"></textarea><br><br>

<button type="submit">Save</button>
</form>

<hr>
<h3>Saved Records</h3>
<table border="1" cellpadding="5">
<tr><th>Name</th><th>School</th><th>Category</th><th>Remarks</th></tr>
{% for r in records %}
<tr>
<td>{{r[1]}}</td>
<td>{{r[2]}}</td>
<td>{{r[3]}}</td>
<td>{{r[4]}}</td>
</tr>
{% endfor %}
</table>
'''

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('school.db')
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        school = request.form['school']
        category = request.form['category']
        remarks = request.form['remarks']

        cur.execute("INSERT INTO records (name,school,category,remarks) VALUES (?,?,?,?)",
                    (name, school, category, remarks))
        conn.commit()

    cur.execute("SELECT * FROM records")
    records = cur.fetchall()
    conn.close()

    return render_template_string(dashboard_page, records=records)

# ================= EXPORT TO EXCEL =================
@app.route('/export')
def export():
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('school.db')
    df = pd.read_sql_query("SELECT name, school, category, remarks FROM records", conn)
    conn.close()

    file_path = "export.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

