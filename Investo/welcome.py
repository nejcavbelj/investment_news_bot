#!/usr/bin/env python3
import os, time, threading, requests
from flask import Flask, request, render_template_string, redirect, url_for
from dotenv import load_dotenv

# Config
HOTSPOT_SSID = "Investo-Setup"
HOTSPOT_PASSWORD = "investo1234"
ENV_FILE = "/home/pi/investo/.env"
WPA_SUPPLICANT_PATH = "/etc/wpa_supplicant/wpa_supplicant.conf"
SYSTEMD_SERVICE = "investo.service"

app = Flask(__name__)
load_dotenv(ENV_FILE) if os.path.exists(ENV_FILE) else None

# ---------- Shared style ----------
STYLE = """
<style>
  body {
    font-family: Arial, sans-serif;
    background-color: #fff7f0;  /* light orange */
    color: #222;
    margin: 0;
    padding: 0;
  }
  header {
    background-color: #ff6600; /* strong orange */
    color: white;
    padding: 1em;
    text-align: center;
  }
  h2 { margin: 0; }
  .container {
    max-width: 600px;
    background: white;
    margin: 2em auto;
    padding: 2em;
    border-radius: 10px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
  }
  h3 { color: #ff6600; margin-top: 1.5em; }
  label { display: block; margin-top: 1em; font-weight: bold; }
  input {
    width: 100%;
    padding: 8px;
    margin-top: 5px;
    border: 1px solid #ccc;
    border-radius: 5px;
  }
  small {
    display: block;
    color: #666;
    margin-top: 4px;
    margin-bottom: 8px;
    font-size: 0.85em;
  }
  input[type=submit] {
    background-color: #ff6600;
    border: none;
    color: white;
    font-weight: bold;
    font-size: 1em;
    padding: 12px;
    margin-top: 20px;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }
  input[type=submit]:hover {
    background-color: #e65c00;
  }
  .success {
    color: green;
    font-weight: bold;
  }
  .error {
    color: red;
    font-weight: bold;
  }
  .info-box {
    padding: 1em;
    border-radius: 8px;
    margin-top: 1em;
  }
  .success-box {
    background: #e6ffe6;
    border: 1px solid green;
  }
  .error-box {
    background: #ffe6e6;
    border: 1px solid red;
  }
  .waiting-box {
    background: #fff4e0;
    border: 1px solid #ff6600;
  }
</style>
"""

# ---------- Setup Form ----------
FORM_HTML = f"""
<!doctype html>
<html>
<head>
  <title>Investo - Setup</title>
  {STYLE}
</head>
<body>
  <header>
    <h2>Welcome to Investo Setup</h2>
  </header>
  <div class="container">
    <p>Please fill in the details so your Investo bot can connect to Wi-Fi and Telegram.<br>
    This only needs to be done once.</p>

    <form method=post>
      <h3>1. Wi-Fi Connection</h3>
      <label>Wi-Fi Network Name (SSID):
        <input name=ssid placeholder="e.g. Home-WiFi" required>
      </label>
      <small>This is the name of your home Wi-Fi network (check on your phone).</small>

      <label>Wi-Fi Password:
        <input name=wifi_pass type=password placeholder="Wi-Fi password">
      </label>
      <small>Use the same password you normally type when connecting a new device.</small>

      <h3>2. Telegram Bot</h3>
      <label>Telegram Bot Token:
        <input name=tg_token placeholder="123456:ABC-DEF..." required>
      </label>
      <small>
        Get this from <b>BotFather</b> in Telegram:<br>
        1. Search <b>@BotFather</b><br>
        2. Send <code>/newbot</code><br>
        3. Copy the token string and paste it here
      </small>

      <h3>3. OpenAI API Key (optional)</h3>
      <label>OpenAI API Key:
        <input name=openai placeholder="sk-...">
      </label>
      <small>Needed for AI stock summaries. Get one at <a href="https://platform.openai.com/" target="_blank">OpenAI</a>.</small>

      <h3>4. Finnhub API Key (optional)</h3>
      <label>Finnhub API Key:
        <input name=finnhub placeholder="finnhub_token">
      </label>
      <small>Needed for real-time stock news. Free at <a href="https://finnhub.io/" target="_blank">finnhub.io</a>.</small>

      <h3>5. Reddit API (optional)</h3>
      <p>Follow these steps to create Reddit API keys:</p>
      <ol>
        <li>Go to <a href="https://www.reddit.com/prefs/apps" target="_blank">Reddit Apps</a></li>
        <li>Click <b>Create App</b>, choose <b>script</b> type</li>
        <li>Set redirect URI = <code>http://localhost:8080</code></li>
        <li>Copy your <b>Client ID</b> and <b>Client Secret</b></li>
        <li>Create a <b>User Agent</b> like <code>InvestoBot/1.0 by your_username</code></li>
      </ol>

      <label>Reddit Client ID:
        <input name=reddit_id placeholder="e.g. XyZaBc123">
      </label>
      <label>Reddit Client Secret:
        <input name=reddit_secret placeholder="e.g. AbC123XyZaBc">
      </label>
      <label>Reddit User Agent:
        <input name=reddit_agent placeholder="InvestoBot/1.0 by your_username">
      </label>

      <input type=submit value="Save & Connect">
    </form>
  </div>
</body>
</html>
"""

