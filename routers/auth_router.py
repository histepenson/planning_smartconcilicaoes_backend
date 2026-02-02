from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from middleware.auth import get_current_user, CurrentUser
from schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SelectEmpresaRequest,
    SelectEmpresaResponse,
    UserMe,
)
from services.auth_service import (
    login,
    refresh_access_token,
    logout,
    request_password_reset,
    reset_password,
    select_empresa,
    me,
)
from models import Usuario


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def auth_login(payload: LoginRequest, db: Session = Depends(get_db)):
    return login(db, payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
def auth_refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    return refresh_access_token(db, payload.refresh_token)


@router.post("/logout")
def auth_logout(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    return logout(db, payload.refresh_token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def auth_forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return request_password_reset(db, payload.email)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def auth_reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    return reset_password(db, payload.token, payload.new_password)


@router.post("/select-empresa", response_model=SelectEmpresaResponse)
def auth_select_empresa(
    payload: SelectEmpresaRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(Usuario).filter(Usuario.id == current_user.user_id).first()
    return select_empresa(db, user, payload.empresa_id)


@router.get("/me", response_model=UserMe)
def auth_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(Usuario).filter(Usuario.id == current_user.user_id).first()
    return me(db, user, current_user.empresa_id)
