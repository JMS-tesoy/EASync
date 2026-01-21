# Rust Installation Guide for Windows

## 📥 Step-by-Step Installation

### Step 1: Download the Installer

![Rust Download Page](file:///C:/Users/Lenovo/.gemini/antigravity/brain/9e68c9b4-79be-4d71-949b-7b1cbf5c2919/rust_windows_download_1768918094922.png)

1. **Visit:** https://rustup.rs/
2. **Click:** "rustup-init.exe (64-bit)" button
3. **Save** the file to your Downloads folder

---

### Step 2: Run the Installer

1. **Locate** the downloaded file: `rustup-init.exe`
2. **Double-click** to run it
3. **If Windows SmartScreen appears:**
   - Click "More info"
   - Click "Run anyway"

---

### Step 3: Installation Options

When the installer runs, you'll see:

```
Welcome to Rust!

This will download and install the official compiler for the Rust
programming language, and its package manager, Cargo.

Current installation options:

   default host triple: x86_64-pc-windows-msvc
     default toolchain: stable (default)
               profile: default
  modify PATH variable: yes

1) Proceed with installation (default)
2) Customize installation
3) Cancel installation
>
```

**What to do:**
- Press **1** (or just press Enter) to proceed with default installation
- This is the recommended option for most users

---

### Step 4: Wait for Installation

The installer will:
1. Download Rust components (~400 MB)
2. Install the Rust compiler (`rustc`)
3. Install Cargo (package manager)
4. Add Rust to your PATH

**This takes 5-10 minutes** depending on your internet speed.

You'll see output like:
```
info: downloading component 'cargo'
info: downloading component 'rustc'
info: installing component 'cargo'
info: installing component 'rustc'
```

---

### Step 5: Installation Complete

When finished, you'll see:

```
Rust is installed now. Great!

To get started you may need to restart your current shell.
This would reload your PATH environment variable to include
Cargo's bin directory (%USERPROFILE%\.cargo\bin).

Press the Enter key to continue.
```

**Press Enter** to close the installer.

---

### Step 6: Restart Your Terminal

**IMPORTANT:** You must restart PowerShell/Command Prompt for the changes to take effect.

1. **Close** all open PowerShell/Command Prompt windows
2. **Open** a new PowerShell window

---

### Step 7: Verify Installation

In the new PowerShell window, run:

```powershell
cargo --version
```

**Expected output:**
```
cargo 1.75.0 (1d8b05cdd 2024-01-01)
```

Also check:
```powershell
rustc --version
```

**Expected output:**
```
rustc 1.75.0 (82e1608df 2024-01-01)
```

✅ **If you see version numbers, Rust is installed successfully!**

---

## 🎯 Next Steps: Build the Ingest Server

Now that Rust is installed, let's build the ingest server:

### 1. Navigate to the Project

```powershell
cd "d:\Antigravity Project\Fintech Systems Architect\ingest-server"
```

### 2. Build the Server (First Time)

```powershell
cargo build --release
```

**What happens:**
- Downloads dependencies (tokio, prost, redis, etc.)
- Compiles Protobuf definitions
- Builds the server in release mode (optimized)

**This takes 3-5 minutes the first time** (subsequent builds are much faster).

You'll see:
```
   Compiling proc-macro2 v1.0.70
   Compiling unicode-ident v1.0.12
   Compiling libc v0.2.151
   ...
   Compiling tokio v1.35.1
   Compiling ingest-server v0.1.0
    Finished release [optimized] target(s) in 3m 45s
```

### 3. Run the Server

```powershell
cargo run --release
```

**Expected output:**
```
2026-01-20T22:10:00Z INFO  ingest_server: Initializing IngestServer on 0.0.0.0:9000
2026-01-20T22:10:00Z INFO  ingest_server: Connected to Redis pool at redis://127.0.0.1:6379
2026-01-20T22:10:00Z INFO  ingest_server: Server listening on 0.0.0.0:9000
```

✅ **Server is running!**

---

## 🧪 Test the Server

In a **new PowerShell window**, run:

```powershell
# Test connection
Test-NetConnection -ComputerName localhost -Port 9000
```

**Expected:**
```
TcpTestSucceeded : True
```

Or use the Python test client:

```powershell
cd "d:\Antigravity Project\Fintech Systems Architect\ingest-server"
python test_client.py
```

---

## ❓ Troubleshooting

### Issue: "cargo: command not found"

**Solution:** Restart your terminal (PowerShell/CMD)

### Issue: "error: linker 'link.exe' not found"

**Solution:** Install Visual Studio Build Tools
1. Download: https://visualstudio.microsoft.com/downloads/
2. Install "Build Tools for Visual Studio 2022"
3. Select "Desktop development with C++"

### Issue: "Cannot connect to Redis"

**Solution:** Make sure Redis is running
```powershell
# If using WSL
wsl redis-server

# Or install Redis for Windows
# https://github.com/microsoftarchive/redis/releases
```

### Issue: Build is slow

**Solution:** This is normal for the first build. Subsequent builds are much faster (5-10 seconds).

---

## 📚 Useful Cargo Commands

```powershell
# Build (debug mode, faster compilation)
cargo build

# Build (release mode, optimized)
cargo build --release

# Run the server
cargo run --release

# Check for errors (no compilation)
cargo check

# Run tests
cargo test

# Clean build artifacts
cargo clean

# Update dependencies
cargo update
```

---

## ✅ Installation Checklist

- [ ] Downloaded rustup-init.exe
- [ ] Ran installer
- [ ] Chose option 1 (default installation)
- [ ] Waited for installation to complete
- [ ] Restarted terminal
- [ ] Verified with `cargo --version`
- [ ] Navigated to ingest-server directory
- [ ] Ran `cargo build --release`
- [ ] Server compiled successfully
- [ ] Ran `cargo run --release`
- [ ] Server is listening on port 9000

---

## 🎉 Success!

Once you see "Server listening on 0.0.0.0:9000", your Rust installation and ingest server are working perfectly!

You're now ready to process high-frequency trading signals with sub-20ms latency! 🚀
