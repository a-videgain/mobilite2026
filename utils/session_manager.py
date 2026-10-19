# utils/session_manager.py
"""
Sauvegarde et reprise du travail des étudiants.

Trois mécanismes complémentaires :
1. Fichier .json téléchargeable (sauvegarde de référence, à déposer sur Moodle).
2. Code texte à copier-coller (secours si le téléchargement échoue).
3. Copie automatique dans le navigateur (localStorage), proposée à la reprise
   si la page a été rafraîchie. Ne remplace pas le fichier : elle disparaît si le
   cache du navigateur est vidé ou si l'étudiant change d'ordinateur.

Utilisation dans chaque page :
    sauvegarde = demarrer_sauvegarde()    # en haut, après initialiser_session()
    ...
    arreter_page(sauvegarde)              # à la place de st.stop()
    ...
    terminer_sauvegarde(sauvegarde)       # en bas, une fois l'état de la page à jour
"""

import base64
import hashlib
import json
import re
import zlib
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from utils.constants import calculer_km_territoire

APP_ID = "mobilite-pb-2050"
VERSION_FORMAT = 1
PREFIXE_CODE = "MPB1:"
CLE_NAVIGATEUR = "mpb2050_session"
TAILLE_MAX_CODE = 200_000          # caractères acceptés au chargement
TAILLE_MAX_DECOMPRESSEE = 1_000_000  # octets

# Dictionnaires de la session à sauvegarder (toutes les valeurs saisies, dont les émissions)
CLES_DICT = [
    "km_2025_habitant",
    "nb_depl_hab",
    "parc_2025",
    "parc_velo_2025",
    "parc_bus_2025",
    "emissions",
    "scenario",
]
# Valeurs simples : (clé, type attendu)
CLES_SIMPLES = [
    ("population", int),
    ("donnees_2025_validees", bool),
    ("bilan_2025_valide", bool),
    ("scenario_2050_valide", bool),
    ("nom_groupe", str),
]

_composant_navigateur = components.declare_component(
    "mpb_stockage_navigateur",
    path=str(Path(__file__).parent / "stockage_navigateur"),
)


# ==================== OUTILS ====================

def _maintenant():
    """Heure de Paris (le serveur est probablement en UTC)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Paris"))
    except Exception:
        return datetime.now()


def _date_lisible(iso):
    """'2026-10-19T20:37:12+02:00' -> '19/10/2026 à 20:37'."""
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y à %H:%M")
    except Exception:
        return "date inconnue"


def _heure_txt(dt=None):
    return (dt or _maintenant()).strftime("%H:%M")


def etat_vierge():
    """Vrai tant que l'étudiant n'a validé aucune étape."""
    return not any(
        st.session_state.get(c, False)
        for c in ("donnees_2025_validees", "bilan_2025_valide", "scenario_2050_valide")
    )


def _etat_courant():
    """Données à sauvegarder, sans horodatage."""
    etat = {}
    for cle in CLES_DICT:
        if cle in st.session_state:
            etat[cle] = dict(st.session_state[cle])
    for cle, _type in CLES_SIMPLES:
        if cle in st.session_state:
            etat[cle] = st.session_state[cle]
    return etat


def _signature(etat):
    brut = json.dumps(etat, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(brut.encode("utf-8")).hexdigest()


def _document(etat):
    return {
        "app": APP_ID,
        "format": VERSION_FORMAT,
        "horodatage": _maintenant().isoformat(timespec="seconds"),
        "donnees": etat,
    }


def exporter_json(etat):
    return json.dumps(_document(etat), ensure_ascii=False, indent=1)


def exporter_code(etat):
    brut = json.dumps(_document(etat), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return PREFIXE_CODE + base64.urlsafe_b64encode(zlib.compress(brut, 9)).decode("ascii")


def decoder(texte):
    """Accepte le contenu d'un fichier .json ou un code MPB1:... ; renvoie le document."""
    texte = (texte or "").strip().lstrip("﻿")
    if not texte:
        raise ValueError("Aucun contenu à charger.")
    if len(texte) > TAILLE_MAX_CODE:
        raise ValueError("Contenu trop volumineux.")
    if texte.startswith(PREFIXE_CODE):
        morceau = re.sub(r"\s+", "", texte[len(PREFIXE_CODE):])
        try:
            compresse = base64.urlsafe_b64decode(morceau + "=" * (-len(morceau) % 4))
            decompresseur = zlib.decompressobj()
            brut = decompresseur.decompress(compresse, TAILLE_MAX_DECOMPRESSEE)
            doc = json.loads(brut.decode("utf-8"))
        except Exception:
            raise ValueError("Le code est incomplet ou abîmé. Copiez-le en entier, sans rien ajouter.")
    else:
        try:
            doc = json.loads(texte)
        except Exception:
            raise ValueError("Ce fichier n'est pas une sauvegarde de cet outil.")
    if not isinstance(doc, dict) or doc.get("app") != APP_ID or not isinstance(doc.get("donnees"), dict):
        raise ValueError("Ce fichier n'est pas une sauvegarde de cet outil.")
    return doc


