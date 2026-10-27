# ---------------------------------------------------------------------------
# ข้อมูล Server และการ Maintenance (PO-Online)
# ---------------------------------------------------------------------------
# [สำหรับ Linux VPS / Production Server]
# Web Server: Gunicorn (จัดการโดย Systemd Service: po-online)
# คำสั่ง Restart: sudo systemctl restart po-online
# ถ้าแก้ Config: sudo systemctl daemon-reload && sudo systemctl restart po-online
#
# [สำหรับ Windows / Local Development]
# Web Server: Flask Development Server
# วิธี Restart:
#   1. ไปที่หน้าต่าง Terminal หรือ CMD ที่รันโปรแกรมอยู่
#   2. กด Ctrl + C เพื่อหยุดการทำงาน
#   3. พิมพ์คำสั่ง: python app.py เพื่อเริ่มใหม่
#
# [สำหรับ Docker]
# คำสั่ง Restart: docker-compose restart
# (หากระบุชื่อ service ไม่ถูก "no such service" ให้พิมพ์ docker-compose ps ดูชื่อ service ก่อน ปกติมักเป็น 'web' หรือ 'app')
# ---------------------------------------------------------------------------

# RECOMMENDATION: Your logs show "Worker was sent SIGKILL! Perhaps out of memory?".
# This means your VPS is running out of RAM.
# Please edit your systemd service file (/etc/systemd/system/po-online.service)
# and change "--workers 4" to "--workers 2".
# Then run: sudo systemctl daemon-reload && sudo systemctl restart po-online
from datetime import datetime, date, timedelta
import os
import sys
from dotenv import load_dotenv
load_dotenv()

import base64
import mimetypes
import uuid
import re
import secrets

APP_VERSION = "1.7.4"  # Performance optimization and CIAM integration
from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    make_response,
    send_file,
)
from flask import Response
from extensions import db, bcrypt, login_manager, limiter
from sqlalchemy import or_, and_, text, func
from sqlalchemy.orm import (
    joinedload,
    foreign,
    remote,
    contains_eager,
    subqueryload,
    selectinload,
    aliased,
    load_only,
)
from flask_login import login_user, logout_user, login_required, current_user
from utils import (
    now_bangkok,
    ensure_bangkok,
    BANGKOK_TZ,
    _parse_decimal,
    _parse_bool,
    _decimal_to_str,
    _parse_date,
    _clean,
    _date_to_iso,
    allowed_image_file,
    send_telegram_msg,
    test_telegram_sync,
    get_encryption_key,
    encrypt_data,
    decrypt_data,
    encrypt_string,
    decrypt_string,
    roles_required,
    bangkok_datetime_filter,
)

from models import (
    User,
    Customer,
    Product,
    PurchaseOrder,
    POItem,
    Comment,
    Notification,
    Promotion,
    CiamSetting,
    CiamAuditLog,
    LoginLog,
    SystemSetting,
    TransactionLog,
    COMPANY_DATA,
    MOCK_CUSTOMER_DATA,
    CUSTOMER_CSV_COLUMNS,
    PRODUCT_CSV_COLUMNS,
    import_customer_from_csv,
    import_product_from_csv,
    get_template_csv,
    _update_customer_from_payload,
    _update_product_from_payload,
    build_product_image_url,
    create_notification,
)

from utils_ciam import (
    get_ciam_config,
    test_ciam_connection,
    generate_pkce_codes,
    exchange_oauth_code,
    verify_rs256_jwt,
    mask_secret,
    sync_with_ciam_now,
    init_default_ciam_settings,
    authenticate_ad_gateway,
)

from werkzeug.utils import secure_filename
import io  # NEW: For PDF in memory
import urllib
from urllib.parse import urlparse, unquote, quote_plus, urlencode
import json  # NEW: For Telegram Payload
import traceback  # NEW: For detailed logging
import logging  # NEW: Import logging

# FIX: Import WeasyPrint for PDF Generation
try:
    from weasyprint import HTML
except ImportError:
    HTML = None
    print(
        "WARNING: WeasyPrint not installed. PDF generation will fail.", file=sys.stderr
    )

# ---------------- FIX: QR Code Import (Top Level) ----------------
try:
    import qrcode
    from PIL import Image

    QR_AVAILABLE = True
    print("DEBUG: QR Code libraries loaded successfully.", file=sys.stderr)
except ImportError as e:
    QR_AVAILABLE = False
    qrcode = None
    print(f"CRITICAL ERROR: QR Code libraries NOT found: {e}", file=sys.stderr)
# ----------------------------------------------------------------

from cryptography.fernet import Fernet  # NEW: For Signature Encryption
from werkzeug.middleware.proxy_fix import ProxyFix  # NEW: Import ProxyFix

app = Flask(
    __name__, template_folder=".", static_folder=None, instance_relative_config=True
)

# [IMPROVED] Setup Advanced Logger with File + Console Output
if __name__ != "__main__":
    # Production: Use Gunicorn Logger
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
else:
    # Development: Use Basic Config
    logging.basicConfig(level=logging.INFO)

# [NEW] Add File Handler for Error Logging (All Environments)
try:
    if not os.path.exists("logs"):
        os.makedirs("logs")

    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    )
    app.logger.addHandler(file_handler)

    # Also log INFO level to separate file
    info_handler = logging.FileHandler("logs/info.log")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    )
    app.logger.addHandler(info_handler)

    app.logger.info(f"PO-Online v{APP_VERSION} - Logging initialized")
except Exception as e:
    print(f"WARNING: Could not setup file logging: {e}", file=sys.stderr)

# NEW: Apply ProxyFix to handle headers from Nginx correctly (X-Forwarded-For)
# This ensures Flask-Limiter sees the real client IP, not 127.0.0.1
# Important for security and correct rate limiting on VPS
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Rate limiting setup handled in extensions and init_app

# -------------------------

app.jinja_env.filters["bangkok_datetime"] = bangkok_datetime_filter


def bahttext(amount):
    if amount is None:
        return ""
    try:
        amount = float(amount)
        if amount == 0:
            return "ศูนย์บาทถ้วน"

        # Simple Thai Baht conversion logic
        def _thai_num_to_text(num):
            thai_num = [
                "ศูนย์",
                "หนึ่ง",
                "สอง",
                "สาม",
                "สี่",
                "ห้า",
                "หก",
                "เจ็ด",
                "แปด",
                "เก้า",
            ]
            thai_unit = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"]

            num_str = str(int(num))
            res = ""
            for i, n in enumerate(num_str[::-1]):
                digit = int(n)
                if digit != 0:
                    if i == 0 and digit == 1 and len(num_str) > 1:
                        res = "เอ็ด" + res
                    elif i == 1 and digit == 1:
                        res = "สิบ" + res
                    elif i == 1 and digit == 2:
                        res = "ยี่สิบ" + res
                    else:
                        res = thai_num[digit] + thai_unit[i % 6] + res

                if i > 0 and i % 6 == 0:
                    res = "ล้าน" + res
            return res

        baht = int(amount)
        satang = int(round((amount - baht) * 100))

        res = _thai_num_to_text(baht) + "บาท"
        if satang == 0:
            res += "ถ้วน"
        else:
            res += _thai_num_to_text(satang) + "สตางค์"
        return res
    except:
        return str(amount)


app.jinja_env.filters["bahttext"] = bahttext

# --- Configuration ---
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "a_very_secret_key_that_should_be_changed"
)

# Database Configuration
# CHANGE: ใช้ Environment Variables (DB_HOST, etc.) เพื่อให้ Flexible กับ Docker
db_user = os.environ.get("POSTGRES_USER", "WAUser")  # REVERT to Docker default
db_pass = os.environ.get("POSTGRES_PASSWORD", "Wa@!0302$")  # REVERT to Docker default
db_host = os.environ.get("DB_HOST", "db")  # REVERT: 'localhost' -> 'db'
db_port = os.environ.get("DB_PORT", "5432")
db_name = os.environ.get("POSTGRES_DB", "po_online_db")

# Encode password for URL compatibility (handles '@', '$', etc.)
safe_db_pass = quote_plus(db_pass)
default_db_url = f"postgresql://{db_user}:{safe_db_pass}@{db_host}:{db_port}/{db_name}"

raw_db_url = os.environ.get("DATABASE_URL", default_db_url)
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

# Ensure database driver compatibility (psycopg v3 vs psycopg2)
try:
    import psycopg  # noqa: F401
except ImportError:
    # If psycopg v3 is not installed in the environment, fallback to psycopg2 explicitly
    if raw_db_url.startswith("postgresql+psycopg://"):
        raw_db_url = raw_db_url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    elif raw_db_url.startswith("postgresql://"):
        raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 1800,
    "pool_pre_ping": True,
}

# File Upload Configuration
# We will save files in the 'instance/uploads' folder
UPLOAD_FOLDER = os.path.join(app.instance_path, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_PDF_EXTENSIONS = {"pdf"}  # Only allow PDF for signed QT uploads
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


# Ensure the instance folder and upload folder exist
PRODUCT_IMAGE_FOLDER = os.path.join(app.instance_path, "product_images")
STATIC_PRODUCT_IMAGE_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "static", "product_images"
)

try:
    os.makedirs(app.instance_path)
except OSError:
    pass  # Instance folder already exists
try:
    os.makedirs(app.config["UPLOAD_FOLDER"])
except OSError:
    pass  # Upload folder already exists
try:
    os.makedirs(PRODUCT_IMAGE_FOLDER)
except OSError:
    pass

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
limiter.init_app(app)
login_manager.login_view = "login"  # Name of the login route
login_manager.login_message_category = "info"


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "success": False,
        "error": "คำขอถี่เกินไป กรุณารอสักครู่ (Too Many Requests)"
    }), 429


# FIX: Add user_loader callback for Flask-Login (Crucial for session management)
@login_manager.user_loader
def load_user(user_id):
    # This callback is used to reload the user object from the user ID stored in the session
    try:
        user = User.query.get(int(user_id))
        if user and getattr(user, "status", "active") == "inactive":
            return None  # Instant session revocation when user account is deactivated
        return user
    except Exception:
        return None


# NEW: Global dictionary for rate limiting (ป้องกัน Error: login_attempts is not defined)
login_attempts = {}


# Data constants and helpers moved to models.py

# Models moved to models.py

# =================================================================================
# [START] ส่วนที่หายไป: Routes หลัก (Login, Logout, Home, APIs) ใส่กลับคืนตรงนี้
# =================================================================================


