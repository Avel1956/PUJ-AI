"""rag_engine.py — Motor RAG con LangChain + ChromaDB + sentence-transformers."""
import os
import hashlib
import time
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASIGNATURAS_DIR = os.path.join(BASE_DIR, "asignaturas")
VECTORSTORE_DIR = os.path.join(BASE_DIR, ".vectorstores")


class MotorRAG:
    """Carga documentos de una asignatura, indexa en ChromaDB, y provee retrieval."""

    def __init__(self, nombre_asignatura: str):
        self.nombre = nombre_asignatura
        self.ruta = os.path.join(ASIGNATURAS_DIR, nombre_asignatura)
        self.ruta_docs = os.path.join(self.ruta, "documentos")
        self.persist_dir = os.path.join(VECTORSTORE_DIR, nombre_asignatura)

        # Embedder ligero (~80 MB) — compatible con Streamlit Cloud (1 GB RAM)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )

        self.documents: list[Document] = []
        self.vectorstore: Chroma | None = None
        self._fingerprint: str = ""

    # ----- Carga de documentos -----
    def cargar_documentos(self) -> int:
        """Carga PDFs, .txt, .md desde documentos/. Retorna cuántos docs cargó."""
        self.documents = []
        if not os.path.isdir(self.ruta_docs):
            return 0

        for archivo in sorted(os.listdir(self.ruta_docs)):
            ruta_completa = os.path.join(self.ruta_docs, archivo)
            try:
                if archivo.endswith(".pdf"):
                    loader = PyPDFLoader(ruta_completa)
                    self.documents.extend(loader.load())
                elif archivo.endswith((".txt", ".md")):
                    loader = TextLoader(ruta_completa, encoding="utf-8")
                    self.documents.extend(loader.load())
            except Exception:
                continue

        return len(self.documents)

    # ----- Fingerprint para cache -----
    def _calcular_fingerprint(self) -> str:
        """Hash del contenido de la carpeta documentos/ para detectar cambios."""
        hasher = hashlib.md5()
        if not os.path.isdir(self.ruta_docs):
            return ""
        for archivo in sorted(os.listdir(self.ruta_docs)):
            ruta = os.path.join(self.ruta_docs, archivo)
            hasher.update(archivo.encode())
            hasher.update(str(os.path.getmtime(ruta)).encode())
            hasher.update(str(os.path.getsize(ruta)).encode())
        return hasher.hexdigest()

    # ----- Indexación -----
    def indexar(self, force: bool = False) -> bool:
        """
        Crea/actualiza el índice vectorial.
        Si el fingerprint no cambió y no se fuerza, reutiliza el índice existente.
        Retorna True si indexó desde cero.
        """
        fp_actual = self._calcular_fingerprint()
        if not force and fp_actual == self._fingerprint and self.vectorstore is not None:
            return False

        self.cargar_documentos()
        if not self.documents:
            self.vectorstore = None
            self._fingerprint = fp_actual
            return True

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(self.documents)

        os.makedirs(self.persist_dir, exist_ok=True)

        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_dir,
        )
        self._fingerprint = fp_actual
        return True

    # ----- Retrieval -----
    def recuperar(self, consulta: str, k: int = 4) -> list[str]:
        """Recupera los k fragmentos más relevantes."""
        if self.vectorstore is None:
            return []
        docs = self.vectorstore.similarity_search(consulta, k=k)
        return [d.page_content for d in docs]

    def esta_listo(self) -> bool:
        """True si hay documentos indexados y listos para retrieval."""
        return self.vectorstore is not None and len(self.documents) > 0


# ============================================================
# Gestor de asignaturas
# ============================================================
class GestorAsignaturas:
    """Escanea la carpeta asignaturas/ y lista los cursos disponibles."""

    @staticmethod
    def listar() -> list[str]:
        if not os.path.isdir(ASIGNATURAS_DIR):
            return []
        return sorted([
            d for d in os.listdir(ASIGNATURAS_DIR)
            if os.path.isdir(os.path.join(ASIGNATURAS_DIR, d))
            and not d.startswith(".")
        ])

    @staticmethod
    def nombre_legible(slug: str) -> str:
        return slug.replace("-", " ").title()

    @staticmethod
    def tiene_documentos(slug: str) -> bool:
        ruta = os.path.join(ASIGNATURAS_DIR, slug, "documentos")
        return os.path.isdir(ruta) and len(os.listdir(ruta)) > 0
