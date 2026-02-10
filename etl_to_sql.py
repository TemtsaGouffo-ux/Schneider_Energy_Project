import pandas as pd
import math

# --- CONFIGURATION ---
path_csv = r"C:\Users\TEMTSA GOUFFO\OneDrive - Fondation EPF\Bureau\Nouveau dossier\buildings-energy-consumption-clean-data.csv"
path_excel = r"C:\Users\TEMTSA GOUFFO\OneDrive - Fondation EPF\Bureau\Nouveau dossier\metadata_clean_v2.xlsx"
output_sql = "schneider_data_final.sql"

print("Démarrage de l'ETL ")

try:
    # 1. CHARGEMENT
    df_conso = pd.read_csv(path_csv, sep=';')
    df_meta = pd.read_excel(path_excel)

    # 2. TRANSFORMATION
    df_melted = df_conso.melt(id_vars=['Timestamp'], var_name='Compteur_Complet', value_name='Conso_kWh')
    df_main = df_melted[df_melted['Compteur_Complet'].str.contains("Main Meter")].copy()
    df_main['Site_ID'] = df_main['Compteur_Complet'].str.split('_').str[0].astype(int)
    df_final = pd.merge(df_main, df_meta, on='Site_ID', how='left')

    # CONVERSION DATE
    print(" Conversion des dates...")
    df_final['Timestamp'] = pd.to_datetime(df_final['Timestamp'], utc=True)

    # Colonnes SQL
    df_final['Date_Heure'] = df_final['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df_final['Mois'] = df_final['Timestamp'].dt.month
    df_final['Intensite_Conso'] = df_final['Conso_kWh'] / df_final['Surface']
    df_final = df_final.fillna(0)

    total_rows = len(df_final)
    print(f" {total_rows} lignes prêtes à être écrites.")

    # 3. ÉCRITURE PAR PAQUETS (SANS NUMPY)
    chunk_size = 1000
    # On calcule combien de blocs on va faire
    total_chunks = math.ceil(total_rows / chunk_size)

    print(f" Écriture du fichier SQL en {total_chunks} blocs...")
    
    with open(output_sql, 'w', encoding='utf-8') as f:
        # En-tête
        f.write("CREATE DATABASE IF NOT EXISTS schneider_project;\n")
        f.write("USE schneider_project;\n")
        f.write("DROP TABLE IF EXISTS consommation;\n")
        f.write("""
        CREATE TABLE consommation (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date_heure DATETIME,
            site_id INT,
            surface INT,
            activite VARCHAR(50),
            conso_kwh FLOAT,
            intensite_conso FLOAT,
            mois INT
        );\n
        """)

        # BOUCLE FOR ROBUSTE (Range avec pas de 1000)
        # On avance de 1000 en 1000 : 0, 1000, 2000...
        for i in range(0, total_rows, chunk_size):
            
            # Barre de progression
            current_chunk_num = (i // chunk_size) + 1
            if current_chunk_num % 50 == 0:
                print(f"   -> Bloc {current_chunk_num}/{total_chunks} traité...")

            # Découpage sécurisé avec Pandas (.iloc)
            chunk = df_final.iloc[i : i + chunk_size]
            
            f.write("INSERT INTO consommation (date_heure, site_id, surface, activite, conso_kwh, intensite_conso, mois) VALUES\n")
            
            values_list = []
            for _, row in chunk.iterrows():
                activite_safe = str(row['Customer Activity']).replace("'", "")
                val = f"('{row['Date_Heure']}', {row['Site_ID']}, {row['Surface']}, '{activite_safe}', {row['Conso_kWh']}, {row['Intensite_Conso']:.4f}, {row['Mois']})"
                values_list.append(val)
            
            f.write(",\n".join(values_list))
            f.write(";\n") 

    print(f"\n SUCCÈS TOTAL ! Le fichier '{output_sql}' est généré.")
    print(" Importe-le dans MySQL Workbench (via 'Run SQL Script').")

except Exception as e:

    print(f" Erreur : {e}")
