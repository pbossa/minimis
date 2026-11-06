import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from bdns.fetch.client import BDNSClient
import ssl
import urllib3

# ── PARCHE PARA EL ERROR SSL ───────────────────────────────────────────────
# Desactiva la verificación de certificados para evitar el SSLError en Streamlit Cloud
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# ───────────────────────────────────────────────────────────────────────────

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
        fecha_hasta = datetime.now().date()
        fecha_desde = fecha_hasta - timedelta(days=3*365)

        with st.spinner("Descargando y filtrando datos de la BDNS..."):
            try:
                client = BDNSClient()
                
                resultados = client.fetch_concesiones_busqueda(
                    fechaDesde=fecha_desde,
                    fechaHasta=fecha_hasta,
                    pageSize=1000,
                    num_pages=100 
                )

                if not resultados:
                    st.info(f"No se han encontrado concesiones en el periodo para el CIF {cif}.")
                    st.stop()

                df = pd.DataFrame(resultados)
                col_cif = next((col for col in df.columns if 'nif' in col.lower() or 'beneficiario' in col.lower()), None)
                
                if col_cif:
                    df_filtrado = df[df[col_cif].astype(str).str.upper() == cif].copy()
                else:
                    st.error("No se ha podido identificar la columna del CIF en los datos descargados.")
                    st.stop()

                if df_filtrado.empty:
                    st.info(f"No se han encontrado ayudas de minimis para el CIF {cif} en los últimos 3 años.")
                else:
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