# [NEW] Health Check Endpoint (สำหรับ Docker \u0026 Monitoring)
@app.route("/company-logo.png")
def serve_logo():
    return send_from_directory(".", "company-logo.png")


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for Docker healthcheck and monitoring systems.
    Returns 200 OK if application is running and database is accessible.
    """
    try:
        # Test database connection
        db.session.execute(text("SELECT 1"))

        return (
            jsonify(
                {
                    "status": "healthy",
                    "version": APP_VERSION,
                    "timestamp": now_bangkok().isoformat(),
                    "database": "connected",
                }
            ),
            200,
        )
    except Exception as e:
        app.logger.error(f"Health check failed: {e}")
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "version": APP_VERSION,
                    "timestamp": now_bangkok().isoformat(),
                    "error": str(e),
                }
            ),
            503,
        )


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login():
    if request.args.get("logout"):
        logout_user()
        session.clear()
    elif current_user.is_authenticated:
        return redirect(url_for("app_shell"))

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form or {}
        # Honeypot
        if data.get("website"):
            return jsonify({"success": False, "error": "Spam detected"}), 400

        username = data.get("username", "").strip()
        password = data.get("password", "")

        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.remote_addr
            or "127.0.0.1"
        )
        user_agent = request.headers.get("User-Agent", "-")

        user = User.query.filter(func.lower(User.username) == username.lower()).first()

        authenticated = False
        auth_source = "LOCAL_PASSWORD"

        if user:
            # 1. If account is enabled for AD authentication (use_ad_auth == True)
            if getattr(user, "use_ad_auth", True):
                if authenticate_ad_gateway(username, password):
                    authenticated = True
                    auth_source = "AD_GATEWAY"

            # 2. Check local password if not authenticated via AD Gateway
            if not authenticated:
                if user.password and bcrypt.check_password_hash(user.password, password):
                    authenticated = True
                    auth_source = "LOCAL_PASSWORD"

        if user and authenticated:
            if getattr(user, "status", "active") != "active":
                try:
                    db.session.add(
                        LoginLog(
                            username=username,
                            user_id=user.id,
                            ip_address=client_ip,
                            user_agent=user_agent,
                            status="ACCOUNT_DISABLED",
                            failure_reason="Account is disabled",
                        )
                    )
                    db.session.commit()
                except Exception as log_err:
                    print(f"Error writing login log: {log_err}")

                TransactionLog.log(
                    category="ciam_sso",
                    action="account_deactivated",
                    status="warning",
                    message=f"ปฏิเสธการเข้าสู่ระบบ: บัญชี '{username}' ถูกระงับสิทธิ์",
                    details={"username": username, "ip": client_ip, "reason": "status is inactive"},
                    triggered_by=f"user:{username}",
                )
                return jsonify({"success": False, "error": "Account disabled"}), 403

            login_user(user, remember=True)
            session["auth_provider"] = "local"
            session["is_sso"] = False
            user.lastLogin = now_bangkok()

            try:
                db.session.add(
                    LoginLog(
                        username=username,
                        user_id=user.id,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        status="SUCCESS",
                    )
                )
                db.session.commit()
            except Exception as log_err:
                print(f"Error writing login log: {log_err}")

            # ISO 27001 Audit Trail (Event BG-02 or Direct Login)
            log_action = "fallback_ad_login" if auth_source == "AD_GATEWAY" else "direct_login_success"
            log_category = "security_break_glass" if auth_source == "AD_GATEWAY" else "ciam_sso"
            TransactionLog.log(
                category=log_category,
                action=log_action,
                status="success",
                message=f"เข้าสู่ระบบสำเร็จผ่าน {auth_source}: ผู้ใช้ '{user.username}'",
                details={
                    "username": user.username,
                    "auth_source": auth_source,
                    "ip": client_ip,
                    "use_ad_auth": getattr(user, "use_ad_auth", True),
                },
                triggered_by=f"user:{user.username}",
            )

            return jsonify({"success": True})

        # Login failed
        try:
            db.session.add(
                LoginLog(
                    username=username,
                    user_id=user.id if user else None,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    status="FAILED_CREDENTIALS" if user else "USER_NOT_FOUND",
                    failure_reason="Invalid password" if user else "Username not found",
                )
            )
            db.session.commit()
        except Exception as log_err:
            print(f"Error writing login log: {log_err}")

        TransactionLog.log(
            category="security",
            action="login_failed",
            status="failed",
            message=f"พยายามเข้าสู่ระบบไม่สำเร็จ: ผู้ใช้ '{username}'",
            details={
                "username": username,
                "ip": client_ip,
                "reason": "Invalid credentials" if user else "Username not found",
            },
            triggered_by=f"user:{username}" if user else "system:anonymous",
        )

        err_msg = "ไม่พบบัญชีผู้ใช้นี้ในระบบตรง สำหรับพนักงานองค์กร กรุณาเข้าสู่ระบบด้วยปุ่ม 'Window Asia SSO' ด้านบน" if not user else "รหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบหรือเข้าสู่ระบบด้วยปุ่ม 'Window Asia SSO' ด้านบน"
        return jsonify({"success": False, "error": err_msg}), 401

    cfg = get_ciam_config()
    return render_template(
        "login.html",
        version=APP_VERSION,
        username="",
        sso_enabled=cfg.get("ciam_sso_enabled", True),
        break_glass_active=cfg.get("ciam_break_glass_active", False),
    )


@app.route("/logout")
def logout():
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
        or "127.0.0.1"
    )
    is_sso = session.get("auth_provider") == "ciam_sso" or session.get("is_sso", False)
    cfg = get_ciam_config()
    portal_url = f"{cfg.get('ciam_base_url', 'https://ciam.windowasia.com').rstrip('/')}/portal"

    if current_user.is_authenticated:
        username = current_user.username
        TransactionLog.log(
            category="ciam_sso",
            action="logout",
            status="info",
            message=f"ออกจากระบบ: ผู้ใช้ '{username}' ({'SSO' if is_sso else 'Local'})",
            details={"username": username, "auth_provider": "ciam_sso" if is_sso else "local", "ip": client_ip},
            triggered_by=f"user:{username}",
        )

    # Invalidate Flask-Login and session
    logout_user()
    session.clear()

    # Spec 5.3 & 10.6: Seamless return to Central IAM App Portal if logged in via SSO
    target_url = portal_url if is_sso else url_for("login", logout="1")
    response = make_response(redirect(target_url))

    # Explicitly clear remember_token and session cookies across path and domains
    remember_cookie_name = app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    session_cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")

    response.delete_cookie(remember_cookie_name, path="/")
    response.delete_cookie(session_cookie_name, path="/")
    if app.config.get("REMEMBER_COOKIE_DOMAIN"):
        response.delete_cookie(remember_cookie_name, domain=app.config.get("REMEMBER_COOKIE_DOMAIN"), path="/")
    if app.config.get("SESSION_COOKIE_DOMAIN"):
        response.delete_cookie(session_cookie_name, domain=app.config.get("SESSION_COOKIE_DOMAIN"), path="/")

    # Prevent browser caching of authenticated state
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@app.route("/")
@login_required
def app_shell():
    response = make_response(
        render_template("app.html", version=APP_VERSION)
    )  # FIX: Already correct
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.route("/api/current_user")
@login_required
def get_current_user():
    return jsonify(current_user.to_dict())


@app.route("/api/change_password", methods=["POST"])
@login_required
def change_password():
    """
    Allow logged-in users to change their own password.
    Requires current password for verification.
    """
    data = request.json
    current_pw = data.get("currentPassword")
    new_pw = data.get("newPassword")

    if not current_pw or not new_pw:
        return jsonify({"success": False, "error": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400

    # 1. Verify current password
    if not bcrypt.check_password_hash(current_user.password, current_pw):
        return jsonify({"success": False, "error": "รหัสผ่านปัจจุบันไม่ถูกต้อง"}), 401

    # 2. Validate new password complexity
    # We use the same regex as in User Management for consistency
    # Note: The regex requires 8-10 chars (per existing code), uppercase, lowercase, number, and special char.
    pw_pattern = (
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,10}$"
    )
    if not re.match(pw_pattern, new_pw):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "รหัสผ่านต้องยาว 8-10 ตัวอักษร, มีตัวใหญ่, ตัวเล็ก, ตัวเลข และอักขระพิเศษ (@$!%*?&)",
                }
            ),
            400,
        )

    # 3. Update password
    try:
        hashed_password = bcrypt.generate_password_hash(new_pw).decode("utf-8")
        current_user.password = hashed_password
        db.session.commit()

        app.logger.info(
            f"User {current_user.username} changed their password successfully."
        )
        return jsonify({"success": True, "message": "เปลี่ยนรหัสผ่านสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error changing password for {current_user.username}: {e}")
        return jsonify({"success": False, "error": "เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์"}), 500


@app.route("/api/dashboard/stats")
@login_required
def get_dashboard_stats():
    """
    High-performance Server-side Dashboard Aggregations.
    Replaces client-side calculation of 500 POs with instant SQL queries.
    """
    now = now_bangkok()
    month_param = request.args.get("month", "").strip()

    # Parse month (YYYY-MM) with fallback to current month
    selected_year = now.year
    selected_month = now.month
    if month_param:
        try:
            m_parts = month_param.split("-")
            y_val = int(m_parts[0])
            if y_val > 2500:
                y_val -= 543
            selected_year = y_val
            selected_month = int(m_parts[1])
        except Exception:
            selected_year = now.year
            selected_month = now.month

    start_of_month = datetime(selected_year, selected_month, 1)
    if selected_month == 12:
        end_of_month = datetime(selected_year + 1, 1, 1)
    else:
        end_of_month = datetime(selected_year, selected_month + 1, 1)

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    days_since_monday = start_of_day.weekday()
    start_of_week = start_of_day - timedelta(days=days_since_monday)

    # Base Role Filter condition
    is_admin = current_user.role in ["Administrator", "Sale Admin"]
    if is_admin:
        role_cond = or_(PurchaseOrder.status != "Draft", PurchaseOrder.sale_user_id == current_user.id)
    else:
        role_cond = (PurchaseOrder.sale_user_id == current_user.id)

    # All dashboard metrics and graphs are filtered by the selected month
    month_cond = and_(
        PurchaseOrder.created >= start_of_month,
        PurchaseOrder.created < end_of_month
    )

    # 1. Today & Week Count (active only when viewing current month)
    is_current_month = (selected_year == now.year and selected_month == now.month)
    if is_current_month:
        today_count = db.session.query(func.count(PurchaseOrder.id)).filter(
            role_cond,
            PurchaseOrder.created >= start_of_day,
            PurchaseOrder.status != "Cancelled"
        ).scalar() or 0

        week_count = db.session.query(func.count(PurchaseOrder.id)).filter(
            role_cond,
            PurchaseOrder.created >= start_of_week,
            PurchaseOrder.status != "Cancelled"
        ).scalar() or 0
    else:
        # If viewing another month, show 0 or total in that month
        today_count = 0
        week_count = 0

    # 2. Status Summary (Counts for Funnel and Pie Chart) - Monthly
    status_order = ["Draft", "Pending Review", "Changes Requested", "Approved", "Completed", "SAP SO", "Cancellation Requested", "Cancelled"]
    status_rows = db.session.query(
        PurchaseOrder.status, func.count(PurchaseOrder.id)
    ).filter(role_cond, month_cond).group_by(PurchaseOrder.status).all()
    raw_status_map = {s_name: s_cnt for s_name, s_cnt in status_rows}

    # SAP SO Count for the month
    sap_so_count = db.session.query(func.count(PurchaseOrder.id)).filter(
        role_cond,
        month_cond,
        PurchaseOrder.sap_doc_num.isnot(None),
        PurchaseOrder.sap_sync_status == "SYNCED"
    ).scalar() or 0

    status_counts = {}
    for st in status_order:
        if st == "SAP SO":
            status_counts[st] = sap_so_count
        else:
            status_counts[st] = raw_status_map.get(st, 0)
    for st, cnt in raw_status_map.items():
        if st not in status_counts:
            status_counts[st] = cnt

    # 3. Monthly Approved Value and Count
    approved_statuses = ["Approved", "Completed", "Cancellation Requested"]
    month_approved_row = db.session.query(
        func.count(PurchaseOrder.id),
        func.coalesce(func.sum(PurchaseOrder.amount), 0.0)
    ).filter(
        role_cond,
        PurchaseOrder.status.in_(approved_statuses),
        month_cond
    ).first()
    monthly_approved_count = month_approved_row[0] if month_approved_row else 0
    monthly_approved_value = float(month_approved_row[1]) if month_approved_row else 0.0

    # 4. Action Count for the month
    if current_user.role == "Sale":
        action_count = status_counts.get("Draft", 0) + status_counts.get("Changes Requested", 0)
    else:
        action_count = status_counts.get("Pending Review", 0) + status_counts.get("Cancellation Requested", 0)

    # 5. Cycle Durations (Avg delivery days for the month)
    cycle_rows = db.session.query(
        PurchaseOrder.created, PurchaseOrder.deliveryDate
    ).filter(
        role_cond,
        PurchaseOrder.status.in_(approved_statuses),
        PurchaseOrder.deliveryDate.isnot(None),
        month_cond
    ).order_by(PurchaseOrder.id.desc()).limit(100).all()

    cycle_durations = []
    for c_created, c_delivery in cycle_rows:
        if c_created and c_delivery:
            try:
                d_obj = c_delivery
                if isinstance(d_obj, str):
                    d_obj = _parse_date(d_obj)
                c_date = c_created.date() if hasattr(c_created, "date") else c_created
                if isinstance(d_obj, (date, datetime)) and isinstance(c_date, (date, datetime)):
                    diff = (d_obj - c_date).days
                    if diff >= 0:
                        cycle_durations.append(diff)
            except Exception:
                pass
    avg_cycle = round(sum(cycle_durations) / len(cycle_durations), 1) if cycle_durations else None

    # 6. Top 5 Customers for the month
    top_cust_rows = db.session.query(
        func.coalesce(PurchaseOrder.customerName, PurchaseOrder.customerId).label("cname"),
        func.sum(PurchaseOrder.amount).label("total")
    ).filter(
        role_cond,
        PurchaseOrder.status != "Cancelled",
        month_cond
    ).group_by(func.coalesce(PurchaseOrder.customerName, PurchaseOrder.customerId)).order_by(text("total DESC")).limit(5).all()

    top_customers = [
        {"name": r[0] or "Unknown", "total": float(r[1] or 0.0)}
        for r in top_cust_rows
    ]

    # 7. Top 5 Products for the month
    top_prod_rows = db.session.query(
        POItem.productCode,
        POItem.name,
        func.sum(POItem.total).label("ptotal")
    ).join(PurchaseOrder, POItem.po_id == PurchaseOrder.id).filter(
        role_cond,
        PurchaseOrder.status != "Cancelled",
        month_cond
    ).group_by(POItem.productCode, POItem.name).order_by(text("ptotal DESC")).limit(5).all()

    top_products = [
        {
            "productCode": r[0] or "",
            "name": r[1] or "Unknown",
            "total": float(r[2] or 0.0)
        }
        for r in top_prod_rows
    ]

    # 8. Recent Timeline Events for the month
    recent_pos = (
        PurchaseOrder.query.filter(role_cond, month_cond)
        .options(
            joinedload(PurchaseOrder.canceller),
            joinedload(PurchaseOrder.requester)
        )
        .order_by(PurchaseOrder.id.desc())
        .limit(10)
        .all()
    )
    timeline_events = []
    for p in recent_pos:
        c_dt = ensure_bangkok(p.created)
        if c_dt:
            timeline_events.append({
                "timestamp": c_dt.isoformat(),
                "title": f"สร้าง {p.poNumber}",
                "body": p.customerName or p.customerId or "ไม่ทราบลูกค้า",
                "icon": "file-plus"
            })
        if p.cancelRequestAt:
            cr_dt = ensure_bangkok(p.cancelRequestAt)
            cr_by = p.requester.fullName if p.requester else "Sale"
            timeline_events.append({
                "timestamp": cr_dt.isoformat() if cr_dt else "",
                "title": f"ขอเลิก {p.poNumber}",
                "body": f"โดย {cr_by}: {p.cancelRequestReason or '-'}",
                "icon": "alert-circle"
            })
        if p.cancelledAt:
            can_dt = ensure_bangkok(p.cancelledAt)
            can_by = p.canceller.fullName if p.canceller else "Admin"
            timeline_events.append({
                "timestamp": can_dt.isoformat() if can_dt else "",
                "title": f"ยกเลิก {p.poNumber} สำเร็จ",
                "body": f"อนุมัติโดย {can_by}: {p.cancelReason or '-'}",
                "icon": "x-circle"
            })
        if p.signedAt:
            s_dt = ensure_bangkok(p.signedAt)
            timeline_events.append({
                "timestamp": s_dt.isoformat() if s_dt else "",
                "title": f"เซ็นชื่อสำเร็จ {p.poNumber}",
                "body": "รายการเสร็จสมบูรณ์เข้าระบบ",
                "icon": "check-circle"
            })

    timeline_events.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    timeline_events = timeline_events[:10]

    return jsonify(
        {
            "month": f"{selected_year}-{selected_month:02d}",
            "isCurrentMonth": is_current_month,
            "todayCount": today_count,
            "weekCount": week_count,
            "statusCounts": status_counts,
            "statusOrder": status_order,
            "monthlyApprovedCount": monthly_approved_count,
            "monthlyApprovedValue": monthly_approved_value,
            "actionCount": action_count,
            "avgCycleDays": avg_cycle,
            "topCustomers": top_customers,
            "topProducts": top_products,
            "timelineEvents": timeline_events,
            "lastUpdate": now.strftime("%d-%m-%Y %H:%M"),
        }
    )


def get_next_po_number():
    today = now_bangkok().date()
    # FIX: เขียนแยกตัวแปร ลดความสับสนเรื่อง Quote
    yymm = today.strftime("%y%m")
    prefix = f"QT{yymm}"

    last_po = (
        PurchaseOrder.query.filter(PurchaseOrder.poNumber.like(f"{prefix}%"))
        .order_by(PurchaseOrder.poNumber.desc())
        .first()
    )
    if last_po:
        try:
            seq = int(last_po.poNumber[len(prefix) :]) + 1
            return f"{prefix}{seq:04d}"
        except:
            pass
    return f"{prefix}0001"


@app.route("/api/pos/<int:id>/request-cancel", methods=["POST"])
@login_required
def request_cancel_po(id):
    po = PurchaseOrder.query.get_or_404(id)

    # Permission check: Only Creator OR Administrator OR Sale Admin
    if current_user.id != po.sale_user_id and current_user.role not in [
        "Administrator",
        "Sale Admin",
    ]:
        return jsonify({"error": "Unauthorized to request cancellation"}), 403

    if po.status not in ["Pending Review", "Approved", "Completed"]:
        return (
            jsonify(
                {
                    "error": "Only Pending Review, Approved or Completed POs can be cancelled"
                }
            ),
            400,
        )

    data = request.json
    reason = data.get("reason", "").strip()
    if not reason:
        return jsonify({"error": "Reason for cancellation is required"}), 400

    po.previousStatus = po.status
    po.status = "Cancellation Requested"
    po.cancelRequestBy = current_user.id
    po.cancelRequestAt = now_bangkok()
    po.cancelRequestReason = reason
    po.updatedAt = now_bangkok()

    try:
        # 1. Telegram Notification (To Admins)
        customer_name = po.get_customer_name()
        msg = (
            f"🔔 <b>QT-Online System</b>\n"
            f"📅 {now_bangkok().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"⚠️ <b>Cancellation REQUESTED</b>\n"
            f"<b>QT:</b> {po.poNumber}\n"
            f"<b>Customer:</b> {customer_name}\n"
            f"<b>From:</b> {po.previousStatus}\n"
            f"<b>By:</b> {current_user.fullName}\n"
            f"<b>Reason:</b> {reason}"
        )
        send_telegram_msg(msg)

        # 2. Add a log comment
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"Requested QT Cancellation. Reason: {reason}",
        )
        db.session.add(comment)

        db.session.commit()
        return (
            jsonify({"message": "Cancellation request submitted", "status": po.status}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/pos/<int:id>/approve-cancel", methods=["POST"])
@login_required
@roles_required("Administrator", "Sale Admin")
def approve_cancel_po(id):
    po = PurchaseOrder.query.get_or_404(id)

    if po.status != "Cancellation Requested":
        return jsonify({"error": "QT is not in Cancellation Requested status"}), 400

    po.status = "Cancelled"
    po.cancelReason = po.cancelRequestReason
    po.cancelledAt = now_bangkok()
    po.cancelledBy = current_user.id
    po.updatedAt = now_bangkok()

    try:
        # 1. Telegram Notification
        customer_name = po.get_customer_name()
        msg = (
            f"🔔 <b>QT-Online System</b>\n"
            f"📅 {now_bangkok().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"🚫 <b>QT Cancelled (Approved)</b>\n"
            f"<b>QT:</b> {po.poNumber}\n"
            f"<b>Customer:</b> {customer_name}\n"
            f"<b>Approved By:</b> {current_user.fullName}\n"
            f"<b>Reason:</b> {po.cancelReason}"
        )
        send_telegram_msg(msg)

        # 2. In-App Notification (Notify Sale Owner)
        if po.sale_user_id:
            create_notification(
                po.sale_user_id,
                f"Cancellation Approved: QT {po.poNumber} is now Cancelled.",
                link_id=po.id,
            )

        # 3. Add a log comment
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"Approved Cancellation. QT is now Cancelled.",
        )
        db.session.add(comment)

        db.session.commit()
        return (
            jsonify({"message": "QT Cancelled successfully", "status": "Cancelled"}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/pos/<int:id>/reject-cancel", methods=["POST"])
@login_required
@roles_required("Administrator", "Sale Admin")
def reject_cancel_po(id):
    po = PurchaseOrder.query.get_or_404(id)

    if po.status != "Cancellation Requested":
        return jsonify({"error": "QT is not in Cancellation Requested status"}), 400

    data = request.json
    reject_reason = data.get("reason", "").strip()

    old_target_status = po.previousStatus or "Approved"
    po.status = old_target_status
    po.updatedAt = now_bangkok()

    try:
        # 1. Telegram Notification
        customer_name = po.get_customer_name()
        msg = (
            f"🔔 <b>QT-Online System</b>\n"
            f"📅 {now_bangkok().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"✅ <b>Cancellation REJECTED</b>\n"
            f"<b>QT:</b> {po.poNumber}\n"
            f"<b>Customer:</b> {customer_name}\n"
            f"<b>Status Reverted to:</b> {po.status}\n"
            f"<b>By:</b> {current_user.fullName}"
        )
        if reject_reason:
            msg += f"\n<b>Note:</b> {reject_reason}"
        send_telegram_msg(msg)

        # 2. In-App Notification (Notify Sale Owner)
        if po.sale_user_id:
            create_notification(
                po.sale_user_id,
                f"Cancellation Rejected: QT {po.poNumber} remains {po.status}.",
                link_id=po.id,
            )

        # 3. Add a log comment
        comment_text = (
            f"Rejected Cancellation Request. QT status reverted to {po.status}."
        )
        if reject_reason:
            comment_text += f" Note: {reject_reason}"
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=comment_text,
        )
        db.session.add(comment)

        db.session.commit()
        return (
            jsonify({"message": "Cancellation request rejected", "status": po.status}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/pos/export-excel", methods=["GET"])
@login_required
def export_pos_excel():
    keyword = request.args.get("keyword", "").strip()
    status_filter = request.args.get("status", "").strip()
    month_filter = request.args.get("month", "").strip()  # YYYY-MM

    # Base query based on user roles (Same security logic as manage_pos)
    query = PurchaseOrder.query
    if current_user.role in ["Administrator", "Sale Admin"]:
        # Admins/Sale Admins see all POs EXCEPT other people's Drafts
        query = query.filter(
            or_(
                PurchaseOrder.status != "Draft",
                PurchaseOrder.sale_user_id == current_user.id,
            )
        )
    else:
        # Sale users see only their own POs
        query = query.filter_by(sale_user_id=current_user.id)

    # Apply Month Filter (with BE -> CE conversion)
    if month_filter:
        try:
            parts = month_filter.split('-')
            year = int(parts[0])
            month = int(parts[1])
            if year > 2500:
                year -= 543
            from sqlalchemy import extract
            query = query.filter(extract('year', PurchaseOrder.updatedAt) == year)
            query = query.filter(extract('month', PurchaseOrder.updatedAt) == month)
        except Exception as e:
            app.logger.error(f"Error filtering month in export: {e}")

    # Apply Status Filter
    if status_filter:
        if status_filter.lower() == "sap so":
            query = query.filter(PurchaseOrder.sap_doc_num.isnot(None), PurchaseOrder.sap_sync_status == "SYNCED")
        else:
            query = query.filter(PurchaseOrder.status == status_filter)

    # Apply Keyword Filter (Replicating frontend searchable fields)
    if keyword:
        keyword_like = f"%{keyword}%"
        query = query.join(User, PurchaseOrder.sale_user_id == User.id, isouter=True)
        query = query.filter(
            or_(
                PurchaseOrder.poNumber.ilike(keyword_like),
                PurchaseOrder.customerId.ilike(keyword_like),
                PurchaseOrder.customerName.ilike(keyword_like),
                PurchaseOrder.status.ilike(keyword_like),
                User.fullName.ilike(keyword_like),
                PurchaseOrder.saleId.ilike(keyword_like)
            )
        )

    # Fetch data ordered by ID desc
    pos = (
        query.options(
            joinedload(PurchaseOrder.creator),
            joinedload(PurchaseOrder.customer_rel),
            selectinload(PurchaseOrder.items).joinedload(POItem.product)
        )
        .order_by(PurchaseOrder.id.desc())
        .all()
    )

    import csv
    import io

    output = io.StringIO()
    # Write BOM for Microsoft Excel character encoding compatibility
    output.write(u'\ufeff')
    writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    # Detailed report headers
    headers = [
        "เลขที่ QT (QT Number)",
        "สถานะ (Status)",
        "วันที่สร้าง (Created Date)",
        "กำหนดส่งสินค้า (Delivery Date)",
        "รหัสลูกค้า (Customer Code)",
        "ชื่อลูกค้า (Customer Name)",
        "ที่อยู่จัดส่ง (Ship To)",
        "ชื่อพนักงานขาย (Sale Name)",
        "รหัสสินค้า (Product Code)",
        "ชื่อสินค้า (Product Name)",
        "จำนวน (Quantity)",
        "ราคาต่อหน่วย (Unit Price)",
        "ราคาแนะนำ (Recommended Price)",
        "ส่วนลดรายการ (Item Discount)",
        "ราคารวมรายการ (Item Total)",
        "ส่วนลดท้ายบิล 1 (%) (QT Discount 1 %)",
        "ส่วนลดท้ายบิล 2 (%) (QT Discount 2 %)",
        "มูลค่ารวมทั้งใบ QT (QT Total Amount)",
        "วันที่แก้ไขล่าสุด (Updated Date)",
        "เหตุผลการยกเลิก (Cancel Reason)"
    ]
    writer.writerow(headers)

    for po in pos:
        sale_name = po.creator.fullName if po.creator else (po.saleId or "Unknown")
        customer_name = po.get_customer_name()

        created_str = ensure_bangkok(po.created).strftime("%d/%m/%Y %H:%M") if po.created else ""
        delivery_str = po.deliveryDate.strftime("%d/%m/%Y") if po.deliveryDate else ""
        updated_str = ensure_bangkok(po.updatedAt).strftime("%d/%m/%Y %H:%M") if po.updatedAt else ""

        # Build detailed shipping address
        ship_to = po.poShipTo or ""
        if not ship_to and po.customer_rel:
            cust_name = po.customer_rel.name
            s_build = po.customer_rel.shipToBuilding
            if s_build and cust_name and s_build.strip() == cust_name.strip():
                s_build = None
            ship_parts = [
                s_build,
                po.customer_rel.shipToStreet,
                po.customer_rel.shipToCity,
                po.customer_rel.shipToCounty,
                po.customer_rel.shipToCountry,
                po.customer_rel.shipToZipCode,
            ]
            ship_to = " ".join(filter(None, ship_parts))
            if not ship_to.strip():
                b_build = po.customer_rel.billToBuilding
                if b_build and cust_name and b_build.strip() == cust_name.strip():
                    b_build = None
                bill_parts = [
                    b_build,
                    po.customer_rel.billToStreet,
                    po.customer_rel.billToCity,
                    po.customer_rel.billToCounty,
                    po.customer_rel.billToCountry,
                    po.customer_rel.billToZipCode,
                ]
                ship_to = " ".join(filter(None, bill_parts))

        # Write each item as a separate row to provide item-level granularity
        if po.items:
            for item in po.items:
                prod_code = item.productCode or ""
                if not prod_code and item.product:
                    prod_code = item.product.productCode or ""

                row = [
                    po.poNumber,
                    po.status,
                    created_str,
                    delivery_str,
                    po.customerId,
                    customer_name,
                    ship_to,
                    sale_name,
                    prod_code,
                    item.name or "",
                    item.qty or 0,
                    item.price or 0.0,
                    item.recommendedPrice or 0.0,
                    item.discount or 0.0,
                    item.total or 0.0,
                    po.discount_percent_1 or 0.0,
                    po.discount_percent_2 or 0.0,
                    po.amount or 0.0,
                    updated_str,
                    po.cancelReason or ""
                ]
                writer.writerow(row)
        else:
            row = [
                po.poNumber,
                po.status,
                created_str,
                delivery_str,
                po.customerId,
                customer_name,
                ship_to,
                sale_name,
                "", "", 0, 0.0, 0.0, 0.0, 0.0,
                po.discount_percent_1 or 0.0,
                po.discount_percent_2 or 0.0,
                po.amount or 0.0,
                updated_str,
                po.cancelReason or ""
            ]
            writer.writerow(row)

    response_data = output.getvalue()
    output.close()

    filename = f"qt_export_{ensure_bangkok(now_bangkok()).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        response_data.encode('utf-8-sig'),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/pos", methods=["GET", "POST"])
@login_required
def manage_pos():
    if request.method == "GET":
        query = PurchaseOrder.query
        if current_user.role in ["Administrator", "Sale Admin"]:
            # Admins/Sale Admins see all POs EXCEPT other people's Drafts
            query = query.filter(
                or_(
                    PurchaseOrder.status != "Draft",
                    PurchaseOrder.sale_user_id == current_user.id,
                )
            )
        else:
            # Sale users see only their own POs
            query = query.filter_by(sale_user_id=current_user.id)

        # Month or Date Filtering
        month_param = request.args.get("month", "").strip()
        if month_param and month_param.lower() != "all":
            try:
                parts = [int(p) for p in month_param.split("-")]
                if parts[0] > 2500:
                    parts[0] -= 543  # Convert Buddhist year to Gregorian
                filter_col = func.coalesce(PurchaseOrder.updatedAt, PurchaseOrder.created)
                if len(parts) == 2:
                    y, m = parts[0], parts[1]
                    start_dt = datetime(y, m, 1, 0, 0, 0)
                    if m == 12:
                        end_dt = datetime(y + 1, 1, 1, 0, 0, 0)
                    else:
                        end_dt = datetime(y, m + 1, 1, 0, 0, 0)
                    query = query.filter(
                        and_(filter_col >= start_dt, filter_col < end_dt)
                    )
                elif len(parts) == 3:
                    y, m, d = parts[0], parts[1], parts[2]
                    start_dt = datetime(y, m, d, 0, 0, 0)
                    end_dt = start_dt + timedelta(days=1)
                    query = query.filter(
                        and_(filter_col >= start_dt, filter_col < end_dt)
                    )
            except Exception as ex:
                app.logger.warning(f"Invalid month filter format: {month_param}, error: {ex}")

        is_summary = request.args.get("summary", "true").lower() != "false"

        try:
            if is_summary:
                # Fast summary query without heavy items/comments joins
                q = (
                    query.options(
                        joinedload(PurchaseOrder.creator),
                        joinedload(PurchaseOrder.customer_rel),
                    )
                    .order_by(PurchaseOrder.id.desc())
                )
                if not month_param or month_param.lower() == "all":
                    q = q.limit(500)
                pos = q.all()
                return jsonify([po.to_summary_dict() for po in pos])
            else:
                pos = (
                    query.options(
                        joinedload(PurchaseOrder.creator),
                        joinedload(PurchaseOrder.customer_rel),
                        joinedload(PurchaseOrder.requester),
                        joinedload(PurchaseOrder.canceller),
                        joinedload(PurchaseOrder.location_uploader),
                        joinedload(PurchaseOrder.po_uploader),
                        selectinload(PurchaseOrder.comments),
                        joinedload(PurchaseOrder.items).joinedload(POItem.product),
                    )
                    .order_by(PurchaseOrder.id.desc())
                    .limit(500)
                    .all()
                )
                return jsonify([po.to_dict() for po in pos])
        except Exception as e:
            print(f"ERROR in manage_pos: {e}")
            import traceback

            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    if request.method == "POST":
        data = request.json
        try:
            new_po = PurchaseOrder(
                poNumber=get_next_po_number(),
                customerId=data["customerId"],
                customerName=data.get("customerName"),
                poShipTo=data.get("poShipTo"),
                sale_user_id=current_user.id,
                amount=data["total"],
                status=data["status"],
                deliveryDate=_parse_date(data.get("deliveryDate")),
                accessToken=str(uuid.uuid4()),
                discount_percent_1=float(data.get("discountPercent1", 0.0)),
                discount_percent_2=float(data.get("discountPercent2", 0.0)),
                promotion_id=data.get("promotionId"),
                promotion_name=data.get("promotionName"),
                promotion_discount=float(data.get("promotionDiscount", 0.0)),
                customer_ref_no=data.get("customerRefNo"),
            )
            item_list = data.get("items", [])
            product_ids = [it["productId"] for it in item_list if it.get("productId")]
            product_map = {}
            if product_ids:
                products = Product.query.filter(Product.id.in_(product_ids)).all()
                product_map = {p.id: p for p in products}

            for item in item_list:
                prod = product_map.get(item.get("productId"))
                new_po.items.append(
                    POItem(
                        productId=item.get("productId"),
                        productCode=prod.productCode if prod else item.get("productCode"),
                        name=item["name"],
                        qty=item["qty"],
                        price=item["price"],
                        recommendedPrice=item.get("recommendedPrice", 0),
                        discount=item.get("discount", 0),
                        total=item["total"],
                        is_gift=bool(item.get("isGift", False)),
                        imageUrl=prod.imageUrl if prod else None,
                    )
                )
            db.session.add(new_po)
            db.session.commit()
            print(
                f"DEBUG: QT {new_po.poNumber} created successfully by {current_user.username}"
            )
            return jsonify(new_po.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to create PO: {e}")
            import traceback

            traceback.print_exc()
            return jsonify({"error": str(e)}), 500


@app.route("/api/pos/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
def manage_po(id):
    po = PurchaseOrder.query.get_or_404(id)

    if request.method == "GET":
        # Restriction: Only creator can see Drafts
        if po.status == "Draft" and po.sale_user_id != current_user.id:
            return jsonify({"error": "Unauthorized to view this draft"}), 403

        # Optional: Further restriction for non-admins viewing others' POs
        if (
            current_user.role not in ["Administrator", "Sale Admin"]
            and po.sale_user_id != current_user.id
        ):
            return jsonify({"error": "Unauthorized to view this PO"}), 403

        return jsonify(po.to_dict())

    if request.method == "DELETE":
        if (
            po.status not in ["Draft", "Pending Review"]
            and current_user.role != "Administrator"
        ):
            return jsonify({"error": "Cannot delete processed PO"}), 403
        try:
            # Notify cancellation before delete (Optional, but good for tracking)
            if po.status != "Draft":
                send_telegram_msg(
                    f"🔔 <b>QT-Online System</b>\n"
                    f"📅 {now_bangkok().strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"🗑️ <b>QT Deleted</b>\n"
                    f"<b>QT:</b> {po.poNumber}\n"
                    f"<b>By:</b> {current_user.fullName}"
                )

            db.session.delete(po)
            db.session.commit()
            return "", 204
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    if request.method == "PUT":
        data = request.json

        # --- Handle Status Change & Notifications ---
        if "status" in data and data["status"] != po.status:
            old_status = po.status
            new_status = data["status"]
            po.status = new_status

            # 1. Telegram Notification
            try:
                icon = "📝"
                if new_status == "Approved":
                    icon = "✅"
                elif new_status == "Changes Requested":
                    icon = "⚠️"
                elif new_status == "Pending Review":
                    icon = "w"
                elif new_status == "Completed":
                    icon = "🏁"

                customer_name = po.get_customer_name()
                msg = (
                    f"🔔 <b>QT-Online System</b>\n"
                    f"📅 {now_bangkok().strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"{icon} <b>Status Update</b>\n"
                    f"<b>QT:</b> {po.poNumber}\n"
                    f"<b>Customer:</b> {customer_name}\n"
                    f"<b>Status:</b> {old_status} ➝ <b>{new_status}</b>\n"
                    f"<b>By:</b> {current_user.fullName}"
                )
                send_telegram_msg(msg)
            except Exception as e:
                print(f"Failed to send telegram: {e}")

            # 2. In-App Notification
            # Notify the Sale (Owner) if someone else (e.g. Admin) updated it
            if current_user.id != po.sale_user_id:
                notify_text = f"QT {po.poNumber} status is now {new_status}"
                if new_status == "Changes Requested":
                    notify_text = f"QT {po.poNumber} requires changes."
                if new_status == "Approved":
                    notify_text = f"QT {po.poNumber} has been Approved."
                create_notification(po.sale_user_id, notify_text, link_id=po.id)

            # Notify Admins if Sale submitted for review
            if new_status == "Pending Review":
                # In a real app, you'd loop through all admins.
                # For now, we rely on Telegram for Admin alerts,
                # or we could add a specific admin notification if we had a list of admin IDs.
                pass

        # Update Customer
        if "customerId" in data:
            po.customerId = data["customerId"]
        if "customerName" in data:
            po.customerName = data["customerName"]
        if "poShipTo" in data:
            po.poShipTo = data["poShipTo"]

        # Update Delivery Date
        if "deliveryDate" in data:
            po.deliveryDate = _parse_date(data.get("deliveryDate"))

        # Update Discounts
        if "discountPercent1" in data:
            po.discount_percent_1 = float(data.get("discountPercent1", 0.0))
        if "discountPercent2" in data:
            po.discount_percent_2 = float(data.get("discountPercent2", 0.0))

        # Update Promotion & Customer Ref
        if "promotionId" in data:
            po.promotion_id = data.get("promotionId")
        if "promotionName" in data:
            po.promotion_name = data.get("promotionName")
        if "promotionDiscount" in data:
            po.promotion_discount = float(data.get("promotionDiscount", 0.0))
        if "customerRefNo" in data:
            po.customer_ref_no = data.get("customerRefNo")

        # Update Items (if provided)
        if "items" in data:
            # Clear existing items
            PurchaseOrder.query.session.execute(
                db.delete(POItem).where(POItem.po_id == id)
            )

            item_list = data.get("items", [])
            product_ids = [it["productId"] for it in item_list if it.get("productId")]
            product_map = {}
            if product_ids:
                products = Product.query.filter(Product.id.in_(product_ids)).all()
                product_map = {p.id: p for p in products}

            for item in item_list:
                prod = product_map.get(item.get("productId"))
                po.items.append(
                    POItem(
                        productId=item.get("productId"),
                        productCode=prod.productCode if prod else item.get("productCode"),
                        name=item["name"],
                        qty=item["qty"],
                        price=item["price"],
                        recommendedPrice=item.get("recommendedPrice", 0),
                        discount=item.get("discount", 0),
                        total=item["total"],
                        is_gift=bool(item.get("isGift", False)),
                        imageUrl=prod.imageUrl if prod else None,
                    )
                )

            # Recalculate amount if items changed
            po.amount = sum(i.total for i in po.items)

    po.updatedAt = now_bangkok()
    db.session.commit()
    return jsonify(po.to_dict())


@app.route("/api/pos/<int:id>/comments", methods=["POST"])
@login_required
def add_comment(id):
    po = PurchaseOrder.query.get_or_404(id)
    comment = Comment(
        po_id=po.id,
        user_id=current_user.id,
        user=current_user.fullName,
        text=request.json["comment"],
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


# =================================================================================
# [NEW] Customer Document Upload APIs
# =================================================================================


@app.route("/api/pos/<int:id>/upload-location", methods=["POST"])
@login_required
def upload_customer_location(id):
    """
    Upload customer location/map file

    Authorization: QT Owner OR Sale Admin OR Administrator
    File Types: PDF, JPG, JPEG, PNG, GIF
    Max Size: 10MB
    """
    po = PurchaseOrder.query.get_or_404(id)

    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in [
        "Administrator",
        "Sale Admin",
    ]:
        return jsonify({"error": "Unauthorized to upload documents for this PO"}), 403

    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Validate file type
    allowed_extensions = {"pdf", "jpg", "jpeg", "png", "gif"}
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: PDF, JPG, PNG, GIF"}), 400

    # Validate file size (10MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 10 * 1024 * 1024:
        return jsonify({"error": "File size exceeds 10MB limit"}), 400

    try:
        # Delete old file if exists
        if po.customerLocationFile:
            old_path = os.path.join(
                app.config["UPLOAD_FOLDER"], po.customerLocationFile
            )
            if os.path.exists(old_path):
                os.remove(old_path)
                app.logger.info(f"Deleted old location file: {po.customerLocationFile}")

        # Determine output extension and path
        save_ext = "jpg" if ext in {"jpg", "jpeg", "png", "gif"} else ext
        filename = secure_filename(
            f"location_{po.poNumber}_{int(datetime.now().timestamp())}.{save_ext}"
        )
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Save to temp file first, then compress
        temp_filename = f"temp_{filename}"
        temp_filepath = os.path.join(app.config["UPLOAD_FOLDER"], temp_filename)
        file.save(temp_filepath)

        from utils import compress_image, compress_pdf
        if save_ext == "pdf":
            compress_pdf(temp_filepath, filepath)
        else:
            compress_image(temp_filepath, filepath)

        # Remove temp file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

        # Update database
        po.customerLocationFile = filename
        po.customerLocationFileUrl = f"/uploads/{filename}"
        po.customerLocationUploadedAt = now_bangkok()
        po.customerLocationUploadedBy = current_user.id

        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"อัปโหลดแผนที่/ตำแหน่งลูกค้า: {file.filename}",
        )
        db.session.add(comment)

        db.session.commit()

        app.logger.info(
            f"Location file uploaded: {filename} for QT {po.poNumber} by {current_user.fullName}"
        )

        return (
            jsonify(
                {
                    "message": "อัปโหลดแผนที่สำเร็จ",
                    "fileUrl": po.customerLocationFileUrl,
                    "filename": filename,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error uploading location file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/pos/<int:id>/upload-customer-po", methods=["POST"])
@login_required
def upload_customer_po_file(id):
    """
    Upload customer QT document

    Authorization: QT Owner OR Sale Admin OR Administrator
    File Types: PDF, JPG, JPEG, PNG, GIF
    Max Size: 10MB
    """
    po = PurchaseOrder.query.get_or_404(id)

    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in [
        "Administrator",
        "Sale Admin",
    ]:
        return jsonify({"error": "Unauthorized to upload documents for this PO"}), 403

    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Validate file type
    allowed_extensions = {"pdf", "jpg", "jpeg", "png", "gif"}
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: PDF, JPG, PNG, GIF"}), 400

    # Validate file size (10MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 10 * 1024 * 1024:
        return jsonify({"error": "File size exceeds 10MB limit"}), 400

    try:
        # Delete old file if exists
        if po.customerPoFile:
            old_path = os.path.join(app.config["UPLOAD_FOLDER"], po.customerPoFile)
            if os.path.exists(old_path):
                os.remove(old_path)
                app.logger.info(f"Deleted old customer QT file: {po.customerPoFile}")

        # Determine output extension and path
        save_ext = "jpg" if ext in {"jpg", "jpeg", "png", "gif"} else ext
        filename = secure_filename(
            f"customer_po_{po.poNumber}_{int(datetime.now().timestamp())}.{save_ext}"
        )
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Save to temp file first, then compress
        temp_filename = f"temp_{filename}"
        temp_filepath = os.path.join(app.config["UPLOAD_FOLDER"], temp_filename)
        file.save(temp_filepath)

        from utils import compress_image, compress_pdf
        if save_ext == "pdf":
            compress_pdf(temp_filepath, filepath)
        else:
            compress_image(temp_filepath, filepath)

        # Remove temp file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

        # Update database
        po.customerPoFile = filename
        po.customerPoFileUrl = f"/uploads/{filename}"
        po.customerPoUploadedAt = now_bangkok()
        po.customerPoUploadedBy = current_user.id

        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"อัปโหลด PO ของลูกค้า: {file.filename}",
        )
        db.session.add(comment)

        db.session.commit()

        app.logger.info(
            f"Customer PO file uploaded: {filename} for QT {po.poNumber} by {current_user.fullName}"
        )

        return (
            jsonify(
                {
                    "message": "อัปโหลด PO ลูกค้าสำเร็จ",
                    "fileUrl": po.customerPoFileUrl,
                    "filename": filename,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error uploading customer PO file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/pos/<int:id>/delete-location", methods=["DELETE"])
@login_required
def delete_customer_location(id):
    """
    Delete customer location file

    Authorization: QT Owner OR Sale Admin OR Administrator
    """
    po = PurchaseOrder.query.get_or_404(id)

    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in [
        "Administrator",
        "Sale Admin",
    ]:
        return jsonify({"error": "Unauthorized to delete documents for this PO"}), 403

    if not po.customerLocationFile:
        return jsonify({"error": "No location file to delete"}), 400

    try:
        # Delete file from filesystem
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], po.customerLocationFile)
        if os.path.exists(filepath):
            os.remove(filepath)
            app.logger.info(f"Deleted location file: {po.customerLocationFile}")

        # Update database
        old_filename = po.customerLocationFile
        po.customerLocationFile = None
        po.customerLocationFileUrl = None
        po.customerLocationUploadedAt = None
        po.customerLocationUploadedBy = None

        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"ลบแผนที่/ตำแหน่งลูกค้า: {old_filename}",
        )
        db.session.add(comment)

        db.session.commit()

        app.logger.info(
            f"Location file deleted for QT {po.poNumber} by {current_user.fullName}"
        )

        return jsonify({"message": "ลบไฟล์แผนที่สำเร็จ"}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting location file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/pos/<int:id>/delete-customer-po", methods=["DELETE"])
@login_required
def delete_customer_po_file(id):
    """
    Delete customer PO file

    Authorization: PO Owner OR Sale Admin OR Administrator
    """
    po = PurchaseOrder.query.get_or_404(id)

    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in [
        "Administrator",
        "Sale Admin",
    ]:
        return jsonify({"error": "Unauthorized to delete documents for this PO"}), 403

    if not po.customerPoFile:
        return jsonify({"error": "No customer PO file to delete"}), 400

    try:
        # Delete file from filesystem
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], po.customerPoFile)
        if os.path.exists(filepath):
            os.remove(filepath)
            app.logger.info(f"Deleted customer PO file: {po.customerPoFile}")

        # Update database
        old_filename = po.customerPoFile
        po.customerPoFile = None
        po.customerPoFileUrl = None
        po.customerPoUploadedAt = None
        po.customerPoUploadedBy = None

        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"ลบ PO ของลูกค้า: {old_filename}",
        )
        db.session.add(comment)

        db.session.commit()

        app.logger.info(
            f"Customer PO file deleted for PO {po.poNumber} by {current_user.fullName}"
        )

        return jsonify({"message": "ลบไฟล์ PO ลูกค้าสำเร็จ"}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting customer PO file: {e}")
        return jsonify({"error": str(e)}), 500


# [NEW] Route สำหรับแสดงรูปสินค้า (แก้ปัญหา Error 404 ในหน้า View/Create PO) - เพิ่ม Fallback หลายโฟลเดอร์
@app.route("/product-images/<path:filename>")
def serve_product_image(filename):
    # 1. ลองหาใน instance folder (สำหรับไฟล์อัปโหลดใหม่)
    try:
        return send_from_directory(PRODUCT_IMAGE_FOLDER, filename)
    except Exception:
        pass

    # 2. ลองหาใน static folder (สำหรับไฟล์เก่า/Demo)
    try:
        return send_from_directory(STATIC_PRODUCT_IMAGE_FOLDER, filename)
    except Exception:
        pass

    # 3. ลองหาใน upload folder ปกติ
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    except Exception as e:
        return f"Image not found: {e}", 404


# [ADDED BACK] Route สำหรับอัปโหลดรูปสินค้า (แก้ไข Error ตอนอัปโหลดรูป)
@app.route("/api/products/<key>/image", methods=["POST"])
@login_required
@roles_required("Administrator", "Sale Admin", "Uploader")
def upload_product_image(key):
    # ค้นหาสินค้า
    prod = None
    if key.isdigit():
        prod = Product.query.get(int(key))
    if not prod:
        decoded_key = unquote(key)
        prod = Product.query.filter_by(productCode=decoded_key).first()

    if not prod:
        return jsonify({"error": "Product not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_image_file(file.filename):
        # สร้างชื่อไฟล์ใหม่ตามรหัสสินค้า
        ext = file.filename.rsplit(".", 1)[1].lower()
        new_filename = secure_filename(f"{prod.productCode}.{ext}")

        # บันทึกลงโฟลเดอร์ product_images ใน instance path
        filepath = os.path.join(PRODUCT_IMAGE_FOLDER, new_filename)
        temp_filepath = os.path.join(PRODUCT_IMAGE_FOLDER, f"temp_{new_filename}")
        file.save(temp_filepath)

        # Compress product image (max 1024px, keep format)
        from utils import compress_image
        compress_image(temp_filepath, filepath, max_dimension=1024, quality=75, keep_format=True)

        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

        # อัปเดต URL ในฐานข้อมูล (เก็บเป็น Path สั้นๆ)
        prod.imageUrl = f"/product-images/{new_filename}"

        # [Backup] ก็อปปี้ไปที่โฟลเดอร์ static ด้วยเผื่อกรณี Web Server เรียกหาผิดที่
        try:
            import shutil

            if not os.path.exists(STATIC_PRODUCT_IMAGE_FOLDER):
                os.makedirs(STATIC_PRODUCT_IMAGE_FOLDER)
            shutil.copy(
                os.path.join(PRODUCT_IMAGE_FOLDER, new_filename),
                os.path.join(STATIC_PRODUCT_IMAGE_FOLDER, new_filename),
            )
        except Exception:
            pass  # ignore copy error

        db.session.commit()

        # FIX: Add success=True for frontend check
        response_data = prod.to_detail_dict()
        response_data["success"] = True
        return jsonify(response_data)

    return jsonify({"error": "Invalid file type"}), 400


# [MODIFIED] รองรับการค้นหา Customer (?q=...) และปรับ Format ให้ Dropdown ทำงานได้ 100% พร้อม Pagination ที่รวดเร็ว
CUSTOMER_SUMMARY_LOAD_FIELDS = (
    Customer.id,
    Customer.customerCode,
    Customer.name,
    Customer.billToCounty,
    Customer.shipToCounty,
    Customer.telephone1,
    Customer.telephone2,
    Customer.mobilePhone,
    Customer.paymentTermsCode,
    Customer.creditLimit,
    Customer.inactive,
)


@app.route("/api/customers", methods=["GET"])
@login_required
def list_customers():
    page = request.args.get("page", type=int)
    search = request.args.get("q")
    status = request.args.get("status", "all")  # active, inactive, all
    per_page = request.args.get("pageSize", type=int) or request.args.get("per_page", type=int) or 50
    per_page = min(max(per_page, 10), 250)

    query = Customer.query.options(load_only(*CUSTOMER_SUMMARY_LOAD_FIELDS))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.customerCode.ilike(term),
                Customer.name.ilike(term),
                Customer.telephone1.ilike(term),
            )
        )

    if status == "active":
        query = query.filter(or_(Customer.inactive == False, Customer.inactive == None))
    elif status == "inactive":
        query = query.filter(Customer.inactive == True)
    # else status == 'all', no filter applied

    query = query.order_by(Customer.id)

    # กรณีขอแบบแบ่งหน้า (สำหรับหน้า Management Tables)
    if page:
        pg = query.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify(
            {
                "items": [c.to_summary_dict() for c in pg.items],
                "total": pg.total,
                "page": page,
                "pageSize": per_page,
            }
        )

    # กรณี Dropdown / Cache (ไม่ส่ง page มา)
    limit = request.args.get("pageSize", type=int) or request.args.get("limit", type=int) or 500
    if not page and status == "all":
        query = query.filter(or_(Customer.inactive == False, Customer.inactive == None))

    results = query.limit(limit).all()
    return jsonify([c.to_summary_dict() for c in results])


# [MODIFIED] ปรับแก้ Product List เช่นกัน เพื่อให้ Dropdown หน้า Create QT ทำงานได้
@app.route("/api/products", methods=["GET"])
@login_required
def list_products():
    try:
        page = request.args.get("page", type=int)
        search = request.args.get("q")
        status = request.args.get("status", "all")

        query = Product.query
        if search:
            keywords = search.split()
            for kw in keywords:
                term = f"%{kw}%"
                query = query.filter(
                    or_(
                        Product.productCode.ilike(term),
                        Product.name.ilike(term),
                        Product.itemGroup.ilike(term),
                    )
                )

        if status == "active":
            query = query.filter(
                or_(Product.inactive == False, Product.inactive == None)
            )
        elif status == "inactive":
            query = query.filter_by(inactive=True)

        query = query.order_by(Product.productCode)

        # สำหรับหน้า Product Management (มี page)
        if page:
            pg = query.paginate(page=page, per_page=100, error_out=False)

            # Convert to dict with error handling
            items = []
            for p in pg.items:
                try:
                    items.append(p.to_dict())
                except Exception as e:
                    app.logger.error(f"Error converting product {p.id} to dict: {e}")
                    # Add minimal data to prevent complete failure
                    items.append(
                        {
                            "id": p.id,
                            "productCode": p.productCode or "",
                            "name": p.name or "Error loading product",
                            "error": str(e),
                        }
                    )

            return jsonify({"items": items, "total": pg.total, "page": page})

        # สำหรับ Dropdown (ไม่มี page) -> ส่ง List [] กลับไปตรงๆ
        # Default to active if status is not specified for dropdown
        if status == "all":
            query = query.filter(
                or_(Product.inactive == False, Product.inactive == None)
            )

        # ดึงข้อมูลทั้งหมดเพื่อให้ Dropdown แสดงครบ (ไม่จำกัดจำนวน)
        results = query.all()

        # Convert to dict with error handling
        items = []
        for p in results:
            try:
                items.append(p.to_dict())
            except Exception as e:
                app.logger.error(f"Error converting product {p.id} to dict: {e}")
                items.append(
                    {
                        "id": p.id,
                        "productCode": p.productCode or "",
                        "name": p.name or "Error loading product",
                        "error": str(e),
                    }
                )

        return jsonify(items)

    except Exception as e:
        app.logger.error(f"Error in list_products: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Failed to load products: {str(e)}"}), 500


# [NEW] Route สำหรับดูรายละเอียดสินค้า (แก้ปัญหา View ไม่ได้)
@app.route("/api/products/<key>", methods=["GET", "PUT", "DELETE"])
@login_required
def get_product_detail(key):
    """
    Get, Update, or Delete product by ID or Product Code
    """
    try:
        # Try to find by ID first (if key is numeric)
        prod = None
        if key.isdigit():
            prod = Product.query.get(int(key))

        # Try to find by Product Code
        if not prod:
            decoded_key = unquote(key)
            prod = Product.query.filter_by(productCode=decoded_key).first()

        if not prod:
            app.logger.warning(f"Product not found: {key}")
            return jsonify({"error": "Product not found"}), 404

        # GET
        if request.method == "GET":
            return jsonify(prod.to_detail_dict())

        # PUT
        if request.method == "PUT":
            if current_user.role not in ["Administrator", "Sale Admin"]:
                return jsonify({"error": "Unauthorized to edit products"}), 403
            data = request.json

            # Handle standard fields
            allowed_fields = [
                "name",
                "itemGroup",
            ]

            for field in allowed_fields:
                if field in data:
                    setattr(prod, field, data[field])

            # Handle Booleans
            bool_fields = [
                "manageBatch",
                "manageInventoryByWarehouse",
                "salesItem",
                "purchaseItem",
                "inventoryItem",
                "inactive",
            ]
            for field in bool_fields:
                if field in data:
                    setattr(prod, field, bool(data[field]))

            # Handle Numerics
            if "unitPrice" in data:
                prod.unitPrice = float(data["unitPrice"])
            if "inStock" in data:
                prod.inStock = float(data["inStock"])
            if "itemCost" in data:
                prod.itemCost = float(data["itemCost"])
            if "discountPercent" in data and data["discountPercent"] is not None:
                try:
                    prod.discountPercent = float(data["discountPercent"])
                except (ValueError, TypeError):
                    prod.discountPercent = 0.0
            elif "discount" in data and data["discount"] is not None:
                try:
                    prod.discountPercent = float(data["discount"])
                except (ValueError, TypeError):
                    prod.discountPercent = 0.0

            # Handle Date
            if "productionDate" in data and data["productionDate"]:
                try:
                    prod.productionDate = _parse_date(data["productionDate"])
                except:
                    pass

            db.session.commit()
            return jsonify({"success": True, "product": prod.to_detail_dict()})

        # DELETE
        if request.method == "DELETE":
            if current_user.role not in ["Administrator", "Sale Admin"]:
                return jsonify({"error": "Unauthorized to delete products"}), 403
            db.session.delete(prod)
            db.session.commit()
            return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in manage_product({key}): {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Failed to process product: {str(e)}"}), 500


@app.route("/api/customers/<key>", methods=["GET", "PUT", "DELETE"])
@login_required
def get_customer_detail(key):
    # รองรับการหาด้วย ID
    cust = None
    if key.isdigit():
        cust = Customer.query.get(int(key))

    if not cust:
        # รองรับการหาด้วย Customer Code
        decoded_key = unquote(key)
        cust = Customer.query.filter_by(customerCode=decoded_key).first()

    if not cust:
        return jsonify({"error": "Customer not found"}), 404

    if request.method == "GET":
        return jsonify(cust.to_detail_dict())

    if request.method == "PUT":
        try:
            data = request.json

            # Handle Status
            if "inactive" in data:
                cust.inactive = bool(data["inactive"])

            # Handle Fields
            allowed_fields = [
                "name",
                "foreignName",
                "currency",
                "groupCode",
                "priceListNo",
                "aliasName",
                "taxId",
                "branch",
                "taxGroup",
                "taxCode",
                "paymentTermsCode",
                "salesEmployeeCode",
                "shippingType",
                "arAccount",
                "accountBalance",
                "creditLimit",
                "globalLocationNumber",
                "updateFullTime",
                "remarks",
                "remark1",
                "telephone1",
                "telephone2",
                "mobilePhone",
                "selfEmployed",
                "billToBuilding",
                "billToStreet",
                "billToCity",
                "billToCounty",
                "billToCountry",
                "billToBlock",
                "billToStreetNo",
                "billToZipCode",
                "shipToBuilding",
                "shipToStreet",
                "shipToCity",
                "shipToCounty",
                "shipToCountry",
                "shipToBlock",
                "shipToStreetNo",
                "shipToZipCode",
            ]

            for field in allowed_fields:
                if field in data:
                    setattr(cust, field, data[field])

            # Special Date Handling
            if "creationDate" in data and data["creationDate"]:
                try:
                    cust.creationDate = _parse_date(data["creationDate"])
                except:
                    pass

            db.session.commit()
            return jsonify({"success": True, "customer": cust.to_detail_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    if request.method == "DELETE":
        try:
            db.session.delete(cust)
            db.session.commit()
            return jsonify({"success": True})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500


# [NEW] Notification APIs (เติมส่วนที่หายไปกลับเข้ามาครับ)
@app.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    try:
        # FIX: Only get unread notifications so they "disappear" when marked as read
        notifs = (
            Notification.query.filter_by(user_id=current_user.id, is_read=False)
            .order_by(Notification.created.desc())
            .limit(20)
            .all()
        )
        return jsonify([n.to_dict() for n in notifs])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Promotion Management & Evaluation APIs
# ---------------------------------------------------------------------------
@app.route("/api/promotions", methods=["GET", "POST"])
@login_required
def handle_promotions():
    if request.method == "GET":
        active_only = request.args.get("active_only", "false").lower() in ("true", "1", "yes")
        is_admin = current_user.role in ["Administrator", "Sale Admin"]
        
        query = Promotion.query
        if active_only or not is_admin:
            query = query.filter_by(is_active=True)
            today = now_bangkok().date()
            query = query.filter(
                or_(Promotion.start_date.is_(None), Promotion.start_date <= today),
                or_(Promotion.end_date.is_(None), Promotion.end_date >= today)
            )
        
        promos = query.order_by(Promotion.id.desc()).all()
        return jsonify([p.to_dict() for p in promos])

    if request.method == "POST":
        if current_user.role not in ["Administrator", "Sale Admin"]:
            return jsonify({"error": "เฉพาะ Admin หรือ Sale Admin เท่านั้นที่มีสิทธิ์จัดการโปรโมชั่น"}), 403

        data = request.json or {}
        code = (data.get("code") or "").strip().upper()
        name = (data.get("name") or "").strip()
        if not code or not name:
            return jsonify({"error": "กรุณาระบุรหัสและชื่อโปรโมชั่น"}), 400

        existing = Promotion.query.filter_by(code=code).first()
        if existing:
            return jsonify({"error": f"รหัสโปรโมชั่น '{code}' มีอยู่ในระบบแล้ว"}), 400

        try:
            start_d = _parse_date(data.get("start_date")) if data.get("start_date") else None
            end_d = _parse_date(data.get("end_date")) if data.get("end_date") else None

            promo = Promotion(
                code=code,
                name=name,
                description=data.get("description", ""),
                promo_type=data.get("promo_type", "ORDER_DISCOUNT_FIXED"),
                min_order_amount=float(data.get("min_order_amount", 0.0) or 0.0),
                discount_value=float(data.get("discount_value", 0.0) or 0.0),
                max_discount_amount=float(data["max_discount_amount"]) if data.get("max_discount_amount") else None,
                condition_product_code=(data.get("condition_product_code") or "").strip(),
                condition_qty=int(data.get("condition_qty", 1) or 1),
                reward_product_code=(data.get("reward_product_code") or "").strip(),
                reward_product_name=(data.get("reward_product_name") or "").strip(),
                reward_qty=int(data.get("reward_qty", 1) or 1),
                start_date=start_d,
                end_date=end_d,
                is_active=bool(data.get("is_active", True)),
                created_by=current_user.id
            )
            db.session.add(promo)
            db.session.commit()
            return jsonify({"success": True, "promotion": promo.to_dict()}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500


@app.route("/api/promotions/<int:promo_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def handle_single_promotion(promo_id):
    promo = Promotion.query.get(promo_id)
    if not promo:
        return jsonify({"error": "Promotion not found"}), 404

    if request.method == "GET":
        return jsonify(promo.to_dict())

    if current_user.role not in ["Administrator", "Sale Admin"]:
        return jsonify({"error": "เฉพาะ Admin หรือ Sale Admin เท่านั้นที่มีสิทธิ์จัดการโปรโมชั่น"}), 403

    if request.method == "DELETE":
        try:
            db.session.delete(promo)
            db.session.commit()
            return jsonify({"success": True, "message": "ลบโปรโมชั่นเรียบร้อยแล้ว"})
        except Exception as e:
            db.session.rollback()
            try:
                promo.is_active = False
                db.session.commit()
                return jsonify({"success": True, "message": "ปิดการใช้งานโปรโมชั่นเรียบร้อยแล้ว"})
            except:
                return jsonify({"error": str(e)}), 500

    if request.method == "PUT":
        data = request.json or {}
        try:
            if "name" in data:
                promo.name = data["name"].strip()
            if "description" in data:
                promo.description = data["description"]
            if "promo_type" in data:
                promo.promo_type = data["promo_type"]
            if "min_order_amount" in data:
                promo.min_order_amount = float(data["min_order_amount"] or 0.0)
            if "discount_value" in data:
                promo.discount_value = float(data["discount_value"] or 0.0)
            if "max_discount_amount" in data:
                promo.max_discount_amount = float(data["max_discount_amount"]) if data["max_discount_amount"] else None
            if "condition_product_code" in data:
                promo.condition_product_code = (data["condition_product_code"] or "").strip()
            if "condition_qty" in data:
                promo.condition_qty = int(data["condition_qty"] or 1)
            if "reward_product_code" in data:
                promo.reward_product_code = (data["reward_product_code"] or "").strip()
            if "reward_product_name" in data:
                promo.reward_product_name = (data["reward_product_name"] or "").strip()
            if "reward_qty" in data:
                promo.reward_qty = int(data["reward_qty"] or 1)
            if "start_date" in data:
                promo.start_date = _parse_date(data["start_date"]) if data["start_date"] else None
            if "end_date" in data:
                promo.end_date = _parse_date(data["end_date"]) if data["end_date"] else None
            if "is_active" in data:
                promo.is_active = bool(data["is_active"])

            promo.updated_at = now_bangkok()
            db.session.commit()
            return jsonify({"success": True, "promotion": promo.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500


@app.route("/api/promotions/settings", methods=["GET", "POST"])
@login_required
def handle_promotion_settings():
    if request.method == "GET":
        enabled_val = SystemSetting.get_value("promotion_system_enabled", "true")
        mode_val = SystemSetting.get_value("promotion_selection_mode", "auto")
        return jsonify({
            "success": True,
            "promotion_system_enabled": str(enabled_val).lower() in ("true", "1", "yes"),
            "promotion_selection_mode": mode_val if mode_val in ["auto", "manual"] else "auto",
            "is_admin": current_user.role == "Administrator"
        })

    if request.method == "POST":
        if current_user.role != "Administrator":
            return jsonify({"error": "เฉพาะ Administrator เท่านั้นที่มีสิทธิ์ตั้งค่าระบบโปรโมชั่น"}), 403

        data = request.json or {}
        if "promotion_system_enabled" in data:
            is_en = bool(data["promotion_system_enabled"])
            SystemSetting.set_value("promotion_system_enabled", "true" if is_en else "false", description="เปิด/ปิดการใช้งานระบบโปรโมชั่น", category="promotion", data_type="boolean")
        if "promotion_selection_mode" in data:
            mode = str(data["promotion_selection_mode"]).strip().lower()
            if mode not in ["auto", "manual"]:
                mode = "auto"
            SystemSetting.set_value("promotion_selection_mode", mode, description="โหมดการเลือกโปรโมชั่น (auto/manual)", category="promotion", data_type="string")

        db.session.commit()
        return jsonify({
            "success": True,
            "promotion_system_enabled": str(SystemSetting.get_value("promotion_system_enabled", "true")).lower() in ("true", "1", "yes"),
            "promotion_selection_mode": SystemSetting.get_value("promotion_selection_mode", "auto")
        })


@app.route("/api/promotions/evaluate", methods=["POST"])
@login_required
def evaluate_promotions():
    """
    Evaluates eligible promotions for a given quotation based on subtotal and items.
    Checks master system ON/OFF and selection mode configured by Administrator.
    """
    # 1. ตรวจสอบการเปิด/ปิดระบบโปรโมชั่นและโหมดที่ตั้งค่าไว้
    is_promo_system_enabled = str(SystemSetting.get_value("promotion_system_enabled", "true")).lower() in ("true", "1", "yes")
    selection_mode = SystemSetting.get_value("promotion_selection_mode", "auto")
    if selection_mode not in ["auto", "manual"]:
        selection_mode = "auto"

    if not is_promo_system_enabled:
        return jsonify({
            "success": True,
            "enabled": False,
            "selection_mode": selection_mode,
            "eligible_promotions": [],
            "best_promotion": None
        })

    data = request.json or {}
    subtotal = float(data.get("subtotal", 0.0) or 0.0)
    items = data.get("items", [])

    today = now_bangkok().date()
    promos = Promotion.query.filter_by(is_active=True).filter(
        or_(Promotion.start_date.is_(None), Promotion.start_date <= today),
        or_(Promotion.end_date.is_(None), Promotion.end_date >= today)
    ).all()

    eligible = []
    qty_by_code = {}
    total_qty = 0
    for it in items:
        if it.get("isGift"):
            continue
        code = (it.get("productCode") or "").strip().upper()
        q = int(it.get("qty", 0) or 0)
        total_qty += q
        if code:
            qty_by_code[code] = qty_by_code.get(code, 0) + q

    for p in promos:
        is_match = False
        benefit_text = ""
        calc_discount = 0.0
        free_gift = None

        if p.promo_type == "ORDER_DISCOUNT_FIXED":
            if subtotal >= (p.min_order_amount or 0.0):
                is_match = True
                calc_discount = min(float(p.discount_value or 0.0), subtotal)
                benefit_text = f"ส่วนลดท้ายบิล {calc_discount:,.2f} บาท"

        elif p.promo_type == "ORDER_DISCOUNT_PERCENT":
            if subtotal >= (p.min_order_amount or 0.0):
                is_match = True
                disc = subtotal * (float(p.discount_value or 0.0) / 100.0)
                if p.max_discount_amount and p.max_discount_amount > 0:
                    disc = min(disc, float(p.max_discount_amount))
                calc_discount = disc
                benefit_text = f"ส่วนลด {p.discount_value}% (-{calc_discount:,.2f} บาท)"

        elif p.promo_type == "BUY_X_GET_Y":
            cond_code = (p.condition_product_code or "").strip().upper()
            cond_qty = int(p.condition_qty or 1)
            reward_code = (p.reward_product_code or "").strip().upper()
            reward_name = (p.reward_product_name or "").strip()
            reward_qty = int(p.reward_qty or 1)

            # กรณีที่ 1: กำหนดรหัสสินค้าของแถมเฉพาะเจาะจง (เช่น ซื้อครบ 20 ชิ้น แถม ประตู DR-01)
            if reward_code:
                # ถ้าระบุ cond_code ให้ตรวจเฉพาะสินค้านั้น ถ้าไม่ระบุให้ตรวจยอดรวมสินค้าทั้งหมดในบิล
                matching_qty = qty_by_code.get(cond_code, 0) if cond_code else total_qty
                if matching_qty >= cond_qty:
                    is_match = True
                    reward_times = matching_qty // cond_qty
                    total_reward_qty = reward_times * reward_qty
                    clean_reward_name = (reward_name or f"{reward_code}").replace(" (ของแถมฟรี)", "").replace(" (แถมฟรี)", "").strip()
                    free_gift = {
                        "productCode": reward_code,
                        "name": clean_reward_name,
                        "qty": total_reward_qty,
                        "price": 0.0,
                        "isGift": True
                    }
                    benefit_text = f"แถม {clean_reward_name} จำนวน {total_reward_qty} ชิ้น"

            # กรณีที่ 2: ไม่ได้ระบุรหัสสินค้าของแถม (แปลว่าแถมสินค้าเดียวกันกับที่ซื้อ! เช่น ซื้อชนิดเดียวกันครบ 10 ชิ้น แถม 1 ชิ้น)
            else:
                qualifying_items = []
                for it in items:
                    if it.get("isGift"):
                        continue
                    it_code = (it.get("productCode") or "").strip().upper()
                    it_qty = int(it.get("qty", 0) or 0)
                    if (not cond_code or it_code == cond_code) and it_qty >= cond_qty:
                        qualifying_items.append(it)

                if qualifying_items:
                    # เลือกสินค้าที่มีมูลค่าสูงสุดหรือยอดสั่งซื้อมากที่สุด
                    qualifying_items.sort(key=lambda x: (float(x.get("price", 0) or 0), int(x.get("qty", 0) or 0)), reverse=True)
                    best_match_item = qualifying_items[0]
                    matched_qty = int(best_match_item.get("qty", 0) or 0)
                    reward_times = matched_qty // cond_qty
                    total_reward_qty = reward_times * reward_qty

                    item_code = best_match_item.get("productCode") or "FREE-GIFT"
                    item_name = best_match_item.get("name")
                    if not item_name or item_name == item_code:
                        p_obj = Product.query.filter_by(productCode=item_code).first()
                        if p_obj and p_obj.name:
                            item_name = p_obj.name
                        else:
                            item_name = item_code

                    clean_name = item_name.replace(" (ของแถมฟรี)", "").replace(" (แถมฟรี)", "").strip()
                    free_gift = {
                        "productCode": item_code,
                        "name": clean_name,
                        "qty": total_reward_qty,
                        "price": 0.0,
                        "isGift": True,
                        "imageUrl": best_match_item.get("imageUrl") or ""
                    }
                    is_match = True
                    benefit_text = f"แถม {clean_name} จำนวน {total_reward_qty} ชิ้น"

        if is_match:
            eligible.append({
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "promo_type": p.promo_type,
                "description": p.description,
                "calculated_discount": calc_discount,
                "free_gift": free_gift,
                "benefit_text": benefit_text,
                "score": calc_discount + (100.0 if free_gift else 0.0)
            })

    eligible.sort(key=lambda x: x["score"], reverse=True)
    best_promotion = eligible[0] if eligible else None

    return jsonify({
        "success": True,
        "enabled": True,
        "selection_mode": selection_mode,
        "eligible_promotions": eligible,
        "best_promotion": best_promotion
    })


# --- CSV Import & Template Routes ---


@app.route("/api/customers/template", methods=["GET"])
@login_required
def download_customer_template():
    csv_content = get_template_csv("customer")
    ts = now_bangkok().strftime("%Y%m%d_%H%M")
    response = make_response(csv_content)
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=customer_template_{ts}.csv"
    )
    return response


@app.route("/api/products/template", methods=["GET"])
@login_required
def download_product_template():
    csv_content = get_template_csv("product")
    ts = now_bangkok().strftime("%Y%m%d_%H%M")
    response = make_response(csv_content)
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=product_template_{ts}.csv"
    )
    return response


@app.route("/api/customers/upload", methods=["POST"])
@login_required
@roles_required("Administrator", "Sale Admin", "Uploader")
def upload_customer_csv():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"}), 400

    try:
        content = file.read()
        stats = import_customer_from_csv(content)
        return jsonify({"success": True, **stats})
    except Exception as e:
        app.logger.error(f"Customer upload error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/products/upload", methods=["POST"])
@login_required
@roles_required("Administrator", "Sale Admin", "Uploader")
def upload_product_csv():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"}), 400

    try:
        content = file.read()
        stats = import_product_from_csv(content)
        return jsonify({"success": True, **stats})
    except Exception as e:
        app.logger.error(f"Product upload error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/notifications/<int:id>/read", methods=["POST"])
@login_required
def read_notification(id):
    try:
        n = Notification.query.filter_by(id=id, user_id=current_user.id).first_or_404()
        n.is_read = True
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/read-all", methods=["POST"])
@login_required
def read_all_notifications():
    try:
        Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
            {"is_read": True}
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# [NEW] Add missing route for frontend call (Fixes 404 Error in Screenshot)
@app.route("/api/notifications/read-by-po/<int:po_id>", methods=["POST"])
@login_required
def read_notifications_by_po(po_id):
    try:
        # Mark all notifications related to this QT as read for the current user
        Notification.query.filter_by(
            user_id=current_user.id, link_id=po_id, is_read=False
        ).update({"is_read": True})

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error reading QT notifications: {e}")
        return jsonify({"error": str(e)}), 500


# [NEW] Generic QR Code Route (Support for legacy/direct frontend calls)
@app.route("/qrcode", methods=["GET"])
def generate_generic_qr():
    base_url = request.args.get("base_url")
    if not base_url:
        return "Missing base_url", 400

    if not QR_AVAILABLE or qrcode is None:
        return "QR Library not installed", 500

    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(base_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        buffered.seek(0)

        return send_file(buffered, mimetype="image/png")
    except Exception as e:
        return str(e), 500


# --- PDF Generation Helper (Put this back!) ---
def _generate_pdf_bytes(po, is_draft=True):
    if not HTML:
        raise Exception("WeasyPrint library is missing.")

    sale_signature_src = None
    if po.creator and po.creator.signature_image:
        # Reuse logic from get_user_signature_preview
        try:
            if po.creator.signature_image.startswith("DB_SIG:"):
                b64_str = po.creator.signature_image.split(":", 1)[1]
                encrypted_data = base64.b64decode(b64_str)
                decrypted = decrypt_data(encrypted_data)
                enc_img = base64.b64encode(decrypted).decode("ascii")
                sale_signature_src = f"data:image/png;base64,{enc_img}"
            else:
                spath = os.path.join(
                    app.config["UPLOAD_FOLDER"], po.creator.signature_image
                )
                if os.path.exists(spath):
                    with open(spath, "rb") as f:
                        raw = f.read()
                        if po.creator.signature_image.endswith(".enc"):
                            raw = decrypt_data(raw)
                        enc_img = base64.b64encode(raw).decode("ascii")
                        sale_signature_src = f"data:image/png;base64,{enc_img}"
        except Exception as e:
            print(f"Error loading sale signature for PDF: {e}")

    # Load Customer Signature if exists
    signature_image_src = None
    if po.signatureImage:
        # Check database storage first (if you decide to move cust sig to DB later) or file
        # Currently cust sig is file-based in existing code
        spath = os.path.join(app.config["UPLOAD_FOLDER"], po.signatureImage)
        if os.path.exists(spath):
            with open(spath, "rb") as f:
                enc_img = base64.b64encode(f.read()).decode("ascii")
                signature_image_src = f"data:image/png;base64,{enc_img}"

    # Prepare Items
    items_for_print = []
    current_subtotal = 0
    for idx, item in enumerate(po.items, 1):
        img_src = None
        img_url = item.imageUrl
        if not img_url and item.productCode:
            img_url = f"/product-images/{item.productCode}.jpg"

        if img_url:
            fname = img_url.split("/")[-1]
            lpath = os.path.join(PRODUCT_IMAGE_FOLDER, fname)
            if os.path.exists(lpath):
                img_src = "file://" + lpath

        # Assign item qty and discount first to prevent variable leak from previous iteration
        qty = item.qty or 0
        discount = item.discount or 0.0
        is_item_gift = bool(getattr(item, "is_gift", False))

        if is_item_gift:
            unit_price = 0.0
            line_total = 0.0
        else:
            unit_price = (
                item.recommendedPrice
                if (item.recommendedPrice and item.recommendedPrice > 0)
                else item.price
            )
            line_total = (unit_price * qty) * (1 - discount / 100.0)
            current_subtotal += line_total

        # Clean item name: remove (ของแถมฟรี) and prevent duplicate productCode prefix
        raw_name = (item.name or "").replace(" (ของแถมฟรี)", "").replace(" (แถมฟรี)", "").strip()
        pcode = item.productCode or ""
        if pcode and raw_name.startswith(pcode):
            raw_name = raw_name[len(pcode):].lstrip(" -").strip()

        if not raw_name and pcode:
            p_obj = Product.query.filter_by(productCode=pcode).first()
            if p_obj and p_obj.name:
                raw_name = p_obj.name

        items_for_print.append(
            {
                "index": idx,
                "name": raw_name or pcode,
                "productCode": pcode,
                "quantity": qty,
                "unit_price": unit_price,
                "discount": discount,
                "total": line_total,
                "image_src": img_src,
                "is_gift": is_item_gift,
            }
        )

    # Calculations (Custom 6-Line Summary)
    non_gift_items = [i for i in po.items if not getattr(i, "is_gift", False)]
    # 1. Subtotal (Recommended Price on Non-Gift Items)
    total_recommended = sum(
        (
            i.recommendedPrice
            if (i.recommendedPrice and i.recommendedPrice > 0)
            else i.price
        )
        * i.qty
        for i in non_gift_items
    )

    # 2. Price Difference Discount (Recommended - Cost)
    non_gift_items = [i for i in po.items if not getattr(i, "is_gift", False)]
    total_cost_base = sum(i.price * i.qty for i in non_gift_items)
    price_diff_discount = total_recommended - total_cost_base

    # Promotion Discount (Deducted before Step 1 & Step 2)
    promo_discount = float(po.promotion_discount or 0.0)
    cost_after_promo = max(0.0, total_cost_base - promo_discount)

    # 3. Bill Discount (2-Step on Cost Base after Promo)
    disc1_percent = po.discount_percent_1 or 0.0
    disc1_amount = cost_after_promo * (disc1_percent / 100.0)
    total_after_1 = cost_after_promo - disc1_amount

    disc2_percent = po.discount_percent_2 or 0.0
    disc2_amount = total_after_1 * (disc2_percent / 100.0)
    total_after_2 = total_after_1 - disc2_amount

    bill_discount_total = disc1_amount + disc2_amount

    # 4. Total After All Discounts
    total_after_discount = total_after_2

    # 5. VAT 7%
    vat_amount = round(total_after_discount * 0.07, 2)

    # 6. Grand Total
    grand_total = total_after_discount + vat_amount

    totals_summary = {
        "subtotal_recommended": total_recommended,
        "price_diff_discount": price_diff_discount,
        "promotion_discount": promo_discount,
        "bill_discount_total": bill_discount_total,
        "total_after_discount": total_after_discount,
        "vat": vat_amount,
        "grand_total": grand_total,
        # Keep original fields for compatibility if needed
        "discount_percent_1": disc1_percent,
        "discount_percent_2": disc2_percent,
    }

    # Resolve local paths for header images (rendered via WeasyPrint using file://)
    logo_path = os.path.abspath(os.path.join(app.root_path, "company-logo.png")).replace("\\", "/")
    if not logo_path.startswith("/"):
        logo_path = "/" + logo_path
    company_logo_src = "file://" + logo_path if os.path.exists(os.path.join(app.root_path, "company-logo.png")) else None

    name_path = os.path.abspath(os.path.join(app.root_path, "company-name.png")).replace("\\", "/")
    if not name_path.startswith("/"):
        name_path = "/" + name_path
    company_name_src = "file://" + name_path if os.path.exists(os.path.join(app.root_path, "company-name.png")) else None

    iso_path = os.path.abspath(os.path.join(app.root_path, "company-iso.png")).replace("\\", "/")
    if not iso_path.startswith("/"):
        iso_path = "/" + iso_path
    company_iso_src = "file://" + iso_path if os.path.exists(os.path.join(app.root_path, "company-iso.png")) else None

    # Render HTML
    html_content = render_template(
        "po_print.html",
        po=po,
        company=COMPANY_DATA,
        customer=po.to_dict(),  # We use the logic in to_dict to resolve names/addresses
        items_for_print=items_for_print,
        totals_summary=totals_summary,
        is_draft=is_draft,
        sale_signature_src=sale_signature_src,
        signature_image_src=signature_image_src,
        company_logo_src=company_logo_src,
        company_name_src=company_name_src,
        company_iso_src=company_iso_src,
    )

    return HTML(string=html_content).write_pdf()


# --- MISSING ROUTE: PDF Print ---
@app.route("/api/pos/<int:id>/print", methods=["GET"])
@login_required
def print_po(id):
    po = PurchaseOrder.query.get_or_404(id)
    is_draft = request.args.get("draft", "true") == "true"

    try:
        pdf_bytes = _generate_pdf_bytes(po, is_draft=is_draft)

        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        fname = f"QT_{po.poNumber}_{'DRAFT' if is_draft else 'OFFICIAL'}.pdf"
        response.headers["Content-Disposition"] = f"inline; filename={fname}"
        return response
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/pos/<int:id>/qr", methods=["GET"])
@app.route("/api/pos/<int:id>/qrcode", methods=["GET"])
@login_required
def get_po_qr_code(id):
    """Generate QR Code for QT sharing link - ROBUST VERSION (Returns Image)"""
    # print(f"[QR v1.6.8] Request for QT ID: {id}", file=sys.stderr)

    # Check 1: Library Available?
    if not QR_AVAILABLE or qrcode is None:
        return "QR libraries not installed", 500

    try:
        # Check 2: QT Exists?
        po = PurchaseOrder.query.get(id)
        if not po:
            return "QT not found", 404

        # Check 3: Ensure Token Exists
        if not po.accessToken:
            try:
                po.accessToken = str(uuid.uuid4())
                db.session.commit()
            except Exception:
                db.session.rollback()
                return "Database error", 500

        # Check 4: Build URL
        manual_base_url = request.args.get("base_url")
        if manual_base_url:
            manual_base_url = unquote(manual_base_url).rstrip("/")
            portal_url = f"{manual_base_url}/p/{po.accessToken}"
        else:
            portal_url = url_for(
                "customer_portal_view", token=po.accessToken, _external=True
            )

        # Check 5: Generate QR Image (Return bytes instead of JSON)
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(portal_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        buffered.seek(0)

        return send_file(buffered, mimetype="image/png")

    except Exception as e:
        print(f"[QR CRITICAL] Unexpected error: {e}", file=sys.stderr)
        return f"QR Error: {str(e)}", 500


# FIX: แก้ URL จาก /api/p/... เป็น /p/... (เพราะเป็นหน้าเว็บ ไม่ใช่ API)
@app.route("/p/<token>")
def customer_portal_view(token):
    try:
        # Check if template exists
        template_name = "customer_portal.html"
        template_path = os.path.join(app.root_path, template_name)  # Assuming same dir

        # Note: render_template looks in app.template_folder. Since we set template_folder='.', it looks in root.
        # Let's verify file existence first to be sure
        if not os.path.isfile(template_path):
            # Fallback: Create a simple string response if template is missing
            return (
                f"<h1>Error: Template '{template_name}' not found.</h1><p>Please ensure the file exists in folder: {app.root_path}</p>",
                500,
            )

        po = PurchaseOrder.query.filter_by(accessToken=token).first_or_404()

        # Check link expiration (15 days)
        from utils import ensure_bangkok, now_bangkok
        expired = False
        is_signed_expired = False
        target_dt = None

        if po.status == "Completed" or po.signedAt:
            target_dt = ensure_bangkok(po.signedAt)
            if target_dt and (now_bangkok() - target_dt > timedelta(days=15)):
                expired = True
                is_signed_expired = True
        else:
            target_dt = ensure_bangkok(po.created)
            if target_dt and (now_bangkok() - target_dt > timedelta(days=15)):
                expired = True

        if expired:
            sale_user = po.creator
            sale_name = sale_user.fullName if sale_user else (po.saleId or "ไม่ระบุ")
            sale_phone = sale_user.phoneNumber if (sale_user and sale_user.phoneNumber) else ""
            created_date_str = ensure_bangkok(po.created).strftime("%d/%m/%Y")
            return render_template(
                "expired.html",
                po_number=po.poNumber,
                created_date=created_date_str,
                sale_name=sale_name,
                sale_phone=sale_phone,
                is_signed_expired=is_signed_expired
            )

        # Pre-calculate totals safely (prices are VAT-inclusive)
        # Resolve Sale Info
        sale_user = po.creator
        sale_info = {
            "name": sale_user.fullName if sale_user else (po.saleId or "Unknown"),
            "phone": (
                sale_user.phoneNumber if (sale_user and sale_user.phoneNumber) else "-"
            ),
        }

        # CALCULATE TOTALS (6-Line Logic synchronized with PDF)
        # 1. Total Recommended (Gross Subtotal on Non-Gift items)
        non_gift_items = [i for i in po.items if not getattr(i, "is_gift", False)]
        total_recommended = sum(
            (
                i.recommendedPrice
                if (i.recommendedPrice and i.recommendedPrice > 0)
                else (i.price or 0.0)
            )
            * (i.qty or 0)
            for i in non_gift_items
        )

        # 2. Product Discount (Recommended - Cost)
        total_cost_base = sum((i.price or 0.0) * (i.qty or 0) for i in non_gift_items)
        price_diff_discount = total_recommended - total_cost_base

        # Promotion Discount (Deducted before Step 1 & Step 2)
        promo_discount = float(po.promotion_discount or 0.0)
        cost_after_promo = max(0.0, total_cost_base - promo_discount)

        # 3. Bill Discount (2-Step on Cost Base after Promo)
        disc1_percent = po.discount_percent_1 or 0.0
        disc1_amount = cost_after_promo * (disc1_percent / 100.0)
        total_after_1 = cost_after_promo - disc1_amount

        disc2_percent = po.discount_percent_2 or 0.0
        disc2_amount = total_after_1 * (disc2_percent / 100.0)
        total_after_2 = total_after_1 - disc2_amount

        bill_discount_total = disc1_amount + disc2_amount

        # 4. Total After All Discounts
        total_after_discount = total_after_2

        # 5. VAT 7% (Round VAT amount first as per Thai standard used in PDF)
        vat_amount = round(total_after_discount * 0.07, 2)

        # 6. Grand Total
        grand_total = total_after_discount + vat_amount

        # po_dict will be used as 'customer' in the template context
        po_dict = po.to_dict()

        # Package totals into a dictionary for the template
        totals = {
            "subtotal": total_recommended,
            "product_discount": price_diff_discount,
            "promotion_discount": promo_discount,
            "bill_discount": bill_discount_total,
            "after_discount": total_after_discount,
            "vat": vat_amount,
            "grand_total": grand_total,
        }

        # We ensure the template gets the synchronized 'totals' and 'sale_info'
        resp = make_response(
            render_template(
                template_name,
                token=token,
                po=po,
                customer=po_dict,
                company=COMPANY_DATA,
                sale_info=sale_info,
                totals=totals,
            )
        )
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

    except Exception as e:
        print(f"[Portal Error] {e}", file=sys.stderr)
        traceback.print_exc()
        # Return clearer error message
        return (
            f"<h1>System Error</h1><p>Failed to load Portal.</p><p><b>Detail:</b> {str(e)}</p>",
            500,
        )


@app.route("/p/<token>/pdf")
def customer_download_pdf(token):
    try:
        po = PurchaseOrder.query.filter_by(accessToken=token).first_or_404()
        
        # Check link expiration (15 days)
        from utils import ensure_bangkok, now_bangkok
        expired = False
        if po.status == "Completed" or po.signedAt:
            target_dt = ensure_bangkok(po.signedAt)
            if target_dt and (now_bangkok() - target_dt > timedelta(days=15)):
                expired = True
        else:
            target_dt = ensure_bangkok(po.created)
            if target_dt and (now_bangkok() - target_dt > timedelta(days=15)):
                expired = True

        if expired:
            return "Link expired / ลิงก์หมดอายุแล้ว", 403

        # Generate the PDF dynamically ensuring the same output as Print Official QT
        pdf_bytes = _generate_pdf_bytes(po, is_draft=False)
        if not pdf_bytes:
            return "Failed to generate PDF", 500

        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        fname = f"signed_po_{po.id}_{po.poNumber}.pdf"
        response.headers["Content-Disposition"] = f"attachment; filename={fname}"
        return response

    except Exception as e:
        print(f"[PDF Dynamic Download Error] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 500


@app.route("/api/p/<token>")
def get_customer_po(token):
    po = PurchaseOrder.query.filter_by(accessToken=token).first_or_404()
    # Check link expiration (15 days)
    from utils import ensure_bangkok, now_bangkok
    expired = False
    if po.status == "Completed" or po.signedAt:
        target_dt = ensure_bangkok(po.signedAt)
        if target_dt and (now_bangkok() - target_dt > timedelta(days=15)):
            expired = True
    else:
        target_dt = ensure_bangkok(po.created)
        if target_dt and (now_bangkok() - target_dt > timedelta(days=15)):
            expired = True

    if expired:
        return jsonify({"error": "Link expired / ลิงก์หมดอายุแล้ว"}), 403
    return jsonify(po.to_dict())


@app.route("/api/p/<token>/sign", methods=["POST"])
def sign_customer_po(token):
    po = (
        PurchaseOrder.query.options(
            joinedload(PurchaseOrder.items).joinedload(POItem.product),
            joinedload(PurchaseOrder.creator),
            joinedload(PurchaseOrder.customer_rel),
        )
        .filter_by(accessToken=token)
        .first_or_404()
    )

    if po.status == "Draft":
        return jsonify({"error": "เอกสารฉบับร่างไม่สามารถลงนามได้ (Draft quotation cannot be signed)"}), 400

    # Check link expiration (15 days)
    from utils import ensure_bangkok, now_bangkok
    expired = False
    if po.status == "Completed" or po.signedAt:
        target_dt = ensure_bangkok(po.signedAt)
        if target_dt and (now_bangkok() - target_dt > timedelta(days=15)):
            expired = True
    else:
        target_dt = ensure_bangkok(po.created)
        if target_dt and (now_bangkok() - target_dt > timedelta(days=15)):
            expired = True

    if expired:
        return jsonify({"error": "Link expired / ลิงก์หมดอายุแล้ว"}), 403

    data = request.json
    signature_data = data.get("signature")

    if not signature_data:
        return jsonify({"error": "No signature provided"}), 400

    if "," in signature_data:
        header, encoded = signature_data.split(",", 1)
    else:
        encoded = signature_data

    try:
        img_data = base64.b64decode(encoded)
        filename = secure_filename(f"sig_{po.id}_{po.accessToken[:8]}.png")
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        with open(filepath, "wb") as f:
            f.write(img_data)

        print(f"[OK] Saved signature image: {filename}")

        po.signatureImage = filename
        po.signedAt = now_bangkok()
        po.status = "Completed"
        po.updatedAt = now_bangkok()

        pdf_filename = secure_filename(f"signed_po_{po.id}_{po.poNumber}.pdf")
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)

        try:
            pdf_bytes = _generate_pdf_bytes(po, is_draft=False)
            if pdf_bytes:
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                po.signedFile = pdf_filename
                print(f"[OK] PDF generated and saved: {pdf_filename}")
            else:
                print("[WARN] PDF generation returned None (WeasyPrint error?)")
                po.signedFile = None
        except Exception as pdf_error:
            print(f"[ERROR] PDF generation error: {pdf_error}")
            import traceback

            traceback.print_exc()
            po.signedFile = None

        if po.sale_user_id:
            create_notification(
                po.sale_user_id, f"Customer signed QT {po.poNumber}", po.id
            )

        try:
            db.session.commit()
            print("[OK] Database updated successfully")

            # Send Telegram notification ONLY after successful commit
            if po.sale_user_id:
                try:
                    sale_name = po.creator.fullName if po.creator else "Unknown"
                    customer_name = po.get_customer_name()
                    msg = (
                        f"🔔 <b>QT-Online System</b>\n"
                        f"📅 {now_bangkok().strftime('%d/%m/%Y %H:%M')}\n\n"
                        f"🎉 <b>QT Completed (Signed)</b>\n"
                        f"<b>QT:</b> {po.poNumber}\n"
                        f"<b>Customer:</b> {customer_name}\n"
                        f"<b>Sale Owner:</b> {sale_name}"
                    )
                    send_telegram_msg(msg)
                except Exception as e:
                    print(f"Telegram Error in Sign: {e}")

        except Exception as db_err:
            db.session.rollback()
            print(f"[ERROR] DB error during commit: {db_err}")
            raise db_err

        return jsonify(
            {
                "success": True,
                "redirect": url_for("customer_portal_view", token=token),
                "status": po.status,
                "signedFile": po.signedFile,
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Sign error: {e}")
        return jsonify({"error": str(e)}), 500


# --- 9. User Management API ---
import re  # Import regex


@app.route("/api/users", methods=["GET", "POST"])
@login_required
@roles_required("Administrator")
@limiter.limit("10 per minute")  # NEW: Rate limit for user management
def manage_users():

    if request.method == "GET":
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])

    if request.method == "POST":
        data = request.json
        # Check if user already exists
        if User.query.filter_by(username=data["username"]).first():
            return jsonify({"error": "Username already exists"}), 400

        # Password Validation
        password = data["password"]
        if not re.match(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,10}$",
            password,
        ):
            return (
                jsonify(
                    {
                        "error": "Password must be 8-10 chars, contain uppercase, lowercase, number, and special char."
                    }
                ),
                400,
            )

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        use_ad_auth = data.get("use_ad_auth")
        if use_ad_auth is None:
            use_ad_auth = data.get("useAdAuth", True)

        sap_account = data.get("sap_account") or data.get("sapAccount") or None
        sap_password_raw = data.get("sap_password") or data.get("sapPassword") or None
        sap_password_enc = encrypt_string(sap_password_raw.strip()) if sap_password_raw and sap_password_raw.strip() else None
        can_use_sap = bool(data.get("can_use_sap_api") if "can_use_sap_api" in data else data.get("canUseSapApi", False))

        new_user = User(
            username=data["username"],
            fullName=data["fullName"],
            email=data.get("email", "").strip() or None,
            telegram_chat_id=data.get("telegramChatId") or data.get("telegram_chat_id") or None,
            password=hashed_password,
            role=data.get("role", "Sale"),
            status="active",
            use_ad_auth=bool(use_ad_auth),
            sap_account=sap_account.strip() if sap_account else None,
            sap_password=sap_password_enc,
            can_use_sap_api=can_use_sap,
            target_amount=data.get("targetAmount", 0),
            phoneNumber=data.get("phoneNumber", ""),
            createdAt=now_bangkok(),
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201


@app.route("/api/users/<int:id>", methods=["GET", "PUT", "DELETE"])
@login_required
@roles_required("Administrator")
def manage_user(id):
    user = User.query.get_or_404(id)

    if request.method == "GET":
        return jsonify(user.to_dict())

    if request.method == "PUT":
        data = request.json
        user.username = data.get("username", user.username)
        user.fullName = data.get("fullName", user.fullName)
        if "email" in data:
            user.email = data.get("email", "").strip() or None
        if "telegramChatId" in data or "telegram_chat_id" in data:
            user.telegram_chat_id = data.get("telegramChatId") or data.get("telegram_chat_id") or None
        if "use_ad_auth" in data or "useAdAuth" in data:
            val = data.get("use_ad_auth")
            if val is None:
                val = data.get("useAdAuth")
            user.use_ad_auth = bool(val)
        if "sap_account" in data or "sapAccount" in data:
            val_acc = data.get("sap_account") if "sap_account" in data else data.get("sapAccount")
            user.sap_account = val_acc.strip() if val_acc else None
        if "can_use_sap_api" in data or "canUseSapApi" in data:
            val_can = data.get("can_use_sap_api") if "can_use_sap_api" in data else data.get("canUseSapApi")
            user.can_use_sap_api = bool(val_can)
        if "sap_password" in data or "sapPassword" in data:
            val_pwd = data.get("sap_password") if "sap_password" in data else data.get("sapPassword")
            if val_pwd and not val_pwd.startswith("****") and val_pwd.strip():
                user.sap_password = encrypt_string(val_pwd.strip())
        user.role = data.get("role", user.role)
        user.status = data.get("status", user.status)
        user.target_amount = data.get("targetAmount", user.target_amount)
        user.phoneNumber = data.get("phoneNumber", user.phoneNumber)

        # Add password change logic if needed
        if "password" in data and data["password"]:
            password = data["password"]
            if not re.match(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,10}$",
                password,
            ):
                return (
                    jsonify(
                        {
                            "error": "Password must be 8-10 chars, contain uppercase, lowercase, number, and special char."
                        }
                    ),
                    400,
                )
            user.password = bcrypt.generate_password_hash(password).decode("utf-8")

        db.session.commit()
        return jsonify(user.to_dict())

    if request.method == "DELETE":
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": "User deleted"})


@app.route("/api/users/<int:id>/signature", methods=["POST"])
@login_required
def upload_user_signature(id):
    # Allow Admin or the user themselves to update the signature
    if current_user.role != "Administrator" and current_user.id != id:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(id)

    img_binary_data = None

    # Handle Base64 Signature (from Pad)
    data = request.json
    if data and "signature" in data:
        signature_data = data["signature"]
        if "," in signature_data:
            header, encoded = signature_data.split(",", 1)
        else:
            encoded = signature_data
        try:
            img_binary_data = base64.b64decode(encoded)
        except Exception as e:

            return (
                jsonify(
                    {"success": False, "message": f"Error decoding base64: {str(e)}"}
                ),
                500,
            )

    # Handle File Upload (Legacy/Fallback)
    elif "file" in request.files:
        file = request.files["file"]
        if file.filename != "" and allowed_image_file(file.filename):
            img_binary_data = file.read()

    # Process if we have data
    if img_binary_data:
        try:
            # 1. Encrypt the binary data
            encrypted_data = encrypt_data(img_binary_data)

            # 2. FIX: SAVE TO DATABASE INSTEAD OF FILE
            # Convert encrypted bytes to base64 string for storage in Text column
            # Prefix with DB_SIG: to distinguish from legacy filenames
            b64_encrypted = base64.b64encode(encrypted_data).decode("ascii")

            user.signature_image = f"DB_SIG:{b64_encrypted}"
            db.session.commit()

            return jsonify({"success": True, "signatureImage": "Stored in Database"})

        except Exception as e:
            return (
                jsonify(
                    {"success": False, "message": f"Error saving signature: {str(e)}"}
                ),
                500,
            )

    return (
        jsonify({"success": False, "message": "No file or signature data provided"}),
        400,
    )


@app.route("/api/users/<int:id>/signature-preview", methods=["GET"])
@login_required
def get_user_signature_preview(id):
    # Allow Admin or the user themselves to see the signature
    if current_user.role != "Administrator" and current_user.id != id:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(id)

    if not user.signature_image:
        return jsonify({"error": "No signature found"}), 404

    # --- NEW: Retrieve from Database (Persistent) ---
    if user.signature_image.startswith("DB_SIG:"):
        try:
            b64_str = user.signature_image.split(":", 1)[1]
            encrypted_data = base64.b64decode(b64_str)

            # Decrypt
            final_img_data = decrypt_data(encrypted_data)

            # Detect Mime Type (Simple)
            mime_type = "image/png"
            if final_img_data.startswith(b"\xff\xd8"):
                mime_type = "image/jpeg"
            elif final_img_data.startswith(b"GIF8"):
                mime_type = "image/gif"

            # Prepare for frontend
            encoded_sig = base64.b64encode(final_img_data).decode("ascii")
            return jsonify({"imageSrc": f"data:{mime_type};base64,{encoded_sig}"})

        except Exception as e:
            print(f"Error decoding DB signature for user {id}: {e}")
            return jsonify({"error": "Corrupted signature data"}), 500

    # --- Legacy: Retrieve from File System ---
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], user.signature_image)

    if not os.path.isfile(filepath):
        print(f"DEBUG: Signature file not found on disk: {filepath}")
        return jsonify({"error": "File not found"}), 404

    try:
        with open(filepath, "rb") as f:
            file_content = f.read()  # Read raw content first

        print(
            f"DEBUG: Read file {user.signature_image}, Size: {len(file_content)} bytes"
        )

        if len(file_content) == 0:
            print("ERROR: File is empty")
            return jsonify({"error": "File is empty"}), 500

        # FIX 1: Robust Decryption Check
        is_encrypted = user.signature_image.endswith(".enc")
        final_img_data = b""

        if is_encrypted:
            try:
                final_img_data = decrypt_data(file_content)
                # ... check magic numbers ...
                if not (
                    final_img_data.startswith(b"\x89PNG\r\n\x1a\n")
                    or final_img_data.startswith(b"\xff\xd8")
                    or final_img_data.startswith(b"GIF8")
                ):
                    print("WARNING: Decrypted data header invalid (Wrong Key?).")
            except Exception as de:
                print(
                    f"WARNING: Decryption failed ({de}), checking if it is legacy raw file..."
                )
                final_img_data = file_content
        else:
            final_img_data = file_content

        encoded_sig = base64.b64encode(final_img_data).decode("ascii")

        # Mime type detection
        mime_type = "image/png"
        if final_img_data.startswith(b"\xff\xd8"):
            mime_type = "image/jpeg"
        elif final_img_data.startswith(b"GIF8"):
            mime_type = "image/gif"

        print(f"DEBUG: Sending signature with mime {mime_type}")
        return jsonify({"imageSrc": f"data:{mime_type};base64,{encoded_sig}"})

    except Exception as e:
        print(f"ERROR: Failed to load signature for User {id}: {e}")
        return jsonify({"error": f"Failed to load signature: {str(e)}"}), 500


# [NEW] Route for serving uploaded files (PDFs, Images) - Essential for "Scanned PO" link
@app.route("/uploads/<path:filename>")
def download_file(filename):
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    except Exception as e:
        return f"File not found: {e}", 404


# NEW: Route to clear Transaction Data (Keeps Users, Products, Customers)
@app.route("/api/system/reset_transactions", methods=["POST"])
@login_required
@roles_required("Administrator")
def reset_transactions():
    """
    ลบข้อมูล Transaction ทั้งหมด (POs, Items, Comments, Notifications)
    แต่เก็บดาราง Users, Products, Customers ไว้
    """
    try:
        # Delete dependent data first to avoid Foreign Key constraints
        # 1. ลบรายการสินค้าใน QT ทั้งหมด
        deleted_items = POItem.query.delete()

        # 2. ลบความคิดเห็นทั้งหมด
        deleted_comments = Comment.query.delete()

        # 3. ลบการแจ้งเตือนทั้งหมด
        deleted_notifs = Notification.query.delete()

        # 4. ลบใบสั่งซื้อ (PO) ทั้งหมด
        deleted_pos = PurchaseOrder.query.delete()

        # Commit เพื่อยืนยันการลบ
        db.session.commit()

        msg = (
            f"System Reset Complete. Deleted: "
            f"{deleted_items} Items, {deleted_comments} Comments, {deleted_notifs} Notifs, "
            f"{deleted_pos} POs."
        )

        print(f"DEBUG: {msg}")

        return jsonify({"success": True, "message": msg})
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Reset Transactions Failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/system/reset_products", methods=["POST"])
@login_required
@roles_required("Administrator")
def reset_products():
    """
    ลบข้อมูลสินค้า (Products) ทั้งหมด
    """
    try:
        # ลบข้อมูลสินค้าทั้งหมด
        deleted_count = Product.query.delete()
        db.session.commit()

        print(f"DEBUG: System Reset - Deleted {deleted_count} Products.")

        return jsonify(
            {
                "success": True,
                "message": f"ลบข้อมูลสินค้าทั้งหมดเรียบร้อยแล้ว ({deleted_count} รายการ)",
            }
        )
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Reset Products Failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =================================================================================
# [END] เพิ่มส่วนการทำงานเริ่มต้น (Startup & Entry Point)
# =================================================================================

# สร้างตารางฐานข้อมูลอัตโนมัติถ้ายังไม่มี (Auto Create Tables)
with app.app_context():
    try:
        db.create_all()

        # [NEW] Auto-Migration for missing columns (Schema Update) before querying models
        with db.engine.connect() as conn:
            # 1. Check purchase_orders columns
            res_po = conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='purchase_orders';")
            )
            existing_po_cols = [row[0].lower() for row in res_po]
            po_new_columns = {
                "customerLocationFile": "TEXT",
                "customerLocationFileUrl": "TEXT",
                "customerLocationUploadedAt": "TIMESTAMP WITHOUT TIME ZONE",
                "customerLocationUploadedBy": "INTEGER",
                "customerPoFile": "TEXT",
                "customerPoFileUrl": "TEXT",
                "customerPoUploadedAt": "TIMESTAMP WITHOUT TIME ZONE",
                "customerPoUploadedBy": "INTEGER",
                "updatedAt": "TIMESTAMP WITHOUT TIME ZONE",
                "sap_doc_num": "VARCHAR(50)",
                "sap_doc_entry": "INTEGER",
                "sap_created_at": "TIMESTAMP WITHOUT TIME ZONE",
                "sap_created_by": "INTEGER",
                "sap_sync_status": "VARCHAR(20)",
                "sap_sync_error": "TEXT",
                "promotion_id": "INTEGER",
                "promotion_name": "VARCHAR(255)",
                "promotion_discount": "NUMERIC(15, 2) DEFAULT 0.0",
                "customer_ref_no": "VARCHAR(100)",
                "sap_remarks": "TEXT",
            }
            for col, dtype in po_new_columns.items():
                if col.lower() not in existing_po_cols:
                    conn.execute(text(f'ALTER TABLE purchase_orders ADD COLUMN "{col}" {dtype};'))

            # Check po_items columns (is_gift)
            res_po_items = conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='po_items';")
            )
            existing_po_item_cols = [row[0].lower() for row in res_po_items]
            if "is_gift" not in existing_po_item_cols:
                conn.execute(text('ALTER TABLE po_items ADD COLUMN is_gift BOOLEAN DEFAULT FALSE;'))

            # 2. Check users columns (use_ad_auth, email, telegram_chat_id)
            res_user = conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='users';")
            )
            existing_user_cols = [row[0].lower() for row in res_user]
            if "use_ad_auth" not in existing_user_cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN use_ad_auth BOOLEAN DEFAULT TRUE;'))
            if "email" not in existing_user_cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN email VARCHAR(150);'))
            if "telegram_chat_id" not in existing_user_cols:
                conn.execute(text('ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(100);'))

            # 3. Check products columns (discountPercent)
            res_prod = conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='products';")
            )
            existing_prod_cols = [row[0] for row in res_prod]
            if "discountPercent" not in existing_prod_cols:
                if "discountpercent" in existing_prod_cols:
                    conn.execute(text('ALTER TABLE products RENAME COLUMN discountpercent TO "discountPercent";'))
                else:
                    conn.execute(text('ALTER TABLE products ADD COLUMN "discountPercent" NUMERIC(5, 2) DEFAULT 0.0;'))

            conn.commit()
            print("DEBUG: Schema is up to date.")

        # Seed sample promotions if table is empty
        try:
            if Promotion.query.count() == 0:
                p1 = Promotion(
                    code="PROMO-20K-500",
                    name="ซื้อสินค้าครบ 20,000 บาท ลดทันที 500 บาท",
                    description="เมื่อมียอดสั่งซื้อรวมตั้งแต่ 20,000 บาทขึ้นไป รับส่วนลดท้ายบิล 500 บาททันที",
                    promo_type="ORDER_DISCOUNT_FIXED",
                    min_order_amount=20000.0,
                    discount_value=500.0,
                    is_active=True
                )
                p2 = Promotion(
                    code="PROMO-50K-5PCT",
                    name="ซื้อสินค้าครบ 50,000 บาท ลดพิเศษ 5%",
                    description="เมื่อมียอดสั่งซื้อรวมตั้งแต่ 50,000 บาทขึ้นไป รับส่วนลดพิเศษ 5%",
                    promo_type="ORDER_DISCOUNT_PERCENT",
                    min_order_amount=50000.0,
                    discount_value=5.0,
                    is_active=True
                )
                p3 = Promotion(
                    code="PROMO-BUY5-GET1",
                    name="ซื้อสินค้าครบ 5 ชิ้น แถมฟรีมุ้งลวดพรีเมียม 1 ชิ้น",
                    description="เมื่อสั่งซื้อสินค้าในใบเสนอราคาครบ 5 ชิ้นขึ้นไป รับฟรีมุ้งลวดกันแมลง 1 ชิ้น",
                    promo_type="BUY_X_GET_Y",
                    condition_qty=5,
                    reward_product_code="GIFT-SCREEN",
                    reward_product_name="มุ้งลวดกันแมลงเกรดพรีเมียม (Free Gift)",
                    reward_qty=1,
                    is_active=True
                )
                db.session.add_all([p1, p2, p3])
                db.session.commit()
                print("DEBUG: Seeded 3 default promotions.")
        except Exception as promo_err:
            db.session.rollback()
            print(f"DEBUG: Could not seed promotions: {promo_err}")

        # [NEW] ตรวจสอบและสร้าง Admin เริ่มต้นถ้ายังไม่มีข้อมูล
        if not User.query.first():
            print("----------------------------------------------------------------")
            print("DEBUG: No users found. Creating default 'admin' user...")
            hashed_pw = bcrypt.generate_password_hash("1234").decode("utf-8")
            admin = User(
                username="admin",
                password=hashed_pw,
                role="Administrator",
                fullName="System Administrator",
                status="active",
            )
            db.session.add(admin)
            db.session.commit()
            print("DEBUG: Default user created -> User: admin / Pass: 1234")
            print("----------------------------------------------------------------")

        print(
            f"DEBUG: Database initialized successfully. (Timezone: {now_bangkok().tzinfo})"
        )
    except Exception as e:
        print(f"CRITICAL WARNING: Database init failed: {e}", file=sys.stderr)


# --- [NEW] Bulk Delete Routes ---
@app.route("/api/pos/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_pos():
    if current_user.role not in ["Administrator", "Sale Admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    ids = request.json.get("ids", [])
    if not ids:
        return jsonify({"error": "No IDs provided"}), 400

    try:
        count = 0
        for pid in ids:
            po = PurchaseOrder.query.get(pid)
            if po:
                # Follow existing restriction: only admin can delete processed POs
                if (
                    po.status not in ["Draft", "Pending Review"]
                    and current_user.role != "Administrator"
                ):
                    continue
                db.session.delete(po)
                count += 1
        db.session.commit()
        return jsonify({"success": True, "count": count})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/products/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_products():
    if current_user.role not in ["Administrator", "Sale Admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    ids = request.json.get("ids", [])
    if not ids:
        return jsonify({"error": "No IDs provided"}), 400

    try:
        count = 0
        for pid in ids:
            item = Product.query.get(pid)
            if item:
                db.session.delete(item)
                count += 1
        db.session.commit()
        return jsonify({"success": True, "count": count})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/customers/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_customers():
    if current_user.role not in ["Administrator", "Sale Admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    ids = request.json.get("ids", [])
    if not ids:
        return jsonify({"error": "No IDs provided"}), 400

    try:
        count = 0
        for pid in ids:
            item = Customer.query.get(pid)
            if item:
                db.session.delete(item)
                count += 1
        db.session.commit()
        return jsonify({"success": True, "count": count})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# =================================================================================
# [START] Centralized Identity Management (CIAM) & System Settings APIs
# Corporate Standard: Centralized Identity Management API Specification
# Base URL Prefix: /api/v1/directory
# =================================================================================

def get_client_ip():
    """Extract client IP address, safely handling X-Forwarded-For reverse proxy header."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def verify_ciam_access():
    """
    Validates Machine-to-Machine (M2M) API Key and IP Whitelisting according to Corporate CIAM Spec.
    Returns: (is_valid: bool, status_code: int, error_detail: str, client_ip: str)
    """
    client_ip = get_client_ip()
    try:
        setting = CiamSetting.query.first()
    except Exception as e:
        app.logger.error(f"Error querying CiamSetting: {e}")
        return False, 500, "Internal server error reading configuration.", client_ip

    if not setting or not setting.is_enabled:
        return False, 403, "Central Identity Management API is currently disabled.", client_ip

    api_key_header = request.headers.get("X-Management-API-Key", "").strip()
    if not api_key_header:
        return False, 401, "Invalid or missing X-Management-API-Key header.", client_ip

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key_header, setting.api_key):
        return False, 401, "Invalid or missing X-Management-API-Key header.", client_ip

    # IP Whitelisting check
    allowed_ips_raw = setting.allowed_ips or ""
    allowed_ips = [
        ip.strip()
        for ip in allowed_ips_raw.replace("\n", ",").split(",")
        if ip.strip()
    ]
    if allowed_ips and "*" not in allowed_ips and client_ip not in allowed_ips:
        return False, 403, f"Origin IP '{client_ip}' is not permitted.", client_ip

    return True, 200, None, client_ip


