import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime, time
from typing import List, Dict, Tuple

st.set_page_config(page_title="Planificateur d'Emplois du Temps – Diplôme Santé", layout="wide")

# ============================================================
#   CONSTANTES & AIDES
# ============================================================
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Dimanche"]  # Samedi exclus d'office
JOUR_INDEX = {j: i for i, j in enumerate(["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"])}

DEFAULT_LOCATIONS = [
    ("Quai de la Rapée", [f"Salle {i}" for i in range(1, 5)]),  # 4 salles
    ("Ledru-Rollin",    [f"Salle {i}" for i in range(1, 5)])     # 4 salles
]

# Horaires imposés: toujours entre 9h et 18h
START_HOUR = 9
END_HOUR = 18

@st.cache_data(show_spinner=False)
def default_rooms() -> pd.DataFrame:
    rows = []
    for loc, rooms in DEFAULT_LOCATIONS:
        for s in rooms:
            rows.append({"Lieu": loc, "Salle": s, "Capacité": 50})
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False)
def default_data():
    classes = pd.DataFrame([
        {"Classe": "PASS-B1", "Faculté": "Bobigny"},
        {"Classe": "PASS-B2", "Faculté": "Bobigny"},
        {"Classe": "LAS-P7",  "Faculté": "Paris 7"},
    ])
    matieres = pd.DataFrame(
        [{"Matière": m} for m in ["Biologie cellulaire", "Chimie", "Physique"]]
    )
    # Tableau "curriculum" : l'utilisateur peut AJOUTER des lignes
    curriculum = pd.DataFrame([
        {"Classe": "PASS-B1", "Matière": "Biologie cellulaire", "Heures": 4, "Prof": "Dr Martin"},
        {"Classe": "PASS-B1", "Matière": "Chimie",               "Heures": 2, "Prof": "Dr Silva"},
        {"Classe": "PASS-B2", "Matière": "Biologie cellulaire", "Heures": 4, "Prof": "Dr Martin"},
        {"Classe": "PASS-B2", "Matière": "Physique",            "Heures": 2, "Prof": "Dr Chen"},
        {"Classe": "LAS-P7",  "Matière": "Chimie",              "Heures": 4, "Prof": "Dr Silva"},
    ])
    profs = pd.DataFrame([
        {"Prof": "Dr Martin", "Indisponibilités": ["Jeudi"]},
        {"Prof": "Dr Silva",  "Indisponibilités": []},
        {"Prof": "Dr Chen",   "Indisponibilités": ["Jeudi"]},
    ])
    return classes, matieres, curriculum, profs

# Utilitaires temps

def to_datetime(d: date, t: time) -> datetime:
    return datetime.combine(d, t)

# ============================================================
#   BARRE LATÉRALE : PARAMÈTRES
# ============================================================
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
st.write(
    "Cette application génère : (1) un **EDT général**, (2) un **EDT par classe**, et (3) un **EDT par professeur**, "
    "avec contraintes de salles, d'indisponibilités, blocs **toujours de 2h**, et plages 9h–18h."
)

# ============================================================
#   ZONE DONNÉES – ROOMS / CLASSES / MATIÈRES / CURRICULUM / PROFS
# ============================================================

rooms_df = st.data_editor(
    default_rooms(),
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Lieu": st.column_config.SelectboxColumn(options=["Quai de la Rapée", "Ledru-Rollin"], width="medium"),
        "Salle": st.column_config.TextColumn(width="small"),
        "Capacité": st.column_config.NumberColumn(min_value=1, step=1, width="small"),
    },
    disabled=["Capacité"],
)

st.subheader("📚 Données pédagogiques")
classes_df, matieres_df, curriculum_df, profs_df = default_data()

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Classes** (ajoute/édite : classe, faculté)")
    classes_df = st.data_editor(
        classes_df,
        use_container_width=True,
        num_rows="dynamic",
    )
