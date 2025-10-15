# app.py
import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Usuarios API",
    page_icon="📊",
    layout="wide"
)

# Título principal
st.title("📊 Análisis de Usuarios: API → SQLite → Plotly")
st.markdown("---")

# Configuración
NOMBRE_BD = 'usuarios_streamlit.db'
URL_API = 'https://jsonplaceholder.typicode.com/users'

# Barra lateral para controles
st.sidebar.header("⚙️ Configuración")

# 1) Consumir la API
st.sidebar.subheader("1. Obtener Datos")
if st.sidebar.button("🔄 Actualizar datos desde la API"):
    with st.spinner("Obteniendo datos desde la API..."):
        try:
            respuesta = requests.get(URL_API, timeout=20)
            if respuesta.status_code == 200:
                usuarios = respuesta.json()
                st.sidebar.success(f"✅ {len(usuarios)} usuarios obtenidos correctamente")
                
                # Guardar en SQLite
                conexion = sqlite3.connect(NOMBRE_BD)
                cursor = conexion.cursor()
                
                # Reiniciar tabla
                cursor.execute('DROP TABLE IF EXISTS usuarios;')
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT,
                    usuario TEXT,
                    correo TEXT,
                    telefono TEXT,
                    sitio_web TEXT
                )
                ''')
                
                for u in usuarios:
                    cursor.execute('''
                        INSERT OR REPLACE INTO usuarios (id, nombre, usuario, correo, telefono, sitio_web)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        u.get('id'), u.get('name'), u.get('username'), 
                        u.get('email'), u.get('phone'), u.get('website')
                    ))
                
                conexion.commit()
                conexion.close()
                st.success("✅ Datos guardados exitosamente en SQLite")
                
            else:
                st.error(f"❌ Error al consumir la API ({respuesta.status_code})")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# 2) Leer datos de SQLite
st.sidebar.subheader("2. Cargar Datos")
if st.sidebar.button("📂 Cargar desde SQLite"):
    try:
        conexion = sqlite3.connect(NOMBRE_BD)
        df = pd.read_sql_query('SELECT * FROM usuarios', conexion)
        conexion.close()
        
        if not df.empty:
            # Convertir tipos de datos compatibles
            df = df.astype({
                'id': 'int64',
                'nombre': 'string',
                'usuario': 'string', 
                'correo': 'string',
                'telefono': 'string',
                'sitio_web': 'string'
            })
            st.session_state.df = df
            st.sidebar.success(f"✅ {len(df)} registros cargados correctamente")
        else:
            st.sidebar.warning("⚠️ No hay datos en la base de datos")
    except Exception as e:
        st.sidebar.error(f"❌ Error al cargar datos: {str(e)}")

# Verificar si hay datos cargados
if 'df' not in st.session_state:
    st.info("👈 Usa los controles en la barra lateral para cargar los datos primero")
    st.stop()

df = st.session_state.df

# Mostrar datos básicos
st.header("📋 Datos de Usuarios")

col1, col2, col3 = st.columns(3)
col1.metric("Total de Usuarios", len(df))
col2.metric("Columnas", df.shape[1])
col3.metric("Dominios Únicos", df['correo'].str.split('@').str[1].nunique())

# Mostrar tabla de datos
with st.expander("📊 Ver tabla de datos completa"):
    st.dataframe(df, use_container_width=True)

# 3) Ingeniería de características
st.header("🔧 Ingeniería de Características")

# Crear columnas adicionales
df['longitud_nombre'] = df['nombre'].str.len().fillna(0).astype('int64')
df['dominio_correo'] = df['correo'].str.split('@').str[1].str.lower()

# Mostrar datos con nuevas características
with st.expander("🔍 Ver datos con características adicionales"):
    st.dataframe(df[['id', 'nombre', 'longitud_nombre', 'correo', 'dominio_correo']], use_container_width=True)

# 4) Visualizaciones con Plotly
st.header("📈 Visualizaciones Interactivas")

# Seleccionar tipo de gráfico
tipo_grafico = st.selectbox(
    "Selecciona el tipo de gráfico:",
    ["Histograma", "Barras Horizontales", "Gráfico de Dona", "Tabla Interactiva", "Estadísticas Avanzadas"]
)

# Contenedor para gráficos
contenedor_graficos = st.container()

