import pandas as pd
import plotly.express as px
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import dash_ag_grid as dag

df = pd.read_csv("./data/processed/full_data.csv")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("NJ Transit Bus Stop Accessibility", className="text-center my-4"), width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Label("Select Analysis View:", className="fw-bold"),
            dcc.RadioItems(id='analysis-selector',
                options=[{'label': 'Disability Equity', 'value': 'disability'}, {'label': 'Income Equity', 'value': 'income'}],
                value='disability', inline=True, className="mb-4"
            ),
            html.H4(id='table-title', className="text-center"),
            dag.AgGrid(id='top-stops-table',
                columnDefs=[{"field": "Bus Stop", "flex": 2}, {"field": "Isolation Index", "width": 150, "flex": 1}],
                style={"height": "45vh"}, 
            ),
            html.H4("Group Analysis Summary", className="text-center mt-4"),
            dbc.Row([
                dbc.Col(dbc.Card(id='high-group-card', color="light"), md=6),
                dbc.Col(dbc.Card(id='low-group-card', color="light"), md=6)
            ])

        ], md=4),

        dbc.Col([
            dcc.Graph(id='accessibility-map', style={'height': '80vh'})
        ], md=8)
    ])
], fluid=True, style={'backgroundColor': "#F8FFF8"}) 

@app.callback(
    [Output('accessibility-map', 'figure'),
     Output('top-stops-table', 'rowData'),
     Output('table-title', 'children'),
     Output('high-group-card', 'children'), 
     Output('low-group-card', 'children')], 
    [Input('analysis-selector', 'value')]
)
def update_visuals(analysis_type):
    if analysis_type == 'disability':
        group_col = 'disability_group'
        hover_col = 'disability_percentage'
        hover_col_name = 'Neighborhood Disability %'
    else:
        group_col = 'income_group'
        hover_col = 'median_income'
        hover_col_name = 'Neighborhood Median Income'

    filtered_df = df[df[group_col].isin(['High', 'Low'])].copy()

    map_fig = px.scatter_mapbox(
        filtered_df, lat="latitude", lon="longitude", color="isolation_index", size="reachable_area",
        hover_name="stop_name", custom_data=['reachable_area', 'latitude', 'longitude', group_col, hover_col, 'isolation_index'],
        color_continuous_scale=px.colors.sequential.Viridis_r, mapbox_style="carto-positron", zoom=7,
        center={"lat": 40.4, "lon": -74.4}, labels={"isolation_index": "Isolation Index"}
    )
    if analysis_type == 'disability':
        hover_format = hover_col_name + """: %{customdata[4]:.2f}%"""
    else:
        hover_format = hover_col_name + """: $%{customdata[4]:,.0f}"""
    hovertemplate = "<b>%{hovertext}</b><br><br>Reachable Area: %{customdata[0]:,.0f} m²<br>Latitude: %{customdata[1]:.5f}<br>Longitude: %{customdata[2]:.5f}<br>Analysis Group: %{customdata[3]}<br>" + hover_format + "<br>Isolation Index: %{customdata[5]:.2f}"
    map_fig.update_traces(hovertemplate=hovertemplate)
    map_fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    if analysis_type == 'disability':
        worst_group_df = filtered_df[filtered_df[group_col] == 'High']
        table_title_text = "Most Isolated Stops (High Disability Areas)"
    else:
        worst_group_df = filtered_df[filtered_df[group_col] == 'Low']
        table_title_text = "Most Isolated Stops (Low Income Areas)"
    top_20_worst = worst_group_df.nsmallest(20, 'isolation_index')
    table_data = top_20_worst[['stop_name', 'isolation_index']].rename(columns={'stop_name': 'Bus Stop', 'isolation_index': 'Isolation Index'})
    table_data['Isolation Index'] = table_data['Isolation Index'].round(3)
    table_data_dict = table_data.to_dict('records')

    high_group_df = filtered_df[filtered_df[group_col] == 'High']
    low_group_df = filtered_df[filtered_df[group_col] == 'Low']
    
    high_card_content = [
        dbc.CardHeader("High Group Stats"),
        dbc.CardBody([
            html.P(f"Avg. Isolation Index: {high_group_df['isolation_index'].mean():.3f}"),
            html.P(f"Avg. Reachable Area: {high_group_df['reachable_area'].mean():,.0f} m²"),
        ])
    ]
    low_card_content = [
        dbc.CardHeader("Low Group Stats"),
        dbc.CardBody([
            html.P(f"Avg. Isolation Index: {low_group_df['isolation_index'].mean():.3f}"),
            html.P(f"Avg. Reachable Area: {low_group_df['reachable_area'].mean():,.0f} m²"),
        ])
    ]

    return map_fig, table_data_dict, table_title_text, high_card_content, low_card_content

if __name__ == '__main__':
    app.run(debug=False)