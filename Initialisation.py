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

st.title("🚗 Mobilité Pays Basque 2050 - ESTIA")


st.header("Projet Décarbonation des Mobilités")

st.markdown("""
### Contexte du projet

La Stratégie nationale bas-carbone (SNBC 3) vise une décarbonation complète du secteur des transports en 2050 ([page SNBC Transports](https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone/transports)).
Cet exercice s'en inspire : il retient une réduction de **70 %** des émissions de la mobilité des habitants entre 2025 et 2050, calculées sur le **cycle de vie** (ACV).
Ce repère de 70 % est un choix pédagogique de l'exercice.

Vous êtes des **consultant.e.s en mobilités**.  
Votre client : la Communauté d'Agglomération Pays Basque, en partenariat avec le Syndicat des Mobilités Pays Basque-Adour.  
Votre mission : construire un scénario de décarbonation cohérent pour le territoire Pays Basque en mobilisant différents leviers d'action.

### Les 5 leviers disponibles

1. **Électrification** : Remplacer les véhicules thermiques (voitures, bus) par des électriques
2. **Sobriété** : Réduire le nombre total de km parcourus
3. **Report modal** : Transférer vers des modes moins émetteurs (vélo, bus, train)
4. **Taux de remplissage** : Augmenter l'occupation des véhicules
5. **Allègement** : Réduire le poids des véhicules

Pensez à **télécharger votre sauvegarde** régulièrement (menu de gauche) : c'est elle qui permet de reprendre votre travail.

###  Bibliographie

#### Les chiffres et objectifs nationaux

- **La consommation d’énergie des transports (édition 2022)** — Ministère de la Transition écologique et de la Cohésion des territoires    [Bilan énergétique, édition 2022, chapitre Transports](https://www.statistiques.developpement-durable.gouv.fr/edition-numerique/bilan-energetique-2022/30-55-transports--poursuite-de)
- **Les émissions de gaz à effet de serre du secteur des transports (février 2021)** — Ministère de la Transition écologique et de la Cohésion des territoires    [Article sur les émissions de GES](https://www.notre-environnement.gouv.fr/themes/climat/les-emissions-de-gaz-a-effet-de-serre-et-l-empreinte-carbone-ressources/article/les-emissions-de-gaz-a-effet-de-serre-du-secteur-des-transports)
- **Stratégie nationale bas-carbone (SNBC 3), secteur des transports** — Ministère de la Transition écologique    [Page SNBC Transports](https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone/transports)
- **ADEME — Bouger autrement au quotidien**    [Guide ADEME (PDF)](https://librairie.ademe.fr/mobilite-et-transports/8487-comment-bouger-autrement--9791029725050.html)


---

#### Articles de presse

- Bigo Aurélien — *La voiture électrique passée au crible de la soutenabilité*, Institut Polytechnique de Paris, Juin 2022    [Lire l’article](https://www.polytechnique-insights.com/tribunes/planete/la-voiture-electrique-passee-au-crible-de-la-soutenabilite/)
- Bigo Aurélien — *Les véhicules intermédiaires : l’avenir de la mobilité ?*    [Lire sur Bon Pote](https://bonpote.com/les-vehicules-intermediaires-lavenir-de-la-mobilite/)
- Chassignet Mathieu — *Assumer le choix politique de réduire l'espace de la voiture*, *Les Echos*, Septembre 2019    [Lire l’article](https://www.lesechos.fr/thema/mobilites-innovations/assumer-le-choix-politique-de-reduire-lespace-de-lavoiture-1131113)
- Gaborit Baptiste — *Atlas des mobilités : Les Français parcourent 50 kilomètres en moyenne chaque jour*, *Radio Classique*, Juin 2022    [Lire l’article](https://www.radioclassique.fr/environnement/atlas-des-mobilites-les-francais-parcourent-50-kilometres-en-moyenne-chaque-jour/)
- Lavadinho Sonia — *Réduire la place de la voiture ne sert à rien si l’on ne redonne pas cette place à l’humain*, *Envies de Ville*, Novembre 2022    [Lire l’article](https://www.enviesdeville.fr/penser-la-ville/mobilite-ville-sonia-lavadinho/)
- Marqués Ricardo — *Politiques cyclables : Quelles leçons tirer de l’exemple de Séville*, *Forum Vies Mobiles*, Novembre 2022    [Lire l’article](https://forumviesmobiles.org/points-de-vue/15715/politiques-cyclables-quelles-lecons-tirer-de-lexemple-de-seville)
- Razemon Olivier — *Le système routier, en manque, pris au piège de sa toute puissance*, *Le Monde*, Octobre 2022    [Lire l’article](https://www.lemonde.fr/blog/transports/2022/10/12/le-systeme-routier-en-manque-pris-au-piege-de-sa-toute-puissance/)


###  Démarrage

Cliquez sur "Commencer" pour accéder aux données de mobilité 2025.

""")


terminer_sauvegarde(sauvegarde)

if st.button("🚀 Commencer", type="primary", width="stretch"):
    st.switch_page("pages/1_📝_Donnees_2025.py")
    st.rerun()


st.info("Utilisez la navigation à gauche pour accéder aux différentes pages")
