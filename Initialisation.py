import streamlit as st
import pandas as pd
from utils.constants import initialiser_session
from utils.session_manager import demarrer_sauvegarde, terminer_sauvegarde

st.set_page_config(
    page_title="Mobilité Pays Basque 2050 - ESTIA",
    page_icon="",
    layout="wide"
)

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

# Initialisation et sauvegarde / reprise du travail (barre latérale)
if 'initialized' not in st.session_state:
    initialiser_session()
sauvegarde = demarrer_sauvegarde()

st.title("Mobilité Pays Basque 2050  - ESTIA")


st.header("Projet Décarbonation des Mobilités")

st.markdown("""
### Contexte du projet

Dans le cadre de la **Stratégie Nationale Bas-Carbone (SNBC)**, la France s'est fixée un objectif ambitieux : 
**réduire d'environ 70% les émissions du secteur transport d'ici 2050** par rapport à la situation actuelle. [Stratégie SNBC Transports](https://www.ecologie.gouv.fr/sites/default/files/documents/Fiche%20SNBC%20Transports_0.pdf).

Vous êtes des **consultant.e.s en mobilités**.  
Votre client : la Communauté d'Agglomération Pays Basque, en partenariat avec le Syndicat des Mobilités Pays Basque-Adour.  
Votre mission : construire un scénario de décarbonation cohérent pour le territoire Pays Basque en mobilisant différents leviers d'action et détailler les actions à mettre en oeuvre pour réaliser votre scénario.



###  Objectifs pédagogiques

À travers cette application, vous allez :
- Analyser les données de mobilité actuelles du territoire
- Construire un scénario 2050 en combinant différents leviers d'action
- Évaluer l'impact de vos choix sur les émissions de CO₂
- Comprendre quels leviers sont les plus efficaces pour décarboner la mobilité

### Les 5 leviers disponibles

1. **Électrification** : Remplacer les véhicules thermiques (voitures, bus) par des électriques
2. **Sobriété** : Réduire le nombre total de km parcourus
3. **Report modal** : Transférer vers des modes moins émetteurs (vélo, bus, train)
4. **Taux de remplissage** : Augmenter l'occupation des véhicules
5. **Allègement** : Réduire le poids des véhicules


###  Livrable attendu

À la fin de ce projet, vous devrez produire un rapport (format docx ou pdf) de 8 à 12 pages, présentant :
- **Un scénario 2050** cohérent et justifié permettant d'atteindre l'objectif de -70% d'émissions. Ce scénario sera propre au groupe de travail.
- **Une analyse** de votre scénario : quels leviers sont les plus efficaces ? Le niveau de chaque levier est-il réaliste ?
- **Une synthèse** présentant vos choix sur chaque levier
- **Un plan d'action**: les actions à mettre en place par les pouvoirs publics et par les citoyen.ne.s pour parvenir à atteindre les évolutions de chaque levier. Bien citer les sources utilisées, avec lien, date et page de l'information utilisée.
- **Une critique** de cet outil interactif: les limites des hypothèses simplificatrices


L'outil permet des **exports de données** (fichier csv/png) de l'ensemble des résultats. 
Pensez à **sauvegarder régulièrement** vos données en exportant vos résultats !
Les graphiques peuvent également être exportés et intégrés dans votre rapport.

###  Bibliographie

#### Les chiffres et objectifs nationaux

- **La consommation d’énergie des transports (2023)** — Ministère de la Transition écologique et de la Cohésion des territoires    [Bilan énergétique 2023](https://www.statistiques.developpement-durable.gouv.fr/edition-numerique/bilan-energetique-2022/30-55-transports--poursuite-de)
- **Les émissions de gaz à effet de serre du secteur des transports (février 2021)** — Ministère de la Transition écologique et de la Cohésion des territoires    [Article sur les émissions de GES](https://www.notre-environnement.gouv.fr/themes/climat/les-emissions-de-gaz-a-effet-de-serre-et-l-empreinte-carbone-ressources/article/les-emissions-de-gaz-a-effet-de-serre-du-secteur-des-transports)
- **Stratégie Nationale Bas Carbone (SNBC)** — Ministère de la Transition écologique et de la Cohésion des territoires (août 2025)    [SNBC - Politique publique](https://www.ecologie.gouv.fr/politiques-publiques/strategie-nationale-bas-carbone-snbc)
- **ADEME — Bouger autrement au quotidien**    [Guide ADEME (PDF)](https://librairie.ademe.fr/mobilite-et-transports/8487-comment-bouger-autrement--9791029725050.html)


---

#### Articles de presse

- Bigo Aurélien — *La voiture électrique passée au crible de la soutenabilité*, Institut Polytechnique de Paris, Juin 2022    [Lire l’article](https://www.polytechnique-insights.com/tribunes/planete/la-voiture-electrique-passee-au-crible-de-la-soutenabilite/)
- Bigo Aurélien — *Les véhicules intermédiaires : l’avenir de la mobilité ?*    [Lire sur Bon Pote](https://bonpote.com/les-vehicules-intermediaires-lavenir-de-la-mobilite/)
- Chassignet Mathieu — *Assumer le choix politique de réduire l'espace de la voiture*, *Les Echos*, Septembre 2019    [Lire l’article](https://www.lesechos.fr/thema/mobilites-innovations/assumer-le-choix-politique-de-reduire-lespace-de-lavoiture-1131113)
- Gaborit Baptiste — *Atlas des mobilités : Les Français parcourent 50 kilomètres en moyenne chaque jour*, *Radio Classique*, Juin 2022    [Lire l’article](https://www.radioclassique.fr/environnement/atlas-des-mobilites-les-francais-parcourent-50-kilometres-en-moyenne-chaque-jour/)
- Lavadinho Sonia — *Réduire la place de la voiture ne sert à rien si l’on ne redonne pas cette place à l’humain*, *Envies de Ville*, Novembre 2022    [Lire l’article](https://www.enviesdeville.fr/penser-la-ville/mobilite-ville-sonia-lavadinho/)
- Marqués Ricardo — *Politiques cyclables : Quelles leçons tirer de l’exemple de Séville*, *Forum Vies Mobiles*, Novembre 2021    [Lire l’article](https://forumviesmobiles.org/points-de-vue/15715/politiques-cyclables-quelles-lecons-tirer-de-lexemple-de-seville)
- Razemon Olivier — *Le système routier, en manque, pris au piège de sa toute puissance*, *Le Monde*, Octobre 2022    [Lire l’article](https://www.lemonde.fr/blog/transports/2022/10/12/le-systeme-routier-en-manque-pris-au-piege-de-sa-toute-puissance/)


###  Démarrage

Cliquez sur "Commencer" pour accéder aux données de mobilité 2025.

""")


terminer_sauvegarde(sauvegarde)

if st.button("Commencer", type="primary", use_container_width=True):
    st.switch_page("pages/1_Donnees_2025.py")
    st.rerun()


st.info("Utilisez la navigation à gauche pour accéder aux différentes pages")
