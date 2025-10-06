Feature: Auto tests

Scenario: User can reset password via email link – AC1
  Given As per story
  When Given the user has requested a reset email, when the link is used the password can be changed.
  Then Acceptance criterion satisfied


Scenario: User can reset password via email link – AC2
  Given As per story
  When Email link expires after one use.
  Then Acceptance criterion satisfied

