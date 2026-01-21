# Install Rust to D: Drive
# This script sets environment variables to install Rust on D: instead of C:

Write-Host "Installing Rust to D: Drive..." -ForegroundColor Green

# Set environment variables for this session
$env:CARGO_HOME = "D:\.cargo"
$env:RUSTUP_HOME = "D:\.rustup"

# Create directories if they don't exist
New-Item -ItemType Directory -Force -Path "D:\.cargo" | Out-Null
New-Item -ItemType Directory -Force -Path "D:\.rustup" | Out-Null

Write-Host "Cargo will be installed to: $env:CARGO_HOME" -ForegroundColor Cyan
Write-Host "Rustup will be installed to: $env:RUSTUP_HOME" -ForegroundColor Cyan

# Set permanent environment variables (user-level)
[System.Environment]::SetEnvironmentVariable('CARGO_HOME', 'D:\.cargo', 'User')
[System.Environment]::SetEnvironmentVariable('RUSTUP_HOME', 'D:\.rustup', 'User')

Write-Host "`nEnvironment variables set!" -ForegroundColor Green
Write-Host "Now running the Rust installer..." -ForegroundColor Yellow

# Run the installer
Start-Process -FilePath "C:\Users\Lenovo\Downloads\rustup-init.exe" -Wait

Write-Host "`nInstallation complete!" -ForegroundColor Green
Write-Host "Rust is now installed to D: drive" -ForegroundColor Green
Write-Host "`nIMPORTANT: Close this PowerShell window and open a NEW one" -ForegroundColor Yellow
Write-Host "Then verify with: cargo --version" -ForegroundColor Cyan
