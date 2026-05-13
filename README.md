# Project-1-Analyse-et-Monitoring-du-r-seau-Oslo-Bysykkel
Comprendre les habitudes des usagers pour optimiser la répartition des flottes de vélos (dimension historique). Monitorer l'état du réseau pour repérer les zones de tension en direct (dimension temps réel).

## Installation
1. Cloner le dépôt : `git clone <url>`
2. Installer les dépendances : `pip install -r requirements.txt`

## Utilisation
1. **Génération de la base historique** : Exécuter toutes les cellules de `eda_finale.ipynb`. Cela crée le fichier `oslo_v2.db`.
2. **Lancement de l'API (Optionnel)** : Le dashboard gère l'API de manière autonome, mais vous pouvez lancer `python api_feed.py` pour une mise à jour constante en tâche de fond.
3. **Lancement du Dashboard** : `streamlit run dashboard.py`

## Structure des fichiers
- `dashboard.py` : Interface utilisateur Streamlit.
- `eda_finale.ipynb` : Analyse exploratoire et modèle de clustering.
- `oslo_v2.db` : Base de données des trajets classés par l'IA.
