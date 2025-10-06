# Nautilus Trader - Installation & Setup Guide

**Last Updated:** October 2025

## Supported Platforms

### Official Support

| Operating System | Versions | CPU Architecture |
|-----------------|----------|------------------|
| Linux (Ubuntu) | 22.04+ | x86_64 |
| Linux (Ubuntu) | 22.04+ | ARM64 |
| macOS | 15.0+ | ARM64 |
| Windows Server | 2022+ | x86_64 |

### Python Versions
- Python 3.11
- Python 3.12
- Python 3.13 (latest supported)

### Requirements

**Linux**: glibc 2.35 or newer
- Check: `ldd --version`

## Installation Methods

### Method 1: From PyPI (Recommended)

```bash
pip install -U nautilus_trader
```

#### With Extras
```bash
# Specific integrations
pip install -U "nautilus_trader[docker,ib]"
```

Available extras:
- `betfair`: Betfair adapter dependencies
- `docker`: Docker support (for IB gateway)
- `dydx`: dYdX adapter dependencies
- `ib`: Interactive Brokers dependencies
- `polymarket`: Polymarket dependencies

### Method 2: From Nautech Package Index

#### Stable Releases
```bash
pip install -U nautilus_trader --index-url=https://packages.nautechsystems.io/simple
```

Or with PyPI fallback:
```bash
pip install -U nautilus_trader --extra-index-url=https://packages.nautechsystems.io/simple
```

#### Development Wheels

**Nightly builds** (from `nightly` branch):
```bash
pip install -U nautilus_trader --pre --index-url=https://packages.nautechsystems.io/simple
```

**Specific nightly version**:
```bash
pip install nautilus_trader==1.221.0a20250912 --index-url=https://packages.nautechsystems.io/simple
```

**Development builds** (from `develop` branch):
- Version format: `dev{date}+{build_number}` (e.g., `1.208.0.dev20241212+7001`)
- Published on every commit to `develop`

⚠️ **Warning**: Development wheels not recommended for production/live trading

#### Wheel Availability

| Platform | Nightly | Develop |
|----------|---------|---------|
| Linux (x86_64) | ✓ | ✓ |
| Linux (ARM64) | ✓ | - |
| macOS (ARM64) | ✓ | ✓ |
| Windows (x86_64) | ✓ | ✓ |

#### Retention Policies
- **Develop wheels**: Only most recent build retained
- **Nightly wheels**: 30 most recent builds retained

#### View Available Versions
```bash
curl -s https://packages.nautechsystems.io/simple/nautilus-trader/index.html | \
  grep -oP '(?<=<a href="))[^"]+(?=")' | awk -F'#' '{print $1}' | sort
```

### Method 3: From Source

#### Prerequisites

**1. Install Rust**

Linux/macOS:
```bash
curl https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env
```

