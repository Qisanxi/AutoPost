import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

CLIENT_ID = "enter your client Id from linkedin developer portal "
CLIENT_SECRET = "enter your client secret from linkedin devloper portal"
REDIRECT_URI = "http://localhost:8000/callback"
SCOPE = "openid profile w_member_social"

auth_code = None


class OAuthHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    global auth_code
    query_components = urllib.parse.parse_qs(
        urllib.parse.urlparse(self.path).query
    )
    if "code" in query_components:
      auth_code = query_components["code"][0]
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(
          b"<h1>Authorization Successful!</h1><p>You can close this window and"
          b" return to your terminal.</p>"
      )


# 1. Open Authorization URL in browser
auth_url = (
    f"https://www.linkedin.com/oauth/v2/authorization?"
    f"response_type=code&client_id={CLIENT_ID}&"
    f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
    f"scope={urllib.parse.quote(SCOPE)}&state=xyz123"
)

print("Opening browser for authorization...")
webbrowser.open(auth_url)

# 2. Start local server to capture redirect code
server = HTTPServer(("localhost", 8000), OAuthHandler)
server.handle_request()

# 3. Exchange code for Access Token & Person URN
if auth_code:
  token_url = "https://www.linkedin.com/oauth/v2/accessToken"
  payload = {
      "grant_type": "authorization_code",
      "code": auth_code,
      "redirect_uri": REDIRECT_URI,
      "client_id": CLIENT_ID,
      "client_secret": CLIENT_SECRET,
  }
  headers = {"Content-Type": "application/x-www-form-urlencoded"}

  response = requests.post(token_url, data=payload, headers=headers)
  token_data = response.json()

  access_token = token_data.get("access_token")
  print("\n--- YOUR ACCESS TOKEN ---")
  print(access_token)

  # Fetch User Profile URN
  profile_url = "https://api.linkedin.com/v2/userinfo"
  user_headers = {"Authorization": f"Bearer {access_token}"}
  user_info = requests.get(profile_url, headers=user_headers).json()

  person_urn = f"urn:li:person:{user_info.get('sub')}"
  print("\n--- YOUR PERSON URN ---")
  print(person_urn)