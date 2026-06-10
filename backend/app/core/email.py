"""
Envio de e-mail transacional via SMTP.

Se SMTP_HOST não estiver configurado no .env, o envio é ignorado e a
função retorna False — o endpoint pode então devolver o link diretamente
na resposta (útil em desenvolvimento/testes).
"""
import smtplib
import ssl
from datetime import datetime
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


def _cor_score(score: float) -> str:
    if score >= 70:
        return "#2EE8B4"
    if score >= 50:
        return "#FCD34D"
    return "#FCA5A5"


def email_cv_processado(
    destinatario   : str,
    nome_rh        : str,
    candidato_nome : str,
    vaga_nome      : str,
    score          : float,
    explicacao     : dict | None = None,
) -> bool:
    cor   = _cor_score(score)
    comp  = (explicacao or {}).get("componentes", {})
    vaga_c = comp.get("aderencia_vaga",    {})
    mkt_c  = comp.get("aderencia_mercado", {})
    skills = (explicacao or {}).get("sinais_estruturais", {}).get("habilidades_em_comum", [])

    # Construir blocos HTML separadamente para evitar f-strings aninhados
    skills_html = "".join(
        '<span style="display:inline-block;margin:2px 4px 2px 0;padding:2px 8px;'
        'border-radius:6px;background:rgba(26,170,128,0.18);color:#2EE8B4;'
        'font-size:11px;font-family:monospace">' + s + '</span>'
        for s in skills[:8]
    )

    bloco_componentes = ""
    if vaga_c:
        bloco_componentes = (
            '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px"><tr>'
            '<td width="48%" style="padding:12px 16px;background:rgba(26,139,191,0.12);'
            'border-radius:10px;border:1px solid rgba(26,139,191,0.2)">'
            '<p style="margin:0 0 2px;font-size:10px;color:rgba(125,216,240,0.4);'
            'text-transform:uppercase;letter-spacing:0.8px">Aderência à vaga</p>'
            '<p style="margin:0;font-size:18px;font-weight:700;color:#4DC8E8;font-family:monospace">'
            + str(vaga_c.get("score", 0)) + '/100</p>'
            '<p style="margin:2px 0 0;font-size:11px;color:rgba(125,216,240,0.35)">Peso '
            + str(vaga_c.get("peso", "—")) + " · " + str(vaga_c.get("classificacao", "")).capitalize() + '</p>'
            '</td><td width="4%"></td>'
            '<td width="48%" style="padding:12px 16px;background:rgba(26,139,191,0.08);'
            'border-radius:10px;border:1px solid rgba(26,139,191,0.15)">'
            '<p style="margin:0 0 2px;font-size:10px;color:rgba(125,216,240,0.4);'
            'text-transform:uppercase;letter-spacing:0.8px">Aderência ao mercado</p>'
            '<p style="margin:0;font-size:18px;font-weight:700;color:#4DC8E8;font-family:monospace">'
            + str(mkt_c.get("score", 0)) + '/100</p>'
            '<p style="margin:2px 0 0;font-size:11px;color:rgba(125,216,240,0.35)">Peso '
            + str(mkt_c.get("peso", "—")) + " · " + str(mkt_c.get("classificacao", "")).capitalize() + '</p>'
            '</td></tr></table>'
        )

    bloco_skills = ""
    if skills:
        bloco_skills = (
            '<div style="margin-bottom:16px">'
            '<p style="margin:0 0 6px;font-size:11px;color:rgba(125,216,240,0.4);'
            'text-transform:uppercase;letter-spacing:0.8px">Skills em comum</p>'
            + skills_html + '</div>'
        )

    corpo = (
        '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#07111A;font-family:\'Segoe UI\',sans-serif">'
        '<table width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td align="center" style="padding:40px 16px">'
        '<table width="520" cellpadding="0" cellspacing="0" style="background:#0E2030;'
        'border-radius:16px;overflow:hidden;border:1px solid rgba(77,200,232,0.15)">'
        '<tr><td style="background:linear-gradient(135deg,#1A8BBF,#4DC8E8);padding:24px 32px">'
        '<p style="margin:0;font-size:20px;font-weight:700;color:#07111A">SIRS</p>'
        '<p style="margin:2px 0 0;font-size:11px;color:rgba(7,17,26,0.6)">'
        'Sistema Inteligente de Recrutamento e Seleção</p></td></tr>'
        '<tr><td style="padding:28px 32px">'
        '<p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#DFF0F6">Olá, ' + nome_rh + '</p>'
        '<p style="margin:0 0 20px;font-size:13px;color:rgba(125,216,240,0.55);line-height:1.6">'
        'O currículo de <strong style="color:#4DC8E8">' + candidato_nome + '</strong>'
        ' para a vaga <strong style="color:#4DC8E8">' + vaga_nome + '</strong> foi processado.</p>'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:rgba(14,80,104,0.3);'
        'border-radius:12px;margin-bottom:20px"><tr><td style="padding:18px 24px">'
        '<p style="margin:0 0 4px;font-size:11px;font-weight:700;color:rgba(125,216,240,0.4);'
        'text-transform:uppercase;letter-spacing:1px">Score curricular</p>'
        '<p style="margin:0;font-size:36px;font-weight:700;color:' + cor + ';font-family:monospace">'
        + str(score) + '<span style="font-size:16px;color:rgba(125,216,240,0.35)">/100</span></p>'
        '</td></tr></table>'
        + bloco_componentes
        + bloco_skills
        + '<a href="' + settings.FRONTEND_URL + '" style="display:inline-block;padding:12px 24px;'
        'border-radius:10px;background:linear-gradient(135deg,#1A8BBF,#4DC8E8);'
        'color:#07111A;font-weight:700;font-size:13px;text-decoration:none">'
        'Ver candidato no SIRS →</a>'
        '</td></tr>'
        '<tr><td style="padding:14px 32px 20px;border-top:1px solid rgba(77,200,232,0.08)">'
        '<p style="margin:0;font-size:10px;color:rgba(125,216,240,0.2)">'
        'SIRS — Sistema Inteligente de Recrutamento e Seleção</p></td></tr>'
        '</table></td></tr></table></body></html>'
    )

    assunto = f"SIRS — CV processado: {candidato_nome} → {vaga_nome} ({score}/100)"
    return enviar_email(destinatario, assunto, corpo)