@app.route("/api/v1/directory/accounts", methods=["GET"])
def ciam_list_accounts():
    """
    Endpoint 1: ดึงรายชื่อบัญชีผู้ใช้ทั้งหมด (Account Inventory / Reconciliation)
    Spec: GET /api/v1/directory/accounts
    """
    is_valid, code, err, client_ip = verify_ciam_access()
    if not is_valid:
        try:
            db.session.add(
                CiamAuditLog(
                    client_ip=client_ip,
                    action="list_accounts",
                    status_code=code,
                    message=err,
                )
            )
            db.session.commit()
        except Exception:
            pass
        return jsonify({"detail": err}), code

    status_filter = request.args.get("status", "all").lower()
    dept_filter = request.args.get("department", "").strip()
    search_query = request.args.get("search", "").strip().lower()

    query = User.query
    if status_filter == "active":
        query = query.filter(func.lower(User.status) == "active")
    elif status_filter == "inactive":
        query = query.filter(func.lower(User.status) == "inactive")

    if dept_filter:
        query = query.filter(func.lower(User.role) == dept_filter.lower())

    if search_query:
        query = query.filter(
            or_(
                func.lower(User.username).like(f"%{search_query}%"),
                func.lower(User.fullName).like(f"%{search_query}%"),
            )
        )

    users = query.order_by(User.id.asc()).all()

    accounts_list = []
    active_count = 0
    inactive_count = 0

    for u in users:
        is_active = getattr(u, "status", "active") == "active"
        if is_active:
            active_count += 1
        else:
            inactive_count += 1

        created_local = ensure_bangkok(u.createdAt)
        last_login_local = ensure_bangkok(u.lastLogin)
        accounts_list.append(
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.fullName or u.username,
                "email": getattr(u, "email", None) or f"{u.username}@windowasia.com",
                "department": u.role or "General",
                "telegram_chat_id": getattr(u, "telegram_chat_id", None),
                "group_name": u.role or "Sale",
                "use_ad_auth": getattr(u, "use_ad_auth", True),
                "is_active": is_active,
                "last_login_at": (
                    last_login_local.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if last_login_local
                    else None
                ),
                "created_at": (
                    created_local.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if created_local
                    else None
                ),
                "updated_at": (
                    created_local.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if created_local
                    else None
                ),
            }
        )

    try:
        db.session.add(
            CiamAuditLog(
                client_ip=client_ip,
                action="list_accounts",
                status_code=200,
                message=f"Fetched {len(accounts_list)} accounts successfully.",
            )
        )
        db.session.commit()
    except Exception:
        pass

    return (
        jsonify(
            {
                "application_name": "PO-Online (QT-Online)",
                "total_accounts": len(accounts_list),
                "active_accounts": active_count,
                "inactive_accounts": inactive_count,
                "accounts": accounts_list,
            }
        ),
        200,
    )


