"""
Dead Code Detector — O14: Detect and classify dead code in output.

Scans code output for unused imports, unreachable code, unwired
functions, commented blocks, and dead variables. Provides
classification (DELETE / KEEP_LEGACY / WIRE) and markdown reports.

Like a meticulous code reviewer who spots every unused import
and commented-out block.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IssueType(Enum):
    """Types of dead code issues."""
    UNUSED_IMPORT = "unused_import"
    UNREACHABLE_CODE = "unreachable_code"
    UNWIRED_FUNCTION = "unwired_function"
    COMMENTED_BLOCK = "commented_block"
    DEAD_VARIABLE = "dead_variable"


class DeadCodeVerdict(Enum):
    """What to do with detected dead code."""
    DELETE = "delete"
    KEEP_LEGACY = "keep_legacy"
    WIRE = "wire"


@dataclass
class DeadCodeIssue:
    """A single dead code issue found during scanning."""
    file: str = ""
    line: int = 0
    issue_type: IssueType = IssueType.UNUSED_IMPORT
    description: str = ""
    symbol: str = ""


# Python-specific patterns
_PYTHON_PATTERNS: dict[IssueType, list[str]] = {
    IssueType.UNUSED_IMPORT: [
        r"^import\s+(\w+)",
        r"^from\s+[\w.]+\s+import\s+(.+)",
    ],
    IssueType.UNREACHABLE_CODE: [
        r"return\s+.*\n\s+\S+",
        r"raise\s+.*\n\s+\S+",
        r"sys\.exit\s*\(.*\)\n\s+\S+",
    ],
    IssueType.UNWIRED_FUNCTION: [
        r"^(?:async\s+)?def\s+(\w+)\s*\(",
    ],
    IssueType.COMMENTED_BLOCK: [
        r"^\s*#\s*.*\n(\s*#\s*.*\n){2,}",
    ],
    IssueType.DEAD_VARIABLE: [
        r"^\s*(\w+)\s*=\s*.+",
    ],
}

# TypeScript-specific patterns
_TYPESCRIPT_PATTERNS: dict[IssueType, list[str]] = {
    IssueType.UNUSED_IMPORT: [
        r"^import\s+.*\s+from\s+",
        r"^import\s*\{[^}]+\}\s+from\s+",
    ],
    IssueType.UNREACHABLE_CODE: [
        r"return\s+.*;\n\s+\S+",
        r"throw\s+.*;\n\s+\S+",
    ],
    IssueType.UNWIRED_FUNCTION: [
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
        r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(",
    ],
    IssueType.COMMENTED_BLOCK: [
        r"/\*[\s\S]*?\*/",
        r"^\s*//\s*.*\n(\s*//\s*.*\n){2,}",
    ],
    IssueType.DEAD_VARIABLE: [
        r"(?:const|let|var)\s+(\w+)\s*=\s*.+",
    ],
}


class DeadCodeDetector:
    """
    Dead Code Detector — find and classify dead code.

    Language-specific scanners for Python and TypeScript use
    regex-based detection. Each issue is classified with a
    verdict: DELETE, KEEP_LEGACY, or WIRE.

    Usage:
        detector = DeadCodeDetector()
        findings = detector.scan_output(code, "python")
        for finding in findings:
            verdict = detector.classify(finding)
        report = detector.generate_report(findings)
    """

    def scan_output(
        self, output: str, language: str = "python"
    ) -> list[DeadCodeIssue]:
        """
        Scan code output for dead code issues.

        Args:
            output: The code to scan
            language: "python" or "typescript"

        Returns:
            List of DeadCodeIssue instances
        """
        if not output:
            return []

        language = language.lower()
        if language in ("typescript", "ts", "tsx", "jsx", "javascript", "js"):
            return self._scan_typescript(output)
        else:
            return self._scan_python(output)

    def _scan_python(self, output: str) -> list[DeadCodeIssue]:
        """Scan Python code for dead code issues."""
        issues: list[DeadCodeIssue] = []
        lines = output.split("\n")

        # Detect unused imports
        imported_symbols: dict[str, int] = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            # from X import a, b, c
            m = re.match(r"^from\s+[\w.]+\s+import\s+(.+)", stripped)
            if m:
                symbols = [s.strip().split(" as ")[0].strip() for s in m.group(1).split(",")]
                for sym in symbols:
                    if sym and sym != "*":
                        imported_symbols[sym] = i + 1
            # import X
            m = re.match(r"^import\s+(\w+)", stripped)
            if m:
                imported_symbols[m.group(1)] = i + 1

        # Check if imported symbols are used elsewhere
        code_without_imports = "\n".join(
            line for line in lines if not line.strip().startswith(("import ", "from "))
        )
        for sym, line_num in imported_symbols.items():
            # Check if symbol appears outside its import line
            pattern = r"\b" + re.escape(sym) + r"\b"
            matches = re.findall(pattern, code_without_imports)
            if not matches:
                issues.append(DeadCodeIssue(
                    file="output",
                    line=line_num,
                    issue_type=IssueType.UNUSED_IMPORT,
                    description=f"Import '{sym}' is never used",
                    symbol=sym,
                ))

        # Detect commented blocks (3+ consecutive comment lines)
        comment_block_start = -1
        comment_block_lines = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                if comment_block_start == -1:
                    comment_block_start = i + 1
                comment_block_lines += 1
            else:
                if comment_block_lines >= 3:
                    issues.append(DeadCodeIssue(
                        file="output",
                        line=comment_block_start,
                        issue_type=IssueType.COMMENTED_BLOCK,
                        description=f"Commented block of {comment_block_lines} lines",
                        symbol=f"lines_{comment_block_start}-{comment_block_start + comment_block_lines - 1}",
                    ))
                comment_block_start = -1
                comment_block_lines = 0
        # Handle trailing block
        if comment_block_lines >= 3:
            issues.append(DeadCodeIssue(
                file="output",
                line=comment_block_start,
                issue_type=IssueType.COMMENTED_BLOCK,
                description=f"Commented block of {comment_block_lines} lines",
                symbol=f"lines_{comment_block_start}-{comment_block_start + comment_block_lines - 1}",
            ))

        # Detect unwired functions (defined but never called)
        defined_functions: dict[str, int] = {}
        for i, line in enumerate(lines):
            m = re.match(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", line)
            if m:
                defined_functions[m.group(1)] = i + 1

        for func_name, line_num in defined_functions.items():
            # Check if function is called (excluding its definition and dunder methods)
            if func_name.startswith("__") and func_name.endswith("__"):
                continue
            # Search for function calls (not definition)
            call_pattern = r"\b" + re.escape(func_name) + r"\s*\("
            call_matches = []
            for i, line in enumerate(lines):
                if i + 1 == line_num:
                    continue  # Skip the definition line
                if re.search(call_pattern, line):
                    call_matches.append(line)
            if not call_matches:
                issues.append(DeadCodeIssue(
                    file="output",
                    line=line_num,
                    issue_type=IssueType.UNWIRED_FUNCTION,
                    description=f"Function '{func_name}' is defined but never called",
                    symbol=func_name,
                ))

        # Detect unreachable code (code after return/raise at same indent level)
        for i in range(len(lines) - 1):
            stripped = lines[i].strip()
            if re.match(r"^\s*(return|raise|sys\.exit)", stripped):
                # Check if next non-empty line is at same or lower indent level
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() and not next_line.strip().startswith(("def ", "class ", "#", "elif ", "else:", "except ", "finally:", "if ")):
                        curr_indent = len(lines[i]) - len(lines[i].lstrip())
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent >= curr_indent and next_line.strip():
                            issues.append(DeadCodeIssue(
                                file="output",
                                line=i + 2,
                                issue_type=IssueType.UNREACHABLE_CODE,
                                description="Code after return/raise is unreachable",
                                symbol=f"line_{i + 2}",
                            ))

        # Detect dead variables (assigned but never used)
        assigned_vars: dict[str, int] = {}
        for i, line in enumerate(lines):
            m = re.match(r"^\s*(\w+)\s*=\s*.+", line)
            if m:
                var_name = m.group(1)
                if not var_name.startswith("_") and var_name not in ("self", "cls"):
                    assigned_vars[var_name] = i + 1

        for var_name, line_num in assigned_vars.items():
            # Check if variable is referenced after its assignment
            ref_pattern = r"\b" + re.escape(var_name) + r"\b"
            used = False
            for i, line in enumerate(lines):
                if i + 1 == line_num:
                    # On the assignment line, check if it's used in RHS too
                    rhs = line.split("=", 1)[1] if "=" in line else ""
                    if re.search(ref_pattern, rhs) and re.search(ref_pattern, rhs).start() != 0:
                        used = True
                        break
                    continue
                if re.search(ref_pattern, line):
                    used = True
                    break
            if not used:
                issues.append(DeadCodeIssue(
                    file="output",
                    line=line_num,
                    issue_type=IssueType.DEAD_VARIABLE,
                    description=f"Variable '{var_name}' is assigned but never used",
                    symbol=var_name,
                ))

        return issues

    def _scan_typescript(self, output: str) -> list[DeadCodeIssue]:
        """Scan TypeScript/JavaScript code for dead code issues."""
        issues: list[DeadCodeIssue] = []
        lines = output.split("\n")

        # Detect unused imports
        imported_symbols: dict[str, int] = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            # import { a, b } from 'x'
            m = re.match(r"^import\s*\{([^}]+)\}\s+from\s+", stripped)
            if m:
                symbols = [s.strip().split(" as ")[0].strip() for s in m.group(1).split(",")]
                for sym in symbols:
                    if sym:
                        imported_symbols[sym] = i + 1
            # import X from 'y'
            m = re.match(r"^import\s+(\w+)\s+from\s+", stripped)
            if m:
                imported_symbols[m.group(1)] = i + 1

        code_without_imports = "\n".join(
            line for line in lines if not line.strip().startswith("import ")
        )
        for sym, line_num in imported_symbols.items():
            pattern = r"\b" + re.escape(sym) + r"\b"
            if not re.search(pattern, code_without_imports):
                issues.append(DeadCodeIssue(
                    file="output",
                    line=line_num,
                    issue_type=IssueType.UNUSED_IMPORT,
                    description=f"Import '{sym}' is never used",
                    symbol=sym,
                ))

        # Detect unwired functions
        defined_functions: dict[str, int] = {}
        for i, line in enumerate(lines):
            m = re.match(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", line)
            if m:
                defined_functions[m.group(1)] = i + 1
                continue
            m = re.match(r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(", line)
            if m:
                defined_functions[m.group(1)] = i + 1

        for func_name, line_num in defined_functions.items():
            call_pattern = r"\b" + re.escape(func_name) + r"\s*[\(\.]"
            call_matches = []
            for i, line in enumerate(lines):
                if i + 1 == line_num:
                    continue
                if re.search(call_pattern, line):
                    call_matches.append(line)
            if not call_matches:
                issues.append(DeadCodeIssue(
                    file="output",
                    line=line_num,
                    issue_type=IssueType.UNWIRED_FUNCTION,
                    description=f"Function '{func_name}' is defined but never called",
                    symbol=func_name,
                ))

        # Detect unreachable code
        for i in range(len(lines) - 1):
            stripped = lines[i].strip()
            if re.match(r"^\s*(return|throw)\s+", stripped):
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() and not next_line.strip().startswith(("//", "}", "else", "catch", "finally")):
                        issues.append(DeadCodeIssue(
                            file="output",
                            line=i + 2,
                            issue_type=IssueType.UNREACHABLE_CODE,
                            description="Code after return/throw is unreachable",
                            symbol=f"line_{i + 2}",
                        ))

        # Detect dead variables
        assigned_vars: dict[str, int] = {}
        for i, line in enumerate(lines):
            m = re.match(r"^\s*(?:const|let|var)\s+(\w+)\s*=\s*.+", line)
            if m:
                assigned_vars[m.group(1)] = i + 1

        for var_name, line_num in assigned_vars.items():
            ref_pattern = r"\b" + re.escape(var_name) + r"\b"
            used = False
            for i, line in enumerate(lines):
                if i + 1 == line_num:
                    continue
                if re.search(ref_pattern, line):
                    used = True
                    break
            if not used:
                issues.append(DeadCodeIssue(
                    file="output",
                    line=line_num,
                    issue_type=IssueType.DEAD_VARIABLE,
                    description=f"Variable '{var_name}' is assigned but never used",
                    symbol=var_name,
                ))

        return issues

    def classify(self, issue: DeadCodeIssue) -> DeadCodeVerdict:
        """
        Classify a dead code issue with a verdict.

        Classification rules:
        - UNUSED_IMPORT → DELETE
        - UNREACHABLE_CODE → DELETE
        - COMMENTED_BLOCK → KEEP_LEGACY (might contain useful info)
        - UNWIRED_FUNCTION → WIRE (might need to be connected)
        - DEAD_VARIABLE → DELETE (unless it's a constant/config)

        Args:
            issue: The DeadCodeIssue to classify

        Returns:
            DeadCodeVerdict indicating what to do
        """
        if issue.issue_type == IssueType.UNUSED_IMPORT:
            return DeadCodeVerdict.DELETE
        elif issue.issue_type == IssueType.UNREACHABLE_CODE:
            return DeadCodeVerdict.DELETE
        elif issue.issue_type == IssueType.COMMENTED_BLOCK:
            return DeadCodeVerdict.KEEP_LEGACY
        elif issue.issue_type == IssueType.UNWIRED_FUNCTION:
            # If it's a test or main function, keep it
            if any(kw in issue.symbol.lower() for kw in ("test", "main", "setup", "handler")):
                return DeadCodeVerdict.KEEP_LEGACY
            return DeadCodeVerdict.WIRE
        elif issue.issue_type == IssueType.DEAD_VARIABLE:
            # Constants and configs might be intentional
            if issue.symbol.isupper() or "config" in issue.symbol.lower():
                return DeadCodeVerdict.KEEP_LEGACY
            return DeadCodeVerdict.DELETE
        else:
            return DeadCodeVerdict.DELETE

    def generate_report(self, findings: list[DeadCodeIssue]) -> str:
        """
        Generate a markdown report of dead code findings.

        Args:
            findings: List of DeadCodeIssue instances

        Returns:
            Markdown formatted report
        """
        if not findings:
            return "# Dead Code Report\n\nNo dead code found. Code is clean! ✨\n"

        # Group by verdict
        by_verdict: dict[str, list[DeadCodeIssue]] = {
            "DELETE": [],
            "KEEP_LEGACY": [],
            "WIRE": [],
        }
        for f in findings:
            verdict = self.classify(f).value
            by_verdict.setdefault(verdict, []).append(f)

        lines = ["# Dead Code Report\n"]
        lines.append(f"**Total issues found:** {len(findings)}\n")

        for verdict_name, issues in by_verdict.items():
            if not issues:
                continue
            lines.append(f"\n## {verdict_name} ({len(issues)})\n")
            lines.append("| Line | Type | Symbol | Description |")
            lines.append("|------|------|--------|-------------|")
            for issue in issues:
                lines.append(
                    f"| {issue.line} | {issue.issue_type.value} | "
                    f"`{issue.symbol}` | {issue.description} |"
                )

        lines.append("")
        return "\n".join(lines)
