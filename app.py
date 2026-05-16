# ===============================
# School Data Entry Web App
# Tech: Python Flask + PostgreSQL + Google Drive OAuth Image Upload
# ===============================

from flask import Flask, render_template_string, request, redirect, session, send_file, url_for
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()
import json
import io
from datetime import datetime

# ========================
# PostgreSQL
# ========================
import psycopg2
from psycopg2.extras import RealDictCursor

# ========================
# Google Drive
# ========================
from werkzeug.utils import secure_filename
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive']

# ========================
# GOOGLE DRIVE OAUTH CONNECTION
# ========================

TOKEN_FILE = "token.json"
drive_service = None


def save_token(creds):
    token_data = json.loads(creds.to_json())

    with open(TOKEN_FILE, "w") as token_file:
        json.dump(token_data, token_file)

    return token_data


def load_token():
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")

    if token_json:
        return json.loads(token_json)

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as token_file:
            return json.load(token_file)

    return None


def get_drive_service():
    try:
        token_data = load_token()

        if not token_data:
            print("❌ Google OAuth token not found. Open /authorize first.")
            return None

        creds = Credentials.from_authorized_user_info(
            token_data,
            SCOPES
        )

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_token(creds)

        if not creds or not creds.valid:
            print("❌ Google OAuth credentials are invalid. Open /authorize again.")
            return None

        service = build(
            'drive',
            'v3',
            credentials=creds,
            cache_discovery=False
        )

        print("✅ Google Drive OAuth Connected Successfully")
        return service

    except Exception as e:
        print("❌ GOOGLE DRIVE OAUTH CONNECTION ERROR:", str(e))
        return None


drive_service = get_drive_service()

# ========================
# GOOGLE DRIVE PARENT FOLDER
# ========================

PARENT_FOLDER_ID = os.environ.get(
    "PARENT_FOLDER_ID",
    "1SzrOrn93f3SDRBmWcYwhrLH3YUeQ-cuy"
)

app = Flask(
    __name__,
    static_folder='static',
    template_folder='templates'
)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# ===== IMAGE UPLOAD CONFIG =====
USE_GOOGLE_DRIVE = True
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========================
# POSTGRESQL CONNECTION
# ========================

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL environment variable not found")

    return psycopg2.connect(database_url)


def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                id SERIAL PRIMARY KEY,
                udisc_number VARCHAR(100) NOT NULL,
                school_name TEXT NOT NULL,
                location TEXT,
                establishment_year VARCHAR(50),
                girls INTEGER DEFAULT 0,
                boys INTEGER DEFAULT 0,
                total_students INTEGER DEFAULT 0,
                company_name TEXT,
                fy VARCHAR(50),
                phase VARCHAR(50),
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS school_images (
                id SERIAL PRIMARY KEY,
                udisc_number VARCHAR(100) NOT NULL,
                school_name TEXT NOT NULL,
                category VARCHAR(100) NOT NULL,
                file_name TEXT NOT NULL,
                drive_file_id TEXT,
                drive_folder_id TEXT,
                drive_link TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cur.close()
        conn.close()

        print("✅ PostgreSQL tables ready")

    except Exception as e:
        print("❌ POSTGRESQL INIT ERROR:", str(e))


init_db()


def save_school_to_db(data):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO schools (
            udisc_number,
            school_name,
            location,
            establishment_year,
            girls,
            boys,
            total_students,
            company_name,
            fy,
            phase,
            remarks
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data["UDISC Number"],
        data["School Name"],
        data["Location"],
        data["Year"],
        data["Girls"],
        data["Boys"],
        data["Total Students"],
        data["Company Name"],
        data["FY"],
        data["Phase"],
        data["Remarks"]
    ))

    conn.commit()
    cur.close()
    conn.close()

    print("✅ School data saved to PostgreSQL")


def save_image_to_db(data):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO school_images (
            udisc_number,
            school_name,
            category,
            file_name,
            drive_file_id,
            drive_folder_id,
            drive_link
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        data["UDISC Number"],
        data["School Name"],
        data["Category"],
        data["File Name"],
        data["Drive File ID"],
        data["Drive Folder ID"],
        data["Drive Link"]
    ))

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Image record saved to PostgreSQL")


