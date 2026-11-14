
// ! Discord-independent MHN ARCADE V4 engine.

use mhn_domain::{Request, Response, PROTOCOL_VERSION};
use serde_json::json;

pub const ENGINE_NAME: &str = "mhn-engine";

#[derive(Debug, Default)]
pub struct Engine;

impl Engine {
    pub fn handle(&self, request: Request) -> Response {
        if request.protocol_version != PROTOCOL_VERSION {
            return Response::failure(
                request.request_id,
                "unsupported_protocol_version",
                format!("Supported protocol version is {}", PROTOCOL_VERSION),
            );
        }

        if request.kind != "request" {
            return Response::failure(
                request.request_id,
                "invalid_message_kind",
                "Expected kind=request",
            );
        }

        match request.operation.as_str() {
            "system.health" => Response::success(
                request.request_id,
                json!({
                    "status": "ok",
                    "engine": ENGINE_NAME,
                    "engine_version": env!("CARGO_PKG_VERSION"),
                    "protocol_version": PROTOCOL_VERSION
                }),
            ),

            operation => Response::failure(
                request.request_id,
                "unknown_operation",
                format!("Unknown operation: {operation}"),
            ),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_request(operation: &str) -> Request {
        Request {
            protocol_version: PROTOCOL_VERSION,
            request_id: "test-1".to_string(),
            kind: "request".to_string(),
            operation: operation.to_string(),
            payload: json!({}),
        }
    }

    #[test]
    fn health_request_succeeds() {
        let response = Engine.handle(make_request("system.health"));

        assert!(response.ok);
        assert_eq!(response.request_id, "test-1");
        assert_eq!(response.payload.unwrap()["engine"], ENGINE_NAME);
    }

    #[test]
    fn unknown_operation_returns_error() {
        let response = Engine.handle(make_request("unknown.operation"));

        assert!(!response.ok);
        assert_eq!(response.error.unwrap().code, "unknown_operation");
    }

    #[test]
    fn unsupported_protocol_is_rejected() {
        let mut request = make_request("system.health");
        request.protocol_version = PROTOCOL_VERSION + 1;

        let response = Engine.handle(request);

        assert!(!response.ok);
        assert_eq!(response.error.unwrap().code, "unsupported_protocol_version");
    }
}
