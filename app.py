# ===============================
# School Data Entry Web App
# Tech: Python Flask + Excel + Image Upload
# ===============================

from flask import Flask, render_template, request, redirect, session, send_file, url_for
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

PARENT_FOLDER_ID = '1SzrOrn93f3SDRBmWcYwhrLH3YUeQ-cuy'

app = Flask(
    __name__,
    static_folder='static',
    template_folder='templates'
)
app.secret_key = "secret123"

excel_file = "school_data.xlsx"

# ===== IMAGE UPLOAD CONFIG =====
USE_GOOGLE_DRIVE = True
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
            redirect_uri=redirect_uri
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        session['state'] = state

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

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=session.get('state'),
            redirect_uri=redirect_uri
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


# ================= LOGIN =================
@app.route('/', methods=['GET', 'POST'])
def login():

    error = ""

    if request.method == 'POST':

        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':

            session['user'] = 'admin'

            return redirect('/dashboard')

        else:
            error = "Invalid login"

    return render_template("login.html", error=error)


# ================= DASHBOARD =================


# ================= SAVE =================

def save_to_excel(data):

    try:

        df_new = pd.DataFrame([data])

        # If file exists, try reading
        if os.path.exists(excel_file):

            try:
                df_old = pd.read_excel(excel_file, engine='openpyxl')

                df = pd.concat(
                    [df_old, df_new],
                    ignore_index=True
                )

            except Exception as e:

                print("Excel read failed:", str(e))

                # create fresh dataframe
                df = df_new

        else:
            df = df_new

        # Save safely
        df.to_excel(
            excel_file,
            index=False,
            engine='openpyxl'
        )

        print("✅ Excel Saved Successfully")

    except Exception as e:

        print("❌ EXCEL SAVE ERROR:", str(e))

        raise e

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
            fields='id,name,parents',
            supportsAllDrives=True
        )

        uploaded_file = None

        while uploaded_file is None:
            status, uploaded_file = request_upload.next_chunk()

        print(f"✅ Uploaded SUCCESS: {uploaded_file.get('name')} ID: {uploaded_file.get('id')}")
        return uploaded_file.get("id")

    except HttpError as e:
        error_content = e.content.decode("utf-8") if hasattr(e, "content") else str(e)
        print("❌ FILE UPLOAD HTTP ERROR:", error_content)
        raise Exception(f"Google Drive upload failed for {file.filename}: {error_content}")

    except Exception as e:
        print("❌ FILE UPLOAD ERROR:", repr(e))
        raise e
# ================= DASHBOARD =================

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
                        upload_file(file, folder_id)

            data = {
                "UDISC Number": udisc_number,
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

            import traceback
            error_text = traceback.format_exc()

            print("DASHBOARD ERROR:")
            print(error_text)

            return f"<pre>Error occurred:\n{error_text}</pre>"

    return render_template("dashboard.html", success=success)

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

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
