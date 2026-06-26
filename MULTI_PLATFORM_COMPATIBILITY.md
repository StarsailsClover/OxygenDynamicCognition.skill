# Multi-Platform Compatibility Guide
## Oxygen Dynamic Cognition v26.0-alpha.8

**Author**: StarsailsClover
**Date**: 2026-06-26
**Version**: v26.0-alpha.8

---

## 1. Supported Platforms

Oxygen Dynamic Cognition is designed to work across all major operating systems:

| Platform | Status | Notes |
|----------|--------|-------|
| **Linux** | ✅ Fully Supported | Primary development and testing platform |
| **macOS** | ✅ Fully Supported | Tested on macOS 12+ (Intel & Apple Silicon) |
| **Windows** | ✅ Fully Supported | Tested on Windows 10/11 (PowerShell & CMD) |

---

## 2. Compatibility Considerations

### 2.1 Path Handling

**Status**: ✅ Cross-platform compatible

All file path operations use `pathlib.Path` which handles platform-specific path separators automatically:

```python
from pathlib import Path

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
```

**Avoid**:
- Hardcoded path separators (`/` or `\`)
- `os.path.join` with string literals containing separators

### 2.2 Line Endings

**Status**: ✅ Handled by Git

Git is configured to handle line ending conversion:
- Linux/macOS: LF (`\n`)
- Windows: CRLF (`\r\n`)

Git's `core.autocrlf` setting handles this automatically.

### 2.3 Console Output Formatting

**Status**: ✅ Fixed in Alpha 8

**Before (Alpha 7)**: Used emoji characters which may not render correctly on all terminals:
```
⚡ **动态认知 [L1]**
📊 置信度：85/100
```

**After (Alpha 8)**: Uses `[TAG]` format for maximum compatibility:
```
[L1] [Dynamic Cognition]
[Confidence] 85.0%
[Rounds] 3
```

This ensures consistent rendering across:
- Windows CMD/PowerShell
- macOS Terminal
- Linux terminals (bash, zsh, etc.)
- CI/CD output logs
- IDE integrated terminals

### 2.4 Character Encoding

**Status**: ✅ UTF-8 by default

All files use UTF-8 encoding with proper BOM handling:
- Source files: UTF-8 without BOM
- Markdown files: UTF-8 without BOM
- JSON output: UTF-8 with `ensure_ascii=False`

### 2.5 Python Version

**Status**: ✅ Python 3.8+

The codebase is compatible with Python 3.8 and above:
- Uses `from __future__ import annotations` where needed
- Type hints compatible with 3.8+ syntax
- No 3.10+ exclusive features (match statement, etc.)

**Tested versions**:
- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12 (primary development)

### 2.6 Threading and Concurrency

**Status**: ✅ Cross-platform compatible

L5 parallel reasoning uses `concurrent.futures.ThreadPoolExecutor` which is available on all platforms:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(task, arg): arg for arg in args}
    for future in as_completed(futures):
        result = future.result()
```

**Notes**:
- Thread count is limited to 3 (matching reasoning paths)
- GIL limitations apply equally across platforms
- I/O-bound tasks (API calls) benefit most from threading

### 2.7 File System Operations

**Status**: ✅ Cross-platform compatible

All file operations use standard library functions that work across platforms:
- `open()` with `encoding='utf-8'`
- `pathlib.Path` for path manipulation
- `json` module for JSON files

### 2.8 Environment Variables

**Status**: ✅ Cross-platform compatible

API keys and configuration use `os.environ` which works on all platforms:

```python
api_key = os.environ.get("OPENAI_API_KEY")
```

**Platform-specific variable names are avoided** - the same variable names work everywhere.

---

## 3. Platform-Specific Notes

### 3.1 Windows

**Known considerations**:
- Maximum path length: 260 characters (default). Enable long paths if needed.
- Python executable may be `python` or `py` depending on installation
- PowerShell execution policy may need adjustment for scripts

**Recommended**:
- Use Python from python.org (not Windows Store version)
- Add Python to PATH during installation
- Use Git Bash or WSL for best terminal experience

### 3.2 macOS

**Known considerations**:
- Apple Silicon (M1/M2/M3): Python runs natively via arm64
- Homebrew is recommended for Python installation
- Gatekeeper may block unsigned packages

**Recommended**:
- Use `brew install python` for latest Python
- Use virtual environments for dependency isolation

### 3.3 Linux

**Known considerations**:
- Most distributions include Python 3 by default
- `python3` and `pip3` are standard commands
- Development headers may need separate installation

**Recommended**:
- Use system package manager for Python (apt, dnf, pacman, etc.)
- Install `python3-venv` for virtual environments

---

## 4. Testing Across Platforms

### 4.1 Core Functionality Tests

All tests should pass on every supported platform:

```bash
# Mock mode test (no API key needed)
python -m scripts.dynamic_cognition_v26 --question "What is 2+2?" --mock

# Agent-native mode test
python -c "from scripts import create_skill_engine; print('OK')"

# Import test
python -c "from scripts import OxygenDynamicCognitionV26, LLMBackend; print('All imports OK')"
```

### 4.2 CI/CD Pipeline

For automated cross-platform testing, use GitHub Actions matrix:

```yaml
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Test imports
        run: python -c "from scripts import OxygenDynamicCognitionV26; print('OK')"
      - name: Test mock mode
        run: python -m scripts.dynamic_cognition_v26 -q "test" --mock --json
```

---

## 5. Dependencies

### 5.1 Core Dependencies

| Dependency | Purpose | Platform Compatibility |
|------------|---------|----------------------|
| `openai` | OpenAI API client | ✅ Cross-platform |
| Python Standard Library | Core functionality | ✅ Cross-platform |

### 5.2 Optional Dependencies

| Dependency | Purpose | Platform Compatibility |
|------------|---------|----------------------|
| `tiktoken` | Accurate token counting | ✅ Cross-platform |
| `numpy` | Advanced calculations | ✅ Cross-platform |

---

## 6. Installation

### 6.1 All Platforms (Universal)

```bash
# Clone the repository
git clone https://github.com/StarsailsClover/OxygenDynamicCognition.skill.git
cd OxygenDynamicCognition.skill

# Install dependencies
pip install openai

# Test installation
python -m scripts.dynamic_cognition_v26 --version
```

### 6.2 As a Skill

When loaded as a skill by an agent framework, no additional installation is needed beyond the skill directory.

---

## 7. Known Issues and Workarounds

### 7.1 Windows: Long Paths

**Issue**: Paths longer than 260 characters may fail on Windows.

**Workaround**:
1. Enable long paths in Windows (requires admin):
   ```
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```
2. Or use a shorter base directory path.

### 7.2 All Platforms: OpenAI SDK Version

**Issue**: Different versions of the OpenAI SDK may have different APIs.

**Workaround**: Pin the version:
```bash
pip install openai>=1.0.0
```

---

## 8. Version History

| Version | Compatibility Improvements |
|---------|---------------------------|
| v26.0-alpha.8 | Changed console output from emoji to [TAG] format; Added cross-platform documentation; Verified pathlib usage |
| v26.0-alpha.7 | Initial v26 engine release |
| v2.0.0 | Initial v2 engine release |

---

## 9. Reporting Platform Issues

If you encounter a platform-specific issue, please report it with:
- Operating system and version
- Python version
- Exact error message and stack trace
- Steps to reproduce

Report issues at: https://github.com/StarsailsClover/OxygenDynamicCognition.skill/issues
