## ADDED Requirements

### Requirement: Microphone toggle button
The system SHALL provide a button that toggles the user's microphone on and off. When the microphone is enabled, the local audio track SHALL be published to the LiveKit room. When disabled, the track SHALL be muted. The button SHALL visually reflect the current state (muted/unmuted).

#### Scenario: Microphone initially enabled
- **WHEN** the user connects to the LiveKit room
- **THEN** the microphone SHALL be enabled by default and the audio track published

#### Scenario: User mutes microphone
- **WHEN** the user clicks the microphone toggle while it is enabled
- **THEN** the local audio track SHALL be muted and the button SHALL display the muted state

#### Scenario: User unmutes microphone
- **WHEN** the user clicks the microphone toggle while it is muted
- **THEN** the local audio track SHALL be unmuted and the button SHALL display the active state

### Requirement: Audio level visualization
The system SHALL display a real-time audio level indicator when the microphone is active. The visualization SHALL reflect the current input volume level from the local audio track.

#### Scenario: User speaking
- **WHEN** the user speaks into the microphone
- **THEN** the audio level indicator SHALL animate to reflect the voice amplitude

#### Scenario: Silence
- **WHEN** no audio input is detected
- **THEN** the audio level indicator SHALL show a minimal/idle state

#### Scenario: Microphone muted
- **WHEN** the microphone is muted
- **THEN** the audio level indicator SHALL be hidden or show a disabled state

### Requirement: Agent audio visualization
The system SHALL display an audio level indicator for the agent's voice output when the agent is speaking. The visualization SHALL reflect the agent's audio track volume.

#### Scenario: Agent speaking
- **WHEN** the agent's audio track is active and producing audio
- **THEN** the agent audio indicator SHALL animate to reflect the output amplitude

#### Scenario: Agent silent
- **WHEN** the agent is not producing audio
- **THEN** the agent audio indicator SHALL show an idle state
