#!/bin/bash

set -e

RUST_DIR="src/engine/wasm"
ASSET_DIR="src/assets/wasm"
TARGET="wasm32-unknown-unknown"

echo "Compiling Rust to WASM..."
cd $RUST_DIR
cargo build --release --target $TARGET

echo "Optimizing binary..."
wasm-opt -Oz -o main.wasm target/$TARGET/release/flux.wasm

echo "Moving to assets..."
mkdir -p ../../../$ASSET_DIR
mv main.wasm ../../../$ASSET_DIR/flux.wasm

cd ../../../

echo "Starting dev server..."
npx wrangler pages dev public --port 8787