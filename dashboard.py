import json
import math
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, ctx, no_update

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
df['rating']    = pd.to_numeric(df['rating'],    errors='coerce')
df['n_ratings'] = pd.to_numeric(df['n_ratings'], errors='coerce').fillna(0).astype(int)
df['price_num'] = pd.to_numeric(df['price_num'], errors='coerce')
df['note']      = df['note'].fillna('')

# Google returns no price level for ~⅓ of venues — show that honestly instead of defaulting to €€
PRICE_KEY = {1: '€', 2: '€€', 3: '€€€', 4: '€€€'}  # a single €€€€ venue folds into €€€+
df['price_key'] = df['price_num'].map(PRICE_KEY).fillna('?')
df['price']     = df['price_key'].replace({'€€€': '€€€+', '?': '–'})
total = len(df)

TYPE_ICON = {
    'Restaurant': '🍽️', 'Bar': '🍺', 'Café / Bakery': '🥐', 'Tapas / Vermut': '🫒', 'Japanese': '🍣',
    'South American': '🌶️', 'Coffee Shop': '☕', 'Mexican': '🌮', 'Brunch Spot': '🥞', 'Burger Bar': '🍔',
    'Rooftop Bar': '🌇', 'Cocktail Bar': '🍸', 'Healthy': '🥗', 'Club / Pub': '🪩', 'Beach Bar': '🏖️',
    'Argentinian': '🥩', 'Thai': '🍜', 'Poke Bowl': '🥙', 'Other': '📍',
}

# ── Theme ─────────────────────────────────────────────────────────────────────
TEXT, TEXT2, MUTED = '#f6f1ea', '#c4bbae', '#8d8478'
GRID   = 'rgba(255,240,225,0.07)'
ACCENT = '#ff7a45'
DIM    = '#3a332d'          # de-emphasised marks when a filter is active
FONT   = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
# One-hue sequential ramp (dark → bright on a dark surface) for rating magnitude
RATING_SCALE = [[0.0, '#4a2413'], [0.35, '#a8431b'], [0.65, '#ff7a45'], [0.85, '#ffb08a'], [1.0, '#ffe3d2']]
# Ordinal ramp for price tiers, plus neutral grey for "unknown"
PRICE_TIERS  = [('€', 'Budget', '#b04a1f'), ('€€', 'Mid-range', '#ff7a45'),
                ('€€€', 'Upscale', '#ffbf9f'), ('?', 'No price info', '#4a433c')]

MAP_STYLE = os.environ.get('MAP_STYLE', 'carto-darkmatter')   # override for offline testing
GRAPH_CFG = dict(displayModeBar=False, responsive=True)

def base_layout(height, **kw):
    d = dict(height=height, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
             font=dict(family=FONT, color=TEXT2, size=12),
             margin=dict(t=8, b=8, l=8, r=8), showlegend=False, bargap=0.28,
             hoverlabel=dict(bgcolor='#2a2622', bordercolor='rgba(255,240,225,0.16)',
                             font=dict(family=FONT, color=TEXT, size=12)),
             uirevision='keep')
    d.update(kw)
    return d

def empty_fig(height, msg='No venues match these filters'):
    fig = go.Figure()
    fig.update_layout(**base_layout(height), xaxis=dict(visible=False), yaxis=dict(visible=False),
                      annotations=[dict(text=msg, showarrow=False, font=dict(color=MUTED, size=13),
                                        x=0.5, y=0.5, xref='paper', yref='paper')])
    return fig

def fmt_k(n):
    n = int(n)
    return f'{n/1000:.1f}k'.replace('.0k', 'k') if n >= 1000 else str(n)

