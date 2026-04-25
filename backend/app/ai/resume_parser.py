import fitz
from sentence_transformers import SentenceTransformer

_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def extrair_texto_pdf(caminho_pdf: str) -> str:
    """
    Abre o PDF e extrai o texto de todas as páginas.
    """
    doc = fitz.open(caminho_pdf)
    paginas = []

    for pagina in doc:
        texto = pagina.get_text("text")
        if texto.strip():
            paginas.append(texto)

    doc.close()

    if not paginas:
        raise ValueError("PDF não contém texto extraível — pode ser imagem escaneada")

    return "\n".join(paginas)


def vetorizar_texto(texto: str) -> list[float]:
    """
    Transforma qualquer texto em um vetor de 384 dimensões.
    Usado tanto para currículos quanto para requisitos de vaga.
    """
    model = get_model()
    vetor = model.encode(
        texto,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vetor.tolist()


def parsear_curriculo(caminho_pdf: str) -> dict:
    """
    Pipeline completo: PDF → texto → vetor.
    Simples e direto — sem catálogo, sem NER.
    """
    texto = extrair_texto_pdf(caminho_pdf)
    vetor = vetorizar_texto(texto)

    return {
        "texto_extraido" : texto,
        "vetor_embedding": vetor,
    }