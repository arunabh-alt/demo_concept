# AppBank Proxy 2026 Implementation Plan

## What To Build First

Do not start with full voice biometrics and multi-agent complexity at once.

Build the product in four controlled stages.

## Stage 1: Control Plane MVP

Deliverables:

* FastAPI control plane
* structured request model
* agent orchestration placeholder
* verifier contract placeholder
* audit envelope for every request

Success criteria:

* every request produces a structured action proposal
* no direct action execution yet

## Stage 2: Verification-First Execution

Deliverables:

* verifier rule engine
* risk scoring model
* JIT token abstraction
* simulated proxy executor

Success criteria:

* approved actions can run in sandbox only
* rejected actions provide machine-readable reasons

## Stage 3: Voice and Identity Trust Layer

Deliverables:

* voice enrollment lifecycle
* liveness detection
* speaker matching
* DID and VC validation
* adaptive challenge workflow

Success criteria:

* privileged actions require successful trust pipeline completion

## Stage 4: Realtime Communications

Deliverables:

* streaming STT integration
* low-latency conversational session handling
* TTS output pipeline
* watermarking and transparency controls

Success criteria:

* sub-200 ms interactive path for non-privileged conversation steps
* privileged action latency remains bounded and auditable

## Stage 5: Regulated Deployment Readiness

Deliverables:

* immutable audit pipeline
* observability stack
* incident response hooks
* approval workflow for shadow mode rollout

Success criteria:

* product can run in pilot mode with compliance review evidence

## Recommended Team Split

### Backend Platform

Owns:

* API contracts
* config and deployment
* observability

### Identity and Security

Owns:

* VBA pipeline
* DID and VC integration
* challenge-response layer

### AI and Verification

Owns:

* orchestration design
* verifier logic
* policy mapping

### Execution and Integrations

Owns:

* proxy executor
* JIT credentials
* downstream service integration

## Product Risk To Avoid

Do not ship the following too early:

* direct bank execution from raw LLM output
* voice-only trust without challenge-response
* persistent raw audio retention by default
* mixed ownership between reasoning and execution layers
