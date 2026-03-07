## 1. Interruption event handling

- [x] 1.1 Subscribe to `AgentSession` interruption events (`agent_speech_interrupted`, `user_state_changed`) in `apps/agent/src/main.py` and implement handler stubs that log the event
- [x] 1.2 Implement LLM generation task cancellation on valid interruption — cancel the active LLM stream when the user interrupts during agent response
- [x] 1.3 Verify TTS playback stops on interruption (SDK-managed via `AgentSession`) and confirm no orphaned TTS audio is played after cancellation

## 2. False interruption recovery

- [x] 2.1 Confirm `resume_false_interruption=True` and `false_interruption_timeout` are correctly wired in `build_session()` and the SDK resumes buffered TTS audio on false interruption
- [x] 2.2 Implement fallback continuation: when a false interruption is detected but the TTS buffer is exhausted, send a continuation prompt to the LLM requesting 1-2 sentences completing the interrupted response
- [x] 2.3 Ensure the proactive silence timer resets correctly after both valid and false interruptions

## 3. Data channel events

- [x] 3.1 Publish `{"type": "interruption_started"}` on the data channel when a valid interruption is detected
- [x] 3.2 Publish `{"type": "interruption_resolved", "resumed": false}` when the interrupted user speech produces a recognized transcript and new response generation begins
- [x] 3.3 Publish `{"type": "interruption_false", "resumed": true}` when a false interruption is detected and the agent resumes its previous response

## 4. Logging and observability

- [x] 4.1 Log all interruption lifecycle events at INFO level with room ID, participant ID, and event type
- [x] 4.2 Log LLM cancellation at DEBUG level including token count generated before cancellation

## 5. Tests

- [x] 5.1 Unit test: valid interruption triggers LLM cancellation and `interruption_started` data channel event
- [x] 5.2 Unit test: false interruption (no transcript within timeout) triggers resume and `interruption_false` data channel event
- [x] 5.3 Unit test: short noise below `MIN_INTERRUPTION_DURATION` does not trigger interruption
- [x] 5.4 Unit test: `FALSE_INTERRUPTION_TIMEOUT=0` disables false interruption detection
- [x] 5.5 Integration test: full interruption cycle — agent speaking → user interrupts → agent cancels → processes new input → responds
