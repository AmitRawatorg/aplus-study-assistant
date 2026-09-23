import secrets

env = {}
for line in open(".env"):
    if "=" in line:
        k, v = line.strip().split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

text = f'''[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "{secrets.token_hex(32)}"
client_id = "{env["GOOGLE_CLIENT_ID"]}"
client_secret = "{env["GOOGLE_CLIENT_SECRET"]}"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
'''

open(".streamlit/secrets.toml", "w").write(text)
print("secrets.toml ban gayi")