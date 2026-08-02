import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import time
import uuid
import smtplib
from email.message import EmailMessage
from supabase import create_client, Client

# --- 1. הגדרות עמוד ועיצוב UI/UX יוקרתי ---
st.set_page_config(page_title="FocusFlow Pro | ניהול משימות מתקדם", page_icon="⚡", layout="centered")

CUSTOM_CSS = """
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
        transition: transform 0.2s ease;
    }
    .task-card:hover {
        transform: translateY(-2px);
    }
    .task-title { font-size: 20px; font-weight: 700; color: #38bdf8; margin-bottom: 4px; }
    .task-desc { font-size: 14px; color: #94a3b8; margin-bottom: 12px; }
    .task-meta { font-size: 12px; color: #cbd5e1; display: flex; justify-content: flex-start; align-items: center; flex-wrap: wrap; gap: 8px;}
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
    
    .timer-display {
        font-size: 72px;
        font-weight: 800;
        text-align: center;
        color: #f43f5e;
        text-shadow: 0 0 20px rgba(244, 63, 94, 0.5);
        margin: 20px 0;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- 2. חיבור ל-SUPABASE ושמירת נתונים ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def load_data():
    default_data = {
        "tasks": [], 
        "archive": [], 
        "reminders": [], 
        "xp": 0, 
        "level": 1, 
        "sender_email": "", 
        "sender_password": "",
        "target_email": ""
    }
    
    if not supabase:
        return default_data
        
    try:
        response = supabase.table("app_data").select("data").eq("id", 1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]["data"]
        else:
            # אם אין שורה במסד הנתונים, ניצור אחת חדשה
            supabase.table("app_data").insert({"id": 1, "data": default_data}).execute()
            return default_data
    except Exception as e:
        st.error(f"שגיאה בטעינת נתונים מ-Supabase: {e}")
        return default_data

def save_data(data):
    if not supabase:
        st.error("הגדרות Supabase חסרות ב-Secrets!")
        return
    try:
        supabase.table("app_data").upsert({"id": 1, "data": data}).execute()
    except Exception as e:
        st.error(f"שגיאה בשמירת נתונים ב-Supabase: {e}")

if 'app_data' not in st.session_state:
    st.session_state.app_data = load_data()

def get_config(key, default=""):
    if key in st.secrets:
        return st.secrets[key]
    return st.session_state.app_data.get(key.lower(), default)

def update_xp(amount):
    st.session_state.app_data['xp'] += amount
    new_level = (st.session_state.app_data['xp'] // 100) + 1
    if new_level > st.session_state.app_data['level']:
        st.session_state.app_data['level'] = new_level
        st.balloons()
        st.toast(f"🎉 מזל טוב! עלית לרמה {new_level}!")
    save_data(st.session_state.app_data)

def send_email_notification(subject, body):
    sender_email = get_config("SENDER_EMAIL").strip()
    sender_password = get_config("SENDER_PASSWORD").strip()
    target_email = get_config("TARGET_EMAIL", "SHIRPI29@GMAIL.COM").strip()
    
    if not sender_email or not sender_password:
        return False, "לא הוגדרו פרטי מייל שולח (חסר Secrets או הגדרות)."
    if not target_email:
        return False, "לא הוגדר מייל יעד."
        
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = target_email
        msg.set_content(body)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, f"המייל נשלח בהצלחה אל {target_email}!"
    except Exception as e:
        return False, f"שגיאה בשליחת המייל: {str(e)}"

def generate_ics_content(title, rem_date, rem_time):
    dt_str = f"{rem_date.strftime('%Y%m%d')}T{rem_time.strftime('%H%M%S')}"
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
    return ics_content

def get_priority_value(priority_str):
    mapping = {"גבוהה": 1, "בינונית": 2, "נמוכה": 3}
    return mapping.get(priority_str, 2)

def safe_date(date_str):
    try: return datetime.strptime(date_str, "%Y-%m-%d")
    except: return datetime.max

tasks = st.session_state.app_data['tasks']
archive = st.session_state.app_data.setdefault('archive', [])
reminders = st.session_state.app_data.setdefault('reminders', [])

# --- 3. ניהול ראשי ב-Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎯 משימות", "➕ הוספה", "📊 התקדמות", "⏰ תזכורות", "🗂️ ארכיון", "🍅 פוקוס", "⚙️ הגדרות"
])

# ----------------------------------------
# Tab 1: רשימת משימות
# ----------------------------------------
with tab1:
    st.title("⚡ FocusFlow | משימות פעילות")
    
    col1, col2, col3 = st.columns(3)
    active_tasks = len(tasks)
    archived_tasks = len(archive)
    
    with col1: st.metric("רמה 🏆", st.session_state.app_data['level'])
    with col2: st.metric("פעילות ⏳", active_tasks)
    with col3: st.metric("בארכיון 🗂️", archived_tasks)
    
    st.markdown("---")
    
    if not tasks:
        st.info("💡 אין משימות פעילות כרגע. הוסף משימה חדשה בלשונית 'הוספה'.")
    else:
        f_col1, f_col2, f_col3 = st.columns(3)
        all_categories = ["הכל"] + list(set([t.get('category', 'אחר') for t in tasks]))
        
        filter_cat = f_col1.selectbox("🔍 קטגוריה:", all_categories)
        filter_pri = f_col2.selectbox("⚡ עדיפות:", ["הכל", "גבוהה", "בינונית", "נמוכה"])
        sort_by = f_col3.selectbox("⇅ מיין לפי:", [
            "תאריך יעד ואז עדיפות", 
            "תאריך יעד (קרוב לרחוק)", 
            "עדיפות (גבוהה לנמוכה)", 
            "הוסף לאחרונה"
        ])

        display_tasks = tasks.copy()
        if filter_cat != "הכל":
            display_tasks = [t for t in display_tasks if t.get('category') == filter_cat]
        if filter_pri != "הכל":
            display_tasks = [t for t in display_tasks if t.get('priority', 'בינונית') == filter_pri]
        
        if sort_by == "תאריך יעד (קרוב לרחוק)":
            display_tasks.sort(key=lambda x: safe_date(x.get('due_date', '')))
        elif sort_by == "עדיפות (גבוהה לנמוכה)":
            display_tasks.sort(key=lambda x: get_priority_value(x.get('priority', 'בינונית')))
        elif sort_by == "תאריך יעד ואז עדיפות":
            display_tasks.sort(key=lambda x: (safe_date(x.get('due_date', '')), get_priority_value(x.get('priority', 'בינונית'))))
        
        if not display_tasks:
            st.warning("לא נמצאו משימות תחת הסינון הנוכחי (נסה לשנות את הסינונים למעלה ל-'הכל').")

        for task in display_tasks:
            idx = tasks.index(task) 
            
            with st.container():
                progress_val = task.get('progress', 0)
                border_color = "#10b981" if progress_val == 100 else "#3b82f6"
                
                priority_text = task.get('priority', 'בינונית')
                pri_color = "#ef4444" if priority_text == "גבוהה" else "#f59e0b" if priority_text == "בינונית" else "#10b981"
                
                st.markdown(f"""
                <div class="task-card" style="border-right: 6px solid {border_color};">
                    <div class="task-title">{task['title']}</div>
                    <div class="task-desc">{task['description'] if task.get('description') else 'אין תיאור נוסף'}</div>
                    <div class="task-meta">
                        <span class="tag">{task.get('category', 'אחר')}</span>
                        <span class="tag" style="background-color: {pri_color};">🔥 עדיפות: {priority_text}</span>
                        <span>📅 יעד: {task.get('due_date', '')}</span>
                        <span style="font-weight: bold; color: {'#10b981' if progress_val == 100 else '#38bdf8'}; margin-right:auto;">הושלם: {progress_val}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_slider, col_actions = st.columns([2, 1])
                
                with col_slider:
                    new_progress = st.slider(
                        "עדכון התקדמות", 
                        0, 100, int(progress_val), 5, 
                        key=f"slider_{task['id']}",
                        label_visibility="collapsed"
                    )
                
                with col_actions:
                    if st.button("✏️ עריכה", key=f"btn_edit_{task['id']}"):
                        current_state = st.session_state.get(f"show_edit_{task['id']}", False)
                        st.session_state[f"show_edit_{task['id']}"] = not current_state

                if new_progress != progress_val:
                    tasks[idx]['progress'] = new_progress
                    if new_progress == 100:
                        archive.append(tasks[idx])
                        tasks.pop(idx)
                        update_xp(30)
                        save_data(st.session_state.app_data)
                        st.success(f"כל הכבוד! '{task['title']}' הושלמה! 🏆")
                        time.sleep(1)
                        st.rerun()
                    else:
                        save_data(st.session_state.app_data)

                if st.session_state.get(f"show_edit_{task['id']}", False):
                    with st.container():
                        with st.form(f"form_edit_{task['id']}"):
                            e_title = st.text_input("שם", task['title'])
                            e_desc = st.text_area("תיאור", task.get('description', ''))
                            
                            col_e1, col_e2, col_e3 = st.columns(3)
                            with col_e1:
                                try: curr_date = datetime.strptime(task.get('due_date', ''), "%Y-%m-%d").date()
                                except: curr_date = date.today()
                                e_date = st.date_input("יעד", curr_date)
                            with col_e2:
                                e_cat = st.selectbox("קטגוריה", ["עבודה", "לימודים", "אישי", "פרויקט", "אחר"], index=["עבודה", "לימודים", "אישי", "פרויקט", "אחר"].index(task.get('category', 'עבודה')) if task.get('category') in ["עבודה", "לימודים", "אישי", "פרויקט", "אחר"] else 4)
                            with col_e3:
                                pri_list = ["נמוכה", "בינונית", "גבוהה"]
                                e_pri = st.selectbox("עדיפות", pri_list, index=pri_list.index(priority_text) if priority_text in pri_list else 1)
                            
                            if st.form_submit_button("שמור שינויים", type="primary"):
                                tasks[idx]['title'] = e_title
                                tasks[idx]['description'] = e_desc
                                tasks[idx]['due_date'] = e_date.strftime("%Y-%m-%d")
                                tasks[idx]['category'] = e_cat
                                tasks[idx]['priority'] = e_pri
                                st.session_state[f"show_edit_{task['id']}"] = False
                                save_data(st.session_state.app_data)
                                st.rerun()

                c1, c2 = st.columns(2)
                if c1.button("✔️ סיים מיד (100%)", key=f"t_done_{task['id']}", type="primary"):
                    tasks[idx]['progress'] = 100
                    archive.append(tasks[idx])
                    tasks.pop(idx)
                    update_xp(30)
                    save_data(st.session_state.app_data)
                    st.rerun()
                if c2.button("🗑️ מחק", key=f"t_del_{task['id']}"):
                    tasks.pop(idx)
                    save_data(st.session_state.app_data)
                    st.rerun()
                
                st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

