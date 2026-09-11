@real_plc
Feature: Connect to and identify a real PLC

  Background:
    Given I am using a dedicated test PLC
    And the test configuration contains no secrets in reportable fields

  @smoke
  Scenario Outline: Establish and close a session
    Given the client uses the "<protocol>" protocol path
    When I connect to the configured PLC
    Then the client reports that it is connected
    And the negotiated protocol and security mode are recorded
    And the PLC identity and CPU state are recorded when available
    When I disconnect
    Then the client reports that it is disconnected

    @legacy_s7
    Examples: legacy S7
      | protocol   |
      | legacy_s7  |

    @s7commplus
    Examples: S7CommPlus
      | protocol   |
      | s7commplus |
