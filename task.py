import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import time
import uuid
import requests

# --- 1. הגדרות עמוד ועיצוב ---
st.set_page_config(page_title="FocusFlow | ניהול משימות חכם", page_icon="🎯", layout="wide")

# הזרקת CSS לעיצוב מודרני, תמיכה ב-RTL
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;800&display=swap');
    
    body, .stApp, p, h1, h2, h3, h4, h5, h6, span, label, div {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif !important;
    }
    
    /* עיצוב כרטיסיות משימות */
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
    
    /* מטריצת אייזנהאואר */
    .matrix-box { padding: 15px; border-radius: 10px; height: 100%; min-height: 200px; margin-bottom: 15px; }
    .box-do { background-color: rgba(34, 197, 94, 0.1); border: 1px solid #22c55e; }
    .box-schedule { background-color: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; }
    .box-delegate { background-color: rgba(245, 158, 11, 0.1); border: 1px solid #f59e0b; }
    .box-delete { background-color: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; }
</style>
""", unsafe_allow_html=True)

# --- 2. מנגנון שמירה חסין (Absolute Path & Cloud Sync) ---
# נתיב אבסולוטי - מבטיח שהקובץ תמיד יישמר בתיקיית הפרויקט ולא יאבד
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'focusflow_data.json')

def load_data():
    # קודם כל ננסה לקרוא מהקובץ המקומי
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # אם הקובץ לא קיים, נייצר מבנה נתונים חדש
    return {"tasks": [], "xp": 0, "level": 1, "cloud_url": ""}

def save_data(data):
    # שמירה מקומית קשיחה
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"שגיאה בשמירת נתונים מקומית: {e}")
    
    # גיבוי לענן (אם המשתמש הגדיר כתובת JSONBin) - למניעת מחיקה בשרתים חינמיים
    if data.get("cloud_url"):
        try:
            requests.put(data["cloud_url"], json=data, timeout=2)
        except Exception:
            pass

# טעינת הנתונים ל-Session State כדי שיהיו זמינים לאורך כל הגלישה
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

# --- 3. מבנה האפליקציה (Tabs) ---
st.title("🎯 FocusFlow | מנהל משימות חכם")
st.markdown("---")

tab_dash, tab_add, tab_kanban, tab_matrix, tab_pomodoro, tab_settings = st.tabs([
    "📊 דשבורד", "➕ הוספת משימות", "📋 קנבן", "🔲 אייזנהאואר", "🍅 פומודורו", "⚙️ גיבוי ענן"
])

tasks = st.session_state.app_data['tasks']

# ----------------------------------------
# Tab 1: Dashboard
# ----------------------------------------
with tab_dash:
    st.header("פרופיל אישי והתקדמות")
    
    col1, col2, col3 = st.columns(3)
    completed_tasks = len([t for t in tasks if t['status'] == 'הושלם'])
    active_tasks = len([t for t in tasks if t['status'] != 'הושלם'])
    
    with col1:
        st.metric("רמה נוכחית 🏆", st.session_state.app_data['level'])
    with col2:
        st.metric("משימות שהושלמו ✅", completed_tasks)
    with col3:
        st.metric("משימות פתוחות ⏳", active_tasks)
        
    st.subheader("מד ניסיון (XP)")
    xp = st.session_state.app_data['xp']
    xp_to_next = 100 - (xp % 100)
    progress = (xp % 100) / 100.0
    st.progress(progress)
    st.caption(f"יש לך {xp} XP. נותרו עוד {xp_to_next} XP לרמה הבאה!")

# ----------------------------------------
# Tab 2: הוספה וניהול משימות
# ----------------------------------------
with tab_add:
    st.header("הוספת משימה חדשה")
    
    with st.form("new_task_form"):
        col_t1, col_t2 = st.columns([3, 1])
        title = col_t1.text_input("שם המשימה *")
        category = col_t2.selectbox("קטגוריה", ["עבודה", "לימודים", "אישי", "פרויקט", "אחר"])
        desc = st.text_area("תיאור מפורט")
        
        col_d1, col_d2, col_d3 = st.columns(3)
        due_date = col_d1.date_input("תאריך יעד")
        is_urgent = col_d2.checkbox("🔥 משימה דחופה (Urgent)")
        is_important = col_d3.checkbox("⭐ משימה חשובה (Important)")
        
        if st.form_submit_button("הוסף משימה למערכת", type="primary"):
            if title.strip() == "":
                st.error("חובה להזין שם משימה!")
            else:
                new_task = {
                    "id": str(uuid.uuid4())[:8],
                    "title": title,
                    "description": desc,
                    "category": category,
                    "due_date": due_date.strftime("%Y-%m-%d"),
                    "is_urgent": is_urgent,
                    "is_important": is_important,
                    "status": "לביצוע",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                st.session_state.app_data['tasks'].append(new_task)
                save_data(st.session_state.app_data)
                update_xp(5)
                st.success("המשימה נוספה בהצלחה! קיבלת 5 XP.")
                st.rerun()

    st.markdown("---")
    st.subheader("ניהול משימות קיימות")
    if tasks:
        df = pd.DataFrame(tasks)
        df_display = df[['title', 'category', 'status', 'due_date']].copy()
        df_display.columns = ['שם משימה', 'קטגוריה', 'סטטוס', 'תאריך יעד']
        st.dataframe(df_display, use_container_width=True)
        
        task_to_delete = st.selectbox("בחר משימה למחיקה:", [t['title'] for t in tasks])
        if st.button("🗑️ מחק משימה זו"):
            st.session_state.app_data['tasks'] = [t for t in tasks if t['title'] != task_to_delete]
            save_data(st.session_state.app_data)
            st.warning("המשימה נמחקה!")
            st.rerun()

# ----------------------------------------
# Tab 3: לוח קנבן (Kanban)
# ----------------------------------------
def render_task_card(task):
    urgent_icon = "🔥" if task['is_urgent'] else ""
    important_icon = "⭐" if task['is_important'] else ""
    st.markdown(f"""
    <div class="task-card">
        <div class="task-title">{task['title']} {urgent_icon}{important_icon}</div>
        <div class="task-desc">{task['description']}</div>
        <div class="task-meta">
            <span class="tag">{task['category']}</span>
            <span>📅 {task['due_date']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with tab_kanban:
    st.header("לוח קנבן")
    col_todo, col_prog, col_done = st.columns(3)
    
    with col_todo:
        st.subheader("📝 לביצוע")
        for t in tasks:
            if t['status'] == 'לביצוע':
                render_task_card(t)
                if st.button("התחל לעבוד ➡️", key=f"start_{t['id']}"):
                    t['status'] = 'בתהליך'
                    save_data(st.session_state.app_data)
                    st.rerun()

    with col_prog:
        st.subheader("⏳ בתהליך")
        for t in tasks:
            if t['status'] == 'בתהליך':
                render_task_card(t)
                col_p1, col_p2 = st.columns(2)
                if col_p1.button("✅ סיים", key=f"finish_{t['id']}", type="primary"):
                    t['status'] = 'הושלם'
                    update_xp(20)
                    save_data(st.session_state.app_data)
                    st.rerun()
                if col_p2.button("⬅️ החזר", key=f"back_{t['id']}"):
                    t['status'] = 'לביצוע'
                    save_data(st.session_state.app_data)
                    st.rerun()

    with col_done:
        st.subheader("✅ הושלם")
        for t in tasks:
            if t['status'] == 'הושלם':
                render_task_card(t)

# ----------------------------------------
# Tab 4: מטריצת אייזנהאואר (Eisenhower)
# ----------------------------------------
with tab_matrix:
    st.header("מטריצת אייזנהאואר - תעדוף חכם")
    q1, q2 = st.columns(2)
    q3, q4 = st.columns(2)
    
    with q1:
        st.markdown('<div class="matrix-box box-do"><h3>🔥⭐ תעשה עכשיו (דחוף וחשוב)</h3>', unsafe_allow_html=True)
        for t in tasks:
            if t['status'] != 'הושלם' and t['is_urgent'] and t['is_important']: st.write(f"• **{t['title']}**")
        st.markdown('</div>', unsafe_allow_html=True)

    with q2:
        st.markdown('<div class="matrix-box box-schedule"><h3>📅 תתכנן מתי (לא דחוף, אבל חשוב)</h3>', unsafe_allow_html=True)
        for t in tasks:
            if t['status'] != 'הושלם' and not t['is_urgent'] and t['is_important']: st.write(f"• **{t['title']}**")
        st.markdown('</div>', unsafe_allow_html=True)

    with q3:
        st.markdown('<div class="matrix-box box-delegate"><h3>🤝 תאציל (דחוף, לא חשוב)</h3>', unsafe_allow_html=True)
        for t in tasks:
            if t['status'] != 'הושלם' and t['is_urgent'] and not t['is_important']: st.write(f"• **{t['title']}**")
        st.markdown('</div>', unsafe_allow_html=True)

    with q4:
        st.markdown('<div class="matrix-box box-delete"><h3>🗑️ תמחק/תדחה (לא חשוב ולא דחוף)</h3>', unsafe_allow_html=True)
        for t in tasks:
            if t['status'] != 'הושלם' and not t['is_urgent'] and not t['is_important']: st.write(f"• **{t['title']}**")
        st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------
# Tab 5: טיימר פומודורו
# ----------------------------------------
with tab_pomodoro:
    st.header("🍅 טיימר פומודורו")
    active_task_titles = [t['title'] for t in tasks if t['status'] != 'הושלם']
    if not active_task_titles:
        st.info("אין משימות פתוחות.")
    else:
        focus_task = st.selectbox("בחר משימה לפוקוס:", active_task_titles)
        col_timer1, col_timer2, col_timer3 = st.columns([1, 2, 1])
        with col_timer2:
            st.markdown(f"<h3 style='text-align: center;'>{focus_task}</h3>", unsafe_allow_html=True)
            if st.button("התחל טיימר 25:00 ⏱️", use_container_width=True):
                timer_placeholder = st.empty()
                progress_bar = st.progress(0)
                demo_seconds = 10  # מוגדר ל-10 שניות כדי לא לתקוע את האפליקציה למפתחים
                for i in range(demo_seconds, -1, -1):
                    mins, secs = divmod(i, 60)
                    timer_placeholder.markdown(f"<h1 style='text-align: center; font-size: 60px;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
                    progress_bar.progress(1.0 - (i / demo_seconds))
                    time.sleep(1)
                update_xp(10)
                st.success("🍅 הושלם! קיבלת 10 XP.")

# ----------------------------------------
# Tab 6: הגדרות גיבוי ענן (מניעת מחיקה)
# ----------------------------------------
with tab_settings:
    st.header("☁️ גיבוי ענן אוטומטי")
    st.write("אם אתה מארח את האפליקציה בשרת חינמי, הזן כאן כתובת API (לדוגמה של JSONBin.io) כדי שהנתונים לא יימחקו כשהשרת מתאפס.")
    
    current_url = st.session_state.app_data.get("cloud_url", "")
    new_cloud_url = st.text_input("כתובת גיבוי בענן (Webhook / JSONBin PUT URL):", value=current_url)
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("שמור הגדרות ענן", type="primary"):
            st.session_state.app_data["cloud_url"] = new_cloud_url.strip()
            save_data(st.session_state.app_data)
            st.success("הגדרות נשמרו! מעכשיו כל פעולה תגובה גם לענן.")
    with col_s2:
        if st.button("משיכת נתונים מהענן 📥") and current_url:
            try:
                response = requests.get(current_url)
                if response.status_code == 200:
                    data = response.json()
                    # תמיכה במבנה של jsonbin שבו הנתונים תחת מפתח "record"
                    if "record" in data:
                        data = data["record"]
                    st.session_state.app_data = data
                    save_data(data)
                    st.success("הנתונים נמשכו מהענן בהצלחה!")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"שגיאה במשיכת נתונים: {e}")
