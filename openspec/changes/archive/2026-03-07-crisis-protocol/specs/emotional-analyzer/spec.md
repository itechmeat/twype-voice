## MODIFIED Requirements

### Requirement: Sliding window trend tracking
The Emotional Analyzer SHALL maintain a sliding window of the last N emotional snapshots (default N=10). Each snapshot SHALL contain valence, arousal, and timestamp. The analyzer SHALL compute trend direction for each dimension: `rising` (mean of recent half > mean of older half + threshold), `falling` (mean of recent half < mean of older half - threshold), or `stable`. The trend threshold SHALL default to 0.1. Additionally, the analyzer SHALL expose a `high_distress` signal that is set to `True` when the last 3 or more consecutive snapshots are in the `distress` quadrant AND the valence trend is `falling`.

#### Scenario: Rising valence trend
- **WHEN** the window contains 6+ snapshots and recent snapshots have consistently higher valence than older ones
- **THEN** the trend for valence is `rising`

#### Scenario: Stable trend with few snapshots
- **WHEN** the window contains fewer than 3 snapshots
- **THEN** both trend dimensions are `stable`

#### Scenario: Window eviction
- **WHEN** the window is full (N snapshots) and a new snapshot is added
- **THEN** the oldest snapshot is evicted and the trend is recomputed

#### Scenario: High distress signal activated
- **WHEN** the last 3 consecutive snapshots are in the `distress` quadrant and valence trend is `falling`
- **THEN** the `high_distress` property returns `True`

#### Scenario: High distress signal deactivated
- **WHEN** the most recent snapshot is not in the `distress` quadrant
- **THEN** the `high_distress` property returns `False`
