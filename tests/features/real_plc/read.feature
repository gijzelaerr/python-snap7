@real_plc
Feature: Read a known test data block

  @smoke
  @classic_s7
  Scenario: Read the canonical fixture
    Given the client uses the classic S7 protocol
    And the read-only test DB has the documented canonical layout
    When I read the complete fixture DB
    Then INT, REAL, BYTE, WORD, DWORD, DINT, CHAR and BOOL values match the fixture
    And individual reads return the same values as the complete-block read

  @smoke
  @classic_s7
  Scenario: Read multiple values in one request
    Given the client uses the classic S7 protocol
    And the read-only test DB has the documented canonical layout
    When I read values of different sizes in one multi-variable request
    Then every value and result code matches the fixture
