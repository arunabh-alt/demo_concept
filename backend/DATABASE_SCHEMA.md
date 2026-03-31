# Digital Twin Database Schema

## Purpose

This document describes the database design for the digital twin backend.

The goal is to support this deterministic request pipeline:

1. Client sends `message`, `agent_id`, and `user_id`
2. FastAPI service builds execution context
3. Direct mode or orchestrator mode is selected
4. Structured response is returned
5. Learning engine stores reusable patterns
6. Memory manager retrieves relevant patterns for later requests
7. Action history and conversation history are persisted

## High-Level Architecture Mapping

The schema supports these architecture components:

- `User / Frontend`: represented by `users`
- `FastAPI Service`: service layer over all tables
- `Role Agent`: represented by `agent_profiles` with role `role_agent`
- `Coordinator Agent`: represented logically by orchestrator mode and persisted in execution records
- `Specialist Agents`: represented logically through `specialists_used` in response payloads and action records
- `Learning Engine`: represented by writes to `memory_patterns`
- `Memory Manager`: represented by reads and updates to `memory_patterns`
- `Secure Storage`: represented by the local SQLAlchemy database, currently SQLite for local development

## Core Tables

### `users`

Stores the authenticated human user.

Fields:

- `id`: UUID primary key
- `full_name`: display name
- `email`: unique login identity
- `password_hash`: hashed password
- `created_at`: creation timestamp

Relationships:

- one-to-many with `agent_profiles`
- one-to-many with `conversations`
- one-to-many with `memory_patterns`
- one-to-many with `action_executions`

### `agent_profiles`

Stores digital twin identities associated with a user.

Fields:

- `id`: UUID primary key
- `user_id`: owner user
- `name`: human-readable agent name
- `role`: `role_agent`, coordinator-like role, or future specialist role
- `mode_preference`: preferred execution mode
- `description`: optional agent description
- `is_primary`: marks the main agent for the user
- `created_at`: creation timestamp

Purpose:

- binds an `agent_id` to a specific user
- enables one user to own multiple digital twins

### `conversations`

Stores a request session between a user and an agent.

Fields:

- `id`: UUID primary key
- `user_id`: owner user
- `agent_id`: responding digital twin
- `title`: truncated request title
- `mode`: `direct` or `orchestrator`
- `created_at`: creation timestamp

Purpose:

- top-level envelope for a request/response exchange

### `conversation_messages`

Stores individual messages inside a conversation.

Fields:

- `id`: UUID primary key
- `conversation_id`: parent conversation
- `role`: `user` or `assistant`
- `content`: message text
- `created_at`: creation timestamp

Purpose:

- audit trail of the request and the returned response

### `memory_patterns`

Stores reusable learned patterns from prior exchanges.

Fields:

- `id`: UUID primary key
- `user_id`: owner user
- `agent_id`: associated agent
- `pattern_key`: compact lookup key such as `transfer_money`
- `pattern_text`: original learned request shape
- `response_template`: last known response pattern
- `usage_count`: retrieval/update frequency
- `last_used_at`: last retrieval or update time
- `created_at`: creation timestamp

Purpose:

- supports the learning engine and memory manager loop
- enables repeated intent handling to reuse prior context

### `action_executions`

Stores structured actions produced by the digital twin.

Fields:

- `id`: UUID primary key
- `user_id`: owner user
- `agent_id`: acting digital twin
- `conversation_id`: related conversation
- `request_message`: original user request
- `intent`: interpreted intent name
- `action_type`: structured action label
- `status`: completed, failed, pending_review
- `amount`: optional monetary amount
- `currency`: optional currency code
- `beneficiary_name`: optional beneficiary
- `response_payload`: structured JSON result
- `notes`: optional execution notes
- `created_at`: creation timestamp

Purpose:

- durable action envelope for audit and downstream execution
- carries transfer or workflow details directly in `response_payload`

## Relationship Summary

```text
users
  -> agent_profiles
  -> conversations
  -> memory_patterns
  -> action_executions

agent_profiles
  -> conversations
  -> memory_patterns
  -> action_executions

conversations
  -> conversation_messages
  -> action_executions (logical association via conversation_id)
```

## Request Pipeline to Data Writes

When a client sends:

```json
{
  "user_id": "...",
  "agent_id": "...",
  "message": "Transfer 500 Pounds to Alice"
}
```

the backend performs this sequence:

1. Validate `user_id` belongs to the authenticated user
2. Validate `agent_id` belongs to that user
3. Retrieve relevant rows from `memory_patterns`
4. Detect intent and choose `direct` or `orchestrator`
5. Create a `conversations` row
6. Create `conversation_messages` rows for user input and assistant response
7. If an action is required, write an `action_executions` row
8. Update or create a `memory_patterns` row through the learning engine
9. Return the structured response envelope to the API caller

## Example: Transfer to Alice

Input:

```text
Transfer 500 Pounds to Alice
```

Expected data dependencies:

- user must exist in `users`
- `agent_id` must exist in `agent_profiles`

Expected writes:

- new `conversations` row
- two `conversation_messages` rows
- new `action_executions` row with `intent=transfer_money`
- upsert-like learning behavior in `memory_patterns`

In the simplified schema, transfer metadata such as beneficiary name, amount, currency, and execution notes are stored directly in `action_executions` and `response_payload`.

## Current Execution Model

Current implementation is deterministic and rule-based.

Direct mode handles:

- `transfer_money`
- `check_balance`

`check_balance` is currently recorded as an action request only. The simplified schema does not store account balances.

Orchestrator mode handles:

- complex financial requests
- general requests that need coordinator-style routing

The current coordinator does not yet persist specialist-specific tables. Instead, specialist participation is recorded in the returned structured response and action details.

## Recommended Next Schema Enhancements

If this project evolves into a fuller agentic platform, add:

- `specialist_agent_profiles` for explicit specialist identity records
- `orchestration_runs` for coordinator-level planning state
- `orchestration_steps` for specialist-by-specialist traces
- `transaction_ledger` for immutable accounting entries if balance tracking returns later
- `policy_checks` for verifier outcomes before action execution
- `learning_events` for explicit learning-engine audit trails
- `memory_embeddings` if semantic retrieval is introduced later

## Current Storage Mode

Local development uses:

- SQLite database at `backend/local.db`

Optional future database target:

- PostgreSQL using the SQL reference in `backend/sql/schema.sql`