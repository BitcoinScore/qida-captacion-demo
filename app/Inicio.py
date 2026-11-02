import streamlit as st

import comun

st.set_page_config(page_title="Qida · Captación (concepto)", page_icon=":material/home_health:", layout="wide")
comun.estilo()

paginas = {
    "Lo que ve la familia": [
        st.Page("paginas/web.py", title="Web con asistente de noche", icon=":material/language:"),
    ],
    "Panel del equipo": [
        st.Page("paginas/viaje.py", title="Viaje de la familia", icon=":material/filter_alt:", default=True),
        st.Page("paginas/descubre.py", title="Canales y ciudades", icon=":material/campaign:"),
        st.Page("paginas/primera_llamada.py", title="Cola de llamadas", icon=":material/call:"),
        st.Page("paginas/se_queda.py", title="Retención", icon=":material/favorite:"),
        st.Page("paginas/calidad.py", title="Calidad del asistente", icon=":material/verified:"),
    ],
}
st.navigation(paginas).run()
st.sidebar.caption("Concepto de Máximo Fernández para la entrevista de AI Product Builder. No es una herramienta oficial "
                   "de Qida. Cifras del panel inventadas; marca, servicios y condiciones tomados de qida.es.")
