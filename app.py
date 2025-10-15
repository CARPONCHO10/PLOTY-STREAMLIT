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
DB_NAME = 'usuarios_streamlit.db'
API_URL = 'https://jsonplaceholder.typicode.com/users'

# Sidebar para controles
st.sidebar.header("⚙️ Configuración")

# 1) Consumir la API
st.sidebar.subheader("1. Obtener Datos")
if st.sidebar.button("🔄 Actualizar datos desde API"):
    with st.spinner("Obteniendo datos de la API..."):
        try:
            response = requests.get(API_URL, timeout=20)
            if response.status_code == 200:
                users = response.json()
                st.sidebar.success(f"✅ {len(users)} usuarios obtenidos")
                
                # Guardar en SQLite
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                
                # Reiniciar tabla
                cur.execute('DROP TABLE IF EXISTS users;')
                cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    email TEXT,
                    phone TEXT,
                    website TEXT
                )
                ''')
                
                for u in users:
                    cur.execute('''
                        INSERT OR REPLACE INTO users (id, name, username, email, phone, website)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        u.get('id'), u.get('name'), u.get('username'), 
                        u.get('email'), u.get('phone'), u.get('website')
                    ))
                
                conn.commit()
                conn.close()
                st.success("✅ Datos guardados exitosamente en SQLite")
                
            else:
                st.error(f"❌ Error al consumir la API ({response.status_code})")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# 2) Leer datos de SQLite
st.sidebar.subheader("2. Cargar Datos")
if st.sidebar.button("📂 Cargar desde SQLite"):
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query('SELECT * FROM users', conn)
        conn.close()
        
        if not df.empty:
            # Convertir a tipos compatibles con pandas 2.3.3
            df = df.astype({
                'id': 'int64',
                'name': 'string',
                'username': 'string', 
                'email': 'string',
                'phone': 'string',
                'website': 'string'
            })
            st.session_state.df = df
            st.sidebar.success(f"✅ {len(df)} registros cargados")
        else:
            st.sidebar.warning("⚠️ No hay datos en la base de datos")
    except Exception as e:
        st.sidebar.error(f"❌ Error al cargar datos: {str(e)}")

# Verificar si hay datos cargados
if 'df' not in st.session_state:
    st.info("👈 Usa los controles en la sidebar para cargar los datos primero")
    st.stop()

df = st.session_state.df

# Mostrar datos básicos
st.header("📋 Datos de Usuarios")

col1, col2, col3 = st.columns(3)
col1.metric("Total de Usuarios", len(df))
col2.metric("Columnas", df.shape[1])
col3.metric("Dominios Únicos", df['email'].str.split('@').str[1].nunique())

# Mostrar tabla de datos
with st.expander("📊 Ver tabla de datos completa"):
    st.dataframe(df, use_container_width=True)

# 3) Feature Engineering - Ajustado para pandas 2.3.3
st.header("🔧 Ingeniería de Características")

# Crear columnas adicionales con manejo seguro de tipos
df['name_length'] = df['name'].str.len().fillna(0).astype('int64')
df['email_domain'] = df['email'].str.split('@').str[1].str.lower()

# Mostrar datos con nuevas características
with st.expander("🔍 Ver datos con características adicionales"):
    st.dataframe(df[['id', 'name', 'name_length', 'email', 'email_domain']], use_container_width=True)

# 4) Visualizaciones con Plotly
st.header("📈 Visualizaciones Interactivas")

# Seleccionar tipo de gráfico
chart_type = st.selectbox(
    "Selecciona el tipo de gráfico:",
    ["Histograma", "Barras Horizontales", "Gráfico de Donut", "Tabla Interactiva", "Estadísticas Avanzadas"]
)

# Contenedor para gráficos
chart_container = st.container()