def get_school_records():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            udisc_number AS "UDISC Number",
            school_name AS "School Name",
            location AS "Location",
            establishment_year AS "Year",
            girls AS "Girls",
            boys AS "Boys",
            total_students AS "Total Students",
            company_name AS "Company Name",
            fy AS "FY",
            phase AS "Phase",
            remarks AS "Remarks",
            created_at AS "Created At"
        FROM schools
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows


# ================= GOOGLE OAUTH ROUTES =================

@app.route('/authorize')
def authorize():

    try:
        client_secrets_json = os.environ.get("GOOGLE_CLIENT_SECRETS")

        if not client_secrets_json:
            return "❌ GOOGLE_CLIENT_SECRETS environment variable not found"

        client_config = json.loads(client_secrets_json)

        redirect_uri = os.environ.get(
            "GOOGLE_REDIRECT_URI",
            url_for('oauth2callback', _external=True)
        )

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            autogenerate_code_verifier=True
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        session['state'] = state
        session['code_verifier'] = flow.code_verifier

        return redirect(authorization_url)

    except Exception as e:
        return f"❌ OAuth Authorization Error: {str(e)}"


@app.route('/oauth2callback')
def oauth2callback():

    global drive_service

    try:
        client_secrets_json = os.environ.get("GOOGLE_CLIENT_SECRETS")

        if not client_secrets_json:
            return "❌ GOOGLE_CLIENT_SECRETS environment variable not found"

        client_config = json.loads(client_secrets_json)

        redirect_uri = os.environ.get(
            "GOOGLE_REDIRECT_URI",
            url_for('oauth2callback', _external=True)
        )

        code_verifier = session.get('code_verifier')

        if not code_verifier:
            return "❌ OAuth Callback Error: Missing code verifier in session. Open /authorize again in the same browser."

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=session.get('state'),
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )

        flow.fetch_token(authorization_response=request.url)

        creds = flow.credentials
        token_data = save_token(creds)

        drive_service = get_drive_service()

        return f"""
        ✅ Google Drive OAuth Connected Successfully <br><br>

        Copy this full token JSON and save it in Render Environment Variable:<br><br>

        Key:<br>
        <b>GOOGLE_TOKEN_JSON</b><br><br>

        Value:<br>
        <textarea style='width:100%; height:250px;'>{json.dumps(token_data)}</textarea><br><br>

        After saving GOOGLE_TOKEN_JSON in Render, redeploy the app.
        """

    except Exception as e:
        return f"❌ OAuth Callback Error: {str(e)}"


@app.route('/oauth-status')
def oauth_status():

    global drive_service

    drive_service = get_drive_service()

    if drive_service:
        return "✅ Google Drive OAuth is connected"

    return "❌ Google Drive OAuth is not connected. Open /authorize"


# ========================
# HTML TEMPLATES
# ========================

BASE_STYLE = """
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
    justify-content:space-between;
    align-items:center;
}
.header-logo {
    width: 40px;
    height: 40px;
    object-fit: contain;
    margin-right: 10px;
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
    max-width:760px;
    box-shadow:0 6px 18px rgba(0,0,0,0.15);
}
.menu-card {
    background:white;
    padding:24px;
    border-radius:12px;
    width:100%;
    max-width:600px;
    box-shadow:0 6px 18px rgba(0,0,0,0.15);
    text-align:center;
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
button, .menu-button {
    width:100%;
    background:#2e7d32;
    color:white;
    padding:12px;
    border:none;
    border-radius:6px;
    margin-top:20px;
    display:block;
    text-decoration:none;
    font-size:16px;
    cursor:pointer;
}
.menu-button.secondary {
    background:#1565c0;
}
.success {
    text-align:center;
    color:green;
    font-weight:bold;
    margin-top:10px;
}
.error {
    text-align:center;
    color:red;
    font-weight:bold;
    margin-top:10px;
}
.table-wrap {
    overflow-x:auto;
}
table {
    width:100%;
    border-collapse:collapse;
    background:white;
}
th, td {
    border:1px solid #ddd;
    padding:8px;
    font-size:13px;
}
th {
    background:#2e7d32;
    color:white;
}
@media(max-width:700px) {
    .form-grid {
        grid-template-columns: 1fr;
    }
    .form-group.full {
        grid-column: span 1;
    }
}
</style>
"""

