#!/bin/bash
set -e

echo "=== Anchor CLI Source Build Script for GLIBC Compatibility ==="
echo "This script builds Anchor CLI from source to avoid GLIBC 2.38/2.39 issues"

echo "Current GLIBC version:"
ldd --version

if ! command -v rustc &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
fi

if ! command -v solana &> /dev/null; then
    echo "Installing Solana CLI..."
    sh -c "$(curl -sSfL https://release.solana.com/v1.18.22/install)"
    export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"
fi

echo "Building Anchor CLI from source..."
cd /tmp
git clone https://github.com/coral-xyz/anchor
cd anchor
git checkout v0.29.0

export RUSTFLAGS="-C link-arg=-Wl,--no-as-needed -C link-arg=-l:libc.so.6"

cargo build --release --bin anchor

sudo cp target/release/anchor /usr/local/bin/anchor
chmod +x /usr/local/bin/anchor

cargo install cargo-build-sbf --locked

echo "Verifying installation..."
anchor --version
solana --version
cargo build-sbf --help

echo "✅ Anchor CLI built from source successfully!"
echo "You can now use 'anchor build' and 'anchor test' commands"
