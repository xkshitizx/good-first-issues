"""Utils for CLI"""
import re
import os
import shutil
import http.server
import socketserver
from pathlib import Path
from typing import Dict, Union, Optional

import requests
from gfi.graphql import services
from gfi.graphql.queries import rate_limit_query


# Global variables
home_dir: str = str(Path.home())
filename: str = "good-first-issues"
credential_dir: str = f"{home_dir}/.gfi"
credential_file: str = f"{credential_dir}/{filename}"


def add_credential(credential: str):
    """
    Write creds to .gfi/good-first-issue file if credential argument passed.
    Delete config folder if exists and create a new one.
    """
    if os.path.exists(credential_dir):
        shutil.rmtree(credential_dir)

    os.mkdir(credential_dir)

    with open(f"{credential_file}", "w+") as cred:
        cred.write(credential)

    print(f"Credentials saved to {credential_file}")


def check_credential() -> Union[str, bool]:
    """
    Check for GitHub credential in config file.
    Return if exists.
    """
    if os.path.exists(credential_file):
        with open(credential_file) as cred:
            return cred.readline()

    return False


def rate_limit() -> int:
    """
    Fetch rate_limit for GitHub REST API.
    """
    request_headers: Dict = dict()

    # Check if the token is available.
    token: Union[str, bool] = check_credential()

    if token:
        request_headers["Authorization"] = f"token {token}"

    response = requests.get(
        "https://api.github.com/rate_limit", headers=request_headers
    )
    data: Dict = response.json()

    return data["resources"].get("core").get("remaining")


def gql_rate_limit() -> int:
    """
    Fetch rate_limit for GraphQL API.
    """
    token: Union[str, bool] = check_credential()
    payload: Dict = services.caller(token, rate_limit_query, {})

    return payload["data"].get("rateLimit").get("remaining")


def identify_limit(limit: Optional[int], all: bool) -> Optional[int]:
    """
    Define the value of limiter based on the values passed.
    """
    if limit:
        return limit
    elif all:
        return None
    else:
        return 10


def web_server(html_data):
    """
    Start web server for obtained issues.
    """
    PORT = 8000
    Handler = http.server.SimpleHTTPRequestHandler
    filename = "index.html"

    url_data = add_anchor_tag(html_data)
    try:

        with open(filename, "w+") as file:
            file.write(html_template.format(table=url_data))

        socketserver.TCPServer.allow_reuse_address = True

        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print("serving at port", PORT)
            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        os.remove(filename)


def add_anchor_tag(html_data):
    """
    Use regex to get URL elements inside <td> tag and
    wrap them inside an anchor tag.
    """
    pattern = re.compile(r"<td>(https.+)<\/td>")
    matches = re.findall(pattern, html_data)

    for item in matches:
        url = f"<td><a target='_blank' href='{item}'>{item}</a></td>"
        html_data = re.sub(pattern, url, html_data)

    return html_data


# Template for displaying issues on web.
html_template = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      table {{
        border-collapse: collapse;
        width: 100%;
        font-family: sans-serif;
      }}

      th,
      td {{
        text-align: left;
        padding: 8px;
      }}

      tr:nth-child(even) {{
        background-color: #f2f2f2;
      }}

      th {{
        background-color: #009879;
        color: white;
      }}
    </style>
    <title>Good First Issues</title>
  </head>
  <body>
    <h1>Good First Issues</h1>
    {table}
  </body>
</html>

"""