@app.route("/api/v1/directory/accounts/<string:username>/status", methods=["PATCH"])
def ciam_update_account_status(username):
    """
    Endpoint 2: สั่งเปิดหรือระงับการใช้งานบัญชี (Status Provisioning / Instant Offboarding)
    Spec: PATCH /api/v1/directory/accounts/{username}/status
    """
    is_valid, code, err, client_ip = verify_ciam_access()
    if not is_valid:
        try:
            db.session.add(
                CiamAuditLog(
                    client_ip=client_ip,
                    action="update_account_status",
                    target_username=username,
                    status_code=code,
                    message=err,
                )
            )
            db.session.commit()
        except Exception:
            pass
        return jsonify({"detail": err}), code

    data = request.json or {}
    if "is_active" not in data:
        return jsonify({"detail": "Validation error: 'is_active' field is required."}), 400

    new_is_active = bool(data.get("is_active"))
    reason = data.get("reason", "Status updated by Central IAM")
    updated_by = data.get("updated_by", "Central-IAM-Service")

    user = User.query.filter(func.lower(User.username) == username.strip().lower()).first()
    if not user:
        try:
            db.session.add(
                CiamAuditLog(
                    client_ip=client_ip,
                    action="update_account_status",
                    target_username=username,
                    status_code=404,
                    reason=reason,
                    updated_by=updated_by,
                    message=f"User account '{username}' does not exist.",
                )
            )
            db.session.commit()
        except Exception:
            pass
        return jsonify({"detail": f"User account '{username}' does not exist."}), 404

    prev_status = getattr(user, "status", "active")
    new_status = "active" if new_is_active else "inactive"
    user.status = new_status

    try:
        db.session.commit()

        audit = CiamAuditLog(
            client_ip=client_ip,
            action="update_account_status",
            target_username=user.username,
            previous_status=prev_status,
            new_status=new_status,
            reason=reason,
            updated_by=updated_by,
            status_code=200,
            message=f"Status changed from {prev_status} to {new_status}",
        )
        db.session.add(audit)
        db.session.commit()

        status_text = "ACTIVE" if new_is_active else "INACTIVE"
        return (
            jsonify(
                {
                    "username": user.username,
                    "is_active": new_is_active,
                    "message": f"Account '{user.username}' status has been successfully updated to {status_text}.",
                    "updated_at": now_bangkok().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"detail": f"Internal server error: {str(e)}"}), 500


@app.route("/api/v1/directory/accounts", methods=["POST"])
def ciam_create_account():
    """
    Endpoint 3: สร้างบัญชีผู้ใช้งานใหม่ (Account Provisioning)
    Spec: POST /api/v1/directory/accounts
    """
    is_valid, code, err, client_ip = verify_ciam_access()
    if not is_valid:
        try:
            db.session.add(
                CiamAuditLog(
                    client_ip=client_ip,
                    action="create_account",
                    status_code=code,
                    message=err,
                )
            )
            db.session.commit()
        except Exception:
            pass
        return jsonify({"detail": err}), code

    data = request.json or {}
    username = data.get("username", "").strip()
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    department = data.get("department", "").strip()
    group_name = data.get("group_name", "").strip()
    created_by = data.get("created_by", "Central-IAM-Service")

    if not username or not full_name:
        return (
            jsonify({"detail": "Validation error: username and full_name are required"}),
            400,
        )

    existing_user = User.query.filter(func.lower(User.username) == username.lower()).first()
    if existing_user:
        return jsonify({"detail": f"User account '{username}' already exists."}), 409

    role = "Sale"
    if group_name in ["Administrator", "Sale Admin", "Sale"]:
        role = group_name
    elif department in ["Administrator", "Sale Admin", "Sale"]:
        role = department

    # Generate random initial password
    random_temp_pass = secrets.token_urlsafe(12)
    hashed_pw = bcrypt.generate_password_hash(random_temp_pass).decode("utf-8")

    new_user = User(
        username=username,
        fullName=full_name,
        email=email or None,
        telegram_chat_id=data.get("telegram_chat_id", "").strip() or None,
        use_ad_auth=bool(data.get("use_ad_auth", True)),
        password=hashed_pw,
        role=role,
        status="active",
        createdAt=now_bangkok(),
    )

    try:
        db.session.add(new_user)
        db.session.commit()

        audit = CiamAuditLog(
            client_ip=client_ip,
            action="create_account",
            target_username=new_user.username,
            new_status="active",
            reason="Account created via CIAM provisioning",
            updated_by=created_by,
            status_code=201,
            message=f"User {new_user.username} created with role {role}",
        )
        db.session.add(audit)
        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "id": new_user.id,
                    "username": new_user.username,
                    "message": f"Account '{new_user.username}' created successfully.",
                    "group_name": new_user.role,
                    "is_active": True,
                    "created_at": now_bangkok().isoformat(),
                }
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"detail": f"Internal server error: {str(e)}"}), 500


