import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import pydeck as pdk
import requests
import time
from datetime import datetime, timedelta

# --- FONCTION DE MISE À JOUR AUTO ---
def sync_live_data():
    conn = sqlite3.connect('oslo_live.db')
    
    # Étape A : Créer la table si elle n'existe pas (évite l'erreur "no such table")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS live_stations (
            station_id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL, 
            bikes_available INTEGER, docks_available INTEGER, last_updated TEXT
        )
    ''')
    
    # Étape B : Vérifier s'il faut mettre à jour
    should_update = False
    try:
        last_up_query = pd.read_sql("SELECT MAX(last_updated) as last FROM live_stations", conn)
        if last_up_query['last'].iloc[0] is None:
            should_update = True
        else:
            last_up = datetime.strptime(last_up_query['last'].iloc[0], "%Y-%m-%d %H:%M:%S")
            if datetime.now() - last_up > timedelta(minutes=5):
                should_update = True
    except:
        should_update = True

    # Étape C : Appel API si nécessaire
    if should_update:
        try:
            INFO_URL = "https://gbfs.urbansharing.com/oslobysykkel.no/station_information.json"
            STATUS_URL = "https://gbfs.urbansharing.com/oslobysykkel.no/station_status.json"
            
            # Récupération
            r_info = requests.get(INFO_URL).json()['data']['stations']
            r_status = requests.get(STATUS_URL).json()['data']['stations']
            
            df_i = pd.DataFrame(r_info)[['station_id', 'name', 'lat', 'lon']]
            df_s = pd.DataFrame(r_status)[['station_id', 'num_bikes_available', 'num_docks_available']]
            
            df_l = pd.merge(df_i, df_s, on='station_id')
            df_l.rename(columns={'num_bikes_available': 'bikes_available', 'num_docks_available': 'docks_available'}, inplace=True)
            df_l['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            df_l.to_sql('live_stations', conn, if_exists='replace', index=False)
        except Exception as e:
            st.error(f"Erreur API : {e}")
    
    conn.close()

sync_live_data()

st.set_page_config(page_title="Oslo - SAE Data", layout="wide")
st.title("Oslo : Analyse et Monitoring du reseau")

tab1, tab2 = st.tabs(["Analyse Historique (Clustering IA)", "Temps Reel (Monitoring)"])

# ---------------------------------------------------------
# ONGLET 1 : HISTORIQUE ET CLUSTERS
# ---------------------------------------------------------
with tab1:
    st.header("Profilage des trajets (Visualisation des Flux)")
    st.markdown("Explorez les trajets reels classes par notre algorithme (K-Means).")
    
    try:
        conn_hist = sqlite3.connect('oslo_v2.db') 
        df_hist = pd.read_sql("SELECT * FROM trips_clustered LIMIT 5000", conn_hist)
        conn_hist.close()
        
        if not df_hist.empty:
            st.markdown("### Filtres d'exploration")
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.write("**Plage horaire :**")
                c_start, c_end = st.columns(2)
                with c_start:
                    h_debut = st.number_input("Debut", min_value=0, max_value=23, value=0, step=1)
                with c_end:
                    h_fin = st.number_input("Fin", min_value=0, max_value=23, value=23, step=1)

            with col_f2:
                st.write("**Type de periode :**")
                type_periode = st.radio("Filtrer par :", ["Tous les jours", "Semaine uniquement", "Week-end uniquement"], horizontal=True)

            col_f3, col_f4 = st.columns(2)
            with col_f3:
                noms_jours = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"}
                jours_selectionnes = st.multiselect("Jours specifiques :", options=list(noms_jours.values()), default=list(noms_jours.values()))
            
            with col_f4:
                clusters_dispos = sorted(df_hist['Profil_Metier'].dropna().unique().tolist())
                clusters_choisis = st.multiselect("Profils d'utilisateurs :", options=clusters_dispos, default=clusters_dispos)

            st.write("**Duree du trajet (en minutes) :**")
            min_val, max_val = int(df_hist['duration_min'].min()), int(df_hist['duration_min'].max())
            duree_range = st.slider("Selectionnez la plage de duree :", min_value=min_val, max_value=max_val, value=(min_val, max_val))
            
            st.divider()

            # Application des filtres
            mask_heure = (df_hist['hour'] >= h_debut) & (df_hist['hour'] <= h_fin) if h_debut <= h_fin else (df_hist['hour'] >= h_debut) | (df_hist['hour'] <= h_fin)
            mask_periode = (df_hist['is_weekend'] == 0) if type_periode == "Semaine uniquement" else (df_hist['is_weekend'] == 1) if type_periode == "Week-end uniquement" else True
            mask_jours = df_hist['day_of_week'].isin([k for k, v in noms_jours.items() if v in jours_selectionnes])
            mask_duree = (df_hist['duration_min'] >= duree_range[0]) & (df_hist['duration_min'] <= duree_range[1])

            df_filtered = df_hist[mask_heure & mask_periode & mask_jours & mask_duree & (df_hist['Profil_Metier'].isin(clusters_choisis))].copy()
        
            # Configuration des couleurs
            def get_colors(profil_name):
                p = str(profil_name).lower()
                if "vélotafeur" in p or "business" in p: return {"rgb": [255, 75, 75, 200], "hex": "#FF4B4B"}
                elif "touriste" in p or "loisir" in p: return {"rgb": [0, 204, 150, 200], "hex": "#00CC96"}
                elif "noctambule" in p or "nuit" in p: return {"rgb": [171, 99, 250, 200], "hex": "#AB63FA"}
                elif "standard" in p or "locaux" in p: return {"rgb": [25, 211, 243, 200], "hex": "#19D3F3"}
                else: return {"rgb": [150, 150, 150, 200], "hex": "#999999"}

            df_filtered['color_pydeck'] = df_filtered['Profil_Metier'].apply(lambda x: get_colors(x)['rgb'])
            plotly_color_map = {prof: get_colors(prof)['hex'] for prof in df_filtered['Profil_Metier'].unique()}

            # Couche Pydeck
            arc_layer = pdk.Layer(
                "ArcLayer",
                data=df_filtered,
                get_source_position=["start_station_longitude", "start_station_latitude"],
                get_target_position=["end_station_longitude", "end_station_latitude"],
                get_source_color="color_pydeck",
                get_target_color="color_pydeck",
                get_width=3,
                pickable=True,
                auto_highlight=True
            )

            view_state = pdk.ViewState(
                latitude=df_filtered["start_station_latitude"].mean() if not df_filtered.empty else 59.91,
                longitude=df_filtered["start_station_longitude"].mean() if not df_filtered.empty else 10.75,
                zoom=11.5, pitch=50, bearing=0
            )

            colA, colB = st.columns([2, 1])
            
            with colA:
                st.pydeck_chart(pdk.Deck(
                    map_style="dark", 
                    initial_view_state=view_state,
                    layers=[arc_layer],
                    tooltip={"html": "<b>Profil :</b> {Profil_Metier}<br/><b>Trajet :</b> {start_station_name} vers {end_station_name}"}
                ))
                    
            with colB:
                st.subheader("Volumes par profil")
                if not df_filtered.empty:
                    profil_counts = df_filtered['Profil_Metier'].value_counts().reset_index()
                    profil_counts.columns = ['Profil', 'Nombre']
                    fig_bar = px.bar(
                        profil_counts, x='Profil', y='Nombre', 
                        color='Profil', color_discrete_map=plotly_color_map, template="plotly_dark"
                    )
                    fig_bar.update_layout(showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.write("Aucune donnee avec ces filtres.")

    except Exception as e:
        st.error(f"Erreur de chargement de la base historique : {e}.")

# ---------------------------------------------------------
# ONGLET 2 : TEMPS REEL
# ---------------------------------------------------------
with tab2:
    st.header("État du réseau en direct")
    st.info("Ce flux affiche la disponibilité immédiate des bornes via l'API officielle d'Oslo.")

    # --- 1. BOUTON DE MISE À JOUR (Toujours visible) ---
    if st.button(" Actualiser les données "):
        with st.spinner("Connexion à l'API d'Oslo..."):
            sync_live_data()
            st.success("Données mises à jour !")
            time.sleep(1)
            st.rerun()

    # --- 2. AFFICHAGE DES DONNÉES ---
    try:
        conn = sqlite3.connect('oslo_live.db')
        df_live = pd.read_sql("SELECT * FROM live_stations", conn)
        conn.close()

        if not df_live.empty:
            # Calcul des indicateurs
            total_bikes = df_live['bikes_available'].sum()
            total_docks = df_live['docks_available'].sum()
            derniere_maj = df_live['last_updated'].max()

            # Affichage des KPIs
            k1, k2, k3 = st.columns(3)
            k1.metric("Vélos disponibles", int(total_bikes))
            k2.metric("Places libres", int(total_docks))
            k3.metric("Heure API", str(derniere_maj)[11:19])

            # Carte interactive
            st.subheader("Carte des stations")
            fig_live = px.scatter_mapbox(
                df_live, 
                lat="lat", lon="lon", 
                size="bikes_available", 
                color="bikes_available",
                color_continuous_scale="Viridis",
                hover_name="name", 
                hover_data={"bikes_available": True, "docks_available": True, "lat": False, "lon": False},
                zoom=11.5, 
                mapbox_style="carto-positron", 
                height=600
            )
            st.plotly_chart(fig_live, use_container_width=True)
            
            st.caption(f"Dernier rafraîchissement local : {time.strftime('%H:%M:%S')}")
        else:
            st.warning("La base de données est vide. Cliquez sur le bouton 'Actualiser' pour charger les données.")

    except Exception as e:
        st.error(f"Erreur d'affichage : {e}")
        st.info("Conseil : Cliquez sur le bouton d'actualisation pour recréer la base de données.")
