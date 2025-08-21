import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime, time
from typing import List, Dict, Tuple

st.set_page_config(page_title="Planificateur d'Emplois du Temps – Diplôme Santé", layout="wide")

# ================= CONSTANTES & AIDES =================
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Dimanche"]  # Samedi exclus d'office
JOUR_INDEX = {j: i for i, j in enumerate(["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"])}

DEFAULT_LOCATIONS = [
    ("Quai de la Rapée", [f"Salle {i}" for i in range(1, 5)]),
    ("Ledru-Rollin",    [f"Salle {i}" for i in range(1, 5)])
]

START_HOUR = 9
END_HOUR = 18

# ---- Catalogue des classes (déroulant) ----
CLASS_CATALOG = [
    ("PAES", 1, 4),
    ("Terminale Santé", 1, 8),
    ("PASS SU", 1, 4),
    ("PASS UPC", 1, 3),
    ("LAS UPC", 1, 1),
    ("PASS UVSQ", 1, 1),
    ("PASS UPS", 1, 1),
    ("LSPS1 UPEC", 1, 4),
    ("LSPS2 UPEC", 1, 3),
    ("LSPS3 UPEC", 1, 1),
]

def build_class_options() -> List[str]:
    opts = []
    for label, a, b in CLASS_CATALOG:
        for i in range(a, b+1):
            opts.append(f"{label} - Classe {i}")
    return opts

CLASS_OPTIONS = build_class_options()

@st.cache_data(show_spinner=False)
def default_rooms() -> pd.DataFrame:
    rows = []
    for loc, rooms in DEFAULT_LOCATIONS:
        for s in rooms:
            rows.append({"Lieu": loc, "Salle": s})
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False)
def default_data():
    classes = pd.DataFrame([
        {"Classe": "PAES - Classe 1", "Faculté": "—"},
        {"Classe": "Terminale Santé - Classe 1", "Faculté": "—"},
    ])
    matieres = pd.DataFrame([{"Matière": m} for m in ["Biologie cellulaire", "Chimie", "Physique"]])
    curriculum = pd.DataFrame([
        {"Classe": "PAES - Classe 1", "Matière": "Biologie cellulaire", "Heures": 4, "Prof": "Dr Martin"},
        {"Classe": "Terminale Santé - Classe 1", "Matière": "Chimie", "Heures": 2, "Prof": "Dr Silva"},
    ])
    profs = pd.DataFrame([
        {"Prof": "Dr Martin", "Indisponibilités": ["Jeudi"]},
        {"Prof": "Dr Silva",  "Indisponibilités": []},
        {"Prof": "Dr Chen",   "Indisponibilités": ["Jeudi"]},
    ])
    return classes, matieres, curriculum, profs

# ----------------- Utilitaires temps -----------------

def to_datetime(d: date, t: time) -> datetime:
    return datetime.combine(d, t)

ALLOWED_DAYS = {"Lundi","Mardi","Mercredi","Jeudi","Vendredi","Dimanche"}

def parse_days(value) -> List[str]:
    if isinstance(value, list):
        return [d for d in value if d in ALLOWED_DAYS]
    if isinstance(value, str):
        parts = [p.strip().capitalize() for p in value.replace(";", ",").split(",") if p.strip()]
        return [p for p in parts if p in ALLOWED_DAYS]
    return []

# ================= BARRE LATÉRALE =================
with st.sidebar:
    st.header("Paramètres généraux")
    semaine_lundi: date = st.date_input(
        "Semaine (choisir le lundi)",
        value=date.today() - timedelta(days=date.today().weekday()),
        help="Choisis le lundi de la semaine à planifier."
    )
    include_sunday = st.checkbox("Inclure le Dimanche", value=True)
    slot_minutes = st.selectbox("Granularité (min)", [60, 30], index=0)
    st.info("Horaires imposés pour tous les jours: **09:00 → 18:00**. Samedi exclu.")

st.title("🗓️ Planificateur d'Emplois du Temps – Streamlit")
st.write("Cette application génère : (1) un **EDT général**, (2) un **EDT par classe**, (3) un **EDT par professeur**; blocs **2h**, 9h–18h, samedi exclu, dimanche optionnel.")

# ================= DONNÉES =================
rooms_df = st.data_editor(
    default_rooms(),
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Lieu": st.column_config.SelectboxColumn(options=["Quai de la Rapée", "Ledru-Rollin"], width="medium"),
        "Salle": st.column_config.TextColumn(width="small"),
    },
)

st.subheader("📚 Données pédagogiques")
classes_df, matieres_df, curriculum_df, profs_df = default_data()

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Classes** (choisis depuis le catalogue)")
    classes_df = st.data_editor(
        classes_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Classe": st.column_config.SelectboxColumn(options=CLASS_OPTIONS, width="large"),
            "Faculté": st.column_config.TextColumn(width="medium")
        }
    )
