import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, dash_table, Input, Output, callback

# ── Load & classify data ──────────────────────────────────────────────────────
raw = json.loads((Path(__file__).parent / 'venues_enriched2.json').read_text(encoding='utf-8'))

# Refine type: name-keyword override on top of Google broad type
TYPE_RULES = [
    (['sushi', 'ramen', 'noodle', 'tokyo', 'bushido', 'ruixian', 'japanese', 'yakumanka', 'umashu', 'ryu'], 'Japanese'),
    (['ceviche', 'nikkei', 'peruv', 'chifa', 'sr. ceviche', 'xolo', 'acurio', 'peru'],   'South American'),
    (['taqueria', 'mexican', 'mexico', 'burrito', 'tierra burrito'],                       'Mexican'),
    (['thai', 'khao'],                                                                      'Thai'),
    (['poke'],                                                                              'Poke Bowl'),
    (['smash', 'burger', 'nina burger'],                                                   'Burger Bar'),
    (['brunch', 'billy brunch', 'wake coffee', 'fem un brunch'],                          'Brunch Spot'),
    (['rooftop', 'roof top', 'sky bar', 'terraza verbena', 'azimuth'],                    'Rooftop Bar'),
    (['cocktail', 'rouge cocktail', 'xolo nikkei'],                                       'Cocktail Bar'),
    (['tapas', 'tapes', 'vermut', 'bodega', 'bodegueta', 'tasca', '4 latas', 'bormuth'],  'Tapas / Vermut'),
    (['pastiss', 'browneria', 'iaia', 'zentral', 'carrot caf'],                           'Café / Bakery'),
    (['coffee', 'brew', 'cober coffee'],                                                   'Coffee Shop'),
    (['surf house', 'beach', 'chiringuito', 'xiringuito'],                                'Beach Bar'),
    (['pub crawl', 'night_club'],                                                           'Club / Pub'),
    (['acai', 'healthy', 'quinoa', 'honest green', 'green leka'],                         'Healthy'),
    (['argentinas', 'argentina', 'bondi'],                                                 'Argentinian'),
]

def classify(name: str, google_types: list) -> str:
    n = name.lower()
    gt = ' '.join(google_types)
    for keywords, label in TYPE_RULES:
        if any(kw in n or kw in gt for kw in keywords):
            return label
    # Fall back to broad Google type
    if 'cafe' in google_types:       return 'Café / Bakery'
    if 'bakery' in google_types:     return 'Café / Bakery'
    if 'night_club' in google_types: return 'Club / Pub'
    if 'bar' in google_types:        return 'Bar'
    if 'restaurant' in google_types: return 'Restaurant'
    return 'Other'

for v in raw:
    v['type'] = classify(v['name'], v.get('google_types', []))

df = pd.DataFrame(raw)
df['rating']   = pd.to_numeric(df['rating'],   errors='coerce')
df['n_ratings']= pd.to_numeric(df['n_ratings'],errors='coerce')
df['price_num']= pd.to_numeric(df['price_num'],errors='coerce')

PRICE_ORDER  = ['€', '€€', '€€€', '€€€€']
PRICE_LABELS = {'€': 'Budget (€)', '€€': 'Mid-range (€€)', '€€€': 'Upscale (€€€)', '€€€€': 'Fine dining (€€€€)'}
total = len(df)

# ── Colours ───────────────────────────────────────────────────────────────────
BG, CARD, CARD2 = '#0f1117', '#1a1d27', '#21263a'
BORDER, TEXT, MUTED = '#2d3348', '#e2e8f0', '#8892a4'
ACCENT, ACCENT2, ACCENT3 = '#e8614a', '#f0a500', '#4aa8e8'

TYPE_COLORS = {
    'Bar':            '#4aa8e8', 'Restaurant':    '#e8614a',
    'Tapas / Vermut': '#f0a500', 'Café / Bakery': '#34d399',
    'Cocktail Bar':   '#a78bfa', 'Japanese':      '#f472b6',
    'South American': '#fb923c', 'Brunch Spot':   '#60a5fa',
    'Mexican':        '#facc15', 'Healthy':       '#4ade80',
    'Burger Bar':     '#c084fc', 'Poke Bowl':     '#67e8f9',
    'Thai':           '#86efac', 'Coffee Shop':   '#fbbf24',
    'Argentinian':    '#f87171', 'Beach Bar':     '#38bdf8',
    'Rooftop Bar':    '#818cf8', 'Club / Pub':    '#fb7185',
    'Other':          '#475569',
}

