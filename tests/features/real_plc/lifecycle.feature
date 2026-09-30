@real_plc
Feature: Recover from normal connection lifecycle events

  @smoke
  @classic_s7
  Scenario: Reconnect after a clean disconnect
    Given the client uses the classic S7 protocol
    And I connected to and disconnected from the PLC
    When I reconnect with the same configuration
    Then a known read succeeds

  @smoke
  @classic_s7
  Scenario: Repeated operations do not corrupt the session
    Given the client uses the classic S7 protocol
    And I am connected to the PLC
    When I read the canonical fixture repeatedly
    Then every read succeeds with the expected value
    And disconnect completes cleanly
