import fitz

_model = None


def get_model():
    global _model
    if _model is None:
        from app.core.config import settings
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def extrair_texto_pdf(caminho_pdf: str) -> str:
    doc    = fitz.open(caminho_pdf)
    partes = [p.get_text("text") for p in doc if p.get_text("text").strip()]
    doc.close()
    if not partes:
        raise ValueError("PDF não contém texto extraível — pode ser imagem escaneada")
    return "\n".join(partes)


def vetorizar_texto(texto: str) -> list[float]:
    """Transforma qualquer texto em vetor normalizado (dim = EMBEDDING_DIM)."""
    vetor = get_model().encode(
        texto,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vetor.tolist()


def vetorizar_secoes(texto: str) -> dict[str, list[float] | None]:
    """
    Segmenta o currículo em seções e vetoriza cada uma.
    Seções não encontradas retornam None.

    Returns dict com chaves: exp, skills
    """
    from app.ai.section_extractor import extrair_secoes
    secoes = extrair_secoes(texto)
    return {
        "exp"   : vetorizar_texto(secoes["experiencia"]) if secoes["experiencia"].strip() else None,
        "skills": vetorizar_texto(secoes["habilidades"]) if secoes["habilidades"].strip() else None,
    }


def parsear_curriculo(caminho_pdf: str) -> dict:
    """Pipeline completo: PDF → texto → vetor principal + vetores de seção."""
    texto = extrair_texto_pdf(caminho_pdf)
    vetor = vetorizar_texto(texto)
    secs  = vetorizar_secoes(texto)
    return {
        "texto_extraido"  : texto,
        "vetor_embedding" : vetor,
        "vetor_secao_exp" : secs["exp"],
        "vetor_secao_skills": secs["skills"],
    }
