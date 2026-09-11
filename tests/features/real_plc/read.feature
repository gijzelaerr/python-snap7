@real_plc
Feature: Read a known test data block

  @smoke
  Scenario Outline: Read the canonical fixture
    Given the client uses the "<protocol>" protocol path
    And the read-only test DB has the documented canonical layout
    When I read the complete fixture DB
    Then INT, REAL, BYTE, WORD, DWORD, DINT, CHAR and BOOL values match the fixture
    And individual reads return the same values as the complete-block read

    @legacy_s7
    Examples: legacy S7
      | protocol   |
      | legacy_s7  |

    @s7commplus
    Examples: S7CommPlus
      | protocol   |
      | s7commplus |

  @smoke
  Scenario Outline: Read multiple values in one request
    Given the client uses the "<protocol>" protocol path
    And the read-only test DB has the documented canonical layout
    When I read values of different sizes in one multi-variable request
    Then every value and result code matches the fixture

    @legacy_s7
    Examples: legacy S7
      | protocol   |
      | legacy_s7  |

    @s7commplus
    Examples: S7CommPlus
      | protocol   |
      | s7commplus |
