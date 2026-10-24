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
            'temps_stationnement': 80
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
            'velo_elec': 1, 'velo_classique': 1,
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


# Valeurs de départ volontairement fausses : tant qu'un champ garde sa valeur de départ
# ET n'a jamais été modifié par l'étudiant, les données 2025 ne peuvent pas être validées.
DEFAUTS_SAISIE = {
    'population': 100000,
    'km_voiture': 100, 'km_bus': 100, 'km_train': 100, 'km_velo': 100, 'km_avion': 100, 'km_marche': 100,
    'nb_voiture': 100, 'nb_bus': 100, 'nb_train': 100, 'nb_velo': 100, 'nb_avion': 100, 'nb_marche': 100,
    'part_ve': 50, 'em_thermique': 100, 'em_voiture_elec': 100, 'occupation': 1.0, 'stationnement': 80,
    'part_velo_elec': 50, 'em_velo_elec': 1, 'em_velo_classique': 1,
    'part_bus_elec': 50, 'em_bus_thermique': 100, 'em_bus_elec': 100,
    'em_train': 10.0, 'em_avion': 100, 'em_marche': 1,
}
_MODES = {'voiture': 'Voiture', 'bus': 'Bus / TC', 'train': 'Train',
          'velo': 'Vélo', 'avion': 'Avion', 'marche': 'Marche'}
LIBELLES_SAISIE = {
    'population': "Population",
    'part_ve': "Part de voitures électriques", 'em_thermique': "Émission voiture thermique",
    'em_voiture_elec': "Émission voiture électrique", 'occupation': "Taux d'occupation",
    'stationnement': "Temps stationné", 'part_velo_elec': "Part de vélos électriques",
    'em_velo_elec': "Émission vélo électrique", 'em_velo_classique': "Émission vélo classique",
    'part_bus_elec': "Part de bus électriques", 'em_bus_thermique': "Émission bus thermique",
    'em_bus_elec': "Émission bus électrique", 'em_train': "Émission train",
    'em_avion': "Émission avion", 'em_marche': "Émission marche",
}
for _m, _n in _MODES.items():
    LIBELLES_SAISIE[f'km_{_m}'] = f"{_n} : km/an/habitant"
    LIBELLES_SAISIE[f'nb_{_m}'] = f"{_n} : déplacements/an/habitant"


def valeurs_saisie():
    """Valeurs actuelles de tous les champs de la page 1, par identifiant."""
    ss = st.session_state
    v = {'population': ss.population}
    for m in _MODES:
        v[f'km_{m}'] = ss.km_2025_habitant.get(m)
        v[f'nb_{m}'] = ss.nb_depl_hab.get(m)
    v['part_ve'] = ss.parc_2025.get('part_ve')
    v['em_thermique'] = ss.parc_2025.get('emission_thermique')
    v['occupation'] = ss.parc_2025.get('taux_occupation')
    v['stationnement'] = ss.parc_2025.get('temps_stationnement')
    v['part_velo_elec'] = ss.parc_velo_2025.get('part_elec')
    v['part_bus_elec'] = ss.parc_bus_2025.get('part_elec')
    em = ss.emissions
    v['em_voiture_elec'] = em.get('voiture_electrique')
    v['em_velo_elec'] = em.get('velo_elec')
    v['em_velo_classique'] = em.get('velo_classique')
    v['em_bus_thermique'] = em.get('bus_thermique')
    v['em_bus_elec'] = em.get('bus_electrique')
    v['em_train'] = em.get('train')
    v['em_avion'] = em.get('avion')
    v['em_marche'] = em.get('marche')
    return v


def marquer_modifications(avant):
    """À appeler après les champs de saisie : retient les champs dont la valeur a changé
    pendant cette exécution (donc modifiés par l'étudiant)."""
    touches = st.session_state.setdefault('_champs_touches', set())
    for cle, valeur in valeurs_saisie().items():
        if avant.get(cle) != valeur:
            touches.add(cle)


def saisie_modifiee():
    """Vrai si au moins un champ diffère de sa valeur de départ ou a été modifié."""
    if st.session_state.get('_champs_touches'):
        return True
    return any(valeurs_saisie().get(k) != d for k, d in DEFAUTS_SAISIE.items())


def champs_non_modifies():
    """Libellés des champs encore à leur valeur de départ et jamais modifiés."""
    touches = st.session_state.get('_champs_touches', set())
    actuel = valeurs_saisie()
    return [LIBELLES_SAISIE[k] for k, d in DEFAUTS_SAISIE.items()
            if actuel.get(k) == d and k not in touches]
