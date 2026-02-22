"""Messages models for Comdirect API."""

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Category-specific metadata of documents."""

    archived: bool = Field(
        default=False, description="Is document archived?"
    )
    date_read: str | None = Field(
        default=None,
        alias="dateRead",
        description="Date on which the document was read (YYYY-MM-DD)",
    )
    already_read: bool = Field(
        default=False, alias="alreadyRead", description="Has the document been read?"
    )
    predocument_exists: bool = Field(
        default=False,
        alias="predocumentExists",
        description="Does a predocument exist?",
    )

    class Config:
        populate_by_name = True


class Document(BaseModel):
    """Model for a document."""

    document_id: str = Field(
        ...,
        alias="documentId",
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
        alias="dateCreation",
        description="Date at which the Document was assigned to the client (YYYY-MM-DD)",
    )
    mime_type: str = Field(
        ...,
        alias="mimeType",
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
        alias="documentMetaData",
        description="Optional information about the document",
    )

    class Config:
        populate_by_name = True


class Documents(BaseModel):
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

    class Config:
        populate_by_name = True
