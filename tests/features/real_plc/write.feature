@real_plc @write
Feature: Write safely to a scratch data block

  @classic_s7
  Scenario Outline: Round-trip a value and restore the PLC
    Given the client uses the classic S7 protocol
    And writing has been explicitly enabled
    And I have a dedicated scratch DB
    And the original bytes for <type> have been saved
    When I write a valid <type> value
    Then reading the address returns the written value
    And the original bytes are restored and verified

    Examples: classic S7 values
      | type  |
      | INT   |
      | REAL  |
      | BYTE  |
      | WORD  |
      | DWORD |
      | DINT  |
      | CHAR  |
      | BOOL  |
