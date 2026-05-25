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
# PROJECT MASTER CONFIG
# ========================

PROJECT_MASTER_LIST = [
    {"slug": "education", "name": "Education"},
    {"slug": "women-empowerment", "name": "Women Empowerment"},
    {"slug": "agriculture", "name": "Agriculture"},
    {"slug": "environmental-climate", "name": "Environmental/Climate"},
    {"slug": "health-hygiene", "name": "Health & Hygiene"},
    {"slug": "hunger-malnutrition", "name": "Hunger & Malnutrition"},
]


# ========================
# HTML TEMPLATES
# ========================

BASE_STYLE = """
<style>
:root {
    --primary:#1b5e20;
    --primary-light:#2e7d32;
    --secondary:#1565c0;
    --danger:#c62828;
    --bg1:#e3f2fd;
    --bg2:#f1f8e9;
    --card:#ffffff;
    --text:#1f2937;
    --muted:#6b7280;
    --border:#d9e2dd;
    --shadow:0 10px 30px rgba(15, 23, 42, 0.14);
}
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body {
    font-family:'Segoe UI', Arial, sans-serif;
    margin:0;
    color:var(--text);
    background:
        radial-gradient(circle at top left, rgba(46,125,50,0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(21,101,192,0.12), transparent 25%),
        linear-gradient(120deg, var(--bg1), var(--bg2));
    min-height:100vh;
}
.header {
    background:rgba(27,94,32,0.96);
    color:white;
    padding:12px 18px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    position:sticky;
    top:0;
    z-index:10;
    box-shadow:0 6px 20px rgba(0,0,0,0.16);
    backdrop-filter: blur(8px);
}
.header-logo {
    width:42px;
    height:42px;
    object-fit:contain;
    margin-right:10px;
    background:white;
    border-radius:10px;
    padding:3px;
}
.header a {
    color:white;
    text-decoration:none;
    margin-left:8px;
    font-size:14px;
    padding:8px 10px;
    border-radius:8px;
    transition:all 0.2s ease;
}
.header a:hover {
    background:rgba(255,255,255,0.18);
    transform:translateY(-1px);
}
.container {
    display:flex;
    justify-content:center;
    padding:24px 15px;
}
.form-card, .menu-card {
    background:rgba(255,255,255,0.96);
    padding:24px;
    border-radius:18px;
    width:100%;
    max-width:780px;
    box-shadow:var(--shadow);
    border:1px solid rgba(255,255,255,0.65);
    animation:fadeIn 0.35s ease;
}
.form-card:hover, .menu-card:hover {
    box-shadow:0 14px 38px rgba(15,23,42,0.18);
}
.form-grid {
    display:grid;
    grid-template-columns:repeat(2, 1fr);
    gap:16px;
}
.form-group {
    display:flex;
    flex-direction:column;
}
.form-group.full {
    grid-column:span 2;
}
h2 {
    text-align:center;
    color:var(--primary);
    margin-top:4px;
    margin-bottom:20px;
    font-size:28px;
    letter-spacing:0.2px;
}
label {
    font-weight:700;
    color:#254235;
    margin-bottom:3px;
}
input, textarea, select {
    width:100%;
    padding:11px 12px;
    margin-top:5px;
    border-radius:10px;
    border:1px solid var(--border);
    background:#fbfdfc;
    transition:border 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    font-size:15px;
}
input:focus, textarea:focus, select:focus {
    outline:none;
    border-color:var(--primary-light);
    background:white;
    box-shadow:0 0 0 4px rgba(46,125,50,0.12);
}
textarea {
    min-height:90px;
    resize:vertical;
}
button, .menu-button {
    width:100%;
    background:linear-gradient(135deg, var(--primary-light), var(--primary));
    color:white;
    padding:13px;
    border:none;
    border-radius:10px;
    margin-top:20px;
    display:block;
    text-align:center;
    text-decoration:none;
    font-size:16px;
    font-weight:700;
    cursor:pointer;
    transition:transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
    box-shadow:0 8px 18px rgba(46,125,50,0.22);
}
button:hover, .menu-button:hover {
    transform:translateY(-2px);
    box-shadow:0 12px 24px rgba(46,125,50,0.28);
}
button:disabled {
    opacity:0.65;
    cursor:not-allowed;
    transform:none;
}
.menu-button.secondary {
    background:linear-gradient(135deg, #1976d2, var(--secondary));
    box-shadow:0 8px 18px rgba(21,101,192,0.22);
}
.success {
    text-align:center;
    color:#1b5e20;
    background:#e8f5e9;
    border:1px solid #c8e6c9;
    border-radius:10px;
    padding:10px;
    font-weight:bold;
    margin-top:14px;
}
.error {
    text-align:center;
    color:#b71c1c;
    background:#ffebee;
    border:1px solid #ffcdd2;
    border-radius:10px;
    padding:10px;
    font-weight:bold;
    margin-top:14px;
}
.table-wrap {
    overflow-x:auto;
    border-radius:14px;
    border:1px solid var(--border);
    background:white;
}
table {
    width:100%;
    border-collapse:collapse;
    margin-top:0;
}
th, td {
    border-bottom:1px solid #e5e7eb;
    border-right:1px solid #edf2ef;
    padding:10px;
    font-size:13px;
    vertical-align:middle;
}
th {
    background:#e8f5e9;
    color:#0f3d18;
    position:sticky;
    top:0;
    z-index:1;
}
tbody tr:nth-child(even) { background:#fbfdfc; }
tbody tr:hover { background:#f1f8e9; }
.action-link {
    display:inline-block;
    padding:7px 11px;
    border-radius:8px;
    color:white;
    text-decoration:none;
    margin:2px;
    font-size:12px;
    font-weight:700;
    transition:transform 0.2s ease, opacity 0.2s ease;
}
.action-link:hover { transform:translateY(-1px); opacity:0.92; }
.edit-link { background:#1565c0; }
.delete-link { background:#c62828; }
.inline-form { display:inline; }
.inline-button {
    width:auto;
    padding:7px 11px;
    margin:2px;
    font-size:12px;
    background:#c62828;
    box-shadow:none;
}
.badge {
    display:inline-block;
    padding:5px 9px;
    border-radius:999px;
    background:#e8f5e9;
    color:#1b5e20;
    font-size:12px;
    font-weight:700;
}
.page-note {
    text-align:center;
    color:#1b5e20;
    font-weight:bold;
    background:#f1f8e9;
    border:1px solid #c8e6c9;
    padding:10px;
    border-radius:12px;
}
.toolbar {
    display:flex;
    gap:10px;
    align-items:center;
    justify-content:space-between;
    margin-bottom:14px;
    flex-wrap:wrap;
}
.search-box {
    max-width:340px;
    margin:0;
}
@keyframes fadeIn {
    from { opacity:0; transform:translateY(8px); }
    to { opacity:1; transform:translateY(0); }
}
@media(max-width:700px) {
    .header { flex-direction:column; gap:10px; align-items:flex-start; }
    .header div:last-child { display:flex; flex-wrap:wrap; gap:4px; }
    .header a { margin-left:0; }
    .form-grid { grid-template-columns:1fr; }
    .form-group.full { grid-column:span 1; }
    .container { padding:16px 10px; }
    h2 { font-size:24px; }
}
</style>
<script>
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function() {
            var btn = form.querySelector('button[type="submit"]');
            if (btn && !btn.classList.contains('inline-button')) {
                btn.dataset.originalText = btn.innerText;
                btn.innerText = 'Please wait...';
                setTimeout(function(){ btn.disabled = true; }, 20);
            }
        });
    });
});

function filterRecordsTable() {
    var input = document.getElementById('recordSearch');
    var table = document.getElementById('recordsTable');
    if (!input || !table) return;

    var filter = input.value.toLowerCase();
    var rows = table.getElementsByTagName('tr');

    for (var i = 1; i < rows.length; i++) {
        var txt = rows[i].innerText.toLowerCase();
        rows[i].style.display = txt.indexOf(filter) > -1 ? '' : 'none';
    }
}
</script>
"""

