# AppBank Proxy 2026 Architecture

## Product Decomposition

The system should be built as a set of explicit control-plane and execution-plane services.

## Core Services

### 1. API Gateway

Responsibilities:

* Receives client requests
* Terminates authentication and session tokens
* Routes traffic to orchestration and verification flows
* Returns signed response envelopes

Suggested implementation:

* FastAPI
* WebSocket support for realtime streaming events
* OpenTelemetry instrumentation

### 2. Identity and Voice Verification Service

Responsibilities:

* Voice enrollment lifecycle
* Liveness detection
* Speaker embedding comparison
* DID and VC binding validation
* Adaptive challenge enforcement

Suggested implementation:

* FastAPI worker service
* Python ML inference pipelines
* Strict separation between raw audio buffers and persistent identity metadata

### 3. Agent Orchestrator

Responsibilities:

* Decide direct mode vs coordinator mode
* Build prompts and tool context
* Route work to role agents and specialist agents
* Produce structured action proposals instead of freeform final actions

Suggested implementation:

* Python service layer
* Clear contract for `proposed_action`, `risk_score`, `required_checks`, and `execution_plan`

### 4. Verifier and Policy Engine

Responsibilities:

* Validate agent outputs before execution
* Enforce business policy and compliance policy
* Score risk and reject hallucinated or unsafe actions
* Run dry-run simulations where possible

Suggested implementation:

* Rule engine plus deterministic validators
* Separate package from the orchestration layer
* Audit every validation decision

### 5. Proxy Execution Service

Responsibilities:

* Issue just-in-time scoped tokens
* Execute approved tasks only
* Record immutable audit logs
* Enforce hard transaction and operation constraints

Suggested implementation:

* Separate service boundary from agent reasoning
* Integrate with vault, IAM, and downstream systems

### 6. Learning and Memory Service

Responsibilities:

* Store approved patterns and non-sensitive interaction features
* Retrieve role or user context
* Support post-conversation learning with policy-aware filtering

Suggested implementation:

* Short-term memory cache
* Long-term secure storage
* Feature-level retention rather than raw audio retention

## Build Order

1. API gateway and control contracts
2. Verifier and policy engine
3. Identity and voice verification
4. Proxy execution layer
5. Realtime STT and TTS integration
6. Agent specialization and learning loops

## MVP Architecture

The first product milestone should avoid over-distribution.

Start with a modular monolith in Python:

* one FastAPI app
* one orchestration package
* one verifier package
* one proxy-execution package
* one voice-auth package

Split into microservices only after contracts, logs, and policies stabilize.
