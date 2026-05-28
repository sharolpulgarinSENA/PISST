# app/services/email_service.py
import httpx
import os
import logging

logger = logging.getLogger(__name__)
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

RESEND_API_URL = "https://api.resend.com/emails"


def enviar_correo_reset(email_destino: str, nombre: str, token: str) -> bool:
    enlace = f"{FRONTEND_URL}/reset-password?token={token}"

    payload = {
        "from": f"PISST <{FROM_EMAIL}>",
        "to": [email_destino],
        "subject": "Recuperación de contraseña — PISST",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
          <h1 style="color: #1E3A5F;">PISST</h1>
          <p style="color: #666; font-size: 13px;">Plataforma Integral de Seguridad y Salud en el Trabajo</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
          <h2 style="color: #1E3A5F;">Hola, {nombre}</h2>
          <p style="color: #444; font-size: 15px; line-height: 1.6;">
            Recibimos una solicitud para restablecer la contraseña de tu cuenta en PISST.
          </p>
          <div style="text-align: center; margin: 32px 0;">
            <a href="{enlace}" style="background-color: #1d4ed8; color: white; padding: 14px 32px;
               text-decoration: none; border-radius: 8px; font-size: 15px; font-weight: bold; display: inline-block;">
              Restablecer contraseña
            </a>
          </div>
          <p style="color: #666; font-size: 13px;">Este enlace expira en <strong>30 minutos</strong>.</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="color: #999; font-size: 12px; text-align: center;">PISST — Este es un correo automático.</p>
        </div>
        """,
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(RESEND_API_URL, json=payload, headers=headers, timeout=10.0)
        if response.status_code in [200, 201]:
            logger.info(f"Correo enviado. ID: {response.json().get('id')}")
            return True
        else:
            logger.error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al enviar correo: {str(e)}")
        return False


def enviar_correo_bienvenida(email_destino: str, nombre: str, password_temporal: str) -> bool:
    payload = {
        "from": f"PISST <{FROM_EMAIL}>",
        "to": [email_destino],
        "subject": "Bienvenido a PISST — Tu cuenta ha sido creada",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
          <h1 style="color: #1E3A5F;">PISST</h1>
          <p style="color: #666; font-size: 13px;">Plataforma Integral de Seguridad y Salud en el Trabajo</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
          <h2 style="color: #1E3A5F;">Hola, {nombre}</h2>
          <p style="color: #444; font-size: 15px;">Tu cuenta en PISST ha sido creada exitosamente.</p>
          <div style="background: #F1EFE8; border-radius: 8px; padding: 20px; margin: 24px 0;">
            <p style="margin: 0 0 8px; color: #444; font-size: 14px;"><strong>Correo:</strong> {email_destino}</p>
            <p style="margin: 0; color: #444; font-size: 14px;">
              <strong>Contraseña temporal:</strong>
              <span style="font-family: monospace; background: #fff; padding: 2px 8px;
                     border-radius: 4px; border: 1px solid #ddd;">{password_temporal}</span>
            </p>
          </div>
          <div style="text-align: center; margin: 28px 0;">
            <a href="{FRONTEND_URL}/login" style="background-color: #1d4ed8; color: white; padding: 14px 32px;
               text-decoration: none; border-radius: 8px; font-size: 15px; font-weight: bold; display: inline-block;">
              Ingresar a PISST
            </a>
          </div>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="color: #999; font-size: 12px; text-align: center;">PISST — Este es un correo automático.</p>
        </div>
        """,
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(RESEND_API_URL, json=payload, headers=headers, timeout=10.0)
        if response.status_code in [200, 201]:
            logger.info(f"Correo bienvenida enviado. ID: {response.json().get('id')}")
            return True
        else:
            logger.error(f"Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al enviar correo de bienvenida: {str(e)}")
        return False
    
    