HEADER_HTML = """
<div class="header">
    <div style="display:flex; align-items:center;">
        <img src="{{ url_for('static', filename='logo.png') }}" class="header-logo" alt="Logo" onerror="this.style.display='none'">
        <strong>Ummid Foundation (Hope for Human)</strong>
    </div>
    <div>
        <a href="/menu">Menu</a>
        <a href="/projects">Projects</a>
        <a href="/project-data-entry">Project Data Entry</a>
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
</head><body><div class="container" style="min-height:100vh; align-items:center;"><div class="form-card" style="max-width:420px;"><div style="text-align:center; margin-bottom:15px;">
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
<style>
.project-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:18px;}
.project-card{display:block;text-decoration:none;color:#1f2937;background:linear-gradient(135deg,#ffffff,#f1f8e9);border:1px solid #d9e2dd;border-radius:16px;padding:18px;box-shadow:0 8px 20px rgba(15,23,42,0.08);transition:all .2s ease;}
.project-card:hover{transform:translateY(-3px);box-shadow:0 12px 26px rgba(15,23,42,0.14);border-color:#2e7d32;}
.project-card strong{color:#1b5e20;font-size:18px;display:block;margin-bottom:6px;}
.quick-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:18px;}
@media(max-width:700px){.project-grid,.quick-actions{grid-template-columns:1fr;}}
</style>
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="menu-card" style="max-width:1100px;"><h2>Ummid Foundation Project Dashboard</h2>
<div class="page-note">Select a project page below to continue data entry/upload work.</div>
<div class="project-grid">
{% for project in projects %}
<a class="project-card" href="/project/{{ project.slug }}">
<strong>{{ project.name }}</strong>
</a>
{% endfor %}
</div>
</div></div></body></html>
"""

