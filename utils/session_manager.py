# utils/session_manager.py
"""
Sauvegarde et reprise du travail des étudiants.

Deux mécanismes complémentaires :
1. Fichier .json téléchargeable (sauvegarde de référence, à déposer sur Moodle).
2. Copie automatique dans le navigateur (localStorage), proposée à la reprise
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
import math
import re
import zlib
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from utils.constants import calculer_km_territoire, saisie_modifiee

APP_ID = "mobilite-pb-2050"
VERSION_FORMAT = 1
PREFIXE_CODE = "MPB1:"
CLE_NAVIGATEUR = "mpb2050_session"        # copie validée
CLE_BROUILLON = "mpb2050_brouillon"       # brouillon en cours de saisie
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

# Limites acceptées au chargement (identiques à celles des champs de saisie et des curseurs).
# Un fichier modifié à la main avec des valeurs hors limites est refusé en entier.
LIMITES = {
    "km_2025_habitant": {"voiture": (0, 20000), "bus": (0, 5000), "train": (0, 3000),
                         "velo": (0, 3000), "avion": (0, 10000), "marche": (0, 1000)},
    "nb_depl_hab": {"voiture": (0, 2000), "bus": (0, 1000), "train": (0, 500),
                    "velo": (0, 1000), "avion": (0, 100), "marche": (0, 2000)},
    "parc_2025": {"part_ve": (0, 100), "part_thermique": (0, 100), "emission_thermique": (0, 500),
                  "taux_occupation": (1.0, 4.0), "temps_stationnement": (80, 99)},
    "parc_velo_2025": {"part_elec": (0, 100), "part_classique": (0, 100)},
    "parc_bus_2025": {"part_elec": (0, 100), "part_thermique": (0, 100)},
    "emissions": {"voiture_electrique": (0, 200), "bus_thermique": (0, 300), "bus_electrique": (0, 100),
                  "train": (0, 50), "velo_elec": (0, 50), "velo_classique": (0, 20),
                  "avion": (0, 500), "marche": (0, 10)},
    "scenario": {"reduction_km_voiture": (-50, 10), "reduction_km_avion": (-50, 10),
                 "report_velo": (0, 50), "report_bus": (0, 50), "report_train": (0, 50),
                 "report_marche": (0, 50), "report_train_avion": (0, 100),
                 "taux_remplissage": (1.0, 4.0), "part_ve": (0, 100), "part_thermique": (0, 100),
                 "part_velo_elec": (0, 100), "part_velo_classique": (0, 100),
                 "part_bus_elec": (0, 100), "part_bus_thermique": (0, 100),
                 "reduction_poids": (0, 30)},
}
LIMITE_POPULATION = (100000, 500000)

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
        return int(round(valeur))
    if isinstance(actuel, float):
        return float(valeur)
    return None


def _nombre_valide(valeur, bornes):
    return (isinstance(valeur, (int, float)) and not isinstance(valeur, bool)
            and math.isfinite(valeur) and bornes[0] <= valeur <= bornes[1])


def appliquer_document(doc):
    """Remplace l'état de la session par celui du document. Renvoie un message.

    Toutes les valeurs sont vérifiées avant d'appliquer quoi que ce soit : en cas de problème,
    l'état courant n'est pas modifié."""
    donnees = doc["donnees"]
    nouvelles = {}

    for cle in CLES_DICT:
        charge = donnees.get(cle)
        actuel = st.session_state.get(cle)
        if charge is None or not isinstance(actuel, dict):
            continue
        if not isinstance(charge, dict):
            raise ValueError("Ce fichier est incomplet ou a été modifié.")
        copie = dict(actuel)
        for sous_cle, valeur in charge.items():
            if sous_cle not in actuel:
                continue   # champ inconnu (autre version) : ignoré
            if not _nombre_valide(valeur, LIMITES[cle][sous_cle]):
                raise ValueError("Ce fichier contient une valeur hors limites ou illisible : il a sans doute été modifié.")
            convertie = _convertir_comme(actuel[sous_cle], valeur)
            if convertie is not None:
                copie[sous_cle] = convertie
        nouvelles[cle] = copie

    simples = {}
    for cle, type_attendu in CLES_SIMPLES:
        if cle not in donnees:
            continue
        valeur = donnees[cle]
        if type_attendu is bool and isinstance(valeur, bool):
            simples[cle] = valeur
        elif type_attendu is int:
            if not _nombre_valide(valeur, LIMITE_POPULATION):
                raise ValueError("Ce fichier contient une population hors limites : il a sans doute été modifié.")
            simples[cle] = int(valeur)
        elif type_attendu is str and isinstance(valeur, str):
            simples[cle] = valeur[:40]

    # Parts complémentaires recalculées (toujours cohérentes entre elles)
    if "parc_2025" in nouvelles:
        nouvelles["parc_2025"]["part_thermique"] = 100 - nouvelles["parc_2025"]["part_ve"]
    if "parc_velo_2025" in nouvelles:
        nouvelles["parc_velo_2025"]["part_classique"] = 100 - nouvelles["parc_velo_2025"]["part_elec"]
    if "parc_bus_2025" in nouvelles:
        nouvelles["parc_bus_2025"]["part_thermique"] = 100 - nouvelles["parc_bus_2025"]["part_elec"]
    if "scenario" in nouvelles:
        sc = nouvelles["scenario"]
        sc["part_thermique"] = 100 - sc["part_ve"]
        sc["part_velo_classique"] = 100 - sc["part_velo_elec"]
        sc["part_bus_thermique"] = 100 - sc["part_bus_elec"]
        if sc["report_velo"] + sc["report_bus"] + sc["report_train"] + sc["report_marche"] > 100:
            raise ValueError("Ce fichier contient un report modal supérieur à 100 % : il a sans doute été modifié.")

    # Application (aucune erreur possible à partir d'ici)
    for cle, valeur in nouvelles.items():
        st.session_state[cle] = valeur
    for cle, valeur in simples.items():
        st.session_state[cle] = valeur

    # Les champs de saisie de la page 1 se réinitialisent à partir des nouvelles valeurs
    for cle in [c for c in st.session_state.keys() if isinstance(c, str) and c.startswith("w1_")]:
        del st.session_state[cle]

    calculer_km_territoire()  # km territoire = km/hab x population (non sauvegardé)

    return f"Travail rechargé (sauvegarde du {_date_lisible(doc.get('horodatage', ''))})."


def charger_texte(texte):
    try:
        doc = decoder(texte)
        message = appliquer_document(doc)
        st.session_state["_restauration_ignoree"] = True
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
        st.markdown("**Reprendre un travail**")
        fichier = st.file_uploader(
            "Charger un fichier de sauvegarde (.json)",
            type=["json"],
            key=f"upl_{n}",
        )
        if fichier is not None:
            ok, message = charger_texte(fichier.getvalue().decode("utf-8-sig", errors="replace"))
            st.session_state["_msg_import"] = (ok, message)
            st.session_state["_n_import"] = n + 1   # vide le champ : pas de rechargement en boucle
            st.rerun()

        message = st.session_state.pop("_msg_import", None)
        if message:
            (st.success if message[0] else st.error)(message[1])

    return {"export": zone_export}


def _marquer_export(signature):
    st.session_state["_export_sig"] = signature
    st.session_state["_export_heure"] = _heure_txt()


def _proposer_restauration(zone, copies):
    """Propose de reprendre la copie validée et/ou le brouillon trouvés dans le navigateur.
    copies : liste de (libellé, texte stocké)."""
    valides = []
    for libelle, stocke in copies:
        if not stocke:
            continue
        try:
            doc = decoder(stocke)
        except ValueError:
            continue
        valides.append((libelle, stocke, doc))
    if not valides:
        return
    with zone:
        st.warning("Un travail a été retrouvé dans ce navigateur. Voulez-vous le reprendre ?")
        for i, (libelle, stocke, doc) in enumerate(valides):
            groupe = doc["donnees"].get("nom_groupe") or "sans nom"
            quand = _date_lisible(doc.get("horodatage", ""))
            if st.button(f"Reprendre {libelle} ({groupe}, {quand})", key=f"restaurer_nav_{i}",
                         type="primary" if i == 0 else "secondary", width="stretch"):
                ok, message = charger_texte(stocke)
                st.session_state["_msg_import"] = (ok, message)
                st.session_state["_restauration_ignoree"] = True
                st.rerun()
        if st.button("Ignorer", key="ignorer_nav", width="stretch"):
            st.session_state["_restauration_ignoree"] = True
            st.rerun()


def _bouton_telechargement(etat, nom_fichier, signature, actif):
    """Bouton de téléchargement 100 % côté navigateur.

    Le fichier est fabriqué par le navigateur à partir des données de la page : aucun fichier
    n'est stocké sur le serveur. Le st.download_button de Streamlit passe par une adresse
    /media/... propre à une instance du serveur ; sur Cloud Run (plusieurs instances, réponses
    plus lentes) il pouvait répondre « Fichier non disponible sur le site ».
    Le dernier export est mémorisé dans le navigateur (localStorage) pour l'indicateur."""
    donnees = json.dumps(etat, ensure_ascii=True).replace("</", "<\\/")
    config = json.dumps({
        "app": APP_ID, "format": VERSION_FORMAT, "nom": nom_fichier,
        "sig": signature, "actif": bool(actif),
    })
    html = _HTML_TELECHARGEMENT.replace("__DONNEES__", donnees).replace("__CONFIG__", config)
    st.iframe(html, height=86)


