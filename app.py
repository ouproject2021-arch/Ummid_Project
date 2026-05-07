# ===============================
# School Data Entry Web App
# Tech: Python Flask + Excel + Image Upload
# ===============================

from flask import Flask, render_template_string, request, redirect, session, send_file
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "secret123"

excel_file = "school_data.xlsx"

# ===== IMAGE UPLOAD CONFIG =====
UPLOAD_BASE = r"C:\Som_Download"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ================= LOGIN =================
login_page = '''
<!DOCTYPE html>
<html>
<head>
<style>
body { font-family: Arial; background: linear-gradient(135deg,#e8f5e9,#fff); display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
.login-box { background:#fff; padding:30px; border-radius:12px; box-shadow:0 6px 18px rgba(0,0,0,0.15); text-align:center; width:320px; }
.logo { width:80px; }
.brand { font-weight:bold; color:#2e7d32; margin:10px 0; }
input { padding:10px; width:100%; }
button { padding:10px; background:#2e7d32; color:white; border:none; }
</style>
</head>
<body>
<div class="login-box">
    <img src="/static/logo.png" class="logo">
    <div class="brand">Ummid Foundation (Hope for Human)</div>
    <h3>Login</h3>
    <form method="post">
        <input name="username" placeholder="Username"><br><br>
        <input type="password" name="password" placeholder="Password"><br><br>
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
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['user'] = 'admin'
            return redirect('/dashboard')
        else:
            error = "Invalid login"
    return render_template_string(login_page, error=error)


# ================= DASHBOARD =================
dashboard_page = '''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { font-family: Arial; background: #f5f5f5; }
.container { display:flex; justify-content:center; padding:20px; }
.form-card { background:white; padding:20px; width:600px; border-radius:10px; }
input, textarea, select { width:100%; padding:8px; margin-bottom:10px; }
button { width:100%; padding:10px; background:#2e7d32; color:white; border:none; }
.success { color:green; text-align:center; }
</style>

<script>
function calculateTotal() {
    var boys = parseInt(document.getElementById('boys').value) || 0;
    var girls = parseInt(document.getElementById('girls').value) || 0;
    document.getElementById('total').value = boys + girls;
}
</script>
</head>

<body>
<div class="container">
<div class="form-card">

<h2>School Data Entry</h2>

<form method="post" enctype="multipart/form-data">

<label>School Name</label>
<input name="school">

<label>UDISC</label>
<input name="udisc">

<label>Location</label>
<input name="location">

<label>Year</label>
<input name="year">

<label>Girls</label>
<input id="girls" name="girls" onkeyup="calculateTotal()">

<label>Boys</label>
<input id="boys" name="boys" onkeyup="calculateTotal()">

<label>Total</label>
<input id="total" readonly>

<label>Company</label>
<input name="company">

<label>FY</label>
<input name="fy">

<label>Phase</label>
<select name="phase">
<option>1st</option>
<option>2nd</option>
</select>

<label>Remarks</label>
<textarea name="remarks"></textarea>

<hr>

<label>Smart Class Photos</label>
<input type="file" name="smart_class" multiple>

<label>RO Photos</label>
<input type="file" name="ro" multiple>

<label>Sanitary Photos</label>
<input type="file" name="sanitary" multiple>

<label>Toilet Photos</label>
<input type="file" name="toilet" multiple>

<button type="submit">Submit</button>

</form>

{% if success %}
<p class="success">Data + Images Saved ✅</p>
{% endif %}

</div>
</div>
</body>
</html>
'''

# ================= SAVE =================
def save_to_excel(data):
    df_new = pd.DataFrame([data])
    if os.path.exists(excel_file):
        df_old = pd.read_excel(excel_file)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_excel(excel_file, index=False)


# ================= DASHBOARD LOGIC =================
@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/')

    success = False

    if request.method == 'POST':
        boys = int(request.form.get('boys') or 0)
        girls = int(request.form.get('girls') or 0)

        school_name = request.form['school'].strip().replace(" ", "_")

        # Create folder
        school_folder = os.path.join(UPLOAD_BASE, school_name)
        os.makedirs(school_folder, exist_ok=True)

        def save_files(files, category):
            category_folder = os.path.join(school_folder, category)
            os.makedirs(category_folder, exist_ok=True)

            for file in files:
                if file and allowed_file(file.filename):
                    file.save(os.path.join(category_folder, file.filename))

        save_files(request.files.getlist('smart_class'), "Smart_Class")
        save_files(request.files.getlist('ro'), "RO")
        save_files(request.files.getlist('sanitary'), "Sanitary")
        save_files(request.files.getlist('toilet'), "Toilet")

        data = {
            "School Name": request.form['school'],
            "UDISC": request.form['udisc'],
            "Location": request.form['location'],
            "Year": request.form['year'],
            "Girls": girls,
            "Boys": boys,
            "Total": boys + girls,
            "Company": request.form['company'],
            "FY": request.form['fy'],
            "Phase": request.form['phase'],
            "Remarks": request.form['remarks']
        }

        save_to_excel(data)
        success = True

    return render_template_string(dashboard_page, success=success)


# ================= EXPORT =================
@app.route('/export')
def export():
    if os.path.exists(excel_file):
        return send_file(excel_file, as_attachment=True)
    return "No data"


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')
# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