# ── Filtering ─────────────────────────────────────────────────────────────────
def apply_filters(d, search=None, types=None, hoods=None, prices=None, min_rating=None, noted=None,
                  skip=()):
    if search:
        q = search.strip().lower()
        d = d[d['name'].str.lower().str.contains(q, regex=False) |
              d['note'].str.lower().str.contains(q, regex=False)]
    if types and 'type' not in skip:
        d = d[d['type'].isin(types)]
    if hoods and 'hood' not in skip:
        d = d[d['hood'].isin(hoods)]
    if prices:
        d = d[d['price_key'].isin(prices)]
    if min_rating:
        d = d[d['rating'] >= float(min_rating)]
    if noted:
        d = d[d['note'] != '']
    return d

# ── Figures ───────────────────────────────────────────────────────────────────
def fig_map(d, mode):
    d = d[d['lat'].notna() & d['lon'].notna()]
    if d.empty:
        return empty_fig(None)
    if mode == 'heat':
        trace = go.Densitymap(
            lat=d['lat'], lon=d['lon'], z=[1] * len(d), radius=16, showscale=False,
            colorscale=[[0, 'rgba(255,122,69,0)'], [0.25, 'rgba(168,67,27,0.55)'],
                        [0.6, 'rgba(255,122,69,0.85)'], [1, '#ffe3d2']],
            hoverinfo='skip')
    else:
        d = d.sort_values('rating', na_position='first')   # best-rated drawn on top
        size = 7 + d['n_ratings'].clip(lower=1).apply(math.log10).clip(upper=4.3) * 3
        trace = go.Scattermap(
            lat=d['lat'], lon=d['lon'], mode='markers',
            marker=dict(size=size, color=d['rating'].fillna(3.8), colorscale=RATING_SCALE,
                        cmin=3.8, cmax=4.9, opacity=0.9,
                        colorbar=dict(orientation='h', x=0.02, xanchor='left', y=0.03, yanchor='bottom',
                                      len=0.28, thickness=6, outlinewidth=0,
                                      title=dict(text='Google rating', side='top',
                                                 font=dict(color=TEXT2, size=11)),
                                      tickvals=[4.0, 4.4, 4.8], ticktext=['4.0', '4.4', '4.8'],
                                      tickfont=dict(color=MUTED, size=10),
                                      bgcolor='rgba(13,12,11,0.7)', xpad=10, ypad=8)),
            customdata=list(zip(d['name'], d['type'].map(TYPE_ICON) + ' ' + d['type'], d['hood'],
                                d['rating'].fillna(0), d['n_ratings'].map(fmt_k), d['price'], d['url'])),
            hovertemplate=('<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>'
                           '★ %{customdata[3]:.1f}  ·  %{customdata[4]} reviews  ·  %{customdata[5]}'
                           '<br><span style="color:#8d8478">Click to open in Google Maps</span><extra></extra>'))
    fig = go.Figure(trace)
    fig.update_layout(**base_layout(None, margin=dict(t=0, b=0, l=0, r=0)),
                      map=dict(style=MAP_STYLE, center=dict(lat=41.398, lon=2.170), zoom=12.2))
    return fig

def fig_bar_counts(counts, selected, height, label_fn=lambda s: s, extra_hover=None):
    """Horizontal ranked bar; selected categories stay accent, the rest dim when a selection exists."""
    counts = counts.sort_values(ascending=True)
    colors = [ACCENT if (not selected or c in selected) else DIM for c in counts.index]
    hover = extra_hover.reindex(counts.index).tolist() if extra_hover is not None else [''] * len(counts)
    fig = go.Figure(go.Bar(
        x=counts.values, y=[label_fn(c) for c in counts.index], orientation='h',
        marker=dict(color=colors, cornerradius=4), customdata=list(zip(counts.index, hover)),
        text=counts.values, textposition='outside', cliponaxis=False,
        textfont=dict(color=TEXT2, size=11),
        hovertemplate='<b>%{customdata[0]}</b><br>%{x} venues%{customdata[1]}<extra></extra>'))
    fig.update_layout(**base_layout(height, margin=dict(t=4, b=4, l=4, r=36), bargap=0.3),
                      xaxis=dict(visible=False),
                      yaxis=dict(tickfont=dict(color=TEXT, size=12), ticksuffix='  ', showgrid=False))
    return fig