# ---------- Helpers ----------
def write_env_from_form(data):
    lines = [
        f"TELEGRAM_BOT_TOKEN={data.get('tg_token','')}",
        f"OPENAI_API_KEY={data.get('openai','')}",
        f"FINNHUB_API_KEY={data.get('finnhub','')}",
        f"REDDIT_CLIENT_ID={data.get('reddit_id','')}",
        f"REDDIT_CLIENT_SECRET={data.get('reddit_secret','')}",
        f"REDDIT_USER_AGENT={data.get('reddit_agent','')}",
    ]
    os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {ENV_FILE}")

def write_wpa(ssid, psk):
    conf = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={{
    ssid="{ssid}"
    psk="{psk}"
    key_mgmt=WPA-PSK
}}
"""
    with open("/tmp/wpa_supplicant.conf.new", "w") as f:
        f.write(conf)
    os.system(f"sudo mv /tmp/wpa_supplicant.conf.new {WPA_SUPPLICANT_PATH}")
    os.system("sudo chown root:root " + WPA_SUPPLICANT_PATH)
    print("Wrote wpa_supplicant config")

def poll_telegram_for_chat_id(bot_token, timeout=300, poll_interval=2):
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    deadline = time.time() + timeout
    last_update_id = None
    print("Waiting for /start in Telegram...")
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=10).json()
            if not r.get("ok"):
                time.sleep(poll_interval); continue
            for u in r.get("result", []):
                uid = u.get("update_id")
                if last_update_id is not None and uid <= last_update_id:
                    continue
                last_update_id = uid
                msg = u.get("message") or u.get("edited_message") or {}
                text = msg.get("text","")
                chat = msg.get("chat",{})
                if text.strip().lower().startswith("/start"):
                    chat_id = chat.get("id")
                    print("Captured chat_id:", chat_id)
                    return chat_id
        except Exception as e:
            print("Telegram poll error:", e)
        time.sleep(poll_interval)
    return None

# ---------- Routes ----------
@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        ssid = request.form["ssid"]
        wifi_pass = request.form["wifi_pass"]
        tg_token = request.form["tg_token"]
        write_env_from_form(request.form)
        write_wpa(ssid, wifi_pass)
        return f"""
        <html><head>{STYLE}</head><body>
        <header><h2>Investo Setup</h2></header>
        <div class="container waiting-box">
          <h3>⚙️ Configuration saved</h3>
          <p>The device is connecting to your Wi-Fi.</p>
          <p>👉 Open Telegram and send <code>/start</code> to your bot.</p>
          <p>This page will check pairing automatically...</p>
          <meta http-equiv="refresh" content="5; url=/status">
        </div>
        </body></html>
        """
    return render_template_string(FORM_HTML)

@app.route("/status")
def status():
    if not os.path.exists(ENV_FILE):
        return redirect(url_for("index"))

    lines = open(ENV_FILE).read().splitlines()
    token, chat_id = None, None
    for l in lines:
        if l.startswith("TELEGRAM_BOT_TOKEN="):
            token = l.split("=",1)[1].strip()
        if l.startswith("TELEGRAM_CHAT_ID="):
            chat_id = l.split("=",1)[1].strip()

    if chat_id:
        return f"""
        <html><head>{STYLE}</head><body>
        <header><h2>Investo Setup</h2></header>
        <div class="container success-box">
          <h3>✅ Setup Complete!</h3>
          <p>Paired with Telegram Chat ID: <b>{chat_id}</b></p>
          <p>Your Investo bot will start shortly.</p>
        </div>
        </body></html>
        """

    if not token:
        return redirect(url_for("index"))

    cid = poll_telegram_for_chat_id(token, timeout=180)
    if cid:
        with open(ENV_FILE, "a") as f:
            f.write(f"TELEGRAM_CHAT_ID={cid}\n")
        os.system(f"sudo systemctl restart {SYSTEMD_SERVICE}")
        return f"""
        <html><head>{STYLE}</head><body>
        <header><h2>Investo Setup</h2></header>
        <div class="container success-box">
          <h3>✅ Paired!</h3>
          <p>Chat ID saved: <b>{cid}</b></p>
          <p>Launching your Investo bot...</p>
        </div>
        </body></html>
        """
    else:
        return f"""
        <html><head>{STYLE}</head><body>
        <header><h2>Investo Setup</h2></header>
        <div class="container error-box">
          <h3>⚠️ Pairing timed out</h3>
          <p>Did you send <code>/start</code> to your bot?</p>
          <p><a href='/'>⬅ Back to Setup</a></p>
        </div>
        </body></html>
        """

# ---------- Hotspot fallback ----------
def start_hotspot_if_needed():
    try:
        requests.get("https://api.ipify.org", timeout=3)
        print("Network OK — skipping hotspot")
        return
    except:
        print("No network — starting hotspot")
    os.system(f"sudo create_ap --no-virt wlan0 wlan0 {HOTSPOT_SSID} {HOTSPOT_PASSWORD} &")

if __name__ == "__main__":
    os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
    if not os.path.exists(ENV_FILE):
        t = threading.Thread(target=start_hotspot_if_needed, daemon=True)
        t.start()
    app.run(host="0.0.0.0", port=80)
