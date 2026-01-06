import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
import os

# --- Configuration ---
st.set_page_config(
    page_title="Monitor de Eficiência - Educação Infantil",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Constants & Paths ---
DATA_PATH = 'tabela.csv'
GEOJSON_PATH = 'ceara.json'

# --- Data Loading ---
@st.cache_data
def load_data():
    try:
        if not os.path.exists(DATA_PATH):
            st.error(f"Arquivo não encontrado: {DATA_PATH}")
            return None
        df = pd.read_csv(DATA_PATH)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

@st.cache_data
def load_geojson():
    try:
        if not os.path.exists(GEOJSON_PATH):
            st.error(f"Arquivo não encontrado: {GEOJSON_PATH}")
            return None
        with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
        for feature in geojson['features']:
             if 'id' in feature['properties']:
                 original_id = str(feature['properties']['id'])
                 feature['id'] = original_id[:6]
        return geojson
    except Exception as e:
        st.error(f"Erro ao carregar GeoJSON: {e}")
        return None

# --- Helper for Plots (Adaptive Theme) ---
def update_fig_layout(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif"),
        modebar=dict(bgcolor='rgba(0,0,0,0)', color='#a3a3a3'),
        margin=dict(t=30, l=10, r=10, b=10),
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    return fig

# --- Processing Functions ---
def process_kpis(df):
    avg = df[df['ano'] == 2019]['tae_creche_capped'].mean()
    below = (df[df['ano'] == 2019]['tae_creche_capped'] < 50).sum()
    return avg, below

def get_event_study_fig(df):
    trend = df.groupby(['ano', 'grupo_renda'])['log_emp_mulher'].mean().unstack()
    trend['gap'] = trend['Maior Dinamismo Econômico'] - trend['Menor Dinamismo Econômico']
    base_gap = trend.loc[2012, 'gap']
    trend['normalized_gap'] = trend['gap'] - base_gap
    
    colors = ['#94a3b8' if x <= 2012 else '#1e3a8a' for x in trend.index]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=trend.index,
        y=trend['normalized_gap'],
        name='Diferencial',
        marker_color=colors,
        hovertemplate='<b>%{x}</b><br>Gap: %{y:.3f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=trend.index,
        y=trend['normalized_gap'],
        mode='lines',
        line=dict(color='gray', width=2, dash='dot'),
        name='Tendência'
    ))
    
    fig.add_shape(type="line", x0=2012, x1=2012, y0=-0.2, y1=0.2, 
                  line=dict(color="gray", width=1, dash="dash"))
    
    fig.update_layout(
        title="Event Study: Abertura do Gap",
        legend=dict(orientation='h', y=1.1, x=0.5, xanchor='center'),
        height=350
    )
    return update_fig_layout(fig)

def get_map_fig(df, geojson):
    df_2007 = df[df['ano'] == 2007].set_index('id_municipio_6')
    df_2019 = df[df['ano'] == 2019].set_index('id_municipio_6')
    common = df_2019.index.intersection(df_2007.index)
    
    expansion = df_2019.loc[common, 'tae_creche_capped'] - df_2007.loc[common, 'tae_creche_capped']
    names = df_2019.loc[common, 'nome_municipio']
    ids = common.astype(str).tolist()
    
    custom_scale = [
        [0.0, 'rgb(202,0,32)'],
        [0.5, 'rgb(247,247,247)'],
        [1.0, 'rgb(5,113,176)']
    ]
    
    fig = go.Figure(go.Choropleth(
        geojson=geojson,
        locations=ids,
        z=expansion,
        text=names,
        colorscale=custom_scale,
        autocolorscale=False,
        marker_line_color='white',
        marker_line_width=0.5,
        colorbar=dict(title="pp", thickness=10, len=0.8),
        hovertemplate='<b>%{text}</b><br>Expansão: %{z:.1f} pp<extra></extra>'
    ))
    
    fig.update_layout(
        title="Expansão (Mapa)",
        geo=dict(fitbounds="locations", visible=False, bgcolor='rgba(0,0,0,0)'),
        margin=dict(t=30, l=0, r=0, b=0),
        height=400
    )
    return update_fig_layout(fig)

def get_scatter_fig(df):
    df_2007 = df[df['ano'] == 2007].set_index('id_municipio_6')
    df_2019 = df[df['ano'] == 2019].set_index('id_municipio_6')
    common = df_2019.index.intersection(df_2007.index)
    
    x = (df_2019.loc[common, 'tae_creche_capped'] - df_2007.loc[common, 'tae_creche_capped'])
    y = ((df_2019.loc[common, 'Total_mulheres'] - df_2007.loc[common, 'Total_mulheres']) / df_2007.loc[common, 'Total_mulheres']) * 100
    names = df_2019.loc[common, 'nome_municipio']
    groups = df_2019.loc[common, 'grupo_renda']
    
    temp = pd.DataFrame({'x': x, 'y': y, 'name': names, 'group': groups})
    
    fig = px.scatter(temp, x='x', y='y', color='group', hover_name='name',
                     color_discrete_map={'Maior Dinamismo Econômico': '#1e3a8a', 'Menor Dinamismo Econômico': '#94a3b8'},
                     labels={'x': 'Expansão (pp)', 'y': 'Crescimento (%)'})
    
    fig.update_traces(marker=dict(size=10, opacity=0.8, line=dict(width=0)))
    fig.update_layout(
        title="Expansão vs Emprego",
        legend=dict(orientation='h', y=-0.2),
        height=400
    )
    return update_fig_layout(fig)