def _convertir_comme(actuel, valeur):
    """Garde le type de la valeur par défaut (int/float) pour ne pas gêner les widgets Streamlit."""
    if isinstance(actuel, bool) or isinstance(valeur, bool):
        return None
    if isinstance(actuel, int):
        return int(valeur) if float(valeur) == int(valeur) else float(valeur)
    if isinstance(actuel, float):
        return float(valeur)
    return None


def appliquer_document(doc):
    """Remplace l'état de la session par celui du document. Renvoie un message."""
    donnees = doc["donnees"]
    ignores = []

    for cle in CLES_DICT:
        charge = donnees.get(cle)
        if not isinstance(charge, dict) or not isinstance(st.session_state.get(cle), dict):
            continue
        actuel = st.session_state[cle]
        for sous_cle, valeur in charge.items():
            if sous_cle not in actuel or not isinstance(valeur, (int, float)):
                ignores.append(f"{cle}.{sous_cle}")
                continue
            converti = _convertir_comme(actuel[sous_cle], valeur)
            if converti is not None:
                actuel[sous_cle] = converti

    for cle, type_attendu in CLES_SIMPLES:
        if cle not in donnees:
            continue
        valeur = donnees[cle]
        if type_attendu is bool and isinstance(valeur, bool):
            st.session_state[cle] = valeur
        elif type_attendu is int and isinstance(valeur, (int, float)) and not isinstance(valeur, bool):
            st.session_state[cle] = int(valeur)
        elif type_attendu is str and isinstance(valeur, str):
            st.session_state[cle] = valeur[:60]

    calculer_km_territoire()  # km territoire = km/hab x population (non sauvegardé)

    return f"Travail rechargé (sauvegarde du {_date_lisible(doc.get('horodatage', ''))})."


def charger_texte(texte):
    try:
        doc = decoder(texte)
        message = appliquer_document(doc)
        return True, message
    except ValueError as e:
        return False, str(e)
    except Exception:
        return False, "Le chargement a échoué. Vérifiez le fichier ou appelez l'enseignant."


# ==================== INTERFACE ====================

def demarrer_sauvegarde():
    """À appeler en haut de la page. Traite le chargement d'un fichier ou d'un code
    AVANT l'affichage de la page, puis renvoie les emplacements de la barre latérale."""
    with st.sidebar:
        zone_export = st.container()
        zone_import = st.container()

    n = st.session_state.get("_n_import", 0)
    with zone_import:
        st.markdown("**📂 Reprendre un travail**")
        fichier = st.file_uploader(
            "Charger un fichier de sauvegarde (.json)",
            type=["json", "txt"],
            key=f"upl_{n}",
        )
        if fichier is not None:
            ok, message = charger_texte(fichier.getvalue().decode("utf-8-sig", errors="replace"))
            st.session_state["_msg_import"] = (ok, message)
            st.session_state["_n_import"] = n + 1   # vide le champ : pas de rechargement en boucle
            st.rerun()

        with st.expander("…ou coller un code de secours"):
            code = st.text_area("Code", key=f"txt_{n}", height=90, label_visibility="collapsed",
                                placeholder="Collez ici le code qui commence par MPB1:")
            if st.button("Charger ce code", key=f"btn_{n}", use_container_width=True):
                ok, message = charger_texte(code)
                st.session_state["_msg_import"] = (ok, message)
                st.session_state["_n_import"] = n + 1
                st.rerun()

        message = st.session_state.pop("_msg_import", None)
        if message:
            (st.success if message[0] else st.error)(message[1])

    return {"export": zone_export}