def fig_rating_hist(d):
    r = d['rating'].dropna()
    if r.empty:
        return empty_fig(400)
    bins = [round(3.5 + i / 10, 1) for i in range(16)]            # 3.5 … 5.0
    clipped = r.clip(lower=3.5).round(1)
    counts = clipped.value_counts().reindex(bins, fill_value=0)
    labels = ['≤3.5' if b == 3.5 else f'{b:.1f}' for b in bins]
    avg = r.mean()
    colors = [ACCENT if b >= 4.5 else '#a8431b' for b in bins]
    fig = go.Figure(go.Bar(x=labels, y=counts.values, marker=dict(color=colors, cornerradius=3),
                           hovertemplate='<b>★ %{x}</b><br>%{y} venues<extra></extra>'))
    fig.update_layout(**base_layout(400, margin=dict(t=30, b=8, l=8, r=8), bargap=0.18),
                      xaxis=dict(tickfont=dict(color=MUTED, size=10), showgrid=False, type='category'),
                      yaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED, size=10), zeroline=False),
                      annotations=[dict(text=f'avg <b style="color:{TEXT}">★ {avg:.2f}</b>  ·  '
                                             f'<b style="color:{TEXT}">{(r >= 4.5).mean():.0%}</b> rated 4.5+',
                                        x=0, y=1.1, xref='paper', yref='paper', xanchor='left',
                                        showarrow=False, font=dict(size=12, color=TEXT2))])
    return fig

def fig_price(d):
    if d.empty:
        return empty_fig(340)
    counts = d['price_key'].value_counts()
    xs = [f'{k if k != "?" else "–"}<br><span style="font-size:10px;color:{MUTED}">{lbl}</span>'
          for k, lbl, _ in PRICE_TIERS]
    ys = [int(counts.get(k, 0)) for k, _, _ in PRICE_TIERS]
    share = [y / max(sum(ys), 1) for y in ys]
    fig = go.Figure(go.Bar(x=xs, y=ys, marker=dict(color=[c for *_, c in PRICE_TIERS], cornerradius=4),
                           text=[f'{s:.0%}' for s in share], textposition='outside', cliponaxis=False,
                           textfont=dict(color=TEXT2, size=11),
                           customdata=[lbl for _, lbl, _ in PRICE_TIERS],
                           hovertemplate='<b>%{customdata}</b><br>%{y} venues<extra></extra>'))
    fig.update_layout(**base_layout(340, margin=dict(t=24, b=8, l=8, r=8), bargap=0.35),
                      xaxis=dict(tickfont=dict(color=TEXT, size=14), showgrid=False),
                      yaxis=dict(visible=False))
    return fig

def fig_rating_by_type(d):
    g = (d.dropna(subset=['rating']).groupby('type')
          .agg(avg=('rating', 'mean'), cnt=('rating', 'size')).query('cnt >= 3')
          .sort_values('avg'))
    if g.empty:
        return empty_fig(340, 'Not enough venues per type')
    lo = min(4.0, math.floor(g['avg'].min() * 10) / 10 - 0.05)
    labels = [f'{TYPE_ICON.get(t, "")} {t}' for t in g.index]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=g['avg'] - lo, base=lo, y=labels, orientation='h', width=0.12,
                         marker=dict(color='rgba(255,122,69,0.35)'), hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=g['avg'], y=labels, mode='markers+text',
                             marker=dict(size=11, color=ACCENT, line=dict(width=2, color='#171513')),
                             text=[f'{a:.2f}' for a in g['avg']], textposition='middle right',
                             textfont=dict(color=TEXT2, size=11), customdata=g['cnt'],
                             hovertemplate='<b>%{y}</b><br>avg ★ %{x:.2f} · %{customdata} venues<extra></extra>'))
    fig.update_layout(**base_layout(340, margin=dict(t=4, b=24, l=4, r=40)),
                      xaxis=dict(range=[lo, 5.0], gridcolor=GRID, tickfont=dict(color=MUTED, size=10),
                                 zeroline=False, dtick=0.2),
                      yaxis=dict(tickfont=dict(color=TEXT, size=12), ticksuffix='  ', showgrid=False))
    return fig

