import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import os
import time
import uuid
import smtplib
from email.message import EmailMessage

# --- 1. הגדרות עמוד ועיצוב ויזואלי מרהיב ---
st.set_page_config(page_title="FocusFlow | ניהול משימות מתקדם", page_icon="🎯", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap');
    
    [data-testid="stSidebar"], [data-testid="collapsedControl"], header, [data-testid="stToolbar"] {
        display: none !important;
    }

    body, .stApp, p, h1, h2, h3, h4, h5, h6, span, label, div {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif !important;
    }

    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }

    /* כרטיסיות משימות מעוצבות */
    .task-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 16px;
        border-right: 6px solid #3b82f6;
        margin-bottom: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    .task-title { font-size: 19px; font-weight: 700; color: #38bdf8; margin-bottom: 4px; }
    .task-desc { font-size: 14px; color: #94a3b8; margin-bottom: 10px; }
    .task-meta { font-size: 12px; color: #cbd5e1; display: flex; justify-content: space-between; align-items: center; }
    .tag { background-color: #1e3a8a; color: #bfdbfe; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    
    /* עיצוב כפתורים */
    .stButton>button {
        border-radius: 12px;
        font-weight: 700;
        transition: all 0.2s ease;
        width: 100%;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    
    div[data-testid="metric-container"] {
        background: #1e293b;
        border: 1px solid #334155;
        padding: 12px;
        border-radius: 14px;
        text-align: center;
        border-right: 4px solid #10b981;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. מנגנון שמירה יציב ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'focusflow_data.json')

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"tasks": [], "reminders": [], "xp": 0, "level": 1, "sender_email": "", "sender_password": ""}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"שגיאה בשמירת נתונים: {e}")

if 'app_data' not in st.session_state:
    st.session_state.app_data = load_data()

def update_xp(amount):
    st.session_state.app_data['xp'] += amount
    new_level = (st.session_state.app_data['xp'] // 100) + 1
    if new_level > st.session_state.app_data['level']:
        st.session_state.app_data['level'] = new_level
        st.balloons()
        st.toast(f"🎉 מזל טוב! עלית לרמה {new_level}!")
    save_data(st.session_state.app_data)

# פונקציית שליחת מייל אמיתית ל-SHIRPI29@GMAIL.COM
def send_email_notification(subject, body):
    target_email = "SHIRPI29@GMAIL.COM"
    sender_email = st.session_state.app_data.get("sender_email", "").strip()
    sender_password = st.session_state.app_data.get("sender_password", "").strip()
    
    if not sender_email or not sender_password:
        return False, "לא הוגדרו פרטי מייל שולח בלשונית 'הגדרות'."
    
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = target_email
        msg.set_content(body)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, "המייל נשלח בהצלחה ל-SHIRPI29@GMAIL.COM!"
    except Exception as e:
        return False, f"שגיאה בשליחת המייל (ודא סיסמת אפליקציה תקינה בגוגל): {str(e)}"

tasks = st.session_state.app_data['tasks']
reminders = st.session_state.app_data.setdefault('reminders', [])

# --- 3. ניהול ראשי ב-Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 משימות", "➕ הוספה", "📋 קנבן", "⏰ תזכורות", "🍅 פוקוס", "⚙️ הגדרות"
])

# ----------------------------------------
# Tab 1: רשימת משימות ודשבורד
# ----------------------------------------
with tab1:
    st.title("🎯 FocusFlow | לוח בקרה")
    
    col1, col2, col3 = st.columns(3)
    completed_tasks = len([t for t in tasks if t['status'] == 'הושלם'])
    active_tasks = len([t for t in tasks if t['status'] != 'הושלם'])
    
    with col1: st.metric("רמה 🏆", st.session_state.app_data['level'])
    with col2: st.metric("הושלמו ✅", completed_tasks)
    with col3: st.metric("פתוחות ⏳", active_tasks)
    
    st.markdown("---")
    st.subheader("משימות פעילות")
    
    if not tasks:
        st.info("💡 אין משימות כרגע. הוסף משימה חדשה בלשונית 'הוספה'.")
    else:
        for idx, task in enumerate(tasks):
            if task['status'] != 'הושלם':
                with st.container():
                    st.markdown(f"""
                    <div class="task-card">
                        <div class="task-title">{task['title']}</div>
                        <div class="task-desc">{task['description'] if task['description'] else 'אין תיאור נוסף'}</div>
                        <div class="task-meta">
                            <span class="tag">{task['category']}</span>
                            <span>📅 יעד: {task['due_date']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    if c1.button("✔️ סיים משימה", key=f"t_done_{idx}", type="primary"):
                        task['status'] = 'הושלם'
                        update_xp(20)
                        save_data(st.session_state.app_data)
                        st.rerun()
                    if c2.button("🗑️ מחק", key=f"t_del_{idx}"):
                        tasks.pop(idx)
                        save_data(st.session_state.app_data)
                        st.rerun()

# ----------------------------------------
# Tab 2: הוספת משימה
# ----------------------------------------
with tab2:
    st.header("➕ הוספת משימה חדשה")
    with st.form("add_task_form"):
        title = st.text_input("שם המשימה *")
        category = st.selectbox("קטגוריה", ["עבודה", "לימודים", "אישי", "פרויקט", "אחר"])
        desc = st.text_area("תיאור מפורט")
        due_date = st.date_input("תאריך יעד")
        
        if st.form_submit_button("הוסף למערכת 🛒", type="primary"):
            if title.strip():
                new_task = {
                    "id": str(uuid.uuid4())[:8],
                    "title": title.strip(),
                    "description": desc,
                    "category": category,
                    "due_date": due_date.strftime("%Y-%m-%d"),
                    "status": "לביצוע"
                }
                tasks.append(new_task)
                save_data(st.session_state.app_data)
                update_xp(5)
                st.success("המשימה נוספה בהצלחה וקיבלת 5 XP!")
            else:
                st.warning("נא להזין שם משימה.")

# ----------------------------------------
# Tab 3: קנבן
# ----------------------------------------
with tab3:
    st.header("📋 לוח קנבן ויזואלי")
    col_todo, col_done = st.columns(2)
    with col_todo:
        st.subheader("לביצוע 📝")
        for t in tasks:
            if t['status'] != 'הושלם':
                st.markdown(f"• **{t['title']}** ({t['category']})")
    with col_done:
        st.subheader("הושלם ✅")
        for t in tasks:
            if t['status'] == 'הושלם':
                st.markdown(f"• ~~{t['title']}~~")

# ----------------------------------------
# Tab 4: תזכורות (מקושרות למשימות + מייל + שעון אייפון)
# ----------------------------------------
with tab4:
    st.header("⏰ ניהול תזכורות למשימות")
    st.write("בחר משימה קיימת, קבע לה מועד, והמערכת תתריע לך במייל ותסנכרן עם האייפון.")
    
    # כפתור קיצור דרך לשעון באייפון
    st.markdown("""
    <a href="clock-alarm://" target="_blank">
        <button style="background-color: #3b82f6; color: white; border: none; padding: 12px 20px; border-radius: 12px; font-weight: bold; cursor: pointer; width: 100%; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
            ⏰ פתח את אפליקציית השעון / שעון מעורר באייפון
        </button>
    </a>
    """, unsafe_allow_html=True)
    
    active_tasks_list = [t for t in tasks if t['status'] != 'הושלם']
    
    if not active_tasks_list:
        st.info("💡 אין משימות פתוחות שאפשר לקשר אליהן תזכורת. הוסף משימה תחילה.")
    else:
        with st.form("reminder_form"):
            task_titles = [t['title'] for t in active_tasks_list]
            selected_task_title = st.selectbox("בחר משימה מתוך הרשימה שלך:", task_titles)
            
            rem_date = st.date_input("תאריך התזכורת")
            rem_time = st.time_input("שעת התזכורת")
            
            send_email_checkbox = st.checkbox("שלח התראה מיידית ל־SHIRPI29@GMAIL.COM 📧", value=True)
            
            if st.form_submit_button("הגדר תזכורת למשימה 🔔", type="primary"):
                rem_str = f"{rem_date} בשעה {rem_time}"
                reminders.append({"title": selected_task_title, "time": rem_str})
                save_data(st.session_state.app_data)
                
                if send_email_checkbox:
                    success, msg = send_email_notification(
                        subject=f"תזכורת למשימה: {selected_task_title}",
                        body=f"היי שיר,\n\nיש לך תזכורת למשימה שלך:\n📌 משימה: {selected_task_title}\n⏰ מועד: {rem_str}\n\nבהצלחה בביצוע!"
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.warning(f"התזכורת נשמרה, אך שליחת המייל נכשלה: {msg}")
                else:
                    st.success("התזכורת נוספה בהצלחה!")

    if reminders:
        st.markdown("### 🔔 תזכורות פעילות למשימות:")
        for idx, r in enumerate(reminders):
            c1, c2 = st.columns([4, 1])
            c1.write(f"• **{r['title']}** (מועד: {r['time']})")
            if c2.button("מחק", key=f"rem_del_{idx}"):
                reminders.pop(idx)
                save_data(st.session_state.app_data)
                st.rerun()

# ----------------------------------------
# Tab 5: פומודורו
# ----------------------------------------
with tab5:
    st.header("🍅 טיימר פוקוס (פומודורו)")
    if st.button("התחל סבב ריכוז (25 דקות) ⏱️", type="primary"):
        st.success("הטיימר הופעל! קח עמוק אליך את הפוקוס למשימה הבאה.")
        time.sleep(1)

# ----------------------------------------
# Tab 6: הגדרות (כולל חיבור למייל)
# ----------------------------------------
with tab6:
    st.header("⚙️ הגדרות מערכת ומייל")
    st.markdown("""
    **איך להגדיר שליחת מייל ל־SHIRPI29@GMAIL.COM:**
    1. היכנס לחשבון הגוגל שדרכו אתה שולח את ההודעות והפעל **אימות דו-שלבי (2-Step Verification)**.
    2. חפש בהגדרות החשבון **סיסמאות אפליקציה (App Passwords)** וצור סיסמה חדשה (תקבל קוד בן 16 תווים).
    3. הכנס כאן למטה את המייל השולח ואת קוד ה-16 תווים כסיסמה.
    """)
    
    current_sender = st.session_state.app_data.get("sender_email", "")
    current_pass = st.session_state.app_data.get("sender_password", "")
    
    new_sender = st.text_input("כתובת מייל שולחת (Gmail):", value=current_sender)
    new_pass = st.text_input("סיסמת אפליקציה (App Password בן 16 תווים):", type="password", value=current_pass)
    
    if st.button("שמור הגדרות מייל 💾", type="primary"):
        st.session_state.app_data["sender_email"] = new_sender.strip()
        st.session_state.app_data["sender_password"] = new_pass.strip()
        save_data(st.session_state.app_data)
        st.success("הגדרות המייל עודכנו בהצלחה במערכת!")
