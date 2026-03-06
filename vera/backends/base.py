"""StorageBackend — interface abstrata para acesso a dados.

O core NUNCA importa Notion (ou qualquer backend concreto) diretamente.
Tudo passa por esta interface. Cada método retorna dicts genéricos.
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Interface abstrata para storage de dados."""

    @abstractmethod
    async def query(
        self,
        collection_id: str,
        filters: dict | None = None,
        sorts: list | None = None,
        max_pages: int = 1,
    ) -> list[dict]:
        """Busca registros de uma collection (database/table/etc)."""
        ...

    @abstractmethod
    async def query_parallel(self, queries: list[dict]) -> dict[str, list[dict]]:
        """Busca múltiplas collections em paralelo.

        Cada query: {"collection_id": str, "filters": dict, "label": str}
        Retorna: {"label": [records]}
        """
        ...

    @abstractmethod
    async def create_record(self, collection_id: str, properties: dict) -> dict:
        """Cria um registro em uma collection."""
        ...

    @abstractmethod
    async def update_record(self, record_id: str, properties: dict) -> dict:
        """Atualiza um registro existente."""
        ...

    @abstractmethod
    def extract_text(self, record: dict) -> str:
        """Extrai texto legível de um registro (Notion rich text, etc)."""
        ...