with col2:
    st.markdown("**Matières** (liste des enseignements)")
    matieres_df = st.data_editor(
        matieres_df,
        use_container_width=True,
        num_rows="dynamic",
    )

st.markdown("**Curriculum – Heures (multiples de 2) par classe et matière, avec le professeur associé**")
curriculum_df = st.data_editor(
    curriculum_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Classe": st.column_config.SelectboxColumn(options=sorted(classes_df["Classe"].unique()), width="medium"),
        "Matière": st.column_config.SelectboxColumn(options=sorted(matieres_df["Matière"].unique()), width="medium"),
        "Heures": st.column_config.NumberColumn(min_value=2, max_value=20, step=2, help="Toujours par blocs de 2h (2, 4, 6, ...)")
            ,
        "Prof": st.column_config.TextColumn(help="Nom du professeur pour cette matière dans cette classe"),
    }
)

st.markdown("**Professeurs – Indisponibilités** (multi-sélection de jours)")
profs_df = st.data_editor(
    profs_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Indisponibilités": st.column_config.MultiselectColumn(options=["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Dimanche"], width="large")
    }
)

# ============================================================
#   GÉNÉRATION DES CRÉNEAUX (9h→18h)
# ============================================================

def build_day_slots(day_name: str) -> List[time]:
    # Samedi jamais
    if day_name == "Samedi":
        return []
    # Dimanche non inclus si décoché
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

# ============================================================
#   ALGORITHME D'AFFECTATION (BLOCS STRICTS DE 2H)
# ============================================================
# Objectif: respecter salles/profs/classes, indispos profs, pas de samedi, et blocs **strictement 2h**.
# On tend aussi vers 4–6h/jour pour chaque classe.

class Scheduler:
    def __init__(self, semaine_lundi: date, rooms_df: pd.DataFrame, profs_df: pd.DataFrame,
                 curriculum_df: pd.DataFrame):
        self.week_start = semaine_lundi
        self.rooms = rooms_df.copy()
        self.profs = profs_df.copy()
        self.curriculum = curriculum_df[curriculum_df["Heures"] > 0].copy()

        # Préparer map indispos
        self.prof_indispo = {
            row["Prof"]: set(row.get("Indisponibilités", []) or [])
            for _, row in self.profs.iterrows()
        }

        # Jours actifs
        self.days = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi"]
        if include_sunday:
            self.days.append("Dimanche")

        self.day_slots: Dict[str, List[time]] = {d: build_day_slots(d) for d in self.days}

        # Grille d'occupation pour chaque salle
        self.rooms_list = [(r["Lieu"], r["Salle"]) for _, r in self.rooms.iterrows()]
        self.room_busy: Dict[Tuple[str,str], Dict[str, List[bool]]] = {}
        for room in self.rooms_list:
            self.room_busy[room] = {d: [False]*len(self.day_slots[d]) for d in self.days}

        # Occupations profs & classes
        self.prof_busy: Dict[str, Dict[str, List[bool]]] = {}
        self.class_busy: Dict[str, Dict[str, List[bool]]] = {}

        # Compteur d'heures par classe & par jour (pour tendre vers 4–6h)
        self.class_hours_per_day: Dict[str, Dict[str, float]] = {}

        # Résultats (liste de dicts)
        self.assignments: List[Dict] = []

        # Longueur d'un bloc 2h en slots
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
        # Ordonner pour tendre vers 4–6h/jour / éviter 1h et 9h
        indispo = self.prof_indispo.get(prof, set())
        candidates = [d for d in self.days if d not in indispo and len(self.day_slots[d])>0]
        def score(d):
            h = self.class_hours_per_day[classe][d]
            if h < 3.5: return (0, h)
            if h < 6.0: return (1, h)
            return (2, h)
        return sorted(candidates, key=score)

    def find_consecutive_room_window(self, day: str, length: int, classe: str, prof: str):
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
        minutes_total = length * slot_minutes
        end_dt = start_dt + timedelta(minutes=minutes_total)
        self.assignments.append({
            "Jour": day,
            "Début": start_dt,
            "Fin": end_dt,
            "Classe": classe,
            "Matière": matiere,
            "Prof": prof,
            "Lieu": room[0],
            "Salle": room[1],
            "Durée (h)": round(minutes_total/60, 2)
        })
        self.class_hours_per_day[classe][day] += minutes_total/60

    def schedule(self):
        # Validation: toutes les heures doivent être multiples de 2
        invalid = self.curriculum[self.curriculum["Heures"] % 2 != 0]
        if not invalid.empty:
            raise ValueError("Toutes les valeurs 'Heures' doivent être des multiples de 2 (blocs de 2h).")

        for _, row in self.curriculum.iterrows():
            self.ensure_prof(row["Prof"])
            self.ensure_class(row["Classe"])

        # Trier: grandes charges d'abord, puis profs contraints
        def weight(row):
            ind = len(self.prof_indispo.get(row["Prof"], []))
            return (-row["Heures"], -ind)
        tasks = sorted(self.curriculum.to_dict("records"), key=weight)

        for task in tasks:
            classe, matiere, prof, h_total = task["Classe"], task["Matière"], task["Prof"], int(task["Heures"])
            n_blocks = h_total // 2  # garanti entier via validation ci-dessus

            for _ in range(n_blocks):
                days_pref = self.pick_day_for_class(classe, prof)
                placed = False
                for day in days_pref:
                    room, start_idx = self.find_consecutive_room_window(day, self.block2, classe, prof)
                    if room is not None:
                        self.assign_block(classe, matiere, prof, day, room, start_idx, self.block2)
                        placed = True
                        break
                if not placed:
                    st.warning(f"Impossible de placer un bloc 2h pour {classe} - {matiere} (prof {prof}).")

        return pd.DataFrame(self.assignments)

