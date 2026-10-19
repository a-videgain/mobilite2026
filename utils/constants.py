import streamlit as st

# Constantes globales
DISTANCE_TERRE_SOLEIL = 149.6e6

def initialiser_session():
    """Initialise toutes les variables de session"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
        # Population du territoire (modifiable)
        st.session_state.population = 330000  # Valeur par défaut
        
        # Données PAR HABITANT (en km/an/hab)
        st.session_state.km_2025_habitant = {
            'voiture': 9581,
            'bus': 329,
            'train': 1600,
            'velo': 113,
            'avion': 2750,
            'marche': 219
        }
        
        # Les km territoire seront calculés automatiquement
        st.session_state.km_2025_territoire = {}
        
        st.session_state.nb_depl_hab = {
            'voiture': 766.5, 'bus': 73.0, 'train': 20.0,
            'velo': 35.5, 'avion': 2.5, 'marche': 219.0
        }
        
        st.session_state.parc_2025 = {
            'part_ve': 3, 'part_thermique': 97,
            'emission_thermique': 218, 'taux_occupation': 1.4,
            'temps_stationnement': 97
        }
        
        st.session_state.parc_velo_2025 = {
            'part_elec': 12, 'part_classique': 88
        }
        
        st.session_state.parc_bus_2025 = {
            'part_elec': 10, 'part_thermique': 90
        }
        
        st.session_state.emissions = {
            'voiture_electrique': 103, 'bus_thermique': 122,
            'bus_electrique': 22, 'train': 5.1,
            'velo_elec': 11, 'velo_classique': 0,
            'avion': 225, 'marche': 0
        }
        
        st.session_state.scenario = {
            'reduction_km_voiture': 0,
            'reduction_km_avion': 0,
            'report_velo': 0,
            'report_bus': 0,
            'report_train': 0,
            'report_marche': 0,  # NOUVEAU
            'report_train_avion': 0,
            'taux_remplissage': 1.4,
            'part_ve': 3,
            'part_thermique': 97,
            'part_velo_elec': 12,
            'part_velo_classique': 88,
            'part_bus_elec': 5,
            'part_bus_thermique': 95,
            'reduction_poids': 0
        }



def calculer_km_territoire():
    """Calcule les km territoire (en Mkm/an) à partir des km/hab/an et de la population"""
    if 'km_2025_habitant' in st.session_state and 'population' in st.session_state:
        st.session_state.km_2025_territoire = {
            mode: (km_hab * st.session_state.population) / 1_000_000
            for mode, km_hab in st.session_state.km_2025_habitant.items()
        }

def format_nombre(n, decimales=0):
    """Formate un nombre avec espaces entre milliers"""
    if decimales == 0:
        return f"{n:,.0f}".replace(',', ' ')
    else:
        return f"{n:,.{decimales}f}".replace(',', ' ')
