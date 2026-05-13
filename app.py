import streamlit as st
import pandas as pd
import datetime

# 1. Page settings for mobile
st.set_page_config(page_title="AI Fitness & Jawline Tracker", page_icon="💪", layout="centered")

# CSS for mobile look and clean layout
st.markdown("""
    <style>
    .main .block-container { max-width: 480px; padding-top: 1rem; }
    .stProgress > div > div > div > div { background-color: #1f77b4; }
    div[data-testid="metric-container"] { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("💪 AI Fitness & Jawline Tracker")

# 2. User Profile (Personalization)
st.sidebar.header("👤 My Profile")
age = st.sidebar.number_input("Age", min_value=1, max_value=120, value=25)
height = st.sidebar.number_input("Height (cm)", min_value=100, max_value=250, value=175)
current_weight = st.sidebar.number_input("Current Weight (kg)", min_value=30.0, max_value=200.0, value=80.0)
target_weight = st.sidebar.number_input("Target Weight (kg)", min_value=30.0, max_value=200.0, value=75.0)
days_training = st.sidebar.slider("Days training per week", 0, 7, 3)

# Calorie needs calculation for weight loss (BMR estimate via Mifflin-St Jeor -500 kcal)
maintenance_kcal = int((10 * current_weight) + (6.25 * height) - (5 * age) + 5)
weight_loss_kcal = maintenance_kcal - 500
target_protein = int(current_weight * 2) # 2g per kg weight

st.sidebar.markdown(f"**Weight Loss Goals:**\n* Calories: `{weight_loss_kcal} kcal` per day\n* Protein: `{target_protein} g` per day")

# Navigation Tabs for the app components
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 AI Food", "📈 Weight", "💧 Water", "🗿 Jawline", "🏋️ Muscles"])

# --- TAB 1: AI PHOTO SCAN ---
with tab1:
    st.header("📸 Scan your Meal")
    st.write("Take a photo of your food to check calories and protein.")
    
    photo = st.camera_input("Take a photo of your meal")
    # Alternative upload button for existing photos on mobile
    if not photo:
        photo = st.file_uploader("Or choose an existing photo", type=["jpg", "jpeg", "png"])
        
    if photo:
        st.success("Photo successfully received!")
        st.info("AI Analysis starts... (Simulation based on photo)")
        # In a production environment, this photo is sent to the Google Gemini API.
        # Below is the output structure that the AI immediately returns:
        st.metric(label="Estimated Calories", value="450 kcal")
        st.metric(label="Proteins", value="32 g")
        st.metric(label="Carbohydrates / Fats", value="45g / 12g")
        
        if st.button("Add to log"):
            st.toast("Meal saved!")

# --- TAB 2: WEIGHT TRACKER ---
with tab2:
    st.header("📈 My Weight")
    
    # Dummy data to make the graph work immediately
    today = datetime.date.today()
    data = {
        "Date": [today - datetime.timedelta(days=i) for i in range(6, -1, -1)],
        "Weight": [current_weight + 1.2, current_weight + 0.9, current_weight + 0.8, current_weight + 0.4, current_weight + 0.2, current_weight + 0.1, current_weight]
    }
    df = pd.DataFrame(data)
    
    st.line_chart(df.set_index("Date"))
    st.metric(label="Total Lost", value=f"-{(data['Weight'][0] - current_weight):.1f} kg", delta="Good job!")

# --- TAB 3: WATER LOG ---
with tab3:
    st.header("💧 Water Intake")
    
    if "water_glasses" not in st.session_state:
        st.session_state.water_glasses = 0
        
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Glass of Water (250ml)"):
            st.session_state.water_glasses += 1
    with col2:
        if st.button("🔄 Reset"):
            st.session_state.water_glasses = 0
            
    total_liters = st.session_state.water_glasses * 0.25
    st.metric(label="Water drunk today", value=f"{total_liters} Liters")
    
    # Progress bar (Goal is 2 Liters / 8 glasses)
    percent = min(st.session_state.water_glasses / 8, 1.0)
    st.progress(percent)
    st.caption(f"Goal: 2.0 Liters ({st.session_state.water_glasses}/8 glasses drunk)")

# --- TAB 4: JAWLINE ROUTINE ---
with tab4:
    st.header("🗿 Daily Jawline Routine")
    st.write("Perform these exercises for a tighter jawline:")
    
    exercise_1 = st.checkbox("1. Mewing (Pressing tongue against palate) — 5 minutes")
    exercise_2 = st.checkbox("2. Chin Tucks (Making a double chin and holding) — 3 sets of 10 reps")
    exercise_3 = st.checkbox("3. Jaw Juicer (Tensing chewing muscles without grinding teeth) — 2 minutes")
    
    done_percent = (exercise_1 + exercise_2 + exercise_3) / 3
    st.progress(done_percent)
    if done_percent == 1.0:
        st.balloons()
        st.success("Routine completed for today!")

# --- TAB 5: MUSCLE TRAINING TRACKER ---
with tab5:
    st.header("🏋️ Training Muscle Groups")
    
    st.write("Check the exercises you have done today:")
    push_up = st.checkbox("Push-ups (Chest & Triceps)")
    pull_up = st.checkbox("Pull-ups / Rows (Back & Biceps)")
    squat = st.checkbox("Squats / Lunges (Legs & Glutes)")
    plank = st.checkbox("Plank / Crunches (Abdominals)")
    
    st.subheader("📊 Trained Muscle Groups Status")
    
    # Dynamic overview of how well muscles are trained based on the checkboxes
    muscles = {"Chest/Triceps": 80 if push_up else 0, 
               "Back/Biceps": 85 if pull_up else 0, 
               "Legs": 90 if squat else 0, 
               "Core": 75 if plank else 0}
               
    for muscle, score in muscles.items():
        st.write(f"**{muscle}**")
        st.progress(score / 100)
        if score > 0:
            st.caption(f"Status: Excellent training ({score}%)")
        else:
            st.caption("Status: Not trained today (0%)")