PROJECTS_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
<style>
.project-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:18px;}
.project-card{display:block;text-decoration:none;color:#1f2937;background:linear-gradient(135deg,#ffffff,#f1f8e9);border:1px solid #d9e2dd;border-radius:16px;padding:18px;box-shadow:0 8px 20px rgba(15,23,42,0.08);transition:all .2s ease;}
.project-card:hover{transform:translateY(-3px);box-shadow:0 12px 26px rgba(15,23,42,0.14);border-color:#2e7d32;}
.project-card strong{color:#1b5e20;font-size:18px;display:block;margin-bottom:6px;}
@media(max-width:700px){.project-grid{grid-template-columns:1fr;}}
</style>
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="menu-card" style="max-width:1000px;"><h2>Project Pages</h2>
<div class="page-note">Six core project areas of Ummid Foundation.</div>
<div class="project-grid">
{% for project in projects %}
<a class="project-card" href="/project/{{ project.slug }}">
<strong>{{ project.name }}</strong>
</a>
{% endfor %}
</div>
</div></div></body></html>
"""

PROJECT_MASTER_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
<style>
.action-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;}
.summary-box{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;}
.summary-item{background:#f1f8e9;border:1px solid #c8e6c9;border-radius:14px;padding:12px;text-align:center;}
.summary-item strong{display:block;color:#1b5e20;font-size:20px;}
@media(max-width:800px){.action-row,.summary-box{grid-template-columns:1fr;}}
</style>
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card" style="max-width:1000px;"><h2>{{ project.project_name }}</h2>
<div class="summary-box">
<div class="summary-item"><strong>{{ stats.total_records }}</strong><span>Records</span></div>
<div class="summary-item"><strong>{{ stats.total_uploads }}</strong><span>Uploads</span></div>
<div class="summary-item"><strong>{{ project.fy or 'N/A' }}</strong><span>FY</span></div>
<div class="summary-item"><strong>₹ {{ project.project_cost or '0' }}</strong><span>Cost</span></div>
</div>
<form method="post"><div class="form-grid">
<input type="hidden" name="slug" value="{{ project.slug }}">
<div class="form-group"><label>Project Area</label><input name="project_name" value="{{ project.project_name }}" readonly></div>
<div class="form-group"><label>Project ID</label><input name="project_id" value="{{ project.project_id or '' }}" placeholder="Example: EDU-2025-26-01" required></div>
<div class="form-group"><label>Project Title</label><input name="project_title" value="{{ project.project_title or '' }}" placeholder="Enter project title" required></div>
{% if project.slug != 'education' %}<div class="form-group"><label>Company Code</label><input name="company_code" value="{{ project.company_code or '' }}" placeholder="Example: CUBIC01" required></div>{% endif %}
<div class="form-group"><label>Company Name</label><input name="company_name" value="{{ project.company_name or '' }}" placeholder="CSR Partner / Company Name"></div>
<div class="form-group"><label>FY</label><input name="fy" value="{{ project.fy or '' }}" placeholder="FY 2025-26"></div>
<div class="form-group"><label>Project Cost</label><input name="project_cost" value="{{ project.project_cost or '' }}" placeholder="Example: 500000"></div>
<div class="form-group"><label>Status</label><select name="status">
<option {% if project.status == 'Planning' %}selected{% endif %}>Planning</option>
<option {% if project.status == 'In Progress' %}selected{% endif %}>In Progress</option>
<option {% if project.status == 'Completed' %}selected{% endif %}>Completed</option>
<option {% if project.status == 'On Hold' %}selected{% endif %}>On Hold</option>
</select></div>
<div class="form-group full"><label>About the Project</label><textarea name="about_project" placeholder="Write project objective, scope, beneficiary details and implementation notes">{{ project.about_project or '' }}</textarea></div>
</div><button type="submit">Save Project Master</button></form>
{% if success %}<p class="success">Project master updated successfully ✅</p>{% endif %}
<div class="action-row">
{% if project.slug == 'education' %}<a class="menu-button" href="/school-entry?project={{ project.slug }}">Add Data Entry</a>{% endif %}
<a class="menu-button secondary" href="/image-upload?project={{ project.slug }}">Upload Pics/Files</a>
{% if project.slug == 'education' %}<a class="menu-button" href="/records?project={{ project.slug }}">View Records</a>{% else %}<a class="menu-button" href="/upload-records?project={{ project.slug }}">View Records</a>{% endif %}
</div>
</div></div></body></html>
"""


PROJECT_INFO_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card" style="max-width:1100px;"><h2>Project Data Entry</h2>
<div class="page-note">Enter Project ID details once. These values will auto-populate in all project pages when Project ID is entered.</div>
<form method="post"><div class="form-grid">
<div class="form-group"><label>Project ID</label><input name="project_id" required placeholder="Example: EDU-2025-26-01"></div>
<div class="form-group"><label>Company Code</label><input name="company_code" required placeholder="Example: CUBIC01"></div>
<div class="form-group"><label>Company Name</label><input name="company_name" required></div>
<div class="form-group"><label>Project Cost</label><input name="project_cost" type="number" step="0.01" required></div>
<div class="form-group"><label>FY</label><input name="fy" placeholder="FY 2025-26" required></div>
</div><button type="submit">Save Project Data</button></form>
{% if success %}<p class="success">Project data saved successfully ✅</p>{% endif %}
<br><h2 style="font-size:22px;">Saved Project Data</h2>
<div class="table-wrap"><table id="recordsTable"><thead><tr><th>ID</th><th>Project ID</th><th>Company Code</th><th>Company Name</th><th>Project Cost</th><th>FY</th><th>Updated</th><th>Action</th></tr></thead>
<tbody>{% for row in records %}<tr><td>{{ loop.index }}</td><td>{{ row.project_id }}</td><td>{{ row.company_code }}</td><td>{{ row.company_name }}</td><td>{{ row.project_cost }}</td><td>{{ row.fy }}</td><td>{{ row.updated_at }}</td><td><a class="action-link edit-link" href="/edit-project-info/{{ row.id }}">Edit</a><form class="inline-form" method="POST" action="/delete-project-info/{{ row.id }}" onsubmit="return confirm('Delete this project data entry?');"><button class="inline-button" type="submit">Delete</button></form></td></tr>{% endfor %}</tbody></table></div>
</div></div></body></html>
"""

SCHOOL_ENTRY_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
<script>
function calculateTotal(){
    var boys=parseInt(document.getElementById('boys').value)||0;
    var girls=parseInt(document.getElementById('girls').value)||0;
    document.getElementById('total').value=boys+girls;
}

function fetchProjectInfo(){
    var projectIdInput = document.getElementById('project_id');
    if (!projectIdInput || !projectIdInput.value.trim()) return;
    fetch('/get-project-info/' + encodeURIComponent(projectIdInput.value.trim()))
        .then(function(response){ return response.json(); })
        .then(function(data){
            if(data.found){
                var cc = document.getElementById('company_code');
                var cn = document.getElementById('company');
                var fy = document.getElementById('fy');
                var pc = document.getElementById('project_cost');
                if(cc) cc.value = data.company_code || '';
                if(cn) cn.value = data.company_name || '';
                if(fy) fy.value = data.fy || '';
                if(pc) pc.value = data.project_cost || '';
            } else {
                alert('Project ID not found. Please add it first from Menu > Project Data Entry.');
            }
        })
        .catch(function(error){ console.log('Project lookup failed:', error); });
}

function validateSchoolCode(){
    var schoolCodeInput = document.getElementById('school_code');
    var submitButton = document.getElementById('save_school_button');

    if (!schoolCodeInput) return;

    var schoolCode = schoolCodeInput.value.trim();

    if (submitButton) {
        submitButton.disabled = false;
    }

    if (!schoolCode) return;

    fetch('/check-school-code/' + encodeURIComponent(schoolCode))
        .then(function(response){ return response.json(); })
        .then(function(data){
            if(data.exists){
                alert('Duplicate School Code detected. Please enter a unique School Code.');
                schoolCodeInput.value = '';
                schoolCodeInput.focus();

                if (submitButton) {
                    submitButton.disabled = true;
                }
            }
        })
        .catch(function(error){
            console.log('School Code validation failed:', error);
        });
}
</script>
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card"><h2>School Data Entry</h2><form method="post"><div class="form-grid">
<input type="hidden" name="project_slug" value="education">
<div class="form-group"><label>Project Area</label><input value="Education" readonly></div>
<div class="form-group"><label>Project ID</label><input id="project_id" name="project_id" value="{{ project_master.project_id or '' }}" onblur="fetchProjectInfo()" required></div>
<div class="form-group full"><label>Project Title</label><input value="{{ project_master.project_title or '' }}" readonly></div>
<div class="form-group"><label>UDISC Number</label><input name="udisc" required></div>
<div class="form-group"><label>School Code</label><input id="school_code" name="school_code" required onblur="validateSchoolCode()"></div>
<div class="form-group"><label>School_Name</label><input name="school_name" required></div>
<div class="form-group"><label>Location</label><input name="location"></div>
<div class="form-group"><label>Year of Establishment</label><input name="year"></div>
<div class="form-group"><label>Girls</label><input id="girls" name="girls" onkeyup="calculateTotal()"></div>
<div class="form-group"><label>Boys</label><input id="boys" name="boys" onkeyup="calculateTotal()"></div>
<div class="form-group"><label>Total Students</label><input id="total" name="total" readonly></div>
<div class="form-group"><label>Company Code</label><input id="company_code" name="company_code" readonly></div>
<div class="form-group"><label>Company Name</label><input id="company" name="company" readonly></div>
<div class="form-group"><label>Project Cost</label><input id="project_cost" name="project_cost" readonly></div>
<div class="form-group"><label>FY</label><input id="fy" name="fy" readonly></div>
<div class="form-group"><label>Phase</label><select name="phase"><option>1st Phase</option><option>2nd Phase</option><option>3rd Phase</option><option>4th Phase</option></select></div>
<div class="form-group full"><label>Remarks</label><textarea name="remarks"></textarea></div>
</div><button id="save_school_button" type="submit">Save School Data</button></form>{% if success %}<p class="success">School data saved to Supabase ✅</p>{% endif %}</div></div></body></html>
"""

IMAGE_UPLOAD_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
<script>
function fetchProjectInfo(){
    var projectIdInput = document.getElementById('project_id');
    if (!projectIdInput || !projectIdInput.value.trim()) return;
    fetch('/get-project-info/' + encodeURIComponent(projectIdInput.value.trim()))
        .then(function(response){ return response.json(); })
        .then(function(data){
            if(data.found){
                var cc = document.getElementById('company_code');
                var cn = document.getElementById('company_name');
                var fy = document.getElementById('fy');
                var pc = document.getElementById('project_cost');
                if(cc) cc.value = data.company_code || '';
                if(cn) cn.value = data.company_name || '';
                if(fy) fy.value = data.fy || '';
                if(pc) pc.value = data.project_cost || '';
            } else {
                alert('Project ID not found. Please add it first from Menu > Project Data Entry.');
            }
        })
        .catch(function(error){ console.log('Project lookup failed:', error); });
}

function fetchSchoolByUdisc() {
    var udisc = document.getElementById('udisc');
    var schoolCodeInput = document.getElementById('school_code');
    var msg = document.getElementById('school_lookup_message');
    if (!udisc || !schoolCodeInput || !msg) return;

    schoolCodeInput.value = "";
    msg.innerText = "";

    if (!udisc.value.trim()) return;

    fetch('/get-school-by-udisc/' + encodeURIComponent(udisc.value.trim()))
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.found) {
                schoolCodeInput.value = data.school_code || "";
                msg.innerText = "School_Name: " + (data.school_name || "");
                msg.style.color = "#1b5e20";
            } else {
                msg.innerText = "No school record found for this UDISC Number. Please enter school data first.";
                msg.style.color = "#b71c1c";
            }
        })
        .catch(function(error) {
            msg.innerText = "Unable to fetch school details.";
            msg.style.color = "#b71c1c";
        });
}
</script>
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card"><h2>{{ project.project_name }} - Image Upload</h2>
{% if project.slug == 'education' %}
<p class="page-note">Folder will be created as Project ID_UDISC Number_School Code. You can upload multiple images for Smart Class, RO, Sanitary, Toilet and Other Photos.</p>
<form method="post" enctype="multipart/form-data"><div class="form-grid">
<input type="hidden" name="project_slug" value="education">
<div class="form-group"><label>Project Area</label><input value="Education" readonly></div>
<div class="form-group"><label>Project ID</label><input id="project_id" name="project_id" value="{{ project.project_id or '' }}" onblur="fetchProjectInfo()" required></div>
<div class="form-group"><label>UDISC Number</label><input name="udisc" id="udisc" required onblur="fetchSchoolByUdisc()"></div>
<div class="form-group"><label>School Code</label><input name="school_code" id="school_code" readonly required></div>
<div class="form-group full"><p id="school_lookup_message" style="margin:0; color:#1b5e20; font-weight:bold;"></p></div>
<div class="form-group full"><label>Smart Class Photos</label><input type="file" name="smart_class" accept="image/png,image/jpeg" multiple></div>
<div class="form-group full"><label>RO Photos</label><input type="file" name="ro" accept="image/png,image/jpeg" multiple></div>
<div class="form-group full"><label>Sanitary Photos</label><input type="file" name="sanitary" accept="image/png,image/jpeg" multiple></div>
<div class="form-group full"><label>Toilet Photos</label><input type="file" name="toilet" accept="image/png,image/jpeg" multiple></div>
<div class="form-group full"><label>Other Photos</label><input type="file" name="other_photos" accept="image/png,image/jpeg" multiple></div>
</div><button type="submit">Upload Images</button></form>
{% else %}
<p class="page-note">Folder will be created as Project ID_Company Code.</p>
<form method="post" enctype="multipart/form-data"><div class="form-grid">
<input type="hidden" name="project_slug" value="{{ project.slug }}">
<div class="form-group"><label>Project Area</label><input value="{{ project.project_name }}" readonly></div>
<div class="form-group"><label>Project ID</label><input id="project_id" name="project_id" value="{{ project.project_id or '' }}" onblur="fetchProjectInfo()" required></div>
<div class="form-group"><label>Project Title</label><input value="{{ project.project_title or '' }}" readonly></div>
<div class="form-group"><label>Company Code</label><input id="company_code" name="company_code" value="{{ project.company_code or '' }}" readonly required></div>
<div class="form-group"><label>Company Name</label><input id="company_name" readonly></div>
<div class="form-group"><label>FY</label><input id="fy" readonly></div>
<div class="form-group"><label>Project Cost</label><input id="project_cost" readonly></div>
<div class="form-group full"><label>Upload Photos / Files</label><input type="file" name="project_files" accept="image/png,image/jpeg,application/pdf,.doc,.docx,.xls,.xlsx" multiple required></div>
</div><button type="submit">Upload Files</button></form>
{% endif %}
{% if success %}<p class="success">{{ upload_count }} file(s) uploaded to Google Drive ✅</p>{% endif %}</div></div></body></html>
"""

RECORDS_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card" style="max-width:1200px;"><h2>Saved School Records</h2><div class="toolbar"><input id="recordSearch" class="search-box" onkeyup="filterRecordsTable()" placeholder="Search by UDISC, School Code, Name, FY..."><span class="badge">Total Records: {{ records|length }}</span></div><div class="table-wrap"><table id="recordsTable">
<thead><tr><th>ID</th><th>Project</th><th>UDISC</th><th>School Code</th>
<th>School_Name</th><th>Location</th><th>Year</th><th>Girls</th><th>Boys</th><th>Total</th><th>Company</th><th>FY</th><th>Phase</th><th>Remarks</th><th>Created</th><th>Google Drive Folder</th><th>Action</th></tr></thead>
<tbody>{% for row in records %}<tr><td>{{ loop.index }}</td><td>{{ row.project_slug or "education" }}</td><td>{{ row.udisc_number }}</td><td>{{ row.school_code }}</td>
<td>{{ row.school_name }}</td><td>{{ row.location }}</td><td>{{ row.year }}</td><td>{{ row.girls }}</td><td>{{ row.boys }}</td><td>{{ row.total_students }}</td><td>{{ row.company_name }}</td><td>{{ row.fy }}</td><td>{{ row.phase }}</td><td>{{ row.remarks }}</td><td>{{ row.created_at }}</td>
<td>
{% if row.drive_folder_link %}
<a class="action-link edit-link" href="{{ row.drive_folder_link }}" target="_blank">Open Folder</a>
{% else %}
N/A
{% endif %}
</td>
<td>
<a class="action-link edit-link" href="/edit-record/{{ row.id }}">Edit</a>
<form class="inline-form" method="POST" action="/delete-record/{{ row.id }}" onsubmit="return confirm('Delete this record?');">
<button class="inline-button" type="submit">Delete</button>
</form>
</td></tr>{% endfor %}</tbody>
</table></div></div></div></body></html>
"""

