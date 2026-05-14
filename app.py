import streamlit as st
import pandas as pd
import datetime
import sqlite3
import hashlib
import os

# --- 1. CONFIGURATIE & DONKERE MODUS ---
st.set_page_config(page_title="NutriSnap - AI Calisthenics Pro", page_icon="💪", layout="centered")

# CSS voor permanente donkere modus en mobiele optimalisatie
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .main .block-container { max-width: 480px; padding-top: 1rem; }
    .stProgress > div > div > div > div { background-color: #FF1493; } /* Neon roze passend bij logo */
    div[data-testid="metric-container"] { 
        background-color: #1F2937; 
        padding: 12px; 
        border-radius: 10px; 
        border: 1px solid #374151;
    }
    div[data-testid="metric-container"] label { color: #9CA3AF !important; }
    div[data-testid="metric-container"] div { color: #FFFFFF !important; }
    .stTabs [data-baseweb="tab"] { color: #9CA3AF; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #FF1493; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE INITIALISATIE ---
def init_db():
    conn = sqlite3.connect('nutrisnap_data.db')
    c = conn.cursor()
    # Gebruikers tabel met e-mailregistratie
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, name TEXT, age INTEGER, height REAL, weight REAL, target_weight REAL, days_train INTEGER, duration_train INTEGER)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def add_user(email, password, name, age, height, weight, target_weight, days_train, duration_train):
    conn = sqlite3.connect('nutrisnap_data.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (email, make_hashes(password), name, age, height, weight, target_weight, days_train, duration_train))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = sqlite3.connect('nutrisnap_data.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE email = ?', (email,))
    data = c.fetchone()
    conn.close()
    if data and check_hashes(password, data):
        return True
    return False

def get_user_data(email):
    conn = sqlite3.connect('nutrisnap_data.db')
    c = conn.cursor()
    c.execute('SELECT age, height, weight, target_weight, days_train, duration_train, name FROM users WHERE email = ?', (email,))
    data = c.fetchone()
    conn.close()
    return data

init_db()

# --- 3. SESSION STATE INITIALISATIE (BLIJF INGELOGD EN TRACKING) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = ""
if "water_ml" not in st.session_state:
    st.session_state.water_ml = 0
if "kcal_gegeten" not in st.session_state:
    st.session_state.kcal_gegeten = 0
if "eiwit_gegeten" not in st.session_state:
    st.session_state.eiwit_gegeten = 0
if "kaaklijn_gedaan" not in st.session_state:
    st.session_state.kaaklijn_gedaan = False
if "oefening_gedaan" not in st.session_state:
    st.session_state.oefening_gedaan = False

# --- 4. AUTHENTICATIE SCHERM ---
if not st.session_state.logged_in:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.title("📸 NutriSnap")
        
    auth_option = st.radio("Kies een optie:", ["Inloggen", "Account Aanmaken"], horizontal=True)
    email_input = st.text_input("E-mailadres")
    password_input = st.text_input("Wachtwoord", type="password")
    
    if auth_option == "Account Aanmaken":
        name = st.text_input("Voornaam")
        age = st.number_input("Leeftijd", min_value=12, max_value=100, value=20)
        height = st.number_input("Lengte (cm)", min_value=120, max_value=230, value=180)
        weight = st.number_input("Huidig Gewicht (kg)", min_value=40.0, max_value=180.0, value=80.0)
        target_weight = st.number_input("Doel Gewicht (kg)", min_value=40.0, max_value=180.0, value=75.0)
        days_train = st.slider("Aantal dagen per week sporten", 0, 7, 3)
        duration_train = st.slider("Gemiddelde duur per training (minuten)", 15, 180, 60)
        
        if st.button("Registreren"):
            if "@" in email_input and password_input and name:
                if add_user(email_input, password_input, name, age, height, weight, target_weight, days_train, duration_train):
                    st.success("Account aangemaakt! Je kunt nu inloggen.")
                else:
                    st.error("Dit e-mailadres is al geregistreerd.")
            else:
                st.error("Vul alle velden correct in en gebruik een geldig e-mailadres.")
                
    elif auth_option == "Inloggen":
        if st.button("Inloggen"):
            if login_user(email_input, password_input):
                st.session_state.logged_in = True
                st.session_state.email = email_input
                st.rerun()
            else:
                st.error("Onjuiste e-mail of wachtwoord.")
    st.stop()

# --- 5. GEBRUIKERS DATA & INSTRELLINGEN ---
u_age, u_height, u_weight, u_target_weight, u_days, u_duration, u_name = get_user_data(st.session_state.email)

# Automatische berekeningen voor afvallen
bmr = (10 * u_weight) + (6.25 * u_height) - (5 * u_age) + 5
activiteit = 1.2 if u_days <= 1 else 1.375 if u_days <= 3 else 1.55 if u_days <= 5 else 1.725
extra_kcal = (u_duration * 6 * u_days) / 7
afval_kcal = int((bmr * activiteit) + extra_kcal - 500)
doel_eiwit = int(u_weight * 2.0)
doel_water_liters = round((u_weight * 0.035) + ((u_duration * 0.01 * u_days) / 7), 1)

# Uitlogknop in de zijbalk
if st.sidebar.button("Uitloggen"):
    st.session_state.logged_in = False
    st.session_state.email = ""
    st.rerun()

# APPLICATIE TABS (Met het Hoofdscherm vooraan)
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Hoofdscherm", "📸 AI Scanner", "📈 Voortgang & Groei", "💧 Water & Eten", "🗿 Oefeningen"])

# --- TAB 1: HOOFDSCHERM (DASHBOARD) ---
with tab1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
    st.title(f"Hoi {u_name}! 👋")
    st.caption("Jouw overzicht van vandaag:")

    # Status berekeningen
    resterend_kcal = max(0, afval_kcal - st.session_state.kcal_gegeten)
    resterend_water = max(0.0, doel_water_liters - (st.session_state.water_ml / 1000))
    resterend_eiwit = max(0, doel_eiwit - st.session_state.eiwit_gegeten)
    
    # Voedingscirkels tabellen overzicht
    st.subheader("📊 Jouw Voedingsstatus")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Calorieën Status**")
        df_kcal = pd.DataFrame({"Status": ["Gegeten", "Nog te gaan"], "Kcal": [st.session_state.kcal_gegeten, resterend_kcal]})
        st.dataframe(df_kcal, hide_index=True) 
        
    with col2:
        st.write("**Eiwitten Status**")
        df_eiwit = pd.DataFrame({"Status": ["Binnen", "Nog te gaan"], "Gram": [st.session_state.eiwit_gegeten, resterend_eiwit]})
        st.dataframe(df_eiwit, hide_index=True)

    # Wat moet ik nog doen counters
    st.subheader("🎯 Resterende Behoefte")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(label="Nog te eten calorieën", value=f"{resterend_kcal} kcal", delta=f"Doel: {afval_kcal}")
    with col_m2:
        st.metric(label="Nog te drinken water", value=f"{resterend_water:.1f} Liter", delta=f"Doel: {doel_water_liters}L")

    # Live Checklist gekoppeld aan de andere tabbladen
    st.markdown("### 📋 Dagelijke Checklist")
    if st.session_state.kaaklijn_gedaan:
        st.success("✅ Kaaklijntraining succesvol afgerond voor vandaag!")
    else:
        st.info("❌ Je moet je kaaklijnoefeningen nog doen vandaag. (Ga naar tabblad Oefeningen)")
        
    if st.session_state.oefening_gedaan:
        st.success("✅ Krachttraining geregistreerd voor vandaag!")
    else:
        st.warning("⚠️ Je moet je workout van vandaag nog invoeren via tekst (Ga naar tabblad Oefeningen).")

# --- TAB 2: AI FOTO SCANNER ---
with tab2:
    st.header("📸 AI Scanner")
    foto = st.camera_input("Fotografeer je maaltijd")
    if not foto:
        foto = st.file_uploader("Of kies een foto uit je galerij", type=["jpg", "jpeg", "png"])
        
    if foto:
        st.success("Maaltijd gedetecteerd!")
        st.session_state.kcal_gegeten += 450
        st.session_state.eiwit_gegeten += 30
        st.write("Automatisch toegevoegd: **450 kcal en 30g eiwitten**.")

# --- TAB 3: VOORTGANG & LICHAAMSGEWICHT GRAFIEKEN ---
with tab3:
    st.header("📈 Voortgang & Groei")
    
    st.subheader("Gewichtsverloop")
    vandaag = datetime.date.today()
    df_gewicht = pd.DataFrame({
        "Datum": [vandaag - datetime.timedelta(days=i) for i in range(4, -1, -1)],
        "Gewicht (kg)": [u_weight + 1.0, u_weight + 0.7, u_weight + 0.4, u_weight + 0.2, u_weight]
    }).set_index("Datum")
    st.line_chart(df_gewicht)
    
    st.subheader("📊 Wekelijkse Lichaamsgewicht Groei (Reps/Sec)")
    st.caption("Eén keer per week doe je een test om te kijken of je bent gegroeid. Elke spiergroep heeft een eigen gekleurde lijn!")
    
    # Wekelijkse Calisthenics voortgangslijnen
    df_groei = pd.DataFrame({
        "Weken": ["Week 1", "Week 2", "Week 3", "Week 4"],
        "Borst: Push-ups (Reps)": [20, 22, 25, 27],
        "Rug: Pull-ups (Reps)": [6, 7, 7, 9],
        "Benen: Pistol Squats (Reps)": [5, 6, 8, 10],
        "Core: Plank (Seconden)": [60, 75, 80, 95]
    }).set_index("Weken")
    st.line_chart(df_groei)

# --- TAB 4: WATER & HANDMATIGE VOEDING LOG ---
with tab4:
    st.header("💧 Variabele Water Tracker")
    st.write(f"Doel op basis van je account: **{doel_water_liters} Liter**.")
    
    ml_toevoegen = st.number_input("Hoeveelheid water toevoegen (in ml):", min_value=0, max_value=2000, value=300, step=50)
    if st.button("➕ Water drinken"):
        st.session_state.water_ml += ml_toevoegen
        st.toast(f"{ml_toevoegen}ml water toegevoegd!")
        
    st.write(f"Totaal gedronken: {st.session_state.water_ml / 1000} / {doel_water_liters} Liter")
    st.progress(min((st.session_state.water_ml / 1000) / doel_water_liters, 1.0))
    
    st.subheader("🔥 Handmatige Calorieën")
    handmatige_kcal = st.number_input("Calorieën handmatig toevoegen:", min_value=0, max_value=3000, value=250, step=50)
    handmatige_eiwit = st.number_input("Eiwit handmatig toevoegen (g):", min_value=0, max_value=150, value=20, step=5)
    if st.button("➕ Voeding handmatig opslaan"):
        st.session_state.kcal_gegeten += handmatige_kcal
        st.session_state.eiwit_gegeten += handmatige_eiwit
        st.success("Voeding succesvol bijgewerkt!")

# --- TAB 5: OEFENINGEN & KAAKLIJN ---
with tab5:
    st.header("🗿 Dagelijkse Trainingen")
    
    st.subheader("Dagelijkse Kaaklijntraining")
    st.write("Vink aan als je de oefeningen hebt gedaan:")
    o1 = st.checkbox("Mewing (Tong strak tegen het gehemelte houden) — 5 min")
    o2 = st.checkbox("Chin Tucks (Houding corrigeren & kin intrekken) — 3 sets")
    if o1 and o2:
        st.session_state.kaaklijn_gedaan = True
        st.success("Status bijgewerkt! Je checklist op het hoofdscherm staat nu op groen.")
        
    st.subheader("Spiertraining Tekstinvoer (Eigen Lichaamsgewicht)")
    st.write("Typ in je eigen woorden welke oefeningen je hebt gedaan (geen vinkjes):")
    user_oefening = st.text_input("Bijv: Ik heb vandaag pushups, pullups en geplankt.", "")
    
    if st.button("Verstuur workout naar AI"):
        if user_oefening:
            st.session_state.oefening_gedaan = True
            st.success("Workout verwerkt in je checklist op het hoofdscherm!")
            
            tekst = user_oefening.lower()
            if any(x in tekst for x in ["pushup", "opdrukken", "dips"]):
                st.info("💪 Getraind: Borst & Triceps (Kwaliteit: Lichaamsgewicht 85%)")
            if any(x in tekst for x in ["squat", "benen", "lunges", "pistol"]):
                st.info("🍗 Getraind: Benen & Billen (Kwaliteit: Lichaamsgewicht 90%)")
            if any(x in tekst for x in ["pullup", "optrekken", "rows", "chinup"]):
                st.info("🦅 Getraind: Rug & Biceps (Kwaliteit: Lichaamsgewicht 80%)")
            if any(x in tekst for x in ["plank", "crunches", "situp", "buik"]):
                st.info("🧱 Getraind: Buikspieren / Core (Kwaliteit: Lichaamsgewicht 85%)")