HEADER_HTML = """
<div class="header">
    <div style="display:flex; align-items:center;">
        <img
            src="{{ url_for('static', filename='logo.png') }}"
            class="header-logo"
            alt="Logo"
        >
        <strong>Ummid Foundation (Hope for Human)</strong>
    </div>
    <div>
        <a href="/menu">Menu</a>
        <a href="/records">View Records</a>
        <a href="/export">Download Excel</a>
        <a href="/logout">Logout</a>
    </div>
</div>
"""


def page_template(title, body):
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
{BASE_STYLE}
<script>
function calculateTotal() {{
    var boys = parseInt(document.getElementById('boys')?.value) || 0;
    var girls = parseInt(document.getElementById('girls')?.value) || 0;
    var total = document.getElementById('total');
    if (total) {{
        total.value = boys + girls;
    }}
}}
</script>
</head>
<body>
{HEADER_HTML}
{body}
</body>
</html>
"""


# ================= LOGIN =================

@app.route('/', methods=['GET', 'POST'])
def login():

    error = ""

    if request.method == 'POST':

        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':

            session['user'] = 'admin'

            return redirect('/menu')

        else:
            error = "Invalid login"

    login_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login</title>
{BASE_STYLE}
</head>
<body>
<div class="container">
    <div class="form-card" style="max-width:420px;">
        <h2>Login</h2>
        <form method="post">
            <div class="form-group">
                <label>Username</label>
                <input name="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input name="password" type="password">
            </div>
            <button type="submit">Login</button>
        </form>
        {{% if error %}}
        <p class="error">{{{{ error }}}}</p>
        {{% endif %}}
    </div>
</div>
</body>
</html>
"""

    return render_template_string(login_html, error=error)


# ================= MENU =================

@app.route('/menu')
def menu():

    if 'user' not in session:
        return redirect('/')

    body = """
<div class="container">
    <div class="menu-card">
        <h2>Main Menu</h2>
        <a class="menu-button" href="/school-entry">School Data Entery</a>
        <a class="menu-button secondary" href="/image-upload">Image upload</a>
    </div>
</div>
"""

    return render_template_string(page_template("Menu", body))


# ================= SCHOOL DATA ENTRY =================

@app.route('/school-entry', methods=['GET', 'POST'])
def school_entry():

    if 'user' not in session:
        return redirect('/')

    success = False

    if request.method == 'POST':

        try:
            boys = int(request.form.get('boys') or 0)
            girls = int(request.form.get('girls') or 0)

            school_name = request.form.get('school', '').strip()
            udisc_number = request.form.get('udisc', '').strip()

            if not school_name:
                return "School name is required"

            if not udisc_number:
                return "UDISC number is required"

            data = {
                "UDISC Number": udisc_number,
                "School Name": school_name,
                "Location": request.form.get('location', ''),
                "Year": request.form.get('year', ''),
                "Girls": girls,
                "Boys": boys,
                "Total Students": boys + girls,
                "Company Name": request.form.get('company', ''),
                "FY": request.form.get('fy', ''),
                "Phase": request.form.get('phase', ''),
                "Remarks": request.form.get('remarks', '')
            }

            save_school_to_db(data)

            success = True

        except Exception as e:
            import traceback
            error_text = traceback.format_exc()
            print("SCHOOL ENTRY ERROR:")
            print(error_text)
            return f"<pre>Error occurred:\n{error_text}</pre>"

    body = """
<div class="container">
<div class="form-card">
<h2>School Data Entry</h2>

<form method="post">

<div class="form-grid">

<div class="form-group">
<label>UDISC Number</label>
<input name="udisc" required>
</div>

<div class="form-group">
<label>School Name</label>
<input name="school" required>
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

</div>

<button type="submit">Submit School Data</button>

</form>

{% if success %}
<p class="success">School Data Saved to PostgreSQL ✅</p>
{% endif %}

</div>
</div>
"""

    return render_template_string(page_template("School Data Entry", body), success=success)


