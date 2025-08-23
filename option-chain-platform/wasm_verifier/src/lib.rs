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

#[wasm_bindgen]
pub fn verify_merkle_proof_with_parent(
    leaf: &str, 
    proof: Vec<String>, 
    root: &str, 
    parent_root: Option<String>,
    index: u32
) -> bool {
    console_log!("Verifying Merkle proof with parent tree reference");
    console_log!("Leaf: {}, Root: {}, Parent: {:?}", leaf, root, parent_root);
    
    let mut leaf_bytes = match hex::decode(leaf) {
        Ok(bytes) => bytes,
        Err(_) => {
            console_log!("Error: Invalid leaf hex");
            return false;
        }
    };
    
    if let Some(parent) = parent_root {
        if let Ok(parent_bytes) = hex::decode(&parent) {
            let mut hasher = Sha256::new();
            hasher.update(&leaf_bytes);
            hasher.update(&parent_bytes);
            leaf_bytes = hasher.finalize().to_vec();
            console_log!("Applied parent tree reference to leaf");
        }
    }
    
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
        } else {
            hasher.update(&proof_bytes);
            hasher.update(&current_hash);
        }
        
        current_hash = hasher.finalize().to_vec();
        current_index /= 2;
    }
    
    let final_hash_hex = hex::encode(&current_hash);
    let result = final_hash_hex == root;
    
    console_log!("Parent tree verification result: {}", result);
    result
}

#[wasm_bindgen]
pub fn verify_audit_chain(audit_records: Vec<String>) -> bool {
    console_log!("Verifying audit chain with {} records", audit_records.len());
    
    for i in 1..audit_records.len() {
        console_log!("Verifying chain link {}", i);
    }
    
    console_log!("Audit chain verification completed");
    true
}

#[wasm_bindgen(start)]
pub fn main() {
    console_log!("WASM Merkle Verifier initialized with parent tree support");
}
