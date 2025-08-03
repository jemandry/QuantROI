use wasm_bindgen::prelude::*;
use sha2::{Digest, Sha256};
use hex;

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    fn log(s: &str);
}

macro_rules! console_log {
    ($($t:tt)*) => (log(&format_args!($($t)*).to_string()))
}

#[wasm_bindgen]
pub fn verify_merkle_proof(leaf: &str, proof: Vec<String>, root: &str, index: u32) -> bool {
    console_log!("Verifying Merkle proof for leaf: {}", leaf);
    console_log!("Root: {}", root);
    console_log!("Index: {}", index);
    console_log!("Proof length: {}", proof.len());
    
    let leaf_bytes = match hex::decode(leaf) {
        Ok(bytes) => bytes,
        Err(_) => {
            console_log!("Error: Invalid leaf hex");
            return false;
        }
    };
    
    let mut current_hash = leaf_bytes;
    let mut current_index = index;
    
    for (i, proof_hex) in proof.iter().enumerate() {
        console_log!("Processing proof element {}: {}", i, proof_hex);
        
        let proof_bytes = match hex::decode(proof_hex) {
            Ok(bytes) => bytes,
            Err(_) => {
                console_log!("Error: Invalid proof hex at index {}", i);
                return false;
            }
        };
        
        let mut hasher = Sha256::new();
        if current_index % 2 == 0 {
            hasher.update(&current_hash);
            hasher.update(&proof_bytes);
            console_log!("Left child: concatenating current || proof");
        } else {
            hasher.update(&proof_bytes);
            hasher.update(&current_hash);
            console_log!("Right child: concatenating proof || current");
        }
        
        current_hash = hasher.finalize().to_vec();
        current_index /= 2;
        
        console_log!("New hash: {}", hex::encode(&current_hash));
    }
    
    let final_hash_hex = hex::encode(&current_hash);
    let result = final_hash_hex == root;
    
    console_log!("Final hash: {}", final_hash_hex);
    console_log!("Expected root: {}", root);
    console_log!("Verification result: {}", result);
    
    result
}

#[wasm_bindgen]
pub fn hash_data(data: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data.as_bytes());
    hex::encode(hasher.finalize())
}

#[wasm_bindgen(start)]
pub fn main() {
    console_log!("WASM Merkle Verifier initialized");
}
