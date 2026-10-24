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
            emission_par_personne = emission_voiture / max(parc_config['taux_occupation'], 0.1)
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


# Ordre d'application des leviers (même ordre que dans le cours et dans le graphique en cascade).
# L'électrification est découpée en trois étapes (voitures, bus, vélos) qui s'additionnent.
LEVIERS_ORDRE = [
    "sobriete", "report", "remplissage", "allegement",
    "elec_voiture", "elec_bus", "elec_velo",
]
LIBELLES_LEVIERS = {
    "sobriete": "Sobriété",
    "report": "Report modal",
    "remplissage": "Remplissage",
    "allegement": "Allègement",
    "elec_voiture": "Élec. voitures",
    "elec_bus": "Élec. bus",
    "elec_velo": "Élec. vélos",
}


def _etat_pour(actifs):
    """Situation obtenue en appliquant, sur la situation 2025, uniquement les leviers de `actifs`.

    Renvoie les distances par mode (Mkm/an), les caractéristiques des parcs et la réduction de poids.
    Avec tous les leviers, c'est le scénario 2050 ; sans aucun levier, c'est la situation 2025.
    """
    ss = st.session_state
    sc = ss.scenario
    km25 = ss.km_2025_territoire

    # 1. Sobriété (voiture et avion uniquement)
    km_sobre = dict(km25)
    if "sobriete" in actifs:
        km_sobre['voiture'] = km25['voiture'] * (1 + sc.get('reduction_km_voiture', 0) / 100)
        km_sobre['avion'] = km25['avion'] * (1 + sc.get('reduction_km_avion', 0) / 100)

    # 2. Report modal (en % des km du mode d'origine, après sobriété)
    km = dict(km_sobre)
    if "report" in actifs:
        km_voiture = km_sobre['voiture']
        km_avion = km_sobre['avion']
        parts = {
            'velo': sc.get('report_velo', 0),
            'bus': sc.get('report_bus', 0),
            'train': sc.get('report_train', 0),
            'marche': sc.get('report_marche', 0),
        }
        total_pct = sum(parts.values())
        echelle = 1.0 if total_pct <= 100 else 100.0 / total_pct   # on ne peut pas reporter plus de 100 %
        transfert = {mode: km_voiture * pct * echelle / 100 for mode, pct in parts.items()}
        transfert_train_avion = km_avion * min(sc.get('report_train_avion', 0), 100) / 100
        km['voiture'] = max(0, km_voiture - sum(transfert.values()))
        km['bus'] = km_sobre['bus'] + transfert['bus']
        km['train'] = km_sobre['train'] + transfert['train'] + transfert_train_avion
        km['velo'] = km_sobre['velo'] + transfert['velo']
        km['marche'] = km_sobre['marche'] + transfert['marche']
        km['avion'] = max(0, km_avion - transfert_train_avion)

    # 3. Caractéristiques des parcs
    part_ve = sc.get('part_ve', ss.parc_2025['part_ve']) if "elec_voiture" in actifs else ss.parc_2025['part_ve']
    occupation = sc.get('taux_remplissage', ss.parc_2025['taux_occupation']) if "remplissage" in actifs else ss.parc_2025['taux_occupation']
    parc = {'part_thermique': 100 - part_ve, 'part_ve': part_ve, 'taux_occupation': occupation}

    if "elec_velo" in actifs:
        elec_velo = sc.get('part_velo_elec', ss.parc_velo_2025['part_elec'])
    else:
        elec_velo = ss.parc_velo_2025['part_elec']
    parc_velo = {'part_elec': elec_velo, 'part_classique': 100 - elec_velo}

    if "elec_bus" in actifs:
        elec_bus = sc.get('part_bus_elec', ss.parc_bus_2025['part_elec'])
    else:
        elec_bus = ss.parc_bus_2025['part_elec']
    parc_bus = {'part_elec': elec_bus, 'part_thermique': 100 - elec_bus}

    poids = sc.get('reduction_poids', 0) if "allegement" in actifs else 0

    return {
        'km': km, 'km_apres_sobriete': km_sobre,
        'parc': parc, 'parc_velo': parc_velo, 'parc_bus': parc_bus,
        'reduction_poids': poids,
    }


def _bilan_pour(actifs):
    """Bilan CO2 du territoire (tonnes/an) avec les leviers de `actifs`."""
    ss = st.session_state
    etat = _etat_pour(actifs)
    emissions = {**ss.emissions, 'emission_thermique': ss.parc_2025['emission_thermique']}
    bilan = calculer_bilan_territoire(
        etat['km'], emissions, etat['parc'], etat['parc_velo'], etat['parc_bus'],
        reduction_poids=etat['reduction_poids'],
    )
    return bilan, etat


def calculer_2050():
    """Calcule le scénario 2050 complet à partir des données stockées en session"""
    bilan_2025, _ = _bilan_pour(set())
    bilan_2050, etat_2050 = _bilan_pour(set(LEVIERS_ORDRE))

    if bilan_2025['co2_total_territoire'] > 0:
        reduction_pct = ((bilan_2025['co2_total_territoire'] - bilan_2050['co2_total_territoire']) /
                         bilan_2025['co2_total_territoire']) * 100
    else:
        reduction_pct = 0

    return {
        'km_2050_territoire': etat_2050['km'],
        'km_2025_apres_sobriete': etat_2050['km_apres_sobriete'],
        'bilan_2025': bilan_2025,
        'bilan_2050': bilan_2050,
        'reduction_pct': reduction_pct,
        'objectif_atteint': reduction_pct >= 70
    }


def calculer_contributions():
    """Contribution de chaque levier, appliqués les uns après les autres dans l'ordre LEVIERS_ORDRE.

    Chaque contribution est l'écart de CO2 (tonnes/an) provoqué par le levier, les précédents étant déjà appliqués.
    L'ordre influence les valeurs : la somme, elle, est toujours égale à l'écart total 2025 -> 2050.
    """
    actifs = set()
    precedent = _bilan_pour(actifs)[0]['co2_total_territoire']
    co2_2025 = precedent
    etapes = []
    for levier in LEVIERS_ORDRE:
        actifs.add(levier)
        courant = _bilan_pour(actifs)[0]['co2_total_territoire']
        etapes.append((levier, courant - precedent))
        precedent = courant
    return {'co2_2025': co2_2025, 'etapes': etapes, 'co2_2050': precedent}
