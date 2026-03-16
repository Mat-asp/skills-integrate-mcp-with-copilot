"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

# Demo users for authentication and role-based access.
users = {
    "admin@mergington.edu": {"password": "admin123", "role": "admin"},
    "teacher@mergington.edu": {"password": "teach123", "role": "teacher"},
    "emma@mergington.edu": {"password": "student123", "role": "student"},
    "olivia@mergington.edu": {"password": "student123", "role": "student"},
}

# In-memory bearer-token sessions.
sessions = {}

# In-memory password reset tokens.
reset_tokens = {}


class LoginRequest(BaseModel):
    email: str
    password: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


def _extract_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    return token


def get_current_user(authorization: Optional[str] = Header(default=None)):
    token = _extract_token(authorization)
    email = sessions.get(token)
    if not email or email not in users:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = users[email]
    return {"email": email, "role": user["role"], "token": token}


def ensure_can_manage_email(current_user: dict, email: str):
    if current_user["role"] == "student" and current_user["email"] != email:
        raise HTTPException(
            status_code=403,
            detail="Students can only manage their own activity registrations",
        )


def require_roles(current_user: dict, allowed_roles: set[str]):
    if current_user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient role permissions")


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/login")
def login(request: LoginRequest):
    user = users.get(request.email)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = str(uuid4())
    sessions[token] = request.email

    return {
        "message": "Login successful",
        "token": token,
        "user": {"email": request.email, "role": user["role"]},
    }


@app.post("/auth/logout")
def logout(current_user: dict = Depends(get_current_user)):
    sessions.pop(current_user["token"], None)
    return {"message": "Logout successful"}


@app.get("/auth/me")
def auth_me(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "role": current_user["role"],
    }


@app.post("/auth/password-reset/request")
def request_password_reset(request: PasswordResetRequest):
    if request.email not in users:
        raise HTTPException(status_code=404, detail="User not found")

    token = str(uuid4())
    reset_tokens[token] = request.email
    return {
        "message": "Password reset token generated",
        # Returned here to keep this demo self-contained.
        "reset_token": token,
    }


@app.post("/auth/password-reset/confirm")
def confirm_password_reset(request: PasswordResetConfirmRequest):
    email = reset_tokens.pop(request.token, None)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    users[email]["password"] = request.new_password
    return {"message": f"Password updated for {email}"}


@app.post("/admin/users")
def create_user(
    request: LoginRequest,
    role: str,
    current_user: dict = Depends(get_current_user),
):
    require_roles(current_user, {"admin"})

    if request.email in users:
        raise HTTPException(status_code=400, detail="User already exists")

    if role not in {"student", "teacher", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    users[request.email] = {"password": request.password, "role": role}
    return {
        "message": f"User {request.email} created",
        "user": {"email": request.email, "role": role},
    }


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    current_user: dict = Depends(get_current_user),
):
    """Sign up a student for an activity"""
    ensure_can_manage_email(current_user, email)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    current_user: dict = Depends(get_current_user),
):
    """Unregister a student from an activity"""
    ensure_can_manage_email(current_user, email)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
