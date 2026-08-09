class ObservationRegistrationConflict(ValueError):
    """Raised when an observation ID is reused with different content."""

    def __init__(self, observation_id: str) -> None:
        self.observation_id = observation_id
        super().__init__(f"observation registration conflict: {observation_id}")