UPLOAD_RECORDS_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card" style="max-width:1200px;"><h2>{{ project_name }} Upload Records</h2><div class="toolbar"><input id="recordSearch" class="search-box" onkeyup="filterRecordsTable()" placeholder="Search by Project ID, Company Code, File Name..."><span class="badge">Total Uploads: {{ records|length }}</span></div><div class="table-wrap"><table id="recordsTable">
<thead><tr><th>ID</th><th>Project</th><th>Project ID</th><th>Company Code / School Code</th><th>Category</th><th>File Name</th><th>Uploaded</th><th>Google Drive File</th><th>Action</th></tr></thead>
<tbody>{% for row in records %}<tr><td>{{ loop.index }}</td><td>{{ row.project_slug }}</td><td>{{ row.udisc_number }}</td><td>{{ row.school_code }}</td><td>{{ row.category }}</td><td>{{ row.original_filename }}</td><td>{{ row.uploaded_at }}</td><td>{% if row.drive_web_link %}<a class="action-link edit-link" href="{{ row.drive_web_link }}" target="_blank">Open File</a>{% else %}N/A{% endif %}</td><td><a class="action-link edit-link" href="/edit-upload-record/{{ row.id }}">Edit</a><form class="inline-form" method="POST" action="/delete-upload-record/{{ row.id }}" onsubmit="return confirm('Delete this upload record? This will remove the database entry only.');"><button class="inline-button" type="submit">Delete</button></form></td></tr>{% endfor %}</tbody>
</table></div></div></div></body></html>
"""



EDIT_PROJECT_INFO_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card"><h2>Edit Project Data Entry</h2>
<form method="post"><div class="form-grid">
<div class="form-group"><label>Project ID</label><input name="project_id" value="{{ record.project_id }}" required></div>
<div class="form-group"><label>Company Code</label><input name="company_code" value="{{ record.company_code }}" required></div>
<div class="form-group"><label>Company Name</label><input name="company_name" value="{{ record.company_name }}" required></div>
<div class="form-group"><label>Project Cost</label><input name="project_cost" type="number" step="0.01" value="{{ record.project_cost }}" required></div>
<div class="form-group"><label>FY</label><input name="fy" value="{{ record.fy }}" required></div>
</div><button type="submit">Update Project Data</button></form>
<a class="menu-button secondary" href="/project-data-entry">Back to Project Data Entry</a>
</div></div></body></html>
"""

EDIT_UPLOAD_RECORD_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card"><h2>Edit Upload Record</h2>
<form method="post"><div class="form-grid">
<div class="form-group"><label>Project Area</label><input name="project_slug" value="{{ record.project_slug }}" readonly></div>
<div class="form-group"><label>Project ID</label><input name="udisc_number" value="{{ record.udisc_number }}" required></div>
<div class="form-group"><label>Company Code / School Code</label><input name="school_code" value="{{ record.school_code }}" required></div>
<div class="form-group"><label>Category</label><input name="category" value="{{ record.category }}" required></div>
<div class="form-group full"><label>File Name</label><input name="original_filename" value="{{ record.original_filename }}" required></div>
</div><button type="submit">Update Upload Record</button></form>
<a class="menu-button secondary" href="/upload-records?project={{ record.project_slug }}">Back to Upload Records</a>
</div></div></body></html>
"""


EDIT_RECORD_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
<script>function calculateTotal(){var boys=parseInt(document.getElementById('boys').value)||0;var girls=parseInt(document.getElementById('girls').value)||0;document.getElementById('total').value=boys+girls;}</script>

<script>
function validateEditSchoolCode(){
    var schoolCodeInput = document.getElementById('school_code');
    if (!schoolCodeInput) return;

    var schoolCode = schoolCodeInput.value.trim();
    var originalSchoolCode = "{{ record.school_code }}";

    if (!schoolCode || schoolCode === originalSchoolCode) return;

    fetch('/check-school-code/' + encodeURIComponent(schoolCode))
        .then(function(response){ return response.json(); })
        .then(function(data){
            if(data.exists){
                alert('Duplicate School Code detected. Please enter a unique School Code.');
                schoolCodeInput.value = originalSchoolCode;
                schoolCodeInput.focus();
            }
        })
        .catch(function(error){
            console.log('School Code validation failed:', error);
        });
}
</script>

</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card"><h2>Edit School Record</h2><form method="post"><div class="form-grid">
<div class="form-group"><label>UDISC Number</label><input name="udisc" value="{{ record.udisc_number }}" required></div>
<div class="form-group"><label>School Code</label><input id="school_code" name="school_code" value="{{ record.school_code }}" required onblur="validateEditSchoolCode()"></div>
<div class="form-group"><label>School_Name</label><input name="school_name" value="{{ record.school_name }}" required></div>
<div class="form-group"><label>Location</label><input name="location" value="{{ record.location }}"></div>
<div class="form-group"><label>Year of Establishment</label><input name="year" value="{{ record.year }}"></div>
<div class="form-group"><label>Girls</label><input id="girls" name="girls" value="{{ record.girls }}" onkeyup="calculateTotal()"></div>
<div class="form-group"><label>Boys</label><input id="boys" name="boys" value="{{ record.boys }}" onkeyup="calculateTotal()"></div>
<div class="form-group"><label>Total Students</label><input id="total" name="total" value="{{ record.total_students }}" readonly></div>
<div class="form-group"><label>Company Name</label><input name="company" value="{{ record.company_name }}"></div>
<div class="form-group"><label>FY</label><input name="fy" value="{{ record.fy }}"></div>
<div class="form-group"><label>Phase</label><select name="phase">
<option {% if record.phase == '1st Phase' %}selected{% endif %}>1st Phase</option>
<option {% if record.phase == '2nd Phase' %}selected{% endif %}>2nd Phase</option>
<option {% if record.phase == '3rd Phase' %}selected{% endif %}>3rd Phase</option>
<option {% if record.phase == '4th Phase' %}selected{% endif %}>4th Phase</option>
</select></div>
<div class="form-group full"><label>Remarks</label><textarea name="remarks">{{ record.remarks }}</textarea></div>
</div><button type="submit">Update Record</button></form></div></div></body></html>
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS project_master (
            id SERIAL PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            project_name TEXT NOT NULL,
            project_id TEXT,
            project_title TEXT,
            company_code TEXT,
            about_project TEXT,
            company_name TEXT,
            fy TEXT,
            project_cost NUMERIC DEFAULT 0,
            status TEXT DEFAULT 'Planning',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS project_info (
            id SERIAL PRIMARY KEY,
            project_id TEXT UNIQUE NOT NULL,
            company_code TEXT,
            company_name TEXT,
            project_cost NUMERIC DEFAULT 0,
            fy TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            code_verifier TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("ALTER TABLE school_records ADD COLUMN IF NOT EXISTS school_code TEXT")
    cur.execute("ALTER TABLE school_records ADD COLUMN IF NOT EXISTS school_name TEXT")
    cur.execute("ALTER TABLE school_records ADD COLUMN IF NOT EXISTS project_slug TEXT")
    cur.execute("ALTER TABLE school_records ADD COLUMN IF NOT EXISTS project_id TEXT")
    cur.execute("ALTER TABLE school_records ADD COLUMN IF NOT EXISTS company_code TEXT")
    cur.execute("ALTER TABLE school_records ADD COLUMN IF NOT EXISTS project_cost TEXT")
    cur.execute("ALTER TABLE image_uploads ADD COLUMN IF NOT EXISTS school_code TEXT")
    cur.execute("ALTER TABLE image_uploads ADD COLUMN IF NOT EXISTS school_name TEXT")
    cur.execute("ALTER TABLE image_uploads ADD COLUMN IF NOT EXISTS project_slug TEXT")
    cur.execute("ALTER TABLE project_master ADD COLUMN IF NOT EXISTS project_id TEXT")
    cur.execute("ALTER TABLE project_master ADD COLUMN IF NOT EXISTS project_title TEXT")
    cur.execute("ALTER TABLE project_master ADD COLUMN IF NOT EXISTS company_code TEXT")

    for project in PROJECT_MASTER_LIST:
        cur.execute("""
            INSERT INTO project_master (slug, project_name)
            VALUES (%s, %s)
            ON CONFLICT (slug) DO NOTHING
        """, (project["slug"], project["name"]))

    conn.commit()
    cur.close()
    conn.close()


def save_school_to_db(data):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO school_records (
            udisc_number, school_code, school_name, location, year, girls, boys, total_students,
            company_name, fy, phase, remarks, project_slug, project_id, company_code, project_cost
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["UDISC Number"], data["School Code"], data["School_Name"], data["Location"], data["Year"],
        data["Girls"], data["Boys"], data["Total Students"], data["Company Name"],
        data["FY"], data["Phase"], data["Remarks"], data.get("Project Slug", "education"),
        data.get("Project ID", ""), data.get("Company Code", ""), data.get("Project Cost", "")
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
            udisc_number, school_code, school_name, category, original_filename,
            drive_file_id, drive_file_name, drive_folder_id, drive_web_link, project_slug
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["udisc_number"], data["school_code"], data["school_name"], data["category"],
        data["original_filename"], data["drive_file_id"], data["drive_file_name"],
        data["drive_folder_id"], data["drive_web_link"], data.get("project_slug", "education")
    ))
    conn.commit()
    cur.close()
    conn.close()




def get_project_master(slug):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, slug, project_name, project_id, project_title, company_code, about_project, company_name, fy, project_cost, status, created_at, updated_at
        FROM project_master
        WHERE slug = %s
    """, (slug,))
    project = cur.fetchone()
    cur.close()
    conn.close()
    return project