# ================= IMAGE UPLOAD =================

@app.route('/image-upload', methods=['GET', 'POST'])
def image_upload():

    if 'user' not in session:
        return redirect('/')

    success = False

    if request.method == 'POST':

        try:
            school_name = request.form.get('school', '').strip()
            udisc_number = request.form.get('udisc', '').strip()

            if not school_name:
                return "School name is required"

            if not udisc_number:
                return "UDISC number is required"

            main_folder_name = f"{school_name}_{udisc_number}"

            school_folder_id = create_folder(main_folder_name, PARENT_FOLDER_ID)

            if not school_folder_id:
                return "❌ Failed to create School folder in Google Drive. Open /authorize first."

            folders = {
                "smart_class": create_folder("Smart_Class", school_folder_id),
                "ro": create_folder("RO", school_folder_id),
                "sanitary": create_folder("Sanitary", school_folder_id),
                "toilet": create_folder("Toilet", school_folder_id)
            }

            for field, folder_id in folders.items():

                if not folder_id:
                    print(f"⚠ Skipping {field} folder")
                    continue

                files = request.files.getlist(field)

                for file in files:

                    if file and file.filename and allowed_file(file.filename):
                        uploaded = upload_file(file, folder_id)

                        save_image_to_db({
                            "UDISC Number": udisc_number,
                            "School Name": school_name,
                            "Category": field,
                            "File Name": uploaded["name"],
                            "Drive File ID": uploaded["id"],
                            "Drive Folder ID": folder_id,
                            "Drive Link": uploaded["webViewLink"]
                        })

            success = True

        except Exception as e:
            import traceback
            error_text = traceback.format_exc()
            print("IMAGE UPLOAD ERROR:")
            print(error_text)
            return f"<pre>Error occurred:\n{error_text}</pre>"

    body = """
<div class="container">
<div class="form-card">
<h2>Image Upload</h2>

<form method="post" enctype="multipart/form-data">

<div class="form-grid">

<div class="form-group">
<label>UDISC Number</label>
<input name="udisc" required>
</div>

<div class="form-group">
<label>School Name</label>
<input name="school" required>
</div>

<div class="form-group full">
<label>Smart Class Photos</label>
<input type="file" name="smart_class" accept="image/png,image/jpeg" multiple>
</div>

<div class="form-group full">
<label>RO Photos</label>
<input type="file" name="ro" accept="image/png,image/jpeg" multiple>
</div>

<div class="form-group full">
<label>Sanitary Photos</label>
<input type="file" name="sanitary" accept="image/png,image/jpeg" multiple>
</div>

<div class="form-group full">
<label>Toilet Photos</label>
<input type="file" name="toilet" accept="image/png,image/jpeg" multiple>
</div>

</div>

<button type="submit">Upload Images</button>

</form>

{% if success %}
<p class="success">Images Uploaded to Google Drive + Saved in PostgreSQL ✅</p>
{% endif %}

</div>
</div>
"""

    return render_template_string(page_template("Image Upload", body), success=success)


# ================= TEST GOOGLE DRIVE =================

@app.route('/test-drive')
def test_drive():

    global drive_service
    drive_service = get_drive_service()

    try:

        if not drive_service:
            return "❌ Drive service not initialized. Open /authorize first."

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

