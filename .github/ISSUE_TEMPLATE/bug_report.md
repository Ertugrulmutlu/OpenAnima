name: Bug Report
description: Report a bug or unexpected behavior in OpenAnima
title: "[BUG] "
labels: ["bug"]

body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to report a bug in OpenAnima.

  - type: textarea
    id: bug_description
    attributes:
      label: Describe the bug
      description: Explain what happened.
      placeholder: A clear and concise description of the issue.
    validations:
      required: true

  - type: textarea
    id: reproduction_steps
    attributes:
      label: Steps to reproduce
      description: How can this issue be reproduced?
      value: |
        1.
        2.
        3.
      render: bash
    validations:
      required: true

  - type: textarea
    id: expected_behavior
    attributes:
      label: Expected behavior
      description: What did you expect to happen?
      placeholder: The overlay should stay visible after restart.
    validations:
      required: true

  - type: dropdown
    id: operating_system
    attributes:
      label: Operating System
      options:
        - Windows 10
        - Windows 11
        - Other
    validations:
      required: true

  - type: input
    id: app_version
    attributes:
      label: OpenAnima Version
      placeholder: v1.0.0
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: Logs or screenshots
      description: Add screenshots or logs if available.
      render: shell

  - type: checkboxes
    id: confirmation
    attributes:
      label: Confirmation
      options:
        - label: I checked existing issues before creating this report.
          required: true