# ── Picks ─────────────────────────────────────────────────────────────────────
PICK_MODES = {
    'top':    ('Top rated',     'min. 100 reviews, best Google rating'),
    'loved':  ('Crowd faves',   'most reviewed on Google'),
    'gems':   ('Hidden gems',   'rated 4.6+ with fewer than 500 reviews'),
}

def picks(d, mode, n=12):
    d = d.dropna(subset=['rating'])
    if mode == 'loved':
        d = d.sort_values(['n_ratings', 'rating'], ascending=False)
    elif mode == 'gems':
        d = d[(d['rating'] >= 4.6) & d['n_ratings'].between(20, 499)].sort_values(
            ['rating', 'n_ratings'], ascending=False)
    else:
        d = d[d['n_ratings'] >= 100].sort_values(['rating', 'n_ratings'], ascending=False)
    d = d.head(n)
    if d.empty:
        return html.Div('Nothing here with the current filters.', className='empty')
    items = []
    for i, r in enumerate(d.itertuples(), 1):
        body = [html.Div(r.name, className='name'),
                html.Div(f'{TYPE_ICON.get(r.type, "")} {r.type}  ·  {r.hood}  ·  {r.price}', className='meta')]
        if r.note:
            body.append(html.Div(f'“{r.note}”', className='note'))
        items.append(html.A([
            html.Div(str(i), className='rank'),
            html.Div(body, style=dict(minWidth=0)),
            html.Div([html.Div([f'{r.rating:.1f} ', html.Span('★', className='star')], className='r'),
                      html.Div(f'{fmt_k(r.n_ratings)} reviews', className='n')], className='score'),
        ], href=r.url, target='_blank', rel='noopener', className='pick'))
    return items

# ── KPIs ──────────────────────────────────────────────────────────────────────
def kpi(label, value, sub, small=False):
    return html.Div([html.Div(label, className='k-label'),
                     html.Div(value, className='k-value' + (' sm' if small else '')),
                     html.Div(sub, className='k-sub')], className='card kpi')

def kpis(d):
    n = len(d)
    if n == 0:
        return [kpi('Venues', '0', f'of {total}'), kpi('Avg rating', '–', ''), kpi('Rated 4.5+', '–', ''),
                kpi('Budget-friendly', '–', ''), kpi('Top area', '–', '', small=True)]
    r = d['rating'].dropna()
    hoods = d[d['hood'] != 'Unknown']['hood'].value_counts()
    top_hood = hoods.index[0] if len(hoods) else '–'
    return [
        kpi('Venues', f'{n}', f'of {total} saved places'),
        kpi('Avg rating', [f'{r.mean():.2f}', html.Span('★', className='star')],
            f'median {int(d["n_ratings"].median()):,} reviews'),
        kpi('Rated 4.5+', f'{(r >= 4.5).sum()}', f'{(r >= 4.5).mean():.0%} of the selection'),
        kpi('Budget-friendly', f'{(d["price_key"] == "€").sum()}', 'venues at €  ·  under ~€10 pp'),
        kpi('Top area', top_hood, f'{hoods.iloc[0] if len(hoods) else 0} venues here', small=True),
    ]

# ── App & layout ──────────────────────────────────────────────────────────────
FONTS = ('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
         '&family=Instrument+Serif:ital@0;1&display=swap')
app = Dash(__name__, title='Barcelona HoReCa', external_stylesheets=[FONTS])
server = app.server  # expose for gunicorn

