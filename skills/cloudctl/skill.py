"""Main cloudctl skill implementation for Claude."""

import json
import os
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.syntax import Syntax

from .models import CloudContext, CloudProvider, CommandResult, CommandStatus, OperationLog, SkillConfig


class CloudctlSkill:
    """Autonomous cloud context and operation management skill."""

    def __init__(self, config: Optional[SkillConfig] = None):
        """Initialize the skill with configuration.

        Args:
            config: SkillConfig instance or None to use environment defaults.
        """
        self.config = config or SkillConfig.from_env()
        self.console = Console()
        self._context_cache: Optional[CloudContext] = None
        self._operation_log: list[OperationLog] = []

    async def switch_context(
        self,
        organization: str,
        account_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> CommandResult:
        """Switch cloud context to specified organization/account/role.

        Args:
            organization: Organization name
            account_id: AWS account ID or GCP project ID
            role: IAM role or GCP role

        Returns:
            CommandResult with switch operation status
        """
        if not organization:
            raise ValueError("Organization is required")

        cmd_parts = ["switch", organization]
        if account_id:
            cmd_parts.append(account_id)
        if role:
            cmd_parts.append(role)

        result = await self._execute_cloudctl(cmd_parts)

        if result.success and self.config.verify_context_after_switch:
            context = await self.get_context()
            self._context_cache = context
            self.console.print(f"[green]✅ Switched to context: {context}[/green]")
        elif not result.success:
            self.console.print(f"[red]❌ Context switch failed: {result.stderr}[/red]")

        return result

    async def login(self, organization: str) -> CommandResult:
        """Authenticate with specified organization's cloud provider.

        Args:
            organization: Organization name to authenticate

        Returns:
            CommandResult with login status
        """
        if not organization:
            raise ValueError("Organization is required")

        result = await self._execute_cloudctl(["login", organization])

        if result.success:
            self.console.print(f"[green]✅ Authenticated to {organization}[/green]")
        else:
            self.console.print(f"[red]❌ Authentication failed: {result.stderr}[/red]")

        return result

    async def get_context(self) -> CloudContext:
        """Get current cloud context.

        Returns:
            CloudContext with current provider, org, account, role, etc.
        """
        result = await self._execute_cloudctl(["env", "--json"])

        if not result.success:
            raise RuntimeError(f"Failed to get context: {result.stderr}")

        try:
            data = json.loads(result.stdout)
            provider = CloudProvider(data.get("provider", "aws"))

            return CloudContext(
                provider=provider,
                organization=data.get("organization", "unknown"),
                account_id=data.get("account_id"),
                role=data.get("role"),
                region=data.get("region"),
                project_id=data.get("project_id"),
            )
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Failed to parse context: {e}")

    async def list_organizations(self) -> list[dict]:
        """List all configured organizations.

        Returns:
            List of organization configuration dicts
        """
        result = await self._execute_cloudctl(["org", "list", "--json"])

        if not result.success:
            raise RuntimeError(f"Failed to list organizations: {result.stderr}")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse organizations: {e}")

    async def list_accounts(self, organization: str) -> list[dict]:
        """List accounts for organization.

        Args:
            organization: Organization name

        Returns:
            List of account configuration dicts
        """
        result = await self._execute_cloudctl(["accounts", organization, "--json"])

        if not result.success:
            raise RuntimeError(f"Failed to list accounts: {result.stderr}")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse accounts: {e}")

    async def execute_command(self, command: list[str], verify_context: bool = True) -> CommandResult:
        """Execute arbitrary cloudctl command.

        Args:
            command: Command parts as list
            verify_context: Verify context after execution

        Returns:
            CommandResult
        """
        result = await self._execute_cloudctl(command)

        if verify_context and result.success:
            try:
                context = await self.get_context()
                self._context_cache = context
            except Exception as e:
                self.console.print(f"[yellow]⚠️  Failed to verify context: {e}[/yellow]")

        return result

    async def verify_credentials(self, organization: str) -> bool:
        """Verify that credentials for organization are valid.

        Args:
            organization: Organization to check

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            result = await self._execute_cloudctl(["env", organization])
            return result.success
        except Exception:
            return False

    async def _execute_cloudctl(self, args: list[str], retries: int = 0) -> CommandResult:
        """Execute cloudctl command with error handling and retries.

        Args:
            args: Command arguments (without 'cloudctl' itself)
            retries: Current retry count (internal use)

        Returns:
            CommandResult with execution details
        """
        if retries > self.config.max_retries:
            return CommandResult(
                status=CommandStatus.FAILURE,
                return_code=1,
                stderr=f"Max retries ({self.config.max_retries}) exceeded",
                command=" ".join(args),
            )

        cmd = [self.config.cloudctl_path] + args

        if self.config.dry_run:
            self.console.print(f"[dim][DRY RUN] {' '.join(cmd)}[/dim]")
            return CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="[dry run]",
                command=" ".join(args),
            )

        try:
            start_time = time.time()
            env = os.environ.copy()
            env.update(self.config.environment_overrides)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                env=env,
            )

            duration = time.time() - start_time
            status = CommandStatus.SUCCESS if result.returncode == 0 else CommandStatus.FAILURE

            return CommandResult(
                status=status,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                command=" ".join(args),
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired:
            if retries < self.config.max_retries:
                self.console.print(f"[yellow]⚠️  Timeout, retrying... ({retries + 1}/{self.config.max_retries})[/yellow]")
                return await self._execute_cloudctl(args, retries + 1)

            return CommandResult(
                status=CommandStatus.TIMEOUT,
                return_code=124,
                stderr=f"Command timed out after {self.config.timeout_seconds} seconds",
                command=" ".join(args),
            )

        except FileNotFoundError:
            return CommandResult(
                status=CommandStatus.FAILURE,
                return_code=127,
                stderr=f"cloudctl not found at {self.config.cloudctl_path}. Install with: pip install cloudctl",
                command=" ".join(args),
            )

        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILURE,
                return_code=1,
                stderr=f"Error executing cloudctl: {str(e)}",
                command=" ".join(args),
            )

    def log_operation(
        self,
        operation: str,
        result: CommandResult,
        context_before: Optional[CloudContext] = None,
        context_after: Optional[CloudContext] = None,
    ) -> None:
        """Log operation for audit trail.

        Args:
            operation: Operation name
            result: CommandResult
            context_before: Context before operation
            context_after: Context after operation
        """
        if not self.config.enable_audit_logging:
            return

        log_entry = OperationLog(
            timestamp=datetime.utcnow().isoformat(),
            operation=operation,
            context_before=context_before,
            context_after=context_after,
            result=result,
            user=os.getenv("USER"),
            success=result.success,
        )

        self._operation_log.append(log_entry)

        # Write to audit log file
        log_dir = Path.home() / ".config" / "cloudctl" / "audit"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"operations_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        try:
            with open(log_file, "a") as f:
                f.write(log_entry.json() + "\n")
        except Exception as e:
            self.console.print(f"[yellow]⚠️  Failed to write audit log: {e}[/yellow]")

    def get_operation_log(self) -> list[OperationLog]:
        """Get in-memory operation log.

        Returns:
            List of logged operations from this session
        """
        return self._operation_log.copy()

    def print_context(self) -> None:
        """Print current context in human-readable format."""
        try:
            if self._context_cache:
                context = self._context_cache
            else:
                import asyncio

                context = asyncio.run(self.get_context())

            self.console.print("[bold cyan]Current Cloud Context[/bold cyan]")
            self.console.print(f"  Provider:     [yellow]{context.provider.value}[/yellow]")
            self.console.print(f"  Organization: [yellow]{context.organization}[/yellow]")
            if context.account_id:
                self.console.print(f"  Account:      [yellow]{context.account_id}[/yellow]")
            if context.role:
                self.console.print(f"  Role:         [yellow]{context.role}[/yellow]")
            if context.region:
                self.console.print(f"  Region:       [yellow]{context.region}[/yellow]")
            if context.project_id:
                self.console.print(f"  Project:      [yellow]{context.project_id}[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error getting context: {e}[/red]")