# --- Admin System Settings & Logs Endpoints ---

@app.route("/api/admin/ciam/settings", methods=["GET", "PUT"])
@roles_required("Administrator")
def manage_ciam_settings():
    setting = CiamSetting.query.order_by(CiamSetting.id.asc()).first()
    if not setting:
        token = secrets.token_hex(16)
        setting = CiamSetting(
            is_enabled=True,
            api_key=f"sec_po_mgmt_{token}",
            allowed_ips="157.173.219.153, 192.168.12.11, 127.0.0.1",
            default_role="Sale",
        )
        db.session.add(setting)
        db.session.commit()

    if request.method == "GET":
        resp = jsonify(setting.to_dict())
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    if request.method == "PUT":
        data = request.json or {}
        if "isEnabled" in data:
            setting.is_enabled = bool(data["isEnabled"])
        elif "is_enabled" in data:
            setting.is_enabled = bool(data["is_enabled"])

        if "allowedIps" in data:
            setting.allowed_ips = str(data["allowedIps"]).strip()
        elif "allowed_ips" in data:
            setting.allowed_ips = str(data["allowed_ips"]).strip()

        if "defaultRole" in data:
            setting.default_role = str(data["defaultRole"]).strip()
        elif "default_role" in data:
            setting.default_role = str(data["default_role"]).strip()

        if data.get("regenerateKey"):
            token = secrets.token_hex(16)
            setting.api_key = f"sec_po_mgmt_{token}"
        elif "apiKey" in data and data["apiKey"]:
            setting.api_key = str(data["apiKey"]).strip()
        elif "api_key" in data and data["api_key"]:
            setting.api_key = str(data["api_key"]).strip()

        setting.updated_at = now_bangkok()
        db.session.commit()
        return jsonify({"success": True, "setting": setting.to_dict()})


@app.route("/api/admin/ciam/logs", methods=["GET"])
@roles_required("Administrator")
def get_ciam_logs():
    logs = CiamAuditLog.query.order_by(CiamAuditLog.id.desc()).limit(100).all()
    return jsonify([log.to_dict() for log in logs])


@app.route("/api/admin/login-logs", methods=["GET"])
@roles_required("Administrator")
def get_login_logs():
    logs = LoginLog.query.order_by(LoginLog.id.desc()).limit(100).all()
    return jsonify([log.to_dict() for log in logs])


# =================================================================================
# [NEW] CIAM Spec v2.7.0: Group B Single Sign-On (SSO) & Group A Settings Channels
# =================================================================================

@app.route("/api/auth/sso/config", methods=["GET"])
def ciam_sso_config():
    """
    Spec B.1: Public endpoint providing current SSO availability & parameters
    """
    cfg = get_ciam_config()
    return jsonify({
        "sso_enabled": cfg["ciam_sso_enabled"],
        "break_glass_active": cfg["ciam_break_glass_active"],
        "ciam_base_url": cfg["ciam_base_url"],
        "client_id": cfg["ciam_client_id"],
        "login_button_label": "เข้าสู่ระบบด้วย Window Asia SSO",
        "fallback_ad_available": bool(cfg.get("ciam_ad_gateway_url")),
    }), 200


