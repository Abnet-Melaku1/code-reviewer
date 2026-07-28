from pydantic import Field

from codereviewer.schemas.models import DomainModel, StrippedStrModel, VerbatimStr


class RepositoryUpdate(DomainModel):
    """Payload to update repository settings."""

    posting_enabled: bool


class RepositoryCreate(StrippedStrModel):
    """Payload to register a new GitHub repository."""

    github_installation_id: int = Field(gt=0)
    owner: str = Field(min_length=1)
    name: str = Field(min_length=1)
    default_branch: str = Field(default="main", min_length=1)


class ConventionUpdate(DomainModel):
    """Payload to toggle a convention's active status."""

    active: bool


class ConventionCreate(StrippedStrModel):
    """Payload to create a new user-defined convention."""

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    example_code: VerbatimStr | None = None
