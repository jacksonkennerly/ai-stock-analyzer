import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title = 'AI Stock Analysis Tool',
    layout = 'wide'
)


ticker = st.sidebar.text_input('Enter a stock ticker:')

if ticker:
    col1, col2, col3 = st.columns(3)
    stock = yf.Ticker(ticker)
    data = stock.history(period='1y')

    old_price = data['Close'].iloc[-30]
    latest_price = data['Close'].dropna().iloc[-1]
    # dropna() = Drop Not A Number (NaN)

    change = (latest_price - old_price) / old_price
    percent_change = change * 100

    st.subheader(f'Stock Analysis for {ticker.upper()}')
    st.markdown('----------------------------------')

    data['MA_50'] = data['Close'].rolling(window=50).mean()
    ma_50 = data['MA_50'].dropna().iloc[-1]
    # Take the closing price of the last 50 days and take the average (.mean()) of it
    # .rolling groups the 50 days to a group so hat we could average
    col2.metric('50-Day Average', f'${ma_50:.2f}')

    avg_percent = ((latest_price - ma_50) / ma_50) * 100


    if latest_price > ma_50:
        col1.metric('Latest Price:', f'${latest_price:.2f}', f'{avg_percent:.2f}% above 50-Day Average')
    else:
        col1.metric('Latest Price:', f'${latest_price:.2f}', f'{avg_percent:.2f}% below 50-Day Average')

    col1.metric('30-Day Price:', f'${old_price:.2f}')

    with col1:
        st.markdown('Change:')

        if percent_change > 0:
            st.markdown(f"<h3 style='color:green;'>+{percent_change:.2f}%</h3>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h3 style='color:red;'>{percent_change:.2f}%</h3>", unsafe_allow_html=True)

    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    data['RSI'] = 100 - (100 / (1 + rs))
    rsi = data['RSI'].dropna().iloc[-1]
    # RSI = Relative Strength Index (how fast the price has changed and shows if overbought or oversold by investors)
    # delta = the change from the previous row (marginal)
    # .clip = keep only positives or negatives and turn uppers to 0 or lowers to 0
    # .rolling groups the last 14 days

    if rsi > 70:
        col2.metric('RSI', f'{rsi:.2f} (Overbought, may drop soon)')
    elif rsi < 30:
        col2.metric('RSI', f'{rsi:.2f} (Underbought, may rise soon)')
    else:
        col2.metric('RSI', f'{rsi:.2f} (Neutral momentum)')



    data['Returns'] = data['Close'].pct_change()
    vol = data['Returns'].std() * 100
    # .std = measures how spread out the values are

    risk_score = 0
    if vol > 2:
        risk_score += 1
    if rsi > 70 or rsi < 30:
        risk_score += 1
    if abs(percent_change) < 2:
        risk_score += 1

    if risk_score == 0:
        risk = 'Low'
    elif risk_score == 2:
        risk = 'Medium'
    else:
        risk = 'High'


    st.subheader('Risk Analysis')
    st.write(f'Volatility: {vol:.2f}%')
    if risk == 'Low':
        st.success('Low Risk')
    elif risk == 'Medium':
        st.warning('Medium Risk')
    else:
        st.error('High Risk')


    st.subheader('Price Chart + 50-Day Average')
    st.line_chart(data[['Close', 'MA_50']])
    st.markdown('----------------------------------')

    st.metric('DCF valuations are highly sensitive to assumptions and should not be used as investment advice.', 'Discounted Cash Flow')

    cashflow = stock.cashflow
    fcf_series = cashflow.loc["Free Cash Flow"]
    fcf = fcf_series.iloc[:3].mean()
    # .loc = Find the mean of the last 3 rows

    revenue_growth = stock.info.get('revenueGrowth')
    growth_rate = min(revenue_growth, 0.15)

    terminal_growth = 0.03

    beta = stock.info.get('beta')
    if beta is None:
        beta = 1.0

    risk_free_rate = 0.04
    # an investor can reasonably earn 4% returns with low risk
    market_risk_premium = 0.05
    # an investor can expect 5% EXTRA returns for taking stock market risk
    cost_of_equity = (risk_free_rate + beta * market_risk_premium)
    discount_rate = cost_of_equity
    years = 5

    fut_cashflows = []

    for i in range(1, years + 1):
        projected_fcf = fcf * (1 + growth_rate) ** i
        fut_cashflows.append(projected_fcf)
    # Estimates what free cash flow will be in the next 5 years
    # range(1, years + 1) = creates years 1-5
    # ** means raised to the power of
    # append () means adding each projected fcf to the list
    # i = the current year #

    dis_cashflows = []

    for i, cashflow_value in enumerate(fut_cashflows, start=1):
        dis_value = cashflow_value / ((1 + discount_rate) ** i)
        dis_cashflows.append(dis_value)
    # Converts that future cash flow into today's dollars

    terminal_value = (fut_cashflows[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
    # Estimates all future years after year 5

    dis_terminal = terminal_value / ((1 + discount_rate) ** years)
    # Putting the terminal value in today's dollars

    enterprise_value = sum(dis_cashflows) + dis_terminal
    # Estimated value of the entire company

    shares_outstanding = stock.info.get('sharesOutstanding', 1)
    # Grabs shares outstanding (amt of total shares in a company) from yfinance

    fair_value = enterprise_value / shares_outstanding


    if fair_value > latest_price:
        st.success(f'Fair Value: ${fair_value:.2f}')
    else:
        st.error(f'Fair Value: ${fair_value:.2f}')

    col1, col2 = st.columns(2)


    col1.metric("FCF Used", f"${fcf / 1e9:.1f}B")

    col1.metric("Growth Rate", f"{growth_rate * 100:.1f}%")

    col2.metric("Terminal Growth", f"{terminal_growth * 100:.1f}%")

    col2.metric("Discount Rate", f"{discount_rate * 100:.1f}%")





    valuation_gap = ((fair_value - latest_price) / latest_price) * 100

    score = 0
    max_score = 6
    if latest_price > ma_50:
        score += 1
    if percent_change > 0:
        score += 1
    if 30 <= rsi <= 70:
        score += 1
    if valuation_gap > 20:
        score += 3
    elif valuation_gap > 10:
        score += 2
    elif valuation_gap > 0:
        score += 1
    elif valuation_gap < -10:
        score -= 2
    elif valuation_gap < -20:
        score -= 3

    if score >= 5:
        decision = "BUY"
    elif score>= 3:
        decision = 'HOLD'
    else:
        decision = 'SELL'

    conf = max(0, min(100, (score / max_score) * 100))


    if decision == "BUY":
        st.success(f'BUY (Score: {score}/{max_score})')
    elif decision == 'SELL':
        st.error(f'SELL (Score: {score}/{max_score})')
    else:
        st.warning(f'HOLD (Score: {score}/{max_score})')


