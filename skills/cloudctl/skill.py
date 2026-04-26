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

from .models import (
    CloudContext,
    CloudProvider,
    CommandResult,
    CommandStatus,
    HealthCheckResult,
    OperationLog,
    SkillConfig,
    TokenStatus,
)


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
        self._cloudctl_available = self._check_cloudctl_installed()

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

        # Log current context before switch
        try:
            old_context = await self.get_context()
            self.console.print(f"[dim]📍 Current: {old_context}[/dim]")
        except Exception:
            pass

        cmd_parts = ["switch", organization]
        if account_id:
            cmd_parts.append(account_id)
        if role:
            cmd_parts.append(role)

        result = await self._execute_cloudctl(cmd_parts)

        if result.success and self.config.verify_context_after_switch:
            context = await self.get_context()
            self._context_cache = context
            self.console.print(f"[green]✅ Switched to: {context}[/green]")
        elif not result.success:
            self.console.print(f"[red]❌ Context switch failed: {result.stderr}[/red]")

        return result

    async def switch_region(self, region: str) -> CommandResult:
        """Switch to a different region in current context.

        Args:
            region: Region name (e.g., us-west-2, eu-central-1)

        Returns:
            CommandResult with switch operation status
        """
        if not region:
            raise ValueError("Region is required")

        result = await self._execute_cloudctl(["switch", "region", region])

        if result.success:
            context = await self.get_context()
            self._context_cache = context
            self.console.print(f"[green]✅ Switched region to: {region}[/green]")
        else:
            self.console.print(f"[red]❌ Region switch failed: {result.stderr}[/red]")

        return result

    async def switch_project(self, project_id: str) -> CommandResult:
        """Switch to a different GCP project in current context.

        Args:
            project_id: GCP project ID

        Returns:
            CommandResult with switch operation status
        """
        if not project_id:
            raise ValueError("Project ID is required")

        result = await self._execute_cloudctl(["switch", "project", project_id])

        if result.success:
            context = await self.get_context()
            self._context_cache = context
            self.console.print(f"[green]✅ Switched project to: {project_id}[/green]")
        else:
            self.console.print(f"[red]❌ Project switch failed: {result.stderr}[/red]")

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
        # Log current context before executing
        try:
            context = await self.get_context()
            self._context_cache = context
            self.console.print(f"[dim]📍 Operating in: {context}[/dim]")
        except Exception:
            pass

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

    async def get_token_status(self, organization: str) -> TokenStatus:
        """Get token expiry status for an organization.

        Gracefully handles older cloudctl versions that don't support 'token status'.

        Args:
            organization: Organization name

        Returns:
            TokenStatus with expiry information (valid=False if unavailable)
        """
        try:
            result = await self._execute_cloudctl(["token", "status", organization, "--json"])

            # If command not found (old version), try fallback method
            if result.return_code == 127 or "not found" in result.stderr.lower():
                # Graceful degradation: just check if credentials work
                verify_result = await self.verify_credentials(organization)
                return TokenStatus(
                    organization=organization,
                    provider=CloudProvider.AWS,
                    valid=verify_result,
                )

            if not result.success:
                return TokenStatus(
                    organization=organization,
                    provider=CloudProvider.AWS,
                    valid=False,
                )

            try:
                data = json.loads(result.stdout)
                provider = CloudProvider(data.get("provider", "aws"))
                expires_at = data.get("expires_at")
                expires_in_seconds = data.get("expires_in_seconds")
                is_expired = data.get("is_expired", False)

                return TokenStatus(
                    organization=organization,
                    provider=provider,
                    valid=True,
                    expires_at=expires_at,
                    expires_in_seconds=expires_in_seconds,
                    is_expired=is_expired,
                )
            except (json.JSONDecodeError, ValueError):
                return TokenStatus(
                    organization=organization,
                    provider=CloudProvider.AWS,
                    valid=False,
                )
        except Exception:
            return TokenStatus(
                organization=organization,
                provider=CloudProvider.AWS,
                valid=False,
            )

    async def check_all_credentials(self) -> dict:
        """Check credentials and token status across all organizations.

        Returns:
            Dict with org names as keys, status dicts as values:
            {
                "org1": {"valid": True, "token_expires_in": 3600, "accessible": True},
                "org2": {"valid": False, "token_expires_in": None, "accessible": False},
            }
        """
        try:
            orgs = await self.list_organizations()
        except Exception as e:
            self.console.print(f"[red]Failed to list organizations: {e}[/red]")
            return {}

        results = {}

        for org in orgs:
            org_name = org.get("name", "")
            if not org_name:
                continue

            # Check if credentials are valid
            try:
                is_valid = await self.verify_credentials(org_name)
            except Exception:
                is_valid = False

            # Check token status
            token_status = await self.get_token_status(org_name)

            # Try to access the cloud
            try:
                test_result = await self._execute_cloudctl(["env", org_name])
                is_accessible = test_result.success
            except Exception:
                is_accessible = False

            results[org_name] = {
                "valid": token_status.valid,
                "token_expires_in": token_status.expires_in_seconds,
                "is_expired": token_status.is_expired,
                "accessible": is_accessible,
            }

            # Print status for each org
            if token_status.is_expired:
                self.console.print(f"[red]⏰ {org_name}: Token EXPIRED[/red]")
            elif token_status.valid and token_status.expires_in_seconds:
                if token_status.expires_in_seconds < 3600:
                    self.console.print(
                        f"[yellow]🟡 {org_name}: Token expires in {token_status.expires_in_seconds // 60}m[/yellow]"
                    )
                elif token_status.expires_in_seconds < 86400:
                    hours = token_status.expires_in_seconds / 3600
                    self.console.print(f"[cyan]ℹ️  {org_name}: Valid for {int(hours)}h[/cyan]")
                else:
                    self.console.print(f"[green]✅ {org_name}: Valid[/green]")
            elif not token_status.valid:
                self.console.print(f"[red]❌ {org_name}: Invalid or missing credentials[/red]")

        return results

    async def validate_switch(self) -> bool:
        """Validate that context switch was successful.

        Useful after switch_context to ensure you're in the right place.

        Returns:
            True if current context is valid and accessible, False otherwise
        """
        try:
            context = await self.get_context()
            # Try to access current org to validate
            result = await self._execute_cloudctl(["env", context.organization])
            return result.success
        except Exception:
            return False

    async def health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check on cloudctl setup.

        Returns:
            HealthCheckResult with diagnostic information
        """
        result = HealthCheckResult(
            cloudctl_installed=self._cloudctl_available,
        )

        if not result.cloudctl_installed:
            result.issues.append(
                f"cloudctl not found at {self.config.cloudctl_path}. Install or set CLOUDCTL_PATH environment variable."
            )
            return result

        # Check version
        try:
            version_result = await self._execute_cloudctl(["--version"])
            if version_result.success:
                result.cloudctl_version = version_result.stdout.strip()
        except Exception:
            pass

        # Check credentials
        try:
            orgs = await self.list_organizations()
            result.organizations_available = len(orgs)

            if result.organizations_available == 0:
                result.issues.append("No organizations configured")
                result.has_credentials = False
            else:
                result.has_credentials = True

                # Try to access at least one org
                for org in orgs:
                    if await self.verify_credentials(org.get("name", "")):
                        result.can_access_cloud = True
                        break

                if not result.can_access_cloud:
                    result.warnings.append("Configured organizations found but unable to access any")

                # Check token expiry for each org
                for org in orgs:
                    token_status = await self.get_token_status(org.get("name", ""))
                    if token_status.expires_in_seconds and token_status.expires_in_seconds < 3600:
                        result.warnings.append(
                            f"{org.get('name', '')}: Token expires in {token_status.expires_in_seconds // 60} minutes"
                        )

        except Exception as e:
            result.issues.append(f"Failed to check credentials: {str(e)}")

        return result

    def _check_cloudctl_installed(self) -> bool:
        """Check if cloudctl is installed at configured path.

        Returns:
            True if cloudctl is available, False otherwise
        """
        try:
            result = subprocess.run(
                [self.config.cloudctl_path, "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def _execute_cloudctl(
        self, args: list[str], retries: int = 0, auto_refresh_attempted: bool = False
    ) -> CommandResult:
        """Execute cloudctl command with error handling and retries.

        Args:
            args: Command arguments (without 'cloudctl' itself)
            retries: Current retry count (internal use)
            auto_refresh_attempted: Track if token refresh was already tried

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

            cmd_result = CommandResult(
                status=status,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                command=" ".join(args),
                duration_seconds=duration,
            )

            # Auto-refresh on token expiry if not already attempted
            if (
                not cmd_result.success
                and not auto_refresh_attempted
                and self._should_auto_refresh_token(cmd_result, args)
            ):
                self.console.print("[yellow]⏰ Token expired, attempting to refresh...[/yellow]")
                try:
                    # Extract organization from command if possible
                    org_to_refresh = None
                    if len(args) > 1 and args[0] in ["env", "switch"]:
                        org_to_refresh = args[1]

                    if org_to_refresh:
                        login_result = await self.login(org_to_refresh)
                        if login_result.success:
                            self.console.print(f"[green]✅ Re-authenticated to {org_to_refresh}[/green]")
                            # Retry original command
                            return await self._execute_cloudctl(
                                args, retries=retries + 1, auto_refresh_attempted=True
                            )
                except Exception as e:
                    self.console.print(f"[yellow]⚠️  Auto-refresh failed: {e}[/yellow]")

            return cmd_result

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

    def _should_auto_refresh_token(self, result: CommandResult, args: list[str]) -> bool:
        """Check if we should auto-refresh token and retry.

        Args:
            result: CommandResult with potential error
            args: Command arguments

        Returns:
            True if token refresh should be attempted
        """
        if result.success:
            return False

        error_text = (result.stderr + result.stdout).lower()
        token_errors = ["unauthorized", "token expired", "token invalid", "not authenticated", "invalid credentials"]

        for error in token_errors:
            if error in error_text:
                # Only auto-refresh for context commands, not for login itself
                if args and args[0] not in ["login"]:
                    return True

        return False

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
