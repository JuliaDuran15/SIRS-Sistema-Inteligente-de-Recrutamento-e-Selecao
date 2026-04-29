"""
Envio de e-mail transacional via SMTP.

Se SMTP_HOST não estiver configurado no .env, o envio é ignorado e a
função retorna False — o endpoint pode então devolver o link diretamente
na resposta (útil em desenvolvimento/testes).
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def smtp_configurado() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS)


def enviar_email(destinatario: str, assunto: str, corpo_html: str) -> bool:
    """
    Envia um e-mail HTML.
    Retorna True em caso de sucesso, False se SMTP não configurado ou erro.
    """
    if not smtp_configurado():
        return False

    remetente = settings.SMTP_FROM or settings.SMTP_USER
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"]    = remetente
    msg["To"]      = destinatario
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
            smtp.sendmail(remetente, destinatario, msg.as_string())
        return True
    except Exception as exc:
        print(f"[EMAIL] Falha ao enviar para {destinatario}: {exc}")
        return False


def email_reset_senha(destinatario: str, nome: str, reset_url: str) -> bool:
    assunto = "SIRS — Redefinição de senha"
    corpo   = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#07111A;font-family:'Segoe UI',sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#0E2030;border-radius:16px;overflow:hidden;border:1px solid rgba(77,200,232,0.15)">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1A8BBF,#4DC8E8);padding:28px 32px">
            <p style="margin:0;font-size:22px;font-weight:700;color:#07111A;letter-spacing:-0.5px">
              SIRS
            </p>
            <p style="margin:4px 0 0;font-size:12px;color:rgba(7,17,26,0.6)">
              Sistema Inteligente de Recrutamento e Seleção
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px">
            <p style="margin:0 0 8px;font-size:16px;font-weight:600;color:#DFF0F6">
              Olá, {nome}
            </p>
            <p style="margin:0 0 24px;font-size:14px;color:rgba(125,216,240,0.6);line-height:1.6">
              Recebemos uma solicitação para redefinir a senha da sua conta.
              Clique no botão abaixo para criar uma nova senha.
              O link é válido por <strong style="color:#4DC8E8">1 hora</strong>.
            </p>

            <a href="{reset_url}"
               style="display:inline-block;padding:14px 28px;border-radius:12px;
                      background:linear-gradient(135deg,#1A8BBF,#4DC8E8);
                      color:#07111A;font-weight:700;font-size:14px;text-decoration:none">
              Redefinir senha
            </a>

            <p style="margin:24px 0 0;font-size:12px;color:rgba(125,216,240,0.35);line-height:1.6">
              Se você não solicitou a redefinição de senha, ignore este e-mail.
              Sua senha permanece a mesma.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:16px 32px 24px;border-top:1px solid rgba(77,200,232,0.1)">
            <p style="margin:0;font-size:11px;color:rgba(125,216,240,0.25)">
              SIRS — Sistema Inteligente de Recrutamento e Seleção
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""
    return enviar_email(destinatario, assunto, corpo)