def get_all_project_master():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, slug, project_name, project_id, project_title, company_code, about_project, company_name, fy, project_cost, status, created_at, updated_at
        FROM project_master
        ORDER BY id ASC
    """)
    projects = cur.fetchall()
    cur.close()
    conn.close()
    return projects


def update_project_master(slug, data):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE project_master
        SET project_id = %s,
            project_title = %s,
            company_code = %s,
            about_project = %s,
            company_name = %s,
            fy = %s,
            project_cost = %s,
            status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE slug = %s
    """, (
        data.get("project_id", ""),
        data.get("project_title", ""),
        data.get("company_code", ""),
        data.get("about_project", ""),
        data.get("company_name", ""),
        data.get("fy", ""),
        data.get("project_cost") or 0,
        data.get("status", "Planning"),
        slug
    ))
    conn.commit()
    cur.close()
    conn.close()


def get_project_stats(slug):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) AS total_records FROM school_records WHERE project_slug = %s", (slug,))
    record_count = cur.fetchone()["total_records"]
    cur.execute("SELECT COUNT(*) AS total_uploads FROM image_uploads WHERE project_slug = %s", (slug,))
    upload_count = cur.fetchone()["total_uploads"]
    cur.close()
    conn.close()
    return {"total_records": record_count, "total_uploads": upload_count}




def save_project_info(data):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO project_info (project_id, company_code, company_name, project_cost, fy)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (project_id) DO UPDATE SET
            company_code = EXCLUDED.company_code,
            company_name = EXCLUDED.company_name,
            project_cost = EXCLUDED.project_cost,
            fy = EXCLUDED.fy,
            updated_at = CURRENT_TIMESTAMP
    """, (
        data.get("project_id", "").strip(),
        data.get("company_code", "").strip(),
        data.get("company_name", "").strip(),
        data.get("project_cost") or 0,
        data.get("fy", "").strip()
    ))
    conn.commit()
    cur.close()
    conn.close()


def get_project_info_by_id(project_id):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, project_id, company_code, company_name, project_cost, fy, created_at, updated_at
        FROM project_info
        WHERE project_id = %s
        LIMIT 1
    """, (project_id,))
    record = cur.fetchone()
    cur.close()
    conn.close()
    return record


def get_project_info_records():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, project_id, company_code, company_name, project_cost, fy, created_at, updated_at
        FROM project_info
        ORDER BY id DESC
    """)
    records = cur.fetchall()
    cur.close()
    conn.close()
    return records




def get_project_info_record_by_id(record_id):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, project_id, company_code, company_name, project_cost, fy, created_at, updated_at
        FROM project_info
        WHERE id = %s
    """, (record_id,))
    record = cur.fetchone()
    cur.close()
    conn.close()
    return record


def update_project_info_record(record_id, data):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE project_info
        SET project_id = %s,
            company_code = %s,
            company_name = %s,
            project_cost = %s,
            fy = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (
        data.get("project_id", "").strip(),
        data.get("company_code", "").strip(),
        data.get("company_name", "").strip(),
        data.get("project_cost") or 0,
        data.get("fy", "").strip(),
        record_id
    ))
    conn.commit()
    cur.close()
    conn.close()


def delete_project_info_record(record_id):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM project_info WHERE id = %s", (record_id,))
    conn.commit()
    cur.close()
    conn.close()

def school_code_exists(school_code, exclude_id=None):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()

    if exclude_id:
        cur.execute(
            "SELECT 1 FROM school_records WHERE school_code = %s AND id != %s LIMIT 1",
            (school_code, exclude_id)
        )
    else:
        cur.execute(
            "SELECT 1 FROM school_records WHERE school_code = %s LIMIT 1",
            (school_code,)
        )

    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists


def get_school_by_udisc(udisc_number):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, udisc_number, school_code, school_name
        FROM school_records
        WHERE udisc_number = %s
        ORDER BY id DESC
        LIMIT 1
    """, (udisc_number,))
    record = cur.fetchone()
    cur.close()
    conn.close()
    return record


def get_school_record_by_id(record_id):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, udisc_number, school_code, school_name, location, year, girls, boys,
               total_students, company_name, fy, phase, remarks, project_slug, created_at
        FROM school_records
        WHERE id = %s
    """, (record_id,))
    record = cur.fetchone()
    cur.close()
    conn.close()
    return record


def update_school_record(record_id, data):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE school_records
        SET
            udisc_number = %s,
            school_code = %s,
            school_name = %s,
            location = %s,
            year = %s,
            girls = %s,
            boys = %s,
            total_students = %s,
            company_name = %s,
            fy = %s,
            phase = %s,
            remarks = %s
        WHERE id = %s
    """, (
        data["UDISC Number"],
        data["School Code"],
        data["School_Name"],
        data["Location"],
        data["Year"],
        data["Girls"],
        data["Boys"],
        data["Total Students"],
        data["Company Name"],
        data["FY"],
        data["Phase"],
        data["Remarks"],
        record_id
    ))
    conn.commit()
    cur.close()
    conn.close()


def delete_school_record(record_id):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM school_records WHERE id = %s", (record_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_school_records(project_slug=None):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if project_slug:
        cur.execute("""
            SELECT id, udisc_number, school_code, school_name, location, year, girls, boys,
                   total_students, company_name, fy, phase, remarks, project_slug, created_at
            FROM school_records
            WHERE project_slug = %s
            ORDER BY id DESC
        """, (project_slug,))
    else:
        cur.execute("""
            SELECT id, udisc_number, school_code, school_name, location, year, girls, boys,
                   total_students, company_name, fy, phase, remarks, project_slug, created_at
            FROM school_records
            ORDER BY id DESC
        """)
    records = cur.fetchall()
    cur.close()
    conn.close()
    return records

def get_upload_records(project_slug=None):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if project_slug:
        cur.execute("""
            SELECT id, udisc_number, school_code, school_name, category, original_filename,
                   drive_file_id, drive_file_name, drive_folder_id, drive_web_link, project_slug, uploaded_at
            FROM image_uploads
            WHERE project_slug = %s
            ORDER BY id DESC
        """, (project_slug,))
    else:
        cur.execute("""
            SELECT id, udisc_number, school_code, school_name, category, original_filename,
                   drive_file_id, drive_file_name, drive_folder_id, drive_web_link, project_slug, uploaded_at
            FROM image_uploads
            ORDER BY id DESC
        """)
    records = cur.fetchall()
    cur.close()
    conn.close()
    return records



def get_upload_record_by_id(record_id):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, udisc_number, school_code, school_name, category, original_filename,
               drive_file_id, drive_file_name, drive_folder_id, drive_web_link, project_slug, uploaded_at
        FROM image_uploads
        WHERE id = %s
    """, (record_id,))
    record = cur.fetchone()
    cur.close()
    conn.close()
    return record