with col2:
    st.markdown("**Matières**")
    matieres_df = st.data_editor(matieres_df, use_container_width=True, num_rows="dynamic")

st.markdown("**Curriculum – Heures (multiples de 2) par classe et matière, avec le professeur associé**")
curriculum_df = st.data_editor(
    curriculum_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Classe": st.column_config.SelectboxColumn(options=CLASS_OPTIONS, width="large"),
        "Matière": st.column_config.SelectboxColumn(options=sorted(matieres_df["Matière"].unique()), width="medium"),
        "Heures": st.column_config.NumberColumn(min_value=2, max_value=20, step=2, help="Toujours par blocs de 2h (2, 4, 6, ...)"),
        "Prof": st.column_config.TextColumn(help="Nom du professeur pour cette matière dans cette classe"),
    }
)

st.markdown("**Professeurs – Indisponibilités** (écrire: Jeudi, Dimanche)")
profs_ui = profs_df.copy()
profs_ui["Indisponibilités"] = profs_ui["Indisponibilités"].apply(lambda v: ", ".join(v) if isinstance(v, list) else (v if isinstance(v, str) else ""))
profs_ui = st.data_editor(
    profs_ui,
    use_container_width=True,
    num_rows="dynamic",
    column_config={"Indisponibilités": st.column_config.TextColumn(help="Ex.: 'Jeudi' ou 'Mardi, Dimanche'")}
)

profs_df_processed = profs_ui.copy()
profs_df_processed["Indisponibilités"] = profs_df_processed["Indisponibilités"].apply(parse_days)

# ================= CRÉNEAUX =================

def build_day_slots(day_name: str) -> List[time]:
    if day_name == "Samedi":
        return []
    if day_name == "Dimanche" and not include_sunday:
        return []
    slots = []
    h = START_HOUR
    m = 0
    while True:
        if h >= END_HOUR:
            break
        slots.append(time(hour=h, minute=m))
        m += slot_minutes
        while m >= 60:
            h += 1
            m -= 60
    return slots

# ================= PLANIF (2H STRICTES) =================
class Scheduler:
    def __init__(self, semaine_lundi: date, rooms_df: pd.DataFrame, profs_df: pd.DataFrame, curriculum_df: pd.DataFrame):
        self.week_start = semaine_lundi
        self.rooms = rooms_df.copy()
        self.profs = profs_df.copy()
        self.curriculum = curriculum_df[curriculum_df["Heures"] > 0].copy()
        self.prof_indispo = {row["Prof"]: set(parse_days(row.get("Indisponibilités", []))) for _, row in self.profs.iterrows()}
        self.days = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi"] + (["Dimanche"] if include_sunday else [])
        self.day_slots: Dict[str, List[time]] = {d: build_day_slots(d) for d in self.days}
        self.rooms_list = [(r["Lieu"], r["Salle"]) for _, r in self.rooms.iterrows()]
        self.room_busy: Dict[Tuple[str,str], Dict[str, List[bool]]] = {rm: {d:[False]*len(self.day_slots[d]) for d in self.days} for rm in self.rooms_list}
        self.prof_busy: Dict[str, Dict[str, List[bool]]] = {}
        self.class_busy: Dict[str, Dict[str, List[bool]]] = {}
        self.class_hours_per_day: Dict[str, Dict[str, float]] = {}
        self.assignments: List[Dict] = []
        self.block2 = self.slots_needed(2.0)

    def ensure_prof(self, prof: str):
        if prof not in self.prof_busy:
            self.prof_busy[prof] = {d: [False]*len(self.day_slots[d]) for d in self.days}

    def ensure_class(self, classe: str):
        if classe not in self.class_busy:
            self.class_busy[classe] = {d: [False]*len(self.day_slots[d]) for d in self.days}
        if classe not in self.class_hours_per_day:
            self.class_hours_per_day[classe] = {d: 0.0 for d in self.days}

    def slots_needed(self, hours: float) -> int:
        return int(round(hours*60/slot_minutes))

    def pick_day_for_class(self, classe: str, prof: str) -> List[str]:
        indispo = self.prof_indispo.get(prof, set())
        candidates = [d for d in self.days if d not in indispo and len(self.day_slots[d])>0]
        def score(d):
            h = self.class_hours_per_day[classe][d]
            if h < 3.5: return (0, h)
            if h < 6.0: return (1, h)
            return (2, h)
        return sorted(candidates, key=score)

    def find_window(self, day: str, length: int, classe: str, prof: str):
        for room in self.rooms_list:
            busy = self.room_busy[room][day]
            for start in range(0, len(busy)-length+1):
                if any(busy[start:start+length]):
                    continue
                if any(self.class_busy.setdefault(classe, {day:[False]*len(self.day_slots[day])})[day][start:start+length]):
                    continue
                if any(self.prof_busy.setdefault(prof, {day:[False]*len(self.day_slots[day])})[day][start:start+length]):
                    continue
                return room, start
        return None, None

    def assign_block(self, classe: str, matiere: str, prof: str, day: str, room: Tuple[str,str], start_idx: int, length: int):
        for i in range(start_idx, start_idx+length):
            self.room_busy[room][day][i] = True
            self.class_busy[classe][day][i] = True
            self.prof_busy[prof][day][i] = True
        slot_time = self.day_slots[day][start_idx]
        start_dt = to_datetime(self.week_start + timedelta(days=JOUR_INDEX[day]), slot_time)
        end_dt = start_dt + timedelta(minutes=length*slot_minutes)
        self.assignments.append({"Jour": day, "Début": start_dt, "Fin": end_dt, "Classe": classe, "Matière": matiere, "Prof": prof, "Lieu": room[0], "Salle": room[1], "Durée (h)": round(length*slot_minutes/60, 2)})
        self.class_hours_per_day[classe][day] += length*slot_minutes/60

    def schedule(self):
        invalid = self.curriculum[self.curriculum["Heures"] % 2 != 0]
        if not invalid.empty:
            raise ValueError("Toutes les valeurs 'Heures' doivent être des multiples de 2 (blocs de 2h).")
        for _, row in self.curriculum.iterrows():
            self.ensure_prof(row["Prof"])
            self.ensure_class(row["Classe"])
        def weight(row):
            ind = len(self.prof_indispo.get(row["Prof"], []))
            return (-row["Heures"], -ind)
        tasks = sorted(self.curriculum.to_dict("records"), key=weight)
        for task in tasks:
            classe, matiere, prof, h_total = task["Classe"], task["Matière"], task["Prof"], int(task["Heures"]) 
            n_blocks = h_total // 2
            for _ in range(n_blocks):
                for day in self.pick_day_for_class(classe, prof):
                    room, start_idx = self.find_window(day, self.block2, classe, prof)
                    if room is not None:
                        self.assign_block(classe, matiere, prof, day, room, start_idx, self.block2)
                        break
                else:
                    st.warning(f"Impossible de placer un bloc 2h pour {classe} - {matiere} (prof {prof}).")
        return pd.DataFrame(self.assignments)

