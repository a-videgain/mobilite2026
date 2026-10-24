# pages/2_📊_Bilan_2025.py

import streamlit as st
import pandas as pd
import plotly.express as px
from utils.constants import DISTANCE_TERRE_SOLEIL, initialiser_session
from utils.calculations import calculer_bilan_territoire, calculer_parts_modales, format_nombre
from utils.session_manager import demarrer_sauvegarde, terminer_sauvegarde, arreter_page

st.set_page_config(page_title="Bilan 2025", page_icon="", layout="wide")

# Masquer le menu hamburger et le pied de page (le bandeau du haut et la barre
# latérale restent intacts : les masquer empêchait de rouvrir la barre latérale)
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbarActions"], [data-testid="stMainMenu"],
    [data-testid="stAppDeployButton"] {display: none !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


# Initialisation
if 'initialized' not in st.session_state:
    initialiser_session()

# Sauvegarde / reprise du travail (barre latérale)
sauvegarde = demarrer_sauvegarde()

# VÉRIFICATION DES ÉTAPES PRÉCÉDENTES
if not st.session_state.get('donnees_2025_validees', False):
    st.error("Vous devez d'abord compléter l'étape 1 : Données 2025")
    if st.button("Aller à l'étape 1", type="primary"):
        st.switch_page("pages/1_📝_Donnees_2025.py")
    arreter_page(sauvegarde)


# ==================== PAGE 2 : BILAN 2025 ====================

st.title("Mobilité Pays Basque 2050")
st.header("📊 Bilan 2025")

# Vérification des données nécessaires
if 'km_2025_territoire' not in st.session_state:
    st.error("Données 2025 manquantes. Veuillez d’abord compléter la page 'Données 2025'.")
    arreter_page(sauvegarde)

# Calcul du bilan 2025
bilan_2025 = calculer_bilan_territoire(
    st.session_state.km_2025_territoire,
    {**st.session_state.emissions, 'emission_thermique': st.session_state.parc_2025['emission_thermique']},
    st.session_state.parc_2025,
    st.session_state.parc_velo_2025,
    st.session_state.parc_bus_2025,
    reduction_poids=0
)
parts_2025 = calculer_parts_modales(st.session_state.km_2025_territoire)

# Calculs par habitant
co2_par_hab = (bilan_2025['co2_total_territoire'] ) / st.session_state.population
km_par_hab_jour = (bilan_2025['km_total_territoire'] * 1e6) / st.session_state.population / 365
depl_par_hab_jour = sum(st.session_state.nb_depl_hab.values()) / 365

# Calcul équivalent Terre-Soleil
nb_terre_soleil = (bilan_2025['km_total_territoire'] * 1e6) / DISTANCE_TERRE_SOLEIL

# ==================== MÉTRIQUES ====================

st.subheader("Échelle territoire (Pays Basque français)")
col1, col2 = st.columns(2)
with col1:
    st.metric("Km totaux/an", f"{format_nombre(bilan_2025['km_total_territoire'])} millions de km")
    st.caption(f"Soit {nb_terre_soleil:.1f} fois la distance Terre-Soleil")
with col2:
    st.metric("CO₂ total/an", f"{format_nombre(bilan_2025['co2_total_territoire'])} tonnes")

st.divider()

st.subheader("Échelle habitant (moyennes)")
col1, col2, col3 = st.columns(3)
with col3:
    st.metric("CO₂/habitant/an", f"{format_nombre(co2_par_hab,2)} tonnes")
with col1:
    st.metric("Km/habitant/jour", f"{format_nombre(km_par_hab_jour, 1)} km")
with col2:
    st.metric("Déplacements/habitant/jour", f"{depl_par_hab_jour:.2f}")

st.divider()

# ==================== GRAPHIQUES ====================

col1, col2 = st.columns(2)

# Parts modales
with col1:
    st.subheader("Parts modales 2025")
    df_parts = pd.DataFrame({
        'Mode': list(parts_2025.keys()),
        'Part (%)': list(parts_2025.values())
    })
    df_parts['Mode'] = df_parts['Mode'].map({
        'voiture': 'Voiture',
        'bus': 'Bus',
        'train': 'Train',
        'velo': 'Vélo',
        'avion': 'Avion',
        'marche': 'Marche'
    })
    fig_parts = px.pie(df_parts, values='Part (%)', names='Mode', hole=0.4, title="Répartition des km parcourus en 2025")
    fig_parts.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_parts, use_container_width=True)

