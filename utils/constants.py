import streamlit as st

# Constantes globales
DISTANCE_TERRE_SOLEIL = 149.6e6

def initialiser_session():
    """Initialise toutes les variables de session"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
        # Valeurs par défaut VOLONTAIREMENT FAUSSES (100, 50, 1...) : les étudiants
        # doivent chercher les vraies valeurs et les saisir.
        st.session_state.population = 100000

        # Données PAR HABITANT (en km/an/hab)
        st.session_state.km_2025_habitant = {
            'voiture': 100, 'bus': 100, 'train': 100,
            'velo': 100, 'avion': 100, 'marche': 100
        }

        # Les km territoire seront calculés automatiquement
        st.session_state.km_2025_territoire = {}

        st.session_state.nb_depl_hab = {
            'voiture': 100.0, 'bus': 100.0, 'train': 100.0,
            'velo': 100.0, 'avion': 100.0, 'marche': 100.0
        }

        st.session_state.parc_2025 = {
            'part_ve': 50, 'part_thermique': 50,
            'emission_thermique': 100, 'taux_occupation': 1.0,
            'temps_stationnement': 90
        }

        st.session_state.parc_velo_2025 = {
            'part_elec': 50, 'part_classique': 50
        }

        st.session_state.parc_bus_2025 = {
            'part_elec': 50, 'part_thermique': 50
        }

        st.session_state.emissions = {
            'voiture_electrique': 100, 'bus_thermique': 100,
            'bus_electrique': 100, 'train': 10.0,
            'velo_elec': 10, 'velo_classique': 1,
            'avion': 100, 'marche': 1
        }

        st.session_state.scenario = {
            'reduction_km_voiture': 0,
            'reduction_km_avion': 0,
            'report_velo': 0,
            'report_bus': 0,
            'report_train': 0,
            'report_marche': 0,  # NOUVEAU
            'report_train_avion': 0,
            'taux_remplissage': 1.0,
            'part_ve': 50,
            'part_thermique': 50,
            'part_velo_elec': 50,
            'part_velo_classique': 50,
            'part_bus_elec': 50,
            'part_bus_thermique': 50,
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
