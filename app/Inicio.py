import streamlit as st

import comun

st.set_page_config(page_title="Qida · Captación (concepto)", page_icon=":material/home_health:", layout="wide")
comun.estilo()

# El orden sigue el recorrido de la demo: medir → lo que ve la familia → la cola → los canales → la calidad.
paginas = {
    "Recorrido": [
        st.Page("paginas/empieza.py", title="Empieza aquí", icon=":material/flag:", default=True),
        st.Page("paginas/viaje.py", title="1 · Viaje de la familia", icon=":material/filter_alt:"),
        st.Page("paginas/web.py", title="2 · Web con asistente de noche", icon=":material/language:"),
        st.Page("paginas/primera_llamada.py", title="3 · Cola de llamadas", icon=":material/call:"),
        st.Page("paginas/descubre.py", title="4 · Canales y ciudades", icon=":material/campaign:"),
        st.Page("paginas/calidad.py", title="5 · Calidad del asistente", icon=":material/verified:"),
    ],
    "Anexo": [
        st.Page("paginas/se_queda.py", title="Retención", icon=":material/favorite:"),
    ],
}
st.navigation(paginas).run()
st.sidebar.caption("Concepto de Máximo Fernández Catalán para la candidatura de AI Product Builder. No es una herramienta "
                   "oficial de Qida. Cifras del panel inventadas; marca, servicios y condiciones tomados de qida.es.")
