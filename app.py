import streamlit as st
import pandas as pd
import datetime
import hashlib
import time
from supabase import create_client, Client
import google.generativeai as genai
from PIL import Image

# --- 1. CONFIGURATIE & DONKERE MODUS ---
st.set_page_config(page_title="NutriSnap AI Pro", page_icon="💪", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .main .block-container { max-width: 480px; padding-top: 1rem; }
    .stProgress > div > div > div > div { background-color: #FF1493; }
    div[data-testid="metric-container"] { 
        background-color: #1F2937; padding: 12px; border-radius: 10px; border: 1px solid #374151;
    }
    div[data-testid="metric-container"] label { color: #9CA3AF !important; }
    div[data-testid="metric-container"] div { color: #FFFFFF !important; }
    .stTabs [data-baseweb="tab"] { color: #9CA3AF; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #FF1493; }
    </style>
""", unsafe_allow_html=True)

# --- 2. VERBINDING SUPABASE & GOOGLE GEMINI INITIALISEREN ---
# Haalt de geheime sleutels veilig op uit de cloudomgeving/settings
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    
    # Clients opstarten
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    st.error("⚠️ Setup niet compleet: Voeg SUPABASE_URL, SUPABASE_KEY en GEMINI_API_KEY toe aan je Streamlit Secrets!")
    st.stop()

# --- 3. CLOUD DATABASE FUNCTIES ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user_exists(email):
    res = supabase.table("users").select("email").eq("email", email).execute()
    return len(res.data) > 0

def add_user(email, password, name, age, height, weight, target_weight, days_train, duration_train):
    hashed_pwd = make_hashes(password)
    user_data = {
        "email": email, "password": hashed_pwd, "name": name, "age": age,
        "height": height, "weight": weight, "target_weight": target_weight,
        "days_train": days_train, "duration_train": duration_train
    }
    try:
        supabase.table("users").insert(user_data).execute()
        return True
    except Exception:
        return False

def login_user(email, password):
    hashed_pwd = make_hashes(password)
    res = supabase.table("users").select("password").eq("email", email).execute()
    if res.data and res.data[0]["password"] == hashed_pwd:
        return True
    return False

def get_user_data(email):
    res = supabase.table("users").select("*").eq("email", email).execute()
    if res.data:
        d = res.data[0]
        return d["age"], d["height"], d["weight"], d["target_weight"], d["days_train"], d["duration_train"], d["name"]
    return 20, 180, 80, 75, 3, 60, "User"

# --- 4. SESSION STATE INITIALISATIE ---
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

# --- 5. AUTHENTICATIE SCHERM ---
if not st.session_state.logged_in:
    st.title("📸 NutriSnap AI")
    st.caption("Veilig gesynchroniseerd via de Cloud met Supabase")
        
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
                if not check_user_exists(email_input):
                    if add_user(email_input, password_input, name, age, height, weight, target_weight, days_train, duration_train):
                        st.success("Account succesvol aangemaakt in de cloud! Je kunt inloggen.")
                    else:
                        st.error("Er ging iets mis bij de database registratie.")
                else:
                    st.error("Dit e-mailadres is al geregistreerd.")
            else:
                st.error("Vul alle velden correct in.")
                
    elif auth_option == "Inloggen":
        if st.button("Inloggen"):
            if login_user(email_input, password_input):
                st.session_state.logged_in = True
                st.session_state.email = email_input
                st.rerun()
            else:
                st.error("Onjuiste e-mail of wachtwoord.")
    st.stop()

# --- 6. HOOFDAPPLICATIE (INGELOGD) ---
u_age, u_height, u_weight, u_target_weight, u_days, u_duration, u_name = get_user_data(st.session_state.email)

# Dynamische gezondheidsberekeningen
bmr = (10 * u_weight) + (6.25 * u_height) - (5 * u_age) + 5
activiteit = 1.2 if u_days <= 1 else 1.375 if u_days <= 3 else 1.55 if u_days <= 5 else 1.725
extra_kcal = (u_duration * 6 * u_days) / 7
afval_kcal = int((bmr * activiteit) + extra_kcal - 500)
doel_eiwit = int(u_weight * 2.0)
doel_water_liters = round((u_weight * 0.035) + ((u_duration * 0.01 * u_days) / 7), 1)

st.sidebar.title("✨ NutriSnap Cloud Pro")
st.sidebar.markdown(f"Ingelogd als: **{u_name}**")
if st.sidebar.button("Uitloggen"):
    st.session_state.logged_in = False
    st.session_state.email = ""
    st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Hoofdscherm", "📸 AI Scanner", "📈 Voortgang", "💧 Water & Eten", "🗿 Oefeningen"])

# --- TAB 1: HOOFDSCHERM ---
with tab1:
    st.title(f"Hoi {u_name}! 👋")
    resterend_kcal = max(0, afval_kcal - st.session_state.kcal_gegeten)
    resterend_water = max(0.0, doel_water_liters - (st.session_state.water_ml / 1000))
    resterend_eiwit = max(0, doel_eiwit - st.session_state.eiwit_gegeten)
    
    st.subheader("📊 Dagelijkse Voedingsstatus")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Calorieën Status**")
        st.dataframe(pd.DataFrame({"Status": ["Gegeten", "Nog"], "Kcal": [st.session_state.kcal_gegeten, resterend_kcal]}), hide_index=True) 
    with col2:
        st.write("**Eiwitten Status**")
        st.dataframe(pd.DataFrame({"Status": ["Binnen", "Nog"], "Gram": [st.session_state.eiwit_gegeten, resterend_eiwit]}), hide_index=True)

    col_m1, col_m2 = st.columns(2)
    with col_m1: st.metric(label="Nog te eten", value=f"{resterend_kcal} kcal", delta=f"Doel: {afval_kcal}")
    with col_m2: st.metric(label="Nog te drinken", value=f"{resterend_water:.1f} L", delta=f"Doel: {doel_water_liters}L")

    st.markdown("### 📋 Checklist")
    st.success("✅ Kaaklijntraining voltooid!") if st.session_state.kaaklijn_gedaan else st.info("❌ Je moet je kaaklijnoefeningen nog doen.")
    st.success("✅ Krachttraining geregistreerd!") if st.session_state.oefening_gedaan else st.warning("⚠️ Voer je workout van vandaag nog in.")

# --- TAB 2: ECHTE GOOGLE GEMINI AI VISION SCANNER ---
with tab2:
    st.header("📸 Echte AI Maaltijd Scanner")
    st.caption("Aangedreven door Gemini 2.0 Flash Vision")
    
    foto = st.camera_input("Fotografeer je eten")
    if not foto:
        foto = st.file_uploader("Of kies een foto uit je galerij", type=["jpg", "jpeg", "png"])
        
    if foto:
        st.success("Foto succesvol geladen! AI start met analyseren...")
        try:
            image = Image.open(foto)
            # Gemini Model aanroepen met een gerichte prompt
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            prompt = "Analyseer deze foto van eten. Geef ALLEEN het geschatte aantal calorieën (als getal) en eiwitten (als getal in gram) terug gescheiden door een komma. Voorbeeldoutput: 450,30"
            
            response = model.generate_content([prompt, image])
            ai_output = response.text.strip()
            
            # Resultaten splitsen
            kcal_parsed, eiwit_parsed = map(int, ai_output.split(","))
            
            st.metric(label="Gescande Calorieën", value=f"{kcal_parsed} kcal")
            st.metric(label="Gescande Eiwitten", value=f"{eiwit_parsed} g")
            
            if st.button("Voeg deze AI waarden toe aan je dag"):
                st.session_state.kcal_gegeten += kcal_parsed
                st.session_state.eiwit_gegeten += eiwit_parsed
                st.success("Succesvol toegevoegd aan je totalen!")
        except Exception as e:
            st.error("De AI kon de afbeelding niet goed verwerken. Probeer een duidelijkere foto of controleer je Gemini API Key.")

# --- TAB 3: VOORTGANG ---
with tab3:
    st.header("📈 Voortgang & Groei")
    vandaag = datetime.date.today()
    st.line_chart(pd.DataFrame({"Datum": [vandaag - datetime.timedelta(days=i) for i in range(4, -1, -1)], "Gewicht (kg)": [u_weight+1.0, u_weight+0.7, u_weight+0.4, u_weight+0.2, u_weight]}).set_index("Datum"))
    st.subheader("📊 Wekelijkse Lichaamsgewicht Groei")
    st.line_chart(pd.DataFrame({"Weken": ["Week 1", "Week 2", "Week 3", "Week 4"], "Borst: Push-ups":, "Rug: Pull-ups":, "Benen: Pistol Squats":, "Core: Plank (Sec)":}).set_index("Weken"))

# --- TAB 4: WATER & CALORIEEN ---
with tab4:
    st.header("💧 Handmatige Invoer")
    ml_toevoegen = st.number_input("Hoeveelheid water (ml):", min_value=0, max_value=2000, value=300, step=50)
    if st.button("➕ Water registreren"):
        st.session_state.water_ml += ml_toevoegen
        st.toast(f"{ml_toevoegen}ml toegevoegd!")
        
    st.subheader("🔥 Handmatige Voeding")
    hkcal = st.number_input("Calorieën:", min_value=0, max_value=3000, value=250)
    heiwit = st.number_input("Eiwit (g):", min_value=0, max_value=150, value=20)
    if st.button("➕ Voeding opslaan"):
        st.session_state.kcal_gegeten += hkcal
        st.session_state.eiwit_gegeten += heiwit
        st.success("Handmatig bijgewerkt!")

# --- TAB 5: OEFENINGEN & LIVE KAAKLIJN TIMER ---
with tab5:
    st.header("🗿 Dagelijkse Trainingen")
    
    st.subheader("Dagelijkse Kaaklijntraining")
    st.write("Druk op de knop om te starten met Mewen (5 minuten timer):")
    
    # Interactieve live countdown timer voor Mewing
    if st.button("⏱️ Start 5 Minuten Mewing Timer"):
        timer_placeholder = st.empty()
        totale_tijd = 5 * 60  # 300 seconden
        for resterend in range(totale_tijd, -1, -1):
            mins, secs = divmod(resterend, 60)
            timer_placeholder.metric("Resterende tijd", f"{mins:02d}:{secs:02d}")
            time.sleep(1)
        st.balloons()
        st.success("Geweldig! Je hebt 5 minuten geknipt en getraind!")
        
    o1 = st.checkbox("Mewing voltooid")
    o2 = st.checkbox("Chin Tucks (Kin intrekken) — 3 sets")
    if o1 and o2:
        st.session_state.kaaklijn_gedaan = True
        
    st.subheader("Spiertraining Tekstinvoer (Eigen Lichaamsgewicht)")
    user_oefening = st.text_input("Typ in wat je hebt gedaan (bijv. pushups, pullups, planken):", "")
    if st.button("Verstuur workout"):
        if user_oefening:
            st.session_state.oefening_gedaan = True
            st.success("Workout verwerkt!")
            tekst = user_oefening.lower()
            if any(x in tekst for x in ["pushup", "opdrukken"]): st.info("💪 Getraind: Borst & Triceps (85%)")
            if any(x in tekst for x in ["squat", "pistol"]): st.info("🍗 Getraind: Benen & Billen (90%)")
            if any(x in tekst for x in ["pullup", "optrekken"]): st.info("🦅 Getraind: Rug & Biceps (80%)")
            if any(x in tekst for x in ["plank", "buik"]): st.info("🧱 Getraind: Buikspieren / Core (85%)")

