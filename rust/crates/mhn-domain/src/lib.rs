//! MHN ARCADE V4 domain and protocol contracts.

use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const PROTOCOL_VERSION: u16 = 1;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Request {
    pub protocol_version: u16,
    pub request_id: String,
    pub kind: String,
    pub operation: String,

    #[serde(default = "empty_object")]
    pub payload: Value,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Response {
    pub protocol_version: u16,
    pub request_id: String,
    pub ok: bool,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub payload: Option<Value>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<ProtocolError>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ProtocolError {
    pub code: String,
    pub message: String,
}

impl Response {
    pub fn success(
        request_id: impl Into<String>,
        payload: Value,
    ) -> Self {
        Self {
            protocol_version: PROTOCOL_VERSION,
            request_id: request_id.into(),
            ok: true,
            payload: Some(payload),
            error: None,
        }
    }

    pub fn failure(
        request_id: impl Into<String>,
        code: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            protocol_version: PROTOCOL_VERSION,
            request_id: request_id.into(),
            ok: false,
            payload: None,
            error: Some(ProtocolError {
                code: code.into(),
                message: message.into(),
            }),
        }
    }
}

fn empty_object() -> Value {
    Value::Object(Default::default())
}