_MESES = ["janeiro","fevereiro","março","abril","maio","junho",
          "julho","agosto","setembro","outubro","novembro","dezembro"]


def _fmt_data(dt: datetime) -> str:
    return f"{dt.day} de {_MESES[dt.month - 1]} de {dt.year}, às {dt.hour:02d}h{dt.minute:02d}"


def email_entrevista_agendada(
    destinatario       : str,
    nome_entrevistador : str,
    candidato_nome     : str,
    vaga_nome          : str,
    tipo               : str,       # "rh" | "tecnica"
    agendada_para      : datetime,
) -> bool:
    tipo_label = "Entrevista de RH" if tipo == "rh" else "Entrevista Técnica"
    data_fmt   = _fmt_data(agendada_para)
    assunto    = f"SIRS — {tipo_label} agendada: {candidato_nome}"

    corpo = (
        '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#07111A;font-family:\'Segoe UI\',sans-serif">'
        '<table width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td align="center" style="padding:40px 16px">'
        '<table width="500" cellpadding="0" cellspacing="0" style="background:#0E2030;'
        'border-radius:16px;overflow:hidden;border:1px solid rgba(77,200,232,0.15)">'

        # Header
        '<tr><td style="background:linear-gradient(135deg,#1A8BBF,#4DC8E8);padding:24px 32px">'
        '<p style="margin:0;font-size:20px;font-weight:700;color:#07111A">SIRS</p>'
        '<p style="margin:2px 0 0;font-size:11px;color:rgba(7,17,26,0.6)">Sistema Inteligente de Recrutamento e Seleção</p>'
        '</td></tr>'

        # Body
        '<tr><td style="padding:28px 32px">'
        '<p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#DFF0F6">Olá, ' + nome_entrevistador + '</p>'
        '<p style="margin:0 0 24px;font-size:13px;color:rgba(125,216,240,0.55);line-height:1.6">'
        'Uma <strong style="color:#4DC8E8">' + tipo_label.lower() + '</strong> foi agendada para você no SIRS.</p>'

        # Card com detalhes
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:rgba(14,80,104,0.3);'
        'border-radius:12px;margin-bottom:24px"><tr><td style="padding:20px 24px">'
        '<table width="100%" cellpadding="0" cellspacing="0">'

        '<tr><td style="padding-bottom:12px">'
        '<p style="margin:0 0 2px;font-size:10px;font-weight:700;color:rgba(125,216,240,0.4);'
        'text-transform:uppercase;letter-spacing:1px">Candidato</p>'
        '<p style="margin:0;font-size:15px;font-weight:600;color:#DFF0F6">' + candidato_nome + '</p>'
        '</td></tr>'

        '<tr><td style="padding-bottom:12px;border-top:1px solid rgba(77,200,232,0.08);padding-top:12px">'
        '<p style="margin:0 0 2px;font-size:10px;font-weight:700;color:rgba(125,216,240,0.4);'
        'text-transform:uppercase;letter-spacing:1px">Vaga</p>'
        '<p style="margin:0;font-size:14px;color:#4DC8E8">' + vaga_nome + '</p>'
        '</td></tr>'

        '<tr><td style="border-top:1px solid rgba(77,200,232,0.08);padding-top:12px">'
        '<p style="margin:0 0 2px;font-size:10px;font-weight:700;color:rgba(125,216,240,0.4);'
        'text-transform:uppercase;letter-spacing:1px">Data e hora</p>'
        '<p style="margin:0;font-size:14px;font-weight:600;color:#2EE8B4;font-family:monospace">' + data_fmt + '</p>'
        '</td></tr>'

        '</table></td></tr></table>'

        '<a href="' + settings.FRONTEND_URL + '" style="display:inline-block;padding:12px 24px;'
        'border-radius:10px;background:linear-gradient(135deg,#1A8BBF,#4DC8E8);'
        'color:#07111A;font-weight:700;font-size:13px;text-decoration:none">'
        'Abrir no SIRS →</a>'
        '</td></tr>'

        # Footer
        '<tr><td style="padding:14px 32px 20px;border-top:1px solid rgba(77,200,232,0.08)">'
        '<p style="margin:0;font-size:10px;color:rgba(125,216,240,0.2)">SIRS — Sistema Inteligente de Recrutamento e Seleção</p>'
        '</td></tr>'

        '</table></td></tr></table></body></html>'
    )
    return enviar_email(destinatario, assunto, corpo)


