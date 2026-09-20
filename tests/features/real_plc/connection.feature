@real_plc
Feature: Connect to and identify a real PLC

  Background:
    Given I am using a dedicated test PLC
    And the test configuration contains no secrets in reportable fields

  @smoke
  @classic_s7
  Scenario: Establish and close a session
    Given the client uses the classic S7 protocol
    When I connect to the configured PLC
    Then the client reports that it is connected
    And the negotiated protocol and security mode are recorded
    And the PLC identity and CPU state are recorded when available
    When I disconnect
    Then the client reports that it is disconnected