with contenedor_graficos:
    if tipo_grafico == "Histograma":
        st.subheader("📊 Distribución de Longitud de Nombres")
        
        col1, col2 = st.columns(2)
        with col1:
            nbins = st.slider("Número de barras", min_value=5, max_value=20, value=10)
        with col2:
            color = st.color_picker("Color del histograma", "#636efa")
        
        fig = px.histogram(
            df, 
            x='longitud_nombre', 
            nbins=nbins,
            title='Distribución de caracteres en los nombres',
            color_discrete_sequence=[color]
        )
        fig.update_layout(
            xaxis_title='Cantidad de caracteres',
            yaxis_title='Frecuencia',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("**Estadísticas:**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Mínimo", int(df['longitud_nombre'].min()))
        col2.metric("Máximo", int(df['longitud_nombre'].max()))
        col3.metric("Promedio", f"{df['longitud_nombre'].mean():.1f}")
        col4.metric("Mediana", int(df['longitud_nombre'].median()))
    
    elif tipo_grafico == "Barras Horizontales":
        st.subheader("📊 Usuarios por Dominio de Correo")
        
        dom_counts = df['dominio_correo'].value_counts().reset_index()
        dom_counts.columns = ['dominio_correo', 'cantidad']
        
        col1, col2 = st.columns(2)
        with col1:
            orden = st.radio("Ordenar por:", ["Cantidad", "Alfabético"])
            if orden == "Alfabético":
                dom_counts = dom_counts.sort_values('dominio_correo')
            else:
                dom_counts = dom_counts.sort_values('cantidad', ascending=True)
        
        with col2:
            color_barras = st.color_picker("Color de barras", "#636efa")
        
        fig = px.bar(
            dom_counts, 
            x='cantidad', 
            y='dominio_correo', 
            orientation='h',
            title='Usuarios por dominio de correo electrónico',
            color_discrete_sequence=[color_barras]
        )
        fig.update_layout(
            xaxis_title='Cantidad de usuarios',
            yaxis_title='Dominio'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif tipo_grafico == "Gráfico de Dona":
        st.subheader("🍩 Distribución de Dominios de Correo")
        
        dom_counts = df['dominio_correo'].value_counts().reset_index()
        dom_counts.columns = ['dominio_correo', 'cantidad']
        
        col1, col2 = st.columns(2)
        with col1:
            tam_agujero = st.slider("Tamaño del agujero", 0.0, 0.8, 0.4)
        with col2:
            mostrar_valores = st.checkbox("Mostrar valores", value=True)
        
        fig = px.pie(
            dom_counts, 
            names='dominio_correo', 
            values='cantidad', 
            hole=tam_agujero,
            title='Distribución de dominios de correo'
        )
        
        if mostrar_valores:
            fig.update_traces(textposition='inside', textinfo='percent+label')
        else:
            fig.update_traces(textposition='inside', textinfo='percent')
            
        st.plotly_chart(fig, use_container_width=True)
    
    elif tipo_grafico == "Tabla Interactiva":
        st.subheader("📋 Tabla de Usuarios")
        
        col1, col2 = st.columns(2)
        with col1:
            min_longitud = st.number_input("Longitud mínima del nombre", 
                                       min_value=0, 
                                       max_value=int(df['longitud_nombre'].max()), 
                                       value=0)
        with col2:
            dominios_seleccionados = st.multiselect(
                "Filtrar por dominio:",
                options=df['dominio_correo'].unique().tolist(),
                default=df['dominio_correo'].unique().tolist()
            )
        
        filtrado = df[
            (df['longitud_nombre'] >= min_longitud) & 
            (df['dominio_correo'].isin(dominios_seleccionados))
        ]
        
        st.write(f"**Mostrando {len(filtrado)} de {len(df)} usuarios**")
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(filtrado[['id','nombre','usuario','correo','telefono','sitio_web']].columns),
                fill_color='lightblue',
                align='left',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=[filtrado['id'], filtrado['nombre'], filtrado['usuario'], 
                       filtrado['correo'], filtrado['telefono'], filtrado['sitio_web']],
                align='left',
                font=dict(size=11)
            )
        )])
        fig.update_layout(title='Usuarios (tabla filtrada)', height=400)
        st.plotly_chart(fig, use_container_width=True)
        
    elif tipo_grafico == "Estadísticas Avanzadas":
        st.subheader("📈 Análisis Estadístico Avanzado")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Resumen Estadístico de Longitud de Nombres:**")
            st.dataframe(df['longitud_nombre'].describe(), use_container_width=True)
            
        with col2:
            st.write("**Top 5 Nombres Más Largos:**")
            top_long = df.nlargest(5, 'longitud_nombre')[['nombre', 'longitud_nombre']]
            st.dataframe(top_long, use_container_width=True)
        
        fig_box = px.box(df, y='longitud_nombre', title='Distribución - Diagrama de Caja')
        st.plotly_chart(fig_box, use_container_width=True)

# 5) Exportar datos
st.header("💾 Exportar Datos")

col1, col2, col3 = st.columns(3)

with col1:
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name="usuarios.csv",
        mime="text/csv"
    )

with col2:
    stats_csv = df['longitud_nombre'].describe().to_csv()
    st.download_button(
        label="📊 Descargar Estadísticas",
        data=stats_csv,
        file_name="estadisticas_usuarios.csv",
        mime="text/csv"
    )

with col3:
    if st.button("🗑️ Limpiar Datos"):
        if 'df' in st.session_state:
            del st.session_state.df
        st.rerun()

# Información adicional
st.sidebar.markdown("---")
st.sidebar.header("ℹ️ Información")
st.sidebar.info("""
**Versiones compatibles:**
- Streamlit 1.50.0 ✅
- Pandas 2.3.3 ✅  
- Numpy 2.3.3 ✅
- Plotly 5.17.0+ ✅

**Fuente de datos:** API JSONPlaceholder
""")

# Pie de página
st.markdown("---")
st.caption("Desarrollado por Steven Carpio | Realizado con Streamlit | Totalmente en Español 🇪🇨")