# ----------------------------------------
# Tab 2: הוספת משימה
# ----------------------------------------
with tab2:
    st.header("➕ הוספת משימה חדשה")
    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("שם המשימה *")
        desc = st.text_area("תיאור מפורט")
        
        c1, c2, c3 = st.columns(3)
        with c1: due_date = st.date_input("תאריך יעד")
        with c2: category = st.selectbox("קטגוריה", ["עבודה", "לימודים", "אישי", "פרויקט", "אחר"])
        with c3: priority = st.selectbox("עדיפות", ["נמוכה", "בינונית", "גבוהה"], index=1)
        
        if st.form_submit_button("הוסף למערכת 🚀", type="primary"):
            if title.strip():
                new_task = {
                    "id": str(uuid.uuid4())[:8],
                    "title": title.strip(),
                    "description": desc,
                    "category": category,
                    "priority": priority,
                    "due_date": due_date.strftime("%Y-%m-%d"),
                    "progress": 0
                }
                tasks.append(new_task)
                save_data(st.session_state.app_data)
                update_xp(5)
                st.session_state.task_added_success = True
            else:
                st.warning("נא להזין שם משימה.")

    if st.session_state.get('task_added_success', False):
        st.session_state.task_added_success = False
        st.success("המשימה נוספה בהצלחה! מעביר אותך לרשימת המשימות...")
        time.sleep(0.8)
        st.rerun()

