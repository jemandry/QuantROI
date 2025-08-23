FROM rust:1.79.0-slim as builder

RUN apt-get update && apt-get install -y curl pkg-config libssl-dev && \
    curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

ENV PATH="/usr/local/cargo/bin:/root/.cargo/bin:$PATH"

WORKDIR /wasm_verifier

COPY Cargo.toml ./
COPY src/ ./src/

RUN wasm-pack build --target web

FROM python:3.12-slim

WORKDIR /wasm_verifier

COPY --from=builder /wasm_verifier/pkg ./pkg

EXPOSE 8081

CMD ["python", "-m", "http.server", "8081"]