Windows:
- Download [`rustup-init.exe`](https://win.rustup.rs/x86_64)
- Install "Desktop development with C++" via [Build Tools for Visual Studio 2022](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

Verify:
```bash
rustc --version
```

**2. Install Clang**

Linux:
```bash
sudo apt-get install clang
```

Windows:
- Add via Visual Studio Installer: Start → Visual Studio Installer → Modify → "C++ Clang tools for Windows" (latest)
- Enable in PowerShell:
```powershell
[System.Environment]::SetEnvironmentVariable('path', "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\Llvm\x64\bin\;" + $env:Path,"User")
```

Verify:
```bash
clang --version
```

**3. Install uv**

Linux/macOS:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell):
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

#### Build and Install

```bash
# Clone repository
git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
cd nautilus_trader

# Install dependencies and build
uv sync --all-extras
```

#### Set PyO3 Environment (Linux/macOS Only)

```bash
# Set library path (adjust Python version to match yours)
export LD_LIBRARY_PATH="$HOME/.local/share/uv/python/cpython-3.13.4-linux-x86_64-gnu/lib:$LD_LIBRARY_PATH"

# Set Python executable for PyO3
export PYO3_PYTHON=$(pwd)/.venv/bin/python
```

Find your Python path:
```bash
uv python list
```

### Method 4: From GitHub Release

1. Navigate to [latest release](https://github.com/nautechsystems/nautilus_trader/releases/latest)
2. Download appropriate `.whl` for your OS and Python version
3. Install:
```bash
pip install <file-name>.whl
```

## Precision Modes

NautilusTrader supports two precision modes for core value types (`Price`, `Quantity`, `Money`):

### High-Precision (128-bit)
- **Decimal precision**: Up to 16 decimals
- **Value range**: Larger
- **Performance**: ~3-5% slower
- **Platforms**: Linux, macOS (official wheels)
- **Default**: Yes (except Windows)

### Standard-Precision (64-bit)
- **Decimal precision**: Up to 9 decimals
- **Value range**: Smaller
- **Performance**: ~3-5% faster
- **Platforms**: All (required for Windows)
- **Default**: Windows only

### Building with Specific Precision

#### High-Precision (128-bit)
```bash
export HIGH_PRECISION=true
make install-debug
```

#### Standard-Precision (64-bit)
```bash
export HIGH_PRECISION=false
make install-debug
```

### Rust Feature Flag

In `Cargo.toml`:
```toml
[dependencies]
nautilus_core = { version = "*", features = ["high-precision"] }
```

## Redis Setup (Optional)

Redis required only if using as:
- Cache database backend
- Message bus backend

### Minimum Version
Redis 6.2+ (requires streams functionality)

### Quick Start with Docker

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

This will:
- Pull latest Redis from Docker Hub
- Run in detached mode
- Name container "redis"
- Expose port 6379

### Container Management
```bash
docker start redis   # Start container
docker stop redis    # Stop container
```

### GUI Tool
Recommended: [Redis Insight](https://redis.io/insight/) for visualization and debugging

## Package Managers

### Recommended: uv
- Fast and modern
- Works with "vanilla" CPython
- Official documentation: https://docs.astral.sh/uv

### Not Officially Supported
- Conda
- Other Python distributions

These *may* work but aren't tested in CI.

## Virtual Environments

**Always use virtual environments** to isolate dependencies.

With uv:
```bash
uv venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

With venv:
```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

## Versioning and Releases

### Release Schedule
- Target: Weekly releases
- May vary with experimental/large features

### Stability Warning
- Still under active development
- API becoming more stable
- Breaking changes possible between releases
- Release notes document changes (best effort)

⚠️ Use only if prepared to adapt to changes

## Build Dependencies

### Required for Building from Source
- Rust toolchain (rustup)
- Clang
- C++ compiler
- Python headers

### Not Required for Binary Wheels
Pre-built wheels don't require:
- Rust
- Cython
- C++ compiler

## Environment Variables

### Important for Building

**HIGH_PRECISION**: Set precision mode
```bash
export HIGH_PRECISION=true   # 128-bit mode
export HIGH_PRECISION=false  # 64-bit mode
```

**LD_LIBRARY_PATH** (Linux): Python library path
```bash
export LD_LIBRARY_PATH="$HOME/.local/share/uv/python/cpython-3.13.4-linux-x86_64-gnu/lib:$LD_LIBRARY_PATH"
```

**PYO3_PYTHON** (Linux/macOS): Python executable for PyO3
```bash
export PYO3_PYTHON=$(pwd)/.venv/bin/python
```

## Troubleshooting

### glibc Version Error (Linux)
- Ensure glibc 2.35+
- Check: `ldd --version`
- Upgrade system or use newer Ubuntu

### Import Errors
- Verify Python version (3.11-3.13)
- Check virtual environment activated
- Reinstall: `pip install --force-reinstall nautilus_trader`

### Build Errors
- Verify Rust installed: `rustc --version`
- Verify Clang installed: `clang --version`
- Check environment variables set (Linux/macOS)

### Performance Issues
- Consider precision mode (64-bit slightly faster)
- Use release builds, not debug builds
- Check Redis connection if using external backend

## Best Practices

1. **Use Latest Python**: 3.13 recommended
2. **Virtual Environments**: Always isolate dependencies
3. **Binary Wheels**: Use pre-built wheels unless customizing
4. **Package Index**: Nautech index for latest/development builds
5. **Redis**: Use Docker for easy setup
6. **Precision Mode**: High-precision unless Windows or need speed
7. **Updates**: Keep package updated with `pip install -U`
8. **Development Wheels**: Avoid in production

## Quick Start Commands

### Standard Installation
```bash
# Create environment
python -m venv venv
source venv/bin/activate

# Install
pip install -U nautilus_trader

# Verify
python -c "import nautilus_trader; print(nautilus_trader.__version__)"
```

### With Interactive Brokers
```bash
pip install -U "nautilus_trader[docker,ib]"
```

### Development Build
```bash
pip install -U nautilus_trader --pre --index-url=https://packages.nautechsystems.io/simple
```

### Build from Source
```bash
# Prerequisites
curl https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env
sudo apt-get install clang  # Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and build
git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
cd nautilus_trader
uv sync --all-extras
```
