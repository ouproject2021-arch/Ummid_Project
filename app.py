# ===============================
# School Data Entry Web App
# Tech: Python Flask + Excel + Image Upload
# ===============================

from flask import Flask, render_template_string, request, redirect, session, send_file, url_for
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()
import json
import io

# ========================
# Google Drive
# ========================
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ['https://www.googleapis.com/auth/drive']

# ========================
# GOOGLE DRIVE CONNECTION
# ========================

drive_service = None

try:

    creds_json = os.environ.get("GOOGLE_CREDENTIALS")

    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS environment variable not found")

    creds_dict = json.loads(creds_json)

    # Fix private key formatting
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

    drive_service = build(
        'drive',
        'v3',
        credentials=creds
    )

    print("✅ Google Drive Connected Successfully")

except Exception as e:
    print("❌ GOOGLE DRIVE CONNECTION ERROR")
    print(str(e))
    drive_service = None


# ========================
# GOOGLE DRIVE PARENT FOLDER
# ========================

PARENT_FOLDER_ID = '1SzrOrn93f3SDRBmWcYwhrLH3YUeQ-cuy'

app = Flask(__name__)
app.secret_key = "secret123"

excel_file = "school_data.xlsx"

# ===== IMAGE UPLOAD CONFIG =====
USE_GOOGLE_DRIVE = True
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ================= LOGIN =================