# Émissions par mode
with col2:
    st.subheader("Émissions par mode (kg/hab/an)")
    emissions_hab_an = {mode: (co2 * 1000) / st.session_state.population for mode, co2 in bilan_2025['detail_par_mode'].items()}
    df_emissions = pd.DataFrame({
        'Mode': list(emissions_hab_an.keys()),
        'CO₂ (kg/hab/an)': list(emissions_hab_an.values())
    })
    df_emissions['Mode'] = df_emissions['Mode'].map({
        'voiture': 'Voiture',
        'bus': 'Bus',
        'train': 'Train',
        'velo': 'Vélo',
        'avion': 'Avion',
        'marche': 'Marche'
    })
    df_emissions = df_emissions.sort_values('CO₂ (kg/hab/an)', ascending=False)
    fig_emissions = px.bar(
        df_emissions,
        x='Mode',
        y='CO₂ (kg/hab/an)',
        text='CO₂ (kg/hab/an)',
        color='CO₂ (kg/hab/an)',
        color_continuous_scale='Reds',
        title="Contribution aux émissions"
    )
    fig_emissions.update_traces(texttemplate='%{text:.0f} kg', textposition='outside')
    fig_emissions.update_layout(showlegend=False)
    st.plotly_chart(fig_emissions, use_container_width=True)

st.divider()
# ==================== EXPORT DONNÉES DIAGNOSTIC 2025 ====================
st.subheader("Export du diagnostic 2025")
st.info("Sauvegardez vos données avant de passer à l'étape suivante")

