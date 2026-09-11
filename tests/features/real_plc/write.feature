@real_plc @write
Feature: Write safely to a scratch data block

  Scenario Outline: Round-trip a value and restore the PLC
    Given the client uses the "<protocol>" protocol path
    And writing has been explicitly enabled
    And I have a dedicated scratch DB
    And the original bytes for <type> have been saved
    When I write a valid <type> value
    Then reading the address returns the written value
    And the original bytes are restored and verified

    @legacy_s7
    Examples: legacy S7
      | protocol   | type  |
      | legacy_s7  | INT   |
      | legacy_s7  | REAL  |
      | legacy_s7  | BYTE  |
      | legacy_s7  | WORD  |
      | legacy_s7  | DWORD |
      | legacy_s7  | DINT  |
      | legacy_s7  | CHAR  |
      | legacy_s7  | BOOL  |

    @s7commplus
    Examples: S7CommPlus
      | protocol   | type  |
      | s7commplus | INT   |
      | s7commplus | REAL  |
      | s7commplus | BYTE  |
      | s7commplus | WORD  |
      | s7commplus | DWORD |
      | s7commplus | DINT  |
      | s7commplus | CHAR  |
      | s7commplus | BOOL  |
