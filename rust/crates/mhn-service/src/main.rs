
// ! JSON Lines process interface.
// ! stdout is reserved for protocol messages.
// ! Logs are written to stderr.

use std::io::{self, BufRead, Write};

use mhn_domain::{Request, Response, PROTOCOL_VERSION};
use mhn_engine::Engine;

fn main() {
    let stdin = io::stdin();
    let mut stdout = io::BufWriter::new(io::stdout());

    let engine = Engine;

    eprintln!(
        "MHN ARCADE Rust service started. Protocol v{}",
        PROTOCOL_VERSION
    );

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(value) => value,
            Err(error) => {
                eprintln!("Input error: {error}");
                break;
            }
        };

        if line.trim().is_empty() {
            continue;
        }

        let response = match serde_json::from_str::<Request>(&line) {
            Ok(request) => engine.handle(request),
            Err(error) => {
                eprintln!("Invalid request JSON: {error}");

                Response::failure("", "invalid_json", "Request must be valid JSON")
            }
        };

        if let Err(error) = serde_json::to_writer(&mut stdout, &response) {
            eprintln!("Serialization error: {error}");
            break;
        }

        if let Err(error) = stdout.write_all(b"\n").and_then(|_| stdout.flush()) {
            eprintln!("Output error: {error}");
            break;
        }
    }

    eprintln!("MHN ARCADE Rust service stopped.");
}
