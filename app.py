# ===============================
# School Data Entry Web App
# Tech: Python Flask + Supabase PostgreSQL + Google Drive OAuth Image Upload
# ===============================

from flask import Flask, render_template_string, request, redirect, session, send_file, url_for
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()
import json
import io
import traceback

# ========================
# PostgreSQL / Supabase
# ========================
import psycopg2
import psycopg2.extras

# ========================
# Google Drive OAuth
# ========================
from werkzeug.utils import secure_filename
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive']

# Required Render env variables:
# SUPABASE_DATABASE_URL  OR DATABASE_URL
# GOOGLE_CLIENT_SECRETS
# GOOGLE_REDIRECT_URI
# GOOGLE_TOKEN_JSON
# PARENT_FOLDER_ID

# ========================
# APP CONFIG
# ========================

app = Flask(
    __name__,
    static_folder='static',
    template_folder='templates'
)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "secret123")

PARENT_FOLDER_ID = os.environ.get("PARENT_FOLDER_ID", "1SzrOrn93f3SDRBmWcYwhrLH3YUeQ-cuy")
TOKEN_FILE = "token.json"
drive_service = None

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# ========================
# HTML TEMPLATES
# ========================

BASE_STYLE = """
<style>
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', Arial; margin:0; background: linear-gradient(120deg, #e3f2fd, #f1f8e9); }
.header { background:#1b5e20; color:white; padding:12px 16px; display:flex; justify-content:space-between; align-items:center; }
.header-logo { width:40px; height:40px; object-fit:contain; margin-right:10px; }
.header a { color:white; text-decoration:none; margin-left:10px; font-size:14px; }
.container { display:flex; justify-content:center; padding:15px; }
.form-card, .menu-card { background:white; padding:20px; border-radius:12px; width:100%; max-width:760px; box-shadow:0 6px 18px rgba(0,0,0,0.15); }
.form-grid { display:grid; grid-template-columns: repeat(2, 1fr); gap:15px; }
.form-group { display:flex; flex-direction:column; }
.form-group.full { grid-column: span 2; }
h2 { text-align:center; color:#2e7d32; }
label { font-weight:bold; }
input, textarea, select { width:100%; padding:10px; margin-top:5px; border-radius:6px; border:1px solid #ccc; }
button, .menu-button { width:100%; background:#2e7d32; color:white; padding:12px; border:none; border-radius:6px; margin-top:20px; display:block; text-align:center; text-decoration:none; font-size:16px; }
.menu-button.secondary { background:#1565c0; }
.success { text-align:center; color:green; font-weight:bold; margin-top:10px; }
.error { text-align:center; color:#b71c1c; font-weight:bold; margin-top:10px; }
.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; margin-top:16px; }
th, td { border:1px solid #ddd; padding:8px; font-size:13px; }
th { background:#e8f5e9; }
@media(max-width:700px) { .form-grid { grid-template-columns:1fr; } .form-group.full { grid-column:span 1; } }
</style>
"""

HEADER_HTML = """
<div class="header">
    <div style="display:flex; align-items:center;">
        <img src="{{ url_for('static', filename='logo.png') }}" class="header-logo" alt="Logo" onerror="this.style.display='none'">
        <strong>Ummid Foundation (Hope for Human)</strong>
    </div>
    <div>
        <a href="/menu">Menu</a>
        <a href="/records">Records</a>
        <a href="/export">Download Excel</a>
        <a href="/oauth-status">OAuth Status</a>
        <a href="/logout">Logout</a>
    </div>
</div>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body><div class="container"><div class="form-card" style="max-width:420px;"><div style="text-align:center; margin-bottom:15px;">
<img src="{{ url_for('static', filename='logo.png') }}" alt="Logo" style="width:100px; height:100px; object-fit:contain;" onerror="this.style.display='none'">
<div style="margin-top:10px; color:#1b5e20; font-size:18px;">
<strong>Ummid Foundation (Hope for Human)</strong>
</div>
</div>
<h2>Login</h2>
<form method="POST"><div class="form-group"><label>Username</label><input name="username" required></div>
<div class="form-group"><label>Password</label><input type="password" name="password" required></div>
<button type="submit">Login</button></form>{% if error %}<p class="error">{{ error }}</p>{% endif %}</div></div></body></html>
"""

