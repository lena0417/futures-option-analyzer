from flask import Flask, render_template_string, request
import yfinance as yf
import pandas as pd
import talib

app = Flask(__name__)

# ===== 技術分析邏輯 =====
def analyze_tech(ticker="^TWII", interval="1d", period="30d"):
    try:
        df = yf.download(ticker, interval=interval, period=period)
        df.dropna(inplace=True)
        close = df['Close']

        macd, macdsignal, _ = talib.MACD(close)
        slowk, slowd = talib.STOCH(df['High'], df['Low'], df['Close'])

        macd_cross = macd.iloc[-1] - macdsignal.iloc[-1]
        macd_prev_cross = macd.iloc[-2] - macdsignal.iloc[-2]

        if macd_cross > 0 and macd_prev_cross < 0:
            macd_signal = "MACD黃金交叉（偏多）"
        elif macd_cross < 0 and macd_prev_cross > 0:
            macd_signal = "MACD死亡交叉（偏空）"
        elif macd_cross > 0:
            macd_signal = "MACD多頭趨勢"
        elif macd_cross < 0:
            macd_signal = "MACD空頭趨勢"
        else:
            macd_signal = "MACD盤整"

        if slowk.iloc[-1] > slowd.iloc[-1] and slowk.iloc[-2] < slowd.iloc[-2]:
            kd_signal = "KD黃金交叉（偏多）"
        elif slowk.iloc[-1] < slowd.iloc[-1] and slowk.iloc[-2] > slowd.iloc[-2]:
            kd_signal = "KD死亡交叉（偏空）"
        elif slowk.iloc[-1] > slowd.iloc[-1]:
            kd_signal = "KD多頭趨勢"
        elif slowk.iloc[-1] < slowd.iloc[-1]:
            kd_signal = "KD空頭趨勢"
        else:
            kd_signal = "KD盤整"

        return [macd_signal, kd_signal]
    except Exception as e:
        return ["技術分析錯誤: " + str(e)]

# ===== 支撐壓力判斷 =====
def get_support_resistance(ticker="^TWII", interval="5m", period="1d"):
    try:
        df = yf.download(ticker, interval=interval, period=period)
        df.dropna(inplace=True)
        recent = df.tail(20)
        support = recent['Low'].min()
        resistance = recent['High'].max()
        return f"支撐區：約 {support:.2f}，壓力區：約 {resistance:.2f}"
    except Exception as e:
        return f"支撐壓力計算錯誤: {e}"

# ===== 籌碼分析 =====
def analyze_chips_text(buy_oi, sell_oi, pc_ratio, foreign_buy):
    signals = []
    if buy_oi > 0 and sell_oi < 0:
        signals.append("偏多（買權增、賣權減）")
    elif buy_oi < 0 and sell_oi > 0:
        signals.append("偏空（買權減、賣權增）")
    if pc_ratio > 1:
        signals.append("偏空（P/C Ratio > 1）")
    else:
        signals.append("偏多（P/C Ratio < 1）")
    if foreign_buy > 0:
        signals.append("偏多（外資買買權）")
    elif foreign_buy < 0:
        signals.append("偏空（外資賣買權）")

    bullish = signals.count("偏多（買權增、賣權減）") + signals.count("偏多（P/C Ratio < 1）") + signals.count("偏多（外資買買權）")
    bearish = 3 - bullish
    if bullish >= 2:
        final = "➡ 綜合判斷：偏多"
    elif bearish >= 2:
        final = "➡ 綜合判斷：偏空"
    else:
        final = "➡ 綜合判斷：中性"

    return signals, final

# ===== Flask 路由與前端模板 =====
HTML_PAGE = """
<!doctype html>
<title>台指分析</title>
<h2>台指籌碼＋技術分析工具</h2>
<form method=post>
  買權OI：<input type=number name=buy_oi><br>
  賣權OI：<input type=number name=sell_oi><br>
  P/C Ratio：<input type=text name=pc_ratio><br>
  外資買權淨額：<input type=number name=foreign_buy><br>
  <input type=submit value=分析>
</form>
{% if result %}
  <h3>📊 籌碼分析</h3>
  <ul>{% for item in result['chips'] %}<li>{{ item }}</li>{% endfor %}</ul>
  <p><b>{{ result['chips_final'] }}</b></p>

  <h3>📈 技術分析</h3>
  <ul>{% for item in result['tech'] %}<li>{{ item }}</li>{% endfor %}</ul>

  <h3>⏰ 5分鐘支撐壓力</h3>
  <p>{{ result['sr'] }}</p>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        try:
            buy_oi = int(request.form["buy_oi"])
            sell_oi = int(request.form["sell_oi"])
            pc_ratio = float(request.form["pc_ratio"])
            foreign_buy = int(request.form["foreign_buy"])

            chips, chips_final = analyze_chips_text(buy_oi, sell_oi, pc_ratio, foreign_buy)
            tech = analyze_tech()
            sr = get_support_resistance()
            result = {"chips": chips, "chips_final": chips_final, "tech": tech, "sr": sr}
        except Exception as e:
            result = {"chips": ["輸入錯誤或處理失敗"], "chips_final": str(e), "tech": [], "sr": ""}

    return render_template_string(HTML_PAGE, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
