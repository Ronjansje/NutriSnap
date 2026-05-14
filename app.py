import streamlit as st
import pandas as pd
import datetime
import sqlite3
import hashlib

# --- 1. CONFIGURATIE & AUTOMATISCHE DONKERE MODUS ---
st.set_page_config(page_title="AI Fitness Pro", page_icon="💪", layout="centered")

# CSS om de app permanent een strakke donkere modus te geven en te optimaliseren voor mobiel
st.markdown("""
    <style>
    /* Forceer donkere achtergrond en witte tekst */
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .main .block-container { max-width: 480px; padding-top: 1rem; }
    
    /* Styling voor voortgangsbalken en metrics in dark mode */
    .stProgress > div > div > div > div { background-color: #1E90FF; }
    div[data-testid="metric-container"] { 
        background-color: #1F2937; 
        padding: 12px; 
        border-radius: 10px; 
        border: 1px solid #374151;
    }
    div[data-testid="metric-container"] label { color: #9CA3AF !important; }
    div[data-testid="metric-container"] div { color: #FFFFFF !important; }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab"] { color: #9CA3AF; }
    .stTabs [data-baseweb="tab"] aria-selected="true" { color: #1E90FF; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE INSTELLINGEN (Voor accounts en data) ---
def init_db():
    conn = sqlite3.connect('fitness_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, age INTEGER, height REAL, weight REAL, target_weight REAL, days_train INTEGER, duration_train INTEGER)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def add_user(username, password, age, height, weight, target_weight, days_train, duration_train):
    conn = sqlite3.connect('fitness_database.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?)', (username, make_hashes(password), age, height, weight, target_weight, days_train, duration_train))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('fitness_database.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data and check_hashes(password, data[0]):
        return True
    return False

def get_user_data(username):
    conn = sqlite3.connect('fitness_database.db')
    c = conn.cursor()
    c.execute('SELECT age, height, weight, target_weight, days_train, duration_train FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data

init_db()

# --- 3. INLOG / REGISTRATIE SCHERM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Welkom bij AI Fitness Pro")
    auth_option = st.radio("Kies een optie:", ["Inloggen", "Account Aanmaken"], horizontal=True)
    
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    
    if auth_option == "Account Aanmaken":
        st.subheader("Personaliseer je profiel:")
        age = st.number_input("Leeftijd", min_value=12, max_value=100, value=22)
        height = st.number_input("Lengte (cm)", min_value=120, max_value=230, value=180)
        weight = st.number_input("Huidig Gewicht (kg)", min_value=40.0, max_value=180.0, value=85.0)
        target_weight = st.number_input("Doel Gewicht (kg)", min_value=40.0, max_value=180.0, value=78.0)
        days_train = st.slider("Hoeveel dagen per week train je?", 0, 7, 4)
        duration_train = st.slider("Gemiddelde trainingsduur per sessie (minuten)", 15, 180, 60)
        
        if st.button("Account Aanmaken"):
            if username and password:
                success = add_user(username, password, age, height, weight, target_weight, days_train, duration_train)
                if success:
                    st.success("Account succesvol aangemaakt! Je kunt nu inloggen.")
                else:
                    st.error("Deze gebruikersnaam bestaat al.")
            else:
                st.warning("Vul alle velden in.")
                
    elif auth_option == "Inloggen":
        if st.button("Inloggen"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Onjuiste gebruikersnaam of wachtwoord.")
    st.stop()

# --- 4. HOOFDAPPLICATIE (INGELOGD) ---
# Haal gepersonaliseerde data op uit de database
u_age, u_height, u_weight, u_target_weight, u_days, u_duration = get_user_data(st.session_state.username)

# --- DYNAMISCHE BEREKENINGEN ---
# Basisbehoefte (BMR via Mifflin-St Jeor)
bmr = (10 * u_weight) + (6.25 * u_height) - (5 * u_age) + 5

# Activiteitsfactor op basis van dagen én duur van de training
if u_days <= 1: activiteit = 1.2
elif u_days <= 3: activiteit = 1.375
elif u_days <= 5: activiteit = 1.55
else: activiteit = 1.725

# Extra calorieverbruik op basis van trainingsduur (gemiddeld 6 kcal per minuut tijdens actieve training)
extra_kcal_per_dag = (u_duration * 6 * u_days) / 7

onderhoud_kcal = (bmr * activiteit) + extra_kcal_per_dag
afval_kcal = int(onderhoud_kcal - 500) # 500 kcal tekort om gezond af te vallen
doel_eiwit = int(u_weight * 2.0)

# Dynamische waterberekening (35ml per kg lichaamsgewicht + extra vochtverlies tijdens het trainen)
water_basis = u_weight * 0.035
water_extra_training = (u_duration * 0.01 * u_days) / 7 # 10ml per minuut training, verdeeld over de week
doel_water_liters = round(water_basis + water_extra_training, 1)

# Toon profielinfo in de zijbalk
st.sidebar.title(f"👤 {st.session_state.username}")
st.sidebar.markdown(f"""
**Jouw Profiel:**
* Leeftijd: `{u_age} jaar`
* Training: `{u_days} dagen/week` ({u_duration} min/sessie)

🎯 **Berekende Dagdoelen:**
* 🔥 **Calorieën:** `{afval_kcal} kcal`
* 🥩 **Eiwitten:** `{doel_eiwit} g`
* 💧 **Water:** `{doel_water_liters} Liter`
""")

if st.sidebar.button("Uitloggen"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# HOOFDSCHERM TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 AI Eten", "📈 Gewicht", "💧 Water", "🗿 Kaaklijn", "🏋️ Spieren"])

# --- TAB 1: AI FOTO SCAN ---
with tab1:
    st.header("📸 AI Maaltijd Scanner")
    foto = st.camera_input("Maak een foto van je maaltijd")
    if not foto:
        foto = st.file_uploader("Of upload een foto vanaf je toestel", type=["jpg", "jpeg", "png"])
        
    if foto:
        st.success("Foto succesvol ontvangen!")
        st.info("AI Analyseert de maaltijd... (Simulatie)")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Geschatte Calorieën", value="465 kcal", delta=f"Doel: {afval_kcal}")
        with col2:
            st.metric(label="Eiwitten", value="34 g", delta=f"Doel: {doel_eiwit}g")

# --- TAB 2: GEWICHTSVERLOOP ---
with tab2:
    st.header("📈 Mijn Gewichtsverloop")
    st.write(f"Doel: van **{u_weight} kg** naar **{u_target_weight} kg**")
    
    vandaag = datetime.date.today()
    data_gewicht = {
        "Datum": [vandaag - datetime.timedelta(days=i) for i in range(4, -1, -1)],
        "Gewicht": [u_weight + 1.2, u_weight + 0.9, u_weight + 0.5, u_weight + 0.2, u_weight]
    }
    df = pd.DataFrame(data_gewicht)
    st.line_chart(df.set_index("Datum"))
    
    verloren = data_gewicht["Gewicht"][0] - u_weight
    st.metric(label="Totaal Recent Verloren", value=f"-{verloren:.1f} kg", delta="Ga zo door!")

# --- TAB 3: WATER LOG ---
with tab3:
    st.header("💧 Dagelijks Waterdoel")
    st.write(f"Op basis van je profiel moet je vandaag **{doel_water_liters} Liter** drinken.")
    
    if "glazen" not in st.session_state:
        st.session_state.glazen = 0
        
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Glas (250ml)"): st.session_state.glazen += 1
    with col2:
        if st.button("🔄 Reset"): st.session_state.glazen = 0
        
    gedronken = st.session_state.glazen * 0.25
    st.metric(label="Vandaag Gedronken", value=f"{gedronken} Liter")
    
    voortgang = min(gedronken / doel_water_liters, 1.0)
    st.progress(voortgang)

# --- TAB 4: KAAKLIJN TRAINING ---
with tab4:
    st.header("🗿 Kaaklijn Verstrakken")
    oef1 = st.checkbox("1. Mewing (Tong tegen gehemelte) — 5 min")
    oef2 = st.checkbox("2. Chin Tucks (Dubbele kin vasthouden) — 3 sets")
    oef3 = st.checkbox("3. Kaakspanning (Kauwspieren aanspannen) — 2 min")
    
    kaak_score = (oef1 + oef2 + oef3) / 3
    st.progress(kaak_score)
    if kaak_score == 1.0: st.success("Kaaklijntraining voltooid! 🗿")

# --- TAB 5: SPIERTRAINING TRACKER ---
with tab5:
    st.header("🏋️ Oefeningen & Getrainde Spieren")
    st.write("Vink de oefeningen aan die je vandaag hebt uitgevoerd:")
    
    oef_borst = st.checkbox("Push-ups / Bench Press (Borst & Triceps)")
    oef_rug = st.checkbox("Pull-ups / Rows (Rug & Biceps)")
    oef_benen = st.checkbox("Squats / Leg Press (Benen)")
    oef_buik = st.checkbox("Planken / Crunches (Core)")
    
    st.subheader("📊 Spierstatus & Trainingskwaliteit")
    spieren = {
        "Borst & Triceps": 85 if oef_borst else 0,
        "Rug & Biceps": 80 if oef_rug else 0,
        "Benen & Billen": 90 if oef_benen else 0,
        "Buikspieren (Core)": 75 if oef_buik else 0
    }
    
    for spier, kwaliteit in spieren.items():
        st.write(f"**{spier}**")
        st.progress(kwaliteit / 100)
        st.caption(f"Status: {kwaliteit}% getraind vandaag." if kwaliteit > 0 else "Status: Nog niet getraind (0%)")