def escape_drive_query(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


def create_folder(name, parent_id):

    global drive_service

    if not drive_service:
        drive_service = get_drive_service()

    if not drive_service:
        print("❌ Drive service not initialized")
        return None

    try:
        print(f"📁 Creating folder: {name}")

        safe_name = escape_drive_query(name)

        # Step 1: check if folder exists
        query = (
            f"name='{safe_name}' and "
            f"'{parent_id}' in parents and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        )

        response = drive_service.files().list(
            q=query,
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = response.get("files", [])

        if files:
            print(f"✅ Folder already exists: {name}")
            return files[0]["id"]

        # Step 2: create folder (SIMPLIFIED)
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

        folder_id = folder.get("id")

        print(f"✅ Folder created: {folder_id}")

        return folder_id

    except Exception as e:
        print("❌ FOLDER CREATION ERROR:", repr(e))
        return None


## ======================upload File
def upload_file(file, folder_id):

    global drive_service

    if not drive_service:
        drive_service = get_drive_service()

    if not drive_service or not folder_id:
        raise Exception("Drive service or folder_id missing. Open /authorize first.")

    try:
        filename = secure_filename(file.filename)

        print("📤 Uploading:", filename)

        file.seek(0)
        file_bytes = io.BytesIO(file.read())
        file_bytes.seek(0)

        if file_bytes.getbuffer().nbytes == 0:
            raise Exception(f"File is empty: {filename}")

        media = MediaIoBaseUpload(
            file_bytes,
            mimetype=file.content_type or "application/octet-stream",
            resumable=True
        )

        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }

        request_upload = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,parents,webViewLink',
            supportsAllDrives=True
        )

        uploaded_file = None

        while uploaded_file is None:
            status, uploaded_file = request_upload.next_chunk()

        print(f"✅ Uploaded SUCCESS: {uploaded_file.get('name')} ID: {uploaded_file.get('id')}")

        return {
            "id": uploaded_file.get("id"),
            "name": uploaded_file.get("name"),
            "parents": uploaded_file.get("parents"),
            "webViewLink": uploaded_file.get("webViewLink")
        }

    except HttpError as e:
        error_content = e.content.decode("utf-8") if hasattr(e, "content") else str(e)
        print("❌ FILE UPLOAD HTTP ERROR:", error_content)
        raise Exception(f"Google Drive upload failed for {file.filename}: {error_content}")

    except Exception as e:
        print("❌ FILE UPLOAD ERROR:", repr(e))
        raise e


# ================= VIEW RECORDS =================

@app.route('/records')
def records():

    if 'user' not in session:
        return redirect('/')

    try:
        rows = get_school_records()

        body = """
<div class="container">
<div class="form-card" style="max-width:1100px;">
<h2>School Records</h2>
<div class="table-wrap">
<table>
<thead>
<tr>
<th>UDISC Number</th>
<th>School Name</th>
<th>Location</th>
<th>Year</th>
<th>Girls</th>
<th>Boys</th>
<th>Total</th>
<th>Company</th>
<th>FY</th>
<th>Phase</th>
<th>Remarks</th>
<th>Created At</th>
</tr>
</thead>
<tbody>
{% for row in rows %}
<tr>
<td>{{ row["UDISC Number"] }}</td>
<td>{{ row["School Name"] }}</td>
<td>{{ row["Location"] }}</td>
<td>{{ row["Year"] }}</td>
<td>{{ row["Girls"] }}</td>
<td>{{ row["Boys"] }}</td>
<td>{{ row["Total Students"] }}</td>
<td>{{ row["Company Name"] }}</td>
<td>{{ row["FY"] }}</td>
<td>{{ row["Phase"] }}</td>
<td>{{ row["Remarks"] }}</td>
<td>{{ row["Created At"] }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
</div>
</div>
"""

        return render_template_string(page_template("Records", body), rows=rows)

    except Exception as e:
        import traceback
        error_text = traceback.format_exc()
        print("RECORDS ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


# ================= EXPORT =================

@app.route('/export')
def export():

    if 'user' not in session:
        return redirect('/')

    try:
        rows = get_school_records()

        if not rows:
            return "No data"

        df = pd.DataFrame(rows)

        output = io.BytesIO()

        df.to_excel(
            output,
            index=False,
            engine='openpyxl'
        )

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="school_data.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        import traceback
        error_text = traceback.format_exc()
        print("EXPORT ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


# ================= LOGOUT =================

@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/')


# ================= OLD DASHBOARD REDIRECT =================

@app.route('/dashboard')
def dashboard():
    return redirect('/menu')


# ================= RUN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