login_page = '''
<!DOCTYPE html>
<html>
<head>
<style>
body {
    font-family: Arial;
    background: linear-gradient(135deg,#e8f5e9,#fff);
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
    margin:0;
}
.login-box {
    background:#fff;
    padding:30px;
    border-radius:12px;
    box-shadow:0 6px 18px rgba(0,0,0,0.15);
    text-align:center;
    width:320px;
}
.logo { width:80px; }
.brand {
    font-weight:bold;
    color:#2e7d32;
    margin:10px 0;
}
input {
    padding:10px;
    width:100%;
}
button {
    padding:10px;
    background:#2e7d32;
    color:white;
    border:none;
}
</style>
</head>

<body>

<div class="login-box">
    <img src="{{ url_for('static', filename='logo.png') }}" class="logo">
    <div class="brand">
        Ummid Foundation (Hope for Human)
    </div>

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


@app.route('/', methods=['GET', 'POST'])
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

* {
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Arial;
    margin:0;
    background: linear-gradient(120deg, #e3f2fd, #f1f8e9);
}

.header {
    background:#1b5e20;
    color:white;
    padding:12px 16px;
    display:flex;
    flex-wrap:wrap;
    justify-content:space-between;
    align-items:center;
}

.header img {
    width:36px;
    margin-right:8px;
}

.header a {
    color:white;
    text-decoration:none;
    margin-left:10px;
    font-size:14px;
}

.container {
    display:flex;
    justify-content:center;
    padding:15px;
}

.form-card {
    background:white;
    padding:20px;
    border-radius:12px;
    width:100%;
    max-width:700px;
    box-shadow:0 6px 18px rgba(0,0,0,0.15);
}

.form-grid {
    display:grid;
    grid-template-columns: repeat(2, 1fr);
    gap:15px;
}

.form-group {
    display:flex;
    flex-direction:column;
}

.form-group.full {
    grid-column: span 2;
}

h2 {
    text-align:center;
    color:#2e7d32;
}

label {
    font-weight:bold;
}

input, textarea, select {
    width:100%;
    padding:10px;
    margin-top:5px;
    border-radius:6px;
    border:1px solid #ccc;
}

button {
    width:100%;
    background:#2e7d32;
    color:white;
    padding:12px;
    border:none;
    border-radius:6px;
    margin-top:20px;
}

.success {
    text-align:center;
    color:green;
    font-weight:bold;
    margin-top:10px;
}

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

<div class="header">

    <div style="display:flex; align-items:center;">

        <img src="{{ url_for('static', filename='logo.png') }}" class="logo">

        <strong>Ummid Foundation (Hope for Human)</strong>

    </div>

    <div>
        <a href="/export">Download Excel</a>
        <a href="/logout">Logout</a>
    </div>

</div>

<div class="container">

<div class="form-card">

<h2>School Data Entry</h2>

<form method="post" enctype="multipart/form-data">

<div class="form-grid">

<div class="form-group">
<label>UDISC Number</label>
<input name="udisc">
</div>

<div class="form-group">
<label>School Name</label>
<input name="school">
</div>

<div class="form-group">
<label>Location</label>
<input name="location">
</div>

<div class="form-group">
<label>Year of Establishment</label>
<input name="year">
</div>

<div class="form-group">
<label>Girls</label>
<input id="girls" name="girls" onkeyup="calculateTotal()">
</div>

<div class="form-group">
<label>Boys</label>
<input id="boys" name="boys" onkeyup="calculateTotal()">
</div>

<div class="form-group">
<label>Total Students</label>
<input id="total" name="total" readonly>
</div>

<div class="form-group">
<label>Company Name</label>
<input name="company">
</div>

<div class="form-group">
<label>FY</label>
<input name="fy">
</div>

<div class="form-group">
<label>Phase</label>

<select name="phase">
<option>1st Phase</option>
<option>2nd Phase</option>
<option>3rd Phase</option>
<option>4th Phase</option>
</select>

</div>

<div class="form-group full">
<label>Remarks</label>
<textarea name="remarks"></textarea>
</div>

<div class="form-group full">
<label>Smart Class Photos</label>
<input type="file" name="smart_class" multiple>
</div>

<div class="form-group full">
<label>RO Photos</label>
<input type="file" name="ro" multiple>
</div>

<div class="form-group full">
<label>Sanitary Photos</label>
<input type="file" name="sanitary" multiple>
</div>

<div class="form-group full">
<label>Toilet Photos</label>
<input type="file" name="toilet" multiple>
</div>

</div>

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


# ================= TEST GOOGLE DRIVE =================

@app.route('/test-drive')
def test_drive():

    try:

        if not drive_service:
            return "❌ Drive service not initialized"

        parent = drive_service.files().get(
            fileId=PARENT_FOLDER_ID,
            fields='id,name',
            supportsAllDrives=True
        ).execute()

        folder_id = create_folder("TEST_FOLDER", PARENT_FOLDER_ID)

        return f"""
        ✅ Parent Folder Access OK <br><br>

        Parent Name: {parent['name']} <br><br>

        TEST_FOLDER ID: {folder_id}
        """

    except Exception as e:

        print("TEST DRIVE ERROR:", str(e))

        return f"❌ Google Drive Error: {str(e)}"


# ================= GOOGLE DRIVE HELPERS =================

def create_folder(name, parent_id):

    if not drive_service:
        return None

    try:

        query = f"""
        name = '{name}'
        and '{parent_id}' in parents
        and mimeType = 'application/vnd.google-apps.folder'
        and trashed = false
        """

        response = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id,name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        folders = response.get('files', [])

        # Return existing folder
        if folders:

            print(f"Folder already exists: {name}")

            return folders[0]['id']

        # Create new folder
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }

        folder = drive_service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()

        print(f"Folder created: {name}")

        return folder.get('id')

    except Exception as e:

        print("FOLDER ERROR:", str(e))

        return None


def upload_file(file, folder_id):

    if not drive_service or not folder_id:
        return

    filename = secure_filename(file.filename)

    file_stream = io.BytesIO(file.read())

    media = MediaIoBaseUpload(
        file_stream,
        mimetype=file.content_type,
        resumable=True
    )

    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }

    drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
        supportsAllDrives=True
    ).execute()

    print(f"Uploaded: {filename}")


# ================= DASHBOARD =================

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():

    if 'user' not in session:
        return redirect('/')

    success = False

    if request.method == 'POST':

        try:

            boys = int(request.form.get('boys') or 0)

            girls = int(request.form.get('girls') or 0)

            school_name = request.form['school'].strip()

            if not school_name:
                return "School name is required"

            # Create Main School Folder
            school_folder_id = create_folder(
                school_name,
                PARENT_FOLDER_ID
            )

            print("School Folder:", school_folder_id)

            # Create Subfolders
            folders = {

                "smart_class": create_folder(
                    "Smart_Class",
                    school_folder_id
                ),

                "ro": create_folder(
                    "RO",
                    school_folder_id
                ),

                "sanitary": create_folder(
                    "Sanitary",
                    school_folder_id
                ),

                "toilet": create_folder(
                    "Toilet",
                    school_folder_id
                )
            }

            # Upload Images
            for field, folder_id in folders.items():

                files = request.files.getlist(field)

                for file in files:

                    if file and file.filename != "" and allowed_file(file.filename):

                        upload_file(file, folder_id)

            # Save Excel Data
            data = {

                "UDISC Number": request.form['udisc'],
                "School Name": school_name,
                "Location": request.form['location'],
                "Year": request.form['year'],
                "Girls": girls,
                "Boys": boys,
                "Total Students": boys + girls,
                "Company Name": request.form['company'],
                "FY": request.form['fy'],
                "Phase": request.form['phase'],
                "Remarks": request.form['remarks']
            }

            save_to_excel(data)

            success = True

        except Exception as e:

            print("DASHBOARD ERROR:", str(e))

            return f"Error occurred: {str(e)}"

    return render_template_string(
        dashboard_page,
        success=success
    )


# ================= EXPORT =================

@app.route('/export')
def export():

    if os.path.exists(excel_file):

        return send_file(
            excel_file,
            as_attachment=True
        )

    return "No data"


# ================= LOGOUT =================

@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/')


# ================= RUN =================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000,
        debug=True
    )
