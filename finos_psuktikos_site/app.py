from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# ─── ΡΥΘΜΙΣΕΙΣ EMAIL ──────────────────────────────────────
# Αλλάξτε με τα πραγματικά στοιχεία του θείου σας
EMAIL_SENDER   = "info@psyktikeslyseis.gr"
EMAIL_PASSWORD = "YOUR_EMAIL_PASSWORD"      # ή χρησιμοποιήστε App Password για Gmail
EMAIL_RECEIVER = "thios@psyktikeslyseis.gr" # το email που θα λαμβάνει τα μηνύματα
SMTP_SERVER    = "smtp.gmail.com"           # για Gmail
SMTP_PORT      = 587


# ─── DATABASE SETUP ───────────────────────────────────────
def init_db():
    """Δημιουργεί τη βάση δεδομένων αν δεν υπάρχει."""
    conn = sqlite3.connect("requests.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_requests (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            phone     TEXT NOT NULL,
            email     TEXT,
            service   TEXT,
            message   TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


def save_to_db(data: dict):
    """Αποθηκεύει το αίτημα στη βάση δεδομένων."""
    conn = sqlite3.connect("requests.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO contact_requests (name, phone, email, service, message)
        VALUES (?, ?, ?, ?, ?)
    """, (data["name"], data["phone"], data.get("email", ""),
          data.get("service", ""), data.get("message", "")))
    conn.commit()
    conn.close()


def send_email(data: dict) -> bool:
    """Στέλνει email στον θείο σας με τα στοιχεία του αιτήματος."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 Νέο Αίτημα από {data['name']} – ΨυκτικέςΛύσεις"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = EMAIL_RECEIVER

        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
          <div style="max-width:560px;margin:auto;background:#fff;border-radius:8px;overflow:hidden;">
            <div style="background:#0a1628;padding:20px;text-align:center;">
              <h2 style="color:#00c8e0;margin:0;">ΨυκτικέςΛύσεις</h2>
              <p style="color:#8aa0b4;margin:4px 0 0;">Νέο Αίτημα Επικοινωνίας</p>
            </div>
            <div style="padding:24px;">
              <table style="width:100%;border-collapse:collapse;">
                <tr>
                  <td style="padding:8px 0;color:#666;width:120px;">👤 Όνομα:</td>
                  <td style="padding:8px 0;font-weight:bold;">{data['name']}</td>
                </tr>
                <tr style="background:#f9f9f9;">
                  <td style="padding:8px;color:#666;">📞 Τηλέφωνο:</td>
                  <td style="padding:8px;font-weight:bold;color:#0a1628;">
                    <a href="tel:{data['phone']}">{data['phone']}</a>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0;color:#666;">📧 Email:</td>
                  <td style="padding:8px 0;">{data.get('email', '—')}</td>
                </tr>
                <tr style="background:#f9f9f9;">
                  <td style="padding:8px;color:#666;">🔧 Υπηρεσία:</td>
                  <td style="padding:8px;">{data.get('service', '—')}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;color:#666;vertical-align:top;">💬 Μήνυμα:</td>
                  <td style="padding:8px 0;">{data.get('message', '—')}</td>
                </tr>
              </table>
            </div>
            <div style="background:#f0f0f0;padding:12px;text-align:center;">
              <small style="color:#999;">
                Λήφθηκε: {datetime.now().strftime('%d/%m/%Y %H:%M')}
              </small>
            </div>
          </div>
        </body></html>
        """

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

        return True

    except Exception as e:
        print(f"[Email Error] {e}")
        return False


# ─── ROUTES ───────────────────────────────────────────────

@app.route("/")
def index():
    """Σερβίρει την κύρια σελίδα."""
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    """Δέχεται τα δεδομένα της φόρμας."""
    data = {
        "name":    request.form.get("name", "").strip(),
        "phone":   request.form.get("phone", "").strip(),
        "email":   request.form.get("email", "").strip(),
        "service": request.form.get("service", "").strip(),
        "message": request.form.get("message", "").strip(),
    }

    # Validation
    if not data["name"] or not data["phone"]:
        return jsonify({"success": False, "error": "Συμπληρώστε όνομα και τηλέφωνο."}), 400

    # Αποθήκευση στη βάση
    try:
        save_to_db(data)
    except Exception as e:
        print(f"[DB Error] {e}")

    # Αποστολή email
    email_sent = send_email(data)

    return jsonify({
        "success":    True,
        "email_sent": email_sent,
        "message":    "Το μήνυμά σας ελήφθη! Θα σας καλέσουμε σύντομα."
    })


@app.route("/admin/requests")
def admin_requests():
    """
    Απλό admin endpoint — βλέπει όλα τα αιτήματα.
    ΠΡΟΣΘΕΣΤΕ authentication πριν το βάλετε σε παραγωγή!
    """
    conn = sqlite3.connect("requests.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM contact_requests ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    result = [dict(row) for row in rows]
    return jsonify(result)


# ─── MAIN ─────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("✅ Βάση δεδομένων έτοιμη.")
    print("🚀 Ο server ξεκινά στο http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)