MENU_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="menu-card"><h2>Dashboard Menu</h2>
<a class="menu-button" href="/school-entry">School Data Entry</a>
<a class="menu-button secondary" href="/image-upload">Image Upload</a>
<a class="menu-button" href="/records">View Records</a>
</div></div></body></html>
"""

SCHOOL_ENTRY_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
<script>function calculateTotal(){var boys=parseInt(document.getElementById('boys').value)||0;var girls=parseInt(document.getElementById('girls').value)||0;document.getElementById('total').value=boys+girls;}</script>
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card"><h2>School Data Entry</h2><form method="post"><div class="form-grid">
<div class="form-group"><label>UDISC Number</label><input name="udisc" required></div>
<div class="form-group"><label>School Name</label><input name="school" required></div>
<div class="form-group"><label>Location</label><input name="location"></div>
<div class="form-group"><label>Year of Establishment</label><input name="year"></div>
<div class="form-group"><label>Girls</label><input id="girls" name="girls" onkeyup="calculateTotal()"></div>
<div class="form-group"><label>Boys</label><input id="boys" name="boys" onkeyup="calculateTotal()"></div>
<div class="form-group"><label>Total Students</label><input id="total" name="total" readonly></div>
<div class="form-group"><label>Company Name</label><input name="company"></div>
<div class="form-group"><label>FY</label><input name="fy"></div>
<div class="form-group"><label>Phase</label><select name="phase"><option>1st Phase</option><option>2nd Phase</option><option>3rd Phase</option><option>4th Phase</option></select></div>
<div class="form-group full"><label>Remarks</label><textarea name="remarks"></textarea></div>
</div><button type="submit">Save School Data</button></form>{% if success %}<p class="success">School data saved to Supabase ✅</p>{% endif %}</div></div></body></html>
"""

IMAGE_UPLOAD_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card"><h2>Image Upload</h2><form method="post" enctype="multipart/form-data"><div class="form-grid">
<div class="form-group"><label>UDISC Number</label><input name="udisc" required></div>
<div class="form-group"><label>School Name</label><input name="school" required></div>
<div class="form-group full"><label>Smart Class Photos</label><input type="file" name="smart_class" accept="image/png,image/jpeg" multiple></div>
<div class="form-group full"><label>RO Photos</label><input type="file" name="ro" accept="image/png,image/jpeg" multiple></div>
<div class="form-group full"><label>Sanitary Photos</label><input type="file" name="sanitary" accept="image/png,image/jpeg" multiple></div>
<div class="form-group full"><label>Toilet Photos</label><input type="file" name="toilet" accept="image/png,image/jpeg" multiple></div>
</div><button type="submit">Upload Images</button></form>{% if success %}<p class="success">Images uploaded to Google Drive ✅</p>{% endif %}</div></div></body></html>
"""

RECORDS_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card" style="max-width:1100px;"><h2>Saved School Records</h2><div class="table-wrap"><table>
<thead><tr><th>ID</th><th>UDISC</th><th>School Code</th>
<th>School Name</th><th>Location</th><th>Year</th><th>Girls</th><th>Boys</th><th>Total</th><th>Company</th><th>FY</th><th>Phase</th><th>Remarks</th><th>Created</th></tr></thead>
<tbody>{% for row in records %}<tr><td>{{ row.id }}</td><td>{{ row.udisc_number }}</td><td>{{ row.school_code }}</td>
<td>{{ row.school_name }}</td><td>{{ row.location }}</td><td>{{ row.year }}</td><td>{{ row.girls }}</td><td>{{ row.boys }}</td><td>{{ row.total_students }}</td><td>{{ row.company_name }}</td><td>{{ row.fy }}</td><td>{{ row.phase }}</td><td>{{ row.remarks }}</td><td>{{ row.created_at }}</td></tr>{% endfor %}</tbody>
</table></div></div></div></body></html>
"""

# ========================
# DATABASE HELPERS
# ========================

def get_database_url():
    return os.environ.get("SUPABASE_DATABASE_URL") or os.environ.get("DATABASE_URL")


