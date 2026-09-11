# LRX Termux Environment

Date checked: 2026-09-11

Project path:

`/data/data/com.termux/files/home/Project/Model_build_content_2026_0910`

## Operating System

- Runtime: Termux on Android
- Kernel: `Linux localhost 6.6.77-android15-8-gf9a1d4bd8353-abogki440974771-4k #1 SMP PREEMPT Fri Aug 29 01:48:34 UTC 2025 aarch64 Android`
- Shell used by Codex: `bash`
- Timestamp command result: `Fri Sep 11 06:38:36 UTC 2026`

## Repository Context

- Remote: `https://github.com/WHKLY/Model_build_content_2026_0910.git`
- Branch: `main`
- Upstream: `origin/main`
- Working tree before this documentation update: clean

## MWorks/Syslab Availability

This Termux environment is not the project runtime for MWorks/Syslab. It is useful for repository inspection, Markdown edits, and Git operations, but it should not be treated as proof that the `.jl` scripts run in Syslab.

The recorded Windows MWorks/Syslab environment remains in `env/LRX_env.md`.

## Command Notes

Several commands returned exit code `182` without output in this Termux session, including some version queries and broader Git inspection commands. `termux-info` did not complete promptly and was interrupted. Because of that, this note records only the values that were observed directly.

## Runtime Decision

Do not add Termux-specific dependencies to the project. The primary executable environment remains MWorks/Syslab, and Termux should be used only as an auxiliary environment for lightweight file and Git work unless the team decides otherwise.