def generer_csv_diagnostic():
    """Génère le CSV de manière optimisée"""
    lignes = []
    
    # Fonction helper pour ajouter des lignes
    def ajouter(label, valeur=''):
        lignes.append(f"{label};{valeur}")
    
    # TERRITOIRE
    ajouter('TERRITOIRE')
    ajouter('Population (habitants)', st.session_state.population)
    ajouter('')
    
    # MOBILITÉS PAR HABITANT
    ajouter('MOBILITÉS PAR HABITANT (km/an/hab)')
    for mode, km in st.session_state.km_2025_habitant.items():
        ajouter(mode.capitalize(), km)
    ajouter('TOTAL', sum(st.session_state.km_2025_habitant.values()))
    ajouter('')
    
    # DÉPLACEMENTS PAR HABITANT
    ajouter('DÉPLACEMENTS PAR HABITANT (dépl/an/hab)')
    for mode, nb in st.session_state.nb_depl_hab.items():
        ajouter(mode.capitalize(), f"{nb:.1f}")
    ajouter('TOTAL', f"{sum(st.session_state.nb_depl_hab.values()):.1f}")
    ajouter('')
    
    # PARC AUTOMOBILE
    ajouter('PARC AUTOMOBILE 2025')
    ajouter('Part véhicules électriques (%)', st.session_state.parc_2025['part_ve'])
    ajouter('Part véhicules thermiques (%)', st.session_state.parc_2025['part_thermique'])
    ajouter('Émission voiture thermique (gCO₂/km ACV)', st.session_state.parc_2025['emission_thermique'])
    ajouter('Émission voiture électrique (gCO₂/km ACV)', st.session_state.emissions['voiture_electrique'])
    ajouter("Taux d'occupation moyen (pers/véh)", f"{st.session_state.parc_2025['taux_occupation']:.1f}")
    ajouter('Temps stationné (%)', st.session_state.parc_2025['temps_stationnement'])
    ajouter('')
    
    # PARC VÉLO
    ajouter('PARC VÉLO 2025')
    ajouter('Part vélos électriques (%)', st.session_state.parc_velo_2025['part_elec'])
    ajouter('Part vélos classiques (%)', st.session_state.parc_velo_2025['part_classique'])
    ajouter('Émission vélo électrique (gCO₂/km ACV)', st.session_state.emissions['velo_elec'])
    ajouter('Émission vélo classique (gCO₂/km ACV)', st.session_state.emissions['velo_classique'])
    ajouter('')
    
    # PARC BUS
    ajouter('PARC BUS 2025')
    ajouter('Part bus électriques (%)', st.session_state.parc_bus_2025['part_elec'])
    ajouter('Part bus thermiques (%)', st.session_state.parc_bus_2025['part_thermique'])
    ajouter('Émission bus thermique (gCO₂/km/pass ACV)', st.session_state.emissions['bus_thermique'])
    ajouter('Émission bus électrique (gCO₂/km/pass ACV)', st.session_state.emissions['bus_electrique'])
    ajouter('')
    
    # AUTRES MODES
    ajouter('AUTRES MODES')
    ajouter('Émission train (gCO₂/km/pass)', st.session_state.emissions['train'])
    ajouter('Émission avion (gCO₂/km/pass)', st.session_state.emissions['avion'])
    ajouter('Émission marche (gCO₂/km)', st.session_state.emissions['marche'])
    ajouter('')
    
    # BILAN TERRITOIRE
    ajouter('BILAN TERRITOIRE 2025')
    ajouter('CO₂ total territoire (tonnes/an)', f"{bilan_2025['co2_total_territoire']:.0f}")
    ajouter('CO₂ par habitant (tonnes/an)', f"{co2_par_hab:.2f}")
    ajouter('Km totaux territoire (Mkm/an)', f"{bilan_2025['km_total_territoire']:.1f}")
    ajouter('Km par habitant par jour (km/jour)', f"{km_par_hab_jour:.1f}")
    ajouter('Déplacements par habitant/jour', f"{depl_par_hab_jour:.2f}")
    ajouter('')
    
    # ÉMISSIONS PAR MODE
    ajouter('ÉMISSIONS PAR MODE;tonnes CO₂/an;kg/hab/an')
    for mode in ['voiture', 'bus', 'train', 'velo', 'avion', 'marche']:
        co2_mode = bilan_2025['detail_par_mode'][mode]
        co2_hab_mode = (co2_mode / st.session_state.population) * 1000
        ajouter(mode.capitalize(), f"{co2_mode:.0f};{co2_hab_mode:.1f}")
    ajouter('')
    
    # PARTS MODALES
    ajouter('PARTS MODALES 2025 (% des km)')
    for mode, part in parts_2025.items():
        ajouter(mode.capitalize(), f"{part:.1f}")
    
    # Joindre toutes les lignes
    return '\n'.join(lignes)

# Générer le CSV
try:
    csv_content = generer_csv_diagnostic()
    csv_bytes = csv_content.encode('utf-8-sig')
    
    st.download_button(
        label="Télécharger le diagnostic 2025 (CSV)",
        data=csv_bytes,
        file_name="diagnostic_2025_PB.csv",
        mime="text/csv",
        use_container_width=True
    )
except Exception as e:
    st.error(f"Erreur lors de la génération du CSV : {str(e)}")
    st.info("Essayez de rafraîchir la page si le problème persiste.")

st.divider()

# ==================== QUESTIONS PÉDAGOGIQUES ====================

st.info(""" 
- Quels enseignements tirez-vous de cette situation 2025? 
- A titre personnel, comment vous positionnez-vous par rapport à la moyenne du territoire? 
""")


st.divider()

# ==================== VALIDATION ====================

if 'bilan_2025_valide' not in st.session_state:
    st.session_state.bilan_2025_valide = False

col_space1, col_btn, col_space2 = st.columns([1, 1, 1])
with col_btn:
    if st.button("✅ Valider le bilan 2025", type="primary", use_container_width=True):
        st.session_state.bilan_2025_valide = True
        st.rerun()

terminer_sauvegarde(sauvegarde)

# Si validé, afficher bouton navigation
if st.session_state.bilan_2025_valide:
    st.success("Bilan validé !")
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Construire le scénario 2050", type="primary", use_container_width=True):
            st.switch_page("pages/3_🎯_Scenario_2050.py")
