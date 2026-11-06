import streamlit as st
import pandas as pd
import requests
import ssl
from requests.adapters import HTTPAdapter
from datetime import datetime

# ── ADAPTADOR SSL (se mantiene para evitar el error de handshake) ──────────
class CustomSSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ssl_context = ssl.create_default_context()
        ssl_context.set_ciphers('DEFAULT@SECLEVEL=0')
        ssl_context.check_hostname = False
        kwargs["ssl_context"] = ssl_context
        return super().init_poolmanager(*args, **kwargs)

requests.packages.urllib3.disable_warnings()

st.set_page_config(page_title="Consulta minimis - BDNS", page_icon="🔎", layout="wide")
st.title("🔎 Consulta de ayudas de minimis (últimos 3 años)")
st.markdown("Introduce el **CIF/NIF** de la empresa. Se consultará directamente el registro de beneficiario en la BDNS.")

cif = st.text_input("CIF / NIF (ej. B12345678)", max_chars=20).strip().upper()

if st.button("Consultar", type="primary"):
    if not cif:
        st.warning("Por favor, introduce un CIF/NIF válido.")
    else:
        # Usamos el endpoint directo de beneficiario
        url = f"https://www.infosubvenciones.es/bdnstrans/api/concesiones/beneficiario/{cif}"
        
        with st.spinner("Consultando el registro de beneficiario en la BDNS..."):
            try:
                session = requests.Session()
                session.mount('https://', CustomSSLAdapter())
                
                # Hacemos la petición con un timeout más holgado
                response = session.get(url, verify=False, timeout=45)
                
                # Si el servidor responde con error (ej. 404), lo capturamos
                if response.status_code != 200:
                    st.warning(f"La BDNS no ha devuelto datos para el CIF {cif}. Puede que no tenga ayudas registradas o el CIF no sea correcto.")
                    st.stop()
                
                data = response.json()
                # La API puede devolver directamente una lista o un objeto con 'content'
                resultados = data.get("content", []) if isinstance(data, dict) else data

                if not resultados:
                    st.info(f"No se han encontrado concesiones registradas para el CIF {cif}.")
                    st.stop()

                df = pd.DataFrame(resultados)

                # --- Filtro de fecha (últimos 3 años) ---
                # Buscamos la columna de fecha de concesión para filtrar
                col_fecha = next((col for col in df.columns if 'fechaConcesion' in col or 'fecha_concesion' in col.lower()), None)
                
                if col_fecha:
                    # Convertimos a datetime y filtramos
                    df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce', dayfirst=True)
                    fecha_limite = datetime.now() - pd.DateOffset(years=3)
                    df_filtrado = df[df[col_fecha] >= fecha_limite].copy()
                else:
                    # Si no encontramos la columna de fecha, mostramos todo lo que devuelva el beneficiario
                    df_filtrado = df.copy()

                if df_filtrado.empty:
                    st.info(f"El CIF {cif} existe, pero no tiene concesiones en los últimos 3 años.")
                else:
                    # --- Mapeo de columnas para la visualización ---
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

                    st.success(f"Se han encontrado {len(df_mostrar)} ayudas para el CIF {cif} en los últimos 3 años.")
                    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                    
                    csv = df_mostrar.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Descargar CSV", csv, f"minimis_{cif}.csv", "text/csv")

            except requests.exceptions.Timeout:
                st.error("La consulta ha tardado demasiado. El servidor de la BDNS puede estar saturado. Inténtalo de nuevo en unos minutos.")
            except Exception as e:
                st.error(f"Error inesperado: {e}")