def update_upload_record(record_id, data):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE image_uploads
        SET udisc_number = %s,
            school_code = %s,
            category = %s,
            original_filename = %s
        WHERE id = %s
    """, (
        data.get("udisc_number", "").strip(),
        data.get("school_code", "").strip(),
        data.get("category", "").strip(),
        data.get("original_filename", "").strip(),
        record_id
    ))
    conn.commit()
    cur.close()
    conn.close()


def delete_upload_record(record_id):
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM image_uploads WHERE id = %s", (record_id,))
    conn.commit()
    cur.close()
    conn.close()


# ========================
# OAUTH STATE / PKCE HELPERS
# ========================

def save_oauth_state(state, code_verifier):
    """Store Google OAuth PKCE code_verifier outside Flask session so Render redirects do not break authorization."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            code_verifier TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        INSERT INTO oauth_states (state, code_verifier)
        VALUES (%s, %s)
        ON CONFLICT (state) DO UPDATE SET code_verifier = EXCLUDED.code_verifier, created_at = CURRENT_TIMESTAMP
    """, (state, code_verifier))
    conn.commit()
    cur.close()
    conn.close()


def get_oauth_code_verifier(state):
    if not state:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT code_verifier FROM oauth_states WHERE state = %s", (state,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def delete_oauth_state(state):
    if not state:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM oauth_states WHERE state = %s", (state,))
    conn.commit()
    cur.close()
    conn.close()

# ========================
# GOOGLE DRIVE OAUTH HELPERS
# ========================

def normalize_token_json(token_json):
    if not token_json:
        return None
    try:
        if isinstance(token_json, dict):
            return token_json
        token_json = str(token_json).strip()
        # Render sometimes stores copied values with surrounding quotes or spaces.
        if (token_json.startswith("'") and token_json.endswith("'")) or (token_json.startswith('"') and token_json.endswith('"')):
            try:
                token_json = json.loads(token_json)
            except Exception:
                token_json = token_json[1:-1]
        return json.loads(token_json)
    except Exception as e:
        print("❌ GOOGLE_TOKEN_JSON parse error:", str(e))
        return None


def ensure_google_token_table():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS google_oauth_tokens (
                id INTEGER PRIMARY KEY,
                token_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print("❌ GOOGLE TOKEN TABLE ERROR:", repr(e))
        return False


def save_token_to_db(token_data):
    try:
        if not ensure_google_token_table():
            return False
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO google_oauth_tokens (id, token_json, updated_at)
            VALUES (1, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                token_json = EXCLUDED.token_json,
                updated_at = CURRENT_TIMESTAMP
        """, (json.dumps(token_data),))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print("❌ SAVE GOOGLE TOKEN TO DB ERROR:", repr(e))
        return False


def load_token_from_db():
    try:
        if not ensure_google_token_table():
            return None
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT token_json FROM google_oauth_tokens WHERE id = 1 LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            return normalize_token_json(row[0])
    except Exception as e:
        print("❌ LOAD GOOGLE TOKEN FROM DB ERROR:", repr(e))
    return None


def save_token(creds):
    token_data = json.loads(creds.to_json())
    # Keep existing local token file behavior for local development.
    try:
        with open(TOKEN_FILE, "w") as token_file:
            json.dump(token_data, token_file)
    except Exception as e:
        print("⚠ Could not save local token file:", repr(e))
    # New Render-safe behavior: save token in Supabase/PostgreSQL so it survives redeploys.
    save_token_to_db(token_data)
    return token_data


def load_token():
    # Priority 1: Render environment variable, if already configured.
    token_data = normalize_token_json(os.environ.get("GOOGLE_TOKEN_JSON"))
    if token_data:
        return token_data

    # Priority 2: Supabase/PostgreSQL token saved after /authorize.
    token_data = load_token_from_db()
    if token_data:
        return token_data

    # Priority 3: Local token file, useful while testing on local machine.
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as token_file:
                return json.load(token_file)
        except Exception as e:
            print("❌ LOCAL TOKEN FILE READ ERROR:", repr(e))
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



def build_school_drive_folder_name(udisc_number, school_code):
    safe_udisc = secure_filename(str(udisc_number).strip())
    safe_school_code = secure_filename(str(school_code).strip())
    return f"{safe_udisc}_{safe_school_code}"


def build_education_drive_folder_name(project_id, udisc_number, school_code):
    safe_project_id = secure_filename(str(project_id).strip())
    safe_udisc = secure_filename(str(udisc_number).strip())
    safe_school_code = secure_filename(str(school_code).strip())
    return f"{safe_project_id}_{safe_udisc}_{safe_school_code}"


def build_other_project_drive_folder_name(project_id, company_code):
    safe_project_id = secure_filename(str(project_id).strip())
    safe_company_code = secure_filename(str(company_code).strip())
    return f"{safe_project_id}_{safe_company_code}"


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