# ============================================================
#   GÉNÉRER L'EDT
# ============================================================

if st.button("🚀 Générer l'EDT"):
    try:
        sched = Scheduler(semaine_lundi, rooms_df, profs_df, curriculum_df)
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
                dfc2 = dfc.copy()
                dfc2["Début"] = dfc2["Début"].dt.strftime("%Y-%m-%d %H:%M")
                dfc2["Fin"]   = dfc2["Fin"].dt.strftime("%Y-%m-%d %H:%M")
                safe = ("Classe - " + str(classe))[:31]
                dfc2.to_excel(writer, sheet_name=safe, index=False)

            for prof, dfp in result_df.groupby("Prof"):
                dfp2 = dfp.copy()
                dfp2["Début"] = dfp2["Début"].dt.strftime("%Y-%m-%d %H:%M")
                dfp2["Fin"]   = dfp2["Fin"].dt.strftime("%Y-%m-%d %H:%M")
                safe = ("Prof - " + str(prof))[:31]
                dfp2.to_excel(writer, sheet_name=safe, index=False)

        with open(file_name, "rb") as f:
            st.download_button(
                "💾 Télécharger l'Excel (EDT général + classes + profs)",
                data=f,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ============================================================
#   NOTE DEPLOIEMENT – STREAMLIT CLOUD & REQUIREMENTS
# ============================================================
st.markdown(
    """
---
### 📦 Déploiement sur Streamlit Cloud
- Ce fichier doit s'appeler **`app.py`** dans votre dépôt.
- Ajoutez un fichier **`requirements.txt`** avec :
```text
streamlit>=1.33
pandas>=2.2
xlsxwriter>=3.2
```

**Locaux par défaut** : *Quai de la Rapée* et *Ledru-Rollin* (**4 salles chacun**).\
**Samedi exclu**. **Dimanche** optionnel.\
**Horaires imposés** : **09:00 → 18:00** tous les jours actifs.\
**Blocs** : **toujours 2h** (les colonnes "Heures" doivent être multiples de 2).

Si vous souhaitez verrouiller la granularité à 60 min ou forcer le dimanche activé/désactivé par défaut, je peux l'ajuster.
    """
)