def get_db_connection():
    database_url = get_database_url()
    if not database_url:
        raise Exception("SUPABASE_DATABASE_URL or DATABASE_URL environment variable not found")
    return psycopg2.connect(database_url, sslmode="require")


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS school_records (
            id SERIAL PRIMARY KEY,
            udisc_number TEXT NOT NULL,
            school_code TEXT,
            school_name TEXT NOT NULL,
            location TEXT,
            year TEXT,
            girls INTEGER DEFAULT 0,
            boys INTEGER DEFAULT 0,
            total_students INTEGER DEFAULT 0,
            company_name TEXT,
            fy TEXT,
            phase TEXT,
            remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS image_uploads (
            id SERIAL PRIMARY KEY,
            udisc_number TEXT NOT NULL,
            school_code TEXT,
            school_name TEXT NOT NULL,
            category TEXT NOT NULL,
            original_filename TEXT,
            drive_file_id TEXT,
            drive_file_name TEXT,
            drive_folder_id TEXT,
            drive_web_link TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("ALTER TABLE school_records ADD COLUMN IF NOT EXISTS school_code TEXT")
    cur.execute("ALTER TABLE image_uploads ADD COLUMN IF NOT EXISTS school_code TEXT")
    conn.commit()
    cur.close()
    conn.close()


def save_school_to_db(data):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO school_records (
            udisc_number, school_name, location, year, girls, boys, total_students,
            company_name, fy, phase, remarks
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["UDISC Number"], data["School Name"], data["Location"], data["Year"],
        data["Girls"], data["Boys"], data["Total Students"], data["Company Name"],
        data["FY"], data["Phase"], data["Remarks"]
    ))
    conn.commit()
    cur.close()
    conn.close()


def save_image_to_db(data):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO image_uploads (
            udisc_number, school_name, category, original_filename,
            drive_file_id, drive_file_name, drive_folder_id, drive_web_link
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["udisc_number"], data["school_name"], data["category"],
        data["original_filename"], data["drive_file_id"], data["drive_file_name"],
        data["drive_folder_id"], data["drive_web_link"]
    ))
    conn.commit()
    cur.close()
    conn.close()


