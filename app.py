import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ── Configuración de la página ──────────────────────────────────────────────
st.set_page_config(page_title="Consulta minimis - BDNS", page_icon="🔎", layout="wide")

st.title("🔎 Consulta de ayudas de minimis (últimos 3 años)")
st.markdown(
    "Introduce el **CIF/NIF** de la empresa. La herramienta consultará la BDNS "
    "y mostrará las concesiones de **minimis** de los **últimos 3 años**."
)

cif = st.text_input("CIF / NIF (ej. B12345678)", max_chars=20).strip().upper()

if st.button("Consultar", type="primary"):
    if not cif:
        st.warning("Por favor, introduce un CIF/NIF válido.")
    else:
        # 1. Calcular fechas (últimos 3 años)
        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=3*365)
        
        # 2. Endpoint oficial de búsqueda de la BDNS
        url = "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda"
        
        # 3. Configurar la petición
        payload = {
            "nif": cif,
            "fechaDesde": fecha_desde.strftime("%Y-%m-%d"),
            "fechaHasta": fecha_hasta.strftime("%Y-%m-%d"),
            "page": 0,
            "pageSize": 500
        }
        
        with st.spinner("Consultando la BDNS..."):
            try:
                # Hacemos la petición POST a la API
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # 4. Extraer los resultados dependiendo de cómo devuelva el JSON la API
                if isinstance(data, dict) and "content" in data:
                    resultados = data["content"]
                elif isinstance(data, list):
                    resultados = data
                else:
                    resultados = []

                if not resultados:
                    st.info(f"No se han encontrado ayudas de minimis para el CIF {cif} en los últimos 3 años.")
                else:
                    # 5. Convertir a tabla (DataFrame)
                    df = pd.DataFrame(resultados)
                    
                    # 6. Mapear las columnas para que se vean bonitas
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
                    for col in df.columns:
                        for k, v in mapeo.items():
                            if k.lower() in col.lower():
                                columnas_finales[col] = v
                                break
                    
                    if columnas_finales:
                        df_mostrar = df[list(columnas_finales.keys())].rename(columns=columnas_finales)
                    else:
                        df_mostrar = df # Si no encuentra los nombres, muestra todo

                    st.success(f"Se han encontrado {len(df_mostrar)} ayudas para el CIF {cif}.")
                    
                    # 7. Mostrar tabla interactiva
                    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                    
            except Exception as e:
                st.error(f"Error al conectar con la BDNS: {e}")