def email_triagem_resultado(
    destinatario   : str,
    nome_rh        : str,
    candidato_nome : str,
    vaga_nome      : str,
    aprovado       : bool,
) -> bool:
    cor_status  = "#2EE8B4" if aprovado else "#FCA5A5"
    label       = "Aprovado na triagem" if aprovado else "Reprovado na triagem"
    descricao   = (
        "O candidato foi <strong style='color:#2EE8B4'>aprovado</strong> e pode prosseguir para a entrevista de RH."
        if aprovado else
        "O candidato foi <strong style='color:#FCA5A5'>reprovado</strong> na triagem e não avançará no processo."
    )
    assunto = f"SIRS — Triagem: {candidato_nome} {'aprovado' if aprovado else 'reprovado'} → {vaga_nome}"

    corpo = (
        '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#07111A;font-family:\'Segoe UI\',sans-serif">'
        '<table width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td align="center" style="padding:40px 16px">'
        '<table width="500" cellpadding="0" cellspacing="0" style="background:#0E2030;'
        'border-radius:16px;overflow:hidden;border:1px solid rgba(77,200,232,0.15)">'

        # Header
        '<tr><td style="background:linear-gradient(135deg,#1A8BBF,#4DC8E8);padding:24px 32px">'
        '<p style="margin:0;font-size:20px;font-weight:700;color:#07111A">SIRS</p>'
        '<p style="margin:2px 0 0;font-size:11px;color:rgba(7,17,26,0.6)">Sistema Inteligente de Recrutamento e Seleção</p>'
        '</td></tr>'

        # Body
        '<tr><td style="padding:28px 32px">'
        '<p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#DFF0F6">Olá, ' + nome_rh + '</p>'
        '<p style="margin:0 0 24px;font-size:13px;color:rgba(125,216,240,0.55);line-height:1.6">'
        'A triagem da candidatura abaixo foi concluída no SIRS.</p>'

        # Card status
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:rgba(14,80,104,0.3);'
        'border-radius:12px;margin-bottom:24px"><tr><td style="padding:20px 24px">'
        '<table width="100%" cellpadding="0" cellspacing="0">'

        '<tr><td style="padding-bottom:12px">'
        '<p style="margin:0 0 2px;font-size:10px;font-weight:700;color:rgba(125,216,240,0.4);'
        'text-transform:uppercase;letter-spacing:1px">Candidato</p>'
        '<p style="margin:0;font-size:15px;font-weight:600;color:#DFF0F6">' + candidato_nome + '</p>'
        '</td></tr>'

        '<tr><td style="padding-bottom:12px;border-top:1px solid rgba(77,200,232,0.08);padding-top:12px">'
        '<p style="margin:0 0 2px;font-size:10px;font-weight:700;color:rgba(125,216,240,0.4);'
        'text-transform:uppercase;letter-spacing:1px">Vaga</p>'
        '<p style="margin:0;font-size:14px;color:#4DC8E8">' + vaga_nome + '</p>'
        '</td></tr>'

        '<tr><td style="border-top:1px solid rgba(77,200,232,0.08);padding-top:12px">'
        '<p style="margin:0 0 6px;font-size:10px;font-weight:700;color:rgba(125,216,240,0.4);'
        'text-transform:uppercase;letter-spacing:1px">Resultado</p>'
        '<p style="margin:0 0 8px;font-size:16px;font-weight:700;color:' + cor_status + '">' + label + '</p>'
        '<p style="margin:0;font-size:13px;color:rgba(125,216,240,0.55);line-height:1.5">' + descricao + '</p>'
        '</td></tr>'

        '</table></td></tr></table>'

        '<a href="' + settings.FRONTEND_URL + '" style="display:inline-block;padding:12px 24px;'
        'border-radius:10px;background:linear-gradient(135deg,#1A8BBF,#4DC8E8);'
        'color:#07111A;font-weight:700;font-size:13px;text-decoration:none">'
        'Abrir no SIRS →</a>'
        '</td></tr>'

        # Footer
        '<tr><td style="padding:14px 32px 20px;border-top:1px solid rgba(77,200,232,0.08)">'
        '<p style="margin:0;font-size:10px;color:rgba(125,216,240,0.2)">SIRS — Sistema Inteligente de Recrutamento e Seleção</p>'
        '</td></tr>'

        '</table></td></tr></table></body></html>'
    )
    return enviar_email(destinatario, assunto, corpo)