type_order = df['type'].value_counts().index.tolist()
hood_order = df[df['hood'] != 'Unknown']['hood'].value_counts().index.tolist()

def chips(id_, options, value, cls='chips'):
    return dcc.Checklist(id=id_, value=value, inline=True, className=cls,
                         options=[{'label': html.Span(lbl, className='opt'), 'value': v} for v, lbl in options])

def card_head(title, sub=None, right=None):
    return html.Div([html.Div([html.H3(title, className='card-title'),
                               html.Div(sub, className='card-sub') if sub else None]),
                     right], className='card-head')

app.layout = html.Div([
    # HERO
    html.Header(html.Div([
        html.Div([
            html.Div('Saved on Google Maps · Barcelona', className='eyebrow'),
            html.H1(['Where to ', html.Em('eat & drink'), html.Br(), 'in Barcelona']),
            html.P('Every bar, restaurant and café on my Barcelona: Horeca list, enriched with live Google '
                   'ratings, prices and locations. Filter, explore the map, click any spot to open it.'),
        ]),
        html.Div([html.Div(id='hero-count', className='big'),
                  html.Div('spots match', className='small')], className='hero-count'),
    ], className='hero-inner'), className='hero'),

    # FILTER BAR
    html.Div(html.Div([
        html.Div(dcc.Input(id='f-search', type='text', placeholder='Search venues or notes…',
                           debounce=0.3), className='search'),
        html.Div(dcc.Dropdown(id='f-type', multi=True, placeholder='All types', value=[],
                              options=[{'label': f'{TYPE_ICON.get(t, "")}  {t}', 'value': t} for t in type_order]),
                 className='fdd'),
        html.Div(dcc.Dropdown(id='f-hood', multi=True, placeholder='All neighbourhoods', value=[],
                              options=[{'label': h, 'value': h} for h in hood_order]),
                 className='fdd'),
        html.Div([html.Span('Price', className='lbl'),
                  chips('f-price', [('€', '€'), ('€€', '€€'), ('€€€', '€€€+')], [])], className='chip-group'),
        html.Div([html.Span('Rating', className='lbl'),
                  dcc.RadioItems(id='f-rating', value='', inline=True, className='chips',
                                 options=[{'label': html.Span(l, className='opt'), 'value': v}
                                          for v, l in [('', 'Any'), ('4.3', '4.3+'), ('4.5', '4.5+')]])],
                 className='chip-group'),
        chips('f-noted', [('y', '📝 With my notes')], []),
        html.Button('Reset', id='f-reset', className='btn-reset'),
    ], className='filterbar-inner'), className='filterbar'),

    html.Main([
        html.Div(id='kpis', className='kpis'),

        html.Div([
            html.Div([
                card_head('The map', 'Dot size = number of reviews · colour = rating',
                          dcc.RadioItems(id='map-mode', value='dots', inline=True, className='seg',
                                         options=[{'label': html.Span(l, className='opt'), 'value': v}
                                                  for v, l in [('dots', 'Spots'), ('heat', 'Heatmap')]])),
                dcc.Graph(id='g-map', config=dict(GRAPH_CFG, scrollZoom=True), style=dict(height='100%', minHeight='620px')),
            ], className='card map-card s8'),
            html.Div([
                card_head('Top picks', None,
                          dcc.RadioItems(id='pick-mode', value='top', inline=True, className='seg',
                                         options=[{'label': html.Span(v[0], className='opt'), 'value': k}
                                                  for k, v in PICK_MODES.items()])),
                html.Div(id='pick-sub', className='card-sub'),
                html.Div(id='picks', className='picks'),
            ], className='card s4'),
        ], className='grid'),

        html.Div([
            html.Div([card_head('What kind of place', None, html.Span('click a bar to filter', className='hint')),
                      dcc.Graph(id='g-type', config=GRAPH_CFG, style=dict(height='400px'))], className='card s4'),
            html.Div([card_head('Where', None, html.Span('click a bar to filter', className='hint')),
                      dcc.Graph(id='g-hood', config=GRAPH_CFG, style=dict(height='400px'))], className='card s4'),
            html.Div([card_head('How good', 'Google rating distribution'),
                      dcc.Graph(id='g-rating', config=GRAPH_CFG, style=dict(height='400px'))], className='card s4'),
        ], className='grid'),

        html.Div([
            html.Div([card_head('How pricey', 'Google price level · € ≈ under €10, €€ ≈ €10–25, '
                                              '€€€+ ≈ €25+ per person'),
                      dcc.Graph(id='g-price', config=GRAPH_CFG, style=dict(height='340px'))], className='card s5'),
            html.Div([card_head('Best-rated cuisines', 'Average Google rating · types with 3+ venues'),
                      dcc.Graph(id='g-rtype', config=GRAPH_CFG, style=dict(height='340px'))], className='card s7'),
        ], className='grid'),

        html.Div([
            card_head('All venues', None, html.Span(id='tbl-count', className='hint')),
            dash_table.DataTable(
                id='tbl',
                columns=[
                    {'name': 'Venue',         'id': 'link',      'presentation': 'markdown'},
                    {'name': 'Type',          'id': 'type_lbl'},
                    {'name': 'Neighbourhood', 'id': 'hood'},
                    {'name': 'Price',         'id': 'price'},
                    {'name': 'Rating',        'id': 'rating',    'type': 'numeric'},
                    {'name': 'Reviews',       'id': 'n_ratings', 'type': 'numeric'},
                    {'name': 'My note',       'id': 'note'},
                ],
                data=[], page_size=15, sort_action='native', sort_by=[{'column_id': 'rating', 'direction': 'desc'}],
                markdown_options=dict(link_target='_blank'),
                style_as_list_view=True,
                style_table=dict(overflowX='auto'),
                style_cell=dict(backgroundColor='transparent', color=TEXT2, border='none',
                                borderBottom='1px solid rgba(255,240,225,0.06)', padding='12px 14px',
                                fontSize='0.87rem', textAlign='left', fontFamily=FONT,
                                whiteSpace='normal', height='auto', minWidth='90px', maxWidth='280px'),
                style_header=dict(backgroundColor='transparent', color=MUTED, fontWeight='600',
                                  fontSize='0.7rem', textTransform='uppercase', letterSpacing='0.1em',
                                  borderBottom='1px solid rgba(255,240,225,0.14)'),
                style_data_conditional=[
                    {'if': {'column_id': 'link'},   'color': TEXT, 'minWidth': '200px'},
                    {'if': {'column_id': 'note'},   'color': MUTED, 'fontStyle': 'italic'},
                    {'if': {'column_id': 'rating'}, 'color': TEXT, 'fontWeight': '600'},
                    {'if': {'filter_query': '{rating} >= 4.6', 'column_id': 'rating'}, 'color': ACCENT},
                ],
            ),
        ], className='card', style=dict(paddingBottom='18px')),

        html.Div(f'{total} places · data from Google Places API · built with Dash', className='footer'),
    ], className='page'),

    dcc.Location(id='noop-loc'),
])