# ----------------------------------------
# Tab 3: גרף התקדמות
# ----------------------------------------
with tab3:
    st.header("📊 מדדי התקדמות וגרף ביצוע")
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
        col_g1, col_g2 = st.columns(2)
        col_g1.metric("משימות פתוחות", total_active)
        col_g2.metric("משימות בארכיון", total_archived)

# ----------------------------------------
# Tab 4: תזכורות 
# ----------------------------------------
with tab4:
    st.header("⏰ ניהול תזכורות למשימות")
    st.write(f"קבע מועד למשימה, והורד התראה ישירות ליומן האייפון שלך.")
    
    if not tasks:
        st.info("💡 אין משימות פתוחות. הוסף משימה קודם.")
    else:
        with st.form("reminder_form"):
            task_titles = [t['title'] for t in tasks]
            selected_task_title = st.selectbox("בחר משימה:", task_titles)
            
            c_date, c_time = st.columns(2)
            rem_date = c_date.date_input("תאריך התזכורת")
            rem_time = c_time.time_input("שעת התזכורת")
            
            send_email_checkbox = st.checkbox("שלח בנוסף התראה למייל 📧", value=False)
            
            if st.form_submit_button("שמור תזכורת באפליקציה 🔔", type="primary"):
                rem_str = f"{rem_date} בשעה {rem_time}"
                reminders.append({"title": selected_task_title, "time": rem_str, "date_str": str(rem_date), "time_str": str(rem_time)})
                save_data(st.session_state.app_data)
                
                if send_email_checkbox:
                    send_email_notification(
                        subject=f"תזכורת מ-FocusFlow: {selected_task_title}",
                        body=f"שלום,\n\nיש לך תזכורת למשימה:\n📌 משימה: {selected_task_title}\n⏰ מועד: {rem_str}\n\nבהצלחה!"
                    )
                st.success("התזכורת נוצרה! כעת לחץ על כפתור ההורדה ליומן למטה.")

        if reminders:
            st.markdown("### 📥 תזכורות שנקבעו (להורדה ליומן Apple):")
            for idx, r in enumerate(reminders):
                st.write(f"• **{r['title']}** ({r['time']})")
                
                try: d_obj = datetime.strptime(r['date_str'], "%Y-%m-%d").date()
                except: d_obj = date.today()
                try: t_obj = datetime.strptime(r['time_str'], "%H:%M:%S").time()
                except: t_obj = datetime.now().time()
                
                ics_data = generate_ics_content(r['title'], d_obj, t_obj)
                
                st.download_button(
                    label="📥 הוסף אירוע ליומן האייפון (iCal)",
                    data=ics_data,
                    file_name=f"reminder_{idx}.ics",
                    mime="text/calendar",
                    key=f"dl_ics_{idx}"
                )
                
                if st.button("מחק תזכורת מהאפליקציה", key=f"rem_del_{idx}"):
                    reminders.pop(idx)
                    save_data(st.session_state.app_data)
                    st.rerun()
                st.markdown("---")

