CALLBACK_URL_BOT = "http://localhost:4343/oauth?scopes=" + "%20".join([
    "user:read:chat",
    "user:write:chat",
    "user:bot",
]) + "&force_verify=true"

CALLBACK_URL_OWNER = "http://localhost:4343/oauth?scopes=channel:bot&force_verify=true"