_HTML_TELECHARGEMENT = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { margin: 0; font-family: "Source Sans Pro", "Segoe UI", Arial, sans-serif; color: #31333f; }
  button { width: 100%; height: 40px; border: 1px solid #c8ccd3; border-radius: 8px; background: #fff;
           color: #31333f; font: inherit; font-size: 16px; cursor: pointer; }
  button:hover:enabled { border-color: #ff4b4b; color: #ff4b4b; }
  button:disabled { opacity: .45; cursor: not-allowed; }
  #info { font-size: 13px; color: #6b6f7b; margin-top: 6px; }
</style></head>
<body>
<button id="b" type="button">Télécharger ma sauvegarde</button>
<div id="info"></div>
<script>
(function () {
  var etat = __DONNEES__;
  var cfg = __CONFIG__;
  var CLE = "mpb2050_export";
  var btn = document.getElementById("b"), info = document.getElementById("info");
  btn.disabled = !cfg.actif;

  function lire() {
    try { return JSON.parse(window.localStorage.getItem(CLE) || "null"); } catch (e) { return null; }
  }
  function afficher() {
    if (!cfg.actif) { info.textContent = ""; return; }
    var d = lire();
    if (!d) { info.textContent = "Pas encore exporté."; }
    else if (d.sig !== cfg.sig) { info.textContent = "Modifications depuis le dernier export (" + d.h + ")."; }
    else { info.textContent = "Dernier export : " + d.h + "."; }
  }
  function deux(n) { return (n < 10 ? "0" : "") + n; }

  btn.addEventListener("click", function () {
    var now = new Date();
    var off = -now.getTimezoneOffset(), sg = off >= 0 ? "+" : "-";
    off = Math.abs(off);
    var iso = now.getFullYear() + "-" + deux(now.getMonth() + 1) + "-" + deux(now.getDate()) + "T" +
              deux(now.getHours()) + ":" + deux(now.getMinutes()) + ":" + deux(now.getSeconds()) +
              sg + deux(Math.floor(off / 60)) + ":" + deux(off % 60);
    var doc = { app: cfg.app, format: cfg.format, horodatage: iso, donnees: etat };
    var blob = new Blob([JSON.stringify(doc, null, 1)], { type: "application/json" });
    var nomFichier = "MobilitePB_" + cfg.nom + "_" + now.getFullYear() + deux(now.getMonth() + 1) +
                     deux(now.getDate()) + "_" + deux(now.getHours()) + deux(now.getMinutes()) + ".json";
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = nomFichier;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
    try {
      window.localStorage.setItem(CLE, JSON.stringify({ sig: cfg.sig, h: deux(now.getHours()) + ":" + deux(now.getMinutes()) }));
    } catch (e) {}
    afficher();
  });
  afficher();
})();
</script></body></html>"""



_HTML_FICHIER = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { margin: 0; font-family: "Source Sans Pro", "Segoe UI", Arial, sans-serif; }
  button { width: 100%; height: 40px; border: 1px solid #c8ccd3; border-radius: 8px; background: #fff;
           color: #31333f; font: inherit; font-size: 16px; cursor: pointer; }
  button:hover { border-color: #ff4b4b; color: #ff4b4b; }
</style></head>
<body><button id="b" type="button"></button>
<script>
(function () {
  var cfg = __CONFIG__;
  var btn = document.getElementById("b");
  btn.textContent = cfg.label;
  btn.addEventListener("click", function () {
    var blob = new Blob(["\ufeff" + cfg.texte], { type: cfg.mime + ";charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = cfg.nom;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
  });
})();
</script></body></html>"""


def bouton_fichier(label, texte, nom_fichier, mime="text/csv"):
    """Bouton qui télécharge un fichier texte fabriqué par le navigateur (voir
    _bouton_telechargement : pas de fichier stocké sur le serveur)."""
    config = json.dumps({"label": label, "texte": texte, "nom": nom_fichier, "mime": mime},
                        ensure_ascii=True).replace("</", "<\\/")
    st.iframe(_HTML_FICHIER.replace("__CONFIG__", config), height=48)



def terminer_sauvegarde(sauvegarde):
    """À appeler en bas de la page, une fois l'état à jour (le fichier exporté contient
    ainsi les dernières valeurs saisies sur la page)."""
    zone = sauvegarde["export"]

    with zone:
        emplacement_reprise = st.container()
        st.markdown("### Sauvegarde")
        # Formulaire : le nom est pris en compte au clic comme avec la touche Entrée.
        with st.form("formulaire_nom_groupe", border=False):
            saisie = st.text_input(
                "Nom du groupe",
                value=st.session_state.get("nom_groupe", ""),
                max_chars=40,
                placeholder="ex : Groupe 3",
            )
            nom_valide = st.form_submit_button("Enregistrer le nom", width="stretch")
        if nom_valide:
            st.session_state["nom_groupe"] = saisie.strip()

    nom = st.session_state.get("nom_groupe", "")
    etat = _etat_courant()
    signature = _signature(etat)
    vierge = etat_vierge()
    code = exporter_code(etat)   # utilisé uniquement pour la copie automatique du navigateur

    # Copie automatique dans le navigateur, en deux cases séparées :
    # - copie validée : écrite seulement quand une étape est validée ;
    # - brouillon : écrit dès que des champs sont modifiés (protège d'un rafraîchissement
    #   avant la première validation) et jamais par-dessus la copie validée.
    with zone:
        info = _composant_navigateur(
            storage_key=CLE_NAVIGATEUR,
            draft_key=CLE_BROUILLON,
            payload="" if vierge else code,
            draft_payload=code if (vierge and saisie_modifiee()) else "",
            clear_draft=not vierge,
            key="stockage_navigateur",
            default=None,
        )

    if st.session_state.get("_auto_sig") != signature and (not vierge or saisie_modifiee()):
        st.session_state["_auto_sig"] = signature
        st.session_state["_auto_heure"] = _heure_txt()

    if (info and vierge and not st.session_state.get("_restauration_ignoree")):
        _proposer_restauration(emplacement_reprise, [
            ("la copie validée", info.get("stored_valide")),
            ("le brouillon", info.get("stored_brouillon")),
        ])

    with zone:
        nettoye = re.sub(r"[^A-Za-z0-9_-]+", "_", nom).strip("_") or "groupe"
        _bouton_telechargement(etat, nettoye, signature, actif=bool(nom))
        if not nom:
            st.caption("Saisissez un nom de groupe pour activer le téléchargement.")

        if info is not None and not info.get("ok", False):
            st.caption("Copie automatique indisponible dans ce navigateur (navigation privée ?). Utilisez le fichier.")
        elif st.session_state.get("_auto_heure"):
            st.caption(f"Copie automatique du navigateur : {st.session_state['_auto_heure']}.")

        st.caption("Le scénario n'est enregistré qu'une fois validé (bouton vert).")


def arreter_page(sauvegarde):
    """Remplace st.stop() : affiche la sauvegarde avant d'arrêter la page."""
    terminer_sauvegarde(sauvegarde)
    st.stop()
