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
    get_encryption_key,
    encrypt_data,
    decrypt_data,
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
    CiamSetting,
    CiamAuditLog,
    LoginLog,
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

from werkzeug.utils import secure_filename
import io  # NEW: For PDF in memory
from urllib.parse import urlparse, unquote, quote_plus
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

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", default_db_url)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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


# FIX: Add user_loader callback for Flask-Login (Crucial for session management)
@login_manager.user_loader
def load_user(user_id):
    # This callback is used to reload the user object from the user ID stored in the session
    try:
        return User.query.get(int(user_id))
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
    if current_user.is_authenticated:
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

        if user and bcrypt.check_password_hash(user.password, password):
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
                return jsonify({"success": False, "error": "Account disabled"}), 403

            login_user(user, remember=True)
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

        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    return render_template("login.html", version=APP_VERSION, username="")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


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
    now = now_bangkok()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    query = PurchaseOrder.query
    if current_user.role not in ["Administrator", "Sale Admin"]:
        query = query.filter_by(sale_user_id=current_user.id)

    today_count = query.filter(PurchaseOrder.created >= today).count()
    pos = query.with_entities(PurchaseOrder.status).all()
    status_summary = {}
    for p in pos:
        status_summary[p.status] = status_summary.get(p.status, 0) + 1

    return jsonify(
        {
            "todayCount": today_count,
            "statusSummary": status_summary,
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
                if len(parts) == 2:
                    y, m = parts[0], parts[1]
                    start_dt = datetime(y, m, 1, 0, 0, 0)
                    if m == 12:
                        end_dt = datetime(y + 1, 1, 1, 0, 0, 0)
                    else:
                        end_dt = datetime(y, m + 1, 1, 0, 0, 0)
                    query = query.filter(
                        or_(
                            and_(PurchaseOrder.created >= start_dt, PurchaseOrder.created < end_dt),
                            and_(PurchaseOrder.updatedAt >= start_dt, PurchaseOrder.updatedAt < end_dt),
                        )
                    )
                elif len(parts) == 3:
                    y, m, d = parts[0], parts[1], parts[2]
                    start_dt = datetime(y, m, d, 0, 0, 0)
                    end_dt = start_dt + timedelta(days=1)
                    query = query.filter(
                        or_(
                            and_(PurchaseOrder.created >= start_dt, PurchaseOrder.created < end_dt),
                            and_(PurchaseOrder.updatedAt >= start_dt, PurchaseOrder.updatedAt < end_dt),
                        )
                    )
            except Exception as ex:
                app.logger.warning(f"Invalid month filter format: {month_param}, error: {ex}")

        is_summary = request.args.get("summary", "true").lower() != "false"

        try:
            if is_summary:
                # Fast summary query without heavy items/comments joins
                pos = (
                    query.options(
                        joinedload(PurchaseOrder.creator),
                        joinedload(PurchaseOrder.customer_rel),
                    )
                    .order_by(PurchaseOrder.id.desc())
                    .all()
                )
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
            )
            for item in data.get("items", []):
                prod = (
                    Product.query.get(item["productId"])
                    if item.get("productId")
                    else None
                )
                new_po.items.append(
                    POItem(
                        productId=item.get("productId"),
                        productCode=prod.productCode if prod else None,
                        name=item["name"],
                        qty=item["qty"],
                        price=item["price"],
                        recommendedPrice=item.get("recommendedPrice", 0),
                        discount=item.get("discount", 0),
                        total=item["total"],
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

        # Update Items (if provided)
        if "items" in data:
            # Clear existing items
            PurchaseOrder.query.session.execute(
                db.delete(POItem).where(POItem.po_id == id)
            )

            for item in data.get("items", []):
                prod = (
                    Product.query.get(item["productId"])
                    if item.get("productId")
                    else None
                )
                po.items.append(
                    POItem(
                        productId=item.get("productId"),
                        productCode=prod.productCode if prod else None,
                        name=item["name"],
                        qty=item["qty"],
                        price=item["price"],
                        recommendedPrice=item.get("recommendedPrice", 0),
                        discount=item.get("discount", 0),
                        total=item["total"],
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


# [MODIFIED] รองรับการค้นหา Customer (?q=...) และปรับ Format ให้ Dropdown ทำงานได้ 100%
@app.route("/api/customers", methods=["GET"])
@login_required
def list_customers():
    # REMOVED default=1 เพื่อให้รู้ว่า Frontend ไม่ได้ขอ Pagination
    page = request.args.get("page", type=int)
    search = request.args.get("q")
    status = request.args.get("status", "all")  # active, inactive, all

    query = Customer.query
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Customer.customerCode.ilike(term),
                Customer.name.ilike(term),
                Customer.telephone1.ilike(term),
            )
        )

    if status == "active":
        query = query.filter_by(inactive=False)
    elif status == "inactive":
        query = query.filter_by(inactive=True)
    # else status == 'all', no filter applied

    query = query.order_by(Customer.id)

    # กรณีขอแบบแบ่งหน้า (สำหรับหน้า Management Tables)
    if page:
        pg = query.paginate(page=page, per_page=100, error_out=False)
        return jsonify(
            {"items": [c.to_dict() for c in pg.items], "total": pg.total, "page": page}
        )

    # กรณี Dropdown (ไม่ส่ง page มา) -> ต้องส่งกลับเป็น List [] เท่านั้น
    # Default to active if status is not specified for dropdown
    if not page and status == "all":
        query = query.filter_by(inactive=False)

    # ดึงข้อมูลทั้งหมดเพื่อให้ Dropdown แสดงครบ (ไม่จำกัดจำนวน)
    results = query.all()
    # ส่งคืน List โดยตรง
    return jsonify([c.to_dict() for c in results])


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

        # Use Recommended Price for Customer PDF
        unit_price = (
            item.recommendedPrice
            if (item.recommendedPrice and item.recommendedPrice > 0)
            else item.price
        )
        qty = item.qty or 0
        discount = item.discount or 0.0

        line_total = (unit_price * qty) * (1 - discount / 100.0)
        current_subtotal += line_total

        items_for_print.append(
            {
                "index": idx,
                "name": item.name,
                "quantity": qty,
                "unit_price": unit_price,
                "discount": discount,
                "total": line_total,
                "image_src": img_src,
            }
        )

    # Calculations (Custom 6-Line Summary)
    # 1. Subtotal (Recommended Price)
    total_recommended = sum(
        (
            i.recommendedPrice
            if (i.recommendedPrice and i.recommendedPrice > 0)
            else i.price
        )
        * i.qty
        for i in po.items
    )

    # 2. Price Difference Discount (Recommended - Cost)
    total_cost_base = sum(i.price * i.qty for i in po.items)
    price_diff_discount = total_recommended - total_cost_base

    # 3. Bill Discount (2-Step on Cost Base)
    disc1_percent = po.discount_percent_1 or 0.0
    disc1_amount = total_cost_base * (disc1_percent / 100.0)
    total_after_1 = total_cost_base - disc1_amount

    disc2_percent = po.discount_percent_2 or 0.0
    disc2_amount = total_after_1 * (disc2_percent / 100.0)
    total_after_2 = total_after_1 - disc2_amount

    bill_discount_total = disc1_amount + disc2_amount

    # 4. Total After All Discounts
    total_after_discount = total_after_2  # Should equal Recommended - Diff - BillDisc

    # 5. VAT 7%
    vat_amount = total_after_discount * 0.07

    # 6. Grand Total
    grand_total = total_after_discount + vat_amount

    totals_summary = {
        "subtotal_recommended": total_recommended,
        "price_diff_discount": price_diff_discount,
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
        # 1. Total Recommended (Gross Subtotal)
        total_recommended = sum(
            (
                i.recommendedPrice
                if (i.recommendedPrice and i.recommendedPrice > 0)
                else (i.price or 0.0)
            )
            * (i.qty or 0)
            for i in po.items
        )

        # 2. Product Discount (Recommended - Cost)
        total_cost_base = sum((i.price or 0.0) * (i.qty or 0) for i in po.items)
        price_diff_discount = total_recommended - total_cost_base

        # 3. Bill Discount (2-Step on Cost Base)
        disc1_percent = po.discount_percent_1 or 0.0
        disc1_amount = total_cost_base * (disc1_percent / 100.0)
        total_after_1 = total_cost_base - disc1_amount

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

        print(f"✓ Saved signature image: {filename}")

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
                print(f"✓ PDF generated and saved: {pdf_filename}")
            else:
                print("✗ PDF generation returned None (WeasyPrint error?)")
                po.signedFile = None
        except Exception as pdf_error:
            print(f"✗ PDF generation error: {pdf_error}")
            import traceback

            traceback.print_exc()
            po.signedFile = None

        if po.sale_user_id:
            create_notification(
                po.sale_user_id, f"Customer signed QT {po.poNumber}", po.id
            )

        try:
            db.session.commit()
            print("✓ Database updated successfully")

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
            print(f"✗ DB error during commit: {db_err}")
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
        print(f"✗ Sign error: {e}")
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
        new_user = User(
            username=data["username"],
            fullName=data["fullName"],
            password=hashed_password,
            role=data.get("role", "Sale"),
            status="active",
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

    # [NEW] Auto-Migration for missing columns (Schema Update)
    try:
        with db.engine.connect() as conn:
            # Check if columns exist in 'purchase_orders' table
            # Provide raw SQL compatible with PostgreSQL
            result = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='purchase_orders';"
                )
            )
            existing_columns = [row[0] for row in result]

            # List of new columns to add if missing
            new_columns = {
                "customerLocationFile": "TEXT",
                "customerLocationFileUrl": "TEXT",
                "customerLocationUploadedAt": "TIMESTAMP WITHOUT TIME ZONE",
                "customerLocationUploadedBy": "INTEGER",
                "customerPoFile": "TEXT",
                "customerPoFileUrl": "TEXT",
                "customerPoUploadedAt": "TIMESTAMP WITHOUT TIME ZONE",
                "customerPoUploadedBy": "INTEGER",
                "updatedAt": "TIMESTAMP WITHOUT TIME ZONE",
            }

            alter_statements = []
            for col, dtype in new_columns.items():
                # Note: PostgreSQL column names are usually lowercase in information_schema
                if col.lower() not in [c.lower() for c in existing_columns]:
                    print(f"DEBUG: Migrating 'purchase_orders' - Adding column '{col}'")
                    alter_statements.append(
                        f'ALTER TABLE purchase_orders ADD COLUMN "{col}" {dtype};'
                    )

            if alter_statements:
                for stmt in alter_statements:
                    conn.execute(text(stmt))
                conn.commit()
                print("DEBUG: Schema migration completed successfully.")
            else:
                print("DEBUG: Schema is up to date.")

    except Exception as e:
        print(f"WARNING: Auto-migration failed: {e}", file=sys.stderr)


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
    if allowed_ips and client_ip not in allowed_ips:
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
                "email": f"{u.username}@windowasia.com",
                "department": u.role or "General",
                "telegram_chat_id": None,
                "group_name": u.role or "Sale",
                "use_ad_auth": False,
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
    setting = CiamSetting.query.first()
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
        return jsonify(setting.to_dict())

    if request.method == "PUT":
        data = request.json or {}
        if "isEnabled" in data:
            setting.is_enabled = bool(data["isEnabled"])
        if "allowedIps" in data:
            setting.allowed_ips = str(data["allowedIps"]).strip()
        if "defaultRole" in data:
            setting.default_role = str(data["defaultRole"]).strip()
        if data.get("regenerateKey"):
            token = secrets.token_hex(16)
            setting.api_key = f"sec_po_mgmt_{token}"

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
# [END] Centralized Identity Management (CIAM) & System Settings APIs
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