def chart_style(height=None, margin=None):
    d = dict(paper_bgcolor=CARD, plot_bgcolor=CARD,
             font=dict(color=TEXT, family="'Segoe UI',system-ui,sans-serif"),
             margin=margin or dict(t=15, b=20, l=15, r=30))
    if height: d['height'] = height
    return d

# ── Fig 1: Type treemap ───────────────────────────────────────────────────────
tc = df['type'].value_counts()
fig_type = go.Figure(go.Treemap(
    labels=tc.index.tolist(),
    parents=[''] * len(tc),
    values=tc.values.tolist(),
    marker=dict(
        colors=[TYPE_COLORS.get(t, '#475569') for t in tc.index],
        line=dict(width=2, color=CARD),
    ),
    texttemplate='<b>%{label}</b><br>%{value}',
    textfont=dict(size=13, color='white'),
    hovertemplate='<b>%{label}</b>: %{value} venues<extra></extra>',
    tiling=dict(packing='squarify', pad=4),
))
fig_type.update_layout(**chart_style(360, margin=dict(t=5, b=5, l=5, r=5)))

# ── Fig 2: Neighbourhood bar ──────────────────────────────────────────────────
hood_df = df[df['hood'] != 'Unknown']['hood'].value_counts().reset_index()
hood_df.columns = ['hood', 'count']
fig_hood = go.Figure(go.Bar(
    x=hood_df['count'], y=hood_df['hood'], orientation='h',
    marker=dict(color=hood_df['count'], colorscale=[[0,'#1e3a5f'],[1,ACCENT3]],
                showscale=False, cornerradius=5),
    text=hood_df['count'], textposition='outside', textfont=dict(color=MUTED, size=11),
    hovertemplate='<b>%{y}</b>: %{x} venues<extra></extra>',
))
fig_hood.update_layout(**chart_style(400),
    xaxis=dict(showgrid=True, gridcolor=BORDER, tickfont=dict(color=MUTED), zeroline=False),
    yaxis=dict(showgrid=False, tickfont=dict(color=TEXT, size=12), autorange='reversed'))

# ── Fig 3: Avg rating by neighbourhood (top 8) ───────────────────────────────
rating_hood = (df[df['hood'] != 'Unknown']
               .groupby('hood').agg(avg_rating=('rating','mean'), count=('rating','count'))
               .query('count >= 5').sort_values('avg_rating', ascending=True).tail(10))
fig_rating_hood = go.Figure(go.Bar(
    x=rating_hood['avg_rating'], y=rating_hood.index, orientation='h',
    marker=dict(color=rating_hood['avg_rating'],
                colorscale=[[0,'#1e3a5f'],[0.5,ACCENT2],[1,'#34d399']],
                showscale=False, cornerradius=5),
    text=rating_hood['avg_rating'].round(2), textposition='outside',
    textfont=dict(color=MUTED, size=11),
    hovertemplate='<b>%{y}</b><br>Avg rating: %{x:.2f}<extra></extra>',
))
fig_rating_hood.update_layout(**chart_style(320),
    xaxis=dict(range=[3.5, 5.0], showgrid=True, gridcolor=BORDER,
               tickfont=dict(color=MUTED), zeroline=False),
    yaxis=dict(showgrid=False, tickfont=dict(color=TEXT, size=12)))

# ── Fig 4: Price distribution in euro ranges ──────────────────────────────────
# Map Google price_num (1-4) to approximate per-person spend buckets
PRICE_BUCKETS = {1: '< €10', 2: '€10 – 20', 3: '€20 – 40', 4: '> €40'}
BUCKET_ORDER  = ['< €10', '€10 – 20', '€20 – 40', '> €40']
BUCKET_COLORS = ['#34d399', ACCENT3, ACCENT2, ACCENT]

df['price_bucket'] = df['price_num'].map(PRICE_BUCKETS).fillna('€10 – 20')
bucket_counts = df['price_bucket'].value_counts().reindex(BUCKET_ORDER).fillna(0)

fig_price = go.Figure(go.Bar(
    x=bucket_counts.index.tolist(),
    y=bucket_counts.values,
    marker=dict(color=BUCKET_COLORS, cornerradius=6),
    text=bucket_counts.values.astype(int),
    textposition='outside', textfont=dict(color=MUTED),
    hovertemplate='<b>%{x}</b>: %{y} venues<extra></extra>',
))
fig_price.update_layout(**chart_style(240),
    xaxis=dict(showgrid=False, tickfont=dict(color=TEXT, size=13)),
    yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED)),
    showlegend=False,
    annotations=[dict(
        text='Approx. spend per person · based on Google price level',
        x=0.5, y=-0.22, xref='paper', yref='paper',
        showarrow=False, font=dict(size=10, color=MUTED), xanchor='center',
    )]
)