def get_top5_fig(df):
    df_2007 = df[df['ano'] == 2007].set_index('id_municipio_6')
    df_2019 = df[df['ano'] == 2019].set_index('id_municipio_6')
    common = df_2019.index.intersection(df_2007.index)
    
    growth = ((df_2019.loc[common, 'Total_mulheres'] - df_2007.loc[common, 'Total_mulheres']) / df_2007.loc[common, 'Total_mulheres']) * 100
    names = df_2019.loc[common, 'nome_municipio']
    
    temp = pd.DataFrame({'growth': growth, 'name': names})
    top5 = temp.nlargest(5, 'growth').sort_values('growth', ascending=True)
    
    colors = ['#1e3a8a' if n == 'Quixeramobim' else '#cbd5e1' for n in top5['name']]
    
    fig = go.Figure(go.Bar(
        x=top5['growth'],
        y=top5['name'],
        orientation='h',
        marker_color=colors,
        text=top5['growth'].apply(lambda x: f"{x:.1f}%"),
        textposition='auto'
    ))
    
    fig.update_layout(
        title="Top 5 Performers",
        height=400,
        margin=dict(l=100)
    )
    return update_fig_layout(fig)

def get_table_df(df):
    df_2007 = df[df['ano'] == 2007].set_index('id_municipio_6')
    df_2019 = df[df['ano'] == 2019].set_index('id_municipio_6')
    common = df_2019.index.intersection(df_2007.index)
    
    data = []
    for idx in common:
        row = {}
        row['Município'] = df_2019.loc[idx, 'nome_municipio']
        row['Grupo'] = df_2019.loc[idx, 'grupo_renda']
        row['Cobertura (2019)'] = round(df_2019.loc[idx, 'tae_creche_capped'], 1)
        row['Meta'] = "Sim" if row['Cobertura (2019)'] >= 50 else "Não"
        row['Expansão'] = round(df_2019.loc[idx, 'tae_creche_capped'] - df_2007.loc[idx, 'tae_creche_capped'], 1)
        g = ((df_2019.loc[idx, 'Total_mulheres'] - df_2007.loc[idx, 'Total_mulheres']) / df_2007.loc[idx, 'Total_mulheres']) * 100
        row['Crescimento'] = round(g, 1)
        data.append(row)
    return pd.DataFrame(data)

# --- Main App Layout ---

def main():
    # CSS Injection for Typography & Mobile Layout
    st.markdown("""
    <style>
        /* Typography - Bold Metrics */
        .metric-val {
            font-size: 2.5rem;
            font-weight: 800 !important; /* Bold */
            color: #1e3a8a; /* Blue for visibility */
            line-height: 1.2;
        }
        .metric-lbl {
            font-size: 0.85rem;
            font-weight: 700 !important; /* Bold */
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        /* Dark Mode Adjustments */
        @media (prefers-color-scheme: dark) {
            .metric-val { color: #f8fafc; }
            .metric-lbl { color: #94a3b8; }
        }

        /* Responsive Metric Grid - Forces horizontal layout on mobile */
        .metric-container {
            display: flex;
            flex-direction: row;
            justify-content: space-between;
            gap: 15px;
            width: 100%;
            overflow-x: auto; /* Allow horizontal scroll if needed */
            padding-bottom: 10px;
        }
        .metric-box {
            flex: 1;
            min-width: 120px; /* Prevent squishing too much */
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(128,128,128,0.2);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header
    # Header
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>Monitor de Eficiência (0 a 3 anos)</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #64748b;'>Educação Infantil | Ceará</h3>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; color: #475569; margin-bottom: 20px; font-size: 1.1em;'>
        Este painel apresenta indicadores de acesso e qualidade da educação infantil nos municípios cearenses, 
        destacando a evolução da cobertura de creches, o cumprimento de metas e o impacto na empregabilidade feminina.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    df = load_data()
    geojson = load_geojson()
    
    if df is not None and geojson is not None:
        
        # KPIs
        avg, below = process_kpis(df)
        
        # Custom HTML Component for Mobile-Friendly Row
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-box">
                <div class="metric-val">{avg:.1f}%</div>
                <div class="metric-lbl">Cobertura Média</div>
            </div>
            <div class="metric-box">
                <div class="metric-val" style="color:#ef4444">{below}</div>
                <div class="metric-lbl">Abaixo da Meta</div>
            </div>
            <div class="metric-box">
                <div class="metric-val">+42.5%</div>
                <div class="metric-lbl">Diferencial de Impacto</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Row 2
        col_map, col_study = st.columns(2)
        with col_map:
            st.plotly_chart(get_map_fig(df, geojson), use_container_width=True)
        with col_study:
            st.plotly_chart(get_event_study_fig(df), use_container_width=True)
            
        # Row 3
        col_scatter, col_top5 = st.columns([2, 1])
        with col_scatter:
            st.plotly_chart(get_scatter_fig(df), use_container_width=True)
        with col_top5:
            st.plotly_chart(get_top5_fig(df), use_container_width=True)
            
        # Row 4: Data Table
        st.subheader("Tabela de Municípios Detalhada")
        
        table_df = get_table_df(df)
        
        st.dataframe(
            table_df,
            column_config={
                "Cobertura (2019)": st.column_config.ProgressColumn(
                    "Cobertura (2019)",
                    format="%f%%",
                    min_value=0,
                    max_value=100,
                ),
            },
            hide_index=True,
            use_container_width=True
        )

if __name__ == "__main__":
    main()
