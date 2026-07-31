import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import os
import time
import uuid
import smtplib
from email.message import EmailMessage
import base64

# --- 1. הגדרות עמוד ועיצוב UI/UX יוקרתי ---
st.set_page_config(page_title="FocusFlow Pro | ניהול משימות מתקדם", page_icon="⚡", layout="centered")

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
        background: linear-gradient(135deg, #090d16 0%, #0f172a 100%);
        color: #f8fafc;
    }

    .task-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 18px;
        border-radius: 16px;
        border-right: 6px solid #3b82f6;
        margin-bottom: 14px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }
    .task-title { font-size: 20px; font-weight: 700; color: #38bdf8; margin-bottom: 4px; }
    .task-desc { font-size: 14px; color: #94a3b8; margin-bottom: 12px; }
    .task-meta { font-size: 12px; color: #cbd5e1; display: flex; justify-content: space-between; align-items: center; }
    .tag { background-color: #1e3a8a; color: #bfdbfe; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    
    .stButton>button {
        border-radius: 12px;
        font-weight: 700;
        transition: all 0.2s ease;
        width: 100%;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
    }
    
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 14px;
        border-radius: 16px;
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
    return {"tasks": [], "archive": [], "reminders": [], "xp": 0, "level": 1, "sender_email": "", "sender_password": ""}

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
        return False, f"שגיאה בשליחת המייל: {str(e)}"

# פונקציה ליצירת קובץ לוח שנה (iCal) שמוסיף תזכורת לאייפון בלחיצה
def get_ics_file_download_link(title, rem_date, rem_time):
    # המרת תאריך ושעה לפורמט תקני של לוח שנה
    dt_str = f"{rem_date.strftime('%Y%m%d')}T{rem_time.strftime('%H%M%S')}Z"
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//FocusFlow Task Manager//EN
BEGIN:VEVENT
SUMMARY:תזכורת למשימה: {title}
DESCRIPTION:משימה מתוך אפליקציית FocusFlow Pro
DTSTART:{dt_str}
DTEND:{dt_str}
BEGIN:VALARM
TRIGGER:-PT0M
ACTION:DISPLAY
DESCRIPTION:תזכורת פעילה
END:VALARM
END:VEVENT
END:VCALENDAR"""
    
    b64 = base64.b64encode(ics_content.encode('utf-8')).decode("utf-8")
    href = f'<a href="data:text/calendar;charset=utf-8,{b64}" download="reminder.ics" style="background-color: #10b981; color: white; padding: 10px 15px; border-radius: 10px; text-decoration: none; font-weight: bold; display: block; text-align: center; margin-top: 10px;">📥 הוסף אירוע/התראה ליומן האייפון (iCal)</a>'
    return href

tasks = st.session_state.app_data['tasks']
archive = st.session_state.app_data.setdefault('archive', [])
reminders = st.session_state.app_data.setdefault('reminders', [])

# --- 3. ניהול ראשי ב-Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎯 משימות", "➕ הוספה", "📊 התקדמות", "⏰ תזכורות", "🗂️ ארכיון", "🍅 פוקוס", "⚙️ הגדרות"
])

# ----------------------------------------
# Tab 1: רשימת משימות ועדכון התקדמות חלקית
# ----------------------------------------
with tab1:
    st.title("⚡ FocusFlow | משימות פעילות")
    
    col1, col2, col3 = st.columns(3)
    active_tasks = len(tasks)
    archived_tasks = len(archive)
    
    with col1: st.metric("רמה 🏆", st.session_state.app_data['level'])
    with col2: st.metric("פעילות ⏳", active_tasks)
    with col3: st.metric("באורכיון 🗂️", archived_tasks)
    
    st.markdown("---")
    
    if not tasks:
        st.info("💡 אין משימות פעילות כרגע. הוסף משימה חדשה בלשונית 'הוספה'.")
    else:
        for idx, task in enumerate(tasks):
            with st.container():
                progress_val = task.get('progress', 0)
                border_color = "#10b981" if progress_val == 100 else "#3b82f6"
                
                st.markdown(f"""
                <div class="task-card" style="border-right: 6px solid {border_color};">
                    <div class="task-title">{task['title']}</div>
                    <div class="task-desc">{task['description'] if task['description'] else 'אין תיאור נוסף'}</div>
                    <div class="task-meta">
                        <span class="tag">{task['category']}</span>
                        <span>📅 יעד: {task['due_date']}</span>
                        <span style="font-weight: bold; color: {'#10b981' if progress_val == 100 else '#38bdf8'};">הושלם: {progress_val}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                new_progress = st.slider(
                    f"עדכן אחוז ביצוע עבור: {task['title']}", 
                    0, 100, int(progress_val), 5, 
                    key=f"slider_{task['id']}"
                )
                
                if new_progress != progress_val:
                    task['progress'] = new_progress
                    if new_progress == 100:
                        archive.append(task)
                        tasks.pop(idx)
                        update_xp(30)
                        save_data(st.session_state.app_data)
                        st.success(f"כל הכבוד! המשימה '{task['title']}' הושלמה במלואה והועברה לארכיון! 🏆")
                        time.sleep(1)
                        st.rerun()
                    else:
                        save_data(st.session_state.app_data)
                
                c1, c2 = st.columns(2)
                if c1.button("✔️ סמן כהושלם מיד (100%)", key=f"t_done_{task['id']}", type="primary"):
                    task['progress'] = 100
                    archive.append(task)
                    tasks.pop(idx)
                    update_xp(30)
                    save_data(st.session_state.app_data)
                    st.success("המשימה הושלמה בהצלחה והועברה לארכיון!")
                    st.rerun()
                if c2.button("🗑️ מחק משימה", key=f"t_del_{task['id']}"):
                    tasks.pop(idx)
                    save_data(st.session_state.app_data)
                    st.rerun()
                
                st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

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
        
        if st.form_submit_button("הוסף למערכת 🚀", type="primary"):
            if title.strip():
                new_task = {
                    "id": str(uuid.uuid4())[:8],
                    "title": title.strip(),
                    "description": desc,
                    "category": category,
                    "due_date": due_date.strftime("%Y-%m-%d"),
                    "progress": 0
                }
                tasks.append(new_task)
                save_data(st.session_state.app_data)
                update_xp(5)
                st.success("המשימה נוספה בהצלחה וקיבלת 5 XP!")
            else:
                st.warning("נא להזין שם משימה.")

# ----------------------------------------
# Tab 3: גרף התקדמות כללי (Analytics)
# ----------------------------------------
with tab3:
    st.header("📊 מדדי התקדמות וגרף ביצוע")
    st.write("כאן תוכל לראות את מצב ההתקדמות הכללי של המשימות הפתוחות שלך:")
    
    if not tasks and not archive:
        st.info("אין מספיק נתונים להצגת גרף. הוסף משימות והתחל לעבוד.")
    else:
        total_active = len(tasks)
        total_archived = len(archive)
        avg_progress = sum([t.get('progress', 0) for t in tasks]) / total_active if total_active > 0 else 0
        
        st.subheader("ממוצע התקדמות למשימות הפתוחות:")
        st.progress(avg_progress / 100.0)
        st.markdown(f"<h3 style='text-align: center; color: #38bdf8;'>{avg_progress:.1f}% הושלמו בסך הכל</h3>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("סטטיסטיקה מפורטת:")
        col_g1, col_g2 = st.columns(2)
        col_g1.metric("משימות פתוחות בעבודה", total_active)
        col_g2.metric("משימות שהושלמו (באנציקלופדיה/ארכיון)", total_archived)

# ----------------------------------------
# Tab 4: תזכורות (עם הורדת אירוע ליומן אייפון + מייל)
# ----------------------------------------
with tab4:
    st.header("⏰ ניהול תזכורות למשימות")
    st.write("בחר משימה פתוחה, קבע לה מועד, קבל אימייל ל־**SHIRPI29@GMAIL.COM** והורד התראה ישירות ליומן האייפון.")
    
    if not tasks:
        st.info("💡 אין משימות פתוחות שאפשר לקשר אליהן תזכורת.")
    else:
        with st.form("reminder_form"):
            task_titles = [t['title'] for t in tasks]
            selected_task_title = st.selectbox("בחר משימה מתוך הרשימה:", task_titles)
            
            rem_date = st.date_input("תאריך התזכורת")
            rem_time = st.time_input("שעת התזכורת")
            send_email_checkbox = st.checkbox("שלח התראה מיידית ל־SHIRPI29@GMAIL.COM 📧", value=True)
            
            submitted_rem = st.form_submit_button("הגדר תזכורת למשימה 🔔", type="primary")
            
            if submitted_rem:
                rem_str = f"{rem_date} בשעה {rem_time}"
                reminders.append({"title": selected_task_title, "time": rem_str, "date_obj": rem_date, "time_obj": rem_time})
                save_data(st.session_state.app_data)
                
                if send_email_checkbox:
                    success, msg = send_email_notification(
                        subject=f"תזכורת למשימה: {selected_task_title}",
                        body=f"היי שיר,\n\nיש לך תזכורת למשימה:\n📌 משימה: {selected_task_title}\n⏰ מועד: {rem_str}\n\nבהצלחה!"
                    )
                    if success: st.success(msg)
                    else: st.warning(f"התזכורת נשמרה, אך שליחת המייל נכשלה: {msg}")
                else:
                    st.success("התזכורת נוספה בהצלחה!")

        # יצירת כפתורי הורדה ליומן Apple (iCal) עבור התזכורות שנוצרו
        if reminders:
            st.markdown("### 📥 הוספה ליומן האייפון (לחץ להורדה והוספה אוטומטית):")
            for idx, r in enumerate(reminders):
                st.write(f"• **{r['title']}** (מועד: {r['time']})")
                # מציג כפתור הורדת קובץ לוח שנה
                st.markdown(get_ics_file_download_link(r['title'], r.get('date_obj', date.today()), r.get('time_obj', datetime.now().time())), unsafe_allow_html=True)
                
                if st.button("מחק תזכורת זו", key=f"rem_del_{idx}"):
                    reminders.pop(idx)
                    save_data(st.session_state.app_data)
                    st.rerun()

# ----------------------------------------
# Tab 5: ארכיון משימות שהושלמו (Archive)
# ----------------------------------------
with tab5:
    st.header("🗂️ ארכיון משימות שהושלמו")
    st.write("כאן שמורות כל המשימות שהושלמו במלואן (100% ביצוע):")
    
    if not archive:
        st.info("הארכיון ריק כרגע. משימות יעברו לכאן אוטומטית ברגע שתסיים אותן.")
    else:
        for idx, item in enumerate(archive):
            st.markdown(f"""
            <div class="task-card" style="border-right: 6px solid #10b981; opacity: 0.85;">
                <div class="task-title" style="color: #34d399;">✅ ~~{item['title']}~~</div>
                <div class="task-desc">{item['description'] if item['description'] else 'ללא תיאור'}</div>
                <div class="task-meta">
                    <span class="tag">{item['category']}</span>
                    <span>📅 יעד מקורי: {item['due_date']}</span>
                    <span style="color: #10b981; font-weight: bold;">הושלם (100%)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("מחק לצמיתות מהארכיון", key=f"arch_del_{idx}"):
                archive.pop(idx)
                save_data(st.session_state.app_data)
                st.rerun()

# ----------------------------------------
# Tab 6: פוקוס פומודורו
# ----------------------------------------
with tab6:
    st.header("🍅 טיימר פוקוס (פומודורו)")
    if st.button("התחל סבב ריכוז (25 דקות) ⏱️", type="primary"):
        st.success("הטיימר הופעל! הישאר ממוקד במשימה הבאה שלך.")
        time.sleep(1)

# ----------------------------------------
# Tab 7: הגדרות ומייל
# ----------------------------------------
with tab7:
    st.header("⚙️ הגדרות מערכת ומייל")
    st.markdown("""
    **הגדרת שליחת מייל ל־SHIRPI29@GMAIL.COM:**
    1. הפעל אימות דו-שלבי בחשבון הגוגל השולח.
    2. צור **סיסמת אפליקציה (App Password)** בהגדרות האבטחה של גוגל (קוד בן 16 תווים).
    3. הכנס כאן למטה את המייל השולח ואת הקוד.
    """)
    
    current_sender = st.session_state.app_data.get("sender_email", "")
    current_pass = st.session_state.app_data.get("sender_password", "")
    
    new_sender = st.text_input("כתובת מייל שולחת (Gmail):", value=current_sender)
    new_pass = st.text_input("סיסמת אפליקציה (App Password):", type="password", value=current_pass)
    
    if st.button("שמור הגדרות מייל 💾", type="primary"):
        st.session_state.app_data["sender_email"] = new_sender.strip()
        st.session_state.app_data["sender_password"] = new_pass.strip()
        save_data(st.session_state.app_data)
        st.success("הגדרות המייל עודכנו בהצלחה!")
