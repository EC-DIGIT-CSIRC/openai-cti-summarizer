
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials


security = HTTPBasic()

# fake users to simulate authentication
fake_users = {
    "digit": "united we stand, divided we fall!",
}

# dependency to check if the credentials are valid
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    print(f"get_current_username: {username}/{password}")
    if username in fake_users and password == fake_users[username]:
        return username
    raise HTTPException(status_code=401, detail="Invalid credentials")

