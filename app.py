import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import urllib3

# Desactiva las advertencias de SSL para mantener la consola limpia
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Consulta minimis - BDNS", page_icon="🔎", layout="wide")
st.title("🔎 Consulta de ayudas de minimis (últimos 3 años)")
st.markdown("Introduce el **CIF/NIF** de la empresa. La herramienta consultará la BDNS y mostrará las concesiones de **minimis** de los **últimos 3 años**.")

cif = st.text_input("CIF / NIF (ej. B12345678)", max_chars=20).strip().upper()

if st.button("Consultar", type="primary"):
    if not cif:
        st.warning("Por favor, introduce un CIF/NIF válido.")
    else:
        fecha_hasta = datetime.now().date()
        fecha_desde = fecha_hasta - timedelta(days=3*365)
        
        # Endpoint oficial de búsqueda de concesiones
        url = "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda"
        
        # Parámetros de la petición GET (formato de fecha aceptado por la API: dd/MM/yyyy)
        params = {
            "fechaDesde": fecha_desde.strftime("%d/%m/%Y"),
            "fechaHasta": fecha_hasta.strftime("%d/%m/%Y"),
            "pageSize": 1000,
            "page": 0
        }

        with st.spinner("Consultando la BDNS..."):
            try:
                # Petición con verify=False para evitar el SSLError de Streamlit Cloud
                response = requests.get(url, params=params, verify=False, timeout=30)
                response.raise_for_status()
                data = response.json()

                # La API suele devolver un diccionario con la clave "content"
                resultados = data.get("content", []) if isinstance(data, dict) else data

                if not resultados:
                    st.info(f"No se han encontrado concesiones en el periodo para el CIF {cif}.")
                    st.stop()

                df = pd.DataFrame(resultados)

                # Filtramos por CIF en el cliente (por si la API no lo hace en el servidor)
                col_cif = next((col for col in df.columns if 'nif' in col.lower() or 'beneficiario' in col.lower()), None)
                
                if col_cif:
                    df_filtrado = df[df[col_cif].astype(str).str.upper().str.contains(cif, na=False)].copy()
                else:
                    st.error("No se ha podido identificar la columna del CIF en los datos descargados.")
                    st.stop()

                if df_filtrado.empty:
                    st.info(f"No se han encontrado ayudas de minimis para el CIF {cif} en los últimos 3 años.")
                else:
                    # Mapeo de columnas
                    mapeo = {
                        "fechaConcesion": "Fecha concesión",
                        "importeSubvencion": "SBE (€)",
                        "importe": "SBE (€)",
                        "convocatoria": "Convocatoria",
                        "organo": "Organismo",
                        "fechaPublicacion": "Fecha publicación",
                        "fechaFinPlazo": "Fecha cierre plazo"
                    }
                    
                    columnas_finales = {}
                    for col in df_filtrado.columns:
                        for k, v in mapeo.items():
                            if k.lower() in col.lower():
                                columnas_finales[col] = v
                                break
                    
                    df_mostrar = df_filtrado[list(columnas_finales.keys())].rename(columns=columnas_finales) if columnas_finales else df_filtrado

                    st.success(f"Se han encontrado {len(df_mostrar)} ayudas para el CIF {cif}.")
                    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                    
                    csv = df_mostrar.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Descargar CSV", csv, f"minimis_{cif}.csv", "text/csv")

            except Exception as e:
                st.error(f"Error al conectar con la BDNS: {e}")