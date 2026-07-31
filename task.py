import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import os
import time
import uuid
import smtplib
from email.message import EmailMessage

# --- 1. הגדרות עמוד ועיצוב ---
st.set_page_config(page_title="FocusFlow | ניהול משימות מתקדם", page_icon="🎯", layout="centered")

# הזרקת CSS לעיצוב מודרני ותמיכה מלאה ב-RTL
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;800&display=swap');
    
    [data-testid="stSidebar"], [data-testid="collapsedControl"], header, [data-testid="stToolbar"] {
        display: none !important;
    }

    body, .stApp, p, h1, h2, h3, h4, h5, h6, span, label, div {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif !important;
    }
    
    .task-card {
        background-color: #1E293B;
        color: #F8FAFC;
        padding: 15px;
        border-radius: 10px;
        border-right: 5px solid #3B82F6;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .task-title { font-size: 18px; font-weight: bold; margin-bottom: 5px; color: #38BDF8; }
    .task-desc { font-size: 14px; color: #94A3B8; margin-bottom: 10px; }
    .task-meta { font-size: 12px; color: #CBD5E1; display: flex; justify-content: space-between; }
    .tag { background-color: #334155; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
    
    .stButton>button { border-radius: 10px; font-weight: 600; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. מנגנון שמירה מקומית יציבה ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'focusflow_data.json')

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"tasks": [], "reminders": [], "xp": 0, "level": 1}

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

# פונקציית שליחת מייל ל-SHIRPI29@GMAIL.COM
def send_email_notification(subject, body):
    target_email = "SHIRPI29@GMAIL.COM"
    # הערה: כדי לשלוח מייל אוטומטי משרת חיצוני יש להזין סיסמת אפליקציה (App Password) מתוך חשבון הגוגל השולח.
    # אם מוגדרת כתובת שולח, המערכת תנסה לשלוח.
    sender_email = st.session_state.app_data.get("sender_email", "")
    sender_password = st.session_state.app_data.get("sender_password", "")
    
    if not sender_email or not sender_password:
        return False, "לא הוגדרה כתובת מייל או סיסמת אפליקציה בלשונית הגדרות."
    
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = target_email
        msg.set_content(body)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, "האימייל נשלח בהצלחה ל-SHIRPI29@GMAIL.COM!"
    except Exception as e:
        return False, f"שגיאה בשליחת המייל: {str(e)}"

tasks = st.session_state.app_data['tasks']
reminders = st.session_state.app_data.setdefault('reminders', [])

# --- 3. ממשק משתמש דרך Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🛒 רשימה", "➕ הוספה", "📋 קנבן", "⏰ תזכורות", "🍅 פומודורו", "⚙️ הגדרות"
])

# ----------------------------------------
# Tab 1: רשימה ראשית ודשבורד
# ----------------------------------------
with tab1:
    st.title("🎯 FocusFlow | ניהול משימות")
    
    col1, col2, col3 = st.columns(3)
    completed_tasks = len([t for t in tasks if t['status'] == 'הושלם'])
    active_tasks = len([t for t in tasks if t['status'] != 'הושלם'])
    
    with col1: st.metric("רמה 🏆", st.session_state.app_data['level'])
    with col2: st.metric("הושלמו ✅", completed_tasks)
    with col3: st.metric("פתוחות ⏳", active_tasks)
    
    st.markdown("---")
    st.subheader("משימות לביצוע")
    
    if not tasks:
        st.info("אין משימות כרגע. הוסף משימה בלשונית 'הוספה'.")
    else:
        for idx, task in enumerate(tasks):
            if task['status'] != 'הושלם':
                with st.container():
                    st.markdown(f"""
                    <div class="task-card">
                        <div class="task-title">{task['title']}</div>
                        <div class="task-desc">{task['description']}</div>
                        <div class="task-meta">
                            <span class="tag">{task['category']}</span>
                            <span>📅 {task['due_date']}</span>
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
                st.success("המשימה נוספה בהצלחה!")
            else:
                st.warning("נא להזין שם משימה.")

# ----------------------------------------
# Tab 3: קנבן
# ----------------------------------------
with tab3:
    st.header("📋 לוח קנבן")
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
# Tab 4: תזכורות (שעון מעורר + מייל)
# ----------------------------------------
with tab4:
    st.header("⏰ ניהול תזכורות ושעון מעורר")
    st.write("קבע תזכורת למשימה: המערכת תשלח אימייל אוטומטי ל־**SHIRPI29@GMAIL.COM** ותאפשר לך לפתוח את השעון המעורר באייפון.")
    
    # כפתור קיצור דרך לשעון באייפון
    st.markdown("""
    <a href="clock-alarm://" target="_blank">
        <button style="background-color: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 10px; font-weight: bold; cursor: pointer; width: 100%; margin-bottom: 15px;">
            ⏰ פתח את אפליקציית השעון / שעון מעורר באייפון
        </button>
    </a>
    """, unsafe_allow_html=True)
    
    with st.form("reminder_form"):
        rem_title = st.text_input("כותרת התזכורת (למשל: לקנות חלב / פגישה)")
        rem_date = st.date_input("תאריך התזכורת")
        rem_time = st.time_input("שעת התזכורת")
        
        send_email_checkbox = st.checkbox("שלח התראה מיידית ל־SHIRPI29@GMAIL.COM 📧", value=True)
        
        if st.form_submit_button("הגדר תזכורת 🔔", type="primary"):
            if rem_title.strip():
                rem_str = f"{rem_date} בשעה {rem_time}"
                reminders.append({"title": rem_title, "time": rem_str})
                save_data(st.session_state.app_data)
                
                if send_email_checkbox:
                    success, msg = send_email_notification(
                        subject=f"תזכורת חדשה מ-FocusFlow: {rem_title}",
                        body=f"היי שיר,\n\nיש לך תזכורת חדשה:\nמשימה/אירוע: {rem_title}\nתאריך ושעה: {rem_str}\n\nבהצלחה!"
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.warning(f"התזכורת נשמרה במערכת, אך שליחת המייל נכשלה: {msg}")
                else:
                    st.success("התזכורת נוספה בהצלחה!")
            else:
                st.error("נא להזין כותרת לתזכורת.")

    if reminders:
        st.markdown("### תזכורות פעילות:")
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
    st.header("🍅 טיימר פומודורו לריכוז")
    if st.button("התחל טיימר פוקוס (25 דקות) ⏱️"):
        st.success("הטיימר הופעל! הישאר ממוקד במשימה הבאה שלך.")
        time.sleep(1)

# ----------------------------------------
# Tab 6: הגדרות (כולל הגדרת שליחת מייל)
# ----------------------------------------
with tab6:
    st.header("⚙️ הגדרות מערכת ושליחת מייל")
    st.write("כדי שהאפליקציות יוכלו לשלוח מייל אוטומטי ל־**SHIRPI29@GMAIL.COM**, עליך להזין כאן חשבון גוגל שולח וסיסמת אפליקציה (App Password).")
    
    current_sender = st.session_state.app_data.get("sender_email", "")
    current_pass = st.session_state.app_data.get("sender_password", "")
    
    new_sender = st.text_input("כתובת מייל שולחת (Gmail):", value=current_sender)
    new_pass = st.text_input("סיסמת אפליקציה (App Password מוגדרת מגוגל):", type="password", value=current_pass)
    
    if st.button("שמור הגדרות מייל 💾", type="primary"):
        st.session_state.app_data["sender_email"] = new_sender.strip()
        st.session_state.app_data["sender_password"] = new_pass.strip()
        save_data(st.session_state.app_data)
        st.success("הגדרות המייל נשמרו בהצלחה!")