def _marquer_export(signature):
    st.session_state["_export_sig"] = signature
    st.session_state["_export_heure"] = _heure_txt()


def _proposer_restauration(zone, stocke):
    """Affiche la proposition de reprise de la copie du navigateur."""
    try:
        doc = decoder(stocke)
    except ValueError:
        return
    donnees = doc["donnees"]
    quand = _date_lisible(doc.get("horodatage", ""))
    groupe = donnees.get("nom_groupe") or "sans nom"
    with zone:
        st.warning(
            f"💽 Un travail a été retrouvé dans ce navigateur (groupe : {groupe}, {quand}).  \n"
            "Voulez-vous le reprendre ?"
        )
        c1, c2 = st.columns(2)
        if c1.button("Reprendre", key="restaurer_nav", type="primary", use_container_width=True):
            ok, message = charger_texte(stocke)
            st.session_state["_msg_import"] = (ok, message)
            st.rerun()
        if c2.button("Ignorer", key="ignorer_nav", use_container_width=True):
            st.session_state["_restauration_ignoree"] = True
            st.rerun()


def terminer_sauvegarde(sauvegarde):
    """À appeler en bas de la page, une fois l'état à jour (le fichier exporté contient
    ainsi les dernières valeurs saisies sur la page)."""
    zone = sauvegarde["export"]
    etat = _etat_courant()
    signature = _signature(etat)
    vierge = etat_vierge()
    code = exporter_code(etat)

    # Copie automatique dans le navigateur (on n'écrit rien tant que rien n'est validé,
    # pour ne pas écraser une copie existante par un état vide après un rafraîchissement).
    with zone:
        info = _composant_navigateur(
            storage_key=CLE_NAVIGATEUR,
            payload="" if vierge else code,
            key="stockage_navigateur",
            default=None,
        )

    if st.session_state.get("_auto_sig") != signature and not vierge:
        st.session_state["_auto_sig"] = signature
        st.session_state["_auto_heure"] = _heure_txt()

    if (info and info.get("stored") and vierge
            and not st.session_state.get("_restauration_ignoree")):
        _proposer_restauration(zone, info["stored"])

    with zone:
        st.markdown("### 💾 Sauvegarde")

        nom = st.text_input(
            "Nom du groupe",
            value=st.session_state.get("nom_groupe", ""),
            key="_nom_groupe_widget",
            max_chars=40,
            placeholder="ex : Groupe 3",
            on_change=lambda: st.session_state.update(
                nom_groupe=st.session_state.get("_nom_groupe_widget", "")
            ),
        )

        nettoye = re.sub(r"[^A-Za-z0-9_-]+", "_", (nom or "").strip()).strip("_") or "groupe"
        horodatage = _maintenant().strftime("%Y%m%d_%H%M")
        st.download_button(
            "📥 Télécharger ma sauvegarde",
            data=exporter_json(etat).encode("utf-8"),
            file_name=f"MobilitePB_{nettoye}_{horodatage}.json",
            mime="application/json",
            on_click=_marquer_export,
            args=(signature,),
            use_container_width=True,
            key="telecharger_sauvegarde",
        )

        if "_export_sig" not in st.session_state:
            st.caption("⚠️ Pas encore exporté.")
        elif st.session_state["_export_sig"] != signature:
            st.caption(f"⚠️ Modifications depuis le dernier export ({st.session_state.get('_export_heure', '?')}).")
        else:
            st.caption(f"✅ Dernier export : {st.session_state.get('_export_heure', '?')}.")

        if info is not None and not info.get("ok", False):
            st.caption("⚠️ Copie automatique indisponible dans ce navigateur (navigation privée ?). Utilisez le fichier.")
        elif st.session_state.get("_auto_heure"):
            st.caption(f"💽 Copie automatique du navigateur : {st.session_state['_auto_heure']}.")

        st.caption("Le scénario n'est enregistré qu'une fois **validé** (bouton vert).")

        with st.expander("📋 Code de secours (copier-coller)"):
            st.caption("Si le téléchargement ne marche pas : copiez ce code dans un document personnel. "
                       "Il permet de reprendre votre travail.")
            st.code(code, language=None, wrap_lines=True)


def arreter_page(sauvegarde):
    """Remplace st.stop() : affiche la sauvegarde avant d'arrêter la page."""
    terminer_sauvegarde(sauvegarde)
    st.stop()
