# utils/calculations.py

import streamlit as st

# ==================== CALCULS MOBILITÉ ====================

def format_nombre(n, decimales=0):
    """Formate un nombre avec des espaces pour les milliers"""
    if decimales == 0:
        return f"{n:,.0f}".replace(',', ' ')
    else:
        return f"{n:,.{decimales}f}".replace(',', ' ')


def calculer_bilan_territoire(km_territoire, emissions_parc, parc_config, parc_velo_config, parc_bus_config, reduction_poids=0):
    """
    Calcule le bilan CO₂ total du territoire (en tonnes) et les détails par mode.
    
    km_territoire : dict (millions de km/an)
    emissions_parc : dict (gCO₂/km)
    parc_config : dict caractéristiques voitures
    parc_velo_config : dict caractéristiques vélos
    parc_bus_config : dict caractéristiques bus
    reduction_poids : % de réduction de poids (impacte conso)
    """
    co2_total_territoire = 0
    detail_par_mode = {}

    for mode in km_territoire:
        if mode == 'voiture':
            facteur_allegement = 1 - (reduction_poids * 0.7 / 100)
            emission_thermique_ajustee = emissions_parc['emission_thermique'] * facteur_allegement
            emission_electrique_ajustee = emissions_parc['voiture_electrique'] * facteur_allegement

            emission_voiture = (
                parc_config['part_thermique'] / 100 * emission_thermique_ajustee +
                parc_config['part_ve'] / 100 * emission_electrique_ajustee
            )

            # Conversion g/km → t/an
            emission_par_personne = emission_voiture / parc_config['taux_occupation']
            co2_mode = km_territoire[mode] * 1e6 * emission_par_personne / 1_000_000

        elif mode == 'bus':
            emission_bus = (
                parc_bus_config['part_thermique'] / 100 * emissions_parc['bus_thermique'] +
                parc_bus_config['part_elec'] / 100 * emissions_parc['bus_electrique']
            )
            co2_mode = km_territoire[mode] * 1e6 * emission_bus / 1_000_000

        elif mode == 'velo':
            emission_velo = (
                parc_velo_config['part_elec'] / 100 * emissions_parc['velo_elec'] +
                parc_velo_config['part_classique'] / 100 * emissions_parc['velo_classique']
            )
            co2_mode = km_territoire[mode] * 1e6 * emission_velo / 1_000_000

        elif mode in ['train', 'avion', 'marche']:
            co2_mode = km_territoire[mode] * 1e6 * emissions_parc[mode] / 1_000_000

        else:
            co2_mode = 0

        co2_total_territoire += co2_mode
        detail_par_mode[mode] = co2_mode

    return {
        'co2_total_territoire': co2_total_territoire,
        'km_total_territoire': sum(km_territoire.values()),
        'detail_par_mode': detail_par_mode
    }


def calculer_parts_modales(km_dict):
    """Retourne les parts modales (%) à partir des distances par mode"""
    km_total = sum(km_dict.values())
    if km_total == 0:
        return {mode: 0 for mode in km_dict}
    return {mode: (km / km_total) * 100 for mode, km in km_dict.items()}


def calculer_2050():
    """Calcule le scénario 2050 complet à partir des données stockées en session"""
    
    # 1️⃣ Sobriété (MODIFIÉ : séparé voiture/avion)
    km_2025_apres_sobriete = {}
    for mode, km in st.session_state.km_2025_territoire.items():
        if mode == 'voiture':
            facteur = (1 + st.session_state.scenario.get('reduction_km_voiture', 0) / 100)
            km_2025_apres_sobriete[mode] = km * facteur
        elif mode == 'avion':
            facteur = (1 + st.session_state.scenario.get('reduction_km_avion', 0) / 100)
            km_2025_apres_sobriete[mode] = km * facteur
        else:
            km_2025_apres_sobriete[mode] = km

    # 2️⃣ Report modal
    km_voiture = km_2025_apres_sobriete['voiture']
    km_avion = km_2025_apres_sobriete['avion']
    
    km_transferes_velo = km_voiture * st.session_state.scenario['report_velo'] / 100
    km_transferes_bus = km_voiture * st.session_state.scenario['report_bus'] / 100
    km_transferes_train_voiture = km_voiture * st.session_state.scenario['report_train'] / 100
    km_transferes_marche = km_voiture * st.session_state.scenario.get('report_marche', 0) / 100  # NOUVEAU
    km_transferes_train_avion = km_avion * st.session_state.scenario['report_train_avion'] / 100
    
    # 3️⃣ Nouvelles distances 2050 (avec protection valeurs négatives)
    km_2050 = {
        'voiture': max(0, km_voiture - km_transferes_velo - km_transferes_bus - km_transferes_train_voiture - km_transferes_marche),  # MODIFIÉ
        'bus': km_2025_apres_sobriete['bus'] + km_transferes_bus,
        'train': km_2025_apres_sobriete['train'] + km_transferes_train_voiture + km_transferes_train_avion,
        'velo': km_2025_apres_sobriete['velo'] + km_transferes_velo,
        'avion': max(0, km_avion - km_transferes_train_avion),
        'marche': km_2025_apres_sobriete['marche'] + km_transferes_marche  # MODIFIÉ
    }

    
    # 4️⃣ Nouvelles caractéristiques
    parc_2050 = {
        'part_thermique': st.session_state.scenario['part_thermique'],
        'part_ve': st.session_state.scenario['part_ve'],
        'taux_occupation': st.session_state.scenario['taux_remplissage']
    }

    parc_velo_2050 = {
        'part_elec': st.session_state.scenario['part_velo_elec'],
        'part_classique': st.session_state.scenario['part_velo_classique']
    }

    parc_bus_2050 = {
        'part_elec': st.session_state.scenario['part_bus_elec'],
        'part_thermique': st.session_state.scenario['part_bus_thermique']
    }

    emissions_2050 = st.session_state.emissions.copy()
    emissions_2050['emission_thermique'] = st.session_state.parc_2025['emission_thermique']

    # 5️⃣ Bilans comparatifs
    bilan_2025 = calculer_bilan_territoire(
        st.session_state.km_2025_territoire,
        {**st.session_state.emissions, 'emission_thermique': st.session_state.parc_2025['emission_thermique']},
        st.session_state.parc_2025,
        st.session_state.parc_velo_2025,
        st.session_state.parc_bus_2025,
        reduction_poids=0
    )

    bilan_2050 = calculer_bilan_territoire(
        km_2050,
        emissions_2050,
        parc_2050,
        parc_velo_2050,
        parc_bus_2050,
        reduction_poids=st.session_state.scenario['reduction_poids']
    )

    # 6️⃣ Réduction totale
    if bilan_2025['co2_total_territoire'] > 0:
        reduction_pct = ((bilan_2025['co2_total_territoire'] - bilan_2050['co2_total_territoire']) /
                         bilan_2025['co2_total_territoire']) * 100
    else:
        reduction_pct = 0

    return {
        'km_2050_territoire': km_2050,
        'km_2025_apres_sobriete': km_2025_apres_sobriete,
        'bilan_2025': bilan_2025,
        'bilan_2050': bilan_2050,
        'reduction_pct': reduction_pct,
        'objectif_atteint': reduction_pct >= 70
    }