# ================= ACTION =================
if st.button("🚀 Générer l'EDT"):
    try:
        sched = Scheduler(semaine_lundi, rooms_df, profs_ui, curriculum_df)
        result_df = sched.schedule()
    except Exception as e:
        st.error(str(e))
        result_df = pd.DataFrame()

    if result_df.empty:
        st.error("Aucun cours planifié. Vérifie les données/contraintes.")
    else:
        result_df = result_df.sort_values(["Début", "Lieu", "Salle"]).reset_index(drop=True)
        st.success("EDT généré !")
        st.dataframe(result_df, use_container_width=True)

        file_name = f"EDT_{semaine_lundi.isoformat()}.xlsx"
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            df_export = result_df.copy()
            df_export["Début"] = df_export["Début"].dt.strftime("%Y-%m-%d %H:%M")
            df_export["Fin"]   = df_export["Fin"].dt.strftime("%Y-%m-%d %H:%M")
            df_export.to_excel(writer, sheet_name="General", index=False)
            for classe, dfc in result_df.groupby("Classe"):
                dfc2 = dfc.copy(); dfc2["Début"] = dfc2["Début"].dt.strftime("%Y-%m-%d %H:%M"); dfc2["Fin"] = dfc2["Fin"].dt.strftime("%Y-%m-%d %H:%M")
                dfc2.to_excel(writer, sheet_name=("Classe - "+str(classe))[:31], index=False)
            for prof, dfp in result_df.groupby("Prof"):
                dfp2 = dfp.copy(); dfp2["Début"] = dfp2["Début"].dt.strftime("%Y-%m-%d %H:%M"); dfp2["Fin"] = dfp2["Fin"].dt.strftime("%Y-%m-%d %H:%M")
                dfp2.to_excel(writer, sheet_name=("Prof - "+str(prof))[:31], index=False)
        with open(file_name, "rb") as f:
            st.download_button("💾 Télécharger l'Excel (EDT général + classes + profs)", data=f, file_name=file_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ================= DEPLOIEMENT =================
st.markdown(
    """
---
**requirements.txt** :
```text
streamlit>=1.33
pandas>=2.2
xlsxwriter>=3.2
```

- Locaux : *Quai de la Rapée* & *Ledru-Rollin* (4 salles chacun).
- Blocs : 2h strictes, 9h–18h, samedi exclu, dimanche optionnel.
- Sélection de classe : menu déroulant basé sur le **catalogue** (PAES 1–4, Terminale Santé 1–8, PASS SU 1–4, PASS UPC 1–3, LAS UPC 1, PASS UVSQ 1, PASS UPS 1, LSPS1 UPEC 1–4, LSPS2 UPEC 1–3, LSPS3 UPEC 1).
    """
)