with chart_container:
    if chart_type == "Histograma":
        st.subheader("📊 Distribución de Longitud de Nombres")
        
        # Personalizar histograma
        col1, col2 = st.columns(2)
        with col1:
            nbins = st.slider("Número de bins", min_value=5, max_value=20, value=10)
        with col2:
            color = st.color_picker("Color del histograma", "#636efa")
        
        fig = px.histogram(
            df, 
            x='name_length', 
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
        
        # Estadísticas
        st.write(f"**Estadísticas:**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Mínimo", int(df['name_length'].min()))
        col2.metric("Máximo", int(df['name_length'].max()))
        col3.metric("Promedio", f"{df['name_length'].mean():.1f}")
        col4.metric("Mediana", int(df['name_length'].median()))
    
    elif chart_type == "Barras Horizontales":
        st.subheader("📊 Usuarios por Dominio de Correo")
        
        # Calcular conteos de forma segura
        dom_counts = df['email_domain'].value_counts().reset_index()
        dom_counts.columns = ['email_domain', 'count']
        
        # Personalización
        col1, col2 = st.columns(2)
        with col1:
            sort_order = st.radio("Ordenar por:", ["Cantidad", "Alfabético"])
            if sort_order == "Alfabético":
                dom_counts = dom_counts.sort_values('email_domain')
            else:
                dom_counts = dom_counts.sort_values('count', ascending=True)
        
        with col2:
            bar_color = st.color_picker("Color de barras", "#636efa")
        
        fig = px.bar(
            dom_counts, 
            x='count', 
            y='email_domain', 
            orientation='h',
            title='Usuarios por dominio de correo electrónico',
            color_discrete_sequence=[bar_color]
        )
        fig.update_layout(
            xaxis_title='Cantidad de usuarios',
            yaxis_title='Dominio'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Gráfico de Donut":
        st.subheader("🍩 Distribución de Dominios de Email")
        
        # Calcular conteos
        dom_counts = df['email_domain'].value_counts().reset_index()
        dom_counts.columns = ['email_domain', 'count']
        
        # Personalización
        col1, col2 = st.columns(2)
        with col1:
            hole_size = st.slider("Tamaño del agujero", 0.0, 0.8, 0.4)
        with col2:
            show_values = st.checkbox("Mostrar valores", value=True)
        
        fig = px.pie(
            dom_counts, 
            names='email_domain', 
            values='count', 
            hole=hole_size,
            title='Distribución de dominios de email'
        )
        
        if show_values:
            fig.update_traces(textposition='inside', textinfo='percent+label')
        else:
            fig.update_traces(textposition='inside', textinfo='percent')
            
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Tabla Interactiva":
        st.subheader("📋 Tabla de Usuarios")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            min_length = st.number_input("Longitud mínima del nombre", 
                                       min_value=0, 
                                       max_value=int(df['name_length'].max()), 
                                       value=0)
        with col2:
            selected_domains = st.multiselect(
                "Filtrar por dominio:",
                options=df['email_domain'].unique().tolist(),
                default=df['email_domain'].unique().tolist()
            )
        
        # Aplicar filtros
        filtered_df = df[
            (df['name_length'] >= min_length) & 
            (df['email_domain'].isin(selected_domains))
        ]
        
        st.write(f"**Mostrando {len(filtered_df)} de {len(df)} usuarios**")
        
        # Crear tabla interactiva
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(filtered_df[['id','name','username','email','phone','website']].columns),
                fill_color='lightblue',
                align='left',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=[filtered_df['id'], filtered_df['name'], filtered_df['username'], 
                       filtered_df['email'], filtered_df['phone'], filtered_df['website']],
                align='left',
                font=dict(size=11)
            )
        )])
        fig.update_layout(title='Usuarios (tabla filtrada)', height=400)
        st.plotly_chart(fig, use_container_width=True)
        
    elif chart_type == "Estadísticas Avanzadas":
        st.subheader("📈 Análisis Estadístico Avanzado")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Resumen Estadístico de Longitud de Nombres:**")
            st.dataframe(df['name_length'].describe(), use_container_width=True)
            
        with col2:
            st.write("**Top 5 Nombres Más Largos:**")
            top_long_names = df.nlargest(5, 'name_length')[['name', 'name_length']]
            st.dataframe(top_long_names, use_container_width=True)
        
        # Gráfico de caja
        fig_box = px.box(df, y='name_length', title='Distribución - Diagrama de Caja')
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
    # Exportar estadísticas
    stats_csv = df['name_length'].describe().to_csv()
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

**Fuente de datos:** JSONPlaceholder API
""")

# Footer
st.markdown("---")
st.caption("Desarrollado por Steven Carpio realizado con Streamlit | Compatible con las versiones específicas")