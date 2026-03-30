# AppBank Proxy 2026 Service Map

## Backend Packages

### `appbank_digital_twin.api`

Purpose:

* HTTP and WebSocket entry points
* request validation
* response envelope generation

### `appbank_digital_twin.schemas`

Purpose:

* typed request and response models
* internal action proposal structures

### `appbank_digital_twin.services`

Purpose:

* orchestration logic
* product use-case services
* composition of verification and execution workflows

### `appbank_digital_twin.core`

Purpose:

* config
* logging
* security primitives
* dependency wiring

## Planned Future Packages

### `appbank_digital_twin.voice_auth`

Purpose:

* liveness detection
* speaker matching
* challenge-response validation

### `appbank_digital_twin.verifier`

Purpose:

* deterministic validation
* policy checks
* risk scoring

### `appbank_digital_twin.proxy_exec`

Purpose:

* JIT token issuance
* downstream task execution
* audit trail creation

### `appbank_digital_twin.memory`

Purpose:

* conversational memory
* approved pattern storage
* retention-governed learning artifacts

## Ownership Rule

The orchestration layer may propose actions, but only the verifier may approve them and only the execution layer may perform them.