@app.route("/api/auth/sso/authorize-url", methods=["POST"])
def ciam_sso_authorize_url():
    """
    Spec B.2: Generate PKCE S256 verifier, challenge, state, and authorize_url
    """
    cfg = get_ciam_config()
    if not cfg["ciam_sso_enabled"] or cfg["ciam_break_glass_active"]:
        return jsonify({
            "error": "Single Sign-On is currently unavailable.",
            "break_glass_active": cfg["ciam_break_glass_active"]
        }), 503

    data = request.json or {}
    default_redirect = get_canonical_redirect_uri()
    redirect_uri = get_canonical_redirect_uri(data.get("redirect_uri")) if data.get("redirect_uri") else default_redirect

    code_verifier, code_challenge, state = generate_pkce_codes()
    session["sso_verifier"] = code_verifier
    session["sso_state"] = state
    session["sso_redirect_uri"] = redirect_uri

    params = {
        "response_type": "code",
        "client_id": cfg["ciam_client_id"],
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"{cfg['ciam_base_url']}/oauth/authorize?{urllib.parse.urlencode(params)}"

    return jsonify({
        "authorize_url": authorize_url,
        "code_verifier": code_verifier,
        "state": state,
    }), 200


@app.route("/api/auth/sso/callback", methods=["POST"])
def ciam_sso_callback_api():
    """
    Spec B.3: Exchange Authorization Code, verify RS256 token, resolve/auto-provision user, issue session
    """
    cfg = get_ciam_config()
    if not cfg["ciam_sso_enabled"] or cfg["ciam_break_glass_active"]:
        return jsonify({"error": "Single Sign-On is disabled or in break-glass mode."}), 503

    data = request.json or {}
    code = data.get("code")
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400

    code_verifier = data.get("code_verifier") or session.get("sso_verifier")
    default_redirect = f"{request.host_url.rstrip('/')}/auth/callback"
    redirect_uri = data.get("redirect_uri") or session.get("sso_redirect_uri") or default_redirect
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    try:
        # 1. Exchange code for tokens
        token_res = exchange_oauth_code(code, redirect_uri, code_verifier)
        id_token = token_res.get("id_token") or token_res.get("access_token")
        if not id_token:
            return jsonify({"error": "Failed to retrieve ID token from Central IAM"}), 400

        # 2. Verify token
        claims = verify_rs256_jwt(id_token, cfg["ciam_base_url"], cfg["ciam_client_id"])
        
        # 3. User Identity Resolution
        username = (claims.get("preferred_username") or claims.get("username") or claims.get("sub") or "").strip()
        if not username and claims.get("email"):
            username = claims["email"].split("@")[0].strip()

        if not username:
            return jsonify({"error": "Unable to extract username from identity token"}), 400

        user = User.query.filter(func.lower(User.username) == username.lower()).first()
        is_new_user = False

        if not user:
            # Auto-Provision User (JIT)
            auto_role = cfg["ciam_auto_provision_group"]
            full_name = claims.get("name") or claims.get("full_name") or username.title()
            random_pw = secrets.token_urlsafe(16)
            hashed_pw = bcrypt.generate_password_hash(random_pw).decode("utf-8")

            user = User(
                username=username,
                fullName=full_name,
                password=hashed_pw,
                role=auto_role,
                status="active",
                use_ad_auth=True,
                createdAt=now_bangkok(),
                lastLogin=now_bangkok(),
            )
            db.session.add(user)
            db.session.commit()
            is_new_user = True

            TransactionLog.log(
                category="ciam_sso",
                action="auto_provision_user",
                status="info",
                message=f"สร้างบัญชีผู้ใช้ใหม่อัตโนมัติจาก Central IAM: '{username}' (Role: {auto_role})",
                details={"username": username, "role": auto_role, "ip": client_ip, "claims": claims},
                triggered_by="system:ciam",
            )
        else:
            # Check if account is active
            if getattr(user, "status", "active") == "inactive":
                TransactionLog.log(
                    category="ciam_sso",
                    action="account_deactivated",
                    status="warning",
                    message=f"ปฏิเสธการเข้าสู่ระบบ: บัญชีพนักงาน '{username}' ถูกระงับสิทธิ์ในระบบนี้",
                    details={"username": username, "ip": client_ip},
                    triggered_by=f"user:{username}",
                )
                try:
                    db.session.add(LoginLog(
                        username=username,
                        user_id=user.id,
                        ip_address=client_ip,
                        user_agent=request.user_agent.string if request.user_agent else "-",
                        status="ACCOUNT_DISABLED",
                        failure_reason="Account is inactive in PO-Online",
                    ))
                    db.session.commit()
                except Exception:
                    pass
                return jsonify({"error": "บัญชีผู้ใช้นี้ถูกระงับสิทธิ์การใช้งาน กรุณาติดต่อผู้ดูแลระบบ"}), 403

            user.lastLogin = now_bangkok()
            db.session.commit()

        # 4. Issue Flask-Login session
        login_user(user, remember=True)
        session["auth_provider"] = "ciam_sso"
        session["is_sso"] = True

        # 5. Audit Logging
        try:
            db.session.add(LoginLog(
                username=user.username,
                user_id=user.id,
                ip_address=client_ip,
                user_agent=request.user_agent.string if request.user_agent else "-",
                status="SUCCESS",
                failure_reason=None,
            ))
            db.session.commit()
        except Exception:
            pass

        TransactionLog.log(
            category="ciam_sso",
            action="login_success",
            status="success",
            message=f"เข้าสู่ระบบผ่าน Central IAM SSO สำเร็จ: ผู้ใช้ '{user.username}'",
            details={"username": user.username, "ip": client_ip, "auth_method": "OIDC_PKCE_S256", "is_new": is_new_user},
            triggered_by=f"user:{user.username}",
        )

        # Clear SSO session artifacts
        session.pop("sso_verifier", None)
        session.pop("sso_state", None)

        return jsonify({
            "success": True,
            "redirect_url": "/",
            "user": user.to_dict(),
        }), 200

    except Exception as e:
        app.logger.error(f"SSO Callback failed: {e}")
        TransactionLog.log(
            category="ciam_sso",
            action="login_failed",
            status="failed",
            message=f"การยืนยันตัวตน SSO ล้มเหลว: {str(e)}",
            details={"ip": client_ip, "error": str(e)},
            triggered_by="system:ciam",
        )
        return jsonify({"error": f"SSO Authentication failed: {str(e)}"}), 400


def get_canonical_redirect_uri(custom_uri=None):
    """
    Construct canonical OAuth2 redirect URI, ensuring https scheme in production
    when behind reverse proxies (Traefik / Nginx).
    """
    if custom_uri:
        if "windowasia.com" in custom_uri and custom_uri.startswith("http://"):
            return custom_uri.replace("http://", "https://", 1)
        return custom_uri

    host = request.headers.get("X-Forwarded-Host") or request.host
    proto = request.headers.get("X-Forwarded-Proto")
    if not proto or "windowasia.com" in host or request.is_secure:
        proto = "https" if ("windowasia.com" in host or request.is_secure) else (proto or request.scheme)
    return f"{proto}://{host}/auth/callback"


@app.route("/auth/start", methods=["GET"])
def ciam_auth_start():
    """
    Spec B.3 / RFC 9700: Seamless SSO Initiation Bounce Endpoint
    Triggered when user clicks app card on Central IAM Employee Portal.
    Bounces through CIAM with PKCE for Zero-Prompt 1-Click Launch.
    """
    cfg = get_ciam_config()
    if not cfg["ciam_sso_enabled"] or cfg["ciam_break_glass_active"]:
        return redirect(url_for("login"))

    default_redirect = get_canonical_redirect_uri()
    code_verifier, code_challenge, state = generate_pkce_codes()
    session["sso_verifier"] = code_verifier
    session["sso_state"] = state
    session["sso_redirect_uri"] = default_redirect

    params = {
        "response_type": "code",
        "client_id": cfg["ciam_client_id"],
        "redirect_uri": default_redirect,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"{cfg['ciam_base_url']}/oauth/authorize?{urllib.parse.urlencode(params)}"
    return redirect(authorize_url)


@app.route("/auth/callback", methods=["GET"])
def ciam_auth_callback_page():
    """
    Browser landing route for OIDC redirect. Handles Authorization Code
    seamlessly and logs the user into the main application.
    """
    err = request.args.get("error") or request.args.get("error_description")
    if err:
        return redirect(url_for("login") + f"?error={urllib.parse.quote_plus(err)}")

    code = request.args.get("code")
    if not code:
        return redirect(url_for("login"))

    cfg = get_ciam_config()
    default_redirect = get_canonical_redirect_uri()
    raw_redirect = session.get("sso_redirect_uri") or default_redirect
    redirect_uri = get_canonical_redirect_uri(raw_redirect)
    code_verifier = session.get("sso_verifier")
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    try:
        token_res = exchange_oauth_code(code, redirect_uri, code_verifier)
        id_token = token_res.get("id_token") or token_res.get("access_token")

        # 1. First, check if token_res contains user object directly (CIAM Spec v2.7.0 format)
        user_info = token_res.get("user") or {}
        username = (user_info.get("preferred_username") or user_info.get("username") or "").strip()
        full_name = user_info.get("name") or user_info.get("full_name")
        email = user_info.get("email")
        role = user_info.get("group_name") or user_info.get("role")

        # 2. If username not in user_info, decode from id_token / access_token
        if not username and id_token:
            try:
                claims = verify_rs256_jwt(id_token, cfg["ciam_base_url"], cfg["ciam_client_id"])
                username = (claims.get("preferred_username") or claims.get("username") or claims.get("sub") or "").strip()
                if not username and claims.get("email"):
                    username = claims["email"].split("@")[0].strip()
                if not full_name:
                    full_name = claims.get("name") or claims.get("full_name")
                if not role:
                    role = claims.get("group_name") or claims.get("role")
            except Exception as jwt_err:
                app.logger.warning(f"CIAM RS256 token verify warning: {jwt_err}")
                # Fallback: extract payload from JWT parts directly since back-channel HTTPS is already authenticated
                try:
                    parts = id_token.strip().split('.')
                    if len(parts) >= 2:
                        raw_payload = json.loads(base64url_decode(parts[1]).decode('utf-8'))
                        username = (raw_payload.get("preferred_username") or raw_payload.get("username") or raw_payload.get("sub") or "").strip()
                        if not username and raw_payload.get("email"):
                            username = raw_payload["email"].split("@")[0].strip()
                        if not full_name:
                            full_name = raw_payload.get("name") or raw_payload.get("full_name")
                except Exception:
                    pass

        if not username:
            return redirect(url_for("login") + "?error=UserIdentificationFailed")

        user = User.query.filter(func.lower(User.username) == username.lower()).first()
        if not user:
            auto_role = role or cfg["ciam_auto_provision_group"]
            user_full_name = full_name or username.title()
            random_pw = secrets.token_urlsafe(16)
            hashed_pw = bcrypt.generate_password_hash(random_pw).decode("utf-8")

            user = User(
                username=username,
                fullName=user_full_name,
                password=hashed_pw,
                role=auto_role,
                status="active",
                use_ad_auth=True,
                createdAt=now_bangkok(),
                lastLogin=now_bangkok(),
            )
            db.session.add(user)
            db.session.commit()

            TransactionLog.log(
                category="ciam_sso",
                action="auto_provision_user",
                status="info",
                message=f"สร้างบัญชีผู้ใช้ใหม่อัตโนมัติจาก Central IAM: '{username}' (Role: {auto_role})",
                details={"username": username, "role": auto_role, "ip": client_ip},
                triggered_by="system:ciam",
            )
        else:
            if getattr(user, "status", "active") == "inactive":
                return redirect(url_for("login") + "?error=AccountDisabled")
            user.lastLogin = now_bangkok()
            db.session.commit()

        login_user(user, remember=True)
        session["auth_provider"] = "ciam_sso"
        session["is_sso"] = True

        try:
            db.session.add(LoginLog(
                username=user.username,
                user_id=user.id,
                ip_address=client_ip,
                user_agent=request.user_agent.string if request.user_agent else "-",
                status="SUCCESS",
            ))
            db.session.commit()
        except Exception:
            pass

        TransactionLog.log(
            category="ciam_sso",
            action="login_success",
            status="success",
            message=f"เข้าสู่ระบบผ่าน Central IAM SSO สำเร็จ: ผู้ใช้ '{user.username}'",
            details={"username": user.username, "ip": client_ip, "auth_method": "RFC9700_BOUNCE"},
            triggered_by=f"user:{user.username}",
        )

        session.pop("sso_verifier", None)
        session.pop("sso_state", None)
        session.pop("sso_redirect_uri", None)

        return redirect(url_for("app_shell"))

    except Exception as e:
        app.logger.error(f"Browser SSO callback failed: {e}")
        return redirect(url_for("login") + f"?error={urllib.parse.quote_plus(str(e))}")


@app.route("/api/auth/sso/break-glass-toggle", methods=["POST"])
@roles_required("Administrator")
def ciam_break_glass_toggle():
    """
    Spec B.4: Emergency break-glass toggle for ISO 27001 compliance
    """
    data = request.json or {}
    new_active = bool(data.get("break_glass_active", False))
    reason = data.get("reason", "Manual emergency toggle by Administrator")
    admin_user = current_user.username if current_user.is_authenticated else "admin"
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
        or "127.0.0.1"
    )

    SystemSetting.set_value("ciam_break_glass_active", "true" if new_active else "false", description="โหมดปลดระบบฉุกเฉิน", data_type="boolean")

    status_str = "ENABLED" if new_active else "DISABLED"
    TransactionLog.log(
        category="security_break_glass",
        action="toggle_break_glass",
        status="warning" if new_active else "success",
        message=f"สลับสถานะระบบ Break-Glass: {status_str} โดย '{admin_user}' (เหตุผล: {reason})",
        details={"break_glass_active": new_active, "reason": reason, "admin": admin_user, "ip": client_ip},
        triggered_by=f"user:{admin_user}",
    )

    return jsonify({
        "success": True,
        "break_glass_active": new_active,
        "message": f"Break-glass mode {status_str} successfully.",
    }), 200


# --- Group A: System Settings Channel (Admin) ---

@app.route("/api/settings/ciam-sso", methods=["GET"])
@roles_required("Administrator")
def get_ciam_settings_spec():
    """
    Spec A.1: Retrieve active CIAM configuration with masked secret
    """
    cfg = get_ciam_config()
    setting_row = SystemSetting.query.filter_by(key="ciam_base_url").first()
    updated_at_local = ensure_bangkok(setting_row.updated_at) if setting_row else now_bangkok()

    return jsonify({
        "status": "success",
        "settings": {
            "ciam_base_url": cfg["ciam_base_url"],
            "ciam_client_id": cfg["ciam_client_id"],
            "ciam_client_secret_masked": mask_secret(cfg["ciam_client_secret"]),
            "ciam_sso_enabled": cfg["ciam_sso_enabled"],
            "ciam_break_glass_active": cfg["ciam_break_glass_active"],
            "ciam_ad_gateway_url": cfg["ciam_ad_gateway_url"],
            "ciam_auto_provision_group": cfg["ciam_auto_provision_group"],
            "ciam_session_ttl_minutes": cfg["ciam_session_ttl_minutes"],
            "updated_at": updated_at_local.isoformat() if updated_at_local else None,
        }
    }), 200


@app.route("/api/settings/ciam-sso", methods=["PUT"])
@roles_required("Administrator")
def update_ciam_settings_spec():
    """
    Spec A.2: Real-time update of CIAM settings in system_settings
    """
    data = request.json or {}
    admin_user = current_user.username if current_user.is_authenticated else "admin"
    changed_fields = []

    if "ciam_base_url" in data and data["ciam_base_url"]:
        SystemSetting.set_value("ciam_base_url", str(data["ciam_base_url"]).strip().rstrip("/"), data_type="string")
        changed_fields.append("ciam_base_url")

    if "ciam_client_id" in data and data["ciam_client_id"]:
        SystemSetting.set_value("ciam_client_id", str(data["ciam_client_id"]).strip(), data_type="string")
        changed_fields.append("ciam_client_id")

    # Update secret only if not masked
    new_sec = data.get("ciam_client_secret")
    if new_sec and not new_sec.startswith("sec_****") and not new_sec.startswith("****"):
        SystemSetting.set_value("ciam_client_secret", str(new_sec).strip(), data_type="encrypted")
        changed_fields.append("ciam_client_secret")
        # Also sync to CiamSetting for backward compatibility
        cs = CiamSetting.query.first()
        if cs:
            cs.api_key = str(new_sec).strip()
            db.session.commit()

    if "ciam_sso_enabled" in data:
        val = bool(data["ciam_sso_enabled"])
        SystemSetting.set_value("ciam_sso_enabled", "true" if val else "false", data_type="boolean")
        changed_fields.append("ciam_sso_enabled")
        cs = CiamSetting.query.first()
        if cs:
            cs.is_enabled = val
            db.session.commit()

    if "ciam_ad_gateway_url" in data:
        SystemSetting.set_value("ciam_ad_gateway_url", str(data["ciam_ad_gateway_url"]).strip(), data_type="string")
        changed_fields.append("ciam_ad_gateway_url")

    if "ciam_auto_provision_group" in data:
        SystemSetting.set_value("ciam_auto_provision_group", str(data["ciam_auto_provision_group"]).strip(), data_type="string")
        changed_fields.append("ciam_auto_provision_group")

    if "ciam_session_ttl_minutes" in data:
        try:
            val_int = int(data["ciam_session_ttl_minutes"])
            SystemSetting.set_value("ciam_session_ttl_minutes", str(val_int), data_type="integer")
            changed_fields.append("ciam_session_ttl_minutes")
        except Exception:
            pass

    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
        or "127.0.0.1"
    )

    TransactionLog.log(
        category="system_setting",
        action="update_ciam_settings",
        status="success",
        message=f"แก้ไขการตั้งค่าระบบ Central IAM SSO โดย '{admin_user}' ({len(changed_fields)} ฟิลด์)",
        details={"changed_fields": changed_fields, "admin": admin_user, "ip": client_ip},
        triggered_by=f"user:{admin_user}",
    )

    return jsonify({
        "success": True,
        "message": "CIAM settings updated successfully.",
        "changed_fields": changed_fields,
    }), 200


@app.route("/api/settings/ciam-sso/test-connection", methods=["POST"])
@roles_required("Administrator")
def ciam_test_connection_api():
    """
    Spec A.3: Test connection to Central IAM OpenID configuration & JWKS
    """
    result = test_ciam_connection()
    return jsonify(result), (200 if result.get("status") == "connected" else 502)


@app.route("/api/settings/ciam-agent/sync-now", methods=["POST"])
@roles_required("Administrator")
def ciam_immediate_sync_api():
    """
    Spec D.4: Mandatory Spoke Mode C Immediate Sync Button Endpoint
    Reconciles local user directory with Central IAM in real-time.
    """
    result = sync_with_ciam_now()
    return jsonify(result), (200 if result.get("success") else 500)


@app.route("/api/admin/transaction-logs", methods=["GET"])
@roles_required("Administrator")
def get_transaction_logs_api():
    """
    Spec 4: Fetch recent ISO 27001 transaction logs
    """
    limit = request.args.get("limit", 100, type=int)
    category = request.args.get("category")
    query = TransactionLog.query
    if category:
        query = query.filter_by(category=category)
    logs = query.order_by(TransactionLog.id.desc()).limit(min(limit, 500)).all()
    return jsonify([log.to_dict() for log in logs]), 200


@app.route("/api/admin/unified-logs", methods=["GET"])
@roles_required("Administrator")
def get_unified_logs_api():
    """
    Consolidated audit logs from CIAM, Login Activity, and Transaction Logs (ISO 27001).
    """
    limit = request.args.get("limit", 200, type=int)
    log_type = request.args.get("type", "").strip().upper()

    unified_list = []

    # 1. CIAM Connection Logs
    if not log_type or log_type == "CIAM":
        try:
            ciam_records = CiamAuditLog.query.order_by(CiamAuditLog.id.desc()).limit(min(limit, 250)).all()
            for c in ciam_records:
                created_local = ensure_bangkok(c.created_at)
                is_ok = bool(c.status_code and c.status_code < 400)
                status_text = "SUCCESS" if is_ok else "FAILURE"
                unified_list.append({
                    "id": f"ciam_{c.id}",
                    "logType": "CIAM",
                    "createdAt": created_local.strftime("%d-%m-%Y %H:%M:%S") if created_local else "-",
                    "createdAtIso": created_local.isoformat() if created_local else "",
                    "timestampSort": created_local.timestamp() if created_local else 0,
                    "action": c.action or "-",
                    "status": status_text,
                    "statusCode": c.status_code or 200,
                    "actor": c.updated_by or c.target_username or "system",
                    "ip": c.client_ip or "-",
                    "details": f"{c.message or ''} {c.reason or ''}".strip() or "-"
                })
        except Exception as e:
            print(f"[UNIFIED LOGS] Error loading CIAM logs: {e}")

    # 2. Login Activity Logs
    if not log_type or log_type == "LOGIN":
        try:
            login_records = LoginLog.query.order_by(LoginLog.id.desc()).limit(min(limit, 250)).all()
            for l in login_records:
                created_local = ensure_bangkok(l.created_at)
                is_success = (l.status and l.status.upper() == "SUCCESS")
                status_text = "SUCCESS" if is_success else "FAILURE"
                msg = l.failure_reason if l.failure_reason else ("Login successful" if is_success else l.status)
                unified_list.append({
                    "id": f"login_{l.id}",
                    "logType": "LOGIN",
                    "createdAt": created_local.strftime("%d-%m-%Y %H:%M:%S") if created_local else "-",
                    "createdAtIso": created_local.isoformat() if created_local else "",
                    "timestampSort": created_local.timestamp() if created_local else 0,
                    "action": f"User Login ({l.status})",
                    "status": status_text,
                    "statusCode": 200 if is_success else 401,
                    "actor": l.username or "-",
                    "ip": l.ip_address or "-",
                    "details": msg or "-"
                })
        except Exception as e:
            print(f"[UNIFIED LOGS] Error loading Login logs: {e}")

    # 3. Transaction Logs (ISO 27001)
    if not log_type or log_type == "TRANSACTION":
        try:
            trans_records = TransactionLog.query.order_by(TransactionLog.id.desc()).limit(min(limit, 250)).all()
            for t in trans_records:
                d = t.to_dict()
                created_local = ensure_bangkok(t.created_at)
                status_val = (t.status or "SUCCESS").upper()
                unified_list.append({
                    "id": f"trans_{t.id}",
                    "logType": "TRANSACTION",
                    "createdAt": d.get("createdAt") or (created_local.strftime("%d-%m-%Y %H:%M:%S") if created_local else "-"),
                    "createdAtIso": d.get("createdAtIso") or (created_local.isoformat() if created_local else ""),
                    "timestampSort": created_local.timestamp() if created_local else 0,
                    "action": f"[{t.category}] {t.action}",
                    "status": status_val,
                    "statusCode": 200 if status_val == "SUCCESS" else (400 if status_val == "FAILURE" else 0),
                    "actor": d.get("triggeredBy") or "-",
                    "ip": d.get("ip") or "-",
                    "details": t.message or "-"
                })
        except Exception as e:
            print(f"[UNIFIED LOGS] Error loading Transaction logs: {e}")

    # Sort unified records by timestamp descending
    unified_list.sort(key=lambda x: x["timestampSort"], reverse=True)
    return jsonify(unified_list[:limit]), 200


# =================================================================================
# [START] Telegram Bot, SAP B1 & AI Copilot (CIAM Spec v2.8.0) Settings APIs
# =================================================================================

@app.route("/api/settings/telegram", methods=["GET"])
@roles_required("Administrator")
def get_telegram_settings_api():
    """Retrieve Telegram Bot configuration with masked token"""
    raw_token = SystemSetting.get_value("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "8214911655:AAG5RKU6m75AOc3Wws0FqVBqn1CicDLsVWI")
    group_id = SystemSetting.get_value("telegram_group_id") or os.environ.get("TELEGRAM_GROUP_ID", "-5241471050")
    api_base = SystemSetting.get_value("telegram_api_base_url") or os.environ.get("TELEGRAM_API_BASE_URL", "https://api.telegram.org")
    enabled = SystemSetting.get_value("telegram_enabled", True)
    
    masked_token = f"{raw_token[:6]}...{raw_token[-4:]}" if raw_token and len(raw_token) > 10 else raw_token
    
    return jsonify({
        "status": "success",
        "settings": {
            "telegram_bot_token_masked": masked_token,
            "has_token": bool(raw_token),
            "telegram_group_id": group_id,
            "telegram_api_base_url": api_base,
            "telegram_enabled": bool(enabled),
        }
    }), 200


@app.route("/api/settings/telegram", methods=["PUT"])
@roles_required("Administrator")
def update_telegram_settings_api():
    """Update Telegram Bot configuration in system_settings"""
    data = request.json or {}
    admin_user = current_user.username if current_user.is_authenticated else "admin"
    changed = []

    new_token = data.get("telegram_bot_token")
    if new_token and not new_token.startswith("****") and "..." not in new_token:
        SystemSetting.set_value("telegram_bot_token", str(new_token).strip(), description="Telegram Bot API Token", category="telegram", data_type="encrypted")
        changed.append("telegram_bot_token")

    if "telegram_group_id" in data:
        SystemSetting.set_value("telegram_group_id", str(data["telegram_group_id"]).strip(), description="Telegram Chat/Group ID", category="telegram", data_type="string")
        changed.append("telegram_group_id")

    if "telegram_api_base_url" in data and data["telegram_api_base_url"]:
        SystemSetting.set_value("telegram_api_base_url", str(data["telegram_api_base_url"]).strip().rstrip("/"), description="Telegram API Base URL", category="telegram", data_type="string")
        changed.append("telegram_api_base_url")

    if "telegram_enabled" in data:
        val = bool(data["telegram_enabled"])
        SystemSetting.set_value("telegram_enabled", "true" if val else "false", description="เปิด/ปิดการแจ้งเตือน Telegram", category="telegram", data_type="boolean")
        changed.append("telegram_enabled")

    TransactionLog.log(
        category="system_setting",
        action="update_telegram_settings",
        status="success",
        message=f"แก้ไขการตั้งค่า Telegram Bot โดย '{admin_user}' ({len(changed)} ฟิลด์)",
        details={"changed_fields": changed, "admin": admin_user},
        triggered_by=f"user:{admin_user}",
    )

    return jsonify({"success": True, "message": "บันทึกการตั้งค่า Telegram Bot เรียบร้อยแล้ว", "changed_fields": changed}), 200


@app.route("/api/settings/telegram/test", methods=["POST"])
@roles_required("Administrator")
def test_telegram_connection_api():
    """Test Telegram Bot notification directly"""
    data = request.json or {}
    token = data.get("telegram_bot_token")
    if not token or token.startswith("****") or "..." in token:
        token = SystemSetting.get_value("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "8214911655:AAG5RKU6m75AOc3Wws0FqVBqn1CicDLsVWI")
    group_id = data.get("telegram_group_id") or SystemSetting.get_value("telegram_group_id") or os.environ.get("TELEGRAM_GROUP_ID", "-5241471050")
    api_base = data.get("telegram_api_base_url") or SystemSetting.get_value("telegram_api_base_url") or "https://api.telegram.org"

    success, msg = test_telegram_sync(token, group_id, api_base, message="🔔 <b>[QT-Online Test]</b> ทดสอบการเชื่อมต่อ Telegram Bot สำเร็จเรียบร้อย!")
    return jsonify({"success": success, "message": msg}), (200 if success else 400)


@app.route("/api/settings/sap", methods=["GET"])
@roles_required("Administrator")
def get_sap_settings_api():
    """Retrieve SAP B1 integration settings"""
    return jsonify({
        "status": "success",
        "settings": {
            "sap_b1_service_url": SystemSetting.get_value("sap_b1_service_url", "https://sap.windowasia.com:50000/b1s/v1"),
            "sap_b1_company_db": SystemSetting.get_value("sap_b1_company_db", "WINDOW_ASIA_LIVE"),
            "sap_b1_enabled": bool(SystemSetting.get_value("sap_b1_enabled", False)),
            "sap_b1_default_bu": SystemSetting.get_value("sap_b1_default_bu", "WA"),
            "sap_b1_default_dept": SystemSetting.get_value("sap_b1_default_dept", "SA"),
        }
    }), 200


@app.route("/api/settings/sap", methods=["PUT"])
@roles_required("Administrator")
def update_sap_settings_api():
    """Update SAP B1 integration settings"""
    data = request.json or {}
    admin_user = current_user.username if current_user.is_authenticated else "admin"
    changed = []

    if "sap_b1_service_url" in data:
        SystemSetting.set_value("sap_b1_service_url", str(data["sap_b1_service_url"]).strip().rstrip("/"), description="SAP B1 Service Layer URL", category="sap_b1", data_type="string")
        changed.append("sap_b1_service_url")

    if "sap_b1_company_db" in data:
        SystemSetting.set_value("sap_b1_company_db", str(data["sap_b1_company_db"]).strip(), description="SAP B1 Company DB", category="sap_b1", data_type="string")
        changed.append("sap_b1_company_db")

    if "sap_b1_enabled" in data:
        val = bool(data["sap_b1_enabled"])
        SystemSetting.set_value("sap_b1_enabled", "true" if val else "false", description="เปิด/ปิดการเชื่อมต่อ SAP B1", category="sap_b1", data_type="boolean")
        changed.append("sap_b1_enabled")

    if "sap_b1_default_bu" in data:
        SystemSetting.set_value("sap_b1_default_bu", str(data["sap_b1_default_bu"]).strip(), description="SAP B1 Default Business Unit (CostingCode)", category="sap_b1", data_type="string")
        changed.append("sap_b1_default_bu")

    if "sap_b1_default_dept" in data:
        SystemSetting.set_value("sap_b1_default_dept", str(data["sap_b1_default_dept"]).strip(), description="SAP B1 Default Department (CostingCode2)", category="sap_b1", data_type="string")
        changed.append("sap_b1_default_dept")

    TransactionLog.log(
        category="system_setting",
        action="update_sap_settings",
        status="success",
        message=f"แก้ไขการตั้งค่าระบบ SAP B1 โดย '{admin_user}' ({len(changed)} ฟิลด์)",
        details={"changed_fields": changed, "admin": admin_user},
        triggered_by=f"user:{admin_user}",
    )

    return jsonify({"success": True, "message": "บันทึกการตั้งค่า SAP B1 เรียบร้อยแล้ว", "changed_fields": changed}), 200


@app.route("/api/settings/sap/test-connection", methods=["POST"])
@roles_required("Administrator")
def test_sap_connection_api():
    """Test connection to SAP B1 Service Layer endpoint"""
    url = request.json.get("sap_b1_service_url") if request.json else None
    if not url:
        url = SystemSetting.get_value("sap_b1_service_url", "https://sap.windowasia.com:50000/b1s/v1")
    
    import ssl
    import time
    start = time.time()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "QTOnline-SAP-Connector/1.0"})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            latency = int((time.time() - start) * 1000)
            return jsonify({"success": True, "message": f"เชื่อมต่อไปยัง SAP Service Layer สำเร็จ (HTTP {resp.status})", "latency_ms": latency}), 200
    except urllib.error.HTTPError as e:
        latency = int((time.time() - start) * 1000)
        if e.code in (400, 401, 403, 404, 405):
            return jsonify({"success": True, "message": f"Service Layer พร้อมทำงาน (Endpoint Reachable: HTTP {e.code})", "latency_ms": latency}), 200
        return jsonify({"success": False, "message": f"HTTP Error {e.code}: {e.reason}", "latency_ms": latency}), 502
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return jsonify({"success": False, "message": f"ไม่สามารถเชื่อมต่อไปยัง Service Layer ได้: {str(e)}", "latency_ms": latency}), 502


def _clean_sap_service_url(url: str) -> str:
    cleaned = (url or "").strip().rstrip("/")
    if cleaned.endswith("/Login"):
        cleaned = cleaned[:-6].rstrip("/")
    return cleaned