# ── Callbacks ─────────────────────────────────────────────────────────────────
FILTERS = [Input('f-search', 'value'), Input('f-type', 'value'), Input('f-hood', 'value'),
           Input('f-price', 'value'), Input('f-rating', 'value'), Input('f-noted', 'value')]

@app.callback(
    Output('hero-count', 'children'), Output('kpis', 'children'),
    Output('g-type', 'figure'), Output('g-hood', 'figure'), Output('g-rating', 'figure'),
    Output('g-price', 'figure'), Output('g-rtype', 'figure'),
    Output('tbl', 'data'), Output('tbl-count', 'children'),
    *FILTERS,
)
def update_dashboard(search, types, hoods, prices, min_rating, noted):
    f = dict(search=search, types=types, hoods=hoods, prices=prices, min_rating=min_rating, noted=noted)
    d = apply_filters(df, **f)

    # Type / hood charts ignore their own filter so you can see (and click) the alternatives
    dt = apply_filters(df, **f, skip=('type',))
    type_counts = dt['type'].value_counts()
    type_fig = (fig_bar_counts(type_counts.head(12), types, 400, lambda t: f'{TYPE_ICON.get(t, "")} {t}')
                if len(type_counts) else empty_fig(400))

    dh = apply_filters(df, **f, skip=('hood',))
    dh = dh[dh['hood'] != 'Unknown']
    hood_counts = dh['hood'].value_counts().head(12)
    hood_avg = dh.groupby('hood')['rating'].mean().map(lambda a: f'<br>avg ★ {a:.2f}')
    hood_fig = fig_bar_counts(hood_counts, hoods, 400, extra_hover=hood_avg) if len(hood_counts) else empty_fig(400)

    t = d.copy()
    t['link'] = [f'[{n}]({u})' for n, u in zip(t['name'], t['url'])]
    t['type_lbl'] = t['type'].map(lambda x: f'{TYPE_ICON.get(x, "")} {x}')
    t['rating'] = t['rating'].round(1)
    rows = t[['link', 'type_lbl', 'hood', 'price', 'rating', 'n_ratings', 'note']].to_dict('records')

    return (str(len(d)), kpis(d), type_fig, hood_fig, fig_rating_hist(d), fig_price(d), fig_rating_by_type(d),
            rows, f'{len(d)} of {total}')