def get_school_records():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, udisc_number, school_name, location, year, girls, boys,
               total_students, company_name, fy, phase, remarks, created_at
        FROM school_records
        ORDER BY id DESC
    """)
    records = cur.fetchall()
    cur.close()
    conn.close()
    return records

# ========================
# GOOGLE DRIVE OAUTH HELPERS
# ========================

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
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_token(creds)
        if not creds or not creds.valid:
            print("❌ Google OAuth credentials are invalid. Open /authorize again.")
            return None
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        print("✅ Google Drive OAuth Connected Successfully")
        return service
    except Exception as e:
        print("❌ GOOGLE DRIVE OAUTH CONNECTION ERROR:", str(e))
        return None


def escape_drive_query(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        file_metadata = {'name': filename, 'parents': [folder_id]}
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
        return uploaded_file
    except HttpError as e:
        error_content = e.content.decode("utf-8") if hasattr(e, "content") else str(e)
        print("❌ FILE UPLOAD HTTP ERROR:", error_content)
        raise Exception(f"Google Drive upload failed for {file.filename}: {error_content}")
    except Exception as e:
        print("❌ FILE UPLOAD ERROR:", repr(e))
        raise e

# ========================
# INITIALIZE DRIVE SERVICE
# ========================

drive_service = get_drive_service()

# ========================
# GOOGLE OAUTH ROUTES
# ========================

@app.route('/authorize')
def authorize():
    try:
        client_secrets_json = os.environ.get("GOOGLE_CLIENT_SECRETS")
        if not client_secrets_json:
            return "❌ GOOGLE_CLIENT_SECRETS environment variable not found"
        client_config = json.loads(client_secrets_json)
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", url_for('oauth2callback', _external=True))
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
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", url_for('oauth2callback', _external=True))
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
        Key:<br><b>GOOGLE_TOKEN_JSON</b><br><br>
        Value:<br><textarea style='width:100%; height:250px;'>{json.dumps(token_data)}</textarea><br><br>
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
# LOGIN / MENU ROUTES
# ========================

@app.route('/', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['user'] = 'admin'
            return redirect('/menu')
        else:
            error = "Invalid login"
    return render_template_string(LOGIN_TEMPLATE, error=error)


@app.route('/menu')
def menu():
    if 'user' not in session:
        return redirect('/')
    return render_template_string(MENU_TEMPLATE)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    return redirect('/menu')

# ========================
# SCHOOL DATA ENTRY
# ========================

@app.route('/school-entry', methods=['GET', 'POST'])
def school_entry():
    if 'user' not in session:
        return redirect('/')
    success = False
    if request.method == 'POST':
        try:
            boys = int(request.form.get('boys') or 0)
            girls = int(request.form.get('girls') or 0)
            school_code = request.form.get('school_code', '').strip()
            school_name = request.form.get('school_name', '').strip()
            udisc_number = request.form.get('udisc', '').strip()
            if not school_name:
                return "School name is required"
            if not udisc_number:
                return "UDISC number is required"
            data = {
                "UDISC Number": udisc_number,
                "School Code": school_code,
                "School_Name": school_name,
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
            error_text = traceback.format_exc()
            print("SCHOOL ENTRY ERROR:")
            print(error_text)
            return f"<pre>Error occurred:\n{error_text}</pre>"
    return render_template_string(SCHOOL_ENTRY_TEMPLATE, success=success)

# ========================
# IMAGE UPLOAD
# ========================

@app.route('/image-upload', methods=['GET', 'POST'])
def image_upload():
    if 'user' not in session:
        return redirect('/')
    success = False
    if request.method == 'POST':
        try:
            school_code = request.form.get('school_code', '').strip()
            school_name = request.form.get('school_name', '').strip()
            udisc_number = request.form.get('udisc', '').strip()
            if not school_name:
                return "School name is required"
            if not udisc_number:
                return "UDISC number is required"
            main_folder_name = f"{school_code}_{school_name}_{udisc_number}"
            school_folder_id = create_folder(main_folder_name, PARENT_FOLDER_ID)
            if not school_folder_id:
                return "❌ Failed to create School folder in Google Drive. Open /authorize first."
            folders = {
                "smart_class": create_folder("Smart_Class", school_folder_id),
                "ro": create_folder("RO", school_folder_id),
                "sanitary": create_folder("Sanitary", school_folder_id),
                "toilet": create_folder("Toilet", school_folder_id)
            }
            upload_count = 0
            for field, folder_id in folders.items():
                if not folder_id:
                    print(f"⚠ Skipping {field} folder")
                    continue
                files = request.files.getlist(field)
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        uploaded_file = upload_file(file, folder_id)
                        upload_count += 1
                        save_image_to_db({
                            "udisc_number": udisc_number,
                            "school_code": school_code,
                            "school_name": school_name,
                            "category": field,
                            "original_filename": file.filename,
                            "drive_file_id": uploaded_file.get("id"),
                            "drive_file_name": uploaded_file.get("name"),
                            "drive_folder_id": folder_id,
                            "drive_web_link": uploaded_file.get("webViewLink")
                        })
            if upload_count == 0:
                return "No valid image files selected. Allowed: png, jpg, jpeg"
            success = True
        except Exception as e:
            error_text = traceback.format_exc()
            print("IMAGE UPLOAD ERROR:")
            print(error_text)
            return f"<pre>Error occurred:\n{error_text}</pre>"
    return render_template_string(IMAGE_UPLOAD_TEMPLATE, success=success)

# ========================
# RECORDS / EXPORT
# ========================

@app.route('/records')
def records():
    if 'user' not in session:
        return redirect('/')
    try:
        school_records = get_school_records()
        return render_template_string(RECORDS_TEMPLATE, records=school_records)
    except Exception as e:
        error_text = traceback.format_exc()
        print("RECORDS ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/export')
def export():
    if 'user' not in session:
        return redirect('/')
    try:
        records = get_school_records()
        df = pd.DataFrame(records)
        export_file = "school_data_export.xlsx"
        df.to_excel(export_file, index=False, engine='openpyxl')
        return send_file(export_file, as_attachment=True)
    except Exception as e:
        error_text = traceback.format_exc()
        print("EXPORT ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"

# ========================
# TEST ROUTES
# ========================

@app.route('/test-db')
def test_db():
    try:
        init_db()
        return "✅ Supabase PostgreSQL connection OK"
    except Exception as e:
        error_text = traceback.format_exc()
        return f"<pre>❌ Supabase PostgreSQL Error:\n{error_text}</pre>"


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
        error_text = traceback.format_exc()
        print("TEST DRIVE ERROR:")
        print(error_text)
        return f"<pre>❌ Google Drive Error:\n{error_text}</pre>"

# ========================
# LOGOUT
# ========================

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# ========================
# RUN
# ========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
