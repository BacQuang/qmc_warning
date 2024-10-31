import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from tvdatafeed.tvDatafeed.main import *
from statsmodels.tsa.stattools import grangercausalitytests
import plotly.subplots as ms
from datetime import datetime, date

# ------------------------------------------------------------------------------ #
# Granger Causality test
def granger_causality_test(data_1, data_2, maxlag: int=10):
    df_1 = data_1.copy()
    df_2 = data_2.copy()
    bars = pd.DataFrame()

    df_1['percent_change'] = df_1.close.pct_change()
    df_2['percent_change'] = df_2.close.pct_change()
    bars = pd.concat([bars, df_1, df_2]).reset_index()
    bars['datetime'] = bars.datetime.dt.date
    bars = bars.set_index('datetime')
    df_test = bars.pivot_table(values='percent_change', index='datetime', columns='symbol').dropna()
    df_granger = grangercausalitytests(df_test[[df_1.symbol.unique()[0], df_2.symbol.unique()[0]]], maxlag=[maxlag])
    df_granger = df_granger[maxlag][0]['ssr_ftest'][1]
    return df_granger

# ------------------------------------------------------------------------------ #
# Import Data
USERNAME = ''
PASSWORD = ''
tv = TvDatafeed(USERNAME, PASSWORD)

data_input = {
    'Yếu tố': ['TPCP Mỹ 10 năm', 'TPCP VN 10 năm', 'Chỉ số USD', 'Chỉ số S&P500', 'LS liên ngân hàng VN'],
    'symbol' : ['US10Y', 'VN10Y', 'DXY', 'SPX', 'VNINBR'],
    'exchange' : ['TVC', 'TVC', 'TVC', 'SP', 'ECONOMICS']
}

# VNINDEX index data
df_vnindex = tv.get_hist(symbol='VNINDEX', exchange='HOSE', interval=Interval.in_daily, n_bars=20000)
df_vnindex.index = df_vnindex.index.normalize()

# Factors data
symbol = data_input['symbol']
exchange = data_input['exchange']
factor_data = {}
for i in range(0, len(symbol)):
    df_temp = tv.get_hist(symbol=symbol[i], exchange=exchange[i], interval=Interval.in_daily, n_bars=20000)
    df_temp.index = df_temp.index.normalize()
    factor_data[symbol[i]] = df_temp

# ------------------------------------------------------------------------------ #
# Calculation
correlation_short, correlation_long, granger, status = [], [], [], []
coefficient = [''] * len(symbol)
short_corr_length = 30
long_corr_length = 250
back = 5
for i in range(0, len(symbol)):
    df_corr = pd.concat([df_vnindex.close, factor_data[symbol[i]].close], axis=1)
    df_corr = df_corr.dropna()
    df_corr.columns = ['VNINDEX', symbol[i]]
    correlation_short.append((df_corr['VNINDEX'].pct_change().rolling(short_corr_length).corr(df_corr[symbol[i]].pct_change())).iloc[-1])
    correlation_long.append((df_corr['VNINDEX'].pct_change().rolling(long_corr_length).corr(df_corr[symbol[i]].pct_change())).iloc[-1])
    granger.append(granger_causality_test(df_vnindex, factor_data[symbol[i]]))
    if ((factor_data[symbol[i]].close / factor_data[symbol[i]].close.shift(back) > 0.05).iloc[-1] and (correlation_short[i] > 0)) | \
          ((factor_data[symbol[i]].close / factor_data[symbol[i]].close.shift(back) < -0.05).iloc[-1] and (correlation_short[i] < 0)):
        status.append('Tích cực')
    elif ((factor_data[symbol[i]].close / factor_data[symbol[i]].close.shift(back) > 0.05).iloc[-1] and (correlation_short[i] < 0)) | \
          ((factor_data[symbol[i]].close / factor_data[symbol[i]].close.shift(back) < -0.05).iloc[-1] and (correlation_short[i] > 0)):
        status.append('Tiêu cực')
    else:
        status.append('Trung tính')

# ------------------------------------------------------------------------------ #
data = {
    "Yếu tố": data_input['Yếu tố'],
    "Hệ số tương quan ngắn hạn": correlation_short,
    "Hệ số tương quan dài hạn": correlation_long,
    "Hệ số giải thích": coefficient,
    "Hệ số Granger": granger,
    "Trạng thái": status
}
df = pd.DataFrame(data)


# row_pos = [1, 1, 1, 2, 2, 2]
# col_pos = [1, 2, 3, 1, 2, 3]
# st.title("WARNING MARKET SCREEN")
# fig = ms.make_subplots(rows=2, cols=3)
# for i in range(0, len(row_pos)):
#     if i == 0:
#         fig.add_trace(go.Candlestick(x=df_vnindex.index, open=df_vnindex['open'], high=df_vnindex.high, low=df_vnindex.low, close=df_vnindex.close), row=row_pos[i], col=col_pos[i])
#     else:
#         fig.add_trace(go.Candlestick(x=factor_data[symbol[i-1]].index, open=factor_data[symbol[i-1]]['open'], high=factor_data[symbol[i-1]].high, low=factor_data[symbol[i-1]].low, close=factor_data[symbol[i-1]].close), row=row_pos[i], col=col_pos[i])
# fig.update_yaxes(fixedrange=False)
# fig.update_layout(xaxis1_rangeslider_visible=False,
#                   xaxis2_rangeslider_visible=False,
#                   xaxis3_rangeslider_visible=False,
#                   xaxis4_rangeslider_visible=False,
#                   xaxis5_rangeslider_visible=False,
#                   xaxis6_rangeslider_visible=False,
#                   xaxis1_range=['2024-01-01','2024-12-31'],
#                   xaxis2_range=['2024-01-01','2024-12-31'],
#                   xaxis3_range=['2024-01-01','2024-12-31'],
#                   xaxis4_range=['2024-01-01','2024-12-31'],
#                   xaxis5_range=['2024-01-01','2024-12-31'],
#                   xaxis6_range=['2024-01-01','2024-12-31'],
#                   bargap=0)