def get_drive_folder_link_by_name(folder_name, parent_id):
    global drive_service

    if not drive_service:
        drive_service = get_drive_service()

    if not drive_service:
        return None

    try:
        safe_name = escape_drive_query(folder_name)

        query = (
            f"name='{safe_name}' and "
            f"'{parent_id}' in parents and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        )

        response = drive_service.files().list(
            q=query,
            fields='files(id, name, webViewLink)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = response.get("files", [])

        if not files:
            return None

        folder = files[0]

        return folder.get("webViewLink") or f"https://drive.google.com/drive/folders/{folder.get('id')}"

    except Exception as e:
        print("❌ DRIVE FOLDER LINK LOOKUP ERROR:", repr(e))
        return None


def add_drive_folder_links_to_records(records):
    updated_records = []

    for record in records:
        record_dict = dict(record)

        udisc_number = record_dict.get("udisc_number") or ""
        school_code = record_dict.get("school_code") or ""
        project_slug = record_dict.get("project_slug") or "education"

        record_dict["drive_folder_link"] = None
        if udisc_number and school_code:
            if project_slug == "education":
                project = get_project_master("education")
                project_id = (project or {}).get("project_id") or ""
                if project_id:
                    folder_name = build_education_drive_folder_name(project_id, udisc_number, school_code)
                    record_dict["drive_folder_link"] = get_drive_folder_link_by_name(folder_name, PARENT_FOLDER_ID)
                if not record_dict["drive_folder_link"]:
                    old_folder_name = build_school_drive_folder_name(udisc_number, school_code)
                    record_dict["drive_folder_link"] = get_drive_folder_link_by_name(old_folder_name, PARENT_FOLDER_ID)
            else:
                folder_name = build_other_project_drive_folder_name(udisc_number, school_code)
                record_dict["drive_folder_link"] = get_drive_folder_link_by_name(folder_name, PARENT_FOLDER_ID)

        updated_records.append(record_dict)

    return updated_records


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

        # Robust PKCE OAuth flow:
        # Google may require a code_verifier. We store it in Supabase by state instead
        # of relying only on Flask session, because Render/browser redirects can lose session data.
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
        if getattr(flow, "code_verifier", None):
            save_oauth_state(state, flow.code_verifier)

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
        state = request.args.get('state') or session.get('state')
        code_verifier = get_oauth_code_verifier(state)

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=state,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )

        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        token_data = save_token(creds)
        delete_oauth_state(state)
        drive_service = get_drive_service()

        return render_template_string(OAUTH_CALLBACK_TEMPLATE, token_json=json.dumps(token_data))

    except Exception as e:
        return f"❌ OAuth Callback Error: {str(e)}"


OAUTH_STATUS_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card" style="max-width:760px;">
<h2>Google Drive OAuth Status</h2>
{% if connected %}
<p class="success">✅ Google Drive OAuth is connected successfully.</p>
<a class="menu-button" href="/menu">Back to Menu</a>
{% else %}
<p class="error">❌ Google Drive OAuth is not connected.</p>
<div class="page-note" style="text-align:left;">
Please click the button below and complete Google authorization. After authorization, the token will be saved automatically in Supabase/PostgreSQL and the app can use Google Drive without changing the existing app content.
</div>
<a class="menu-button" href="/authorize">Authorize Google Drive</a>
<a class="menu-button secondary" href="/menu">Back to Menu</a>
{% endif %}
</div></div></body></html>
"""

OAUTH_CALLBACK_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
""" + BASE_STYLE + """
</head><body>
""" + HEADER_HTML + """
<div class="container"><div class="form-card" style="max-width:900px;">
<h2>Google Drive OAuth Connected</h2>
<p class="success">✅ Google Drive OAuth connected successfully.</p>
<div class="page-note" style="text-align:left;">
Your token has been saved securely in Supabase/PostgreSQL. You do not need to copy it into Render unless you want to keep GOOGLE_TOKEN_JSON as a backup.
</div>
<label>GOOGLE_TOKEN_JSON</label>
<textarea readonly style="width:100%;height:260px;margin-top:10px;font-family:monospace;">{{ token_json }}</textarea>
<a class="menu-button" href="/oauth-status">Check OAuth Status</a>
<a class="menu-button secondary" href="/menu">Back to Menu</a>
</div></div></body></html>
"""

@app.route('/oauth-status')
def oauth_status():
    global drive_service
    drive_service = get_drive_service()
    connected = drive_service is not None
    return render_template_string(OAUTH_STATUS_TEMPLATE, connected=connected)

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
    return render_template_string(MENU_TEMPLATE, projects=PROJECT_MASTER_LIST)


@app.route('/projects')
def projects():
    if 'user' not in session:
        return redirect('/')
    return render_template_string(PROJECTS_TEMPLATE, projects=PROJECT_MASTER_LIST)


@app.route('/project/<slug>', methods=['GET', 'POST'])
def project_master(slug):
    if 'user' not in session:
        return redirect('/')

    allowed_slugs = [project["slug"] for project in PROJECT_MASTER_LIST]
    if slug not in allowed_slugs:
        return "Project not found"

    success = False
    try:
        init_db()
        if request.method == 'POST':
            update_project_master(slug, {
                "project_id": request.form.get("project_id", ""),
                "project_title": request.form.get("project_title", ""),
                "company_code": request.form.get("company_code", ""),
                "about_project": request.form.get("about_project", ""),
                "company_name": request.form.get("company_name", ""),
                "fy": request.form.get("fy", ""),
                "project_cost": request.form.get("project_cost", 0),
                "status": request.form.get("status", "Planning")
            })
            success = True

        project = get_project_master(slug)
        stats = get_project_stats(slug)
        return render_template_string(PROJECT_MASTER_TEMPLATE, project=project, stats=stats, success=success)

    except Exception as e:
        error_text = traceback.format_exc()
        print("PROJECT MASTER ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/project-data-entry', methods=['GET', 'POST'])
def project_data_entry():
    if 'user' not in session:
        return redirect('/')
    success = False
    try:
        if request.method == 'POST':
            project_id = request.form.get('project_id', '').strip()
            if not project_id:
                return "Project ID is required"
            save_project_info({
                "project_id": project_id,
                "company_code": request.form.get('company_code', ''),
                "company_name": request.form.get('company_name', ''),
                "project_cost": request.form.get('project_cost', 0),
                "fy": request.form.get('fy', '')
            })
            success = True
        records = get_project_info_records()
        return render_template_string(PROJECT_INFO_TEMPLATE, records=records, success=success)
    except Exception as e:
        error_text = traceback.format_exc()
        print("PROJECT DATA ENTRY ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/edit-project-info/<int:record_id>', methods=['GET', 'POST'])
def edit_project_info(record_id):
    if 'user' not in session:
        return redirect('/')
    try:
        record = get_project_info_record_by_id(record_id)
        if not record:
            return "Project data entry not found"
        if request.method == 'POST':
            project_id = request.form.get('project_id', '').strip()
            if not project_id:
                return "Project ID is required"
            update_project_info_record(record_id, {
                "project_id": project_id,
                "company_code": request.form.get('company_code', ''),
                "company_name": request.form.get('company_name', ''),
                "project_cost": request.form.get('project_cost', 0),
                "fy": request.form.get('fy', '')
            })
            return redirect('/project-data-entry')
        return render_template_string(EDIT_PROJECT_INFO_TEMPLATE, record=record)
    except Exception as e:
        error_text = traceback.format_exc()
        print("EDIT PROJECT INFO ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/delete-project-info/<int:record_id>', methods=['POST'])
def delete_project_info(record_id):
    if 'user' not in session:
        return redirect('/')
    try:
        delete_project_info_record(record_id)
        return redirect('/project-data-entry')
    except Exception as e:
        error_text = traceback.format_exc()
        print("DELETE PROJECT INFO ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/get-project-info/<path:project_id>')
def get_project_info_route(project_id):
    if 'user' not in session:
        return {"found": False, "error": "Not logged in"}
    try:
        record = get_project_info_by_id(project_id.strip())
        if not record:
            return {"found": False}
        return {
            "found": True,
            "project_id": record.get("project_id") or "",
            "company_code": record.get("company_code") or "",
            "company_name": record.get("company_name") or "",
            "project_cost": str(record.get("project_cost") or ""),
            "fy": record.get("fy") or ""
        }
    except Exception as e:
        print("PROJECT INFO LOOKUP ERROR:")
        print(traceback.format_exc())
        return {"found": False, "error": str(e)}


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
            if not school_code:
                return "School code is required"

            if school_code_exists(school_code):
                return "<script>alert('Duplicate School Code detected. Please enter a unique School Code.');window.history.back();</script>"

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
                "Company Code": request.form.get('company_code', ''),
                "Project ID": request.form.get('project_id', ''),
                "Project Cost": request.form.get('project_cost', ''),
                "FY": request.form.get('fy', ''),
                "Phase": request.form.get('phase', ''),
                "Remarks": request.form.get('remarks', ''),
                "Project Slug": request.form.get('project_slug', 'education')
            }
            save_school_to_db(data)
            success = True
        except Exception as e:
            error_text = traceback.format_exc()
            print("SCHOOL ENTRY ERROR:")
            print(error_text)
            return f"<pre>Error occurred:\n{error_text}</pre>"
    selected_project = request.args.get('project', 'education')
    project_master_data = get_project_master('education')
    return render_template_string(SCHOOL_ENTRY_TEMPLATE, success=success, projects=PROJECT_MASTER_LIST, selected_project=selected_project, project_master=project_master_data)


@app.route('/get-school-by-udisc/<udisc_number>')
def get_school_by_udisc_route(udisc_number):
    if 'user' not in session:
        return {"found": False, "error": "Not logged in"}

    try:
        record = get_school_by_udisc(udisc_number)

        if not record:
            return {"found": False}

        return {
            "found": True,
            "school_code": record.get("school_code") or "",
            "school_name": record.get("school_name") or ""
        }

    except Exception as e:
        print("UDISC LOOKUP ERROR:")
        print(traceback.format_exc())
        return {"found": False, "error": str(e)}



@app.route('/check-school-code/<path:school_code>')
def check_school_code(school_code):
    if 'user' not in session:
        return {"exists": False}

    try:
        school_code = school_code.strip()

        if not school_code:
            return {"exists": False}

        exists = school_code_exists(school_code)
        return {"exists": exists}

    except Exception as e:
        print("SCHOOL CODE CHECK ERROR:")
        print(traceback.format_exc())
        return {"exists": False, "error": str(e)}


# ========================
# IMAGE UPLOAD
# ========================

@app.route('/image-upload', methods=['GET', 'POST'])
def image_upload():
    if 'user' not in session:
        return redirect('/')
    success = False
    selected_project = request.args.get('project', request.form.get('project_slug', 'education'))
    project = get_project_master(selected_project)
    if not project:
        return "Project not found"
    if request.method == 'POST':
        try:
            upload_count = 0
            if selected_project == 'education':
                project_id = (request.form.get('project_id') or project.get('project_id') or '').strip()
                udisc_number = request.form.get('udisc', '').strip()

                if not project_id:
                    return "Project ID is required in Education project master"
                if not udisc_number:
                    return "UDISC number is required"

                school_record = get_school_by_udisc(udisc_number)

                if not school_record:
                    return "No school record found for this UDISC Number. Please enter school data first."

                school_code = (school_record.get("school_code") or "").strip()
                school_name = (school_record.get("school_name") or "").strip()

                if not school_code:
                    return "School code not found in database for this UDISC Number"

                if not school_name:
                    return "School name not found in database for this UDISC Number"

                main_folder_name = build_education_drive_folder_name(project_id, udisc_number, school_code)
                school_folder_id = create_folder(main_folder_name, PARENT_FOLDER_ID)
                if not school_folder_id:
                    return "❌ Failed to create School folder in Google Drive. Open /authorize first."
                folders = {
                    "smart_class": create_folder("Smart_Class", school_folder_id),
                    "ro": create_folder("RO", school_folder_id),
                    "sanitary": create_folder("Sanitary", school_folder_id),
                    "toilet": create_folder("Toilet", school_folder_id),
                    "other_photos": create_folder("Other_Photos", school_folder_id)
                }

                for field, folder_id in folders.items():

                    if not folder_id:
                        print(f"⚠ Skipping {field} folder")
                        continue

                    selected_files = request.files.getlist(field)

                    for file in selected_files:

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
                                "drive_web_link": uploaded_file.get("webViewLink"),
                                "project_slug": selected_project
                            })
            else:
                project_id = (request.form.get('project_id') or project.get('project_id') or '').strip()
                company_code = (request.form.get('company_code') or project.get('company_code') or '').strip()
                if not project_id:
                    return "Project ID is required in project master"
                if not company_code:
                    return "Company Code is required in project master"

                main_folder_name = build_other_project_drive_folder_name(project_id, company_code)
                project_folder_id = create_folder(main_folder_name, PARENT_FOLDER_ID)
                if not project_folder_id:
                    return "❌ Failed to create Project folder in Google Drive. Open /authorize first."

                selected_files = request.files.getlist('project_files')
                for file in selected_files:
                    if file and file.filename:
                        uploaded_file = upload_file(file, project_folder_id)
                        upload_count += 1
                        save_image_to_db({
                            "udisc_number": project_id,
                            "school_code": company_code,
                            "school_name": project.get('project_name') or selected_project,
                            "category": "project_files",
                            "original_filename": file.filename,
                            "drive_file_id": uploaded_file.get("id"),
                            "drive_file_name": uploaded_file.get("name"),
                            "drive_folder_id": project_folder_id,
                            "drive_web_link": uploaded_file.get("webViewLink"),
                            "project_slug": selected_project
                        })

            if upload_count == 0:
                return "No valid files selected."
            success = True
        except Exception as e:
            error_text = traceback.format_exc()
            print("IMAGE UPLOAD ERROR:")
            print(error_text)
            return f"<pre>Error occurred:\n{error_text}</pre>"
    return render_template_string(IMAGE_UPLOAD_TEMPLATE, success=success, upload_count=locals().get("upload_count", 0), project=project)


# ========================
# EDIT / DELETE RECORD
# ========================

@app.route('/edit-record/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    if 'user' not in session:
        return redirect('/')

    try:
        record = get_school_record_by_id(record_id)

        if not record:
            return "Record not found"

        if request.method == 'POST':
            boys = int(request.form.get('boys') or 0)
            girls = int(request.form.get('girls') or 0)

            school_code = request.form.get('school_code', '').strip()
            school_name = request.form.get('school_name', '').strip()
            udisc_number = request.form.get('udisc', '').strip()

            if not school_code:
                return "School code is required"

            if school_code_exists(school_code, record_id):
                return "<script>alert('Duplicate School Code detected. Please enter a unique School Code.');window.history.back();</script>"

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
                "Company Code": request.form.get('company_code', ''),
                "Project ID": request.form.get('project_id', ''),
                "Project Cost": request.form.get('project_cost', ''),
                "FY": request.form.get('fy', ''),
                "Phase": request.form.get('phase', ''),
                "Remarks": request.form.get('remarks', '')
            }

            update_school_record(record_id, data)

            return redirect('/records')

        return render_template_string(EDIT_RECORD_TEMPLATE, record=record)

    except Exception as e:
        error_text = traceback.format_exc()
        print("EDIT RECORD ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/delete-record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    if 'user' not in session:
        return redirect('/')

    try:
        delete_school_record(record_id)
        return redirect('/records')

    except Exception as e:
        error_text = traceback.format_exc()
        print("DELETE RECORD ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


# ========================
# RECORDS / EXPORT
# ========================

@app.route('/records')
def records():
    if 'user' not in session:
        return redirect('/')
    try:
        selected_project = request.args.get('project')
        school_records = get_school_records(selected_project)
        school_records = add_drive_folder_links_to_records(school_records)
        return render_template_string(RECORDS_TEMPLATE, records=school_records)
    except Exception as e:
        error_text = traceback.format_exc()
        print("RECORDS ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/upload-records')
def upload_records():
    if 'user' not in session:
        return redirect('/')
    try:
        selected_project = request.args.get('project')
        uploads = get_upload_records(selected_project)
        project_name = selected_project or "All Projects"
        project = get_project_master(selected_project) if selected_project else None
        if project:
            project_name = project.get('project_name') or project_name
        return render_template_string(UPLOAD_RECORDS_TEMPLATE, records=uploads, project_name=project_name)
    except Exception as e:
        error_text = traceback.format_exc()
        print("UPLOAD RECORDS ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/edit-upload-record/<int:record_id>', methods=['GET', 'POST'])
def edit_upload_record(record_id):
    if 'user' not in session:
        return redirect('/')
    try:
        record = get_upload_record_by_id(record_id)
        if not record:
            return "Upload record not found"
        if request.method == 'POST':
            update_upload_record(record_id, {
                "udisc_number": request.form.get('udisc_number', ''),
                "school_code": request.form.get('school_code', ''),
                "category": request.form.get('category', ''),
                "original_filename": request.form.get('original_filename', '')
            })
            return redirect('/upload-records?project=' + (record.get('project_slug') or ''))
        return render_template_string(EDIT_UPLOAD_RECORD_TEMPLATE, record=record)
    except Exception as e:
        error_text = traceback.format_exc()
        print("EDIT UPLOAD RECORD ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/delete-upload-record/<int:record_id>', methods=['POST'])
def delete_upload_record_route(record_id):
    if 'user' not in session:
        return redirect('/')
    try:
        record = get_upload_record_by_id(record_id)
        project_slug = (record or {}).get('project_slug') or ''
        delete_upload_record(record_id)
        return redirect('/upload-records?project=' + project_slug)
    except Exception as e:
        error_text = traceback.format_exc()
        print("DELETE UPLOAD RECORD ERROR:")
        print(error_text)
        return f"<pre>Error occurred:\n{error_text}</pre>"


@app.route('/export')
def export():
    if 'user' not in session:
        return redirect('/')
    try:
        records = get_school_records()
        records = add_drive_folder_links_to_records(records)
        df = pd.DataFrame(records)

        if not df.empty:
            df["drive_folder_link"] = df["drive_folder_link"].fillna("N/A")
            df.insert(0, "ID", range(1, len(df) + 1))

            rename_map = {
                "project_slug": "Project",
                "udisc_number": "UDISC",
                "school_code": "School Code",
                "school_name": "School_Name",
                "location": "Location",
                "year": "Year",
                "girls": "Girls",
                "boys": "Boys",
                "total_students": "Total",
                "company_name": "Company",
                "fy": "FY",
                "phase": "Phase",
                "remarks": "Remarks",
                "created_at": "Created",
                "drive_folder_link": "Google Drive Folder"
            }

            if "id" in df.columns:
                df = df.drop(columns=["id"])

            df = df.rename(columns=rename_map)

            ordered_columns = [
                "ID",
                "Project",
                "UDISC",
                "School Code",
                "School_Name",
                "Location",
                "Year",
                "Girls",
                "Boys",
                "Total",
                "Company",
                "FY",
                "Phase",
                "Remarks",
                "Created",
                "Google Drive Folder"
            ]

            df = df[[col for col in ordered_columns if col in df.columns]]

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
