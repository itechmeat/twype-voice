## MODIFIED Requirements

### Requirement: Route definitions
The system SHALL define the following routes:

| Path | Layout | Component |
|------|--------|-----------|
| `/login` | PublicLayout | LoginPage |
| `/register` | PublicLayout | RegisterPage |
| `/verify` | PublicLayout | VerifyPage |
| `/` | ProtectedLayout | ChatPage |
| `*` | — | Redirect to `/login` |

#### Scenario: Known public route
- **WHEN** a user navigates to `/register`
- **THEN** the `RegisterPage` component SHALL render inside `PublicLayout`

#### Scenario: Known protected route
- **WHEN** an authenticated user navigates to `/`
- **THEN** the `ChatPage` component SHALL render inside `ProtectedLayout`

#### Scenario: Unknown route
- **WHEN** a user navigates to `/nonexistent`
- **THEN** the system SHALL redirect to `/login`
