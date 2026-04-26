"""Main Confluence documentation skill."""

import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from .code_scanner import CodeScanner
from .confluence_client import ConfluenceClient
from .doc_generators import create_generator, DocumentTemplate
from .guardrails import GuardailValidator, ApprovalGate
from .models import (
    SkillConfig,
    DocumentMetadata,
    DocumentChange,
    DocumentGenerationResult,
    ValidationError,
)


class ConfluenceSkill:
    """Center-of-excellence Confluence documentation skill."""

    def __init__(self, config: SkillConfig):
        """Initialize skill with configuration.

        Args:
            config: Skill configuration
        """
        self.config = config
        self.console = Console()
        self.client = ConfluenceClient(config.confluence)
        self.scanner = CodeScanner(config.code_analysis)
        self.validator = GuardailValidator(config.guardrails)
        self.approval_gate = ApprovalGate(
            require_approval=config.guardrails.require_approval,
            interactive=False,  # Can be set to True for interactive mode
        )
        self._operation_log: list[DocumentChange] = []

    def document(
        self,
        task: str,
        repos: Optional[list[str]] = None,
        doc_type: Optional[str] = None,
        space_key: Optional[str] = None,
        parent_page_title: Optional[str] = None,
        dry_run: Optional[bool] = None,
        interactive: bool = False,
    ) -> DocumentGenerationResult:
        """Generate documentation from task description and code.

        Args:
            task: Task description for documentation
            repos: List of repos to analyze (overrides config)
            doc_type: Document template type
            space_key: Target space key (overrides config)
            parent_page_title: Parent page title
            dry_run: Run in dry-run mode (overrides config default)
            interactive: Interactive mode for approvals

        Returns:
            DocumentGenerationResult with outcome
        """
        start_time = time.time()
        result = DocumentGenerationResult(
            success=False,
            dry_run=dry_run if dry_run is not None else self.config.guardrails.dry_run_by_default,
        )

        self.approval_gate.interactive = interactive

        try:
            self.console.print(f"\n[bold blue]Confluence Documentation Skill[/bold blue]")
            self.console.print(f"Task: {task}\n")

            # 1. Prepare configuration
            self.console.print("[cyan]1. Preparing configuration...[/cyan]")
            doc_config = self._prepare_config(doc_type, space_key, parent_page_title, repos)

            # 2. Scan code repositories
            self.console.print("[cyan]2. Analyzing code repositories...[/cyan]")
            extracted_info = self.scanner.scan_repos()
            self.console.print(f"   Found {len(extracted_info.get('apis', []))} APIs")
            self.console.print(f"   Found {len(extracted_info.get('dependencies', []))} dependencies")

            # 3. Generate metadata
            self.console.print("[cyan]3. Generating document metadata...[/cyan]")
            metadata = self._generate_metadata(task, doc_config)
            result.title = metadata.title

            # 4. Check for existing documents
            self.console.print("[cyan]4. Checking for existing documentation...[/cyan]")
            existing_page = self.client.find_page_by_title(doc_config.space_key, metadata.title)

            if existing_page:
                self.console.print(f"   Found existing page: {existing_page.get('id')}")
                result.document_id = existing_page.get("id")

                # Handle merge strategy
                merge_strategy = self._handle_existing_page(existing_page, metadata, doc_config)
                if merge_strategy == "skip":
                    result.success = True
                    result.errors.append(
                        ValidationError(
                            level="info",
                            field="merge",
                            message="Document exists and merge strategy is 'skip'",
                        )
                    )
                    return result

            # 5. Validate permissions
            self.console.print("[cyan]5. Validating permissions...[/cyan]")
            if not self.client.check_write_permission(doc_config.space_key):
                result.errors.append(
                    ValidationError(
                        level="error",
                        field="permissions",
                        message=f"No write permission for space '{doc_config.space_key}'",
                    )
                )
                return result

            # 6. Generate document content
            self.console.print("[cyan]6. Generating document content...[/cyan]")
            generator = create_generator(doc_config.template, metadata, extracted_info)
            content = generator.generate()

            # 7. Validate content
            self.console.print("[cyan]7. Validating document...[/cyan]")
            self.validator.validate_metadata(metadata)
            self.validator.validate_content(content, metadata)

            if self.validator.errors:
                for error in self.validator.errors:
                    result.errors.append(error)
                self.console.print(f"[red]{self.validator.get_summary()}[/red]")

            if self.validator.warnings:
                for warning in self.validator.warnings:
                    result.warnings.append(warning)
                self.console.print(f"[yellow]{self.validator.get_summary()}[/yellow]")

            # Preview content
            result.content_preview = content[:500] + "..." if len(content) > 500 else content

            # 8. Request approval if needed
            if self.approval_gate.require_approval and not result.dry_run:
                approved = self.approval_gate.request_approval(
                    metadata.title,
                    "CREATE" if not existing_page else "UPDATE",
                    f"Document: {metadata.title}",
                )
                if not approved:
                    result.errors.append(
                        ValidationError(
                            level="warning",
                            field="approval",
                            message="User declined to approve changes",
                        )
                    )
                    return result

            # 9. Write or preview
            if result.dry_run:
                self.console.print("[yellow]DRY RUN MODE - No changes written[/yellow]")
                result.success = len(result.errors) == 0
            else:
                self.console.print("[cyan]8. Writing to Confluence...[/cyan]")

                if existing_page:
                    page = self.client.update_page(
                        existing_page["id"],
                        metadata.title,
                        content,
                        labels=metadata.labels,
                    )
                    result.document_id = page["id"]
                    result.document_url = f"{self.config.confluence.instance_url}/wiki/spaces/{doc_config.space_key}/pages/{page['id']}"
                    self.console.print(f"[green]✅ Updated page: {page['id']}[/green]")

                    # Add audit comment
                    if self.config.output.create_audit_trail:
                        comment = f"Updated by Confluence Skill on {datetime.utcnow().isoformat()}"
                        self.client.add_page_comment(page["id"], f"<p>{comment}</p>")
                else:
                    page = self.client.create_page(
                        doc_config.space_key,
                        metadata.title,
                        content,
                        parent_page_id=self._get_parent_page_id(doc_config),
                        labels=metadata.labels,
                    )
                    result.document_id = page["id"]
                    result.document_url = f"{self.config.confluence.instance_url}/wiki/spaces/{doc_config.space_key}/pages/{page['id']}"
                    self.console.print(f"[green]✅ Created page: {page['id']}[/green]")

                result.success = True

        except Exception as e:
            self.console.print(f"[red]❌ Error: {str(e)}[/red]")
            result.errors.append(
                ValidationError(
                    level="error",
                    field="exception",
                    message=str(e),
                )
            )
            result.success = False

        finally:
            result.duration_seconds = time.time() - start_time
            self._print_result_summary(result)

        return result

    def _prepare_config(self, doc_type, space_key, parent_page_title, repos):
        """Prepare documentation configuration.

        Args:
            doc_type: Document type override
            space_key: Space key override
            parent_page_title: Parent page title override
            repos: Repos override

        Returns:
            Prepared configuration object
        """
        config = self.config.documentation

        # Override template
        if doc_type:
            try:
                config.template = DocumentTemplate(doc_type)
            except ValueError:
                self.console.print(f"[yellow]Unknown doc type: {doc_type}[/yellow]")

        # Override space and repos
        if space_key:
            config.space_key = space_key
        if not config.space_key:
            config.space_key = self.config.confluence.space_key

        if parent_page_title:
            config.parent_page = parent_page_title

        if repos:
            self.config.code_analysis.repos = [{"path": r} for r in repos]

        return config

    def _generate_metadata(self, task: str, doc_config) -> DocumentMetadata:
        """Generate document metadata.

        Args:
            task: Task description
            doc_config: Documentation configuration

        Returns:
            DocumentMetadata
        """
        # Auto-generate title from task if needed
        title = task if doc_config.auto_title else doc_config.parent_page

        metadata = DocumentMetadata(
            title=title,
            space_key=doc_config.space_key,
            version=doc_config.metadata.version or "1.0",
            owner=doc_config.metadata.owner,
            audience=doc_config.metadata.audience,
            status=doc_config.metadata.status.value if hasattr(doc_config.metadata.status, "value") else doc_config.metadata.status,
            labels=doc_config.metadata.labels or [],
            created_at=datetime.utcnow(),
        )

        return metadata

    def _handle_existing_page(self, existing_page: dict, metadata: DocumentMetadata, doc_config) -> Optional[str]:
        """Handle strategy for existing pages.

        Args:
            existing_page: Existing page data
            metadata: New metadata
            doc_config: Documentation configuration

        Returns:
            Merge strategy (append, replace, skip) or None
        """
        strategy = doc_config.merge_strategy.value if hasattr(doc_config.merge_strategy, "value") else doc_config.merge_strategy

        if strategy == "interactive":
            # Ask user
            result = self.approval_gate.request_merge_strategy(metadata.title)
            return result if result else "skip"

        self.console.print(f"   Using merge strategy: {strategy}")
        return strategy

    def _get_parent_page_id(self, doc_config) -> Optional[str]:
        """Get parent page ID.

        Args:
            doc_config: Documentation configuration

        Returns:
            Parent page ID or None
        """
        if doc_config.parent_page_id:
            return doc_config.parent_page_id

        if doc_config.parent_page:
            parent = self.client.find_page_by_title(doc_config.space_key, doc_config.parent_page)
            if parent:
                return parent.get("id")
            self.console.print(f"[yellow]Parent page not found: {doc_config.parent_page}[/yellow]")

        return None

    def _print_result_summary(self, result: DocumentGenerationResult) -> None:
        """Print result summary to console.

        Args:
            result: DocumentGenerationResult
        """
        summary = result.summary()
        color = "green" if result.success else "red"
        self.console.print(f"\n[{color}]{summary}[/{color}]")

        if result.content_preview:
            self.console.print("\n[bold]Content Preview:[/bold]")
            panel = Panel(result.content_preview[:300], expand=False)
            self.console.print(panel)
