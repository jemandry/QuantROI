
use std::collections::HashMap; // Should trigger disallowed-types lint

fn main() {
    let result = Some(42).unwrap();
    
    println!("Testing enhanced Clippy rules: {}", result);
    
    let fee_rate = 0.1;
    if fee_rate == 0.1 {
        println!("Fee rate comparison");
    }
    
    let number = 42;
    let _number_string = number.to_string();
    
    let mut _map: HashMap<String, i32> = HashMap::new();
    
    todo!("Implement quantum-resistant encryption");
    
    panic!("This should not be allowed in fintech code");
}

fn undocumented_function() {
    dbg!("Debug output not allowed");
}

fn too_many_args(_a: i32, _b: i32, _c: i32, _d: i32, _e: i32, _f: i32, _g: i32) {
}