# ── Fig 5: Barcelona heatmap ─────────────────────────────────────────────────
map_df = df[df['lat'].notna() & df['lon'].notna()].copy()
fig_map = go.Figure(go.Densitymapbox(
    lat=map_df['lat'],
    lon=map_df['lon'],
    z=[1] * len(map_df),
    radius=18,
    colorscale=[
        [0.0,  'rgba(0,0,0,0)'],
        [0.2,  '#1e3a5f'],
        [0.5,  ACCENT3],
        [0.75, ACCENT2],
        [1.0,  ACCENT],
    ],
    showscale=False,
    hovertemplate='<extra></extra>',
))
fig_map.update_layout(
    mapbox=dict(
        style='carto-darkmatter',
        center=dict(lat=41.390, lon=2.168),
        zoom=11.8,
    ),
    **chart_style(440, margin=dict(t=0, b=0, l=0, r=0)),
)

# ── Fig 7: Avg rating by type ─────────────────────────────────────────────────
rating_type = (df.groupby('type')
               .agg(avg=('rating','mean'), cnt=('rating','count'))
               .query('cnt >= 3').sort_values('avg', ascending=False))
fig_rating_type = go.Figure(go.Bar(
    x=rating_type.index, y=rating_type['avg'],
    marker=dict(color=[TYPE_COLORS.get(t,'#475569') for t in rating_type.index], cornerradius=5),
    text=rating_type['avg'].round(2), textposition='outside', textfont=dict(color=MUTED, size=10),
    hovertemplate='<b>%{x}</b><br>Avg rating: %{y:.2f}<extra></extra>',
))
fig_rating_type.update_layout(**chart_style(260),
    xaxis=dict(showgrid=False, tickfont=dict(color=TEXT, size=10), tickangle=-30),
    yaxis=dict(range=[3.5,5.1], gridcolor=BORDER, tickfont=dict(color=MUTED)), showlegend=False)

# ── Top 10 highest-rated venues ───────────────────────────────────────────────
top_rated = (df[df['n_ratings'] >= 50]
             .sort_values('rating', ascending=False)
             .head(10)[['name','type','hood','rating','n_ratings','price']])

# ── Layout helpers ────────────────────────────────────────────────────────────
def sec(text):
    return html.Div(text, style=dict(fontSize='0.75rem', fontWeight='700', color=MUTED,
                                     textTransform='uppercase', letterSpacing='0.08em', marginBottom='10px'))
def card(*children, flex=None, min_width=None):
    s = dict(background=CARD, border=f'1px solid {BORDER}', borderRadius='14px', padding='20px 22px')
    if flex:      s['flex'] = flex
    if min_width: s['minWidth'] = min_width
    return html.Div(list(children), style=s)

def stat_card(icon, value, label, color):
    return html.Div([
        html.Div(style=dict(position='absolute',top=0,left=0,right=0,height='3px',background=color)),
        html.Div(icon, style=dict(fontSize='1.5rem', marginBottom='8px')),
        html.Div(str(value), style=dict(fontSize='2.1rem',fontWeight='800',lineHeight='1',
                                        color=color, marginBottom='5px')),
        html.Div(label, style=dict(fontSize='0.73rem',color=MUTED,textTransform='uppercase',
                                   letterSpacing='0.06em',fontWeight='600')),
    ], style=dict(background=CARD, border=f'1px solid {BORDER}', borderRadius='14px',
                  padding='20px 18px', flex='1', minWidth='155px', position='relative', overflow='hidden'))

DARK_DD = '''
.Select-control,.Select-menu-outer{background:#21263a!important;border-color:#2d3348!important;}
.Select-value-label,.Select-placeholder,.Select-option{color:#e2e8f0!important;background:#21263a!important;}
.Select-option.is-focused{background:#2d3348!important;}
.Select-arrow{border-top-color:#8892a4!important;}
'''

avg_rating  = round(df['rating'].mean(), 2)
top_hood    = hood_df.iloc[0]['hood']
top_type    = tc.index[0]
most_common_price = df['price'].value_counts().index[0]

all_types  = ['All'] + sorted(df['type'].unique().tolist())
all_hoods  = ['All'] + sorted(df[df['hood'] != 'Unknown']['hood'].unique().tolist())
all_prices = ['All'] + PRICE_ORDER

app = Dash(__name__, title='Barcelona HoReCa')
app.index_string = app.index_string.replace('</head>', f'<style>{DARK_DD}</style></head>')

def dd(id_, opts, val, width):
    return dcc.Dropdown(id=id_, options=[{'label':o,'value':o} for o in opts],
                        value=val, clearable=False, style=dict(width=width))