# st.plotly_chart(fig)
# st.header("Bảng thông tin")
# st.dataframe(df.style)

# Plot setup
st.title("WARNING MARKET SCREEN")

# Get today's date
today = pd.Timestamp(date.today())

# Find the latest start date among all datasets
all_dfs = [df_vnindex] + list(factor_data.values())
latest_start_date = max(df.index.min() for df in all_dfs)
max_date = today

# Filter all dataframes to start from the latest start date
df_vnindex = df_vnindex[df_vnindex.index >= latest_start_date]
for sym in factor_data:
    factor_data[sym] = factor_data[sym][factor_data[sym].index >= latest_start_date]


# Create subplots with custom layout
fig = ms.make_subplots(
    rows=3, cols=2,
    specs=[[{"colspan": 2}, None],
           [{}, {}],
           [{}, {}]],
    row_heights=[0.5, 0.25, 0.25],
    subplot_titles=['VNINDEX'] + symbol[:5],
    vertical_spacing=0.08,
    horizontal_spacing=0.05,
    shared_xaxes=True  # Share x axes between all subplots
)

# Add VNINDEX as main chart
fig.add_trace(
    go.Candlestick(
        x=df_vnindex.index,
        open=df_vnindex['open'],
        high=df_vnindex.high,
        low=df_vnindex.low,
        close=df_vnindex.close,
        name='VNINDEX'
    ),
    row=1, col=1
)

# Add other charts in smaller size
positions = [(2,1), (2,2), (3,1), (3,2)]
for i, (row, col) in enumerate(positions):
    if i < len(symbol):
        fig.add_trace(
            go.Candlestick(
                x=factor_data[symbol[i]].index,
                open=factor_data[symbol[i]]['open'],
                high=factor_data[symbol[i]].high,
                low=factor_data[symbol[i]].low,
                close=factor_data[symbol[i]].close,
                name=symbol[i]
            ),
            row=row, col=col
        )

# Update layout
fig.update_layout(
    height=900,
    showlegend=False,
    bargap=0,
    # Add range selector buttons
    updatemenus=[dict(
        type="buttons",
        direction="left",
        x=0.1,
        y=1.1,
        xanchor="left",
        yanchor="top",
        pad={"r": 10, "t": 10},
        showactive=True,
        buttons=[
            # 2024 button
            dict(
                label="2024",
                method="relayout",
                args=[{
                    "xaxis.range": ["2024-01-01", today.strftime('%Y-%m-%d')],
                    "xaxis2.range": ["2024-01-01", today.strftime('%Y-%m-%d')],
                    "xaxis3.range": ["2024-01-01", today.strftime('%Y-%m-%d')],
                    "xaxis4.range": ["2024-01-01", today.strftime('%Y-%m-%d')],
                    "xaxis5.range": ["2024-01-01", today.strftime('%Y-%m-%d')]
                }]
            ),
            # All Time button
            dict(
                label="All Time",
                method="relayout",
                args=[{
                    "xaxis.range": [latest_start_date, today.strftime('%Y-%m-%d')],
                    "xaxis2.range": [latest_start_date, today.strftime('%Y-%m-%d')],
                    "xaxis3.range": [latest_start_date, today.strftime('%Y-%m-%d')],
                    "xaxis4.range": [latest_start_date, today.strftime('%Y-%m-%d')],
                    "xaxis5.range": [latest_start_date, today.strftime('%Y-%m-%d')]
                }]
            )
        ]
    )]
)

# Set default range to 2024 and disable range sliders
for i in range(1, 6):
    xaxis_name = f"xaxis{i}" if i > 1 else "xaxis"
    fig.update_layout({
        f"{xaxis_name}.range": ["2024-01-01", today.strftime('%Y-%m-%d')],
        f"{xaxis_name}.rangeslider.visible": False,
        f"{xaxis_name}.matches": 'x'  # Make all x-axes match the first one
    })

# Allow y-axis zooming but keep x-axis sync
fig.update_yaxes(fixedrange=False)
fig.update_xaxes(
    fixedrange=False,  # Allow x-axis zooming
    constrain='domain',  # Constrain the zooming to the plot domain
    constraintoward='middle'  # Center the zoom
)

# Update chart margin and spacing
fig.update_layout(
    margin=dict(l=50, r=50, t=100, b=50),
)

# Display chart and table
st.plotly_chart(fig, use_container_width=True)
st.header("Bảng thông tin")
st.dataframe(df.style)