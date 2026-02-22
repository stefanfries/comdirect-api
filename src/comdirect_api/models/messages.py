"""Messages models for Comdirect API."""

from pydantic import Field

from . import ComdirectBaseModel


class DocumentMetadata(ComdirectBaseModel):
    """Category-specific metadata of documents."""

    archived: bool = Field(
        default=False, description="Is document archived?"
    )
    date_read: str | None = Field(
        default=None,
        description="Date on which the document was read (YYYY-MM-DD)",
    )
    already_read: bool = Field(
        default=False, description="Has the document been read?"
    )
    predocument_exists: bool = Field(
        default=False,
        description="Does a predocument exist?",
    )


class Document(ComdirectBaseModel):
    """Model for a document."""

    document_id: str = Field(
        ...,
        description="Unique ID of the document (UUID)",
        max_length=32,
    )
    name: str = Field(
        ...,
        description="Name or description of the document",
        max_length=50,
    )
    date_creation: str = Field(
        ...,
        description="Date at which the Document was assigned to the client (YYYY-MM-DD)",
    )
    mime_type: str = Field(
        ...,
        description="The native mimeType of the document (e.g., application/pdf)",
    )
    deletable: bool = Field(
        default=False,
        description="Is the client allowed to delete the document?",
    )
    advertisement: bool = Field(
        default=False,
        description="Is the document advertising comdirect products?",
    )
    document_meta_data: DocumentMetadata | None = Field(
        default=None,
        description="Optional information about the document",
    )


class Documents(ComdirectBaseModel):
    """List of documents with pagination."""

    values: list[Document] = Field(
        default_factory=list, description="List of documents"
    )
    paging: dict | None = Field(
        default=None, description="Pagination information"
    )
    aggregated: dict | None = Field(
        default=None, description="Aggregated information"
    )