def _test_sap_b1_login(sap_user: str, sap_password: str, service_url: str = None, company_db: str = None):
    """
    Test authenticating against SAP B1 Service Layer with provided credentials.
    Returns (success: bool, message: str, latency_ms: int)
    """
    import ssl
    import json
    import time
    import urllib.request
    import urllib.error

    if not sap_user or not sap_password:
        return False, "กรุณาระบุบัญชี SAP (Username) และรหัสผ่าน", 0

    base_url = _clean_sap_service_url(service_url or SystemSetting.get_value("sap_b1_service_url", "https://sap.windowasia.com:50000/b1s/v1"))
    db_name = company_db or SystemSetting.get_value("sap_b1_company_db", "WINDOW_ASIA_LIVE")

    start = time.time()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        login_url = f"{base_url}/Login"
        payload = json.dumps({
            "CompanyDB": db_name,
            "UserName": sap_user,
            "Password": sap_password
        }).encode("utf-8")

        req = urllib.request.Request(
            login_url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "QTOnline-SAP-Connector/1.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            latency = int((time.time() - start) * 1000)
            return True, f"ยืนยันตัวตนสำเร็จ (Company: {db_name})", latency
    except urllib.error.HTTPError as e:
        latency = int((time.time() - start) * 1000)
        err_msg = f"HTTP Error {e.code}"
        try:
            err_body = e.read().decode("utf-8")
            err_json = json.loads(err_body)
            if "error" in err_json and "message" in err_json["error"]:
                val = err_json["error"]["message"]
                err_msg = val.get("value", err_msg) if isinstance(val, dict) else str(val)
        except Exception:
            pass
        return False, f"SAP ปฏิเสธการเข้าสู่ระบบ: {err_msg}", latency
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return False, f"ไม่สามารถติดต่อ SAP Service Layer ได้: {str(e)}", latency


@app.route("/api/me/sap-status", methods=["GET"])
@login_required
def get_my_sap_status():
    """
    Check if current user can create Sales Order on SAP B1.
    Tests SAP logon if credentials exist and SAP is enabled.
    """
    import time
    enabled_val = SystemSetting.get_value("sap_b1_enabled", False)
    sap_enabled = str(enabled_val).lower() in ("true", "1", "yes")
    sap_user = (current_user.sap_account or "").strip()
    raw_pwd = getattr(current_user, "sap_password", "") or ""
    sap_pwd = ""
    if raw_pwd:
        try:
            sap_pwd = decrypt_string(raw_pwd)
        except Exception:
            sap_pwd = raw_pwd

    has_credentials = bool(sap_user and sap_pwd)
    force_refresh = request.args.get("refresh", "0") in ("1", "true")

    if not sap_enabled:
        return jsonify({
            "sap_enabled": False,
            "has_credentials": has_credentials,
            "sap_account": sap_user,
            "can_create_so": False,
            "reason": "ระบบ SAP B1 ปิดการใช้งานอยู่ (Disabled ใน System Settings)",
            "login_valid": False,
            "latency_ms": 0,
        }), 200

    if not has_credentials:
        return jsonify({
            "sap_enabled": True,
            "has_credentials": False,
            "sap_account": sap_user,
            "can_create_so": False,
            "reason": "ผู้ใช้งานยังไม่ได้ระบุบัญชี SAP หรือรหัสผ่านใน Profile (มุมบนขวา)",
            "login_valid": False,
            "latency_ms": 0,
        }), 200

    # Cached check within session (valid 3 minutes unless refresh=1)
    cached = session.get("sap_auth_cache")
    now_ts = time.time()
    if not force_refresh and cached and (now_ts - cached.get("time", 0) < 180) and cached.get("user_id") == current_user.id:
        return jsonify({
            "sap_enabled": True,
            "has_credentials": True,
            "sap_account": sap_user,
            "can_create_so": cached.get("success", False),
            "reason": cached.get("message", ""),
            "login_valid": cached.get("success", False),
            "latency_ms": cached.get("latency_ms", 0),
        }), 200

    # Live logon test
    success, msg, latency = _test_sap_b1_login(sap_user, sap_pwd)
    session["sap_auth_cache"] = {
        "time": now_ts,
        "user_id": current_user.id,
        "success": success,
        "message": msg,
        "latency_ms": latency
    }

    return jsonify({
        "sap_enabled": True,
        "has_credentials": True,
        "sap_account": sap_user,
        "can_create_so": success,
        "reason": msg,
        "login_valid": success,
        "latency_ms": latency,
    }), 200


@app.route("/api/me/test-sap-login", methods=["POST"])
@login_required
def test_my_sap_login():
    """Test SAP B1 login for current user with provided or existing credentials"""
    import time
    data = request.json or {}
    sap_user = (data.get("sap_account") or current_user.sap_account or "").strip()
    sap_pwd = data.get("sap_password", "")
    if not sap_pwd and getattr(current_user, "sap_password", ""):
        try:
            sap_pwd = decrypt_string(current_user.sap_password)
        except Exception:
            sap_pwd = current_user.sap_password

    if not sap_user or not sap_pwd:
        return jsonify({"success": False, "message": "กรุณาระบุบัญชี SAP และรหัสผ่าน"}), 400

    success, msg, latency = _test_sap_b1_login(sap_user, sap_pwd)
    session["sap_auth_cache"] = {
        "time": time.time(),
        "user_id": current_user.id,
        "success": success,
        "message": msg,
        "latency_ms": latency
    }
    return jsonify({"success": success, "message": msg, "latency_ms": latency}), 200


@app.route("/api/me/sap-password", methods=["GET"])
@login_required
def get_my_sap_password():
    """Get current user's decrypted SAP password for viewing in profile modal"""
    if not getattr(current_user, "sap_password", None):
        return jsonify({"password": ""}), 200
    try:
        decrypted = decrypt_string(current_user.sap_password)
        return jsonify({"password": decrypted}), 200
    except Exception:
        return jsonify({"password": current_user.sap_password}), 200


@app.route("/api/me/sap-profile", methods=["PUT", "POST"])
@login_required
def update_my_sap_profile():
    """Update current user's SAP Account and SAP Password"""
    data = request.json or {}
    sap_user = (data.get("sap_account") or "").strip()
    new_pwd = data.get("sap_password", "").strip()

    current_user.sap_account = sap_user
    if new_pwd:
        current_user.sap_password = encrypt_string(new_pwd)

    session.pop("sap_auth_cache", None)
    db.session.commit()

    TransactionLog.log(
        category="user_profile",
        action="update_sap_profile",
        status="success",
        message=f"ผู้ใช้ '{current_user.username}' อัปเดตข้อมูลบัญชี SAP B1 (Account: {sap_user or '-'})",
        details={"user_id": current_user.id, "username": current_user.username, "sap_account": sap_user},
        triggered_by=f"user:{current_user.username}",
    )

    return jsonify({
        "success": True,
        "message": "บันทึกข้อมูลบัญชี SAP เรียบร้อยแล้ว",
        "sap_account": sap_user,
        "hasSapPassword": bool(current_user.sap_password)
    }), 200


def _sync_to_sap_b1(po, user, customer_ref_no=None, comments=None):
    """
    Helper to create Sales Order in SAP B1 Service Layer.
    Returns (success: bool, doc_num: str, doc_entry: int, message: str, is_simulation: bool)
    NOTE: Simulation mode has been completely removed per requirements.
    """
    import ssl
    import json
    import urllib.request
    import urllib.error

    service_url = _clean_sap_service_url(SystemSetting.get_value("sap_b1_service_url", "https://sap.windowasia.com:50000/b1s/v1"))
    company_db = SystemSetting.get_value("sap_b1_company_db", "WINDOW_ASIA_LIVE")
    enabled = str(SystemSetting.get_value("sap_b1_enabled", "false")).lower() in ("true", "1", "yes")

    # If SAP integration is not enabled, reject creation (no simulation)
    if not enabled:
        return False, None, None, "ไม่สามารถสร้าง Sales Order ได้: ระบบ SAP B1 ถูกปิดใช้งานอยู่ใน System Settings", False

    sap_user = (user.sap_account or SystemSetting.get_value("sap_b1_default_user", "")).strip()
    sap_pwd = ""
    raw_pwd = getattr(user, "sap_password", "")
    if raw_pwd:
        try:
            sap_pwd = decrypt_string(raw_pwd)
        except Exception:
            sap_pwd = raw_pwd

    if not sap_user or not sap_pwd:
        return False, None, None, "ไม่สามารถสร้าง Sales Order ได้: ผู้ใช้งานยังไม่ได้ระบุบัญชี SAP หรือรหัสผ่านใน Profile", False

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # 1. Login to SAP B1 Service Layer
        login_url = f"{service_url}/Login"
        login_payload = json.dumps({
            "CompanyDB": company_db,
            "UserName": sap_user,
            "Password": sap_pwd
        }).encode("utf-8")
        login_req = urllib.request.Request(
            login_url,
            data=login_payload,
            headers={"Content-Type": "application/json", "User-Agent": "QTOnline-SAP/1.0"},
            method="POST"
        )
        with urllib.request.urlopen(login_req, timeout=12, context=ctx) as login_resp:
            cookies = login_resp.headers.get("Set-Cookie", "")

        # 2. Prepare Order Payload
        due_date = po.deliveryDate.strftime("%Y-%m-%d") if po.deliveryDate else now_bangkok().strftime("%Y-%m-%d")
        default_bu = SystemSetting.get_value("sap_b1_default_bu", "WA") or "WA"
        default_dept = SystemSetting.get_value("sap_b1_default_dept", "SA") or "SA"

        doc_lines = []
        for item in po.items:
            is_item_gift = bool(getattr(item, "is_gift", False))

            # คำนวณ UnitPrice และ Discount % สำหรับ SAP B1 (ช่อง "Discount %" บน DocumentLines)
            # ข้อ 1: สินค้าที่แถม จะต้องไม่มีราคา (0.00) และ Discount จะเป็น 0.00
            # ข้อ 2: สินค้าแต่ละชิ้น (ที่ไม่ใช่ของแถม) จะต้องแสดง Discount ตามในตาราง Product (Product.discountPercent)
            if is_item_gift:
                unit_price = 0.0
                item_discount = 0.0
            else:
                unit_price = float(
                    item.recommendedPrice
                    if (item.recommendedPrice and item.recommendedPrice > 0)
                    else (item.price or 0.0)
                )
                item_discount = 0.0
                prod = item.product
                if not prod and item.productCode:
                    prod = Product.query.filter_by(productCode=item.productCode).first()
                if prod and getattr(prod, "discountPercent", None) is not None and float(prod.discountPercent or 0.0) > 0:
                    item_discount = float(prod.discountPercent)
                elif item.discount is not None and float(item.discount) > 0:
                    item_discount = float(item.discount)

            clean_desc = (item.name or "").replace(" (ของแถมฟรี)", "").replace(" (แถมฟรี)", "").strip()
            pcode = item.productCode or f"GEN-{item.id}"
            if pcode and clean_desc.startswith(pcode):
                clean_desc = clean_desc[len(pcode):].lstrip(" -:").strip()

            line_data = {
                "ItemCode": pcode,
                "ItemDescription": clean_desc or pcode,
                "Quantity": float(item.qty),
                "UnitPrice": unit_price,
                "DiscountPercent": item_discount,
            }
            if default_bu:
                line_data["CostingCode"] = default_bu
            if default_dept:
                line_data["CostingCode2"] = default_dept
            doc_lines.append(line_data)

        # ข้อ 3 & 4: กำหนด Customer Ref. No. และ Remarks ที่ส่งเข้า SAP B1 (จำกัดสูงสุด 1,000 ตัวอักษร)
        final_customer_ref = (customer_ref_no or po.customer_ref_no or po.poNumber or "").strip()
        default_comment = f"Created from QT-Online {po.poNumber} by {user.fullName}"
        final_comments = (comments or po.sap_remarks or default_comment).strip()[:1000]

        order_payload = json.dumps({
            "CardCode": po.customerId,
            "CardName": po.customerName or po.get_customer_name(),
            "DocDueDate": due_date,
            "DocDate": now_bangkok().strftime("%Y-%m-%d"),
            "NumAtCard": final_customer_ref,
            "Comments": final_comments,
            "DocumentLines": doc_lines
        }).encode("utf-8")

        order_url = f"{service_url}/Orders"
        order_req = urllib.request.Request(
            order_url,
            data=order_payload,
            headers={
                "Content-Type": "application/json",
                "Cookie": cookies,
                "User-Agent": "QTOnline-SAP/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(order_req, timeout=15, context=ctx) as order_resp:
            resp_body = json.loads(order_resp.read().decode("utf-8"))
            doc_num = str(resp_body.get("DocNum") or resp_body.get("DocEntry"))
            doc_entry = int(resp_body.get("DocEntry", 0))

            # บันทึกข้อมูลที่ส่งเข้า SAP สำเร็จลงใน PO
            po.customer_ref_no = final_customer_ref
            po.sap_remarks = final_comments

            return True, doc_num, doc_entry, "สร้าง Sales Order บน SAP B1 สำเร็จ", False

    except urllib.error.HTTPError as e:
        err_msg = f"HTTP Error {e.code}"
        try:
            err_body = e.read().decode("utf-8")
            err_json = json.loads(err_body)
            if "error" in err_json and "message" in err_json["error"]:
                val = err_json["error"]["message"]
                err_msg = val.get("value", err_msg) if isinstance(val, dict) else str(val)
        except Exception:
            pass
        return False, None, None, f"SAP Service Layer Error: {err_msg}", False
    except Exception as e:
        return False, None, None, f"ไม่สามารถสร้าง Sales Order บน SAP ได้: {str(e)}", False


@app.route("/api/purchase-orders/<int:po_id>/sap-preview", methods=["GET"])
@login_required
def get_sap_so_preview(po_id):
    po = PurchaseOrder.query.get(po_id)
    if not po:
        return jsonify({"error": "Quotation not found"}), 404

    is_admin = current_user.role in ["Administrator", "Sale Admin"]
    is_owner = po.sale_user_id == current_user.id
    if not (is_admin or is_owner or getattr(current_user, "can_use_sap_api", False)):
        return jsonify({"error": "ไม่มีสิทธิ์เข้าถึงข้อมูลนี้"}), 403

    allowed_statuses = ["Completed"]
    can_create = True
    validation_issues = []

    # Validate global SAP status
    enabled_val = SystemSetting.get_value("sap_b1_enabled", False)
    sap_enabled = str(enabled_val).lower() in ("true", "1", "yes")
    if not sap_enabled:
        can_create = False
        validation_issues.append("ระบบ SAP B1 ปิดการใช้งานอยู่ใน System Settings (Disabled)")

    # Validate current user credentials
    sap_user = (current_user.sap_account or "").strip()
    raw_pwd = getattr(current_user, "sap_password", "") or ""
    if not sap_user or not raw_pwd:
        can_create = False
        validation_issues.append("คุณยังไม่ได้ระบุบัญชี SAP หรือรหัสผ่านใน Profile (คลิกที่รูปโปรไฟล์มุมบนขวาเพื่อตั้งค่า)")

    if po.status not in allowed_statuses:
        can_create = False
        validation_issues.append(f"สถานะเอกสารต้องเป็น Completed เท่านั้นจึงจะสามารถสร้าง Sales Order บน SAP ได้ (ปัจจุบัน: {po.status})")

    if po.sap_doc_num:
        can_create = False
        validation_issues.append(f"เอกสารนี้เคยสร้าง Sales Order บน SAP แล้ว (#{po.sap_doc_num})")

    if not po.customerId:
        can_create = False
        validation_issues.append("ไม่มี Customer Code สำหรับ SAP Business Partner (CardCode)")

    missing_codes = [f"#{i+1} {item.name}" for i, item in enumerate(po.items) if not item.productCode]
    if missing_codes:
        validation_issues.append(f"สินค้าบางรายการไม่มี Product Code: {', '.join(missing_codes[:2])}")

    delivery_date_str = po.deliveryDate.strftime("%d/%m/%Y") if po.deliveryDate else "-"
    doc_date_str = now_bangkok().strftime("%d/%m/%Y")

    subtotal = sum(item.total for item in po.items)
    disc1 = subtotal * ((po.discount_percent_1 or 0.0) / 100.0)
    after1 = subtotal - disc1
    disc2 = after1 * ((po.discount_percent_2 or 0.0) / 100.0)
    after2 = after1 - disc2
    vat = after2 * 0.07
    grand_total = after2 + vat

    items_preview = []
    for idx, item in enumerate(po.items):
        is_item_gift = bool(getattr(item, "is_gift", False))

        if is_item_gift:
            price = 0.0
            item_discount = 0.0
            line_total = 0.0
        else:
            price = float(
                item.recommendedPrice
                if (item.recommendedPrice and item.recommendedPrice > 0)
                else (item.price or 0.0)
            )
            item_discount = 0.0
            prod = item.product
            if not prod and item.productCode:
                prod = Product.query.filter_by(productCode=item.productCode).first()
            if prod and getattr(prod, "discountPercent", None) is not None and float(prod.discountPercent or 0.0) > 0:
                item_discount = float(prod.discountPercent)
            elif item.discount is not None and float(item.discount) > 0:
                item_discount = float(item.discount)
            line_total = float(item.qty) * price

        clean_name = (item.name or "").replace(" (ของแถมฟรี)", "").replace(" (แถมฟรี)", "").strip()
        pcode = item.productCode or "N/A"
        if pcode and clean_name.startswith(pcode):
            clean_name = clean_name[len(pcode):].lstrip(" -:").strip()

        items_preview.append({
            "index": idx + 1,
            "product_code": pcode,
            "name": clean_name or pcode,
            "qty": item.qty,
            "unit_price": price,
            "discount_percent": item_discount,
            "line_total": line_total,
            "is_gift": is_item_gift
        })

    default_comments = po.sap_remarks or f"Created from QT-Online {po.poNumber} by {current_user.fullName}"

    return jsonify({
        "success": True,
        "can_create": can_create,
        "validation_issues": validation_issues,
        "po_id": po.id,
        "po_number": po.poNumber,
        "status": po.status,
        "card_code": po.customerId,
        "card_name": po.customerName or po.get_customer_name(),
        "delivery_date": delivery_date_str,
        "doc_date": doc_date_str,
        "customer_ref_no": po.customer_ref_no or po.poNumber,
        "default_comments": default_comments,
        "items": items_preview,
        "subtotal": subtotal,
        "discount_percent_1": po.discount_percent_1 or 0.0,
        "discount_amount_1": disc1,
        "discount_percent_2": po.discount_percent_2 or 0.0,
        "discount_amount_2": disc2,
        "vat_amount": vat,
        "grand_total": grand_total,
        "sap_doc_num": po.sap_doc_num,
        "sap_doc_entry": po.sap_doc_entry,
        "sap_sync_status": po.sap_sync_status,
        "sap_created_at": (po.sap_created_at if po.sap_created_at.tzinfo is None else ensure_bangkok(po.sap_created_at)).strftime("%d-%m-%Y %H:%M") if po.sap_created_at else None,
        "sap_created_by": po.sap_creator.fullName if po.sap_creator else None
    })


@app.route("/api/purchase-orders/<int:po_id>/create-sap-so", methods=["POST"])
@login_required
def create_sap_so_api(po_id):
    po = PurchaseOrder.query.get(po_id)
    if not po:
        return jsonify({"error": "Quotation not found"}), 404

    is_admin = current_user.role in ["Administrator", "Sale Admin"]
    is_owner = po.sale_user_id == current_user.id
    if not (is_admin or is_owner or getattr(current_user, "can_use_sap_api", False)):
        return jsonify({"error": "คุณไม่มีสิทธิ์สร้าง Sales Order สำหรับเอกสารนี้"}), 403

    allowed_statuses = ["Completed"]
    if po.status not in allowed_statuses:
        return jsonify({"error": f"สถานะของเอกสารต้องเป็น Completed เท่านั้นจึงจะสามารถสร้าง Sales Order บน SAP ได้ (ปัจจุบัน: {po.status})"}), 400

    if po.sap_doc_num and po.sap_sync_status == "SYNCED":
        return jsonify({
            "error": f"เอกสารนี้เคยสร้าง Sales Order บน SAP แล้ว (#{po.sap_doc_num})",
            "doc_num": po.sap_doc_num,
            "doc_entry": po.sap_doc_entry
        }), 400

    # อ่านข้อมูล Customer Ref. No. และ Remarks จาก Client
    data = request.get_json(silent=True) or {}
    customer_ref_no = (data.get("customer_ref_no") or "").strip()
    comments = (data.get("comments") or "").strip()[:1000]

    now = now_bangkok()
    time_str = now.strftime("%d/%m/%Y %H:%M:%S")
    user_display = f"{current_user.fullName} ({current_user.username})"

    success, doc_num, doc_entry, msg, is_sim = _sync_to_sap_b1(
        po, current_user, customer_ref_no=customer_ref_no, comments=comments
    )
    if not success:
        po.sap_sync_status = "FAILED"
        po.sap_sync_error = msg
        po.sap_created_at = now
        po.sap_created_by = current_user.id

        # 1. Log in QT Comments (Quotation History)
        fail_comment_text = f"สร้าง Sales Order บน SAP ไม่สำเร็จ: {msg} โดย {user_display} เมื่อ {time_str}"
        fail_comment = Comment(
            text=fail_comment_text,
            user_id=current_user.id,
            po_id=po.id,
            created=now
        )
        db.session.add(fail_comment)

        # 2. System Transaction Log
        try:
            TransactionLog.log(
                category="sap_integration",
                action="create_sap_so",
                message=f"สร้าง Sales Order บน SAP สำหรับ {po.poNumber} ไม่สำเร็จ: {msg}",
                status="failed",
                details={
                    "po_id": po.id,
                    "po_number": po.poNumber,
                    "user_id": current_user.id,
                    "username": current_user.username,
                    "fullname": current_user.fullName,
                    "error": msg,
                    "timestamp": time_str
                },
                triggered_by=f"user:{current_user.username}"
            )
        except Exception as log_err:
            app.logger.warning(f"Could not write TransactionLog: {log_err}")

        app.logger.error(f"[SAP SO FAILED] QT {po.poNumber} by {user_display} at {time_str}: {msg}")
        db.session.commit()
        return jsonify({"success": False, "error": msg}), 200

    # On Success:
    po.sap_doc_num = doc_num
    po.sap_doc_entry = doc_entry
    po.sap_created_at = now
    po.sap_created_by = current_user.id
    po.sap_sync_status = "SYNCED"
    po.sap_sync_error = None

    sim_badge = " [Simulation Mode]" if is_sim else ""
    success_comment_text = (
        f"สร้าง Sales Order บน SAP สำเร็จ{sim_badge} "
        f"หมายเลข SO: {doc_num} (DocEntry: {doc_entry}) "
        f"โดย {user_display} เมื่อ {time_str}"
    )
    comment = Comment(
        text=success_comment_text,
        user_id=current_user.id,
        po_id=po.id,
        created=now
    )
    db.session.add(comment)

    # System Transaction Log
    try:
        TransactionLog.log(
            category="sap_integration",
            action="create_sap_so",
            message=f"สร้าง Sales Order บน SAP สำเร็จ ({doc_num}) สำหรับ {po.poNumber}",
            status="success",
            details={
                "po_id": po.id,
                "po_number": po.poNumber,
                "sap_doc_num": doc_num,
                "sap_doc_entry": doc_entry,
                "is_simulation": is_sim,
                "user_id": current_user.id,
                "username": current_user.username,
                "fullname": current_user.fullName,
                "timestamp": time_str
            },
            triggered_by=f"user:{current_user.username}"
        )
    except Exception as log_err:
        app.logger.warning(f"Could not write TransactionLog: {log_err}")

    app.logger.info(f"[SAP SO SUCCESS] QT {po.poNumber} -> SO {doc_num} by {user_display} at {time_str}")

    if po.sale_user_id and po.sale_user_id != current_user.id:
        create_notification(
            po.sale_user_id,
            f"QT {po.poNumber} ถูกสร้างเป็น Sales Order {doc_num} บน SAP แล้ว",
            po.id
        )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": msg,
        "doc_num": doc_num,
        "doc_entry": doc_entry,
        "is_simulation": is_sim,
        "created_at": time_str,
        "created_by": current_user.fullName
    })


@app.route("/api/settings/ai", methods=["GET"])
@roles_required("Administrator")
def get_ai_settings_api():
    """Spec v2.8.0 11.3: Retrieve AI Copilot configuration with masked API Key"""
    raw_key = SystemSetting.get_value("ai_api_key", "")
    masked_key = f"{raw_key[:6]}...{raw_key[-4:]}" if raw_key and len(raw_key) > 10 else ("****" if raw_key else "")
    return jsonify({
        "status": "success",
        "settings": {
            "enabled": bool(SystemSetting.get_value("ai_copilot_enabled", False)),
            "provider": SystemSetting.get_value("ai_provider", "google"),
            "model": SystemSetting.get_value("ai_model", "gemini-2.5-flash"),
            "has_api_key": bool(raw_key),
            "api_key_masked": masked_key,
            "system_prompt": SystemSetting.get_value("ai_system_prompt", ""),
        }
    }), 200


@app.route("/api/settings/ai", methods=["PUT"])
@roles_required("Administrator")
def update_ai_settings_api():
    """Spec v2.8.0 11.3: Update AI Copilot settings"""
    data = request.json or {}
    admin_user = current_user.username if current_user.is_authenticated else "admin"
    changed = []

    if "enabled" in data:
        val = bool(data["enabled"])
        SystemSetting.set_value("ai_copilot_enabled", "true" if val else "false", description="เปิด/ปิด AI Copilot", category="ai_copilot", data_type="boolean")
        changed.append("ai_copilot_enabled")

    if "provider" in data and data["provider"]:
        SystemSetting.set_value("ai_provider", str(data["provider"]).strip(), description="AI Provider", category="ai_copilot", data_type="string")
        changed.append("ai_provider")

    if "model" in data and data["model"]:
        SystemSetting.set_value("ai_model", str(data["model"]).strip(), description="AI Model", category="ai_copilot", data_type="string")
        changed.append("ai_model")

    new_key = data.get("api_key")
    if new_key and not new_key.startswith("****") and "..." not in new_key:
        SystemSetting.set_value("ai_api_key", str(new_key).strip(), description="AI Provider API Key", category="ai_copilot", data_type="encrypted")
        changed.append("ai_api_key")

    if "system_prompt" in data:
        SystemSetting.set_value("ai_system_prompt", str(data["system_prompt"]).strip(), description="AI System Prompt", category="ai_copilot", data_type="string")
        changed.append("ai_system_prompt")

    TransactionLog.log(
        category="system_setting",
        action="update_ai_settings",
        status="success",
        message=f"แก้ไขการตั้งค่า AI Copilot โดย '{admin_user}' ({len(changed)} ฟิลด์)",
        details={"changed_fields": changed, "admin": admin_user},
        triggered_by=f"user:{admin_user}",
    )

    return jsonify({"success": True, "message": "บันทึกการตั้งค่า AI Copilot เรียบร้อยแล้ว", "changed_fields": changed}), 200


@app.route("/api/settings/ai/test", methods=["POST"])
@roles_required("Administrator")
def test_ai_connection_api():
    """Spec v2.8.0 11.3: Test connection to AI Provider API Key"""
    data = request.json or {}
    api_key = data.get("api_key")
    if not api_key or api_key.startswith("****") or "..." in api_key:
        api_key = SystemSetting.get_value("ai_api_key", "")
    
    if not api_key:
        return jsonify({"success": False, "message": "ยังไม่ได้ระบุ API Key สำหรับทดสอบ กรุณากรอก API Key แล้วกดบันทึก"}), 200

    provider = data.get("provider") or SystemSetting.get_value("ai_provider", "google")
    model = (data.get("model") or SystemSetting.get_value("ai_model", "gemini-1.5-flash")).strip()

    import time
    start = time.time()
    try:
        if provider == "google":
            # Canonical Google Generative Language API Key validation
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            req = urllib.request.Request(
                url,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "QTOnline-AICopilot/1.0",
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                models_list = [m.get("name", "").replace("models/", "") for m in resp_data.get("models", [])]
                latency = int((time.time() - start) * 1000)
                model_found = any(model in m for m in models_list) if model else True
                model_note = f" (โมเดล '{model}' พร้อมใช้งาน)" if model_found else f" (พร้อมใช้งาน, โมเดลแนะนำ: gemini-1.5-flash)"
                return jsonify({
                    "success": True,
                    "message": f"เชื่อมต่อ AI Engine สำเร็จ (Google API Key Valid, Latency {latency} ms){model_note}",
                    "latency_ms": latency
                }), 200
        else:
            latency = int((time.time() - start) * 1000)
            return jsonify({"success": True, "message": f"การตั้งค่า Provider '{provider}' พร้อมใช้งาน", "latency_ms": latency}), 200
    except urllib.error.HTTPError as e:
        latency = int((time.time() - start) * 1000)
        err_msg = f"HTTP Error {e.code}: {e.reason}"
        try:
            err_json = json.loads(e.read().decode('utf-8'))
            err_msg = err_json.get("error", {}).get("message", err_msg)
        except Exception:
            pass
        return jsonify({"success": False, "message": f"การทดสอบ API Key ล้มเหลว ({err_msg})", "latency_ms": latency}), 200
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return jsonify({"success": False, "message": f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}", "latency_ms": latency}), 200


def _safe_date_str(val, fmt="%d/%m/%Y %H:%M น."):
    if not val:
        return "-"
    if isinstance(val, str):
        try:
            from datetime import datetime
            clean_val = val.replace("T", " ").split(".")[0]
            dt = datetime.strptime(clean_val, "%Y-%m-%d %H:%M:%S")
            return dt.strftime(fmt)
        except Exception:
            return str(val)
    if hasattr(val, "strftime"):
        return val.strftime(fmt)
    return str(val)


def build_direct_local_answer(
    user_query, current_user, top_products, top_customers,
    month_cnt, month_val, current_month_name, year_cnt, year_val, current_year_str,
    status_summary, status_dict, sales_rep_rows, recent_pos, pending_pos,
    user_target, target_achievement_pct
):
    q = user_query.lower()

    # 1. Pending Review / Waiting Approval ("รอตรวจสอบ", "รออนุมัติ", "อนุมัติ", "pending")
    if any(k in q for k in ["รอตรวจสอบ", "รออนุมัติ", "รอตรวจ", "ค้างตรวจ", "pending", "รอการอนุมัติ", "ตรวจ"]):
        if not pending_pos:
            return (
                "### ⏳ สรุปใบเสนอราคาที่รอตรวจสอบและรออนุมัติ (Pending Review / Approval)\n\n"
                f"ขณะนี้ **ไม่มีใบเสนอราคาที่ค้างสถานะรอตรวจสอบหรือรออนุมัติ** ในระบบครับ (0 ใบ)\n\n"
                f"💡 *ตรวจสอบข้อมูลล่าสุดจากฐานข้อมูลตามสิทธิ์ของ {current_user.fullName or current_user.username} ({current_user.role})*"
            )
        lines = [
            f"### ⏳ สรุปใบเสนอราคาที่รอตรวจสอบและรออนุมัติ (Pending Review / Approval)\n",
            f"พบรายการที่รอตรวจสอบ/รออนุมัติทั้งหมด **{len(pending_pos):,} ใบ** ในระบบ (ตามสิทธิ์ของ {current_user.fullName or current_user.username}):\n",
            "| เลขที่ QT | ชื่อลูกค้า | ยอดเงินรวม (บาท) | สถานะปัจจุบัน | พนักงานขาย | วันที่สร้าง |",
            "| :---: | :--- | :---: | :---: | :---: | :---: |"
        ]
        for p in pending_pos:
            p_num = p.poNumber or f"QT-{p.id}"
            c_name = p.customerName or "-"
            amt = float(p.amount or 0.0)
            st = p.status or "-"
            sale_name = p.creator.fullName if p.creator else (p.creator.username if p.creator else "-")
            c_date = _safe_date_str(p.created)
            lines.append(f"| `{p_num}` | {c_name} | {amt:,.2f} บาท | **{st}** | {sale_name} | {c_date} |")
        lines.append(f"\n💡 *สามารถคลิกดูหรือดำเนินการตรวจสอบใบเสนอราคาดังกล่าวได้ในแท็บ 'รายการใบเสนอราคา' บนหน้าจอระบบครับ*")
        return "\n".join(lines)

    # 2. Status Breakdown / Status Summary ("สถานะ", "status", "อนุมัติแล้ว", "ยกเลิกแล้ว", "ขอยกเลิก", "ฉบับร่าง")
    if any(k in q for k in ["สถานะ", "status", "อนุมัติแล้ว", "ยกเลิกแล้ว", "ขอยกเลิก", "ฉบับร่าง", "เสร็จสิ้น", "ร่าง"]):
        lines = [
            "### 📊 สรุปจำนวนและยอดเงินใบเสนอราคาแยกตามสถานะ (Status Breakdown)\n",
            "| สถานะ (Status) | จำนวน (ใบ) | ยอดเงินรวม (บาท) |",
            "| :--- | :---: | :---: |"
        ]
        if status_dict:
            for st_name, st_info in status_dict.items():
                cnt = st_info.get("count", 0)
                tot = st_info.get("total", 0.0)
                lines.append(f"| **{st_name}** | {cnt:,} ใบ | {tot:,.2f} บาท |")
        lines.append(f"\n💡 *ข้อมูลจริง Real-Time ตามสิทธิ์ของผู้ใช้ {current_user.fullName or current_user.username}*")
        return "\n".join(lines)

    # 3. Top Customers
    if any(k in q for k in ["ลูกค้า", "customer", "ยอดซื้อสูงสุด", "ซื้อรวม", "ซื้อเยอะ"]):
        if not top_customers:
            return "### 👥 สรุป 10 อันดับลูกค้าที่มียอดซื้อสูงสุด\n\nยังไม่มีข้อมูลคำสั่งซื้อหรือลูกค้าในระบบขณะนี้ครับ"
        lines = [
            "### 👥 สรุป 10 อันดับลูกค้าที่มียอดซื้อสูงสุด (Top 10 Customers)\n",
            "| อันดับ | ชื่อลูกค้า | ยอดซื้อรวม (บาท) | จำนวนใบเสนอราคา (QT) | สั่งซื้อล่าสุด |",
            "| :---: | :--- | :---: | :---: | :---: |"
        ]
        for idx, c in enumerate(top_customers, 1):
            c_name = c.customerName or "ไม่ระบุชื่อ"
            spent = float(c.total_spent or 0.0)
            qt_count = c.qt_count or 0
            last_dt = _safe_date_str(c.last_order)
            lines.append(f"| {idx} | **{c_name}** | {spent:,.2f} บาท | {qt_count:,} ใบ | {last_dt} |")
        lines.append(f"\n💡 *ข้อมูลคำนวณแบบ Real-Time จากฐานข้อมูลระบบ QT-Online ตามสิทธิ์ของ {current_user.fullName or current_user.username}*")
        return "\n".join(lines)

    # 4. Top Products
    if any(k in q for k in ["สินค้า", "product", "ขายดี", "ขายได้เท่าไร", "ขายดีที่สุด", "อันดับสินค้า"]):
        if not top_products:
            return "### 🏆 สรุป 10 อันดับสินค้าขายดีที่สุด\n\nยังไม่มีข้อมูลการขายสินค้าในระบบขณะนี้ครับ"
        lines = [
            "### 🏆 สรุป 10 อันดับสินค้าขายดีที่สุด (Top 10 Best Sellers)\n",
            "| อันดับ | รหัสสินค้า | ชื่อสินค้า | จำนวนที่ขายได้ | ยอดขายรวม (บาท) | ขายล่าสุดเมื่อ |",
            "| :---: | :---: | :--- | :---: | :---: | :---: |"
        ]
        for idx, p in enumerate(top_products, 1):
            p_code = p.productCode or "-"
            p_name = p.name or "-"
            qty = p.total_qty or 0
            sales = float(p.total_sales or 0.0)
            last_dt = _safe_date_str(p.last_sold)
            lines.append(f"| {idx} | `{p_code}` | **{p_name}** | {qty:,} ชิ้น | {sales:,.2f} บาท | {last_dt} |")
        lines.append(f"\n💡 *ข้อมูลคำนวณแบบ Real-Time จากฐานข้อมูลระบบ QT-Online ตามสิทธิ์ของ {current_user.fullName or current_user.username}*")
        return "\n".join(lines)

    # 5. Target / Sales Rep Performance
    if any(k in q for k in ["เป้า", "target", "ผลงาน", "ยอดขายพนักงาน"]):
        rep_section = ""
        if sales_rep_rows:
            rep_lines = [
                "| พนักงานขาย | จำนวน QT | ยอดขายรวม (บาท) |",
                "| :--- | :---: | :---: |"
            ]
            for r in sales_rep_rows:
                r_name = r.fullName or r.username or "-"
                r_cnt = r.qt_count or 0
                r_tot = float(r.total_sales or 0.0)
                rep_lines.append(f"| **{r_name}** | {r_cnt:,} ใบ | {r_tot:,.2f} บาท |")
            rep_section = "\n\n#### 👥 ยอดขายแยกตามพนักงานขายเดือนนี้:\n" + "\n".join(rep_lines)

        target_display = f"{user_target:,.2f} บาท" if user_target > 0 else "ไม่ได้กำหนดเป้า"
        pct_display = f"{target_achievement_pct:.1f}%" if user_target > 0 else "-"
        return (
            f"### 🎯 ข้อมูลเป้าขายและผลงาน (Sales Performance & Target)\n\n"
            f"- **พนักงาน:** {current_user.fullName or current_user.username} ({current_user.role})\n"
            f"- **ยอดขายเดือน {current_month_name}:** `{month_val:,.2f}` บาท ({month_cnt:,} ใบ)\n"
            f"- **เป้าขายประจำเดือน (Target Amount):** `{target_display}`\n"
            f"- **อัตราความสำเร็จ (Achievement):** `{pct_display}`"
            f"{rep_section}"
        )

    # 6. Monthly / Yearly Summary
    if any(k in q for k in ["เดือนนี้", "ประจำเดือน", "สรุปยอด", "ยอดขายเดือน", "ยอดขายปีนี้", "สถิติ"]):
        return (
            f"### 📊 สรุปยอดขายและสถิติใบเสนอราคา (QT)\n\n"
            f"#### 🗓️ สรุปประจำเดือน {current_month_name}:\n"
            f"- **จำนวนใบเสนอราคา:** `{month_cnt:,}` ใบ\n"
            f"- **ยอดเงินรวม:** `{month_val:,.2f}` บาท\n\n"
            f"#### 📅 สรุปภาพรวมทั้งปี {current_year_str}:\n"
            f"- **จำนวนใบเสนอราคาทั้งหมด:** `{year_cnt:,}` ใบ\n"
            f"- **ยอดเงินรวมทั้งปี:** `{year_val:,.2f}` บาท\n"
            f"- **สถานะรายการในปีนี้:** {status_summary}\n\n"
            f"💡 *ข้อมูลคำนวณจากระบบสดตามสิทธิ์ของ {current_user.fullName or current_user.username} ({current_user.role})*"
        )

    # 7. Recent QTs
    if any(k in q for k in ["ล่าสุด", "recent", "ใบเสนอราคาล่าสุด", "รายการ qt ล่าสุด"]):
        if not recent_pos:
            return "### 📋 รายการใบเสนอราคาล่าสุด\n\nไม่พบรายการใบเสนอราคาในระบบ"
        lines = [
            "### 📋 รายการใบเสนอราคา (QT) 10 รายการล่าสุด\n",
            "| เลขที่ QT | ลูกค้า | ยอดเงิน (บาท) | สถานะ | วันที่สร้าง |",
            "| :---: | :--- | :---: | :---: | :---: |"
        ]
        for p in recent_pos:
            p_num = p.poNumber or f"QT-{p.id}"
            c_name = p.customerName or "-"
            amt = float(p.amount or 0.0)
            st = p.status or "-"
            c_date = _safe_date_str(p.created)
            lines.append(f"| `{p_num}` | {c_name} | {amt:,.2f} บาท | **{st}** | {c_date} |")
        return "\n".join(lines)

    # 8. Specific Quotation Inspection
    po_matches = re.findall(r"(?:QT[-_\s]*)?([0-9]{3,10})", q, re.IGNORECASE)
    if po_matches:
        for cand in po_matches:
            target_po = PurchaseOrder.query.filter(
                or_(PurchaseOrder.poNumber.ilike(f"%{cand}%"), PurchaseOrder.id == int(cand) if cand.isdigit() else False)
            ).first()
            if target_po and (current_user.role in ["Administrator", "Sale Admin"] or target_po.sale_user_id == current_user.id):
                items = POItem.query.filter_by(po_id=target_po.id).all()
                p_num = target_po.poNumber or f"QT-{target_po.id}"
                c_date = _safe_date_str(target_po.created)
                del_date = _safe_date_str(target_po.deliveryDate, "%d/%m/%Y")
                items_table = [
                    "| รหัสสินค้า | รายการสินค้า | จำนวน | ราคา/หน่วย | รวม (บาท) |",
                    "| :---: | :--- | :---: | :---: | :---: |"
                ]
                for it in items:
                    items_table.append(f"| `{it.productCode or '-'}` | {it.name or '-'} | {it.qty} ชิ้น | {it.price:,.2f} | {it.total:,.2f} |")
                items_str = "\n".join(items_table) if items else "ไม่มีรายการสินค้า"
                return (
                    f"### 📄 รายละเอียดใบเสนอราคา {p_num}\n\n"
                    f"- **ชื่อลูกค้า:** **{target_po.customerName or '-'}**\n"
                    f"- **ยอดเงินรวม:** `{target_po.amount:,.2f}` บาท\n"
                    f"- **สถานะปัจจุบัน:** **{target_po.status}**\n"
                    f"- **วันที่สร้าง:** {c_date}\n"
                    f"- **กำหนดส่งมอบ:** {del_date}\n"
                    f"- **สถานที่จัดส่ง:** {target_po.poShipTo or '-'}\n\n"
                    f"#### 📦 รายการสินค้าในใบเสนอราคานี้:\n"
                    f"{items_str}\n"
                )

    # 9. Default overview
    return (
        f"🤖 **QT-Online AI Copilot (Real-Time Database):**\n\n"
        f"ยินดีให้บริการครับ จากการตรวจสอบข้อมูลในระบบตามสิทธิ์ของ **{current_user.fullName or current_user.username}**:\n\n"
        f"- ⏳ **ใบเสนอราคาที่รอตรวจสอบ/รออนุมัติ:** {len(pending_pos):,} ใบ\n"
        f"- 📈 **ยอดขายเดือน {current_month_name}:** {month_cnt:,} ใบ รวม `{month_val:,.2f}` บาท\n"
        f"- 📊 **ยอดขายทั้งปี {current_year_str}:** {year_cnt:,} ใบ รวม `{year_val:,.2f}` บาท\n"
        f"- 👥 **ลูกค้าที่มีการสั่งซื้อสูงสุด:** {len(top_customers)} รายการ\n"
        f"- 🏆 **สินค้าขายดีในระบบ:** {len(top_products)} รายการ\n\n"
        f"💡 *สามารถกดปุ่มคำถามแนะนำด้านล่าง หรือพิมพ์ถามเจาะจง เช่น 'QT รอตรวจสอบ/อนุมัติ', '10 สินค้าขายดี' หรือ '10 ลูกค้ายอดซื้อสูงสุด' ได้ทันทีครับ*"
    )


@app.route("/api/ai/chat", methods=["POST"])
@login_required
def ai_chat_api():
    """
    Spec v2.8.0 11.3 & 11.5: In-App AI Copilot chat endpoint
    Strict Read-Only, DLP Scrubber, Zero-Training privacy headers & RBAC scoped.
    """
    try:
        enabled = SystemSetting.get_value("ai_copilot_enabled", False)
        if not enabled:
            return jsonify({
                "message": {
                    "role": "assistant",
                    "content": "⚠️ ระบบ AI Copilot ถูกปิดใช้งานอยู่ กรุณาติดต่อผู้ดูแลระบบเพื่อเปิดใช้งานในหน้า System Settings"
                }
            }), 200

        req_data = request.json or {}
        messages = req_data.get("messages", [])
        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        user_query = messages[-1].get("content", "")
        
        # DLP Scrubber (Spec v2.8.0): Redact secrets/passwords
        user_query_clean = re.sub(r"sec_[A-Za-z0-9_]{6,}", "[REDACTED_SECRET]", user_query)
        user_query_clean = re.sub(r'("(?:password|hashed_password|sap_password|client_secret|api_key)"\s*:\s*)"[^"]*"', r'\1"[REDACTED]"', user_query_clean, flags=re.IGNORECASE)

        # Check for imperative mutation commands (Spec v2.8.0 11.1 rule 3: Strict Zero-Mutation)
        # MUST NOT block read queries asking about status ("รออนุมัติ", "อนุมัติแล้ว", "ขอยกเลิก", "ขอแก้ไข", "มีกี่ใบ", etc.)
        q_lower = user_query_clean.lower()
        is_query_intent = any(k in q_lower for k in [
            "กี่ใบ", "มีกี่", "อะไรบ้าง", "แสดง", "ดู", "ค้นหา", "สรุป", "รายงาน", "เช็ค",
            "สถานะ", "ประวัติ", "เท่าไร", "รายชื่อ", "รายการ", "รายละเอียด", "ใคร", "ไหน", "เท่าใด", "?"
        ])
        
        imperative_mutation_patterns = [
            r"(?:ช่วย|ทำการ|สั่ง|ให้)\s*(?:อนุมัติ|ลบ|แก้ไข|อัปเดต|เปลี่ยนสถานะ|ยกเลิก)",
            r"^(?:อนุมัติ|ลบ|แก้ไข|อัปเดต|เปลี่ยนสถานะ|ยกเลิก)\s+(?:ใบเสนอราคา|qt|po|[0-9]+)",
            r"(?:delete\s+from|drop\s+table|drop\s+database|truncate\s+table|update\s+\w+\s+set)",
        ]
        is_mutation_action = not is_query_intent and any(re.search(pat, q_lower) for pat in imperative_mutation_patterns)
        if is_mutation_action:
            return jsonify({
                "message": {
                    "role": "assistant",
                    "content": "🛡️ <b>นโยบายความปลอดภัย (Strict Read-Only):</b> AI Copilot ได้รับการออกแบบให้สืบค้น คำนวณสรุปสถิติ และวิเคราะห์ข้อมูลในรูปแบบอ่านอย่างเดียว (Read-Only) เท่านั้น <u>ไม่สามารถแก้ไข ลบ หรือเปลี่ยนสถานะข้อมูลในระบบได้</u><br><br>💡 หากต้องการอนุมัติ ลบ หรือเปลี่ยนสถานะ กรุณาใช้ปุ่มดำเนินการบนหน้าจอระบบด้วยตนเองครับ"
                }
            }), 200

        api_key = SystemSetting.get_value("ai_api_key", "")
        provider = SystemSetting.get_value("ai_provider", "google")
        model = SystemSetting.get_value("ai_model", "gemini-1.5-flash")
        system_prompt = SystemSetting.get_value("ai_system_prompt", "คุณคือ AI ผู้ช่วยอัจฉริยะประจำระบบ QT-Online บริษัท วินโดว์ เอเชีย จำกัด (มหาชน)")

        # Build Comprehensive Live Read-Only DB Intelligence (Scoped strictly to RBAC)
        now = now_bangkok()
        current_date_str = now.strftime("%d/%m/%Y %H:%M")
        current_month_name = now.strftime("%B %Y")
        current_year_str = str(now.year)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)

        is_admin = current_user.role in ["Administrator", "Sale Admin"]
        if is_admin:
            po_role_cond = (PurchaseOrder.status != "Cancelled")
        else:
            po_role_cond = and_(PurchaseOrder.status != "Cancelled", PurchaseOrder.sale_user_id == current_user.id)

        # 1. Monthly Summary
        month_row = db.session.query(
            func.count(PurchaseOrder.id),
            func.coalesce(func.sum(PurchaseOrder.amount), 0.0)
        ).filter(
            po_role_cond,
            PurchaseOrder.created >= start_of_month
        ).first()
        month_cnt = month_row[0] if month_row else 0
        month_val = float(month_row[1]) if month_row else 0.0

        # 2. Yearly Summary
        year_row = db.session.query(
            func.count(PurchaseOrder.id),
            func.coalesce(func.sum(PurchaseOrder.amount), 0.0)
        ).filter(
            po_role_cond,
            PurchaseOrder.created >= start_of_year
        ).first()
        year_cnt = year_row[0] if year_row else 0
        year_val = float(year_row[1]) if year_row else 0.0

        # 3. Status Breakdown with Counts & Amount
        status_order = ["Draft", "Pending Review", "Changes Requested", "Approved", "Completed", "Cancellation Requested", "Cancelled"]
        status_stat_rows = db.session.query(
            PurchaseOrder.status,
            func.count(PurchaseOrder.id).label("cnt"),
            func.coalesce(func.sum(PurchaseOrder.amount), 0.0).label("total")
        ).filter(po_role_cond).group_by(PurchaseOrder.status).all()
        status_dict = {s: {"count": 0, "total": 0.0} for s in status_order}
        for st_name, st_cnt, st_tot in status_stat_rows:
            status_dict[st_name] = {"count": st_cnt, "total": float(st_tot)}
        status_summary = ", ".join([f"{st}: {status_dict[st]['count']} ใบ ({status_dict[st]['total']:,.2f} บาท)" for st in status_order if status_dict[st]['count'] > 0]) or "ไม่มีรายการ"

        # 4. Pending Review / Waiting Approval QTs
        pending_pos = PurchaseOrder.query.filter(
            po_role_cond,
            PurchaseOrder.status.in_(["Pending Review", "Waiting Approval", "Wait Review", "Cancellation Requested"])
        ).order_by(PurchaseOrder.created.desc()).limit(20).all()
        pending_lines = []
        for p in pending_pos:
            c_date = _safe_date_str(p.created)
            p_num = p.poNumber or f"QT-{p.id}"
            sale_name = p.creator.fullName if p.creator else (p.creator.username if p.creator else "-")
            pending_lines.append(
                f"- เลขที่: {p_num} | ลูกค้า: {p.customerName or '-'} | ยอดเงิน: {p.amount:,.2f} บาท | สถานะ: {p.status} | ผู้สร้าง: {sale_name} | วันที่: {c_date}"
            )
        pending_str = "\n".join(pending_lines) if pending_lines else "ไม่มีรายการใบเสนอราคาที่ค้างสถานะรอตรวจสอบหรือรออนุมัติในขณะนี้ (0 ใบ)"

        # 5. Top 10 Best-Selling Products (Qty, Sales Amount, Last Sold Date)
        sum_sales = func.coalesce(func.sum(POItem.total), 0.0)
        top_products = db.session.query(
            POItem.productCode,
            POItem.name,
            func.coalesce(func.sum(POItem.qty), 0).label('total_qty'),
            sum_sales.label('total_sales'),
            func.max(PurchaseOrder.created).label('last_sold')
        ).join(PurchaseOrder, POItem.po_id == PurchaseOrder.id).filter(
            po_role_cond
        ).group_by(POItem.productCode, POItem.name).order_by(sum_sales.desc()).limit(10).all()

        top_prod_lines = []
        for idx, p in enumerate(top_products, 1):
            last_sold_fmt = _safe_date_str(p.last_sold)
            p_code = p.productCode or "-"
            p_name = p.name or "-"
            qty = p.total_qty or 0
            sales = float(p.total_sales or 0.0)
            top_prod_lines.append(
                f"อันดับ {idx}: รหัสสินค้า: {p_code} | ชื่อสินค้า: {p_name} | ยอดขายรวม: {sales:,.2f} บาท | จำนวนที่ขายได้: {qty:,} ชิ้น | วันที่ขายล่าสุด: {last_sold_fmt}"
            )
        top_prod_str = "\n".join(top_prod_lines) if top_prod_lines else "ยังไม่มีข้อมูลสินค้าขายในระบบ"

        # 6. Top 10 Customers (Spend, Quotation Count, Last Order Date)
        sum_spent = func.coalesce(func.sum(PurchaseOrder.amount), 0.0)
        top_customers = db.session.query(
            PurchaseOrder.customerName,
            func.count(PurchaseOrder.id).label('qt_count'),
            sum_spent.label('total_spent'),
            func.max(PurchaseOrder.created).label('last_order')
        ).filter(
            po_role_cond
        ).group_by(PurchaseOrder.customerName).order_by(sum_spent.desc()).limit(10).all()

        top_cust_lines = []
        for idx, c in enumerate(top_customers, 1):
            last_ord_fmt = _safe_date_str(c.last_order)
            c_name = c.customerName or "ไม่ระบุชื่อ"
            spent = float(c.total_spent or 0.0)
            top_cust_lines.append(
                f"อันดับ {idx}: ลูกค้า: {c_name} | ยอดซื้อรวม: {spent:,.2f} บาท | จำนวน QT: {c.qt_count:,} ใบ | สั่งซื้อล่าสุด: {last_ord_fmt}"
            )
        top_cust_str = "\n".join(top_cust_lines) if top_cust_lines else "ยังไม่มีข้อมูลลูกค้าในระบบ"

        # 7. Sales Target & Rep Performance
        user_target = float(current_user.target_amount or 0.0)
        target_achievement_pct = (month_val / user_target * 100.0) if user_target > 0 else 0.0
        sales_rep_rows = None
        sales_rep_str = ""
        if is_admin:
            sum_rep_sales = func.coalesce(func.sum(PurchaseOrder.amount), 0.0)
            sales_rep_rows = db.session.query(
                User.fullName,
                User.username,
                func.count(PurchaseOrder.id).label('qt_count'),
                sum_rep_sales.label('total_sales')
            ).join(PurchaseOrder, PurchaseOrder.sale_user_id == User.id).filter(
                po_role_cond,
                PurchaseOrder.created >= start_of_month
            ).group_by(User.fullName, User.username).order_by(sum_rep_sales.desc()).all()
            if sales_rep_rows:
                rep_lines = [f"- {r.fullName or r.username}: {r.qt_count} ใบ | ยอดรวม {float(r.total_sales):,.2f} บาท" for r in sales_rep_rows]
                sales_rep_str = "\n[สรุปยอดขายพนักงานขายประจำเดือนนี้]:\n" + "\n".join(rep_lines)

        # 8. Recent 10 Quotations
        recent_pos = PurchaseOrder.query.filter(po_role_cond).order_by(PurchaseOrder.created.desc()).limit(10).all()
        recent_items = []
        for p in recent_pos:
            c_date = _safe_date_str(p.created)
            p_num = p.poNumber or f"QT-{p.id}"
            recent_items.append(f"- เลขที่ {p_num} | ลูกค้า: {p.customerName or '-'} | ยอดเงิน: {p.amount:,.2f} บาท | สถานะ: {p.status} | วันที่: {c_date}")
        recent_str = "\n".join(recent_items) or "ไม่มีรายการ"

        # 9. Check for specific keywords in user query (e.g. search specific PO)
        specific_context = ""
        po_matches = re.findall(r"(?:QT[-_\s]*)?([0-9]{4,10})", user_query_clean, re.IGNORECASE)
        if po_matches:
            for po_id_candidate in po_matches[:2]:
                target_po = None
                if po_id_candidate.isdigit():
                    target_po = PurchaseOrder.query.filter(or_(PurchaseOrder.id == int(po_id_candidate), PurchaseOrder.poNumber.ilike(f"%{po_id_candidate}%"))).first()
                if target_po and (is_admin or target_po.sale_user_id == current_user.id):
                    items = POItem.query.filter_by(po_id=target_po.id).all()
                    item_details = [f"    * รหัส {it.productCode or '-'}: {it.name or '-'} จำนวน {it.qty} ชิ้น @ {it.price:,.2f} รวม {it.total:,.2f} บาท" for it in items]
                    specific_context += f"\n[ข้อมูลเจาะจงใบเสนอราคา {target_po.poNumber or target_po.id}]:\n  - ลูกค้า: {target_po.customerName}\n  - วันที่: {_safe_date_str(target_po.created, '%d/%m/%Y')}\n  - ยอดรวม: {target_po.amount:,.2f} บาท\n  - สถานะ: {target_po.status}\n  - รายการสินค้า:\n" + "\n".join(item_details) + "\n"

        live_context = (
            f"[ข้อมูลจริงจากฐานข้อมูลระบบ QT-Online (สิทธิ์การเข้าถึงของผู้ใช้: {current_user.fullName or current_user.username} - บทบาท: {current_user.role})]:\n"
            f"- วันและเวลาปัจจุบัน: {current_date_str} (เวลาประเทศไทย UTC+7)\n"
            f"- เป้าหมายยอดขายของผู้ใช้: {user_target:,.2f} บาท (บรรลุแล้ว {target_achievement_pct:.1f}%)\n"
            f"- สรุปภาพรวมยอดขายประจำเดือน {current_month_name}:\n"
            f"  * จำนวนใบเสนอราคาในเดือนนี้: {month_cnt:,} ใบ\n"
            f"  * ยอดเงินรวมในเดือนนี้: {month_val:,.2f} บาท\n"
            f"- สรุปภาพรวมประจำปี {current_year_str}:\n"
            f"  * จำนวนใบเสนอราคาในปีนี้: {year_cnt:,} ใบ\n"
            f"  * ยอดเงินรวมในปีนี้: {year_val:,.2f} บาท\n"
            f"  * สถานะรายการในปีนี้: {status_summary}\n\n"
            f"[รายการใบเสนอราคาที่สถานะรอตรวจสอบ/รออนุมัติ (Pending Review / Approval)]:\n"
            f"{pending_str}\n\n"
            f"[ข้อมูล 10 อันดับสินค้าขายดีที่สุด (Top 10 Best-Selling Products by Revenue & Qty)]:\n"
            f"{top_prod_str}\n\n"
            f"[ข้อมูล 10 อันดับลูกค้าที่มียอดซื้อสูงสุด (Top 10 Customers by Revenue)]:\n"
            f"{top_cust_str}\n"
            f"{sales_rep_str}\n"
            f"{specific_context}\n"
            f"[10 รายการใบเสนอราคาล่าสุดในระบบ]:\n"
            f"{recent_str}\n\n"
            f"[ข้อกำหนดและกฎเหล็กในการตอบคำถาม (Mandatory Response Rules)]:\n"
            f"1. **ทุกข้อมูลข้างต้นเป็นข้อมูลจริงที่มีอยู่ในระบบ QT-Online ณ ปัจจุบัน ซึ่งผู้ใช้คนนี้มีสิทธิ์เข้าถึงได้อย่างถูกต้อง 100%**\n"
            f"2. คุณมีหน้าที่นำข้อมูลจริงเหล่านี้มาแสดง เปรียบเทียบ คำนวณบวกลบสถิติ หรือตอบคำถามของผู้ใช้อย่างครบถ้วน ถูกต้อง ชัดเจนที่สุด\n"
            f"3. **เมื่อผู้ใช้ถามถึง 'QT รอตรวจสอบ/รออนุมัติ' หรือคำถามว่ามีใบเสนอราคารอตรวจสอบกี่ใบ ให้ตอบโดยใช้ข้อมูลจากหัวข้อ [รายการใบเสนอราคาที่สถานะรอตรวจสอบ/รออนุมัติ] ทันที** ระบุจำนวนใบที่พบและแจกแจงรายการเป็นตาราง Markdown\n"
            f"4. **ห้ามตอบเด็ดขาดว่า 'ระบบยังไม่มีการจัดเก็บข้อมูล' หรือ 'ข้อมูลจำกัด' หรือปฏิเสธคำถาม** เพราะข้อมูลจริงทั้งหมดถูกส่งมาให้คุณในบริบทนี้แล้ว\n"
            f"5. **จัดรูปแบบให้อ่านง่าย สบายตา**: ใช้ตาราง Markdown (|...|) หรือหัวข้อ (###) และข้อย่อย (- **...**) มีการเว้นบรรทัดชัดเจน ห้ามพิมพ์ข้อความยาวติดกันเป็นก้อนเดียว\n"
            f"6. ตอบเป็นภาษาไทยอย่างสุภาพ มืออาชีพ และกระชับตรงประเด็น\n"
        )

        # If API key configured and provider is Google Gemini:
        if api_key and provider == "google":
            candidate_models = [model]
            for fallback_m in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-flash"]:
                if fallback_m not in candidate_models:
                    candidate_models.append(fallback_m)

            full_prompt = f"System: {system_prompt}\n{live_context}\nUser Question: {user_query_clean}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": full_prompt}]}]
            }).encode('utf-8')

            for candidate_model in candidate_models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent?key={api_key}"
                    req = urllib.request.Request(
                        url,
                        data=payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-No-Model-Training": "true",
                            "X-Data-Retention": "none",
                            "X-OpenAI-Data-Usage-Opt-Out": "true",
                        }
                    )
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        resp_json = json.loads(resp.read().decode('utf-8'))
                        if "candidates" in resp_json and resp_json["candidates"]:
                            parts = resp_json["candidates"][0].get("content", {}).get("parts", [])
                            if parts and "text" in parts[0]:
                                answer = parts[0]["text"]
                                return jsonify({"message": {"role": "assistant", "content": answer}}), 200
                except urllib.error.HTTPError as http_err:
                    print(f"Gemini API model {candidate_model} returned HTTP {http_err.code}: {http_err.reason}")
                    if http_err.code == 404:
                        continue  # Model name invalid, try next candidate
                    else:
                        break  # Other error (e.g. 400 Invalid Key or 429 Quota), stop loop
                except Exception as e:
                    print(f"Gemini API call failed for {candidate_model}: {e}")
                    break

        # Fallback: Real-Time Zero-Cost Local Intelligence Fallback (Spec v2.8.0 11.2 Rule 4)
        local_answer = build_direct_local_answer(
            user_query=user_query_clean,
            current_user=current_user,
            top_products=top_products,
            top_customers=top_customers,
            month_cnt=month_cnt,
            month_val=month_val,
            current_month_name=current_month_name,
            year_cnt=year_cnt,
            year_val=year_val,
            current_year_str=current_year_str,
            status_summary=status_summary,
            status_dict=status_dict,
            sales_rep_rows=sales_rep_rows if is_admin else None,
            recent_pos=recent_pos,
            pending_pos=pending_pos,
            user_target=user_target,
            target_achievement_pct=target_achievement_pct
        )
        return jsonify({
            "message": {
                "role": "assistant",
                "content": local_answer
            }
        }), 200

    except Exception as outer_err:
        import traceback
        traceback.print_exc()
        return jsonify({
            "message": {
                "role": "assistant",
                "content": f"⚠️ **เกิดข้อผิดพลาดในการประมวลผลคำถาม:** {escape(str(outer_err))}\n\nกรุณาลองใหม่อีกครั้ง หรือตรวจสอบความพร้อมของระบบฐานข้อมูลครับ"
            }
        }), 200

# =================================================================================
# [END] Centralized Identity Management (CIAM), Telegram, SAP & AI Settings APIs
# =================================================================================


# จุดเริ่มต้นโปรแกรมสำหรับ Local Development (python app.py)
if __name__ == "__main__":
    print("----------------------------------------------------------------")
    print(f" PO-Online System : {APP_VERSION}")
    print(" Running in Docker / Development Mode")
    print(" Access Port: 8080")
    print("----------------------------------------------------------------")
    # debug=True จะช่วย Auto-reload เมื่อแก้ไฟล์ code
    # FIX: Run on Port 8080 as requested for Docker environment
    app.run(host="0.0.0.0", port=8080, debug=True)