@app.callback(Output('g-map', 'figure'), *FILTERS, Input('map-mode', 'value'))
def update_map(search, types, hoods, prices, min_rating, noted, mode):
    return fig_map(apply_filters(df, search, types, hoods, prices, min_rating, noted), mode)

@app.callback(Output('picks', 'children'), Output('pick-sub', 'children'), *FILTERS, Input('pick-mode', 'value'))
def update_picks(search, types, hoods, prices, min_rating, noted, mode):
    d = apply_filters(df, search, types, hoods, prices, min_rating, noted)
    return picks(d, mode), PICK_MODES[mode][1]

@app.callback(
    Output('f-type', 'value'), Output('f-hood', 'value'), Output('f-price', 'value'),
    Output('f-rating', 'value'), Output('f-noted', 'value'), Output('f-search', 'value'),
    Input('g-type', 'clickData'), Input('g-hood', 'clickData'), Input('f-reset', 'n_clicks'),
    State('f-type', 'value'), State('f-hood', 'value'),
    prevent_initial_call=True,
)
def cross_filter(type_click, hood_click, _reset, types, hoods):
    def toggle(lst, v):
        lst = list(lst or [])
        return [x for x in lst if x != v] if v in lst else lst + [v]
    trig = ctx.triggered_id
    if trig == 'f-reset':
        return [], [], [], '', [], ''
    if trig == 'g-type' and type_click:
        return toggle(types, type_click['points'][0]['customdata'][0]), *[no_update] * 5
    if trig == 'g-hood' and hood_click:
        return no_update, toggle(hoods, hood_click['points'][0]['customdata'][0]), *[no_update] * 4
    return [no_update] * 6

# Clicking a dot on the map opens the venue in Google Maps
app.clientside_callback(
    """function(click) {
        if (click && click.points && click.points.length) {
            const cd = click.points[0].customdata;
            if (cd && cd[6]) { window.open(cd[6], '_blank', 'noopener'); }
        }
        return window.dash_clientside.no_update;
    }""",
    Output('noop-loc', 'hash'), Input('g-map', 'clickData'), prevent_initial_call=True,
)

if __name__ == '__main__':
    app.run(debug=False, port=8051)
