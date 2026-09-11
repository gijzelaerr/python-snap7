@real_plc
Feature: Recover from normal connection lifecycle events

  @smoke
  Scenario Outline: Reconnect after a clean disconnect
    Given the client uses the "<protocol>" protocol path
    And I connected to and disconnected from the PLC
    When I reconnect with the same configuration
    Then a known read succeeds

    @legacy_s7
    Examples: legacy S7
      | protocol   |
      | legacy_s7  |

    @s7commplus
    Examples: S7CommPlus
      | protocol   |
      | s7commplus |

  @smoke
  Scenario Outline: Repeated operations do not corrupt the session
    Given the client uses the "<protocol>" protocol path
    And I am connected to the PLC
    When I read the canonical fixture repeatedly
    Then every read succeeds with the expected value
    And disconnect completes cleanly

    @legacy_s7
    Examples: legacy S7
      | protocol   |
      | legacy_s7  |

    @s7commplus
    Examples: S7CommPlus
      | protocol   |
      | s7commplus |