app.layout = html.Div(
    style=dict(background=BG, minHeight='100vh', color=TEXT,
               fontFamily="'Segoe UI',system-ui,sans-serif"),
    children=[

        # HEADER
        html.Div([
            html.Span('🍷', style=dict(fontSize='2rem')),
            html.Div([
                html.H1('Barcelona HoReCa',
                        style=dict(fontSize='1.65rem', fontWeight='700', margin=0,
                                   background=f'linear-gradient(90deg,{ACCENT},{ACCENT2})',
                                   WebkitBackgroundClip='text', WebkitTextFillColor='transparent')),
                html.P('555 venues · real Google Places data · type · neighbourhood · price · ratings',
                       style=dict(color=MUTED, fontSize='0.85rem', marginTop='2px')),
            ]),
        ], style=dict(display='flex', alignItems='center', gap='16px',
                      background='linear-gradient(135deg,#1a1d27,#12152a)',
                      borderBottom=f'1px solid {BORDER}', padding='24px 36px')),

        html.Div(style=dict(padding='28px 36px', maxWidth='1500px', margin='0 auto'), children=[

            # STAT CARDS
            html.Div([
                stat_card('📍', total,              'Total Venues',      f'linear-gradient(90deg,{ACCENT},{ACCENT2})'),
                stat_card('🍻', top_type,           'Most Common Type',  ACCENT2),
                stat_card('🏙️',  top_hood,           'Top Neighbourhood', ACCENT3),
                stat_card('⭐', avg_rating,          'Avg Google Rating', '#facc15'),
                stat_card('💶', most_common_price,  'Most Common Price', ACCENT),
            ], style=dict(display='flex', gap='16px', flexWrap='wrap', marginBottom='28px')),

            # ROW 1: Treemap + Neighbourhood bar
            html.Div([
                card(sec('Venue Type'), dcc.Graph(figure=fig_type, config=dict(displayModeBar=False)),
                     flex='1', min_width='340px'),
                card(sec('Venues by Neighbourhood'), dcc.Graph(figure=fig_hood, config=dict(displayModeBar=False)),
                     flex='2', min_width='400px'),
            ], style=dict(display='flex', gap='20px', flexWrap='wrap', marginBottom='20px')),

            # ROW 2: Heatmap (full width)
            card(
                sec('Venue Density Map — Barcelona'),
                dcc.Graph(figure=fig_map, config=dict(displayModeBar=False, scrollZoom=True)),
            ),
            html.Div(style=dict(marginBottom='20px')),

            # ROW 3: Price + Avg rating by type
            html.Div([
                card(sec('Price per Person (approx.)'),
                     dcc.Graph(figure=fig_price, config=dict(displayModeBar=False)),
                     flex='1', min_width='260px'),
                card(sec('Average Google Rating by Type'),
                     dcc.Graph(figure=fig_rating_type, config=dict(displayModeBar=False)),
                     flex='2', min_width='400px'),
            ], style=dict(display='flex', gap='20px', flexWrap='wrap', marginBottom='20px')),

            # ROW 4: Avg rating by neighbourhood + top rated
            html.Div([
                card(sec('Average Rating by Neighbourhood (min 5 venues)'),
                     dcc.Graph(figure=fig_rating_hood, config=dict(displayModeBar=False)),
                     flex='2', min_width='400px'),

                card(
                    sec('Top 10 Highest-Rated (min 50 reviews)'),
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Span(f"{'⭐' * round(r['rating'])}", style=dict(fontSize='0.8rem')),
                                html.Span(f"  {r['rating']}", style=dict(color='#facc15', fontWeight='700', fontSize='0.9rem')),
                                html.Span(f"  {r['name'][:32]}", style=dict(color=TEXT, fontSize='0.85rem')),
                            ]),
                            html.Div(f"{r['type']}  ·  {r['hood']}  ·  {r['price']}",
                                     style=dict(color=MUTED, fontSize='0.75rem', marginTop='2px')),
                        ], style=dict(padding='8px 0', borderBottom=f'1px solid {BORDER}'))
                        for _, r in top_rated.iterrows()
                    ]),
                    flex='1', min_width='300px',
                ),
            ], style=dict(display='flex', gap='20px', flexWrap='wrap', marginBottom='20px')),

            # FULL TABLE
            card(
                html.Div([
                    sec('All Venues'),
                    html.Div([
                        html.Div([html.Label('Type',          style=dict(color=MUTED,fontSize='0.73rem',marginBottom='4px',display='block')),
                                  dd('f-type',  all_types,  'All', '170px')]),
                        html.Div([html.Label('Neighbourhood', style=dict(color=MUTED,fontSize='0.73rem',marginBottom='4px',display='block')),
                                  dd('f-hood',  all_hoods,  'All', '220px')]),
                        html.Div([html.Label('Price',         style=dict(color=MUTED,fontSize='0.73rem',marginBottom='4px',display='block')),
                                  dd('f-price', all_prices, 'All', '140px')]),
                        html.Div([html.Label('Search',        style=dict(color=MUTED,fontSize='0.73rem',marginBottom='4px',display='block')),
                                  dcc.Input(id='f-search', type='text', placeholder='Venue name…',
                                            debounce=True, style=dict(background=CARD2,
                                            border=f'1px solid {BORDER}', borderRadius='6px',
                                            color=TEXT, padding='7px 12px', fontSize='0.85rem',
                                            outline='none', width='180px'))]),
                    ], style=dict(display='flex', gap='14px', flexWrap='wrap', alignItems='flex-end')),
                ], style=dict(marginBottom='16px')),

                dash_table.DataTable(
                    id='tbl',
                    columns=[
                        {'name': '#',             'id': 'idx',        'type': 'numeric'},
                        {'name': 'Venue',         'id': 'name',       'type': 'text'},
                        {'name': 'Type',          'id': 'type',       'type': 'text'},
                        {'name': 'Neighbourhood', 'id': 'hood',       'type': 'text'},
                        {'name': 'Price',         'id': 'price',      'type': 'text'},
                        {'name': '⭐ Rating',     'id': 'rating',     'type': 'numeric'},
                        {'name': '# Reviews',     'id': 'n_ratings',  'type': 'numeric'},
                        {'name': 'Note',          'id': 'note',       'type': 'text'},
                        {'name': 'Maps',          'id': 'url',        'type': 'text', 'presentation': 'markdown'},
                    ],
                    data=[], page_size=20, sort_action='native',
                    style_table=dict(overflowX='auto'),
                    style_cell=dict(background=CARD, color=TEXT, border=f'1px solid {BORDER}',
                                    padding='9px 14px', fontSize='0.85rem', textAlign='left',
                                    fontFamily="'Segoe UI',system-ui,sans-serif",
                                    whiteSpace='normal', maxWidth='260px'),
                    style_header=dict(background=CARD2, color=MUTED, fontWeight='700',
                                      fontSize='0.72rem', textTransform='uppercase',
                                      letterSpacing='0.06em', border=f'1px solid {BORDER}'),
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'},    'background': CARD2},
                        {'if': {'column_id': 'note'},   'color': MUTED, 'fontStyle': 'italic'},
                        {'if': {'column_id': 'idx'},    'color': MUTED, 'maxWidth': '40px'},
                        {'if': {'column_id': 'price'},  'color': ACCENT2, 'fontWeight': '600'},
                        {'if': {'column_id': 'type'},   'fontWeight': '600'},
                        {'if': {'column_id': 'rating'}, 'color': '#facc15', 'fontWeight': '700'},
                        {'if': {'filter_query': '{rating} >= 4.5', 'column_id': 'name'}, 'color': '#34d399'},
                    ],
                    markdown_options=dict(link_target='_blank'),
                ),
                html.Div(id='tbl-footer',
                         style=dict(marginTop='10px', fontSize='0.78rem', color=MUTED, textAlign='right')),
            ),
        ]),
    ],
)

@callback(
    Output('tbl', 'data'),
    Output('tbl-footer', 'children'),
    Input('f-type',   'value'),
    Input('f-hood',   'value'),
    Input('f-price',  'value'),
    Input('f-search', 'value'),
)
def update_table(ftype, fhood, fprice, search):
    out = df.copy()
    if ftype  and ftype  != 'All': out = out[out['type']  == ftype]
    if fhood  and fhood  != 'All': out = out[out['hood']  == fhood]
    if fprice and fprice != 'All': out = out[out['price'] == fprice]
    if search:
        q = search.lower()
        out = out[out['name'].str.lower().str.contains(q, na=False) |
                  out['note'].str.lower().str.contains(q, na=False)]
    out = out.reset_index(drop=True)
    out['idx']    = out.index + 1
    out['rating'] = out['rating'].round(1)
    out['url']    = out['url'].apply(lambda u: f'[↗]({u})' if u and u != 'nan' else '')
    records = out[['idx','name','type','hood','price','rating','n_ratings','note','url']].to_dict('records')
    return records, f'Showing {len(records)} of {total} venues'


server = app.server  # expose for gunicorn

if __name__ == '__main__':
    app.run(debug=False, port=8051)
