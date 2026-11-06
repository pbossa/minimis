import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from bdns.fetch.client import BDNSClient

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
        # 1. Calcular fechas (últimos 3 años desde hoy)
        fecha_hasta = datetime.now().date()
        fecha_desde = fecha_hasta - timedelta(days=3*365)

        with st.spinner("Descargando y filtrando datos de la BDNS (esto puede tardar unos segundos)..."):
            try:
                # 2. Conectar con la API de la BDNS usando la librería oficial
                client = BDNSClient()
                
                # 3. Descargar concesiones del periodo.
                # Nota: Limitamos a 100 páginas de 1000 registros (100.000 concesiones) 
                # para evitar bloqueos por exceso de datos. Si una empresa tiene muchísimas 
                # ayudas, se podría ampliar este número.
                resultados = client.fetch_concesiones_busqueda(
                    fechaDesde=fecha_desde.strftime("%Y-%m-%d"),
                    fechaHasta=fecha_hasta.strftime("%Y-%m-%d"),
                    pageSize=1000,
                    num_pages=100 
                )

                if not resultados:
                    st.info(f"No se han encontrado concesiones en el periodo para el CIF {cif}.")
                    st.stop()

                # 4. Convertir a tabla
                df = pd.DataFrame(resultados)

                # 5. Filtrar por el CIF introducido (la API no lo hace en el servidor)
                # Buscamos la columna que contiene el NIF del beneficiario.
                col_cif = next((col for col in df.columns if 'nif' in col.lower() or 'beneficiario' in col.lower()), None)
                
                if col_cif:
                    # Filtramos comparando el texto en mayúsculas
                    df_filtrado = df[df[col_cif].astype(str).str.upper() == cif].copy()
                else:
                    st.error("No se ha podido identificar la columna del CIF en los datos descargados.")
                    st.stop()

                if df_filtrado.empty:
                    st.info(f"No se han encontrado ayudas de minimis para el CIF {cif} en los últimos 3 años.")
                else:
                    # 6. Mapear y renombrar las columnas para que se vean claras
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
                    
                    if columnas_finales:
                        df_mostrar = df_filtrado[list(columnas_finales.keys())].rename(columns=columnas_finales)
                    else:
                        df_mostrar = df_filtrado # Si no encuentra los nombres exactos, muestra todo

                    st.success(f"Se han encontrado {len(df_mostrar)} ayudas para el CIF {cif}.")
                    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                    
                    # Botón de descarga opcional
                    csv = df_mostrar.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Descargar CSV", csv, f"minimis_{cif}.csv", "text/csv")

            except Exception as e:
                st.error(f"Error al conectar con la BDNS: {e}")