# ----------------------------------------
# Tab 5: ארכיון משימות
# ----------------------------------------
with tab5:
    st.header("🗂️ ארכיון משימות שהושלמו")
    if not archive:
        st.info("הארכיון ריק. משימות יעברו לכאן כשתסיים אותן (100%).")
    else:
        for idx, item in enumerate(archive):
            st.markdown(f"""
            <div class="task-card" style="border-right: 6px solid #10b981; opacity: 0.7;">
                <div class="task-title" style="color: #34d399;">✅ <s>{item['title']}</s></div>
                <div class="task-meta">
                    <span class="tag">{item.get('category', 'אחר')}</span>
                    <span>הושלם (100%)</span>
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
    st.write("מחקרים מראים שעבודה בריכוז רצוף של 25 דקות מעלה משמעותית את הפרודוקטיביות.")
    
    if 'timer_running' not in st.session_state:
        st.session_state.timer_running = False

    if not st.session_state.timer_running:
        if st.button("התחל 25 דקות ריכוז ⏱️", type="primary"):
            st.session_state.timer_running = True
            st.rerun()
    else:
        if st.button("הפסק טיימר ⏹️"):
            st.session_state.timer_running = False
            st.rerun()
            
        timer_placeholder = st.empty()
        
        for i in range(25 * 60, -1, -1):
            if not st.session_state.timer_running:
                break
                
            mins, secs = divmod(i, 60)
            timer_placeholder.markdown(f"<div class='timer-display'>{mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)
            time.sleep(1)
            
        if st.session_state.timer_running:
            st.session_state.timer_running = False
            st.balloons()
            st.success("🎉 סבב הפוקוס הסתיים! עבודה מעולה. קח 5 דקות הפסקה.")
            update_xp(20)

# ----------------------------------------
# Tab 7: הגדרות 
# ----------------------------------------
with tab7:
    st.header("⚙️ הגדרות מערכת ומייל")
    has_secrets = "SENDER_EMAIL" in st.secrets
    current_sender = st.session_state.app_data.get("sender_email", "")
    current_pass = st.session_state.app_data.get("sender_password", "")
    current_target = st.session_state.app_data.get("target_email", "")
    
    with st.form("settings_form"):
        st.write("אם תרצה התראות במייל, הגדר כאן:")
        new_sender = st.text_input("מייל שולח (Gmail):", value=current_sender, disabled=has_secrets)
        new_pass = st.text_input("סיסמת אפליקציה (App Password):", type="password", value=current_pass, disabled=has_secrets)
        new_target = st.text_input("מייל לקבלת התראות:", value=current_target, disabled=("TARGET_EMAIL" in st.secrets))
        
        if st.form_submit_button("שמור הגדרות 💾", type="primary"):
            st.session_state.app_data["sender_email"] = new_sender.strip()
            st.session_state.app_data["sender_password"] = new_pass.strip()
            st.session_state.app_data["target_email"] = new_target.strip()
            save_data(st.session_state.app_data)
            st.success("ההגדרות נשמרו בהצלחה!")
